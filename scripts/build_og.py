#!/usr/bin/env python3
"""
Render og.png (1200x630) — the share/link preview card for Magic The Mini Games.
Dark mystical background, the five WUBRG mana pips, the wordmark and a subtitle.

    python scripts/build_og.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "og.png"
W, H = 1200, 630

FONTS = Path("C:/Windows/Fonts")
def font(names, size):
    for n in names:
        p = FONTS / n
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()

f_title = font(["georgiab.ttf", "timesbd.ttf", "arialbd.ttf"], 82)
f_sub   = font(["georgiai.ttf", "georgia.ttf", "arial.ttf"], 32)
f_foot  = font(["segoeui.ttf", "arial.ttf"], 24)
f_pip   = font(["segoeuib.ttf", "arialbd.ttf"], 22)

# ---- background: vertical gradient + soft gold glow ----
img = Image.new("RGB", (W, H), "#0a0910")
top, bot = (0x1b, 0x15, 0x33), (0x0a, 0x09, 0x10)
px = img.load()
for y in range(H):
    t = y / H
    px_row = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    for x in range(W):
        px[x, y] = px_row

glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([W//2 - 420, -260, W//2 + 420, 300], fill=(227, 180, 90, 46))
glow = glow.filter(ImageFilter.GaussianBlur(90))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
d = ImageDraw.Draw(img)

# ---- gold frame + corner brackets ----
m = 26
d.rounded_rectangle([m, m, W - m, H - m], radius=22, outline=(169, 135, 63), width=2)
c, L = 52, 46
for cx, cy, dx, dy in [(c, c, 1, 1), (W - c, c, -1, 1), (c, H - c, 1, -1), (W - c, H - c, -1, -1)]:
    d.line([(cx, cy), (cx + dx * L, cy)], fill=(227, 180, 90), width=3)
    d.line([(cx, cy), (cx, cy + dy * L)], fill=(227, 180, 90), width=3)

# ---- WUBRG mana pips ----
pips = [("W", (0xf0, 0xe6, 0xc0), (0x5a, 0x4a, 0x1e)),
        ("U", (0x2b, 0x7d, 0xbf), (0xff, 0xff, 0xff)),
        ("B", (0x6a, 0x60, 0x80), (0xef, 0xea, 0xf5)),
        ("R", (0xd1, 0x3f, 0x2b), (0xff, 0xff, 0xff)),
        ("G", (0x2c, 0x9a, 0x5c), (0xff, 0xff, 0xff))]
r = 30
gap = 20
total = len(pips) * (2 * r) + (len(pips) - 1) * gap
x0 = (W - total) // 2
cy = 168
for i, (lab, bg, fg) in enumerate(pips):
    cx = x0 + i * (2 * r + gap) + r
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    d.ellipse([cx - r + 6, cy - r + 5, cx - r + 20, cy - r + 19], fill=tuple(min(255, v + 40) for v in bg))
    tb = d.textbbox((0, 0), lab, font=f_pip)
    d.text((cx - (tb[2] - tb[0]) / 2, cy - (tb[3] - tb[1]) / 2 - tb[1]), lab, font=f_pip, fill=fg)

def centered(text, y, fnt, fill):
    b = d.textbbox((0, 0), text, font=fnt)
    d.text(((W - (b[2] - b[0])) / 2 - b[0], y), text, font=fnt, fill=fill)

centered("Magic The Mini Games", 268, f_title, (227, 180, 90))
centered("8 juegos para adivinar cartas de Magic", 392, f_sub, (206, 196, 170))
centered("fclarat.github.io/MagicTheOraculo", 540, f_foot, (150, 130, 90))

img.save(OUT, "PNG")
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB, {W}x{H})")
