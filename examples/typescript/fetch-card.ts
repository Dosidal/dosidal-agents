// Fetch one card from Dosidal by each of its three codes, check its signature, then read and check the fetch's receipt.
//
//   npm install
//   npx tsx fetch-card.ts                                   # the example pack below
//   npx tsx fetch-card.ts <barcode> <national pack code>    # any pack
//
// 1. fetch by the barcode on the pack (GTIN), over the Model Context Protocol (MCP) server
// 2. the same card by its national pack code
// 3. the same card by its authorisation number: the answer is a list (the authorisation and each of its packs), the same card in it
// 4. verify_card: the card's signature against Dosidal's public keys
// 5. the fetch's receipt, read and checked on the receipts server at mcp.rco-dosidal.ai/mcp (no key, no sign-in)
// 6. the same card over the web API
//
// Every fetch is counted against the read limit and leaves a signed receipt.
// Dosidal identifies a medicine; it does not advise on its use.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const MCP = "https://mcp.dosidal.ai/mcp";
const RECEIPTS = "https://mcp.rco-dosidal.ai/mcp";
const API = "https://dosidal-api.ai/v1/fetch/";
// Name your agent: the name travels as the User-Agent of every call.
const headers = { "User-Agent": process.env.AGENT_NAME ?? "my-agent/0.1" };

// One tool call: the answer (a list comes wrapped as {result: [...]}) and the receipt id in _meta.receipt.
async function call(url: string, name: string, args: Record<string, unknown>): Promise<{ answer: any; receipt?: string }> {
  const client = new Client({ name: "my-agent", version: "0.1.0" });
  await client.connect(new StreamableHTTPClientTransport(new URL(url), { requestInit: { headers } }));
  try {
    const r: any = await client.callTool({ name, arguments: args });
    let answer = r.structuredContent ?? JSON.parse(r.content[0].text);
    if (answer && typeof answer === "object" && !Array.isArray(answer) && Object.keys(answer).join() === "result") answer = answer.result;
    return { answer, receipt: r._meta?.receipt };
  } finally {
    await client.close();
  }
}

// The value of a card field (null when the regulator does not publish it).
const value = (f: any) => (Array.isArray(f?.value) ? f.value.map((x: any) => (typeof x === "object" ? x.value : x)).join(", ") : f?.value ?? null);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function main(gtin: string, packCode: string) {
  // 1. by the barcode on the pack
  const { answer: card, receipt: receiptId } = await call(MCP, "fetch", { code: gtin });
  console.log("1. by barcode", gtin, "->", card.card);
  console.log("   market:", card.identity.market, "| level:", card.record.level, "| status:", value(card.standing.status));
  console.log("   codes: barcode", value(card.codes.gtin), "| national pack code", value(card.codes.national_pack_code), "| authorisation number", value(card.codes.authorisation_number));
  console.log("   stamp: checked against the regulator on", card.stamp.checked, `(market ${card.stamp.market})`);
  console.log("   receipt:", receiptId);

  // 2. the same card by its national pack code
  const { answer: same } = await call(MCP, "fetch", { code: packCode });
  console.log("2. by national pack code", packCode, "->", same.card, "| same card:", same.card === card.card);

  // 3. by its authorisation number: a list. Present the list; do not pick.
  const auth = card.codes.authorisation_number.value[0].value;
  const { answer: many } = await call(MCP, "fetch", { code: auth });
  console.log("3. by authorisation number", auth, "->", many.length, "cards | the same card is in the list:", many.some((c: any) => c.card === card.card));

  // 4. the card's signature
  const { answer: check } = await call(MCP, "verify_card", { card });
  console.log("4. verify_card -> valid:", check.valid, "| stamp valid:", check.stamp_valid, "| key:", check.kid);

  // 5. the receipt: written after the answer has gone, so read it once it is there
  let got: any = {};
  for (let i = 0; i < 10; i++) {
    got = (await call(RECEIPTS, "get_receipt", { id: receiptId })).answer;
    if (got.found) break;
    await sleep(2000);
  }
  const receipt = got.stored_receipt;
  console.log("5. receipt", receipt.id, "| chain:", receipt.chain, "| seq:", receipt.seq, "| cleared_at:", receipt.cleared_at, "| cards:", receipt.cards);
  const { answer: verdict } = await call(RECEIPTS, "verify_receipt", { receipt, answer: card });
  console.log("   verify_receipt -> valid:", verdict.valid, "| signature:", verdict.signature_valid, "| hash:", verdict.hash_valid, "| on the chain:", verdict.on_chain,
    "| answer_hash matches the card:", verdict.answer_hash_matches);

  // 6. the same card over the web API
  const r = await fetch(API + encodeURIComponent(gtin), { headers: { ...headers, Accept: "application/json" } });
  const web: any = await r.json();
  console.log("6. web API ->", web.card, "| same signature:", web.signature.sig === card.signature.sig, "| receipt:", r.headers.get("x-dosidal-receipt"));
}

main(process.argv[2] ?? "00300020152018", process.argv[3] ?? "0002-0152-01").catch((e) => {
  console.error(e);
  process.exit(1);
});
