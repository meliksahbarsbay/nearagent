"""Voice mode: live money moves only on the whole phrase, heard clearly.

Typed answers and the Confirm button send no voice fields, and keep the old rules.
"""
from decimal import Decimal

import pytest

import app.live as live
import app.main as main
import app.messages as messages
from app.confirm import voice_clear, voice_confirms, voice_says_no
from tests.test_live import agent, offer, swap_body  # noqa: F401
from app.intent import Intent
from tests.test_quote import make_client
from tests.test_withdraw import wallet  # noqa: F401

CLEAR = 0.95


def use_swap(monkeypatch, language):
    async def fake_parse(text):
        return Intent(action="swap", amount="4", from_token="USDC", to_token="SOL", language=language)

    monkeypatch.setattr(main, "parse_intent", fake_parse)


def voice_offer(client, monkeypatch, language="tr"):
    """A live swap heard by voice: 4 USDC to SOL."""
    use_swap(monkeypatch, language)
    return client.post("/api/ask", json={"text": "4 USDC'yi SOL'a çevir", "live": True, "voice": True}).json()


def say(client, key, text, confidence=CLEAR, alternatives=(), lang="tr"):
    body = {"text": text, "pending": key, "lang": lang, "voice": True, "alternatives": list(alternatives)}
    if confidence is not None:
        body["confidence"] = confidence
    return client.post("/api/ask", json=body).json()


def nothing_sent(fake):
    return fake.live_swaps() == [] and live.ledger.total() == 0


# The phrase itself


@pytest.mark.parametrize("text", ["evet onaylıyorum", "Evet, onaylıyorum.", "EVET ONAYLIYORUM", "yes I confirm", "Yes, I confirm."])
def test_the_whole_phrase_confirms(text):
    assert voice_confirms(text)


@pytest.mark.parametrize("text", ["evet", "yes", "onaylıyorum", "evet onaylıyorum ama 10 olsun", "yes I confirm it", ""])
def test_anything_else_is_not_the_phrase(text):
    assert not voice_confirms(text)


@pytest.mark.parametrize("confidence, clear", [(None, False), (0.0, False), (0.5, False), (0.79, False), (0.8, True), (0.99, True)])
def test_confidence_threshold(confidence, clear):
    assert voice_clear(confidence) is clear


def test_a_refusal_in_any_alternative_counts():
    assert voice_says_no(["evet onaylıyorum", "hayır onaylamıyorum"])
    assert not voice_says_no(["evet onaylıyorum", "evet onaylıyor um"])


# The question


def test_the_live_question_repeats_amount_and_token(agent, monkeypatch):
    client, _ = make_client()
    data = voice_offer(client, monkeypatch)
    assert data["spoken"].endswith(
        "4 USDC verip en az 0,00396 SOL alacaksın. Onaylamak için evet onaylıyorum de. Vazgeçmek için iptal de."
    )
    assert messages.say("confirm_question_live", "tr") not in data["spoken"]
    assert data["confirm_button"] is True


def test_the_english_question(agent, monkeypatch):
    client, _ = make_client()
    data = voice_offer(client, monkeypatch, language="en")
    assert data["spoken"].endswith(
        "You give 4 USDC and get at least 0.00396 SOL. To confirm, say yes I confirm. To stop, say cancel."
    )


def test_a_typed_request_keeps_the_typed_question(agent, monkeypatch):
    client, _ = make_client()
    use_swap(monkeypatch, "tr")
    data = client.post("/api/ask", json={"text": "4 USDC'yi SOL'a çevir", "live": True}).json()
    assert data["spoken"].endswith(messages.say("confirm_question_live", "tr"))
    assert "evet onaylıyorum" not in data["spoken"]


# Live answers by voice


@pytest.mark.parametrize("text", ["evet onaylıyorum", "yes I confirm"])
def test_the_phrase_sends_once(agent, monkeypatch, text):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    data = say(client, key, text)
    assert data["action"] == "live_sent"
    assert len(agent.live_swaps()) == 1
    assert live.ledger.total() == Decimal("4.00")


@pytest.mark.parametrize("text", ["evet", "yes", "onayla", "confirm"])
def test_a_bare_yes_is_asked_again(agent, monkeypatch, text):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    data = say(client, key, text)
    assert data["spoken"] == "Sesli onay için yalnızca evet yetmez. Evet onaylıyorum de, ya da iptal de."
    assert data["pending"] == key
    assert nothing_sent(agent)
    # The question is still open, so the phrase works after it.
    assert say(client, key, "evet onaylıyorum")["action"] == "live_sent"


@pytest.mark.parametrize("confidence", [0.5, 0.0, None])
def test_low_or_missing_confidence_cancels(agent, monkeypatch, confidence):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    data = say(client, key, "evet onaylıyorum", confidence=confidence)
    assert data["spoken"] == "Seni net duyamadım, onay saymadım. İptal ettim, işlem yapılmadı."
    assert "pending" not in data
    assert nothing_sent(agent)
    assert say(client, key, "evet onaylıyorum")["action"] == "expired"
    assert nothing_sent(agent)


def test_a_refusal_among_alternatives_cancels(agent, monkeypatch):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    data = say(client, key, "evet onaylıyorum", alternatives=["hayır onaylamıyorum"])
    assert data["action"] == "cancelled"
    assert nothing_sent(agent)


def test_silence_cancels(agent, monkeypatch):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    data = say(client, key, "")
    assert data["spoken"] == "Onay duymadım, iptal ettim. İşlem yapılmadı."
    assert nothing_sent(agent)


def test_other_words_cancel(agent, monkeypatch):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    assert say(client, key, "evet bence olur")["action"] == "cancelled"
    assert nothing_sent(agent)


@pytest.mark.parametrize("text", ["iptal", "cancel", "hayır"])
def test_cancel_works_even_unclear(agent, monkeypatch, text):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    data = say(client, key, text, confidence=0.3)
    assert data["action"] == "cancelled"
    assert nothing_sent(agent)


def test_an_expired_quote_is_refused(agent, monkeypatch):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    main.pendings.get(key).expires_at = 0
    assert say(client, key, "evet onaylıyorum")["action"] == "expired"
    assert nothing_sent(agent)


def test_a_form_quote_answered_by_voice_follows_the_voice_rule(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    assert say(client, key, "evet")["pending"] == key
    assert nothing_sent(agent)


def test_a_withdrawal_needs_the_phrase_too(wallet, monkeypatch):
    client, _ = make_client()
    data = client.post("/api/ask", json={"text": "paramı cüzdanıma çek", "live": True, "voice": True}).json()
    assert data["spoken"].endswith(
        "4 USDC sahip adresine çekilecek. Onaylamak için evet onaylıyorum de. Vazgeçmek için iptal de."
    )
    key = data["pending"]
    say(client, key, "evet")
    assert wallet.sends() == []
    assert say(client, key, "evet onaylıyorum")["action"] == "live_sent"
    assert len(wallet.sends()) == 1


def test_freeze_by_voice_still_cuts_through(agent, monkeypatch):
    client, _ = make_client()
    key = voice_offer(client, monkeypatch)["pending"]
    calls = []

    async def fake_control(kind):
        calls.append(kind)

    monkeypatch.setattr("app.main.control_agent", fake_control)
    data = say(client, key, "ajanı dondur")
    assert calls == ["agent_freeze"]
    assert data["signed"] is True
    assert nothing_sent(agent)


def test_unfreeze_by_voice_still_needs_the_code(agent, monkeypatch):
    monkeypatch.setattr("app.main.owner_ready", lambda: True)
    client, _ = make_client()
    data = client.post("/api/ask", json={"text": "ajanı çöz", "voice": True}).json()
    key = data["pending"]
    assert say(client, key, "evet onaylıyorum")["spoken"] != data["spoken"]
    assert "pending" in say(client, key, "evet onaylıyorum")


# Typed answers keep today's rules


def test_typed_yes_still_confirms_live(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = client.post("/api/ask", json={"text": "evet", "pending": key}).json()
    assert data["action"] == "live_sent"


def test_the_confirm_button_sends_no_voice_fields(agent):
    """The button posts the word evet with no voice flag, which still confirms."""
    client, _ = make_client()
    key = offer(client)["pending"]
    data = client.post("/api/ask", json={"text": "evet", "pending": key, "lang": "tr", "live": True}).json()
    assert data["action"] == "live_sent"


def test_dry_voice_yes_works_as_today():
    client, _ = make_client()
    key = client.post("/api/quote", json={"from_token": "NEAR", "to_token": "USDC", "amount": "1", "lang": "tr"}).json()[
        "pending"
    ]
    assert say(client, key, "evet")["spoken"] == "Deneme modu: işlem yapılmadı."


def test_dry_silence_never_confirms():
    client, _ = make_client()
    key = client.post("/api/quote", json={"from_token": "NEAR", "to_token": "USDC", "amount": "1", "lang": "tr"}).json()[
        "pending"
    ]
    data = say(client, key, "")
    assert data["spoken"] == "Cevabını duyamadım. Evet ya da hayır de."
    assert data["pending"] == key


@pytest.mark.parametrize("field, value", [("confidence", 1.5), ("confidence", -0.1), ("alternatives", ["a", "b", "c", "d"])])
def test_bad_voice_fields_are_refused(field, value):
    client, _ = make_client()
    response = client.post("/api/ask", json={"text": "evet", "voice": True, field: value})
    assert response.status_code == 422
