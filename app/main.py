"""nearagent API. Serves the page, sentence requests, and the advanced form."""
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

# Only the readiness check is imported: nothing in this file can reach a money action.
from app.agent_api import live_ready  # noqa: E402
from app.confirm import Pending, PendingStore, answer_word, read_amount  # noqa: E402
from app.intent import Intent, ParserUnavailable, parse_intent  # noqa: E402
from app.messages import (  # noqa: E402
    detect_language,
    from_atomic,
    say,
    say_assumed,
    say_error,
    say_large,
    say_price,
    say_quote,
)
from app.oneclick import (  # noqa: E402
    OneClick,
    QuoteError,
    build_quote_request,
    find_token,
    parse_amount,
    to_atomic,
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_TOKEN_TEXT = 64
MAX_SENTENCE = 300
LARGE_USD = Decimal(100)

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


async def run_swap(
    client: OneClick,
    from_token: str,
    from_chain: str | None,
    to_token: str,
    to_chain: str | None,
    amount: str,
    lang: str,
    live: bool = False,
) -> dict:
    origin, origin_assumed, destination, destination_assumed = await resolve_pair(
        client, from_token, from_chain, to_token, to_chain
    )
    atomic = to_atomic(amount, origin["decimals"])
    # Live execution is not connected: even live mode only ever asks for dry quotes.
    body = build_quote_request(
        origin["assetId"], destination["assetId"], atomic, client.account, dry=True
    )
    result = await client.quote(body)
    details = result["quote"]
    min_out = from_atomic(details["minAmountOut"], destination["decimals"])
    assumed = [t for t, flag in ((origin, origin_assumed), (destination, destination_assumed)) if flag]
    terms = say_quote(details, origin["symbol"], destination["symbol"], min_out, lang, live)

    value_in = Decimal(details.get("amountInUsd") or 0)
    if value_in > LARGE_USD:
        kind, question = "large", say_large(value_in, lang, live)
    else:
        kind, question = "confirm", say("confirm_question_live" if live else "confirm_question", lang)
    return {
        "action": "swap",
        "mode": "live" if live else "dry",
        "language": lang,
        "pending": pendings.add(kind, lang, live=live),
        "confirm_button": live,
        "spoken": f"{terms}{say_assumed(assumed, lang)} {question}",
        "quote": {
            "from": origin["assetId"],
            "to": destination["assetId"],
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
    return {
        "action": "price",
        "language": lang,
        "spoken": say_price(amount, token, lang) + say_assumed([token] if assumed else [], lang),
    }


async def run_intent(client: OneClick, intent: Intent, live: bool = False) -> dict:
    lang = intent.language
    if intent.action == "help":
        return reply("help", "help", lang)
    if intent.action == "price":
        return await run_price(client, intent)
    swap = {
        "from_token": intent.from_token or "",
        "from_chain": intent.from_chain,
        "to_token": intent.to_token or "",
        "to_chain": intent.to_chain,
    }
    if intent.amount:
        return await run_swap(client, amount=intent.amount, lang=lang, live=live, **swap)
    # Check the tokens first, so nobody answers a question for a swap that cannot happen.
    await resolve_pair(client, **swap)
    return reply("ask_amount", "missing_amount", lang, pendings.add("amount", lang, swap, live))


async def answer_amount(client: OneClick, key: str, item: Pending, text: str) -> dict | JSONResponse:
    amount = read_amount(text, item.swap["from_token"])
    if amount is None:
        return reply("ask_amount", "amount_again", item.lang, key)
    try:
        offer = await run_swap(client, amount=amount, lang=item.lang, live=item.live, **item.swap)
    except QuoteError as error:
        # The tokens stay valid, so the user can answer again with another amount.
        return error_response(error, item.lang, key)
    pendings.drop(key)
    return offer


def ask_again(item: Pending, key: str, message: str) -> dict:
    return {**reply(item.kind, message, item.lang, key), "confirm_button": item.live}


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
        return {**reply("confirmed", "live_not_connected", item.lang), "mode": "live"}
    return {**reply("confirmed", "confirmed_dry", item.lang), "mode": "dry"}


@app.post("/api/ask")
async def ask(data: AskInput, client: OneClick = Depends(get_oneclick)):
    text = data.text.strip()
    if data.pending:
        # "evet" alone gives no language hint, so the page language decides.
        lang = data.lang or detect_language(text)
        return await answer_pending(client, data.pending, text, lang)
    lang = data.lang if data.lang and not text else detect_language(text)
    try:
        require_live(data.live)
        if not text:
            raise QuoteError("empty_text")
        if len(text) > MAX_SENTENCE:
            raise QuoteError("too_long")
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
        return await run_swap(
            client, data.from_token, None, data.to_token, None, data.amount, data.lang, data.live
        )
    except QuoteError as error:
        return error_response(error, data.lang)


@app.post("/api/mode")
async def mode(data: ModeInput):
    try:
        require_live(data.live)
    except QuoteError as error:
        return error_response(error, data.lang)
    return {**reply("mode", "live_on" if data.live else "live_off", data.lang), "live": data.live}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
