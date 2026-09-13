# Contributing to onlinegantt

Thanks for improving the skill. The highest-value contributions are **engine rules with proof**
(a behaviour of onlinegantt.com the scheduler does not model yet, with a live dump that shows it),
**interview screens** for conventions the current ones miss, **importers** for other spreadsheet
layouts, **eval prompts**, and **worked examples**.

## Setup

```bash
git clone https://github.com/A-H-911/onlinegantt
cd onlinegantt
python check.py     # everything CI runs - if this is green, you are set up
```

- **Python 3.9+**, standard library only. No pytest, no third-party packages anywhere in the repository;
  Playwright + Chromium is the one optional runtime extra (PNG rendering) and the test that needs it skips
  itself when it is absent.
- `python check.py` is **the one command**: the `tests/` suite, the lint battery (JSON parses, name and
  version agreement across `plugin.json` / `marketplace.json` / `SKILL.md` / `CHANGELOG.md` / `README.md`,
  every file `SKILL.md` lists exists, no dead links in the bundle prose, the interview screens the skill
  relies on are present, the logos are well-formed, no authoring-machine paths leaked), the examples
  rebuilt byte for byte, and the committed eval results re-graded. CI (`.github/workflows/ci.yaml`) runs
  exactly this on Python 3.9–3.13 on Ubuntu and 3.12 on Windows, plus a job that renders the reference
  example to PNG. `python check.py <gate>` runs a subset (`suites`, `lint`, `examples`, `evals`).

## Invariants to preserve

1. **The bundle is self-contained.** Claude Code copies `plugins/onlinegantt/` to a cache on install, so
   everything the skill reads or runs must live inside it, with no outward references. `README.md`,
   `examples/`, `evals/` and `tests/` may point into the bundle; the bundle never points out.
2. **The scripts write the file; the site's engine is the oracle.** A change to the scheduler ships with
   evidence: a spec, the `.gantt` it produces, and rows dumped from the live site
   (`references/site-guide.md` §9.2) that `gantt.py verify` accepts. Extend
   `tests/data/engine-fidelity.spec.json` and its `.engine-rows.json` together.
3. **Nothing is assumed.** A new situation the skill can meet must get an interview screen in
   `references/plan-interview.md` (2–4 options, the recommended one first and labelled, `multiSelect` where
   several apply), not a silent default. Defaults are recommendations the user still confirms.
4. **Never install, never sign up, never overwrite.** The scripts print install commands and stop; the skill
   asks before running them. It never signs the user up for the site's cloud version. Edits produce a new
   version; ids stay stable; the original file is untouched.
5. **Examples are regression fixtures.** `check.py` rebuilds every `examples/*/plan.json` and expects the
   committed `.gantt` byte for byte. If a scheduler change alters an example on purpose, regenerate it with
   the command in `examples/README.md` and say why in the commit.

## Adding an engine rule, end to end

1. Reproduce the behaviour on the site: build a small spec, load the file with the recipe in
   `references/site-guide.md` §9.1, dump the rows (§9.2), run `gantt.py verify` — the `DIFF` lines are the
   rule you are about to add.
2. Implement it in `scripts/ogantt/schedule.py` (or `calendar.py` for working-time arithmetic) and describe
   it in `references/gantt-format.md` §9 "Engine rules on load".
3. Add the task(s) to `tests/data/engine-fidelity.spec.json`, refresh
   `tests/data/engine-fidelity.engine-rows.json` from the site, and add a focused case in
   `tests/test_gantt.py`.
4. If the rule changes what the skill should ask, add or adjust the screen in `plan-interview.md` and the
   one-line pointer in `SKILL.md`.
5. `python check.py` green; note the rule in `CHANGELOG.md` under *Unreleased*.

## Test conventions

- stdlib `unittest` in `tests/test_gantt.py`, runnable with `python -m unittest discover -s tests -v`.
- Fixtures live in `tests/data/`; specs are small and named for what they prove. The engine dump is the only
  fixture that cannot be regenerated offline — date it in its file when you refresh it.
- CLI behaviour (exit codes, file names, what is printed) is tested through `subprocess`, not by importing
  private functions.

## Versioning and releases

`plugin.json` carries the version; the newest `CHANGELOG.md` heading must match it and `README.md` must
mention it (`check.py` enforces all three). Additive changes (a new command flag, a new screen, a new
importer alias) bump MINOR; a change to the spec format, the file naming or the CLI contract bumps MAJOR
with a note on how to migrate. A release is a tag `vX.Y.Z` with a GitHub Release that attaches
`onlinegantt.skill` (the bundle zipped with the `.skill` extension, for hosts that import a packaged skill).

## Before opening a PR

- `python check.py` exits 0.
- New runtime-read files live inside `plugins/onlinegantt/` and add no outward references.
- Conventional commit messages (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` …).
