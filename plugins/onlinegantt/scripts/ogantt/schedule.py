"""Scheduler: turns a Plan (spec) into scheduled tasks and a .gantt document.

The site's engine re-schedules every dependent task on load: successor start =
(predecessor end/start + lag) snapped to working time - earlier *or* later than
the date stored in the file.  We reproduce that here so the file we write is
already what the site will show, and so date/dependency disagreements can be
reported instead of silently "fixed".
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .calendar import WorkCalendar
from .model import (COLUMN_ALIASES, COLUMN_DEFAULT_SHOW, COLUMN_DEFAULT_WIDTH, COLUMN_NAMES, DATE_FORMATS,
                    DEPENDENCY_CONFLICT, EMPTY_NOTES, TIME_FORMATS, ZOOM_LEVELS, Dep, Plan, SpecError, Task,
                    deps_to_string)
from .tz import Zone, iso_z


class ScheduleResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.moved: List[Dict[str, Any]] = []
        self.notes: List[str] = []       # things done automatically that the user should hear about
        self.review: List[str] = []      # things the user should be asked about (no automatic change)


def _lag_hours(dep: Dep, cal: WorkCalendar) -> float:
    if dep.lag_unit == "day":
        return dep.lag * cal.hours_per_day
    if dep.lag_unit == "hour":
        return dep.lag
    return dep.lag / 60.0


def duration_hours(task: Task, cal: WorkCalendar) -> float:
    if task.duration is None:
        return 0.0
    if task.unit == "day":
        return task.duration * cal.hours_per_day
    if task.unit == "hour":
        return task.duration
    return task.duration / 60.0


def hours_to_unit(hours: float, unit: str, cal: WorkCalendar) -> float:
    if unit == "day":
        return round(hours / cal.hours_per_day, 4)
    if unit == "hour":
        return round(hours, 4)
    return round(hours * 60, 2)


def make_calendar(plan: Plan) -> WorkCalendar:
    return WorkCalendar(plan.work_week, plan.work_time, [(h["from"], h["to"]) for h in plan.holidays])


def assign_ids(plan: Plan, res: ScheduleResult) -> None:
    """Missing ids get max+1 in document order (stable ids matter for later edits)."""
    seen: Dict[int, Task] = {}
    for t in plan.all_tasks():
        if t.id is not None:
            if t.id in seen:
                res.errors.append(f"Duplicate task id {t.id}: {seen[t.id].name!r} and {t.name!r}")
            seen[t.id] = t
    nxt = (max(seen) + 1) if seen else 1
    for t in plan.all_tasks():
        if t.id is None:
            t.id = nxt
            nxt += 1


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def apply_work_on(plan: Plan, res: ScheduleResult, span_end: Optional[date] = None) -> None:
    """calendar.workOn = days that must be working days although they fall outside workWeek
    (e.g. a Friday-Saturday office move in a Sunday-Thursday week). The site has one calendar per
    file, so this is expressed as: 7-day work week + every other off-day in the plan's span
    (plus 60 days of buffer) blocked as a holiday. Recomputed on every build, so it grows with the plan."""
    if not plan.work_on:
        return
    from datetime import timedelta
    intended = set(plan.intended_work_week)
    start = plan.start or min(plan.work_on)
    end = span_end or (max(plan.work_on) + timedelta(days=90))
    end = max(end, max(plan.work_on)) + timedelta(days=60)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    blocked = []
    d = start - timedelta(days=7)
    while d <= end:
        if day_names[d.weekday()] not in intended and d not in plan.work_on:
            blocked.append(d)
        d += timedelta(days=1)
    existing = {(h["from"], h["to"]) for h in plan.holidays}
    # merge consecutive blocked days into ranges
    ranges: List[Dict[str, Any]] = []
    for d in blocked:
        if ranges and (d - ranges[-1]["to"]).days == 1:
            ranges[-1]["to"] = d
        else:
            ranges.append({"from": d, "to": d, "name": "non-working"})
    added = 0
    for r in ranges:
        if (r["from"], r["to"]) not in existing:
            plan.holidays.append(r)
            added += 1
    plan.work_week = list(day_names)
    res.notes.append(f"calendar: {len(plan.work_on)} exception day(s) {', '.join(x.isoformat() for x in plan.work_on)} are working days; "
                     f"the file therefore uses a 7-day week with {added} blocked range(s) covering {start - timedelta(days=7)} .. {end} "
                     f"(re-computed on every build - extend the plan and the blocks follow)")


def schedule(plan: Plan, on_conflict: str = "ask", today: Optional[date] = None) -> ScheduleResult:
    """on_conflict: 'ask' (report, do not resolve), 'deps' (dependencies win),
    'lag' (keep the explicit date by adjusting the lag of the governing link),
    'dates' (keep the explicit date and drop the conflicting links)."""
    res = ScheduleResult()
    if on_conflict not in ("ask", "deps", "lag", "dates"):
        raise SpecError("on_conflict must be ask | deps | lag | dates")
    if plan.work_on:
        # pass 1 with the intended week to learn the span, then block the other off-days
        probe = _copy_plan(plan)
        probe.work_on = []
        pr = schedule(probe, on_conflict="deps", today=today)
        span_end = max((t.sched_end for t in probe.all_tasks() if t.sched_end), default=None)
        apply_work_on(plan, res, span_end.date() if span_end else None)
    cal = make_calendar(plan)
    assign_ids(plan, res)
    by_id = plan.by_id()

    # ---- static validation
    for t in plan.all_tasks():
        if t.is_parent and t.deps:
            res.errors.append(f"Task {t.id} {t.name!r} is a parent (has children) but has dependencies {deps_to_string(t.deps)}. "
                              "The site drops links on summary tasks - put the dependency on the first child instead.")
        if t.is_parent and (t.start or t.duration is not None):
            res.warnings.append(f"Task {t.id} {t.name!r}: start/duration on a parent are ignored (computed from children)")
        for d in t.deps:
            if d.pred not in by_id:
                res.errors.append(f"Task {t.id} {t.name!r} depends on unknown task id {d.pred}")
            elif by_id[d.pred].is_parent:
                last = _last_leaf(by_id[d.pred])
                res.errors.append(f"Task {t.id} {t.name!r} depends on {d.pred} {by_id[d.pred].name!r}, which is a parent. "
                                  f"The site drops links from summary tasks - link to its last leaf task {last.id} {last.name!r} (or another child) instead.")
            elif d.pred == t.id:
                res.errors.append(f"Task {t.id} depends on itself")
        if t.milestone and (t.duration or 0) != 0:
            res.errors.append(f"Milestone {t.id} {t.name!r} must have duration 0")
        if not t.is_parent and not t.milestone and t.duration is None and not (t.start and t.end):
            if t.end and not t.start and not t.deps:
                res.errors.append(f"Task {t.id} {t.name!r}: give a duration or a start date together with the end date")
            elif not t.end:
                res.warnings.append(f"Task {t.id} {t.name!r}: no duration given - assuming 1 day")
                t.duration, t.unit = 1.0, "day"
    declared = {r for r in plan.resources}
    for t in plan.all_tasks():
        for r in t.resources:
            if r["name"] not in declared:
                declared.add(r["name"])
                plan.resources.append(r["name"])
    if res.errors:
        return res

    # ---- topological order over leaves
    leaves = plan.leaves()
    order = _topo(leaves, res)
    if res.errors:
        return res

    project_start = plan.start
    if project_start is None:
        starts = [t.start for t in leaves if t.start]
        project_start = min(starts).date() if starts else date.today()
        plan.start = project_start
    default_start = cal.day_start(project_start)

    for t in order:
        dur_h = duration_hours(t, cal)
        explicit_start: Optional[datetime] = None
        explicit_end: Optional[datetime] = None
        if t.start:
            if t.milestone and not t.start_has_time:
                explicit_start = cal.day_end(t.start.date()) if plan.milestone_time == "end" else cal.day_start(t.start.date())
            else:
                explicit_start = cal.next_working_time(t.start)
        if t.end:
            explicit_end = cal.prev_working_time(t.end if t.end_has_time else t.end + timedelta(days=1))
        if t.duration is None and explicit_start and explicit_end:
            dur_h = cal.hours_between(explicit_start, explicit_end)
            t.duration, t.unit = hours_to_unit(dur_h, "day", cal), "day"
        elif explicit_end and not explicit_start and dur_h > 0:
            explicit_start = cal.sub_hours(explicit_end, dur_h)

        # dependency constraint
        dep_start: Optional[datetime] = None
        governing: Optional[Dep] = None
        for d in t.deps:
            p = by_id[d.pred]
            lag = _lag_hours(d, cal)
            if d.type == "FS":
                s = cal.add_hours(p.sched_end, lag)
            elif d.type == "SS":
                s = cal.add_hours(p.sched_start, lag)
            elif d.type == "FF":
                s = cal.sub_hours(cal.add_hours(p.sched_end, lag), dur_h)
            else:  # SF
                s = cal.sub_hours(cal.add_hours(p.sched_start, lag), dur_h)
            # the engine snaps a task start forward to working time, but places a
            # milestone exactly on the constraint instant (e.g. 17:00 at the predecessor's end)
            if not t.milestone:
                s = cal.next_working_time(s)
            if dep_start is None or s > dep_start:
                dep_start, governing = s, d

        if dep_start is not None and explicit_start is not None and dep_start != explicit_start:
            item = {"id": t.id, "name": t.name, "explicit": _fmt(explicit_start), "fromDeps": _fmt(dep_start),
                    "governing": governing.to_string() if governing else "", "delta_days": cal.days_between(
                        min(explicit_start, dep_start), max(explicit_start, dep_start)) * (1 if dep_start > explicit_start else -1)}
            res.conflicts.append(item)
            if on_conflict == "deps":
                start = dep_start
                res.moved.append({**item, "resolution": "dependencies win"})
            elif on_conflict == "lag":
                # adjust the governing link so it yields the explicit date
                diff_h = cal.hours_between(min(explicit_start, dep_start), max(explicit_start, dep_start))
                sign = 1 if explicit_start > dep_start else -1
                governing.lag = round(governing.lag + sign * (diff_h / cal.hours_per_day if governing.lag_unit == "day"
                                                                 else diff_h if governing.lag_unit == "hour" else diff_h * 60), 4)
                # re-evaluate with the new lag (other links may still push later)
                start = explicit_start
                for d in t.deps:
                    if d is governing:
                        continue
                    p = by_id[d.pred]
                    lag = _lag_hours(d, cal)
                    s = {"FS": lambda: cal.add_hours(p.sched_end, lag), "SS": lambda: cal.add_hours(p.sched_start, lag),
                         "FF": lambda: cal.sub_hours(cal.add_hours(p.sched_end, lag), dur_h),
                         "SF": lambda: cal.sub_hours(cal.add_hours(p.sched_start, lag), dur_h)}[d.type]()
                    s = cal.next_working_time(s)
                    if s > start:
                        start = s
                res.moved.append({**item, "resolution": f"lag on {governing.to_string()}"})
            elif on_conflict == "dates":
                keep = []
                for d in t.deps:
                    p = by_id[d.pred]
                    lag = _lag_hours(d, cal)
                    s = {"FS": lambda: cal.add_hours(p.sched_end, lag), "SS": lambda: cal.add_hours(p.sched_start, lag),
                         "FF": lambda: cal.sub_hours(cal.add_hours(p.sched_end, lag), dur_h),
                         "SF": lambda: cal.sub_hours(cal.add_hours(p.sched_start, lag), dur_h)}[d.type]()
                    if cal.next_working_time(s) == explicit_start:
                        keep.append(d)
                t.deps = keep
                start = explicit_start
                res.moved.append({**item, "resolution": "kept date, dropped conflicting links"})
            else:
                start = dep_start  # provisional; the caller is expected to stop and ask
        elif dep_start is not None:
            start = dep_start
        elif explicit_start is not None:
            start = explicit_start
        else:
            start = default_start
            if not t.deps:
                res.warnings.append(f"Task {t.id} {t.name!r}: no start date and no dependencies - placed at the project start {project_start}")
        t.governing_dep = governing.pred if governing else None
        t.sched_start = start
        t.sched_hours = dur_h
        t.sched_end = start if t.milestone else cal.add_hours(start, dur_h)
        if t.start and not t.milestone and cal.next_working_time(t.start) != t.start and t.start_has_time:
            res.warnings.append(f"Task {t.id} {t.name!r}: start {_fmt(t.start)} is outside working time; moved to {_fmt(cal.next_working_time(t.start))}")
        elif t.start and not t.milestone and not t.start_has_time and not cal.is_work_day(t.start.date()):
            res.warnings.append(f"Task {t.id} {t.name!r}: start {t.start.date()} is not a working day; moved to {t.sched_start.date()}")

    # ---- parents (bottom-up)
    def roll_up(t: Task) -> None:
        for c in t.children:
            if c.is_parent:
                roll_up(c)
        if t.is_parent:
            t.sched_start = min(c.sched_start for c in t.children)
            t.sched_end = max(c.sched_end for c in t.children)
            t.sched_hours = cal.hours_between(t.sched_start, t.sched_end)
            t.duration, t.unit = hours_to_unit(t.sched_hours, "day", cal), "day"
            weights = [(c.progress, duration_hours(c, cal) if not c.is_parent else c.sched_hours) for c in t.children]
            tot = sum(w for _, w in weights)
            t.progress = round(sum(p * w for p, w in weights) / tot, 2) if tot > 0 else 0.0
            t.milestone = False
    # milestones whose predecessors are all complete are complete themselves
    for t in leaves:
        if t.milestone and t.deps and t.progress < 100 and all(by_id[d.pred].progress >= 100 for d in t.deps if d.pred in by_id):
            t.progress = 100.0
            res.notes.append(f"milestone {t.id} {t.name!r} set to 100% because everything it waits for is complete")
    # progress on tasks that have not started yet - the user decides
    ref = today or date.today()
    for t in leaves:
        if not t.milestone and t.progress > 0 and t.sched_start and t.sched_start.date() > ref:
            res.review.append(f"task {t.id} {t.name!r} is {t.progress:g}% done but starts {t.sched_start:%Y-%m-%d} (after {ref}) - reset to 0%?")
    for t in plan.tasks:
        roll_up(t)
    return res


def _copy_plan(plan: Plan) -> Plan:
    import copy
    return copy.deepcopy(plan)


def _last_leaf(t: Task) -> Task:
    while t.is_parent:
        t = t.children[-1]
    return t


def _topo(leaves: List[Task], res: ScheduleResult) -> List[Task]:
    by_id = {t.id: t for t in leaves}
    indeg = {t.id: 0 for t in leaves}
    succ: Dict[int, List[int]] = {t.id: [] for t in leaves}
    for t in leaves:
        for d in t.deps:
            if d.pred in by_id:
                indeg[t.id] += 1
                succ[d.pred].append(t.id)
    ready = [t.id for t in leaves if indeg[t.id] == 0]
    out: List[Task] = []
    while ready:
        i = ready.pop(0)
        out.append(by_id[i])
        for s in succ[i]:
            indeg[s] -= 1
            if indeg[s] == 0:
                ready.append(s)
    if len(out) != len(leaves):
        cyc = [f"{t.id} {t.name!r}" for t in leaves if indeg[t.id] > 0]
        res.errors.append("Dependency cycle involving: " + ", ".join(cyc))
    return out


# ------------------------------------------------------------- .gantt output
def _notes_html(text: str) -> str:
    if not text or not text.strip():
        return EMPTY_NOTES
    if "<" in text and ">" in text:
        return text
    paras = [p.strip() for p in re.split(r"\n\s*\n|\r\n\s*\r\n", text) if p.strip()]
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return "".join(f"<p>{esc(p)}</p>" for p in paras)


def _columns(settings: Dict[str, Any], res: ScheduleResult) -> List[Dict[str, Any]]:
    visible = settings.get("columns", settings.get("visibleColumns"))
    widths = settings.get("columnWidths", {}) or {}
    shown: Dict[str, bool] = dict(COLUMN_DEFAULT_SHOW)
    if visible is not None:
        if isinstance(visible, str):
            visible = [v.strip() for v in visible.split(",") if v.strip()]
        shown = {}
        for v in visible:
            key = str(v).strip()
            canon = key if key in COLUMN_NAMES else COLUMN_ALIASES.get(key.lower())
            if not canon:
                raise SpecError(f"Unknown column {v!r}; valid: {COLUMN_NAMES}")
            shown[canon] = True
    out = []
    for name in COLUMN_NAMES:
        w = widths.get(name, widths.get(COLUMN_ALIASES.get(name.lower(), name), COLUMN_DEFAULT_WIDTH[name]))
        w = int(float(w))
        if not 50 <= w <= 1000:
            res.warnings.append(f"Column {name} width {w} clamped to 50..1000 (site limits)")
            w = min(1000, max(50, w))
        out.append({"name": name, "width": str(w), "show": bool(shown.get(name, False))})
    return out


def to_gantt(plan: Plan, res: ScheduleResult) -> Dict[str, Any]:
    cal = make_calendar(plan)
    zone = Zone(plan.timezone, plan.utc_offset)
    s = plan.settings

    def task_json(t: Task) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "TaskID": t.id,
            "TaskName": t.name,
            "StartDate": iso_z(zone.to_utc(t.sched_start)),
            "EndDate": iso_z(zone.to_utc(t.sched_end)),
            "Duration": _num(t.duration if t.duration is not None else 0),
            "Predecessor": None if t.is_parent else deps_to_string(t.deps),
            "resources": [{"resourceId": r["name"], "resourceName": r["name"], "unit": _num(r["unit"])} for r in t.resources],
            "Progress": _num(t.progress),
            "color": t.color,
            "info": _notes_html(t.notes),
            "DurationUnit": t.unit,
        }
        if t.is_parent:
            d["subtasks"] = [task_json(c) for c in t.children]
        return d

    date_format = s.get("dateFormat", "yyyy-MM-dd")
    if date_format not in DATE_FORMATS:
        raise SpecError(f"dateFormat {date_format!r} is not offered by the site; choose one of {DATE_FORMATS}")
    time_format = TIME_FORMATS.get(str(s.get("timeFormat", "HH:mm")).lower(), None) or TIME_FORMATS.get(s.get("timeFormat", "HH:mm"))
    if time_format is None:
        raise SpecError("timeFormat must be 'HH:mm' (24 hour) or 'h a' (12 hour)")
    fdow = s.get("firstDayOfWeek", 0)
    if isinstance(fdow, str):
        from .model import normalise_day_names
        fdow = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(normalise_day_names(fdow)[0])
    if fdow not in range(7):
        raise SpecError("firstDayOfWeek must be 0 (Sunday) .. 6 (Saturday)")
    zoom = int(s.get("zoomLevel", 0))
    if zoom not in ZOOM_LEVELS:
        raise SpecError(f"zoomLevel must be between -9 and 9; got {zoom}")
    conflict = s.get("dependencyConflict", "Add Offset to Dependency")
    if conflict not in DEPENDENCY_CONFLICT:
        raise SpecError(f"dependencyConflict must be one of {DEPENDENCY_CONFLICT}")

    ref_local = datetime(plan.start.year, plan.start.month, plan.start.day) if plan.start else datetime.now()
    advanced = {
        "columns": _columns(s, res),
        "zoomLevel": zoom,
        "timezone": plan.timezone,
        "timezoneOffset": zone.js_timezone_offset(ref_local),
        "dependencyConflict": conflict,
        "dateFormat": date_format,
        "timeFormat": time_format,
        "firstDayOfWeek": int(fdow),
        "workWeek": list(plan.work_week),
        "workTime": [{"from": _num(r["from"]), "to": _num(r["to"])} for r in plan.work_time],
        "holidays": [{"from": iso_z(zone.to_utc(datetime(h["from"].year, h["from"].month, h["from"].day))),
                      "to": iso_z(zone.to_utc(datetime(h["to"].year, h["to"].month, h["to"].day)))} for h in plan.holidays],
    }
    resources = [{"resourceId": r, "resourceName": r} for r in plan.resources]
    return {"data": [task_json(t) for t in plan.tasks], "resources": resources,
            "projectStartDate": None, "projectEndDate": None, "advanced": advanced}


def _num(x: float) -> Any:
    x = float(x)
    return int(x) if x.is_integer() else round(x, 4)
