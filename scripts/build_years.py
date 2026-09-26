#!/usr/bin/env python3
"""
Fetch the FIRST-print year of each answer card (famous, or famous within a
format) for the Timeline game from Scryfall and cache it to data/years.json
({name: {y, id, set}}). Resumable: re-running only fetches names not already
cached.

Names are looked up in batches with `prefer:oldest`, which returns each card's
earliest printing -- one request per BATCH cards instead of one per card.

    python scripts/build_years.py
"""
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "years.json"
UA = "blackcatmagic/0.3 (personal hobby project)"
BATCH = 20

years = {}
if OUT.exists():
    try:
        years = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        years = {}

def done(v):   # a good cached entry has the year, first-print id and its set
    return isinstance(v, dict) and v.get("y") and v.get("id") and v.get("set")

names = [c["n"] for c in GAMES["cards"] if c.get("fam") or c.get("ff")]
todo = [n for n in names if not done(years.get(n))]   # (re)fetch missing/old-format/failed
print(f"{len(names)} answer cards, {len(todo)} to fetch")


def get(url):
    """GET a Scryfall JSON page, honoring rate limits. None on 404 (no match)."""
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            wait = e.headers.get("Retry-After")           # 429/503: honor server, else exp backoff
            time.sleep(float(wait) if wait else min(2 ** attempt, 20))
        except Exception:
            time.sleep(min(2 ** attempt, 20))             # network hiccup: exp backoff
    raise RuntimeError(f"giving up on {url}")


def entry(card):
    rel = card.get("released_at", "")
    yr = int(rel[:4]) if rel[:4].isdigit() else None
    if yr and card.get("id") and card.get("set_name"):
        return {"y": yr, "id": card["id"], "set": card["set_name"]}
    return None


fails = []
for i in range(0, len(todo), BATCH):
    chunk = todo[i:i + BATCH]
    q = "(" + " or ".join(f'!"{n}"' for n in chunk) + ") prefer:oldest"
    url = "https://api.scryfall.com/cards/search?" + urllib.parse.urlencode({"q": q, "unique": "cards"})
    found = {}
    try:
        while url:
            page = get(url)
            if not page:
                break
            for c in page["data"]:
                found[c["name"]] = c
            url = page.get("next_page") if page.get("has_more") else None
            time.sleep(0.1)          # Scryfall asks for 50-100 ms between requests
    except RuntimeError:
        pass
    for n in chunk:
        years[n] = entry(found[n]) if n in found else None
        if not years[n]:
            fails.append(n)
    print(f"  {min(i + BATCH, len(todo))}/{len(todo)} (fails so far: {len(fails)})", flush=True)
    OUT.write_text(json.dumps(years, ensure_ascii=False), encoding="utf-8")

OUT.write_text(json.dumps(years, ensure_ascii=False), encoding="utf-8")
got = sum(1 for v in years.values() if v)
print(f"done: {got}/{len(years)} with a year -> {OUT}")
if fails:
    print(f"  no year for: {fails[:10]}")
