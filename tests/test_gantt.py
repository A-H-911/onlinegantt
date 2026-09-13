"""Test suite for the onlinegantt skill scripts (standard library only).

Run from the repository root:

    python3 -m unittest discover -s tests -v

The engine-fidelity test compares a file built by the skill with rows dumped from
onlinegantt.com's own scheduling engine (tests/data/engine-fidelity.engine-rows.json,
captured in a browser on 2026-09-13 with the snippet in references/site-guide.md §9.2).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "plugins", "onlinegantt", "scripts")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EXAMPLE = os.path.join(ROOT, "plugins", "onlinegantt", "assets", "example-plan.json")
GANTT_PY = os.path.join(SCRIPTS, "gantt.py")

sys.path.insert(0, SCRIPTS)

from ogantt import csvio, gantt_io, inspect as inspect_mod, png as png_mod, preview, recolor  # noqa: E402
from ogantt.model import SpecError, plan_from_spec  # noqa: E402
from ogantt.schedule import schedule, to_gantt  # noqa: E402
from ogantt.verify import compare  # noqa: E402

sys.path.insert(0, SCRIPTS)
import gantt as cli  # noqa: E402  (the CLI module: versioned_name, _safe_stem)


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def build(spec, on_conflict="deps", today=None):
    """Spec dict -> (gantt doc, ScheduleResult)."""
    plan = plan_from_spec(spec, [])
    res = schedule(plan, on_conflict=on_conflict, today=date.fromisoformat(today) if today else None)
    if res.errors:
        raise SpecError("; ".join(res.errors))
    return to_gantt(plan, res), res


def leaves(doc):
    return {t["TaskID"]: t for t, _, _ in gantt_io.flatten(doc) if not t.get("subtasks")}


def local_day(iso_utc, offset_hours):
    """'2026-11-19T21:00:00.000Z' with UTC+3 -> date(2026, 11, 20)."""
    return (datetime.strptime(iso_utc[:19], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=offset_hours)).date()


def run_cli(*args, cwd=None):
    return subprocess.run([sys.executable, GANTT_PY, *args], capture_output=True, text=True, cwd=cwd)


class EngineFidelity(unittest.TestCase):
    """The scheduler must reproduce the site's engine field for field."""

    def test_matches_live_engine_dump(self):
        doc, _ = build(load(os.path.join(DATA, "engine-fidelity.spec.json")))
        report, ok = compare.report(doc, load(os.path.join(DATA, "engine-fidelity.engine-rows.json")))
        self.assertTrue(ok, report)
        self.assertTrue(report.startswith("VERIFIED"))

    def test_links_override_dates_and_snap_to_working_time(self):
        doc, res = build(load(os.path.join(DATA, "engine-fidelity.spec.json")))
        t = leaves(doc)
        # 2 'B slack' asked for 19 Oct, the FS link from task 1 (ends Fri 9 Oct) puts it on Mon 12 Oct 08:00 local
        self.assertEqual(t[2]["StartDate"], "2026-10-12T05:00:00.000Z")
        self.assertEqual([m["id"] for m in res.moved], [2])
        # 15 'Weekend start' asked for Saturday 17 Oct -> Monday 19 Oct
        self.assertEqual(t[15]["StartDate"], "2026-10-19T05:00:00.000Z")
        # hour lag: 1FS+4 hours -> 12 Oct 13:00 local (lunch 12-13 skipped)
        self.assertEqual(t[6]["StartDate"], "2026-10-12T10:00:00.000Z")
        # milestone
        self.assertEqual(t[16]["Duration"], 0)
        self.assertEqual(t[16]["Predecessor"], "13FS")

    def test_file_shape(self):
        doc, _ = build(load(EXAMPLE))
        self.assertEqual(sorted(doc), ["advanced", "data", "projectEndDate", "projectStartDate", "resources"])
        self.assertIsNone(doc["projectStartDate"])
        adv = doc["advanced"]
        self.assertEqual(len(adv["columns"]), 10)
        self.assertEqual(adv["timezone"], "Asia/Riyadh")
        self.assertEqual(adv["timezoneOffset"], -180)
        for t, _, parent in gantt_io.flatten(doc):
            if t.get("subtasks"):
                self.assertIsNone(t["Predecessor"], "parents never carry links")
            else:
                self.assertNotIn("subtasks", t, "the site strips empty subtasks arrays")
        text = gantt_io.dump_gantt(doc)
        self.assertNotIn('"subtasks":[]', text)
        self.assertNotIn("\n", text.strip(), "compact JSON like the site writes")


class Calendar(unittest.TestCase):
    def test_timezone_shifts_utc_timestamps(self):
        spec = load(os.path.join(DATA, "engine-fidelity.spec.json"))
        riyadh, _ = build(spec)
        spec["calendar"]["timezone"] = "Europe/London"  # BST in October: UTC+1
        london, _ = build(spec)
        self.assertEqual(leaves(riyadh)[1]["StartDate"], "2026-10-05T05:00:00.000Z")
        self.assertEqual(leaves(london)[1]["StartDate"], "2026-10-05T07:00:00.000Z")
        self.assertEqual(london["advanced"]["timezoneOffset"], -60)

    def test_holidays_are_skipped(self):
        spec = load(os.path.join(DATA, "engine-fidelity.spec.json"))
        spec["calendar"]["holidays"] = [{"from": "2026-10-06", "to": "2026-10-07", "name": "Break"}]
        doc, _ = build(spec)
        t = leaves(doc)
        # 5 working days from Mon 5 Oct with Tue+Wed blocked -> ends Tue 13 Oct 17:00
        self.assertEqual(t[1]["EndDate"], "2026-10-13T14:00:00.000Z")
        self.assertEqual(doc["advanced"]["holidays"][0]["from"], "2026-10-05T21:00:00.000Z")

    def test_work_on_off_days(self):
        doc, res = build(load(os.path.join(DATA, "workon.spec.json")))
        adv = doc["advanced"]
        self.assertEqual(len(adv["workWeek"]), 7, "7-day week when specific off-days are worked")
        blocked = set()
        for h in adv["holidays"]:  # stored as local midnight -> UTC (Riyadh = UTC+3), inclusive ranges
            d0 = local_day(h["from"], 3)
            d1 = local_day(h["to"], 3)
            while d0 <= d1:
                blocked.add(d0.isoformat())
                d0 += timedelta(days=1)
        t = leaves(doc)
        self.assertEqual(t[7]["StartDate"][:10], "2026-12-04", "Friday move day kept")
        self.assertEqual(t[8]["StartDate"][:10], "2026-12-05", "Saturday unload kept")
        self.assertNotIn("2026-12-04", blocked)
        self.assertNotIn("2026-12-05", blocked)
        self.assertNotIn("2026-12-03", blocked)  # Thursday is a normal working day
        self.assertIn("2026-11-20", blocked)      # every other Friday / Saturday is blocked
        self.assertIn("2026-11-21", blocked)
        self.assertIn("2026-12-11", blocked)
        self.assertTrue(any("calendar" in n.lower() or "off-day" in n.lower() or "7-day" in n.lower() for n in res.notes), res.notes)

    def test_week_means_five_working_days(self):
        spec = {"name": "W", "start": "2026-10-04", "calendar": {"timezone": "Asia/Riyadh"},
                "tasks": [{"id": 1, "name": "a", "duration": "1 week"}]}
        doc, _ = build(spec)
        self.assertEqual(leaves(doc)[1]["Duration"], 5)


class Scheduling(unittest.TestCase):
    def test_parent_rollup(self):
        doc, _ = build(load(EXAMPLE))
        rows = {t["TaskID"]: t for t, _, _ in gantt_io.flatten(doc)}
        phase = rows[1]
        kids = [rows[c["TaskID"]] for c in phase["subtasks"]]
        self.assertEqual(phase["StartDate"], min(k["StartDate"] for k in kids))
        self.assertEqual(phase["EndDate"], max(k["EndDate"] for k in kids))
        self.assertIsNone(phase["Predecessor"])

    def test_conflict_is_reported_not_silently_fixed(self):
        plan = plan_from_spec(load(os.path.join(DATA, "engine-fidelity.spec.json")), [])
        res = schedule(plan, on_conflict="ask")
        self.assertEqual([c["id"] for c in res.conflicts], [2])
        self.assertEqual(res.conflicts[0]["governing"], "1FS")

    def test_conflict_lag_keeps_the_date(self):
        doc, res = build(load(os.path.join(DATA, "engine-fidelity.spec.json")), on_conflict="lag")
        t = leaves(doc)
        self.assertEqual(t[2]["StartDate"][:10], "2026-10-19")
        self.assertEqual(t[2]["Predecessor"], "1FS+5 days")

    def test_conflict_dates_drops_the_link(self):
        doc, _ = build(load(os.path.join(DATA, "engine-fidelity.spec.json")), on_conflict="dates")
        t = leaves(doc)
        self.assertEqual(t[2]["StartDate"][:10], "2026-10-19")
        self.assertIn(t[2]["Predecessor"], (None, ""))

    def test_milestone_completes_when_predecessors_done(self):
        doc, res = build(load(os.path.join(DATA, "workon.spec.json")))
        self.assertEqual(leaves(doc)[5]["Progress"], 100)
        self.assertTrue(any("milestone" in n.lower() for n in res.notes), res.notes)

    def test_future_progress_flagged_for_review(self):
        spec = {"name": "P", "start": "2026-10-04", "calendar": {"timezone": "Asia/Riyadh"},
                "tasks": [{"id": 1, "name": "later", "start": "2026-12-01", "duration": 2, "progress": 40}]}
        _, res = build(spec, today="2026-10-04")
        self.assertEqual(len(res.review), 1)
        self.assertIn("later", res.review[0])

    def test_spec_errors_name_the_problem(self):
        spec = load(os.path.join(DATA, "bad.spec.json"))
        plan = plan_from_spec(spec, [])
        res = schedule(plan, on_conflict="deps")
        joined = "\n".join(res.errors)
        self.assertEqual(len(res.errors), 3, joined)
        self.assertIn("is a parent (has children) but has dependencies", joined)
        self.assertIn("which is a parent", joined)
        self.assertIn("unknown task id 9", joined)

    def test_dependency_cycle(self):
        spec = {"name": "Cyc", "start": "2026-10-04", "calendar": {"timezone": "Asia/Riyadh"},
                "tasks": [{"id": 5, "name": "cyc1", "duration": 1, "deps": "6FS"},
                          {"id": 6, "name": "cyc2", "duration": 1, "deps": "5FS"}]}
        res = schedule(plan_from_spec(spec, []), on_conflict="deps")
        self.assertEqual(len(res.errors), 1)
        self.assertIn("Dependency cycle involving: 5 'cyc1', 6 'cyc2'", res.errors[0])

    def test_resources_declared_automatically(self):
        doc, _ = build(load(EXAMPLE))
        declared = {r["resourceName"] for r in doc["resources"]}
        used = {r["resourceName"] for t, _, _ in gantt_io.flatten(doc) for r in t.get("resources", []) or []}
        self.assertTrue(used <= declared, used - declared)
        for t, _, _ in gantt_io.flatten(doc):
            for r in t.get("resources", []) or []:
                self.assertEqual(set(r), {"resourceId", "resourceName", "unit"})


class RoundTrip(unittest.TestCase):
    def test_decompile_then_build_is_stable(self):
        doc1, _ = build(load(EXAMPLE))
        spec2 = gantt_io.to_spec(doc1, name="Website Relaunch")
        doc2, _ = build(spec2)
        for tid, t in leaves(doc1).items():
            u = leaves(doc2)[tid]
            for k in ("TaskName", "StartDate", "EndDate", "Duration", "DurationUnit", "Progress", "color"):
                self.assertEqual(t[k], u[k], f"task {tid} {k}")
            self.assertEqual(compare.expected_rows(doc1), compare.expected_rows(doc2))

    def test_validate_accepts_built_file_and_rejects_broken_one(self):
        doc, _ = build(load(EXAMPLE))
        errors, _ = gantt_io.validate(doc)
        self.assertEqual(errors, [])
        self.assertEqual(compare.drift(doc), [])
        broken = gantt_io.load_gantt(os.path.join(DATA, "broken.gantt"))
        errors, warnings = gantt_io.validate(broken)
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("parent" in e for e in errors))
        self.assertTrue(any("resource" in e for e in errors))
        self.assertTrue(any("dateFormat" in e for e in errors))
        self.assertTrue(compare.drift(broken), "a hand-edited date the engine will move")


class Csv(unittest.TestCase):
    def test_export_matches_site_format(self):
        doc, _ = build(load(EXAMPLE))
        text = csvio.export_csv(doc)
        lines = text.split("\r\n")
        self.assertEqual(lines[0], "Outline Level,ID,Name,Start,Finish,Duration,% Complete,Predecessors,Resource Names,Color,Notes")
        self.assertTrue(lines[1].startswith("1,1,"))
        self.assertIn("2SS+1 day", text)
        self.assertIn(" day,", lines[2])

    def test_import_spreadsheet(self):
        spec = csvio.import_table(os.path.join(DATA, "team_plan.csv"), name="Team plan")
        phases = spec["tasks"]
        self.assertEqual([p["name"] for p in phases], ["Planning", "Delivery"])
        kick = phases[0]["children"][0]
        self.assertEqual(kick["id"], 2, "renumbered top-down: phase 1, first task 2")
        self.assertEqual(kick["resources"], ["Anas"])
        self.assertEqual(kick["progress"], 100)
        self.assertEqual(spec["_id_map"]["1"], 2)
        self.assertIn("05/10/2026", spec["_ambiguous_dates"])
        self.assertEqual(kick["start"], "2026-10-05")  # day-first by default
        uat = phases[1]["children"][1]
        self.assertTrue(uat["deps"].startswith(str(phases[1]["children"][0]["id"])), uat["deps"])
        self.assertIn("FS+2 days", uat["deps"])
        signoff = phases[0]["children"][2]
        self.assertTrue(signoff.get("milestone"))
        self.assertEqual(sorted(phases[0]["children"][1]["resources"]), ["Anas", "Sara"])
        doc, _ = build(spec)  # the imported spec must build
        self.assertEqual(len(leaves(doc)), 5)

    def test_import_month_first_and_keep_ids(self):
        spec = csvio.import_table(os.path.join(DATA, "team_plan.csv"), month_first=True, renumber=False)
        self.assertEqual(spec["tasks"][0]["children"][0]["start"], "2026-05-10")
        self.assertEqual(spec["tasks"][0]["children"][0]["id"], 1)
        self.assertNotIn("_id_map", spec)


class Outputs(unittest.TestCase):
    def test_inspect_summary(self):
        doc, _ = build(load(EXAMPLE))
        text = inspect_mod.summary(doc, today="2026-10-20")
        for needle in ("## Plan summary", "## Critical path", "## Status as of 2026-10-20", "## Workload", "Over-allocation"):
            self.assertIn(needle, text)
        self.assertIn("Sara", text)

    def test_recolor_by_phase_then_status(self):
        doc, _ = build(load(EXAMPLE))
        n = recolor.apply(doc, ["phase"])
        self.assertGreater(n, 0)
        hues = {t["color"] for t in leaves(doc).values()}
        self.assertTrue(hues <= {"", "31", "61", "91", "121", "151", "181", "211", "241", "271", "301", "331"})
        recolor.apply(doc, ["status"], today="2026-10-20")
        self.assertEqual(leaves(doc)[2]["color"], "121", "done -> green")
        recolor.apply(doc, ["clear"])
        self.assertEqual({t["color"] for t in leaves(doc).values()}, {""})

    def test_html_preview(self):
        doc, _ = build(load(EXAMPLE))
        html = preview.render(doc, title="Website Relaunch", today="2026-10-20")
        self.assertIn("<html", html.lower())
        self.assertIn("Wireframes", html)
        self.assertNotIn("<script src=", html, "self-contained: no external resources")
        for mode in ("fit", "day", "table"):
            self.assertIn("Wireframes", preview.render(doc, title="x", mode=mode, for_image=True))

    def test_png_renderer_is_never_installed_silently(self):
        ok, msg = png_mod.availability()
        if not ok:
            self.assertIn("playwright", msg.lower())
            self.skipTest("Playwright/Chromium not installed - PNG rendering skipped: " + msg)
        doc, _ = build(load(EXAMPLE))
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.png")
            good, _ = png_mod.render_png(preview.render(doc, title="x", for_image=True), out, scale=1, width=1200)
            self.assertTrue(good)
            with open(out, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")


class Naming(unittest.TestCase):
    def test_versioned_name(self):
        self.assertEqual(cli.versioned_name("Website Relaunch – إعادة إطلاق الموقع", 2, date(2026, 9, 13)),
                         "Website Relaunch v2 2026-09-13.gantt")
        self.assertEqual(cli.versioned_name('Q4: "Launch"/plan?', 1, date(2026, 9, 13)), "Q4 Launchplan v1 2026-09-13.gantt")
        self.assertEqual(cli._safe_stem("مخطط عربي فقط"), "مخطط عربي فقط")
        self.assertEqual(cli.versioned_name("Plan", 3, date(2026, 1, 2), ext=".png"), "Plan v3 2026-01-02.png")


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ogantt-test-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_build_stops_on_conflict_then_builds(self):
        spec = os.path.join(DATA, "engine-fidelity.spec.json")
        r = run_cli("build", spec, "--out-dir", self.dir, "--no-png")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("CONFLICTS", r.stdout)
        self.assertEqual(os.listdir(self.dir), [], "nothing written on a conflict")
        r = run_cli("build", spec, "--out-dir", self.dir, "--no-png", "--on-conflict", "deps", "--version", "2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        names = sorted(os.listdir(self.dir))
        today = date.today().isoformat()
        self.assertEqual(names, [f"Engine fidelity test v2 {today}.gantt", f"Engine fidelity test v2 {today}.html",
                                 f"Engine fidelity test v2 {today}.spec.json"])
        self.assertIn("## Critical path", r.stdout)

    def test_validate_exit_codes(self):
        self.assertEqual(run_cli("validate", os.path.join(DATA, "broken.gantt")).returncode, 2)
        out = os.path.join(self.dir, "ok.gantt")
        self.assertEqual(run_cli("build", EXAMPLE, "-o", out, "--no-png", "--no-preview", "--no-spec").returncode, 0)
        r = run_cli("validate", out)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("OK - valid .gantt", r.stdout)

    def test_verify_and_decompile_and_csv(self):
        out = os.path.join(self.dir, "ef.gantt")
        run_cli("build", os.path.join(DATA, "engine-fidelity.spec.json"), "-o", out, "--no-png", "--no-preview",
                "--no-spec", "--on-conflict", "deps")
        r = run_cli("verify", out, os.path.join(DATA, "engine-fidelity.engine-rows.json"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(r.stdout.startswith("VERIFIED"))
        spec_out = os.path.join(self.dir, "plan.json")
        self.assertEqual(run_cli("decompile", out, "-o", spec_out, "--name", "EF").returncode, 0)
        self.assertEqual(load(spec_out)["name"], "EF")
        csv_out = os.path.join(self.dir, "plan.csv")
        self.assertEqual(run_cli("csv", out, "-o", csv_out).returncode, 0)
        with open(csv_out, encoding="utf-8") as f:
            self.assertTrue(f.readline().startswith("Outline Level,ID,Name"))
        r = run_cli("csv", os.path.join(DATA, "team_plan.csv"), "-o", os.path.join(self.dir, "team.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("review: ambiguous dates", r.stdout)
        self.assertIn("renumbered", r.stdout)

    def test_name_command(self):
        r = run_cli("name", "Office move – انتقال المكتب", "4", "--date", "2026-09-13")
        self.assertEqual(r.stdout.strip(), "Office move v4 2026-09-13.gantt")

    def test_preview_png_exit_code_without_renderer(self):
        out = os.path.join(self.dir, "ok.gantt")
        run_cli("build", EXAMPLE, "-o", out, "--no-png", "--no-preview", "--no-spec")
        r = run_cli("preview", out, "--png", "fit")
        ok, _ = png_mod.availability()
        self.assertEqual(r.returncode, 0 if ok else 4, r.stdout + r.stderr)
        if not ok:
            self.assertIn("Ask the user before installing", r.stdout)


if __name__ == "__main__":
    unittest.main()
