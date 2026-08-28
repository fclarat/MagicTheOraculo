#!/usr/bin/env python3
"""
Build data/games.json: a lean, popularity-ranked subset of the cards for the
mini-games (Cardle / Wordle / MTG-dle). Only the fields the games need, and only
reasonably well-known cards (top by EDHREC rank, with an image), so targets are
guessable.

    python scripts/build_games_data.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
cards = src["cards"]

N = 6000
ranked = sorted((c for c in cards if c.get("id")),
                key=lambda c: c["rk"] if c.get("rk") is not None else 10 ** 9)

out = []
for c in ranked[:N]:
    tl = c["t"]
    st = tl.split("—", 1)[1].strip() if "—" in tl else ""
    out.append({
        "n": c["n"], "mc": c.get("mc", ""), "co": c["co"], "cmc": c["cmc"], "t": tl,
        "r": c["r"], "rk": c.get("rk"), "id": c["id"],
        "pt": c.get("pt"), "st": st,
    })

dest = ROOT / "data" / "games.json"
dest.write_text(json.dumps({"cards": out}, ensure_ascii=False,
                           separators=(",", ":")), encoding="utf-8")
kb = dest.stat().st_size / 1024
print(f"Wrote {len(out)} cards -> {dest} ({kb:.0f} KB)")
