// The two other answers a fetch can give: several cards, and none.
//
//   npx tsx lists.ts                          # the two example codes below
//   npx tsx lists.ts <shared code> <code>     # your own
//
// - A code that several cards share returns all of them, as a plain list of signed cards. Present the list; do not pick one.
// - A code that finds no card returns an empty list. That means the pack is not on the record, not that the medicine does not exist.
//
// Dosidal identifies a medicine; it does not advise on its use.
const API = "https://dosidal-api.ai/v1/fetch/";
const headers = { "User-Agent": process.env.AGENT_NAME ?? "my-agent/0.1", Accept: "application/json" };

async function show(code: string) {
  const r = await fetch(API + encodeURIComponent(code), { headers });
  const answer: any = await r.json();
  const receipt = r.headers.get("x-dosidal-receipt");
  if (!Array.isArray(answer)) {
    console.log(code, "-> one card:", answer.card, "| receipt:", receipt);
  } else if (answer.length) {
    console.log(code, "->", answer.length, "cards share this code | receipt:", receipt);
    for (const c of answer) console.log("  ", c.card, "|", c.record.level, "| market", c.identity.market, "| stamp", c.stamp.checked);
  } else {
    console.log(code, "-> [] no card: this pack is not on the record | receipt:", receipt);
  }
}

async function main() {
  await show(process.argv[2] ?? "NDA217806"); // an authorisation number: the authorisation's card and each of its packs
  await show(process.argv[3] ?? "09506000134352"); // a well-formed barcode that is on no card
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
