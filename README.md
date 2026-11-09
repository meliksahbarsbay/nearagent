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
- Shortcuts: Enter sends or confirms, Esc cancels, Alt+M turns on the microphone, Alt+R repeats the last reply, and Alt+H reads the help. They are shown under the text box, and a screen reader hears them with it.
- The page opens in the browser's language: Turkish for a Turkish browser, and English otherwise. A language menu sits below the text box, and a change is announced.
- Focus is kept: after Confirm it moves to the text box, and copy buttons keep it when their list changes.
- Live mode shows in text and without relying on colour: a `Mod: Canlı, gerçek para` line, and every button and help text warns of real money. A microphone that is listening shows the same way.
- Voice input through the browser's Web Speech API. It uses Turkish or English to match the page, announces `Dinliyorum` and `Anladım: ...`, and writes what it heard into the text box. It never sends by itself: you check the text and press Enter.
- `Bunu mu demek istedin` (`Did you mean`): when a sentence fails on its tokens, for example `0.5 New usd'ye çevir`, the app asks `Bunu mu demek istedin: 0,5 NEAR'ı USDC'ye çevir? Evet ya da hayır de.` and asks for no quote until you say yes. No, silence, or anything else cancels it. Known mishearings such as `new` and `usd` are fixed by rules first. Only if those are not enough is a language model asked: NEAR AI Cloud first, with OpenAI as the backup. Code checks its answer: both tokens must be on the supported list, the amount must be the one code reads from the sentence, or the app asks how much, and under 0.7 confidence nothing is suggested. With no key, only the rules run. This yes accepts the sentence and never confirms a live swap: the quote that follows has its own confirmation.
- Speech recognition is chosen under Advanced (`Ses tanıma`, `Speech recognition`): `Tarayıcı (Google)`, `NEAR AI`, or `OpenAI`. With a NEAR AI key, NEAR AI is marked as recommended. The browser's is the default. NEAR AI and OpenAI record a short clip, announce when recording starts and ends, and send it to `/api/transcribe` with the token names as a hint. NEAR AI runs `openai/whisper-large-v3`, which gives no confidence, so a live yes heard through it is refused and the page asks for a typed yes or the Confirm button. If a service is off or fails, the page says so and uses the browser's. Both the microphone and voice mode use the chosen one.
- Dictated text is fixed like voice mode while you leave it unchanged, and pieces are joined with a space. Text you type or edit is never rewritten.
- Voice mode, off by default: the `Sesli mod` (`Voice mode`) button or Alt+S. While it is on, the app listens, sends what it heard, speaks the reply with the browser's own speech, and listens again. The result area stops reading aloud, so a screen reader does not speak over it, and Alt+R speaks the last reply again. `sesli modu kapat`, `stop voice mode`, Escape, or the button turns it off, and Escape also cancels a waiting quote.
- In voice mode, live money needs the whole phrase `evet onaylıyorum` or `yes I confirm`, after the app repeats the amount and the token. A bare `evet` or `yes` is asked again. Low or missing recognition confidence (under 0.80), a refusal in any of the top three guesses, other words, 8 seconds of silence, or an expired quote cancels it. The server checks these rules too. Freezing works by voice, and unfreezing still needs the six digit code. Typed answers and the Confirm button keep the rules above.
- An Advanced section keeps a field-based form, `POST /api/quote`, which works with no keys.
- Dry mode by default. A dry confirmation only replies `Deneme modu: işlem yapılmadı.`
- A quote warns once, 30 seconds before it expires, and says so again when it has. Dry quotes last 10 minutes, and live quotes last 2.
- A form error marks the field with `aria-invalid` and moves focus there. Typing clears the mark.
- Amounts as people say them, read in code: `yarım SOL`, `bir buçuk NEAR`, `half a SOL`, `one and a half`, `1.000`, and `1,5`. Dollars work too: `50 dolarlık SOL al` and `fifty dollars of SOL`.
- `son işlemlerimi oku` or `read my recent trades` reads the last 5 confirmed trades, dry and live, with date, what was given and received, and status. Long identifiers stay out of the sentence, and each trade has a copy button.
- Agent commands, typed or spoken: `cüzdanımda ne var`, `politikamı oku`, `bütçem ne kadar kaldı`, `ajanı dondur`, and `ajanı çöz`, or `what's my balance`, `read my policy`, `how much budget is left`, `freeze the agent`, and `unfreeze the agent`. With no agent they reply `Ajan cüzdanı kurulmadı`. The wallet is read token by token, with dollar values.
- `ajanı dondur` is the emergency stop. It takes one step, needs no language model, and cuts through any open question, so the command itself is the owner's approval. It signs with the owner key and reports success only after the API confirms it.
- `ajanı çöz` signs nothing at first. It says what would happen and gives a six digit code, and only that code signs. Enter and `evet` do not. Three wrong codes end the attempt.
- A live mode switch in the Advanced section. It stays off with the reply `Canlı mod için ajan cüzdanı kurulmadı` unless `LIVE_ENABLED=true` and the Agent API key, `AGENT_ID`, and `GRANT_TOKEN` are all set.
- In live mode, Enter alone never confirms. You must type `evet` or `yes`, or press a separate Confirm button.

## Live mode: off by default

Live mode is off by default. An agent was created on NEAR mainnet through the Agent API's demo server and funded with 5 USDC. Freezing and unfreezing ran once on it. On 5 November 2026, one real swap, 4.9 USDC to 1.207098 wNEAR, was confirmed from the page with the NVDA screen reader. The proof links are under `Known limits`. That is the only real swap so far. Withdrawals and the NEAR send script have not run on mainnet yet.

Every real swap needs the owner's explicit approval. It is mainnet only, with real money, in a dedicated account.

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

`docs/funding.md` has the full numbered steps in Turkish. The order matters: NEAR first, because the owner account must exist before it signs, and USDC last, because the deposit address exists only after the agent does.

Funding uses real money and needs two transfers, about 0.1 NEAR and 5 USDC:

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
6. Run `python scripts/owner_setup.py deposit`. It prints a one-time address. Send 5 USDC to it on the Base network, and only to that address. A repeat run shows the same address, and `--yeni` asks for a new one.
7. Run `python scripts/owner_setup.py balance` to see the funds arrive.
8. Set `LIVE_ENABLED=true` in `.env` and restart the app. Only do this for the first real swap, after the owner approves it.

`freeze` stops the agent from a terminal, in one step. `unfreeze` prints a code, and `unfreeze --onay=CODE` signs. Unfreezing has a 10 minute cooldown on the API's side. Freezing has none.

### Withdrawing

Funds can leave only to the owner address, which is read from the signed policy. A sentence that names any address is refused. With live mode on, `paramı cüzdanıma çek`, `hepsini USDC çek`, or `withdraw 2 USDC` reads what would leave, where it goes, and what it takes from the daily budget, then waits for a typed `evet` or the Confirm button. It checks everything again before sending, and follows the result like a swap.

From a terminal, `python scripts/owner_setup.py withdraw --ne "hepsini USDC"` shows the same terms and a code, and `--onay=CODE` sends. The code belongs to that exact amount.

Withdrawals count against the daily budget and the per-transaction limit. `hepsini` stops at the limit and says so. This has only run against a stand-in API.

### Returning funds to an exchange

Swap to NEAR in the agent, withdraw it to the owner account, and send it on with `scripts/owner/send_near.mjs`. The Agent API documents that NEAR withdrawn to `near` always arrives as native NEAR, with no registration, so no unwrap step is needed. A token other than NEAR would stay on the owner account, and the withdrawal says so before you confirm.

`send_near.mjs` shows the terms and a one-time code, and sends only with that code, for that exact address and amount. It keeps at least 0.05 NEAR in the account. A plain NEAR transfer has no memo field, so `--memo` stops it. It does not send without the memo, because that could lose the funds. `docs/funding.md` has the numbered steps.

The rules: swap, plus withdraw only to the owner's address, for USDC on NEAR and Base, wNEAR, SOL, and ETH, with 10 dollars a day and 10 actions an hour. The API has no per-transaction dollar cap, so the 5 dollar cap is converted to token amounts at the prices when the plan was made. If a token's price rises, that cap rises in dollars. The daily cap stays in dollars.

The signing approach follows the Agent API documentation and its examples. That examples repository states no license, so no code was copied from it.

## How NEAR is used

- NEAR AI Cloud is the first provider for parsing sentences, for `did you mean` suggestions with `z-ai/glm-5.3-flash`, and for speech to text with `openai/whisper-large-v3`, through its OpenAI-compatible API at `https://cloud-api.near.ai/v1`. If NEAR AI fails or is silent for 8 seconds, OpenAI takes the same suggestion or recording, and the server log names the service, the model, the time, and whether the backup was used, never a key or the sentence. Both models were checked in NEAR AI's model list on 5 November 2026. Sentence parsing ran with a NEAR AI key on 7 November 2026, and suggestions and speech to text on 9 November 2026. The results are under `Parser evaluation`. Suggestions ask NEAR AI for `reasoning_effort: low`, because the model otherwise thinks for over 100 tokens and can pass 8 seconds. `NEARAI_REPAIR_REASONING_EFFORT=full` turns this off. Parsing does not use it. `REPAIR_PROVIDER` and `TRANSCRIBE_PROVIDER` can put OpenAI first. The page shows `Kullanılan sağlayıcı` (`Provider in use`) under Advanced, and a switch to the backup is announced.
- NEAR AI Cloud parses sentences through its OpenAI-compatible API. The default model is `z-ai/glm-5.3-flash`, listed as Private TEE. OpenAI is the fallback, used when the NEAR AI key is missing or NEAR AI fails. For parsing, NEAR AI gets 30 seconds before OpenAI takes over.
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
4. Do: press Tab until you reach the `Advanced` section (`Gelişmiş` on a Turkish browser), press Enter to open it, Tab to `Get dry-run quote` (`Deneme teklifi al`), and press Enter. See: a real dry quote for 1 wNEAR to USDC read in fixed order, ending with `Do you confirm?` (`Onaylıyor musun?`). This uses the public 1Click API.
5. Do: press Enter on the empty text box. See: `Dry run: nothing was executed.` (`Deneme modu: işlem yapılmadı.`)
6. Do: type `freeze the agent` (`ajanı dondur`) and press Enter. See: `The agent wallet is not set up. Try again after setup.` (`Ajan cüzdanı kurulmadı. Kurulum bitince yeniden dene.`)

Sentences such as `1 SOL kaç dolar` need a key. Copy `.env.example` to `.env`, set `NEAR_AI_API_KEY` or `OPENAI_API_KEY`, and restart. Without a key, the text box says parsing is off and the form still works.

## Try it: do X, see Y

Prices below are examples, so your numbers will differ. Steps 3 to 10, 12, and 13 need a key. Each step starts from an empty text box.

1. Do: run `python -m pytest -q`. See: all tests pass, with no network calls.
2. Do: open http://127.0.0.1:8000 and press Tab. See: focus lands on the text box labelled `Ne yapmak istiyorsun?` or `What do you want to do?`, by your browser's language, and a screen reader also reads the shortcuts. The steps below use the Turkish labels.
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

NEAR AI Cloud with `z-ai/glm-5.3-flash`, one run on 7 November 2026: 44 of 44 through the app's parser. NEAR AI answered 43 itself. One request, `50 dolar kaç SOL`, reached the 30 second parsing timeout, and the OpenAI backup answered it correctly. NEAR AI's answers took 4.0 seconds on average, 2.8 at the median, and 13.8 at most. Three took longer than 8 seconds. The run used about 24,000 input tokens and 8,400 output tokens, about 0.006 dollars at NEAR AI's listed price. This is the same set that shaped the prompt, so it is not unseen data either.

NEAR AI Cloud for `did you mean` and speech to text, one short run on 9 November 2026, 16 requests in all:

- Suggestions: 5 garbled sentences that the rules cannot fix, 3 Turkish and 2 English, such as `0.5 nyar'ı dolar coin'e çevir`. Each ran with the model's default reasoning and with `reasoning_effort: low`. Both got 5 of 5 right. With the default, NEAR AI took 5.1 seconds at the median and up to 6.6, and one request passed 8 seconds, so the OpenAI backup answered it, correctly. With `low`, NEAR AI answered all 5 itself, in 1.5 seconds at the median and 2.0 at most, and reasoning fell from about 135 tokens a request to about 6. `low` is now the default.
- Speech to text: 4 English clips made with Windows' built-in voice, not a person. Whisper on NEAR AI answered each in 0.4 to 0.75 seconds, with no backup. 2 of 4 had every word right. It heard `sol` as `soul` twice, and `two` as `to` once. Whisper has no reasoning setting. Turkish speech and real voices were not tested.
- Tokens: NEAR AI's suggestion model used about 1,700 input and 1,000 output tokens, under 0.001 dollars at its listed price. Whisper reported no token use. OpenAI was used once, as the backup: 230 input and 81 output tokens.

## Known limits

- `NEAR` maps to `wNEAR`, because 1Click lists NEAR that way on the NEAR chain.
- `1.000` follows the sentence's language: a thousand in Turkish, and one in English. The quote reads the amount back before you confirm.
- A number counts only when a token or a dollar word follows it, so `bir` as a plain word is not read as an amount. A number with no such word falls back to what the language model read.
- A sentence that buys without saying how to pay uses USDC, and the quote says so.
- Dollar amounts use the token's current list price, so the real value can differ slightly. In dry mode a bought amount uses `EXACT_OUTPUT`. The Agent API takes an exact input only, so in live mode every amount becomes the input that matches it at the current price.
- Trade history is stored in `data/history.json` on this computer. It is a convenience, and the Agent API holds the real record of a live swap. A swap still running when the app restarts stays marked as processing.
- Reading the wallet works against the real Agent API from the terminal, with `python scripts/owner_setup.py balance`. The page's wallet reply was tested against a stand-in.
- Some quotes fail upstream with no specific reason. In live mode the Agent API's code decides the sentence: no route, or an amount too low. The API names no minimum, so none is read out. The code is written to the server log.
- Prices come from the 1Click token list, so they may be a few minutes old.
- Sending to a person or a wallet address is not supported. Those sentences get the help reply.
- 1Click reports no total fee, so the spoken fee is `amountInUsd` minus `amountOutUsd`. It covers fees and price difference together.
- Dry quotes return no deadline, so the spoken validity is the 10 minutes the app requests.
- Amounts are rounded down, so a guaranteed minimum is never read out higher than it is. Very small amounts keep four significant digits, even past six decimals, or they would read as zero.
- An answer to `how much` must be only an amount, such as `yarım`, `bir buçuk`, `50 dolar`, or `50 USDC`. A unit that is neither dollars nor one of the swap's tokens is asked again.
- Open questions live in server memory, so a restart ends them and the page says the quote expired.
- Tests cover the server, and `node --test tests/js/voice.test.cjs` covers voice mode's pure helpers. The page's keyboard behaviour was checked by hand in Chrome. Voice mode's loop has not been checked with NVDA or a real microphone yet.
- Voice recognition was checked with a stand-in recognizer, and NEAR AI's Whisper with 4 English clips from a computer voice, not a real microphone or a person. Chrome and Edge may send audio to their own speech service, unlike sentence parsing on NEAR AI Cloud.
- Where your voice goes: with the browser's speech recognition, to the browser's speech service, which is Google's in Chrome and Microsoft's in Edge. With NEAR AI chosen, the recording passes through nearagent's server to NEAR AI Cloud, which runs Whisper inside its TEE. With OpenAI chosen, or when OpenAI is the backup, it goes to OpenAI. nearagent's server does not keep recordings. The public demo refuses recordings.
- In voice mode only, the server rewrites what speech recognition wrote before reading it: spoken decimals such as `sıfır virgül beş` and `one point two` become 0,5 and 1.2, common mishearings such as `nir` and `u es di si` become NEAR and USDC, and an answer to `how much` drops extra words such as `tane`, `olsun`, and `çevir`. The quote still reads the amount back before any confirmation. Typed text is never rewritten.
- Voice input follows the page language, so an English sentence on a Turkish page may be misheard. Change the language menu below the text box first.
- Owner signing runs from a key in `.env`, not a wallet. Keep only a small amount in a dedicated owner account.
- Freezing and unfreezing ran once on the real Agent API, on 5 November 2026. Before that they were tested with the real signer against a local stand-in API. If the result takes more than about 30 seconds, the page says it is not known yet and never claims success.
- Outside voice mode, a spoken `ajanı dondur` still needs Enter, because the microphone button never sends by itself. In voice mode it is sent at once.
- The Agent API documents the live quote's `quote` object only loosely. The app reads `amount_out`, `min_amount_out`, and `time_estimate_seconds`, the names a real quote used on 5 November 2026. The older `time_estimate` is still read. If `amount_out` is missing, nothing is sent. If the minimum is missing, the app uses 1% below the quote.
- The Agent API gave no transaction hash for the first real swap, only an intent hash that no explorer opens. After a live operation, the Identifiers section lists what it has, most specific first: a transaction link on nearblocks when there is a hash, the swap on the NEAR Intents explorer when a 1Click deposit address is known, the agent's token movements on nearblocks, and the intent hash as `Kayıt kimliği` (`Record ID`). Each link has a copy button and an `Open in explorer` link that opens a new tab. `EXPLORER_TX_URL`, `EXPLORER_INTENTS_URL`, and `EXPLORER_ACCOUNT_URL` change the link forms.
- The first real swap, 4.9 USDC to 1.207098124 wNEAR on 5 November 2026: the agent's transfer https://nearblocks.io/txns/3szqE97UvCerjvEudipAas7Rcgz4prpDHKEMFk4KoNK5, the delivery https://nearblocks.io/txns/Gum4SfcPJsvKn4msjvir2PQ8zj9wxqappdx6jgoLRg8L, and the swap on the NEAR Intents explorer https://explorer.near-intents.org/transactions/5bd678812f52462bd516d64afd0ff4933b66cdf1388e1e0d435eafede076b952. The app did not receive the deposit address of that swap, so it showed the agent's page instead.
- Live swaps do not check the token list of 1Click: the agent's own token list is used.
- Trade history is off in the public demo, because a shared server would read one visitor's trades to another.
- The accessibility audit in `docs/accessibility-audit.md` was run again after the fixes, with 0 axe violations in 20 scans. High and medium findings are closed except B5, which needs NVDA. It is not a conformance claim.

## NVDA ile doğrulanacaklar

Not yet checked with NVDA:

- [ ] Esc: NVDA may use the first press to leave focus mode, so cancelling may take two presses.
- [ ] Focus after a copy button: Enter copies again until focus returns to the text box. Check that this is clear in use.
- [ ] Focus after the form: moving to the text box reads its label and shortcuts. Check that this does not delay or cut the quote that follows.
- [ ] Shortcuts: they are visible and also linked to the text box, so browse mode may read them twice.
- [ ] Spoken replies: check that each `aria-live` reply is read aloud in full, including a repeat with Alt+R.
- [ ] Microphone: check that speakers do not feed NVDA's voice into recognition. Headphones may be needed.
- [ ] Voice mode: check that NVDA does not read the result area while voice mode is on, and reads it again after it is off.

## Configuration

All settings are optional in dry mode. See `.env.example`. Keys belong in `.env`, which git ignores.

## Stack and disclosures

- Backend: Python, FastAPI, httpx, uvicorn, python-dotenv. Tests: pytest.
- Owner signing and sending: Node with `near-api-js`.
- Frontend: plain HTML and vanilla JavaScript, no framework.
- All code was written for this hackathon, with AI assistance from Claude Code.
- NEAR agent skills `near-intents` and `near-ai-cloud` were used as references. `skills-lock.json` records them.

## License

MIT. See `LICENSE`.
