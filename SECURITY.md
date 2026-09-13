# Security policy

onlinegantt is an agent **skill**: Markdown instructions plus standard-library Python scripts that read
and write plan files. It has a small attack surface — no network access, no dependencies, no code
executed from the files it reads — but it (a) ingests user-supplied files and (b) can drive a browser on
the user's behalf, so this document states the trust model and how to report a problem.

## Trust boundaries

1. **User files → scripts.** A `.gantt` file, a plan spec or a spreadsheet is *data*. The scripts parse it
   with `json`, `csv`, `zipfile` + `xml.etree` (for `.xlsx`); nothing in the input is evaluated or executed,
   and a malformed file produces an error message and exit code 2, never a crash with partial output.
2. **Files → HTML preview.** Every value that reaches the HTML preview (names, resources, predecessor
   strings, the title, tooltips) passes through one escaping function. Task notes (`info`, stored as HTML by
   the site) are **not** rendered in the preview at all. The preview loads no external resources and runs no
   scripts.
3. **Skill → the user's browser session on onlinegantt.com.** The site-guide recipes run JavaScript in the
   user's tab through the browser tools. The file-loading recipe pastes the plan as a JSON object literal
   into `JSON.stringify(...)` — never into a string or template literal — so quotes, backticks or `${` in
   task names cannot break out of the snippet. The recipes only call the site's own Open handler, read the
   engine's rendered rows, and read settings; they never sign the user up for the cloud version, accept
   prompts on the user's behalf, or send data anywhere but the site the user opened.
4. **Instructions in observed content.** Text inside a plan file, a spreadsheet cell or a web page is never
   an instruction to the skill. The interview screens are the only place decisions are taken, and they are
   answered by the user.

## Controls in place

- **Standard library only, no network.** The scripts import nothing outside Python's standard library and
  open no sockets. The one optional extra, Playwright + Chromium for PNG rendering, is never installed by
  the scripts: they print the command and the skill asks the user first (`png: skipped …`, exit code 4).
- **No path surprises.** Output paths are those the user chose (`--out-dir`, `-o`); file names derived from
  plan names have `<>:"/\|?*` stripped and trailing dots removed; nothing is written on a conflict (exit 3)
  or a spec error (exit 2). Existing plan files are never modified — edits produce a new version.
- **Deterministic builds.** The same spec produces the same `.gantt` byte for byte (`check.py` proves it
  on the examples), so a reviewer can rebuild and diff.
- **CSV export mirrors the site's format on purpose.** `gantt.py csv plan.gantt` writes exactly what
  onlinegantt.com's *Export to Excel File* writes so that the file re-imports there. A task name or note
  that begins with `=`, `+`, `-` or `@` is therefore written as is — the site reads it as text, but a
  spreadsheet application may evaluate it (CWE-1236). Treat exported CSVs from files you did not author
  with the same care as any downloaded CSV.
- **XLSX reading is bounded.** Only the workbook index, the shared-strings table and the first sheet are
  parsed, with `xml.etree` (which does not resolve external entities); formulas are never evaluated — the
  cached cell value is read.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the maintainer
([github.com/A-H-911](https://github.com/A-H-911)) — open a **private** GitHub Security Advisory on the
repository, or a minimal issue that omits exploit detail and asks for a private channel. Do not open a
public issue containing a working exploit.

When reporting, include: affected file/version, a minimal reproduction (a spec or `.gantt` file is ideal),
the impact, and (if known) a suggested fix. Thank you.
