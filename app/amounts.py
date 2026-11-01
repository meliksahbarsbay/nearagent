"""Read amounts the way people say them, in Turkish and English.

This runs in code and not in the model, because 1.000 is a thousand in Turkish and one in
English, and a wrong guess there costs money. A number counts only when a token or a dollar
word follows it, so "bir" as a plain article is never read as an amount.
"""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.confirm import ASCII_FOLD

MAX_TOKENS_IN_AMOUNT = 8

ONES_TR = {
    "sifir": 0, "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6, "yedi": 7,
    "sekiz": 8, "dokuz": 9, "on": 10, "yirmi": 20, "otuz": 30, "kirk": 40, "elli": 50,
    "altmis": 60, "yetmis": 70, "seksen": 80, "doksan": 90,
}
ONES_EN = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"yuz": 100, "bin": 1000, "milyon": 10**6, "hundred": 100, "thousand": 1000, "million": 10**6}
FRACTIONS = {"yarim": "0.5", "ceyrek": "0.25", "half": "0.5", "quarter": "0.25"}
USD_WORDS = {"dolar", "dolarlik", "dolarlk", "usd", "dollar", "dollars", "bucks", "$"}
LINKS = {"of", "worth"}
USD_NAMES = {"USD", "DOLAR", "DOLLAR", "DOLLARS"}
TOKEN_NAMES = {
    "bitcoin": "BTC",
    "ether": "ETH",
    "ethereum": "ETH",
    "tether": "USDT",
    "solana": "SOL",
    "wnear": "NEAR",
}
TOKEN_PATTERN = re.compile(r"\$?\d[\d.,]*\$?|\$|[^\W\d_]+")


@dataclass
class Amount:
    value: str
    usd: bool = False
    token: str | None = None


def canonical(value: Decimal) -> str:
    return f"{value.normalize():f}"


def normalize_number(text: str, lang: str) -> str | None:
    """Read digits by local rules. Turkish: 1.000,5 is 1000.5. English: 1,000.5 is 1000.5."""
    text = text.strip().strip("$").rstrip(".,")
    if not re.fullmatch(r"\d+(?:[.,]\d+)*", text):
        return None
    decimal_mark, thousands_mark = (",", ".") if lang == "tr" else (".", ",")
    if "." in text and "," in text:
        decimal_mark = max(".,", key=text.rfind)
        thousands_mark = "," if decimal_mark == "." else "."
        whole, _, fraction = text.rpartition(decimal_mark)
        groups = whole.split(thousands_mark)
        if thousands_mark in fraction or not valid_groups(groups):
            return None
        return canonical(Decimal(f"{''.join(groups)}.{fraction}"))
    mark = "." if "." in text else "," if "," in text else ""
    if not mark:
        return canonical(Decimal(text))
    groups = text.split(mark)
    if len(groups) > 2:
        return canonical(Decimal("".join(groups))) if valid_groups(groups) else None
    if mark == thousands_mark and valid_groups(groups) and groups[0] != "0":
        return canonical(Decimal("".join(groups)))
    # A lone mark that cannot be a thousands mark is a decimal, whichever key was pressed.
    return canonical(Decimal(f"{groups[0]}.{groups[1]}"))


def valid_groups(groups: list[str]) -> bool:
    return 1 <= len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:])


def tokenize(text: str) -> list[str]:
    """Lower-case words with suffixes cut: NEAR'ı becomes near, and SOL'u becomes sol."""
    folded = text.translate(ASCII_FOLD).casefold().replace("’", "'")
    folded = re.sub(r"'\w+", " ", folded).replace("-", " ")
    return TOKEN_PATTERN.findall(folded)


def word_value(words: list[str]) -> Decimal | None:
    """Add up number words: bin beş yüz, one hundred and fifty, bir buçuk, half a."""
    total = Decimal(0)
    current = Decimal(0)
    seen = False
    for index, word in enumerate(words):
        if word in ("a", "an", "and"):
            if word != "and" and index + 1 < len(words) and words[index + 1] in ("hundred", "thousand", "million"):
                current = Decimal(1)
                seen = True
            continue
        if word in ONES_TR or word in ONES_EN:
            current += (ONES_TR | ONES_EN)[word]
        elif word in ("bucuk", "half") and seen:
            current += Decimal("0.5")
        elif word in ("ceyrek", "quarter") and seen:
            current *= Decimal("0.25")
        elif word in FRACTIONS:
            current += Decimal(FRACTIONS[word])
        elif word in SCALES:
            scale = SCALES[word]
            if scale == 100:
                current = (current or Decimal(1)) * 100
            else:
                total += (current or Decimal(1)) * scale
                current = Decimal(0)
        else:
            return None
        seen = True
    return total + current if seen else None


def is_number_word(word: str, lang: str) -> bool:
    if lang == "tr":
        return word in ONES_TR or word in ("yuz", "bin", "milyon", "bucuk", "ceyrek", "yarim")
    return word in ONES_EN or word in ("hundred", "thousand", "million", "half", "quarter")


def read_run(tokens: list[str], start: int, lang: str) -> tuple[str, int, bool] | None:
    """Read one amount at `start`. Returns the value, where it ended, and a leading $."""
    first = tokens[start]
    if re.match(r"\$?\d", first):
        number = normalize_number(first, lang)
        return (number, start + 1, "$" in first) if number else None
    end = start
    while end < len(tokens) and end - start < MAX_TOKENS_IN_AMOUNT:
        word = tokens[end]
        joins = lang == "en" and word in ("a", "an", "and")
        if not joins and not is_number_word(word, lang):
            break
        end += 1
    while end > start and tokens[end - 1] in ("a", "an", "and"):
        end -= 1
    if end == start:
        return None
    value = word_value(tokens[start:end])
    return (canonical(value), end, False) if value is not None else None


def ticker(word: str) -> str:
    return TOKEN_NAMES.get(word, word.upper())


def unit_after(tokens: list[str], index: int, known: set[str]) -> tuple[bool, str | None] | None:
    """What follows a number: dollars, a known token, or dollars of a known token."""
    if index >= len(tokens):
        return None
    word = tokens[index]
    # "half a SOL" keeps its "a" inside the sentence, and it means nothing here.
    if word in ("a", "an"):
        return unit_after(tokens, index + 1, known)
    if word in USD_WORDS:
        return True, token_after(tokens, index + 1, known)
    if ticker(word) in known:
        return False, ticker(word)
    return None


def token_after(tokens: list[str], index: int, known: set[str]) -> str | None:
    """The token that dollars buy: "dollars of SOL", "dollars worth of SOL", "dolarlık SOL"."""
    while index < len(tokens) and tokens[index] in LINKS:
        index += 1
    if index < len(tokens) and ticker(tokens[index]) in known:
        return ticker(tokens[index])
    return None


def find_amount(text: str, lang: str, known: set[str]) -> Amount | None:
    """Find the first number that a dollar word or a known token follows."""
    tokens = tokenize(text)
    for start in range(len(tokens)):
        run = read_run(tokens, start, lang)
        if run is None:
            continue
        value, end, dollar_sign = run
        if dollar_sign:
            return Amount(value, True, token_after(tokens, end, known))
        unit = unit_after(tokens, end, known)
        if unit is not None:
            return Amount(value, unit[0], unit[1])
    return None


def read_answer(text: str, lang: str, known: set[str]) -> Amount | None:
    """Read an answer to "how much". All of it must be the amount.

    Fifty dollars is not fifty SOL, so a unit that is neither dollars nor one of the
    swap's own tokens is refused, and the question is asked again.
    """
    tokens = tokenize(text)
    if not tokens:
        return None
    run = read_run(tokens, 0, lang)
    if run is None:
        return None
    value, end, dollar_sign = run
    rest = tokens[end:]
    if not rest:
        return Amount(value, dollar_sign)
    unit = unit_after(tokens, end, known)
    if unit is None:
        return None
    usd, token = unit
    expected = 1 + sum(1 for word in rest if word in LINKS or word in ("a", "an")) + (1 if usd and token else 0)
    if len(rest) != expected:
        return None
    return Amount(value, usd or dollar_sign, token)


def number_or_same(text: str, lang: str) -> str:
    """For the form field: local digits become canonical, and anything else is left alone."""
    try:
        return normalize_number(text, lang) or text
    except InvalidOperation:
        return text
