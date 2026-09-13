#!/usr/bin/env python3
"""Regenerate the onlinegantt logos (plugins/onlinegantt/assets/logo*.svg).

The wordmark, tagline and Arabic line are outlined into paths, so the SVGs render the same
everywhere (GitHub, plugin lists, PDF exports) without depending on installed fonts.

    python -m pip install fonttools uharfbuzz
    python docs/logo/build_logo.py

Fonts (SIL Open Font License, fetched into docs/logo/fonts/ on first run from google/fonts):
  Inter[opsz,wght].ttf         the wordmark (wght 700) and the tagline (wght 500)
  NotoSansArabic[wdth,wght].ttf  the Arabic line (wght 500)

This is a maintenance tool, not part of the skill bundle, which stays standard-library only.
"""
from __future__ import annotations

import io
import os
import re
import sys
import urllib.request

try:
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
except ImportError:  # pragma: no cover
    sys.exit("needs: python -m pip install fonttools uharfbuzz")

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
ASSETS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "plugins", "onlinegantt", "assets")
FONT_URLS = {
    "Inter.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
    "NotoSansArabic.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf",
}

TAGLINE = "plans as .gantt files · a Claude skill"
ARABIC = "مهارة مخططات جانت"
AMBER = "#f59e0b"
PALETTE = {
    "light": dict(ink="#0f172a", muted="#64748b", tile="#2563eb"),
    "dark": dict(ink="#f8fafc", muted="#94a3b8", tile="#3b82f6"),
}

_cache: dict = {}


def font(name: str, axes: dict):
    key = (name, tuple(sorted(axes.items())))
    if key not in _cache:
        path = os.path.join(FONT_DIR, name)
        if not os.path.exists(path):
            os.makedirs(FONT_DIR, exist_ok=True)
            print(f"fetching {name} ...")
            urllib.request.urlretrieve(FONT_URLS[name], path)
        f = TTFont(path)
        if "fvar" in f:
            f = instancer.instantiateVariableFont(f, axes)
        buf = io.BytesIO()
        f.save(buf)
        face = hb.Face(hb.Blob(buf.getvalue()))
        _cache[key] = (f, hb.Font(face), face.upem)
    return _cache[key]


def text_path(fk, s: str, size: float, x: float, y: float, tracking: float = 0.0):
    """Outline `s` (shaped by HarfBuzz, so Arabic joins correctly) with its baseline-left at (x, y).
    Returns (path data, advance in px)."""
    f, hbfont, upem = fk
    scale = size / upem
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {})
    glyphs = f.getGlyphSet()
    order = f.getGlyphOrder()
    pen_x = 0.0
    parts = []
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        pen = SVGPathPen(glyphs)
        glyphs[order[info.codepoint]].draw(TransformPen(pen, (scale, 0, 0, -scale, x + (pen_x + pos.x_offset) * scale, y - pos.y_offset * scale)))
        if pen.getCommands():
            parts.append(pen.getCommands())
        pen_x += pos.x_advance + (tracking / scale if i < len(buf.glyph_infos) - 1 else 0)
    return re.sub(r"(\d+\.\d)\d+", r"\1", " ".join(parts)), pen_x * scale


def tile(x: float, y: float, s: float, colour: str) -> str:
    """The mark: a rounded tile with three white bars and an amber milestone."""
    k = s / 72
    out = [f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{16 * k:.1f}" fill="{colour}"/>']
    for bx, by, bw, op in ((10, 15, 28, 1.0), (21, 31, 32, 0.8), (32, 47, 17, 0.6)):
        out.append(f'<rect x="{x + bx * k:.1f}" y="{y + by * k:.1f}" width="{bw * k:.1f}" height="{10 * k:.1f}" '
                   f'rx="{5 * k:.1f}" fill="#ffffff" fill-opacity="{op}"/>')
    cx, cy, r = x + 58 * k, y + 52 * k, 7 * k
    out.append(f'<path d="M{cx:.1f} {cy - r:.1f} L{cx + r:.1f} {cy:.1f} L{cx:.1f} {cy + r:.1f} L{cx - r:.1f} {cy:.1f} Z" fill="{AMBER}"/>')
    return "\n".join(out)


def logo(theme: str) -> str:
    p = PALETTE[theme]
    inter_bold = font("Inter.ttf", {"wght": 700, "opsz": 32})
    inter_med = font("Inter.ttf", {"wght": 500, "opsz": 32})
    noto = font("NotoSansArabic.ttf", {"wght": 500, "wdth": 100})
    body = [tile(12, 20, 72, p["tile"])]
    d1, a1 = text_path(inter_bold, "online", 40, 104, 62, tracking=-0.48)
    d2, _ = text_path(inter_bold, "gantt", 40, 104 + a1 - 0.48, 62, tracking=-0.48)
    body.append(f'<path fill="{p["ink"]}" d="{d1}"/>')
    body.append(f'<path fill="{p["tile"]}" d="{d2}"/>')
    body.append(f'<path fill="{p["muted"]}" d="{text_path(inter_med, TAGLINE, 13.5, 106, 86)[0]}"/>')
    body.append(f'<path fill="{p["muted"]}" d="{text_path(noto, ARABIC, 13.5, 106, 104)[0]}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="440" height="112" viewBox="0 0 440 112" role="img" '
            'aria-label="onlinegantt — plans as .gantt files, a Claude skill">\n<title>onlinegantt</title>\n'
            + "\n".join(body) + "</svg>\n")


def main() -> int:
    for name, theme in (("logo.svg", "light"), ("logo-light.svg", "light"), ("logo-dark.svg", "dark")):
        path = os.path.join(ASSETS, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(logo(theme))
        print(f"wrote {os.path.relpath(path)} ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
