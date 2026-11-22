"""The two other answers a fetch can give: several cards, and none.

    python lists.py                         # the two example codes below
    python lists.py <shared code> <code>    # your own

- A code that several cards share returns all of them, as a plain list of signed cards. Present the list; do not pick one.
- A code that finds no card returns an empty list. That means the pack is not on the record, not that the medicine does not exist.

Dosidal identifies a medicine; it does not advise on its use.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://dosidal-api.ai/v1/fetch/"
HEADERS = {"User-Agent": os.environ.get("AGENT_NAME", "my-agent/0.1"), "Accept": "application/json"}


def fetch(code):
    req = urllib.request.Request(API + urllib.parse.quote(code, safe=""), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r), r.headers.get("x-dosidal-receipt")


def show(code):
    answer, receipt = fetch(code)
    if isinstance(answer, dict):
        print(code, "-> one card:", answer["card"], "| receipt:", receipt)
    elif answer:
        print(code, "->", len(answer), "cards share this code | receipt:", receipt)
        for card in answer:
            print("  ", card["card"], "|", card["record"]["level"], "| market", card["identity"]["market"], "| stamp", card["stamp"]["checked"])
    else:
        print(code, "-> [] no card: this pack is not on the record | receipt:", receipt)


if __name__ == "__main__":
    a = sys.argv[1:]
    show(a[0] if a else "NDA217806")        # an authorisation number: the authorisation's card and each of its packs
    show(a[1] if len(a) > 1 else "09506000134352")  # a well-formed barcode that is on no card
