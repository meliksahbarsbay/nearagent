"""Short sentences for the screen reader, in Turkish and English."""
import re
from decimal import ROUND_DOWN, Decimal

from app.oneclick import chain_name

MAX_DECIMALS = 6
MIN_SIGNIFICANT = 4

# Only the words ignore case: with the flag on, "ı" would also match a plain "I".
TURKISH_HINT = re.compile(r"[çğıöşüÇĞİÖŞÜ]|(?i:\b(cevir|fiyat|nedir|yardim|merhaba|ne kadar)\b)")

# Turkish suffixes depend on how a ticker is pronounced, so only known ones get one.
TURKISH_ACCUSATIVE = {
    "SOL": "SOL'u",
    "USDC": "USDC'yi",
    "USDT": "USDT'yi",
    "ETH": "ETH'yi",
    "BTC": "BTC'yi",
}

MESSAGES = {
    "tr": {
        "quote": (
            "Deneme modu. {amount_in} {symbol_in} karşılığında yaklaşık "
            "{amount_out} {symbol_out} alırsın. En az {min_out} {symbol_out}. "
            "Tahmini süre {seconds} saniye. Hiçbir işlem yapılmadı."
        ),
        "price": "{amount} {symbol} yaklaşık {usd} dolar.",
        "assumed": "{tokens} kullandım; başka zincir istersen söyle.",
        "assumed_join": " ve ",
        "help": (
            "Takas teklifi ve fiyat söyleyebilirim. Örnek: 2 NEAR'ı USDC'ye çevir, "
            "ya da 1 SOL kaç dolar. Şimdilik yalnızca deneme modu var, para hareket etmez."
        ),
        "empty_text": "Bir cümle yaz, örneğin 1 SOL kaç dolar.",
        "too_long": "Cümle çok uzun. Daha kısa yaz.",
        "no_parser": "Cümle çözümleme kapalı. Gelişmiş bölümündeki formu kullan.",
        "parser_failed": "Cümleni çözemedim. Yeniden yaz ya da gelişmiş bölümündeki formu kullan.",
        "invalid_amount": "Miktar geçersiz. Sıfırdan büyük bir sayı yaz, örneğin 1,5.",
        "missing_amount": "Ne kadar çevirmek istediğini de yaz.",
        "missing_token": "Gönderilen ve alınan token adlarını yaz.",
        "same_token": "Gönderilen ve alınan token aynı. Farklı bir token seç.",
        "unknown_token": "{symbol} tokenini bulamadım.",
        "token_not_on_chain": "{symbol} {chain} zincirinde yok. Bulunduğu zincirler: {chains}.",
        "no_price": "{symbol} için fiyat bilgisi yok.",
        "quote_rejected": "Teklif alınamadı. Miktar çok düşük olabilir ya da rota yok olabilir.",
        "upstream": "Teklif servisine ulaşılamadı. Biraz sonra yeniden dene.",
    },
    "en": {
        "quote": (
            "Dry run. For {amount_in} {symbol_in} you would get about "
            "{amount_out} {symbol_out}. At least {min_out} {symbol_out}. "
            "Estimated time {seconds} seconds. Nothing was executed."
        ),
        "price": "{amount} {symbol} is about {usd} dollars.",
        "assumed": "I used {tokens}; tell me if you want another chain.",
        "assumed_join": " and ",
        "help": (
            "I can give swap quotes and prices. For example: swap 2 NEAR to USDC, "
            "or what is 1 SOL worth. Only dry mode exists for now, so no funds move."
        ),
        "empty_text": "Type a sentence, for example what is 1 SOL worth.",
        "too_long": "That sentence is too long. Try a shorter one.",
        "no_parser": "Sentence parsing is off. Use the form in the advanced section.",
        "parser_failed": "I could not read that sentence. Rephrase it or use the form in the advanced section.",
        "invalid_amount": "Invalid amount. Enter a number above zero, for example 1.5.",
        "missing_amount": "Tell me how much you want to convert.",
        "missing_token": "Enter the token to send and the token to receive.",
        "same_token": "Both tokens are the same. Choose a different token.",
        "unknown_token": "I could not find the token {symbol}.",
        "token_not_on_chain": "{symbol} is not on {chain}. It is on: {chains}.",
        "no_price": "No price is available for {symbol}.",
        "quote_rejected": "No quote available. The amount may be too low, or there may be no route.",
        "upstream": "The quote service is unreachable. Try again shortly.",
    },
}


def detect_language(text: str) -> str:
    """Rough guess, for replies sent before the parser has run."""
    return "tr" if TURKISH_HINT.search(text) else "en"


def format_amount(value: str, lang: str) -> str:
    """Trim to a speakable number. Turkish uses a decimal comma."""
    number = Decimal(value)
    # Small amounts keep four significant digits, or they round to the same number.
    places = max(MAX_DECIMALS, MIN_SIGNIFICANT - 1 - number.adjusted())
    trimmed = number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_DOWN).normalize()
    text = f"{trimmed:f}"
    return text.replace(".", ",") if lang == "tr" else text


def say(key: str, lang: str, **values) -> str:
    return MESSAGES[lang][key].format(**values)


def from_atomic(value: str, decimals: int) -> str:
    return f"{Decimal(value).scaleb(-decimals):f}"


def say_quote(quote: dict, symbol_in: str, symbol_out: str, min_out: str, lang: str) -> str:
    return say(
        "quote",
        lang,
        amount_in=format_amount(quote["amountInFormatted"], lang),
        symbol_in=symbol_in,
        amount_out=format_amount(quote["amountOutFormatted"], lang),
        min_out=format_amount(min_out, lang),
        symbol_out=symbol_out,
        seconds=quote["timeEstimate"],
    )


def say_price(amount: Decimal, token: dict, lang: str) -> str:
    usd = amount * Decimal(str(token["price"]))
    return say(
        "price",
        lang,
        amount=format_amount(str(amount), lang),
        symbol=token["symbol"],
        usd=format_amount(str(usd), lang),
    )


def describe_token(token: dict, lang: str) -> str:
    chain = chain_name(token["blockchain"])
    if lang == "tr":
        name = TURKISH_ACCUSATIVE.get(token["symbol"], f"{token['symbol']} tokenini")
        return f"{chain} üzerindeki {name}"
    return f"{token['symbol']} on {chain}"


def say_assumed(tokens: list[dict], lang: str) -> str:
    """Name the chains we picked. Empty when the user chose them all."""
    if not tokens:
        return ""
    joined = MESSAGES[lang]["assumed_join"].join(describe_token(t, lang) for t in tokens)
    return " " + say("assumed", lang, tokens=joined)
