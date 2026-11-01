"""The Agent API client against a mock transport. Nothing here reaches a network."""
import asyncio
import hashlib
import json
import logging

import httpx
import pytest

from app.agent_api import (
    FINAL_STATUSES,
    PENDING_STATUSES,
    AgentApi,
    AgentApiError,
    AgentApiRequestError,
    GrantRequired,
    create_grant_credential,
    near_owner,
    new_idempotency_key,
    safe_policy,
)

API_KEY = "naa_secret_value"
GRANT = "ngt_secret_value"
USDC = "nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near"
USDT = "nep141:usdt.tether-token.near"


def make_api(status=200, reply=None, grant=GRANT):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={} if reply is None else reply)

    api = AgentApi(API_KEY, grant_token=grant, transport=httpx.MockTransport(handler))
    return api, seen


def run(call):
    return asyncio.run(call)


def test_key_is_sent_as_x_api_key():
    api, seen = make_api(reply={"api_key_id": "a", "tenant_id": "b"})
    run(api.whoami())
    assert str(seen[0].url) == "https://api.agentsonintents.com/v1/whoami"
    assert seen[0].headers["X-API-Key"] == API_KEY
    assert "X-Grant-Token" not in seen[0].headers


@pytest.mark.parametrize("call", ["network", "tokens"])
def test_public_endpoints_send_no_key(call):
    api, seen = make_api()
    run(getattr(api, call)())
    assert "X-API-Key" not in seen[0].headers


def test_quote_needs_no_grant_or_idempotency_key():
    api, seen = make_api()
    run(api.quote_swap("agent", USDC, USDT, "5000000"))
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/agents/agent/swap"
    assert json.loads(request.content) == {
        "origin_asset": USDC,
        "destination_asset": USDT,
        "amount": "5000000",
        "dry": True,
    }
    assert "X-Grant-Token" not in request.headers
    assert "Idempotency-Key" not in request.headers


def test_swap_sends_grant_and_key_and_is_not_dry():
    api, seen = make_api(status=202, reply={"correlation_id": "op_1", "status": "PROCESSING"})
    run(api.swap("agent", USDC, USDT, "5000000", "swap-user-1", "4900000"))
    request = seen[0]
    assert request.headers["X-Grant-Token"] == GRANT
    assert request.headers["Idempotency-Key"] == "swap-user-1"
    body = json.loads(request.content)
    assert "dry" not in body
    assert body["min_amount_out"] == "4900000"


def test_swap_without_grant_sends_nothing():
    api, seen = make_api(grant="")
    with pytest.raises(GrantRequired):
        run(api.swap("agent", USDC, USDT, "1", "swap-user-1"))
    assert seen == []


@pytest.mark.parametrize("key", ["short", "has space in it", "x" * 129])
def test_bad_idempotency_keys_send_nothing(key):
    api, seen = make_api()
    with pytest.raises(ValueError):
        run(api.swap("agent", USDC, USDT, "1", key))
    assert seen == []


def test_new_idempotency_key_is_valid():
    api, seen = make_api()
    run(api.deposit("agent", USDC, new_idempotency_key()))
    assert seen


def test_deposit_leaves_amount_out_when_not_given():
    api, seen = make_api(status=202)
    run(api.deposit("agent", USDC, "deposit-user-1"))
    assert seen[0].url.path == "/v1/agents/agent/deposit"
    assert json.loads(seen[0].content) == {"origin_asset": USDC}
    assert "X-Grant-Token" not in seen[0].headers


def test_generate_and_submit_intent():
    api, seen = make_api()
    run(api.generate_intent({"type": "grant_issue"}, "grant-user-1"))
    run(api.submit_intent("grant_issue", "intent_1", {"signature": "x"}))
    assert seen[0].url.path == "/v1/generate-intent"
    assert seen[0].headers["Idempotency-Key"] == "grant-user-1"
    assert seen[1].url.path == "/v1/submit-intent"
    assert json.loads(seen[1].content) == {
        "type": "grant_issue",
        "correlation_id": "intent_1",
        "signed_data": {"signature": "x"},
    }


def test_status_caps_the_wait():
    api, seen = make_api()
    run(api.status("op_1", wait_ms=90_000))
    assert seen[0].url.params["wait_ms"] == "30000"
    assert seen[0].url.params["correlation_id"] == "op_1"
    assert "refresh" not in seen[0].url.params


def test_balances_use_the_public_source_by_default():
    api, seen = make_api()
    run(api.balances("agent"))
    assert seen[0].url.params["source"] == "public"


def test_agent_id_cannot_change_the_path():
    api, seen = make_api()
    run(api.policy("a/../b"))
    assert seen[0].url.raw_path.startswith(b"/v1/agents/a%2F..%2Fb/policy")


def test_errors_keep_only_stable_fields():
    reply = {
        "errors": [
            {
                "status": "429",
                "code": "rate_limited",
                "layer": "api",
                "title": "Too many",
                "meta": {"retryable": True, "available_at": "2026-11-01T00:00:00Z"},
            }
        ],
        "meta": {"request_id": "req-1"},
    }
    api, _ = make_api(status=429, reply=reply)
    with pytest.raises(AgentApiError) as raised:
        run(api.whoami())
    error = raised.value
    assert (error.status, error.code, error.layer) == (429, "rate_limited", "api")
    assert error.retryable is True
    assert error.available_at == "2026-11-01T00:00:00Z"
    assert error.request_id == "req-1"


def test_retryable_is_false_when_absent():
    reply = {"errors": [{"code": "wallet_busy"}]}
    api, _ = make_api(status=409, reply=reply)
    with pytest.raises(AgentApiError) as raised:
        run(api.whoami())
    assert raised.value.retryable is False


def test_unreadable_error_body_still_raises():
    def handler(request):
        return httpx.Response(502, text="<html>bad gateway</html>")

    api = AgentApi(API_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(AgentApiError) as raised:
        run(api.whoami())
    assert raised.value.code == "unknown_error"


def test_lost_response_keeps_the_key_and_never_retries():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("no route")

    api = AgentApi(API_KEY, grant_token=GRANT, transport=httpx.MockTransport(handler))
    with pytest.raises(AgentApiRequestError) as raised:
        run(api.swap("agent", USDC, USDT, "1", "swap-user-1"))
    assert raised.value.idempotency_key == "swap-user-1"
    assert len(calls) == 1


def test_secrets_stay_out_of_repr_and_logs(caplog):
    caplog.set_level(logging.DEBUG, logger="nearagent.agent_api")

    def handler(request):
        raise httpx.ConnectError("no route")

    api = AgentApi(API_KEY, grant_token=GRANT, transport=httpx.MockTransport(handler))
    with pytest.raises(AgentApiRequestError):
        run(api.swap("agent", USDC, USDT, "1", "swap-user-1"))
    for text in (repr(api), caplog.text):
        assert API_KEY not in text
        assert GRANT not in text


def test_grant_credential_matches_the_docs():
    token, commitment = create_grant_credential()
    assert token.startswith("ngt_")
    assert "=" not in token
    assert commitment == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert create_grant_credential()[0] != token


def test_owner_holds_public_data_only():
    assert near_owner("alice.near", "ed25519:abc") == {
        "type": "near",
        "account_id": "alice.near",
        "public_key": "ed25519:abc",
    }


def test_safe_policy_has_every_required_field_and_pays_only_the_owner():
    policy = safe_policy("alice.near", {USDC: "25000000"}, "50")
    assert set(policy) == {
        "frozen",
        "actions",
        "confidential",
        "owner_approval",
        "assets",
        "limits",
        "max_actions_per_hour",
        "destinations",
        "budget",
        "timelock_ms",
    }
    assert policy["assets"] == [USDC]
    assert policy["destinations"] == {
        "mode": "only",
        "list": [{"action": "withdraw", "chain": "near", "address": "alice.near", "memo": None}],
    }
    assert "transfer" not in policy["actions"]
    assert policy["budget"]["daily_usd"] == "50"


def test_uncertain_is_never_treated_as_final():
    assert "UNCERTAIN" in PENDING_STATUSES
    assert not PENDING_STATUSES & FINAL_STATUSES
