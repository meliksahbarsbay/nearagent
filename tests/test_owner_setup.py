"""The owner flow against mock transports. No key is real and no network is reached."""
import asyncio
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import dotenv_values

import scripts.owner_setup as setup
from app.agent_api import AgentApiError

OWNER = "a" * 64
PUBLIC_KEY = "ed25519:owner"
PRIVATE_KEY = "ed25519:private-value"
API_KEY = "naa_secret"
TOKENS = [
    {"asset_id": "usdc-near", "symbol": "USDC", "blockchain": "near", "decimals": 6, "price": 1.0},
    {"asset_id": "usdc-base", "symbol": "USDC", "blockchain": "base", "decimals": 6, "price": 1.0},
    {"asset_id": "wnear", "symbol": "wNEAR", "blockchain": "near", "decimals": 24, "price": 4.0},
    {"asset_id": "sol", "symbol": "SOL", "blockchain": "sol", "decimals": 9, "price": 100.0},
    {"asset_id": "eth", "symbol": "ETH", "blockchain": "eth", "decimals": 18, "price": 2000.0},
    {"asset_id": "other", "symbol": "DOGE", "blockchain": "doge", "decimals": 8, "price": 0.1},
]
ENV = {
    "NEAR_INTENTS_AGENT_API_KEY": API_KEY,
    "OWNER_ACCOUNT_ID": OWNER,
    "OWNER_PUBLIC_KEY": PUBLIC_KEY,
    "OWNER_PRIVATE_KEY": PRIVATE_KEY,
}


def plan():
    return setup.build_plan(OWNER, PUBLIC_KEY, TOKENS)


class FakeChain:
    """Answers the RPC and the Agent API, and records every request."""

    def __init__(self, key_live=True, status="SUCCESS", preview_policy=None, signer=None):
        self.requests = []
        self.key_live = key_live
        self.status = status
        self.preview_policy = preview_policy
        self.signer = signer or {"account_id": OWNER, "public_key": PUBLIC_KEY}
        self.transport = httpx.MockTransport(self.handle)

    def paths(self):
        return [request.url.path for request in self.requests]

    def handle(self, request):
        self.requests.append(request)
        path = request.url.path
        if "rpc" in request.url.host:
            result = {"permission": "FullAccess"} if self.key_live else None
            return httpx.Response(200, json={"result": result})
        if path == "/v1/whoami":
            return httpx.Response(200, json={"api_key_id": "a"})
        if path == "/v1/network":
            return httpx.Response(200, json={"supported_owner_types": ["near", "passkey"]})
        if path == "/v1/tokens":
            return httpx.Response(200, json={"data": TOKENS})
        if path == "/v1/generate-intent":
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "type": body["type"],
                    "correlation_id": "intent_1",
                    "agent_id": "agent-1",
                    "signer": {"type": "near", **self.signer},
                    "intent": {"standard": "nep413", "payload": {}},
                    "preview": {
                        "summary": "summary",
                        "policy": self.preview_policy or body.get("policy"),
                    },
                },
            )
        if path == "/v1/submit-intent":
            return httpx.Response(202, json={"status": "PROCESSING"})
        if path == "/v1/status":
            return httpx.Response(
                200,
                json={
                    "status": self.status,
                    "agent_id": "agent-1",
                    "failure_code": None if self.status == "SUCCESS" else "denied",
                    "details": {"grant": {"grant_id": "grant-1", "expires_at": "later"}},
                },
            )
        if path.endswith("/policy"):
            return httpx.Response(200, json={"status": "APPLIED"})
        return httpx.Response(404, json={"errors": [{"code": "not_found"}]})


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Point the script at throwaway files and replace the Node signer."""
    plan_path = tmp_path / "plan.json"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=keep\n", encoding="utf-8")
    monkeypatch.setattr(setup, "PLAN_PATH", plan_path)
    monkeypatch.setattr(setup.load_plan, "__defaults__", (plan_path, None))
    signed = []

    def fake_sign(generated, env):
        signed.append(generated)
        return {"signature": "x"}

    monkeypatch.setattr(setup, "sign", fake_sign)
    return plan_path, env_path, signed


def saved_plan(plan_path):
    made = plan()
    plan_path.write_text(json.dumps(made), encoding="utf-8")
    return setup.plan_code(made)


def test_policy_matches_what_the_owner_asked_for():
    policy = plan()["policy"]
    assert policy["actions"] == ["swap", "withdraw"]
    assert policy["budget"] == {"daily_usd": "10", "weekly_usd": None, "monthly_usd": None}
    assert policy["destinations"] == {
        "mode": "only",
        "list": [{"action": "withdraw", "chain": "near", "address": OWNER, "memo": None}],
    }
    assert policy["frozen"] is False
    assert policy["owner_approval"] is False
    assert policy["assets"] == ["usdc-near", "usdc-base", "wnear", "sol", "eth"]


def test_per_transaction_caps_are_five_dollars_at_current_prices():
    caps = plan()["policy"]["limits"]["per_transaction"]
    assert caps["usdc-near"] == "5000000"
    assert caps["wnear"] == "1250000000000000000000000"
    assert caps["sol"] == "50000000"
    assert caps["eth"] == "2500000000000000"
    assert "other" not in caps


def test_missing_price_stops_the_plan():
    tokens = [{**t, "price": None} if t["asset_id"] == "sol" else t for t in TOKENS]
    with pytest.raises(setup.SetupError):
        setup.build_plan(OWNER, PUBLIC_KEY, tokens)


def test_missing_token_stops_the_plan():
    with pytest.raises(setup.SetupError):
        setup.build_plan(OWNER, PUBLIC_KEY, TOKENS[1:])


def test_plan_code_changes_with_the_rules():
    first = plan()
    changed = json.loads(json.dumps(first))
    changed["policy"]["budget"]["daily_usd"] = "1000"
    assert setup.plan_code(first) != setup.plan_code(changed)


def test_plan_command_saves_rules_and_signs_nothing(workspace, capsys):
    plan_path, _, signed = workspace
    chain = FakeChain()
    asyncio.run(setup.plan_command({**ENV}, plan_path, chain.transport))
    assert plan_path.exists()
    assert chain.paths() == ["/v1/tokens"]
    assert signed == []
    assert PRIVATE_KEY not in capsys.readouterr().out


def test_wrong_code_signs_nothing(workspace):
    plan_path, env_path, signed = workspace
    saved_plan(plan_path)
    chain = FakeChain()
    with pytest.raises(setup.SetupError):
        asyncio.run(setup.create_command({**ENV}, "wrong", env_path, chain.transport))
    assert chain.requests == []
    assert signed == []


def test_old_plan_is_refused(workspace):
    plan_path, _, _ = workspace
    code = saved_plan(plan_path)
    later = datetime.now(timezone.utc) + timedelta(hours=2)
    with pytest.raises(setup.SetupError):
        setup.load_plan(code, plan_path, later)


def test_inactive_owner_account_signs_nothing(workspace):
    plan_path, env_path, signed = workspace
    code = saved_plan(plan_path)
    chain = FakeChain(key_live=False)
    env = {**ENV, "NEAR_RPC_URL": "https://rpc.example"}
    with pytest.raises(setup.SetupError, match="aktif degil"):
        asyncio.run(setup.create_command(env, code, env_path, chain.transport))
    assert signed == []
    assert "/v1/generate-intent" not in chain.paths()


def test_second_agent_is_refused(workspace):
    plan_path, env_path, signed = workspace
    code = saved_plan(plan_path)
    with pytest.raises(setup.SetupError, match="ikinci ajan"):
        asyncio.run(setup.create_command({**ENV, "AGENT_ID": "x"}, code, env_path))
    assert signed == []


def test_create_signs_the_approved_policy_and_saves_the_agent(workspace):
    plan_path, env_path, signed = workspace
    code = saved_plan(plan_path)
    chain = FakeChain()
    env = {**ENV, "NEAR_RPC_URL": "https://rpc.example"}
    asyncio.run(setup.create_command(env, code, env_path, chain.transport))
    assert len(signed) == 1
    generate = next(r for r in chain.requests if r.url.path == "/v1/generate-intent")
    body = json.loads(generate.content)
    assert body["type"] == "agent_create"
    assert body["policy"] == plan()["policy"]
    assert dotenv_values(env_path)["AGENT_ID"] == "agent-1"
    assert dotenv_values(env_path)["OPENAI_API_KEY"] == "keep"


def test_changed_policy_from_the_api_is_never_signed(workspace):
    plan_path, env_path, signed = workspace
    code = saved_plan(plan_path)
    other = json.loads(json.dumps(plan()["policy"]))
    other["budget"]["daily_usd"] = "100000"
    chain = FakeChain(preview_policy=other)
    env = {**ENV, "NEAR_RPC_URL": "https://rpc.example"}
    with pytest.raises(setup.SetupError, match="uymuyor"):
        asyncio.run(setup.create_command(env, code, env_path, chain.transport))
    assert signed == []
    assert "/v1/submit-intent" not in chain.paths()
    assert "AGENT_ID" not in dotenv_values(env_path)


def test_other_signer_is_never_signed_for(workspace):
    plan_path, env_path, signed = workspace
    code = saved_plan(plan_path)
    chain = FakeChain(signer={"account_id": "b" * 64, "public_key": PUBLIC_KEY})
    env = {**ENV, "NEAR_RPC_URL": "https://rpc.example"}
    with pytest.raises(setup.SetupError, match="imzaci"):
        asyncio.run(setup.create_command(env, code, env_path, chain.transport))
    assert signed == []


def test_failed_create_saves_no_agent(workspace):
    plan_path, env_path, _ = workspace
    code = saved_plan(plan_path)
    chain = FakeChain(status="FAILED")
    env = {**ENV, "NEAR_RPC_URL": "https://rpc.example"}
    with pytest.raises(setup.SetupError, match="denied"):
        asyncio.run(setup.create_command(env, code, env_path, chain.transport))
    assert "AGENT_ID" not in dotenv_values(env_path)


def test_grant_saves_the_token_but_sends_only_its_commitment(workspace, capsys):
    plan_path, env_path, signed = workspace
    code = saved_plan(plan_path)
    chain = FakeChain()
    asyncio.run(setup.grant_command({**ENV, "AGENT_ID": "agent-1"}, code, env_path, chain.transport))
    saved = dotenv_values(env_path)
    token = saved["GRANT_TOKEN"]
    assert token.startswith("ngt_")
    assert saved["GRANT_ID"] == "grant-1"
    generate = next(r for r in chain.requests if r.url.path == "/v1/generate-intent")
    assert token not in generate.content.decode()
    assert token not in capsys.readouterr().out
    assert len(signed) == 1


def test_failed_grant_does_not_turn_on_live_mode(workspace):
    plan_path, env_path, _ = workspace
    code = saved_plan(plan_path)
    chain = FakeChain(status="FAILED")
    with pytest.raises(setup.SetupError):
        asyncio.run(setup.grant_command({**ENV, "AGENT_ID": "a"}, code, env_path, chain.transport))
    saved = dotenv_values(env_path)
    assert "GRANT_TOKEN" not in saved
    assert saved["GRANT_TOKEN_PENDING"].startswith("ngt_")


def test_second_grant_is_refused(workspace):
    plan_path, env_path, _ = workspace
    code = saved_plan(plan_path)
    env = {**ENV, "AGENT_ID": "a", "GRANT_ID": "g"}
    with pytest.raises(setup.SetupError, match="ikinci yetki"):
        asyncio.run(setup.grant_command(env, code, env_path))


def test_freeze_sends_the_freeze_intent(workspace):
    _, _, signed = workspace
    chain = FakeChain()
    env = {**ENV, "AGENT_ID": "agent-1"}
    asyncio.run(setup.control_command(env, "agent_freeze", chain.transport))
    generate = next(r for r in chain.requests if r.url.path == "/v1/generate-intent")
    assert json.loads(generate.content) == {"type": "agent_freeze", "agent_id": "agent-1"}
    assert len(signed) == 1


def test_missing_settings_are_named_without_values():
    with pytest.raises(setup.SetupError) as raised:
        setup.require({"OWNER_PRIVATE_KEY": PRIVATE_KEY}, "OWNER_PRIVATE_KEY", "AGENT_ID")
    assert "AGENT_ID" in str(raised.value)
    assert PRIVATE_KEY not in str(raised.value)


def test_api_refusal_is_not_swallowed(workspace):
    plan_path, env_path, _ = workspace
    code = saved_plan(plan_path)

    def handler(request):
        if "rpc" in request.url.host:
            return httpx.Response(200, json={"result": {"permission": "FullAccess"}})
        return httpx.Response(401, json={"errors": [{"code": "invalid_api_key"}]})

    env = {**ENV, "NEAR_RPC_URL": "https://rpc.example"}
    with pytest.raises(AgentApiError):
        asyncio.run(setup.create_command(env, code, env_path, httpx.MockTransport(handler)))


def test_signer_timeout_sends_nothing(monkeypatch):
    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired("node", 45)

    monkeypatch.setattr(setup.subprocess, "run", hang)
    with pytest.raises(setup.SetupError, match="zaman asimi"):
        setup.sign({}, {"OWNER_PRIVATE_KEY": PRIVATE_KEY})


def test_the_real_env_file_is_ignored_by_git():
    setup.assert_env_ignored()


def test_a_tracked_file_is_refused():
    with pytest.raises(setup.SetupError):
        setup.assert_env_ignored(setup.ROOT / "README.md")


@pytest.mark.skipif(
    not (setup.ROOT / "scripts" / "owner" / "node_modules").exists() or not shutil.which("node"),
    reason="node tools are not installed",
)
def test_node_signing_tools():
    done = subprocess.run(
        ["node", "--test"],
        cwd=Path(setup.ROOT / "scripts" / "owner"),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert done.returncode == 0, done.stdout[-1500:]
