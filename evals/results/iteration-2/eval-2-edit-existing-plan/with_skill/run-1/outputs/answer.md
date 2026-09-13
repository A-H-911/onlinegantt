Done – the plan is saved as version 2 (the original v1 file is untouched):

- `evals/results/iteration-2/eval-2-edit-existing-plan/with_skill/run-1/outputs/Website Relaunch v2 2026-09-13.gantt`
- `… /Website Relaunch v2 2026-09-13.html` (preview)
- `… /Website Relaunch v2 2026-09-13.png` (whole plan, fit-width, 2×)

**New finish date: Sunday 13/12/2026 (Go live, 17:00) – previously 24/11/2026, i.e. 13 working days later.**

What moved

| Task | Before | Now |
|---|---|---|
| 14 Test plan – خطة الاختبار (Anas, 3 days) | – | 25/11 → 29/11, after Front-end (10FS) and CMS setup (11FS) |
| 15 Functional testing – الاختبار الوظيفي (Sara, 6 days) | – | 30/11 → 07/12, after Test plan (14FS) |
| 16 Bug fixing – إصلاح الأخطاء (Sara, 4 days) | – | 08/12 → 13/12, after Functional testing (15FS) |
| 12 Go live – الإطلاق | 24/11/2026 (10FS,11FS, inside Build) | 13/12/2026 (16FS, after Bug fixing) |
| 13 QA – ضمان الجودة (new phase) | – | 25/11 → 13/12 (13 days), between Build and Go live |

Nothing else moved: Discovery, Design and Build keep exactly the same dates (Build is still 04/11 → 24/11, driven by Front-end), and the calendar (Asia/Riyadh, Sun–Thu, 08–12 / 13–17, holiday 13–14/10), settings, columns, colours and all existing ids are unchanged. New ids are 13–16.

Other changes applied

- Content audit – تدقيق المحتوى: 40 % → 100 % (Discovery phase now rolls up to 100 %).
- CMS setup – إعداد نظام المحتوى: Sara → Anas. Sara now has Front-end alone in November, then Functional testing and Bug fixing in sequence.

Decisions I took (nobody was available to ask)

- Go live's old links to Front-end and CMS setup were replaced by the single link to Bug fixing (16FS), because the Test plan already waits for both; the old links would have been redundant. Its date, colour (pink/red) and id 12 are kept.
- Go live now sits as the last row of the plan, after the QA phase, so the phase is literally "between Build and Go live" and Build's own bar does not stretch over QA.
- New tasks use the default colour, like most existing tasks.

Summary
- Plan: Website Relaunch — Website Relaunch v2 2026-09-13.gantt (+ .html preview, fit PNG)
- Span: 04/10/2026 → 13/12/2026 (49 working days) · 10 tasks / 2 milestones / 4 phases
- Critical path: Stakeholder interviews → Content audit → Discovery complete → Wireframes → Visual design → Design review → Front-end → Test plan → Functional testing → Bug fixing → Go live
- Workload: Sara 29.5 days, Anas 20 days, Design Studio 13 days – no over-allocation (the Front-end / CMS setup clash is resolved).
- File validated: 0 warnings, no task will move when the site loads it.

To open it: go to https://www.onlinegantt.com/#/gantt → **Open (.gantt file)** → pick `Website Relaunch v2 2026-09-13.gantt`.
