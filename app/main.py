"""nearagent API. Serves the page, sentence requests, and the advanced form."""
from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

# The money methods stay behind app/live.py, which checks everything again before sending.
from app.agent_api import (  # noqa: E402
    AgentApiError,
    AgentApiRequestError,
    agent_ready,
    live_ready,
    read_agent_balances,
    read_agent_policy,
)
from app.amounts import number_or_same, read_answer  # noqa: E402
from app.commands import detect_command  # noqa: E402
from app.history import history  # noqa: E402
from app.live import QUOTE_MINUTES, execute_order, prepare_order, read_operation  # noqa: E402
from app.confirm import (  # noqa: E402
    Pending,
    PendingStore,
    answer_word,
    code_matches,
    new_code,
)
from app.intent import Intent, ParserUnavailable, parse_intent  # noqa: E402
from app.messages import (  # noqa: E402
    detect_language,
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
    say_usd_note,
)
from app.owner import (  # noqa: E402
    OwnerError,
    OwnerKeyMissing,
    ResultPending,
    control_agent,
    owner_ready,
)
from app.oneclick import (  # noqa: E402
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


class ModeInput(BaseModel):
    live: bool = False
    lang: Literal["tr", "en"] = "tr"


class TrackInput(BaseModel):
    track: str = ""
    lang: Literal["tr", "en"] = "tr"


def get_oneclick() -> OneClick:
    return oneclick


def error_response(error: QuoteError, lang: str, pending: str | None = None) -> JSONResponse:
    content = {
        "error": error.code,
        "language": lang,
        "spoken": say_error(error.code, lang, error.details),
    }
    if pending:
        content["pending"] = pending
    return JSONResponse(status_code=error.status, content=content)


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
        "pending": pendings.add(kind, lang, live=True, order=order),
        "confirm_button": True,
        "spoken": f"{terms}{warning}{say_assumed(assumed, lang)} {question}",
        "quote": {"from": origin["assetId"], "to": destination["assetId"]},
    }


async def run_live(item: Pending) -> dict | JSONResponse:
    """Send a confirmed order, or ask again if anything changed since the user heard it."""
    try:
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


async def run_command(command: str, lang: str) -> dict:
    if command == "history":
        return run_history(lang)
    if not agent_ready():
        return reply(command, "no_agent", lang)
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


@app.post("/api/ask")
async def ask(data: AskInput, client: OneClick = Depends(get_oneclick)):
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
            return await run_command(*command)
        require_live(data.live)
        try:
            intent = await parse_intent(text)
        except ParserUnavailable:
            raise QuoteError("no_parser", 503) from None
        lang = intent.language
        return await run_intent(client, intent, data.live)
    except QuoteError as error:
        return error_response(error, lang)


@app.post("/api/quote")
async def quote(data: QuoteInput, client: OneClick = Depends(get_oneclick)):
    try:
        require_live(data.live)
        amount = number_or_same(data.amount, data.lang)
        return await run_swap(
            client, data.from_token, None, data.to_token, None, amount, data.lang, data.live
        )
    except QuoteError as error:
        return error_response(error, data.lang)


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
    return content


@app.post("/api/mode")
async def mode(data: ModeInput):
    try:
        require_live(data.live)
    except QuoteError as error:
        return error_response(error, data.lang)
    return {**reply("mode", "live_on" if data.live else "live_off", data.lang), "live": data.live}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
