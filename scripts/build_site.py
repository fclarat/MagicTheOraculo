#!/usr/bin/env python3
"""
Assemble the playable app from one source of truth.

Reads scripts/app.html (inner content: <style> + markup + <script> with a
`__DATA__` placeholder) and data/cards.json, then writes:

  oraculo.html   full standalone page for GitHub Pages (linked from the hub)
  artifact.html  inner content only, for publishing as a Claude Artifact

(index.html is the games hub, maintained by hand -- not generated here.)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
app = (ROOT / "scripts" / "app.html").read_text(encoding="utf-8")
data = (ROOT / "data" / "cards.json").read_text(encoding="utf-8")

inner = app.replace("__DATA__", data)

# artifact: inner content only (Claude wraps it in <html>/<head>/<body>)
(ROOT / "artifact.html").write_text(inner, encoding="utf-8")

# index.html: full standalone page
FAVICON = ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 100 100'><text y='.9em' font-size='90'>%F0%9F%94%AE</text></svg>")
page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Magic The Oráculo</title>
<meta name="description" content="Un oráculo de 20 preguntas que adivina tu carta de Magic: The Gathering por sus propiedades.">
<link rel="icon" href="{FAVICON}">
</head>
<body>
<a href="index.html" style="position:fixed;top:10px;left:12px;z-index:99;color:#a29bbb;text-decoration:none;font:13px 'Jost',sans-serif;letter-spacing:.04em">‹ juegos</a>
{inner}
</body>
</html>
"""
(ROOT / "oraculo.html").write_text(page, encoding="utf-8")

kb = len(inner.encode("utf-8")) / 1024
print(f"Built oraculo.html + artifact.html ({kb:.0f} KB each, data embedded).")
