"""Which model service a request goes to: NEAR AI Cloud first, OpenAI as the backup.

The order follows a setting, REPAIR_PROVIDER or TRANSCRIBE_PROVIDER. With no setting, NEAR AI
goes first when its key is set, and OpenAI otherwise. The other one is the backup. NEAR AI
gets 8 seconds before the backup takes the same request.
"""
import os
from dataclasses import dataclass

from app.intent import DEFAULT_NEAR_AI_BASE_URL, DEFAULT_OPENAI_BASE_URL

NEAR_AI = "near_ai"
OPENAI = "openai"
NEAR_AI_TIMEOUT_SECONDS = 8
NAMES = {NEAR_AI: "NEAR AI", OPENAI: "OpenAI"}


@dataclass
class Service:
    name: str
    base_url: str
    api_key: str
    model: str
    timeout: float


def near_ai_key() -> str:
    """NEARAI_API_KEY, or the older NEAR_AI_API_KEY."""
    return os.getenv("NEARAI_API_KEY") or os.getenv("NEAR_AI_API_KEY") or ""


def near_ai_base() -> str:
    return os.getenv("NEARAI_BASE_URL") or os.getenv("NEAR_AI_BASE_URL") or DEFAULT_NEAR_AI_BASE_URL


def first_choice(setting: str) -> str:
    chosen = (os.getenv(setting) or "").strip().lower().replace("-", "_")
    if chosen in ("near_ai", "nearai", "near"):
        return NEAR_AI
    if chosen == OPENAI:
        return OPENAI
    return NEAR_AI if near_ai_key() else OPENAI


def chain(setting: str, near_ai_model: str, openai_model: str, openai_timeout: float, first: str | None = None) -> list[Service]:
    """The services to try, in order. A service with no key is left out."""
    services = {}
    if near_ai_key():
        services[NEAR_AI] = Service(NEAR_AI, near_ai_base(), near_ai_key(), near_ai_model, NEAR_AI_TIMEOUT_SECONDS)
    if os.getenv("OPENAI_API_KEY"):
        services[OPENAI] = Service(OPENAI, DEFAULT_OPENAI_BASE_URL, os.getenv("OPENAI_API_KEY"), openai_model, openai_timeout)
    lead = first or first_choice(setting)
    order = [lead, OPENAI if lead == NEAR_AI else NEAR_AI]
    return [services[name] for name in order if name in services]
