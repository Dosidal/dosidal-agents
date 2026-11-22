// The voluntary test payment over x402: one small payment, machine to machine, to try the payment flow.
// It is voluntary. It unlocks nothing, raises no limit and is never required. No card is ever behind a payment.
//
//   npx tsx pay-x402.ts                               # reads the live offer and prints it; nothing is paid
//   PAYER_KEY=0x... npx tsx pay-x402.ts               # pays in USDC (the offer's first entry)
//   PAYER_KEY=0x... npx tsx pay-x402.ts --open-usd    # pays in Open USD (the offer's second entry)
//
// x402 runs inside the call: the address answers 402 Payment Required with its offer (USDC first, Open USD second, both on Base),
// the x402 client signs a payment for the entry it picks and sends the same request again, and the answer carries the settlement.
// The ceiling of the payment is read from the live offer itself: nothing is typed here.
//
// PAYER_KEY is the private key of the wallet that pays. Keep it in your environment or a secret store; never commit it.
// The answer carries a signed receipt and a caller token. The caller token is yours: keep it like a password.
import { decodePaymentResponseHeader, wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme, toClientEvmSigner } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const URL_ = "https://dosidal-api.ai/v1/test-payment";
const BASE = "eip155:8453";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const OPEN_USD = "0xB2000000000000000000002fEb517dFeC7415344";
const BASE_RPC = process.env.BASE_RPC ?? "https://mainnet.base.org";
const headers = { "User-Agent": process.env.AGENT_NAME ?? "my-agent/0.1", Accept: "application/json" };
const currency = (a: string) => (a.toLowerCase() === USDC.toLowerCase() ? "USDC" : a.toLowerCase() === OPEN_USD.toLowerCase() ? "Open USD" : a);

// The live offer: the 402 answer's PAYMENT-REQUIRED header (base64 JSON), or its body.
async function readOffer(): Promise<any> {
  const r = await fetch(URL_, { headers });
  if (r.status !== 402) throw new Error(`HTTP ${r.status}: no offer is open at ${URL_}`);
  const h = r.headers.get("PAYMENT-REQUIRED");
  return h ? JSON.parse(Buffer.from(h, "base64").toString("utf8")) : r.json();
}

async function pay(asset: string) {
  const entry = (await readOffer()).accepts.find((a: any) => a.asset.toLowerCase() === asset.toLowerCase());
  const account = privateKeyToAccount(process.env.PAYER_KEY as `0x${string}`);
  const client = x402Client.fromConfig({
    schemes: [{ network: BASE, client: new ExactEvmScheme(toClientEvmSigner(account), { rpcUrl: BASE_RPC }) }],
    // the ceiling is the offer's own amount for this asset, in its smallest unit
    spendControls: { allowedAssets: [{ network: BASE, asset, maxAmountPerPayment: entry.amount }] },
    paymentRequirementsSelector: (_v: number, reqs: any[]) => reqs.find((r) => r.asset.toLowerCase() === asset.toLowerCase()) ?? reqs[0],
  });
  const r = await wrapFetchWithPayment(fetch, client)(URL_, { headers });
  console.log("HTTP", r.status, "|", currency(asset), "from", account.address);
  const body: any = await r.json();
  if (r.status !== 200) {
    console.log("not paid:", body.error);
    process.exit(1);
  }
  const settled = r.headers.get("PAYMENT-RESPONSE") ?? r.headers.get("X-PAYMENT-RESPONSE");
  if (settled) {
    const s: any = decodePaymentResponseHeader(settled);
    console.log("settled:", s.success, "| network:", s.network, "| transaction:", s.transaction);
  }
  console.log("receipt:", body.receipt?.id, "| kind:", body.receipt?.kind, "| check it at https://mcp.rco-dosidal.ai/mcp (verify_receipt)");
  console.log("caller token:", body.caller_token ? "received (not printed: keep it like a password)" : "none");
}

async function main() {
  const offer = await readOffer();
  for (const a of offer.accepts) console.log("accepts", currency(a.asset), "on", a.network, `(${a.scheme}, ${a.extra?.assetTransferMethod})`, "pay to", a.payTo);
  if (!process.env.PAYER_KEY) {
    console.log("No PAYER_KEY: nothing paid.");
    return;
  }
  await pay(process.argv.includes("--open-usd") ? OPEN_USD : USDC);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
