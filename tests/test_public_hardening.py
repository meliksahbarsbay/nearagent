"""The public entry point: hidden API docs, security headers, and crashes as JSON."""
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.demo_guard import DemoGuard, Settings
from app.messages import say, say_assets, say_duration, say_history, say_live_status, say_withdraw

HEADERS = ("content-security-policy", "x-content-type-options", "referrer-policy", "permissions-policy")


def crashing_app():
    app = FastAPI()

    @app.post("/api/boom")
    async def boom():
        raise RuntimeError("secret-looking detail")

    @app.get("/page")
    async def page():
        return {"page": True}

    return app


@pytest.fixture
def client():
    return TestClient(DemoGuard(crashing_app(), Settings()))


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"])
def test_api_docs_are_hidden(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"


@pytest.mark.parametrize("path", ["/health", "/page", "/docs"])
def test_security_headers_on_every_response(client, path):
    response = client.get(path)
    for name in HEADERS:
        assert name in response.headers, (path, name)
    assert response.headers["x-content-type-options"] == "nosniff"


def test_csp_keeps_the_page_and_microphone_working(client):
    response = client.get("/page")
    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "connect-src 'self'" in policy
    # index.html styles itself inline, and the recorder uses blob audio.
    assert "style-src 'self' 'unsafe-inline'" in policy
    assert "unsafe-eval" not in policy
    assert "microphone=(self)" in response.headers["permissions-policy"]


def test_hsts_only_over_https(client):
    assert "strict-transport-security" not in client.get("/page").headers
    secure = client.get("/page", headers={"X-Forwarded-Proto": "https"})
    assert secure.headers["strict-transport-security"].startswith("max-age=")


def test_crash_becomes_spoken_json(client):
    response = client.post("/api/boom", json={"lang": "en", "pending": "abc"})
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "server_error"
    assert data["spoken"].startswith("Something went wrong on the server")
    assert data["pending"] == "abc"
    assert "secret-looking" not in response.text


def test_crash_in_turkish(client):
    response = client.post("/api/boom", json={"lang": "tr"})
    assert response.json()["spoken"].startswith("Sunucuda bir hata oldu")


def test_crash_is_logged_without_its_message(client, caplog):
    client.post("/api/boom", json={})
    assert "RuntimeError" in caplog.text
    assert "secret-looking" not in caplog.text


# --- Small English fixes -------------------------------------------------------------

def test_one_asset_is_singular():
    assert say_assets(["a"], "en") == "One asset is allowed."
    assert say_assets(["a", "b"], "en") == "2 assets are allowed."
    assert say_assets(None, "en") == "All assets are allowed."


def test_one_trade_is_singular():
    entry = {"at": "2026-11-09T10:00:00+00:00", "mode": "live", "gave": "1", "gave_symbol": "NEAR",
             "got": "2", "got_symbol": "USDC", "status": "done"}
    assert say_history([entry], "en").startswith("Your last trade. Trade 1:")
    assert say_history([entry, entry], "en").startswith("Last 2 trades.")


def test_one_second_and_one_minute_are_singular():
    assert say_duration(1, "en") == "1 second"
    assert say("unfreeze_wait_one", "en").endswith("Try again in about a minute.")


def test_no_message_names_binance():
    from app.messages import MESSAGES

    for lang in ("tr", "en"):
        for key, text in MESSAGES[lang].items():
            assert "Binance" not in str(text), (lang, key)


class Withdraw:
    symbol = "wNEAR"
    amount_text = "1.5"
    received_text = "1.5"
    usd = Decimal("4")
    left_usd = Decimal("6")
    fee_usd = None
    chain = "near"
    capped = False


def test_withdrawn_wnear_is_spoken_as_near():
    spoken = say_withdraw(Withdraw(), "en", 2)
    assert "Withdrawing: 1.5 NEAR." in spoken
    assert "Arriving: about 1.5 NEAR." in spoken
    done = say_live_status({"state": "done", "amount": "1.5", "symbol": "wNEAR", "withdraw": True}, "en")
    assert done.startswith("Withdrawal done. 1.5 NEAR went to your owner address.")


def test_a_swap_still_says_wnear():
    done = say_live_status({"state": "done", "amount": "1.5", "symbol": "wNEAR"}, "en")
    assert "1.5 wNEAR" in done
