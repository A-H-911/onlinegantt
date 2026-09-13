"""Self-contained HTML preview of a .gantt document (no JavaScript, no external assets).

Mirrors the site's look: grey summary bars, coloured task bars using the same
hsl(hue,100%,50%) palette, darker progress fill, milestone diamonds, FS/SS/FF/SF
connector arrows, shaded non-working days, a red 'today' line.
"""
from __future__ import annotations

import html
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from . import gantt_io
from .calendar import WorkCalendar
from .model import COLOR_LABEL, parse_deps
from .tz import Zone, parse_iso

ROW_H = 30
HEAD_H = 44


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _bar_colors(t: Dict[str, Any], is_parent: bool):
    c = str(t.get("color") or "")
    if c:
        return f"hsl({c},100%,50%)", f"hsl({c},100%,35%)"
    if is_parent:
        return "hsl(208,7%,46%)", "hsl(210,9%,31%)"
    return "hsl(211,100%,50%)", "hsl(211,100%,35%)"


def render(doc: Dict[str, Any], title: str = "Plan", today: Optional[str] = None,
           mode: str = "day", for_image: bool = False, timeline_width: int = 1100) -> str:
    """mode: 'day' (fixed day columns, wide for long plans), 'fit' (whole timeline in ~timeline_width px),
    'table' (task table only). for_image removes scrolling so a full-page screenshot shows everything."""
    if mode not in ("day", "fit", "table"):
        raise ValueError("mode must be day, fit or table")
    adv = doc.get("advanced") or {}
    zone = Zone(adv.get("timezone") or "UTC")
    hol = [(zone.to_local(parse_iso(h["from"])).date(), zone.to_local(parse_iso(h["to"])).date())
           for h in adv.get("holidays", []) or []]
    cal = WorkCalendar(adv.get("workWeek") or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                       adv.get("workTime") or [{"from": 8, "to": 12}, {"from": 13, "to": 17}], hol)
    rows = []
    for t, depth, parent in gantt_io.flatten(doc):
        s = zone.to_local(parse_iso(t["StartDate"])) if t.get("StartDate") else None
        e = zone.to_local(parse_iso(t["EndDate"])) if t.get("EndDate") else None
        rows.append({"t": t, "depth": depth, "start": s, "end": e, "parent": bool(t.get("subtasks")),
                     "ms": t.get("Duration") == 0 and not t.get("subtasks")})
    if not rows:
        return "<p>Empty plan</p>"
    starts = [r["start"] for r in rows if r["start"]]
    ends = [r["end"] for r in rows if r["end"]]
    d0 = (min(starts).date() - timedelta(days=2))
    d1 = (max(ends).date() + timedelta(days=3))
    today_d = date.fromisoformat(today) if today else date.today()
    if d0 <= today_d <= d1 + timedelta(days=14):
        d1 = max(d1, today_d + timedelta(days=1))
    ndays = (d1 - d0).days + 1
    if mode == "fit":
        day_w = max(2.0, min(28.0, timeline_width / ndays))
    else:
        day_w = 28 if ndays <= 70 else 18 if ndays <= 200 else 11 if ndays <= 420 else 6
    total_w = ndays * day_w
    hours_per_day = 24.0

    def x_of(dt: datetime) -> float:
        return ((dt.date() - d0).days + (dt.hour + dt.minute / 60) / hours_per_day) * day_w

    # non-working shading as one reusable gradient
    stops = []
    for i in range(ndays):
        d = d0 + timedelta(days=i)
        if not cal.is_work_day(d):
            col = "#fde8e8" if d in cal.holiday_days else "#f1f3f5"
            stops.append(f"transparent {i * day_w}px,{col} {i * day_w}px,{col} {(i + 1) * day_w}px,transparent {(i + 1) * day_w}px")
    shade = "linear-gradient(to right," + ",".join(stops) + ")" if stops else "none"

    # header: months + days
    months = []
    i = 0
    while i < ndays:
        d = d0 + timedelta(days=i)
        nxt = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
        span = min((nxt - d).days, ndays - i)
        months.append((d.strftime("%b %Y"), span))
        i += span
    month_cells = "".join(f'<div class="m" style="width:{span * day_w}px">{_esc(m) if span * day_w > 60 else ""}</div>' for m, span in months)
    day_cells = []
    for i in range(ndays):
        d = d0 + timedelta(days=i)
        cls = "d" + (" nw" if not cal.is_work_day(d) else "")
        label = str(d.day) if day_w >= 16 else (str(d.day) if (day_w >= 9 and d.day in (1, 8, 15, 22)) else "")
        day_cells.append(f'<div class="{cls}" style="width:{day_w}px" title="{d.isoformat()} {d.strftime("%A")}">{label}</div>')

    # rows
    grid_rows, tl_rows = [], []
    pos: Dict[int, Dict[str, float]] = {}
    for idx, r in enumerate(rows):
        t = r["t"]
        name = _esc(t.get("TaskName", ""))
        indent = 14 * r["depth"]
        dur = t.get("Duration")
        unit = t.get("DurationUnit", "day")
        dur_txt = "" if dur is None else f"{dur:g} {unit}{'' if dur == 1 else 's'}"
        res = ", ".join((a.get("resourceName", a.get("resourceId", "")) + ("" if a.get("unit", 100) == 100 else f"[{a.get('unit'):g}%]"))
                        for a in (t.get("resources") or []))
        cls = "parent" if r["parent"] else ("ms" if r["ms"] else "leaf")
        grid_rows.append(
            f'<tr class="{cls}"><td class="id">{_esc(t.get("TaskID"))}</td>'
            f'<td class="nm" dir="auto"><span style="padding-inline-start:{indent}px">{"◆ " if r["ms"] else ""}{name}</span></td>'
            f'<td>{r["start"]:%Y-%m-%d}</td><td>{r["end"]:%Y-%m-%d}</td><td>{dur_txt}</td>'
            f'<td class="num">{float(t.get("Progress", 0)):g}</td><td>{_esc(t.get("Predecessor") or "")}</td><td dir="auto">{_esc(res)}</td></tr>')
        x1, x2 = x_of(r["start"]), x_of(r["end"])
        y = HEAD_H + idx * ROW_H
        pos[t.get("TaskID")] = {"x1": x1, "x2": x2, "y": y + ROW_H / 2, "ms": r["ms"]}
        bg, dark = _bar_colors(t, r["parent"])
        prog = float(t.get("Progress", 0))
        tip = _esc(f"{t.get('TaskName')}\n{r['start']:%Y-%m-%d %H:%M} → {r['end']:%Y-%m-%d %H:%M}\n{dur_txt}  {prog:g}%  {res}\ncolour: {COLOR_LABEL.get(str(t.get('color') or ''), t.get('color'))}")
        if r["ms"]:
            bar = f'<div class="msd" style="left:{x1 - 7:.1f}px;background:{dark}" title="{tip}"></div>'
        elif r["parent"]:
            w = max(x2 - x1, 4)
            bar = (f'<div class="pbar" style="left:{x1:.1f}px;width:{w:.1f}px;background:{bg};border-color:{dark}" title="{tip}">'
                   f'<div class="fill" style="width:{prog:.1f}%;background:{dark}"></div></div>')
        else:
            w = max(x2 - x1, 4)
            label = f"{prog:g}%" if w > 34 else ""
            bar = (f'<div class="bar" style="left:{x1:.1f}px;width:{w:.1f}px;background:{bg};border-color:{dark}" title="{tip}">'
                   f'<div class="fill" style="width:{prog:.1f}%;background:{dark}"></div><span>{label}</span></div>')
        tl_rows.append(f'<div class="row">{bar}</div>')

    # connectors
    paths = []
    for r in rows:
        t = r["t"]
        if r["parent"] or not t.get("Predecessor"):
            continue
        to = pos.get(t.get("TaskID"))
        for d in parse_deps(t["Predecessor"]):
            fr = pos.get(d.pred)
            if not fr or not to:
                continue
            sx = fr["x2"] if d.type in ("FS", "FF") else fr["x1"]
            ex = to["x1"] if d.type in ("FS", "SS") else to["x2"]
            sy, ey = fr["y"], to["y"]
            if d.type in ("FS", "SS"):
                ex_arrow = ex - 1
                mid = max(sx + 8, ex - 8) if d.type == "FS" else min(sx, ex) - 8
                pth = f"M{sx:.1f},{sy:.1f} H{mid:.1f} V{ey:.1f} H{ex_arrow:.1f}"
                head = f"M{ex:.1f},{ey:.1f} l-6,-4 v8 z"
            else:
                mid = max(sx, ex) + 8
                pth = f"M{sx:.1f},{sy:.1f} H{mid:.1f} V{ey:.1f} H{ex + 1:.1f}"
                head = f"M{ex:.1f},{ey:.1f} l6,-4 v8 z"
            paths.append(f'<path d="{pth}" class="ln"/><path d="{head}" class="ah"/>')
    today_line = ""
    if d0 <= today_d <= d1:
        tx = (today_d - d0).days * day_w + day_w / 2
        today_line = f'<div class="today" style="left:{tx:.1f}px" title="today {today_d.isoformat()}"></div>'
    svg_h = HEAD_H + len(rows) * ROW_H

    ww = ", ".join(d[:3] for d in adv.get("workWeek", []))
    wt = ", ".join(f"{r['from']:g}-{r['to']:g}" for r in adv.get("workTime", []))
    info = f"{zone.name} · work week {ww} · hours {wt} · {len(hol)} holiday range(s) · generated for onlinegantt.com"
    css = f"""
    body{{font:13px/1.35 -apple-system,Segoe UI,Roboto,Helvetica,Arial,'Noto Sans Arabic',sans-serif;color:#222;margin:0;background:#fff}}
    h1{{font-size:18px;margin:14px 16px 2px}} .info{{margin:0 16px 10px;color:#666;font-size:12px}}
    .wrap{{display:flex;border-top:1px solid #dee2e6;border-bottom:1px solid #dee2e6;overflow:auto;max-height:calc(100vh - 80px)}}
    table.grid{{border-collapse:collapse;flex:none;font-size:12px;position:sticky;left:0;background:#fff;z-index:3;box-shadow:2px 0 4px rgba(0,0,0,.06)}}
    table.grid th,table.grid td{{border:1px solid #e9ecef;padding:0 6px;height:{ROW_H - 1}px;white-space:nowrap;text-align:left}}
    table.grid th{{background:#f8f9fa;height:{HEAD_H - 1}px;position:sticky;top:0;z-index:4}}
    td.id,td.num{{text-align:right;color:#555}} td.nm{{min-width:220px;max-width:380px;overflow:hidden;text-overflow:ellipsis}}
    tr.parent td{{font-weight:600;background:#fafbfc}} tr.ms td.nm{{color:#333}}
    .tl{{position:relative;flex:none;width:{total_w}px}}
    .hdr{{position:sticky;top:0;z-index:2;background:#f8f9fa;border-bottom:1px solid #dee2e6;height:{HEAD_H}px;box-sizing:border-box}}
    .hdr .mrow,.hdr .drow{{display:flex;height:{HEAD_H // 2}px}} .m{{border-right:1px solid #dee2e6;font-size:11px;font-weight:600;padding-left:4px;overflow:hidden;white-space:nowrap;box-sizing:border-box}}
    .d{{border-right:1px solid #eceff1;font-size:10px;text-align:center;color:#555;box-sizing:border-box;overflow:hidden}} .d.nw{{background:#f1f3f5}}
    .row{{position:relative;height:{ROW_H}px;border-bottom:1px solid #f1f3f5;box-sizing:border-box;background-image:{shade}}}
    .bar,.pbar{{position:absolute;top:7px;height:16px;border:1px solid;border-radius:3px;box-sizing:border-box;overflow:hidden}}
    .pbar{{top:10px;height:9px;border-radius:2px}} .fill{{position:absolute;left:0;top:0;bottom:0}}
    .bar span{{position:absolute;left:0;right:0;top:0;text-align:center;font-size:10px;color:#fff;line-height:14px;text-shadow:0 0 2px rgba(0,0,0,.6)}}
    .msd{{position:absolute;top:8px;width:14px;height:14px;transform:rotate(45deg);border-radius:2px}}
    svg.cn{{position:absolute;left:0;top:0;pointer-events:none;z-index:1}} .ln{{fill:none;stroke:#1e88e5;stroke-width:1.3}} .ah{{fill:#1e88e5}}
    .today{{position:absolute;top:{HEAD_H}px;bottom:0;width:0;border-left:2px solid #e53935;z-index:1}}
    .legend{{margin:8px 16px;color:#666;font-size:11px}} .legend i{{display:inline-block;width:12px;height:10px;vertical-align:middle;margin:0 4px 0 10px;border-radius:2px}}
    @media print{{.wrap{{max-height:none;overflow:visible}}}}
    {"body{display:inline-block;padding:0 12px 6px 0} .wrap{max-height:none;overflow:visible;display:inline-flex} table.grid{position:static;box-shadow:none} .hdr,table.grid th{position:static} td.nm{max-width:640px} h1,.info,.legend{white-space:nowrap}" if for_image else ""}
    """
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{_esc(title)}</title><style>{css}</style></head><body>"
        f"<h1 dir='auto'>{_esc(title)}</h1><p class='info'>{_esc(info)} · span {min(starts):%Y-%m-%d} → {max(ends):%Y-%m-%d}</p>"
        f"<div class='wrap'><table class='grid'><thead><tr><th>ID</th><th>Task</th><th>Start</th><th>End</th><th>Duration</th><th>%</th><th>Deps</th><th>Resources</th></tr></thead>"
        f"<tbody>{''.join(grid_rows)}</tbody></table>"
        + ("" if mode == "table" else
           f"<div class='tl'><div class='hdr'><div class='mrow'>{month_cells}</div><div class='drow'>{''.join(day_cells)}</div></div>"
           f"{''.join(tl_rows)}{today_line}<svg class='cn' width='{total_w:.0f}' height='{svg_h}'>{''.join(paths)}</svg></div>")
        + "</div>"
        f"<p class='legend'>Legend: <i style='background:hsl(211,100%,50%)'></i>task (default) <i style='background:hsl(208,7%,46%)'></i>summary "
        f"<i style='background:#f1f3f5;border:1px solid #ddd'></i>non-working day <i style='background:#fde8e8;border:1px solid #f5c2c2'></i>holiday "
        f"<i style='border-left:2px solid #e53935;width:0'></i> today · darker fill = progress · ◆ milestone</p></body></html>"
    )
