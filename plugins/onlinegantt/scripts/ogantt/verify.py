"""Compare a .gantt file with what the site's engine actually renders.

The engine dump is produced in the browser by the snippet in
references/site-guide.md ("Dump engine rows"), a JSON list of
{id, name, start, end, dur, unit, pred, res, prog, ms, parent}.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from . import gantt_io
from .model import parse_deps, deps_to_string, plan_from_spec
from .schedule import schedule, to_gantt


class compare:  # namespace-style helper used by the CLI
    @staticmethod
    def expected_rows(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for t, depth, parent in gantt_io.flatten(doc):
            res = ",".join(_res_label(r) for r in t.get("resources", []) or [])
            rows.append({
                "id": t.get("TaskID"), "name": t.get("TaskName"), "start": t.get("StartDate"), "end": t.get("EndDate"),
                "dur": t.get("Duration"), "unit": t.get("DurationUnit", "day"),
                "pred": _canon_pred(t.get("Predecessor")) if not t.get("subtasks") else None,
                "res": res, "prog": t.get("Progress", 0), "ms": (t.get("Duration") == 0 and not t.get("subtasks")),
                "parent": bool(t.get("subtasks")),
            })
        return rows

    @staticmethod
    def drift(doc: Dict[str, Any]) -> List[str]:
        """Tasks whose stored dates differ from what the engine will compute on load."""
        try:
            spec = gantt_io.to_spec(doc)
            spec["settings"] = {}  # display settings never affect dates; keep the simulation robust
            plan = plan_from_spec(spec, [])
            res = schedule(plan, on_conflict="deps")
            if res.errors:
                return [f"cannot simulate: {e}" for e in res.errors]
            sim = to_gantt(plan, res)
        except Exception as e:  # pragma: no cover
            return [f"cannot simulate: {e}"]
        stored = {t["TaskID"]: t for t, _, _ in gantt_io.flatten(doc)}
        out = []
        for t, _, _ in gantt_io.flatten(sim):
            s = stored.get(t["TaskID"])
            if not s or s.get("subtasks"):
                continue
            if s.get("StartDate") != t["StartDate"] or s.get("EndDate") != t["EndDate"]:
                out.append(f"task {t['TaskID']} {t['TaskName']!r}: stored {s.get('StartDate')} -> {s.get('EndDate')}, "
                           f"engine will show {t['StartDate']} -> {t['EndDate']}")
        return out

    @staticmethod
    def report(doc: Dict[str, Any], dump: List[Dict[str, Any]]) -> Tuple[str, bool]:
        exp = {r["id"]: r for r in compare.expected_rows(doc)}
        got = {}
        for r in dump:
            try:
                got[int(r.get("id"))] = r
            except (TypeError, ValueError):
                continue  # resource-view group rows have string ids
        lines = []
        ok = True
        for tid, e in exp.items():
            g = got.get(tid)
            if g is None:
                lines.append(f"MISSING  task {tid} {e['name']!r} not rendered by the site")
                ok = False
                continue
            diffs = []
            if (g.get("name") or "") != (e["name"] or ""):
                diffs.append(f"name {g.get('name')!r} != {e['name']!r}")
            for k in ("start", "end"):
                if _norm_iso(g.get(k)) != _norm_iso(e.get(k)):
                    diffs.append(f"{k} {g.get(k)} != {e.get(k)}")
            if not e["parent"] and _numeq(g.get("dur"), e.get("dur")) is False:
                diffs.append(f"duration {g.get('dur')} != {e.get('dur')}")
            if not e["parent"] and _canon_pred(g.get("pred")) != (e.get("pred") or ""):
                diffs.append(f"predecessor {g.get('pred')!r} != {e.get('pred')!r}")
            if (g.get("res") or "") != (e.get("res") or ""):
                diffs.append(f"resources {g.get('res')!r} != {e.get('res')!r}")
            if not e["parent"] and _numeq(g.get("prog"), e.get("prog")) is False:
                diffs.append(f"progress {g.get('prog')} != {e.get('prog')}")
            if bool(g.get("ms")) != bool(e.get("ms")):
                diffs.append(f"milestone {g.get('ms')} != {e.get('ms')}")
            if diffs:
                ok = False
                lines.append(f"DIFF     task {tid} {e['name']!r}: " + "; ".join(diffs))
            else:
                lines.append(f"ok       task {tid} {e['name']!r}")
        extra = [tid for tid in got if tid not in exp]
        if extra:
            ok = False
            lines.append(f"EXTRA    site shows task ids not in the file: {extra}")
        head = "VERIFIED - the site renders every task exactly as stored" if ok else "MISMATCH - see lines marked DIFF/MISSING/EXTRA"
        return head + "\n" + "\n".join(lines), ok


def _res_label(r: Dict[str, Any]) -> str:
    name = str(r.get("resourceName", r.get("resourceId", "")))
    unit = r.get("unit", 100)
    try:
        unit = float(unit)
    except (TypeError, ValueError):
        unit = 100.0
    return name if unit == 100 else f"{name}[{unit:g}%]"


def _canon_pred(p: Any) -> str:
    if p in (None, ""):
        return ""
    try:
        return deps_to_string(parse_deps(str(p)))
    except Exception:
        return re.sub(r"\s+", "", str(p)).upper()


def _norm_iso(v: Any) -> str:
    if not v:
        return ""
    v = str(v)
    return v.replace(".000Z", "Z")


def _numeq(a: Any, b: Any):
    try:
        return abs(float(a) - float(b)) < 0.01
    except (TypeError, ValueError):
        return None
