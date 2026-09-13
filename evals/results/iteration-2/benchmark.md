# Skill benchmark: onlinegantt — iteration 2

**Executor**: Claude subagents launched from a Cowork session (configured model id `claude-fable-5-1`)
**Date**: 2026-09-13
**Evals**: 1, 2, 3, 4 — one run per configuration (`with_skill` / `without_skill`), graded mechanically by `evals/grade.py`

## Summary

| Metric | With skill | Without skill | Delta |
|--------|-----------:|--------------:|------:|
| Pass rate | 100 % (45/45 assertions) | 59 % (26/45) | +41 points |
| Time per eval | 206.7 s (84–442) | 586.8 s (319–831) | −380 s |
| Tokens per eval | 91 345 (78 k–111 k) | 145 395 (89 k–209 k) | −54 050 |

## Per eval

| Eval | With skill | Without skill | What separated them |
|---|---:|---:|---|
| 1 create-from-prose | 15/15 | 8/15 | without the skill: dates written at midnight UTC, holidays and columns in the wrong shape, no PNG, finish date off |
| 2 edit-existing-plan | 10/10 | 10/10 | the reference file acted as a template; both produced a valid v2 |
| 3 spreadsheet-to-plan | 9/9 | 5/9 | without the skill: `Depends on` lags lost, dates one working day off, no image |
| 4 under-specified request (interview) | 11/11 | 3/11 | without the skill: free-text questions or silent assumptions instead of tap-to-select screens with recommendations |

Per-run details (`grading.json`, `timing.json`, `eval_metadata.json` and the text outputs) are in the eval folders next to
this file. PNG images produced during the runs are not committed (the repository is pushed through the GitHub API,
text only); the grader's PNG assertion is therefore skipped when re-checking committed results
(`python3 evals/grade.py evals/results/iteration-2 --check --skip-png`).

## Notes

- New in iteration 2: PNG rendering (every with-skill run produced a 1600 px fit-width image at 2x through the skill's Chromium renderer) and the tap-to-select interview. Eval 4 (under-specified request) is the discriminating test for the interview: with the skill, 11/11 - shortcut screen, plan-specific screens (dates, moving weekend, holidays, team incl. the movers, units, images, location, file name), a 24-row proposal table for the missing durations/owners with one confirm question, the draft + dependency list with one confirm question, then a valid bilingual file. Without the skill: 3/11 - eight generic questions, no proposals/confirm step, and a .gantt file that is not even the site's shape (no 'data'/'resources').
- Eval 1 baseline again produced a file the site would mangle (45 validator errors: date-only strings, non-palette hues, Syncfusion-style settings, non-ISO holidays) after 12.8 minutes of reverse-engineering; the skill run took 2 minutes and is site-verified. Eval 3 baseline this time had no reference file to copy (it was told not to read the workspace) and dropped to 5/9: settings block wrong, 14 validator errors, wrong file name.
- Eval 2 remains non-discriminating (10/10 both): the baseline copies the structure of the plan it is editing, which is realistic. Its PNG came from Pillow with libraqm, ours from Chromium; both pass the >= 1400 px check, so that assertion does not separate quality - the reviewer should compare the two images visually.
- With-skill eval 4 made one judgement call worth a look: to show movers on a Fri-Sat while keeping a Sun-Thu working week (the site has a single calendar per file), it proposed a Sun-Sat calendar with every other weekend blocked as holidays and offered that as the recommended option. It is correct on the site but adds 11 holiday ranges; the reviewer may prefer the alternative it also offered (Thu load / Sun unload).
- Time and tokens: with skill 84-441 s (eval 4 is long because it writes the whole interview) vs 319-831 s without; tokens 78-111k vs 89-209k. Timing variance without the skill stays high.

## Follow-up (iteration 3)

The twelve findings of this iteration were reviewed with the author and turned into rules in
`references/plan-interview.md` and the scripts: work on non-working days is now asked with **no** recommended
option (the two ways of modelling a moving weekend are both legitimate); milestones whose predecessors are all
complete are set to 100 % automatically; progress on tasks that have not started is listed for the user to reset;
spreadsheet ids are renumbered top-down with the mapping shown; a bilingual plan name uses its English half for
the file name. A re-run of eval 4 with the updated skill kept 11/11 (105 933 tokens, 330.9 s).
