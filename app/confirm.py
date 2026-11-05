"""Open questions to the user: how much, is that amount right, and do you confirm.

They live on the server so that a confirmation is tied to one specific quote, can be
used once, and expires with that quote.
"""
import re
import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from app.oneclick import QUOTE_TTL_MINUTES

MAX_OPEN = 1000
CODE_DIGITS = 6

YES_WORDS = {"evet", "onayla", "onayliyorum", "yes", "confirm"}
NO_WORDS = {"hayir", "iptal", "vazgec", "vazgectim", "no", "cancel"}

ASCII_FOLD = str.maketrans("ıİçğöşü", "iicgosu")


def answer_word(text: str) -> Literal["yes", "no"] | None:
    """Exact words only, so that "evet ama 10 olsun" never counts as a yes."""
    word = text.translate(ASCII_FOLD).casefold().strip(string.punctuation + " ")
    if word in YES_WORDS:
        return "yes"
    if word in NO_WORDS:
        return "no"
    return None


# Voice mode only. Speech can mishear a short "evet", so live money needs the whole phrase.
VOICE_YES_PHRASES = {"evet onayliyorum", "yes i confirm"}
VOICE_MIN_CONFIDENCE = 0.80
MAX_ALTERNATIVES = 3


def folded_words(text: str) -> list[str]:
    folded = text.translate(ASCII_FOLD).casefold()
    return re.sub(r"[^\w\s]", " ", folded).split()


def voice_confirms(text: str) -> bool:
    """Exactly the confirmation phrase, ignoring case and punctuation."""
    return " ".join(folded_words(text)) in VOICE_YES_PHRASES


def voice_says_no(texts: list[str]) -> bool:
    """A refusal heard anywhere, even in a lower-ranked alternative, is never a yes."""
    return any(NO_WORDS & set(folded_words(text)) for text in texts)


def voice_clear(confidence: float | None) -> bool:
    """A browser that reports no confidence, or zero, gets no benefit of the doubt."""
    return confidence is not None and confidence >= VOICE_MIN_CONFIDENCE


def new_code() -> str:
    """A six digit code, read digit by digit, that only a deliberate answer can match."""
    return "".join(secrets.choice(string.digits) for _ in range(CODE_DIGITS))


def code_matches(text: str, code: str) -> bool:
    """Spaces are allowed, because speech input may write 1 2 3 4 5 6."""
    return secrets.compare_digest(re.sub(r"\D", "", text), code)


@dataclass
class Pending:
    kind: Literal["amount", "large", "confirm", "unfreeze", "repair", "repair_amount"]
    lang: str
    swap: dict = field(default_factory=dict)
    expires_at: float = 0.0
    live: bool = False
    code: str = ""
    attempts: int = 0
    order: Any = None
    summary: dict = field(default_factory=dict)


class PendingStore:
    def __init__(self):
        self._items: dict[str, Pending] = {}

    def add(
        self,
        kind: str,
        lang: str,
        swap: dict | None = None,
        live: bool = False,
        code: str = "",
        order: Any = None,
        summary: dict | None = None,
        seconds: int = QUOTE_TTL_MINUTES * 60,
    ) -> str:
        now = time.monotonic()
        self._items = {k: v for k, v in self._items.items() if v.expires_at > now}
        # Dicts keep insertion order, so the first key is the oldest question.
        if len(self._items) >= MAX_OPEN:
            del self._items[next(iter(self._items))]
        key = secrets.token_urlsafe(16)
        expires_at = now + seconds
        self._items[key] = Pending(kind, lang, swap or {}, expires_at, live, code, order=order, summary=summary or {})
        return key

    def get(self, key: str) -> Pending | None:
        item = self._items.get(key)
        if item is None or item.expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return item

    def drop(self, key: str) -> None:
        self._items.pop(key, None)
