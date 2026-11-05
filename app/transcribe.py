"""Speech to text with OpenAI, as a choice beside the browser's Web Speech.

The page records a short clip and posts it here. The audio goes to OpenAI and is not kept.
Token names are given as a hint, because a model that has not heard of wNEAR writes "new".
Confidence comes from the model's own token probabilities, so the voice confirmation rule
of 0.80 still applies. With no probabilities there is no confidence, and a live yes fails.
"""
import logging
import math
import os
import sys
import time

import httpx

from app.intent import DEFAULT_OPENAI_BASE_URL

log = logging.getLogger("nearagent.transcribe")
# Each call is logged with its time and result, never with a key or the words.
if not log.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
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
    """No OpenAI key, or switched off."""


class TranscribeFailed(Exception):
    pass


def ready() -> bool:
    return allowed and bool(os.getenv("OPENAI_API_KEY"))


def confidence_of(logprobs) -> float | None:
    """The mean token probability, from 0 to 1. None when the model gave none."""
    if not isinstance(logprobs, list) or not logprobs:
        return None
    values = [item.get("logprob") for item in logprobs if isinstance(item, dict)]
    values = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
    if not values:
        return None
    return round(math.exp(sum(values) / len(values)), 4)


async def transcribe(audio: bytes, content_type: str, lang: str) -> dict:
    if not ready():
        raise TranscribeOff
    kind = (content_type or "").split(";")[0].strip().lower()
    extension = AUDIO_TYPES.get(kind, "webm")
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL") or DEFAULT_MODEL
    data = {"model": model, "language": lang, "prompt": HINTS[lang], "response_format": "json", "include[]": "logprobs"}
    files = {"file": (f"speech.{extension}", audio, kind or "audio/webm")}
    headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=DEFAULT_OPENAI_BASE_URL, timeout=TIMEOUT_SECONDS, transport=transport) as client:
            response = await client.post("audio/transcriptions", data=data, files=files, headers=headers)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        elapsed = round((time.monotonic() - started) * 1000)
        status = getattr(getattr(error, "response", None), "status_code", "-")
        log.warning("transcribe model=%s ms=%d failed=%s status=%s", model, elapsed, type(error).__name__, status)
        raise TranscribeFailed from None
    elapsed = round((time.monotonic() - started) * 1000)
    text = str(body.get("text") or "").strip()
    confidence = confidence_of(body.get("logprobs"))
    # The words are not logged, only how long they are.
    log.info("transcribe model=%s ms=%d bytes=%d chars=%d confidence=%s", model, elapsed, len(audio), len(text), confidence)
    return {"text": text, "confidence": confidence}
