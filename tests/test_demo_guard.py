import asyncio
import gzip
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.agent_api import agent_ready, live_ready
from app.demo_guard import (
    AGENT_SECRETS,
    MAX_BODY_BYTES,
    MAX_TRACKED_IPS,
    OVERFLOW_KEY,
    BudgetExceeded,
    DailyBudget,
    DemoGuard,
    MeteredTransport,
    RateLimiter,
    Settings,
    client_key,
    protect,
)
from app.intent import parse_intent

ROOT = Path(__file__).resolve().parent.parent
HELP_REPLY = {
    "action": "help", "amount": None, "from_token": None, "from_chain": None,
    "to_token": None, "to_chain": None, "language": "en",
}
SMALL = Settings(per_minute=2, per_day=3)


def chat(usage=None, status=200):
    body = {"choices": [{"message": {"content": json.dumps(HELP_REPLY)}}]}
    if usage is not None:
        body["usage"] = usage
    return httpx.Response(status, json=body)


USAGE = {"prompt_tokens": 1000, "completion_tokens": 100}


def echo_app():
    app = FastAPI()

    @app.post("/api/echo")
    async def echo(data: dict):
        return data

    @app.get("/page")
    async def page():
        return {"page": True}

    return app


def guarded(settings=SMALL):
    return TestClient(DemoGuard(echo_app(), settings))


def scope_with(header=None, peer="10.0.0.1"):
    headers = [(b"x-real-ip", header)] if header else []
    return {"headers": headers, "client": (peer, 1234)}


@pytest.fixture
def public(monkeypatch):
    """The real app behind the guard, with a stand-in language model provider."""
    # Saved here so that the test puts the real parser back afterwards.
    monkeypatch.setattr(main, "parse_intent", main.parse_intent)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("NEAR_AI_API_KEY", raising=False)
    for name in AGENT_SECRETS:
        monkeypatch.setenv(name, "secret-value")
    calls = []

    def handler(request):
        calls.append(request)
        return chat(USAGE)

    def build(settings):
        guard = protect(
            main, settings, make_transport=lambda: httpx.MockTransport(handler)
        )
        return TestClient(guard), calls

    return build


def test_rate_limit_per_minute_then_a_new_minute_opens():
    now = [120.0]
    limiter = RateLimiter(2, 100, clock=lambda: now[0])
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") == ("rate_minute", 60)
    assert limiter.check("b") is None
    now[0] += 60
    assert limiter.check("a") is None


def test_rate_limit_per_day_outlasts_the_minute():
    now = [0.0]
    limiter = RateLimiter(10, 2, clock=lambda: now[0])
    limiter.check("a")
    limiter.check("a")
    now[0] += 120
    window, seconds = limiter.check("a")
    assert window == "rate_day"
    assert seconds == 86400 - 120
    now[0] = 86400
    assert limiter.check("a") is None


def test_flood_of_new_addresses_shares_one_count():
    limiter = RateLimiter(1000, 1, clock=lambda: 0.0)
    limiter._day = 0
    limiter._day_counts = {str(i): 1 for i in range(MAX_TRACKED_IPS)}
    assert limiter.check("new-1") is None
    assert OVERFLOW_KEY in limiter._day_counts
    assert limiter.check("new-2") is not None


def test_client_key_prefers_the_edge_header():
    assert client_key(scope_with(b"203.0.113.7"), "x-real-ip") == "203.0.113.7"


def test_client_key_broken_or_missing_header_uses_the_peer():
    assert client_key(scope_with(b"1.1.1.1, 2.2.2.2"), "x-real-ip") == "10.0.0.1"
    assert client_key(scope_with(), "x-real-ip") == "10.0.0.1"


def test_client_key_ignores_the_header_when_turned_off():
    assert client_key(scope_with(b"203.0.113.7"), "") == "10.0.0.1"


def test_client_key_groups_ipv6_by_network():
    one = client_key(scope_with(b"2001:db8:1:2::1"), "x-real-ip")
    two = client_key(scope_with(b"2001:db8:1:2:ffff::9"), "x-real-ip")
    assert one == two == "2001:db8:1:2::/64"


def test_guard_answers_429_in_the_page_language_and_keeps_the_question():
    client = guarded()
    for _ in range(2):
        assert client.post("/api/echo", json={"lang": "en"}).status_code == 200
    response = client.post("/api/echo", json={"lang": "en", "pending": "abc"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert "one minute" in response.json()["spoken"]
    assert response.json()["pending"] == "abc"


def test_guard_429_is_turkish_by_default():
    client = guarded(Settings(per_minute=1))
    client.post("/api/echo", json={})
    assert "dakikalık" in client.post("/api/echo", json={}).json()["spoken"]


def test_different_edge_ips_have_their_own_limit():
    client = guarded(Settings(per_minute=1))
    first = {"X-Real-IP": "203.0.113.1"}
    second = {"X-Real-IP": "203.0.113.2"}
    assert client.post("/api/echo", json={}, headers=first).status_code == 200
    assert client.post("/api/echo", json={}, headers=first).status_code == 429
    assert client.post("/api/echo", json={}, headers=second).status_code == 200


def test_pages_are_not_limited():
    client = guarded(Settings(per_minute=1))
    for _ in range(3):
        assert client.get("/page").status_code == 200


def test_health_needs_no_limit_budget_or_app():
    client = guarded(Settings(per_minute=1))
    for _ in range(3):
        assert client.get("/health").json() == {"status": "ok"}


def test_body_reaches_the_app_unchanged():
    assert guarded().post("/api/echo", json={"text": "çevir"}).json() == {"text": "çevir"}


def test_oversized_body_is_refused():
    response = guarded().post("/api/echo", json={"text": "x" * (MAX_BODY_BYTES + 1)})
    assert response.status_code == 413
    assert response.json()["spoken"]


@pytest.mark.parametrize("value", [True, 1, "true", "false"])
def test_any_request_for_live_is_refused(value):
    response = guarded().post("/api/echo", json={"live": value, "lang": "en"})
    assert response.status_code == 403
    assert "public demo" in response.json()["spoken"]


def test_live_false_passes():
    assert guarded().post("/api/echo", json={"live": False}).status_code == 200


def test_not_json_still_reaches_the_app():
    response = guarded().post(
        "/api/echo", content=b"[1", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_budget_refuses_at_the_cap_and_resets_next_day():
    now = [0.0]
    budget = DailyBudget(Decimal("0.02"), clock=lambda: now[0])
    assert budget.reserve(Decimal("0.01"))
    assert budget.reserve(Decimal("0.01"))
    assert not budget.reserve(Decimal("0.01"))
    now[0] = 86400
    assert budget.reserve(Decimal("0.01"))


def run_call(handler, budget=None, settings=None):
    budget = budget or DailyBudget(Decimal(1))
    settings = settings or Settings()
    transport = MeteredTransport(httpx.MockTransport(handler), budget, settings)

    async def go():
        async with httpx.AsyncClient(base_url="https://x.test", transport=transport) as client:
            return await client.post("/chat")

    return asyncio.run(go()), budget


def test_charges_the_real_usage_instead_of_the_reservation():
    _, budget = run_call(lambda request: chat(USAGE))
    # 1000 tokens at 5 dollars and 100 tokens at 20 dollars, per million.
    assert budget.spent == Decimal("0.007")


def test_unknown_usage_keeps_the_reservation():
    _, budget = run_call(lambda request: chat())
    assert budget.spent == Settings().reserve_usd


def test_server_error_keeps_the_reservation():
    _, budget = run_call(lambda request: httpx.Response(500, text="down"))
    assert budget.spent == Settings().reserve_usd


def test_refused_call_costs_nothing():
    _, budget = run_call(lambda request: httpx.Response(401, json={"error": "no"}))
    assert budget.spent == 0


def test_failed_connection_keeps_the_reservation():
    def handler(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(httpx.ConnectError):
        run_call(handler, budget := DailyBudget(Decimal(1)))
    assert budget.spent == Settings().reserve_usd


def test_full_budget_never_reaches_the_provider():
    seen = []

    def handler(request):
        seen.append(request)
        return chat(USAGE)

    with pytest.raises(BudgetExceeded):
        run_call(handler, DailyBudget(Decimal(0)))
    assert seen == []


def test_compressed_reply_still_reads_correctly():
    def handler(request):
        body = json.dumps({"usage": USAGE, "ok": True}).encode()
        return httpx.Response(200, content=gzip.compress(body), headers={"Content-Encoding": "gzip"})

    response, budget = run_call(handler)
    assert response.json()["ok"] is True
    assert budget.spent == Decimal("0.007")


def test_settings_defaults(monkeypatch):
    for name in ("DEMO_RATE_PER_MINUTE", "DEMO_DAILY_BUDGET_USD", "DEMO_CLIENT_IP_HEADER"):
        monkeypatch.delenv(name, raising=False)
    assert Settings.from_env() == Settings()


def test_settings_read_the_environment(monkeypatch):
    monkeypatch.setenv("DEMO_RATE_PER_MINUTE", "7")
    monkeypatch.setenv("DEMO_RATE_PER_DAY", "70")
    monkeypatch.setenv("DEMO_DAILY_BUDGET_USD", "2.5")
    monkeypatch.setenv("DEMO_CLIENT_IP_HEADER", "X-Client-IP")
    settings = Settings.from_env()
    assert (settings.per_minute, settings.per_day) == (7, 70)
    assert settings.daily_budget_usd == Decimal("2.5")
    assert settings.ip_header == "x-client-ip"


@pytest.mark.parametrize(
    "name, value",
    [
        ("DEMO_RATE_PER_MINUTE", "many"),
        ("DEMO_RATE_PER_DAY", "0"),
        ("DEMO_DAILY_BUDGET_USD", "lots"),
        ("DEMO_DAILY_BUDGET_USD", "NaN"),
        ("DEMO_DAILY_BUDGET_USD", "-1"),
        ("DEMO_LLM_RESERVE_USD", "0"),
    ],
)
def test_wrong_setting_stops_the_boot(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        Settings.from_env()


def test_protect_removes_every_agent_secret(public):
    public(Settings())
    assert not any(os.getenv(name) for name in AGENT_SECRETS)
    assert not live_ready()
    assert not agent_ready()


def test_public_app_refuses_live_mode_on_every_route(public):
    client, _ = public(Settings())
    for path in ("/api/mode", "/api/quote", "/api/ask"):
        response = client.post(path, json={"live": True, "lang": "en", "text": "x"})
        assert response.status_code == 403


def test_public_freeze_reaches_no_agent(public):
    client, calls = public(Settings())
    response = client.post("/api/ask", json={"text": "ajanı dondur"})
    assert "kurulmadı" in response.json()["spoken"]
    assert "signed" not in response.json()
    assert calls == []


def test_public_sentence_is_charged_to_the_budget(public):
    client, calls = public(Settings())
    response = client.post("/api/ask", json={"text": "hello there"})
    assert response.status_code == 200
    assert response.json()["action"] == "help"
    assert len(calls) == 1


def test_public_sentence_stops_when_the_budget_runs_out(public):
    # The first call costs 0.007 dollars, so nothing is left for a second reservation.
    client, calls = public(Settings(daily_budget_usd=Decimal("0.012")))
    assert client.post("/api/ask", json={"text": "hello"}).status_code == 200
    response = client.post("/api/ask", json={"text": "hello", "lang": "en"})
    assert response.status_code == 503
    assert response.json()["error"] == "no_parser"
    assert response.json()["spoken"]
    assert len(calls) == 1


def test_guard_does_not_change_the_local_app():
    assert main.app.title == "nearagent"
    assert main.parse_intent is parse_intent


def test_public_entry_point_works_with_secrets_set():
    """A separate process, so the real import order is what gets checked."""
    code = (
        "import os, app.public_main as p;"
        "from app.agent_api import live_ready, agent_ready;"
        "from app.owner import owner_ready;"
        "print(live_ready(), agent_ready(), owner_ready(), type(p.app).__name__)"
    )
    env = {**os.environ, **{name: "secret-value" for name in AGENT_SECRETS}}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True
    )
    assert result.stdout.split() == ["False", "False", "False", "DemoGuard"]
