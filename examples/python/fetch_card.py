"""Fetch one card from Dosidal by each of its three codes, check its signature, then read and check the fetch's receipt.

    pip install -r requirements.txt
    python fetch_card.py                                   # the example pack below
    python fetch_card.py <barcode> <national pack code>     # any pack

1. fetch by the barcode on the pack (GTIN), over the Model Context Protocol (MCP) server
2. the same card by its national pack code
3. the same card by its authorisation number: the answer is a list (the authorisation and each of its packs), the same card in it
4. verify_card: the card's signature against Dosidal's public keys
5. the fetch's receipt, read and checked on the receipts server at mcp.rco-dosidal.ai/mcp (no key, no sign-in)
6. the same card over the web API

Every fetch is counted against the read limit and leaves a signed receipt.
Dosidal identifies a medicine; it does not advise on its use.
"""
import asyncio
import json
import os
import sys
import urllib.request

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP = "https://mcp.dosidal.ai/mcp"
RECEIPTS = "https://mcp.rco-dosidal.ai/mcp"
API = "https://dosidal-api.ai/v1/fetch/"
# Name your agent: the name travels as the User-Agent of every call.
HEADERS = {"User-Agent": os.environ.get("AGENT_NAME", "my-agent/0.1")}


async def call(url, name, args):
    """Call one tool. Returns (the answer, the receipt id the answer carries in _meta.receipt, if any)."""
    async with streamablehttp_client(url, headers=HEADERS) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
    answer = result.structuredContent if result.structuredContent is not None else json.loads(result.content[0].text)
    if isinstance(answer, dict) and set(answer) == {"result"}:  # a list answer comes wrapped as {"result": [...]}
        answer = answer["result"]
    meta = result.meta or {}
    return answer, meta.get("receipt")


def value(field):
    """The value of a card field ([] or None when the regulator does not publish it)."""
    v = (field or {}).get("value")
    return ", ".join(x["value"] if isinstance(x, dict) else str(x) for x in v) if isinstance(v, list) else v


async def main(gtin, pack_code):
    # 1. by the barcode on the pack
    card, receipt_id = await call(MCP, "fetch", {"code": gtin})
    print("1. by barcode", gtin, "->", card["card"])
    print("   name:", value(card["identity"]["name"]), "| market:", card["identity"]["market"], "| level:", card["record"]["level"])
    print("   codes: barcode", value(card["codes"]["gtin"]), "| national pack code", value(card["codes"]["national_pack_code"]),
          "| authorisation number", value(card["codes"]["authorisation_number"]))
    print("   status:", value(card["standing"]["status"]), "| holder:", value(card["holder"]))
    print("   stamp: checked against the regulator on", card["stamp"]["checked"], "(market", card["stamp"]["market"] + ")")
    print("   receipt:", receipt_id)

    # 2. the same card by its national pack code
    same, _ = await call(MCP, "fetch", {"code": pack_code})
    print("2. by national pack code", pack_code, "->", same["card"], "| same card:", same["card"] == card["card"])

    # 3. by its authorisation number: one authorisation has many packs, so the answer is a list. Present the list; do not pick.
    auth = card["codes"]["authorisation_number"]["value"][0]["value"]
    many, _ = await call(MCP, "fetch", {"code": auth})
    print("3. by authorisation number", auth, "->", len(many), "cards | the same card is in the list:", any(c["card"] == card["card"] for c in many))

    # 4. the card's signature
    check, _ = await call(MCP, "verify_card", {"card": card})
    print("4. verify_card ->", json.dumps(check)[:200])

    # 5. the receipt: written after the answer has gone, so read it once it is there
    for _ in range(10):
        got, _ = await call(RECEIPTS, "get_receipt", {"id": receipt_id})
        if got.get("found"):
            break
        await asyncio.sleep(2)  # get_receipt answers found: false until the receipt is written
    receipt = got["stored_receipt"]
    print("5. receipt", receipt["id"], "| chain:", receipt["chain"], "| seq:", receipt["seq"], "| cleared_at:", receipt["cleared_at"], "| cards:", receipt["cards"])
    verdict, _ = await call(RECEIPTS, "verify_receipt", {"receipt": receipt, "answer": card})
    print("   verify_receipt -> valid:", verdict.get("valid"), "| signature:", verdict.get("signature_valid"), "| hash:", verdict.get("hash_valid"),
          "| on the chain:", verdict.get("on_chain"), "| answer_hash matches the card:", verdict.get("answer_hash_matches"))

    # 6. the same card over the web API
    req = urllib.request.Request(API + urllib.request.quote(gtin), headers={**HEADERS, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        web = json.load(r)
        web_receipt = r.headers.get("x-dosidal-receipt")
    print("6. web API ->", web["card"], "| same signature:", web["signature"]["sig"] == card["signature"]["sig"], "| receipt:", web_receipt)


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main(a[0] if a else "00300020152018", a[1] if len(a) > 1 else "0002-0152-01"))
