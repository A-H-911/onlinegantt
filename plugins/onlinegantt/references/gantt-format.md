# The `.gantt` file format (onlinegantt.com free tool)

Verified 2026-09-13 by reading the site's source (`Gantt.vue`, Syncfusion EJ2 Gantt engine)
and by loading test files into the live app. Everything below is what the site actually
does, not what its marketing says.

Contents: 1 Top level · 2 Task object · 3 Dates & working time · 4 Dependencies · 5 Resources ·
6 Colours · 7 Notes · 8 `advanced` (settings) · 9 Engine rules on load · 10 Minimal example · 11 Gotchas

## 1. Top level

A `.gantt` file is UTF-8 JSON (the site writes it compact, `text/plain`):

```json
{"data": [ ...tasks... ], "resources": [ {"resourceId": "Anas", "resourceName": "Anas"} ],
 "projectStartDate": null, "projectEndDate": null, "advanced": { ...settings... }}
```

* `data` and `resources` are **required** – the Open button shows "Invalid file" without them.
* `advanced` is optional; missing keys fall back to defaults (section 8).
* `projectStartDate` / `projectEndDate` are always `null` (the site computes the timeline range).
* The site strips every `,"subtasks":[]` when saving – leaf tasks simply have no `subtasks` key.
* Save As names the download `Online Gantt YYYYMMDD.gantt`; the file has no project-name field,
  so the file name is the only place a plan's name lives.

## 2. Task object

```json
{"TaskID": 2, "TaskName": "Kickoff – انطلاق",
 "StartDate": "2026-10-04T05:00:00.000Z", "EndDate": "2026-10-05T14:00:00.000Z",
 "Duration": 2, "DurationUnit": "day",
 "Predecessor": "",
 "resources": [{"resourceId": "Anas", "resourceName": "Anas", "unit": 100}],
 "Progress": 50, "color": "121", "info": "<p>Kickoff meeting</p>",
 "subtasks": [ ...child tasks, only on parents... ]}
```

| key | type | notes |
|---|---|---|
| `TaskID` | positive integer, unique across the whole tree | referenced by `Predecessor`; the site's "Reset Task IDs" renumbers depth-first |
| `TaskName` | string | any Unicode (Arabic renders fine) |
| `StartDate`, `EndDate` | UTC ISO `YYYY-MM-DDTHH:MM:SS.000Z` | represent *local* working-hour instants (see 3) |
| `Duration` | number ≥ 0 | in `DurationUnit`; `0` = milestone; fractions allowed (0.5 day) |
| `DurationUnit` | `"day"` \| `"hour"` \| `"minute"` | the UI shows "5 days", "4 hours" |
| `Predecessor` | string (leaf) / `null` (parent) | grammar in 4; `""` when none |
| `resources` | array of `{resourceId, resourceName, unit}` | see 5 |
| `Progress` | 0–100 | parent value is recomputed (duration-weighted) |
| `color` | `""` or one of 12 hue strings | see 6 |
| `info` | HTML string | notes; empty is `"<p><br></p>"` |
| `subtasks` | array | present only on parents |

Parent (summary) rows: `StartDate`, `EndDate`, `Duration`, `Progress` are **overwritten** from the
children on load; `Predecessor` must be `null`; `resources` are usually `[]`.
New-task template used by the site: `Duration 1, Progress 0, color "", info "<p><br></p>", DurationUnit "day"`.

## 3. Dates and working time

* Work time comes from `advanced.workTime` (default 08:00–12:00 and 13:00–17:00 = **8 working hours per day**).
* A day-based task starts at the first work range start and ends at the last range end:
  Riyadh (UTC+3) `2026-10-04 08:00` → `"2026-10-04T05:00:00.000Z"`, `17:00` → `"...T14:00:00.000Z"`.
* Durations count working time only: weekends (days not in `workWeek`), holidays and the lunch gap are skipped.
  1 day == `hours_per_day` working hours, so a task starting at 13:00 with duration 1 day ends 12:00 next working day.
* Milestones: `Duration 0`, `StartDate == EndDate`; the site's own example puts them at end of day (17:00).
* `advanced.timezone` (IANA) + `advanced.timezoneOffset` (JS `getTimezoneOffset()`, e.g. `-180` for Riyadh)
  record the zone the dates were made in. If the file is opened in a browser in another zone, the site
  shifts every date so wall-clock times are preserved – always write the real zone name.
* Holidays: `[{"from": ISO, "to": ISO}]`, inclusive range, values are **local midnight converted to UTC**
  (Riyadh 2026-09-23 → `"2026-09-22T21:00:00.000Z"`); matched by local calendar date.

## 4. Dependencies (`Predecessor`)

Grammar (Syncfusion): comma-separated items `<TaskID><type>[<+|-><n> <unit>]`

* type: `FS` (default when omitted) `SS` `FF` `SF`, case-insensitive
* lag unit: `day(s)` `hour(s)` `minute(s)`; lag counts **working** time (`+2 days` = 16 working hours)
* canonical form the site writes back: `2FS`, `2FS+2 days`, `4SF-1 day`, `3SS+4 hours`
* tolerated input: `"1"`, `"1fs"`, `"1 FS , 4FS"` (normalised on load)

Rules verified on the site:
* links must be **leaf → leaf**: a `Predecessor` on a parent is ignored, and a link *from* a parent is dropped
  (link to the phase's last task instead – that is what the site's own AI helper does);
* **dependencies override stored dates on load**: each linked task is moved to exactly
  `predecessor end (or start) + lag`, earlier *or* later than the stored date. Slack must be an explicit lag;
* multiple predecessors: the latest constraint wins;
* a milestone linked FS sits exactly at the predecessor's end instant (17:00), not at the next morning;
* `dependencyConflict` in settings only governs interactive drags, not loading.

## 5. Resources

* Top-level `resources`: flat list `{resourceId, resourceName}`; the site uses the name as the id.
  No capacity, cost, calendar, role or group exists.
* Task `resources`: `{resourceId, resourceName, unit}`; `unit` is the allocation % (default 100). The task
  dialog can only tick resources – `unit` is file-only. `unit ≠ 100` renders as `Name[50%]` (150 also works).
* Every `resourceId` used by a task **must** exist in the top-level list, otherwise the cell renders blank.
* Resource View (read-only) groups tasks per resource; shared tasks appear under each person;
  tasks without resources go under "Unassigned Task"; unused resources show as empty groups.
* The site's CSV import auto-creates resources from the "Resource Names" column (unit 100).

## 6. Colours (`color`)

The colour picker offers 12 values; bars render as `hsl(<hue>,100%,50%)` with a darker progress fill.

| value | `""` | 31 | 61 | 91 | 121 | 151 | 181 | 211 | 241 | 271 | 301 | 331 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| looks | default (blue task / grey parent) | orange | yellow | lime | green | teal | cyan | blue | indigo | purple | magenta | pink/red |

Any other hue string still renders a bar, but the Color column icon (`img/color/color<hue>.png`) is missing.
The scripts snap unknown hues to the nearest palette value with a warning.

## 7. Notes (`info`)

Rich-text HTML from the dialog's Notes tab (bold, lists, links, colours …). Plain text works too;
the scripts wrap plain text in `<p>…</p>`. Keep notes small – the cloud version rejects projects
whose notes embed images.

## 8. `advanced` (the "Edit Settings" page)

```json
{"columns": [{"name": "Task ID", "width": "70", "show": true}, {"name": "Task Name", "width": "350", "show": true},
             {"name": "Start Date", "width": "130", "show": false}, {"name": "End Date", "width": "130", "show": false},
             {"name": "Duration", "width": "130", "show": false}, {"name": "Progress %", "width": "150", "show": false},
             {"name": "Dependency", "width": "150", "show": false}, {"name": "Resources", "width": "200", "show": false},
             {"name": "Color", "width": "100", "show": false}, {"name": "Notes", "width": "200", "show": false}],
 "zoomLevel": 0, "timezone": "Asia/Riyadh", "timezoneOffset": -180,
 "dependencyConflict": "Add Offset to Dependency", "dateFormat": "yyyy-MM-dd", "timeFormat": "HH:mm",
 "firstDayOfWeek": 0, "workWeek": ["Sunday","Monday","Tuesday","Wednesday","Thursday"],
 "workTime": [{"from": 8, "to": 12}, {"from": 13, "to": 17}], "holidays": []}
```

| key | values | default | meaning |
|---|---|---|---|
| `columns` | exactly these 10 objects, in this order (indexed by position in the code) | ID + Task Name shown | `show:true` columns sit left of the splitter; the rest are appended to the right of the visible ones and hidden behind the chart (drag the splitter to see them). `width` is a string, 50–1000 |
| `zoomLevel` | -9 … 9 | 0 (1 Day) | -9/-8 1–2 h, -6/-5 6 h, -4/-3 12 h, -2..0 1 day, 1..3 1 week, 4 1 month, 5/6 3 months, 7/8 6 months, 9 1 year |
| `dependencyConflict` | `Cancel Move` \| `Remove Dependency` \| `Add Offset to Dependency` | Add Offset | what a drag does when it breaks a link |
| `dateFormat` | `yyyy-MM-dd` `yyyy/MM/dd` `yyyy.MM.dd` `yyyy MMM dd` `dd-MM-yyyy` `dd/MM/yyyy` `dd.MM.yyyy` `dd MMM yyyy` `MM-dd-yyyy` `MM/dd/yyyy` `MM.dd.yyyy` `MMM dd, yyyy` | `yyyy-MM-dd` | grid + timeline header |
| `timeFormat` | `HH:mm` (24 h) \| `h a` (12 h) | `HH:mm` | hour-level zoom labels and the work-time pickers |
| `firstDayOfWeek` | 0 Sunday … 6 Saturday | 0 | timeline week start |
| `workWeek` | English day names | Mon–Fri | working days |
| `workTime` | 1 or 2 `{from,to}` ranges, hours in 0.5 steps | 8–12, 13–17 | working hours; `to` 24 allowed |
| `holidays` | `[{from, to}]` ISO | `[]` | non-working ranges |
| `timezone` / `timezoneOffset` | IANA / minutes | browser's | see section 3 |

## 9. What the engine does on load (why the scripts schedule the way they do)

1. Reads `resources`, then `data`; unknown keys are kept but ignored.
2. Applies the calendar (workWeek, workTime, holidays).
3. Snaps every start outside working time forward (midnight → 08:00, Friday evening → next working day).
4. Computes missing `Duration` from the dates, or missing dates from duration (task with nothing lands on the
   project start).
5. Re-derives the start of every task with a `Predecessor` from its links (section 4).
6. Rolls parents up: start = min(children), end = max(children), duration = working days between,
   progress = Σ(child progress × child duration) / Σ(child duration).
7. Shifts all dates if `advanced.timezone` differs from the browser zone.

The bundled scripts reproduce 3–6 (`scripts/gantt.py build`, `validate --drift`), so a built file opens
without any task moving. `verify` compares the file with rows dumped from the engine.

## 10. Minimal valid file (the site's own default example, Riyadh)

```json
{"data":[{"TaskID":1,"TaskName":"Example","StartDate":"2026-09-07T05:00:00.000Z","EndDate":"2026-09-25T14:00:00.000Z","Duration":15,"Predecessor":null,"resources":[],"Progress":50,"color":"","info":"<p><br></p>","DurationUnit":"day","subtasks":[
 {"TaskID":2,"TaskName":"Example Task 1","StartDate":"2026-09-07T05:00:00.000Z","EndDate":"2026-09-11T14:00:00.000Z","Duration":5,"Predecessor":"","resources":[{"resourceId":"Team Member 1","resourceName":"Team Member 1","unit":100}],"Progress":80,"color":"121","info":"<p><br></p>","DurationUnit":"day"},
 {"TaskID":3,"TaskName":"Example Task 2","StartDate":"2026-09-14T05:00:00.000Z","EndDate":"2026-09-18T14:00:00.000Z","Duration":5,"Predecessor":"2FS","resources":[{"resourceId":"Team Member 2","resourceName":"Team Member 2","unit":100}],"Progress":50,"color":"211","info":"<p><br></p>","DurationUnit":"day"},
 {"TaskID":5,"TaskName":"Example Milestone","StartDate":"2026-09-18T14:00:00.000Z","EndDate":"2026-09-18T14:00:00.000Z","Duration":0,"Predecessor":"3FS","resources":[],"Progress":0,"color":"","info":"<p><br></p>","DurationUnit":"day"}]}],
 "resources":[{"resourceId":"Team Member 1","resourceName":"Team Member 1"},{"resourceId":"Team Member 2","resourceName":"Team Member 2"}],
 "projectStartDate":null,"projectEndDate":null,
 "advanced":{"columns":[{"name":"Task ID","width":"70","show":true},{"name":"Task Name","width":"350","show":true},{"name":"Start Date","width":"130","show":false},{"name":"End Date","width":"130","show":false},{"name":"Duration","width":"130","show":false},{"name":"Progress %","width":"150","show":false},{"name":"Dependency","width":"150","show":false},{"name":"Resources","width":"200","show":false},{"name":"Color","width":"100","show":false},{"name":"Notes","width":"200","show":false}],"zoomLevel":0,"timezone":"Asia/Riyadh","timezoneOffset":-180,"dependencyConflict":"Add Offset to Dependency","dateFormat":"yyyy-MM-dd","timeFormat":"HH:mm","firstDayOfWeek":0,"workWeek":["Monday","Tuesday","Wednesday","Thursday","Friday"],"workTime":[{"from":8,"to":12},{"from":13,"to":17}],"holidays":[]}}
```

## 11. Gotchas collected while testing

* Writing `"StartDate": "2026-10-05"` (no time) breaks: the site requires full ISO with `Z`.
* Writing dates at UTC midnight works in Riyadh (snaps to 08:00) but shifts the day in zones east of UTC+8
  or west of UTC – always write the true local working-hour instant in UTC.
* Progress on a milestone is ignored; progress on a parent is overwritten.
* Resource `unit` other than 100 cannot be edited on the site – only via the file/CSV.
* Column `show:false` does not delete the column; it parks it behind the chart.
* Big notes (pasted Word content with images) bloat the file; the cloud version rejects >~1 MB.
* Firefox/Safari may fail the site's PDF/PNG export; Chrome/Edge work.
