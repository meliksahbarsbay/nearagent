"""1Click API client: token lookup and quotes."""
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, InvalidOperation

import httpx

log = logging.getLogger("nearagent.oneclick")

DEFAULT_BASE_URL = "https://1click.chaindefuser.com"
DEFAULT_ACCOUNT = "dry-run.near"
DEFAULT_CHAIN = "near"
SLIPPAGE_BPS = 100
QUOTE_TTL_MINUTES = 10
TOKENS_TTL_SECONDS = 300
TIMEOUT_SECONDS = 20
MAX_AMOUNT_CHARS = 40

# 1Click lists native NEAR as wNEAR on the near chain.
SYMBOL_ALIASES = {"NEAR": "WNEAR"}


class QuoteError(Exception):
    """A failure the user should hear. `code` is a key in messages.py."""

    def __init__(self, code: str, status: int = 400, **details):
        super().__init__(code)
        self.code = code
        self.status = status
        self.details = details


def find_token(tokens: list[dict], symbol: str) -> dict:
    """Pick a token by symbol, preferring the NEAR chain."""
    wanted = symbol.strip().upper()
    wanted = SYMBOL_ALIASES.get(wanted, wanted)
    matches = [t for t in tokens if t["symbol"].upper() == wanted]
    if not matches:
        raise QuoteError("unknown_token", 404, symbol=symbol.strip())
    for token in matches:
        if token["blockchain"] == DEFAULT_CHAIN:
            return token
    if len(matches) == 1:
        return matches[0]
    raise QuoteError(
        "ambiguous_token",
        symbol=symbol.strip(),
        chains=", ".join(sorted(t["blockchain"] for t in matches)),
    )


def to_atomic(amount: str, decimals: int) -> str:
    """Convert a human amount such as "1,5" to atomic units."""
    text = amount.strip().replace(",", ".")
    if not text or len(text) > MAX_AMOUNT_CHARS:
        raise QuoteError("invalid_amount")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise QuoteError("invalid_amount") from None
    if not value.is_finite() or value <= 0:
        raise QuoteError("invalid_amount")
    atomic = (value * (Decimal(10) ** decimals)).to_integral_value(rounding=ROUND_DOWN)
    if atomic <= 0:
        raise QuoteError("invalid_amount")
    return str(atomic)


def build_quote_request(
    origin_asset: str, destination_asset: str, amount: str, account: str, dry: bool
) -> dict:
    """Build a quote body. Dry and live share this path: only `dry` differs."""
    deadline = datetime.now(timezone.utc) + timedelta(minutes=QUOTE_TTL_MINUTES)
    return {
        "dry": dry,
        "swapType": "EXACT_INPUT",
        "slippageTolerance": SLIPPAGE_BPS,
        "originAsset": origin_asset,
        "depositType": "INTENTS",
        "destinationAsset": destination_asset,
        "amount": amount,
        "refundTo": account,
        "refundType": "INTENTS",
        "recipient": account,
        "recipientType": "INTENTS",
        "deadline": deadline.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


class OneClick:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = os.getenv("ONECLICK_BASE_URL") or DEFAULT_BASE_URL
        self.jwt = os.getenv("ONECLICK_JWT") or ""
        self.account = os.getenv("INTENTS_ACCOUNT_ID") or DEFAULT_ACCOUNT
        self.transport = transport
        self._tokens: list[dict] = []
        self._tokens_at = 0.0

    def _client(self) -> httpx.AsyncClient:
        headers = {"Authorization": f"Bearer {self.jwt}"} if self.jwt else {}
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
            transport=self.transport,
        )

    async def tokens(self) -> list[dict]:
        if self._tokens and time.monotonic() - self._tokens_at < TOKENS_TTL_SECONDS:
            return self._tokens
        try:
            async with self._client() as client:
                response = await client.get("/v0/tokens")
            response.raise_for_status()
        except httpx.HTTPError as error:
            log.warning("tokens failed: %r", error)
            raise QuoteError("upstream", 502) from None
        self._tokens = response.json()
        self._tokens_at = time.monotonic()
        return self._tokens

    async def quote(self, body: dict) -> dict:
        try:
            async with self._client() as client:
                response = await client.post("/v0/quote", json=body)
        except httpx.HTTPError as error:
            log.warning("quote failed: %r", error)
            raise QuoteError("upstream", 502) from None
        if response.is_error:
            log.warning("quote %s: %s", response.status_code, response.text[:300])
            raise QuoteError("quote_rejected", 502)
        return response.json()
