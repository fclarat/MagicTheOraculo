#!/usr/bin/env python3
"""
Read the shared "searches" collection (cards players looked for but the oracle
didn't pin down) from Firestore and aggregate them, so we know which cards to
add / which features to sharpen next.

Usage:
    python scripts/fetch_searches.py <projectId> <apiKey>

Prints the most-requested cards, split by whether they're already in the pool
(inSet). Cards with inSet=False are missing from the grimoire -> add them.
Cards with inSet=True that show up a lot -> the oracle keeps failing to isolate
them; look at the answer `path` to see which feature is off.
"""
import collections
import json
import sys
import urllib.request

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
PROJECT, KEY = sys.argv[1], sys.argv[2]
BASE = (f"https://firestore.googleapis.com/v1/projects/{PROJECT}"
        f"/databases/(default)/documents/searches")


def val(f):
    if not f:
        return None
    for k in ("stringValue", "booleanValue", "timestampValue"):
        if k in f:
            return f[k]
    return None


def fetch_all():
    rows, token = [], None
    while True:
        url = f"{BASE}?pageSize=300&key={KEY}"
        if token:
            url += f"&pageToken={token}"
        with urllib.request.urlopen(url, timeout=30) as r:
            page = json.load(r)
        for d in page.get("documents", []):
            fields = d.get("fields", {})
            rows.append({k: val(v) for k, v in fields.items()})
        token = page.get("nextPageToken")
        if not token:
            break
    return rows


def main():
    rows = fetch_all()
    print(f"{len(rows)} searches collected\n")
    missing = collections.Counter()
    present = collections.Counter()
    for r in rows:
        name = r.get("name") or "?"
        (missing if r.get("inSet") in (False, "false") else present)[name] += 1
    print("== Not in the grimoire (ADD these) ==")
    for name, n in missing.most_common(40):
        print(f"  {n:>4}  {name}")
    print("\n== In the pool but kept losing (sharpen features) ==")
    for name, n in present.most_common(40):
        print(f"  {n:>4}  {name}")


if __name__ == "__main__":
    main()
