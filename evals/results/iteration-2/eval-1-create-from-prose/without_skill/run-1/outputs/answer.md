The Wafi launch plan is built and saved as version 1:

- `Wafi-App-Launch-Plan-v1.gantt` — the onlinegantt.com plan (open it with **Open (.gantt file)** at onlinegantt.com)
- `Wafi-App-Launch-Plan-v1.png` — fit-width PNG of the chart (weekly timeline, Sunday-start weeks, Fri/Sat and the 22–23 Nov holiday shaded, bars coloured by phase)

## Plan summary

16 rows: 4 phase rows (Discovery, Design, Build, Launch) with 9 tasks and 3 milestones. Task names are bilingual (English – Arabic). Calendar: Asia/Riyadh, Sun–Thu, 08:00–12:00 / 13:00–17:00, holiday 22–23/11/2026. Dates shown in dd/MM/yyyy.

| ID | Task | Start | End | Days | Predecessor | Resources |
|---|---|---|---|---|---|---|
| 1 | Discovery – الاستكشاف | 01/11/2026 | 05/11/2026 | | | |
| 2 | Stakeholder workshops – ورش عمل أصحاب المصلحة | 01/11/2026 | 04/11/2026 | 4 | | Anas |
| 3 | Competitor review – مراجعة المنافسين | 01/11/2026 | 05/11/2026 | 5 | | Sara |
| 4 | Requirements sign-off – اعتماد المتطلبات (milestone) | 05/11/2026 | 05/11/2026 | 0 | 2FS, 3FS | |
| 5 | Design – التصميم | 08/11/2026 | 03/12/2026 | | | |
| 6 | UX wireframes – المخططات الهيكلية لتجربة المستخدم | 08/11/2026 | 17/11/2026 | 8 | 4FS | Layla |
| 7 | Visual design – التصميم البصري | 18/11/2026 | 03/12/2026 | 10 | 6FS | Layla |
| 8 | Design approved – اعتماد التصميم (milestone) | 03/12/2026 | 03/12/2026 | 0 | 7FS | |
| 9 | Build – البناء | 06/12/2026 | 26/01/2027 | | | |
| 10 | Backend APIs – واجهات برمجة التطبيقات الخلفية | 06/12/2026 | 31/12/2026 | 20 | 8FS | Omar |
| 11 | Mobile app – تطبيق الجوال | 13/12/2026 | 14/01/2027 | 25 | 10SS+5 days | Sara |
| 12 | Integration testing – اختبار التكامل | 17/01/2027 | 26/01/2027 | 8 | 10FS, 11FS | Omar, Sara |
| 13 | Launch – الإطلاق | 27/01/2027 | 07/02/2027 | | | |
| 14 | UAT – اختبار قبول المستخدم | 27/01/2027 | 02/02/2027 | 5 | 12FS | Anas |
| 15 | App store submission – التقديم إلى متاجر التطبيقات | 03/02/2027 | 07/02/2027 | 3 | 14FS | Sara |
| 16 | Go-live – بدء التشغيل الفعلي (milestone) | 07/02/2027 | 07/02/2027 | 0 | 15FS | |

Visual design spans the 22–23 Nov holiday (that is why 10 working days run 18/11 → 03/12).

## Finish date

**Sunday 7 February 2027** (Go-live milestone, end of the working day). That is 14 weeks from the 1 November start; 69 working days in total.

## Critical path

Competitor review (3) → Requirements sign-off (4) → UX wireframes (6) → Visual design (7) → Design approved (8) → Backend APIs (10) → Mobile app (11) → Integration testing (12) → UAT (14) → App store submission (15) → Go-live (16).

Notes:
- Backend APIs is critical through its *start*, not its finish: the mobile app's start is tied to it (SS + 5 working days), so any delay starting the backend pushes go-live. Its finish (31/12) has 10 working days of float before integration testing needs it (integration testing waits for the mobile app, which finishes 14/01).
- The only non-critical task is Stakeholder workshops (Anas), with 1 working day of float (it finishes 04/11; the sign-off waits for the competitor review on 05/11).
- Every other task has zero float, so any slip anywhere else moves the 07/02/2027 go-live one-for-one.

## Over-allocation

**No one is over-allocated.** Each person's assignments are strictly sequential, with no overlapping days:

- Anas: Stakeholder workshops (01–04/11) → UAT (27/01–02/02)
- Sara: Competitor review (01–05/11) → Mobile app (13/12–14/01) → Integration testing (17–26/01) → App store submission (03–07/02)
- Layla: UX wireframes (08–17/11) → Visual design (18/11–03/12)
- Omar: Backend APIs (06–31/12) → Integration testing (17–26/01)

Sara is the busiest (41 of the 69 working days) and sits on the critical path from mid-December to go-live, so she is the person to protect. Integration testing is the only task with two people (Omar and Sara), both at full allocation and both free at that point.

## Assumptions and how the file was built

- **Format:** onlinegantt.com's .gantt is JSON on top of Syncfusion Gantt fields (`data[]` with `TaskID`, `TaskName`, `StartDate`, `EndDate`, `Duration`, `DurationUnit`, `Progress`, `color`, `Predecessor`, `resources[]`, `info`, `subtasks[]`; a top-level `resources[]`; and an `advanced` block with `columns`, `timezone`, `workWeek`, `workTime`, `holidays`). Milestones are zero-duration tasks. Predecessors use the standard `2FS,3FS` / `10SS+5 days` notation. Colours are hue numbers (Discovery 211 blue, Design 280 purple, Build 140 green, Launch 25 orange), matching how the onlinegantt API describes the Color field.
- **Schedule verification:** the dates were computed on the Sun–Thu calendar with the holiday and then cross-checked by loading the file into the Syncfusion Gantt engine headlessly; both agree on every start/end date and on the 07/02/2027 finish.
- **Settings I could not verify against a saved file** (the app has no published schema): the key names `dateFormat`, `firstDayOfWeek`, `zoomLevel` and `allocationUnits` in the `advanced` block are best-effort. If the app does not pick them up, set date format dd/MM/yyyy, first day of week Sunday, zoom = weekly, and hide Duration/Progress/Dependency/Color/Notes columns once in **Edit Settings**; the tasks, calendar, holidays, dependencies, resources and colours are in the standard fields and will load regardless.
- **No allocation units:** resource assignments carry only the resource name (no `unit` value), so nobody shows a [xx%] suffix.
- **Milestone convention:** a milestone that follows a finish-to-start link sits on its predecessor's finish day (e.g. sign-off on 05/11), and the next task starts the following working day (08/11) — this is how onlinegantt/Syncfusion schedules it.
