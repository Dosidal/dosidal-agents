# dosidal-agents

**Agent tools and SDKs for Dosidal.** Connect your agent to the signed record of a prescription medicine and get a card on the first call.

Dosidal holds the regulator's own record of each prescription medicine (prescription drug) as a signed card. Fetch a card by its address or by any one of three codes: the barcode on the pack (Global Trade Item Number, GTIN), the national pack code, or the authorisation number. You get the card; or a list of cards where several share the code; or an empty list. Every card shows a stamp: the date it was last checked against the regulator. Every fetch leaves a signed receipt. Dosidal identifies a medicine; it does not advise on its use. Cards follow the open standard DOSE-10060.

Starter code only: no package to install from us. Page: [dosidal.ai/agent-tools](https://dosidal.ai/agent-tools).

## The address

```
https://mcp.dosidal.ai/mcp
```

Model Context Protocol (MCP), streamable HTTP, server name `dosidal`. No sign-in. Three tools: `fetch`, `verify_card`, `changes`.

## Setup

**Claude Code**

```
claude mcp add --transport http dosidal https://mcp.dosidal.ai/mcp
```

**Cursor** (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "dosidal": { "url": "https://mcp.dosidal.ai/mcp" }
  }
}
```

**VS Code** (`.vscode/mcp.json`)

```json
{
  "servers": {
    "dosidal": { "type": "http", "url": "https://mcp.dosidal.ai/mcp" }
  }
}
```

**Any other MCP client** that speaks streamable HTTP takes the same address. Plain HTTP works too:

```
curl -s https://mcp.dosidal.ai/mcp -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "fetch", "arguments": {"code": "00300020152018"}}}'
```

The files are in [setup/](setup/); `python setup/check_setup.py` connects to every server they name and lists its tools.

## Fetch: one example and its card

```
fetch {"code": "00300020152018"}
```

The barcode on the pack finds one card, at its own permanent address:

| Part of the card | In this card |
|---|---|
| Address | `https://dosidal.ai/pack/us/00300020152018` |
| Level, market | pack, US |
| Codes | barcode `00300020152018` · national pack code `0002-0152-01` · authorisation number `NDA217806` |
| Standing | status as the regulator publishes it, with its source and the date it was read |
| Signature | ES256 over the card (JCS form), key `dosidal-record-1.9dbf5d53` |
| Stamp | `checked`: the date the US market was last checked against the regulator |

The card also carries the name, substance, strength, form, pack size and holder as the regulator publishes them, each with the regulator's page it was read from and the date it was read.

## The three codes

A card is found by the barcode on the pack (a Global Trade Item Number, GTIN, with a valid check digit), by the regulator's own number for the pack (the national pack code), or by the regulator's number for the authorised medicine (the authorisation number), whichever the regulator publishes. All three are on the card. You do not say which kind of code you hold.

- **One card**: the signed card itself, with its stamp.
- **Several cards share the code**: all of them, as a plain list of signed cards. An authorisation number usually does this: the authorisation's own card and each of its packs. Present the list; do not pick.
- **No card**: an empty list. The pack is not on the record; that does not mean the medicine does not exist.

## The stamp

Every card shows a stamp: the date it was last checked against the regulator. Each full read of a market gives that market one signed stamp, and every card of the market shows it. The stamp is a date. Nothing expires.

## changes and verify_card

- **changes**: list the real changes to a country's cards since a date (`market`, `since`).
- **verify_card**: check a card's signature against Dosidal's public keys (`card`, as fetched).

## Web API

The same cards over plain web requests and JSON:

```
curl -s 'https://dosidal-api.ai/v1/fetch/00300020152018'
```

Also `POST /v1/verify` (a card), `GET /v1/changes/{market}`, `POST /v1/verify/receipt`. Description: [dosidal-api.ai/openapi.json](https://dosidal-api.ai/openapi.json).

## Receipts

Every fetch leaves a signed receipt: which card was read, and when. The answer carries the receipt's id, in the header `x-dosidal-receipt` and, over MCP, in `_meta.receipt`. The receipt is written after the answer has gone. Read it and check it on the receipts server, with no key and no sign-in:

```
https://mcp.rco-dosidal.ai/mcp      get_receipt {"id": "<receipt id>"}   verify_receipt {"receipt": ..., "answer": <the card>}
```

`verify_receipt` checks the receipt's hash, its signature and its place in the chain, and, given the answer, that the receipt's `answer_hash` is the hash of that answer.

## Read limit

2,000 fetches a day for each caller address, and 2,000 a day across every address of the network that owns it, counted over the UTC day. At the limit the answer is HTTP 429. No payment is offered or asked for. No caller and no crawler is exempt. Name your agent: every example sends `AGENT_NAME` as its User-Agent.

## Voluntary test payment

One small payment, machine to machine, to try the payment flow, at `https://dosidal-api.ai/v1/test-payment`. It is voluntary. It unlocks nothing, raises no limit and is never required. Standard: x402, inside the call. The address answers 402 with its offer: USDC first, Open USD second, both on Base. The x402 client pays and sends the same request again. The example reads the ceiling from the live offer; no amount is typed in it.

## Examples

| Example | Python | TypeScript |
|---|---|---|
| One card by its barcode, the same card by its national pack code and by its authorisation number; `verify_card`; that fetch's receipt read and checked at `mcp.rco-dosidal.ai/mcp`; the same card over the web API | [fetch_card.py](examples/python/fetch_card.py) | [fetch-card.ts](examples/typescript/fetch-card.ts) |
| A code several cards share, and a code that returns the empty list | [lists.py](examples/python/lists.py) | [lists.ts](examples/typescript/lists.ts) |
| The voluntary test payment over x402, ceiling read from the live offer | [pay_x402.py](examples/python/pay_x402.py) | [pay-x402.ts](examples/typescript/pay-x402.ts) |

```
cd examples/python && pip install -r requirements.txt && python fetch_card.py
cd examples/typescript && npm install && npx tsx fetch-card.ts
```

## Skill

[skills/dosidal/SKILL.md](skills/dosidal/SKILL.md): when an agent should fetch a card, which code to pass, how to read the card and its stamp, and how to keep and verify the receipt.

## Links

- [Agent tools and SDKs](https://dosidal.ai/agent-tools)
- [Docs](https://dosidal.ai/docs)
- [Agent card](https://dosidal.ai/.well-known/agent-card.json)
- [llms.txt](https://dosidal.ai/llms.txt)
- [Signing keys](https://dosidal-registry.ai/.well-known/jwks.json)
- [Standard: DOSE-10060](https://dose-10060.org/)
- [Library: the Book of DOSE](https://book-of-dose.org/)

Dosidal is a product record. It identifies a medicine and its regulatory status. It does not advise on use.

MIT licence. © 2027 Dosidal AI Corp.
