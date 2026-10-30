# nearagent

An accessibility-first crypto assistant for NEAR Intents. Built at NEAR HACKATHON.

## Problem

Swap interfaces are visual: charts, popups, and icon-only buttons. A blind user on a screen reader often cannot tell what a swap will cost or what they will receive. nearagent answers in one short sentence that a screen reader reads aloud, and every step works from the keyboard.

## What works today

- A single page with labelled fields, full keyboard use, and one `aria-live` result area.
- `POST /api/quote`: looks up tokens with 1Click `GET /v0/tokens`, requests a dry quote with `POST /v0/quote`, and returns a spoken sentence in Turkish or English.
- Dry mode only. The code cannot execute a swap today, and no keys are needed.

## Planned, not built yet

- Voice and free-text input, parsed by NEAR AI Cloud with OpenAI as fallback.
- Live execution through a policy-bound Agent API wallet. It is mainnet only and uses real funds, so it will stay off by default, use a separate account with small amounts, and require explicit user confirmation for every action.

## How NEAR is used

- NEAR Intents 1Click API for token data and quotes.
- Dry and live quotes share one code path, and both use `INTENTS` for `depositType`, `refundType`, and `recipientType`. Only the `dry` flag differs.

## Run it

Requires Python 3.10 or later. No keys or accounts are needed.

```sh
git clone https://github.com/meliksahbarsbay/nearagent.git
cd nearagent
python -m venv .venv
```

Activate on macOS or Linux: `source .venv/bin/activate`

Activate on Windows PowerShell: `.venv\Scripts\Activate.ps1`

```sh
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Try it: do X, see Y

Prices below are examples, so your numbers will differ.

1. Do: run `python -m pytest -q`. See: all tests pass, with no network calls.
2. Do: open http://127.0.0.1:8000. See: a form with fields for language, token to send, token to receive, and amount.
3. Do: press Tab until the submit button has focus, then press Enter. See: the Result area gets a sentence like `Deneme modu. 1 wNEAR karşılığında yaklaşık 4,2854 USDC alırsın. En az 4,242546 USDC. Tahmini süre 12 saniye. Hiçbir işlem yapılmadı.`
4. Do: choose English in the language field and submit again. See: `Dry run. For 1 wNEAR you would get about ...`
5. Do: enter `abc` as the amount and submit. See: a spoken error asking for a number above zero.
6. Do: enter `XXXX` as the token to receive and submit. See: a spoken error saying the token was not found.
7. Do: call the API directly:

```sh
curl -X POST http://127.0.0.1:8000/api/quote -H "Content-Type: application/json" -d "{\"from_token\":\"NEAR\",\"to_token\":\"USDC\",\"amount\":\"1\",\"lang\":\"en\"}"
```

See: JSON with `"mode":"dry"`, a `spoken` sentence, a `quote` object, and a `correlationId`.

## Known limits

- `NEAR` maps to `wNEAR`, because 1Click lists NEAR that way on the NEAR chain.
- A symbol resolves to its NEAR chain token. A symbol on several chains but not on NEAR, such as `SOL`, returns a spoken error for now.
- Some quotes fail upstream with no specific reason, for example when the amount is too low. The app then gives a general spoken message.

## Configuration

All settings are optional in dry mode. See `.env.example`. Keys belong in `.env`, which git ignores.

## Stack and disclosures

- Backend: Python, FastAPI, httpx, uvicorn, python-dotenv. Tests: pytest.
- Frontend: plain HTML and vanilla JavaScript, no framework.
- All code was written for this hackathon, with AI assistance from Claude Code.
- NEAR agent skills `near-intents` and `near-ai-cloud` were used as references. `skills-lock.json` records them.

## License

MIT. See `LICENSE`.
