"""Speech to text: NEAR AI Cloud first, OpenAI as the backup, the browser's own as the last.

The page records a short clip and posts it here. The audio goes to the chosen service and is
not kept. Token names are given as a hint, because a model that has not heard of wNEAR writes
"new".

NEAR AI runs Whisper, which gives no token probabilities, so its text has no confidence. A
live voice yes then fails, and the user is asked to type yes or press Confirm. OpenAI gives
probabilities, so its text has a confidence and the 0.80 rule applies as before.
"""
import logging
import math
import os
import sys
import time

import httpx

from app.providers import NEAR_AI, OPENAI, chain

log = logging.getLogger("nearagent.transcribe")
# Each call is logged with its service, time, and result, never with a key or the words.
if not log.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

# Listed by NEAR AI Cloud for /audio/transcriptions. Checked on 5 November 2026.
DEFAULT_NEAR_AI_MODEL = "openai/whisper-large-v3"
DEFAULT_MODEL = "gpt-4o-mini-transcribe"
MAX_AUDIO_BYTES = 1_000_000
TIMEOUT_SECONDS = 30
HINTS = {
    "tr": "Kripto takas komutu. Token adları: NEAR, wNEAR, USDC, USDT, ETH, SOL. Örnek: sıfır virgül beş NEAR'ı USDC'ye çevir.",
    "en": "A crypto swap command. Token names: NEAR, wNEAR, USDC, USDT, ETH, SOL. Example: swap 0.5 NEAR to USDC.",
}
AUDIO_TYPES = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/wav": "wav", "audio/mpeg": "mp3"}
transport: httpx.AsyncBaseTransport | None = None
allowed = True


class TranscribeOff(Exception):
    """No key for any service, or switched off."""


class TranscribeFailed(Exception):
    pass


def services(first: str | None = None):
    return chain(
        "TRANSCRIBE_PROVIDER",
        os.getenv("NEARAI_TRANSCRIBE_MODEL") or DEFAULT_NEAR_AI_MODEL,
        os.getenv("OPENAI_TRANSCRIBE_MODEL") or DEFAULT_MODEL,
        TIMEOUT_SECONDS,
        first,
    )


def ready() -> bool:
    return allowed and bool(services())


def available() -> list[str]:
    return [service.name for service in services()] if allowed else []


def confidence_of(logprobs) -> float | None:
    """The mean token probability, from 0 to 1. None when the model gave none."""
    if not isinstance(logprobs, list) or not logprobs:
        return None
    values = [item.get("logprob") for item in logprobs if isinstance(item, dict)]
    values = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
    if not values:
        return None
    return round(math.exp(sum(values) / len(values)), 4)


async def ask_service(service, audio: bytes, kind: str, lang: str) -> dict:
    extension = AUDIO_TYPES.get(kind, "webm")
    data = {"model": service.model, "language": lang, "prompt": HINTS[lang], "response_format": "json"}
    if service.name == OPENAI:
        # Only OpenAI's own models return probabilities. Whisper is not asked for them.
        data["include[]"] = "logprobs"
    files = {"file": (f"speech.{extension}", audio, kind or "audio/webm")}
    headers = {"Authorization": f"Bearer {service.api_key}"}
    async with httpx.AsyncClient(base_url=service.base_url, timeout=service.timeout, transport=transport) as client:
        response = await client.post("audio/transcriptions", data=data, files=files, headers=headers)
    response.raise_for_status()
    return response.json()


async def transcribe(audio: bytes, content_type: str, lang: str, first: str | None = None) -> dict:
    """Try each service in order. Returns the text, its confidence, and who answered."""
    if not allowed:
        raise TranscribeOff
    order = services(first)
    if not order:
        raise TranscribeOff
    kind = (content_type or "").split(";")[0].strip().lower()
    for index, service in enumerate(order):
        backup = index > 0
        started = time.monotonic()
        try:
            body = await ask_service(service, audio, kind, lang)
        except (httpx.HTTPError, ValueError) as error:
            elapsed = round((time.monotonic() - started) * 1000)
            status = getattr(getattr(error, "response", None), "status_code", "-")
            log.warning(
                "transcribe provider=%s model=%s ms=%d backup=%s failed=%s status=%s next=%s",
                service.name, service.model, elapsed, backup, type(error).__name__, status,
                order[index + 1].name if index + 1 < len(order) else "browser",
            )
            continue
        elapsed = round((time.monotonic() - started) * 1000)
        text = str(body.get("text") or "").strip()
        confidence = confidence_of(body.get("logprobs"))
        # The words are not logged, only how long they are.
        log.info(
            "transcribe provider=%s model=%s ms=%d backup=%s bytes=%d chars=%d confidence=%s",
            service.name, service.model, elapsed, backup, len(audio), len(text), confidence,
        )
        return {"text": text, "confidence": confidence, "provider": service.name, "backup": backup}
    raise TranscribeFailed


__all__ = ["NEAR_AI", "OPENAI", "transcribe", "ready", "available"]
