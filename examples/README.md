# Examples

Real plans produced by the skill's scripts, kept as regression fixtures: `check.py` rebuilds every
`plan.json` here and expects the committed `.gantt` byte for byte.

| folder | what it shows | built with |
|---|---|---|
| `website-relaunch/` | the reference plan from `plugins/onlinegantt/assets/example-plan.json`: three phases, SS/FF links with lags, a 50 % allocation, progress, one holiday, bilingual names, a `--today` status report | `gantt.py build plan.json --out-dir . --version 1 --png fit,table --today 2026-10-20` |
| `wafi-app-launch/` | a plan written from a prose brief (eval 1): four phases, three milestones, `SS+5 days` overlap, colour by phase, a two-day holiday, `dd/MM/yyyy` dates and weekly zoom | `gantt.py build plan.json --out-dir . --version 1` |
| `office-relocation/` | the interview eval (eval 4): work on a Friday–Saturday moving weekend through `calendar.workOn`, an external party as a resource, 24 tasks across three phases | `gantt.py build plan.json --out-dir . --version 1` |
| `team-plan-from-spreadsheet/` | the spreadsheet path (eval 3): `team_plan.csv` → `gantt.py csv` (renumbered ids, `_id_map`, an ambiguous date flagged) → `build` | `gantt.py csv team_plan.csv -o plan.json` then `build` |

Each folder holds the input spec (`plan.json`), the `.gantt` file the site opens, the self-contained
HTML preview, and `build-output.md` with everything the build printed (summary, critical path, status,
workload). `website-relaunch/` also carries `engine-rows.json` — the rows onlinegantt.com's engine rendered
for that file on 2026-09-13, dumped with the recipe in `references/site-guide.md` §9.2 — and
`verify-output.md`, the `gantt.py verify` result (`VERIFIED`). The PNG images the builds also produced are not committed - this repository is published through
the GitHub API, which carries text only - run the command in the table to regenerate them (Playwright +
Chromium needed for PNG; the HTML preview needs nothing).

To open one on the site: https://www.onlinegantt.com/#/gantt → **Open (.gantt file)** → pick the `.gantt`.
