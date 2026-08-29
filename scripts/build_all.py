#!/usr/bin/env python3
"""
Build data/all.json — the FULL set of Magic cards (~32k) trimmed to just the
fields the mini-games need to let you TYPE/guess any card:

    n  name        co color       cmc mana value   mc mana cost
    t  type line   r  rarity      id  scryfall id  rk popularity rank

No feature bitstring (that's Oracle-only and heavy). Sorted most-popular first
so autocomplete surfaces well-known cards. The daily ANSWER still comes from the
curated famous set in games.json — this file only widens what you can type.

    python scripts/build_all.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
CARDS = SRC["cards"] if isinstance(SRC, dict) else SRC
OUT = ROOT / "data" / "all.json"

# co/cmc/t/r power MTG-dle's guess comparison; n is the autocomplete list.
# mc/id/rk aren't needed for typing (guessed cards show no image), so drop them
# to keep the download small. Sort by rank first, then discard it.
KEEP = ("n", "co", "cmc", "t", "r")
BIG = 10 ** 9  # cards without a rank sort to the end

rows = []
seen = set()
for c in CARDS:
    n = c.get("n")
    if not n or "//" in n or n in seen:   # skip split-card halves & dupes (match games.json)
        continue
    seen.add(n)
    rows.append(((c.get("rk") if c.get("rk") is not None else BIG),
                 {k: c.get(k) for k in KEEP if c.get(k) is not None}))

rows.sort(key=lambda pair: pair[0])
rows = [r for _, r in rows]
OUT.write_text(json.dumps({"cards": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
kb = OUT.stat().st_size / 1024
print(f"Wrote {len(rows)} cards -> {OUT} ({kb:.0f} KB)")
