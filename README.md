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
- Shortcuts: Enter sends or confirms, Esc cancels, Alt+M turns on the microphone, Alt+R repeats the last reply, and Alt+H reads the help. The text box also announces them through hidden help text.
- Voice input through the browser's Web Speech API. It uses Turkish or English to match the page, announces `Dinliyorum` and `Anladım: ...`, and writes what it heard into the text box. It never sends by itself: you check the text and press Enter.
- An Advanced section keeps a field-based form, `POST /api/quote`, which works with no keys.
- Dry mode by default. A dry confirmation only replies `Deneme modu: işlem yapılmadı.`
- Amounts as people say them, read in code: `yarım SOL`, `bir buçuk NEAR`, `half a SOL`, `one and a half`, `1.000`, and `1,5`. Dollars work too: `50 dolarlık SOL al` and `fifty dollars of SOL`.
- `son işlemlerimi oku` or `read my recent trades` reads the last 5 confirmed trades, dry and live, with date, what was given and received, and status. Long identifiers stay out of the sentence, and each trade has a copy button.
- Agent commands, typed or spoken: `cüzdanımda ne var`, `politikamı oku`, `bütçem ne kadar kaldı`, `ajanı dondur`, and `ajanı çöz`, or `what's my balance`, `read my policy`, `how much budget is left`, `freeze the agent`, and `unfreeze the agent`. With no agent they reply `Ajan cüzdanı kurulmadı`. The wallet is read token by token, with dollar values.
- `ajanı dondur` is the emergency stop. It takes one step, needs no language model, and cuts through any open question, so the command itself is the owner's approval. It signs with the owner key and reports success only after the API confirms it.
- `ajanı çöz` signs nothing at first. It says what would happen and gives a six digit code, and only that code signs. Enter and `evet` do not. Three wrong codes end the attempt.
- A live mode switch in the Advanced section. It stays off with the reply `Canlı mod için ajan cüzdanı kurulmadı` unless `LIVE_ENABLED=true` and the Agent API key, `AGENT_ID`, and `GRANT_TOKEN` are all set.
- In live mode, Enter alone never confirms. You must type `evet` or `yes`, or press a separate Confirm button.

## Live mode: off until funded

Live mode is off, and it stays off until the agent is funded. No agent exists yet, no real funds are held, and nothing here has run against NEAR mainnet. Live swaps have only been tested against a local stand-in for the Agent API.

The first real swap needs the owner's explicit approval, once funds arrive. It is mainnet only, with real money, in a dedicated account.

### How a live swap works

`app/live.py` is the only app file that can spend. Every swap follows the same order:

1. The app checks the agent is active. A frozen agent replies `Ajan dondurulmuş, çözmek için ajanı çöz de.` and nothing starts. A frozen state it cannot confirm counts as frozen.
2. It takes a dry quote from the agent's own account and reads the terms. The quote is valid for 2 minutes.
3. It waits for a typed `evet` or the Confirm button.
4. Just before sending, it checks the agent again and takes a fresh quote. If the quote has expired, or the output or dollar value moved by more than 0.5%, it reads the new terms and asks again.
5. It checks its own limits, counts the swap, and sends it with one idempotency key. If the answer is lost, it sends the same request once more with the same key.
6. It follows the result in plain words: processing, done with the amount received and a copy button for the transaction link, refunded with where the money went, or failed.

An unknown result is never sent again under a new key. The page says so and tells you to check the balance.

The app's limits sit on top of the owner's signed policy. `MAX_LIVE_USD` caps one swap, with a default of 5. `MAX_LIVE_DAILY_USD` caps the last 24 hours, with a default of 10. The total is stored in `data/live_spend.json`, so a restart cannot reset it. A swap stays counted unless it is proven that nothing was sent, so a refund still counts. If that file cannot be read, live swaps stop.

### Funding

Funding uses real money and needs two transfers, about 0.1 NEAR and about 10 USDC:

1. Get a partner API key from https://partners.near-intents.org and add it to `.env` as `NEAR_INTENTS_AGENT_API_KEY`.
2. Install the signer and create the owner key. This needs Node 20 or later:

   ```sh
   cd scripts/owner
   npm ci --ignore-scripts
   cd ../..
   node scripts/owner/generate_key.mjs
   ```

   It writes a new ed25519 key to `.env`, which must be ignored by git, and prints only the owner's implicit account address. It refuses to replace an existing key. There is no recovery for a lost owner key, so back it up.
3. Send 0.1 NEAR to that owner address. The account appears on chain with its first transfer. The 0.1 follows the NEAR docs' example, and is not a required minimum.
4. Run `python scripts/owner_setup.py plan`. It prints the rules and a code, and signs nothing.
5. Run `python scripts/owner_setup.py create --onay=CODE`, then `grant --onay=CODE`. They sign only the saved rules, and stop if the API prepared anything different. The plan is valid for one hour.
6. Run `python scripts/owner_setup.py deposit`. It prints a one-time address. Send about 10 USDC to it on the Base network, and only to that address. A repeat run shows the same address, and `--yeni` asks for a new one.
7. Run `python scripts/owner_setup.py balance` to see the funds arrive.
8. Set `LIVE_ENABLED=true` in `.env` and restart the app. Only do this for the first real swap, after the owner approves it.

`freeze` stops the agent from a terminal, in one step. `unfreeze` prints a code, and `unfreeze --onay=CODE` signs. Unfreezing has a 10 minute cooldown on the API's side. Freezing has none.

The rules: swap, plus withdraw only to the owner's address, for USDC on NEAR and Base, wNEAR, SOL, and ETH, with 10 dollars a day and 10 actions an hour. The API has no per-transaction dollar cap, so the 5 dollar cap is converted to token amounts at the prices when the plan was made. If a token's price rises, that cap rises in dollars. The daily cap stays in dollars.

The signing approach follows the Agent API documentation and its examples. That examples repository states no license, so no code was copied from it.

## How NEAR is used

- NEAR AI Cloud parses sentences through its OpenAI-compatible API. The default model is `z-ai/glm-5.3-flash`, listed as Private TEE. OpenAI is the fallback, used when the NEAR AI key is missing or NEAR AI fails.
- NEAR Intents 1Click API supplies token data, prices, and quotes in dry mode, always with `INTENTS` for `depositType`, `refundType`, and `recipientType`.
- The NEAR Intents Agent API runs live swaps from a policy-bound agent wallet, which holds its funds in its own NEAR Intents account.

## Run it in 5 minutes

Dry mode needs no wallet, no funds, and no keys. It moves no money. It needs Python 3.10 or later.

1. Do: get the code and install it.

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

2. Do: run `python -m pytest -q`. See: all tests pass with no network calls. One signer test is skipped until the Node tools are installed.
3. Do: run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`, and open http://127.0.0.1:8000.
4. Do: press Tab until you reach the `Gelişmiş` section, press Enter to open it, Tab to `Deneme teklifi al`, and press Enter. See: a real dry quote for 1 wNEAR to USDC read in fixed order, ending with `Onaylıyor musun?` This uses the public 1Click API.
5. Do: press Enter on the empty text box. See: `Deneme modu: işlem yapılmadı.`
6. Do: type `ajanı dondur` and press Enter. See: `Ajan cüzdanı kurulmadı. Kurulum bitince yeniden dene.`

Sentences such as `1 SOL kaç dolar` need a key. Copy `.env.example` to `.env`, set `NEAR_AI_API_KEY` or `OPENAI_API_KEY`, and restart. Without a key, the text box says parsing is off and the form still works.

## Try it: do X, see Y

Prices below are examples, so your numbers will differ. Steps 3 to 10, 12, and 13 need a key. Each step starts from an empty text box.

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
11. Do: type `politikamı oku` and press Enter, then do the same with `cüzdanımda ne var`, `bütçem ne kadar kaldı`, `ajanı dondur`, and `ajanı çöz`. See: `Ajan cüzdanı kurulmadı. Kurulum bitince yeniden dene.` each time. This step needs no key.
12. Do: in Chrome or Edge, press Alt+M and allow the microphone, then say `bir SOL kaç dolar`. See: `Dinliyorum`, then `Anladım: ...`, and the text in the box. Nothing is sent until you press Enter.
13. Do: type `50 dolarlık SOL al` and press Enter. See: `Veriyorsun: en çok ...`, then `Alıyorsun: tam ...`, because the amount you named is what arrives. Then type `evet` and press Enter. This step needs a key.
14. Do: type `son işlemlerimi oku` and press Enter. See: the date, what was given and received, and the status, with a `Kopyala` button for each trade and no long identifiers read aloud. This step needs a confirmed quote, and no key if it came from the Advanced form.
15. Do: Tab to the Advanced section and press Enter to open it, then press Enter on the `Canlı mod` button. See: `Canlı mod için ajan cüzdanı kurulmadı. Deneme modunda devam edebilirsin.` This step needs no key.
16. Do: Tab to the submit button in the Advanced section and press Enter. See: a dry quote from the field-based form, with focus back in the text box for your answer. This step needs no key.
17. Do: call the API directly:

```sh
curl -X POST http://127.0.0.1:8000/api/quote -H "Content-Type: application/json" -d "{\"from_token\":\"NEAR\",\"to_token\":\"USDC\",\"amount\":\"1\",\"lang\":\"en\"}"
```

See: JSON with `"mode":"dry"`, a `spoken` sentence, a `quote` object, a `correlationId`, and a `pending` value. Send that value back to `POST /api/ask` with `{"text":"evet","pending":"..."}` to answer the question.

## Parser evaluation

`tests/intent_cases.json` holds 30 sentences, 15 Turkish and 15 English, with expected JSON. `tests/amount_cases.json` adds 14 sentences on amounts. `python -m pytest -m live` compares a real provider with them. This run needs a key and costs a small amount.

Latest result with OpenAI `gpt-6-luna`: 44 of 44, in three runs in a row. Earlier runs showed sentences that failed some of the time, and the prompt and code rules were changed after seeing those failures, so this score is not from unseen data. Code decides three things the model got wrong at times: a chain after Turkish `Solana'da` is the source, amounts are read in code, and `50 dolar kaç SOL` is a question, not an offer.

NEAR AI Cloud has not been measured on this set yet.

## Known limits

- `NEAR` maps to `wNEAR`, because 1Click lists NEAR that way on the NEAR chain.
- `1.000` follows the sentence's language: a thousand in Turkish, and one in English. The quote reads the amount back before you confirm.
- A number counts only when a token or a dollar word follows it, so `bir` as a plain word is not read as an amount. A number with no such word falls back to what the language model read.
- A sentence that buys without saying how to pay uses USDC, and the quote says so.
- Dollar amounts use the token's current list price, so the real value can differ slightly. In dry mode a bought amount uses `EXACT_OUTPUT`. The Agent API takes an exact input only, so in live mode every amount becomes the input that matches it at the current price.
- Trade history is stored in `data/history.json` on this computer. It is a convenience, and the Agent API holds the real record of a live swap. A swap still running when the app restarts stays marked as processing.
- Reading the wallet was tested against a stand-in, not the real Agent API.
- Some quotes fail upstream with no specific reason, for example when the amount is too low. The app then gives a general spoken message.
- Prices come from the 1Click token list, so they may be a few minutes old.
- Sending to a person or a wallet address is not supported. Those sentences get the help reply.
- 1Click reports no total fee, so the spoken fee is `amountInUsd` minus `amountOutUsd`. It covers fees and price difference together.
- Dry quotes return no deadline, so the spoken validity is the 10 minutes the app requests.
- Amounts are rounded down, so a guaranteed minimum is never read out higher than it is. Very small amounts keep four significant digits, even past six decimals, or they would read as zero.
- An answer to `how much` must be only an amount, such as `yarım`, `bir buçuk`, `50 dolar`, or `50 USDC`. A unit that is neither dollars nor one of the swap's tokens is asked again.
- Open questions live in server memory, so a restart ends them and the page says the quote expired.
- Tests cover the server. The page's keyboard behaviour was checked by hand in Chrome.
- Voice recognition was checked with a stand-in recognizer, not a real microphone. Chrome and Edge may send audio to their own speech service, unlike sentence parsing on NEAR AI Cloud.
- Voice input follows the page language, so an English sentence on a Turkish page may be misheard. Change the language in the Advanced section first.
- Owner signing runs from a key in `.env`, not a wallet. Keep only a small amount in a dedicated owner account.
- Freezing and unfreezing were tested with the real signer against a local stand-in API, not the real Agent API. Real timing will be slower. If the result takes more than about 30 seconds, the page says it is not known yet and never claims success.
- A spoken `ajanı dondur` still needs Enter, because voice input never sends by itself.
- The Agent API documents the live quote's `quote` object only loosely. The app reads `amount_out`, `min_amount_out`, and `time_estimate`. Only `amount_out` is named in the docs, so these need checking on the first real quote. If `amount_out` is missing, nothing is sent. If the minimum is missing, the app uses 1% below the quote.
- The docs give no per-transaction link form. The default is `https://nearblocks.io/txns/{hash}`, which `EXPLORER_TX_URL` can change. With no transaction hash, the copy button holds the intent hash.
- Live swaps do not check the token list of 1Click: the agent's own token list is used.

## NVDA ile doğrulanacaklar

Not yet checked with NVDA:

- [ ] Esc: NVDA may use the first press to leave focus mode, so cancelling may take two presses.
- [ ] Focus after a copy button: Enter copies again until focus returns to the text box. Check that this is clear in use.
- [ ] Spoken replies: check that each `aria-live` reply is read aloud in full, including a repeat with Alt+R.
- [ ] Microphone: check that speakers do not feed NVDA's voice into recognition. Headphones may be needed.

## Configuration

All settings are optional in dry mode. See `.env.example`. Keys belong in `.env`, which git ignores.

## Stack and disclosures

- Backend: Python, FastAPI, httpx, uvicorn, python-dotenv. Tests: pytest.
- Owner signing: Node with `near-api-js`.
- Frontend: plain HTML and vanilla JavaScript, no framework.
- All code was written for this hackathon, with AI assistance from Claude Code.
- NEAR agent skills `near-intents` and `near-ai-cloud` were used as references. `skills-lock.json` records them.

## License

MIT. See `LICENSE`.
