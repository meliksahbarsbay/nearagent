"""Did you mean ...? Rules first, a mocked model second, and code checks every answer."""
import json
import logging

import httpx
import pytest

import app.live as live
import app.main as main
from app import intent_repair, transcribe
from app.intent import Intent, ParserUnavailable
from tests.test_live import agent  # noqa: F401
from tests.test_quote import make_client

QUESTION_TR = "Bunu mu demek istedin: 0,5 NEAR'ı USDC'ye çevir? Evet ya da hayır de."
QUESTION_EN = "Did you mean: swap 0.5 NEAR to USDC? Say yes or no."
GARBLED_TR = "0.5 New usd'ye çevir"


def model_reads(monkeypatch, from_token, to_token, language="tr", amount="0.5"):
    """The sentence parser read the broken names as they were written."""
    seen = []

    async def fake_parse(text):
        seen.append(text)
        return Intent(action="swap", amount=amount, from_token=from_token, to_token=to_token, language=language)

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    return seen


def fake_model(monkeypatch, answer=None, status=200):
    """The repair model, answering with this JSON. Records every request."""
    calls = []

    def handler(request):
        calls.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "no"})
        content = json.dumps(answer)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.delenv("REPAIR_PROVIDER", raising=False)
    monkeypatch.setattr(intent_repair, "llm_allowed", True)
    monkeypatch.setattr(intent_repair, "transport", httpx.MockTransport(handler))
    return calls


def ask(client, text, **extra):
    return client.post("/api/ask", json={"text": text, **extra}).json()


def answer(client, key, text, lang="tr", **extra):
    return client.post("/api/ask", json={"text": text, "pending": key, "lang": lang, **extra}).json()


# Rules


def test_the_observed_sentence_is_suggested_by_rules(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    calls = fake_model(monkeypatch, {"action": "other"})
    data = ask(client, GARBLED_TR)
    assert data["action"] == "repair"
    assert data["spoken"] == QUESTION_TR
    assert data["answer_required"] is True
    assert sent == []
    # The rules were enough, so the model was never asked.
    assert calls == []


def test_english_suggestion(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD", language="en")
    data = ask(client, "swap 0.5 new to usd")
    assert data["spoken"] == QUESTION_EN
    assert sent == []


def test_yes_asks_for_the_quote(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    key = ask(client, GARBLED_TR)["pending"]
    offer = answer(client, key, "evet")
    assert offer["action"] == "swap"
    assert sent[0]["originAsset"] == "nep141:wrap.near"
    assert sent[0]["destinationAsset"] == "nep141:usdc.near"
    assert sent[0]["amount"] == "500000000000000000000000"


@pytest.mark.parametrize("reply", ["hayır", "no", ""])
def test_no_or_nothing_cancels_with_no_quote(monkeypatch, reply):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    key = ask(client, GARBLED_TR)["pending"]
    data = answer(client, key, reply)
    assert data["action"] == "cancelled"
    assert sent == []
    assert answer(client, key, "evet")["action"] == "expired"
    assert sent == []


def test_silence_in_voice_mode_cancels(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    key = ask(client, GARBLED_TR, voice=True)["pending"]
    data = answer(client, key, "", voice=True)
    assert data["spoken"].startswith("Evet demediğin için iptal ettim")
    assert sent == []


def test_a_new_sentence_instead_of_an_answer_is_read_as_one(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    key = ask(client, GARBLED_TR)["pending"]
    data = answer(client, key, "son işlemlerimi oku")
    assert data["action"] == "history"
    assert sent == []


def test_rules_with_no_amount_ask_how_much_then_suggest(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "NEW", "USD", amount=None)
    data = ask(client, "New'i usd'ye çevir")
    assert data["spoken"] == "Ne kadar çevirmek istiyorsun?"
    question = answer(client, data["pending"], "yarım")
    assert question["spoken"] == QUESTION_TR
    assert sent == []


# The model, mocked


def unclear(monkeypatch):
    """A sentence the rules cannot read: no known token name in it."""
    model_reads(monkeypatch, "NYAR", "DOLARCOIN")
    return "0.5 nyar'ı dolar coin'e çevir"


def test_the_model_is_asked_when_rules_are_not_enough(monkeypatch, caplog):
    client, sent = make_client()
    text = unclear(monkeypatch)
    calls = fake_model(monkeypatch, {"action": "swap", "from_token": "NEAR", "to_token": "USDC", "amount": "0.5", "confidence": 0.9})
    with caplog.at_level(logging.INFO, logger="nearagent.repair"):
        intent_repair.log.propagate = True
        try:
            data = ask(client, text)
        finally:
            intent_repair.log.propagate = False
    assert data["spoken"] == QUESTION_TR
    assert len(calls) == 1
    assert sent == []
    body = json.loads(calls[0].content)
    assert "NEAR, USDC" in body["messages"][0]["content"]
    assert "outcome=suggest" in caplog.text and "ms=" in caplog.text
    assert "sk-test-not-real" not in caplog.text


def test_a_token_off_the_list_is_refused(monkeypatch):
    client, sent = make_client()
    text = unclear(monkeypatch)
    fake_model(monkeypatch, {"action": "swap", "from_token": "DOGE", "to_token": "USDC", "amount": "0.5", "confidence": 0.95})
    data = ask(client, text)
    assert "pending" not in data
    assert data["spoken"].endswith("Kullanabileceğin tokenler: NEAR, USDC, USDT, SOL, ETH, BTC.")
    assert sent == []


def test_a_changed_amount_is_refused_and_how_much_is_asked(monkeypatch):
    client, sent = make_client()
    text = unclear(monkeypatch)
    fake_model(monkeypatch, {"action": "swap", "from_token": "NEAR", "to_token": "USDC", "amount": "5", "confidence": 0.95})
    data = ask(client, text)
    assert data["spoken"] == "Ne kadar çevirmek istiyorsun?"
    assert "5 NEAR" not in data["spoken"]
    assert sent == []


def test_low_confidence_asks_nothing(monkeypatch):
    client, sent = make_client()
    text = unclear(monkeypatch)
    fake_model(monkeypatch, {"action": "swap", "from_token": "NEAR", "to_token": "USDC", "amount": "0.5", "confidence": 0.5})
    data = ask(client, text)
    assert "pending" not in data
    assert data["spoken"].startswith("NYAR tokenini bulamadım.")
    assert "Kullanabileceğin tokenler" in data["spoken"]
    assert sent == []


def test_a_model_failure_falls_back_to_the_usual_error(monkeypatch):
    client, sent = make_client()
    text = unclear(monkeypatch)
    fake_model(monkeypatch, status=500)
    data = ask(client, text)
    assert "pending" not in data
    assert data["spoken"].startswith("NYAR tokenini bulamadım.")


def test_near_ai_can_be_chosen_in_env(monkeypatch):
    monkeypatch.setenv("REPAIR_PROVIDER", "near_ai")
    monkeypatch.setenv("NEAR_AI_API_KEY", "near-test-not-real")
    provider = intent_repair.repair_provider()
    assert provider.name == "near_ai"
    assert provider.base_url.startswith("https://cloud-api.near.ai")


def test_openai_is_the_default_provider(monkeypatch):
    monkeypatch.delenv("REPAIR_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    assert intent_repair.repair_provider().name == "openai"


def test_no_key_means_no_model(monkeypatch):
    monkeypatch.delenv("REPAIR_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert intent_repair.repair_provider() is None


# No key at all


def test_with_no_key_the_rules_still_suggest(monkeypatch):
    client, sent = make_client()

    async def no_parser(text):
        raise ParserUnavailable

    monkeypatch.setattr(main, "parse_intent", no_parser)
    data = ask(client, GARBLED_TR)
    assert data["spoken"] == QUESTION_TR
    assert sent == []
    assert answer(client, data["pending"], "evet")["action"] == "swap"
    assert len(sent) == 1


# Live money


def test_the_yes_to_a_suggestion_never_confirms_a_live_swap(agent, monkeypatch):
    client, _ = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    key = ask(client, GARBLED_TR, live=True)["pending"]
    offer = answer(client, key, "evet", live=True)
    assert offer["mode"] == "live"
    assert offer["confirm_button"] is True
    assert offer["pending"] != key
    assert agent.live_swaps() == []
    assert live.ledger.total() == 0


def test_by_voice_the_live_quote_still_needs_the_phrase(agent, monkeypatch):
    client, _ = make_client()
    model_reads(monkeypatch, "NEW", "USD")
    key = ask(client, GARBLED_TR, live=True, voice=True)["pending"]
    offer = answer(client, key, "evet", live=True, voice=True, confidence=0.95)
    assert "evet onaylıyorum" in offer["spoken"]
    data = answer(client, offer["pending"], "evet", live=True, voice=True, confidence=0.95)
    assert data["spoken"].startswith("Sesli onay için yalnızca evet yetmez")
    assert agent.live_swaps() == []


def test_live_suggestions_use_the_agents_tokens(monkeypatch):
    assert intent_repair.supported(True) == ("NEAR", "USDC", "SOL", "ETH")


# Typed and dictated text


def test_typed_text_reaches_the_parser_as_written(monkeypatch):
    client, _ = make_client()
    seen = model_reads(monkeypatch, "NEAR", "USDC")
    ask(client, "sıfır virgül beş nir'ı USDC'ye çevir")
    assert seen == ["sıfır virgül beş nir'ı USDC'ye çevir"]


def test_dictated_text_is_fixed_like_voice(monkeypatch):
    client, _ = make_client()
    seen = model_reads(monkeypatch, "NEAR", "USDC")
    ask(client, "sıfır virgül beş nir'ı USDC'ye çevir", source="dictation")
    assert seen == ["0,5 NEAR'ı USDC'ye çevir"]


def test_a_dictated_amount_answer_loses_extra_words(monkeypatch):
    client, sent = make_client()
    model_reads(monkeypatch, "USDC", "SOL", amount=None)
    key = ask(client, "USDC'yi SOL'a çevir")["pending"]
    offer = answer(client, key, "sıfır virgül beş tane", source="dictation")
    assert offer["action"] == "swap"
    assert sent[0]["amount"] == "500000"


# Speech to text


def fake_openai_audio(monkeypatch, reply=None, status=200):
    calls = []

    def handler(request):
        calls.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "no"})
        return httpx.Response(200, json=reply)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(transcribe, "allowed", True)
    monkeypatch.setattr(transcribe, "transport", httpx.MockTransport(handler))
    return calls


def post_audio(client, body=b"\x1a\x45\xdf\xa3fake-webm", lang="tr"):
    return client.post(f"/api/transcribe?lang={lang}", content=body, headers={"Content-Type": "audio/webm;codecs=opus"})


def test_transcription_is_off_without_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(transcribe, "allowed", True)
    client, _ = make_client()
    response = post_audio(client)
    assert response.status_code == 503
    assert response.json()["error"] == "stt_off"


def test_transcription_returns_text_and_confidence(monkeypatch):
    calls = fake_openai_audio(monkeypatch, {"text": " 0,5 NEAR'ı USDC'ye çevir ", "logprobs": [{"logprob": -0.01}, {"logprob": -0.05}]})
    client, _ = make_client()
    data = post_audio(client).json()
    assert data["text"] == "0,5 NEAR'ı USDC'ye çevir"
    assert 0.94 < data["confidence"] < 0.98
    sent = calls[0].content.decode("utf-8", "replace")
    assert "gpt-4o-mini-transcribe" in sent
    assert "NEAR, wNEAR, USDC" in sent
    assert "logprobs" in sent
    assert calls[0].url.path.endswith("/audio/transcriptions")


def test_no_probabilities_means_no_confidence(monkeypatch):
    fake_openai_audio(monkeypatch, {"text": "evet onaylıyorum"})
    client, _ = make_client()
    assert post_audio(client).json()["confidence"] is None


def test_the_transcription_model_can_be_set(monkeypatch):
    calls = fake_openai_audio(monkeypatch, {"text": "x"})
    monkeypatch.setenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe")
    client, _ = make_client()
    post_audio(client)
    assert "gpt-4o-transcribe" in calls[0].content.decode("utf-8", "replace")


def test_a_failed_transcription_says_so(monkeypatch):
    fake_openai_audio(monkeypatch, status=500)
    client, _ = make_client()
    response = post_audio(client)
    assert response.status_code == 502
    assert response.json()["spoken"] == "Kaydı yazıya çeviremedim. Yeniden dene ya da cümleyi yaz."


def test_a_long_recording_is_refused(monkeypatch):
    calls = fake_openai_audio(monkeypatch, {"text": "x"})
    client, _ = make_client()
    response = post_audio(client, body=b"0" * (transcribe.MAX_AUDIO_BYTES + 1))
    assert response.status_code == 413
    assert calls == []


def test_an_empty_recording_is_refused(monkeypatch):
    calls = fake_openai_audio(monkeypatch, {"text": "x"})
    client, _ = make_client()
    assert post_audio(client, body=b"").status_code == 400
    assert calls == []
