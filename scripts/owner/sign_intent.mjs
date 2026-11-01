// Sign one generated owner intent. Reads it from stdin and writes signed_data to stdout.
// The key comes from OWNER_PRIVATE_KEY and is never printed. Errors name a code only.
// scripts/owner_setup.py is the only caller.
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import {
  actions,
  encodeDelegateAction,
  encodeSignedDelegate,
  JsonRpcProvider,
  KeyPair,
  KeyPairSigner,
  Signature,
} from "near-api-js";

// About two minutes of blocks: enough to submit, short enough to expire if it stalls.
const DELEGATE_BLOCKS = 120n;

async function signMessage(generated, keyPair) {
  const { intent, signer } = generated;
  const nonce = Buffer.from(intent.payload.nonce, "base64");
  const message = { ...intent.payload, nonce };
  const walletSigner = KeyPairSigner.fromSecretKey(keyPair.toString());
  const signed = await walletSigner.signNep413Message(signer.account_id, message);
  return {
    ...intent,
    public_key: signer.public_key,
    signature: Buffer.from(signed.signature).toString("base64"),
  };
}

async function signDelegate(generated, keyPair, provider) {
  const { intent, signer } = generated;
  const access = await provider.viewAccessKey({
    accountId: signer.account_id,
    publicKey: signer.public_key,
    finalityQuery: { finality: "final" },
  });
  const delegateAction = {
    senderId: signer.account_id,
    receiverId: intent.payload.receiverId,
    publicKey: keyPair.getPublicKey(),
    nonce: access.nonce + 1n,
    maxBlockHeight: BigInt(access.block_height) + DELEGATE_BLOCKS,
    actions: intent.payload.actions.map(({ params }) =>
      actions.functionCall(
        params.methodName,
        Buffer.from(JSON.stringify(params.args)),
        BigInt(params.gas),
        BigInt(params.deposit),
      ),
    ),
  };
  const digest = createHash("sha256").update(encodeDelegateAction(delegateAction)).digest();
  const signature = new Signature({ keyType: 0, data: keyPair.sign(digest).signature });
  const encoded = encodeSignedDelegate({ delegateAction, signature });
  return { ...intent, signed_delegate: Buffer.from(encoded).toString("base64") };
}

export async function signIntent(generated, keyPair, provider) {
  const { intent, signer } = generated;
  if (signer?.type !== "near" || keyPair.getPublicKey().toString() !== signer.public_key) {
    throw new Error("owner_key_mismatch");
  }
  if (intent.standard === "nep413") return signMessage(generated, keyPair);
  if (intent.standard === "nep366") return signDelegate(generated, keyPair, provider);
  throw new Error("unsupported_standard");
}

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const generated = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  const keyPair = KeyPair.fromString(process.env.OWNER_PRIVATE_KEY);
  const provider = new JsonRpcProvider({ url: process.env.NEAR_RPC_URL });
  process.stdout.write(JSON.stringify(await signIntent(generated, keyPair, provider)));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((error) => {
    // Library errors could quote their input, so only our own codes are printed.
    const known = ["owner_key_mismatch", "unsupported_standard"];
    console.error(known.includes(error.message) ? error.message : "sign_failed");
    // process.exit() crashes Node on Windows while a network handle is closing.
    process.exitCode = 1;
  });
}
