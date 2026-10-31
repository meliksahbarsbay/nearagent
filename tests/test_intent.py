import asyncio
import json
import logging

import httpx
import pytest

from app.intent import (
    Intent,
    ParserUnavailable,
    clean,
    fix_turkish_source_chain,
    parse_intent,
)
from app.oneclick import QuoteError

FAKE_KEY = "fake-key-not-real"
INTENT = {
    "action": "swap",
    "amount": "2.0",
    "from_token": "near",
    "from_chain": None,
    "to_token": "usdc",
    "to_chain": "Base",
    "language": "en",
}


def chat_response(content):
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        },
    )


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("NEAR_AI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.delenv("NEAR_AI_BASE_URL", raising=False)
    monkeypatch.delenv("NEAR_AI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)


def test_near_ai_is_tried_first(keys):
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        return chat_response(json.dumps(INTENT))

    intent = asyncio.run(parse_intent("x", httpx.MockTransport(handler)))
    assert hosts == ["cloud-api.near.ai"]
    assert intent.to_chain == "base"


def test_request_enforces_schema(keys):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return chat_response(json.dumps(INTENT))

    asyncio.run(parse_intent("x", httpx.MockTransport(handler)))
    schema = bodies[0]["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert set(schema["schema"]["required"]) == set(Intent.model_fields)


def test_openai_used_when_near_ai_key_is_missing(keys, monkeypatch):
    monkeypatch.delenv("NEAR_AI_API_KEY")
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        return chat_response(json.dumps(INTENT))

    asyncio.run(parse_intent("x", httpx.MockTransport(handler)))
    assert hosts == ["api.openai.com"]


def test_falls_back_when_near_ai_fails(keys):
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        if request.url.host == "cloud-api.near.ai":
            return httpx.Response(500, json={"error": "down"})
        return chat_response(json.dumps(INTENT))

    asyncio.run(parse_intent("x", httpx.MockTransport(handler)))
    assert hosts == ["cloud-api.near.ai", "api.openai.com"]


def test_no_keys_means_parser_unavailable(monkeypatch):
    monkeypatch.delenv("NEAR_AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ParserUnavailable):
        asyncio.run(parse_intent("x"))


@pytest.mark.parametrize("content", ["not json", '{"action": "transfer", "language": "en"}'])
def test_bad_output_is_rejected(keys, content):
    transport = httpx.MockTransport(lambda request: chat_response(content))
    with pytest.raises(QuoteError) as failed:
        asyncio.run(parse_intent("x", transport))
    assert failed.value.code == "parser_failed"


def test_failures_never_log_key_or_body(keys, caplog):
    def handler(request):
        return httpx.Response(401, json={"error": f"Incorrect API key {FAKE_KEY}"})

    with caplog.at_level(logging.WARNING), pytest.raises(QuoteError):
        asyncio.run(parse_intent("x", httpx.MockTransport(handler)))
    assert "status=401" in caplog.text
    assert FAKE_KEY not in caplog.text


def test_clean_normalizes_fields():
    intent = clean(Intent(**{**INTENT, "from_chain": "Solana", "amount": "1,50"}))
    assert intent.amount == "1.5"
    assert intent.from_chain == "sol"
    assert intent.from_token == "NEAR"
    assert intent.to_token == "USDC"


def chains(text, from_chain=None, to_chain=None, action="swap"):
    intent = Intent(**{**INTENT, "action": action, "from_chain": from_chain, "to_chain": to_chain})
    fixed = fix_turkish_source_chain(text, intent)
    return fixed.from_chain, fixed.to_chain


@pytest.mark.parametrize("apostrophe", ["'", "’"])
def test_bare_locative_moves_chain_to_source(apostrophe):
    text = f"50 USDC'yi Solana{apostrophe}da SOL'a çevir"
    assert chains(text, to_chain="sol") == ("sol", None)


@pytest.mark.parametrize(
    "text",
    [
        "10 USDT'yi Solana üzerindeki SOL'a çevir",
        "10 USDT'yi Solana'daki SOL'a çevir",
        "10 USDT'yi Solana'ya taşı",
        "swap 15 USDT to SOL on Solana",
    ],
)
def test_destination_wording_keeps_to_chain(text):
    assert chains(text, to_chain="sol") == (None, "sol")


def test_locative_for_another_chain_changes_nothing():
    assert chains("Base'de 10 USDT'yi SOL'a çevir", to_chain="sol") == (None, "sol")


def test_named_source_chain_is_kept():
    text = "USDC'yi Base'de Solana'da çevir"
    assert chains(text, from_chain="base", to_chain="sol") == ("base", "sol")


def test_only_swaps_are_changed():
    assert chains("Solana'da SOL kaç dolar", to_chain="sol", action="price") == (None, "sol")
