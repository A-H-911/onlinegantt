#!/usr/bin/env python3
"""ogantt - build, inspect, convert and check onlinegantt.com plans (.gantt files).

Standard-library only.  Run `python3 gantt.py <command> -h` for options.

  build      plan-spec JSON  -> .gantt (+ expected-render JSON) with conflict/warning report
  validate   .gantt          -> errors/warnings the site would hit
  decompile  .gantt          -> editable plan-spec JSON (local dates, readable durations)
  inspect    .gantt|spec     -> markdown summary, critical path, status, workload/over-allocation
  preview    .gantt|spec     -> self-contained HTML timeline, or --png fit|day|table images (headless Chromium)
  csv        .gantt -> CSV (site "Export to Excel" format) | CSV/XLSX -> plan spec
  recolor    .gantt|spec     -> apply a colour scheme (phase / resource / status / clear)
  verify     .gantt + engine dump (from the site) -> field-by-field comparison
  name       print the versioned file name for a plan ("<Plan> vN YYYY-MM-DD.gantt")
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ogantt import csvio, gantt_io, inspect as inspect_mod, png as png_mod, preview as preview_mod, recolor as recolor_mod  # noqa: E402
from ogantt.model import SpecError, plan_from_spec  # noqa: E402
from ogantt.schedule import schedule, to_gantt  # noqa: E402
from ogantt.verify import compare  # noqa: E402


def _read_json(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _is_gantt(doc) -> bool:
    return isinstance(doc, dict) and "data" in doc and "resources" in doc and "tasks" not in doc


def _safe_stem(name: str) -> str:
    """File-name base: the English half of a bilingual 'English – Arabic' name, invalid characters stripped."""
    import re
    parts = re.split(r"\s+[–—|-]\s+", name, maxsplit=1)
    if len(parts) == 2:
        latin = [p for p in parts if not re.search(r"[؀-ۿ]", p)]
        if len(latin) == 1:
            name = latin[0]
    bad = '<>:"/\\|?*'
    out = "".join(ch for ch in name if ch not in bad).strip().rstrip(".")
    return out or "Plan"


def versioned_name(stem: str, version: int, day: date | None = None, ext: str = ".gantt") -> str:
    day = day or date.today()
    return f"{_safe_stem(stem)} v{int(version)} {day.isoformat()}{ext}"


def _load_plan(path: str, warnings: list):
    """Accept either a plan spec or a .gantt file and return (plan, spec_dict)."""
    doc = _read_json(path)
    if _is_gantt(doc):
        spec = gantt_io.to_spec(doc, name=os.path.splitext(os.path.basename(path))[0])
    else:
        spec = doc
    return plan_from_spec(spec, warnings), spec


def _write_pngs(doc, stem: str, title: str, modes: str, scale: int, today, width: int) -> list:
    """Render one PNG per mode (fit / day / table). Returns the list of written paths; prints
    the install instructions instead when the renderer is unavailable (never installs anything)."""
    out = []
    wanted = [m.strip() for m in (modes or "").split(",") if m.strip()]
    if not wanted:
        return out
    ok, msg = png_mod.availability()
    if not ok:
        print(f"png: skipped - {msg}")
        print("png: ask the user before installing; the HTML preview is available meanwhile")
        return out
    for m in wanted:
        if m not in ("fit", "day", "table"):
            print(f"png: unknown mode {m!r} (fit | day | table)")
            continue
        html = preview_mod.render(doc, title=title, today=today, mode=m, for_image=True, timeline_width=width - 700)
        path = png_mod.png_name(stem, m)
        refit = (lambda tw, _m=m: preview_mod.render(doc, title=title, today=today, mode=_m, for_image=True, timeline_width=tw)) if m == "fit" else None
        good, res = png_mod.render_png(html, path, scale=scale, width=width, refit=refit)
        if good:
            print(f"wrote {path}")
            out.append(path)
        else:
            print(f"png: failed - {res}")
    return out


# ------------------------------------------------------------------ commands
def cmd_build(a) -> int:
    warnings: list = []
    spec = _read_json(a.spec)
    if _is_gantt(spec):
        print("error: input is already a .gantt file; use `decompile` to get an editable spec first", file=sys.stderr)
        return 2
    try:
        plan = plan_from_spec(spec, warnings)
        res = schedule(plan, on_conflict=a.on_conflict, today=date.fromisoformat(a.today) if a.today else None)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for w in warnings + res.warnings:
        print(f"warning: {w}")
    for n in res.notes:
        print(f"note: {n}")
    for r in res.review:
        print(f"review: {r}")
    if res.errors:
        for e in res.errors:
            print(f"error: {e}", file=sys.stderr)
        return 2
    if res.conflicts and a.on_conflict == "ask":
        print("\nDATE / DEPENDENCY CONFLICTS - the site would move these tasks on load. Nothing was written.")
        print("Ask the user how to resolve, then re-run with --on-conflict deps | lag | dates (or fix the spec):")
        for c in res.conflicts:
            direction = "later" if c["delta_days"] > 0 else "earlier"
            print(f"  - task {c['id']} {c['name']!r}: you asked for {c['explicit']}, but link {c['governing']} "
                  f"puts it at {c['fromDeps']} ({abs(c['delta_days']):g} working days {direction})")
        print("     deps  = dependencies win, the task moves to the linked date")
        print("     lag   = keep the requested date by writing the difference as a lag on the governing link")
        print("     dates = keep the requested date and drop the links that disagree with it")
        return 3
    for m in res.moved:
        print(f"resolved: task {m['id']} {m['name']!r}: {m['resolution']} -> {m['explicit'] if m['resolution'].startswith(('lag','kept')) else m['fromDeps']}")
    doc = to_gantt(plan, res)
    for w in res.warnings[len(res.warnings):]:
        print(f"warning: {w}")
    version = a.version or plan.version or 1
    if a.out:
        out = a.out
    else:
        stem = plan.file_stem or plan.name
        out = os.path.join(a.out_dir or ".", versioned_name(stem, version))
    _write(out, gantt_io.dump_gantt(doc))
    errors, vwarn = gantt_io.validate(doc)
    for w in vwarn:
        print(f"warning: {w}")
    if errors:  # should not happen - defensive
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"wrote {out}")
    if not a.no_preview:
        html_path = os.path.splitext(out)[0] + ".html"
        _write(html_path, preview_mod.render(doc, title=plan.name, today=a.today))
        print(f"wrote {html_path}")
    if not a.no_png:
        _write_pngs(doc, os.path.splitext(out)[0], plan.name, a.png, a.png_scale, a.today, a.png_width)
    if a.expected:
        _write(a.expected, json.dumps(compare.expected_rows(doc), ensure_ascii=False, indent=1))
        print(f"wrote {a.expected}")
    if not a.no_spec:
        spec_path = os.path.splitext(out)[0] + ".spec.json"
        _write(spec_path, json.dumps(spec, ensure_ascii=False, indent=2))
        print(f"wrote {spec_path}")
    print()
    print(inspect_mod.summary(doc, today=a.today, workload=not a.no_workload))
    if res.review:
        print("\n## Needs your decision")
        for r in res.review:
            print(f"- {r}")
    return 0


def cmd_validate(a) -> int:
    try:
        doc = gantt_io.load_gantt(a.file)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    errors, warnings = gantt_io.validate(doc)
    drift = compare.drift(doc)
    for w in warnings:
        print(f"warning: {w}")
    for d in drift:
        print(f"drift: {d}")
    for e in errors:
        print(f"error: {e}")
    if errors:
        print(f"\n{len(errors)} error(s) - the site will reject or mangle this file")
        return 2
    print(f"\nOK - valid .gantt ({len(warnings)} warning(s), {len(drift)} task(s) will move on load)")
    return 0


def cmd_decompile(a) -> int:
    try:
        doc = gantt_io.load_gantt(a.file)
        name = a.name or os.path.splitext(os.path.basename(a.file))[0]
        spec = gantt_io.to_spec(doc, utc_offset=a.utc_offset, name=name, keep_dependent_dates=a.keep_dates)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text = json.dumps(spec, ensure_ascii=False, indent=2)
    if a.out:
        _write(a.out, text)
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0


def _doc_from_any(path: str, on_conflict: str = "deps"):
    doc = _read_json(path)
    if _is_gantt(doc):
        return doc
    warnings: list = []
    plan = plan_from_spec(doc, warnings)
    res = schedule(plan, on_conflict=on_conflict)
    if res.errors:
        raise SpecError("; ".join(res.errors))
    return to_gantt(plan, res)


def cmd_inspect(a) -> int:
    try:
        doc = _doc_from_any(a.file)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(inspect_mod.summary(doc, today=a.today, workload=not a.no_workload, table=not a.no_table))
    return 0


def cmd_preview(a) -> int:
    try:
        doc = _doc_from_any(a.file)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    title = a.title or os.path.splitext(os.path.basename(a.file))[0]
    stem = os.path.splitext(a.out)[0] if a.out else os.path.splitext(a.file)[0]
    if a.png:
        ok, msg = png_mod.availability()
        if not ok:
            print(f"png: {msg}")
            print("Ask the user before installing anything. Exit code 4 = renderer unavailable.")
            return 4
        written = _write_pngs(doc, stem, title, a.png, a.png_scale, a.today, a.png_width)
        return 0 if written else 2
    out = a.out or stem + ".html"
    _write(out, preview_mod.render(doc, title=title, today=a.today, mode=a.mode))
    print(f"wrote {out}")
    return 0


def cmd_csv(a) -> int:
    try:
        if a.file.lower().endswith((".csv", ".xlsx", ".tsv")):
            spec = csvio.import_table(a.file, name=a.name or os.path.splitext(os.path.basename(a.file))[0],
                                      month_first=a.month_first, renumber=not a.keep_ids)
            text = json.dumps(spec, ensure_ascii=False, indent=2)
            out = a.out or os.path.splitext(a.file)[0] + ".plan.json"
            _write(out, text)
            print(f"wrote {out} (plan spec) - review dates/deps, then `build` it")
            if spec.get("_ambiguous_dates"):
                print(f"review: ambiguous dates {spec['_ambiguous_dates']} read as {'month-first' if a.month_first else 'day-first'} "
                      f"- ask the user which reading is right (re-run with --month-first to flip)")
            if spec.get("_id_map"):
                print("note: tasks renumbered top-down; spreadsheet id -> task id: " + ", ".join(f"{k}->{v}" for k, v in spec["_id_map"].items()))
        else:
            doc = _doc_from_any(a.file)
            out = a.out or os.path.splitext(a.file)[0] + ".csv"
            _write(out, csvio.export_csv(doc))
            print(f"wrote {out}")
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


def cmd_recolor(a) -> int:
    try:
        doc = _doc_from_any(a.file)
        changed = recolor_mod.apply(doc, schemes=a.by, today=a.today, status_all=a.status_all)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out = a.out or a.file
    if a.file.lower().endswith(".gantt") or a.out:
        _write(out, gantt_io.dump_gantt(doc))
        print(f"wrote {out} ({changed} task colours set)")
    else:
        print(json.dumps(doc, ensure_ascii=False))
    return 0


def cmd_verify(a) -> int:
    try:
        doc = gantt_io.load_gantt(a.file)
        dump = _read_json(a.engine_dump)
    except (SpecError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    report, ok = compare.report(doc, dump)
    print(report)
    return 0 if ok else 1


def cmd_name(a) -> int:
    print(versioned_name(a.plan_name, a.version, date.fromisoformat(a.date) if a.date else None, a.ext))
    return 0


def _utf8_output() -> None:
    """Print UTF-8 whatever the console code page: the summaries contain arrows, diamonds and Arabic names,
    and a redirected stdout on Windows defaults to cp1252, which cannot encode them."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, AttributeError):  # pragma: no cover - closed or exotic streams
                pass


def main(argv=None) -> int:
    _utf8_output()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="plan spec -> .gantt")
    b.add_argument("spec")
    b.add_argument("-o", "--out", help="output .gantt path (default: '<name> vN YYYY-MM-DD.gantt' in --out-dir)")
    b.add_argument("--out-dir", help="directory for the auto-named file")
    b.add_argument("--version", type=int, help="version number for the auto name (default: spec.version or 1)")
    b.add_argument("--on-conflict", choices=["ask", "deps", "lag", "dates"], default="ask",
                   help="what to do when an explicit start date disagrees with the dependencies")
    b.add_argument("--expected", help="also write the expected engine rows JSON (for `verify`)")
    b.add_argument("--today", help="YYYY-MM-DD used for status/overdue (default: today)")
    b.add_argument("--no-preview", action="store_true")
    b.add_argument("--png", default="fit", help="PNG variants to render, comma list of fit,day,table (default fit)")
    b.add_argument("--no-png", action="store_true", help="skip PNG rendering")
    b.add_argument("--png-scale", type=int, default=2, help="device scale factor (2 = retina/print)")
    b.add_argument("--png-width", type=int, default=1600, help="image width in CSS px for the fit variant")
    b.add_argument("--no-workload", action="store_true")
    b.add_argument("--no-spec", action="store_true", help="do not save a copy of the spec next to the outputs")
    b.set_defaults(fn=cmd_build)

    v = sub.add_parser("validate", help="check a .gantt file")
    v.add_argument("file")
    v.set_defaults(fn=cmd_validate)

    d = sub.add_parser("decompile", help=".gantt -> plan spec")
    d.add_argument("file")
    d.add_argument("-o", "--out")
    d.add_argument("--name", help="plan name to put in the spec")
    d.add_argument("--utc-offset", help="e.g. +03:00 when the file's timezone is unknown to this machine")
    d.add_argument("--keep-dates", action="store_true",
                   help="also write 'start' for tasks that have dependencies (normally omitted: the links define them)")
    d.set_defaults(fn=cmd_decompile)

    i = sub.add_parser("inspect", help="summary / critical path / status / workload")
    i.add_argument("file")
    i.add_argument("--today")
    i.add_argument("--no-workload", action="store_true")
    i.add_argument("--no-table", action="store_true")
    i.set_defaults(fn=cmd_inspect)

    pv = sub.add_parser("preview", help="render HTML timeline")
    pv.add_argument("file")
    pv.add_argument("-o", "--out")
    pv.add_argument("--title")
    pv.add_argument("--today")
    pv.add_argument("--mode", choices=["day", "fit", "table"], default="day", help="HTML layout (default day)")
    pv.add_argument("--png", nargs="?", const="fit", help="render PNG(s) instead of HTML: fit | day | table, comma list")
    pv.add_argument("--png-scale", type=int, default=2)
    pv.add_argument("--png-width", type=int, default=1600)
    pv.set_defaults(fn=cmd_preview)

    c = sub.add_parser("csv", help=".gantt -> CSV, or CSV/XLSX -> plan spec")
    c.add_argument("file")
    c.add_argument("-o", "--out")
    c.add_argument("--name")
    c.add_argument("--month-first", action="store_true", help="read ambiguous dates like 05/10/2026 as month-first (US)")
    c.add_argument("--keep-ids", action="store_true", help="keep spreadsheet row numbers as task ids instead of renumbering top-down")
    c.set_defaults(fn=cmd_csv)

    r = sub.add_parser("recolor", help="apply colour schemes")
    r.add_argument("file")
    r.add_argument("--by", action="append", required=True,
                   help="phase | resource | status | clear ; repeat: later schemes override earlier ones where they apply")
    r.add_argument("--status-all", action="store_true", help="status scheme also colours on-track / not-started tasks")
    r.add_argument("--today")
    r.add_argument("-o", "--out")
    r.set_defaults(fn=cmd_recolor)

    vf = sub.add_parser("verify", help="compare a .gantt with rows dumped from the site's engine")
    vf.add_argument("file")
    vf.add_argument("engine_dump")
    vf.set_defaults(fn=cmd_verify)

    n = sub.add_parser("name", help="versioned file name")
    n.add_argument("plan_name")
    n.add_argument("version", type=int)
    n.add_argument("--date")
    n.add_argument("--ext", default=".gantt")
    n.set_defaults(fn=cmd_name)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
