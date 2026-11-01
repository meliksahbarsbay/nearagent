"""Set up the agent on NEAR mainnet with the owner's key. Only the owner runs this.

    python scripts/owner_setup.py plan                Show the rules. Signs nothing.
    python scripts/owner_setup.py create --onay=KOD   Sign and create the agent.
    python scripts/owner_setup.py grant --onay=KOD    Sign the grant for this backend.
    python scripts/owner_setup.py deposit             Get the address that funds the agent.
    python scripts/owner_setup.py balance             Read the agent's balance.
    python scripts/owner_setup.py freeze              Stop every action now, in one step.
    python scripts/owner_setup.py unfreeze            Show the code that unfreezing needs.
    python scripts/owner_setup.py unfreeze --onay=KOD Sign and let the agent act again.

`plan` saves the exact rules and prints a code. `create` signs only those saved rules, and
only with that code, so what you read is what gets signed. Keys stay in .env, are passed to
the signer through its environment, and are never printed.
"""
import argparse
import asyncio
import hashlib
import json
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
    AgentApi,
    AgentApiError,
    AgentApiRequestError,
    create_grant_credential,
    near_owner,
    new_idempotency_key,
    safe_policy,
)
from app.owner import DEFAULT_RPC_URL, run_intent  # noqa: E402
from app.owner import OwnerError as SetupError  # noqa: E402

ENV_PATH = ROOT / ".env"
PLAN_PATH = ROOT / "scripts" / "owner" / "plan.json"

PER_TRANSACTION_USD = Decimal(5)
DAILY_USD = "10"
MAX_ACTIONS_PER_HOUR = 10
AGENT_NAME = "nearagent"
GRANT_LABEL = "nearagent backend"
GRANT_DAYS = 30
PLAN_MAX_AGE = timedelta(hours=1)
FUNDING_TOKEN = ("USDC", "base")

# Symbol and chain as GET /v1/tokens lists them. USDC appears twice, because the docs fund
# an agent with USDC on Base and the app's quotes default to USDC on NEAR.
WANTED_TOKENS = (
    ("USDC", "near"),
    FUNDING_TOKEN,
    ("wNEAR", "near"),
    ("SOL", "sol"),
    ("ETH", "eth"),
)


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


def pick_token(tokens: list[dict], symbol: str, chain: str) -> dict:
    match = [t for t in tokens if t["symbol"] == symbol and t["blockchain"] == chain]
    if len(match) != 1:
        raise SetupError(f"{symbol} ({chain}) token listesinde tek olarak bulunamadi.")
    return match[0]


def build_plan(owner_account: str, owner_public_key: str, tokens: list[dict]) -> dict:
    picked = [pick_token(tokens, symbol, chain) for symbol, chain in WANTED_TOKENS]
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


def short_code(value: dict) -> str:
    signed = json.dumps(value, sort_keys=True)
    return hashlib.sha256(signed.encode("utf-8")).hexdigest()[:12]


def plan_code(plan: dict) -> str:
    """A short code for the exact owner and rules, for the owner to pass back."""
    return short_code({"owner": plan["owner"], "policy": plan["policy"]})


def unfreeze_code(env: dict) -> str:
    """The same idea for unfreezing: a code for this owner and this agent."""
    return short_code({"owner": owner_from(env), "intent": "agent_unfreeze", "agent": env["AGENT_ID"]})


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


def require(env: dict, *names: str) -> None:
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise SetupError(f".env icinde eksik: {', '.join(missing)}")


def require_owner(env: dict, *extra: str) -> None:
    require(
        env,
        "NEAR_INTENTS_AGENT_API_KEY",
        "OWNER_ACCOUNT_ID",
        "OWNER_PUBLIC_KEY",
        "OWNER_PRIVATE_KEY",
        *extra,
    )


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
    require_owner(env)
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
    require_owner(env, "AGENT_ID")
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


async def deposit_command(
    env: dict, fresh: bool = False, env_path: Path = ENV_PATH, transport=None
) -> dict:
    """Get the one-time address for USDC on Base. It moves nothing by itself."""
    require(env, "NEAR_INTENTS_AGENT_API_KEY", "AGENT_ID")
    api = client_for(env, transport)
    listing = await api.tokens()
    token = pick_token(listing["data"], *FUNDING_TOKEN)
    key = env.get("DEPOSIT_KEY")
    if fresh or not key:
        key = new_idempotency_key()
        # Saved first: one key means one address, so a retry cannot make a second.
        set_key(str(env_path), "DEPOSIT_KEY", key, quote_mode="never")
    deposit = await api.deposit(env["AGENT_ID"], token["asset_id"], key)
    details = deposit.get("details") or {}
    address = details.get("deposit_address")
    if not address:
        raise SetupError("API adres vermedi. Hicbir yere para gonderme.")
    print(f"Ag: Base. Token: USDC. Adres: {address}")
    if details.get("memo"):
        print(f"Not (memo): {details['memo']}")
    minimum = Decimal(details.get("min_amount") or 0).scaleb(-token["decimals"])
    print(f"En az: {minimum.normalize():f} USDC. Son tarih: {details.get('expires_at')}")
    print(f"Takip kodu: {deposit.get('correlation_id')}")
    return deposit


async def balance_command(env: dict, transport=None) -> None:
    require(env, "NEAR_INTENTS_AGENT_API_KEY", "AGENT_ID")
    listing = await client_for(env, transport).balances(env["AGENT_ID"])
    rows = listing.get("balances") or []
    if not rows:
        print("Ajanin bakiyesi yok.")
    for row in rows:
        print(f"{row.get('symbol')} ({row.get('blockchain')}): {row.get('balance')}")


async def control_command(env: dict, kind: str, transport=None) -> None:
    require_owner(env, "AGENT_ID")
    api = client_for(env, transport)
    intent = {"type": kind, "agent_id": env["AGENT_ID"]}
    await run_intent(api, intent, env, owner_from(env))
    print("Ajan donduruldu." if kind == "agent_freeze" else "Ajan cozuldu.")


async def unfreeze_command(env: dict, code: str, transport=None) -> None:
    require_owner(env, "AGENT_ID")
    expected = unfreeze_code(env)
    if not code:
        print("Ajan yeniden islem yapabilir hale gelecek. Politika degismez.")
        print(f"Onay kodu: {expected}")
        return
    if code != expected:
        raise SetupError("Onay kodu uymuyor. Hicbir sey imzalanmadi.")
    await control_command(env, "agent_unfreeze", transport)


async def run(args: argparse.Namespace) -> None:
    assert_env_ignored()
    env = dotenv_values(ENV_PATH)
    if args.command == "plan":
        await plan_command(env)
    elif args.command == "create":
        await create_command(env, args.onay)
    elif args.command == "grant":
        await grant_command(env, args.onay)
    elif args.command == "deposit":
        await deposit_command(env, args.yeni)
    elif args.command == "balance":
        await balance_command(env)
    elif args.command == "freeze":
        await control_command(env, "agent_freeze")
    else:
        await unfreeze_command(env, args.onay)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="nearagent owner setup")
    parser.add_argument(
        "command",
        choices=["plan", "create", "grant", "deposit", "balance", "freeze", "unfreeze"],
    )
    parser.add_argument("--onay", default="")
    parser.add_argument("--yeni", action="store_true", help="deposit: ask for a new address")
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
