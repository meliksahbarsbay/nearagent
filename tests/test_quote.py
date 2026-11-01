import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.intent import Intent, ParserUnavailable
from app.main import app, get_oneclick
from app.messages import detect_language, format_amount
from app.oneclick import OneClick, QuoteError, build_quote_request, find_token, to_atomic

TOKENS = [
    {"assetId": "nep141:wrap.near", "decimals": 24, "blockchain": "near", "symbol": "wNEAR", "price": 4.3},
    {"assetId": "1cs_v1:sol:wnear", "decimals": 24, "blockchain": "sol", "symbol": "wNEAR", "price": 4.3},
    {"assetId": "nep141:usdc.eth", "decimals": 6, "blockchain": "eth", "symbol": "USDC", "price": 1.0},
    {"assetId": "nep141:usdc.near", "decimals": 6, "blockchain": "near", "symbol": "USDC", "price": 1.0},
    {"assetId": "nep141:usdc.base", "decimals": 6, "blockchain": "base", "symbol": "USDC", "price": 1.0},
    {"assetId": "1cs_v1:aptos:sol", "decimals": 9, "blockchain": "aptos", "symbol": "SOL", "price": 180.5},
    {"assetId": "nep141:sol.omft.near", "decimals": 9, "blockchain": "sol", "symbol": "SOL", "price": 180.5},
    {"assetId": "nep141:eth.bridge.near", "decimals": 18, "blockchain": "near", "symbol": "ETH", "price": 2240.0},
    {"assetId": "nep141:eth.omft.near", "decimals": 18, "blockchain": "eth", "symbol": "ETH", "price": 2240.0},
    {"assetId": "nep141:only.base", "decimals": 18, "blockchain": "base", "symbol": "ONE", "price": 2.0},
]
QUOTE = {
    "amountInFormatted": "1.0",
    "amountOutFormatted": "4.3019123",
    "minAmountOut": "4258648",
    "amountInUsd": "4.31",
    "amountOutUsd": "4.30",
    "timeEstimate": 12,
}


def make_client(quote_status=201, **quote_changes):
    sent = []

    def handler(request):
        if request.url.path == "/v0/tokens":
            return httpx.Response(200, json=TOKENS)
        sent.append(json.loads(request.content))
        if quote_status != 201:
            return httpx.Response(quote_status, json={"message": "no"})
        return httpx.Response(201, json={"quote": {**QUOTE, **quote_changes}, "correlationId": "abc"})

    oneclick = OneClick(transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_oneclick] = lambda: oneclick
    return TestClient(app), sent


def payload(**changes):
    return {"from_token": "NEAR", "to_token": "USDC", "amount": "1", "lang": "tr", **changes}


def use_intent(monkeypatch, **fields):
    async def fake_parse(text):
        return Intent(language="tr", **fields)

    monkeypatch.setattr(main, "parse_intent", fake_parse)


@pytest.mark.parametrize("dry", [True, False])
def test_both_modes_use_intents(dry):
    body = build_quote_request("a", "b", "1", "x.near", dry=dry)
    assert body["dry"] is dry
    assert body["depositType"] == body["refundType"] == body["recipientType"] == "INTENTS"


@pytest.mark.parametrize(
    "symbol, asset",
    [
        ("usdc", "nep141:usdc.near"),
        ("NEAR", "nep141:wrap.near"),
        ("SOL", "nep141:sol.omft.near"),
        ("ETH", "nep141:eth.omft.near"),
    ],
)
def test_default_chains_are_flagged_as_assumed(symbol, asset):
    token, assumed = find_token(TOKENS, symbol)
    assert token["assetId"] == asset
    assert assumed is True


def test_single_chain_token_is_not_assumed():
    token, assumed = find_token(TOKENS, "ONE")
    assert token["blockchain"] == "base"
    assert assumed is False


def test_named_chain_is_used_and_not_assumed():
    token, assumed = find_token(TOKENS, "USDC", "base")
    assert token["assetId"] == "nep141:usdc.base"
    assert assumed is False


def test_token_missing_on_named_chain_lists_real_chains():
    with pytest.raises(QuoteError) as missing:
        find_token(TOKENS, "SOL", "base")
    assert missing.value.code == "token_not_on_chain"
    assert missing.value.details["chains"] == "Aptos, Solana"


def test_unknown_token_is_rejected():
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


def test_quote_is_always_dry_and_reads_terms_in_order():
    client, sent = make_client()
    response = client.post("/api/quote", json=payload())
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "dry"
    assert sent[0]["dry"] is True
    assert sent[0]["amount"] == "1" + "0" * 24
    assert data["spoken"] == (
        "Deneme modu. Veriyorsun: 1 wNEAR. Alıyorsun: yaklaşık 4,301912 USDC. "
        "En az garanti: 4,258648 USDC. Ücret: yaklaşık 0,01 dolar. "
        "Süre: yaklaşık 12 saniye. Teklif 10 dakika geçerli. "
        "NEAR üzerindeki wNEAR tokenini ve NEAR üzerindeki USDC'yi kullandım; "
        "başka zincir istersen söyle. Onaylıyor musun? Evet de ya da Enter'a bas."
    )


def test_quote_speaks_english():
    client, _ = make_client()
    data = client.post("/api/quote", json=payload(lang="en")).json()
    assert data["spoken"].startswith("Dry run. You give: 1 wNEAR. You get: about 4.301912 USDC.")
    assert data["spoken"].endswith(
        "I used wNEAR on NEAR and USDC on NEAR; tell me if you want another chain. "
        "Do you confirm? Say yes or press Enter."
    )


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


def test_ask_swap_names_the_chain_it_chose(monkeypatch):
    client, sent = make_client()
    use_intent(
        monkeypatch, action="swap", amount="50", from_token="USDC", from_chain="base", to_token="SOL"
    )
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["action"] == "swap"
    assert sent[0]["originAsset"] == "nep141:usdc.base"
    assert sent[0]["destinationAsset"] == "nep141:sol.omft.near"
    assert sent[0]["dry"] is True
    assert "Solana üzerindeki SOL'u kullandım; başka zincir istersen söyle." in data["spoken"]


def test_ask_price_uses_token_list_and_requests_no_quote(monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="price", amount="2", from_token="SOL")
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["action"] == "price"
    assert data["spoken"].startswith("2 SOL yaklaşık 361 dolar.")
    assert sent == []


def test_ask_price_defaults_to_one(monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="price", from_token="ONE")
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["spoken"] == "1 ONE yaklaşık 2 dolar."


def test_ask_help(monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="help")
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["action"] == "help"
    assert sent == []


def test_ask_swap_without_amount_asks_and_binds_the_answer(monkeypatch):
    client, sent = make_client()
    use_intent(
        monkeypatch, action="swap", from_token="USDC", from_chain="base", to_token="SOL"
    )
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["spoken"] == "Ne kadar çevirmek istiyorsun?"
    assert sent == []

    offer = client.post("/api/ask", json={"text": "10", "pending": data["pending"]}).json()
    assert offer["action"] == "swap"
    assert sent[0]["originAsset"] == "nep141:usdc.base"
    assert sent[0]["destinationAsset"] == "nep141:sol.omft.near"
    assert sent[0]["amount"] == "10000000"
    assert offer["spoken"].startswith("Deneme modu.")
    assert offer["pending"] != data["pending"]


def test_unreadable_amount_is_asked_again_with_no_quote(monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", from_token="USDC", to_token="SOL")
    key = client.post("/api/ask", json={"text": "x"}).json()["pending"]
    data = client.post("/api/ask", json={"text": "50 dolar", "pending": key}).json()
    assert data["spoken"].startswith("Miktarı anlayamadım.")
    assert data["pending"] == key
    assert sent == []


def test_rejected_amount_keeps_the_question_open(monkeypatch):
    client, _ = make_client(quote_status=400)
    use_intent(monkeypatch, action="swap", from_token="USDC", to_token="SOL")
    key = client.post("/api/ask", json={"text": "x"}).json()["pending"]
    data = client.post("/api/ask", json={"text": "0,0001", "pending": key}).json()
    assert data["error"] == "quote_rejected"
    assert data["pending"] == key


def test_no_amount_for_unknown_token_is_not_asked(monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="swap", from_token="NOPE", to_token="SOL")
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["error"] == "unknown_token"
    assert "pending" not in data


def test_cancel_during_amount_question(monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", from_token="USDC", to_token="SOL")
    key = client.post("/api/ask", json={"text": "x"}).json()["pending"]
    data = client.post("/api/ask", json={"text": "iptal", "pending": key}).json()
    assert data["action"] == "cancelled"
    assert sent == []


def offer(client):
    return client.post("/api/quote", json=payload()).json()


@pytest.mark.parametrize("answer", ["evet", "Evet.", "EVET", "yes", ""])
def test_confirm_says_nothing_was_executed(answer):
    client, sent = make_client()
    key = offer(client)["pending"]
    data = client.post("/api/ask", json={"text": answer, "pending": key}).json()
    assert data["spoken"] == "Deneme modu: işlem yapılmadı."
    assert data["mode"] == "dry"
    assert "pending" not in data
    assert len(sent) == 1


@pytest.mark.parametrize("answer", ["hayır", "HAYIR", "iptal", "İPTAL", "no", "cancel"])
def test_cancel_words(answer):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = client.post("/api/ask", json={"text": answer, "pending": key}).json()
    assert data["action"] == "cancelled"
    assert "pending" not in data


@pytest.mark.parametrize("answer", ["evet ama 10 olsun", "belki", "1 SOL kaç dolar"])
def test_other_answers_never_confirm(answer):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = client.post("/api/ask", json={"text": answer, "pending": key}).json()
    assert data["spoken"] == "Cevabını anlayamadım. Evet ya da hayır de."
    assert data["pending"] == key


def test_confirmation_works_only_once():
    client, _ = make_client()
    key = offer(client)["pending"]
    client.post("/api/ask", json={"text": "evet", "pending": key})
    data = client.post("/api/ask", json={"text": "evet", "pending": key, "lang": "tr"}).json()
    assert data["action"] == "expired"
    assert data["language"] == "tr"


def test_expired_confirmation_is_refused():
    client, _ = make_client()
    key = offer(client)["pending"]
    main.pendings.get(key).expires_at = 0
    data = client.post("/api/ask", json={"text": "evet", "pending": key, "lang": "tr"}).json()
    assert data["spoken"] == "Teklifin süresi doldu. İsteğini yeniden yaz."


def test_large_amount_is_spelled_before_the_confirmation():
    client, _ = make_client(amountInUsd="500.00", amountOutUsd="498.76")
    first = offer(client)
    assert first["spoken"].endswith(
        "Yaklaşık beş yüz dolar mı dedin? Evet de ya da Enter'a bas. "
        "Değilse hayır de ya da Esc'e bas."
    )
    assert "Onaylıyor musun" not in first["spoken"]

    key = first["pending"]
    second = client.post("/api/ask", json={"text": "evet", "pending": key}).json()
    assert second["spoken"] == "Onaylıyor musun? Evet de ya da Enter'a bas."

    third = client.post("/api/ask", json={"text": "evet", "pending": key}).json()
    assert third["spoken"] == "Deneme modu: işlem yapılmadı."


def test_exactly_one_hundred_dollars_is_not_large():
    client, _ = make_client(amountInUsd="100.00", amountOutUsd="99.75")
    assert offer(client)["spoken"].endswith("Onaylıyor musun? Evet de ya da Enter'a bas.")


def test_ids_stay_out_of_the_spoken_sentence():
    client, _ = make_client()
    data = offer(client)
    assert data["correlationId"] == "abc"
    assert data["quote"]["from"] not in data["spoken"]
    assert data["pending"] not in data["spoken"]


def test_pasted_address_is_not_read_aloud():
    client, _ = make_client()
    address = "0x1234567890abcdef1234567890abcdef12345678"
    data = client.post("/api/quote", json=payload(from_token=address)).json()
    assert address not in data["spoken"]
    assert data["spoken"].startswith("Bu tokeni bulamadım.")


def test_ask_without_keys_points_to_the_form(monkeypatch):
    client, _ = make_client()

    async def unavailable(text):
        raise ParserUnavailable

    monkeypatch.setattr(main, "parse_intent", unavailable)
    response = client.post("/api/ask", json={"text": "1 SOL kaç dolar"})
    assert response.status_code == 503
    assert response.json()["language"] == "tr"
    assert "Gelişmiş" in response.json()["spoken"]


def test_ask_rejects_empty_and_long_text():
    client, _ = make_client()
    assert client.post("/api/ask", json={"text": "  "}).json()["error"] == "empty_text"
    assert client.post("/api/ask", json={"text": "a" * 301}).json()["error"] == "too_long"


def test_detect_language():
    assert detect_language("1 SOL kaç dolar") == "tr"
    assert detect_language("price of NEAR") == "en"


def test_page_is_served():
    client, _ = make_client()
    response = client.get("/")
    assert response.status_code == 200
    assert 'aria-live="polite"' in response.text
    assert "<details>" in response.text
    assert 'aria-describedby="shortcuts"' in response.text
