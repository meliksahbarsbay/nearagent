"""Freeze and unfreeze from the page. Mock transports, a fake signer, and no real key."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import app.main as main
import app.owner as owner_module
from app.agent_api import AgentApiError, AgentApiRequestError
from app.confirm import code_matches, new_code
from app.owner import OwnerError, OwnerKeyMissing, ResultPending, control_agent
from tests.test_quote import make_client, payload

OWNER = "a" * 64
PUBLIC_KEY = "ed25519:owner"
SETTINGS = {
    "NEAR_INTENTS_AGENT_API_KEY": "naa_test",
    "AGENT_ID": "agent-1",
    "OWNER_ACCOUNT_ID": OWNER,
    "OWNER_PUBLIC_KEY": PUBLIC_KEY,
    "OWNER_PRIVATE_KEY": "ed25519:private-value",
}


@pytest.fixture
def agent(monkeypatch):
    for name, value in SETTINGS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("GRANT_TOKEN", raising=False)


@pytest.fixture
def controls(monkeypatch):
    """Record every signing request the page makes."""
    calls = []

    async def fake_control(kind):
        calls.append(kind)
        return {"status": "SUCCESS"}

    monkeypatch.setattr(main, "control_agent", fake_control)
    return calls


def ask(client, text, pending=None):
    body = {"text": text, "lang": "tr"}
    if pending:
        body["pending"] = pending
    return client.post("/api/ask", json=body).json()


def failing(error):
    async def fail(kind):
        raise error

    return fail


def code_from(data):
    return data["spoken"].split("şu kodu yaz: ")[1].split(".")[0]


def test_freeze_is_one_step(agent, controls):
    client, _ = make_client()
    data = ask(client, "ajanı dondur")
    assert controls == ["agent_freeze"]
    assert data["spoken"].startswith("Ajan donduruldu")
    assert "pending" not in data


def test_freeze_needs_no_parser(agent, controls, monkeypatch):
    async def fail(text):
        raise AssertionError("freeze must not wait for the language model")

    monkeypatch.setattr(main, "parse_intent", fail)
    client, _ = make_client()
    ask(client, "emergency stop")
    assert controls == ["agent_freeze"]


def test_freeze_cuts_through_an_open_quote(agent, controls):
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    data = ask(client, "ajanı dondur", key)
    assert controls == ["agent_freeze"]
    assert "pending" not in data
    assert ask(client, "evet", key)["action"] == "expired"


def test_freeze_cuts_through_an_open_unfreeze(agent, controls):
    client, _ = make_client()
    key = ask(client, "ajanı çöz")["pending"]
    ask(client, "ajanı dondur", key)
    assert controls == ["agent_freeze"]


def test_no_agent_signs_nothing(monkeypatch, controls):
    for name in SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    client, _ = make_client()
    assert ask(client, "ajanı dondur")["spoken"].startswith("Ajan cüzdanı kurulmadı")
    assert controls == []


def test_unfreeze_shows_a_code_and_signs_nothing_yet(agent, controls):
    client, _ = make_client()
    data = ask(client, "ajanı çöz")
    assert controls == []
    assert data["spoken"].startswith("Ajanı çözmek için sahip anahtarıyla imza atacağım.")
    assert "politikası değişmez" in data["spoken"]
    assert len(code_from(data).split()) == 6


def test_correct_code_signs_once(agent, controls):
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    code = code_from(first).replace(" ", "")
    data = ask(client, code, first["pending"])
    assert controls == ["agent_unfreeze"]
    assert data["spoken"].startswith("Ajan çözüldü")
    assert ask(client, code, first["pending"])["action"] == "expired"
    assert controls == ["agent_unfreeze"]


def test_spoken_code_with_spaces_works(agent, controls):
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    ask(client, code_from(first), first["pending"])
    assert controls == ["agent_unfreeze"]


@pytest.mark.parametrize("answer", ["", "   ", "evet", "yes", "onayla", "000000x"])
def test_only_the_code_unfreezes(agent, controls, answer):
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    data = ask(client, answer, first["pending"])
    assert controls == []
    assert data["pending"] == first["pending"]


def test_three_wrong_codes_end_the_attempt(agent, controls):
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    key = first["pending"]
    right = code_from(first).replace(" ", "")
    wrong = "1" * 6 if right != "1" * 6 else "2" * 6
    ask(client, wrong, key)
    ask(client, wrong, key)
    data = ask(client, wrong, key)
    assert data["spoken"].startswith("Kod üç kez yanlış girildi")
    assert ask(client, right, key)["action"] == "expired"
    assert controls == []


def test_no_cancels_unfreeze(agent, controls):
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    assert ask(client, "hayır", first["pending"])["action"] == "cancelled"
    assert controls == []


def test_expired_code_signs_nothing(agent, controls):
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    code = code_from(first).replace(" ", "")
    main.pendings.get(first["pending"]).expires_at = 0
    assert ask(client, code, first["pending"])["action"] == "expired"
    assert controls == []


def test_unfreeze_needs_the_owner_key_before_showing_a_code(agent, controls, monkeypatch):
    monkeypatch.delenv("OWNER_PRIVATE_KEY")
    client, _ = make_client()
    data = ask(client, "ajanı çöz")
    assert data["spoken"].startswith("Sahip anahtarı bu bilgisayarda yok")
    assert "pending" not in data


@pytest.mark.parametrize(
    "error, start",
    [
        (OwnerKeyMissing(), "Sahip anahtarı bu bilgisayarda yok"),
        (ResultPending("x"), "İstek gönderildi, ama sonuç henüz belli değil."),
        (AgentApiRequestError(None), "İstek gönderildi, ama sonuç henüz belli değil."),
        (AgentApiError(409, "wallet_already_frozen"), "Ajan zaten dondurulmuş."),
        (AgentApiError(503, "provider_unavailable"), "İşlem tamamlanmadı"),
        (OwnerError("Imza atilamadi: sign_failed"), "İşlem tamamlanmadı"),
    ],
)
def test_freeze_is_never_claimed_without_proof(agent, monkeypatch, error, start):
    monkeypatch.setattr(main, "control_agent", failing(error))
    client, _ = make_client()
    data = ask(client, "ajanı dondur")
    assert data["spoken"].startswith(start)
    assert "signed" not in data
    assert "provider" not in data["spoken"]


def test_already_active_is_said_on_unfreeze(agent, monkeypatch):
    error = AgentApiError(409, "wallet_already_unfrozen")
    monkeypatch.setattr(main, "control_agent", failing(error))
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    data = ask(client, code_from(first), first["pending"])
    assert data["spoken"].startswith("Ajan zaten çalışır durumda.")


def test_cooldown_says_how_long(agent, monkeypatch):
    ready = (datetime.now(timezone.utc) + timedelta(minutes=7, seconds=10)).isoformat()
    error = AgentApiError(429, "agent_unfreeze_throttled", available_at=ready)
    monkeypatch.setattr(main, "control_agent", failing(error))
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    data = ask(client, code_from(first), first["pending"])
    assert "Yaklaşık 8 dakika sonra" in data["spoken"]


def test_cooldown_without_a_time_uses_the_documented_wait(agent, monkeypatch):
    error = AgentApiError(429, "agent_unfreeze_throttled")
    monkeypatch.setattr(main, "control_agent", failing(error))
    client, _ = make_client()
    first = ask(client, "ajanı çöz")
    assert "Yaklaşık 10 dakika" in ask(client, code_from(first), first["pending"])["spoken"]


def test_page_can_reach_only_freeze_and_unfreeze(agent):
    for kind in ("agent_delete", "policy_update", "grant_issue", "swap"):
        with pytest.raises(ValueError):
            asyncio.run(control_agent(kind))


def test_control_needs_the_owner_key(agent, monkeypatch):
    monkeypatch.delenv("OWNER_PRIVATE_KEY")
    with pytest.raises(OwnerKeyMissing):
        asyncio.run(control_agent("agent_freeze"))


class FakeApi:
    def __init__(self, final="SUCCESS", signer_account=OWNER):
        self.requests = []
        self.final = final
        self.signer_account = signer_account
        self.transport = httpx.MockTransport(self.handle)

    def paths(self):
        return [request.url.path for request in self.requests]

    def handle(self, request):
        self.requests.append(request)
        if request.url.path == "/v1/generate-intent":
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "type": body["type"],
                    "correlation_id": "intent_1",
                    "signer": {"account_id": self.signer_account, "public_key": PUBLIC_KEY},
                    "intent": {"standard": "nep366", "payload": {}},
                    "preview": {"summary": "freeze"},
                },
            )
        if request.url.path == "/v1/submit-intent":
            return httpx.Response(202, json={})
        return httpx.Response(200, json={"status": self.final, "failure_code": None})


@pytest.fixture
def signer(monkeypatch):
    signed = []

    def fake_sign(generated, env):
        signed.append((generated, env))
        return {"signature": "x"}

    monkeypatch.setattr(owner_module, "sign", fake_sign)
    return signed


def test_control_generates_signs_and_submits_in_order(agent, signer):
    fake = FakeApi()
    status = asyncio.run(control_agent("agent_freeze", fake.transport))
    assert status["status"] == "SUCCESS"
    assert fake.paths() == ["/v1/generate-intent", "/v1/submit-intent", "/v1/status"]
    body = json.loads(fake.requests[0].content)
    assert body == {"type": "agent_freeze", "agent_id": "agent-1"}
    assert len(signer) == 1
    assert all("X-Grant-Token" not in r.headers for r in fake.requests)


def test_control_refuses_another_signer(agent, signer):
    fake = FakeApi(signer_account="b" * 64)
    with pytest.raises(OwnerError):
        asyncio.run(control_agent("agent_freeze", fake.transport))
    assert signer == []
    assert "/v1/submit-intent" not in fake.paths()


def test_slow_result_is_reported_as_unknown(agent, signer):
    fake = FakeApi(final="PROCESSING")
    with pytest.raises(ResultPending):
        asyncio.run(control_agent("agent_freeze", fake.transport))
    assert fake.paths().count("/v1/status") == owner_module.PAGE_POLLS


def test_failed_result_is_not_success(agent, signer):
    fake = FakeApi(final="FAILED")
    with pytest.raises(OwnerError):
        asyncio.run(control_agent("agent_unfreeze", fake.transport))


def test_codes_are_six_digits_and_differ():
    codes = {new_code() for _ in range(50)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 1


@pytest.mark.parametrize(
    "text, expected",
    [("123456", True), ("1 2 3 4 5 6", True), ("123457", False), ("", False), ("12345", False)],
)
def test_code_matching(text, expected):
    assert code_matches(text, "123456") is expected
