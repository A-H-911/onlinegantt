"""CSV in the exact format of the site's "Export to Excel File" / "Import from Excel File"
(and its REST API), plus a stdlib-only reader for CSV / TSV / XLSX task lists that
produces a plan spec.

Site CSV header (CRLF, comma):
  Outline Level,ID,Name,Start,Finish,Duration,% Complete,Predecessors,Resource Names,Color,Notes
- Outline Level 1..100, may only increase by 1 per row (child of the previous row)
- Start / Finish strictly YYYY-MM-DD; Duration "5 day" / "4 hour"; Color = hue or empty
- the import replaces the whole project and auto-creates resources
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from . import gantt_io
from .model import SpecError
from .tz import Zone, parse_iso

HEADER = ["Outline Level", "ID", "Name", "Start", "Finish", "Duration", "% Complete", "Predecessors",
          "Resource Names", "Color", "Notes"]

# header aliases understood by the site's importer (normalised: lower, no spaces/_/-)
_ALIASES = {
    "level": {"outlinelevel", "level", "outline", "indent", "wbslevel"},
    "id": {"id", "taskid", "ids", "taskids", "idnumber", "taskidnumber", "idnum", "id#", "taskid#", "no", "#", "wbs"},
    "name": {"name", "taskname", "task", "title", "names", "tasknames", "tasks", "titles", "name/title", "activity",
             "activities", "activityname", "activitynames", "المهمة", "اسمالمهمة", "النشاط"},
    "start": {"start", "startdate", "startdates", "begin", "from", "البداية", "تاريخالبداية"},
    "finish": {"finish", "finishdate", "finishdates", "end", "enddate", "enddates", "due", "duedate", "to", "النهاية", "تاريخالنهاية"},
    "duration": {"duration", "durations", "days", "المدة"},
    "progress": {"%complete", "percentcomplete", "progress", "%progress", "percentprogress", "progress%", "progresspercent",
                 "complete", "completion", "%done", "done", "الإنجاز", "الانجاز", "نسبةالإنجاز"},
    "deps": {"predecessor", "predecessors", "dependency", "dependencies", "deps", "dependson", "after", "المتطلبات", "الاعتمادية"},
    "resources": {"resource", "resources", "resourcename", "resourcenames", "assigned", "assignedto", "owner", "owners",
                  "who", "responsible", "team", "المسؤول", "الموارد"},
    "color": {"color", "colour", "colors", "colours", "taskcolor", "taskcolour", "taskcolors", "taskcolours", "اللون"},
    "notes": {"note", "notes", "comment", "comments", "info", "information", "description", "details", "ملاحظات", "الوصف"},
    "milestone": {"milestone", "ismilestone", "type"},
    "parent": {"parent", "parentid", "phase", "group", "section", "المرحلة"},
}


def _norm(h: str) -> str:
    return re.sub(r"[\s_\-\"']", "", str(h)).lower()


def export_csv(doc: Dict[str, Any]) -> str:
    adv = doc.get("advanced") or {}
    zone = Zone(adv.get("timezone") or "UTC")
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(HEADER)
    for t, depth, parent in gantt_io.flatten(doc):
        s = zone.to_local(parse_iso(t["StartDate"])).strftime("%Y-%m-%d") if t.get("StartDate") else ""
        e = zone.to_local(parse_iso(t["EndDate"])).strftime("%Y-%m-%d") if t.get("EndDate") else ""
        d = t.get("Duration")
        dur = f"{d:g} {t.get('DurationUnit', 'day')}" if d is not None else ""
        res = ",".join(str(r.get("resourceName", r.get("resourceId", ""))) for r in t.get("resources", []) or [])
        w.writerow([depth + 1, t.get("TaskID"), t.get("TaskName", ""), s, e, dur, t.get("Progress", 0),
                    t.get("Predecessor") or "", res, t.get("color", ""), t.get("info") or ""])
    return out.getvalue()


# ------------------------------------------------------------------ reading
def _read_xlsx(path: str) -> List[List[str]]:
    with zipfile.ZipFile(path) as z:
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        shared: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
        # first worksheet
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = wb.find("m:sheets/m:sheet", ns).attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = next(r.attrib["Target"] for r in rels if r.attrib.get("Id") == rid)
        sheet_path = "xl/" + target.lstrip("/").replace("xl/", "", 1) if not target.startswith("/") else target.lstrip("/")
        root = ET.fromstring(z.read(sheet_path))
        rows: List[List[str]] = []
        for row in root.iter("{%s}row" % ns["m"]):
            cells: Dict[int, str] = {}
            for c in row.findall("m:c", ns):
                ref = c.attrib.get("r", "A1")
                col = 0
                for ch in re.match(r"[A-Z]+", ref).group(0):
                    col = col * 26 + (ord(ch) - 64)
                v = c.find("m:v", ns)
                is_ = c.find("m:is", ns)
                typ = c.attrib.get("t")
                if typ == "s" and v is not None:
                    val = shared[int(v.text)]
                elif typ == "inlineStr" and is_ is not None:
                    val = "".join(t.text or "" for t in is_.iter("{%s}t" % ns["m"]))
                else:
                    val = v.text if v is not None else ""
                    # Excel serial dates -> ISO when the cell looks like a date serial
                    if val and re.fullmatch(r"\d{4,5}(\.0+)?", val) and c.attrib.get("s"):
                        pass  # keep serial; converted below if the column is a date column
                cells[col - 1] = val or ""
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
        return rows


def _excel_serial_to_iso(v: str) -> str:
    from datetime import date, timedelta
    try:
        n = float(v)
    except ValueError:
        return v
    if 20000 < n < 80000:
        return (date(1899, 12, 30) + timedelta(days=int(n))).isoformat()
    return v


def _read_table(path: str) -> List[List[str]]:
    if path.lower().endswith(".xlsx"):
        return _read_xlsx(path)
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        text = f.read()
    first = text.split("\n", 1)[0]
    delim = "\t" if path.lower().endswith(".tsv") or first.count("\t") > first.count(",") else (";" if first.count(";") > first.count(",") else ",")
    return [row for row in csv.reader(io.StringIO(text), delimiter=delim)]


def _ambiguous(v: str) -> bool:
    """True for d/m/y-style dates where both first numbers are <= 12 (05/10/2026 could be 5 Oct or 10 May)."""
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", (v or "").strip())
    return bool(m) and int(m.group(1)) <= 12 and int(m.group(2)) <= 12 and m.group(1) != m.group(2)


def _norm_date(v: str, month_first: bool = False) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    v = _excel_serial_to_iso(v)
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", v)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", v)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if a > 12 and b <= 12:      # unambiguous day-first
            return f"{y}-{b:02d}-{a:02d}"
        if b > 12 and a <= 12:      # unambiguous month-first
            return f"{y}-{a:02d}-{b:02d}"
        return f"{y}-{a:02d}-{b:02d}" if month_first else f"{y}-{b:02d}-{a:02d}"
    return v


def import_table(path: str, name: str = "Plan", month_first: bool = False, renumber: bool = True) -> Dict[str, Any]:
    """month_first: how to read ambiguous dates like 05/10/2026 (default day-first). The spec lists every
    ambiguous value under _ambiguous_dates so the caller can ask the user.
    renumber: give tasks tidy top-down ids (phase 1, its tasks 2..) and remap the row-number links;
    the old->new mapping is returned under _id_map."""
    rows = _read_table(path)
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        raise SpecError("empty table")
    header = [_norm(h) for h in rows[0]]
    col: Dict[str, int] = {}
    for key, aliases in _ALIASES.items():
        for i, h in enumerate(header):
            if h in aliases and key not in col:
                col[key] = i
    if "name" not in col:
        raise SpecError(f"no task-name column found in header {rows[0]} (need Name / Task / Title / Activity)")

    def get(r: List[str], key: str) -> str:
        i = col.get(key)
        return str(r[i]).strip() if i is not None and i < len(r) else ""

    tasks: List[Dict[str, Any]] = []
    stack: List[Dict[str, Any]] = []      # by outline level
    by_parent_name: Dict[str, Dict[str, Any]] = {}
    synthetic_parents: List[Dict[str, Any]] = []
    warnings: List[str] = []
    ambiguous: List[str] = []
    row_no = 0
    for r in rows[1:]:
        nm = get(r, "name")
        if not nm:
            continue
        row_no += 1
        for key in ("start", "finish"):
            if _ambiguous(get(r, key)) and get(r, key) not in ambiguous:
                ambiguous.append(get(r, key))
        t: Dict[str, Any] = {"name": nm}
        if get(r, "id"):
            try:
                t["id"] = int(float(get(r, "id")))
            except ValueError:
                warnings.append(f"row {nm!r}: id {get(r, 'id')!r} is not an integer; using the row number {row_no}")
                t["id"] = row_no
        else:
            t["id"] = row_no  # 'depends on 3' in a spreadsheet almost always means row 3
        if get(r, "start"):
            t["start"] = _norm_date(get(r, "start"), month_first)
        if get(r, "finish"):
            t["end"] = _norm_date(get(r, "finish"), month_first)
        d = get(r, "duration")
        if d:
            t["duration"] = d if re.search(r"[A-Za-z؀-ۿ]", d) else (f"{d} day" if d.strip() == "1" else f"{d} days")
        if get(r, "progress"):
            try:
                t["progress"] = max(0.0, min(100.0, float(get(r, "progress").replace("%", ""))))
            except ValueError:
                pass
        if get(r, "deps"):
            t["deps"] = get(r, "deps")
        if get(r, "resources"):
            t["resources"] = [x.strip() for x in re.split(r"[,;/&]|\band\b|\bو\b", get(r, "resources")) if x.strip()]
        if get(r, "color"):
            t["color"] = get(r, "color")
        if get(r, "notes"):
            t["notes"] = get(r, "notes")
        ms = get(r, "milestone").lower()
        if ms in ("yes", "y", "true", "1", "milestone", "ms", "نعم") or (d and d.strip() in ("0", "0 day", "0 days")):
            t["milestone"] = True
            t.pop("duration", None)
        level = 1
        if "level" in col and get(r, "level"):
            try:
                level = int(float(get(r, "level")))
            except ValueError:
                level = 1
        parent_name = get(r, "parent")
        if "level" in col:
            if level < 1 or level > len(stack) + 1:
                raise SpecError(f"row {nm!r}: outline level {level} jumps more than one step (site rule)")
            stack = stack[:level - 1]
            (stack[-1].setdefault("children", []) if stack else tasks).append(t)
            stack.append(t)
        elif parent_name:
            p = by_parent_name.get(parent_name)
            if p is None:
                p = {"name": parent_name, "children": []}
                by_parent_name[parent_name] = p
                synthetic_parents.append(p)
                tasks.append(p)
            p.setdefault("children", []).append(t)
        else:
            tasks.append(t)
        by_parent_name.setdefault(nm, t)
    next_id = max([t.get("id", 0) for t in _walk(tasks)] + [0]) + 1
    synthetic_ids = set()
    for p in synthetic_parents:  # phases created from a Parent/Phase column get ids after all rows
        p["id"] = next_id
        synthetic_ids.add(next_id)
        next_id += 1
    id_map: Dict[int, int] = {}
    if renumber:
        # tidy top-down ids (phase 1, its tasks 2, 3 ..) and remap every dependency reference
        counter = [1]
        def _renumber(ts):
            for t in ts:
                id_map[t["id"]] = counter[0]
                t["id"] = counter[0]
                counter[0] += 1
                _renumber(t.get("children", []))
        _renumber(tasks)
        def _remap(dep_text: str) -> str:
            def rep(m):
                old = int(m.group(1))
                return str(id_map.get(old, old)) + m.group(2)
            return ",".join(re.sub(r"^\s*(\d+)(.*)$", rep, part) for part in str(dep_text).split(","))
        for t in _walk(tasks):
            if t.get("deps"):
                t["deps"] = _remap(t["deps"])
    spec: Dict[str, Any] = {
        "name": name,
        "start": None,
        "calendar": {"timezone": "Asia/Riyadh", "workWeek": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
                     "workTime": [{"from": 8, "to": 12}, {"from": 13, "to": 17}], "holidays": []},
        "settings": {"columns": ["Task ID", "Task Name"]},
        "tasks": tasks,
        "_import_warnings": warnings,
        "_import_note": "calendar/settings are placeholders - confirm them with the user before building",
        "_ambiguous_dates": ambiguous,
        "_ambiguous_dates_note": ("these values could be day-first or month-first; read as " + ("month-first" if month_first else "day-first") + " - ask the user, re-run with --month-first if needed") if ambiguous else "",
    }
    id_map_out = {str(k): v for k, v in id_map.items() if k != v and k not in synthetic_ids}
    if id_map_out:
        spec["_id_map"] = id_map_out
        spec["_id_map_note"] = "spreadsheet row/ID -> task id after top-down renumbering (links already remapped)"
    starts = [t.get("start") for t in _walk(tasks) if t.get("start")]
    if starts:
        spec["start"] = min(starts)
    return spec


def _walk(tasks):
    for t in tasks:
        yield t
        yield from _walk(t.get("children", []))
