"""Emergency stop and control words, in both languages. No network, no real key."""
import pytest

import app.main as main
from app.commands import detect_command
from tests.test_freeze import SETTINGS, controls  # noqa: F401  (fixture)
from tests.test_quote import make_client, payload

AGENT_SECRETS = (
    "NEAR_INTENTS_AGENT_API_KEY", "AGENT_API_KEY", "AGENT_ID", "GRANT_TOKEN",
    "OWNER_ACCOUNT_ID", "OWNER_PUBLIC_KEY", "OWNER_PRIVATE_KEY",
)


@pytest.fixture(autouse=True)
def no_agent_reads(monkeypatch):
    """Every agent read is a stand-in here, so no test can reach the real Agent API."""
    async def policy():
        return {"status": "APPLIED", "provider_policy_synced": True,
                "policy": {"frozen": False, "actions": ["swap"], "assets": ["a"], "budget": {}}}

    async def balances():
        return {"balances": []}

    monkeypatch.setattr(main, "read_agent_policy", policy)
    monkeypatch.setattr(main, "read_agent_balances", balances)


@pytest.fixture
def agent(monkeypatch):
    for name, value in SETTINGS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("GRANT_TOKEN", raising=False)


@pytest.fixture
def no_agent(monkeypatch):
    for name in AGENT_SECRETS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def no_parser(monkeypatch):
    async def fail(text):
        raise AssertionError("control words must not reach the language model")

    monkeypatch.setattr(main, "parse_intent", fail)


def ask(client, text, pending=None, lang=None):
    body = {"text": text}
    if lang:
        body["lang"] = lang
    if pending:
        body["pending"] = pending
    return client.post("/api/ask", json=body).json()


# --- Which words mean what ---------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("freeze", ("freeze", "en")),
        ("Freeze!", ("freeze", "en")),
        ("freeze it", ("freeze", "en")),
        ("freeze now", ("freeze", "en")),
        ("freeze the agent", ("freeze", "en")),
        ("please freeze the wallet", ("freeze", "en")),
        ("stop the agent", ("freeze", "en")),
        ("pause the agent", ("freeze", "en")),
        ("halt the bot", ("freeze", "en")),
        ("stop everything", ("freeze", "en")),
        ("emergency stop", ("freeze", "en")),
        ("dondur", ("freeze", "tr")),
        ("hemen dondur", ("freeze", "tr")),
        ("ajanı dondur", ("freeze", "tr")),
        ("ajanı durdur", ("freeze", "tr")),
        ("Ajanı duraklat.", ("freeze", "tr")),
        ("her şeyi durdur", ("freeze", "tr")),
        ("acil durdur", ("freeze", "tr")),
    ],
)
def test_clear_stop_words_freeze(text, expected):
    assert detect_command(text) == expected


@pytest.mark.parametrize(
    "text, lang",
    [("stop", "en"), ("Stop.", "en"), ("stop please", "en"), ("pause", "en"), ("halt", "en"),
     ("durdur", "tr"), ("Dur!", "tr"), ("durdur lütfen", "tr")],
)
def test_a_bare_stop_asks_first(text, lang):
    assert detect_command(text) == ("freeze_ask", lang)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("unfreeze", ("unfreeze", "en")),
        ("unfreeze the agent", ("unfreeze", "en")),
        ("resume", ("unfreeze", "en")),
        ("resume the agent", ("unfreeze", "en")),
        ("unpause the agent", ("unfreeze", "en")),
        ("çöz", ("unfreeze", "tr")),
        ("ajanı çöz", ("unfreeze", "tr")),
        ("devam et", ("unfreeze", "tr")),
        ("ajanı devam ettir", ("unfreeze", "tr")),
        ("dondurmayı kaldır", ("unfreeze", "tr")),
    ],
)
def test_resume_words_unfreeze(text, expected):
    assert detect_command(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("what's my budget", ("budget", "en")),
        ("budget", ("budget", "en")),
        ("my daily limit", ("budget", "en")),
        ("bütçe", ("budget", "tr")),
        ("günlük limitim ne kadar", ("budget", "tr")),
        ("policy", ("policy", "en")),
        ("what are my limits", ("policy", "en")),
        ("my limits", ("policy", "en")),
        ("politika", ("policy", "tr")),
        ("limitlerim ne", ("policy", "tr")),
        ("history", ("history", "en")),
        ("my transactions", ("history", "en")),
        ("show my history", ("history", "en")),
        ("what did I trade", ("history", "en")),
        ("geçmiş", ("history", "tr")),
        ("işlemlerim", ("history", "tr")),
        ("what's my balance", ("balance", "en")),
    ],
)
def test_reading_commands_in_plain_words(text, expected):
    assert detect_command(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "stop loss",
        "set a stop loss at 3 dollars",
        "swap 1 NEAR to USDC and stop",
        "swap 2 NEAR to USDC, then stop",
        "stop voice mode",
        "what is the freeze cooldown",
        "dondurma fiyatı ne",
        "dondurma",
        "2 NEAR'ı USDC'ye çevir ve dur",
        "durum ne",
        "swap 2 NEAR to USDC on Base",
        "help",
        "merhaba",
    ],
)
def test_swap_and_ordinary_sentences_never_freeze(text):
    found = detect_command(text)
    assert found is None or found[0] not in ("freeze", "freeze_ask", "unfreeze"), (text, found)


# --- What the page hears and does ----------------------------------------------------

@pytest.mark.parametrize("text", ["freeze", "stop the agent", "pause the agent", "dondur", "ajanı durdur"])
def test_clear_stop_signs_at_once(agent, controls, no_parser, text):  # noqa: F811
    client, _ = make_client()
    data = ask(client, text)
    assert controls == ["agent_freeze"]
    assert data.get("signed") is True


def test_bare_stop_asks_and_signs_nothing(agent, controls, no_parser):  # noqa: F811
    client, _ = make_client()
    data = ask(client, "stop")
    assert controls == []
    assert data["action"] == "freeze_ask"
    assert data["spoken"].startswith("Do you want to freeze the agent?")
    assert data["answer_required"] is True
    assert data["pending"]


def test_yes_to_the_question_freezes(agent, controls, no_parser):  # noqa: F811
    client, _ = make_client()
    key = ask(client, "stop")["pending"]
    data = ask(client, "yes", key, lang="en")
    assert controls == ["agent_freeze"]
    assert data["spoken"].startswith("The agent is frozen")


def test_turkish_question_and_evet(agent, controls, no_parser):  # noqa: F811
    client, _ = make_client()
    data = ask(client, "durdur")
    assert data["spoken"].startswith("Ajanı dondurmamı istiyor musun?")
    ask(client, "evet", data["pending"], lang="tr")
    assert controls == ["agent_freeze"]


@pytest.mark.parametrize("answer", ["no", "hayır", ""])
def test_no_or_silence_freezes_nothing(agent, controls, no_parser, answer):  # noqa: F811
    client, _ = make_client()
    key = ask(client, "stop")["pending"]
    data = ask(client, answer, key, lang="en")
    assert controls == []
    assert data["action"] == "cancelled"
    assert "pending" not in data


def test_a_new_sentence_after_the_question_is_read_as_new(agent, controls, no_parser):  # noqa: F811
    client, _ = make_client()
    key = ask(client, "stop")["pending"]
    data = ask(client, "read my policy", key, lang="en")
    # Reading the policy is a fresh command, and the question is gone.
    assert controls == []
    assert data["action"] == "policy"
    assert data["spoken"].startswith("Policy: allowed actions are swap. One asset is allowed.")
    assert ask(client, "yes", key, lang="en")["action"] == "expired"


def test_bare_stop_cancels_an_open_quote_and_signs_nothing(agent, controls):  # noqa: F811
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    data = ask(client, "stop", key, lang="en")
    assert controls == []
    assert data["action"] == "cancelled"
    # The quote was asked in Turkish, so the reply follows the quote's language.
    assert data["spoken"].startswith("İptal ettim, işlem yapılmadı.")
    assert "ajanı dondur" in data["spoken"]
    assert ask(client, "yes", key, lang="en")["action"] == "expired"


def test_freeze_still_cuts_through_an_open_quote(agent, controls):  # noqa: F811
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    ask(client, "freeze", key, lang="en")
    assert controls == ["agent_freeze"]


def test_resume_asks_for_the_code(agent, controls, no_parser):  # noqa: F811
    client, _ = make_client()
    data = ask(client, "resume")
    assert controls == []
    assert data["action"] == "unfreeze"
    assert "type this code" in data["spoken"]


def test_bare_stop_with_no_agent_says_so(no_agent, no_parser):
    client, _ = make_client()
    data = ask(client, "stop")
    assert data["spoken"].startswith("The agent wallet is not set up.")
    assert "pending" not in data


def test_public_demo_explains_agent_commands(no_agent, no_parser, monkeypatch):
    monkeypatch.setattr(main, "public_demo", True)
    client, _ = make_client()
    english = ask(client, "what's my balance")["spoken"]
    turkish = ask(client, "politikamı oku")["spoken"]
    assert english.startswith("This is the public demo")
    assert "demo video" in english
    assert turkish.startswith("Bu herkese açık demo")
    assert "Demo videosu" in turkish


@pytest.mark.parametrize("live", [False, True])
def test_help_names_the_agent_commands(live, monkeypatch):
    from app.messages import say

    for lang, words in (("en", ("balance", "policy", "freeze", "withdraw")),
                        ("tr", ("cüzdanımda", "politikamı", "dondur", "çek"))):
        text = say("help_live" if live else "help", lang)
        for word in words:
            assert word in text, (lang, word)
