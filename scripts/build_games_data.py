#!/usr/bin/env python3
"""
Build data/games.json: a lean, popularity-ranked subset of the cards for the
mini-games. It also writes famous.json, the ~600-card answer pool used by every
game except MTG-dle, and famous_pm.json, the same idea restricted to the
Premodern format. Only the fields the games need are retained.

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
# Premodern answer pool: the most popular Premodern cards plus the era's icons,
# which EDHREC (a Commander site) underrates.
PM_N = 400
PM_FAMOUS = {
    "Psychatog", "Goblin Lackey", "Survival of the Fittest", "Replenish", "Opposition",
    "Stroke of Genius", "Tinker", "Yawgmoth's Will", "Mind Twist", "Necropotence",
    "Hypnotic Specter", "Serra Angel", "Shivan Dragon", "Lightning Bolt",
    "Force of Will", "Wasteland", "Brainstorm", "Swords to Plowshares", "Dark Ritual",
    "Counterspell", "Birds of Paradise", "Llanowar Elves", "Wrath of God", "Fireball",
    "Giant Growth", "Duress", "Goblin Piledriver", "Goblin Warchief",
    "Siege-Gang Commander", "Rancor", "Blastoderm", "Masticore", "Morphling",
    "Phyrexian Negator", "Flametongue Kavu", "Fact or Fiction", "Mother of Runes",
    "Exalted Angel", "Meddling Mage", "Call of the Herd", "Wild Mongrel", "Circular Logic",
    "Deep Analysis", "Mesmeric Fiend", "Stupefying Touch", "Accumulated Knowledge",
    "Faerie Conclave", "Treetop Village", "Mishra's Factory", "Parallax Wave",
    "Stasis", "Armageddon", "Balance", "Land Tax", "Enlightened Tutor", "Academy Rector",
    "Oath of Druids", "Sneak Attack", "Show and Tell", "Pernicious Deed", "Spiritmonger",
    "Nimble Mongoose", "Arrogant Wurm", "Squee, Goblin Nabob", "Volrath's Stronghold",
    "Crusade", "Glorious Anthem", "Lord of Atlantis", "Winter Orb", "Zuran Orb",
}
ranked = sorted((c for c in cards if c.get("id") and "//" not in c["n"]),
                key=lambda c: c["rk"] if c.get("rk") is not None else 10 ** 9)

pm_rank = [c for c in ranked if c.get("pm")]
PMF = {c["n"] for c in pm_rank[:PM_N]} | {c["n"] for c in pm_rank if c["n"] in PM_FAMOUS}

# keep every Premodern answer even if it falls outside the top-N popularity cut
top = ranked[:N]
top_names = {c["n"] for c in top}
top += [c for c in ranked[N:] if c["n"] in PMF and c["n"] not in top_names]

out = []
for c in top:
    tl = c["t"]
    st = tl.split("—", 1)[1].strip() if "—" in tl else ""
    # cards appended only for the Premodern pool must not change the default one
    fam = 1 if c["n"] in top_names and ((c.get("rk") is not None and c["rk"] <= FAME_RANK)
                                        or c["n"] in FAMOUS) else 0
    out.append({
        "n": c["n"], "mc": c.get("mc", ""), "co": c["co"], "cmc": c["cmc"], "t": tl,
        "r": c["r"], "rk": c.get("rk"), "id": c["id"],
        "pt": c.get("pt"), "st": st, "fam": fam,
    })
    if c.get("pm"):
        out[-1]["pm"] = 1
    if c["n"] in PMF:
        out[-1]["pmf"] = 1

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

# Most games only draw daily answers from the famous set. Keeping that subset
# separate means those pages no longer need to download the whole 6,000-card
# game pool just to choose one of ~600 recognizable cards.
famous = [c for c in out if c["fam"]]
famous_dest = ROOT / "data" / "famous.json"
famous_dest.write_text(json.dumps({"cards": famous}, ensure_ascii=False,
                                  separators=(",", ":")), encoding="utf-8")
famous_kb = famous_dest.stat().st_size / 1024
print(f"Wrote {len(famous)} famous cards -> {famous_dest} ({famous_kb:.0f} KB)")

pm_famous = [c for c in out if c.get("pmf")]
pm_dest = ROOT / "data" / "famous_pm.json"
pm_dest.write_text(json.dumps({"cards": pm_famous}, ensure_ascii=False,
                              separators=(",", ":")), encoding="utf-8")
pm_kb = pm_dest.stat().st_size / 1024
print(f"Wrote {len(pm_famous)} Premodern famous cards -> {pm_dest} ({pm_kb:.0f} KB)")
missing_pm = sorted(PM_FAMOUS - {c["n"] for c in pm_famous})
if missing_pm:
    print(f"  {len(missing_pm)} PM_FAMOUS names not found: {missing_pm}")
