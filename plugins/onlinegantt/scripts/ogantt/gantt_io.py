"""Read, validate and decompile .gantt files (the JSON onlinegantt.com writes)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .calendar import WorkCalendar
from .model import (COLUMN_NAMES, DATE_FORMATS, DEPENDENCY_CONFLICT, EMPTY_NOTES, PALETTE, Dep, SpecError,
                    parse_deps)
from .tz import Zone, iso_z, parse_iso

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$")


def load_gantt(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise SpecError(f"{path} is not valid JSON ({e}); the site would show 'Invalid file'")
    if not isinstance(doc, dict) or "data" not in doc or "resources" not in doc:
        raise SpecError(f"{path}: a .gantt file must be an object with 'data' and 'resources' (the site requires both)")
    return doc


def dump_gantt(doc: Dict[str, Any]) -> str:
    """Serialise exactly like the site: compact JSON, no empty subtasks arrays."""
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return text.replace(',"subtasks":[]', "")


def walk(tasks: List[Dict[str, Any]], depth: int = 0, parent: Optional[Dict[str, Any]] = None):
    for t in tasks:
        yield t, depth, parent
        if t.get("subtasks"):
            yield from walk(t["subtasks"], depth + 1, t)


def flatten(doc: Dict[str, Any]) -> List[Tuple[Dict[str, Any], int, Optional[Dict[str, Any]]]]:
    return list(walk(doc.get("data", [])))


# ------------------------------------------------------------------ validate
def validate(doc: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Returns (errors, warnings). Errors = the site will reject/mangle the file.
    Warnings = it will load but not look the way the author probably intended."""
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(doc.get("data"), list):
        errors.append("'data' must be a list of tasks")
        return errors, warnings
    if not isinstance(doc.get("resources"), list):
        errors.append("'resources' must be a list")
        return errors, warnings
    res_ids = set()
    for r in doc["resources"]:
        if not isinstance(r, dict) or "resourceId" not in r or "resourceName" not in r:
            errors.append(f"resource entries need resourceId and resourceName: {r}")
        else:
            res_ids.add(str(r["resourceId"]))
    ids: Dict[Any, str] = {}
    flat = flatten(doc)
    parents = {id(t) for t, _, _ in flat if t.get("subtasks")}
    for t, depth, parent in flat:
        label = f"task {t.get('TaskID')} {t.get('TaskName')!r}"
        if "TaskID" not in t or "TaskName" not in t:
            errors.append(f"{label}: TaskID and TaskName are required")
            continue
        tid = t["TaskID"]
        if not isinstance(tid, int) or isinstance(tid, bool) or tid <= 0:
            errors.append(f"{label}: TaskID must be a positive integer")
        if tid in ids:
            errors.append(f"{label}: duplicate TaskID (also {ids[tid]!r})")
        ids[tid] = t.get("TaskName")
        for k in ("StartDate", "EndDate"):
            v = t.get(k)
            if v is None:
                warnings.append(f"{label}: missing {k}; the site will place the task at the project start")
            elif not isinstance(v, str) or not ISO_RE.match(v):
                errors.append(f"{label}: {k}={v!r} must be a UTC ISO string like 2026-10-04T05:00:00.000Z")
        if t.get("DurationUnit") not in ("day", "hour", "minute", None):
            errors.append(f"{label}: DurationUnit must be day, hour or minute")
        d = t.get("Duration")
        if d is not None and (not isinstance(d, (int, float)) or d < 0):
            errors.append(f"{label}: Duration must be a non-negative number")
        p = t.get("Progress", 0)
        if not isinstance(p, (int, float)) or not 0 <= p <= 100:
            errors.append(f"{label}: Progress must be 0..100")
        c = t.get("color", "")
        if c is None:
            warnings.append(f"{label}: color is null; use \"\" for the default colour")
        elif str(c) not in PALETTE:
            warnings.append(f"{label}: color {c!r} is not one of the site's 12 hues {PALETTE[1:]}; the bar renders but the Color column icon will be blank")
        if t.get("info") is not None and not isinstance(t.get("info"), str):
            errors.append(f"{label}: info (notes) must be a string (HTML)")
        for r in t.get("resources", []) or []:
            if not isinstance(r, dict) or "resourceId" not in r:
                errors.append(f"{label}: resource assignment needs resourceId/resourceName/unit: {r}")
            elif str(r["resourceId"]) not in res_ids:
                errors.append(f"{label}: resource {r['resourceId']!r} is not in the top-level resources list (renders blank on the site)")
            elif "unit" not in r:
                warnings.append(f"{label}: resource {r['resourceId']!r} has no unit; add \"unit\": 100")
        if id(t) in parents:
            if t.get("Predecessor") not in (None, ""):
                errors.append(f"{label}: is a parent but has Predecessor {t.get('Predecessor')!r}; the site ignores links on summary tasks")
        else:
            pred = t.get("Predecessor")
            if pred not in (None, ""):
                try:
                    parse_deps(pred)
                except SpecError as e:
                    errors.append(f"{label}: {e}")
        if d == 0 and t.get("StartDate") != t.get("EndDate"):
            warnings.append(f"{label}: milestone (Duration 0) should have StartDate == EndDate")
    # second pass: predecessor targets
    id_to_task = {t["TaskID"]: t for t, _, _ in flat if "TaskID" in t}
    for t, _, _ in flat:
        if id(t) in parents:
            continue
        pred = t.get("Predecessor")
        if pred in (None, ""):
            continue
        try:
            for dep in parse_deps(pred):
                if dep.pred not in id_to_task:
                    errors.append(f"task {t['TaskID']}: predecessor {dep.pred} does not exist")
                elif id(id_to_task[dep.pred]) in parents:
                    errors.append(f"task {t['TaskID']}: predecessor {dep.pred} is a parent task; the site drops such links (link to a leaf task)")
                elif dep.pred == t["TaskID"]:
                    errors.append(f"task {t['TaskID']}: depends on itself")
        except SpecError:
            pass
    adv = doc.get("advanced")
    if adv is None:
        warnings.append("no 'advanced' block; the site will apply default settings (Mon-Fri, 08-12/13-17, yyyy-MM-dd ...)")
    elif not isinstance(adv, dict):
        errors.append("'advanced' must be an object")
    else:
        cols = adv.get("columns")
        if cols is not None:
            names = [c.get("name") for c in cols if isinstance(c, dict)]
            if names[:len(names)] != COLUMN_NAMES[:len(names)] or len(names) > 10:
                errors.append(f"advanced.columns must be exactly these 10 entries in this order: {COLUMN_NAMES}")
            for c in cols:
                if isinstance(c, dict) and not (isinstance(c.get("width"), str) or isinstance(c.get("width"), (int, float))):
                    errors.append(f"column {c}: width must be a string number, e.g. \"130\"")
        if "dateFormat" in adv and adv["dateFormat"] not in DATE_FORMATS:
            errors.append(f"advanced.dateFormat {adv['dateFormat']!r} is not one of {DATE_FORMATS}")
        if "timeFormat" in adv and adv["timeFormat"] not in ("HH:mm", "h a"):
            errors.append("advanced.timeFormat must be 'HH:mm' or 'h a'")
        if "firstDayOfWeek" in adv and adv["firstDayOfWeek"] not in range(7):
            errors.append("advanced.firstDayOfWeek must be 0..6 (0 = Sunday)")
        if "zoomLevel" in adv and adv["zoomLevel"] not in range(-9, 10):
            errors.append("advanced.zoomLevel must be -9..9")
        if "dependencyConflict" in adv and adv["dependencyConflict"] not in DEPENDENCY_CONFLICT:
            errors.append(f"advanced.dependencyConflict must be one of {DEPENDENCY_CONFLICT}")
        ww = adv.get("workWeek")
        if ww is not None:
            bad = [d for d in ww if d not in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
            if bad or not ww:
                errors.append(f"advanced.workWeek must be a non-empty list of English day names; got {ww}")
        wt = adv.get("workTime")
        if wt is not None:
            if not isinstance(wt, list) or not 1 <= len(wt) <= 2:
                errors.append("advanced.workTime must be a list of 1 or 2 {from,to} ranges (hours)")
            else:
                for r in wt:
                    if not isinstance(r, dict) or not (0 <= float(r.get("from", -1)) < float(r.get("to", -1)) <= 24):
                        errors.append(f"advanced.workTime range {r} must satisfy 0 <= from < to <= 24")
        for h in adv.get("holidays", []) or []:
            if not isinstance(h, dict) or not all(isinstance(h.get(k), str) and ISO_RE.match(h[k]) for k in ("from", "to")):
                errors.append(f"advanced.holidays entry {h} must have ISO 'from' and 'to'")
        if "timezone" in adv and not isinstance(adv["timezone"], str):
            errors.append("advanced.timezone must be an IANA name string")
    return errors, warnings


# ---------------------------------------------------------------- decompile
def _plain_text(html: str) -> str:
    if not html or html == EMPTY_NOTES:
        return ""
    simple = re.fullmatch(r"(?:<p>(?:(?!<[a-zA-Z/]).)*?</p>)+", html, flags=re.S)
    if simple:
        parts = re.findall(r"<p>(.*?)</p>", html, flags=re.S)
        text = "\n\n".join(p.replace("<br>", "\n") for p in parts)
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&nbsp;", " ")
        if "<" not in text:
            return text
    return html  # keep rich HTML untouched


def to_spec(doc: Dict[str, Any], utc_offset: Optional[str] = None, name: str = "Plan",
            keep_dependent_dates: bool = False) -> Dict[str, Any]:
    """Turn a .gantt document back into an editable plan spec (local dates, readable durations).

    Tasks that have dependencies get no 'start' (their dates are derived from the links, and
    the engine re-derives them on load anyway) unless keep_dependent_dates=True; that keeps
    later edits free of spurious date/dependency conflicts."""
    adv = doc.get("advanced") or {}
    tzname = adv.get("timezone") or "UTC"
    zone = Zone(tzname, utc_offset)
    work_week = adv.get("workWeek") or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    work_time = adv.get("workTime") or [{"from": 8, "to": 12}, {"from": 13, "to": 17}]
    holidays = []
    for h in adv.get("holidays", []) or []:
        f = zone.to_local(parse_iso(h["from"])).date()
        t = zone.to_local(parse_iso(h["to"])).date()
        holidays.append({"from": f.isoformat(), "to": t.isoformat()})
    cal = WorkCalendar(work_week, work_time, [(datetime.fromisoformat(h["from"]).date(), datetime.fromisoformat(h["to"]).date()) for h in holidays])
    first_start = cal.ranges[0][0]
    last_end = cal.ranges[-1][1]

    def local(v: Optional[str]) -> Optional[datetime]:
        return zone.to_local(parse_iso(v)) if v else None

    def fmt_dt(dt: datetime, is_ms: bool) -> str:
        h = dt.hour + dt.minute / 60
        if (not is_ms and abs(h - first_start) < 1e-6) or (is_ms and abs(h - last_end) < 1e-6):
            return dt.strftime("%Y-%m-%d")
        return dt.strftime("%Y-%m-%d %H:%M")

    def conv(t: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {"id": t.get("TaskID"), "name": t.get("TaskName", "")}
        kids = t.get("subtasks") or []
        is_ms = (t.get("Duration") == 0) and not kids
        if not kids:
            s = local(t.get("StartDate"))
            if s and (keep_dependent_dates or not t.get("Predecessor")):
                out["start"] = fmt_dt(s, is_ms)
            if is_ms:
                out["milestone"] = True
            else:
                d = t.get("Duration")
                unit = t.get("DurationUnit", "day")
                if d is not None:
                    out["duration"] = f"{d:g} {unit}{'' if d == 1 else 's'}"
                elif t.get("EndDate"):
                    out["end"] = fmt_dt(local(t["EndDate"]), False)
            if t.get("Predecessor"):
                out["deps"] = t["Predecessor"]
        if t.get("Progress") not in (None, 0) and not kids:
            out["progress"] = t["Progress"]
        res = []
        for r in t.get("resources", []) or []:
            nm = r.get("resourceName", r.get("resourceId"))
            u = r.get("unit", 100)
            res.append(nm if u == 100 else {"name": nm, "unit": u})
        if res:
            out["resources"] = res
        if t.get("color"):
            out["color"] = t["color"]
        notes = _plain_text(t.get("info") or "")
        if notes:
            out["notes"] = notes
        if kids:
            out["children"] = [conv(k) for k in kids]
        return out

    starts = [local(t.get("StartDate")) for t, _, _ in flatten(doc) if t.get("StartDate")]
    spec: Dict[str, Any] = {
        "name": name,
        "start": min(starts).strftime("%Y-%m-%d") if starts else None,
        "calendar": {"timezone": tzname, "workWeek": work_week, "workTime": work_time, "holidays": holidays},
        "settings": {
            "dateFormat": adv.get("dateFormat", "yyyy-MM-dd"),
            "timeFormat": adv.get("timeFormat", "HH:mm"),
            "firstDayOfWeek": adv.get("firstDayOfWeek", 0),
            "zoomLevel": adv.get("zoomLevel", 0),
            "dependencyConflict": adv.get("dependencyConflict", "Add Offset to Dependency"),
            "columns": [c["name"] for c in adv.get("columns", []) if c.get("show")] or ["Task ID", "Task Name"],
            "columnWidths": {c["name"]: int(float(c["width"])) for c in adv.get("columns", []) if isinstance(c, dict)},
        },
        "resources": [r.get("resourceName", r.get("resourceId")) for r in doc.get("resources", [])],
        "tasks": [conv(t) for t in doc.get("data", [])],
    }
    if utc_offset:
        spec["calendar"]["utcOffset"] = utc_offset
    return spec
