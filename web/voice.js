"use strict";

// Voice mode: listen, send, speak the reply, and listen again.
// The pure helpers at the top are tested with node --test. The loop below needs a browser.

const SILENCE_MS = 8000;
const RELISTEN_MS = 400;
const MAX_SILENCES = 3;
const ALTERNATIVES = 3;
const FOLD = { ı: "i", İ: "i", ç: "c", Ç: "c", ğ: "g", Ğ: "g", ö: "o", Ö: "o", ş: "s", Ş: "s", ü: "u", Ü: "u" };
const EXIT_PHRASES = [
  "sesli modu kapat",
  "sesli moddan cik",
  "sesli mod kapat",
  "sesli modu durdur",
  "stop voice mode",
  "exit voice mode",
  "turn off voice mode",
  "voice mode off",
];

function fold(text) {
  return String(text || "")
    .replace(/[ıİçÇğĞöÖşŞüÜ]/g, (letter) => FOLD[letter])
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isExitPhrase(text) {
  const folded = fold(text);
  return EXIT_PHRASES.some((phrase) => folded.includes(phrase));
}

// One recognition result, as the server expects it. Confidence 0 means unknown.
function readResult(result) {
  const choices = [];
  for (let index = 0; index < result.length; index += 1) choices.push(result[index]);
  const [best, ...rest] = choices;
  const confidence = Number(best && best.confidence);
  return {
    text: String((best && best.transcript) || "").trim(),
    confidence: Number.isFinite(confidence) && confidence > 0 ? Math.min(confidence, 1) : null,
    alternatives: rest.map((choice) => String(choice.transcript || "").trim()).filter(Boolean),
  };
}

// What silence means. Live money waiting for an answer is cancelled, never confirmed.
function onSilence({ livePending, silences }) {
  if (livePending) return "cancel";
  if (silences >= MAX_SILENCES) return "stop";
  return "listen";
}

function pickVoice(voices, lang) {
  const prefix = lang.slice(0, 2).toLowerCase();
  const matching = voices.filter((voice) => String(voice.lang || "").toLowerCase().startsWith(prefix));
  return matching.find((voice) => voice.localService) || matching[0] || null;
}

const helpers = { fold, isExitPhrase, readResult, onSilence, pickVoice, SILENCE_MS, ALTERNATIVES, MAX_SILENCES };

if (typeof module !== "undefined" && module.exports) {
  module.exports = helpers;
}

// The loop. app.js gives it what it needs through hooks, so this file keeps no page state.
function createVoiceMode(hooks) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synth = window.speechSynthesis;
  let on = false;
  let session = null;
  let silenceTimer = 0;
  let relistenTimer = 0;
  let silences = 0;

  function supported() {
    return Boolean(Recognition && synth && window.SpeechSynthesisUtterance);
  }

  function stopListening() {
    window.clearTimeout(silenceTimer);
    window.clearTimeout(relistenTimer);
    if (session) {
      const old = session;
      session = null;
      old.onresult = old.onerror = old.onend = null;
      try {
        old.abort();
      } catch {
        // Already stopped.
      }
    }
    hooks.showListening(false);
  }

  function heardNothing() {
    stopListening();
    silences += 1;
    const step = onSilence({ livePending: hooks.livePending(), silences });
    if (step === "cancel") hooks.sendVoice({ text: "", confidence: null, alternatives: [] });
    else if (step === "stop") hooks.stopped("voiceIdle");
    else listen();
  }

  function listen() {
    if (!on || session || synth.speaking || synth.pending || hooks.busy()) return;
    const current = new Recognition();
    let heard = false;
    current.lang = hooks.locale();
    current.continuous = false;
    current.interimResults = false;
    current.maxAlternatives = ALTERNATIVES;
    current.onresult = (event) => {
      heard = true;
      const result = readResult(event.results[0]);
      stopListening();
      if (!result.text) {
        heardNothing();
        return;
      }
      silences = 0;
      if (isExitPhrase(result.text)) {
        hooks.stopped("voiceOff");
        return;
      }
      hooks.sendVoice(result);
    };
    current.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "aborted") return;
      heard = true;
      stopListening();
      hooks.stopped(event.error === "not-allowed" || event.error === "service-not-allowed" ? "voiceDenied" : "voiceFailed");
    };
    current.onend = () => {
      if (session !== current) return;
      session = null;
      hooks.showListening(false);
      if (!heard) heardNothing();
    };
    session = current;
    try {
      current.start();
    } catch {
      session = null;
      hooks.stopped("voiceFailed");
      return;
    }
    hooks.showListening(true);
    // Browsers end a silent session at different times, so the app keeps its own clock.
    silenceTimer = window.setTimeout(() => {
      if (session === current) heardNothing();
    }, SILENCE_MS);
  }

  function listenSoon() {
    window.clearTimeout(relistenTimer);
    relistenTimer = window.setTimeout(listen, RELISTEN_MS);
  }

  // The microphone is never open while the app speaks, so it cannot hear itself.
  function speak(message) {
    if (!on || !message) return;
    stopListening();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = hooks.locale();
    const voice = pickVoice(synth.getVoices(), utterance.lang);
    if (voice) utterance.voice = voice;
    utterance.onend = utterance.onerror = () => {
      if (!synth.speaking && !synth.pending) listenSoon();
    };
    synth.speak(utterance);
  }

  function start(greeting) {
    on = true;
    silences = 0;
    speak(greeting);
  }

  function stop() {
    on = false;
    stopListening();
    synth.cancel();
  }

  return {
    supported,
    start,
    stop,
    speak,
    listenSoon,
    get on() {
      return on;
    },
  };
}

if (typeof window !== "undefined") {
  window.NearVoice = { ...helpers, createVoiceMode };
}
