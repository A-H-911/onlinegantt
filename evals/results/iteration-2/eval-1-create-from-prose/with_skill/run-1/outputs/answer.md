The Wafi launch plan is built, validated (0 warnings, no task will move when the site loads it) and saved in your outputs directory:

- `Wafi Mobile Banking App Launch v1 2026-09-13.gantt` – open this on onlinegantt.com
- `Wafi Mobile Banking App Launch v1 2026-09-13.html` – preview
- `Wafi Mobile Banking App Launch v1 2026-09-13.png` – whole plan, fit-width, 2×

**Plan:** Wafi Mobile Banking App Launch – إطلاق تطبيق وافي للخدمات المصرفية
**Span:** 01/11/2026 → 07/02/2027 (69 working days, 99 calendar days) · 9 tasks / 3 milestones / 4 phases
**Calendar:** Asia/Riyadh, Sun–Thu, 08:00–12:00 + 13:00–17:00, holiday 22–23/11/2026

| ID | Phase / task | Start | End | Days | Owner |
|---:|---|---|---|---:|---|
| 1 | **Discovery – الاستكشاف** (blue) | 01/11/2026 | 05/11/2026 | 5 | |
| 2 | Stakeholder workshops – ورش عمل أصحاب المصلحة | 01/11/2026 | 04/11/2026 | 4 | Anas |
| 3 | Competitor review – مراجعة المنافسين | 01/11/2026 | 05/11/2026 | 5 | Sara |
| 4 | ◆ Requirements sign-off – اعتماد المتطلبات | 05/11/2026 | | | after 2, 3 |
| 5 | **Design – التصميم** (green) | 08/11/2026 | 03/12/2026 | 18 | |
| 6 | UX wireframes – المخططات الهيكلية لتجربة المستخدم | 08/11/2026 | 17/11/2026 | 8 | Layla |
| 7 | Visual design – التصميم البصري | 18/11/2026 | 03/12/2026 | 10 | Layla (spans the 22–23/11 holiday) |
| 8 | ◆ Design approved – اعتماد التصميم | 03/12/2026 | | | after 7 |
| 9 | **Build – البناء** (orange) | 06/12/2026 | 26/01/2027 | 38 | |
| 10 | Backend APIs – واجهات برمجة التطبيقات الخلفية | 06/12/2026 | 31/12/2026 | 20 | Omar |
| 11 | Mobile app – تطبيق الجوال | 13/12/2026 | 14/01/2027 | 25 | Sara (10SS+5 days) |
| 12 | Integration testing – اختبار التكامل | 17/01/2027 | 26/01/2027 | 8 | Omar, Sara |
| 13 | **Launch – الإطلاق** (purple) | 27/01/2027 | 07/02/2027 | 8 | |
| 14 | UAT – اختبار قبول المستخدم | 27/01/2027 | 02/02/2027 | 5 | Anas |
| 15 | App store submission – تقديم التطبيق لمتاجر التطبيقات | 03/02/2027 | 07/02/2027 | 3 | Sara |
| 16 | ◆ Go-live – الإطلاق الفعلي | 07/02/2027 | | | after 15 |

**Finish date:** Go-live on **Sunday 07/02/2027** (end of day, 17:00).

**Critical path** (every task except Stakeholder workshops, which has 1 day of float):
Competitor review → Requirements sign-off → UX wireframes → Visual design → Design approved → Backend APIs (its *start* drives the mobile app via the SS+5 link) → Mobile app → Integration testing → UAT → App store submission → Go-live.
Delaying any of these by a day moves Go-live by a day.

**Workload – nobody is over-allocated.** Every assignment is sequential per person, so no one exceeds 100 % on any working day:

| Resource | Tasks | Working days |
|---|---:|---:|
| Sara | 4 | 41 |
| Omar | 2 | 28 |
| Layla | 2 | 18 |
| Anas | 2 | 9 |

**Decisions taken from your answers:** Asia/Riyadh · Sun–Thu, 08–12 + 13–17 · holiday 22–23/11/2026 · dd/MM/yyyy · week starts Sunday · zoom 1 (weekly) · columns Task ID, Task Name, Start Date, End Date, Resources · bilingual English – Arabic names · coloured by phase (blue / green / orange / purple; summary bars stay grey) · everyone at 100 % · fit-width PNG · file `Wafi Mobile Banking App Launch v1 2026-09-13.gantt`.
**Links as specified, nothing inferred beyond them:** milestones close each phase FS; Mobile app = `10SS+5 days`; Integration testing waits for both Backend APIs and Mobile app.

**Verified on onlinegantt.com:** not in this session (no browser). To open it: go to `https://www.onlinegantt.com/#/gantt` → **Open (.gantt file)** → pick `Wafi Mobile Banking App Launch v1 2026-09-13.gantt`. The calendar, columns, zoom and date format load with the file.
