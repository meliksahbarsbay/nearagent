"""NEAR AI Cloud first, OpenAI as the backup, rules and the browser last. No real network."""
import json
import logging

import httpx
import pytest

import app.main as main
from app import intent_repair, providers, transcribe
from app.intent import Intent
from tests.test_live import agent, offer  # noqa: F401
from tests.test_quote import make_client

NEAR_HOST = "cloud-api.near.ai"
OPENAI_HOST = "api.openai.com"
QUESTION_TR = "Bunu mu demek istedin: 0,5 NEAR'ı USDC'ye çevir? Evet ya da hayır de."
SUGGESTION = {"action": "swap", "from_token": "NEAR", "to_token": "USDC", "amount": "0.5", "confidence": 0.9}


def both_keys(monkeypatch):
    monkeypatch.setenv("NEARAI_API_KEY", "near-test-not-real")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")


def names(services):
    return [service.name for service in services]


# Choosing a service


def test_no_keys_means_no_services(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert intent_repair.repair_chain() == []
    assert transcribe.services() == []


def test_with_only_openai_it_goes_alone(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    assert names(intent_repair.repair_chain()) == ["openai"]
    assert names(transcribe.services()) == ["openai"]


def test_a_near_ai_key_makes_it_first_with_openai_as_backup(monkeypatch):
    both_keys(monkeypatch)
    assert names(intent_repair.repair_chain()) == ["near_ai", "openai"]
    assert names(transcribe.services()) == ["near_ai", "openai"]


def test_settings_can_put_openai_first(monkeypatch):
    both_keys(monkeypatch)
    monkeypatch.setenv("REPAIR_PROVIDER", "openai")
    monkeypatch.setenv("TRANSCRIBE_PROVIDER", "openai")
    assert names(intent_repair.repair_chain()) == ["openai", "near_ai"]
    assert names(transcribe.services()) == ["openai", "near_ai"]


def test_the_older_key_name_still_works(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("NEAR_AI_API_KEY", "near-test-not-real")
    assert names(intent_repair.repair_chain()) == ["near_ai"]


def test_near_ai_defaults(monkeypatch):
    both_keys(monkeypatch)
    near = intent_repair.repair_chain()[0]
    assert near.base_url == "https://cloud-api.near.ai/v1"
    assert near.model == "z-ai/glm-5.3-flash"
    assert near.timeout == 8
    assert transcribe.services()[0].model == "openai/whisper-large-v3"


def test_near_ai_settings(monkeypatch):
    both_keys(monkeypatch)
    monkeypatch.setenv("NEARAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NEARAI_REPAIR_MODEL", "Qwen/Qwen3.8-27B")
    monkeypatch.setenv("NEARAI_TRANSCRIBE_MODEL", "openai/whisper-other")
    assert intent_repair.repair_chain()[0].base_url == "https://example.test/v1"
    assert intent_repair.repair_chain()[0].model == "Qwen/Qwen3.8-27B"
    assert transcribe.services()[0].model == "openai/whisper-other"


def test_the_sentence_parser_reads_the_new_key_name(monkeypatch):
    from app.intent import providers as parser_providers

    monkeypatch.setenv("NEARAI_API_KEY", "near-test-not-real")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert [provider.name for provider in parser_providers()] == ["near_ai"]


# Suggestions with a backup


def unclear(monkeypatch):
    async def fake_parse(text):
        return Intent(action="swap", amount="0.5", from_token="NYAR", to_token="DOLARCOIN", language="tr")

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    return "0.5 nyar'ı dolar coin'e çevir"


def models(monkeypatch, near, openai=None):
    """near and openai are a reply, an exception to raise, or None for never called."""
    calls = []

    def handler(request):
        calls.append(request.url.host)
        reply = near if request.url.host == NEAR_HOST else openai
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, int):
            return httpx.Response(reply, json={"error": "no"})
        content = json.dumps(reply)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(intent_repair, "llm_allowed", True)
    monkeypatch.setattr(intent_repair, "transport", httpx.MockTransport(handler))
    return calls


def test_near_ai_answers_first(monkeypatch):
    both_keys(monkeypatch)
    calls = models(monkeypatch, SUGGESTION)
    client, _ = make_client()
    data = client.post("/api/ask", json={"text": unclear(monkeypatch)}).json()
    assert data["spoken"] == QUESTION_TR
    assert data["provider"] == "near_ai" and data["backup"] is False
    assert calls == [NEAR_HOST]


@pytest.mark.parametrize("failure", [500, httpx.ReadTimeout("slow"), httpx.ConnectError("down")])
def test_a_near_ai_error_or_timeout_goes_to_openai(monkeypatch, caplog, failure):
    both_keys(monkeypatch)
    calls = models(monkeypatch, failure, SUGGESTION)
    client, sent = make_client()
    intent_repair.log.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="nearagent.repair"):
            data = client.post("/api/ask", json={"text": unclear(monkeypatch)}).json()
    finally:
        intent_repair.log.propagate = False
    assert calls == [NEAR_HOST, OPENAI_HOST]
    assert data["spoken"] == QUESTION_TR
    assert data["provider"] == "openai" and data["backup"] is True
    assert sent == []
    assert "provider=near_ai" in caplog.text and "next=openai" in caplog.text
    assert "provider=openai" in caplog.text and "backup=True" in caplog.text
    assert "near-test-not-real" not in caplog.text and "sk-test-not-real" not in caplog.text
    assert "nyar" not in caplog.text


def test_when_both_fail_the_usual_error_and_tokens_are_said(monkeypatch):
    both_keys(monkeypatch)
    models(monkeypatch, 500, 500)
    client, _ = make_client()
    data = client.post("/api/ask", json={"text": unclear(monkeypatch)}).json()
    assert "pending" not in data
    assert data["spoken"].startswith("NYAR tokenini bulamadım.")


def test_the_backup_is_checked_by_the_same_rules(monkeypatch):
    both_keys(monkeypatch)
    models(monkeypatch, 500, {**SUGGESTION, "confidence": 0.4})
    client, _ = make_client()
    data = client.post("/api/ask", json={"text": unclear(monkeypatch)}).json()
    assert "pending" not in data


def test_with_no_keys_the_rules_still_suggest(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = models(monkeypatch, SUGGESTION, SUGGESTION)

    async def fake_parse(text):
        return Intent(action="swap", amount="0.5", from_token="NEW", to_token="USD", language="tr")

    monkeypatch.setattr(main, "parse_intent", fake_parse)
    client, sent = make_client()
    data = client.post("/api/ask", json={"text": "0.5 New usd'ye çevir"}).json()
    assert data["spoken"] == QUESTION_TR
    assert data["provider"] == "rule"
    assert calls == [] and sent == []


# Speech to text with a backup


def audio_services(monkeypatch, near, openai=None):
    calls = []

    def handler(request):
        calls.append(request)
        reply = near if request.url.host == NEAR_HOST else openai
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, int):
            return httpx.Response(reply, json={"error": "no"})
        return httpx.Response(200, json=reply)

    monkeypatch.setattr(transcribe, "allowed", True)
    monkeypatch.setattr(transcribe, "transport", httpx.MockTransport(handler))
    return calls


def post_audio(client, provider=None):
    query = "?lang=tr" + (f"&provider={provider}" if provider else "")
    return client.post(f"/api/transcribe{query}", content=b"fake-webm", headers={"Content-Type": "audio/webm"})


def test_whisper_on_near_ai_gives_text_without_confidence(monkeypatch):
    both_keys(monkeypatch)
    calls = audio_services(monkeypatch, {"text": "yarım NEAR'ı USDC'ye çevir", "id": "trans-1"})
    client, _ = make_client()
    data = post_audio(client).json()
    assert data == {"language": "tr", "text": "yarım NEAR'ı USDC'ye çevir", "confidence": None, "provider": "near_ai", "backup": False}
    sent = calls[0].content.decode("utf-8", "replace")
    assert calls[0].url.host == NEAR_HOST and calls[0].url.path == "/v1/audio/transcriptions"
    assert "openai/whisper-large-v3" in sent
    assert "NEAR, wNEAR, USDC" in sent
    assert "logprobs" not in sent


@pytest.mark.parametrize("failure", [503, httpx.ReadTimeout("slow")])
def test_a_near_ai_failure_goes_to_openai(monkeypatch, failure):
    both_keys(monkeypatch)
    calls = audio_services(monkeypatch, failure, {"text": "evet", "logprobs": [{"logprob": -0.01}]})
    client, _ = make_client()
    data = post_audio(client).json()
    assert [call.url.host for call in calls] == [NEAR_HOST, OPENAI_HOST]
    assert data["provider"] == "openai" and data["backup"] is True
    assert data["confidence"] > 0.9


def test_both_failing_says_so(monkeypatch):
    both_keys(monkeypatch)
    audio_services(monkeypatch, 500, 500)
    client, _ = make_client()
    response = post_audio(client)
    assert response.status_code == 502


def test_no_service_means_the_browser(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = audio_services(monkeypatch, {"text": "x"})
    client, _ = make_client()
    response = post_audio(client)
    assert response.status_code == 503
    assert response.json()["error"] == "stt_off"
    assert calls == []


def test_the_page_can_ask_for_openai_first(monkeypatch):
    both_keys(monkeypatch)
    calls = audio_services(monkeypatch, {"text": "x"}, {"text": "y"})
    client, _ = make_client()
    assert post_audio(client, provider="openai").json()["provider"] == "openai"
    assert calls[0].url.host == OPENAI_HOST


def test_the_provider_list_names_services_and_never_keys(monkeypatch):
    both_keys(monkeypatch)
    client, _ = make_client()
    monkeypatch.setattr(intent_repair, "llm_allowed", True)
    monkeypatch.setattr(transcribe, "allowed", True)
    response = client.get("/api/providers")
    assert response.json() == {"transcribe": ["near_ai", "openai"], "repair": ["near_ai", "openai"], "near_ai": True}
    assert "test-not-real" not in response.text


# Live money heard through Whisper


def voice_answer(client, key, text, engine, confidence=None):
    body = {"text": text, "pending": key, "lang": "tr", "voice": True, "engine": engine}
    if confidence is not None:
        body["confidence"] = confidence
    return client.post("/api/ask", json=body).json()


def test_no_confidence_from_whisper_asks_for_a_typed_yes(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = voice_answer(client, key, "evet onaylıyorum", "near_ai")
    assert data["spoken"] == (
        "Bu ses tanıma güven değeri vermiyor, bu yüzden sesli onayı kabul edemem. "
        "Onaylamak için evet yaz ya da Onayla düğmesine bas. Vazgeçmek için iptal de."
    )
    assert data["pending"] == key
    assert agent.live_swaps() == []
    # Typing yes, or the Confirm button, still confirms as it always has.
    typed = client.post("/api/ask", json={"text": "evet", "pending": key, "lang": "tr", "live": True}).json()
    assert typed["action"] == "live_sent"
    assert len(agent.live_swaps()) == 1


def test_english_no_confidence_sentence(agent):
    client, _ = make_client()
    key = offer(client, lang="en")["pending"]
    body = {"text": "yes I confirm", "pending": key, "lang": "en", "voice": True, "engine": "near_ai"}
    data = client.post("/api/ask", json=body).json()
    assert data["spoken"].startswith("This speech recognition gives no confidence, so I cannot accept a spoken yes.")
    assert agent.live_swaps() == []


def test_browser_speech_with_no_confidence_still_cancels(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = voice_answer(client, key, "evet onaylıyorum", "browser")
    assert data["action"] == "cancelled"
    assert agent.live_swaps() == []


def test_openai_with_clear_confidence_still_confirms_by_voice(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = voice_answer(client, key, "evet onaylıyorum", "openai", confidence=0.95)
    assert data["action"] == "live_sent"


def test_the_public_demo_lists_no_services(monkeypatch):
    both_keys(monkeypatch)
    monkeypatch.setattr(intent_repair, "llm_allowed", False)
    monkeypatch.setattr(transcribe, "allowed", False)
    client, _ = make_client()
    data = client.get("/api/providers").json()
    assert data["transcribe"] == [] and data["repair"] == []


def test_the_shared_order_rule(monkeypatch):
    monkeypatch.setenv("NEARAI_API_KEY", "near-test-not-real")
    assert providers.first_choice("ANY_SETTING") == "near_ai"
    monkeypatch.delenv("NEARAI_API_KEY")
    assert providers.first_choice("ANY_SETTING") == "openai"
