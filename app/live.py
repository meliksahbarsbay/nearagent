"""Real swaps through the Agent API. This is the only app file that can spend.

Every swap passes through here in one order: check the agent is not frozen, quote, read
the terms, take a typed confirmation, check everything again, then send. The app's own
limits come on top of the owner's signed policy, and any doubt stops the swap.
"""
import asyncio
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path

import httpx

from app.agent_api import (
    AgentApi,
    AgentApiError,
    AgentApiRequestError,
    live_settings,
    new_idempotency_key,
)
from app.amounts import find_amount, first_number, named_tokens, says_all, tokenize
from app.history import history
from app.oneclick import (
    CHAIN_NAMES,
    SYMBOL_ALIASES,
    QuoteError,
    find_token,
    parse_amount,
    to_atomic,
    token_amount,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = ROOT / "data" / "live_spend.json"
DEFAULT_MAX_USD = "5"
DEFAULT_MAX_DAILY_USD = "10"
DAY_SECONDS = 86_400
QUOTE_SECONDS = 120
QUOTE_MINUTES = QUOTE_SECONDS // 60
# Prices tick all the time. Past half a percent, the user is asked again.
CHANGE_TOLERANCE = Decimal("0.005")
# Used only if a quote states no minimum, matching the slippage of dry quotes.
DEFAULT_SLIPPAGE = Decimal("0.01")
STATUS_WAIT_MS = 3_000
# The documented link form is unknown, so it lives in one place, and can be set.
DEFAULT_TX_URL = "https://nearblocks.io/txns/{hash}"

# Rules the live swap would fail, as `warnings` lists them on a quote.
BLOCKING_WARNINGS = {
    "policy_action_denied",
    "policy_destination_denied",
    "unsupported_token",
    "invalid_address",
    "insufficient_balance",
    "policy_asset_denied",
    "policy_schedule_denied",
    "spend_price_unavailable",
    "spend_budget_exceeded",
    "policy_limit_exceeded",
    "policy_action_limit_exceeded",
    "policy_usage_unavailable",
}
# Refusals the docs say sent nothing. Any other failure stays counted in the daily total.
PROVEN_REFUSALS = {
    "spend_budget_exceeded",
    "spend_price_unavailable",
    "policy_limit_exceeded",
    "policy_action_limit_exceeded",
    "policy_usage_unavailable",
    "policy_action_denied",
    "policy_not_ready",
    "wallet_busy",
    "wallet_frozen",
}
SPOKEN_REFUSALS = {
    "wallet_frozen": "agent_frozen",
    "insufficient_balance": "live_no_balance",
    "spend_budget_exceeded": "live_budget",
    "policy_limit_exceeded": "live_budget",
    "policy_action_limit_exceeded": "live_budget",
    "spend_price_unavailable": "live_no_price",
    "wallet_busy": "live_busy",
    "route_unavailable": "quote_rejected",
    "provider_refused": "quote_rejected",
    "amount_too_low": "quote_rejected",
    "provider_unavailable": "upstream",
    "unsupported_token": "live_refused",
}

# A sentence that names any address is refused: only the signed address can receive.
ADDRESS_LIKE = re.compile(
    r"\b0x[0-9a-fA-F]{6,}\b|\b[0-9a-fA-F]{32,}\b|\b[\w-]+\.(?:near|testnet|eth|sol)\b"
    r"|\b[1-9A-HJ-NP-Za-km-z]{32,}\b"
)
KNOWN_TICKERS = {"USDC", "USDT", "SOL", "ETH", "BTC", "NEAR", "WNEAR", "XRP", "DOGE", "LTC", "ZEC"}

# Tests replace this. Nothing else ever sets it.
transport: httpx.AsyncBaseTransport | None = None
# One swap at a time: the wallet refuses a second, and limits must be checked in order.
live_lock = asyncio.Lock()


@dataclass
class LiveOrder:
    request: dict
    origin: dict
    destination: dict
    amount: str
    amount_in_text: str
    amount_out: str
    min_out: str
    usd: Decimal
    fee_usd: str | None
    seconds: int | None
    high_fee: bool
    quoted_at: float = field(default_factory=time.monotonic)
    idempotency_key: str = field(default_factory=new_idempotency_key)

    def view(self) -> dict:
        """The terms, shaped as the spoken quote expects them."""
        fee = Decimal(self.fee_usd) if self.fee_usd is not None else None
        return {
            "amountInFormatted": self.amount_in_text,
            "amountOutFormatted": scaled(self.amount_out, self.destination["decimals"]),
            "amountInUsd": str(self.usd),
            "amountOutUsd": str(self.usd - fee) if fee is not None else None,
            "timeEstimate": self.seconds,
        }


@dataclass
class WithdrawOrder:
    """One withdrawal. The recipient comes from the signed policy, never from the user."""

    request: dict
    asset: str
    symbol: str
    decimals: int
    amount: str
    chain: str
    recipient: str
    usd: Decimal
    left_usd: Decimal | None
    received: str | None
    fee_usd: str | None
    capped: bool
    quoted_at: float = field(default_factory=time.monotonic)
    idempotency_key: str = field(default_factory=new_idempotency_key)

    @property
    def amount_text(self) -> str:
        return scaled(self.amount, self.decimals)

    @property
    def received_text(self) -> str | None:
        return scaled(self.received, self.decimals) if self.received else None


@dataclass
class Operation:
    correlation_id: str
    order: LiveOrder | WithdrawOrder
    entry: str = ""


operations: dict[str, Operation] = {}


def scaled(atomic: str, decimals: int) -> str:
    return f"{Decimal(atomic).scaleb(-decimals):f}"


def usd_limit(name: str, default: str) -> Decimal:
    """A broken setting falls back to the default and never lifts the limit."""
    try:
        value = Decimal(os.getenv(name) or default)
    except InvalidOperation:
        return Decimal(default)
    return value if value.is_finite() and value >= 0 else Decimal(default)


def max_live_usd() -> Decimal:
    return usd_limit("MAX_LIVE_USD", DEFAULT_MAX_USD)


def max_daily_usd() -> Decimal:
    return usd_limit("MAX_LIVE_DAILY_USD", DEFAULT_MAX_DAILY_USD)


class SpendLedger:
    """The last 24 hours of live spending, kept on disk so a restart cannot reset it."""

    def path(self) -> Path:
        return Path(os.getenv("LIVE_LEDGER_PATH") or DEFAULT_LEDGER)

    def _read(self) -> list[dict]:
        path = self.path()
        if not path.exists():
            return []
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
            cutoff = time.time() - DAY_SECONDS
            return [e for e in entries if e["at"] > cutoff]
        except (ValueError, KeyError, TypeError):
            # An unreadable total could hide spending, so nothing runs until it is fixed.
            raise QuoteError("live_ledger_broken", 503) from None

    def _write(self, entries: list[dict]) -> None:
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(entries), encoding="utf-8")
        temporary.replace(path)

    def total(self) -> Decimal:
        return sum((Decimal(e["usd"]) for e in self._read()), Decimal(0))

    def reserve(self, key: str, usd: Decimal) -> None:
        self._write([*self._read(), {"key": key, "usd": str(usd), "at": time.time()}])

    def release(self, key: str) -> None:
        self._write([e for e in self._read() if e["key"] != key])


ledger = SpendLedger()


def check_limits(usd: Decimal) -> None:
    limit = max_live_usd()
    if usd > limit:
        raise QuoteError("live_over_limit", 409, usd=str(usd), limit=str(limit))
    left = max_daily_usd() - ledger.total()
    if usd > left:
        raise QuoteError("live_over_daily", 409, left=str(max(left, Decimal(0))))


def client() -> AgentApi:
    settings = live_settings()
    return AgentApi(
        settings.api_key, settings.base_url, settings.grant_token, transport=transport
    )


def refusal(error: AgentApiError) -> QuoteError:
    status = error.status if 400 <= error.status < 500 else 502
    return QuoteError(SPOKEN_REFUSALS.get(error.code, "live_refused"), status)


async def ensure_active(api: AgentApi, agent_id: str) -> dict:
    try:
        data = await api.policy(agent_id)
    except AgentApiError as error:
        raise refusal(error) from None
    except AgentApiRequestError:
        raise QuoteError("agent_read_failed", 502) from None
    policy = data.get("policy")
    if not policy or data.get("status") != "APPLIED" or not data.get("provider_policy_synced"):
        raise QuoteError("policy_not_ready", 409)
    if policy.get("frozen") is not False:
        raise QuoteError("agent_frozen", 409)
    return policy


async def token_list(api: AgentApi) -> list[dict]:
    """The agent's own list, in the shape find_token reads."""
    try:
        listing = await api.tokens()
    except (AgentApiError, AgentApiRequestError):
        raise QuoteError("upstream", 502) from None
    return [
        {
            "assetId": t["asset_id"],
            "symbol": t["symbol"],
            "blockchain": t["blockchain"],
            "decimals": t["decimals"],
            "price": t.get("price"),
        }
        for t in listing["data"]
    ]


def read_quote(data: dict) -> dict:
    """Keep only what is proven readable. A quote that cannot be read cannot be confirmed."""
    quote = data.get("quote") or {}
    amount_out = quote.get("amount_out")
    usd = (data.get("spend") or {}).get("amount_usd")
    if not isinstance(amount_out, str) or not amount_out.isdigit() or int(amount_out) <= 0:
        raise QuoteError("live_quote_unreadable", 502)
    try:
        usd = Decimal(str(usd))
    except InvalidOperation:
        raise QuoteError("live_no_price", 409) from None
    if not usd.is_finite() or usd <= 0:
        raise QuoteError("live_no_price", 409)
    minimum = quote.get("min_amount_out")
    if not isinstance(minimum, str) or not minimum.isdigit():
        floor = (Decimal(amount_out) * (1 - DEFAULT_SLIPPAGE)).to_integral_value(ROUND_DOWN)
        minimum = str(floor)
    seconds = quote.get("time_estimate")
    return {
        "amount_out": amount_out,
        "min_out": minimum,
        "usd": usd,
        "fee_usd": (data.get("fee") or {}).get("amount_usd"),
        "seconds": seconds if isinstance(seconds, int) else None,
        "warnings": {w.get("code") for w in data.get("warnings") or []},
        "owner_approval": bool(data.get("owner_approval")),
    }


async def fresh_quote(api: AgentApi, agent_id: str, order_fields: dict) -> dict:
    try:
        data = await api.quote_swap(
            agent_id,
            order_fields["origin"]["assetId"],
            order_fields["destination"]["assetId"],
            order_fields["amount"],
        )
    except AgentApiError as error:
        raise refusal(error) from None
    except AgentApiRequestError:
        raise QuoteError("upstream", 502) from None
    terms = read_quote(data)
    blocked = terms["warnings"] & BLOCKING_WARNINGS
    if blocked:
        code = sorted(blocked)[0]
        raise QuoteError(SPOKEN_REFUSALS.get(code, "live_refused"), 409)
    return terms


async def prepare_order(
    from_token: str,
    from_chain: str | None,
    to_token: str,
    to_chain: str | None,
    amount: str,
    unit: str = "token",
    side: str = "from",
) -> tuple[LiveOrder, bool, bool]:
    """Quote a swap and check it. Nothing is sent. Returns the two assumed-chain flags."""
    api = client()
    agent_id = live_settings().agent_id
    await ensure_active(api, agent_id)
    if not from_token.strip() or not to_token.strip():
        raise QuoteError("missing_token")
    tokens = await token_list(api)
    origin, origin_assumed = find_token(tokens, from_token, from_chain)
    destination, destination_assumed = find_token(tokens, to_token, to_chain)
    if origin["assetId"] == destination["assetId"]:
        raise QuoteError("same_token")
    atomic = to_atomic(input_amount(amount, unit, side, origin, destination), origin["decimals"])
    fields = {"origin": origin, "destination": destination, "amount": atomic}
    terms = await fresh_quote(api, agent_id, fields)
    check_limits(terms["usd"])
    order = LiveOrder(
        request={
            "from_token": from_token,
            "from_chain": from_chain,
            "to_token": to_token,
            "to_chain": to_chain,
            "amount": amount,
            "unit": unit,
            "side": side,
        },
        origin=origin,
        destination=destination,
        amount=atomic,
        amount_in_text=scaled(atomic, origin["decimals"]),
        amount_out=terms["amount_out"],
        min_out=terms["min_out"],
        usd=terms["usd"],
        fee_usd=terms["fee_usd"],
        seconds=terms["seconds"],
        high_fee="high_fee" in terms["warnings"],
    )
    return order, origin_assumed, destination_assumed


def input_amount(amount: str, unit: str, side: str, origin: dict, destination: dict) -> str:
    """The Agent API takes an exact input only, so every amount becomes one."""
    for token in (origin, destination) if unit == "usd" or side == "to" else ():
        if not token.get("price"):
            raise QuoteError("live_no_price", 409)
    if unit == "usd":
        return token_amount(amount, "usd", origin)
    if side == "to":
        value = parse_amount(amount) * Decimal(str(destination["price"]))
        return token_amount(f"{value:f}", "usd", origin)
    return amount


def moved(before: Decimal, after: Decimal) -> bool:
    return abs(after - before) > before * CHANGE_TOLERANCE


def terms_changed(order: LiveOrder, terms: dict) -> bool:
    if time.monotonic() - order.quoted_at > QUOTE_SECONDS:
        return True
    return moved(Decimal(order.amount_out), Decimal(terms["amount_out"])) or moved(
        order.usd, terms["usd"]
    )


async def send_swap(api: AgentApi, agent_id: str, order: LiveOrder) -> dict | None:
    """Send once, and once more with the same key if the answer was lost. None means unknown."""
    request = (
        agent_id,
        order.origin["assetId"],
        order.destination["assetId"],
        order.amount,
        order.idempotency_key,
        order.min_out,
    )
    for _ in range(2):
        try:
            return await api.swap(*request)
        except AgentApiRequestError:
            continue
        except AgentApiError as error:
            if error.retryable or error.status >= 500:
                continue
            if error.code in PROVEN_REFUSALS:
                ledger.release(order.idempotency_key)
            raise refusal(error) from None
    return None


async def execute_order(order: LiveOrder) -> str | None:
    """Run a confirmed order. Returns a tracking id, or None if the terms changed.

    The caller has taken the user's typed confirmation. Nothing is sent unless the agent
    is still active, the terms still hold, and the limits still allow it.
    """
    api = client()
    agent_id = live_settings().agent_id
    fields = {
        "origin": order.origin,
        "destination": order.destination,
        "amount": order.amount,
    }
    async with live_lock:
        await ensure_active(api, agent_id)
        terms = await fresh_quote(api, agent_id, fields)
        if terms_changed(order, terms):
            return None
        check_limits(terms["usd"])
        # Counted before sending: a crash must never leave spending uncounted.
        ledger.reserve(order.idempotency_key, terms["usd"])
        entry = history.add(
            mode="live",
            gave=order.amount_in_text,
            gave_symbol=order.origin["symbol"],
            got=scaled(terms["amount_out"], order.destination["decimals"]),
            got_symbol=order.destination["symbol"],
            status="processing",
            ref=None,
        )
        try:
            result = await send_swap(api, agent_id, order)
        except QuoteError:
            history.update(entry, status="refused")
            raise
    if not result or not result.get("correlation_id"):
        history.update(entry, status="unknown")
        raise QuoteError("live_unknown", 502)
    history.update(entry, ref=result["correlation_id"])
    track = secrets.token_urlsafe(16)
    operations[track] = Operation(result["correlation_id"], order, entry)
    return track


def withdraw_target(policy: dict) -> tuple[str, str]:
    """The one address the owner signed. With no single answer, nothing moves."""
    rules = policy.get("destinations") or {}
    entries = [e for e in rules.get("list") or [] if e.get("action") == "withdraw"]
    if "withdraw" not in (policy.get("actions") or []):
        raise QuoteError("withdraw_no_target", 409)
    if rules.get("mode") != "only" or len(entries) != 1:
        raise QuoteError("withdraw_no_target", 409)
    chain, address = entries[0].get("chain"), entries[0].get("address")
    if not chain or not address:
        raise QuoteError("withdraw_no_target", 409)
    owner = os.getenv("OWNER_ACCOUNT_ID")
    if owner and owner != address:
        raise QuoteError("withdraw_no_target", 409)
    return chain, address


def available(row: dict) -> int:
    raw = row.get("available_raw") if row.get("available_raw") is not None else row.get("balance_raw")
    return int(raw or 0)


def row_names(row: dict) -> set[str]:
    symbol = str(row.get("symbol", "")).upper()
    plain = {alias: name for name, alias in SYMBOL_ALIASES.items()}.get(symbol)
    return {symbol, plain} if plain else {symbol}


def holdings_text(rows: list[dict]) -> str:
    return ", ".join(sorted({str(row.get("symbol")) for row in rows}))


def pick_row(rows: list[dict], text: str) -> dict:
    """Find the one balance a sentence means. A wrong guess here would move the wrong token."""
    if not rows:
        raise QuoteError("withdraw_empty", 409)
    named = named_tokens(text)
    matches = [row for row in rows if row_names(row) & named]
    if any(word.isalpha() and word.upper() in KNOWN_TICKERS for word in tokenize(text)) and not matches:
        raise QuoteError("withdraw_no_token", 409, tokens=holdings_text(rows))
    choices = matches or rows
    words = set(tokenize(text))
    on_chain = [
        row for row in choices
        if row.get("blockchain") in words or CHAIN_NAMES.get(row.get("blockchain"), "").lower() in words
    ]
    choices = on_chain or choices
    if len(choices) > 1:
        raise QuoteError("withdraw_which", 409, tokens=holdings_text(choices))
    return choices[0]


def chosen_amount(text: str, lang: str, row: dict) -> tuple[int, bool]:
    """Atomic amount and whether the user asked for everything."""
    decimals = row["decimals"]
    found = find_amount(text, lang, row_names(row))
    if found and found.usd:
        token = {"symbol": row.get("symbol"), "price": row.get("price")}
        return int(to_atomic(token_amount(found.value, "usd", token), decimals)), False
    if found:
        return int(to_atomic(found.value, decimals)), False
    # A bare "5 çek" must never become "everything", so any number wins over the default.
    number = first_number(text, lang)
    if number is not None and not says_all(text):
        return int(to_atomic(number, decimals)), False
    return available(row), True


def transaction_cap(policy: dict, asset: str) -> int | None:
    cap = ((policy.get("limits") or {}).get("per_transaction") or {}).get(asset)
    return int(cap) if cap else None


async def read_balances(api: AgentApi, agent_id: str) -> list[dict]:
    try:
        listing = await api.balances(agent_id)
    except (AgentApiError, AgentApiRequestError):
        raise QuoteError("agent_read_failed", 502) from None
    return [row for row in listing.get("balances") or [] if available(row) > 0]


def withdraw_refusal(error: AgentApiError) -> QuoteError:
    if error.code == "spend_budget_exceeded":
        return QuoteError("withdraw_no_budget", 409)
    if error.code == "policy_limit_exceeded":
        return QuoteError("withdraw_over_limit", 409)
    if error.code == "withdraw_preview_limit_reached":
        return QuoteError("withdraw_preview_limit", 429)
    return refusal(error)


async def preview_withdraw(api: AgentApi, agent_id: str, fields: dict) -> dict:
    """Ask for a preview under a fresh key. The same key would replay an old answer."""
    try:
        data = await api.withdraw(
            agent_id,
            fields["asset"],
            fields["amount"],
            fields["chain"],
            fields["recipient"],
            new_idempotency_key(),
            dry=True,
        )
    except AgentApiError as error:
        raise withdraw_refusal(error) from None
    except AgentApiRequestError:
        raise QuoteError("upstream", 502) from None
    codes = {w.get("code") for w in data.get("warnings") or []}
    if "spend_budget_exceeded" in codes:
        raise QuoteError("withdraw_no_budget", 409)
    if "policy_limit_exceeded" in codes:
        raise QuoteError("withdraw_over_limit", 409)
    blocked = codes & BLOCKING_WARNINGS
    if blocked:
        raise QuoteError(SPOKEN_REFUSALS.get(sorted(blocked)[0], "live_refused"), 409)
    spend = data.get("spend") or {}
    if spend.get("amount_usd") is None:
        raise QuoteError("live_no_price", 409)
    usd = Decimal(str(spend["amount_usd"]))
    remaining = ((spend.get("budget") or {}).get("daily") or {}).get("remaining_usd")
    left = Decimal(str(remaining)) if remaining is not None else None
    if left is not None and usd > left:
        raise QuoteError("withdraw_no_budget", 409)
    received = (data.get("quote") or {}).get("amount_out")
    return {
        "usd": usd,
        "left": left - usd if left is not None else None,
        "received": received if isinstance(received, str) and received.isdigit() else None,
        "fee_usd": (data.get("fee") or {}).get("amount_usd"),
    }


async def plan_withdraw(api: AgentApi, agent_id: str, text: str, lang: str) -> WithdrawOrder:
    """Read what would leave and where it would go. Nothing is sent here."""
    if ADDRESS_LIKE.search(text):
        raise QuoteError("withdraw_owner_only", 403)
    policy = await ensure_active(api, agent_id)
    chain, recipient = withdraw_target(policy)
    row = pick_row(await read_balances(api, agent_id), text)
    amount, wants_all = chosen_amount(text, lang, row)
    if amount <= 0:
        raise QuoteError("invalid_amount")
    if amount > available(row):
        raise QuoteError("live_no_balance", 409)
    cap = transaction_cap(policy, row["asset_id"])
    capped = cap is not None and amount > cap
    if capped and not wants_all:
        raise QuoteError("withdraw_over_limit", 409)
    amount = min(amount, cap) if capped else amount
    fields = {"asset": row["asset_id"], "amount": str(amount), "chain": chain, "recipient": recipient}
    terms = await preview_withdraw(api, agent_id, fields)
    return WithdrawOrder(
        request={"text": text},
        asset=row["asset_id"],
        symbol=row["symbol"],
        decimals=row["decimals"],
        amount=str(amount),
        chain=chain,
        recipient=recipient,
        usd=terms["usd"],
        left_usd=terms["left"],
        received=terms["received"],
        fee_usd=terms["fee_usd"],
        capped=capped,
    )


def withdraw_changed(order: WithdrawOrder, terms: dict) -> bool:
    if time.monotonic() - order.quoted_at > QUOTE_SECONDS:
        return True
    if moved(order.usd, terms["usd"]):
        return True
    if order.received and terms["received"]:
        return moved(Decimal(order.received), Decimal(terms["received"]))
    return bool(order.received) != bool(terms["received"])


async def send_withdraw(api: AgentApi, agent_id: str, order: WithdrawOrder) -> dict | None:
    """Send once, and again with the same key if the answer was lost. None means unknown."""
    for _ in range(2):
        try:
            return await api.withdraw(
                agent_id,
                order.asset,
                order.amount,
                order.chain,
                order.recipient,
                order.idempotency_key,
            )
        except AgentApiRequestError:
            continue
        except AgentApiError as error:
            if error.retryable or error.status >= 500:
                continue
            raise withdraw_refusal(error) from None
    return None


async def execute_withdraw(order: WithdrawOrder) -> str | None:
    """Run a confirmed withdrawal. Returns a tracking id, or None if the terms changed."""
    api = client()
    agent_id = live_settings().agent_id
    fields = {
        "asset": order.asset,
        "amount": order.amount,
        "chain": order.chain,
        "recipient": order.recipient,
    }
    async with live_lock:
        policy = await ensure_active(api, agent_id)
        # The target is read again: a confirmed order never outlives a changed policy.
        if withdraw_target(policy) != (order.chain, order.recipient):
            raise QuoteError("withdraw_no_target", 409)
        terms = await preview_withdraw(api, agent_id, fields)
        if withdraw_changed(order, terms):
            return None
        entry = history.add(
            mode="withdraw",
            gave=order.amount_text,
            gave_symbol=order.symbol,
            got=order.received_text or order.amount_text,
            got_symbol=order.symbol,
            status="processing",
            ref=None,
        )
        try:
            result = await send_withdraw(api, agent_id, order)
        except QuoteError:
            history.update(entry, status="refused")
            raise
    if not result or not result.get("correlation_id"):
        history.update(entry, status="unknown")
        raise QuoteError("live_unknown", 502)
    history.update(entry, ref=result["correlation_id"])
    track = secrets.token_urlsafe(16)
    operations[track] = Operation(result["correlation_id"], order, entry)
    return track


def proof_of(details: dict) -> tuple[str | None, str]:
    """A link when there is a transaction hash, otherwise the intent hash itself."""
    tx_hash = details.get("destination_tx_hash") or details.get("tx_hash")
    if tx_hash:
        url = os.getenv("EXPLORER_TX_URL") or DEFAULT_TX_URL
        return url.replace("{hash}", tx_hash), "proof"
    return details.get("intent_hash"), "proof_id"


STATES = {
    "PROCESSING": "processing",
    "QUEUED": "processing",
    "PENDING_APPROVAL": "approval",
    "UNCERTAIN": "uncertain",
    "NEEDS_REVIEW": "review",
    "SUCCESS": "done",
    "REFUNDED": "refunded",
    "FAILED": "failed",
}
FINAL_STATES = {"done", "refunded", "failed", "review"}


async def read_operation(track: str) -> dict:
    """The swap's state for the page. A lost answer simply reads as still processing."""
    operation = operations.get(track)
    if operation is None:
        return {"state": "lost", "final": True}
    order = operation.order
    try:
        status = await client().status(operation.correlation_id, wait_ms=STATUS_WAIT_MS)
    except (AgentApiError, AgentApiRequestError):
        return {"state": "processing", "final": False}
    state = STATES.get(status.get("status"), "processing")
    details = status.get("details") or {}
    withdrawing = isinstance(order, WithdrawOrder)
    symbol = order.symbol if withdrawing else order.destination["symbol"]
    decimals = order.decimals if withdrawing else order.destination["decimals"]
    view = {"state": state, "final": state in FINAL_STATES, "symbol": symbol, "withdraw": withdrawing}
    if details.get("amount_out"):
        view["amount"] = scaled(details["amount_out"], decimals)
    elif withdrawing and state == "done":
        view["amount"] = order.amount_text
    if state == "done":
        view["proof"], view["proof_key"] = proof_of(details)
    if state == "failed":
        view["never_ran"] = bool(details.get("never_executed") or details.get("never_submitted"))
        if view["never_ran"] and not withdrawing:
            ledger.release(order.idempotency_key)
    if state != "processing":
        history.update(
            operation.entry,
            status=state,
            got=view.get("amount"),
            ref=view.get("proof"),
        )
    if view["final"]:
        operations.pop(track, None)
    return view
