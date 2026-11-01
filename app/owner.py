"""Owner-signed actions. Shared by scripts/owner_setup.py and the page.

The page reaches only control_agent(), which freezes or unfreezes. Neither moves funds, and
the client here gets no grant token. The key stays in the environment and is passed to the
Node signer through its environment, never through arguments.
"""
import asyncio
import json
import os
import subprocess
from pathlib import Path

from app.agent_api import (
    FINAL_STATUSES,
    MAX_WAIT_MS,
    PENDING_STATUSES,
    REVIEW_STATUS,
    AgentApi,
    live_settings,
    near_owner,
    new_idempotency_key,
)

ROOT = Path(__file__).resolve().parent.parent
SIGNER = ROOT / "scripts" / "owner" / "sign_intent.mjs"
DEFAULT_RPC_URL = "https://free.rpc.fastnear.com"
POLL_LIMIT = 40
SIGN_TIMEOUT_SECONDS = 45
# The page should answer soon: past this, it says the result is not known yet.
PAGE_POLLS = 2
PAGE_WAIT_MS = 15_000
CONTROL_KINDS = {"agent_freeze", "agent_unfreeze"}

# One signed action at a time, so a double press cannot race on the key's nonce.
control_lock = asyncio.Lock()


class OwnerError(Exception):
    """A stop the owner should read. The text never holds a secret."""


class OwnerKeyMissing(OwnerError):
    """This computer does not hold the owner's key."""


class ResultPending(OwnerError):
    """The request went out, but its result is not known yet."""


def normalized(policy: dict) -> dict:
    return {**policy, "assets": sorted(policy["assets"])}


def check_intent(generated: dict, owner: dict, policy: dict | None = None) -> None:
    """Stop before signing if the API prepared something other than what was approved."""
    signer = generated.get("signer") or {}
    if signer.get("account_id") != owner["account_id"] or signer.get("public_key") != owner["public_key"]:
        raise OwnerError("API baska bir imzaci istiyor. Imzalanmadi.")
    if policy is None:
        return
    shown = (generated.get("preview") or {}).get("policy") or {}
    wanted = normalized(policy)
    same = bool(shown.get("assets")) and all(
        normalized(shown).get(key) == value for key, value in wanted.items()
    )
    if not same:
        raise OwnerError("API'nin hazirladigi politika onaylanan plana uymuyor. Imzalanmadi.")


def sign(generated: dict, env: dict) -> dict:
    """Run the Node signer."""
    try:
        done = subprocess.run(
            ["node", str(SIGNER)],
            input=json.dumps(generated),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=SIGN_TIMEOUT_SECONDS,
            env={
                **os.environ,
                "OWNER_PRIVATE_KEY": env["OWNER_PRIVATE_KEY"],
                "NEAR_RPC_URL": env.get("NEAR_RPC_URL") or DEFAULT_RPC_URL,
            },
        )
    except subprocess.TimeoutExpired:
        raise OwnerError("Imza zaman asimina ugradi. Hicbir sey gonderilmedi.") from None
    except OSError:
        raise OwnerError("Node bulunamadi. Hicbir sey gonderilmedi.") from None
    if done.returncode != 0:
        raise OwnerError(f"Imza atilamadi: {done.stderr.strip()[:60]}")
    return json.loads(done.stdout)


async def wait_for(
    api: AgentApi, correlation_id: str, limit: int = POLL_LIMIT, wait_ms: int = MAX_WAIT_MS
) -> dict:
    for _ in range(limit):
        status = await api.status(correlation_id, wait_ms=wait_ms)
        if status["status"] in FINAL_STATUSES or status["status"] == REVIEW_STATUS:
            return status
        if status["status"] not in PENDING_STATUSES and status["status"] != "PENDING_SIGNATURE":
            return status
    raise ResultPending(f"Sonuc henuz belli degil. Takip kodu: {correlation_id}")


async def run_intent(
    api: AgentApi,
    intent: dict,
    env: dict,
    owner: dict,
    policy: dict | None = None,
    limit: int = POLL_LIMIT,
    wait_ms: int = MAX_WAIT_MS,
    report=print,
) -> dict:
    generated = await api.generate_intent(intent, new_idempotency_key())
    report(f"API ozeti: {(generated.get('preview') or {}).get('summary')}")
    check_intent(generated, owner, policy)
    # The signer can read the chain and take seconds, so it must not block the page.
    signed = await asyncio.to_thread(sign, generated, env)
    await api.submit_intent(generated["type"], generated["correlation_id"], signed)
    status = await wait_for(api, generated["correlation_id"], limit, wait_ms)
    if status["status"] != "SUCCESS":
        code = status.get("failure_code") or status["status"]
        raise OwnerError(f"Tamamlanmadi: {code}. Takip kodu: {generated['correlation_id']}")
    return status


def owner_ready() -> bool:
    return all(os.getenv(name) for name in ("OWNER_ACCOUNT_ID", "OWNER_PUBLIC_KEY", "OWNER_PRIVATE_KEY"))


async def control_agent(kind: str, transport=None) -> dict:
    """Freeze or unfreeze from the page. The caller has already checked the user's approval."""
    if kind not in CONTROL_KINDS:
        raise ValueError(kind)
    if not owner_ready():
        raise OwnerKeyMissing
    settings = live_settings()
    api = AgentApi(settings.api_key, settings.base_url, transport=transport)
    owner = near_owner(os.environ["OWNER_ACCOUNT_ID"], os.environ["OWNER_PUBLIC_KEY"])
    env = {
        "OWNER_PRIVATE_KEY": os.environ["OWNER_PRIVATE_KEY"],
        "NEAR_RPC_URL": os.getenv("NEAR_RPC_URL") or DEFAULT_RPC_URL,
    }
    async with control_lock:
        return await run_intent(
            api,
            {"type": kind, "agent_id": settings.agent_id},
            env,
            owner,
            limit=PAGE_POLLS,
            wait_ms=PAGE_WAIT_MS,
            report=lambda _: None,
        )
