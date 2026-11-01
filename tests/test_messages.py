import re
from decimal import Decimal

import pytest

from app.confirm import PendingStore, answer_word, read_amount
from app.messages import (
    MESSAGES,
    fee_usd,
    format_amount,
    say_duration,
    say_fee,
    spell_number,
)

ERROR_KEYS = [
    "empty_text",
    "too_long",
    "no_parser",
    "parser_failed",
    "invalid_amount",
    "missing_token",
    "same_token",
    "unknown_token",
    "unknown_token_long",
    "token_not_on_chain",
    "no_price",
    "quote_rejected",
    "upstream",
    "expired",
    "amount_again",
    "not_understood",
]


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("key", ERROR_KEYS)
def test_errors_say_what_happened_and_what_to_do(key, lang):
    message = MESSAGES[lang][key]
    assert len(re.findall(r"[.!?](?:\s|$)", message)) >= 2, message
    assert not re.search(r"\b[45]\d\d\b", message)


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_both_languages_have_the_same_messages(lang):
    assert MESSAGES[lang].keys() == MESSAGES["tr"].keys()


@pytest.mark.parametrize(
    "value, lang, expected",
    [
        ("1.50", "tr", "1,5"),
        ("1.50", "en", "1.5"),
        ("2.000000", "tr", "2"),
        ("100", "tr", "100"),
        ("1000", "en", "1000"),
        ("0.1234567", "en", "0.123456"),
        ("0", "tr", "0"),
    ],
)
def test_format_amount_for_screen_readers(value, lang, expected):
    assert format_amount(value, lang) == expected


def test_format_amount_never_rounds_a_minimum_up():
    assert format_amount("1.9999999", "en") == "1.999999"


@pytest.mark.parametrize(
    "number, expected",
    [
        (0, "sıfır"),
        (101, "yüz bir"),
        (500, "beş yüz"),
        (1000, "bin"),
        (1500, "bin beş yüz"),
        (2025, "iki bin yirmi beş"),
        (11000, "on bir bin"),
        (1000000, "bir milyon"),
    ],
)
def test_spell_number_turkish(number, expected):
    assert spell_number(number, "tr") == expected


@pytest.mark.parametrize(
    "number, expected",
    [
        (101, "one hundred one"),
        (500, "five hundred"),
        (1234, "one thousand two hundred thirty-four"),
        (15000, "fifteen thousand"),
        (2000000, "two million"),
    ],
)
def test_spell_number_english(number, expected):
    assert spell_number(number, "en") == expected


def test_spell_number_falls_back_to_digits_when_huge():
    assert spell_number(10**12, "tr") == "1000000000000"


def test_fee_is_the_value_lost_between_input_and_output():
    assert fee_usd({"amountInUsd": "500.00", "amountOutUsd": "498.76"}) == Decimal("1.24")


def test_better_output_is_not_a_negative_fee():
    assert fee_usd({"amountInUsd": "10", "amountOutUsd": "11"}) == 0


@pytest.mark.parametrize("quote", [{}, {"amountInUsd": "0", "amountOutUsd": "1"}])
def test_missing_usd_values_mean_no_fee_information(quote):
    assert fee_usd(quote) is None
    assert say_fee(None, "tr") == "Ücret bilgisi yok."


def test_tiny_fee_is_not_read_as_zero():
    assert say_fee(Decimal("0.001"), "tr") == "Ücret: 0,01 dolardan az."


def test_long_durations_use_minutes():
    assert say_duration(12, "tr") == "12 saniye"
    assert say_duration(300, "en") == "5 minutes"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("evet", "yes"),
        (" Evet! ", "yes"),
        ("yes", "yes"),
        ("hayır", "no"),
        ("HAYIR", "no"),
        ("İPTAL", "no"),
        ("no", "no"),
        ("evet ama değil", None),
        ("", None),
    ],
)
def test_answer_word(text, expected):
    assert answer_word(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("10", "10"),
        ("1,5", "1,5"),
        ("0.25", "0.25"),
        ("50 USDC", "50"),
        ("50 usdc'yi", "50"),
        ("yarım", "0.5"),
        ("iki", "2"),
        ("half", "0.5"),
        ("50 dolar", None),
        ("50 SOL", None),
        ("1.000", None),
        ("1,000", None),
        ("çok", None),
        ("", None),
    ],
)
def test_read_amount(text, expected):
    assert read_amount(text, "USDC") == expected


def test_store_drops_the_oldest_question_when_full(monkeypatch):
    monkeypatch.setattr("app.confirm.MAX_OPEN", 2)
    store = PendingStore()
    first = store.add("confirm", "tr")
    second = store.add("confirm", "tr")
    third = store.add("confirm", "tr")
    assert store.get(first) is None
    assert store.get(second) and store.get(third)
