# Changelog

All notable changes to the onlinegantt skill. The version is the one in
`plugins/onlinegantt/.claude-plugin/plugin.json`; `check.py` refuses a release whose newest heading
here disagrees with it. Format after [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-09-13

First public release. Everything below was built against the free tool at
`https://www.onlinegantt.com/#/gantt` and verified on the live site on 2026-09-13.

### Added

- **The skill bundle** (`plugins/onlinegantt/`): `SKILL.md` with five workflows — create a plan, edit one
  as a new version, answer questions about one, convert and render, operate the site — and the two rules
  that shape every interaction (ask as tap-to-select screens; let the scripts write the file).
- **The interview** (`references/plan-interview.md`): a shortcut screen, calendar / display / content /
  resources / output screens with a recommended option first, a proposal table for missing details, one
  confirm question for the draft, one question per date conflict and per over-allocated person, and the
  situational questions — work on non-working days (no recommendation), vague dates, ambiguous spreadsheet
  dates, progress on unstarted tasks, external parties, Arabic names, colour order, where a milestone goes
  when a phase is inserted, a missing PNG renderer.
- **`scripts/gantt.py`** (standard library only, Python 3.9+): `build`, `validate`, `decompile`,
  `inspect`, `preview` (HTML, and PNG in fit / day / table modes through Playwright + Chromium, never
  installed silently), `csv` (the site's Excel format out; CSV / TSV / XLSX in, with top-down renumbering
  and ambiguous-date detection), `recolor` (by phase / resource / status / clear), `verify` (file vs rows
  dumped from the site's engine), `name`.
- **The scheduler** (`scripts/ogantt/`): working-time snapping, work week and holidays, FS/SS/FF/SF links
  with day- and hour-lags that override dates in both directions, parent roll-up, timezone conversion the
  way the site stores it, `calendar.workOn` (a 7-day week with every other off-day blocked, recomputed each
  build), milestones completed automatically when everything they wait for is done, progress on unstarted
  tasks reported for review, date/dependency conflicts reported with exit code 3 and resolved only on
  instruction (`--on-conflict deps | lag | dates`).
- **References**: the `.gantt` format and engine rules (`gantt-format.md`), the plan spec (`plan-spec.md`),
  the site's CSV format and import rules (`csv-format.md`), the site guide with click-by-click steps and
  browser recipes to load a file through the site's own Open handler and dump the rendered rows
  (`site-guide.md`).
- **Versioned outputs**: `<Plan name> vN YYYY-MM-DD.gantt` with `.html`, `.png` (`… (day scale).png`,
  `… (table).png`) and `.spec.json` beside it; the English half of a bilingual name is used for the file name.
- **Repository**: `tests/` (31 cases including engine fidelity against a live dump), `check.py`,
  CI on Python 3.9–3.13 × Linux / Windows plus a PNG rendering job, `examples/` (four real plans),
  `evals/` (four prompts, the grader, iteration-2 results: 100 % with the skill vs 59 % without),
  the marketplace manifest, logos, `CONTRIBUTING.md`, `SECURITY.md`.

### Changed

- **Logo** redrawn: a rounded tile mark (three bars and an amber milestone), a two-tone wordmark, and the
  tagline and Arabic line outlined from Inter and Noto Sans Arabic (SIL OFL), so the three SVGs render the
  same everywhere instead of depending on installed fonts. `docs/logo/build_logo.py` regenerates them.

### Fixed

- **Windows**: `gantt.py` prints UTF-8 whatever the console code page (a redirected stdout defaulted to
  cp1252 and crashed on the ◆ milestone marker and Arabic names) and `check.py`, the tests and the eval
  grader decode it as such; the DST timezone test is skipped where no IANA database exists, and the
  missing-zone error now also suggests the `tzdata` package.
- CI actions moved to their Node 24 releases (`checkout@v7`, `setup-python@v7`, `upload-artifact@v7`).

[1.0.0]: https://github.com/A-H-911/onlinegantt/releases/tag/v1.0.0
