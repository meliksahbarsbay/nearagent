"""Fixed agent commands, matched without the language model.

They work with no parser key, cost nothing, and always mean the same thing. Each pattern
sits under its own language, because "politikam ne" has no letter that shows it is Turkish.
"""
import re

from app.confirm import ASCII_FOLD

COMMANDS = {
    "policy": {
        "tr": re.compile(r"\bpolitika\w*\b.*\b(oku|ne|nedir|soyle|goster|anlat)\b"),
        "en": re.compile(r"\b(read|show|tell|what is|what's)\b.*\bpolicy\b|\bmy policy\b"),
    },
    "budget": {
        "tr": re.compile(r"\bbutce\w*\b.*\b(kadar|kaldi|kalan|oku|ne|nedir|soyle)\b"),
        "en": re.compile(r"\bbudget\b.*\b(left|remaining)\b|\b(how much|read|show|what is)\b.*\bbudget\b"),
    },
    "freeze": {
        "tr": re.compile(r"\bajan\w*\s+(\S+\s+)?dondur\w*\b|\bacil durdur\w*\b"),
        "en": re.compile(r"\bfreeze\b.*\bagent\b|\bemergency stop\b"),
    },
}


def detect_command(text: str) -> tuple[str, str] | None:
    """Return the command and its language, or None for an ordinary sentence."""
    folded = text.translate(ASCII_FOLD).casefold()
    for command, languages in COMMANDS.items():
        for lang, pattern in languages.items():
            if pattern.search(folded):
                return command, lang
    return None
