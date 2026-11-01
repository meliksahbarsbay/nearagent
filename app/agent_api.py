"""Client for the NEAR Intents Agent API, written from its docs and OpenAPI file.

Mainnet only, with real funds. The app does not call this client yet: main.py reads
live_ready() and nothing else, so no code path here can move funds today.

Docs: https://docs.agentsonintents.com/integration/agent-api/
"""
import base64
import hashlib
import logging
import os
import re
import secrets
import uuid
from dataclasses import dataclass
from urllib.parse import quote

import httpx

log = logging.getLogger("nearagent.agent_api")

DEFAULT_BASE_URL = "https://api.agentsonintents.com"
MAX_WAIT_MS = 30_000
# wait_ms holds a status call open, so the timeout must outlast it.
TIMEOUT_SECONDS = 45
IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

# Keep polling the same correlation_id. UNCERTAIN may already have run, so it is
# never sent again under a new Idempotency-Key.
PENDING_STATUSES = {"PROCESSING", "QUEUED", "PENDING_DEPOSIT", "PENDING_APPROVAL", "UNCERTAIN"}
FINAL_STATUSES = {"SUCCESS", "REFUNDED", "FAILED"}
# Automatic settlement stopped. Stop polling and never retry: funds may have moved.
REVIEW_STATUS = "NEEDS_REVIEW"


class AgentApiError(Exception):
    """The API refused. Branch on `code`, never on the title or detail text."""

    def __init__(
        self,
        status: int,
        code: str,
        layer: str | None = None,
        retryable: bool = False,
        available_at: str | None = None,
        request_id: str | None = None,
    ):
        super().__init__(f"{status} {code}")
        self.status = status
        self.code = code
        self.layer = layer
        self.retryable = retryable
        self.available_at = available_at
        self.request_id = request_id


class AgentApiRequestError(Exception):
    """No response arrived, so the request may have reached the API.

    The only safe retry is the same body with this same key.
    """

    def __init__(self, idempotency_key: str | None):
        super().__init__("no response from the Agent API")
        self.idempotency_key = idempotency_key


class GrantRequired(Exception):
    """A money action was attempted with no grant token."""


@dataclass(repr=False)
class LiveSettings:
    api_key: str
    agent_id: str
    grant_token: str
    base_url: str


def live_settings() -> LiveSettings:
    return LiveSettings(
        # The docs name it NEAR_INTENTS_AGENT_API_KEY. AGENT_API_KEY is a short alias.
        api_key=os.getenv("NEAR_INTENTS_AGENT_API_KEY") or os.getenv("AGENT_API_KEY") or "",
        agent_id=os.getenv("AGENT_ID") or "",
        grant_token=os.getenv("GRANT_TOKEN") or "",
        base_url=os.getenv("NEAR_INTENTS_AGENT_API_URL") or DEFAULT_BASE_URL,
    )


def live_ready() -> bool:
    """Live mode needs all three: a key alone cannot act for an agent."""
    settings = live_settings()
    return bool(settings.api_key and settings.agent_id and settings.grant_token)


def create_grant_credential() -> tuple[str, str]:
    """Return a new grant token and its commitment. Only the commitment leaves the backend."""
    encoded = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    token = f"ngt_{encoded}"
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_idempotency_key() -> str:
    """Save the key with the request before sending, so a crash can retry it."""
    return str(uuid.uuid4())


def near_owner(account_id: str, public_key: str) -> dict:
    """Public data only. public_key must be a full-access ed25519 key of the account."""
    return {"type": "near", "account_id": account_id, "public_key": public_key}


def safe_policy(
    owner_account: str,
    per_transaction: dict[str, str],
    daily_usd: str,
    max_actions_per_hour: int = 10,
) -> dict:
    """A narrow first policy: swap only the listed assets, and pay out only to the owner.

    per_transaction maps each allowed asset_id to its cap, in atomic units.
    """
    return {
        "frozen": False,
        "actions": ["swap", "withdraw"],
        "confidential": False,
        "owner_approval": False,
        "assets": list(per_transaction),
        "limits": {"per_transaction": per_transaction},
        "max_actions_per_hour": max_actions_per_hour,
        "destinations": {
            "mode": "only",
            "list": [{"action": "withdraw", "chain": "near", "address": owner_account, "memo": None}],
        },
        "budget": {"daily_usd": daily_usd, "weekly_usd": None, "monthly_usd": None},
        "timelock_ms": 0,
    }


def parse_error(response: httpx.Response) -> AgentApiError:
    """Errors are JSON:API documents. Only stable fields are kept."""
    try:
        document = response.json()
        first = document["errors"][0]
        meta = first.get("meta") or {}
        return AgentApiError(
            response.status_code,
            first["code"],
            first.get("layer"),
            bool(meta.get("retryable")),
            meta.get("available_at"),
            (document.get("meta") or {}).get("request_id"),
        )
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return AgentApiError(
            response.status_code,
            "unknown_error",
            request_id=response.headers.get("X-Request-Id"),
        )


class AgentApi:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        grant_token: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key
        self._grant_token = grant_token
        self.base_url = base_url
        self.transport = transport

    def __repr__(self) -> str:
        return f"AgentApi(base_url={self.base_url!r})"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
        public: bool = False,
        grant: bool = False,
    ) -> dict:
        headers = {}
        if not public:
            headers["X-API-Key"] = self._api_key
        if grant:
            if not self._grant_token:
                raise GrantRequired
            headers["X-Grant-Token"] = self._grant_token
        if idempotency_key is not None:
            if not IDEMPOTENCY_KEY.match(idempotency_key):
                raise ValueError("Idempotency-Key must be 8 to 128 of A-Za-z0-9._:-")
            headers["Idempotency-Key"] = idempotency_key
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=TIMEOUT_SECONDS, transport=self.transport
            ) as client:
                response = await client.request(
                    method, path, json=body, params=params, headers=headers
                )
        except httpx.HTTPError as error:
            # Writes are never retried here: the caller decides, with the same key.
            log.warning("request failed: %s %s", method, type(error).__name__)
            raise AgentApiRequestError(idempotency_key) from None
        if response.is_error:
            raise parse_error(response)
        return response.json()

    async def whoami(self) -> dict:
        return await self._request("GET", "/v1/whoami")

    async def network(self) -> dict:
        return await self._request("GET", "/v1/network", public=True)

    async def quotas(self) -> dict:
        return await self._request("GET", "/v1/quotas")

    async def tokens(self) -> dict:
        return await self._request("GET", "/v1/tokens", public=True)

    async def generate_intent(self, intent: dict, idempotency_key: str | None = None) -> dict:
        """Ask for what the owner must sign. Show `preview` next to the wallet prompt."""
        return await self._request(
            "POST", "/v1/generate-intent", body=intent, idempotency_key=idempotency_key
        )

    async def submit_intent(self, intent_type: str, correlation_id: str, signed_data: dict) -> dict:
        """Send the wallet's output unchanged. Sending the same signature twice is safe."""
        body = {"type": intent_type, "correlation_id": correlation_id, "signed_data": signed_data}
        return await self._request("POST", "/v1/submit-intent", body=body)

    async def status(
        self, correlation_id: str, wait_ms: int = MAX_WAIT_MS, refresh: bool = False
    ) -> dict:
        params = {"correlation_id": correlation_id, "wait_ms": min(wait_ms, MAX_WAIT_MS)}
        if refresh:
            params["refresh"] = "true"
        return await self._request("GET", "/v1/status", params=params)

    def _agent_path(self, agent_id: str, suffix: str = "") -> str:
        return f"/v1/agents/{quote(agent_id, safe='')}{suffix}"

    async def agent(self, agent_id: str) -> dict:
        return await self._request("GET", self._agent_path(agent_id))

    async def policy(self, agent_id: str) -> dict:
        return await self._request("GET", self._agent_path(agent_id, "/policy"))

    async def grants(self, agent_id: str) -> dict:
        return await self._request("GET", self._agent_path(agent_id, "/grants"))

    async def balances(self, agent_id: str, source: str = "public") -> dict:
        path = self._agent_path(agent_id, "/balances")
        return await self._request("GET", path, params={"source": source})

    async def deposit(
        self, agent_id: str, origin_asset: str, idempotency_key: str, amount: str | None = None
    ) -> dict:
        """Create a one-time address. Send funds only to details.deposit_address."""
        body = {"origin_asset": origin_asset}
        if amount is not None:
            body["amount"] = amount
        return await self._request(
            "POST",
            self._agent_path(agent_id, "/deposit"),
            body=body,
            idempotency_key=idempotency_key,
        )

    async def quote_swap(
        self, agent_id: str, origin_asset: str, destination_asset: str, amount: str
    ) -> dict:
        """A dry quote. It moves nothing, and needs no grant or Idempotency-Key.

        Read `warnings` first: each rule the live swap would fail is listed there.
        """
        body = {
            "origin_asset": origin_asset,
            "destination_asset": destination_asset,
            "amount": amount,
            "dry": True,
        }
        return await self._request("POST", self._agent_path(agent_id, "/swap"), body=body)

    async def swap(
        self,
        agent_id: str,
        origin_asset: str,
        destination_asset: str,
        amount: str,
        idempotency_key: str,
        min_amount_out: str | None = None,
    ) -> dict:
        """Run a real swap on mainnet. Follow the returned correlation_id with status()."""
        body = {
            "origin_asset": origin_asset,
            "destination_asset": destination_asset,
            "amount": amount,
        }
        if min_amount_out is not None:
            body["min_amount_out"] = min_amount_out
        return await self._request(
            "POST",
            self._agent_path(agent_id, "/swap"),
            body=body,
            idempotency_key=idempotency_key,
            grant=True,
        )
