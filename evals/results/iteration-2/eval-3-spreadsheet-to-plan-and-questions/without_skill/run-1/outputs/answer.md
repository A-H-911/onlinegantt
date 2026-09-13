# Team Plan v1 – onlinegantt.com file, critical path and workload

## What I produced

| File | Purpose |
|---|---|
| `Team Plan v1.gantt` | The plan, ready to open on onlinegantt.com (**Open (.gantt file)** in the app at `https://www.onlinegantt.com/#/gantt`). |
| `Team Plan v1.png` | Fit-width PNG of the whole chart (Task ID + Task Name grid, weeks starting Sunday, Fri/Sat shaded, critical path outlined in red). |

The `.gantt` file is the site's JSON format: `data` (tasks, nested with `subtasks`), `resources`, and `advanced` (settings). Settings applied: timezone `Asia/Riyadh`, work week Sunday–Thursday, working time 08:00–12:00 and 13:00–17:00, no holidays, English names, default colours (`color: ""`), date format `yyyy-MM-dd`, week starts Sunday, zoom 0, columns Task ID and Task Name, no allocation units shown (every assignment is a plain 100 %). Plan name "Team Plan", version 1.

## The plan as loaded (schedule after applying dependencies and the Sun–Thu calendar)

| ID | Task | Owner | Start | Finish | Days | Depends on | Done |
|---|---|---|---|---|---|---|---|
| 1 | **Planning** | – | 2026-10-05 | 2026-10-08 | 4 | – | 62 % (rolled up) |
| 2 | Kickoff | Anas | 2026-10-05 (Mon) | 2026-10-05 | 1 | – | 100 % |
| 3 | Requirements workshop | Anas, Sara | 2026-10-06 | 2026-10-08 (Thu) | 3 | 2FS | 50 % |
| 4 | Sign-off (milestone) | *nobody* | 2026-10-08 | 2026-10-08 | 0 | 3FS | 0 % |
| 5 | **Delivery** | – | 2026-10-11 | 2026-11-02 | 17 | – | 0 % |
| 6 | Build | Sara | 2026-10-11 (Sun) | 2026-10-22 (Thu) | 10 | 4FS | 0 % |
| 7 | UAT | Anas | 2026-10-27 (Tue) | 2026-11-02 (Mon) | 5 | 6FS+2 days | 0 % |

Project finish: **Monday 2026-11-02** (21 working days from kickoff, 19 of them task work + 2 days of lag).

Note the Task IDs changed from the spreadsheet: the two Phases became parent rows (1 Planning, 5 Delivery), so the spreadsheet's "Depends on" numbers 1/2/3/4 were remapped to 2/3/4/6. `4FS+2 days` became `6FS+2 days` on UAT.

## Critical path

Every task is on the critical path, because the plan is a single chain with no parallel work:

**Kickoff (2) → Requirements workshop (3) → Sign-off (4) → Build (6) → (+2 working days lag) → UAT (7)**

Total float is zero on all five tasks. Any slip anywhere pushes the 2026-11-02 finish by the same amount. The 2-day lag between Build and UAT is dead time on the critical path – if it is not genuinely needed (e.g. a deployment/hand-over wait), removing it brings the finish forward to Thursday 2026-10-29.

## Is anyone overloaded?

**No.** Nobody exceeds 100 % on any working day:

| Person | Assignments | Busiest day | Task-days / 21 working days |
|---|---|---|---|
| Anas | Kickoff, Requirements workshop, UAT | 100 % | 9 (43 %) |
| Sara | Requirements workshop, Build | 100 % | 13 (62 %) |

Things worth a look, though:

- **Sign-off has no owner.** It is a milestone that gates Build, so someone should be named as the approver.
- **Sara is the bottleneck, not overloaded.** The 10-day Build is single-handed and on the critical path; Anas is idle from 2026-10-11 to 2026-10-26 (12 working days). If Build can be split, giving Anas part of it would shorten the path.
- **Progress values don't match the dates.** Kickoff is 100 % and the workshop 50 % done, yet the plan starts 2026-10-05, in the future. I kept the percentages as given; adjust them or the dates.

## Assumptions I had to make (nobody was available to ask)

1. **Kickoff date `05/10/2026` read as day/month/year = 5 October 2026** (the Riyadh convention). If it was meant as 10 May 2026 (US format; that day is a Sunday, the first day of your work week), change the Kickoff start on the site and everything reschedules. With that reading the schedule is: Kickoff 05-10, workshop 05-11→05-13, Sign-off 05-13, Build 05-14→05-27, UAT 06-01→06-07; same critical path and same workload conclusions.
2. The `+2 days` lag on UAT is counted in **working days** (Fri 23 and Sat 24 Oct are skipped; UAT starts Tue 27 Oct). If the site treats it as calendar days, UAT will show as 25–29 Oct instead.
3. "Anas; Sara" on the workshop = both assigned full-time for all 3 days.
4. The `Sign-off` row (0 days, note "milestone") is stored as a milestone with an empty note; the workshop's note "Two sessions, room B" is kept as the task note.
5. Phases became parent (summary) tasks; parent progress is duration-weighted from the children.
6. Format caveat: the task/resource structure (`data`, `resources`, `advanced.workWeek`) matches onlinegantt.com's published format. The remaining settings (`dayWorkingTime`, `timezone`, `dateFormat`, `weekStartDay`, `zoom`, `columns`, `showUnits`, `locale`) are written using the site's underlying Syncfusion Gantt property names, which I could not verify against a live export. If any of them are not picked up on open, set them once under **Edit Settings** on the site and re-save – the tasks, dates, dependencies and resources will load regardless.
