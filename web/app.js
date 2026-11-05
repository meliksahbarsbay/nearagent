"use strict";

const TEXT = {
  tr: {
    intro: "Token takası için deneme teklifi ve fiyat söyler. Para hareket etmez.",
    introLive: "Canlı mod açık. Onayladığın takaslar gerçek para kullanır.",
    modeDry: "Mod: Deneme",
    modeLive: "Mod: Canlı, gerçek para",
    micOn: "Mikrofon açık, dinliyorum.",
    languageSet: "Dil Türkçe oldu.",
    quoteExpiring: "Teklifin süresi 30 saniye içinde doluyor.",
    quoteExpired: "Teklifin süresi doldu, yeni teklif için tekrar söyle.",
    title: "nearagent: erişilebilir kripto asistanı",
    sentence: "Ne yapmak istiyorsun?",
    send: "Gönder",
    heading: "Sonuç",
    advanced: "Gelişmiş",
    lang: "Dil",
    from: "Gönderilen token",
    to: "Alınan token",
    amount: "Miktar",
    submit: "Deneme teklifi al",
    submitLive: "Canlı teklif al, gerçek para",
    busy: "Yanıt bekleniyor.",
    failed: "Sunucuya ulaşılamadı. Uygulamanın çalıştığını kontrol et, sonra yeniden dene.",
    shortcuts:
      "Kısayollar: Enter gönderir ya da onaylar. Esc iptal eder. Alt M mikrofonu açar. Alt R son cevabı tekrar okur. Alt H yardımı okur.",
    shortcutsLive:
      "Kısayollar: Enter gönderir, onaylamaz. Onay için evet yaz. Esc iptal eder. Alt M mikrofonu açar. Alt R son cevabı tekrar okur. Alt H yardımı okur.",
    helpLive:
      "Canlı mod açık, onayladığın takaslar gerçek para kullanır. Bir cümle yaz ve Enter'a bas. Teklif okununca onaylamak için evet yaz ya da Onayla düğmesine bas, Enter onay sayılmaz. Esc ya da hayır iptal eder. Alt M mikrofonu açar. Alt R son cevabı tekrar okur. Komutlar: cüzdanımda ne var, son işlemlerimi oku, paramı cüzdanıma çek, politikamı oku, bütçem ne kadar kaldı, ajanı dondur, ajanı çöz.",
    help:
      "Bir cümle yaz ve Enter'a bas, örneğin 2 NEAR'ı USDC'ye çevir. Teklif okununca Enter ya da evet onaylar, Esc ya da hayır iptal eder. Alt M mikrofonu açar. Alt R son cevabı tekrar okur. Komutlar: cüzdanımda ne var, son işlemlerimi oku, paramı cüzdanıma çek, politikamı oku, bütçem ne kadar kaldı, ajanı dondur, ajanı çöz.",
    mic: "Mikrofon",
    voice: "Sesli mod",
    voiceOn: "Sesli mod açık. Konuş, dinliyorum. Çıkmak için sesli modu kapat de ya da Esc'ye bas.",
    voiceOff: "Sesli mod kapandı.",
    voiceIdle: "Uzun süre ses gelmedi, sesli modu kapattım.",
    voiceUnsupported: "Bu tarayıcı sesli modu desteklemiyor, Chrome ya da Edge kullan.",
    stt: "Ses tanıma",
    sttBrowser: "Tarayıcı, Chrome'da Google",
    sttOpenai: "OpenAI",
    sttSetBrowser: "Ses tanıma tarayıcıda. Chrome'da ses Google'a gider.",
    sttSetOpenai: "Ses tanıma OpenAI. Kayıt OpenAI'ye gider.",
    recordingStarted: "Kayıt başladı, konuş. Bitince sus.",
    recordingDone: "Kayıt bitti, yazıya çeviriyorum.",
    confirm: "Onayla, gerçek para",
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
    open: "Gezginde aç",
    newTab: "yeni sekmede açılır",
    copied: "Kopyalandı.",
    copyFailed: "Kopyalanamadı. Tarayıcının pano iznini kontrol et.",
    trackStopped: "Takibi durdurdum, sonuç hâlâ belirsiz. Yeniden gönderme, önce bakiyeni kontrol et.",
    ids: {
      correlationId: "Teklif kimliği",
      from: "Gönderilen token kimliği",
      to: "Alınan token kimliği",
      proof: "İşlem bağlantısı",
      explorer: "NEAR Intents gezgininde takas",
      agent_txns: "Ajanın token hareketleri, nearblocks",
      proof_id: "Kayıt kimliği",
      trade: "İşlem",
      owner_address: "Sahip adresi",
    },
  },
  en: {
    intro: "Tells you swap quotes and prices. No funds move.",
    introLive: "Live mode is on. Swaps you confirm use real money.",
    modeDry: "Mode: Dry run",
    modeLive: "Mode: Live, real money",
    micOn: "Microphone on, listening.",
    languageSet: "Language set to English.",
    quoteExpiring: "This quote expires within 30 seconds.",
    quoteExpired: "This quote has expired. Say your request again for a new quote.",
    title: "nearagent: an accessible crypto assistant",
    sentence: "What do you want to do?",
    send: "Send",
    heading: "Result",
    advanced: "Advanced",
    lang: "Language",
    from: "Token to send",
    to: "Token to receive",
    amount: "Amount",
    submit: "Get dry-run quote",
    submitLive: "Get live quote, real money",
    busy: "Waiting for a reply.",
    failed: "Could not reach the server. Check that the app is running, then try again.",
    shortcuts:
      "Shortcuts: Enter sends or confirms. Escape cancels. Alt M turns on the microphone. Alt R repeats the last reply. Alt H reads the help.",
    shortcutsLive:
      "Shortcuts: Enter sends and does not confirm. To confirm, type yes. Escape cancels. Alt M turns on the microphone. Alt R repeats the last reply. Alt H reads the help.",
    helpLive:
      "Live mode is on, and swaps you confirm use real money. Type a sentence and press Enter. After a quote, type yes or press the Confirm button to confirm. Enter does not confirm. Escape or no cancels. Alt M turns on the microphone. Alt R repeats the last reply. Commands: what is my balance, read my recent trades, withdraw to my wallet, read my policy, how much budget is left, freeze the agent, unfreeze the agent.",
    help:
      "Type a sentence and press Enter, for example swap 2 NEAR to USDC. After a quote, Enter or yes confirms, and Escape or no cancels. Alt M turns on the microphone. Alt R repeats the last reply. Commands: what is my balance, read my recent trades, withdraw to my wallet, read my policy, how much budget is left, freeze the agent, unfreeze the agent.",
    mic: "Microphone",
    voice: "Voice mode",
    voiceOn: "Voice mode is on. Speak, I am listening. To leave, say stop voice mode or press Escape.",
    voiceOff: "Voice mode is off.",
    voiceIdle: "I heard nothing for a while, so I turned voice mode off.",
    voiceUnsupported: "This browser does not support voice mode. Use Chrome or Edge.",
    stt: "Speech recognition",
    sttBrowser: "Browser, Google in Chrome",
    sttOpenai: "OpenAI",
    sttSetBrowser: "Speech recognition is in the browser. In Chrome, audio goes to Google.",
    sttSetOpenai: "Speech recognition is OpenAI. Recordings go to OpenAI.",
    recordingStarted: "Recording. Speak, then stop talking.",
    recordingDone: "Recording done, turning it into text.",
    confirm: "Confirm, real money",
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
    open: "Open in explorer",
    newTab: "opens in a new tab",
    copied: "Copied.",
    copyFailed: "Could not copy. Check the browser's clipboard permission.",
    trackStopped: "I stopped tracking, and the result is still unknown. Do not send it again. Check your balance first.",
    ids: {
      correlationId: "Quote ID",
      from: "ID of the token to send",
      to: "ID of the token to receive",
      proof: "Transaction link",
      explorer: "Swap on the NEAR Intents explorer",
      agent_txns: "Agent's token movements, nearblocks",
      proof_id: "Record ID",
      trade: "Trade",
      owner_address: "Owner address",
    },
  },
};

const ANNOUNCE_DELAY_MS = 100;
const POLL_MS = 2000;
const EXPIRY_NOTICE_SECONDS = 30;
const FIELD_IDS = { text: "sentence", amount: "amount", from_token: "from-token", to_token: "to-token" };
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
let language = (navigator.language || "").toLowerCase().startsWith("tr") ? "tr" : "en";
let controller = null;
let pending = null;
let lastReply = "";
let lastIds = [];
let drawnIds = "";
let quoteTimers = [];
let announceTimer = 0;
let liveMode = false;
let listening = null;
let pendingLive = false;
// What the microphone last wrote into the box. Sent as dictation only while it is unchanged.
let dictated = "";
// Browser speech by default. OpenAI only when chosen under Advanced.
let sttEngine = readSetting("stt") === "openai" ? "openai" : "browser";
// Voice mode is off until the user turns it on, and then every reply is also spoken.
const voice = window.NearVoice.createVoiceMode({
  locale: () => SPEECH_LOCALES[language],
  lang: () => language,
  engine: () => sttEngine,
  engineFailed: (spoken) => useBrowserSpeech(spoken),
  busy: () => Boolean(controller),
  // A live quote and a "did you mean" both need an answer, so silence cancels them.
  livePending: () => Boolean(pending && pendingLive),
  showListening: (on) => showListening(on),
  sendVoice: (heard) => {
    sentence.value = heard.text;
    ask(heard.text, { voice: true, confidence: heard.confidence, alternatives: heard.alternatives });
  },
  stopped: (reason) => stopVoice(reason),
});

function readSetting(name) {
  try {
    return window.localStorage.getItem(`nearagent.${name}`);
  } catch {
    return null;
  }
}

function saveSetting(name, value) {
  try {
    window.localStorage.setItem(`nearagent.${name}`, value);
  } catch {
    // A private window keeps the choice for this page only.
  }
}

function setSttEngine(next, spoken) {
  sttEngine = next;
  byId("stt").value = next;
  saveSetting("stt", next);
  announce(spoken || TEXT[language][next === "openai" ? "sttSetOpenai" : "sttSetBrowser"]);
}

// OpenAI is off or failed, so the browser's speech takes over and the user hears why.
function useBrowserSpeech(spoken) {
  setSttEngine("browser", spoken);
}

function announce(message) {
  // Emptying first makes a repeated sentence count as a change for screen readers.
  window.clearTimeout(announceTimer);
  result.textContent = "";
  announceTimer = window.setTimeout(() => {
    result.textContent = message;
  }, ANNOUNCE_DELAY_MS);
  // The result area is silent in voice mode, so the app's own voice reads it instead.
  if (voice.on && message !== TEXT[language].busy) voice.speak(message);
}

// Focus returns to the same identifier, else the same place, and last to the text box.
function restoreFocus(value, place) {
  const buttons = [...byId("ids").querySelectorAll("button")];
  const same = buttons.find((button) => button.dataset.value === value);
  (same || buttons[place] || buttons[0] || sentence).focus();
}

function renderIds() {
  // Drawing again would destroy the focused button, so an unchanged list stays as it is.
  const drawing = JSON.stringify([language, lastIds]);
  if (drawing === drawnIds) return;
  drawnIds = drawing;
  const text = TEXT[language];
  const list = byId("ids");
  const place = [...list.querySelectorAll("button")].indexOf(document.activeElement);
  const focusedValue = place >= 0 ? document.activeElement.dataset.value : null;
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
    button.dataset.value = value;
    button.addEventListener("click", () => copy(value));
    item.append(label, shown, button);
    // Only a web address becomes a link. An intent hash opens in no explorer.
    if (value.startsWith("https://")) {
      const open = document.createElement("a");
      open.href = value;
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      open.textContent = text.open;
      open.setAttribute("aria-label", `${name}: ${text.open}, ${text.newTab}`);
      item.append(" ", open);
    }
    list.append(item);
  }
  if (place >= 0) restoreFocus(focusedValue, place);
}

async function copy(value) {
  try {
    await navigator.clipboard.writeText(value);
    announce(TEXT[language].copied);
  } catch {
    announce(TEXT[language].copyFailed);
  }
}

// Everything that says which mode this is, so no dry-run text survives into live mode.
function paintMode() {
  const text = TEXT[language];
  byId("intro").textContent = liveMode ? text.introLive : text.intro;
  byId("submit").textContent = liveMode ? text.submitLive : text.submit;
  byId("shortcuts").textContent = liveMode ? text.shortcutsLive : text.shortcuts;
  const state = byId("mode-state");
  state.textContent = liveMode ? text.modeLive : text.modeDry;
  state.dataset.live = String(liveMode);
  byId("live-toggle").setAttribute("aria-pressed", String(liveMode));
}

function applyLanguage(next) {
  language = next;
  langSelect.value = next;
  document.documentElement.lang = next;
  result.lang = next;
  const text = TEXT[next];
  document.title = text.title;
  byId("sentence-label").textContent = text.sentence;
  byId("ask-submit").textContent = text.send;
  byId("result-heading").textContent = text.heading;
  byId("advanced-summary").textContent = text.advanced;
  byId("lang-label").textContent = text.lang;
  byId("stt-label").textContent = text.stt;
  byId("stt-browser").textContent = text.sttBrowser;
  byId("stt-openai").textContent = text.sttOpenai;
  byId("from-label").textContent = text.from;
  byId("to-label").textContent = text.to;
  byId("amount-label").textContent = text.amount;
  byId("mic").textContent = text.mic;
  byId("voice-toggle").textContent = text.voice;
  byId("confirm").textContent = text.confirm;
  byId("live-toggle").textContent = text.live;
  byId("mic-state").textContent = text.micOn;
  paintMode();
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
        // A plain state change touches no identifier, so the list keeps its focus.
        if (data.proof || data.final) {
          rememberIds(data);
          renderIds();
        }
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

function clearQuoteTimers() {
  quoteTimers.forEach((timer) => window.clearTimeout(timer));
  quoteTimers = [];
}

function say(message) {
  lastReply = message;
  announce(message);
}

function quoteExpired() {
  // A reply on its way decides for itself, and an answer in flight must not be cut.
  if (controller) return;
  pending = null;
  const confirmButton = byId("confirm");
  if (document.activeElement === confirmButton) sentence.focus();
  confirmButton.hidden = true;
  lastIds = [];
  renderIds();
  say(TEXT[language].quoteExpired);
}

// Each notice fires once, and any later reply without this quote cancels both.
function startQuoteTimers(seconds) {
  clearQuoteTimers();
  const noticeAt = seconds - EXPIRY_NOTICE_SECONDS;
  if (noticeAt > 0) {
    quoteTimers.push(
      window.setTimeout(() => {
        if (!controller) say(TEXT[language].quoteExpiring);
      }, noticeAt * 1000)
    );
  }
  quoteTimers.push(window.setTimeout(quoteExpired, seconds * 1000));
}

function clearFieldErrors() {
  Object.values(FIELD_IDS).forEach((id) => byId(id).removeAttribute("aria-invalid"));
}

function markField(name) {
  const field = byId(FIELD_IDS[name]);
  if (!field) return;
  field.setAttribute("aria-invalid", "true");
  field.focus();
}

async function send(path, body, button) {
  if (controller) return;
  controller = new AbortController();
  clearFieldErrors();
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
    pendingLive = Boolean(pending && (data.confirm_button || data.answer_required));
    if (data.expires_in) startQuoteTimers(data.expires_in);
    else if (!pending) clearQuoteTimers();
    const confirmButton = byId("confirm");
    const confirmHadFocus = document.activeElement === confirmButton;
    confirmButton.hidden = !data.confirm_button;
    // Hiding a focused button drops focus to the page, and this is the moment money moves.
    if (confirmHadFocus && confirmButton.hidden) sentence.focus();
    rememberIds(data);
    if (data.language in TEXT) applyLanguage(data.language);
    if (response.ok || pending) sentence.value = "";
    // Answers go in the text box, so a question from the form moves focus there.
    // In voice mode focus stays put, because a screen reader would talk over the reply.
    if (pending && !voice.on) sentence.focus();
    if (data.field && !voice.on) markField(data.field);
    lastReply = data.spoken || TEXT[language].failed;
    announce(lastReply);
    if (data.track) followSwap(data.track);
  } catch (error) {
    if (error.name !== "AbortError") announce(TEXT[language].failed);
  } finally {
    controller = null;
    button.removeAttribute("aria-disabled");
    // A reply that could not be spoken must not leave voice mode deaf.
    if (voice.on) voice.listenSoon();
  }
}

// Only voice mode adds voice fields. Typed answers and the Confirm button never do.
function ask(text, voiceFields) {
  const body = { text, lang: language, live: liveMode, ...voiceFields };
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
    paintMode();
    lastReply = data.spoken || TEXT[language].failed;
    announce(lastReply);
  } catch {
    announce(TEXT[language].failed);
  }
}

function showListening(on) {
  byId("mic").setAttribute("aria-pressed", String(on));
  byId("mic-state").hidden = !on;
}

function stopListening() {
  showListening(false);
  listening = null;
}

// Adds to the box with a space, and remembers it, so the server knows it was dictated.
function writeDictation(heard) {
  sentence.value = window.NearVoice.mergeDictation(sentence.value, heard);
  dictated = sentence.value;
  sentence.focus();
}

// The microphone with OpenAI: record, then send the clip. Start and end are announced.
function dictateWithRecorder() {
  const text = TEXT[language];
  const session = window.NearVoice.createRecorder({ lang: language });
  let finished = false;
  session.onrecorded = () => announce(text.recordingDone);
  session.onresult = (event) => {
    finished = true;
    if (!event.parsed.text) {
      announce(text.noSpeech);
      return;
    }
    writeDictation(event.parsed.text);
    announce(`${text.heard} ${sentence.value}`);
  };
  session.onerror = (event) => {
    finished = true;
    if (event.error === "stt-off" || event.error === "stt-failed") useBrowserSpeech(event.spoken);
    else announce(text[VOICE_ERRORS[event.error] || "voiceFailed"]);
  };
  session.onend = () => {
    stopListening();
    if (!finished) announce(text.noSpeech);
  };
  listening = session;
  showListening(true);
  announce(text.recordingStarted);
  session.start();
}

function toggleListening() {
  const text = TEXT[language];
  if (listening) {
    listening.stop();
    return;
  }
  if (sttEngine === "openai" && window.NearVoice.recorderSupported()) {
    dictateWithRecorder();
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
    showListening(true);
    announce(text.listening);
  };
  session.onresult = (event) => {
    finished = true;
    // Written to the box and never sent: the user checks it, then presses Enter.
    const parts = [];
    for (let index = 0; index < event.results.length; index += 1) parts.push(event.results[index][0].transcript);
    writeDictation(window.NearVoice.joinParts(parts));
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

function startVoice() {
  const text = TEXT[language];
  if (!voice.supported()) {
    announce(text.voiceUnsupported);
    return;
  }
  if (listening) listening.abort();
  byId("voice-toggle").setAttribute("aria-pressed", "true");
  // The app speaks every reply now, so the screen reader must not read it a second time.
  result.setAttribute("aria-live", "off");
  window.clearTimeout(announceTimer);
  result.textContent = text.voiceOn;
  voice.start(text.voiceOn);
}

// Leaving voice mode gives the result area back to the screen reader before it speaks.
function stopVoice(reason, cancelPending = false) {
  voice.stop();
  showListening(false);
  byId("voice-toggle").setAttribute("aria-pressed", "false");
  result.setAttribute("aria-live", "polite");
  if (cancelPending && pending) {
    ask("iptal");
    return;
  }
  announce(TEXT[language][reason] || TEXT[language].voiceOff);
}

function toggleVoice() {
  if (voice.on) stopVoice("voiceOff");
  else startVoice();
}

function cancel() {
  // Escape in voice mode always leaves it, and cancels a waiting quote too.
  if (voice.on) {
    // A request in flight is stopped like today. Otherwise a waiting quote is cancelled.
    if (controller) controller.abort();
    stopVoice("voiceOff", !controller);
    return;
  }
  if (listening) {
    listening.abort();
    // A recording that was stopped ends no session of its own, so it is cleared here.
    stopListening();
    announce(TEXT[language].voiceStopped);
  } else if (controller) {
    controller.abort();
    announce(TEXT[language].stopped);
  } else if (pending) {
    ask("iptal");
  } else {
    // A sentence is cleared only from its own box, so Esc elsewhere loses nothing.
    if (document.activeElement === sentence) sentence.value = "";
    announce(TEXT[language].nothingToCancel);
  }
}

byId("ask-form").addEventListener("submit", (event) => {
  event.preventDefault();
  // Text the user typed or changed is sent as typed, and the server leaves it as it is.
  const fromMicrophone = Boolean(dictated) && sentence.value === dictated;
  dictated = "";
  ask(sentence.value, fromMicrophone ? { source: "dictation" } : undefined);
});

byId("stt").addEventListener("change", () => setSttEngine(byId("stt").value));

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

byId("mic").addEventListener("click", () => {
  // In voice mode the microphone opens again on its own. The button just opens it now.
  if (voice.on) voice.listenSoon();
  else toggleListening();
});
byId("voice-toggle").addEventListener("click", toggleVoice);
byId("confirm").addEventListener("click", () => ask("evet"));
byId("live-toggle").addEventListener("click", () => setLiveMode(!liveMode));

// Typing again is the fix, so the error mark goes with it.
Object.values(FIELD_IDS).forEach((id) => {
  byId(id).addEventListener("input", () => byId(id).removeAttribute("aria-invalid"));
});

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
    announce(liveMode ? TEXT[language].helpLive : TEXT[language].help);
  } else if (key === "m") {
    event.preventDefault();
    if (voice.on) voice.listenSoon();
    else toggleListening();
  } else if (key === "s") {
    event.preventDefault();
    toggleVoice();
  }
});

langSelect.addEventListener("change", () => {
  applyLanguage(langSelect.value);
  announce(TEXT[language].languageSet);
});
applyLanguage(language);
byId("stt").value = sttEngine;
