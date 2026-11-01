"""Withdrawals against a fake Agent API. A mock transport means no request can leave."""
import asyncio
import json

import httpx
import pytest

import app.live as live
import app.main as main
import scripts.owner_setup as setup
from app.commands import detect_command
from app.history import history
from tests.test_live import FakeAgent, answer, status, track
from tests.test_quote import make_client, use_intent

OWNER = "a" * 64
USDC = "usdc-base"
SOL = "sol"
PROOF_CAP = "5000000"


class FakeWallet(FakeAgent):
    def __init__(self):
        super().__init__()
        self.policy["policy"].update(
            {
                "actions": ["swap", "withdraw"],
                "destinations": {
                    "mode": "only",
                    "list": [{"action": "withdraw", "chain": "near", "address": OWNER, "memo": None}],
                },
                "limits": {"per_transaction": {USDC: PROOF_CAP, SOL: "50000000"}},
            }
        )
        self.balances = [
            {
                "asset_id": USDC, "symbol": "USDC", "decimals": 6, "blockchain": "base",
                "price": 1.0, "balance_raw": "4000000", "available_raw": "4000000",
            }
        ]
        self.preview_usd = "4.00"
        self.remaining = "10.000000"
        self.received = "3990000"
        self.withdraw_warnings = []
        self.withdraw_error = None
        self.send_replies = []

    def previews(self):
        return [r for r in self.withdraws() if json.loads(r.content).get("dry")]

    def sends(self):
        return [r for r in self.withdraws() if not json.loads(r.content).get("dry")]

    def withdraws(self):
        return [r for r in self.requests if r.url.path.endswith("/withdraw")]

    def handle(self, request):
        path = request.url.path
        if path.endswith("/balances"):
            self.requests.append(request)
            return httpx.Response(200, json={"balances": self.balances})
        if path.endswith("/withdraw"):
            self.requests.append(request)
            if json.loads(request.content).get("dry"):
                if self.withdraw_error:
                    return self.error(*self.withdraw_error)
                quote = {"amount_out": self.received} if self.received else {}
                return httpx.Response(
                    200,
                    json={
                        "dry": True,
                        "type": "withdraw",
                        "quote": quote,
                        "spend": {
                            "amount_usd": self.preview_usd,
                            "budget": {"daily": {"remaining_usd": self.remaining}},
                        },
                        "fee": {"amount_usd": "0.01", "percent": "0.2"},
                        "warnings": self.withdraw_warnings,
                    },
                )
            if self.send_replies:
                reply = self.send_replies.pop(0)
                if isinstance(reply, Exception):
                    raise reply
                return reply
            return httpx.Response(202, json={"correlation_id": "op_w", "status": "PROCESSING"})
        return super().handle(request)


@pytest.fixture
def wallet(monkeypatch):
    monkeypatch.setenv("LIVE_ENABLED", "true")
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    monkeypatch.setenv("AGENT_ID", "agent")
    monkeypatch.setenv("GRANT_TOKEN", "ngt_test")
    monkeypatch.delenv("OWNER_ACCOUNT_ID", raising=False)
    fake = FakeWallet()
    monkeypatch.setattr(live, "transport", fake.transport)
    return fake


def ask(client, text, live_page=True):
    return client.post("/api/ask", json={"text": text, "live": live_page}).json()


@pytest.mark.parametrize(
    "text, lang",
    [
        ("paramı cüzdanıma çek", "tr"),
        ("hepsini çek", "tr"),
        ("5 USDC'yi cüzdanıma çek", "tr"),
        ("Paramı çek.", "tr"),
        ("withdraw to my wallet", "en"),
        ("withdraw 5 USDC", "en"),
        ("withdraw everything", "en"),
    ],
)
def test_commands(text, lang):
    assert detect_command(text) == ("withdraw", lang)


@pytest.mark.parametrize("text", ["2 NEAR'ı USDC'ye çevir", "cüzdanımda ne var", "what's my balance"])
def test_other_sentences_are_not_withdrawals(text):
    assert (detect_command(text) or ("",))[0] != "withdraw"


def test_no_agent_is_said_plainly(monkeypatch):
    for name in ("NEAR_INTENTS_AGENT_API_KEY", "AGENT_API_KEY", "AGENT_ID"):
        monkeypatch.delenv(name, raising=False)
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["spoken"].startswith("Ajan cüzdanı kurulmadı")


def test_off_without_the_live_switch(wallet, monkeypatch):
    monkeypatch.delenv("LIVE_ENABLED")
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "live_not_configured"
    assert wallet.requests == []


def test_a_page_in_dry_mode_cannot_confirm_real_money(wallet):
    client, _ = make_client()
    data = ask(client, "paramı cüzdanıma çek", live_page=False)
    assert data["spoken"].startswith("Çekim gerçek para kullanır, işlem yapılmadı.")
    assert "pending" not in data
    assert wallet.requests == []


@pytest.mark.parametrize("text, atomic", [("3 çek", "3000000"), ("2,5 çek", "2500000"), ("iki çek", "2000000")])
def test_a_bare_number_is_never_read_as_everything(wallet, text, atomic):
    client, _ = make_client()
    ask(client, text)
    assert json.loads(wallet.previews()[0].content)["amount"] == atomic


def test_an_amount_beats_the_word_all(wallet):
    client, _ = make_client()
    ask(client, "hepsini değil 2 USDC çek")
    assert json.loads(wallet.previews()[0].content)["amount"] == "2000000"


def test_offer_reads_what_where_and_the_budget_before_confirming(wallet):
    client, _ = make_client()
    data = ask(client, "paramı cüzdanıma çek")
    assert data["spoken"] == (
        "Canlı mod, gerçek para. Çekilecek: 4 USDC. Nereye: sahip adresin, NEAR ağı. "
        "Ulaşacak: yaklaşık 3,99 USDC. Ücret: yaklaşık 0,01 dolar. "
        "Bu çekim günlük bütçenden yaklaşık 4 dolar düşer, kalan 6 dolar olur. "
        "Teklif 2 dakika geçerli. "
        "Dikkat, bu token sahip hesabında kalır ve oradan Binance'e gönderilemez. "
        "Binance'e dönecekse önce NEAR'a çevir. "
        "Onaylıyor musun? Evet yaz ya da Onayla düğmesine bas."
    )
    assert data["confirm_button"] is True
    assert data["expires_in"] == live.QUOTE_SECONDS
    assert wallet.sends() == []


def test_owner_address_is_copied_and_never_read(wallet):
    client, _ = make_client()
    data = ask(client, "paramı cüzdanıma çek")
    assert OWNER not in data["spoken"]
    assert data["copies"] == [{"key": "owner_address", "value": OWNER}]


def test_english_terms(wallet):
    client, _ = make_client()
    spoken = ask(client, "withdraw to my wallet")["spoken"]
    assert spoken.startswith("Live mode, real money. Withdrawing: 4 USDC. To: your owner address, on NEAR.")


@pytest.mark.parametrize(
    "text",
    [
        "paramı 0x1234567890abcdef1234567890abcdef12345678 adresine çek",
        "withdraw to bob.near",
        "withdraw 5 USDC to alice.near",
        f"withdraw to {'b' * 64}",
        "withdraw to 7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
    ],
)
def test_any_named_address_is_refused(wallet, text):
    client, _ = make_client()
    data = ask(client, text)
    assert data["spoken"].startswith("Yalnızca sahip adresine çekebilirim") or data[
        "spoken"
    ].startswith("I can only withdraw")
    assert wallet.withdraws() == []


def test_recipient_always_comes_from_the_policy(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    answer(client, key, "evet")
    for request in wallet.withdraws():
        body = json.loads(request.content)
        assert body["recipient"] == OWNER
        assert body["chain"] == "near"


@pytest.mark.parametrize(
    "destinations",
    [
        {"mode": "only", "list": []},
        {"mode": "any", "list": []},
        {"mode": "except", "list": [{"action": "withdraw", "chain": "near", "address": OWNER}]},
        {
            "mode": "only",
            "list": [
                {"action": "withdraw", "chain": "near", "address": OWNER},
                {"action": "withdraw", "chain": "base", "address": "0xabc"},
            ],
        },
        {"mode": "only", "list": [{"action": "transfer", "address": OWNER}]},
    ],
)
def test_no_single_signed_address_moves_nothing(wallet, destinations):
    wallet.policy["policy"]["destinations"] = destinations
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "withdraw_no_target"
    assert wallet.withdraws() == []


def test_policy_without_withdraw_moves_nothing(wallet):
    wallet.policy["policy"]["actions"] = ["swap"]
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "withdraw_no_target"


def test_address_must_match_the_owner_setting(wallet, monkeypatch):
    monkeypatch.setenv("OWNER_ACCOUNT_ID", "c" * 64)
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "withdraw_no_target"


def test_policy_changed_after_confirmation_stops_the_send(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    wallet.policy["policy"]["destinations"]["list"][0]["address"] = "d" * 64
    data = answer(client, key, "evet")
    assert data["error"] == "withdraw_no_target"
    assert wallet.sends() == []


@pytest.mark.parametrize("blank", ["", "   "])
def test_empty_enter_never_sends(wallet, blank):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    for _ in range(3):
        assert answer(client, key, blank)["spoken"].startswith("Canlı modda Enter onay sayılmaz.")
    assert wallet.sends() == []


@pytest.mark.parametrize("word", ["evet", "yes"])
def test_typed_word_sends_with_grant_and_key(wallet, word):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    data = answer(client, key, word)
    assert data["action"] == "live_sent"
    assert data["track"]
    request = wallet.sends()[0]
    assert request.headers["X-Grant-Token"] == "ngt_test"
    assert json.loads(request.content) == {
        "asset": USDC, "amount": "4000000", "chain": "near", "recipient": OWNER,
    }


def test_confirm_works_once(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    answer(client, key, "evet")
    assert answer(client, key, "evet")["action"] == "expired"
    assert len(wallet.sends()) == 1


def test_cancel_sends_nothing(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    assert answer(client, key, "iptal")["action"] == "cancelled"
    assert wallet.sends() == []


def test_each_preview_uses_a_fresh_key_and_differs_from_the_send(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    answer(client, key, "evet")
    keys = [r.headers["Idempotency-Key"] for r in wallet.withdraws()]
    assert len(keys) == 3
    assert len(set(keys)) == 3
    assert json.loads(wallet.previews()[0].content)["dry"] is True


def test_amount_for_one_token(wallet):
    client, _ = make_client()
    data = ask(client, "2,5 USDC'yi cüzdanıma çek")
    assert data["spoken"].startswith("Canlı mod, gerçek para. Çekilecek: 2,5 USDC.")
    assert json.loads(wallet.previews()[0].content)["amount"] == "2500000"


def test_amount_in_words_and_dollars(wallet):
    client, _ = make_client()
    ask(client, "iki buçuk USDC çek")
    ask(client, "2 dolarlık USDC çek")
    amounts = [json.loads(r.content)["amount"] for r in wallet.previews()]
    assert amounts == ["2500000", "2000000"]


def test_more_than_the_balance_is_refused(wallet):
    client, _ = make_client()
    data = ask(client, "4,5 USDC çek")
    assert data["error"] == "live_no_balance"
    assert wallet.withdraws() == []


def test_named_amount_over_the_limit_is_refused(wallet):
    wallet.balances[0].update(balance_raw="10000000", available_raw="10000000")
    client, _ = make_client()
    data = ask(client, "6 USDC çek")
    assert data["error"] == "withdraw_over_limit"
    assert wallet.withdraws() == []


def test_all_is_held_to_the_limit_and_says_so(wallet):
    wallet.balances[0].update(balance_raw="10000000", available_raw="10000000")
    wallet.preview_usd = "5.00"
    client, _ = make_client()
    data = ask(client, "hepsini çek")
    assert data["spoken"].startswith("Hepsi tek seferde çekilemez, tek işlem sınırı bu kadar.")
    assert "Çekilecek: 5 USDC." in data["spoken"]
    assert json.loads(wallet.previews()[0].content)["amount"] == PROOF_CAP


def test_available_is_used_not_the_full_balance(wallet):
    wallet.balances[0]["available_raw"] = "1000000"
    client, _ = make_client()
    ask(client, "hepsini çek")
    assert json.loads(wallet.previews()[0].content)["amount"] == "1000000"


def test_several_tokens_ask_which(wallet):
    wallet.balances.append(
        {"asset_id": SOL, "symbol": "SOL", "decimals": 9, "blockchain": "sol", "price": 100.0,
         "balance_raw": "10000000", "available_raw": "10000000"}
    )
    client, _ = make_client()
    data = ask(client, "paramı cüzdanıma çek")
    assert data["error"] == "withdraw_which"
    assert "SOL, USDC" in data["spoken"]
    assert wallet.withdraws() == []


def test_token_name_picks_it(wallet):
    wallet.balances.append(
        {"asset_id": SOL, "symbol": "SOL", "decimals": 9, "blockchain": "sol", "price": 100.0,
         "balance_raw": "10000000", "available_raw": "10000000"}
    )
    client, _ = make_client()
    assert ask(client, "hepsini SOL çek")["spoken"].count("0,01 SOL") >= 1
    assert json.loads(wallet.previews()[0].content)["asset"] == SOL


def test_same_token_on_two_chains_needs_the_chain(wallet):
    wallet.balances.append(
        {"asset_id": "usdc-near", "symbol": "USDC", "decimals": 6, "blockchain": "near", "price": 1.0,
         "balance_raw": "1000000", "available_raw": "1000000"}
    )
    client, _ = make_client()
    assert ask(client, "hepsini USDC çek")["error"] == "withdraw_which"
    ask(client, "hepsini Base USDC çek")
    assert json.loads(wallet.previews()[0].content)["asset"] == USDC


def test_token_not_held(wallet):
    client, _ = make_client()
    data = ask(client, "hepsini SOL çek")
    assert data["error"] == "withdraw_no_token"
    assert "USDC" in data["spoken"]


def test_near_finds_wnear_and_says_it_arrives_native(wallet):
    wallet.balances[0].update(asset_id="wnear", symbol="wNEAR", decimals=24,
                              balance_raw="1000000000000000000000000",
                              available_raw="1000000000000000000000000")
    wallet.received = "1000000000000000000000000"
    wallet.policy["policy"]["limits"]["per_transaction"]["wnear"] = "2000000000000000000000000"
    client, _ = make_client()
    data = ask(client, "hepsini NEAR çek")
    body = json.loads(wallet.previews()[0].content)
    assert (body["asset"], body["chain"], body["recipient"]) == ("wnear", "near", OWNER)
    assert "wNEAR sahip hesabına native NEAR olarak ulaşır." in data["spoken"]
    assert "Binance'e gönderilemez" not in data["spoken"]


def test_empty_wallet(wallet):
    wallet.balances = []
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "withdraw_empty"


def test_budget_too_low_says_not_today(wallet):
    wallet.remaining = "3.000000"
    client, _ = make_client()
    data = ask(client, "paramı cüzdanıma çek")
    assert data["spoken"] == "Günlük bütçe yetmiyor, bugün çekilemez. Yarın tekrar dene."
    assert "pending" not in data
    assert wallet.sends() == []


def test_budget_warning_says_not_today(wallet):
    wallet.withdraw_warnings = [{"code": "spend_budget_exceeded", "detail": "x"}]
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "withdraw_no_budget"


def test_budget_refused_at_send_says_not_today(wallet):
    wallet.send_replies = [wallet.error(403, "spend_budget_exceeded")]
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    assert answer(client, key, "evet")["error"] == "withdraw_no_budget"


def test_budget_gone_after_confirmation_stops_the_send(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    wallet.remaining = "1.000000"
    assert answer(client, key, "evet")["error"] == "withdraw_no_budget"
    assert wallet.sends() == []


def test_frozen_agent_starts_nothing(wallet):
    wallet.frozen = True
    client, _ = make_client()
    data = ask(client, "paramı cüzdanıma çek")
    assert data["spoken"] == "Ajan dondurulmuş, çözmek için ajanı çöz de."
    assert wallet.withdraws() == []


def test_freezing_after_the_offer_stops_the_send(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    wallet.frozen = True
    assert answer(client, key, "evet")["spoken"].startswith("Ajan dondurulmuş")
    assert wallet.sends() == []


def test_changed_terms_are_read_again(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    wallet.received = "3000000"
    data = answer(client, key, "evet")
    assert data["spoken"].startswith("Teklif değişti, işlem yapılmadı.")
    assert wallet.sends() == []
    assert answer(client, data["pending"], "evet")["action"] == "live_sent"


def test_expired_offer_is_read_again(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    main.pendings.get(key).order.quoted_at -= live.QUOTE_SECONDS + 1
    assert answer(client, key, "evet")["spoken"].startswith("Teklif değişti")
    assert wallet.sends() == []


def test_preview_without_an_amount_is_said_plainly(wallet):
    wallet.received = None
    client, _ = make_client()
    assert "Ulaşacak tutar önizlemede yok." in ask(client, "paramı cüzdanıma çek")["spoken"]


def test_preview_limit_is_said_plainly(wallet):
    wallet.withdraw_error = (429, "withdraw_preview_limit_reached")
    client, _ = make_client()
    assert ask(client, "paramı cüzdanıma çek")["error"] == "withdraw_preview_limit"


def test_lost_answer_retries_with_the_same_key(wallet):
    wallet.send_replies = [httpx.ConnectError("lost")]
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    assert answer(client, key, "evet")["action"] == "live_sent"
    sends = wallet.sends()
    assert sends[0].headers["Idempotency-Key"] == sends[1].headers["Idempotency-Key"]


def test_unknown_result_is_never_resent(wallet):
    wallet.send_replies = [httpx.ConnectError("x"), httpx.ConnectError("x")]
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    data = answer(client, key, "evet")
    assert data["spoken"].startswith("Sonuç belirsiz")
    assert history.recent(1)[0]["status"] == "unknown"


def test_withdrawals_never_touch_the_swap_ledger(wallet):
    client, _ = make_client()
    key = ask(client, "paramı cüzdanıma çek")["pending"]
    answer(client, key, "evet")
    assert live.ledger.total() == 0


def confirm(client):
    return answer(client, ask(client, "paramı cüzdanıma çek")["pending"], "evet")["track"]


def test_following_to_done_with_a_link(wallet):
    client, _ = make_client()
    track_id = confirm(client)
    wallet.status_replies = [status("PROCESSING"), status("SUCCESS", amount_out="3990000", tx_hash="H")]
    assert track(client, track_id)["spoken"].startswith("İşleniyor")
    data = track(client, track_id)
    assert data["spoken"] == (
        "Çekim tamamlandı. 3,99 USDC sahip adresine gitti. İşlem bağlantısı için kopyala düğmesini kullan."
    )
    assert data["proof"].endswith("/H")


def test_done_without_a_delivered_figure_reads_the_sent_amount(wallet):
    client, _ = make_client()
    track_id = confirm(client)
    wallet.status_replies = [status("SUCCESS", tx_hash="H")]
    assert track(client, track_id)["spoken"].startswith("Çekim tamamlandı. 4 USDC")


def test_refund_says_where_the_money_went(wallet):
    client, _ = make_client()
    track_id = confirm(client)
    wallet.status_replies = [status("REFUNDED")]
    assert track(client, track_id)["spoken"].startswith("İade edildi.")


def test_history_records_the_withdrawal(wallet):
    client, _ = make_client()
    track_id = confirm(client)
    wallet.status_replies = [status("SUCCESS", amount_out="3990000", tx_hash="H")]
    track(client, track_id)
    entry = history.recent(1)[0]
    assert (entry["mode"], entry["status"]) == ("withdraw", "done")
    data = ask(client, "son işlemlerimi oku")
    assert ", çekim. 4 USDC verildi, 3,99 USDC alındı, tamamlandı." in data["spoken"]


ENV = {
    "NEAR_INTENTS_AGENT_API_KEY": "naa_test",
    "AGENT_ID": "agent",
    "GRANT_TOKEN": "ngt_test",
}


def run_command(wallet, what, code=""):
    asyncio.run(setup.withdraw_command(ENV, what, code, wallet.transport))


def test_terminal_shows_and_sends_nothing_without_a_code(wallet, capsys):
    run_command(wallet, "hepsini USDC")
    output = capsys.readouterr().out
    assert "Onay kodu:" in output
    assert OWNER in output
    assert "ngt_test" not in output
    assert wallet.sends() == []


def test_terminal_wrong_code_sends_nothing(wallet):
    with pytest.raises(setup.SetupError, match="uymuyor"):
        run_command(wallet, "hepsini USDC", "wrong")
    assert wallet.sends() == []


def test_terminal_sends_with_its_code_to_the_policy_address(wallet, capsys):
    run_command(wallet, "hepsini USDC")
    code = capsys.readouterr().out.split("Onay kodu: ")[1].strip()
    wallet.status_replies = [status("SUCCESS", amount_out="3990000")]
    run_command(wallet, "hepsini USDC", code)
    assert json.loads(wallet.sends()[0].content)["recipient"] == OWNER
    assert "Durum: SUCCESS" in capsys.readouterr().out


def test_terminal_code_belongs_to_one_amount(wallet, capsys):
    run_command(wallet, "hepsini USDC")
    code = capsys.readouterr().out.split("Onay kodu: ")[1].strip()
    with pytest.raises(setup.SetupError, match="uymuyor"):
        run_command(wallet, "2 USDC", code)
    assert wallet.sends() == []


def test_terminal_refuses_any_named_address(wallet):
    with pytest.raises(setup.SetupError, match="withdraw_owner_only"):
        run_command(wallet, "hepsini USDC to bob.near")
    assert wallet.withdraws() == []


def test_terminal_withdrawal_reaches_the_history(wallet, capsys):
    run_command(wallet, "hepsini USDC")
    code = capsys.readouterr().out.split("Onay kodu: ")[1].strip()
    wallet.status_replies = [status("SUCCESS", amount_out="3990000")]
    run_command(wallet, "hepsini USDC", code)
    entry = history.recent(1)[0]
    assert (entry["mode"], entry["status"]) == ("withdraw", "done")


def test_terminal_needs_the_grant():
    with pytest.raises(setup.SetupError, match="GRANT_TOKEN"):
        asyncio.run(setup.withdraw_command({"AGENT_ID": "a", "NEAR_INTENTS_AGENT_API_KEY": "k"}, "x", ""))


def test_terminal_explains_a_refusal(wallet):
    wallet.remaining = "1.000000"
    with pytest.raises(setup.SetupError, match="withdraw_no_budget"):
        run_command(wallet, "hepsini USDC")


def test_the_whole_return_path_inside_the_agent(wallet, monkeypatch):
    """USDC on Base to NEAR, then NEAR to the owner, on the steps of docs/funding.md."""
    tokens = [
        {"asset_id": USDC, "symbol": "USDC", "blockchain": "base", "decimals": 6, "price": 1.0},
        {"asset_id": "wnear", "symbol": "wNEAR", "blockchain": "near", "decimals": 24, "price": 4.0},
    ]

    original = wallet.handle

    def with_tokens(request):
        if request.url.path == "/v1/tokens":
            wallet.requests.append(request)
            return httpx.Response(200, json={"data": tokens})
        return original(request)

    monkeypatch.setattr(live, "transport", httpx.MockTransport(with_tokens))
    wallet.usd = "4.90"
    wallet.amount_out = "1225000000000000000000000"
    wallet.min_out = "1212750000000000000000000"
    client, _ = make_client()
    use_intent(
        monkeypatch, action="swap", amount="4.9", from_token="USDC", from_chain="base",
        to_token="NEAR",
    )
    offer = client.post("/api/ask", json={"text": "x", "live": True}).json()
    assert answer(client, offer["pending"], "evet")["action"] == "live_sent"
    swap = wallet.live_swaps()[0][1]
    assert (swap["origin_asset"], swap["destination_asset"]) == (USDC, "wnear")

    wallet.balances = [
        {"asset_id": "wnear", "symbol": "wNEAR", "decimals": 24, "blockchain": "near", "price": 4.0,
         "balance_raw": "1225000000000000000000000", "available_raw": "1225000000000000000000000"}
    ]
    wallet.policy["policy"]["limits"]["per_transaction"]["wnear"] = "1250000000000000000000000"
    wallet.preview_usd = "4.90"
    wallet.remaining = "5.100000"
    wallet.received = "1225000000000000000000000"
    key = ask(client, "hepsini NEAR çek")["pending"]
    assert answer(client, key, "evet")["action"] == "live_sent"
    body = json.loads(wallet.sends()[0].content)
    assert body == {
        "asset": "wnear", "amount": "1225000000000000000000000", "chain": "near", "recipient": OWNER,
    }
