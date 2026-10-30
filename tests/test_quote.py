import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, get_oneclick
from app.messages import format_amount
from app.oneclick import OneClick, QuoteError, build_quote_request, find_token, to_atomic

TOKENS = [
    {"assetId": "nep141:wrap.near", "decimals": 24, "blockchain": "near", "symbol": "wNEAR"},
    {"assetId": "nep141:usdc.near", "decimals": 6, "blockchain": "near", "symbol": "USDC"},
    {"assetId": "nep141:usdc.eth", "decimals": 6, "blockchain": "eth", "symbol": "USDC"},
    {"assetId": "nep141:sol.a", "decimals": 9, "blockchain": "sol", "symbol": "ABC"},
    {"assetId": "nep141:sol.b", "decimals": 9, "blockchain": "eth", "symbol": "ABC"},
]
QUOTE = {
    "amountInFormatted": "1.0",
    "amountOutFormatted": "4.3019123",
    "minAmountOut": "4258648",
    "amountOutUsd": "4.30",
    "timeEstimate": 12,
}


def make_client(quote_status=201):
    sent = []

    def handler(request):
        if request.url.path == "/v0/tokens":
            return httpx.Response(200, json=TOKENS)
        sent.append(json.loads(request.content))
        if quote_status != 201:
            return httpx.Response(quote_status, json={"message": "no"})
        return httpx.Response(201, json={"quote": QUOTE, "correlationId": "abc"})

    oneclick = OneClick(transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_oneclick] = lambda: oneclick
    return TestClient(app), sent


def payload(**changes):
    return {"from_token": "NEAR", "to_token": "USDC", "amount": "1", "lang": "tr", **changes}


@pytest.mark.parametrize("dry", [True, False])
def test_both_modes_use_intents(dry):
    body = build_quote_request("a", "b", "1", "x.near", dry=dry)
    assert body["dry"] is dry
    assert body["depositType"] == body["refundType"] == body["recipientType"] == "INTENTS"


def test_find_token_prefers_near_and_maps_native_near():
    assert find_token(TOKENS, "usdc")["assetId"] == "nep141:usdc.near"
    assert find_token(TOKENS, "NEAR")["assetId"] == "nep141:wrap.near"


def test_find_token_rejects_ambiguous_and_unknown():
    with pytest.raises(QuoteError) as ambiguous:
        find_token(TOKENS, "ABC")
    assert ambiguous.value.code == "ambiguous_token"
    with pytest.raises(QuoteError) as unknown:
        find_token(TOKENS, "NOPE")
    assert unknown.value.code == "unknown_token"


def test_to_atomic_accepts_decimal_comma():
    assert to_atomic("1,5", 6) == "1500000"


@pytest.mark.parametrize("amount", ["", "0", "-1", "abc", "NaN", "Infinity", "0,0000001"])
def test_to_atomic_rejects_bad_amounts(amount):
    with pytest.raises(QuoteError):
        to_atomic(amount, 6)


def test_format_amount_uses_turkish_comma():
    assert format_amount("4.3019123", "tr") == "4,301912"
    assert format_amount("100", "en") == "100"


def test_format_amount_keeps_small_values_distinct():
    assert format_amount("0.00005544", "en") == "0.00005544"
    assert format_amount("0.00005488", "en") == "0.00005488"


def test_quote_is_always_dry_and_spoken():
    client, sent = make_client()
    response = client.post("/api/quote", json=payload())
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "dry"
    assert sent[0]["dry"] is True
    assert sent[0]["amount"] == "1" + "0" * 24
    assert data["spoken"].startswith("Deneme modu. 1 wNEAR")
    assert "En az 4,258648 USDC" in data["spoken"]
    assert "Hiçbir işlem yapılmadı" in data["spoken"]


def test_quote_speaks_english():
    client, _ = make_client()
    data = client.post("/api/quote", json=payload(lang="en")).json()
    assert data["spoken"].startswith("Dry run. For 1 wNEAR")


@pytest.mark.parametrize(
    "changes, status, code",
    [
        ({"amount": "abc"}, 400, "invalid_amount"),
        ({"from_token": ""}, 400, "missing_token"),
        ({"to_token": "wNEAR"}, 400, "same_token"),
        ({"to_token": "NOPE"}, 404, "unknown_token"),
    ],
)
def test_input_errors_are_spoken_and_send_no_quote(changes, status, code):
    client, sent = make_client()
    response = client.post("/api/quote", json=payload(**changes))
    assert response.status_code == status
    assert response.json()["error"] == code
    assert response.json()["spoken"]
    assert sent == []


def test_upstream_rejection_is_spoken():
    client, _ = make_client(quote_status=400)
    response = client.post("/api/quote", json=payload())
    assert response.status_code == 502
    assert response.json()["error"] == "quote_rejected"


def test_page_is_served():
    client, _ = make_client()
    response = client.get("/")
    assert response.status_code == 200
    assert 'aria-live="polite"' in response.text
