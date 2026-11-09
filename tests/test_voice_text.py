"""Voice mode reads spoken numbers and misheard token names. Typed text stays as it was."""
import pytest

import app.main as main
from app.amounts import find_amount
from app.intent import Intent, apply_amount
from app.voice_text import amount_answer, normalize_voice, two_heard_as_to
from tests.test_quote import make_client


@pytest.mark.parametrize(
    "heard, written",
    [
        ("sıfır virgül beş", "0,5"),
        ("sıfır virgül 5", "0,5"),
        ("1 virgül 5", "1,5"),
        ("bir virgül yirmi beş NEAR", "1,25 NEAR"),
        ("bir virgül iki yüz elli NEAR", "1,2500 NEAR"),
        ("iki virgül sıfır sıfır bir NEAR", "2,0010 NEAR"),
        ("sıfır nokta beş NEAR", "0,5 NEAR"),
        ("one point two", "1.2"),
        ("one point two five NEAR", "1.25 NEAR"),
        ("zero point five near to usdc", "0.5 near to USDC"),
        ("sıfır virgül beş NEAR'ı USDC'ye çevir", "0,5 NEAR'ı USDC'ye çevir"),
    ],
)
def test_spoken_decimals_become_numbers(heard, written):
    assert normalize_voice(heard) == written


@pytest.mark.parametrize(
    "heard, written",
    [
        ("yarım nir'ı USDC'ye çevir", "yarım NEAR'ı USDC'ye çevir"),
        ("yarım niyar", "yarım NEAR"),
        ("bir near'ı u es di si'ye çevir", "bir near'ı USDC'ye çevir"),
        ("iki USD C'ye", "iki USDC'ye"),
        ("swap one near to u s d c", "swap one near to USDC"),
        ("bir eter", "bir ETH"),
    ],
)
def test_misheard_tokens_are_fixed(heard, written):
    assert normalize_voice(heard) == written


@pytest.mark.parametrize(
    "heard",
    ["evet onaylıyorum", "yes I confirm", "ajanı dondur", "son işlemlerimi oku", "read my recent trades", "bu noktada iki", "0,5", "yarım NEAR"],
)
def test_other_sentences_stay_as_heard(heard):
    assert normalize_voice(heard) == heard


@pytest.mark.parametrize(
    "heard, lang, value",
    [
        ("sıfır virgül beş NEAR", "tr", "0.5"),
        ("bir virgül iki yüz elli NEAR", "tr", "1.25"),
        ("one point two five NEAR", "en", "1.25"),
        ("bir virgül iki yüz elli NEAR", "en", "1.25"),
    ],
)
def test_the_amount_reader_gets_the_right_value(heard, lang, value):
    assert find_amount(normalize_voice(heard), lang, {"NEAR"}).value == value


def test_spoken_decimal_was_read_wrong_without_this():
    """The reason for this file: the words alone read as 5."""
    assert find_amount("sıfır virgül beş NEAR", "tr", {"NEAR"}).value == "5"


@pytest.mark.parametrize(
    "heard, kept",
    [("yarım NEAR çevir", "yarım NEAR"), ("1 tane", "1"), ("0,5 olsun", "0,5"), ("make it two", "two"), ("lütfen yarım", "yarım")],
)
def test_amount_answers_lose_extra_words(heard, kept):
    assert amount_answer(heard) == kept


# Through the page


def ask_for_amount(client, monkeypatch, voice):
    seen = []

    async def fake_parse(text):
        seen.append(text)
        return Intent(action="swap", from_token="USDC", from_chain="base", to_token="SOL", language="tr")

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    data = client.post("/api/ask", json={"text": "USDC'yi SOL'a çevir", "voice": voice}).json()
    assert data["spoken"] == "Ne kadar çevirmek istiyorsun?"
    return data["pending"]


@pytest.mark.parametrize("heard", ["sıfır virgül beş", "yarım tane", "0,5 olsun", "sıfır virgül beş USDC çevir", "yarım u es di si"])
def test_a_spoken_amount_answer_is_read(monkeypatch, heard):
    client, sent = make_client()
    key = ask_for_amount(client, monkeypatch, voice=True)
    offer = client.post("/api/ask", json={"text": heard, "pending": key, "voice": True, "lang": "tr"}).json()
    assert offer["action"] == "swap"
    assert sent[0]["amount"] == "500000"


@pytest.mark.parametrize("typed", ["sıfır virgül beş", "yarım tane"])
def test_a_typed_amount_answer_is_unchanged(monkeypatch, typed):
    client, sent = make_client()
    key = ask_for_amount(client, monkeypatch, voice=False)
    data = client.post("/api/ask", json={"text": typed, "pending": key, "lang": "tr"}).json()
    assert data["spoken"].startswith("Miktarı anlayamadım.")
    assert sent == []


def capture_parse(monkeypatch):
    seen = []

    async def fake_parse(text):
        seen.append(text)
        # The model misread 5, and the real code step reads the amount from the text.
        return apply_amount(text, Intent(action="swap", amount="5", from_token="NEAR", to_token="USDC", language="tr"))

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    return seen


def test_a_spoken_sentence_reaches_the_parser_and_amount_reader_fixed(monkeypatch):
    client, sent = make_client()
    seen = capture_parse(monkeypatch)
    client.post("/api/ask", json={"text": "sıfır virgül beş nir'ı USDC'ye çevir", "voice": True})
    assert seen == ["0,5 NEAR'ı USDC'ye çevir"]
    # The code reads the amount from the sentence, so the model's 5 is replaced by 0.5.
    assert sent[0]["amount"] == "500000000000000000000000"


def test_a_typed_sentence_reaches_the_parser_as_written(monkeypatch):
    client, _ = make_client()
    seen = capture_parse(monkeypatch)
    client.post("/api/ask", json={"text": "sıfır virgül beş nir'ı USDC'ye çevir"})
    assert seen == ["sıfır virgül beş nir'ı USDC'ye çevir"]


# Whisper hears SOL as "soul", and two as "to".


@pytest.mark.parametrize(
    "heard, written",
    [
        ("How much is one soul in dollars?", "How much is one SOL in dollars?"),
        ("swap 2 soul to eth", "swap 2 SOL to eth"),
        ("swap 3 souls to usdc", "swap 3 SOL to USDC"),
        ("swap zero point five soul to near", "swap 0.5 SOL to near"),
        ("swap 1 eth to soul", "swap 1 eth to SOL"),
        ("convert usdc into Soul", "convert USDC into SOL"),
        ("Swap to soul to eth.", "Swap to SOL to eth."),
        ("iki soul'u USDC'ye çevir", "iki SOL'u USDC'ye çevir"),
    ],
)
def test_soul_is_sol_where_a_token_goes(heard, written):
    assert normalize_voice(heard) == written


@pytest.mark.parametrize(
    "heard",
    [
        "my soul",
        "soul music",
        "read my soul to me",
        "a soul to keep",
        "put on soul music",
        "souls",
        "consoul 2 near",
        "soulful",
    ],
)
def test_soul_stays_a_word_elsewhere(heard):
    assert normalize_voice(heard) == heard


@pytest.mark.parametrize(
    "heard, words",
    [
        ("Swap to SOL to ETH.", ("SOL", "ETH")),
        ("swap to near to usdc", ("near", "usdc")),
        ("  Swap to eth to sol?", ("eth", "sol")),
    ],
)
def test_swap_to_x_to_y_is_noticed(heard, words):
    assert two_heard_as_to(heard) == words


@pytest.mark.parametrize(
    "heard",
    [
        "swap 1 near to usdc",
        "swap 2 SOL to ETH",
        "swap SOL to ETH",
        "swap to SOL",
        "swap to ETH to SOL on Base",
        "convert to SOL to ETH",
        "swap to dollars to SOL",
        "send to SOL to ETH",
        "swap two SOL to ETH",
        "I want to swap to SOL to ETH",
    ],
)
def test_to_is_never_a_number_elsewhere(heard):
    assert two_heard_as_to(heard) is None
    # And the text itself is never changed to a number.
    assert "2" not in normalize_voice(heard).replace("swap 2 SOL", "")


def test_normal_sentences_are_not_changed():
    assert normalize_voice("swap 1 near to usdc") == "swap 1 near to USDC"
    assert normalize_voice("swap 2 SOL to ETH") == "swap 2 SOL to ETH"


def no_parser_call(monkeypatch):
    seen = []

    async def fake_parse(text):
        seen.append(text)
        raise AssertionError("the parser must not be asked")

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    return seen


@pytest.mark.parametrize("extra", [{"voice": True}, {"source": "dictation"}])
def test_spoken_swap_to_asks_with_the_amount_before_any_quote(monkeypatch, extra):
    client, sent = make_client()
    seen = no_parser_call(monkeypatch)
    data = client.post("/api/ask", json={"text": "Swap to soul to eth.", "lang": "en", **extra}).json()
    assert data["action"] == "repair"
    assert data["spoken"] == "Did you mean: swap 2 SOL to ETH? Say yes or no."
    assert sent == [] and seen == []


def test_no_refuses_the_guessed_two(monkeypatch):
    client, sent = make_client()
    no_parser_call(monkeypatch)
    key = client.post("/api/ask", json={"text": "Swap to soul to eth.", "lang": "en", "voice": True}).json()["pending"]
    data = client.post("/api/ask", json={"text": "no", "pending": key, "lang": "en", "voice": True, "confidence": 0.95}).json()
    assert data["action"] == "cancelled"
    assert sent == []


def test_yes_quotes_two(monkeypatch):
    client, sent = make_client()
    no_parser_call(monkeypatch)
    key = client.post("/api/ask", json={"text": "Swap to soul to eth.", "lang": "en", "voice": True}).json()["pending"]
    data = client.post("/api/ask", json={"text": "yes", "pending": key, "lang": "en", "voice": True, "confidence": 0.95}).json()
    assert len(sent) == 1
    # SOL has 9 decimals, so 2 SOL is 2000000000. The mock quote's own text says 1 SOL.
    assert sent[0]["amount"] == "2000000000"
    assert data["action"] != "cancelled"


def test_typed_swap_to_is_not_guessed(monkeypatch):
    client, _ = make_client()
    seen = []

    async def fake_parse(text):
        seen.append(text)
        return Intent(action="swap", amount=None, from_token="SOL", to_token="ETH", language="en")

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    data = client.post("/api/ask", json={"text": "Swap to soul to eth.", "lang": "en"}).json()
    assert seen == ["Swap to soul to eth."]
    assert data.get("action") != "repair" or "2 SOL" not in data["spoken"]
