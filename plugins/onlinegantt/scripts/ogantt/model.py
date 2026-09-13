"""Data model shared by the ogantt commands.

Two representations exist:

* the **plan spec** - a compact JSON written by hand (or by Claude); dates are
  local, durations are human ("5 days"), dependencies are strings;
* the **.gantt file** - the exact JSON onlinegantt.com reads and writes
  (see references/gantt-format.md).

This module holds constants, the spec schema, and the parsers for durations,
dependencies and colours.  Scheduling lives in schedule.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# ----------------------------------------------------------------- constants
COLUMN_NAMES = ["Task ID", "Task Name", "Start Date", "End Date", "Duration",
                "Progress %", "Dependency", "Resources", "Color", "Notes"]
COLUMN_DEFAULT_WIDTH = {"Task ID": "70", "Task Name": "350", "Start Date": "130", "End Date": "130",
                        "Duration": "130", "Progress %": "150", "Dependency": "150", "Resources": "200",
                        "Color": "100", "Notes": "200"}
COLUMN_DEFAULT_SHOW = {"Task ID": True, "Task Name": True}
COLUMN_ALIASES = {
    "id": "Task ID", "taskid": "Task ID", "task id": "Task ID",
    "name": "Task Name", "taskname": "Task Name", "task name": "Task Name", "task": "Task Name",
    "start": "Start Date", "startdate": "Start Date", "start date": "Start Date",
    "end": "End Date", "enddate": "End Date", "end date": "End Date", "finish": "End Date",
    "duration": "Duration",
    "progress": "Progress %", "progress %": "Progress %", "% complete": "Progress %", "percent": "Progress %",
    "dependency": "Dependency", "dependencies": "Dependency", "predecessor": "Dependency", "predecessors": "Dependency",
    "resources": "Resources", "resource": "Resources",
    "color": "Color", "colour": "Color",
    "notes": "Notes", "note": "Notes", "info": "Notes",
}

DATE_FORMATS = ["yyyy-MM-dd", "yyyy/MM/dd", "yyyy.MM.dd", "yyyy MMM dd", "dd-MM-yyyy", "dd/MM/yyyy",
                "dd.MM.yyyy", "dd MMM yyyy", "MM-dd-yyyy", "MM/dd/yyyy", "MM.dd.yyyy", "MMM dd, yyyy"]
TIME_FORMATS = {"HH:mm": "HH:mm", "24": "HH:mm", "24h": "HH:mm", "24 hour": "HH:mm",
                "h a": "h a", "12": "h a", "12h": "h a", "12 hour": "h a"}
DEPENDENCY_CONFLICT = ["Cancel Move", "Remove Dependency", "Add Offset to Dependency"]
ZOOM_LEVELS = {-9: "1 Hour", -8: "2 Hours", -7: "2 Hours", -6: "6 Hours", -5: "6 Hours", -4: "12 Hours",
               -3: "12 Hours", -2: "1 Day", -1: "1 Day", 0: "1 Day", 1: "1 Week", 2: "1 Week", 3: "1 Week",
               4: "1 Month", 5: "3 Months", 6: "3 Months", 7: "6 Months", 8: "6 Months", 9: "1 Year"}
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ALIASES = {"mon": "Monday", "tue": "Tuesday", "tues": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
               "thur": "Thursday", "thurs": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
               "الاثنين": "Monday", "الإثنين": "Monday", "الثلاثاء": "Tuesday", "الأربعاء": "Wednesday",
               "الاربعاء": "Wednesday", "الخميس": "Thursday", "الجمعة": "Friday", "السبت": "Saturday", "الأحد": "Sunday",
               "الاحد": "Sunday"}

# The 12 task-bar hues offered by the site's colour picker ("" = default: blue leaf / grey parent).
PALETTE = ["", "31", "61", "91", "121", "151", "181", "211", "241", "271", "301", "331"]
COLOR_NAMES = {
    "": "", "default": "", "none": "", "auto": "",
    "orange": "31", "amber": "31", "yellow": "61", "gold": "61", "lime": "91", "yellowgreen": "91",
    "green": "121", "teal": "151", "springgreen": "151", "mint": "151", "cyan": "181", "aqua": "181", "skyblue": "181",
    "blue": "211", "azure": "211", "indigo": "241", "navy": "241", "purple": "271", "violet": "271",
    "magenta": "301", "fuchsia": "301", "pink": "331", "rose": "331", "red": "331", "crimson": "331",
    # Arabic
    "برتقالي": "31", "أصفر": "61", "اصفر": "61", "أخضر": "121", "اخضر": "121", "أزرق": "211", "ازرق": "211",
    "بنفسجي": "271", "وردي": "331", "أحمر": "331", "احمر": "331", "سماوي": "181",
}
COLOR_LABEL = {"": "default", "31": "orange", "61": "yellow", "91": "lime", "121": "green", "151": "teal",
               "181": "cyan", "211": "blue", "241": "indigo", "271": "purple", "301": "magenta", "331": "pink/red"}
# Distinct ordering used when assigning colours automatically (by phase / by resource).
AUTO_COLOR_ORDER = ["211", "121", "31", "271", "181", "301", "61", "151", "241", "91", "331"]
STATUS_COLORS = {"complete": "121", "on-track": "211", "at-risk": "31", "overdue": "331", "not-started": ""}

DURATION_UNITS = {"day": "day", "days": "day", "d": "day", "يوم": "day", "أيام": "day", "ايام": "day",
                  "hour": "hour", "hours": "hour", "h": "hour", "hr": "hour", "hrs": "hour", "ساعة": "hour", "ساعات": "hour",
                  "minute": "minute", "minutes": "minute", "min": "minute", "mins": "minute", "m": "minute",
                  "دقيقة": "minute", "دقائق": "minute"}
WEEK_UNITS = {"week", "weeks", "w", "wk", "wks", "أسبوع", "اسبوع", "أسابيع", "اسابيع"}

EMPTY_NOTES = "<p><br></p>"


class SpecError(ValueError):
    pass


# ----------------------------------------------------------------- parsing
_DUR_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([A-Za-z؀-ۿ]*)\s*$")


def parse_duration(value: Any, default_unit: str = "day") -> tuple[float, str]:
    """'5 days' -> (5, 'day'); '4h' -> (4, 'hour'); 3 -> (3, 'day'); '2 weeks' -> (10, 'day')."""
    if value is None or value == "":
        raise SpecError("empty duration")
    if isinstance(value, (int, float)):
        return float(value), default_unit
    m = _DUR_RE.match(str(value))
    if not m:
        raise SpecError(f"Invalid duration {value!r}; use e.g. '5 days', '4 hours', '30 minutes' or a number of days")
    n = float(m.group(1))
    unit = m.group(2).lower().rstrip("s?") if m.group(2) else ""
    raw = m.group(2).lower()
    if raw in WEEK_UNITS or unit in ("week", "wk", "w"):
        return n * 5, "day"  # a week of work == 5 working days, whatever the calendar
    if not raw:
        return n, default_unit
    if raw in DURATION_UNITS:
        return n, DURATION_UNITS[raw]
    if unit in DURATION_UNITS:
        return n, DURATION_UNITS[unit]
    raise SpecError(f"Unknown duration unit in {value!r} (use days, hours or minutes)")


@dataclass
class Dep:
    pred: int
    type: str = "FS"          # FS | SS | FF | SF
    lag: float = 0.0          # in lag_unit
    lag_unit: str = "day"

    def to_string(self) -> str:
        s = f"{self.pred}{self.type}"
        if abs(self.lag) > 1e-9:
            n = self.lag
            n_txt = str(int(n)) if float(n).is_integer() else str(n)
            unit = self.lag_unit + ("" if abs(n) == 1 else "s")
            s += ("+" if n > 0 else "") + f"{n_txt} {unit}"
        return s


_DEP_RE = re.compile(r"^\s*(\d+)\s*([A-Za-z]{0,2})\s*(?:([+-])\s*([0-9]*\.?[0-9]+)\s*([A-Za-z]*)\s*)?$")


def parse_deps(value: Any) -> List[Dep]:
    """Accepts the site's string grammar ("2FS,3SS+1 day"), a list of strings,
    or a list of dicts {id|pred, type, lag}."""
    if value is None or value == "" or value == []:
        return []
    items: List[Any]
    if isinstance(value, str):
        items = [p for p in value.split(",") if p.strip()]
    elif isinstance(value, (int, float)):
        items = [str(int(value))]
    elif isinstance(value, list):
        items = value
    else:
        raise SpecError(f"Invalid deps value {value!r}")
    out: List[Dep] = []
    for it in items:
        if isinstance(it, dict):
            pred = it.get("id", it.get("pred", it.get("task")))
            typ = str(it.get("type", "FS")).upper()
            lag_v = it.get("lag", 0) or 0
            if isinstance(lag_v, str) and lag_v.strip():
                sign = -1 if lag_v.strip().startswith("-") else 1
                n, u = parse_duration(lag_v.strip().lstrip("+-"))
                lag, unit = sign * n, u
            else:
                lag, unit = float(lag_v), str(it.get("lagUnit", "day"))
            if pred is None:
                raise SpecError(f"Dependency without id: {it}")
            out.append(Dep(int(pred), typ, lag, unit))
            continue
        if isinstance(it, (int, float)):
            out.append(Dep(int(it)))
            continue
        m = _DEP_RE.match(str(it))
        if not m:
            raise SpecError(f"Invalid dependency {it!r}; use e.g. '2FS', '2SS+1 day', '5FF-4 hours'")
        pred = int(m.group(1))
        typ = (m.group(2) or "FS").upper()
        if typ not in ("FS", "SS", "FF", "SF"):
            raise SpecError(f"Invalid dependency type in {it!r} (FS, SS, FF or SF)")
        lag, unit = 0.0, "day"
        if m.group(4):
            n = float(m.group(4))
            u = (m.group(5) or "day").lower()
            if u in WEEK_UNITS:
                n, u = n * 5, "day"
            elif u in DURATION_UNITS:
                u = DURATION_UNITS[u]
            elif u.rstrip("s") in DURATION_UNITS:
                u = DURATION_UNITS[u.rstrip("s")]
            else:
                raise SpecError(f"Unknown lag unit in {it!r}")
            lag = n if m.group(3) == "+" else -n
            unit = u
        out.append(Dep(pred, typ, lag, unit))
    return out


def deps_to_string(deps: List[Dep]) -> str:
    return ",".join(d.to_string() for d in deps)


def parse_color(value: Any, strict: bool = False) -> tuple[str, Optional[str]]:
    """Returns (hue, warning). Names, palette hues and arbitrary hues (snapped) are accepted."""
    if value is None:
        return "", None
    v = str(value).strip()
    key = v.lower().replace(" ", "").replace("-", "")
    if key in COLOR_NAMES:
        return COLOR_NAMES[key], None
    if v in PALETTE:
        return v, None
    if re.match(r"^\d+(\.\d+)?$", v):
        hue = float(v) % 360
        nearest = min(PALETTE[1:], key=lambda p: min(abs(hue - int(p)), 360 - abs(hue - int(p))))
        if strict:
            raise SpecError(f"Colour {v!r} is not one of the site's 12 hues {PALETTE[1:]}")
        return nearest, f"colour {v} is not in the site's palette; snapped to {nearest} ({COLOR_LABEL[nearest]})"
    raise SpecError(f"Unknown colour {value!r}; use a name (green, blue, orange...) or a palette hue {PALETTE[1:]}")


def parse_local_datetime(value: Any) -> tuple[datetime, bool]:
    """'2026-10-04' -> (datetime(2026,10,4,0,0), False); '2026-10-04 13:00' -> (..., True).
    The bool tells whether a time of day was given."""
    if isinstance(value, datetime):
        return value, True
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day), False
    s = str(value).strip().replace("T", " ")
    for fmt, has_time in (("%Y-%m-%d %H:%M", True), ("%Y-%m-%d %H:%M:%S", True), ("%Y-%m-%d", False),
                          ("%Y/%m/%d", False), ("%d/%m/%Y", False), ("%d-%m-%Y", False), ("%d.%m.%Y", False)):
        try:
            return datetime.strptime(s, fmt), has_time
        except ValueError:
            continue
    raise SpecError(f"Invalid date {value!r}; use YYYY-MM-DD or 'YYYY-MM-DD HH:MM'")


def parse_local_date(value: Any) -> date:
    return parse_local_datetime(value)[0].date()


def normalise_day_names(names: Any) -> List[str]:
    if isinstance(names, str):
        parts = re.split(r"[,;/ ]+|\s+and\s+|\s+و\s+", names)
    else:
        parts = list(names)
    out: List[str] = []
    for p in parts:
        if not str(p).strip():
            continue
        k = str(p).strip().lower()
        cap = k[:1].upper() + k[1:]
        if cap in DAY_NAMES:
            out.append(cap)
        elif k[:3] in DAY_ALIASES:
            out.append(DAY_ALIASES[k[:3]])
        elif str(p).strip() in DAY_ALIASES:
            out.append(DAY_ALIASES[str(p).strip()])
        else:
            raise SpecError(f"Unknown day name {p!r}")
    return out


# ----------------------------------------------------------------- spec model
@dataclass
class Task:
    id: Optional[int]
    name: str
    start: Optional[datetime] = None      # local, may be date-only (see start_has_time)
    start_has_time: bool = False
    end: Optional[datetime] = None
    end_has_time: bool = False
    duration: Optional[float] = None      # in unit
    unit: str = "day"
    deps: List[Dep] = field(default_factory=list)
    progress: float = 0.0
    resources: List[Dict[str, Any]] = field(default_factory=list)  # {name, unit}
    color: str = ""
    notes: str = ""
    milestone: bool = False
    children: List["Task"] = field(default_factory=list)
    # filled by the scheduler
    sched_start: Optional[datetime] = None
    sched_end: Optional[datetime] = None
    sched_hours: float = 0.0
    warnings: List[str] = field(default_factory=list)
    governing_dep: Optional[int] = None
    path: str = ""

    @property
    def is_parent(self) -> bool:
        return bool(self.children)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


@dataclass
class Plan:
    name: str
    start: Optional[date]
    timezone: str
    utc_offset: Optional[str]
    work_week: List[str]
    work_time: List[Dict[str, float]]
    holidays: List[Dict[str, Any]]      # {from: date, to: date, name?}
    settings: Dict[str, Any]
    resources: List[str]
    tasks: List[Task]
    milestone_time: str = "end"        # "end" (17:00) or "start" (08:00)
    version: Optional[int] = None
    file_stem: Optional[str] = None
    work_on: List[date] = field(default_factory=list)   # calendar exceptions: days worked although outside workWeek
    intended_work_week: List[str] = field(default_factory=list)

    def all_tasks(self):
        for t in self.tasks:
            yield from t.walk()

    def leaves(self):
        return [t for t in self.all_tasks() if not t.is_parent]

    def by_id(self) -> Dict[int, Task]:
        return {t.id: t for t in self.all_tasks() if t.id is not None}


def _get(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def task_from_spec(d: dict, warnings: List[str], path: str = "") -> Task:
    if not isinstance(d, dict):
        raise SpecError(f"Task must be an object, got {d!r}")
    name = _get(d, "name", "TaskName", "title")
    if not name or not str(name).strip():
        raise SpecError(f"Task at {path or 'root'} has no name")
    t = Task(id=None, name=str(name).strip())
    t.path = path or t.name
    raw_id = _get(d, "id", "TaskID")
    if raw_id is not None:
        try:
            t.id = int(raw_id)
        except (TypeError, ValueError):
            raise SpecError(f"Task {t.name!r}: id must be an integer, got {raw_id!r}")
        if t.id <= 0:
            raise SpecError(f"Task {t.name!r}: id must be a positive integer")
    s = _get(d, "start", "StartDate")
    if s not in (None, ""):
        t.start, t.start_has_time = parse_local_datetime(s)
    e = _get(d, "end", "finish", "EndDate")
    if e not in (None, ""):
        t.end, t.end_has_time = parse_local_datetime(e)
    dur = _get(d, "duration", "Duration")
    if dur not in (None, ""):
        t.duration, t.unit = parse_duration(dur)
        if t.duration < 0:
            raise SpecError(f"Task {t.name!r}: negative duration")
    t.milestone = bool(_get(d, "milestone", default=False)) or (t.duration == 0 and dur not in (None, ""))
    if t.milestone:
        t.duration, t.unit = 0.0, "day"
    t.deps = parse_deps(_get(d, "deps", "dependencies", "predecessors", "predecessor", "Predecessor"))
    p = _get(d, "progress", "Progress", "percentComplete", default=0)
    try:
        t.progress = float(p)
    except (TypeError, ValueError):
        raise SpecError(f"Task {t.name!r}: progress must be a number 0-100")
    if not 0 <= t.progress <= 100:
        raise SpecError(f"Task {t.name!r}: progress {t.progress} must be between 0 and 100")
    res = _get(d, "resources", "resource", "assigned", "owner", default=[])
    if isinstance(res, str):
        res = [r.strip() for r in res.split(",") if r.strip()]
    for r in res:
        if isinstance(r, dict):
            nm = _get(r, "name", "resourceName", "resourceId")
            if not nm:
                raise SpecError(f"Task {t.name!r}: resource without name: {r}")
            t.resources.append({"name": str(nm).strip(), "unit": float(_get(r, "unit", default=100))})
        else:
            t.resources.append({"name": str(r).strip(), "unit": 100.0})
    col, warn = parse_color(_get(d, "color", "colour"))
    t.color = col
    if warn:
        warnings.append(f"Task {t.name!r}: {warn}")
    t.notes = str(_get(d, "notes", "note", "info", "description", default="") or "")
    kids = _get(d, "children", "subtasks", "tasks", default=[])
    for i, k in enumerate(kids or []):
        t.children.append(task_from_spec(k, warnings, f"{t.path} > {k.get('name', i) if isinstance(k, dict) else i}"))
    if t.is_parent and t.milestone:
        raise SpecError(f"Task {t.name!r}: a task with children cannot be a milestone")
    return t


def plan_from_spec(spec: dict, warnings: Optional[List[str]] = None) -> Plan:
    if warnings is None:
        warnings = []
    if not isinstance(spec, dict):
        raise SpecError("Plan spec must be a JSON object")
    name = str(_get(spec, "name", "project", "title", default="Plan")).strip() or "Plan"
    cal = spec.get("calendar", {}) or {}
    tzname = str(_get(cal, "timezone", default=_get(spec, "timezone", default="UTC")))
    utc_offset = _get(cal, "utcOffset", "offset")
    ww = normalise_day_names(_get(cal, "workWeek", "workDays", default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]))
    wt_raw = _get(cal, "workTime", "workHours", default=[{"from": 8, "to": 12}, {"from": 13, "to": 17}])
    work_time: List[Dict[str, float]] = []
    for r in wt_raw:
        if isinstance(r, str):  # "08:00-12:00"
            m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*$", r)
            if not m:
                raise SpecError(f"Invalid work-time range {r!r}; use {{'from': 8, 'to': 12}} or '08:00-12:00'")
            f = int(m.group(1)) + int(m.group(2) or 0) / 60
            t_ = int(m.group(3)) + int(m.group(4) or 0) / 60
            work_time.append({"from": f, "to": t_})
        else:
            work_time.append({"from": float(r["from"]), "to": float(r["to"])})
    if len(work_time) > 2:
        raise SpecError("The site supports at most two work-time ranges per day")
    for r in work_time:
        for k in ("from", "to"):
            if (r[k] * 2) != int(r[k] * 2):
                raise SpecError(f"Work time {r} must use whole or half hours (the site offers 30-minute steps)")
    hol: List[Dict[str, Any]] = []
    for h in _get(cal, "holidays", default=[]) or []:
        if isinstance(h, str):
            d0 = parse_local_date(h)
            hol.append({"from": d0, "to": d0, "name": ""})
        else:
            f = parse_local_date(_get(h, "from", "date", "start"))
            t_ = parse_local_date(_get(h, "to", "end", default=_get(h, "from", "date", "start")))
            if t_ < f:
                raise SpecError(f"Holiday {h} ends before it starts")
            hol.append({"from": f, "to": t_, "name": str(_get(h, "name", "label", default="") or "")})
    work_on: List[date] = []
    for d in _get(cal, "workOn", "openDays", "exceptions", default=[]) or []:
        if isinstance(d, dict):
            f = parse_local_date(_get(d, "from", "date"))
            t_ = parse_local_date(_get(d, "to", default=_get(d, "from", "date")))
            cur = f
            while cur <= t_:
                work_on.append(cur)
                cur = cur + __import__("datetime").timedelta(days=1)
        else:
            work_on.append(parse_local_date(d))
    settings = dict(spec.get("settings", {}) or {})
    start_raw = _get(spec, "start", "projectStart", "startDate")
    start = parse_local_date(start_raw) if start_raw not in (None, "") else None
    resources = [str(r).strip() if not isinstance(r, dict) else str(_get(r, "name", "resourceName")).strip()
                 for r in (_get(spec, "resources", "team", default=[]) or [])]
    tasks_raw = _get(spec, "tasks", "data", default=[])
    if not tasks_raw:
        raise SpecError("Plan has no tasks")
    tasks = [task_from_spec(t, warnings, str(t.get("name", i)) if isinstance(t, dict) else str(i)) for i, t in enumerate(tasks_raw)]
    plan = Plan(name=name, start=start, timezone=tzname, utc_offset=utc_offset, work_week=ww, work_time=work_time,
                holidays=hol, settings=settings, resources=resources, tasks=tasks,
                milestone_time=str(_get(spec, "milestoneTime", default="end")).lower(),
                version=_get(spec, "version"), file_stem=_get(spec, "fileStem", "fileName"),
                work_on=sorted(set(work_on)), intended_work_week=list(ww))
    if plan.milestone_time not in ("end", "start"):
        raise SpecError("milestoneTime must be 'end' or 'start'")
    return plan
