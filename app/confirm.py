"""Open questions to the user: how much, is that amount right, and do you confirm.

They live on the server so that a confirmation is tied to one specific quote, can be
used once, and expires with that quote.
"""
import re
import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Literal

from app.oneclick import QUOTE_TTL_MINUTES

MAX_OPEN = 1000

YES_WORDS = {"evet", "onayla", "onayliyorum", "yes", "confirm"}
NO_WORDS = {"hayir", "iptal", "vazgec", "vazgectim", "no", "cancel"}

AMOUNT_WORDS = {
    "yarım": "0.5",
    "çeyrek": "0.25",
    "bir": "1",
    "iki": "2",
    "üç": "3",
    "dört": "4",
    "beş": "5",
    "altı": "6",
    "yedi": "7",
    "sekiz": "8",
    "dokuz": "9",
    "on": "10",
    "half": "0.5",
    "quarter": "0.25",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}

NUMBER_ANSWER = re.compile(r"^(\d+(?:[.,]\d+)?)(?:\s+([^\s']+)(?:'\S*)?)?$")
# 1.000 means one thousand in Turkish and one in English, so it is never guessed.
AMBIGUOUS_THOUSANDS = re.compile(r"^[1-9]\d{0,2}([.,]\d{3})+$")

ASCII_FOLD = str.maketrans("ıİçğöşü", "iicgosu")


def answer_word(text: str) -> Literal["yes", "no"] | None:
    """Exact words only, so that "evet ama 10 olsun" never counts as a yes."""
    word = text.translate(ASCII_FOLD).casefold().strip(string.punctuation + " ")
    if word in YES_WORDS:
        return "yes"
    if word in NO_WORDS:
        return "no"
    return None


def read_amount(text: str, from_token: str) -> str | None:
    """Read an answer to "how much". Fifty dollars is not fifty SOL, so tickers must match."""
    answer = text.strip().casefold().rstrip(".!")
    if answer in AMOUNT_WORDS:
        return AMOUNT_WORDS[answer]
    match = NUMBER_ANSWER.match(answer)
    if not match or AMBIGUOUS_THOUSANDS.match(match[1]):
        return None
    if match[2] and match[2].upper() != from_token.upper():
        return None
    return match[1]


@dataclass
class Pending:
    kind: Literal["amount", "large", "confirm"]
    lang: str
    swap: dict = field(default_factory=dict)
    expires_at: float = 0.0


class PendingStore:
    def __init__(self):
        self._items: dict[str, Pending] = {}

    def add(self, kind: str, lang: str, swap: dict | None = None) -> str:
        now = time.monotonic()
        self._items = {k: v for k, v in self._items.items() if v.expires_at > now}
        # Dicts keep insertion order, so the first key is the oldest question.
        if len(self._items) >= MAX_OPEN:
            del self._items[next(iter(self._items))]
        key = secrets.token_urlsafe(16)
        expires_at = now + QUOTE_TTL_MINUTES * 60
        self._items[key] = Pending(kind, lang, swap or {}, expires_at)
        return key

    def get(self, key: str) -> Pending | None:
        item = self._items.get(key)
        if item is None or item.expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return item

    def drop(self, key: str) -> None:
        self._items.pop(key, None)
