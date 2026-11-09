"""Fixed agent commands, matched without the language model.

They work with no parser key, cost nothing, and always mean the same thing. Each pattern
sits under its own language, because "politikam ne" has no letter that shows it is Turkish.

The emergency stop must never fall through to the general help reply. A clear request,
such as "freeze" or "stop the agent", freezes at once. A bare "stop" or "durdur" could mean
something else, so it becomes "freeze_ask": the app asks before it signs anything.
"""
import re

from app.confirm import ASCII_FOLD

# Said as a whole sentence, these may mean stop listening or stop this answer, not freeze.
UNCLEAR_STOP = {
    "tr": re.compile(r"^(dur|durdur|duraklat|durdurun)( lutfen| hemen)?$"),
    "en": re.compile(r"^(stop|pause|halt|stop it|stop now)( please| now)?$"),
}

COMMANDS = {
    "withdraw": {
        "tr": re.compile(r"\b(cek|cekin|cekelim|cekmek istiyorum)\b"),
        "en": re.compile(r"\bwithdraw\b"),
    },
    "policy": {
        "tr": re.compile(
            r"\bpolitika\w*\b.*\b(oku|ne|nedir|soyle|goster|anlat)\b|^politika\w*$"
            r"|\b(limitler|kurallar)\w*\b.*\b(oku|ne|neler|nedir|soyle|goster)\b|^(limitler|kurallar)\w*$"
        ),
        "en": re.compile(
            r"\b(read|show|tell|what is|what's)\b.*\bpolicy\b|\bmy policy\b|^(the )?policy$"
            r"|\b(my|the agent's) (limits|rules)\b|\bwhat are (my|the) (limits|rules)\b"
        ),
    },
    "budget": {
        "tr": re.compile(
            r"\bbutce\w*\b.*\b(kadar|kaldi|kalan|oku|ne|nedir|soyle)\b|^butce\w*$|\bgunluk limit\w*\b"
        ),
        "en": re.compile(
            r"\bbudget\b.*\b(left|remaining)\b|\b(how much|read|show|what is|what's)\b.*\bbudget\b"
            r"|^(my |the )?(daily )?budget$|\bmy budget\b|\bdaily (limit|cap)\b"
        ),
    },
    "balance": {
        "tr": re.compile(r"\bcuzdan\w*\s+(\S+\s+)?(ne|neler|oku|goster)\b|\bbakiye\w*\b"),
        "en": re.compile(r"\b(my|the agent's) (balance|wallet)\b|\bwhat's in my wallet\b|\bbalance\b"),
    },
    "history": {
        "tr": re.compile(
            r"\bson (\S+ )?islem\w*\b|\bgecmis\w*\b.*\b(oku|ne|goster)\b|\bislem gecmis\w*\b"
            r"|^gecmis\w*$|\bislemlerim\w*\b"
        ),
        "en": re.compile(
            r"\b(recent|last|latest) (\S+ )?(trades|swaps|transactions)\b|\btrade history\b|\bmy trades\b"
            r"|\bmy (transactions|swaps)\b|\b(my|transaction|swap) history\b|^history$"
            r"|\bshow (me )?(my )?history\b|\bwhat did i (trade|swap)\b"
        ),
    },
    # Before freeze, so "dondurmayı kaldır" is never read as a request to freeze.
    # Unfreezing always asks for a six digit code, so a wide pattern here signs nothing.
    "unfreeze": {
        "tr": re.compile(
            r"\bajan\w*\s+(\S+\s+)?(coz|ac)\b|\bdondurma\w*\s+(kaldir|coz|ac)\b"
            r"|^(ajani )?(coz|devam et|devam ettir)( lutfen)?$|\bajan\w*\s+(\S+\s+)?devam ettir\w*\b"
        ),
        "en": re.compile(
            r"\bunfreeze\b|\bunpause\b|^resume( the agent| the wallet| trading)?( please)?$"
            r"|\bresume (the agent|the wallet|trading)\b"
        ),
    },
    "freeze": {
        "tr": re.compile(
            r"\bajan\w*\s+(\S+\s+)?(dondur|durdur|duraklat)\w*\b|\bacil durdur\w*\b"
            r"|^(hemen )?dondur( hemen| lutfen)?$|\b(her seyi|tum islemleri) durdur\w*\b"
        ),
        "en": re.compile(
            r"\bfreeze\b.*\b(agent|wallet)\b|\bemergency stop\b"
            r"|^(please )?freeze( it| now| everything)?( now| please)?$"
            r"|\b(stop|pause|halt) (the |my )?(agent|wallet|bot)\b"
            r"|\bstop (all trading|everything)\b"
        ),
    },
}


def fold(text: str) -> str:
    folded = text.translate(ASCII_FOLD).casefold()
    return re.sub(r"\s+", " ", folded).strip(" .!?,;:")


def detect_command(text: str) -> tuple[str, str] | None:
    """Return the command and its language, or None for an ordinary sentence."""
    folded = fold(text)
    for command, languages in COMMANDS.items():
        for lang, pattern in languages.items():
            if pattern.search(folded):
                return command, lang
    for lang, pattern in UNCLEAR_STOP.items():
        if pattern.search(folded):
            return "freeze_ask", lang
    return None
