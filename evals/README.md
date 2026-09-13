# Evals

How the skill is measured. Four prompts, each run once with the skill installed and once without,
outputs graded mechanically.

| file | purpose |
|---|---|
| `evals.json` | the four prompts with their expected outcomes (ids 1–4) |
| `inputs/` | files the prompts refer to: the v1 plan that eval 2 edits, the spreadsheet eval 3 imports |
| `grade.py` | checks every assertion against the produced files (`.gantt`, `answer.md`, PNG) and writes `grading.json` per run |
| `results/iteration-2/` | the latest full run: `benchmark.md` (summary), `benchmark.json`, and per eval `with_skill/run-1` and `without_skill/run-1` with `outputs/`, `grading.json`, `timing.json`, `eval_metadata.json` |

## The four prompts

1. **create-from-prose** – a fully specified brief (phases, durations, owners, links, calendar, settings, colour scheme);
   checks the file shape, the calendar arithmetic, an `SS+5 days` overlap, bilingual names, the finish date and the PNG.
2. **edit-existing-plan** – add a QA phase to `inputs/Website Relaunch v1 2026-09-13.gantt`, re-link go-live, change
   progress and an assignment; checks that ids, names, dates and settings of untouched tasks survive and that the
   original file is not modified.
3. **spreadsheet-to-plan** – `inputs/team_plan.csv` with a `Depends on` column and a `05/10/2026` date; checks
   hierarchy, links with lag, resources, calendar/settings and the exact UTC timestamps.
4. **under-specified request** – "make a plan for our office move" with nobody available; checks that the interview
   is run as tap-to-select screens (shortcut, plan-specific questions, proposal table, draft confirmation) and that a
   valid file is built from the recommended answers.

## Running

Reproduce a run by giving the prompt in `evals.json` to Claude (Cowork or Claude Code) with the skill installed,
saving what it produced into `results/<iteration>/eval-N-<name>/with_skill/run-1/outputs/` (the `.gantt`, images,
and the final reply as `answer.md`), and grading:

```
python3 evals/grade.py results/<iteration>            # writes grading.json next to each outputs folder
python3 evals/grade.py results/iteration-2 --check --skip-png   # what check.py runs: re-grade the committed results
```

`--skip-png` exists because the committed results carry no binaries (pushed through the GitHub API); the runs'
HTML previews are not committed either (the with-skill ones are in `examples/`). Assertion texts are the
contract: `evals.json` lists them per eval and `grade.py` implements each one.
