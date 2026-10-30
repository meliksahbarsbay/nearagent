"""nearagent API. Serves the page and one dry-run quote endpoint."""
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from app.messages import from_atomic, say, say_quote  # noqa: E402
from app.oneclick import (  # noqa: E402
    OneClick,
    QuoteError,
    build_quote_request,
    find_token,
    to_atomic,
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_TEXT = 64

app = FastAPI(title="nearagent")
oneclick = OneClick()


class QuoteInput(BaseModel):
    from_token: str = ""
    to_token: str = ""
    amount: str = ""
    lang: Literal["tr", "en"] = "tr"


def get_oneclick() -> OneClick:
    return oneclick


@app.post("/api/quote")
async def quote(data: QuoteInput, client: OneClick = Depends(get_oneclick)):
    try:
        if not data.from_token.strip() or not data.to_token.strip():
            raise QuoteError("missing_token")
        if max(len(data.from_token), len(data.to_token)) > MAX_TEXT:
            raise QuoteError("unknown_token", 404, symbol="")
        tokens = await client.tokens()
        origin = find_token(tokens, data.from_token)
        destination = find_token(tokens, data.to_token)
        if origin["assetId"] == destination["assetId"]:
            raise QuoteError("same_token")
        amount = to_atomic(data.amount, origin["decimals"])
        # Live execution is not built: this endpoint only ever asks for dry quotes.
        body = build_quote_request(
            origin["assetId"], destination["assetId"], amount, client.account, dry=True
        )
        result = await client.quote(body)
    except QuoteError as error:
        return JSONResponse(
            status_code=error.status,
            content={"error": error.code, "spoken": say(error.code, data.lang, **error.details)},
        )
    details = result["quote"]
    min_out = from_atomic(details["minAmountOut"], destination["decimals"])
    return {
        "mode": "dry",
        "spoken": say_quote(details, origin["symbol"], destination["symbol"], min_out, data.lang),
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


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
