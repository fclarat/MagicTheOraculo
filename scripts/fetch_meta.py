#!/usr/bin/env python3
"""
Fetch the most played cards in competitive decks of each format from MTGTop8
("most played cards", maindeck and sideboard) and cache them to data/meta.json.
build_games_data.py turns them into each format's answer pool.

The result is a snapshot kept in the repo: the site never calls MTGTop8. The
build only fetches when data/meta.json is missing; refresh it by hand now and
then (the metagame moves) with:

    python scripts/fetch_meta.py --refresh
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "meta.json"
UA = "blackcatmagic/0.3 (personal hobby project)"
URL = "https://www.mtgtop8.com/topcards"

# our format -> (MTGTop8 format code, metagame id). The ids are MTGTop8's
# "All 2026 Decks" option for each format: the closest it has to "last year".
# Look them up in the metagame <select> of https://www.mtgtop8.com/topcards
PERIOD = "All 2026 Decks"
FORMATS = {
    "premodern": ("PREM", "345"),
    "modern": ("MO", "339"),
    "pauper": ("PAU", "342"),
    "legacy": ("LE", "338"),
}
MD_PAGES = 40   # 20 cards per page -> 800 maindeck cards
SB_PAGES = 15   # 300 sideboard cards
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
          "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
          "Snow-Covered Mountain", "Snow-Covered Forest"}

ROW = re.compile(r"<td id=\w+_1 class=L14>([^<]+)</td>\s*"
                 r"<td id=\w+_2 class=L14 align=center>([\d.]+) %")


def page(code, meta, n, board):
    """One page of the ranking: [(name, % of decks that play it)]."""
    body = urllib.parse.urlencode({
        "data": "1", "current_page": str(n), "format": code,
        f"metagame_sel[{code}]": meta, "maindeck": board, "lands": "1",
    }).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("latin-1")   # the site serves Latin-1
            return [(name.strip(), float(pct)) for name, pct in ROW.findall(html)]
        except Exception:
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"MTGTop8 page {n} of {code}/{board} failed")


def ranking(code, meta, board, pages):
    rows = []
    for n in range(1, pages + 1):
        got = page(code, meta, n, board)
        if not got:
            break
        rows += got
        time.sleep(1)          # be gentle: a hobby project, not a crawler
    return rows


def main():
    if OUT.exists() and "--refresh" not in sys.argv:
        print(f"Using cached {OUT.name} -- run with --refresh to update it")
        return
    out = {"source": "mtgtop8.com", "period": PERIOD,
           "fetched": date.today().isoformat(), "formats": {}}
    for fmt, (code, meta) in FORMATS.items():
        md = ranking(code, meta, "MD", MD_PAGES)
        sb = ranking(code, meta, "SB", SB_PAGES)
        # score = % of decks with the card main + % with it in the side (an upper
        # bound of "decks that play it"); ties keep MTGTop8's maindeck order
        cards = {}
        for i, (name, pct) in enumerate(md):
            cards.setdefault(name, [name, 0.0, 0.0, i])[1] = pct
        for name, pct in sb:
            cards.setdefault(name, [name, 0.0, 0.0, len(md)])[2] = pct
        ranked = sorted((c for c in cards.values() if c[0] not in BASICS),
                        key=lambda c: (-(c[1] + c[2]), c[3]))
        out["formats"][fmt] = [[n, m, s] for n, m, s, _ in ranked]
        print(f"{fmt}: {len(md)} maindeck + {len(sb)} sideboard rows -> {len(ranked)} cards")
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
