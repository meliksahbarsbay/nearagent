"""Short sentences for the screen reader, in Turkish and English.

Every error says what happened and what to do next, and never carries a code.
"""
import re
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.oneclick import QUOTE_TTL_MINUTES, chain_name

MAX_DECIMALS = 6
MIN_SIGNIFICANT = 4
MAX_SPOKEN_SYMBOL = 12
SMALLEST_FEE = Decimal("0.01")
SECONDS_BEFORE_MINUTES = 90
LARGEST_SPELLED = 10**12

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
        "no_agent": "Ajan cüzdanı kurulmadı. Kurulum bitince yeniden dene.",
        "agent_read_failed": "Ajan bilgisi alınamadı. Biraz sonra yeniden dene.",
        "policy_not_ready": "Politika henüz yürürlükte değil. Biraz sonra yeniden sor.",
        "policy": "Politika: izinli işlemler {actions}. {assets} varlık izinli. {budget} {frozen}",
        "action_names": {"swap": "takas", "withdraw": "çekim", "transfer": "transfer"},
        "action_join": " ve ",
        "policy_budget": "Günlük bütçe {limit} dolar.",
        "policy_no_budget": "Günlük bütçe sınırı yok.",
        "policy_frozen": "Ajan şu an dondurulmuş.",
        "policy_active": "Ajan çalışır durumda.",
        "budget_left": "Günlük bütçenden {left} dolar kaldı. Sınır {limit} dolar.",
        "budget_none": "Günlük bütçe sınırı yok. Sınır koymak için politikayı güncellemek gerekir.",
        "owner_key_missing": "Sahip anahtarı bu bilgisayarda yok, imza atılamadı. Önce sahip kurulumunu tamamla.",
        "freeze_done": "Ajan donduruldu, hiçbir işlem yapamaz. Açmak için ajanı çöz de.",
        "unfreeze_done": "Ajan çözüldü, yeniden işlem yapabilir. Durdurmak için ajanı dondur de.",
        "already_frozen": "Ajan zaten dondurulmuş. Açmak için ajanı çöz de.",
        "already_unfrozen": "Ajan zaten çalışır durumda. Durdurmak için ajanı dondur de.",
        "control_failed": "İşlem tamamlanmadı, ajanın durumu değişmedi. Yeniden dene ya da terminaldeki sahip betiğini kullan.",
        "control_pending": "İstek gönderildi, ama sonuç henüz belli değil. Biraz sonra politikamı oku de.",
        "unfreeze_wait": "Ajan şimdi çözülemez, ağın bekleme süresi dolmadı. Yaklaşık {minutes} dakika sonra yeniden dene.",
        "unfreeze_plan": (
            "Ajanı çözmek için sahip anahtarıyla imza atacağım. "
            "Ajan yeniden işlem yapabilir hale gelir, politikası değişmez. "
            "Onaylamak için şu kodu yaz: {code}. Vazgeçmek için hayır de."
        ),
        "code_wrong": "Kod uymuyor. Kodu yeniden yaz ya da vazgeçmek için hayır de.",
        "code_locked": "Kod üç kez yanlış girildi, hiçbir şey imzalanmadı. Yeniden denemek için ajanı çöz de.",
        "mode_dry": "Deneme modu.",
        "mode_live": "Canlı mod.",
        "live_on": "Canlı mod açık. Onay için evet yazman ya da Onayla düğmesine basman gerekir.",
        "live_off": "Canlı mod kapalı. Deneme modundasın, para hareket etmez.",
        "live_not_configured": "Canlı mod için ajan cüzdanı kurulmadı. Deneme modunda devam edebilirsin.",
        "live_not_connected": "Canlı işlem henüz bağlı değil, para hareket etmedi. Deneme modunda devam edebilirsin.",
        "live_needs_word": "Canlı modda Enter onay sayılmaz. Evet yaz ya da Onayla düğmesine bas.",
        "confirm_question_live": "Onaylıyor musun? Evet yaz ya da Onayla düğmesine bas.",
        "large_question_live": (
            "Yaklaşık {words} dolar mı dedin? Evet yaz ya da Onayla düğmesine bas. "
            "Değilse hayır yaz ya da Esc'e bas."
        ),
        "quote": (
            "{mode} Veriyorsun: {amount_in} {symbol_in}. "
            "Alıyorsun: yaklaşık {amount_out} {symbol_out}. "
            "En az garanti: {min_out} {symbol_out}. {fee} "
            "Süre: yaklaşık {duration}. Teklif {ttl} dakika geçerli."
        ),
        "fee": "Ücret: yaklaşık {usd} dolar.",
        "fee_tiny": "Ücret: 0,01 dolardan az.",
        "fee_unknown": "Ücret bilgisi yok.",
        "seconds": "{count} saniye",
        "minutes": "{count} dakika",
        "confirm_question": "Onaylıyor musun? Evet de ya da Enter'a bas.",
        "large_question": (
            "Yaklaşık {words} dolar mı dedin? Evet de ya da Enter'a bas. "
            "Değilse hayır de ya da Esc'e bas."
        ),
        "confirmed_dry": "Deneme modu: işlem yapılmadı.",
        "cancelled": "İptal ettim, işlem yapılmadı. Yeni bir cümle yazabilirsin.",
        "not_understood": "Cevabını anlayamadım. Evet ya da hayır de.",
        "expired": "Teklifin süresi doldu. İsteğini yeniden yaz.",
        "missing_amount": "Ne kadar çevirmek istiyorsun?",
        "amount_again": "Miktarı anlayamadım. Rakamla yaz, örneğin 10. Vazgeçmek için hayır de.",
        "price": "{amount} {symbol} yaklaşık {usd} dolar.",
        "assumed": "{tokens} kullandım; başka zincir istersen söyle.",
        "assumed_join": " ve ",
        "help": (
            "Takas teklifi ve fiyat söyleyebilirim. Örnek: 2 NEAR'ı USDC'ye çevir, "
            "ya da 1 SOL kaç dolar. Şimdilik yalnızca deneme modu var, para hareket etmez."
        ),
        "empty_text": "Cümle boş. Bir cümle yaz, örneğin 1 SOL kaç dolar.",
        "too_long": "Cümle çok uzun. Daha kısa yaz.",
        "no_parser": "Cümle çözümleme kapalı. Gelişmiş bölümündeki formu kullan.",
        "parser_failed": "Cümleni çözemedim. Yeniden yaz ya da gelişmiş bölümündeki formu kullan.",
        "invalid_amount": "Miktar geçersiz. Sıfırdan büyük bir sayı yaz, örneğin 1,5.",
        "missing_token": "Token adı eksik. Gönderilen ve alınan tokeni yaz.",
        "same_token": "Gönderilen ve alınan token aynı. Farklı bir token seç.",
        "unknown_token": "{symbol} tokenini bulamadım. Token adını kontrol edip yeniden yaz.",
        "unknown_token_long": "Bu tokeni bulamadım. Adres yerine token adını yaz.",
        "token_not_on_chain": "{symbol} {chain} zincirinde yok. Şu zincirlerden birini seç: {chains}.",
        "no_price": "{symbol} için fiyat bilgisi yok. Biraz sonra yeniden dene.",
        "quote_rejected": "Teklif alınamadı. Daha yüksek bir miktar ya da başka bir token dene.",
        "upstream": "Teklif servisine ulaşılamadı. Biraz sonra yeniden dene.",
    },
    "en": {
        "no_agent": "The agent wallet is not set up. Try again after setup.",
        "agent_read_failed": "I could not read the agent. Try again shortly.",
        "policy_not_ready": "The policy is not in force yet. Ask again shortly.",
        "policy": "Policy: allowed actions are {actions}. {assets} assets are allowed. {budget} {frozen}",
        "action_names": {"swap": "swap", "withdraw": "withdraw", "transfer": "transfer"},
        "action_join": " and ",
        "policy_budget": "The daily budget is {limit} dollars.",
        "policy_no_budget": "There is no daily budget cap.",
        "policy_frozen": "The agent is frozen.",
        "policy_active": "The agent is active.",
        "budget_left": "You have {left} dollars left of your daily budget. The cap is {limit} dollars.",
        "budget_none": "There is no daily budget cap. Setting one needs a policy update.",
        "owner_key_missing": "The owner key is not on this computer, so nothing was signed. Finish the owner setup first.",
        "freeze_done": "The agent is frozen and can do nothing. To resume, say unfreeze the agent.",
        "unfreeze_done": "The agent is unfrozen and can act again. To stop it, say freeze the agent.",
        "already_frozen": "The agent is already frozen. To resume, say unfreeze the agent.",
        "already_unfrozen": "The agent is already active. To stop it, say freeze the agent.",
        "control_failed": "That did not complete, and the agent's state did not change. Try again or use the owner script in a terminal.",
        "control_pending": "The request was sent, but the result is not known yet. Shortly, say read my policy.",
        "unfreeze_wait": "The agent cannot be unfrozen yet, because the cooldown is still running. Try again in about {minutes} minutes.",
        "unfreeze_plan": (
            "To unfreeze the agent I will sign with the owner key. "
            "The agent can act again, and its policy does not change. "
            "To confirm, type this code: {code}. To stop, say no."
        ),
        "code_wrong": "That code does not match. Type it again, or say no to stop.",
        "code_locked": "The code was wrong three times, so nothing was signed. To try again, say unfreeze the agent.",
        "mode_dry": "Dry run.",
        "mode_live": "Live mode.",
        "live_on": "Live mode is on. To confirm, type yes or press the Confirm button.",
        "live_off": "Live mode is off. You are in dry mode, so no funds move.",
        "live_not_configured": "The agent wallet for live mode is not set up. You can continue in dry mode.",
        "live_not_connected": "Live execution is not connected yet, so no funds moved. You can continue in dry mode.",
        "live_needs_word": "Enter does not confirm in live mode. Type yes or press the Confirm button.",
        "confirm_question_live": "Do you confirm? Type yes or press the Confirm button.",
        "large_question_live": (
            "Did you mean about {words} dollars? Type yes or press the Confirm button. "
            "If not, type no or press Escape."
        ),
        "quote": (
            "{mode} You give: {amount_in} {symbol_in}. "
            "You get: about {amount_out} {symbol_out}. "
            "Guaranteed minimum: {min_out} {symbol_out}. {fee} "
            "Time: about {duration}. Quote valid for {ttl} minutes."
        ),
        "fee": "Fee: about {usd} dollars.",
        "fee_tiny": "Fee: under 0.01 dollars.",
        "fee_unknown": "No fee information.",
        "seconds": "{count} seconds",
        "minutes": "{count} minutes",
        "confirm_question": "Do you confirm? Say yes or press Enter.",
        "large_question": (
            "Did you mean about {words} dollars? Say yes or press Enter. "
            "If not, say no or press Escape."
        ),
        "confirmed_dry": "Dry run: nothing was executed.",
        "cancelled": "Cancelled, nothing was executed. You can type a new sentence.",
        "not_understood": "I did not understand your answer. Say yes or no.",
        "expired": "This quote has expired. Type your request again.",
        "missing_amount": "How much do you want to convert?",
        "amount_again": "I could not read the amount. Type a number, for example 10. Say no to stop.",
        "price": "{amount} {symbol} is about {usd} dollars.",
        "assumed": "I used {tokens}; tell me if you want another chain.",
        "assumed_join": " and ",
        "help": (
            "I can give swap quotes and prices. For example: swap 2 NEAR to USDC, "
            "or what is 1 SOL worth. Only dry mode exists for now, so no funds move."
        ),
        "empty_text": "The sentence is empty. Type one, for example what is 1 SOL worth.",
        "too_long": "That sentence is too long. Try a shorter one.",
        "no_parser": "Sentence parsing is off. Use the form in the advanced section.",
        "parser_failed": "I could not read that sentence. Rephrase it or use the form in the advanced section.",
        "invalid_amount": "Invalid amount. Enter a number above zero, for example 1.5.",
        "missing_token": "A token name is missing. Enter the token to send and the token to receive.",
        "same_token": "Both tokens are the same. Choose a different token.",
        "unknown_token": "I could not find the token {symbol}. Check the name and try again.",
        "unknown_token_long": "I could not find this token. Type its name, not an address.",
        "token_not_on_chain": "{symbol} is not on {chain}. Choose one of these chains: {chains}.",
        "no_price": "No price is available for {symbol}. Try again shortly.",
        "quote_rejected": "No quote available. Try a higher amount or another token.",
        "upstream": "The quote service is unreachable. Try again shortly.",
    },
}

ONES = {
    "tr": ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"],
    "en": ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
}
TENS = {
    "tr": ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"],
    "en": ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"],
}
TEENS = [
    "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
]
SCALES = {
    "tr": ((10**9, "milyar"), (10**6, "milyon"), (10**3, "bin")),
    "en": ((10**9, "billion"), (10**6, "million"), (10**3, "thousand")),
}


def spell_below_thousand(number: int, lang: str) -> str:
    hundreds, rest = divmod(number, 100)
    tens, ones = divmod(rest, 10)
    words = []
    if lang == "tr":
        if hundreds:
            words += ["yüz"] if hundreds == 1 else [ONES[lang][hundreds], "yüz"]
        words += [TENS[lang][tens], ONES[lang][ones]]
    else:
        if hundreds:
            words += [ONES[lang][hundreds], "hundred"]
        if tens == 1:
            words.append(TEENS[ones])
        elif tens and ones:
            words.append(f"{TENS[lang][tens]}-{ONES[lang][ones]}")
        else:
            words += [TENS[lang][tens], ONES[lang][ones]]
    return " ".join(word for word in words if word)


def spell_number(number: int, lang: str) -> str:
    """Write a whole number in words: 500 is "beş yüz" or "five hundred"."""
    if number == 0:
        return "sıfır" if lang == "tr" else "zero"
    if number >= LARGEST_SPELLED:
        return str(number)
    words = []
    for scale, name in SCALES[lang]:
        count, number = divmod(number, scale)
        if count:
            # Turkish says "bin", never "bir bin".
            is_plain_thousand = lang == "tr" and scale == 1000 and count == 1
            words.append(name if is_plain_thousand else f"{spell_below_thousand(count, lang)} {name}")
    if number:
        words.append(spell_below_thousand(number, lang))
    return " ".join(words)


def detect_language(text: str) -> str:
    """Rough guess, for replies sent before the parser has run."""
    return "tr" if TURKISH_HINT.search(text) else "en"


def format_amount(value: str, lang: str) -> str:
    """Trim to a speakable number. Turkish uses a decimal comma.

    Rounds down, so a guaranteed minimum is never read out higher than it is.
    """
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


def say_duration(seconds: int, lang: str) -> str:
    if seconds < SECONDS_BEFORE_MINUTES:
        return say("seconds", lang, count=seconds)
    return say("minutes", lang, count=round(seconds / 60))


def fee_usd(quote: dict) -> Decimal | None:
    """1Click reports no total fee, so this is the value lost between input and output.

    It covers fees and price difference together. Zero means no USD value was given.
    """
    value_in = Decimal(quote.get("amountInUsd") or 0)
    value_out = Decimal(quote.get("amountOutUsd") or 0)
    if value_in <= 0 or value_out <= 0:
        return None
    return max(value_in - value_out, Decimal(0))


def say_fee(fee: Decimal | None, lang: str) -> str:
    if fee is None:
        return say("fee_unknown", lang)
    if fee < SMALLEST_FEE:
        return say("fee_tiny", lang)
    return say("fee", lang, usd=format_amount(str(fee.quantize(SMALLEST_FEE, ROUND_HALF_UP)), lang))


def say_quote(
    quote: dict, symbol_in: str, symbol_out: str, min_out: str, lang: str, live: bool = False
) -> str:
    return say(
        "quote",
        lang,
        mode=say("mode_live" if live else "mode_dry", lang),
        amount_in=format_amount(quote["amountInFormatted"], lang),
        symbol_in=symbol_in,
        amount_out=format_amount(quote["amountOutFormatted"], lang),
        min_out=format_amount(min_out, lang),
        symbol_out=symbol_out,
        fee=say_fee(fee_usd(quote), lang),
        duration=say_duration(quote["timeEstimate"], lang),
        ttl=QUOTE_TTL_MINUTES,
    )


def format_usd(value: str, lang: str) -> str:
    """Cents, rounded down, so a remaining budget is never read out higher than it is."""
    return format_amount(str(Decimal(value).quantize(SMALLEST_FEE, ROUND_DOWN)), lang)


def say_policy(data: dict, lang: str) -> str:
    policy = data.get("policy")
    if not policy or data.get("status") != "APPLIED" or not data.get("provider_policy_synced"):
        return say("policy_not_ready", lang)
    names = MESSAGES[lang]["action_names"]
    actions = MESSAGES[lang]["action_join"].join(names.get(a, a) for a in policy["actions"])
    assets = policy["assets"]
    daily = (policy.get("budget") or {}).get("daily_usd")
    budget = (
        say("policy_budget", lang, limit=format_usd(daily, lang))
        if daily is not None
        else say("policy_no_budget", lang)
    )
    return say(
        "policy",
        lang,
        actions=actions,
        assets=len(assets) if isinstance(assets, list) else say_all_assets(lang),
        budget=budget,
        frozen=say("policy_frozen" if policy["frozen"] else "policy_active", lang),
    )


def say_all_assets(lang: str) -> str:
    return "Tüm" if lang == "tr" else "All"


def say_budget(data: dict, lang: str) -> str:
    daily = ((data.get("usage") or {}).get("budget") or {}).get("daily") or {}
    if daily.get("limit_usd") is None:
        return say("budget_none", lang)
    return say(
        "budget_left",
        lang,
        left=format_usd(daily["remaining_usd"], lang),
        limit=format_usd(daily["limit_usd"], lang),
    )


def say_large(usd: Decimal, lang: str, live: bool = False) -> str:
    words = spell_number(int(usd.to_integral_value(ROUND_HALF_UP)), lang)
    return say("large_question_live" if live else "large_question", lang, words=words)


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


def say_error(code: str, lang: str, details: dict) -> str:
    """A pasted address is unreadable aloud, so it never goes into the sentence."""
    symbol = details.get("symbol", "")
    if code == "unknown_token" and not 0 < len(symbol) <= MAX_SPOKEN_SYMBOL:
        return say("unknown_token_long", lang)
    return say(code, lang, **details)
