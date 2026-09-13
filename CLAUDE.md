# Working in this repository

This is the home of the **onlinegantt** skill (`plugins/onlinegantt/`), not a project that uses it.

- `python check.py` is the one gate; run it before claiming anything works. Sub-gates: `suites`, `lint`,
  `examples`, `evals`.
- The bundle must stay self-contained: nothing under `plugins/onlinegantt/` may reference a file outside it.
- The site's engine is the oracle. A scheduler change needs a live dump (`references/site-guide.md` §9.2)
  that `gantt.py verify` accepts; extend `tests/data/engine-fidelity.*` together.
- `examples/*/plan.json` must rebuild byte for byte into the committed `.gantt`; regenerate deliberately
  (`examples/README.md`) when a change is intended.
- Version lives in `plugins/onlinegantt/.claude-plugin/plugin.json`; the newest `CHANGELOG.md` heading and
  the `README.md` meta line must match it.
- Defaults in `references/plan-interview.md` are recommendations shown to the user, never silent choices;
  a new situation gets a screen, not a default.
- Standard library only. Playwright is optional at runtime and never installed by scripts.
