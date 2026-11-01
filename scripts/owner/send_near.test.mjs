// Run with: npm test, from this folder. A local fake RPC stands in for the chain.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { after, before, beforeEach, test } from "node:test";
import { fileURLToPath } from "node:url";
import { JsonRpcProvider, KeyPair, baseEncode, decodeSignedTransaction, encodeTransaction, nearToYocto } from "near-api-js";
import {
  FEE_MARGIN_YOCTO,
  RESERVE_YOCTO,
  Stop,
  buildTransfer,
  checkAddress,
  describe,
  issueCode,
  planSend,
  readAmount,
  readArgs,
  refuseMemo,
  useCode,
} from "./send_near.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const SCRIPT = resolve(HERE, "send_near.mjs");
const ENV_NAME = ".env.send-test";
const ENV_PATH = resolve(ROOT, ENV_NAME);
const BINANCE = "b".repeat(64);
const keyPair = KeyPair.fromRandom("ed25519");
const OWNER = Buffer.from(keyPair.getPublicKey().data).toString("hex");
const folder = mkdtempSync(join(tmpdir(), "send-near-"));
const PENDING = join(folder, "pending.json");

const chain = { balance: nearToYocto("1.15"), broadcast: [], failBroadcast: false, known: new Set() };

function answer(body) {
  if (body.method === "query") {
    const { request_type: kind, account_id: account } = body.params;
    if (kind === "view_account") {
      if (account !== OWNER && !chain.known.has(account)) {
        return { error: { name: "HANDLER_ERROR", cause: { name: "UNKNOWN_ACCOUNT", info: {} }, code: -32000, message: "Server error" } };
      }
      return { result: { amount: chain.balance.toString(), locked: "0", code_hash: "11111111111111111111111111111111", storage_usage: 182, storage_paid_at: 0, block_height: 1000, block_hash: "11111111111111111111111111111111" } };
    }
    return { result: { nonce: 41, permission: "FullAccess", block_height: 1000, block_hash: "11111111111111111111111111111111" } };
  }
  if (body.method === "block") {
    return { result: { header: { hash: "11111111111111111111111111111111", height: 1000 }, chunks: [] } };
  }
  chain.broadcast.push(body);
  if (chain.failBroadcast) return { error: { name: "HANDLER_ERROR", code: -32000, message: "timeout" } };
  return { result: { status: { SuccessValue: "" }, final_execution_status: "FINAL", transaction: { hash: "x" }, transaction_outcome: { id: "x", outcome: { status: { SuccessValue: "" }, logs: [], receipt_ids: [], gas_burnt: 1, tokens_burnt: "1" }, block_hash: "x", proof: [] }, receipts_outcome: [] } };
}

const server = createServer((request, response) => {
  let raw = "";
  request.on("data", (chunk) => { raw += chunk; });
  request.on("end", () => {
    const body = JSON.parse(raw);
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify({ jsonrpc: "2.0", id: body.id, ...answer(body) }));
  });
});

let provider;
before(async () => {
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const url = `http://127.0.0.1:${server.address().port}`;
  provider = new JsonRpcProvider({ url });
  writeFileSync(
    ENV_PATH,
    `OWNER_ACCOUNT_ID=${OWNER}\nOWNER_PRIVATE_KEY=${keyPair.toString()}\nNEAR_RPC_URL=${url}\n`,
  );
});
after(async () => {
  rmSync(ENV_PATH, { force: true });
  rmSync(folder, { recursive: true, force: true });
  server.closeAllConnections();
  await new Promise((done) => server.close(done));
});
beforeEach(() => {
  chain.balance = nearToYocto("1.15");
  chain.broadcast = [];
  chain.failBroadcast = false;
  rmSync(PENDING, { force: true });
});

// spawnSync would freeze this process, and the fake RPC with it.
function run(...args) {
  return new Promise((done) => {
    const child = spawn("node", [SCRIPT, "--env", ENV_NAME, ...args], {
      env: { ...process.env, SEND_PENDING_PATH: PENDING },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("close", (status) => done({ status, stdout, stderr }));
  });
}

const codeFrom = (output) => /Onay kodu: (\d+)/.exec(output)[1];

test("a run with no code shows the terms and sends nothing", async () => {
  const done = await run("--to", BINANCE, "--miktar", "1");
  assert.equal(done.status, 0);
  assert.match(done.stdout, /Tutar: 1 NEAR/);
  assert.match(done.stdout, /Onay kodu: \d{6}/);
  assert.equal(chain.broadcast.length, 0);
});

test("the code sends exactly one transfer to that address", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  const done = await run("--to", BINANCE, "--miktar", "1", `--onay=${code}`);
  assert.equal(done.status, 0, done.stderr);
  assert.match(done.stdout, /Gonderildi/);
  assert.equal(chain.broadcast.length, 1);
  const bytes = Buffer.from(chain.broadcast[0].params.signed_tx_base64 ?? chain.broadcast[0].params[0], "base64");
  const signed = decodeSignedTransaction(bytes);
  assert.equal(signed.transaction.receiverId, BINANCE);
  assert.equal(signed.transaction.signerId, OWNER);
  assert.equal(signed.transaction.nonce, 42n);
  assert.equal(signed.transaction.actions.length, 1);
  assert.equal(signed.transaction.actions[0].transfer.deposit, BigInt(nearToYocto("1")));
  const digest = createHash("sha256").update(encodeTransaction(signed.transaction)).digest();
  assert.ok(keyPair.getPublicKey().verify(digest, Uint8Array.from(signed.signature.ed25519Signature.data)));
});

test("a code works once", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  await run("--to", BINANCE, "--miktar", "1", `--onay=${code}`);
  const again = await run("--to", BINANCE, "--miktar", "1", `--onay=${code}`);
  assert.equal(again.status, 1);
  assert.match(again.stderr, /Gecerli onay kodu yok/);
  assert.equal(chain.broadcast.length, 1);
});

test("a wrong code sends nothing and burns the real one", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  const wrong = await run("--to", BINANCE, "--miktar", "1", "--onay=000000");
  assert.equal(wrong.status, 1);
  assert.match(wrong.stderr, /yanlis/);
  const late = await run("--to", BINANCE, "--miktar", "1", `--onay=${code}`);
  assert.equal(late.status, 1);
  assert.equal(chain.broadcast.length, 0);
});

test("a code belongs to one address and one amount", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  const other = await run("--to", "c".repeat(64), "--miktar", "1", `--onay=${code}`);
  assert.equal(other.status, 1);
  assert.match(other.stderr, /degisti/);
  const code2 = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  const more = await run("--to", BINANCE, "--miktar", "1.1", `--onay=${code2}`);
  assert.equal(more.status, 1);
  assert.equal(chain.broadcast.length, 0);
});

test("all leaves the reserve and the fee margin", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--hepsi")).stdout);
  await run("--to", BINANCE, "--hepsi", `--onay=${code}`);
  const bytes = Buffer.from(chain.broadcast[0].params.signed_tx_base64 ?? chain.broadcast[0].params[0], "base64");
  const sent = decodeSignedTransaction(bytes).transaction.actions[0].transfer.deposit;
  const expected = BigInt(chain.balance) - BigInt(RESERVE_YOCTO) - BigInt(FEE_MARGIN_YOCTO);
  assert.equal(sent, expected);
  assert.ok(BigInt(chain.balance) - sent >= BigInt(nearToYocto("0.05")));
});

test("an amount that would eat the reserve is refused", async () => {
  const done = await run("--to", BINANCE, "--miktar", "1.11");
  assert.equal(done.status, 1);
  assert.match(done.stderr, /0\.05 NEAR kalmaz/);
  assert.equal(existsSync(PENDING), false);
});

test("the largest allowed amount passes", async () => {
  assert.equal((await run("--to", BINANCE, "--miktar", "1.09")).status, 0);
});

test("a balance under the reserve sends nothing", async () => {
  chain.balance = nearToYocto("0.05");
  const done = await run("--to", BINANCE, "--hepsi");
  assert.equal(done.status, 1);
  assert.match(done.stderr, /Bakiye yetmiyor/);
});

test("a memo is refused, because a transfer cannot carry one", async () => {
  const done = await run("--to", BINANCE, "--miktar", "1", "--memo", "12345");
  assert.equal(done.status, 1);
  assert.match(done.stderr, /memo alani yok/);
  assert.equal(existsSync(PENDING), false);
  assert.equal(chain.broadcast.length, 0);
});

test("the code run with a memo also sends nothing", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  await run("--to", BINANCE, "--miktar", "1", "--memo", "1", `--onay=${code}`);
  assert.equal(chain.broadcast.length, 0);
});

test("a named account that does not exist is refused", async () => {
  const done = await run("--to", "nobody.near", "--miktar", "1");
  assert.equal(done.status, 1);
  assert.match(done.stderr, /bulunamadi/);
});

test("a named account that exists is allowed", async () => {
  chain.known.add("binance.near");
  assert.equal((await run("--to", "binance.near", "--miktar", "1")).status, 0);
});

test("a lost answer gives the transaction id and warns against resending", async () => {
  chain.failBroadcast = true;
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  const done = await run("--to", BINANCE, "--miktar", "1", `--onay=${code}`);
  assert.equal(done.status, 1);
  assert.match(done.stdout, /Islem kimligi: /);
  assert.match(done.stderr, /Yeniden gonderme/);
});

test("the key never reaches the output", async () => {
  const code = codeFrom((await run("--to", BINANCE, "--miktar", "1")).stdout);
  const done = await run("--to", BINANCE, "--miktar", "1", `--onay=${code}`);
  assert.ok(!(done.stdout + done.stderr).includes(keyPair.toString()));
});

test("the terms read plainly", () => {
  const text = describe({ to: BINANCE, amount: nearToYocto("1"), balance: nearToYocto("1.15") });
  assert.match(text, /Tutar: 1 NEAR/);
  assert.match(text, /kalan: yaklasik 0\.15 NEAR/);
});

test("amounts are read strictly", () => {
  assert.equal(readAmount("1,5"), BigInt(nearToYocto("1.5")));
  assert.equal(readAmount("0.125"), BigInt(nearToYocto("0.125")));
  assert.equal(readAmount("2"), BigInt(nearToYocto("2")));
  for (const text of ["", "abc", "1.2.3", "-1", "1,000", "1.000", "0"]) {
    assert.throws(() => readAmount(text), Stop, text);
  }
});

test("addresses are checked", () => {
  assert.throws(() => checkAddress("", OWNER), Stop);
  assert.throws(() => checkAddress("Has Spaces", OWNER), Stop);
  assert.throws(() => checkAddress("UPPER.near", OWNER), Stop);
  assert.throws(() => checkAddress(OWNER, OWNER), /kendisi/);
  checkAddress(BINANCE, OWNER);
  checkAddress("binance.near", OWNER);
});

test("arguments are read in both forms, and unknown ones stop", () => {
  assert.deepEqual(readArgs(["--to", "a.near", "--onay=123"]), { to: "a.near", onay: "123" });
  assert.throws(() => readArgs(["--force"]), /Bilinmeyen/);
  assert.throws(() => refuseMemo(""), /memo/);
});

test("an expired code sends nothing", () => {
  const plan = { to: BINANCE, amount: "1" };
  const code = issueCode(PENDING, plan, 0);
  assert.throws(() => useCode(PENDING, plan, code, 11 * 60_000), /suresi doldu/);
  assert.equal(existsSync(PENDING), false);
});

test("both of --miktar and --hepsi are refused", async () => {
  await assert.rejects(planSend(provider, OWNER, { to: BINANCE, all: true, miktar: "1" }), /ikisinden biri/);
  await assert.rejects(planSend(provider, OWNER, { to: BINANCE }), /ikisinden biri/);
});

test("the transaction id is the hash of what was signed", async () => {
  const plan = { to: BINANCE, amount: nearToYocto("1") };
  const { signed, hash } = await buildTransfer(provider, keyPair, OWNER, plan);
  const digest = createHash("sha256").update(encodeTransaction(signed.transaction)).digest();
  assert.equal(hash, baseEncode(digest));
});
