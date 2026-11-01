"""Protection for the public demo. Local runs of app.main do not use this file.

It adds a request limit per IP, a daily spending cap on language model calls, and it keeps
live mode off. All counters live in one process's memory, so the demo must run with one
worker and one replica, and a restart sets them back to zero.
"""
import ipaddress
import json
import logging
import math
import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

import httpx

from app.intent import ParserUnavailable

log = logging.getLogger("nearagent.demo_guard")

SECONDS_PER_MINUTE = 60
SECONDS_PER_DAY = 86400
TOKENS_PER_PRICE_UNIT = Decimal(1_000_000)
MAX_BODY_BYTES = 4096
MAX_TRACKED_IPS = 100_000
OVERFLOW_KEY = "overflow"
IPV6_NETWORK_BITS = 64

# Without these the app cannot read, sign for, or act as an agent.
AGENT_SECRETS = (
    "NEAR_INTENTS_AGENT_API_KEY",
    "AGENT_API_KEY",
    "AGENT_ID",
    "GRANT_ID",
    "GRANT_TOKEN",
    "OWNER_ACCOUNT_ID",
    "OWNER_PUBLIC_KEY",
    "OWNER_PRIVATE_KEY",
)

MESSAGES = {
    "tr": {
        "rate_minute": "Bir dakikalık istek sınırına ulaştın. Yaklaşık {seconds} saniye sonra yeniden dene.",
        "rate_day": "Bugünlük istek sınırına ulaştın. Yarın yeniden dene.",
        "live_disabled": "Bu herkese açık demoda canlı mod kapalı. Deneme modunda devam edebilirsin, para hareket etmez.",
        "too_large": "İstek çok uzun. Daha kısa yaz.",
    },
    "en": {
        "rate_minute": "You reached the limit for one minute. Try again in about {seconds} seconds.",
        "rate_day": "You reached today's request limit. Try again tomorrow.",
        "live_disabled": "Live mode is off in this public demo. You can continue in dry mode, so no funds move.",
        "too_large": "That request is too long. Try a shorter one.",
    },
}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name) or str(default)
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number") from None
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def env_money(name: str, default: str, minimum: Decimal = Decimal(0)) -> Decimal:
    raw = os.getenv(name) or default
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"{name} must be a number") from None
    if not value.is_finite() or value < minimum:
        raise ValueError(f"{name} must be a number of at least {minimum}")
    return value


@dataclass(frozen=True)
class Settings:
    per_minute: int = 20
    per_day: int = 200
    daily_budget_usd: Decimal = Decimal(1)
    input_usd_per_mtok: Decimal = Decimal(5)
    output_usd_per_mtok: Decimal = Decimal(20)
    reserve_usd: Decimal = Decimal("0.01")
    ip_header: str = "x-real-ip"

    @classmethod
    def from_env(cls) -> "Settings":
        """A wrong value stops the boot, so a typo cannot leave the demo unprotected."""
        return cls(
            per_minute=env_int("DEMO_RATE_PER_MINUTE", cls.per_minute),
            per_day=env_int("DEMO_RATE_PER_DAY", cls.per_day),
            daily_budget_usd=env_money("DEMO_DAILY_BUDGET_USD", str(cls.daily_budget_usd)),
            input_usd_per_mtok=env_money("DEMO_LLM_INPUT_USD_PER_MTOK", str(cls.input_usd_per_mtok)),
            output_usd_per_mtok=env_money("DEMO_LLM_OUTPUT_USD_PER_MTOK", str(cls.output_usd_per_mtok)),
            reserve_usd=env_money("DEMO_LLM_RESERVE_USD", str(cls.reserve_usd), Decimal("0.0001")),
            ip_header=(os.getenv("DEMO_CLIENT_IP_HEADER", cls.ip_header)).strip().lower(),
        )


class RateLimiter:
    """Fixed windows in UTC. A burst across a minute boundary can reach twice the limit."""

    def __init__(self, per_minute: int, per_day: int, clock: Callable[[], float] = time.time):
        self.per_minute = per_minute
        self.per_day = per_day
        self.clock = clock
        self._minute = -1
        self._day = -1
        self._minute_counts: dict[str, int] = {}
        self._day_counts: dict[str, int] = {}

    def check(self, key: str) -> tuple[str, int] | None:
        """Count one request. Return the window that refused it and the seconds left in it."""
        now = self.clock()
        minute = int(now // SECONDS_PER_MINUTE)
        day = int(now // SECONDS_PER_DAY)
        if minute != self._minute:
            self._minute, self._minute_counts = minute, {}
        if day != self._day:
            self._day, self._day_counts = day, {}
        # A flood of new addresses shares one count, so memory stays bounded.
        if key not in self._day_counts and len(self._day_counts) >= MAX_TRACKED_IPS:
            key = OVERFLOW_KEY
        if self._day_counts.get(key, 0) >= self.per_day:
            return "rate_day", math.ceil(SECONDS_PER_DAY - now % SECONDS_PER_DAY)
        if self._minute_counts.get(key, 0) >= self.per_minute:
            return "rate_minute", math.ceil(SECONDS_PER_MINUTE - now % SECONDS_PER_MINUTE)
        self._minute_counts[key] = self._minute_counts.get(key, 0) + 1
        self._day_counts[key] = self._day_counts.get(key, 0) + 1
        return None


class DailyBudget:
    """A total in dollars, across all providers, reset at midnight UTC.

    Each call reserves money before it starts, so many calls at once cannot pass the cap.
    """

    def __init__(self, limit: Decimal, clock: Callable[[], float] = time.time):
        self.limit = limit
        self.clock = clock
        self.spent = Decimal(0)
        self._day = -1

    def _roll(self) -> None:
        day = int(self.clock() // SECONDS_PER_DAY)
        if day != self._day:
            self._day, self.spent = day, Decimal(0)

    def has_room(self, amount: Decimal) -> bool:
        self._roll()
        return self.spent + amount <= self.limit

    def reserve(self, amount: Decimal) -> bool:
        if not self.has_room(amount):
            return False
        self.spent += amount
        return True

    def settle(self, reserved: Decimal, actual: Decimal) -> None:
        self._roll()
        self.spent = max(Decimal(0), self.spent - reserved + actual)


class BudgetExceeded(httpx.TransportError):
    """Raised before sending, so the provider is never reached."""


class MeteredTransport(httpx.AsyncBaseTransport):
    """Charge each provider call to the budget, from the usage in its reply.

    A call with an unknown cost keeps its reservation: a timeout or a server error may
    still be billed. A 4xx is a refusal, so nothing is charged.
    """

    def __init__(self, inner: httpx.AsyncBaseTransport, budget: DailyBudget, settings: Settings):
        self.inner = inner
        self.budget = budget
        self.settings = settings

    def cost(self, response: httpx.Response) -> Decimal | None:
        if 400 <= response.status_code < 500:
            return Decimal(0)
        try:
            usage = response.json()["usage"]
            tokens_in = Decimal(usage["prompt_tokens"])
            tokens_out = Decimal(usage["completion_tokens"])
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return None
        total = tokens_in * self.settings.input_usd_per_mtok
        total += tokens_out * self.settings.output_usd_per_mtok
        return total / TOKENS_PER_PRICE_UNIT

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        reserved = self.settings.reserve_usd
        if not self.budget.reserve(reserved):
            raise BudgetExceeded("daily budget reached", request=request)
        response = await self.inner.handle_async_request(request)
        raw = b"".join([chunk async for chunk in response.stream])
        await response.aclose()
        # A new response, because the raw stream of the first one has been read.
        copy = httpx.Response(response.status_code, headers=response.headers, content=raw)
        actual = self.cost(copy)
        if actual is not None:
            self.budget.settle(reserved, actual)
        return copy


def client_key(scope: dict, header: str) -> str:
    """The limit key for a request. A missing or broken header falls back to the peer."""
    peer = (scope.get("client") or ("unknown",))[0]
    wanted = header.encode("latin-1")
    raw = next((value for name, value in scope["headers"] if header and name == wanted), b"")
    for text in (raw.decode("latin-1").strip(), peer):
        try:
            address = ipaddress.ip_address(text)
        except ValueError:
            continue
        if address.version == 6:
            # One home connection owns a whole /64, so single addresses cost nothing to change.
            return str(ipaddress.ip_network(f"{address}/{IPV6_NETWORK_BITS}", strict=False))
        return str(address)
    return peer


def read_language(scope: dict, data: dict) -> str:
    if data.get("lang") in MESSAGES:
        return data["lang"]
    accepted = dict(scope["headers"]).get(b"accept-language", b"")
    return "en" if accepted[:2].lower() == b"en" else "tr"


class DemoGuard:
    """Sits in front of the app. Only /api/ paths are limited, and /health answers here."""

    def __init__(self, app, settings: Settings, limiter: RateLimiter | None = None):
        self.app = app
        self.settings = settings
        self.limiter = limiter or RateLimiter(settings.per_minute, settings.per_day)

    @staticmethod
    async def read_body(receive) -> tuple[bytes, bool]:
        """Stop at the size limit, so a huge body is never held in memory."""
        body = b""
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return body, False
            body += message.get("body", b"")
            if len(body) > MAX_BODY_BYTES:
                return b"", True
            if not message.get("more_body"):
                return body, False

    @staticmethod
    async def answer(send, status: int, content: dict, headers: list | None = None) -> None:
        body = json.dumps(content, ensure_ascii=False).encode("utf-8")
        start = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
        await send({"type": "http.response.start", "status": status, "headers": start + (headers or [])})
        await send({"type": "http.response.body", "body": body})

    async def refuse(self, send, status: int, key: str, lang: str, data: dict, seconds: int = 0) -> None:
        content = {
            "error": key,
            "language": lang,
            "spoken": MESSAGES[lang][key].format(seconds=seconds),
        }
        # The page drops its open question when a reply has none, so it is handed back.
        if isinstance(data.get("pending"), str):
            content["pending"] = data["pending"]
        headers = [(b"retry-after", str(seconds).encode())] if seconds else None
        await self.answer(send, status, content, headers)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"] == "/health":
            return await self.answer(send, 200, {"status": "ok"})
        if not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)

        body, too_large = await self.read_body(receive)
        try:
            data = json.loads(body)
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        lang = read_language(scope, data)

        refused = self.limiter.check(client_key(scope, self.settings.ip_header))
        if refused:
            return await self.refuse(send, 429, refused[0], lang, data, refused[1])
        if too_large:
            return await self.refuse(send, 413, "too_large", lang, data)
        if data.get("live"):
            return await self.refuse(send, 403, "live_disabled", lang, data)

        sent = False

        async def replay():
            nonlocal sent
            if sent:
                return await receive()
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        return await self.app(scope, replay, send)


def protect(main, settings: Settings | None = None, make_transport=httpx.AsyncHTTPTransport) -> DemoGuard:
    """Wrap the app module for public use. Call it after app.main has loaded .env.

    Live mode is closed twice: the agent secrets leave this process, and the guard refuses
    any request that asks for it. With the secrets gone, nobody can freeze a real agent
    through the public page either.
    """
    settings = settings or Settings.from_env()
    for name in AGENT_SECRETS:
        os.environ.pop(name, None)
    # Trade history is one local file, and every visitor here would share it.
    main.history.enabled = False

    budget = DailyBudget(settings.daily_budget_usd)
    parse = main.parse_intent

    async def parse_within_budget(text: str):
        if not budget.has_room(settings.reserve_usd):
            log.warning("daily language model budget reached")
            # The page then says parsing is off and points to the form, which costs nothing.
            raise ParserUnavailable
        async with make_transport() as inner:
            return await parse(text, MeteredTransport(inner, budget, settings))

    main.parse_intent = parse_within_budget
    return DemoGuard(main.app, settings)
