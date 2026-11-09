"""nearagent API. Serves the page, sentence requests, and the advanced form."""
import json
from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

# The money methods stay behind app/live.py, which checks everything again before sending.
from app.agent_api import (  # noqa: E402
    AgentApiError,
    AgentApiRequestError,
    agent_ready,
    live_ready,
    live_settings,
    read_agent_balances,
    read_agent_policy,
)
from app.amounts import number_or_same, read_answer  # noqa: E402
from app.commands import detect_command  # noqa: E402
from app.history import history  # noqa: E402
from app.live import (  # noqa: E402
    QUOTE_MINUTES,
    QUOTE_SECONDS,
    WithdrawOrder,
    client as live_client,
    execute_order,
    execute_withdraw,
    plan_withdraw,
    prepare_order,
    read_operation,
)
from app.confirm import (  # noqa: E402
    MAX_ALTERNATIVES,
    Pending,
    PendingStore,
    answer_word,
    code_matches,
    new_code,
    voice_clear,
    voice_confirms,
    voice_says_no,
)
from app.intent import Intent, ParserUnavailable, parse_intent  # noqa: E402
from app.voice_text import amount_answer, normalize_voice, two_heard_as_to  # noqa: E402
from app import intent_repair  # noqa: E402
from app import transcribe as speech  # noqa: E402
from app.providers import near_ai_key  # noqa: E402
from app.messages import (  # noqa: E402
    detect_language,
    format_amount,
    from_atomic,
    say,
    say_assumed,
    say_balances,
    say_budget,
    say_error,
    say_history,
    say_large,
    say_live_status,
    say_policy,
    say_price,
    say_price_usd,
    say_quote,
    say_repair_sentence,
    say_usd_note,
    say_withdraw,
)
from app.owner import (  # noqa: E402
    OwnerError,
    OwnerKeyMissing,
    ResultPending,
    control_agent,
    owner_ready,
)
from app.oneclick import (  # noqa: E402
    QUOTE_TTL_MINUTES,
    OneClick,
    QuoteError,
    build_quote_request,
    find_token,
    parse_amount,
    to_atomic,
    token_amount,
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_TOKEN_TEXT = 64
MAX_SENTENCE = 300
LARGE_USD = Decimal(100)
MAX_CODE_ATTEMPTS = 3
TEXT_ERRORS = {"empty_text", "too_long"}
# A sentence that failed on its tokens may still say something clear. See app/intent_repair.py.
REPAIRABLE = {"unknown_token", "missing_token"}
REPAIR_SECONDS = 120
RECENT_TRADES = 5
UNFREEZE_COOLDOWN_MINUTES = 10
ALREADY_DONE = {
    "wallet_already_frozen": "already_frozen",
    "wallet_already_unfrozen": "already_unfrozen",
}

app = FastAPI(title="nearagent")
oneclick = OneClick()
pendings = PendingStore()


class QuoteInput(BaseModel):
    from_token: str = ""
    to_token: str = ""
    amount: str = ""
    lang: Literal["tr", "en"] = "tr"
    live: bool = False


class AskInput(BaseModel):
    text: str = ""
    pending: str | None = None
    lang: Literal["tr", "en"] | None = None
    live: bool = False
    # Set only by voice mode. Typed answers and the Confirm button never send these.
    voice: bool = False
    confidence: float | None = Field(default=None, ge=0, le=1)
    alternatives: list[Annotated[str, Field(max_length=MAX_SENTENCE)]] = Field(
        default_factory=list, max_length=MAX_ALTERNATIVES
    )
    # The page sets dictation when the text came from the microphone and was not edited.
    source: Literal["typed", "dictation"] | None = None
    # Which speech to text heard a voice answer. Whisper on NEAR AI gives no confidence.
    engine: Literal["browser", "near_ai", "openai"] | None = None


class ModeInput(BaseModel):
    live: bool = False
    lang: Literal["tr", "en"] = "tr"


class TrackInput(BaseModel):
    track: str = ""
    lang: Literal["tr", "en"] = "tr"


def get_oneclick() -> OneClick:
    return oneclick


def error_response(
    error: QuoteError, lang: str, pending: str | None = None, field: str | None = None
) -> JSONResponse:
    content = {
        "error": error.code,
        "language": lang,
        "spoken": say_error(error.code, lang, error.details),
    }
    if pending:
        content["pending"] = pending
    if field:
        content["field"] = field
    return JSONResponse(status_code=error.status, content=content)


def form_field(error: QuoteError, data: "QuoteInput") -> str | None:
    """Which form field an error is about, so the page can mark it and move there."""
    if error.code == "invalid_amount":
        return "amount"
    if error.code == "same_token":
        return "to_token"
    if error.code == "missing_token":
        return "from_token" if not data.from_token.strip() else "to_token"
    if error.code in ("unknown_token", "token_not_on_chain"):
        wanted = error.details.get("symbol", "").strip().upper()
        return "to_token" if wanted == data.to_token.strip().upper() else "from_token"
    return None


def reply(action: str, key: str, lang: str, pending: str | None = None) -> dict:
    content = {"action": action, "language": lang, "spoken": say(key, lang)}
    if pending:
        content["pending"] = pending
    return content


def require_live(live: bool) -> None:
    if live and not live_ready():
        raise QuoteError("live_not_configured", 409)


async def resolve_pair(
    client: OneClick,
    from_token: str,
    from_chain: str | None,
    to_token: str,
    to_chain: str | None,
) -> tuple[dict, bool, dict, bool]:
    if not from_token.strip() or not to_token.strip():
        raise QuoteError("missing_token")
    if max(len(from_token), len(to_token)) > MAX_TOKEN_TEXT:
        raise QuoteError("unknown_token", 404, symbol="")
    tokens = await client.tokens()
    origin, origin_assumed = find_token(tokens, from_token, from_chain)
    destination, destination_assumed = find_token(tokens, to_token, to_chain)
    if origin["assetId"] == destination["assetId"]:
        raise QuoteError("same_token")
    return origin, origin_assumed, destination, destination_assumed


def confirm_question(value_in: Decimal, lang: str, live: bool) -> tuple[str, str]:
    if value_in > LARGE_USD:
        return "large", say_large(value_in, lang, live)
    return "confirm", say("confirm_question_live" if live else "confirm_question", lang)


async def offer_live(
    from_token: str,
    from_chain: str | None,
    to_token: str,
    to_chain: str | None,
    amount: str,
    lang: str,
    unit: str = "token",
    side: str = "from",
) -> dict:
    """Quote from the agent's own account and read the terms. Nothing is sent here."""
    order, origin_assumed, destination_assumed = await prepare_order(
        from_token, from_chain, to_token, to_chain, amount, unit, side
    )
    origin, destination = order.origin, order.destination
    assumed = [t for t, flag in ((origin, origin_assumed), (destination, destination_assumed)) if flag]
    min_out = from_atomic(order.min_out, destination["decimals"])
    terms = say_quote(
        order.view(), origin["symbol"], destination["symbol"], min_out, lang, True, QUOTE_MINUTES
    )
    warning = f" {say('high_fee', lang)}" if order.high_fee else ""
    if unit == "usd":
        warning += f" {say_usd_note(amount, lang)}"
    kind, question = confirm_question(order.usd, lang, True)
    return {
        "action": "swap",
        "mode": "live",
        "language": lang,
        "pending": pendings.add(kind, lang, live=True, order=order, seconds=QUOTE_SECONDS),
        "expires_in": QUOTE_SECONDS,
        "confirm_button": True,
        "spoken": f"{terms}{warning}{say_assumed(assumed, lang)} {question}",
        "quote": {"from": origin["assetId"], "to": destination["assetId"]},
    }


async def offer_withdraw(text: str, lang: str) -> dict:
    """Read what would leave and where it goes. Nothing is sent here."""
    order = await plan_withdraw(live_client(), live_settings().agent_id, text, lang)
    kind, question = confirm_question(order.usd, lang, True)
    return {
        "action": "withdraw",
        "mode": "live",
        "language": lang,
        "pending": pendings.add(kind, lang, live=True, order=order, seconds=QUOTE_SECONDS),
        "expires_in": QUOTE_SECONDS,
        "confirm_button": True,
        "spoken": f"{say_withdraw(order, lang, QUOTE_MINUTES)} {question}",
        "copies": [{"key": "owner_address", "value": order.recipient}],
    }


async def run_live(item: Pending) -> dict | JSONResponse:
    """Send a confirmed order, or ask again if anything changed since the user heard it."""
    try:
        if isinstance(item.order, WithdrawOrder):
            track = await execute_withdraw(item.order)
            if track is None:
                offer = await offer_withdraw(item.order.request["text"], item.lang)
                offer["spoken"] = f"{say('live_changed', item.lang)} {offer['spoken']}"
                return offer
        else:
            track = await execute_order(item.order)
            if track is None:
                offer = await offer_live(**item.order.request, lang=item.lang)
                offer["spoken"] = f"{say('live_changed', item.lang)} {offer['spoken']}"
                return offer
    except QuoteError as error:
        return error_response(error, item.lang)
    return {**reply("live_sent", "live_processing", item.lang), "mode": "live", "track": track}


async def run_swap(
    client: OneClick,
    from_token: str,
    from_chain: str | None,
    to_token: str,
    to_chain: str | None,
    amount: str,
    lang: str,
    live: bool = False,
    unit: str = "token",
    side: str = "from",
) -> dict:
    if live:
        return await offer_live(
            from_token, from_chain, to_token, to_chain, amount, lang, unit, side
        )
    origin, origin_assumed, destination, destination_assumed = await resolve_pair(
        client, from_token, from_chain, to_token, to_chain
    )
    # An amount of the bought token is what arrives, so the input floats: EXACT_OUTPUT.
    exact_out = side == "to"
    base = destination if exact_out else origin
    atomic = to_atomic(token_amount(amount, unit, base), base["decimals"])
    body = build_quote_request(
        origin["assetId"],
        destination["assetId"],
        atomic,
        client.account,
        dry=True,
        swap_type="EXACT_OUTPUT" if exact_out else "EXACT_INPUT",
    )
    result = await client.quote(body)
    details = result["quote"]
    min_out = from_atomic(details["minAmountOut"], destination["decimals"])
    assumed = [t for t, flag in ((origin, origin_assumed), (destination, destination_assumed)) if flag]
    terms = say_quote(
        details, origin["symbol"], destination["symbol"], min_out, lang, exact_out=exact_out
    )
    if unit == "usd":
        terms += f" {say_usd_note(amount, lang)}"
    if exact_out:
        terms += f" {say('refund_note', lang)}"
    kind, question = confirm_question(Decimal(details.get("amountInUsd") or 0), lang, False)
    summary = {
        "gave": details["amountInFormatted"],
        "gave_symbol": origin["symbol"],
        "got": details["amountOutFormatted"],
        "got_symbol": destination["symbol"],
        "ref": result.get("correlationId"),
    }
    return {
        "action": "swap",
        "mode": "dry",
        "language": lang,
        "pending": pendings.add(kind, lang, summary=summary),
        "expires_in": QUOTE_TTL_MINUTES * 60,
        "confirm_button": False,
        "spoken": f"{terms}{say_assumed(assumed, lang)} {question}",
        "quote": {
            "from": origin["assetId"],
            "to": destination["assetId"],
            "swapType": "EXACT_OUTPUT" if exact_out else "EXACT_INPUT",
            "amountIn": details["amountInFormatted"],
            "amountOut": details["amountOutFormatted"],
            "minAmountOut": min_out,
            "amountInUsd": details.get("amountInUsd"),
            "amountOutUsd": details["amountOutUsd"],
            "timeEstimate": details["timeEstimate"],
        },
        "correlationId": result["correlationId"],
    }


async def run_price(client: OneClick, intent: Intent) -> dict:
    if not intent.from_token:
        raise QuoteError("missing_token")
    amount = parse_amount(intent.amount or "1")
    tokens = await client.tokens()
    token, assumed = find_token(tokens, intent.from_token, intent.from_chain)
    if token.get("price") is None:
        raise QuoteError("no_price", symbol=token["symbol"])
    lang = intent.language
    usd = intent.amount_unit == "usd"
    spoken = say_price_usd(amount, token, lang) if usd else say_price(amount, token, lang)
    return {
        "action": "price",
        "language": lang,
        "spoken": spoken + say_assumed([token] if assumed else [], lang),
    }


async def run_intent(client: OneClick, intent: Intent, live: bool = False) -> dict:
    lang = intent.language
    if intent.action == "help":
        return reply("help", "help_live" if live else "help", lang)
    if intent.action == "price":
        return await run_price(client, intent)
    swap = {
        "from_token": intent.from_token or "",
        "from_chain": intent.from_chain,
        "to_token": intent.to_token or "",
        "to_chain": intent.to_chain,
    }
    if intent.amount:
        return await run_swap(
            client,
            amount=intent.amount,
            lang=lang,
            live=live,
            unit=intent.amount_unit,
            side=intent.amount_side,
            **swap,
        )
    # Check the tokens first, so nobody answers a question for a swap that cannot happen.
    await resolve_pair(client, **swap)
    return reply("ask_amount", "missing_amount", lang, pendings.add("amount", lang, swap, live))


async def answer_amount(client: OneClick, key: str, item: Pending, text: str) -> dict | JSONResponse:
    tokens = {item.swap["from_token"].upper(), item.swap["to_token"].upper()}
    answer = read_answer(text, item.lang, tokens)
    if answer is None:
        return reply("ask_amount", "amount_again", item.lang, key)
    bought = answer.token == item.swap["to_token"].upper() != item.swap["from_token"].upper()
    try:
        offer = await run_swap(
            client,
            amount=answer.value,
            lang=item.lang,
            live=item.live,
            unit="usd" if answer.usd else "token",
            side="to" if bought else "from",
            **item.swap,
        )
    except QuoteError as error:
        # The tokens stay valid, so the user can answer again with another amount.
        return error_response(error, item.lang, key)
    pendings.drop(key)
    return offer


def ask_again(item: Pending, key: str, message: str) -> dict:
    return {**reply(item.kind, message, item.lang, key), "confirm_button": item.live}


def minutes_until(moment: str | None) -> int:
    if not moment:
        return UNFREEZE_COOLDOWN_MINUTES
    ready = datetime.fromisoformat(moment.replace("Z", "+00:00"))
    seconds = (ready - datetime.now(timezone.utc)).total_seconds()
    return max(1, ceil(seconds / 60))


async def run_control(kind: str, lang: str) -> dict:
    """Sign a freeze or unfreeze. Only a confirmed result is reported as done."""
    done = "freeze_done" if kind == "agent_freeze" else "unfreeze_done"
    action = "freeze" if kind == "agent_freeze" else "unfreeze"
    try:
        await control_agent(kind)
    except OwnerKeyMissing:
        return reply(action, "owner_key_missing", lang)
    except (ResultPending, AgentApiRequestError):
        # No answer does not mean no effect: it may have reached the chain.
        return reply(action, "control_pending", lang)
    except AgentApiError as error:
        if error.code == "agent_unfreeze_throttled":
            minutes = minutes_until(error.available_at)
            return {
                "action": action,
                "language": lang,
                "spoken": say("unfreeze_wait", lang, minutes=minutes),
            }
        return reply(action, ALREADY_DONE.get(error.code, "control_failed"), lang)
    except OwnerError:
        return reply(action, "control_failed", lang)
    return {**reply(action, done, lang), "signed": True}


def ask_unfreeze(lang: str) -> dict:
    if not owner_ready():
        return reply("unfreeze", "owner_key_missing", lang)
    code = new_code()
    key = pendings.add("unfreeze", lang, code=code)
    spoken = say("unfreeze_plan", lang, code=" ".join(code))
    return {"action": "unfreeze", "language": lang, "pending": key, "spoken": spoken}


async def answer_unfreeze(key: str, item: Pending, text: str) -> dict:
    """Only the code signs: not Enter, not yes, and not a sentence."""
    if not code_matches(text, item.code):
        item.attempts += 1
        if item.attempts >= MAX_CODE_ATTEMPTS:
            pendings.drop(key)
            return reply("cancelled", "code_locked", item.lang)
        return reply("unfreeze", "code_wrong", item.lang, key)
    pendings.drop(key)
    return await run_control("agent_unfreeze", item.lang)


async def answer_pending(
    client: OneClick, key: str, text: str, lang: str
) -> dict | JSONResponse:
    item = pendings.get(key)
    if item is None:
        return reply("expired", "expired", lang)
    word = answer_word(text)
    if word == "no":
        pendings.drop(key)
        return reply("cancelled", "cancelled", item.lang)
    if item.kind == "unfreeze":
        return await answer_unfreeze(key, item, text)
    if item.kind == "amount":
        return await answer_amount(client, key, item, text)
    if item.kind == "repair_amount":
        return answer_repair_amount(key, item, text)
    if item.kind == "repair":
        return await answer_repair(client, key, item, text, word)
    if word != "yes":
        if text:
            return ask_again(item, key, "not_understood")
        # The page sends empty text when Enter is pressed on the empty box.
        if item.live:
            return ask_again(item, key, "live_needs_word")
    if item.kind == "large":
        item.kind = "confirm"
        question = "confirm_question_live" if item.live else "confirm_question"
        return ask_again(item, key, question)
    pendings.drop(key)
    if item.live:
        return await run_live(item)
    history.add(mode="dry", status="dry", **item.summary)
    return {**reply("confirmed", "confirmed_dry", item.lang), "mode": "dry"}


def run_history(lang: str) -> dict:
    """History is local and covers dry runs, so it needs no agent."""
    try:
        entries = history.recent(RECENT_TRADES)
    except (OSError, ValueError):
        raise QuoteError("history_broken", 503) from None
    copies = [
        {"key": "trade", "number": number, "value": entry["ref"]}
        for number, entry in enumerate(entries, start=1)
        if entry.get("ref")
    ]
    return {
        "action": "history",
        "language": lang,
        "spoken": say_history(entries, lang),
        "copies": copies,
    }


async def run_command(command: str, lang: str, text: str = "", live: bool = False) -> dict:
    if command == "history":
        return run_history(lang)
    if not agent_ready():
        return reply(command, "no_agent", lang)
    if command == "withdraw":
        require_live(True)
        # The page must already say live, so real money is never confirmed under a dry label.
        if not live:
            raise QuoteError("withdraw_needs_live", 409)
        return await offer_withdraw(text, lang)
    if command == "freeze":
        return await run_control("agent_freeze", lang)
    if command == "unfreeze":
        return ask_unfreeze(lang)
    try:
        data = await (read_agent_balances() if command == "balance" else read_agent_policy())
    except (AgentApiError, AgentApiRequestError):
        raise QuoteError("agent_read_failed", 502) from None
    speakers = {"policy": say_policy, "budget": say_budget, "balance": say_balances}
    spoken = speakers[command](data, lang)
    return {"action": command, "language": lang, "spoken": spoken}


def voice_question(item: Pending) -> str:
    """Repeat the amount and token, then name the whole phrase that confirms."""
    order, lang = item.order, item.lang
    if isinstance(order, WithdrawOrder):
        return say("voice_confirm_withdraw", lang, amount=format_amount(order.amount_text, lang), symbol=order.symbol)
    destination = order.destination
    return say(
        "voice_confirm_swap",
        lang,
        give=format_amount(order.amount_in_text, lang),
        symbol_in=order.origin["symbol"],
        min_out=format_amount(from_atomic(order.min_out, destination["decimals"]), lang),
        symbol_out=destination["symbol"],
    )


def voiced_offer(result):
    """A live offer heard in voice mode ends with the spoken phrase, not with type yes."""
    if not isinstance(result, dict) or result.get("mode") != "live" or not result.get("pending"):
        return result
    item = pendings.get(result["pending"])
    if item is None or not item.live or item.order is None:
        return result
    _, question = confirm_question(item.order.usd, item.lang, True)
    spoken = result["spoken"]
    if spoken.endswith(question):
        spoken = spoken[: -len(question)].rstrip()
    return {**result, "spoken": f"{spoken} {voice_question(item)}"}


async def answer_voice(data: AskInput, text: str, lang: str) -> dict | JSONResponse | None:
    """Stricter answers for live money heard by voice. None leaves the answer to the usual path.

    Every doubt cancels: a refusal in any alternative, silence, low or missing confidence,
    or any words but the whole phrase. A bare yes is asked once more.
    """
    key = data.pending
    item = pendings.get(key)
    if item is None:
        return None
    if not item.live or item.kind not in ("confirm", "large"):
        # Silence must never reach the usual path, where an empty answer confirms a dry quote.
        if not text and item.kind in ("confirm", "large"):
            return ask_again(item, key, "voice_not_heard")
        return None
    if voice_says_no([text, *data.alternatives]):
        pendings.drop(key)
        return reply("cancelled", "cancelled" if answer_word(text) == "no" else "voice_unclear", item.lang)
    if not text:
        pendings.drop(key)
        return reply("cancelled", "voice_silence", item.lang)
    if not voice_clear(data.confidence):
        # A service that gives no confidence cannot confirm by voice, so typing is asked for.
        if data.confidence is None and data.engine in ("near_ai", "openai"):
            return ask_again(item, key, "voice_no_confidence")
        pendings.drop(key)
        return reply("cancelled", "voice_unclear", item.lang)
    if not voice_confirms(text):
        if answer_word(text) == "yes":
            return ask_again(item, key, "voice_needs_phrase")
        pendings.drop(key)
        return reply("cancelled", "voice_unclear", item.lang)
    if item.kind == "large":
        item.kind = "confirm"
        return {**ask_again(item, key, "voice_needs_phrase"), "spoken": voice_question(item)}
    pendings.drop(key)
    return voiced_offer(await run_live(item))


def repair_question(item_swap: dict, lang: str, live: bool, provider: str = "rule", backup: bool = False) -> dict:
    key = pendings.add("repair", lang, swap=item_swap, live=live, seconds=REPAIR_SECONDS)
    sentence = say_repair_sentence(item_swap, lang)
    return {
        "action": "repair",
        "language": lang,
        "pending": key,
        # Silence in voice mode cancels this question, as it does a live quote.
        "answer_required": True,
        "provider": provider,
        "backup": backup,
        "spoken": say("repair_question", lang, sentence=sentence),
    }


async def offer_repair(text: str, lang: str, live: bool, use_model: bool = True) -> dict | None:
    """A suggestion, or how much, for a sentence that failed. None when nothing is clear."""
    found = await intent_repair.suggest(text, lang, live, use_model)
    if found is None:
        return None
    if found.kind == "ask_amount":
        key = pendings.add("repair_amount", lang, swap=found.swap, live=live, seconds=REPAIR_SECONDS)
        return {**reply("ask_amount", "missing_amount", lang, key), "answer_required": True}
    return repair_question(found.swap, lang, live, found.provider, found.backup)


def unrepaired(error: QuoteError, lang: str, live: bool) -> JSONResponse:
    """The usual error, with the tokens that can be used."""
    response = error_response(error, lang)
    content = json.loads(response.body)
    tokens = ", ".join(intent_repair.supported(live))
    content["spoken"] = f"{content['spoken']} {say('supported_tokens', lang, tokens=tokens)}"
    return JSONResponse(status_code=response.status_code, content=content)


def answer_repair_amount(key: str, item: Pending, text: str) -> dict:
    """How much, for a suggestion. The answer leads to the question, not to a quote."""
    tokens = {item.swap["from_token"], item.swap["to_token"]}
    answer = read_answer(text, item.lang, tokens)
    if answer is None or (answer.token and answer.token != item.swap["from_token"]):
        return {**reply("ask_amount", "amount_again", item.lang, key), "answer_required": True}
    pendings.drop(key)
    swap = {**item.swap, "amount": answer.value, "unit": "usd" if answer.usd else "token"}
    return repair_question(swap, item.lang, item.live)


async def answer_repair(client: OneClick, key: str, item: Pending, text: str, word: str | None):
    """Only yes asks for the quote. This yes accepts the sentence, never a live swap."""
    pendings.drop(key)
    if word != "yes":
        if text:
            # Not an answer but a new sentence, so it is read as one.
            return await answer_ask(AskInput(text=text, live=item.live), client)
        return reply("cancelled", "repair_no_yes", item.lang)
    swap = item.swap
    try:
        return await run_swap(
            client,
            swap["from_token"],
            None,
            swap["to_token"],
            None,
            swap["amount"],
            item.lang,
            item.live,
            unit=swap.get("unit", "token"),
        )
    except QuoteError as error:
        return error_response(error, item.lang)


def from_dictation(data: AskInput) -> AskInput:
    """Dictated text is fixed like voice mode. Typed text never comes here."""
    text = normalize_voice(data.text.strip())
    waiting = pendings.get(data.pending) if data.pending else None
    if waiting is not None and waiting.kind in ("amount", "repair_amount"):
        text = amount_answer(text)
    return data.model_copy(update={"text": text})


def two_question(data: AskInput):
    """Spoken "swap to SOL to ETH" probably said two. Ask "Did you mean: swap 2 SOL to ETH?"

    Nothing is quoted until yes, so a wrong 2 is refused with no. None for other sentences.
    """
    words = two_heard_as_to(data.text) if not data.pending else None
    if words is None:
        return None
    allowed = intent_repair.supported(data.live)
    tickers = [intent_repair.ALIASES.get(word.casefold()) for word in words]
    if any(ticker not in allowed for ticker in tickers) or tickers[0] == tickers[1]:
        return None
    try:
        require_live(data.live)
    except QuoteError as error:
        return error_response(error, "en")
    return repair_question({"from_token": tickers[0], "to_token": tickers[1], "amount": "2"}, "en", data.live)


@app.post("/api/ask")
async def ask(data: AskInput, client: OneClick = Depends(get_oneclick)):
    if data.voice:
        return voiced_offer(await ask_by_voice(data, client))
    if data.source == "dictation":
        fixed = from_dictation(data)
        return two_question(fixed) or await answer_ask(fixed, client)
    return await answer_ask(data, client)


async def ask_by_voice(data: AskInput, client: OneClick):
    # Speech writes numbers and token names its own way. Typed text never comes through here.
    text = normalize_voice(data.text.strip())
    waiting = pendings.get(data.pending) if data.pending else None
    if waiting is not None and waiting.kind in ("amount", "repair_amount"):
        text = amount_answer(text)
    data = data.model_copy(update={"text": text})
    guessed = two_question(data)
    if guessed is not None:
        return guessed
    command = detect_command(text) if len(text) <= MAX_SENTENCE else None
    if data.pending and not (command and command[0] == "freeze"):
        lang = data.lang or detect_language(text)
        answered = await answer_voice(data, text, lang)
        if answered is not None:
            return answered
    return await answer_ask(data, client)


async def answer_ask(data: AskInput, client: OneClick):
    text = data.text.strip()
    command = detect_command(text) if len(text) <= MAX_SENTENCE else None
    # The emergency stop never waits behind an open question. The words are the approval.
    if command and command[0] == "freeze":
        if data.pending:
            pendings.drop(data.pending)
        return await run_command(*command)
    if data.pending:
        # "evet" alone gives no language hint, so the page language decides.
        lang = data.lang or detect_language(text)
        return await answer_pending(client, data.pending, text, lang)
    lang = data.lang if data.lang and not text else detect_language(text)
    try:
        if not text:
            raise QuoteError("empty_text")
        if len(text) > MAX_SENTENCE:
            raise QuoteError("too_long")
        if command:
            lang = command[1]
            return await run_command(*command, text, data.live)
        require_live(data.live)
        try:
            intent = await parse_intent(text)
        except ParserUnavailable:
            # With no key, the rules alone may still read the sentence. They suggest, never quote.
            offer = await offer_repair(text, lang, data.live, use_model=False)
            if offer is not None:
                return offer
            raise QuoteError("no_parser", 503) from None
        lang = intent.language
        try:
            return await run_intent(client, intent, data.live)
        except QuoteError as error:
            if error.code not in REPAIRABLE:
                raise
            offer = await offer_repair(text, lang, data.live)
            if offer is not None:
                return offer
            return unrepaired(error, lang, data.live)
    except QuoteError as error:
        return error_response(error, lang, field="text" if error.code in TEXT_ERRORS else None)


def stt_reply(status: int, key: str, lang: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": key, "language": lang, "spoken": say(key, lang)})


@app.get("/api/providers")
async def providers_status():
    """Which services are set up, and which goes first. Never a key."""
    return {
        "transcribe": speech.available(),
        "repair": [service.name for service in intent_repair.repair_chain()] if intent_repair.llm_allowed else [],
        "near_ai": bool(near_ai_key()),
    }


@app.post("/api/transcribe")
async def transcribe_audio(
    request: Request,
    lang: Literal["tr", "en"] = "tr",
    provider: Literal["near_ai", "openai"] | None = None,
):
    """A short recording to text. NEAR AI first, then OpenAI. The page falls back to Web Speech."""
    if not speech.ready():
        return stt_reply(503, "stt_off", lang)
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > speech.MAX_AUDIO_BYTES:
            return stt_reply(413, "stt_too_long", lang)
    if not audio:
        return stt_reply(400, "stt_failed", lang)
    try:
        heard = await speech.transcribe(bytes(audio), request.headers.get("content-type", ""), lang, provider)
    except speech.TranscribeOff:
        return stt_reply(503, "stt_off", lang)
    except speech.TranscribeFailed:
        return stt_reply(502, "stt_failed", lang)
    return {"language": lang, **heard}


@app.post("/api/quote")
async def quote(data: QuoteInput, client: OneClick = Depends(get_oneclick)):
    try:
        require_live(data.live)
        amount = number_or_same(data.amount, data.lang)
        return await run_swap(
            client, data.from_token, None, data.to_token, None, amount, data.lang, data.live
        )
    except QuoteError as error:
        return error_response(error, data.lang, field=form_field(error, data))


@app.post("/api/live/status")
async def live_status(data: TrackInput):
    view = await read_operation(data.track)
    content = {
        "action": "live_status",
        "mode": "live",
        "language": data.lang,
        "state": view["state"],
        "final": view["final"],
        "spoken": say_live_status(view, data.lang),
    }
    if view.get("proof"):
        content["proof"] = view["proof"]
        content["proof_key"] = view["proof_key"]
        content["copies"] = view["proofs"]
    return content


@app.post("/api/mode")
async def mode(data: ModeInput):
    try:
        require_live(data.live)
    except QuoteError as error:
        return error_response(error, data.lang)
    return {**reply("mode", "live_on" if data.live else "live_off", data.lang), "live": data.live}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
