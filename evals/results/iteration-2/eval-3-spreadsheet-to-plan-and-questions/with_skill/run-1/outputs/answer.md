Your spreadsheet is now an onlinegantt.com plan. Files (in the outputs directory):

- `Team Plan v1 2026-09-13.gantt` – open this on the site
- `Team Plan v1 2026-09-13.html` – standalone preview
- `Team Plan v1 2026-09-13.png` – fit-width image of the whole plan

![Team Plan](Team%20Plan%20v1%202026-09-13.png)

**Plan:** Team Plan — `Team Plan v1 2026-09-13.gantt` (+ .html preview, fit-width PNG)
**Span:** 2026-10-05 → 2026-11-02 (21 working days, 29 calendar days) · 4 tasks / 1 milestone / 2 phases · 13 % complete (duration-weighted)
**Calendar:** Asia/Riyadh, Sunday–Thursday, 08:00–12:00 + 13:00–17:00, no holidays
**Settings:** date format yyyy-MM-dd, week starts Sunday, zoom 0 (1 day per column), columns Task ID + Task Name, default colours, English names, everyone at 100 %

| ID | Task | Start | End | Duration | % | Deps | Owner |
|---:|---|---|---|---|---:|---|---|
| 6 | **Planning** | 2026-10-05 | 2026-10-08 | 4 days | 62.5 | | |
| 1 | Kickoff | 2026-10-05 | 2026-10-05 | 1 day | 100 | | Anas |
| 2 | Requirements workshop | 2026-10-06 | 2026-10-08 | 3 days | 50 | 1FS | Anas, Sara |
| 3 | ◆ Sign-off | 2026-10-08 | 2026-10-08 | 0 | 0 | 2FS | |
| 7 | **Delivery** | 2026-10-11 | 2026-11-02 | 17 days | 0 | | |
| 4 | Build | 2026-10-11 | 2026-10-22 | 10 days | 0 | 3FS | Sara |
| 5 | UAT | 2026-10-27 | 2026-11-02 | 5 days | 0 | 4FS+2 days | Anas |

**Critical path:** Kickoff (1) → Requirements workshop (2) → Sign-off (3) → Build (4) → UAT (5), finishing 2026-11-02. Every task in the plan is on it – the whole plan is one dependency chain, so a slip anywhere pushes the finish by the same amount. There is no float except the 2-day lag between Build and UAT (Build ends Thu 22 Oct, the lag skips the weekend, UAT starts Tue 27 Oct); if Build overruns by up to 2 working days you could absorb it by dropping that lag.

**Workload:** nobody is overloaded – no one exceeds 100 % on any working day.

| Resource | Tasks | Assigned working days |
|---|---:|---:|
| Sara | 2 (Requirements workshop, Build) | 13 |
| Anas | 3 (Kickoff, Requirements workshop, UAT) | 9 |

Sara and Anas share the workshop but that is one task each, and Sara's Build and Anas's UAT never overlap. Sara is the busier of the two (13 of the 21 working days, including the entire Build phase), so she is the person whose availability the schedule depends on – not overloaded, but a single point of dependency.

**Verified on onlinegantt.com:** not in this session (no browser). The file passes the skill's validator with 0 warnings and 0 tasks that would move on load. To open it: go to https://www.onlinegantt.com/#/gantt → **Open (.gantt file)** → pick `Team Plan v1 2026-09-13.gantt`. Check Edit Settings if the calendar looks wrong.

**Decisions taken from your answers:** Asia/Riyadh · Sun–Thu · 08–12 + 13–17 · no holidays · English names · default colours · yyyy-MM-dd · week starts Sunday · zoom 0 · columns Task ID + Task Name · everyone 100 % · fit-width PNG · plan name "Team Plan", version 1.

**How the spreadsheet was read:** `05/10/2026` taken day-first as 5 October 2026 (a Monday, a working day); "Depends on" numbers refer to the spreadsheet's row numbers, which became the task IDs (1–5); the two phases got IDs 6 and 7; `Days = 0` + the "milestone" marker made Sign-off a milestone (the marker was not kept as a note); `4FS+2 days` was carried over as the UAT link; "Anas; Sara" became two assignments; "Two sessions, room B" is on the workshop as a note.
