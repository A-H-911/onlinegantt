# The interview – how the skill asks for anything it does not know

> Defaults below (Asia/Riyadh, Sunday–Thursday, bilingual English – Arabic) are the recommended answers, not
> assumptions: every plan still goes through these screens. To change what is recommended, edit this file.

The rule: **nothing is assumed**. Whatever the request leaves open is asked, and every question is a
tap-to-select screen, never free text: 2–4 options, the recommended option **first** and labelled
`(Recommended)`, `multiSelect` when several answers can apply, at most 4 questions per screen.
Use the `AskUserQuestion` tool (Cowork and Claude Code both have it). Only when that tool is genuinely
unavailable, print the same screens as numbered lists with lettered options and wait for the reply.
Answers already given in the request are restated ("using Sun–Thu as you said") and not asked again.

Contents: 1 Screen 0 shortcut · 2 Calendar · 3 Display · 4 Content · 5 Resources · 6 Output ·
7 Missing plan details · 8 Confirming the draft · 9 Conflicts · 10 Workload · 11 Summary template ·
12 Situational questions (weekend work, vague dates, ambiguous spreadsheet dates, future progress,
vendor names, Arabic names, colour order, milestone placement when inserting a phase)

## 1. Screen 0 – the shortcut (always first for a new plan)

| question | options |
|---|---|
| How would you like to set up this plan? | **Use all recommended values (Recommended)** – Asia/Riyadh, Sun–Thu, 08–12 + 13–17, yyyy-MM-dd, week starts Sunday, zoom 1 day, columns ID + Task Name, bilingual English – Arabic names, no colours, everyone at 100 %, fit-width PNG · **Ask me each question** – walk through screens 1–4 |

Whichever is chosen, the plan-specific screens are still asked: holidays, resources, allocation units,
PNG variants, save location and file name (section 5–6), plus anything in sections 7–10 that comes up.

## 2. Screen 1 – calendar (every date in the file depends on it)

| # | question | options (recommended first) | field |
|---|---|---|---|
| 1 | Timezone for the dates | **Asia/Riyadh (UTC+3) (Recommended)** · Asia/Dubai (UTC+4) · Europe/London · Other (type it) | `calendar.timezone` |
| 2 | Working days | **Sunday–Thursday (Recommended)** · Monday–Friday · Sunday–Wednesday + half Thursday (say so) · Other | `calendar.workWeek` |
| 3 | Daily working hours | **08:00–12:00 and 13:00–17:00 (Recommended)** · 08:00–17:00 continuous · 09:00–17:00 · Other | `calendar.workTime` |
| 4 | Holidays to block (multi-select) | **None** · Saudi National Day 23 Sep · Founding Day 22 Feb · Eid al-Fitr / Eid al-Adha breaks (Claude fills the dates for the plan's year and shows them) · Other dates (type them) | `calendar.holidays` |

## 3. Screen 2 – display settings (the site's "Edit Settings" page)

| # | question | options | field |
|---|---|---|---|
| 5 | Date format | **yyyy-MM-dd (Recommended)** · dd/MM/yyyy · dd MMM yyyy · Other (any of the site's 12) | `settings.dateFormat` |
| 6 | First day of the week on the timeline | **Sunday (Recommended)** · Monday · Saturday | `settings.firstDayOfWeek` |
| 7 | Default zoom | **1 day per column (Recommended)** · 1 week · 1 month · Hours | `settings.zoomLevel` 0 / 1 / 4 / -3 |
| 8 | Visible grid columns (multi-select) | **Task ID + Task Name (Recommended)** · Start Date + End Date · Duration + Progress % · Dependency + Resources (Color and Notes on request) | `settings.columns` |

## 4. Screen 3 – content conventions

| # | question | options | notes |
|---|---|---|---|
| 9 | Language of task names and notes | **Bilingual English – Arabic (Recommended)** · English only · Arabic only | en dash, English first |
| 10 | Colour scheme (multi-select) | **None – site default (Recommended)** · By phase · By resource/owner · By status (green done, blue on track, orange at risk, pink/red overdue) · Custom per task (tell me) | mixing allowed |
| 11 | Only if two schemes were picked: which wins when both apply? | **Status overrides phase/resource (Recommended)** · Phase/resource overrides status | `recolor --by a --by b` (later wins) |
| 11b | Only for "by phase": colours per phase | show a table phase → proposed hue (default order blue, green, orange, purple, cyan, magenta, yellow, teal, indigo, lime, pink) then one question: **Use these colours (Recommended)** · I'll list changes ("Design: green …") · Traffic-light order (green, yellow, orange, pink/red, purple, blue) | the user picks per plan |
| 12 | Resource names when bilingual | **Exactly as given (Recommended)** · Bilingual like tasks ("Sara – سارة") | only when 9 = bilingual |
| 12b | Only when 9 = bilingual: the Arabic wording | after drafting, list every bilingual name (phases, tasks, milestones) and ask one question: **Use these Arabic names (Recommended)** · I'll list corrections · Use literal translations instead | the user sees the Arabic before building |

## 5. Screen 4 – resources

| # | question | options | notes |
|---|---|---|---|
| 13 | Team for this plan (multi-select of the names found in the request) | **All of: <names found> (Recommended)** · each name as its own option · Add someone (type) | becomes `resources` |
| 13b | For every external party (vendor, contractor, agency): how to name it | "<Role> (external)" e.g. "Moving company (external)" · The company's real name (type it) · Bilingual "<Role> – <الدور>" · Not a resource – mention in notes only | no recommendation; one question per party |
| 14 | Allocation units | **Everyone 100 % (Recommended)** · Use % units – I'll give splits for shared tasks · Use % units – propose splits for me | `unit` on assignments |

## 6. Screen 5 – output

| # | question | options | notes |
|---|---|---|---|
| 15 | Images to produce with every version (multi-select) | **Whole plan, fit-width, 2× (Recommended)** · Day-scale image (wide) · Task table only · No image | `build --png fit,day,table` / `--no-png` |
| 16 | Where to save | **<connected folder / project directory> (Recommended)** · Another folder (type the path) · Just send the files in chat | Cowork: `device_commit_files`; Claude Code: write there |
| 17 | File name | **"<Plan name> v1 <today>.gantt" (Recommended)** · Different plan name (type it) | English half of a bilingual name; edits → vN+1 |

## 7. Missing plan details (durations, owners, dates, milestones)

Do not guess silently. Build a table of the gaps with a proposed value and a one-line reason
("Testing 5 days – typical for 25 days of build"), show it, then ask **one** question:

| question | options |
|---|---|
| These tasks had no <durations/owners/…>. Use my proposals? | **Yes, use the proposals (Recommended)** · I'll type corrections (list "task: value") · Ask me task by task (4 per screen, options like 1 day / 3 days / 1 week / other) |

## 8. Confirming the draft before building

Show the compact table (phase → tasks with duration, owner, colour; milestones) and the list of
dependencies you inferred, each with its reason, then ask one question:

| question | options |
|---|---|
| Build the plan as shown? | **Yes, build it (Recommended)** · I'll list changes · Walk me through the links one by one (each link becomes keep / drop / change-type, 4 per screen) |

## 9. Date / dependency conflicts (`build` exit code 3)

One question **per conflict**, 4 per screen, phrased with the task name and both dates:

| question | options |
|---|---|
| "Design review" was requested for 02/11 but its link 7FF puts it at 28/10 – which wins? | **Dependency wins – move the task (Recommended)** · Keep my date as a lag on the link (`7FF+3 days`) · Keep my date and drop the link |

Re-run `build` with `--on-conflict deps|lag|dates` when every conflict got the same answer, otherwise edit
the spec (set `start` / lag / remove `deps`) for the exceptions and run with `--on-conflict deps`.

## 10. Workload / over-allocation (after every build or edit)

Show the workload table. For **each over-allocated person** ask one question (4 per screen):

| question | options |
|---|---|
| Sara is at 200 % from 04/11 to 11/11 (Front-end + CMS setup). What should I do? | **Re-sequence: CMS setup after Front-end (Recommended)** · Split the time: 50 % each · Reassign CMS setup to someone else (pick who next) · Keep it – Sara is fine with it |

If nobody exceeds 100 %, say so in the summary and ask nothing.

## 12. Situational questions

**Work on non-working days** (a move on Friday–Saturday in a Sunday–Thursday week, a launch on a Saturday …).
The site has one calendar per plan and silently pushes tasks off non-working days, so ask – with **no**
recommended option, both are legitimate:

| question | options |
|---|---|
| "<task>" must happen on <dates>, which are outside the working week. How should the plan show it? | Open only those days: the file gets a 7-day week with every other off-day blocked as a holiday, so the chart shows the true dates (`calendar.workOn` does this and grows with the plan) · Keep the working week and model it as tasks on the nearest working days (e.g. Thursday load / Sunday unload) with the real dates in the notes |

**Vague dates** ("mid-November", "early Q1", "after Eid"): propose the first working day of that week/period as
the recommended option with two alternatives (a week earlier / later, or the exact calendar midpoint) and let
the user confirm – as in screen 1.

**Ambiguous spreadsheet dates** (`05/10/2026` can be 5 October or 10 May): `gantt.py csv` lists them under
`_ambiguous_dates`. Ask one question showing an example with both readings: **Day first – 5 October
(Recommended)** · Month first – 10 May; re-run with `--month-first` if needed. Unambiguous values (13/10/2026)
need no question.

**Spreadsheet ids**: `gantt.py csv` renumbers tasks top-down (phase 1, its tasks 2, 3 …) and remaps the
"Depends on" references; show the old → new mapping (`_id_map`) in the summary, no question needed.

**Progress on tasks that have not started** (`review:` lines from `build`): ask one question listing them:
**Reset them to 0 % (Recommended)** · Keep the values (work started early) · Decide task by task.

**Milestones whose predecessors are all complete** are set to 100 % automatically (`note:` line); mention it
in the summary, no question.

**Inserting a phase before a milestone that closed the previous phase** (e.g. QA between Build and Go-live):
ask where the milestone goes – **Close the new phase: last row inside it** · A row of its own after the new
phase · Leave it inside its original phase (that phase's bar then spans the new one). Links that become
implied through the new tasks are replaced by the single direct link (say so in the summary).

**PNG renderer missing** (`png: skipped …`): ask **Install Playwright + Chromium now (~150 MB)** · Skip images
this time · Never for this machine (then always pass `--no-png`).

## 11. Summary template (after every build)

```
Plan: <name> — <file>.gantt (+ .html preview, <png variants>, .spec.json for edits)
Span: <start> → <end> (<n> working days) · <tasks> tasks / <milestones> milestones / <phases> phases
Calendar: <tz>, <work week>, <hours>, <holidays>
Critical path: …
Workload: … (over-allocation: none / resolved as …)
Verified on onlinegantt.com: yes/no (+ screenshot) — or the 3 clicks to open it
Decisions taken from your answers: … · Proposals you accepted: … · Automatic: milestones completed, links simplified, ids renumbered (old → new)
```
