"""Live swaps against a fake Agent API. A mock transport means no request can leave."""
import asyncio
import json
import time
from decimal import Decimal

import httpx
import pytest

import app.live as live
import app.main as main
from app.agent_api import live_ready
from tests.test_quote import make_client, payload, use_intent

SETTINGS = ("NEAR_INTENTS_AGENT_API_KEY", "AGENT_API_KEY", "AGENT_ID", "GRANT_TOKEN", "LIVE_ENABLED")
LIMITS = ("MAX_LIVE_USD", "MAX_LIVE_DAILY_USD", "EXPLORER_TX_URL")
TOKENS = [
    {"asset_id": "usdc-near", "symbol": "USDC", "blockchain": "near", "decimals": 6, "price": 1.0},
    {"asset_id": "wnear", "symbol": "wNEAR", "blockchain": "near", "decimals": 24, "price": 4.0},
    {"asset_id": "sol", "symbol": "SOL", "blockchain": "sol", "decimals": 9, "price": 100.0},
]
GOOD_POLICY = {
    "status": "APPLIED",
    "provider_policy_synced": True,
    "policy": {"frozen": False, "actions": ["swap"], "assets": ["a"], "budget": {"daily_usd": "10"}},
}


class FakeAgent:
    """Stands in for the Agent API, and records every request."""

    def __init__(self):
        self.requests = []
        self.frozen = False
        self.policy = json.loads(json.dumps(GOOD_POLICY))
        self.usd = "4.00"
        self.amount_out = "4000000"
        self.min_out = "3960000"
        self.time_estimate = 12
        self.fee = {"amount_usd": "0.02", "percent": "0.5"}
        self.warnings = []
        self.quote_error = None
        self.swap_replies = []
        self.status_replies = []
        self.transport = httpx.MockTransport(self.handle)

    def live_swaps(self):
        found = []
        for request in self.requests:
            if request.url.path.endswith("/swap"):
                body = json.loads(request.content)
                if not body.get("dry"):
                    found.append((request, body))
        return found

    def quotes(self):
        return [
            r for r in self.requests
            if r.url.path.endswith("/swap") and json.loads(r.content).get("dry")
        ]

    def error(self, status, code, retryable=False):
        meta = {"retryable": True} if retryable else {}
        return httpx.Response(status, json={"errors": [{"code": code, "meta": meta}]})

    def handle(self, request):
        self.requests.append(request)
        path = request.url.path
        if path == "/v1/tokens":
            return httpx.Response(200, json={"data": TOKENS})
        if path.endswith("/policy"):
            policy = json.loads(json.dumps(self.policy))
            policy["policy"]["frozen"] = self.frozen
            return httpx.Response(200, json=policy)
        if path == "/v1/status":
            return self.status_replies.pop(0) if self.status_replies else httpx.Response(
                200, json={"status": "PROCESSING", "details": {}}
            )
        if path.endswith("/swap"):
            if json.loads(request.content).get("dry"):
                return self.quote_reply()
            if self.swap_replies:
                reply = self.swap_replies.pop(0)
                if isinstance(reply, Exception):
                    raise reply
                return reply
            return httpx.Response(202, json={"correlation_id": "op_1", "status": "PROCESSING"})
        return httpx.Response(404, json={"errors": [{"code": "not_found"}]})

    def quote_reply(self):
        if self.quote_error:
            return self.error(*self.quote_error)
        quote = {"amount_out": self.amount_out}
        if self.min_out:
            quote["min_amount_out"] = self.min_out
        if self.time_estimate is not None:
            quote["time_estimate"] = self.time_estimate
        return httpx.Response(
            200,
            json={
                "dry": True,
                "type": "swap",
                "quote": quote,
                "spend": {"amount_usd": self.usd, "budget": {}},
                "fee": self.fee,
                "warnings": self.warnings,
                "owner_approval": False,
            },
        )


@pytest.fixture
def no_live(monkeypatch):
    for name in SETTINGS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def agent(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVE_ENABLED", "true")
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    monkeypatch.setenv("AGENT_ID", "agent")
    monkeypatch.setenv("GRANT_TOKEN", "ngt_test")
    monkeypatch.setenv("LIVE_LEDGER_PATH", str(tmp_path / "spend.json"))
    for name in LIMITS:
        monkeypatch.delenv(name, raising=False)
    fake = FakeAgent()
    monkeypatch.setattr(live, "transport", fake.transport)
    return fake


def swap_body(**changes):
    return payload(from_token="USDC", to_token="SOL", amount="4", live=True, **changes)


def offer(client, **changes):
    return client.post("/api/quote", json=swap_body(**changes)).json()


def answer(client, key, text):
    return client.post("/api/ask", json={"text": text, "pending": key}).json()


def track(client, track_id):
    return client.post("/api/live/status", json={"track": track_id, "lang": "tr"}).json()


def status(name, **details):
    return httpx.Response(200, json={"status": name, "failure_code": None, "details": details})


def confirmed(client, fake):
    """Quote and confirm. Returns the reply to the confirmation."""
    data = offer(client)
    return answer(client, data["pending"], "evet")


# Switched off by default


def test_off_when_nothing_is_set(no_live):
    assert live_ready() is False


def test_off_without_the_switch_even_with_every_key(agent, monkeypatch):
    monkeypatch.delenv("LIVE_ENABLED")
    assert live_ready() is False
    client, _ = make_client()
    assert client.post("/api/mode", json={"live": True}).status_code == 409
    assert offer(client)["error"] == "live_not_configured"
    assert agent.requests == []


@pytest.mark.parametrize("value", ["false", "1", "yes", "", "TRUEE"])
def test_only_true_turns_it_on(agent, monkeypatch, value):
    monkeypatch.setenv("LIVE_ENABLED", value)
    assert live_ready() is False


@pytest.mark.parametrize("missing", ["NEAR_INTENTS_AGENT_API_KEY", "AGENT_ID", "GRANT_TOKEN"])
def test_every_setting_is_needed(agent, monkeypatch, missing):
    monkeypatch.delenv(missing)
    client, _ = make_client()
    assert client.post("/api/mode", json={"live": True}).status_code == 409
    assert agent.requests == []


def test_short_key_name_also_counts(agent, monkeypatch):
    monkeypatch.delenv("NEAR_INTENTS_AGENT_API_KEY")
    monkeypatch.setenv("AGENT_API_KEY", "naa_test")
    client, _ = make_client()
    assert client.post("/api/mode", json={"live": True}).json()["live"] is True


def test_mode_message_without_setup(no_live):
    client, _ = make_client()
    response = client.post("/api/mode", json={"live": True, "lang": "tr"})
    assert response.json()["spoken"].startswith("Canlı mod için ajan cüzdanı kurulmadı.")


def test_ask_refuses_live_without_setup(no_live, monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", amount="1", from_token="USDC", to_token="SOL")
    data = client.post("/api/ask", json={"text": "x", "live": True}).json()
    assert data["error"] == "live_not_configured"
    assert sent == []


def test_turning_live_off_needs_nothing(no_live):
    client, _ = make_client()
    assert client.post("/api/mode", json={"live": False}).json()["live"] is False


# Quote, read, confirm


def test_quote_reads_the_terms_and_sends_nothing(agent):
    client, sent = make_client()
    data = offer(client)
    assert data["mode"] == "live"
    assert data["confirm_button"] is True
    assert data["spoken"].startswith(
        "Canlı mod, gerçek para. Veriyorsun: 4 USDC. Alıyorsun: yaklaşık 0,004 SOL. "
        "En az garanti: 0,00396 SOL. Ücret: yaklaşık 0,02 dolar. "
        "Süre: yaklaşık 12 saniye. Teklif 2 dakika geçerli."
    )
    assert data["spoken"].endswith("Onaylıyor musun? Evet yaz ya da Onayla düğmesine bas.")
    assert "Enter" not in data["spoken"]
    assert agent.live_swaps() == []
    assert sent == []


def test_quote_needs_no_grant_token(agent):
    client, _ = make_client()
    offer(client)
    assert "X-Grant-Token" not in agent.quotes()[0].headers


def test_missing_time_is_said_plainly(agent):
    agent.time_estimate = None
    client, _ = make_client()
    assert "Süre bilgisi yok." in offer(client)["spoken"]


def test_high_fee_is_warned(agent):
    agent.warnings = [{"code": "high_fee", "detail": "x"}]
    client, _ = make_client()
    assert "ücret yüzde beşi geçiyor" in offer(client)["spoken"]


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_empty_enter_never_sends(agent, blank):
    client, _ = make_client()
    key = offer(client)["pending"]
    for _ in range(3):
        data = answer(client, key, blank)
        assert data["spoken"].startswith("Canlı modda Enter onay sayılmaz.")
        assert data["confirm_button"] is True
    assert agent.live_swaps() == []
    assert answer(client, key, "evet")["action"] == "live_sent"


@pytest.mark.parametrize("word", ["evet", "EVET", "yes", "Yes."])
def test_typed_word_sends(agent, word):
    client, _ = make_client()
    key = offer(client)["pending"]
    data = answer(client, key, word)
    assert data["mode"] == "live"
    assert data["spoken"] == "İşleniyor. Bitince söyleyeceğim."
    assert data["track"]
    assert len(agent.live_swaps()) == 1


@pytest.mark.parametrize("words", ["belki", "evet ama 10 olsun", "tamam"])
def test_other_words_never_send(agent, words):
    client, _ = make_client()
    key = offer(client)["pending"]
    answer(client, key, words)
    assert agent.live_swaps() == []


def test_cancel_sends_nothing(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    assert answer(client, key, "iptal")["action"] == "cancelled"
    assert agent.live_swaps() == []


def test_one_confirmation_sends_once(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    answer(client, key, "evet")
    assert answer(client, key, "evet")["action"] == "expired"
    assert len(agent.live_swaps()) == 1


def test_swap_request_matches_what_was_read(agent):
    client, _ = make_client()
    confirmed(client, agent)
    request, body = agent.live_swaps()[0]
    assert body == {
        "origin_asset": "usdc-near",
        "destination_asset": "sol",
        "amount": "4000000",
        "min_amount_out": "3960000",
    }
    assert request.headers["X-Grant-Token"] == "ngt_test"
    assert len(request.headers["Idempotency-Key"]) >= 8


def test_minimum_falls_back_to_one_percent(agent):
    agent.min_out = None
    client, _ = make_client()
    confirmed(client, agent)
    assert agent.live_swaps()[0][1]["min_amount_out"] == "3960000"


def test_large_amount_still_needs_two_typed_answers(agent, monkeypatch):
    monkeypatch.setenv("MAX_LIVE_USD", "1000")
    monkeypatch.setenv("MAX_LIVE_DAILY_USD", "1000")
    agent.usd = "500"
    client, _ = make_client()
    first = offer(client)
    key = first["pending"]
    assert "beş yüz dolar mı dedin" in first["spoken"]
    assert answer(client, key, "")["action"] == "large"
    assert answer(client, key, "evet")["action"] == "confirm"
    assert answer(client, key, "")["action"] == "confirm"
    assert agent.live_swaps() == []
    assert answer(client, key, "evet")["action"] == "live_sent"


def test_amount_answer_stays_live(agent, monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="swap", from_token="USDC", to_token="SOL")
    key = client.post("/api/ask", json={"text": "x", "live": True}).json()["pending"]
    data = answer(client, key, "4")
    assert data["mode"] == "live"
    assert answer(client, data["pending"], "")["action"] == "confirm"


# Checked again just before sending


def test_a_fresh_quote_is_taken_before_sending(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    assert len(agent.quotes()) == 1
    answer(client, key, "evet")
    assert len(agent.quotes()) == 2


def test_small_price_ticks_do_not_ask_again(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    agent.amount_out = "3990000"
    assert answer(client, key, "evet")["action"] == "live_sent"


@pytest.mark.parametrize("amount_out", ["3900000", "4100000"])
def test_changed_output_is_asked_again_and_not_sent(agent, amount_out):
    client, _ = make_client()
    key = offer(client)["pending"]
    agent.amount_out = amount_out
    data = answer(client, key, "evet")
    assert data["spoken"].startswith("Teklif değişti, işlem yapılmadı. Yeni teklifi okuyorum.")
    assert data["pending"] != key
    assert agent.live_swaps() == []
    assert answer(client, data["pending"], "evet")["action"] == "live_sent"
    assert len(agent.live_swaps()) == 1


def test_changed_dollar_value_is_asked_again(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    agent.usd = "4.20"
    assert "pending" in answer(client, key, "evet")
    assert agent.live_swaps() == []


def test_expired_quote_is_asked_again(agent):
    client, _ = make_client()
    data = offer(client)
    item = main.pendings.get(data["pending"])
    item.order.quoted_at -= live.QUOTE_SECONDS + 1
    reply = answer(client, data["pending"], "evet")
    assert reply["spoken"].startswith("Teklif değişti")
    assert agent.live_swaps() == []


def test_a_new_rule_warning_stops_the_send(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    agent.warnings = [{"code": "insufficient_balance", "detail": "x"}]
    data = answer(client, key, "evet")
    assert data["spoken"].startswith("Ajanın bakiyesi yetmiyor")
    assert agent.live_swaps() == []


# The app's own limits


def test_over_the_transaction_limit_is_refused_with_what_to_do(agent):
    agent.usd = "5.01"
    client, _ = make_client()
    data = offer(client)
    assert data["error"] == "live_over_limit"
    assert data["spoken"] == (
        "Bu işlem 5,01 dolar, tek işlem sınırı 5 dolar, işlem yapılmadı. "
        "Daha küçük bir miktar söyle."
    )
    assert "pending" not in data
    assert agent.live_swaps() == []


def test_exactly_the_limit_is_allowed(agent):
    agent.usd = "5"
    client, _ = make_client()
    assert "pending" in offer(client)


def test_limit_can_be_lowered(agent, monkeypatch):
    monkeypatch.setenv("MAX_LIVE_USD", "1")
    client, _ = make_client()
    assert offer(client)["error"] == "live_over_limit"


def test_broken_limit_falls_back_to_the_default(agent, monkeypatch):
    monkeypatch.setenv("MAX_LIVE_USD", "not-a-number")
    agent.usd = "6"
    client, _ = make_client()
    assert offer(client)["error"] == "live_over_limit"


def test_daily_total_adds_up_and_stops(agent):
    client, _ = make_client()
    assert confirmed(client, agent)["action"] == "live_sent"
    assert confirmed(client, agent)["action"] == "live_sent"
    data = offer(client)
    assert data["error"] == "live_over_daily"
    assert "kalan 2 dolar" in data["spoken"]
    assert len(agent.live_swaps()) == 2


def test_daily_total_is_checked_again_before_sending(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    live.ledger.reserve("earlier", Decimal("9"))
    data = answer(client, key, "evet")
    assert data["error"] == "live_over_daily"
    assert agent.live_swaps() == []


def test_daily_total_survives_a_restart(agent):
    client, _ = make_client()
    confirmed(client, agent)
    assert live.SpendLedger().total() == Decimal("4.00")


def test_old_spending_leaves_the_total(agent):
    path = live.ledger.path()
    path.write_text(
        json.dumps([{"key": "old", "usd": "9", "at": time.time() - live.DAY_SECONDS - 1}]),
        encoding="utf-8",
    )
    assert live.ledger.total() == 0


def test_broken_ledger_stops_every_swap(agent):
    live.ledger.path().write_text("not json", encoding="utf-8")
    client, _ = make_client()
    data = offer(client)
    assert data["error"] == "live_ledger_broken"
    assert agent.live_swaps() == []


@pytest.mark.parametrize("usd", [None, "0", "-1", "abc", "NaN"])
def test_unusable_dollar_value_stops_the_swap(agent, usd):
    agent.usd = usd
    client, _ = make_client()
    assert offer(client)["error"] == "live_no_price"


@pytest.mark.parametrize("value", [None, "", "abc", "0", "-5"])
def test_unreadable_quote_stops_the_swap(agent, value):
    agent.amount_out = value
    client, _ = make_client()
    assert offer(client)["error"] == "live_quote_unreadable"


# Frozen agent


def test_frozen_agent_gets_no_quote(agent):
    agent.frozen = True
    client, _ = make_client()
    data = offer(client)
    assert data["spoken"] == "Ajan dondurulmuş, çözmek için ajanı çöz de."
    assert agent.quotes() == []
    assert agent.live_swaps() == []


def test_freezing_after_the_quote_stops_the_send(agent):
    client, _ = make_client()
    key = offer(client)["pending"]
    agent.frozen = True
    data = answer(client, key, "evet")
    assert data["spoken"] == "Ajan dondurulmuş, çözmek için ajanı çöz de."
    assert agent.live_swaps() == []


def test_api_frozen_refusal_says_the_same(agent):
    agent.quote_error = (409, "wallet_frozen")
    client, _ = make_client()
    assert offer(client)["spoken"] == "Ajan dondurulmuş, çözmek için ajanı çöz de."


def test_policy_not_in_force_stops_the_swap(agent):
    agent.policy["status"] = "SIGNED"
    client, _ = make_client()
    assert offer(client)["error"] == "policy_not_ready"
    assert agent.quotes() == []


def test_unknown_frozen_state_counts_as_frozen():
    data = {**GOOD_POLICY, "policy": {"actions": ["swap"]}}

    class Reader:
        async def policy(self, agent_id):
            return data

    with pytest.raises(live.QuoteError) as stopped:
        asyncio.run(live.ensure_active(Reader(), "agent"))
    assert stopped.value.code == "agent_frozen"


def test_unreadable_agent_stops_the_swap(agent, monkeypatch):
    def refuse(request):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(live, "transport", httpx.MockTransport(refuse))
    client, _ = make_client()
    assert offer(client)["error"] == "agent_read_failed"


# Refusals, retries, and unknown results


def test_proven_refusal_is_uncounted(agent):
    agent.swap_replies = [agent.error(409, "wallet_busy")]
    client, _ = make_client()
    data = confirmed(client, agent)
    assert data["spoken"].startswith("Ajan başka bir işlemi bitiriyor")
    assert live.ledger.total() == 0


def test_lost_answer_retries_once_with_the_same_key_and_body(agent):
    agent.swap_replies = [httpx.ConnectError("lost")]
    client, _ = make_client()
    assert confirmed(client, agent)["action"] == "live_sent"
    swaps = agent.live_swaps()
    assert len(swaps) == 2
    assert swaps[0][0].headers["Idempotency-Key"] == swaps[1][0].headers["Idempotency-Key"]
    assert swaps[0][1] == swaps[1][1]


def test_two_lost_answers_stay_unknown_and_stay_counted(agent):
    agent.swap_replies = [httpx.ConnectError("lost"), httpx.ConnectError("lost")]
    client, _ = make_client()
    data = confirmed(client, agent)
    assert data["spoken"].startswith("Sonuç belirsiz, para hareket etmiş olabilir.")
    assert "track" not in data
    assert len(agent.live_swaps()) == 2
    assert live.ledger.total() == Decimal("4.00")


def test_server_error_is_never_called_a_refusal(agent):
    agent.swap_replies = [agent.error(500, "internal_error"), agent.error(500, "internal_error")]
    client, _ = make_client()
    data = confirmed(client, agent)
    assert data["error"] == "live_unknown"
    assert live.ledger.total() == Decimal("4.00")


def test_unknown_refusal_stays_counted(agent):
    agent.swap_replies = [agent.error(400, "something_new")]
    client, _ = make_client()
    data = confirmed(client, agent)
    assert data["error"] == "live_refused"
    assert live.ledger.total() == Decimal("4.00")


# Following the swap


def test_processing_then_done_with_a_link(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [
        status("PROCESSING"),
        status("SUCCESS", amount_out="3990000", tx_hash="HASH1"),
    ]
    assert track(client, track_id)["spoken"] == "İşleniyor. Bitince söyleyeceğim."
    data = track(client, track_id)
    assert data["final"] is True
    assert data["spoken"] == (
        "Tamamlandı. 0,00399 SOL aldın. İşlem bağlantısı için kopyala düğmesini kullan."
    )
    assert data["proof"] == "https://nearblocks.io/txns/HASH1"
    assert data["proof_key"] == "proof"


def test_link_form_can_be_set(agent, monkeypatch):
    monkeypatch.setenv("EXPLORER_TX_URL", "https://example.test/tx/{hash}")
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("SUCCESS", amount_out="1000000", tx_hash="H")]
    assert track(client, track_id)["proof"] == "https://example.test/tx/H"


def test_intent_hash_is_copied_when_there_is_no_transaction(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("SUCCESS", amount_out="1000000", intent_hash="INTENT")]
    data = track(client, track_id)
    assert data["proof"] == "INTENT"
    assert data["proof_key"] == "proof_id"


def test_hashes_are_never_read_aloud(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("SUCCESS", amount_out="1000000", tx_hash="HASHVALUE")]
    assert "HASHVALUE" not in track(client, track_id)["spoken"]


def test_refund_says_where_the_money_went(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("REFUNDED")]
    data = track(client, track_id)
    assert data["spoken"].startswith("İade edildi. Para ajanın kendi bakiyesine döndü.")
    assert data["final"] is True


def test_partial_refund_says_what_arrived(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("REFUNDED", amount_out="1000000")]
    assert track(client, track_id)["spoken"].startswith("Kısmen tamamlandı. 0,001 SOL aldın")


def test_failure_that_never_ran_is_uncounted(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("FAILED", never_executed=True)]
    assert track(client, track_id)["spoken"].startswith("Başarısız, para hareket etmedi.")
    assert live.ledger.total() == 0


def test_failure_without_proof_stays_counted_and_is_not_retried(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("FAILED")]
    assert track(client, track_id)["spoken"].startswith("Başarısız, para hareket etmiş olabilir.")
    assert live.ledger.total() == Decimal("4.00")
    assert len(agent.live_swaps()) == 1


def test_uncertain_keeps_following_and_never_resends(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("UNCERTAIN"), status("SUCCESS", amount_out="1000000")]
    first = track(client, track_id)
    assert first["final"] is False
    assert first["spoken"].startswith("Sonuç henüz kesinleşmedi. Yeniden gönderme")
    assert track(client, track_id)["state"] == "done"
    assert len(agent.live_swaps()) == 1


def test_review_stops_following(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [status("NEEDS_REVIEW")]
    data = track(client, track_id)
    assert data["final"] is True
    assert "Yeniden gönderme" in data["spoken"]


def test_missed_status_check_reads_as_processing(agent):
    client, _ = make_client()
    track_id = confirmed(client, agent)["track"]
    agent.status_replies = [httpx.Response(503, json={"errors": [{"code": "x"}]})]
    assert track(client, track_id)["state"] == "processing"


def test_unknown_tracking_id_warns_against_resending(agent):
    client, _ = make_client()
    data = track(client, "unknown")
    assert data["final"] is True
    assert "Yeniden gönderme" in data["spoken"]


# Dry mode is untouched


def test_dry_mode_keeps_empty_enter_and_never_reaches_the_agent(agent):
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    assert answer(client, key, "")["spoken"] == "Deneme modu: işlem yapılmadı."
    assert agent.requests == []


def test_dry_quote_shows_no_confirm_button(no_live):
    client, _ = make_client()
    assert client.post("/api/quote", json=payload()).json()["confirm_button"] is False


def test_money_stays_behind_the_live_module():
    assert not hasattr(main, "AgentApi")
    assert not hasattr(main, "create_grant_credential")


def test_tests_cannot_reach_a_network(agent):
    assert live.client().transport is agent.transport


def test_help_warns_about_real_money_in_live_mode(agent, monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="help")
    data = client.post("/api/ask", json={"text": "x", "live": True}).json()
    assert "gerçek para" in data["spoken"]
    assert "para hareket etmez" not in data["spoken"]


def test_help_stays_calm_in_dry_mode(no_live, monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="help")
    data = client.post("/api/ask", json={"text": "x"}).json()
    assert "para hareket etmez" in data["spoken"]


def test_live_quote_expires_with_its_two_minutes(agent):
    client, _ = make_client()
    data = offer(client)
    assert data["expires_in"] == live.QUOTE_SECONDS
    remaining = main.pendings.get(data["pending"]).expires_at - time.monotonic()
    assert remaining <= live.QUOTE_SECONDS
    main.pendings.get(data["pending"]).expires_at = 0
    assert answer(client, data["pending"], "evet")["action"] == "expired"
    assert agent.live_swaps() == []
