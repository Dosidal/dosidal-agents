---
name: dosidal
description: Fetch the signed record of a prescription medicine from Dosidal by the barcode on the pack, the national pack code or the authorisation number, read the card and its stamp, and keep and verify the receipt. Use when an agent must identify a prescription medicine pack or authorisation, or show where its facts came from. Dosidal identifies a medicine; it does not advise on its use.
---

# Dosidal

Dosidal holds the regulator's own record of each prescription medicine as a signed card: one pack, one authorisation or one substance in one market, at its own permanent address. MCP server: `https://mcp.dosidal.ai/mcp` (no sign-in). Web API: `https://dosidal-api.ai/v1/fetch/{code}`.

Dosidal identifies a medicine; it does not advise on its use. Never turn a card into dosing, indications, interactions, prices or advice. For anything about use, point to the regulator's label, the prescriber or a pharmacist.

## When to fetch

- The user or a task holds a code from a medicine pack or its authorisation and needs to know what it is, in which market, and its standing with the regulator.
- A fact about a prescription medicine must be shown with its source: the card names the regulator's page and the date for every value.
- Not for questions about use, choice between medicines, or anything a card does not hold.

## Which code to pass

Pass the code exactly as you hold it, to the one tool `fetch` (`{"code": "..."}`). Do not say what kind of code it is.

1. **The barcode on the pack** (GTIN): best, if you have it. It names one pack.
2. **The national pack code**: the regulator's own number for the pack. Also names one pack.
3. **The authorisation number**: names the authorised medicine. It usually returns a list: the authorisation's card and each of its packs.
4. **A card's address** (`https://dosidal.ai/pack/...` or `https://dosidal.ai/record/...`): returns that card.

Spaces at the ends and case do not matter; a barcode is padded to 14 digits. After that the match is exact. A name is not a code: Dosidal does not search by name.

## Reading the answer

- **One card** (an object): the answer. Use it.
- **A list of cards**: the code is shared. Present the list and let the user choose; do not pick one yourself. Show each card's address, level (pack, authorisation or substance) and market.
- **An empty list**: the pack is not on the record. Say exactly that. It does not mean the medicine does not exist, is not authorised or is withdrawn.

## Reading the card

- `card`: its permanent address. Cite it.
- `identity`: name, substance, strength, form, pack size, market, as the regulator publishes them.
- `codes`: `gtin`, `national_pack_code`, `authorisation_number`.
- `standing.status`: status with the regulator; a withdrawn medicine says withdrawn, with the date.
- `holder`: the authorisation holder as the regulator publishes it.
- Each field has `value`, `state`, `source` (the regulator's page), `publisher` and `read` (the date it was read). `state: "unknown"` means the regulator does not publish it: say unknown, never guess.
- `signature`: ES256 over the card. Check it with `verify_card {"card": <the card>}`.

## The stamp

`stamp.checked` is the date the card's market was last checked against the regulator. Report it with the card: "checked against the regulator on <date>". The stamp is a date; nothing expires. It is signed: `verify_card` returns `stamp_valid`.

## Keeping and verifying the receipt

Every fetch leaves a signed receipt. Its id comes with the answer: `_meta.receipt` over MCP, the header `x-dosidal-receipt` over the web API.

1. Keep the id with whatever you produced from the card.
2. To prove the read, call the receipts server `https://mcp.rco-dosidal.ai/mcp` (no key, no sign-in): `get_receipt {"id": "<id>"}`. The receipt is written after the answer has gone; if it answers `found: false`, wait a few seconds and ask again.
3. `verify_receipt {"receipt": <stored_receipt>, "answer": <the card or list as served>}` checks the hash, the signature, the place on the chain and that the receipt's `answer_hash` is the hash of that answer.

## Limits

2,000 fetches a day per caller address and per network, UTC day. At the limit the answer is HTTP 429: stop and come back the next day. Send a User-Agent that names your agent. A voluntary test payment over x402 exists at `https://dosidal-api.ai/v1/test-payment`; it unlocks nothing and is never needed to fetch a card.
