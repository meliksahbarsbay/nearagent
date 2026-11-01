// Run with: npm test, from this folder. Uses throwaway keys and makes no network call.
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { KeyPair, actions, encodeDelegateAction } from "near-api-js";
import { signIntent } from "./sign_intent.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const GENERATOR = resolve(HERE, "generate_key.mjs");
const ENV_NAME = ".env.owner-test";
const ENV_PATH = resolve(ROOT, ENV_NAME);

function makeOwner() {
  const keyPair = KeyPair.fromRandom("ed25519");
  const publicKey = keyPair.getPublicKey();
  const accountId = Buffer.from(publicKey.data).toString("hex");
  const signer = { type: "near", account_id: accountId, public_key: publicKey.toString() };
  return { keyPair, signer };
}

function borshString(value) {
  const bytes = Buffer.from(value, "utf8");
  const length = Buffer.alloc(4);
  length.writeUInt32LE(bytes.length);
  return Buffer.concat([length, bytes]);
}

test("generator writes the key to the ignored file and prints only the address", () => {
  rmSync(ENV_PATH, { force: true });
  writeFileSync(ENV_PATH, "OPENAI_API_KEY=keep-me");
  try {
    const output = execFileSync("node", [GENERATOR, ENV_NAME], { encoding: "utf8" }).trim();
    const saved = readFileSync(ENV_PATH, "utf8");
    assert.match(output, /^[0-9a-f]{64}$/);
    assert.ok(saved.startsWith("OPENAI_API_KEY=keep-me\n"));

    const privateKey = saved.match(/^OWNER_PRIVATE_KEY=(\S+)/m)[1];
    const keyPair = KeyPair.fromString(privateKey);
    assert.equal(Buffer.from(keyPair.getPublicKey().data).toString("hex"), output);
    assert.ok(!output.includes(privateKey));
    assert.ok(saved.includes(`OWNER_ACCOUNT_ID=${output}\n`));
    assert.ok(saved.includes(`OWNER_PUBLIC_KEY=${keyPair.getPublicKey().toString()}\n`));
  } finally {
    rmSync(ENV_PATH, { force: true });
  }
});

test("generator refuses to replace an existing key", () => {
  writeFileSync(ENV_PATH, "OWNER_PRIVATE_KEY=ed25519:already-here\n");
  try {
    const run = spawnSync("node", [GENERATOR, ENV_NAME], { encoding: "utf8" });
    assert.equal(run.status, 1);
    assert.equal(run.stdout, "");
    assert.equal(readFileSync(ENV_PATH, "utf8"), "OWNER_PRIVATE_KEY=ed25519:already-here\n");
  } finally {
    rmSync(ENV_PATH, { force: true });
  }
});

test("generator refuses a file git would track", () => {
  const run = spawnSync("node", [GENERATOR, "scripts/owner/not-ignored.txt"], { encoding: "utf8" });
  assert.equal(run.status, 1);
  assert.equal(run.stdout, "");
});

test("nep413 signature verifies against the documented digest", async () => {
  const { keyPair, signer } = makeOwner();
  const nonce = randomBytes(32);
  const payload = { message: "grant", nonce: nonce.toString("base64"), recipient: "api.example" };
  const intent = { standard: "nep413", payload };
  const signed = await signIntent({ intent, signer }, keyPair);

  const tag = Buffer.alloc(4);
  tag.writeUInt32LE(2 ** 31 + 413);
  const digest = createHash("sha256")
    .update(
      Buffer.concat([
        tag,
        borshString(payload.message),
        nonce,
        borshString(payload.recipient),
        Buffer.from([0]),
      ]),
    )
    .digest();
  const signature = Buffer.from(signed.signature, "base64");
  assert.ok(keyPair.getPublicKey().verify(digest, signature));
  assert.equal(signed.public_key, signer.public_key);
  assert.deepEqual(signed.payload, payload);
});

test("nep366 delegate uses the next nonce and keeps the payload", async () => {
  const { keyPair, signer } = makeOwner();
  const seen = [];
  const provider = {
    viewAccessKey: async (query) => {
      seen.push(query);
      return { nonce: 41n, block_height: 1000 };
    },
  };
  const payload = {
    receiverId: "wallet.near",
    actions: [
      {
        type: "FunctionCall",
        params: { methodName: "store", args: { a: 1 }, gas: "30000000000000", deposit: "0" },
      },
    ],
  };
  const signed = await signIntent({ intent: { standard: "nep366", payload }, signer }, keyPair, provider);
  assert.equal(seen[0].accountId, signer.account_id);
  assert.deepEqual(signed.payload, payload);

  // Rebuild what must have been signed: a wrong nonce, height, or call fails this check.
  const expected = {
    senderId: signer.account_id,
    receiverId: "wallet.near",
    publicKey: keyPair.getPublicKey(),
    nonce: 42n,
    maxBlockHeight: 1120n,
    actions: [
      actions.functionCall("store", Buffer.from('{"a":1}'), 30000000000000n, 0n),
    ],
  };
  const digest = createHash("sha256").update(encodeDelegateAction(expected)).digest();
  const encoded = Buffer.from(signed.signed_delegate, "base64");
  const signature = encoded.subarray(encoded.length - 64);
  assert.ok(keyPair.getPublicKey().verify(digest, signature));
});

test("a key that is not the expected signer signs nothing", async () => {
  const { signer } = makeOwner();
  const { keyPair: other } = makeOwner();
  const intent = { standard: "nep413", payload: {} };
  await assert.rejects(signIntent({ intent, signer }, other), /owner_key_mismatch/);
});

test("other signing standards are refused", async () => {
  const { keyPair, signer } = makeOwner();
  const intent = { standard: "eip712", payload: {} };
  await assert.rejects(signIntent({ intent, signer }, keyPair), /unsupported_standard/);
});
