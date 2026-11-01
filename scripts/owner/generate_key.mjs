// Create the owner's ed25519 key and write it only to a git-ignored env file.
// Run from anywhere: node scripts/owner/generate_key.mjs
// The only thing printed is the account address, which is public.
import { execFileSync } from "node:child_process";
import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { KeyPair } from "near-api-js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const envPath = resolve(ROOT, process.argv[2] ?? ".env");

function stop(message) {
  console.error(message);
  process.exit(1);
}

try {
  execFileSync("git", ["check-ignore", "-q", envPath], { cwd: ROOT, stdio: "ignore" });
} catch {
  stop("Durdum: bu dosya git disinda degil. Anahtar yazilmadi.");
}

const existing = existsSync(envPath) ? readFileSync(envPath, "utf8") : "";
if (/^OWNER_PRIVATE_KEY=\S/m.test(existing)) {
  stop("Durdum: dosyada zaten bir sahip anahtari var. Uzerine yazilmadi.");
}

const keyPair = KeyPair.fromRandom("ed25519");
const publicKey = keyPair.getPublicKey();
const accountId = Buffer.from(publicKey.data).toString("hex");
const separator = existing && !existing.endsWith("\n") ? "\n" : "";
appendFileSync(
  envPath,
  `${separator}OWNER_ACCOUNT_ID=${accountId}\n` +
    `OWNER_PUBLIC_KEY=${publicKey.toString()}\n` +
    `OWNER_PRIVATE_KEY=${keyPair.toString()}\n`,
);

// The address is shown only after the key that controls it is safely stored.
const stored = readFileSync(envPath, "utf8").match(/^OWNER_PRIVATE_KEY=(\S+)/m)?.[1];
if (stored !== keyPair.toString()) stop("Durdum: anahtar dosyaya yazilamadi.");
console.log(accountId);
