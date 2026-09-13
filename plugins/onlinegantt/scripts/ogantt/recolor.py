"""Colour schemes for task bars (the site offers 12 hues; see model.PALETTE).

Schemes:
  phase    - every top-level phase gets its own hue; its leaf tasks inherit it
  resource - one hue per resource (first resource of a task decides); unassigned stays default
  status   - complete=green, overdue=pink/red, at-risk=orange; on-track / not started keep
             their current colour unless status_all=True (then blue / default)
  clear    - remove all colours

Several schemes may be combined; later ones override earlier ones wherever they
produce a colour ("phase" then "status" == phase colours with status exceptions).
The user decides that precedence - the skill asks.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from . import gantt_io
from .inspect import _setup
from .model import AUTO_COLOR_ORDER, STATUS_COLORS
from .tz import parse_iso


def apply(doc: Dict[str, Any], schemes: List[str], today: Optional[str] = None, status_all: bool = False) -> int:
    changed = 0
    for s in schemes:
        s = s.strip().lower()
        if s == "clear":
            for t, _, _ in gantt_io.flatten(doc):
                t["color"] = ""
                changed += 1
        elif s == "phase":
            for i, top in enumerate(doc.get("data", [])):
                hue = AUTO_COLOR_ORDER[i % len(AUTO_COLOR_ORDER)]
                for t, _, _ in gantt_io.walk([top]):
                    if not t.get("subtasks"):
                        t["color"] = hue
                        changed += 1
                    else:
                        t["color"] = ""  # summary bars stay grey like the site's default
        elif s == "resource":
            names = [r.get("resourceName", r.get("resourceId")) for r in doc.get("resources", [])]
            hue_of = {n: AUTO_COLOR_ORDER[i % len(AUTO_COLOR_ORDER)] for i, n in enumerate(names)}
            for t, _, _ in gantt_io.flatten(doc):
                if t.get("subtasks"):
                    continue
                res = t.get("resources") or []
                if res:
                    n = res[0].get("resourceName", res[0].get("resourceId"))
                    t["color"] = hue_of.get(n, "")
                    changed += 1
        elif s == "status":
            zone, cal = _setup(doc)
            today_d = date.fromisoformat(today) if today else date.today()
            for t, _, _ in gantt_io.flatten(doc):
                if t.get("subtasks"):
                    continue
                st = status_of(t, zone, cal, today_d)
                if st in ("complete", "overdue", "at-risk") or status_all:
                    t["color"] = STATUS_COLORS[st]
                    changed += 1
        else:
            raise ValueError(f"unknown colour scheme {s!r} (phase | resource | status | clear)")
    return changed


def status_of(t: Dict[str, Any], zone, cal, today_d: date) -> str:
    prog = float(t.get("Progress", 0) or 0)
    if prog >= 100:
        return "complete"
    if not t.get("StartDate") or not t.get("EndDate"):
        return "not-started"
    s = zone.to_local(parse_iso(t["StartDate"]))
    e = zone.to_local(parse_iso(t["EndDate"]))
    if e.date() < today_d:
        return "overdue"
    if s.date() > today_d:
        return "not-started"
    total = cal.hours_between(s, e)
    elapsed = cal.hours_between(s, min(e, cal.day_end(today_d)))
    expected = 100 * elapsed / total if total else 0
    return "at-risk" if expected - prog > 25 else "on-track"
