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
      "Kısayollar: Enter gönderir ya da onaylar. Esc iptal eder. Alt R son cevabı tekrar okur. Alt H yardımı okur.",
    help:
      "Bir cümle yaz ve Enter'a bas, örneğin 2 NEAR'ı USDC'ye çevir. Teklif okununca Enter ya da evet onaylar, Esc ya da hayır iptal eder. Alt R son cevabı tekrar okur.",
    nothing: "Henüz bir cevap yok.",
    nothingToCancel: "İptal edilecek bir işlem yok.",
    stopped: "Bekleyen isteği iptal ettim.",
    idsHeading: "Kimlikler",
    copy: "Kopyala",
    copied: "Kopyalandı.",
    copyFailed: "Kopyalanamadı. Tarayıcının pano iznini kontrol et.",
    ids: {
      correlationId: "Teklif kimliği",
      from: "Gönderilen token kimliği",
      to: "Alınan token kimliği",
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
      "Shortcuts: Enter sends or confirms. Escape cancels. Alt R repeats the last reply. Alt H reads the help.",
    help:
      "Type a sentence and press Enter, for example swap 2 NEAR to USDC. After a quote, Enter or yes confirms, and Escape or no cancels. Alt R repeats the last reply.",
    nothing: "There is no reply yet.",
    nothingToCancel: "There is nothing to cancel.",
    stopped: "I cancelled the waiting request.",
    idsHeading: "Identifiers",
    copy: "Copy",
    copied: "Copied.",
    copyFailed: "Could not copy. Check the browser's clipboard permission.",
    ids: {
      correlationId: "Quote ID",
      from: "ID of the token to send",
      to: "ID of the token to receive",
    },
  },
};

const ANNOUNCE_DELAY_MS = 100;

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
  for (const { key, value } of lastIds) {
    const item = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${text.ids[key]} `;
    // Sighted users can see the value. A screen reader skips it and offers the button.
    const shown = document.createElement("code");
    shown.textContent = value;
    shown.setAttribute("aria-hidden", "true");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text.copy;
    button.setAttribute("aria-label", `${text.ids[key]}: ${text.copy}`);
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
  renderIds();
}

function rememberIds(data) {
  if (data.quote) {
    lastIds = [
      { key: "correlationId", value: data.correlationId },
      { key: "from", value: data.quote.from },
      { key: "to", value: data.quote.to },
    ];
  } else if (!data.pending) {
    lastIds = [];
  }
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
    rememberIds(data);
    if (data.language in TEXT) applyLanguage(data.language);
    if (response.ok || pending) sentence.value = "";
    // Answers go in the text box, so a question from the form moves focus there.
    if (pending) sentence.focus();
    lastReply = data.spoken || TEXT[language].failed;
    announce(lastReply);
  } catch (error) {
    if (error.name !== "AbortError") announce(TEXT[language].failed);
  } finally {
    controller = null;
    button.removeAttribute("aria-disabled");
  }
}

function ask(text) {
  const body = { text, lang: language };
  if (pending) body.pending = pending;
  send("api/ask", body, byId("ask-submit"));
}

function cancel() {
  if (controller) {
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
    },
    byId("submit")
  );
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
    announce(TEXT[language].help);
  }
});

langSelect.addEventListener("change", () => applyLanguage(langSelect.value));
applyLanguage(language);
