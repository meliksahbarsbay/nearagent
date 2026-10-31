"""nearagent API. Serves the page, sentence requests, and the advanced form."""
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from app.intent import Intent, ParserUnavailable, parse_intent  # noqa: E402
from app.messages import (  # noqa: E402
    detect_language,
    from_atomic,
    say,
    say_assumed,
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

app = FastAPI(title="nearagent")
oneclick = OneClick()


class QuoteInput(BaseModel):
    from_token: str = ""
    to_token: str = ""
    amount: str = ""
    lang: Literal["tr", "en"] = "tr"


class AskInput(BaseModel):
    text: str = ""


def get_oneclick() -> OneClick:
    return oneclick


def error_response(error: QuoteError, lang: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content={
            "error": error.code,
            "language": lang,
            "spoken": say(error.code, lang, **error.details),
        },
    )


async def run_swap(
    client: OneClick,
    from_token: str,
    from_chain: str | None,
    to_token: str,
    to_chain: str | None,
    amount: str,
    lang: str,
) -> dict:
    if not from_token.strip() or not to_token.strip():
        raise QuoteError("missing_token")
    if max(len(from_token), len(to_token)) > MAX_TOKEN_TEXT:
        raise QuoteError("unknown_token", 404, symbol="")
    tokens = await client.tokens()
    origin, origin_assumed = find_token(tokens, from_token, from_chain)
    destination, destination_assumed = find_token(tokens, to_token, to_chain)
    if origin["assetId"] == destination["assetId"]:
        raise QuoteError("same_token")
    atomic = to_atomic(amount, origin["decimals"])
    # Live execution is not built: this path only ever asks for dry quotes.
    body = build_quote_request(
        origin["assetId"], destination["assetId"], atomic, client.account, dry=True
    )
    result = await client.quote(body)
    details = result["quote"]
    min_out = from_atomic(details["minAmountOut"], destination["decimals"])
    assumed = [t for t, flag in ((origin, origin_assumed), (destination, destination_assumed)) if flag]
    spoken = say_quote(details, origin["symbol"], destination["symbol"], min_out, lang)
    return {
        "action": "swap",
        "mode": "dry",
        "language": lang,
        "spoken": spoken + say_assumed(assumed, lang),
        "quote": {
            "from": origin["assetId"],
            "to": destination["assetId"],
            "amountIn": details["amountInFormatted"],
            "amountOut": details["amountOutFormatted"],
            "minAmountOut": min_out,
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


async def run_intent(client: OneClick, intent: Intent) -> dict:
    if intent.action == "help":
        return {
            "action": "help",
            "language": intent.language,
            "spoken": say("help", intent.language),
        }
    if intent.action == "price":
        return await run_price(client, intent)
    if not intent.amount:
        raise QuoteError("missing_amount")
    return await run_swap(
        client,
        intent.from_token or "",
        intent.from_chain,
        intent.to_token or "",
        intent.to_chain,
        intent.amount,
        intent.language,
    )


@app.post("/api/ask")
async def ask(data: AskInput, client: OneClick = Depends(get_oneclick)):
    text = data.text.strip()
    lang = detect_language(text)
    try:
        if not text:
            raise QuoteError("empty_text")
        if len(text) > MAX_SENTENCE:
            raise QuoteError("too_long")
        try:
            intent = await parse_intent(text)
        except ParserUnavailable:
            raise QuoteError("no_parser", 503) from None
        lang = intent.language
        return await run_intent(client, intent)
    except QuoteError as error:
        return error_response(error, lang)


@app.post("/api/quote")
async def quote(data: QuoteInput, client: OneClick = Depends(get_oneclick)):
    try:
        return await run_swap(
            client, data.from_token, None, data.to_token, None, data.amount, data.lang
        )
    except QuoteError as error:
        return error_response(error, data.lang)


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
