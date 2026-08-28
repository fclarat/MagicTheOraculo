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
FAME_RANK = 600   # cards this popular (or more) count as "famous" -> good game targets

# culturally-iconic cards that people picture even if their EDHREC rank is lower
FAMOUS = {
    "Black Lotus", "Ancestral Recall", "Time Walk", "Timetwister", "Mox Sapphire",
    "Mox Jet", "Mox Ruby", "Mox Pearl", "Mox Emerald", "Serra Angel", "Shivan Dragon",
    "Birds of Paradise", "Tarmogoyf", "Snapcaster Mage", "Dark Confidant", "Griselbrand",
    "Progenitus", "Emrakul, the Aeons Torn", "Ulamog, the Infinite Gyre", "Grave Titan",
    "Baneslayer Angel", "Wrath of God", "Swords to Plowshares", "Brainstorm", "Dark Ritual",
    "Demonic Tutor", "Path to Exile", "Fireball", "Giant Growth", "Mana Crypt",
    "Sensei's Divining Top", "Goblin Guide", "Thoughtseize", "Liliana of the Veil",
    "Jace, the Mind Sculptor", "Doubling Season", "Cyclonic Rift", "Blightsteel Colossus",
    "Consecrated Sphinx", "Akroma, Angel of Wrath", "Krenko, Mob Boss", "Lord of the Pit",
    "Birthing Pod", "Lightning Bolt", "Counterspell", "Sol Ring", "Llanowar Elves",
    "Craterhoof Behemoth", "Elesh Norn, Grand Cenobite", "Ragavan, Nimble Pilferer",
    "Sheoldred, the Apocalypse", "Ugin, the Spirit Dragon", "Karn Liberated",
    "Emrakul, the Promised End", "Nicol Bolas, God-Pharaoh", "Atraxa, Praetors' Voice",
}
ranked = sorted((c for c in cards if c.get("id") and "//" not in c["n"]),
                key=lambda c: c["rk"] if c.get("rk") is not None else 10 ** 9)

out = []
for c in ranked[:N]:
    tl = c["t"]
    st = tl.split("—", 1)[1].strip() if "—" in tl else ""
    fam = 1 if ((c.get("rk") is not None and c["rk"] <= FAME_RANK) or c["n"] in FAMOUS) else 0
    out.append({
        "n": c["n"], "mc": c.get("mc", ""), "co": c["co"], "cmc": c["cmc"], "t": tl,
        "r": c["r"], "rk": c.get("rk"), "id": c["id"],
        "pt": c.get("pt"), "st": st, "fam": fam,
    })

# merge first-print data (from build_years.py) so games can show the ORIGINAL,
# recognizable art instead of a random recent reprint. fid = first-print card id.
try:
    yrs = json.loads((ROOT / "data" / "years.json").read_text(encoding="utf-8"))
except Exception:
    yrs = {}
merged = 0
for c in out:
    y = yrs.get(c["n"])
    if isinstance(y, dict) and y.get("id"):
        c["fid"] = y["id"]
        if y.get("y"):
            c["yr"] = y["y"]
        if y.get("set"):
            c["set"] = y["set"]
        merged += 1

dest = ROOT / "data" / "games.json"
dest.write_text(json.dumps({"cards": out}, ensure_ascii=False,
                           separators=(",", ":")), encoding="utf-8")
kb = dest.stat().st_size / 1024
print(f"Wrote {len(out)} cards ({merged} with first-print art) -> {dest} ({kb:.0f} KB)")
