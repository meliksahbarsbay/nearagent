"""Short sentences for the screen reader, in Turkish and English."""
from decimal import ROUND_DOWN, Decimal

MAX_DECIMALS = 6
MIN_SIGNIFICANT = 4

MESSAGES = {
    "tr": {
        "quote": (
            "Deneme modu. {amount_in} {symbol_in} karşılığında yaklaşık "
            "{amount_out} {symbol_out} alırsın. En az {min_out} {symbol_out}. "
            "Tahmini süre {seconds} saniye. Hiçbir işlem yapılmadı."
        ),
        "invalid_amount": "Miktar geçersiz. Sıfırdan büyük bir sayı yaz, örneğin 1,5.",
        "missing_token": "Gönderilen ve alınan token adlarını yaz.",
        "same_token": "Gönderilen ve alınan token aynı. Farklı bir token seç.",
        "unknown_token": "{symbol} tokenini bulamadım.",
        "ambiguous_token": "{symbol} birden çok zincirde var: {chains}. Şimdilik yalnızca tek zincirli tokenler seçilebiliyor.",
        "quote_rejected": "Teklif alınamadı. Miktar çok düşük olabilir ya da rota yok olabilir.",
        "upstream": "Teklif servisine ulaşılamadı. Biraz sonra yeniden dene.",
    },
    "en": {
        "quote": (
            "Dry run. For {amount_in} {symbol_in} you would get about "
            "{amount_out} {symbol_out}. At least {min_out} {symbol_out}. "
            "Estimated time {seconds} seconds. Nothing was executed."
        ),
        "invalid_amount": "Invalid amount. Enter a number above zero, for example 1.5.",
        "missing_token": "Enter the token to send and the token to receive.",
        "same_token": "Both tokens are the same. Choose a different token.",
        "unknown_token": "I could not find the token {symbol}.",
        "ambiguous_token": "{symbol} exists on several chains: {chains}. For now only single-chain tokens can be selected.",
        "quote_rejected": "No quote available. The amount may be too low, or there may be no route.",
        "upstream": "The quote service is unreachable. Try again shortly.",
    },
}


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
