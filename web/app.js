"use strict";

const TEXT = {
  tr: {
    intro: "Token takası için deneme teklifi alır. Para hareket etmez.",
    lang: "Dil",
    from: "Gönderilen token",
    to: "Alınan token",
    amount: "Miktar",
    submit: "Deneme teklifi al",
    heading: "Sonuç",
    busy: "Teklif alınıyor.",
    failed: "Sunucuya ulaşılamadı.",
  },
  en: {
    intro: "Gets a dry-run quote for a token swap. No funds move.",
    lang: "Language",
    from: "Token to send",
    to: "Token to receive",
    amount: "Amount",
    submit: "Get dry-run quote",
    heading: "Result",
    busy: "Getting quote.",
    failed: "Could not reach the server.",
  },
};

const byId = (id) => document.getElementById(id);
const form = byId("quote-form");
const langSelect = byId("lang");
const result = byId("result");
let busy = false;

function applyLanguage() {
  const text = TEXT[langSelect.value];
  document.documentElement.lang = langSelect.value;
  byId("intro").textContent = text.intro;
  byId("lang-label").textContent = text.lang;
  byId("from-label").textContent = text.from;
  byId("to-label").textContent = text.to;
  byId("amount-label").textContent = text.amount;
  byId("submit").textContent = text.submit;
  byId("result-heading").textContent = text.heading;
}

async function requestQuote() {
  const response = await fetch("api/quote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      from_token: byId("from-token").value,
      to_token: byId("to-token").value,
      amount: byId("amount").value,
      lang: langSelect.value,
    }),
  });
  const data = await response.json();
  return data.spoken || TEXT[langSelect.value].failed;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  busy = true;
  // The button stays enabled so keyboard focus is never lost.
  byId("submit").setAttribute("aria-disabled", "true");
  result.textContent = TEXT[langSelect.value].busy;
  try {
    result.textContent = await requestQuote();
  } catch {
    result.textContent = TEXT[langSelect.value].failed;
  } finally {
    busy = false;
    byId("submit").removeAttribute("aria-disabled");
  }
});

langSelect.addEventListener("change", applyLanguage);
applyLanguage();
