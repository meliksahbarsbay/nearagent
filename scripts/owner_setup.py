"""Set up the agent on NEAR mainnet with the owner's key. Only the owner runs this.

    python scripts/owner_setup.py plan                 Show the rules. Signs nothing.
    python scripts/owner_setup.py create --onay=KOD    Sign and create the agent.
    python scripts/owner_setup.py grant --onay=KOD     Sign the grant for this backend.
    python scripts/owner_setup.py freeze --onay=dondur Stop every action of the agent.
    python scripts/owner_setup.py unfreeze --onay=ac   Let the agent act again.

`plan` saves the exact rules and prints a code. `create` signs only those saved rules, and
only with that code, so what you read is what gets signed. Keys stay in .env, are passed to
the signer through its environment, and are never printed.
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent_api import (  # noqa: E402
    DEFAULT_BASE_URL,
    FINAL_STATUSES,
    PENDING_STATUSES,
    REVIEW_STATUS,
    AgentApi,
    AgentApiError,
    AgentApiRequestError,
    create_grant_credential,
    near_owner,
    new_idempotency_key,
    safe_policy,
)

ENV_PATH = ROOT / ".env"
PLAN_PATH = ROOT / "scripts" / "owner" / "plan.json"
SIGNER = ROOT / "scripts" / "owner" / "sign_intent.mjs"

PER_TRANSACTION_USD = Decimal(5)
DAILY_USD = "10"
MAX_ACTIONS_PER_HOUR = 10
AGENT_NAME = "nearagent"
GRANT_LABEL = "nearagent backend"
GRANT_DAYS = 30
PLAN_MAX_AGE = timedelta(hours=1)
DEFAULT_RPC_URL = "https://free.rpc.fastnear.com"
POLL_LIMIT = 40
SIGN_TIMEOUT_SECONDS = 45

# Symbol and chain as GET /v1/tokens lists them. USDC appears twice, because the docs fund
# an agent with USDC on Base and the app's quotes default to USDC on NEAR.
WANTED_TOKENS = (
    ("USDC", "near"),
    ("USDC", "base"),
    ("wNEAR", "near"),
    ("SOL", "sol"),
    ("ETH", "eth"),
)


class SetupError(Exception):
    """A stop the owner should read. The text never holds a secret."""


def assert_env_ignored(path: Path = ENV_PATH) -> None:
    done = subprocess.run(
        ["git", "check-ignore", "-q", str(path)], cwd=ROOT, capture_output=True
    )
    if done.returncode != 0:
        raise SetupError(".env git disinda degil. Hicbir sey yapilmadi.")


def per_transaction_cap(token: dict) -> str:
    """Convert the dollar cap to atomic units. The API has only per-asset caps."""
    price = token.get("price")
    if price is None:
        raise SetupError(f"{token['symbol']} icin guncel fiyat yok. Biraz sonra yeniden dene.")
    amount = PER_TRANSACTION_USD / Decimal(str(price)) * (Decimal(10) ** token["decimals"])
    return str(amount.to_integral_value(rounding=ROUND_DOWN))


def pick_tokens(tokens: list[dict]) -> list[dict]:
    found = []
    for symbol, chain in WANTED_TOKENS:
        match = [t for t in tokens if t["symbol"] == symbol and t["blockchain"] == chain]
        if len(match) != 1:
            raise SetupError(f"{symbol} ({chain}) token listesinde tek olarak bulunamadi.")
        found.append(match[0])
    return found


def build_plan(owner_account: str, owner_public_key: str, tokens: list[dict]) -> dict:
    picked = pick_tokens(tokens)
    caps = {t["asset_id"]: per_transaction_cap(t) for t in picked}
    policy = safe_policy(owner_account, caps, DAILY_USD, MAX_ACTIONS_PER_HOUR)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "owner": near_owner(owner_account, owner_public_key),
        "policy": policy,
        "summary": [
            {
                "symbol": t["symbol"],
                "chain": t["blockchain"],
                "price": t["price"],
                "cap": str(Decimal(caps[t["asset_id"]]).scaleb(-t["decimals"]).normalize()),
            }
            for t in picked
        ],
    }


def plan_code(plan: dict) -> str:
    """A short code for the exact owner and rules, for the owner to pass back."""
    signed = json.dumps({"owner": plan["owner"], "policy": plan["policy"]}, sort_keys=True)
    return hashlib.sha256(signed.encode("utf-8")).hexdigest()[:12]


def load_plan(code: str, path: Path = PLAN_PATH, now: datetime | None = None) -> dict:
    if not path.exists():
        raise SetupError("Kayitli plan yok. Once plan komutunu calistir.")
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan_code(plan) != code:
        raise SetupError("Onay kodu plana uymuyor. Hicbir sey imzalanmadi.")
    created = datetime.fromisoformat(plan["created_at"])
    if (now or datetime.now(timezone.utc)) - created > PLAN_MAX_AGE:
        raise SetupError("Plan bir saatten eski, fiyatlar degismis olabilir. Plani yenile.")
    return plan


def normalized(policy: dict) -> dict:
    return {**policy, "assets": sorted(policy["assets"])}


def check_intent(generated: dict, owner: dict, policy: dict | None = None) -> None:
    """Stop before signing if the API prepared something other than what was approved."""
    signer = generated.get("signer") or {}
    if signer.get("account_id") != owner["account_id"] or signer.get("public_key") != owner["public_key"]:
        raise SetupError("API baska bir imzaci istiyor. Imzalanmadi.")
    if policy is None:
        return
    shown = (generated.get("preview") or {}).get("policy") or {}
    same = all(normalized(shown).get(key) == value for key, value in normalized(policy).items()) if shown.get("assets") else False
    if not same:
        raise SetupError("API'nin hazirladigi politika onaylanan plana uymuyor. Imzalanmadi.")


def sign(generated: dict, env: dict) -> dict:
    """Run the Node signer. The key travels in its environment, never in arguments."""
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
        raise SetupError("Imza zaman asimina ugradi. Hicbir sey gonderilmedi.") from None
    if done.returncode != 0:
        raise SetupError(f"Imza atilamadi: {done.stderr.strip()[:60]}")
    return json.loads(done.stdout)


async def owner_key_is_live(account_id: str, public_key: str, rpc_url: str, transport=None) -> bool:
    """The delegate needs the key on chain, so an unfunded implicit account fails here."""
    body = {
        "jsonrpc": "2.0",
        "id": "owner",
        "method": "query",
        "params": {
            "request_type": "view_access_key",
            "finality": "final",
            "account_id": account_id,
            "public_key": public_key,
        },
    }
    async with httpx.AsyncClient(timeout=30, transport=transport) as client:
        response = await client.post(rpc_url, json=body)
    result = response.json().get("result") or {}
    return result.get("permission") == "FullAccess"


async def wait_for(api: AgentApi, correlation_id: str) -> dict:
    for _ in range(POLL_LIMIT):
        status = await api.status(correlation_id)
        if status["status"] in FINAL_STATUSES or status["status"] == REVIEW_STATUS:
            return status
        if status["status"] not in PENDING_STATUSES and status["status"] != "PENDING_SIGNATURE":
            return status
    raise SetupError(f"Sonuc henuz belli degil. Takip kodu: {correlation_id}")


async def run_intent(api: AgentApi, intent: dict, env: dict, owner: dict, policy=None) -> dict:
    generated = await api.generate_intent(intent, new_idempotency_key())
    print("API ozeti:", (generated.get("preview") or {}).get("summary"))
    check_intent(generated, owner, policy)
    signed = sign(generated, env)
    await api.submit_intent(generated["type"], generated["correlation_id"], signed)
    status = await wait_for(api, generated["correlation_id"])
    if status["status"] != "SUCCESS":
        code = status.get("failure_code") or status["status"]
        raise SetupError(f"Tamamlanmadi: {code}. Takip kodu: {generated['correlation_id']}")
    return status


def require(env: dict, *names: str) -> None:
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise SetupError(f".env icinde eksik: {', '.join(missing)}")


def client_for(env: dict, transport=None) -> AgentApi:
    base_url = env.get("NEAR_INTENTS_AGENT_API_URL") or DEFAULT_BASE_URL
    return AgentApi(env["NEAR_INTENTS_AGENT_API_KEY"], base_url, transport=transport)


def owner_from(env: dict) -> dict:
    return near_owner(env["OWNER_ACCOUNT_ID"], env["OWNER_PUBLIC_KEY"])


async def plan_command(env: dict, plan_path: Path = PLAN_PATH, transport=None) -> dict:
    require(env, "OWNER_ACCOUNT_ID", "OWNER_PUBLIC_KEY")
    listing = await AgentApi("", transport=transport).tokens()
    plan = build_plan(env["OWNER_ACCOUNT_ID"], env["OWNER_PUBLIC_KEY"], listing["data"])
    plan_path.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    print(f"Sahip adresi: {env['OWNER_ACCOUNT_ID']}")
    print("Izinli islemler: swap ve yalnizca sahip adresine withdraw")
    print(f"Gunluk butce: {DAILY_USD} dolar. Saatte en cok {MAX_ACTIONS_PER_HOUR} islem.")
    print("Islem basina sinir, simdiki fiyatla yaklasik 5 dolar:")
    for row in plan["summary"]:
        print(f"  {row['symbol']} ({row['chain']}): {row['cap']}")
    print(f"Onay kodu: {plan_code(plan)}")
    return plan


async def create_command(env: dict, code: str, env_path: Path = ENV_PATH, transport=None) -> None:
    require(env, "NEAR_INTENTS_AGENT_API_KEY", "OWNER_ACCOUNT_ID", "OWNER_PUBLIC_KEY", "OWNER_PRIVATE_KEY")
    if env.get("AGENT_ID"):
        raise SetupError("AGENT_ID zaten var, ikinci ajan olusturulmadi.")
    plan = load_plan(code)
    owner = owner_from(env)
    if plan["owner"] != owner:
        raise SetupError("Plan baska bir sahip icin. Plani yenile.")
    rpc_url = env.get("NEAR_RPC_URL") or DEFAULT_RPC_URL
    if not await owner_key_is_live(owner["account_id"], owner["public_key"], rpc_url, transport):
        raise SetupError("Sahip hesabi aktif degil. Once adrese NEAR gonder.")
    api = client_for(env, transport)
    await api.whoami()
    network = await api.network()
    if "near" not in network.get("supported_owner_types", []):
        raise SetupError("Bu dagitim NEAR sahiplerini kabul etmiyor.")
    intent = {
        "type": "agent_create",
        "name": AGENT_NAME,
        "owner": owner,
        "policy": plan["policy"],
    }
    status = await run_intent(api, intent, env, owner, plan["policy"])
    set_key(str(env_path), "AGENT_ID", status["agent_id"], quote_mode="never")
    current = await api.policy(status["agent_id"])
    print(f"Ajan hazir. Politika durumu: {current.get('status')}")
    print("AGENT_ID .env dosyasina yazildi.")


async def grant_command(env: dict, code: str, env_path: Path = ENV_PATH, transport=None) -> None:
    require(env, "NEAR_INTENTS_AGENT_API_KEY", "OWNER_ACCOUNT_ID", "OWNER_PUBLIC_KEY", "OWNER_PRIVATE_KEY", "AGENT_ID")
    if env.get("GRANT_ID"):
        raise SetupError("GRANT_ID zaten var, ikinci yetki verilmedi.")
    load_plan(code)
    token, commitment = create_grant_credential()
    # Saved first: the token exists nowhere else. The app ignores it until the grant succeeds.
    set_key(str(env_path), "GRANT_TOKEN_PENDING", token, quote_mode="never")
    expires_at = datetime.now(timezone.utc) + timedelta(days=GRANT_DAYS)
    intent = {
        "type": "grant_issue",
        "agent_id": env["AGENT_ID"],
        "label": GRANT_LABEL,
        "credential": commitment,
        "expires_at": expires_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }
    api = client_for(env, transport)
    status = await run_intent(api, intent, env, owner_from(env))
    grant = status["details"]["grant"]
    set_key(str(env_path), "GRANT_TOKEN", token, quote_mode="never")
    set_key(str(env_path), "GRANT_ID", grant["grant_id"], quote_mode="never")
    print(f"Yetki hazir. Bitis: {grant.get('expires_at')}")
    print("GRANT_TOKEN .env dosyasina yazildi, ekrana basilmadi.")


async def control_command(env: dict, kind: str, transport=None) -> None:
    require(env, "NEAR_INTENTS_AGENT_API_KEY", "OWNER_ACCOUNT_ID", "OWNER_PUBLIC_KEY", "OWNER_PRIVATE_KEY", "AGENT_ID")
    api = client_for(env, transport)
    intent = {"type": kind, "agent_id": env["AGENT_ID"]}
    await run_intent(api, intent, env, owner_from(env))
    print("Ajan donduruldu." if kind == "agent_freeze" else "Ajan yeniden acildi.")


async def run(args: argparse.Namespace) -> None:
    assert_env_ignored()
    env = dotenv_values(ENV_PATH)
    if args.command == "plan":
        await plan_command(env)
    elif args.command == "create":
        await create_command(env, args.onay)
    elif args.command == "grant":
        await grant_command(env, args.onay)
    elif args.command == "freeze":
        if args.onay != "dondur":
            raise SetupError("Dondurmak icin --onay=dondur yaz.")
        await control_command(env, "agent_freeze")
    else:
        if args.onay != "ac":
            raise SetupError("Acmak icin --onay=ac yaz.")
        await control_command(env, "agent_unfreeze")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="nearagent owner setup")
    parser.add_argument("command", choices=["plan", "create", "grant", "freeze", "unfreeze"])
    parser.add_argument("--onay", default="")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except SetupError as error:
        print(f"Durdum: {error}")
        return 1
    except AgentApiError as error:
        print(f"API reddetti: {error.code} (http {error.status}, istek {error.request_id})")
        return 1
    except AgentApiRequestError:
        print("API'den cevap gelmedi. Sonuc belirsiz, tekrar calistirmadan once durumu kontrol et.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
