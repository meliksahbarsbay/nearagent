// Send native NEAR from the owner account. Run from anywhere:
//
//   node scripts/owner/send_near.mjs --to ADDRESS --miktar 1.5     Show the terms and a code.
//   node scripts/owner/send_near.mjs --to ADDRESS --hepsi          The same, for all but the reserve.
//   node scripts/owner/send_near.mjs --to ADDRESS --hepsi --onay=KOD   Send it.
//
// Nothing is sent without a code from the previous run. A code works once, for that exact
// address and amount, for ten minutes. The key is read from .env and never printed.
import { execFileSync } from "node:child_process";
import { createHash, randomInt, timingSafeEqual } from "node:crypto";
import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseEnv } from "node:util";
import {
  JsonRpcProvider,
  KeyPair,
  Signature,
  SignedTransaction,
  actions,
  baseDecode,
  baseEncode,
  createTransaction,
  encodeTransaction,
  nearToYocto,
  yoctoToNear,
} from "near-api-js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const DEFAULT_RPC_URL = "https://free.rpc.fastnear.com";
const ACCOUNT_ID = /^(?=.{2,64}$)(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$/;
const CODE_MINUTES = 10;
export const RESERVE_YOCTO = nearToYocto("0.05");
// What the sending transaction itself costs at most, kept apart so the reserve stays whole.
export const FEE_MARGIN_YOCTO = nearToYocto("0.001");

export class Stop extends Error {}

export function readArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const [flag, inline] = argv[index].split(/=(.*)/s);
    if (flag === "--hepsi") args.all = true;
    else if (["--to", "--miktar", "--onay", "--memo", "--env"].includes(flag)) {
      const value = inline ?? argv[(index += 1)];
      args[flag.slice(2)] = value;
    } else throw new Stop(`Bilinmeyen secenek: ${flag}`);
  }
  return args;
}

export function readAmount(text) {
  const match = /^(\d+)[.,](\d+)$/.exec(text) ?? /^(\d+)()$/.exec(text);
  if (!match) throw new Stop("Tutari 1.5 gibi yaz.");
  // 1.000 is a thousand in Turkish and one in English, so it is never guessed with money.
  if (match[2].length === 3 && match[1] !== "0") {
    throw new Stop("Tutar belirsiz: 1.000 bin mi, bir mi? Sifirsiz yaz, ornegin 1 ya da 1000.");
  }
  const amount = BigInt(nearToYocto(match[2] ? `${match[1]}.${match[2]}` : match[1]));
  if (amount <= 0n) throw new Stop("Tutar sifirdan buyuk olmali.");
  return amount;
}

export function checkAddress(to, owner) {
  if (!to) throw new Stop("Hedef adresi --to ile yaz.");
  if (!ACCOUNT_ID.test(to)) throw new Stop("Bu gecerli bir NEAR adresi degil. Gonderilmedi.");
  if (to === owner) throw new Stop("Hedef sahip hesabinin kendisi. Gonderilmedi.");
}

const isImplicit = (id) => /^[0-9a-f]{64}$/.test(id) || /^0x[0-9a-f]{40}$/.test(id);

// A plain NEAR transfer has only a receiver and an amount. There is nowhere to put a memo,
// so sending without it would lose the money at an address that needs one.
export function refuseMemo(memo) {
  if (memo !== undefined) {
    throw new Stop(
      "NEAR transferinde memo alani yok, bu yuzden gonderilmedi. " +
        "Binance memo istiyorsa bu betikle gonderme, once Binance destegine sor.",
    );
  }
}

export async function planSend(provider, owner, args) {
  refuseMemo(args.memo);
  checkAddress(args.to, owner);
  if (Boolean(args.all) === Boolean(args.miktar)) throw new Stop("--miktar ya da --hepsi yaz, ikisinden biri.");
  const account = await provider.viewAccount({ accountId: owner });
  const balance = BigInt(account.amount);
  const spendable = balance - BigInt(RESERVE_YOCTO) - BigInt(FEE_MARGIN_YOCTO);
  if (spendable <= 0n) throw new Stop(`Bakiye yetmiyor: ${yoctoToNear(balance)} NEAR var, en az 0.05 kalmali.`);
  const amount = args.all ? spendable : readAmount(args.miktar);
  if (amount > spendable) {
    throw new Stop(`Bu tutardan sonra 0.05 NEAR kalmaz. En cok ${yoctoToNear(spendable, 6)} NEAR gonderilebilir.`);
  }
  // A named account that does not exist would reject the transfer. An implicit one needs none.
  if (!isImplicit(args.to)) {
    const exists = await provider.viewAccount({ accountId: args.to }).then(() => true, () => false);
    if (!exists) throw new Stop("Bu adres zincirde bulunamadi. Gonderilmedi.");
  }
  return { to: args.to, amount: amount.toString(), balance: balance.toString() };
}

export function describe(plan) {
  const left = BigInt(plan.balance) - BigInt(plan.amount);
  return [
    `Gonderen: sahip hesabi`,
    `Alici: ${plan.to}`,
    `Tutar: ${yoctoToNear(plan.amount, 6)} NEAR`,
    `Gonderimden sonra kalan: yaklasik ${yoctoToNear(left, 6)} NEAR`,
    "Memo: yok, NEAR transferinde memo alani bulunmaz",
  ].join("\n");
}

const fingerprint = (code) => createHash("sha256").update(code).digest("hex");

export function issueCode(path, plan, now = Date.now()) {
  const code = String(randomInt(100000, 1000000));
  writeFileSync(path, JSON.stringify({ hash: fingerprint(code), to: plan.to, amount: plan.amount, at: now }));
  return code;
}

// The file goes first, so a code can never work twice, even after a crash mid-send.
export function useCode(path, plan, code, now = Date.now()) {
  if (!existsSync(path)) throw new Stop("Gecerli onay kodu yok. Once kodsuz calistir.");
  const saved = JSON.parse(readFileSync(path, "utf8"));
  rmSync(path, { force: true });
  const given = Buffer.from(fingerprint(String(code)));
  if (!timingSafeEqual(given, Buffer.from(saved.hash))) throw new Stop("Onay kodu yanlis, kod silindi. Gonderilmedi.");
  if (now - saved.at > CODE_MINUTES * 60_000) throw new Stop("Onay kodunun suresi doldu. Gonderilmedi.");
  if (saved.to !== plan.to || saved.amount !== plan.amount) {
    throw new Stop("Adres ya da tutar kod alindigindan beri degisti. Gonderilmedi.");
  }
}

export async function buildTransfer(provider, keyPair, owner, plan) {
  const publicKey = keyPair.getPublicKey();
  const access = await provider.viewAccessKey({
    accountId: owner,
    publicKey: publicKey.toString(),
    finalityQuery: { finality: "final" },
  });
  const block = await provider.viewBlock({ finality: "final" });
  const transaction = createTransaction(
    owner,
    publicKey,
    plan.to,
    BigInt(access.nonce) + 1n,
    [actions.transfer(BigInt(plan.amount))],
    baseDecode(block.header.hash),
  );
  const digest = createHash("sha256").update(encodeTransaction(transaction)).digest();
  const signature = new Signature({ keyType: 0, data: keyPair.sign(digest).signature });
  return { signed: new SignedTransaction({ transaction, signature }), hash: baseEncode(digest) };
}

function loadEnv(path) {
  try {
    execFileSync("git", ["check-ignore", "-q", path], { cwd: ROOT, stdio: "ignore" });
  } catch {
    throw new Stop("Ayar dosyasi git disinda degil. Gonderilmedi.");
  }
  return parseEnv(readFileSync(path, "utf8"));
}

async function main() {
  const args = readArgs(process.argv.slice(2));
  const env = loadEnv(resolve(ROOT, args.env ?? ".env"));
  if (!env.OWNER_ACCOUNT_ID || !env.OWNER_PRIVATE_KEY) throw new Stop(".env icinde sahip hesabi yok.");
  const owner = env.OWNER_ACCOUNT_ID;
  const pendingPath = process.env.SEND_PENDING_PATH ?? resolve(ROOT, "scripts", "owner", "send_pending.json");
  const provider = new JsonRpcProvider({ url: env.NEAR_RPC_URL || DEFAULT_RPC_URL });
  const plan = await planSend(provider, owner, args);
  console.log(describe(plan));
  if (args.onay === undefined) {
    console.log(`Onay kodu: ${issueCode(pendingPath, plan)}`);
    console.log("Kod 10 dakika gecerli ve tek kullanimlik. Gondermek icin ayni komuta --onay=KOD ekle.");
    return;
  }
  useCode(pendingPath, plan, args.onay);
  const keyPair = KeyPair.fromString(env.OWNER_PRIVATE_KEY);
  if (Buffer.from(keyPair.getPublicKey().data).toString("hex") !== owner && isImplicit(owner)) {
    throw new Stop("Anahtar sahip hesabina ait degil. Gonderilmedi.");
  }
  const { signed, hash } = await buildTransfer(provider, keyPair, owner, plan);
  // Printed first: if the answer is lost, this is how the result can still be looked up.
  console.log(`Islem kimligi: ${hash}`);
  try {
    await provider.sendTransaction(signed);
  } catch {
    throw new Stop("Sonuc belirsiz. Yeniden gonderme, once islem kimligini ve bakiyeyi kontrol et.");
  }
  console.log("Gonderildi.");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((error) => {
    // Library errors could quote their input, so only our own sentences are printed.
    console.error(error instanceof Stop ? error.message : "Gonderilemedi.");
    process.exitCode = 1;
  });
}
