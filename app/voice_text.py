"""Voice mode only: turn what speech recognition writes into what the amount reader expects.

Typed text never comes here. Speech writes "sıfır virgül beş" for 0.5, "one point two" for
1.2, and hears NEAR as "nir". Without this, "sıfır virgül beş NEAR" would be read as 5 NEAR.
The quote always reads the amount back before anything is confirmed.
"""
import re

from app.amounts import ONES_EN, ONES_TR, SCALES, word_value
from app.confirm import ASCII_FOLD

# Whole words only, so a Turkish suffix after an apostrophe stays: nir'ı becomes NEAR'ı.
MISHEARD = [
    (re.compile(r"\b(?:nir|niyar|niar|nier|neyir|niyer|nıyır|nıır)\b", re.IGNORECASE), "NEAR"),
    (re.compile(r"\b(?:yu|u|ü)\s*(?:es|s)\s*(?:di|dı|d)\s*(?:si|sı|c)\b", re.IGNORECASE), "USDC"),
    (re.compile(r"\b(?:yu|u|ü)\s*(?:es|s)\s*(?:di|dı|d)\s*(?:ti|tı|t)\b", re.IGNORECASE), "USDT"),
    (re.compile(r"\busd\s+c\b", re.IGNORECASE), "USDC"),
    (re.compile(r"\busd\s+t\b", re.IGNORECASE), "USDT"),
    (re.compile(r"\beter\b", re.IGNORECASE), "ETH"),
]
# Whisper hears SOL as "soul". That is a real word, so it is a token only where a token goes:
# after an amount, as in "one soul", or joined by "to" or "into" to another token name.
TOKEN_WORDS = r"(?:w?near|usdc|usdt|tether|sol|solana|eth|ether|ethereum|btc|bitcoin)"
SOUL = r"souls?"
# Turkish "on" (ten) is left out, because English "on soul" is not an amount.
NUMBER_WORDS = "|".join(
    sorted((re.escape(word) for word in {*ONES_EN, *ONES_TR, *SCALES} - {"on"}), key=len, reverse=True)
)
AMOUNT = rf"(?:\d+(?:[.,]\d+)*|{NUMBER_WORDS})"
SOUL_AS_SOL = [
    re.compile(rf"\b(?P<before>{AMOUNT}\s+){SOUL}\b", re.IGNORECASE),
    re.compile(rf"\b(?P<before>{TOKEN_WORDS}\s+(?:to|into)\s+){SOUL}\b", re.IGNORECASE),
    re.compile(rf"\b{SOUL}(?P<after>\s+(?:to|into)\s+{TOKEN_WORDS})\b", re.IGNORECASE),
]
# "Swap two SOL to ETH" is often heard as "swap to SOL to ETH". Only this exact shape is read
# as 2, and never in the text: the caller asks "Did you mean: swap 2 SOL to ETH?" first.
TWO_HEARD_AS_TO = re.compile(rf"^\W*swap\s+to\s+({TOKEN_WORDS})\s+to\s+({TOKEN_WORDS})\W*$", re.IGNORECASE)
DECIMAL_WORDS = {"virgul": ",", "nokta": ",", "point": ".", "dot": "."}
DIGITS = {word: value for word, value in (ONES_TR | ONES_EN).items() if value < 10}
# Words people add to an amount when asked how much, which the amount reader refuses.
FILLERS = {
    "tane", "adet", "olsun", "cevir", "lutfen", "sadece", "yap", "kadar",
    "please", "only", "just", "convert", "swap", "make", "it",
}
MAX_RUN = 6
WORD = re.compile(r"\d+(?:[.,]\d+)*(?:['’]\w+)?|\w+(?:['’]\w+)?")


def fold(word: str) -> str:
    return re.sub(r"['’].*", "", word.translate(ASCII_FOLD).casefold())


def is_number(word: str) -> bool:
    return word.isdigit() or word in ONES_TR or word in ONES_EN or word in SCALES


def whole_part(words: list[str]) -> str | None:
    if len(words) == 1 and words[0].isdigit():
        return words[0]
    if any(word.isdigit() for word in words):
        return None
    value = word_value(words)
    return str(int(value)) if value is not None and value == int(value) else None


def fraction_part(words: list[str]) -> str | None:
    """One point two five is 1.25, and bir virgül yirmi beş is 1,25."""
    if all(word.isdigit() or word in DIGITS for word in words):
        return "".join(word if word.isdigit() else str(DIGITS[word]) for word in words)
    return whole_part(words)


def spoken_decimals(text: str) -> str:
    """Write "X virgül Y" and "X point Y" as one number with its decimal mark."""
    matches = list(WORD.finditer(text))
    words = [fold(match.group()) for match in matches]
    for index, word in enumerate(words):
        mark = DECIMAL_WORDS.get(word)
        if not mark or index == 0:
            continue
        start = index
        while start > 0 and index - start < MAX_RUN and is_number(words[start - 1]):
            start -= 1
        end = index + 1
        while end < len(words) and end - index <= MAX_RUN and is_number(words[end]):
            end += 1
        if start == index or end == index + 1:
            continue
        whole = whole_part(words[start:index])
        fraction = fraction_part(words[index + 1:end])
        if whole is None or fraction is None:
            continue
        # Three digits after a mark could read as thousands, so a zero keeps it a decimal.
        if len(fraction) == 3:
            fraction += "0"
        number = f"{whole}{mark}{fraction}"
        suffix = re.search(r"['’]\w+$", matches[end - 1].group())
        replaced = text[: matches[start].start()] + number + (suffix.group() if suffix else "") + text[matches[end - 1].end():]
        return spoken_decimals(replaced)
    return text


def normalize_voice(text: str) -> str:
    """Fix misheard token names and spoken decimals. Everything else stays as heard."""
    for pattern, replacement in MISHEARD:
        text = pattern.sub(replacement, text)
    return soul_as_sol(spoken_decimals(text))


def soul_as_sol(text: str) -> str:
    """ "one soul", "ETH to soul", and "soul to ETH" mean SOL. "my soul" stays."""
    for pattern in SOUL_AS_SOL:
        text = pattern.sub(lambda match: (match.groupdict().get("before") or "") + "SOL" + (match.groupdict().get("after") or ""), text)
    return text


def two_heard_as_to(text: str) -> tuple[str, str] | None:
    """The two token words of "swap to SOL to ETH", or None for any other sentence."""
    match = TWO_HEARD_AS_TO.match(text.strip())
    return (match[1], match[2]) if match else None


def amount_answer(text: str) -> str:
    """An answer to how much, without the extra words: "yarım NEAR çevir" is "yarım NEAR"."""
    kept = [match.group() for match in WORD.finditer(text) if fold(match.group()) not in FILLERS]
    return " ".join(kept) if kept else text
