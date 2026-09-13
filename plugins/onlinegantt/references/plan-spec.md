# Plan spec – the JSON you write for `scripts/gantt.py build`

The spec is a compact, human-readable description of a plan: local dates, durations like
"5 days", dependency strings, resource names. `build` schedules it with the same rules as the
site's engine and writes the `.gantt` (plus an HTML preview and a summary).
`decompile` turns an existing `.gantt` back into this shape for editing.

## Shape

```json
{
  "name": "Website Relaunch – إعادة إطلاق الموقع",
  "fileStem": "Website Relaunch",            // optional: file name base (default: name, cleaned)
  "version": 1,                              // optional: used in "<fileStem> vN YYYY-MM-DD.gantt"
  "start": "2026-10-04",                     // project start; tasks without start/deps begin here
  "milestoneTime": "end",                    // "end" (17:00, site style) | "start" (08:00) for dated milestones
  "calendar": {
    "timezone": "Asia/Riyadh",               // IANA name written into the file
    "utcOffset": "+03:00",                   // optional; required only when the machine has no tz database (Windows)
    "workWeek": ["Sunday","Monday","Tuesday","Wednesday","Thursday"],
    "workTime": [{"from": 8, "to": 12}, {"from": 13, "to": 17}],   // or ["08:00-12:00","13:00-17:00"]; max 2 ranges
    "holidays": [{"from": "2026-09-23", "to": "2026-09-23", "name": "National Day"}, "2026-11-01"],
    "workOn": ["2026-12-04", "2026-12-05"]   // optional: off-days that ARE worked (a weekend move). The file gets a
                                            // 7-day week with every other off-day blocked; recomputed on each build
  },
  "settings": {                              // all optional – site defaults otherwise
    "dateFormat": "yyyy-MM-dd", "timeFormat": "HH:mm", "firstDayOfWeek": "Sunday",
    "zoomLevel": 0, "dependencyConflict": "Add Offset to Dependency",
    "columns": ["Task ID", "Task Name", "Start Date", "End Date"],   // visible (left of splitter), fixed order
    "columnWidths": {"Task Name": 420}
  },
  "resources": ["Anas", "Sara"],             // optional; names used by tasks are added automatically
  "tasks": [
    {"id": 1, "name": "Discovery – الاستكشاف", "color": "green", "children": [
      {"id": 2, "name": "Interviews", "start": "2026-10-04", "duration": "4 days",
       "resources": ["Anas"], "progress": 100, "notes": "Six stakeholders.\n\nOutput: findings deck."},
      {"id": 3, "name": "Content audit", "duration": "1 week", "deps": "2SS+1 day",
       "resources": [{"name": "Sara", "unit": 50}]},
      {"id": 4, "name": "Discovery complete", "milestone": true, "deps": "2FS,3FS"}
    ]}
  ]
}
```

## Task fields

| field | accepted values | notes |
|---|---|---|
| `id` | positive int | optional; missing ids get max+1 in document order. Keep ids stable when editing – links and the site's own references depend on them |
| `name` | string | bilingual names are fine ("English – العربية") |
| `start` | `YYYY-MM-DD` or `YYYY-MM-DD HH:MM` (local) | snapped forward to working time. Omit on tasks that have `deps` – their date is derived |
| `end` | same | alternative to `duration` (duration is computed), or with `duration` and no `start` (start is computed backwards) |
| `duration` | `5`, `"5 days"`, `"4 hours"`, `"30 minutes"`, `"2 weeks"` (=10 working days), `"0.5 day"` | number alone = days. Missing → 1 day with a warning |
| `deps` | `"2FS"`, `"2FS+2 days"`, `"3SS,4FF-4 hours"`, `2`, `[2, "3SS"]`, `[{"id": 2, "type": "FS", "lag": "2 days"}]` | leaf-to-leaf only; type defaults to FS |
| `progress` | 0–100 | ignored on parents (computed) |
| `resources` | `["Anas"]`, `"Anas, Sara"`, `[{"name": "Sara", "unit": 50}]` | unit % defaults to 100 |
| `color` | `""`, palette hue `"121"`, or a name: default, orange, yellow, lime, green, teal, cyan, blue, indigo, purple, magenta, pink/red (Arabic names accepted) | other hues snap to the nearest palette value |
| `notes` | plain text or HTML | plain text is wrapped in `<p>` paragraphs |
| `milestone` | `true` | duration 0; `start` optional (else placed by deps); with a date-only start it sits at end of day (`milestoneTime`) |
| `children` | array of tasks | makes this a parent: no `start`/`duration`/`deps`/`progress` (all computed) |

Accepted aliases: `TaskName`, `StartDate`, `finish`, `predecessors`, `dependencies`, `owner`, `assigned`, `subtasks`, `description`.

## What `build` does

1. Validates: unique ids, links to existing leaf tasks, no cycles, ≤2 work ranges, valid settings.
2. Schedules in dependency order with the site's calendar arithmetic; parents roll up.
3. **Stops with exit code 3** when an explicit `start` disagrees with the task's links (the site would move the
   task). Nothing is written. Ask the user, then re-run with
   `--on-conflict deps` (link wins) | `lag` (keep the date by adjusting the governing link's lag) |
   `dates` (keep the date, drop the disagreeing links).
4. Sets milestones to 100 % when everything they wait for is complete (`note:` line) and lists progress on
   tasks that have not started yet (`review:` lines – ask the user, nothing is changed).
5. Writes `<fileStem> v<version> <today>.gantt` in `--out-dir` (or `-o path`), the HTML preview next to it,
   a copy of the spec as `<same stem>.spec.json` (`--no-spec` to skip),
   the PNG variants chosen with `--png fit,day,table` (default `fit`; `--no-png` to skip; `--png-scale 2`,
   `--png-width 1600`), optionally `--expected rows.json` for `verify`, and prints the `inspect` summary
   (span, table, critical path, status, workload / over-allocation).
   PNGs need Playwright + Chromium; when missing the build still succeeds and prints
   `png: skipped - … Install with: …` – ask the user before running that command.

Exit codes: 0 ok · 2 spec/validation error (message on stderr) · 3 conflicts need a decision.
`preview --png` alone: 0 ok · 2 render failure · 4 renderer not installed.

## Editing an existing plan

```
python3 scripts/gantt.py decompile "Plan v1 2026-09-13.gantt" -o plan.json --name "Plan"
# edit plan.json (add/remove tasks, change durations/deps/resources/progress; keep ids)
python3 scripts/gantt.py build plan.json --out-dir <folder> --version 2
```

`decompile` omits `start` on linked tasks so that changing an upstream duration simply reflows
downstream dates instead of raising a conflict for every one of them (`--keep-dates` keeps them).
