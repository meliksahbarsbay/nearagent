"""Amounts as people say them. These never reach a model or a network."""
import pytest

from app.amounts import find_amount, normalize_number, number_or_same, read_answer, tokenize
from app.intent import Intent, apply_amount

SWAP = {"USDC", "SOL"}


@pytest.mark.parametrize(
    "text, lang, expected",
    [
        ("1.000", "tr", "1000"),
        ("1.000", "en", "1"),
        ("1,000", "en", "1000"),
        ("1,000", "tr", "1"),
        ("1,5", "tr", "1.5"),
        ("1,5", "en", "1.5"),
        ("1.5", "tr", "1.5"),
        ("1.5", "en", "1.5"),
        ("1.234,56", "tr", "1234.56"),
        ("1,234.56", "en", "1234.56"),
        ("1,234.56", "tr", "1234.56"),
        ("1.234.567", "tr", "1234567"),
        ("1,234,567", "en", "1234567"),
        ("0.125", "tr", "0.125"),
        ("0,125", "tr", "0.125"),
        ("50", "tr", "50"),
        ("50.", "en", "50"),
        ("$50", "en", "50"),
        ("10.00", "en", "10"),
    ],
)
def test_local_digits(text, lang, expected):
    assert normalize_number(text, lang) == expected


@pytest.mark.parametrize("text", ["", "abc", "1.2.3", "12.34.56", "1,2,3", "1.23,4,5"])
def test_malformed_digits_are_refused(text):
    assert normalize_number(text, "tr") is None


@pytest.mark.parametrize(
    "text, lang, value",
    [
        ("yarım SOL al", "tr", "0.5"),
        ("yarim SOL", "tr", "0.5"),
        ("çeyrek SOL", "tr", "0.25"),
        ("üç çeyrek SOL", "tr", "0.75"),
        ("bir buçuk SOL", "tr", "1.5"),
        ("iki buçuk SOL", "tr", "2.5"),
        ("bir SOL", "tr", "1"),
        ("on bir SOL", "tr", "11"),
        ("yüz elli USDC", "tr", "150"),
        ("bin beş yüz USDC", "tr", "1500"),
        ("iki bin yirmi beş USDC", "tr", "2025"),
        ("üç yüz USDC", "tr", "300"),
        ("half a SOL", "en", "0.5"),
        ("half SOL", "en", "0.5"),
        ("a quarter SOL", "en", "0.25"),
        ("one and a half SOL", "en", "1.5"),
        ("two and a half SOL", "en", "2.5"),
        ("fifty-five USDC", "en", "55"),
        ("a hundred USDC", "en", "100"),
        ("one hundred and fifty USDC", "en", "150"),
        ("two thousand USDC", "en", "2000"),
    ],
)
def test_number_words(text, lang, value):
    found = find_amount(text, lang, SWAP)
    assert found.value == value
    assert found.usd is False


@pytest.mark.parametrize(
    "text, lang, value, token",
    [
        ("elli dolar", "tr", "50", None),
        ("elli dolarlık SOL al", "tr", "50", "SOL"),
        ("50 dolarlık SOL al", "tr", "50", "SOL"),
        ("bin dolarlık SOL", "tr", "1000", "SOL"),
        ("1.000 dolarlık SOL", "tr", "1000", "SOL"),
        ("yüz elli dolar", "tr", "150", None),
        ("fifty dollars", "en", "50", None),
        ("fifty dollars of SOL", "en", "50", "SOL"),
        ("50 dollars worth of SOL", "en", "50", "SOL"),
        ("$50 of SOL", "en", "50", "SOL"),
        ("50$ of SOL", "en", "50", "SOL"),
        ("buy SOL for 1,000 USD", "en", "1000", None),
    ],
)
def test_dollar_amounts(text, lang, value, token):
    found = find_amount(text, lang, SWAP)
    assert (found.value, found.usd, found.token) == (value, True, token)


@pytest.mark.parametrize(
    "text, lang",
    [
        ("bir şey sor", "tr"),
        ("SOL kaç dolar", "tr"),
        ("on Solana", "en"),
        ("one of my friends", "en"),
        ("3 kişi", "tr"),
        ("swap USDC to SOL", "en"),
    ],
)
def test_nothing_is_read_without_a_unit(text, lang):
    assert find_amount(text, lang, SWAP) is None


def test_english_on_is_never_ten():
    assert find_amount("USDC on SOL", "en", SWAP) is None


def test_turkish_suffixes_are_cut():
    assert tokenize("NEAR'ı 1,5 SOL'u") == ["near", "1,5", "sol"]
    assert tokenize("NEAR’ı") == ["near"]


def test_token_names_count():
    found = find_amount("yarım bitcoin", "tr", {"BTC"})
    assert (found.value, found.token) == ("0.5", "BTC")


def intent(**fields):
    return Intent(**{"action": "swap", "language": "tr", **fields})


def test_buying_by_dollars_pays_with_usdc_for_an_exact_output():
    result = apply_amount("50 dolarlık SOL al", intent(to_token="SOL"))
    assert result.amount == "50"
    assert result.amount_unit == "usd"
    assert result.amount_side == "to"
    assert result.from_token == "USDC"


def test_model_saying_usd_counts_as_no_source():
    result = apply_amount("50 dolarlık SOL al", intent(from_token="USD", to_token="SOL"))
    assert result.from_token == "USDC"
    assert result.amount_side == "to"


def test_named_payment_token_is_kept():
    text = "USDT ile 50 dolarlık SOL al"
    result = apply_amount(text, intent(from_token="USDT", to_token="SOL"))
    assert result.from_token == "USDT"
    assert result.amount_side == "to"


def test_buying_a_token_amount_is_an_exact_output():
    result = apply_amount("2 SOL al", intent(to_token="SOL"))
    assert (result.amount, result.amount_unit, result.amount_side) == ("2", "token", "to")
    assert result.from_token == "USDC"


def test_selling_by_dollars_stays_on_the_input_side():
    text = "50 dolarlık SOL'u USDC'ye çevir"
    result = apply_amount(text, intent(from_token="SOL", to_token="USDC"))
    assert (result.amount_unit, result.amount_side) == ("usd", "from")


def test_dollars_with_no_token_named_after_stay_on_the_input_side():
    text = "elli dolar USDC'yi SOL'a çevir"
    result = apply_amount(text, intent(from_token="USDC", to_token="SOL"))
    assert (result.amount, result.amount_unit, result.amount_side) == ("50", "usd", "from")


def test_plain_swap_is_unchanged():
    result = apply_amount(
        "2 NEAR'ı USDC'ye çevir", intent(from_token="NEAR", to_token="USDC", amount="2")
    )
    assert (result.amount, result.amount_unit, result.amount_side) == ("2", "token", "from")


def test_same_token_on_two_chains_stays_on_the_input_side():
    result = apply_amount("10 USDC gönder", intent(from_token="USDC", to_token="USDC"))
    assert result.amount_side == "from"


def test_code_overrides_a_model_that_misread_the_thousands():
    result = apply_amount(
        "1.000 USDC'yi SOL'a çevir", intent(from_token="USDC", to_token="SOL", amount="1")
    )
    assert result.amount == "1000"


def test_english_keeps_one_for_the_same_digits():
    result = apply_amount(
        "swap 1.000 USDC to SOL",
        intent(language="en", from_token="USDC", to_token="SOL", amount="1"),
    )
    assert result.amount == "1"


def test_model_amount_stands_when_code_reads_nothing():
    result = apply_amount(
        "iki kere USDC'yi SOL'a çevir", intent(from_token="USDC", to_token="SOL", amount="2")
    )
    assert result.amount == "2"


def test_help_is_untouched():
    result = apply_amount("50 dolar", intent(action="help"))
    assert result.amount is None


def test_price_in_dollars():
    result = apply_amount("50 dolar kaç SOL", intent(action="price", from_token="SOL"))
    assert (result.amount, result.amount_unit) == ("50", "usd")
    assert result.amount_side == "from"


@pytest.mark.parametrize(
    "text, lang",
    [("50 dolar kaç SOL", "tr"), ("how much SOL is 50 dollars", "en"), ("how many SOL for $50", "en")],
)
def test_a_question_never_becomes_an_offer(text, lang):
    result = apply_amount(text, intent(language=lang, to_token="SOL"))
    assert result.action == "price"
    assert result.from_token == "SOL"
    assert result.to_token is None
    assert result.amount_unit == "usd"


def test_an_order_with_dollars_stays_a_swap():
    assert apply_amount("50 dolarlık SOL al", intent(to_token="SOL")).action == "swap"


@pytest.mark.parametrize(
    "text, lang, value, usd, token",
    [
        ("10", "tr", "10", False, None),
        ("1,5", "tr", "1.5", False, None),
        ("0.25", "en", "0.25", False, None),
        ("1.000", "tr", "1000", False, None),
        ("1.000", "en", "1", False, None),
        ("50 USDC", "tr", "50", False, "USDC"),
        ("50 usdc'yi", "tr", "50", False, "USDC"),
        ("yarım", "tr", "0.5", False, None),
        ("bir buçuk", "tr", "1.5", False, None),
        ("elli", "tr", "50", False, None),
        ("iki", "tr", "2", False, None),
        ("half", "en", "0.5", False, None),
        ("half a SOL", "en", "0.5", False, "SOL"),
        ("fifty dollars", "en", "50", True, None),
        ("50 dolar", "tr", "50", True, None),
        ("elli dolarlık", "tr", "50", True, None),
        ("$20", "en", "20", True, None),
    ],
)
def test_answers_to_how_much(text, lang, value, usd, token):
    answer = read_answer(text, lang, SWAP)
    assert (answer.value, answer.usd, answer.token) == (value, usd, token)


@pytest.mark.parametrize(
    "text",
    ["", "çok", "biraz", "50 NEAR", "50 kişi", "10 USDC ve 5 SOL", "evet 10", "1 SOL kaç dolar"],
)
def test_other_answers_are_asked_again(text):
    assert read_answer(text, "tr", SWAP) is None


def test_form_amount_uses_local_digits():
    assert number_or_same("1.000", "tr") == "1000"
    assert number_or_same("1,5", "tr") == "1.5"
    assert number_or_same("abc", "tr") == "abc"
