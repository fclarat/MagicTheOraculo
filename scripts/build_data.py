#!/usr/bin/env python3
"""
Build the FULL card dataset for Magic The Mini Games from Scryfall's `oracle_cards`
bulk (one entry per Oracle id: every real Magic card, ~28k).

Every feature is derived straight from official Scryfall fields -- structural
ones (colours, types, mana value, keywords, subtypes) plus ~40 semantic tags
approximated with regexes over the oracle text, echoing the tag questions the
original TwentyQuestions project got from Scryfall Tagger, but WITHOUT depending
on that private data.

Output: data/cards.json  (feature catalog + compact per-card records)
"""
import gzip
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "cards.json"
GZ = ROOT / "data" / "oracle-cards.jsonl.gz"
UA = "magic-the-mini-games/1.0 (personal hobby project)"


# --------------------------------------------------------------------------- #
#  Feature helpers (operate on the normalized ctx dict)
# --------------------------------------------------------------------------- #
def kw(c, *names):   return any(n in c["keywords"] for n in names)
def sub(c, *names):  return any(n in c["subtypes"] for n in names)
def has(c, pat):     return re.search(pat, c["oracle"]) is not None
def T(c, *words):    return any(w in c["type"] for w in words)


# each feature: (id, spanish question, category, predicate) -> True/False/None
FEATURES = [
    # ---- colours ---------------------------------------------------------
    ("white", "¿Es blanca?", "color", lambda c: "W" in c["colors"]),
    ("blue", "¿Es azul?", "color", lambda c: "U" in c["colors"]),
    ("black", "¿Es negra?", "color", lambda c: "B" in c["colors"]),
    ("red", "¿Es roja?", "color", lambda c: "R" in c["colors"]),
    ("green", "¿Es verde?", "color", lambda c: "G" in c["colors"]),
    ("colorless", "¿Es incolora?", "color", lambda c: len(c["colors"]) == 0),
    ("multicolor", "¿Es multicolor (dos o más colores)?", "color",
     lambda c: len(c["colors"]) >= 2),
    # ---- card types ------------------------------------------------------
    ("creature", "¿Es una criatura?", "type", lambda c: T(c, "Creature")),
    ("land", "¿Es una tierra?", "type", lambda c: T(c, "Land")),
    ("instant", "¿Es un instantáneo?", "type", lambda c: T(c, "Instant")),
    ("sorcery", "¿Es un conjuro?", "type", lambda c: T(c, "Sorcery")),
    ("artifact", "¿Es un artefacto?", "type", lambda c: T(c, "Artifact")),
    ("enchantment", "¿Es un encantamiento?", "type", lambda c: T(c, "Enchantment")),
    ("planeswalker", "¿Es un planeswalker?", "type", lambda c: T(c, "Planeswalker")),
    ("legendary", "¿Es legendaria?", "type", lambda c: T(c, "Legendary")),
    ("equipment", "¿Es un Equipo?", "type", lambda c: "Equipment" in c["type"]),
    ("aura", "¿Es un Aura?", "type", lambda c: "Aura" in c["type"]),
    ("vehicle", "¿Es un Vehículo?", "type", lambda c: "Vehicle" in c["type"]),
    ("saga", "¿Es una Saga?", "type", lambda c: "Saga" in c["type"]),
    # ---- mana value ------------------------------------------------------
    ("cmc0", "¿Cuesta 0 de maná?", "cost", lambda c: c["cmc"] == 0 and not T(c, "Land")),
    ("cmc_le1", "¿Cuesta 1 o menos de maná?", "cost", lambda c: c["cmc"] <= 1),
    ("cmc_ge3", "¿Cuesta 3 o más de maná?", "cost", lambda c: c["cmc"] >= 3),
    ("cmc_ge4", "¿Cuesta 4 o más de maná?", "cost", lambda c: c["cmc"] >= 4),
    ("cmc_ge5", "¿Cuesta 5 o más de maná?", "cost", lambda c: c["cmc"] >= 5),
    ("cmc_ge6", "¿Cuesta 6 o más de maná?", "cost", lambda c: c["cmc"] >= 6),
    ("cmc_ge8", "¿Cuesta 8 o más de maná?", "cost", lambda c: c["cmc"] >= 8),
    ("x_spell", "¿Tiene {X} en su coste de maná?", "cost", lambda c: "{X}" in c["mana_cost"]),
    # ---- rarity ----------------------------------------------------------
    ("rare_plus", "¿Es rara o mítica?", "rarity", lambda c: c["rarity"] in ("rare", "mythic")),
    ("mythic", "¿Es mítica?", "rarity", lambda c: c["rarity"] == "mythic"),
    ("common", "¿Es común?", "rarity", lambda c: c["rarity"] == "common"),
    # ---- power / toughness ----------------------------------------------
    ("pow_star", "¿Su fuerza es variable (*)?", "stats",
     lambda c: T(c, "Creature") and c["power"] is not None and "*" in c["power"]),
    ("pow_ge4", "¿Es una criatura con fuerza 4 o más?", "stats",
     lambda c: None if c["pow_star"] else (T(c, "Creature") and c["power_i"] is not None and c["power_i"] >= 4)),
    ("pow_ge6", "¿Es una criatura con fuerza 6 o más?", "stats",
     lambda c: None if c["pow_star"] else (T(c, "Creature") and c["power_i"] is not None and c["power_i"] >= 6)),
    ("pow_le1", "¿Es una criatura con fuerza 1 o menos?", "stats",
     lambda c: None if c["pow_star"] else (T(c, "Creature") and c["power_i"] is not None and c["power_i"] <= 1)),
    # ---- keywords --------------------------------------------------------
    ("flying", "¿Tiene Volar?", "keyword", lambda c: kw(c, "flying")),
    ("trample", "¿Tiene Arrollar?", "keyword", lambda c: kw(c, "trample")),
    ("deathtouch", "¿Tiene Toque mortal?", "keyword", lambda c: kw(c, "deathtouch")),
    ("lifelink", "¿Tiene Vínculo vital?", "keyword", lambda c: kw(c, "lifelink")),
    ("haste", "¿Tiene Prisa?", "keyword", lambda c: kw(c, "haste")),
    ("first_strike", "¿Tiene Daño de primer golpe (o doble golpe)?", "keyword",
     lambda c: kw(c, "first strike", "double strike")),
    ("vigilance", "¿Tiene Vigilancia?", "keyword", lambda c: kw(c, "vigilance")),
    ("menace", "¿Tiene Amenaza?", "keyword", lambda c: kw(c, "menace")),
    ("reach", "¿Tiene Alcance?", "keyword", lambda c: kw(c, "reach")),
    ("defender", "¿Tiene Defensor?", "keyword", lambda c: kw(c, "defender")),
    ("flash", "¿Tiene Destello (Flash)?", "keyword", lambda c: kw(c, "flash")),
    ("evasive_prot", "¿Tiene Antimaleficio, Protección o Ward?", "keyword",
     lambda c: kw(c, "hexproof", "shroud", "ward", "protection")),
    ("indestructible", "¿Es indestructible?", "keyword", lambda c: kw(c, "indestructible")),
    ("prowess", "¿Tiene Destreza (Prowess)?", "keyword", lambda c: kw(c, "prowess")),
    # ---- creature subtypes ----------------------------------------------
    ("t_dragon", "¿Es un Dragón?", "subtype", lambda c: sub(c, "dragon")),
    ("t_angel", "¿Es un Ángel?", "subtype", lambda c: sub(c, "angel")),
    ("t_demon", "¿Es un Demonio?", "subtype", lambda c: sub(c, "demon")),
    ("t_elf", "¿Es un Elfo?", "subtype", lambda c: sub(c, "elf")),
    ("t_goblin", "¿Es un Goblin?", "subtype", lambda c: sub(c, "goblin")),
    ("t_zombie", "¿Es un Zombie?", "subtype", lambda c: sub(c, "zombie")),
    ("t_human", "¿Es un Humano?", "subtype", lambda c: sub(c, "human")),
    ("t_wizard", "¿Es un Mago (Wizard)?", "subtype", lambda c: sub(c, "wizard")),
    ("t_warrior", "¿Es un Guerrero?", "subtype", lambda c: sub(c, "warrior")),
    ("t_soldier", "¿Es un Soldado?", "subtype", lambda c: sub(c, "soldier")),
    ("t_beast", "¿Es una Bestia?", "subtype", lambda c: sub(c, "beast")),
    ("t_spirit", "¿Es un Espíritu?", "subtype", lambda c: sub(c, "spirit")),
    ("t_elemental", "¿Es un Elemental?", "subtype", lambda c: sub(c, "elemental")),
    ("t_vampire", "¿Es un Vampiro?", "subtype", lambda c: sub(c, "vampire")),
    ("t_merfolk", "¿Es un Tritón (Merfolk)?", "subtype", lambda c: sub(c, "merfolk")),
    ("t_cat", "¿Es un Gato?", "subtype", lambda c: sub(c, "cat")),
    ("t_bird", "¿Es un Pájaro?", "subtype", lambda c: sub(c, "bird")),
    ("t_sliver", "¿Es un Fragmentado (Sliver)?", "subtype", lambda c: sub(c, "sliver")),
    ("t_eldrazi", "¿Es un Eldrazi?", "subtype", lambda c: sub(c, "eldrazi")),
    ("t_god", "¿Es un Dios?", "subtype", lambda c: sub(c, "god")),
    ("t_hydra", "¿Es una Hidra?", "subtype", lambda c: sub(c, "hydra")),
    ("t_dinosaur", "¿Es un Dinosaurio?", "subtype", lambda c: sub(c, "dinosaur")),
    # ---- semantic tags (regex over oracle text) -------------------------
    ("draw", "¿Puede hacerte robar cartas?", "effect", lambda c: has(c, r"draw[s]? \w+ card")),
    ("tutor", "¿Puede buscar una carta en tu biblioteca?", "effect", lambda c: has(c, r"search your library")),
    ("destroy", "¿Puede destruir un permanente?", "effect", lambda c: has(c, r"\bdestroy\b")),
    ("exile_perm", "¿Puede exiliar un permanente?", "effect", lambda c: has(c, r"exile target|exile all|exile that")),
    ("sweeper", "¿Puede destruir o exiliar varios permanentes a la vez?", "effect",
     lambda c: has(c, r"destroy all|destroy each|exile all|destroy every")),
    ("bounce", "¿Puede devolver un permanente a la mano?", "effect",
     lambda c: has(c, r"return .*to (its owner|their owner|your hand|owner)")),
    ("counter", "¿Puede contrarrestar un hechizo?", "effect", lambda c: has(c, r"counter target")),
    ("burn", "¿Puede hacer daño no de combate?", "effect", lambda c: has(c, r"deal[s]? \w+ damage")),
    ("burn_player", "¿Puede hacer daño directo a un jugador u oponente?", "effect",
     lambda c: has(c, r"damage to (any target|target player|each opponent|target opponent|that player)")),
    ("ramp", "¿Puede producir maná adicional?", "effect",
     lambda c: bool(c["produced_mana"]) or has(c, r"add \{")),
    ("land_ramp", "¿Puede poner tierras adicionales en el campo?", "effect",
     lambda c: has(c, r"onto the battlefield") and has(c, r"land")),
    ("lifegain", "¿Puede hacerte ganar vida?", "effect", lambda c: has(c, r"gain[s]? \w+ life|gain that much life")),
    ("pay_life", "¿Involucra pagar o perder vida?", "effect", lambda c: has(c, r"pay \w+ life|lose[s]? \w+ life")),
    ("sacrifice", "¿Involucra sacrificar un permanente?", "effect", lambda c: has(c, r"sacrifice")),
    ("discard", "¿Puede hacer descartar cartas?", "effect", lambda c: has(c, r"discard")),
    ("mill", "¿Puede moler cartas (mill) de una biblioteca?", "effect", lambda c: has(c, r"mill|puts? the top .* graveyard")),
    ("recursion", "¿Puede recuperar una carta del cementerio?", "effect",
     lambda c: has(c, r"return .*from .*graveyard|from your graveyard")),
    ("flicker", "¿Puede exiliar un permanente y devolverlo al campo?", "effect",
     lambda c: has(c, r"exile .*return") and has(c, r"battlefield")),
    ("tokens", "¿Puede crear fichas (tokens)?", "effect", lambda c: has(c, r"create .*token")),
    ("plus1", "¿Puede poner contadores +1/+1?", "effect", lambda c: has(c, r"\+1/\+1 counter")),
    ("counters_matter", "¿Le importan los contadores?", "effect", lambda c: has(c, r"counter")),
    ("copy", "¿Puede copiar un hechizo, permanente o habilidad?", "effect", lambda c: has(c, r"\bcopy\b")),
    ("cost_reduce", "¿Puede reducir el coste de hechizos?", "effect", lambda c: has(c, r"cost[s]? .*less to cast|costs \{")),
    ("untap", "¿Puede enderezar un permanente?", "effect", lambda c: has(c, r"\buntap\b")),
    ("tap_down", "¿Puede girar (tap) un permanente objetivo?", "effect", lambda c: has(c, r"tap target")),
    ("grant_kw", "¿Puede otorgar una habilidad a criaturas (volar, arrollar, etc.)?", "effect",
     lambda c: has(c, r"gain[s]? (flying|trample|haste|first strike|lifelink|vigilance|deathtouch)|creatures you control (have|gain)")),
    ("anthem", "¿Puede aumentar la fuerza de varias criaturas?", "effect",
     lambda c: has(c, r"creatures you control get \+")),
    ("kindred", "¿Le importa un tipo de criatura?", "effect",
     lambda c: has(c, r"creatures? of the chosen type|choose a creature type|of that type")),
    ("etb", "¿Tiene un efecto al entrar al campo de batalla?", "effect", lambda c: has(c, r"enters(?! the battlefield tapped\.$)")),
    ("activated", "¿Tiene una habilidad activada (coste: efecto)?", "effect", lambda c: has(c, r"\{[^}]*\}[^:]*:|: ")),
    ("dies_trigger", "¿Tiene un disparo cuando una criatura muere?", "effect", lambda c: has(c, r"dies")),
    ("attack_trigger", "¿Tiene un disparo cuando algo ataca?", "effect", lambda c: has(c, r"attacks")),
    ("mana_any", "¿Puede producir maná de cualquier color?", "effect",
     lambda c: len(c["produced_mana"]) >= 5 or has(c, r"any color")),
    ("mana_rock", "¿Es un artefacto (no criatura) que produce maná?", "effect",
     lambda c: T(c, "Artifact") and not T(c, "Creature") and bool(c["produced_mana"])),
    ("fetchland", "¿Es una tierra que se sacrifica para buscar otra tierra?", "effect",
     lambda c: T(c, "Land") and has(c, r"search your library for") and has(c, r"land")),
    ("tapland", "¿Es una tierra que entra girada?", "effect",
     lambda c: T(c, "Land") and has(c, r"enters (the battlefield )?tapped")),
    ("reserved", "¿Está en la Reserved List (clásica valiosa)?", "meta", lambda c: c["reserved"]),
    ("commander", "¿Puede ser tu comandante?", "meta",
     lambda c: (T(c, "Legendary") and T(c, "Creature")) or has(c, r"can be your commander")),
]


# --------------------------------------------------------------------------- #
def oracle_uri():
    req = urllib.request.Request("https://api.scryfall.com/bulk-data",
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cat = json.load(r)
    for b in cat["data"]:
        if b["type"] == "oracle_cards":
            return b["jsonl_download_uri"]
    raise RuntimeError("oracle_cards bulk not found")


def download(uri, dest):
    print(f"Downloading {uri}")
    req = urllib.request.Request(uri, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
    print(f"  saved {dest.stat().st_size/1e6:.1f} MB")


def merged(card, key):
    if card.get(key) is not None:
        return card[key]
    return " ".join(f.get(key, "") for f in card.get("card_faces", []) if f.get(key))


def merged_colors(card):
    if card.get("colors") is not None:
        return set(card["colors"])
    cols = set()
    for f in card.get("card_faces", []):
        cols.update(f.get("colors") or [])
    return cols


def normalize(card):
    tl = card.get("type_line") or ""
    subs = tl.split("—", 1)[1].lower().split() if "—" in tl else []
    power = card.get("power")
    if power is None and card.get("card_faces"):
        power = card["card_faces"][0].get("power")
    try:
        power_i = int(power) if power is not None and power not in ("*", "1+*", "2+*", "*+1") else None
    except ValueError:
        power_i = None
    tough = card.get("toughness")
    if tough is None and card.get("card_faces"):
        tough = card["card_faces"][0].get("toughness")
    ctx = {
        "name": card.get("name", ""),
        "colors": merged_colors(card),
        "type": tl,
        "subtypes": subs,
        "cmc": card.get("cmc", 0) or 0,
        "mana_cost": merged(card, "mana_cost"),
        "rarity": card.get("rarity", ""),
        "power": power, "power_i": power_i, "toughness": tough,
        "keywords": [k.lower() for k in card.get("keywords", [])],
        "oracle": (merged(card, "oracle_text") or "").lower(),
        "produced_mana": card.get("produced_mana") or [],
        "reserved": bool(card.get("reserved")),
        "rank": card.get("edhrec_rank"),
    }
    ctx["pow_star"] = bool(ctx["power"]) and "*" in str(ctx["power"])
    return ctx


SKIP_LAYOUTS = {"token", "double_faced_token", "emblem", "art_series",
                "planar", "scheme", "vanguard", "augment", "host"}
SKIP_TYPES = ("Token", "Emblem", "Plane ", "Phenomenon", "Scheme",
              "Vanguard", "Dungeon", "Basic Land", "Card ")


def keep(card):
    if card.get("layout") in SKIP_LAYOUTS:
        return False
    # NOTE: do NOT filter on games=paper -- a paper card's representative oracle
    # printing can be a digital one (e.g. Black Lotus via MTGO), which would
    # wrongly drop it. Instead exclude joke/digital-only cards explicitly.
    if card.get("set_type") in ("funny", "memorabilia", "token", "alchemy"):
        return False
    if card.get("name", "").startswith("A-"):   # Alchemy rebalanced duplicates
        return False
    tl = card.get("type_line") or ""
    if any(x in tl for x in SKIP_TYPES):
        return False
    if not card.get("name"):
        return False
    return True


def bit(v):
    return "?" if v is None else ("1" if v else "0")


def main():
    if not GZ.exists():
        download(oracle_uri(), GZ)
    else:
        print(f"Using cached {GZ.name} ({GZ.stat().st_size/1e6:.1f} MB) "
              "-- delete it to refresh")

    seen, out, n = set(), [], 0
    with gzip.open(GZ, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            card = json.loads(line)
            n += 1
            if not keep(card):
                continue
            name = card["name"]
            if name in seen:
                continue
            seen.add(name)
            ctx = normalize(card)
            fv = "".join(bit(fn(ctx)) for _, _, _, fn in FEATURES)
            rec = {"n": ctx["name"], "mc": ctx["mana_cost"], "cmc": int(ctx["cmc"]),
                   "co": "".join(sorted(ctx["colors"])), "t": ctx["type"],
                   "r": ctx["rarity"][:1] or "?", "rk": ctx["rank"], "f": fv,
                   "id": card.get("id")}  # Scryfall id -> reconstruct image URL
            if T(ctx, "Creature") and ctx["power"] is not None:
                rec["pt"] = f'{ctx["power"]}/{ctx["toughness"]}'
            out.append(rec)

    # popularity-first (nulls last) so the prior & tie-breaks favour known cards
    out.sort(key=lambda r: r["rk"] if r["rk"] is not None else 10**9)
    data = {"features": [{"id": i, "q": q, "c": cat} for i, q, cat, _ in FEATURES],
            "cards": out}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print(f"\nScanned {n} oracle entries -> kept {len(out)} cards, "
          f"{len(FEATURES)} features")
    print(f"Wrote {OUT}  ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
