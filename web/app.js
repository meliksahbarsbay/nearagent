"use strict";

const TEXT = {
  tr: {
    intro: "Token takası için deneme teklifi ve fiyat söyler. Para hareket etmez.",
    sentence: "Ne yapmak istiyorsun?",
    send: "Gönder",
    heading: "Sonuç",
    advanced: "Gelişmiş",
    lang: "Dil",
    from: "Gönderilen token",
    to: "Alınan token",
    amount: "Miktar",
    submit: "Deneme teklifi al",
    busy: "Yanıt bekleniyor.",
    failed: "Sunucuya ulaşılamadı. Uygulamanın çalıştığını kontrol et, sonra yeniden dene.",
    shortcuts:
      "Kısayollar: Enter gönderir ya da onaylar. Esc iptal eder. Alt M mikrofonu açar. Alt R son cevabı tekrar okur. Alt H yardımı okur.",
    help:
      "Bir cümle yaz ve Enter'a bas, örneğin 2 NEAR'ı USDC'ye çevir. Teklif okununca Enter ya da evet onaylar, Esc ya da hayır iptal eder. Alt M mikrofonu açar. Alt R son cevabı tekrar okur. Komutlar: cüzdanımda ne var, son işlemlerimi oku, politikamı oku, bütçem ne kadar kaldı, ajanı dondur, ajanı çöz.",
    mic: "Mikrofon",
    confirm: "Onayla",
    live: "Canlı mod",
    listening: "Dinliyorum",
    heard: "Anladım:",
    noVoice: "Bu tarayıcı sesli girişi desteklemiyor, Chrome ya da Edge kullan",
    noSpeech: "Bir şey duyamadım. Mikrofona yeniden bas ve konuş.",
    voiceDenied: "Mikrofon izni yok. Tarayıcıdan izin ver, sonra yeniden dene.",
    voiceNoDevice: "Mikrofon bulunamadı. Mikrofonun bağlı olduğunu kontrol et.",
    voiceFailed: "Sesli giriş çalışmadı. İnternet bağlantını kontrol et ya da cümleyi yaz.",
    voiceStopped: "Dinlemeyi durdurdum.",
    nothing: "Henüz bir cevap yok.",
    nothingToCancel: "İptal edilecek bir işlem yok.",
    stopped: "Bekleyen isteği iptal ettim.",
    idsHeading: "Kimlikler",
    copy: "Kopyala",
    copied: "Kopyalandı.",
    copyFailed: "Kopyalanamadı. Tarayıcının pano iznini kontrol et.",
    trackStopped: "Takibi durdurdum, sonuç hâlâ belirsiz. Yeniden gönderme, önce bakiyeni kontrol et.",
    ids: {
      correlationId: "Teklif kimliği",
      from: "Gönderilen token kimliği",
      to: "Alınan token kimliği",
      proof: "İşlem bağlantısı",
      proof_id: "İşlem kimliği",
      trade: "İşlem",
    },
  },
  en: {
    intro: "Tells you swap quotes and prices. No funds move.",
    sentence: "What do you want to do?",
    send: "Send",
    heading: "Result",
    advanced: "Advanced",
    lang: "Language",
    from: "Token to send",
    to: "Token to receive",
    amount: "Amount",
    submit: "Get dry-run quote",
    busy: "Waiting for a reply.",
    failed: "Could not reach the server. Check that the app is running, then try again.",
    shortcuts:
      "Shortcuts: Enter sends or confirms. Escape cancels. Alt M turns on the microphone. Alt R repeats the last reply. Alt H reads the help.",
    help:
      "Type a sentence and press Enter, for example swap 2 NEAR to USDC. After a quote, Enter or yes confirms, and Escape or no cancels. Alt M turns on the microphone. Alt R repeats the last reply. Commands: what is my balance, read my recent trades, read my policy, how much budget is left, freeze the agent, unfreeze the agent.",
    mic: "Microphone",
    confirm: "Confirm",
    live: "Live mode",
    listening: "Listening",
    heard: "I heard:",
    noVoice: "This browser does not support voice input. Use Chrome or Edge.",
    noSpeech: "I heard nothing. Press the microphone again and speak.",
    voiceDenied: "There is no microphone permission. Allow it in the browser, then try again.",
    voiceNoDevice: "No microphone was found. Check that one is connected.",
    voiceFailed: "Voice input did not work. Check your connection, or type the sentence.",
    voiceStopped: "I stopped listening.",
    nothing: "There is no reply yet.",
    nothingToCancel: "There is nothing to cancel.",
    stopped: "I cancelled the waiting request.",
    idsHeading: "Identifiers",
    copy: "Copy",
    copied: "Copied.",
    copyFailed: "Could not copy. Check the browser's clipboard permission.",
    trackStopped: "I stopped tracking, and the result is still unknown. Do not send it again. Check your balance first.",
    ids: {
      correlationId: "Quote ID",
      from: "ID of the token to send",
      to: "ID of the token to receive",
      proof: "Transaction link",
      proof_id: "Transaction ID",
      trade: "Trade",
    },
  },
};

const ANNOUNCE_DELAY_MS = 100;
const POLL_MS = 2000;
const MAX_POLLS = 300;
const SPEECH_LOCALES = { tr: "tr-TR", en: "en-US" };
const VOICE_ERRORS = {
  "not-allowed": "voiceDenied",
  "service-not-allowed": "voiceDenied",
  "audio-capture": "voiceNoDevice",
  "no-speech": "noSpeech",
};
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const byId = (id) => document.getElementById(id);
const langSelect = byId("lang");
const result = byId("result");
const sentence = byId("sentence");
let language = langSelect.value;
let controller = null;
let pending = null;
let lastReply = "";
let lastIds = [];
let announceTimer = 0;
let liveMode = false;
let listening = null;

function announce(message) {
  // Emptying first makes a repeated sentence count as a change for screen readers.
  window.clearTimeout(announceTimer);
  result.textContent = "";
  announceTimer = window.setTimeout(() => {
    result.textContent = message;
  }, ANNOUNCE_DELAY_MS);
}

function renderIds() {
  const text = TEXT[language];
  const list = byId("ids");
  list.replaceChildren();
  byId("ids-section").hidden = lastIds.length === 0;
  byId("ids-heading").textContent = text.idsHeading;
  for (const { key, value, number } of lastIds) {
    const name = number ? `${text.ids[key]} ${number}` : text.ids[key];
    const item = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${name} `;
    // Sighted users can see the value. A screen reader skips it and offers the button.
    const shown = document.createElement("code");
    shown.textContent = value;
    shown.setAttribute("aria-hidden", "true");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text.copy;
    button.setAttribute("aria-label", `${name}: ${text.copy}`);
    button.addEventListener("click", () => copy(value));
    item.append(label, shown, button);
    list.append(item);
  }
}

async function copy(value) {
  try {
    await navigator.clipboard.writeText(value);
    announce(TEXT[language].copied);
  } catch {
    announce(TEXT[language].copyFailed);
  }
}

function applyLanguage(next) {
  language = next;
  langSelect.value = next;
  document.documentElement.lang = next;
  result.lang = next;
  const text = TEXT[next];
  byId("intro").textContent = text.intro;
  byId("sentence-label").textContent = text.sentence;
  byId("ask-submit").textContent = text.send;
  byId("result-heading").textContent = text.heading;
  byId("advanced-summary").textContent = text.advanced;
  byId("lang-label").textContent = text.lang;
  byId("from-label").textContent = text.from;
  byId("to-label").textContent = text.to;
  byId("amount-label").textContent = text.amount;
  byId("submit").textContent = text.submit;
  byId("shortcuts").textContent = text.shortcuts;
  byId("mic").textContent = text.mic;
  byId("confirm").textContent = text.confirm;
  byId("live-toggle").textContent = text.live;
  renderIds();
}

function rememberIds(data) {
  if (data.copies) {
    lastIds = data.copies;
  } else if (data.proof) {
    lastIds = [{ key: data.proof_key, value: data.proof }];
  } else if (data.quote) {
    lastIds = [
      { key: "correlationId", value: data.correlationId },
      { key: "from", value: data.quote.from },
      { key: "to", value: data.quote.to },
    ].filter((id) => id.value);
  } else if (!data.pending) {
    lastIds = [];
  }
}

// Reads a change once, and stops at the final state. The swap goes on if this page closes.
async function followSwap(track) {
  let state = "processing";
  for (let poll = 0; poll < MAX_POLLS; poll += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
    try {
      const response = await fetch("api/live/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ track, lang: language }),
      });
      const data = await response.json();
      if (data.state !== state) {
        state = data.state;
        rememberIds(data);
        renderIds();
        lastReply = data.spoken;
        announce(lastReply);
      }
      if (data.final) return;
    } catch {
      // A missed check changes nothing. The next one reads the same swap.
    }
  }
  lastReply = TEXT[language].trackStopped;
  announce(lastReply);
}

async function send(path, body, button) {
  if (controller) return;
  controller = new AbortController();
  // The button stays enabled so keyboard focus is never lost.
  button.setAttribute("aria-disabled", "true");
  announce(TEXT[language].busy);
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const data = await response.json();
    pending = data.pending || null;
    byId("confirm").hidden = !data.confirm_button;
    rememberIds(data);
    if (data.language in TEXT) applyLanguage(data.language);
    if (response.ok || pending) sentence.value = "";
    // Answers go in the text box, so a question from the form moves focus there.
    if (pending) sentence.focus();
    lastReply = data.spoken || TEXT[language].failed;
    announce(lastReply);
    if (data.track) followSwap(data.track);
  } catch (error) {
    if (error.name !== "AbortError") announce(TEXT[language].failed);
  } finally {
    controller = null;
    button.removeAttribute("aria-disabled");
  }
}

function ask(text) {
  const body = { text, lang: language, live: liveMode };
  if (pending) body.pending = pending;
  send("api/ask", body, byId("ask-submit"));
}

async function setLiveMode(next) {
  try {
    const response = await fetch("api/mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ live: next, lang: language }),
    });
    const data = await response.json();
    if (response.ok) liveMode = data.live;
    byId("live-toggle").setAttribute("aria-pressed", String(liveMode));
    lastReply = data.spoken || TEXT[language].failed;
    announce(lastReply);
  } catch {
    announce(TEXT[language].failed);
  }
}

function stopListening() {
  byId("mic").setAttribute("aria-pressed", "false");
  listening = null;
}

function toggleListening() {
  const text = TEXT[language];
  if (listening) {
    listening.stop();
    return;
  }
  if (!Recognition) {
    announce(text.noVoice);
    return;
  }
  const session = new Recognition();
  let finished = false;
  session.lang = SPEECH_LOCALES[language];
  session.continuous = false;
  session.interimResults = false;
  session.maxAlternatives = 1;
  session.onstart = () => {
    byId("mic").setAttribute("aria-pressed", "true");
    announce(text.listening);
  };
  session.onresult = (event) => {
    finished = true;
    // Written to the box and never sent: the user checks it, then presses Enter.
    sentence.value = event.results[0][0].transcript.trim();
    sentence.focus();
    announce(`${text.heard} ${sentence.value}`);
  };
  session.onerror = (event) => {
    finished = true;
    if (event.error !== "aborted") announce(text[VOICE_ERRORS[event.error] || "voiceFailed"]);
  };
  session.onend = () => {
    stopListening();
    if (!finished) announce(text.noSpeech);
  };
  listening = session;
  try {
    session.start();
  } catch {
    finished = true;
    stopListening();
    announce(text.voiceFailed);
  }
}

function cancel() {
  if (listening) {
    listening.abort();
    announce(TEXT[language].voiceStopped);
  } else if (controller) {
    controller.abort();
    announce(TEXT[language].stopped);
  } else if (pending) {
    ask("iptal");
  } else {
    sentence.value = "";
    announce(TEXT[language].nothingToCancel);
  }
}

byId("ask-form").addEventListener("submit", (event) => {
  event.preventDefault();
  ask(sentence.value);
});

byId("quote-form").addEventListener("submit", (event) => {
  event.preventDefault();
  send(
    "api/quote",
    {
      from_token: byId("from-token").value,
      to_token: byId("to-token").value,
      amount: byId("amount").value,
      lang: langSelect.value,
      live: liveMode,
    },
    byId("submit")
  );
});

byId("mic").addEventListener("click", toggleListening);
byId("confirm").addEventListener("click", () => ask("evet"));
byId("live-toggle").addEventListener("click", () => setLiveMode(!liveMode));

// A held Enter key must not send a request and then confirm the reply.
sentence.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.repeat) event.preventDefault();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    cancel();
    return;
  }
  // Ctrl with Alt is AltGr, which types characters on many keyboards.
  if (!event.altKey || event.ctrlKey) return;
  const key = event.key.toLowerCase();
  if (key === "r") {
    event.preventDefault();
    announce(lastReply || TEXT[language].nothing);
  } else if (key === "h") {
    event.preventDefault();
    announce(TEXT[language].help);
  } else if (key === "m") {
    event.preventDefault();
    toggleListening();
  }
});

langSelect.addEventListener("change", () => applyLanguage(langSelect.value));
applyLanguage(language);
