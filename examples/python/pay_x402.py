"""The voluntary test payment over x402: one small payment, machine to machine, to try the payment flow.

It is voluntary. It unlocks nothing, raises no limit and is never required. No card is ever behind a payment.

    pip install -r requirements.txt
    python pay_x402.py                        # reads the live offer and prints it; nothing is paid
    PAYER_KEY=... python pay_x402.py          # pays in USDC (the offer's first entry)
    PAYER_KEY=... python pay_x402.py --open-usd   # pays in Open USD (the offer's second entry)

x402 runs inside the call: the address answers 402 Payment Required with its offer (USDC first, Open USD second, both on Base),
the x402 client signs a payment for the entry it picks and sends the same request again, and the answer carries the settlement.
The ceiling of the payment is read from the live offer itself: nothing is typed here, and the client refuses to pay more than the
offer asked.

PAYER_KEY is the private key of the wallet that pays. Keep it in your environment or a secret store; never commit it.
The answer carries a signed receipt and a caller token. The caller token is yours: keep it like a password. With it, the receipts
server's get_statement lists what your agents fetched and issue_auditor_key gives an outside auditor a read-only key.
"""
import asyncio
import base64
import json
import os
import sys

import httpx

URL = "https://dosidal-api.ai/v1/test-payment"
BASE = "eip155:8453"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
OPEN_USD = "0xB2000000000000000000002fEb517dFeC7415344"
BASE_RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
HEADERS = {"User-Agent": os.environ.get("AGENT_NAME", "my-agent/0.1"), "Accept": "application/json"}


def currency(asset):
    return {USDC.lower(): "USDC", OPEN_USD.lower(): "Open USD"}.get(asset.lower(), asset)


def read_offer():
    """The live offer: the 402 answer's PAYMENT-REQUIRED header (base64 JSON), or its body."""
    r = httpx.get(URL, headers=HEADERS, timeout=60)
    if r.status_code != 402:
        sys.exit(f"HTTP {r.status_code}: no offer is open at {URL}")
    h = r.headers.get("PAYMENT-REQUIRED")
    return json.loads(base64.b64decode(h)) if h else r.json()


async def pay(asset):
    from eth_account import Account
    from x402.client import x402Client
    from x402.http.clients.httpx import x402HttpxClient
    from x402.mechanisms.evm.exact.client import ExactEvmScheme
    from x402.mechanisms.evm.signers import EthAccountSigner, EthAccountSignerWithRPC

    entry = next(a for a in read_offer()["accepts"] if a["asset"].lower() == asset.lower())
    ceiling = entry["amount"]  # the ceiling is the offer's own amount, in the asset's smallest unit
    account = Account.from_key(os.environ["PAYER_KEY"])
    pick = lambda version, reqs: [r for r in reqs if str(getattr(r, "asset", "")).lower() == asset.lower()][0]
    # Open USD settles through Permit2: the signer reads the chain to prepare it. USDC signs a transfer authorisation (EIP-3009).
    signer = EthAccountSignerWithRPC(account, BASE_RPC) if asset == OPEN_USD else EthAccountSigner(account)
    client = x402Client(pick).register(BASE, ExactEvmScheme(signer)).set_spend_controls(
        {"allowed_assets": [{"network": BASE, "asset": asset, "max_amount_per_payment": ceiling}]})
    async with x402HttpxClient(client, headers=HEADERS, timeout=120) as c:
        r = await c.get(URL)
    print("HTTP", r.status_code, "|", currency(asset), "from", account.address)
    if r.status_code != 200:
        print("not paid:", r.json().get("error") if "json" in r.headers.get("content-type", "") else r.text[:300])
        sys.exit(1)
    settled = r.headers.get("PAYMENT-RESPONSE") or r.headers.get("X-PAYMENT-RESPONSE")
    if settled:
        s = json.loads(base64.b64decode(settled))
        print("settled:", s.get("success"), "| network:", s.get("network"), "| transaction:", s.get("transaction"))
    body = r.json()
    receipt = body.get("receipt") or {}
    print("receipt:", receipt.get("id"), "| kind:", receipt.get("kind"), "| check it at https://mcp.rco-dosidal.ai/mcp (verify_receipt)")
    print("caller token:", "received (not printed: keep it like a password)" if body.get("caller_token") else "none")


def main():
    offer = read_offer()
    for a in offer["accepts"]:
        print("accepts", currency(a["asset"]), "on", a["network"], f"({a['scheme']}, {a['extra'].get('assetTransferMethod')})", "pay to", a["payTo"])
    if not os.environ.get("PAYER_KEY"):
        print("No PAYER_KEY: nothing paid.")
        return
    asyncio.run(pay(OPEN_USD if "--open-usd" in sys.argv else USDC))


if __name__ == "__main__":
    main()
