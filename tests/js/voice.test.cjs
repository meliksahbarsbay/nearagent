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

test("eight seconds of silence cancel live money, and never confirm it", () => {
  assert.equal(voice.onSilence({ livePending: true, quietMs: 7999 }), "listen");
  assert.equal(voice.onSilence({ livePending: true, quietMs: 8000 }), "cancel");
});

test("a browser that ends sessions early does not count as long silence", () => {
  // Three sessions that ended almost at once, as while the permission prompt is open.
  for (const quietMs of [50, 120, 400, 5000]) {
    assert.equal(voice.onSilence({ livePending: false, quietMs, first: true }), "listen");
  }
});

test("voice mode waits at least fifteen seconds before it turns itself off", () => {
  assert.ok(voice.silenceLimit({ livePending: false, first: true }) >= 15000);
  assert.equal(voice.onSilence({ livePending: false, quietMs: 14999, first: true }), "listen");
  assert.equal(voice.onSilence({ livePending: false, quietMs: voice.IDLE_MS, first: false }), "stop");
  assert.equal(voice.onSilence({ livePending: false, quietMs: voice.IDLE_MS - 1, first: false }), "listen");
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

test("dictation pieces get a space between them, never glued", () => {
  assert.equal(voice.joinParts(["0.5 New usd'ye çevir", "near"]), "0.5 New usd'ye çevir near");
  assert.equal(voice.mergeDictation("çevir", "near"), "çevir near");
});

test("a dictation piece that repeats is written once", () => {
  assert.equal(voice.joinParts(["yarım NEAR", "yarım NEAR"]), "yarım NEAR");
  assert.equal(voice.mergeDictation("yarım NEAR'ı USDC'ye çevir", "çevir"), "yarım NEAR'ı USDC'ye çevir");
  assert.equal(voice.mergeDictation("swap", "swap 2 NEAR to USDC"), "swap 2 NEAR to USDC");
});

test("dictation into an empty box, and empty pieces, change nothing else", () => {
  assert.equal(voice.mergeDictation("", "  bir   NEAR "), "bir NEAR");
  assert.equal(voice.mergeDictation("bir NEAR", ""), "bir NEAR");
  assert.equal(voice.joinParts([]), "");
});

test("the recorder tells speech from silence by level", () => {
  assert.equal(voice.level(new Float32Array(10)), 0);
  assert.ok(voice.level(Float32Array.from({ length: 10 }, () => 0.1)) > 0.015);
});
