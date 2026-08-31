#!/usr/bin/env python3
"""
Inject Open Graph + Twitter card meta into each page's <head> so shared links
show the branded og.png preview. Idempotent: skips pages that already have it.
Per-page title/description are reused from the page's own <title>/<meta>.

    python scripts/add_og.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://fclarat.github.io/MagicTheOraculo/"
FILES = ["index.html", "oraculo.html", "cardle.html", "grimorio.html", "zoom.html",
         "wordle.html", "mtgdle.html", "connections.html", "timeline.html"]

def attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;")

for fn in FILES:
    p = ROOT / fn
    if not p.exists():
        print(f"  skip (missing): {fn}")
        continue
    html = p.read_text(encoding="utf-8")
    if "og:image" in html:
        print(f"  skip (already has og): {fn}")
        continue
    tm = re.search(r"<title>(.*?)</title>", html, re.S)
    dm = re.search(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', html, re.S)
    title = tm.group(1).strip() if tm else "Magic The Mini Games"
    desc = dm.group(1).strip() if dm else "Juegos de Magic: The Gathering para adivinar cartas."
    url = BASE + ("" if fn == "index.html" else fn)
    block = "\n".join([
        '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{attr(title)}">',
        f'<meta property="og:description" content="{attr(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{BASE}og.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{attr(title)}">',
        f'<meta name="twitter:description" content="{attr(desc)}">',
        f'<meta name="twitter:image" content="{BASE}og.png">',
    ])
    if dm:
        html = html[:dm.end()] + "\n" + block + html[dm.end():]
    else:
        html = re.sub(r"</title>", "</title>\n" + block, html, count=1)
    p.write_text(html, encoding="utf-8")
    print(f"  added og: {fn}")
