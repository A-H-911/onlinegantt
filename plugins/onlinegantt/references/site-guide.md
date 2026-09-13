# onlinegantt.com – UI guide and browser automation

URL: `https://www.onlinegantt.com/#/gantt` (free tool; no login). The page is a Vue app around the
Syncfusion Gantt component; everything is client-side, nothing is uploaded.

Contents: 1 Layout · 2 File actions (New / Open / Save As) · 3 Import & Export · 4 Editing tasks ·
5 Views, filters, Today · 6 Edit Settings · 7 Edit Resources · 8 Manual step-by-step recipes ·
9 Browser automation (Cowork built-in browser / Claude in Chrome) · 10 Cloud-only features

## 1. Layout

```
[New] [Open (.gantt file)] [Save As (.gantt file)] [Import / Export ▾]        ☐ Today  [All Tasks ▾] [Project View ▾] [≡]
[+ Add] [Edit] [Delete] [Indent] [Outdent] [Expand all] [Collapse all] [Zoom in] [Zoom out] [Zoom to fit] [Search]
| ID | Task Name | (other columns) ‖ timeline ────────────────────────────────────────────────────
```

* Left grid: visible columns per Settings → "Default Column Settings"; the splitter (‖) can be dragged
  to reveal the hidden columns. Column menu (⋮) sorts/filters/hides.
* Right chart: bars (blue = task, grey = summary, coloured = task colour), diamonds = milestones,
  arrows = links, shaded columns = non-working days, red line = Today (when the checkbox is on).
* Keyboard: `Insert` (Mac: Ctrl-I) adds a new task without the dialog.

## 2. File actions

| button | what happens |
|---|---|
| **New** | asks "Discard unsaved changes?" if needed, then empties the plan and resets settings to defaults (Mon–Fri, 8–12/13–17, yyyy-MM-dd, Sunday, zoom 0, ID + Task Name columns) |
| **Open (.gantt file)** | file picker (accepts `.gantt` only); the whole plan + resources + settings are replaced; "Invalid file" if JSON is malformed or `data`/`resources` are missing |
| **Save As (.gantt file)** | downloads `Online Gantt YYYYMMDD.gantt` (browser download folder). The site never saves anywhere else – closing the tab loses unsaved work (it warns) |

## 3. Import / Export menu

| item | details |
|---|---|
| Import from Excel File | accepts **.csv only** (`;` or `,` delimiter auto-detected). Replaces the whole plan. Format: `references/csv-format.md`. Errors explain which column is wrong |
| Export to Excel File | downloads `Online Gantt YYYYMMDD.csv` (same format; Notes as HTML, Color as hue). A popup explains how to open it in Excel for non-English locales (Data → From Text, comma delimiter) |
| Export to PDF File | opens the Export modal (free tool: options locked to defaults – header None, footer "Powered by", columns ID + Task Name, zoom to fit, expand all, 1×). Click **Export** → single-page PDF made from a PNG snapshot. "Exporting large files may take several minutes" |
| Export to Image File | same modal → PNG |

Firefox and Safari can fail the PDF/PNG export; Chrome/Edge work.

## 4. Editing tasks

* **Add** (toolbar) or `Insert`: opens "New Task" dialog. Tabs: **General** (ID, Task Name, Start, End,
  Duration *(excludes non-working days)*, Progress %, Color), **Dependency** (grid: ID, Name, Type FS/SS/FF/SF,
  Offset), **Resources** (tick boxes; "Edit" button explains resources are managed in Edit Resources),
  **Notes** (rich-text editor). OK saves.
* Double-click a row / **Edit** → same dialog. On parents, Start and Progress are disabled
  ("Dates and progress are auto populated from subtasks").
* Cells are editable in place (Task Name, dates, duration, progress, predecessor, resources, colour).
* Right-click menu: Auto fit, Sort, Task Information, Delete Task, **Add Task ▸ Above / Below / Subtask /
  Milestone**, Duplicate Task (copies subtree with new ids and remapped links), Delete Dependency, Convert
  (task ↔ milestone).
* **Indent / Outdent** make the selected row a child of the row above / lift it one level.
* Drag bars to move/resize; drag from a bar's end handle to another bar to create a link. When a drag breaks
  a link, Settings → Dependency Conflict decides (Cancel Move / Remove Dependency / Add Offset).
* Drag the row handle (⋮⋮) to reorder.

## 5. Views, filters, Today

* **Today** checkbox: red marker on today's date and scrolls to it.
* Filter select: **All Tasks** / **Remaining Tasks** (Progress < 100, sorted by end) / **Overdue Tasks**
  (Progress < 100 and end before now). Project View only.
* View select: **Project View** (editable) · **Resource View** (read-only, tasks grouped per resource,
  "Unassigned Task" group) · **Edit Resources** · **Edit Settings** · Share / Revisions (cloud only – the free
  tool shows a "available in our cloud tool" notice).
* Toolbar: Expand/Collapse all, Zoom in/out (hours ↔ years), Zoom to fit, Search (filters the grid).

## 6. Edit Settings (= `advanced` in the file)

Default Column Settings (width 50–1000 + Show/Hide for the 10 columns) · Default Timeline Zoom Level (-9 … 9)
· Reset Task IDs (renumber sequentially, links remapped) · Dependency Conflict · Date Format (12 options)
· Time Format (12/24 h) · First Day of Week · Work Week (7 checkboxes) · Work Time (two From/To rows, 30-min
steps) · Holidays (From/To date pickers; a new empty row appears as you fill one).
Changes apply when you switch back to Project View. They are stored in the `.gantt` on Save As.

## 7. Edit Resources

A plain list of names (one per row, empty row at the bottom to add). Deleting a name removes it from every
task. Names are sorted alphabetically on save. Nothing else (no capacity/cost).

## 8. Manual step-by-step recipes (tell the user these when not automating)

**Open a plan Claude made**: go to `https://www.onlinegantt.com/#/gantt` → **Open (.gantt file)** → pick
`<Plan> vN YYYY-MM-DD.gantt` → the chart appears. Check Edit Settings if the calendar looks wrong.

**Save what you changed on the site**: **Save As (.gantt file)** → the browser downloads
`Online Gantt YYYYMMDD.gantt` → rename it to the next version (`<Plan> vN+1 YYYY-MM-DD.gantt`) and give it to
Claude for further edits.

**Import a spreadsheet directly on the site**: save the sheet as CSV (UTF-8, header row) → Import / Export →
Import from Excel File. Column rules in `csv-format.md`. Prefer letting Claude convert it (`gantt.py csv`) so
calendar/settings/resources are set.

**Export**: Import / Export → Export to Excel File (CSV), Export to PDF File → Export, Export to Image File
→ Export. Downloads land in the browser's download folder.

**Change settings**: Project View ▾ → Edit Settings → change → Project View ▾ → Project View → Save As to persist.

## 9. Browser automation

Use these when a browser tool is available and the user wants Claude to load/verify/export on the site.
Both browsers work with the same JavaScript; only the way to run it differs:

| | Cowork built-in browser | Claude in Chrome |
|---|---|---|
| open the site | `Claude_Browser__preview_start {url}` (first time needs `request_access` on `https://onlinegantt.com`) | `tabs_create_mcp` then `navigate` |
| run JS | `Claude_Browser__javascript_tool {action:"javascript_exec", text}` | `javascript_tool` |
| click / type | `Claude_Browser__computer` / `find` / `form_input` | `computer` / `find` / `form_input` |
| load a `.gantt` | inject the JSON (below) – there is no file-upload control | inject the JSON, **or** `file_upload` on the hidden `input[type=file][accept=".gantt"]` when the file is on the user's machine |
| downloads (Save As, exports) | not reachable from the pane – use the scripts instead | land in the user's Downloads folder |

### 9.1 Load a plan through the site's own Open handler (no file picker needed)

Read the `.gantt` file, then run (paste the file's JSON **as an object literal** into `JSON.stringify(...)` –
never inside a quoted string or a template literal, so that quotes, backticks or `${` in task names and notes
cannot break out of the snippet):

```js
const json = JSON.stringify(<<< the .gantt file's JSON, pasted as is >>>);
const input = document.querySelector('input[type=file][accept=".gantt"]');
const dt = new DataTransfer(); dt.items.add(new File([json], "plan.gantt", {type: "text/plain"}));
input.files = dt.files; input.dispatchEvent(new Event("change", {bubbles: true}));
await new Promise(r => setTimeout(r, 3000));
"loaded"
```

This runs exactly the code the Open button runs (validation, timezone shift, settings). If the site pops
"Discard unsaved changes?" first, click **OK**. For files above ~200 KB build the object in steps
(`window.__p = {data: [...first phases...]}`, then `window.__p.data.push(...more phases...)`, then
`window.__p.resources = [...]; window.__p.advanced = {...}` and use `JSON.stringify(window.__p)`).

### 9.2 Dump the rows the engine rendered → `verify`

```js
const g = document.getElementById("GanttContainer").ej2_instances[0];
JSON.stringify(g.flatData.map(r => { const p = r.ganttProperties; return {
  id: p.taskId, name: p.taskName, start: p.startDate && p.startDate.toISOString(),
  end: p.endDate && p.endDate.toISOString(), dur: p.duration, unit: p.durationUnit,
  pred: p.predecessorsName, res: p.resourceNames || "", prog: p.progress,
  ms: !!p.isMilestone, parent: !!r.hasChildRecords }; }))
```

Save the returned JSON to `rows.json` and run `python3 scripts/gantt.py verify plan.gantt rows.json`.
`VERIFIED` means every task, date, duration, link, resource, progress and milestone matches the file.
Also take a screenshot for the user (`computer {action:"screenshot"}`).

### 9.3 Inspect state / settings the site holds

```js
let vm = document.querySelector("#toolbarElement").__vue__; while (vm && vm.$options.name !== "gantt") vm = vm.$parent;
({advanced: vm.advanced, resources: vm.resources, tasks: vm.data.length})
```

`vm.viewSelected = "Edit Settings"; vm.viewChanged("Edit Settings")` switches views; the settings form is then on
the page (checkboxes/selects can be driven with `form_input`). Prefer changing settings in the plan spec and
rebuilding – it is deterministic and the file is the source of truth.

### 9.4 Export PDF / PNG from the site

Click **Import / Export** → **Export to PDF File** (or **Export to Image File**) → in the modal click **Export**.
`find "Export"` gives the refs. The download only reaches the user's disk in Claude in Chrome; in the Cowork
pane tell the user to do it themselves or use the HTML preview (`gantt.py preview`) instead.

### 9.5 Filters, Today, views

`find "All Tasks"` → `form_input` with `Remaining Tasks` / `Overdue Tasks`; `find "Today"` → click;
`find "Project View"` → `form_input` with `Resource View` / `Edit Resources` / `Edit Settings`.

### 9.6 Etiquette

The pane is the user's browser: do not close their other tabs, do not click **New** while they have unsaved
work without asking, and never accept the cloud signup/subscription prompts.

## 10. Cloud-only features (not in scope of the free tool)

Save to Cloud, project list, revisions (each revision downloads as the same `.gantt` JSON), Share link /
embed, per-user permissions, autosave, AI assistant, REST API (`X-API-Key`: `/project-list`, `/export-csv`,
`/import-csv`, `/share`, `/project-task` GET/POST/DELETE – CSV columns identical to `csv-format.md`).
