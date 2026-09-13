#!/usr/bin/env python3
"""The one-command gate for this repository - standard library only.

CI runs exactly `python check.py`, so local and CI cannot drift. Gates run in order and stop
at the first failure with the failing command echoed:

  suites    - tests/ (engine fidelity against a live dump, calendar, links, CSV, CLI exit codes)
  lint      - every *.json parses; plugin.json / marketplace.json / SKILL.md / CHANGELOG / README
              agree on name and version; every file SKILL.md lists exists; no dead relative
              links in the bundle prose; the interview file still carries every screen the
              skill relies on; the logos are well-formed SVG
  examples  - each examples/*/plan.json rebuilds byte-for-byte into its committed .gantt and
              validates with no errors and no drift
  evals     - re-grading the committed eval results reproduces the committed grading

`python check.py <gate> [<gate> ...]` runs a subset.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent
BUNDLE = REPO / "plugins" / "onlinegantt"
GANTT_PY = BUNDLE / "scripts" / "gantt.py"


def fail(reason: str, cmd: list | None = None) -> None:
    print(f"\nCHECK FAILED: {reason}")
    if cmd:
        print(f"reproduce: {' '.join(str(c) for c in cmd)}")
    sys.exit(1)


def run(args: list, expected: int = 0, capture: bool = False) -> str:
    cmd = [sys.executable, *args]
    print(f"$ python {' '.join(str(a) for a in args)}", flush=True)
    p = subprocess.run(cmd, cwd=REPO, capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if p.returncode != expected:
        if capture:
            print(p.stdout, p.stderr)
        fail(f"exit {p.returncode}, expected {expected}", cmd)
    return p.stdout if capture else ""


# ------------------------------------------------------------------ gates

def gate_suites() -> None:
    run(["-m", "unittest", "discover", "-s", "tests"])


def gate_lint() -> None:
    # 1) every JSON file parses (specs, fixtures, eval results, plugin manifests)
    files = [p for p in REPO.rglob("*.json") if ".git" not in p.parts]
    for p in files:
        try:
            json.loads(p.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            fail(f"unparseable JSON: {p.relative_to(REPO)}: {exc}")
    print(f"lint: {len(files)} JSON file(s) parse")

    # 2) name / version agreement across the surfaces users see
    plugin = json.loads((BUNDLE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    skill_head = (BUNDLE / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
    skill_name = re.search(r"^name:\s*(\S+)", skill_head, re.M).group(1)
    entry = next((e for e in market["plugins"] if e["name"] == plugin["name"]), None)
    if entry is None:
        fail(f"marketplace.json has no plugin named {plugin['name']!r}")
    if entry["source"] != "./plugins/onlinegantt" or skill_name != plugin["name"] or market["name"] != plugin["name"]:
        fail(f"name drift: plugin.json={plugin['name']} skill={skill_name} marketplace={market['name']} source={entry['source']}")
    version = plugin["version"]
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    heads = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)
    if not heads or heads[0] != version:
        fail(f"version skew: plugin.json={version} vs newest CHANGELOG release={heads[0] if heads else None}")
    vt = [tuple(int(x) for x in h.split(".")) for h in heads]
    if any(a <= b for a, b in zip(vt, vt[1:])):
        fail("CHANGELOG releases are not newest-first")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    if f"v{version}" not in readme:
        fail(f"README.md does not mention v{version}")
    print(f"lint: plugin/skill/marketplace agree on '{plugin['name']}', v{version} == CHANGELOG == README")

    # 3) every file the SKILL.md table names exists, and no relative link in the bundle prose is dead
    skill_md = (BUNDLE / "SKILL.md").read_text(encoding="utf-8")
    listed = re.findall(r"^\| `([^`]+)` \|", skill_md, re.M)
    missing = [f for f in listed if not (BUNDLE / f).exists()]
    if missing:
        fail(f"SKILL.md lists files that do not exist: {missing}")
    prose = {"SKILL.md": BUNDLE / "SKILL.md"}
    prose.update({f"references/{p.name}": p for p in sorted((BUNDLE / "references").glob("*.md"))})
    token = re.compile(r"\]\(([^)#\s]+?)\)|`((?:scripts|references|assets)/[A-Za-z0-9_./-]+\.(?:md|json|py))`")
    dead = []
    for rel, path in prose.items():
        for m in token.finditer(path.read_text(encoding="utf-8")):
            target = (m.group(1) or m.group(2) or "").split("#")[0]
            if not target or target.startswith(("http", "mailto:")) or "<" in target:
                continue
            if not ((path.parent / target).exists() or (BUNDLE / target).exists() or (REPO / target).exists()):
                dead.append(f"{rel}: {target}")
    if dead:
        fail("dead path references:\n  " + "\n  ".join(dead))
    print(f"lint: {len(listed)} listed files exist; no dead links across {len(prose)} prose files")

    # 4) the interview file carries every screen SKILL.md relies on, and every command SKILL.md
    #    mentions is a real `gantt.py` command
    interview = (BUNDLE / "references" / "plan-interview.md").read_text(encoding="utf-8")
    for needle in ("Screen 0", "Use all recommended values", "Ask me each question", "Timezone", "Working days",
                   "Holidays", "Date format", "Colour scheme", "Allocation units", "Images to produce", "Where to save",
                   "File name", "Missing plan details", "Confirming the draft", "conflict", "over-allocated",
                   "non-working days", "Vague dates", "Ambiguous spreadsheet dates", "PNG renderer missing",
                   "Summary template"):
        if needle not in interview:
            fail(f"plan-interview.md lost the {needle!r} screen that SKILL.md relies on")
    if "(Recommended)" not in interview or "multiSelect" not in interview:
        fail("plan-interview.md no longer describes the (Recommended) / multiSelect convention")
    help_text = run([str(GANTT_PY), "-h"], capture=True)
    commands = set(re.search(r"\{([a-z,]+)\}", help_text).group(1).split(","))
    used = set(re.findall(r"gantt\.py (build|validate|decompile|inspect|preview|csv|recolor|verify|name)\b", skill_md))
    if not used <= commands:
        fail(f"SKILL.md uses commands gantt.py does not have: {sorted(used - commands)}")
    print(f"lint: interview screens present; SKILL.md uses {len(used)} of {len(commands)} real commands")

    # 5) logos are well-formed SVG with the wordmark
    for name in ("logo.svg", "logo-light.svg", "logo-dark.svg"):
        p = BUNDLE / "assets" / name
        try:
            root = ET.fromstring(p.read_text(encoding="utf-8"))
        except ET.ParseError as exc:
            fail(f"{name} is not well-formed SVG: {exc}")
        if not root.tag.endswith("svg") or "onlinegantt" not in p.read_text(encoding="utf-8"):
            fail(f"{name} is not the onlinegantt wordmark")
    print("lint: 3 logo SVGs well-formed")

    # 6) no absolute paths from the authoring machine leaked into the bundle or the evals
    leaked = []
    for p in list(BUNDLE.rglob("*")) + list((REPO / "evals").rglob("*")) + list((REPO / "examples").rglob("*")):
        if p.is_file() and p.suffix in (".md", ".py", ".json", ".gantt", ".csv", ".html", ".svg"):
            if re.search(r"/home/[a-z]+/|C:\\\\Users\\\\", p.read_text(encoding="utf-8", errors="ignore")):
                leaked.append(str(p.relative_to(REPO)))
    if leaked:
        fail("absolute authoring paths leaked into: " + ", ".join(leaked))
    print("lint: no absolute authoring paths in bundle, examples or evals")


def gate_examples() -> None:
    folders = sorted(p for p in (REPO / "examples").iterdir() if p.is_dir())
    if not folders:
        fail("no examples/ folders")
    for folder in folders:
        spec = folder / "plan.json"
        committed = sorted(folder.glob("*.gantt"))
        if not spec.exists() or len(committed) != 1:
            fail(f"{folder.name}: expected plan.json and exactly one .gantt")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rebuilt.gantt"
            run([str(GANTT_PY), "build", str(spec), "-o", str(out), "--no-png", "--no-preview", "--no-spec",
                 "--no-workload", "--on-conflict", "deps"], capture=True)
            if out.read_bytes() != committed[0].read_bytes():
                fail(f"{folder.name}: rebuilding plan.json no longer reproduces {committed[0].name} - "
                     "rebuild the example (see examples/README.md) if the change is intended")
        text = run([str(GANTT_PY), "validate", str(committed[0])], capture=True)
        if "0 task(s) will move on load" not in text:
            fail(f"{folder.name}: the committed file drifts on load:\n{text}")
        print(f"examples: {folder.name}: rebuilt byte-identical, valid, no drift")


def gate_evals() -> None:
    run(["evals/grade.py", "evals/results/iteration-2", "--check", "--skip-png"])


GATES = [
    ("suites", gate_suites),
    ("lint", gate_lint),
    ("examples", gate_examples),
    ("evals", gate_evals),
]


def main(argv: list | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # UTF-8 output on legacy Windows code pages
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    wanted = list(argv if argv is not None else sys.argv[1:])
    names = [name for name, _ in GATES]
    unknown = set(wanted) - set(names)
    if unknown:
        print(f"unknown gate(s) {sorted(unknown)} - choose from: {', '.join(names)}")
        return 2
    for name, gate in GATES:
        if wanted and name not in wanted:
            continue
        print(f"\n=== gate: {name} ===")
        gate()
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
