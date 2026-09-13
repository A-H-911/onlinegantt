Done. The updated plan is saved as **Website Relaunch v2 2026-09-13.gantt** (the original v1 file is untouched), with a fit-width chart in **Website Relaunch v2 2026-09-13.png**.

## New finish date

**Go live – الإطلاق is now Sunday 13/12/2026 (17:00)** — previously Tuesday 24/11/2026. That is 13 working days (19 calendar days) later, entirely due to the new QA phase; nothing else moved.

## What changed

1. **New phase 13 "QA – ضمان الجودة"** (25/11 – 13/12, 13 days), inserted after Build and before Go live:
   - 14 Test plan – خطة الاختبار: 3 days, Anas, after Front-end **and** CMS setup (10FS,11FS) → Wed 25/11 – Sun 29/11
   - 15 Functional testing – الاختبار الوظيفي: 6 days, Sara, after Test plan (14FS) → Mon 30/11 – Mon 07/12
   - 16 Bug fixing – إصلاح الأخطاء: 4 days, Sara, after Functional testing (15FS) → Tue 08/12 – Sun 13/12
2. **Go live (id 12)** moved out of the Build phase to a top-level milestone after QA; its predecessor is now Bug fixing (16FS) instead of 10FS,11FS (Front-end and CMS setup still gate it transitively through the Test plan). Date 24/11 → 13/12.
3. **Content audit** set to 100 %. The Discovery phase therefore rolls up to 100 % (was 66.67 %). The "Discovery complete" milestone itself was left at 0 % as you did not ask for it.
4. **CMS setup** reassigned Sara → Anas (100 %). Sara is now only on Front-end during 04/11 – 24/11.

## What stayed the same

- All existing dates and links for Discovery, Design and Build (Build is still 04/11 – 24/11, 15 days, now containing just Front-end and CMS setup).
- Calendar (Sun–Thu, 08–12/13–17, holiday 13–14 Oct), timezone Asia/Riyadh, date/time formats, column layout, zoom, task colours and all task ids (1–12 kept; 13–16 are the new rows).
- All new dates were computed on the plan's own calendar: QA starts the first working day after Front-end finishes (Wed 25/11), skips the Fri/Sat weekends, and there are no holidays in Nov/Dec.

## Decisions I made (no one was available to ask)

- Go live is placed as a **top-level milestone after the QA phase** (rather than nested inside QA), which is the literal reading of "a new phase between Build and the Go-live milestone".
- The direct Front-end/CMS → Go live links were replaced by the single Bug fixing → Go live link, since keeping them would only add redundant arrows across the QA phase; the scheduling constraint is unchanged.
