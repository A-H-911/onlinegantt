# CSV format – "Import from Excel File" / "Export to Excel File" / REST API

The site's "Excel" import and export are really CSV. `scripts/gantt.py csv` writes this exact format
from a `.gantt` and reads it (plus looser spreadsheets and `.xlsx`) into a plan spec.

## Export (what the site writes, CRLF, comma, UTF-8)

```
Outline Level,ID,Name,Start,Finish,Duration,% Complete,Predecessors,Resource Names,Color,Notes
1,1,Discovery,2026-10-04,2026-10-11,6 day,66.67,,,,<p><br></p>
2,2,Stakeholder interviews,2026-10-04,2026-10-07,4 day,100,,Anas,121,<p>Interview 6 stakeholders.</p>
2,3,Content audit,2026-10-05,2026-10-11,5 day,40,2SS+1 day,Sara,,<p><br></p>
2,4,Discovery complete,2026-10-11,2026-10-11,0 day,0,"2FS,3FS",,,<p><br></p>
```

| column | meaning |
|---|---|
| Outline Level | 1 = top level, 2 = child of the nearest level-1 row above, … (max 100) |
| ID | TaskID |
| Name | TaskName |
| Start / Finish | local dates `YYYY-MM-DD` |
| Duration | `<n> day` / `<n> hour` / `<n> minute` (singular, as the site writes it) |
| % Complete | Progress |
| Predecessors | Predecessor string (`2FS,3SS+1 day`) |
| Resource Names | comma-separated names (units are not exported) |
| Color | hue string or empty |
| Notes | the HTML notes |

## Import rules (site importer, verified in code)

* Delimiter: `,` or `;` (detected from the header). Header row required. Only **Name** is mandatory.
* Header aliases (case/space/underscore-insensitive): name/task/title/activity(ies) · id/task id/id#
  · outline level/level · start/start date · finish/finish date/end/end date · duration · % complete/
  percent complete/progress/progress % · predecessor(s)/dependency(ies) · resource(s)/resource name(s)/
  assigned/assigned to · color/colour/task color · note(s)/comment(s)/info/information.
* Outline Level: integers 1–100, may increase by at most 1 per row; missing column → everything level 1.
* ID: unique positive integers; missing column → sequential row numbers.
* Start / Finish: **strictly `YYYY-MM-DD`** (Excel: Format Cells → Date → YYYY-MM-DD). Anything else aborts
  with "Column 'Start' must be a valid date".
* Duration: number + unit (`2 day`, `2 days`, `4 h`, `30 min`); a bare number means days. Missing → 1 day,
  or computed from Start and Finish when both are present. Finish missing → computed from Start + Duration.
  Start missing → today (or Finish − Duration).
* % Complete: clamped to 0–100; blank → 0.
* Predecessors: comma-separated; a task referencing itself is ignored.
* Resource Names: comma-separated; every name is added to the resource list with unit 100.
* Color: a number is bucketed to the nearest palette hue (1–31 → 31, 32–61 → 61 … >301 → 331); blank → default.
* Notes: plain text or HTML.
* The import **replaces** the current plan (it asks to discard unsaved changes) and keeps the current settings
  (calendar, columns) – the CSV carries no settings.

## `gantt.py csv` reader (more forgiving than the site)

Reads `.csv`, `.tsv`, `.xlsx` (first sheet). Extra aliases: `Phase`/`Parent`/`Group` (builds the hierarchy
from a phase name column), `Owner`/`Who`/`Responsible`, `Days`, `Due`, `Depends on`/`After`, `Milestone`
(yes/true/1), Arabic headers (المهمة، البداية، النهاية، المدة، المسؤول، الإنجاز، ملاحظات، المرحلة).
Dates: `YYYY-MM-DD`, `DD/MM/YYYY` (day-first by default, `--month-first` flips it), Excel serials; values that
could be either (05/10/2026) are listed under `_ambiguous_dates` – ask the user. "Depends on" row numbers are
resolved, then every task is renumbered top-down (phase 1, its tasks 2, 3 …) with links remapped; the old → new
mapping is under `_id_map` (`--keep-ids` keeps the row numbers).
The output is a plan spec with placeholder calendar/settings – confirm them with the user before `build`.
