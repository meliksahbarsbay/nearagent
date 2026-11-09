"""Balance, local history, and dollar quotes. No real network is reached."""
import json
from datetime import datetime, timezone

import httpx
import pytest

import app.history as history_module
import app.main as main
from app.agent_api import AgentApiError, read_agent_balances
from app.commands import detect_command
from app.history import KEEP, history
from app.messages import fee_usd, say_balances, say_date, say_history
from app.oneclick import QuoteError, build_quote_request, token_amount
from tests.test_live import FakeAgent, swap_body, track, answer, status
from tests.test_quote import make_client, payload, use_intent
import app.live as live

BALANCES = {
    "balances": [
        {"symbol": "USDC", "blockchain": "base", "balance": "10", "price": 0.9999},
        {"symbol": "SOL", "blockchain": "sol", "balance": "0.5", "price": 95.5},
        {"symbol": "ETH", "blockchain": "eth", "balance": "0", "price": 2000},
    ]
}


@pytest.fixture(autouse=True)
def saved_history(monkeypatch, tmp_path):
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setenv("LIVE_LEDGER_PATH", str(tmp_path / "spend.json"))


@pytest.fixture
def agent_set(monkeypatch):
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    monkeypatch.setenv("AGENT_ID", "agent-1")


@pytest.fixture
def no_agent(monkeypatch):
    for name in ("NEAR_INTENTS_AGENT_API_KEY", "AGENT_API_KEY", "AGENT_ID"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def no_parser(monkeypatch):
    async def fail(text):
        raise AssertionError("commands must not reach the parser")

    monkeypatch.setattr(main, "parse_intent", fail)


def ask(client, text):
    return client.post("/api/ask", json={"text": text}).json()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("cüzdanımda ne var", ("balance", "tr")),
        ("cüzdanım ne", ("balance", "tr")),
        ("bakiyem ne kadar", ("balance", "tr")),
        ("what's my balance", ("balance", "en")),
        ("what is my balance", ("balance", "en")),
        ("show my wallet", ("balance", "en")),
        ("son işlemlerimi oku", ("history", "tr")),
        ("son 5 işlemimi oku", ("history", "tr")),
        ("işlem geçmişimi oku", ("history", "tr")),
        ("read my recent trades", ("history", "en")),
        ("show my last trades", ("history", "en")),
    ],
)
def test_commands(text, expected):
    assert detect_command(text) == expected


@pytest.mark.parametrize("text", ["2 NEAR'ı USDC'ye çevir", "swap 2 NEAR to USDC"])
def test_swaps_are_not_commands(text):
    assert detect_command(text) is None


def test_balance_needs_an_agent(no_agent, no_parser):
    client, _ = make_client()
    assert ask(client, "cüzdanımda ne var")["spoken"].startswith("Ajan cüzdanı kurulmadı")


def test_balance_is_read_token_by_token(agent_set, no_parser, monkeypatch):
    async def read():
        return BALANCES

    monkeypatch.setattr(main, "read_agent_balances", read)
    client, _ = make_client()
    assert ask(client, "cüzdanımda ne var")["spoken"] == (
        "Cüzdanında: 10 USDC, yaklaşık 9,99 dolar. 0,5 SOL, yaklaşık 47,75 dolar. "
        "Toplam yaklaşık 57,74 dolar."
    )


def test_balance_in_english():
    spoken = say_balances({"balances": BALANCES["balances"][:1]}, "en")
    assert spoken == "In your wallet: 10 USDC, about 9.99 dollars."


def test_empty_wallet_is_said_plainly():
    assert say_balances({"balances": []}, "tr").startswith("Cüzdanın boş.")
    assert say_balances(BALANCES | {"balances": BALANCES["balances"][2:]}, "tr").startswith(
        "Cüzdanın boş."
    )


def test_unknown_price_is_never_read_as_zero():
    rows = [{"symbol": "ABC", "balance": "3", "price": None}]
    assert say_balances({"balances": rows}, "tr") == (
        "Cüzdanında: 3 ABC, dolar karşılığı bilinmiyor."
    )


def test_dust_is_not_read_as_zero_dollars():
    rows = [{"symbol": "ABC", "balance": "0.001", "price": 1}]
    assert "0,01 dolardan az" in say_balances({"balances": rows}, "tr")


def test_same_symbol_on_two_chains_names_the_chain():
    rows = [
        {"symbol": "USDC", "blockchain": "base", "balance": "1", "price": 1},
        {"symbol": "USDC", "blockchain": "near", "balance": "2", "price": 1},
    ]
    spoken = say_balances({"balances": rows}, "en")
    assert "1 USDC (Base)" in spoken and "2 USDC (NEAR)" in spoken


def test_balance_failure_is_spoken(agent_set, no_parser, monkeypatch):
    async def fail():
        raise AgentApiError(503, "provider_unavailable")

    monkeypatch.setattr(main, "read_agent_balances", fail)
    client, _ = make_client()
    assert ask(client, "cüzdanımda ne var")["spoken"].startswith("Ajan bilgisi alınamadı.")


def test_reading_balance_sends_no_grant_token(agent_set, monkeypatch):
    import asyncio

    monkeypatch.setenv("GRANT_TOKEN", "ngt_test")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=BALANCES)

    asyncio.run(read_agent_balances(httpx.MockTransport(handler)))
    assert seen[0].url.path == "/v1/agents/agent-1/balances"
    assert seen[0].url.params["source"] == "public"
    assert "X-Grant-Token" not in seen[0].headers


def test_history_is_empty_at_first(no_agent, no_parser):
    client, _ = make_client()
    data = ask(client, "son işlemlerimi oku")
    assert data["spoken"].startswith("Henüz kayıtlı işlem yok.")
    assert data["copies"] == []


def test_confirmed_dry_swap_is_saved_and_read(no_agent, no_parser):
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    client.post("/api/ask", json={"text": "evet", "pending": key})
    entry = history.recent(1)[0]
    assert entry["mode"] == "dry"
    assert entry["ref"] == "abc"
    data = ask(client, "son işlemlerimi oku")
    assert data["spoken"].startswith("Son 1 işlem. İşlem 1: ")
    assert ", deneme. Teklif: 1 wNEAR karşılığında 4,301912 USDC, işlem yapılmadı." in data["spoken"]
    # A dry run received nothing, so it never says it did.
    assert "alındı" not in data["spoken"]
    assert "abc" not in data["spoken"]
    assert data["copies"] == [{"key": "trade", "number": 1, "value": "abc"}]


def test_cancelled_quote_is_not_saved(no_agent):
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    client.post("/api/ask", json={"text": "iptal", "pending": key})
    assert history.recent(5) == []


def test_only_the_last_five_are_read_newest_first(no_agent, no_parser):
    for number in range(7):
        history.add(mode="dry", status="dry", gave=str(number + 1), gave_symbol="A",
                    got="1", got_symbol="B", ref=f"ref{number}")
    client, _ = make_client()
    data = ask(client, "read my recent trades")
    assert data["spoken"].startswith("Last 5 trades. Trade 1: ")
    assert "Quote: 7 A for 1 B, nothing executed." in data["spoken"]
    assert "Quote: 2 A" not in data["spoken"]
    assert "received" not in data["spoken"]
    assert [c["value"] for c in data["copies"]] == ["ref6", "ref5", "ref4", "ref3", "ref2"]


def test_file_keeps_a_limit():
    for number in range(KEEP + 3):
        history.add(mode="dry", status="dry", gave="1", gave_symbol="A", got="1", got_symbol="B")
    assert len(json.loads(history.path().read_text(encoding="utf-8"))) == KEEP


def test_broken_history_is_spoken_and_never_stops_a_swap(no_agent, no_parser):
    history.path().write_text("not json", encoding="utf-8")
    client, _ = make_client()
    assert ask(client, "son işlemlerimi oku")["error"] == "history_broken"
    assert history.add(mode="dry", status="dry") is not None


def test_dates_read_plainly():
    moment = datetime(2026, 11, 1, 14, 30, tzinfo=timezone.utc).astimezone().isoformat()
    assert say_date(moment, "tr").startswith("1 Kasım, saat ")
    assert say_date(moment, "en").startswith("November 1 at ")


def test_unknown_status_does_not_crash():
    entry = {"at": datetime.now(timezone.utc).isoformat(), "mode": "live", "gave": "1",
             "gave_symbol": "A", "got": "1", "got_symbol": "B", "status": "new_state"}
    assert "new_state" in say_history([entry], "en")


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("LIVE_ENABLED", "true")
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    monkeypatch.setenv("AGENT_ID", "agent")
    monkeypatch.setenv("GRANT_TOKEN", "ngt_test")
    monkeypatch.delenv("MAX_LIVE_USD", raising=False)
    monkeypatch.delenv("MAX_LIVE_DAILY_USD", raising=False)
    agent = FakeAgent()
    monkeypatch.setattr(live, "transport", agent.transport)
    return agent


def confirm_live(client):
    key = client.post("/api/quote", json=swap_body()).json()["pending"]
    return answer(client, key, "evet")


def test_live_swap_is_saved_then_updated_with_what_arrived(fake):
    client, _ = make_client()
    track_id = confirm_live(client)["track"]
    entry = history.recent(1)[0]
    assert (entry["mode"], entry["status"], entry["ref"]) == ("live", "processing", "op_1")
    fake.status_replies = [status("SUCCESS", amount_out="3990000", tx_hash="HASH")]
    track(client, track_id)
    entry = history.recent(1)[0]
    assert entry["status"] == "done"
    assert entry["got"] == "0.003990000"
    assert entry["ref"].endswith("HASH")


def test_refused_live_swap_is_saved_as_not_sent(fake):
    fake.swap_replies = [fake.error(409, "wallet_busy")]
    client, _ = make_client()
    confirm_live(client)
    assert history.recent(1)[0]["status"] == "refused"


def test_unknown_live_swap_is_saved_as_unknown(fake):
    fake.swap_replies = [httpx.ConnectError("x"), httpx.ConnectError("x")]
    client, _ = make_client()
    confirm_live(client)
    assert history.recent(1)[0]["status"] == "unknown"


def test_history_write_failure_never_stops_a_live_swap(fake, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(history_module.History, "_write", fail)
    client, _ = make_client()
    assert confirm_live(client)["action"] == "live_sent"
    assert len(fake.live_swaps()) == 1


def test_swap_type_is_set_in_the_request():
    body = build_quote_request("a", "b", "1", "x", dry=True, swap_type="EXACT_OUTPUT")
    assert body["swapType"] == "EXACT_OUTPUT"
    assert build_quote_request("a", "b", "1", "x", dry=True)["swapType"] == "EXACT_INPUT"


def test_dollars_become_tokens_at_the_current_price():
    assert token_amount("50", "usd", {"symbol": "SOL", "price": 100.0}).startswith("0.5")
    assert token_amount("50", "token", {"symbol": "SOL", "price": 100.0}) == "50"


@pytest.mark.parametrize("price", [None, 0])
def test_dollars_need_a_price(price):
    with pytest.raises(QuoteError) as stopped:
        token_amount("50", "usd", {"symbol": "SOL", "price": price})
    assert stopped.value.code == "no_price"


def test_buying_by_dollars_uses_exact_output_in_the_bought_token(no_agent, monkeypatch):
    client, sent = make_client(
        amountIn="50633048", amountInFormatted="50.633048", minAmountIn="50126717",
        amountInUsd="50.63", amountOutUsd="50.00", amountOutFormatted="0.277",
        minAmountOut="277000000",
    )
    use_intent(
        monkeypatch, action="swap", amount="50", from_token="USDC", to_token="SOL",
        amount_unit="usd", amount_side="to",
    )
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert sent[0]["swapType"] == "EXACT_OUTPUT"
    # 50 dollars at the mock's SOL price of 180.5, in SOL's nine decimals.
    assert sent[0]["amount"] == "277008310"
    assert sent[0]["originAsset"] == "nep141:usdc.near"
    assert data["quote"]["swapType"] == "EXACT_OUTPUT"
    assert "Veriyorsun: en çok 50,633048 USDC. Alıyorsun: tam 0,277 SOL." in data["spoken"]
    assert "Söylediğin 50 dolar güncel fiyatla çevrildi. Artan para iade edilir." in data["spoken"]


def test_buffer_is_not_read_as_a_fee(no_agent):
    quote = {
        "amountIn": "50633048", "minAmountIn": "50126717",
        "amountInUsd": "50.633048", "amountOutUsd": "50.00",
    }
    assert float(fee_usd(quote, True)) == pytest.approx(0.13, abs=0.01)
    assert float(fee_usd(quote)) == pytest.approx(0.63, abs=0.01)


def test_selling_by_dollars_uses_exact_input_in_the_sold_token(no_agent, monkeypatch):
    client, sent = make_client()
    use_intent(
        monkeypatch, action="swap", amount="90.25", from_token="SOL", to_token="USDC",
        amount_unit="usd", amount_side="from",
    )
    client.post("/api/ask", json={"text": "x"})
    assert sent[0]["swapType"] == "EXACT_INPUT"
    assert sent[0]["originAsset"] == "nep141:sol.omft.near"
    assert sent[0]["amount"] == "500000000"


def test_plain_swap_stays_exact_input(no_agent, monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", amount="2", from_token="NEAR", to_token="USDC")
    client.post("/api/ask", json={"text": "x"})
    assert sent[0]["swapType"] == "EXACT_INPUT"


def test_how_much_answer_in_dollars_binds_to_the_same_swap(no_agent, monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", from_token="SOL", to_token="USDC")
    key = client.post("/api/ask", json={"text": "x"}).json()["pending"]
    client.post("/api/ask", json={"text": "90,25 dolar", "pending": key})
    assert sent[0]["amount"] == "500000000"


def test_how_much_answer_in_words(no_agent, monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", from_token="USDC", to_token="SOL")
    key = client.post("/api/ask", json={"text": "x"}).json()["pending"]
    client.post("/api/ask", json={"text": "bir buçuk", "pending": key})
    assert sent[0]["amount"] == "1500000"


def test_form_reads_turkish_thousands(no_agent):
    client, sent = make_client()
    client.post("/api/quote", json=payload(from_token="USDC", to_token="SOL", amount="1.000"))
    assert sent[0]["amount"] == "1000000000"


def test_form_in_english_reads_the_same_digits_as_one(no_agent):
    client, sent = make_client()
    client.post(
        "/api/quote", json=payload(from_token="USDC", to_token="SOL", amount="1.000", lang="en")
    )
    assert sent[0]["amount"] == "1000000"


def test_price_in_dollars_is_read(no_agent, monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="price", amount="361", from_token="SOL", amount_unit="usd")
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert data["spoken"].startswith("361 dolar yaklaşık 2 SOL.")


def test_live_dollars_become_an_exact_input_at_the_token_price(fake, monkeypatch):
    client, sent = make_client()
    use_intent(
        monkeypatch, action="swap", amount="4", from_token="USDC", to_token="SOL",
        amount_unit="usd", amount_side="to",
    )
    data = client.post("/api/ask", json={"text": "x", "live": True}).json()
    assert data["mode"] == "live"
    assert "Söylediğin 4 dolar güncel fiyatla çevrildi." in data["spoken"]
    body = json.loads(fake.quotes()[0].content)
    assert body["amount"] == "4000000"
    assert sent == []


def test_live_token_amount_of_the_bought_side_becomes_an_input(fake, monkeypatch):
    client, _ = make_client()
    use_intent(
        monkeypatch, action="swap", amount="0.04", from_token="USDC", to_token="SOL",
        amount_side="to",
    )
    client.post("/api/ask", json={"text": "x", "live": True})
    assert json.loads(fake.quotes()[0].content)["amount"] == "4000000"


def test_changed_live_dollar_quote_is_asked_again_with_the_same_meaning(fake, monkeypatch):
    client, _ = make_client()
    use_intent(
        monkeypatch, action="swap", amount="4", from_token="USDC", to_token="SOL",
        amount_unit="usd", amount_side="to",
    )
    key = client.post("/api/ask", json={"text": "x", "live": True}).json()["pending"]
    fake.amount_out = "3000000"
    data = answer(client, key, "evet")
    assert data["spoken"].startswith("Teklif değişti")
    assert "Söylediğin 4 dolar" in data["spoken"]
