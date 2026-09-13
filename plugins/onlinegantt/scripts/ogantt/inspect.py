"""Plan analysis: summary table, critical path, status against today, and the
per-person workload / over-allocation check that the site itself does not do."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from . import gantt_io
from .calendar import WorkCalendar
from .model import COLOR_LABEL, parse_deps
from .tz import Zone, parse_iso


def _setup(doc: Dict[str, Any]):
    adv = doc.get("advanced") or {}
    zone = Zone(adv.get("timezone") or "UTC")
    hol = []
    for h in adv.get("holidays", []) or []:
        hol.append((zone.to_local(parse_iso(h["from"])).date(), zone.to_local(parse_iso(h["to"])).date()))
    cal = WorkCalendar(adv.get("workWeek") or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                       adv.get("workTime") or [{"from": 8, "to": 12}, {"from": 13, "to": 17}], hol)
    return zone, cal


def _rows(doc, zone):
    out = []
    for t, depth, parent in gantt_io.flatten(doc):
        s = zone.to_local(parse_iso(t["StartDate"])) if t.get("StartDate") else None
        e = zone.to_local(parse_iso(t["EndDate"])) if t.get("EndDate") else None
        out.append({"t": t, "depth": depth, "parent": parent, "start": s, "end": e, "id": t.get("TaskID"),
                    "name": t.get("TaskName", ""), "leaf": not t.get("subtasks"),
                    "ms": (t.get("Duration") == 0 and not t.get("subtasks"))})
    return out


def _dur_txt(t) -> str:
    d = t.get("Duration")
    if d is None:
        return ""
    u = t.get("DurationUnit", "day")
    return f"{d:g} {u}{'' if d == 1 else 's'}"


def _res_txt(t) -> str:
    parts = []
    for r in t.get("resources", []) or []:
        u = r.get("unit", 100)
        parts.append(r.get("resourceName", r.get("resourceId")) + ("" if u == 100 else f"[{u:g}%]"))
    return ", ".join(parts)


def summary(doc: Dict[str, Any], today: Optional[str] = None, workload: bool = True, table: bool = True) -> str:
    zone, cal = _setup(doc)
    rows = _rows(doc, zone)
    leaves = [r for r in rows if r["leaf"]]
    today_d = date.fromisoformat(today) if today else date.today()
    lines: List[str] = []
    if not rows:
        return "Plan is empty."
    starts = [r["start"] for r in rows if r["start"]]
    ends = [r["end"] for r in rows if r["end"]]
    p_start, p_end = min(starts), max(ends)
    adv = doc.get("advanced") or {}
    lines.append(f"## Plan summary")
    lines.append(f"- Span: {p_start:%Y-%m-%d} -> {p_end:%Y-%m-%d} ({cal.days_between(p_start, p_end):g} working days, "
                 f"{(p_end.date() - p_start.date()).days + 1} calendar days)")
    n_phase = sum(1 for r in rows if not r["leaf"])
    n_ms = sum(1 for r in leaves if r["ms"])
    lines.append(f"- Tasks: {len(leaves) - n_ms} work tasks, {n_ms} milestones, {n_phase} summary/phase rows; "
                 f"{len(doc.get('resources', []))} resources")
    ww_txt = ", ".join(d[:3] for d in adv.get("workWeek", []))
    wt_txt = ", ".join("%g-%g" % (r["from"], r["to"]) for r in adv.get("workTime", []))
    lines.append(f"- Calendar: {zone.name}; work week {ww_txt}; work time {wt_txt} ({cal.hours_per_day:g} h/day); "
                 f"{len(adv.get('holidays', []))} holiday range(s)")
    tot_h = sum(_hours(r['t'], cal) for r in leaves)
    done_h = sum(_hours(r['t'], cal) * float(r['t'].get('Progress', 0)) / 100 for r in leaves)
    lines.append(f"- Overall progress (duration-weighted): {100 * done_h / tot_h if tot_h else 0:.0f}%")

    if table:
        lines.append("")
        lines.append("## Tasks")
        lines.append("| ID | Task | Start | End | Duration | % | Deps | Resources | Colour |")
        lines.append("|---:|---|---|---|---|---:|---|---|---|")
        for r in rows:
            t = r["t"]
            indent = "  " * r["depth"]
            name = indent + ("**" + r["name"] + "**" if not r["leaf"] else ("◆ " + r["name"] if r["ms"] else r["name"]))
            lines.append(f"| {r['id']} | {name} | {r['start']:%Y-%m-%d} | {r['end']:%Y-%m-%d} | {_dur_txt(t)} | "
                         f"{float(t.get('Progress', 0)):g} | {t.get('Predecessor') or ''} | {_res_txt(t)} | "
                         f"{COLOR_LABEL.get(str(t.get('color', '')), t.get('color'))} |")

    # ---- critical path (chain of governing FS/SS/FF/SF links ending at the latest finish)
    by_id = {r["id"]: r for r in rows}
    latest = max(leaves, key=lambda r: r["end"])

    def chain_of(start_row):
        chain, cur, seen = [], start_row, set()
        while cur and cur["id"] not in seen:
            seen.add(cur["id"])
            chain.append(cur)
            gov, best = None, None
            for d in parse_deps(cur["t"].get("Predecessor") or ""):
                p = by_id.get(d.pred)
                if not p:
                    continue
                anchor = p["end"] if d.type in ("FS", "FF") else p["start"]
                if best is None or anchor > best:
                    best, gov = anchor, p
            cur = gov
        chain.reverse()
        return chain

    chain = chain_of(latest)
    lines.append("")
    lines.append("## Critical path (longest dependency chain to the plan finish)")
    if len(chain) > 1:
        lines.append(" -> ".join(f"{r['id']} {r['name']}" for r in chain))
        lines.append(f"Finish: {latest['end']:%Y-%m-%d}. Delaying any task on this chain delays the plan.")
    else:
        lines.append(f"The plan finish ({latest['end']:%Y-%m-%d}) is set by {latest['id']} {latest['name']!r}, which has no dependencies.")
        linked = [r for r in leaves if r["t"].get("Predecessor")]
        if linked:
            alt = chain_of(max(linked, key=lambda r: r["end"]))
            if len(alt) > 1:
                lines.append("Longest dependency chain: " + " -> ".join(f"{r['id']} {r['name']}" for r in alt) +
                             f" (ends {alt[-1]['end']:%Y-%m-%d})")

    # ---- status vs today
    lines.append("")
    lines.append(f"## Status as of {today_d.isoformat()}")
    overdue, at_risk, due_soon, in_prog = [], [], [], []
    now_local = datetime(today_d.year, today_d.month, today_d.day) + timedelta(days=1)
    for r in leaves:
        t = r["t"]
        prog = float(t.get("Progress", 0))
        if prog >= 100:
            continue
        if r["end"] < now_local - timedelta(days=1) and r["end"].date() < today_d:
            overdue.append(r)
        elif r["start"].date() <= today_d <= r["end"].date():
            in_prog.append(r)
            total = cal.hours_between(r["start"], r["end"])
            elapsed = cal.hours_between(r["start"], min(r["end"], cal.day_end(today_d)))
            expected = 100 * elapsed / total if total else 0
            if expected - prog > 25:
                at_risk.append((r, expected))
        elif today_d < r["start"].date() <= today_d + timedelta(days=7):
            due_soon.append(r)
    if overdue:
        lines.append("Overdue (end passed, not 100%):")
        for r in overdue:
            lines.append(f"  - {r['id']} {r['name']} - ended {r['end']:%Y-%m-%d}, {float(r['t'].get('Progress', 0)):g}%")
    if at_risk:
        lines.append("At risk (progress more than 25 points behind the elapsed time):")
        for r, exp in at_risk:
            lines.append(f"  - {r['id']} {r['name']} - expected ~{exp:.0f}%, actual {float(r['t'].get('Progress', 0)):g}%")
    if in_prog:
        lines.append("In progress: " + ", ".join(f"{r['id']} {r['name']}" for r in in_prog))
    if due_soon:
        lines.append("Starting within 7 days: " + ", ".join(f"{r['id']} {r['name']} ({r['start']:%Y-%m-%d})" for r in due_soon))
    if not (overdue or at_risk or in_prog or due_soon):
        lines.append("Nothing overdue, at risk, in progress or starting within 7 days.")

    if workload:
        lines.append("")
        lines.append("## Workload")
        lines.append(workload_report(doc, cal, zone))
    return "\n".join(lines)


def _hours(t, cal: WorkCalendar) -> float:
    d = t.get("Duration") or 0
    u = t.get("DurationUnit", "day")
    return d * cal.hours_per_day if u == "day" else d if u == "hour" else d / 60


def workload_report(doc: Dict[str, Any], cal: Optional[WorkCalendar] = None, zone: Optional[Zone] = None) -> str:
    if cal is None or zone is None:
        zone, cal = _setup(doc)
    rows = [r for r in _rows(doc, zone) if r["leaf"] and not r["ms"]]
    per_res_days: Dict[str, float] = defaultdict(float)
    per_res_tasks: Dict[str, int] = defaultdict(int)
    daily: Dict[Tuple[str, date], List[Tuple[float, Any]]] = defaultdict(list)
    unassigned = []
    for r in rows:
        t = r["t"]
        res = t.get("resources", []) or []
        if not res:
            unassigned.append(r)
            continue
        h = _hours(t, cal)
        for a in res:
            name = a.get("resourceName", a.get("resourceId"))
            unit = float(a.get("unit", 100)) / 100
            per_res_days[name] += h / cal.hours_per_day * unit
            per_res_tasks[name] += 1
            for d in cal.work_days_in(r["start"].date(), r["end"].date()):
                # hours of this task on day d
                s = max(r["start"], cal.day_start(d))
                e = min(r["end"], cal.day_end(d))
                hd = cal.hours_between(s, e) if e > s else 0
                if hd > 0:
                    daily[(name, d)].append((unit * hd / cal.hours_per_day, r))
    lines = []
    if not per_res_days and not unassigned:
        return "No resources assigned."
    lines.append("| Resource | Tasks | Assigned working days |")
    lines.append("|---|---:|---:|")
    for name in sorted(per_res_days, key=lambda n: -per_res_days[n]):
        lines.append(f"| {name} | {per_res_tasks[name]} | {per_res_days[name]:.1f} |")
    if unassigned:
        lines.append(f"\nUnassigned tasks ({len(unassigned)}): " + ", ".join(f"{r['id']} {r['name']}" for r in unassigned))
    # over-allocation: sum of (unit * fraction of day) > 1.0 on a day
    over: Dict[str, List[Tuple[date, float, List[Any]]]] = defaultdict(list)
    for (name, d), items in daily.items():
        load = sum(x for x, _ in items)
        if load > 1.0001:
            over[name].append((d, load, [r for _, r in items]))
    if over:
        lines.append("\nOver-allocation (more than 100% of a day across overlapping tasks):")
        for name, days in over.items():
            days.sort()
            # merge consecutive days with the same task set
            groups: List[Tuple[date, date, float, List[Any]]] = []
            for d, load, tasks in days:
                key = sorted(r["id"] for r in tasks)
                if groups and sorted(r["id"] for r in groups[-1][3]) == key and (d - groups[-1][1]).days <= 3:
                    groups[-1] = (groups[-1][0], d, max(groups[-1][2], load), tasks)
                else:
                    groups.append((d, d, load, tasks))
            for a, b, load, tasks in groups:
                span = f"{a:%Y-%m-%d}" if a == b else f"{a:%Y-%m-%d} to {b:%Y-%m-%d}"
                lines.append(f"  - {name}: {span} at {load * 100:.0f}% - " + ", ".join(f"{r['id']} {r['name']}" for r in tasks))
        lines.append("Options: shift or re-sequence the overlapping tasks, split the work with units (e.g. 50%), or assign someone else.")
    else:
        lines.append("\nNo over-allocation: nobody exceeds 100% on any working day.")
    return "\n".join(lines)
