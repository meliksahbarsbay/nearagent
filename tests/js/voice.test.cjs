// Run with: node --test tests/js/voice.test.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const voice = require("../../web/voice.js");

const result = (...choices) => Object.assign(
  choices.map(([transcript, confidence]) => ({ transcript, confidence })),
  {},
);

test("exit phrases are heard in both languages, with case and punctuation", () => {
  for (const text of ["Sesli modu kapat", "sesli moddan çık.", "Stop voice mode", "please exit voice mode"]) {
    assert.equal(voice.isExitPhrase(text), true, text);
  }
});

test("ordinary sentences are not exit phrases", () => {
  for (const text of ["read my recent trades", "son işlemlerimi oku", "ajanı dondur", "sesli", "stop", ""]) {
    assert.equal(voice.isExitPhrase(text), false, text);
  }
});

test("Turkish letters fold the same way as on the server", () => {
  assert.equal(voice.fold("Evet, ONAYLIYORUM!"), "evet onayliyorum");
  assert.equal(voice.fold("İptal  ŞİMDİ"), "iptal simdi");
});

test("a result gives its text, confidence and other alternatives", () => {
  const read = voice.readResult(result(["evet onaylıyorum ", 0.91], ["evet onaylıyor um", 0.4], ["hayır", 0.1]));
  assert.deepEqual(read, {
    text: "evet onaylıyorum",
    confidence: 0.91,
    alternatives: ["evet onaylıyor um", "hayır"],
  });
});

test("a confidence of zero or none is sent as unknown", () => {
  assert.equal(voice.readResult(result(["yes I confirm", 0])).confidence, null);
  assert.equal(voice.readResult(result(["yes I confirm", undefined])).confidence, null);
  assert.equal(voice.readResult(result(["yes I confirm", Number.NaN])).confidence, null);
});

test("an empty result is empty text", () => {
  assert.equal(voice.readResult(result()).text, "");
});

test("silence cancels live money, and never confirms it", () => {
  assert.equal(voice.onSilence({ livePending: true, silences: 1 }), "cancel");
});

test("silence without live money listens again, then stops", () => {
  assert.equal(voice.onSilence({ livePending: false, silences: 1 }), "listen");
  assert.equal(voice.onSilence({ livePending: false, silences: voice.MAX_SILENCES }), "stop");
});

test("a local voice in the page language is preferred", () => {
  const voices = [
    { lang: "en-US", localService: true, name: "en" },
    { lang: "tr-TR", localService: false, name: "tr online" },
    { lang: "tr-TR", localService: true, name: "tr local" },
  ];
  assert.equal(voice.pickVoice(voices, "tr-TR").name, "tr local");
  assert.equal(voice.pickVoice(voices, "en-US").name, "en");
  assert.equal(voice.pickVoice([], "tr-TR"), null);
});

test("the recognizer asks for three alternatives and waits eight seconds", () => {
  assert.equal(voice.ALTERNATIVES, 3);
  assert.equal(voice.SILENCE_MS, 8000);
});
