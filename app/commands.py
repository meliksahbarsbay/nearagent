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
    "balance": {
        "tr": re.compile(r"\bcuzdan\w*\s+(\S+\s+)?(ne|neler|oku|goster)\b|\bbakiye\w*\b"),
        "en": re.compile(r"\b(my|the agent's) (balance|wallet)\b|\bwhat's in my wallet\b|\bbalance\b"),
    },
    "history": {
        "tr": re.compile(r"\bson (\S+ )?islem\w*\b|\bgecmis\w*\b.*\b(oku|ne|goster)\b|\bislem gecmis\w*\b"),
        "en": re.compile(r"\b(recent|last|latest) (\S+ )?(trades|swaps|transactions)\b|\btrade history\b|\bmy trades\b"),
    },
    # Before freeze, so "dondurmayı kaldır" is never read as a request to freeze.
    "unfreeze": {
        "tr": re.compile(r"\bajan\w*\s+(\S+\s+)?(coz|ac)\b|\bdondurma\w*\s+(kaldir|coz|ac)\b"),
        "en": re.compile(r"\bunfreeze\b"),
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
