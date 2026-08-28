#!/usr/bin/env python3
"""
Fetch the FIRST-print year of each famous card (for the Timeline game) from
Scryfall and cache it to data/years.json ({name: year}). Resumable: re-running
only fetches names not already cached.

    python scripts/build_years.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "years.json"
UA = "blackcatmagic/0.3 (personal hobby project)"

years = {}
if OUT.exists():
    try:
        years = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        years = {}

def done(v):   # a good cached entry has the year, first-print id and its set
    return isinstance(v, dict) and v.get("y") and v.get("id") and v.get("set")

names = [c["n"] for c in GAMES["cards"] if c.get("fam")]
todo = [n for n in names if not done(years.get(n))]   # (re)fetch missing/old-format/failed
print(f"{len(names)} famous cards, {len(todo)} to fetch")

for i, name in enumerate(todo, 1):
    q = urllib.parse.quote(f'!"{name}"')
    url = (f"https://api.scryfall.com/cards/search?q={q}"
           f"&unique=prints&order=released&dir=asc")
    ok = False
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            first = data["data"][0]                       # earliest printing
            rel = first.get("released_at", "")
            yr = int(rel[:4]) if rel[:4].isdigit() else None
            years[name] = {"y": yr, "id": first.get("id"), "set": first.get("set_name")} \
                if (yr and first.get("id") and first.get("set_name")) else None
            ok = True
            break
        except Exception:
            time.sleep(1.5)          # likely a 429; back off and retry
    if not ok:
        years[name] = None
    if i % 50 == 0:
        print(f"  {i}/{len(todo)}")
        OUT.write_text(json.dumps(years, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.2)                  # ~5 req/s, within Scryfall's limit

OUT.write_text(json.dumps(years, ensure_ascii=False), encoding="utf-8")
got = sum(1 for v in years.values() if v)
print(f"done: {got}/{len(years)} with a year -> {OUT}")
