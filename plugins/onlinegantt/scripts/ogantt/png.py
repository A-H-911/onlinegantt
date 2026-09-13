"""PNG rendering of the HTML preview with headless Chromium (Playwright).

Chromium is the only engine that draws the preview exactly (Arabic shaping, colours,
connector arrows).  Nothing is installed automatically: when Playwright or its Chromium
build is missing, the functions return an instruction string and the caller tells the user.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Optional, Tuple

_PY = os.path.basename(sys.executable) or "python3"
INSTALL_PLAYWRIGHT = f"{_PY} -m pip install playwright && {_PY} -m playwright install chromium"
INSTALL_CHROMIUM = f"{_PY} -m playwright install chromium"

MODE_SUFFIX = {"fit": "", "day": " (day scale)", "table": " (table)"}
MAX_SIDE = 16000  # Chromium screenshot limit is generous; keep images sane


def availability() -> Tuple[bool, str]:
    """(ok, message). Never installs anything."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, ("PNG renderer not installed. Playwright + Chromium are needed (about 150 MB download). "
                       f"Install with:  {INSTALL_PLAYWRIGHT}")
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
        return True, "ok"
    except Exception as e:  # browser binary missing or cannot launch
        return False, (f"Playwright is installed but Chromium cannot start ({str(e).splitlines()[0][:120]}). "
                       f"Install the browser with:  {INSTALL_CHROMIUM}")


def render_png(html: str, out_path: str, scale: int = 2, width: int = 1600,
               refit: Optional[Callable[[int], str]] = None) -> Tuple[bool, str]:
    """Write a PNG of `html` sized exactly to its content.

    refit(timeline_px) -> html: when given (fit mode), the table is measured first and the HTML
    is re-rendered so that table + timeline fill `width` CSS px.  Returns (ok, message)."""
    ok, msg = availability()
    if not ok:
        return False, msg
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 800}, device_scale_factor=scale)
        page.set_content(html, wait_until="load")
        if refit is not None:
            grid_w = page.evaluate("(()=>{const t=document.querySelector('table.grid');return t?t.getBoundingClientRect().width:0})()")
            page.set_content(refit(max(300, int(width - grid_w - 4))), wait_until="load")
        page.wait_for_timeout(100)
        w = int(page.evaluate("Math.ceil(document.body.getBoundingClientRect().width)"))
        h = int(page.evaluate("Math.ceil(document.body.getBoundingClientRect().height)"))
        page.set_viewport_size({"width": max(320, min(w, MAX_SIDE)), "height": max(120, min(h, MAX_SIDE))})
        page.wait_for_timeout(100)
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        page.screenshot(path=out_path, full_page=False)
        browser.close()
    return True, out_path


def png_name(stem: str, mode: str) -> str:
    return f"{stem}{MODE_SUFFIX.get(mode, ' (' + mode + ')')}.png"
