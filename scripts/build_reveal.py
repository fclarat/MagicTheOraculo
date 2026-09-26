#!/usr/bin/env python3
"""
Build data/reveal.json (and reveal_<format>.json) for the "Grimorio" game: the full card sheet of each
famous card (flavor, rules, color, cost, type, power/toughness) with the NAME
redacted from the text, so the player guesses everything-but-the-name.

Source: the local Scryfall bulk (data/oracle-cards.jsonl.gz). No API calls.

    python scripts/build_reveal.py
"""
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GZ = ROOT / "data" / "oracle-cards.jsonl.gz"
GAMES = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
YEARS = json.loads((ROOT / "data" / "years.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "reveal.json"

TOKEN_LAYOUTS = {"token", "double_faced_token", "emblem", "art_series",
                 "planar", "scheme", "vanguard", "augment", "host"}

# name -> real card entry (skip tokens/emblems that share a card's name)
bulk = {}
with gzip.open(GZ, "rt", encoding="utf-8") as f:
    for line in f:
        line = line.strip().rstrip(",")
        if not line or line[0] != "{":
            continue
        try:
            c = json.loads(line)
        except Exception:
            continue
        if c.get("layout") in TOKEN_LAYOUTS:
            continue
        tl = c.get("type_line", "")
        if tl.startswith("Token") or "Emblem" in tl:
            continue
        bulk.setdefault(c["name"], c)


def redact(text, name):
    """Blank the card name — full, pre-comma part, and each name-word >=5 chars —
    so neither the rules nor the flavor leak the answer."""
    if not text:
        return text
    parts = {name}
    if "," in name:
        parts.add(name.split(",")[0].strip())
    for w in re.findall(r"[A-Za-z']+", name):
        if len(w) >= 5:
            parts.add(w)
    for p in sorted(parts, key=len, reverse=True):
        if len(p) >= 3:
            text = re.sub(r"\b" + re.escape(p) + r"\b", "▮▮▮", text, flags=re.IGNORECASE)
    return text


rows, missing = [], []
for c in GAMES["cards"]:
    if not (c.get("fam") or c.get("ff")):
        continue
    name = c["n"]
    b = bulk.get(name)
    if not b:
        missing.append(name)
        continue
    ot = redact(b.get("oracle_text") or "", name).strip()
    if not ot:
        continue  # no rules text = not enough to guess on (rare)
    pt = None
    if b.get("power") is not None and b.get("toughness") is not None:
        pt = f'{b["power"]}/{b["toughness"]}'
    y = YEARS.get(name) or {}
    rows.append({
        "n": name,
        "fl": redact(b.get("flavor_text") or "", name).strip() or None,
        "ot": ot,
        "mc": b.get("mana_cost") or "",
        "cmc": int(c.get("cmc", 0)),
        "co": c.get("co", ""),
        "t": b.get("type_line") or c.get("t", ""),
        "pt": pt,
        "fid": y.get("id") or c.get("fid") or c.get("id"),
    })
    # which answer pools this card belongs to (one file per pool, below)
    rows[-1]["fam"] = c.get("fam", 0)
    rows[-1]["ff"] = c.get("ff", 0)

# reveal.json holds the default pool and reveal_<format>.json each format's,
# so Grimorio only downloads the cards of the format being played
FORMAT_BITS = {"premodern": 1, "modern": 2, "pauper": 4, "legacy": 8}
pools = {OUT: [r for r in rows if r["fam"]]}
pools.update({OUT.with_name(f"reveal_{f}.json"): [r for r in rows if r["ff"] & b]
              for f, b in FORMAT_BITS.items()})
for dest, pool in pools.items():
    pool = [{k: v for k, v in r.items() if k not in ("fam", "ff")} for r in pool]
    dest.write_text(json.dumps({"cards": pool}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    withfl = sum(1 for r in pool if r["fl"])
    print(f"Wrote {len(pool)} cards ({withfl} with flavor) -> {dest.name} ({dest.stat().st_size / 1024:.0f} KB)")
if missing:
    print(f"  {len(missing)} famous not found in bulk (e.g. {missing[:6]})")
