#!/usr/bin/env python3
"""Programmatic grader for the onlinegantt evals (standard library only).

    python3 evals/grade.py <results-dir> [--check] [--skip-png]

<results-dir> holds one folder per eval (evals/evals.json ids and names), each with
with_skill/run-1/outputs and without_skill/run-1/outputs. Every assertion is checked
mechanically against the files the run produced (the .gantt, answer.md, the PNG) and
grading.json is written next to each outputs folder.

--check    do not write; compare with the committed grading.json and exit 1 on any change
--skip-png ignore the PNG assertion (the committed results carry no binaries)
"""
import glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SK = os.path.join(REPO, "plugins", "onlinegantt", "scripts", "gantt.py")
ORIG = os.path.join(HERE, "inputs", "Website Relaunch v1 2026-09-13.gantt")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
FLAGS = {a for a in sys.argv[1:] if a.startswith("--")}
W = ARGS[0] if ARGS else os.path.join(HERE, "results", "iteration-2")
CHECK = "--check" in FLAGS
ORIG_MD5 = "d3e830a8fb5075de75d278d8dc13539d"  # the input file the eval-2 prompt must leave untouched
SKIP_PNG = "--skip-png" in FLAGS
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$")
AR = re.compile(r"[؀-ۿ]")


def flat(ts):
    for t in ts:
        yield t
        yield from flat(t.get("subtasks") or [])


def load(outdir):
    files = sorted(glob.glob(os.path.join(outdir, "*.gantt")))
    if not files:
        return None, None, None
    f = files[0]
    try:
        d = json.load(open(f, encoding="utf-8-sig"))
    except Exception as e:
        return f, None, str(e)
    return f, d, None


def validate(f):
    p = subprocess.run([sys.executable, SK, "validate", f], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, p.stdout + p.stderr


def answer(outdir):
    p = os.path.join(outdir, "answer.md")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def by_name(d, needle):
    for t in flat(d["data"]):
        if needle.lower() in t.get("TaskName", "").lower():
            return t
    return None


def preds(t):
    return (t.get("Predecessor") or "").replace(" ", "").upper()


def grade_eval1(outdir):
    f, d, err = load(outdir)
    ans = answer(outdir)
    E = []
    def add(text, ok, ev): E.append({"text": text, "passed": bool(ok), "evidence": ev})
    add("A .gantt file exists and is JSON with data/resources/advanced", bool(d) and all(k in d for k in ("data", "resources", "advanced")), f or err or "no file")
    if not d:
        return E
    rc, out = validate(f)
    nerr = len([l for l in out.splitlines() if l.startswith("error")])
    add("Skill validator reports 0 errors (site would load it unchanged)", rc == 0 and nerr == 0, out.strip().splitlines()[-1] if out else "")
    tasks = list(flat(d["data"]))
    add("All StartDate/EndDate are UTC ISO strings with time (…T05:00:00.000Z)", all(ISO.match(str(t.get("StartDate", ""))) and ISO.match(str(t.get("EndDate", ""))) for t in tasks), str([t.get("StartDate") for t in tasks[:3]]))
    a = d["advanced"]
    add("Calendar: Sun–Thu work week, Asia/Riyadh, 8-12/13-17", a.get("workWeek") == ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"] and a.get("timezone") == "Asia/Riyadh" and a.get("workTime") == [{"from": 8, "to": 12}, {"from": 13, "to": 17}], json.dumps({k: a.get(k) for k in ("workWeek", "timezone", "workTime")}))
    add("Settings: dateFormat dd/MM/yyyy, firstDayOfWeek 0, zoomLevel 1", a.get("dateFormat") == "dd/MM/yyyy" and a.get("firstDayOfWeek") == 0 and a.get("zoomLevel") == 1, json.dumps({k: a.get(k) for k in ("dateFormat", "firstDayOfWeek", "zoomLevel")}))
    cols = a.get("columns") or []
    shown = [c.get("name") for c in cols if isinstance(c, dict) and c.get("show") is True]
    add("advanced.columns uses the site's 10 {name,width,show} entries with ID/Task Name/Start/End/Resources shown", len(cols) == 10 and all(set(c) >= {"name", "width", "show"} for c in cols) and set(shown) == {"Task ID", "Task Name", "Start Date", "End Date", "Resources"}, str(shown))
    hol = a.get("holidays") or []
    add("Holidays 22–23 Nov stored as ISO from/to", len(hol) == 1 and ISO.match(str(hol[0].get("from", ""))) and "2026-11-2" in hol[0]["from"], json.dumps(hol))
    parents = [t for t in tasks if t.get("subtasks")]
    ms = [t for t in tasks if not t.get("subtasks") and t.get("Duration") == 0]
    leaves = [t for t in tasks if not t.get("subtasks")]
    add("Structure: 4 phases, 3 milestones, 9 work tasks; parents have Predecessor null", len(parents) == 4 and len(ms) == 3 and len(leaves) == 12 and all(p.get("Predecessor") in (None, "") for p in parents), f"phases={len(parents)} milestones={len(ms)} leaves={len(leaves)}")
    mob, be, it = by_name(d, "mobile app"), by_name(d, "backend"), by_name(d, "integration")
    add("Mobile app starts 5 working days after Backend starts (SS+5 days link) and integration testing depends on both", bool(mob and be and it) and f"{be['TaskID']}SS+5DAYS" in preds(mob) and str(be["TaskID"]) in preds(it) and str(mob["TaskID"]) in preds(it), f"mobile={preds(mob) if mob else None} integration={preds(it) if it else None}")
    res = {r.get("resourceId") for r in d["resources"]}
    used = {r.get("resourceId") for t in tasks for r in (t.get("resources") or [])}
    add("Resources Anas/Sara/Layla/Omar declared and every assignment references a declared resource", {"Anas", "Sara", "Layla", "Omar"} <= res and used <= res, f"declared={sorted(res)} used={sorted(used)}")
    add("Task names are bilingual (Arabic script and an en dash)", all(AR.search(t["TaskName"]) and "–" in t["TaskName"] for t in tasks), tasks[1]["TaskName"])
    pal = {"", "31", "61", "91", "121", "151", "181", "211", "241", "271", "301", "331"}
    phase_colours = [{c.get("color") for c in flat([p]) if not c.get("subtasks")} for p in parents]
    add("Colours are palette hues and differ per phase", all(str(t.get("color", "")) in pal for t in tasks) and len({tuple(sorted(s)) for s in phase_colours}) == len(parents), str(phase_colours))
    add("File name follows '<Plan> v1 2026-09-13.gantt'", bool(re.search(r" v1 2026-09-13\.gantt$", os.path.basename(f))), os.path.basename(f))
    add("Answer states finish 7 Feb 2027, a critical path, and no over-allocation", bool(re.search(r"07/02/2027|7 Feb(ruary)? 2027|2027-02-07", ans)) and "critical" in ans.lower() and re.search(r"no over-?allocat|not over-?allocat|nobody is over|no one is over|over-?allocation:? none|nobody exceeds 100", ans, re.I) is not None, ans[:300].replace("\n", " "))
    ok, ev = png_check(outdir)
    add("A fit-width PNG of the chart was produced (>= 1400 px wide)", ok, ev)
    return E


def grade_eval2(outdir):
    f, d, err = load(outdir)
    ans = answer(outdir)
    E = []
    def add(text, ok, ev): E.append({"text": text, "passed": bool(ok), "evidence": ev})
    add("Output is 'Website Relaunch v2 2026-09-13.gantt' and the original file is untouched", bool(f) and os.path.basename(f) == "Website Relaunch v2 2026-09-13.gantt" and hashlib.md5(open(ORIG, "rb").read()).hexdigest() == ORIG_MD5, (os.path.basename(f) if f else "no file"))
    if not d:
        return E
    rc, out = validate(f)
    nerr = len([l for l in out.splitlines() if l.startswith("error")])
    drift = len([l for l in out.splitlines() if l.startswith("drift")])
    add("Skill validator: 0 errors and 0 tasks drift on load", rc == 0 and nerr == 0 and drift == 0, out.strip().splitlines()[-1] if out else "")
    qa = by_name(d, "QA")
    tp, ft, bf, go = by_name(d, "Test plan"), by_name(d, "Functional testing"), by_name(d, "Bug fixing"), by_name(d, "Go live")
    add("QA phase with Test plan (3d Anas), Functional testing (6d Sara), Bug fixing (4d Sara)", bool(qa and tp and ft and bf) and tp.get("Duration") == 3 and ft.get("Duration") == 6 and bf.get("Duration") == 4 and [r["resourceId"] for r in tp["resources"]] == ["Anas"] and [r["resourceId"] for r in ft["resources"]] == ["Sara"] and [r["resourceId"] for r in bf["resources"]] == ["Sara"] and all(x in (qa.get("subtasks") or []) for x in (tp, ft, bf)), f"qa children={[t['TaskName'] for t in (qa.get('subtasks') or [])] if qa else None}")
    add("Links: Test plan after 10FS,11FS; Functional → Test plan; Bug fixing → Functional; Go live → Bug fixing", bool(tp and ft and bf and go) and {"10FS", "11FS"} <= set(preds(tp).split(",")) and preds(ft) == f"{tp['TaskID']}FS" and preds(bf) == f"{ft['TaskID']}FS" and preds(go) == f"{bf['TaskID']}FS", f"tp={preds(tp) if tp else None} ft={preds(ft) if ft else None} bf={preds(bf) if bf else None} go={preds(go) if go else None}")
    ca = by_name(d, "Content audit")
    add("Content audit progress is 100", bool(ca) and ca.get("Progress") == 100, str(ca.get("Progress") if ca else None))
    cms = by_name(d, "CMS setup")
    add("CMS setup reassigned to Anas", bool(cms) and [r["resourceId"] for r in cms["resources"]] == ["Anas"], str(cms.get("resources") if cms else None))
    o = json.load(open(ORIG, encoding="utf-8-sig"))
    add("advanced settings identical to v1", d.get("advanced") == o.get("advanced"), "same" if d.get("advanced") == o.get("advanced") else "differs")
    od = {t["TaskID"]: t for t in flat(o["data"])}
    nd = {t["TaskID"]: t for t in flat(d["data"])}
    same_dates = all(nd.get(i) and nd[i]["StartDate"] == od[i]["StartDate"] and nd[i]["EndDate"] == od[i]["EndDate"] and nd[i]["TaskName"] == od[i]["TaskName"] and nd[i].get("color") == od[i].get("color") for i in range(1, 12) if i in od and not od[i].get("subtasks") and i != 12)
    add("Existing tasks 1–11 keep their ids, names, colours and dates", same_dates, "unchanged" if same_dates else "changed")
    add("Answer states the new finish date 13 Dec 2026", bool(re.search(r"13 Dec|2026-12-13|13/12/2026|Dec(ember)? 13", ans)), ans[:200].replace("\n", " "))
    ok, ev = png_check(outdir)
    add("A fit-width PNG of the chart was produced (>= 1400 px wide)", ok, ev)
    return E


def grade_eval3(outdir):
    f, d, err = load(outdir)
    ans = answer(outdir)
    E = []
    def add(text, ok, ev): E.append({"text": text, "passed": bool(ok), "evidence": ev})
    add("File 'Team Plan v1 2026-09-13.gantt' exists and is JSON with data/resources/advanced", bool(d) and os.path.basename(f) == "Team Plan v1 2026-09-13.gantt", f or err or "no file")
    if not d:
        return E
    rc, out = validate(f)
    nerr = len([l for l in out.splitlines() if l.startswith("error")])
    add("Skill validator reports 0 errors", rc == 0 and nerr == 0, out.strip().splitlines()[-1] if out else "")
    tasks = list(flat(d["data"]))
    parents = [t["TaskName"] for t in tasks if t.get("subtasks")]
    so = by_name(d, "Sign-off")
    add("Two phases (Planning, Delivery) and Sign-off is a milestone", sorted(parents) == ["Delivery", "Planning"] and so is not None and so.get("Duration") == 0, f"phases={parents} signoff={so.get('Duration') if so else None}")
    ko, rw, bu, ua = by_name(d, "Kickoff"), by_name(d, "Requirements"), by_name(d, "Build"), by_name(d, "UAT")
    ok_links = bool(ko and rw and so and bu and ua) and preds(rw) == f"{ko['TaskID']}FS" and preds(so) == f"{rw['TaskID']}FS" and preds(bu) == f"{so['TaskID']}FS" and preds(ua) == f"{bu['TaskID']}FS+2DAYS"
    add("Dependencies from the 'Depends on' column resolve to the right tasks incl. the +2 days lag", ok_links, f"rw={preds(rw) if rw else None} so={preds(so) if so else None} bu={preds(bu) if bu else None} ua={preds(ua) if ua else None}")
    res = {r.get("resourceId") for r in d["resources"]}
    add("Resources Anas and Sara declared; Requirements workshop has both", res == {"Anas", "Sara"} and rw is not None and {r["resourceId"] for r in rw["resources"]} == {"Anas", "Sara"}, f"declared={sorted(res)}")
    a = d["advanced"]
    shown = [c.get("name") for c in (a.get("columns") or []) if isinstance(c, dict) and c.get("show") is True]
    add("Calendar/settings as requested (Sun–Thu, Riyadh, yyyy-MM-dd, zoom 0, only ID+Name shown)", a.get("workWeek") == ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"] and a.get("timezone") == "Asia/Riyadh" and a.get("dateFormat") == "yyyy-MM-dd" and a.get("zoomLevel") == 0 and shown == ["Task ID", "Task Name"], json.dumps({"ww": a.get("workWeek"), "shown": shown, "zoom": a.get("zoomLevel")}))
    add("Dates: Kickoff on 2026-10-05 08:00 Riyadh, UAT ends 2026-11-02 17:00", bool(ko and ua) and ko["StartDate"] == "2026-10-05T05:00:00.000Z" and ua["EndDate"] == "2026-11-02T14:00:00.000Z", f"kickoff={ko.get('StartDate') if ko else None} uat_end={ua.get('EndDate') if ua else None}")
    add("Answer gives the critical path chain and says nobody is overloaded", "critical" in ans.lower() and all(w in ans for w in ("Kickoff", "Build", "UAT")) and re.search(r"no over-?allocat|not overloaded|nobody is overloaded|no one is overloaded|not over-?allocat|rather than overloaded|over-?allocation:? none|nobody exceeds|no-?one exceeds|none", ans, re.I) is not None, ans[:200].replace("\n", " "))
    ok, ev = png_check(outdir)
    add("A fit-width PNG of the chart was produced (>= 1400 px wide)", ok, ev)
    return E


def png_check(outdir):
    """(passed, evidence) for: a PNG of the chart exists, >= 1400 px wide."""
    import struct
    pngs = sorted(glob.glob(os.path.join(outdir, "*.png")))
    best = None
    for f in pngs:
        try:
            b = open(f, "rb").read(24)
            w, h = struct.unpack(">II", b[16:24])
        except Exception:
            continue
        if best is None or w > best[1]:
            best = (os.path.basename(f), w, h)
    if not best:
        return False, "no PNG produced"
    return best[1] >= 1400, f"{best[0]} {best[1]}x{best[2]} px"


def grade_eval4(outdir):
    f, d, err = load(outdir)
    ans = answer(outdir)
    E = []
    def add(text, ok, ev): E.append({"text": text, "passed": bool(ok), "evidence": ev})
    low = ans.lower()
    add("answer.md opens with the shortcut screen (use all recommended values / ask me each question)",
        bool(re.search(r"use all recommended", low)) and bool(re.search(r"ask me each", low)), ans[:200].replace("\n", " "))
    topics = {"holidays": r"holiday", "resources/team": r"team for this plan|resources|team", "allocation units": r"allocation units|100 ?%",
              "images/PNG variants": r"png|image", "save location": r"where to save|save location|save to", "file name": r"file name"}
    missing = [k for k, rx in topics.items() if not re.search(rx, low)]
    add("Asks the plan-specific questions: holidays, team/resources, allocation units, images, save location, file name",
        not missing, "missing: " + ", ".join(missing) if missing else "all present")
    n_rec = len(re.findall(r"\(recommended\)", low))
    n_q = len(re.findall(r"^\s*(?:\*\*)?q?\d*[.)]?\s*.*\?\s*(?:\*\*)?\s*$", ans, re.M))
    add("Every question is tap-to-select: 2-4 options with a (Recommended) label on the first option (>= 8 questions with labels)",
        n_rec >= 8, f"{n_rec} '(Recommended)' labels, ~{n_q} question lines")
    add("Multi-select is indicated where several answers apply (holidays, team, images)", len(re.findall(r"multi-?select", low)) >= 2, f"{len(re.findall(r'multi-?select', low))} multi-select notes")
    add("Team question lists Anas, Sara, Khalid and the moving company", all(x in low for x in ("anas", "sara", "khalid")) and "moving" in low, "names present" if all(x in low for x in ("anas", "sara", "khalid")) else "names missing")
    add("Missing durations/owners are proposed in a table and confirmed with ONE question (use proposals / corrections / task by task)",
        bool(re.search(r"\|\s*(#|id|task)", low)) and bool(re.search(r"use (my|the) proposals", low)) and bool(re.search(r"task by task", low)), "proposal table + confirm present" if re.search(r"use (my|the) proposals", low) else "no proposal confirm found")
    add("Draft with inferred dependencies is confirmed with one question (build as shown / list changes / walk through the links)",
        bool(re.search(r"build (the plan )?as shown|build it", low)) and bool(re.search(r"list changes|walk me through", low)) and bool(re.search(r"\d+\s*fs|depend", low)), "draft confirm present" if re.search(r"build (the plan )?as shown|build it", low) else "no draft confirm")
    add("A .gantt file was built after the interview and validates with 0 errors", bool(d) and validate(f)[0] == 0, (validate(f)[1].strip().splitlines()[-1] if d else (err or "no file")))
    if d and isinstance(d.get("data"), list):
        tasks = list(flat(d["data"]))
        a = d.get("advanced", {})
        res = {r.get("resourceId", "") for r in d.get("resources", [])}
        add("Built with the recommended conventions: Asia/Riyadh, bilingual names, movers as a resource, 3 phases",
            a.get("timezone") == "Asia/Riyadh" and all(AR.search(t["TaskName"]) for t in tasks) and any("mov" in r.lower() for r in res) and len(d["data"]) == 3,
            f"tz={a.get('timezone')} phases={len(d['data'])} resources={sorted(res)}")
        add("File name follows '<Plan> v1 2026-09-13.gantt'", bool(re.search(r" v1 2026-09-13\.gantt$", os.path.basename(f))), os.path.basename(f))
    else:
        add("Built with the recommended conventions: Asia/Riyadh, bilingual names, movers as a resource, 3 phases", False, "no valid .gantt (missing 'data'/'resources')")
        add("File name follows '<Plan> v1 2026-09-13.gantt'", bool(f) and bool(re.search(r" v1 2026-09-13\.gantt$", os.path.basename(f))), os.path.basename(f) if f else "no file")
    ok, ev = png_check(outdir)
    add("A fit-width PNG of the chart was produced (>= 1400 px wide)", ok, ev)
    return E


GRADERS = {"eval-1-create-from-prose": grade_eval1, "eval-2-edit-existing-plan": grade_eval2, "eval-3-spreadsheet-to-plan-and-questions": grade_eval3, "eval-4-underspecified-request-interview": grade_eval4}
PNG_TEXT = "A fit-width PNG of the chart was produced (>= 1400 px wide)"


def main():
    for stream in (sys.stdout, sys.stderr):  # UTF-8 output on legacy Windows code pages
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    changed = 0
    graded = 0
    for ev, fn in GRADERS.items():
        for cfg in ("with_skill", "without_skill"):
            outdir = os.path.join(W, ev, cfg, "run-1", "outputs")
            if not os.path.isdir(outdir):
                outdir = os.path.join(W, ev, cfg, "outputs")
            if not os.path.isdir(os.path.dirname(outdir)):
                continue
            E = fn(outdir)
            if SKIP_PNG:
                E = [e for e in E if e["text"] != PNG_TEXT]
            passed = sum(1 for e in E if e["passed"])
            gpath = os.path.join(os.path.dirname(outdir), "grading.json")
            graded += 1
            if CHECK:
                try:
                    committed = json.load(open(gpath, encoding="utf-8"))["expectations"]
                except (OSError, ValueError, KeyError):
                    committed = []
                if SKIP_PNG:
                    committed = [e for e in committed if e["text"] != PNG_TEXT]
                mine = [(e["text"], e["passed"]) for e in E]
                theirs = [(e["text"], e["passed"]) for e in committed]
                if mine != theirs:
                    changed += 1
                    print(f"{ev:45s} {cfg:14s} CHANGED (now {passed}/{len(E)}, committed {sum(1 for _, p in theirs if p)}/{len(theirs)})")
                    for (t, a), (_, b) in zip(mine, theirs):
                        if a != b:
                            print(f"    {t}: now {a}, committed {b}")
                else:
                    print(f"{ev:45s} {cfg:14s} {passed}/{len(E)}  (unchanged)")
                continue
            json.dump({"expectations": E, "passed": passed, "total": len(E),
                       "summary": {"pass_rate": round(passed / len(E), 4) if E else 0, "passed": passed, "failed": len(E) - passed, "total": len(E)}},
                      open(gpath, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(f"{ev:45s} {cfg:14s} {passed}/{len(E)}")
            for e in E:
                if not e["passed"]:
                    print(f"    FAIL {e['text']} -- {e['evidence'][:160]}")
    if not graded:
        print(f"no results under {W}")
        return 2
    if CHECK and changed:
        print(f"{changed} grading(s) differ from the committed results")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
