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
    failed: "Sunucuya ulaşılamadı.",
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
    failed: "Could not reach the server.",
  },
};

const byId = (id) => document.getElementById(id);
const langSelect = byId("lang");
const result = byId("result");
let language = langSelect.value;
let busy = false;

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
}

async function send(path, body, button) {
  if (busy) return;
  busy = true;
  // The button stays enabled so keyboard focus is never lost.
  button.setAttribute("aria-disabled", "true");
  result.textContent = TEXT[language].busy;
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (data.language in TEXT) applyLanguage(data.language);
    result.textContent = data.spoken || TEXT[language].failed;
  } catch {
    result.textContent = TEXT[language].failed;
  } finally {
    busy = false;
    button.removeAttribute("aria-disabled");
  }
}

byId("ask-form").addEventListener("submit", (event) => {
  event.preventDefault();
  send("api/ask", { text: byId("sentence").value }, byId("ask-submit"));
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

langSelect.addEventListener("change", () => applyLanguage(langSelect.value));
applyLanguage(language);
