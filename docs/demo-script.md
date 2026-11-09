# Demo video script (English, 2:45)

Date: 9 November 2026, updated the same day with the NEAR AI test results. Draft only. Nothing in this file was recorded.

Audience: hackathon judges. Focus: a screen reader user swaps crypto by voice and by text, and stays in control of real money.

This file sits next to `docs/demo-video.md` (Turkish, 2 minutes, three scenes). That file stays as it is. This one is the longer English cut with the Agent API scenes.

## Legend

- **[NO FUNDS]**: dry mode or a read. No money moves. Can be recorded any time.
- **[LIVE, NO FUNDS]**: live mode is on and the real agent is called, but the app refuses before anything is sent.
- **[REAL FUNDS]**: real money moves on NEAR mainnet. Record only with the owner's explicit approval, as a separate take.

## Before recording

- Record on the local build: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. The public demo has no agent wallet and keeps live mode off, so scenes 3 to 6 cannot run there. On the public page, agent commands now say so plainly: `This is the public demo, so there is no agent wallet here...`
- Check the agent balance first with `python scripts/owner_setup.py balance`. Every amount below is a placeholder (`...`). Use what the app really says.
- The app's own limits: 5 dollars per swap, 10 dollars per day (`MAX_LIVE_USD`, `MAX_LIVE_DAILY_USD`). The swap in scene 4 must stay under 5 dollars. Scene 5 needs an amount over 5 dollars on purpose.
- Withdrawals have **not** run on mainnet yet (README, "Live mode"). Rehearse scene 6 once with the owner before the take, or cut it.
- Set the page language to English (menu under the text box). Voice input listens in the page language.
- Voice confirmation of live money needs the browser speech engine (Chrome or Edge) and the exact phrase `yes I confirm`. With NEAR AI speech to text, a spoken yes is refused and the app asks for a typed yes. That refusal is a feature, but do not let it surprise you mid-take.
- Use headphones, so NVDA and the app's voice do not leak into the microphone.
- Record only the browser window. No terminal, no `.env`, no Railway panel.
- Raise NVDA speed a little. Quote sentences are long.
- Do not shorten what NVDA says in a way that changes meaning. If a wait is cut, put `Wait shortened` on screen.

## Scene list

| # | Time | Scene | Funds |
|---|---|---|---|
| 1 | 0:00 - 0:15 | The problem | none |
| 2 | 0:15 - 0:30 | What nearagent is | none |
| 3 | 0:30 - 0:50 | Ask the balance by voice | [NO FUNDS] |
| 4 | 0:50 - 1:35 | Swap: preview, then confirm | [REAL FUNDS] |
| 5 | 1:35 - 2:00 | Policy and limits | [NO FUNDS] then [LIVE, NO FUNDS] |
| 6 | 2:00 - 2:25 | Withdraw to the owner | [REAL FUNDS] |
| 7 | 2:25 - 2:45 | Where NEAR is used, and close | none |

---

## Scene 1: The problem (0:00 - 0:15)

**On screen:** A typical swap page, blurred, with a generic "Swap" button and many unlabeled icons. Caption: `Swap screens are built for eyes.` No real product logo.

**Voiceover (0:00):**
"Swap screens are built for eyes. With a screen reader you hear 'button, button, graphic'. You cannot tell what you pay, what you get, or what the fee is. So you either trust blindly, or you don't use crypto at all."

**Command:** none.

---

## Scene 2: What nearagent is (0:15 - 0:30)

**On screen:** The nearagent page, English. Heading `nearagent`. The line `Mode: Dry run`. The text box `What do you want to do?`. NVDA focus outline on the text box.

**Voiceover (0:15):**
"nearagent is an accessible crypto agent. You say or type one sentence. It reads back every term in plain words: amount, minimum, fee, time. Nothing moves until you confirm. Its wallet is a NEAR Intents agent with a policy that you, the owner, signed."

**Command:** none. Press `Alt H` so NVDA reads the help line, then cut after the first sentence.

---

## Scene 3: Ask the balance by voice (0:30 - 0:50) [NO FUNDS]

**On screen:** Press `Alt S`. The `Voice mode` button shows pressed. Result box: `Voice mode is on. Speak, I am listening...`

**Voiceover (0:30, short, before speaking):**
"Voice mode. I just talk."

**Spoken command:** `What's my balance?`

**App says (example):** `In your wallet: ... wNEAR, about ... dollars. ... USDC, about ... dollars. About ... dollars in total.`

**On screen caption (0:45):** `Read from the NEAR Intents Agent API. Agent's own account.`

**Note:** This is a real read from the Agent API, but no money moves.

---

## Scene 4: Swap: preview, then confirm (0:50 - 1:35) [REAL FUNDS]

**Owner approval needed. Separate take.**

**On screen (0:50):** Open `Advanced`, press `Live mode`. The mode line changes to `Mode: Live, real money` with a double border. App says: `Live mode is on, and swaps you confirm use real money...`

**Voiceover (0:52):**
"Now live mode. Real money, on NEAR mainnet."

**Spoken or typed command (0:56):** `Swap 1 NEAR to USDC`

(Keep the value under 5 dollars. If the agent holds USDC rather than NEAR, use `Swap 2 USDC to NEAR`.)

**App says (example, about 20 seconds, let it play):**
`Live mode, real money. You give: 1 NEAR. You get: about ... USDC. Guaranteed minimum: ... USDC. Fee: about ... dollars. Time: about ... seconds. Quote valid for 2 minutes.`
then, in voice mode:
`You give 1 NEAR and get at least ... USDC. To confirm, say yes I confirm. To stop, say cancel.`

**On screen caption (1:05):** `Quote from the agent's own account. Nothing sent yet.`

**Voiceover (1:15, over the pause):**
"Before anything moves, I hear the minimum I'm guaranteed, and the fee. A plain 'yes' isn't enough by voice. I have to say the whole phrase."

**Spoken command (1:20):** `Yes I confirm`

**App says:** `Processing. I will tell you when it is done.` then `Done. You received ... USDC. The explorer link is in the Identifiers section.`

**On screen (1:30):** Tab to `Identifiers`. NVDA reads `Swap on the NEAR Intents explorer: Open in explorer, opens in a new tab`. Do not open it in the take.

**Fallback take:** If voice confidence is low, the app says `I did not hear you clearly, so I did not count a yes. I cancelled, and nothing was sent.` Keep that take as a bonus clip: it shows the safety rule. Then confirm by typing `yes` and pressing Enter, or the `Confirm, real money` button.

---

## Scene 5: Policy and limits (1:35 - 2:00)

**Part A [NO FUNDS]**

**Spoken command (1:35):** `Read my policy`

**App says (example):** `Policy: allowed actions are swap and withdraw. ... assets are allowed. The daily budget is ... dollars. The agent is active.`

**On screen caption:** `Signed by the owner. Enforced by the Agent API, not by this app.`

**Part B [LIVE, NO FUNDS]**

**Spoken command (1:47):** `Swap 20 USDC to NEAR`

**App says:** `This swap is ... dollars and the limit is 5 dollars, so nothing was sent. Ask for a smaller amount.`

**Voiceover (1:53):**
"Two layers of limits. The owner's signed policy on the agent, and the app's own cap on top. Over the cap, nothing is sent."

**Note:** Part B asks the Agent API for a quote, then refuses on the app's limit before sending (`app/live.py:370-371`). No funds move, but live mode and the real agent are used. If the agent holds less than the amount, the Agent API may refuse first and the app says `The agent's balance is too low...` instead. Pick an amount the agent holds that is still over 5 dollars, or rehearse to see which line comes.

---

## Scene 6: Withdraw to the owner (2:00 - 2:25) [REAL FUNDS]

**Owner approval needed. Separate take. Not yet run on mainnet: rehearse first.**

**Spoken command (2:00):** `Withdraw all NEAR`

**App says (example):**
`Live mode, real money. Withdrawing: ... NEAR. wNEAR arrives at the owner account as native NEAR. To: your owner address, on NEAR. Arriving: about ... NEAR. ... This takes about ... dollars from your daily budget, leaving ... dollars. Quote valid for 2 minutes.`
then `... NEAR will be withdrawn to your owner address. To confirm, say yes I confirm. To stop, say cancel.`

**Voiceover (2:12):**
"Funds can only leave to the owner address in the signed policy. If I say any other address, it refuses. The address is never read aloud. It has a copy button."

**Spoken command (2:18):** `Yes I confirm`

**App says:** `Processing...` then `Withdrawal done. ... wNEAR went to your owner address.`

**Shorter alternative (if withdraw is cut):** say `Withdraw 1 USDC to someone.near`. The app answers `I can only withdraw to the owner address, and no other. Ask again without an address.` That is [LIVE, NO FUNDS]: live mode must be on, the address is refused before anything is read or sent (`app/live.py:623-624`).

---

## Scene 7: Where NEAR is used, and close (2:25 - 2:45)

**On screen (2:25):** Simple text card, two lines, large type:
`NEAR Intents Agent API: policy-bound agent wallet, live swaps, withdrawals, freeze.`
`NEAR AI Cloud: understands your sentence, and suggests a fix when a token is misheard (z-ai/glm-5.3-flash, private TEE).`
Then the `Advanced` section with `Provider in use: NEAR AI` visible.

**Voiceover (2:25):**
"Under the hood: the NEAR Intents Agent API holds the money in a policy-bound agent wallet and runs the swaps. NEAR AI Cloud reads your sentence and, when a token is misheard, asks 'did you mean' before any quote. OpenAI is only a backup. The app never holds the owner key on the public server."

**On screen (2:37):** End card. `nearagent`, the repo link, the public demo link, and one question: `Should the fee be read before the amount you get?`

**Voiceover (2:37):**
"nearagent. Crypto you can hear, and confirm, on your own terms. Try the dry-run demo at the link."

**Honesty notes for this scene:**
- Say only what has run on NEAR AI Cloud:
  - Sentence parsing: 7 November 2026, 44 of 44 through the app's parser.
  - "Did you mean" suggestions: 9 November 2026, 5 of 5 correct, median 1.5 seconds. This can be claimed.
  - Speech to text with NEAR AI Whisper (`openai/whisper-large-v3`): 9 November 2026, with a computer voice, 2 of 4 recordings exactly right. One error was SOL heard as "soul". A rule for that was added the same day (`soul` becomes SOL only where a token goes), but no new recording has been run since. Do **not** claim reliable speech to text on NEAR AI. If it is mentioned at all, say "experimental". The video uses the browser's speech recognition.
  - Whisper gives no confidence score, so with NEAR AI speech to text a spoken `yes I confirm` is refused for live money and the app asks for a typed yes. That is by design.
- Freeze is in the card because it ran on mainnet on 5 November 2026. It is not shown live, because unfreezing has a 10 minute cooldown.

---

## Where each NEAR piece shows up

| Piece | Scene | What the viewer sees |
|---|---|---|
| NEAR Intents Agent API | 3, 4, 5, 6 | Balance read, live quote, policy read, limit refusal, live swap, withdrawal |
| NEAR Intents (1Click) | 2 (mention), public demo | Dry-run quotes in the public demo |
| NEAR AI Cloud | 4, 5, 6, 7 | Every spoken or typed sentence is parsed there, and a misheard token gets a "did you mean" question from it. `Provider in use: NEAR AI` under Advanced |

## Optional beat: "did you mean" (about 10 seconds) [NO FUNDS]

Use it only if the cut has room, for example between scenes 3 and 4. Dry mode is enough.

**Typed command:** `0.5 New usd'ye çevir` on the Turkish page, or in English `swap 0.5 new to usd` (rehearse: the English wording must fail on its tokens to reach the question).

**App says (example):** `Did you mean: swap 0.5 NEAR to USDC? Say yes or no.`

**On screen caption:** `Suggestion from NEAR AI Cloud. No quote until you say yes.`

**Note:** Known mishearings like `new` and `usd` are fixed by rules first, so this line may come from the rules, not the model. The provider line under Advanced says which one answered. Caption it truthfully.

## Takes that need owner approval

1. Scene 4, live swap, under 5 dollars.
2. Scene 6, live withdrawal. First mainnet withdrawal, rehearse once.

Everything else can be recorded without moving funds.

## X announcement draft

Draft only. Not posted. `<VIDEO_LINK>` is a placeholder, X counts any link as 23 characters.

```text
Swap screens are built for eyes. nearagent lets a screen reader user swap by voice: hear the minimum and fee, then say "yes I confirm". Policy-bound wallet on the NEAR Intents Agent API, sentences on NEAR AI Cloud. @NEARProtocol #NEARHackathon <VIDEO_LINK>
```

Length: 267 characters with the link counted as 23 (counted with a script).
