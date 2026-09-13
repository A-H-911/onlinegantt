---
name: onlinegantt
description: Create, edit, analyse, convert, render and verify project plans for onlinegantt.com (the free Gantt chart tool) as .gantt files, with HTML/PNG previews. Use this skill whenever the user mentions onlinegantt, a .gantt file, a Gantt chart, a project plan / schedule / timeline / roadmap / WBS, phases-tasks-milestones, dependencies or predecessors, task progress or resource assignments – even if they only say "make me a plan for …", "update the plan", "shift everything by a week", "who is overloaded", "turn this spreadsheet into a Gantt", "give me an image of the plan", "export it to PDF" or "open it on the site". Also use it for opening, saving, importing, exporting and changing settings on onlinegantt.com, and for reading or explaining an existing .gantt file.
---

# onlinegantt – plans as `.gantt` files

onlinegantt.com's free tool keeps a plan entirely in one JSON file (`.gantt`) that the user opens with
**Open (.gantt file)**. This skill produces those files correctly (dates, calendar, links, resources,
settings), edits them as new versions, renders HTML and PNG previews, analyses plans, converts
spreadsheets, and can drive the site in a browser to verify the result. The rules come from reading the
site's source and testing the live engine; details live in `references/`.

## Files in this skill

| file | read it when |
|---|---|
| `references/plan-interview.md` | any new plan or edit – the question screens (options + recommendations) for everything the request leaves open |
| `references/plan-spec.md` | writing the spec JSON that `build` consumes (fields, examples, exit codes) |
| `references/gantt-format.md` | you need the exact `.gantt` schema, engine rules, colours, settings |
| `references/csv-format.md` | importing/exporting the site's CSV or reading a user spreadsheet |
| `references/site-guide.md` | explaining the UI, giving click-by-click steps, or automating the site in a browser |
| `scripts/gantt.py` | every build / validate / inspect / preview (HTML, PNG) / csv / recolor / verify / decompile |

Run scripts with `python3 <skill-dir>/scripts/gantt.py <command> …` (`python` on Windows; Python 3.9+,
standard library only). PNG rendering additionally needs Playwright + Chromium; the scripts never install
it – they print the command, and you ask the user before running it. `gantt.py -h` lists the commands.

## Two rules that shape every interaction

**1. Ask, don't assume – as tap-to-select screens.** Anything the request does not settle (calendar,
settings, language, colours, resources, units, images, save location, missing durations/owners, inferred
links, conflicts, over-allocation) is asked with the `AskUserQuestion` tool: 2–4 options per question, the
recommended option first and labelled `(Recommended)`, `multiSelect` where several answers apply, up to 4
questions per screen. A new plan starts with the shortcut screen ("Use all recommended values" / "Ask me each
question"); plan-specific items are asked either way. Gaps in the plan itself are proposed in a table and
confirmed with one question. `plan-interview.md` has every screen ready to use. Plain-text questions only
if the tool truly is not available. Never wait silently – when a build stops for a decision, ask.

**2. Let the scripts write the file.** The site's engine re-schedules on load: it snaps starts to working
time, skips weekends/holidays, moves every linked task to `predecessor + lag`, recomputes parents and shifts
dates between timezones. `build` reproduces that engine (verified field-for-field against the site), refuses
files the site would mangle and stops (exit 3) when a requested date and a dependency disagree. Hand-written
`StartDate: "2026-10-05T00:00:00.000Z"` JSON is how plans silently drift – don't.

## Workflow A – create a plan (from a description, notes, or a spreadsheet)

1. **Understand the request.** Extract phases, tasks, milestones, durations, owners, known dates and stated
   dependencies. If a spreadsheet was given, `gantt.py csv <file.csv|.xlsx> -o plan.json` first – rows,
   hierarchy and links come mapped, tasks renumbered top-down (mapping printed); calendar/settings are
   placeholders to confirm; `review:` lines list ambiguous dates to ask about (screen 12).
   Work that must happen on non-working days (a weekend move) and vague dates ("mid-November") are asked
   as in screen 12 – both are situations where the request alone cannot decide.
2. **Interview** (`plan-interview.md` screens 0–5): shortcut, calendar, display settings, language, colour
   scheme (+ precedence when mixed), resources and units, PNG variants, save location, file name.
3. **Fill the gaps** (screen 7): durations/owners/dates the request lacks → proposal table → one confirm question.
4. **Draft and confirm** (screen 8): the compact table of phases, tasks, milestones and the dependencies you
   inferred (leaf-to-leaf, FS unless stated; sequential within a phase when the work is sequential; a milestone
   closing each phase when that reads naturally) → one confirm question. Inferred links are guesses – the user
   decides. Bilingual plans: list the Arabic names for confirmation (screen 12b); colour-by-phase: show the
   phase → hue table for confirmation (screen 11b); external parties: ask how to name each (screen 13b).
5. **Build**: write the spec (`plan-spec.md`) to a temp file, then
   `python3 scripts/gantt.py build spec.json --out-dir <folder> --version 1 --png <fit,day,table|--no-png> [--today YYYY-MM-DD]`.
   * exit 3 = conflicts → one question per conflict (screen 9) → re-run with `--on-conflict …` or fix the spec.
   * exit 2 = spec error → fix it (the message says what).
   * `png: skipped …` = renderer missing → ask whether to run the printed install command; the HTML preview
     exists meanwhile. Never install without a yes.
   * `note:` lines = things done automatically (milestones completed because their tasks are done, calendar
     exceptions applied) – mention them in the summary. `review:` lines = things to ask (progress on tasks that
     have not started: reset to 0 %? – screen 12).
   The build writes `<Plan> v1 <date>.gantt`, `.html`, the chosen `.png` variants and `.spec.json` (the build
   input, kept for later edits), and prints the summary, critical path, status and workload.
6. **Workload** (screen 10): one question per over-allocated person; apply the answer (re-sequence, units,
   reassign) as an edit and rebuild the same version before delivering.
7. **Deliver.** Cowork: `SendUserFile` the `.gantt`, `.html` and `.png` (the PNG shows the chart in chat), then
   `device_commit_files` into the chosen folder. Claude Code: build straight into the chosen directory and
   mention the paths. Then the summary template (screen 11).
8. **Verify on the site** when a browser tool is available (Cowork built-in browser or Claude in Chrome):
   `site-guide.md` §9.1 (inject the file through the site's own Open handler), §9.2 (dump rows),
   `gantt.py verify <file>.gantt rows.json`, screenshot for the user. Without a browser, give the three clicks (§8).

## Workflow B – edit an existing plan

Never overwrite the user's file; every change is a new version, ids stay stable.

1. `gantt.py decompile "<file>" -o plan.json --name "<Plan>"` – ids, names, durations, links, resources,
   colours, notes and settings in readable form (linked tasks carry no `start`; the links define them).
2. Ask only what the edit leaves open (calendar/settings/colours/resources/units/PNG variants only if the
   change touches them; save location and version name always – screen 5/6).
3. Apply the change in the spec: add tasks (new ids = max+1), delete, move, change durations/progress/
   resources/colours, insert links. "Shift X by 5 days" → lag or anchor date; "assign the logistics tasks to
   Sara" → resources; "set draft to 100 %" → progress; "overlap design and development" → SS link or negative
   lag; "add 10 tasks after review" → children chained with FS links. Inserting a phase in front of a
   milestone that closed the previous phase: ask where the milestone goes (screen 12). Links that the new
   tasks make redundant are replaced by the single direct link – say so in the summary.
4. `gantt.py build plan.json --out-dir <folder> --version <N+1> --png …` (N from the old file name;
   unnumbered originals count as v1). Conflicts and workload as in A.
5. Report what moved (the build prints resolved conflicts and new dates), deliver and verify as in A.

`gantt.py recolor "<file>.gantt" --by phase --by status -o "<next version>.gantt"` recolours after the fact
(later schemes override earlier ones; `--status-all` also colours on-track tasks; `--by clear` resets).

## Workflow C – questions about a plan

`gantt.py inspect "<file>.gantt" [--today YYYY-MM-DD] [--no-table]` prints the span, task table, critical
path, overdue / at-risk / in-progress / upcoming tasks and per-person workload with over-allocation days.
Answer from it: "what blocks the launch" = the critical path and the links into the launch milestone; "who is
overloaded" = the over-allocation section; "what slips if the supplier is late" = the successors of that task.

## Workflow D – conversions and images

* Spreadsheet → plan: `gantt.py csv sheet.xlsx -o plan.json`, then Workflow A from step 2.
* Plan → CSV in the site's Excel format: `gantt.py csv "<file>.gantt" -o "<file>.csv"`.
* Images of an existing plan: `gantt.py preview "<file>.gantt" --png fit,day,table [--png-scale 2]`
  (fit = whole plan 1600 px wide; day = one column per day, wide; table = task table only). Exit 4 = renderer
  missing → ask before installing. HTML only: `gantt.py preview "<file>.gantt" [--mode fit|day|table]`.
* Check a file someone else made: `gantt.py validate "<file>.gantt"` (site errors, and `drift:` lines for
  tasks the engine will move on load).

## Workflow E – operating the website

For "open / save as / import / export / settings on onlinegantt.com": give the exact clicks from
`site-guide.md` §2–§8, or drive the browser (§9) when a browser tool exists and the user wants that.
Downloads (Save As, PDF, PNG, CSV) reach the user's disk only through Claude in Chrome; from the Cowork pane,
produce the files with the scripts and let the user click Export themselves. Never sign the user up for the
cloud version or accept its prompts.

## Format rules to keep in mind while drafting (the scripts enforce them)

* Dependencies are **leaf → leaf**. Phases never carry links; link the last task of one phase to the first
  task (or milestone) of the next.
* **Links beat dates.** A linked task starts exactly at `predecessor + lag`; slack is `"3FS+5 days"`, overlap
  `"3SS"` or `"3FS-2 days"`. Explicit dates only on anchor tasks.
* Parents get dates, duration and progress from their children – don't specify them.
* Every resource a task uses must be in the top-level list (`build` adds them automatically).
* 12 colours: default, orange 31, yellow 61, lime 91, green 121, teal 151, cyan 181, blue 211, indigo 241,
  purple 271, magenta 301, pink/red 331 (names accepted in the spec).
* Durations count working days/hours only; "1 week" = 5 working days whatever the calendar.
* Milestones: `milestone: true`, no duration, usually linked FS to the tasks they conclude.
* Task ids: positive integers, unique across the tree, stable across versions.
* Bilingual names: `English – Arabic` (en dash, English first); resource names as the user decided.
* File naming: `<Plan name> vN YYYY-MM-DD.gantt` (English half of the name, `<>:"/\|?*` stripped);
  images `<same stem>.png`, `… (day scale).png`, `… (table).png`; spec copy `<same stem>.spec.json`.
* Work on off-days: `calendar.workOn` (7-day week + every other off-day blocked, recomputed each build) –
  only after the user chose that option; the alternative is tasks on the nearest working days with the real
  dates in the notes.

## Answer style

Practical and short: question screens for decisions, a table before building, the summary after, files
first. Show the PNG in chat when there is one.
