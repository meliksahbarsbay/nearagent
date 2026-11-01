# nearagent

An accessibility-first crypto assistant for NEAR Intents. Built at NEAR HACKATHON.

## Problem

Swap interfaces are visual: charts, popups, and icon-only buttons. A blind user on a screen reader often cannot tell what a swap will cost or what they will receive. nearagent answers in one short sentence that a screen reader reads aloud, and every step works from the keyboard.

## What works today

- One text box. Write a sentence in Turkish or English, for example `50 USDC'yi Solana'da SOL'a çevir`, `swap 2 NEAR to USDC on Base`, or `1 SOL kaç dolar`.
- The reply language follows the sentence, and the reply is read from one `aria-live` area.
- `POST /api/ask` extracts `action` (swap, price, or help), `amount`, `from_token`, `from_chain`, `to_token`, `to_chain`, and `language` as schema-checked JSON.
- If a token is on several chains and no chain is named, the app picks a default and says so. SOL uses Solana, ETH uses Ethereum, BTC uses Bitcoin, and USDC uses NEAR.
- Every swap quote is read in one fixed order: what you give, what you get, the guaranteed minimum, the fee, the time, and how long the quote is valid. Then it asks you to confirm.
- `evet`, `yes`, or Enter on the empty box confirms. `hayır`, `iptal`, `no`, or Esc cancels. Any other answer is asked again, and never counts as a yes.
- Above 100 dollars, it first spells the amount and asks if you meant it, for example `Yaklaşık beş yüz dolar mı dedin?`
- A confirmation is held on the server, works once, belongs to one quote, and expires with that quote.
- If a sentence has no amount, it asks how much and applies your answer to the same swap.
- Numbers are written for screen readers: a comma in Turkish, a dot in English, no extra zeros. Long identifiers are never read aloud, and each one has a copy button.
- Every error says what happened and what to do next, with no codes.
- Shortcuts: Enter sends or confirms, Esc cancels, Alt+R repeats the last reply, and Alt+H reads the help. The text box also announces them through hidden help text.
- An Advanced section keeps a field-based form, `POST /api/quote`, which works with no keys.
- Dry mode only. The code cannot execute a swap today, so a confirmation only replies `Deneme modu: işlem yapılmadı.`

## Planned, not built yet

- Voice input.
- Live execution through a policy-bound Agent API wallet. It is mainnet only and uses real funds, so it will stay off by default, use a separate account with small amounts, and require explicit user confirmation for every action.

## How NEAR is used

- NEAR AI Cloud parses sentences through its OpenAI-compatible API. The default model is `z-ai/glm-5.3-flash`, listed as Private TEE. OpenAI is the fallback, used when the NEAR AI key is missing or NEAR AI fails.
- NEAR Intents 1Click API supplies token data, prices, and quotes.
- Dry and live quotes share one code path, and both use `INTENTS` for `depositType`, `refundType`, and `recipientType`. Only the `dry` flag differs.

## Run it

Requires Python 3.10 or later.

```sh
git clone https://github.com/meliksahbarsbay/nearagent.git
cd nearagent
python -m venv .venv
```

Activate on macOS or Linux: `source .venv/bin/activate`

Activate on Windows PowerShell: `.venv\Scripts\Activate.ps1`

```sh
python -m pip install -r requirements.txt
```

Sentences need a key. Copy `.env.example` to `.env`, then set `NEAR_AI_API_KEY` or `OPENAI_API_KEY`. Without a key, the text box says parsing is off and the Advanced form still works.

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Try it: do X, see Y

Prices below are examples, so your numbers will differ. Steps 3 to 10 need a key. Each step starts from an empty text box.

1. Do: run `python -m pytest -q`. See: all tests pass, with no network calls.
2. Do: open http://127.0.0.1:8000 and press Tab. See: focus lands on the text box labelled `Ne yapmak istiyorsun?`, and a screen reader also reads the shortcuts.
3. Do: type `1 SOL kaç dolar` and press Enter. See: a sentence like `1 SOL yaklaşık 95,93 dolar. Solana üzerindeki SOL'u kullandım; başka zincir istersen söyle.`
4. Do: type `50 USDC'yi Solana'da SOL'a çevir` and press Enter. See: `Deneme modu. Veriyorsun: 50 USDC. Alıyorsun: yaklaşık ...`, ending with `Onaylıyor musun? Evet de ya da Enter'a bas.`
5. Do: press Alt+R. See: the same reply again. Then press Enter on the empty box. See: `Deneme modu: işlem yapılmadı.`
6. Do: type `500 USDC'yi SOL'a çevir` and press Enter. See: the quote, ending with `Yaklaşık beş yüz dolar mı dedin?` Then press Enter. See: `Onaylıyor musun?` Then press Esc. See: `İptal ettim, işlem yapılmadı.`
7. Do: type `swap NEAR to USDC` and press Enter. See: `How much do you want to convert?` Then type `2` and press Enter. See: an English dry quote for 2 wNEAR. Then type `no` and press Enter. See: a cancel message.
8. Do: type `swap 2 NEAR to USDC` and press Enter, then Tab to the first `Copy` button and press Enter. See: `Copied.` Press Esc to cancel the quote.
9. Do: type `merhaba` and press Enter. See: a short Turkish help message. Then press Alt+H. See: how to use the page and its shortcuts.
10. Do: type `5 ABCD'yi SOL'a çevir` and press Enter. See: `ABCD tokenini bulamadım. Token adını kontrol edip yeniden yaz.`
11. Do: Tab to the Advanced section and press Enter to open it, Tab to the submit button, and press Enter. See: a dry quote from the field-based form, with focus back in the text box for your answer. This step needs no key.
12. Do: call the API directly:

```sh
curl -X POST http://127.0.0.1:8000/api/quote -H "Content-Type: application/json" -d "{\"from_token\":\"NEAR\",\"to_token\":\"USDC\",\"amount\":\"1\",\"lang\":\"en\"}"
```

See: JSON with `"mode":"dry"`, a `spoken` sentence, a `quote` object, a `correlationId`, and a `pending` value. Send that value back to `POST /api/ask` with `{"text":"evet","pending":"..."}` to answer the question.

## Parser evaluation

`tests/intent_cases.json` holds 30 sentences, 15 Turkish and 15 English, with expected JSON. `python -m pytest -m live` compares a real provider with them. This run needs a key and costs a small amount.

Latest result with OpenAI `gpt-6-luna`: 30 of 30, in three runs in a row. The first run scored 29 of 30, and repeated runs showed two sentences that failed some of the time. The prompt and one rule in code were then changed after seeing those failures, so this score is not from unseen data. The rule moves a chain to the source side when Turkish says `Solana'da`, because the model sometimes put it on the wrong side.

NEAR AI Cloud has not been measured on this set yet.

## Known limits

- `NEAR` maps to `wNEAR`, because 1Click lists NEAR that way on the NEAR chain.
- Some quotes fail upstream with no specific reason, for example when the amount is too low. The app then gives a general spoken message.
- Prices come from the 1Click token list, so they may be a few minutes old.
- Sending to a person or a wallet address is not supported. Those sentences get the help reply.
- 1Click reports no total fee, so the spoken fee is `amountInUsd` minus `amountOutUsd`. It covers fees and price difference together.
- Dry quotes return no deadline, so the spoken validity is the 10 minutes the app requests.
- Amounts are rounded down, so a guaranteed minimum is never read out higher than it is. Very small amounts keep four significant digits, even past six decimals, or they would read as zero.
- An answer to `how much` must be a number, or a simple word such as `yarım` or `two`. `50 dolar` and `1.000` are asked again, because they could mean a different amount.
- Open questions live in server memory, so a restart ends them and the page says the quote expired.
- Tests cover the server. The page's keyboard behaviour was checked by hand in Chrome.

## Configuration

All settings are optional in dry mode. See `.env.example`. Keys belong in `.env`, which git ignores.

## Stack and disclosures

- Backend: Python, FastAPI, httpx, uvicorn, python-dotenv. Tests: pytest.
- Frontend: plain HTML and vanilla JavaScript, no framework.
- All code was written for this hackathon, with AI assistance from Claude Code.
- NEAR agent skills `near-intents` and `near-ai-cloud` were used as references. `skills-lock.json` records them.

## License

MIT. See `LICENSE`.
