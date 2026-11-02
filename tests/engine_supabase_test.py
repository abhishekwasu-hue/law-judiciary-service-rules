#!/usr/bin/env python3
"""Stdlib test for tools/engine_supabase.py: a local http.server mocks Supabase REST + Storage.
Runs fetch -> step -> finish (fake outputs), then a fail case (missing outputs), then claude_result (cost + Marathi
failure reasons), verify (fake verify_outputs), warn, and the newest-proposal pick. Run: py tests/engine_supabase_test.py"""
import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "engine_supabase.py")
KEY = "test-service-key"
PROP = "प्रस्ताव CR 130 मूळ.pdf"

DB = {
    "cases": [{"id": 7, "cr_no": "130", "cr_year": 2026, "subject": "विषय", "stage": "अभ्यास चालू"}],
    "runs": [{"id": 11, "case_id": 7, "state": "queued", "instructions": "पत्रात फक्त अत्यावश्यक माहिती", "step": None}],
    "case_files": [
        {"id": 1, "case_id": 7, "kind": "proposal", "storage_path": f"proposals/7/proposal/v1/{PROP}", "original_name": PROP, "version": 1, "created_at": "1"},
        {"id": 2, "case_id": 7, "kind": "proposal", "storage_path": "proposals/7/proposal/v2/file.pdf", "original_name": PROP, "version": 2, "created_at": "2"},
        {"id": 3, "case_id": 7, "kind": "reply", "storage_path": "proposals/7/reply/v1/उत्तर.pdf", "original_name": "उत्तर.pdf", "version": 1, "created_at": "3"},
        {"id": 4, "case_id": 7, "kind": "study", "storage_path": "outputs/7/study/v1/CR130_2026_Study.docx", "original_name": "CR130_2026_Study.docx", "version": 1, "created_at": "4"},
    ],
    "activity": [],
}
STORE = {f"proposals/7/proposal/v1/{PROP}": b"%PDF old", "proposals/7/proposal/v2/file.pdf": b"%PDF new",
         "proposals/7/reply/v1/उत्तर.pdf": b"%PDF reply"}
LOG = []
WSTEPS = []
REJECT_KINDS = set()   # case_files kinds the mock DB refuses (enum value not yet added: migration 0006 not applied)


def match(rows, q):
    out = rows
    for k, v in q.items():
        if k in ("select", "order", "limit"): continue
        v = v[0]
        if v.startswith("eq."): out = [r for r in out if str(r.get(k)) == v[3:]]
    if "order" in q:
        col, _, d = q["order"][0].partition(".")
        out = sorted(out, key=lambda r: (0, r[col], "") if isinstance(r.get(col), (int, float)) else (1, 0, str(r.get(col) or "")), reverse=(d == "desc"))
    if "limit" in q: out = out[: int(q["limit"][0])]
    return out


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, obj=None, raw=None):
        b = raw if raw is not None else (json.dumps(obj, ensure_ascii=False).encode() if obj is not None else b"")
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def handle_any(self):
        u = urllib.parse.urlparse(self.path); path = urllib.parse.unquote(u.path); q = urllib.parse.parse_qs(u.query)
        n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n) if n else b""
        LOG.append({"m": self.command, "path": path, "q": q, "body": body, "h": self.headers})
        if path == "/api/engine/step":  # Worker route (H1): run token, no Supabase key
            WSTEPS.append({"auth": self.headers.get("Authorization"), "body": json.loads(body)}); return self.send(200, {"ok": True})
        if self.headers.get("apikey") != KEY or self.headers.get("Authorization") != f"Bearer {KEY}":
            return self.send(401, {"error": "auth"})
        if path.startswith("/storage/v1/object/"):
            key = path[len("/storage/v1/object/"):]
            if self.command == "GET":
                return self.send(200, raw=STORE[key]) if key in STORE else self.send(404, {"error": "nf"})
            if self.command == "DELETE":
                STORE.pop(key, None); return self.send(200, {"ok": True})
            STORE[key] = body; return self.send(200, {"Key": key})
        if path.startswith("/rest/v1/"):
            t = path[len("/rest/v1/"):]; rows = DB[t]
            if self.command == "GET": return self.send(200, match(rows, q))
            data = json.loads(body)
            if self.command == "POST":
                if t == "case_files" and data.get("kind") in REJECT_KINDS:
                    return self.send(400, {"code": "22P02", "message": f'invalid input value for enum file_kind: "{data["kind"]}"'})
                data["id"] = len(rows) + 100; data.setdefault("created_at", "8"); rows.append(data); return self.send(201)
            if self.command == "PATCH":
                for r in match(rows, q): r.update(data)
                return self.send(204)
        self.send(400, {"error": "route"})

    do_GET = do_POST = do_PATCH = do_DELETE = handle_any


def run(*args, **extra):
    env = dict(os.environ, SUPABASE_URL=BASE, SUPABASE_SERVICE_KEY=KEY, CASE_ID="7", RUN_ID="11", PYTHONIOENCODING="utf-8", **extra)
    return subprocess.run([sys.executable, TOOL, *args], env=env, capture_output=True, text=True, encoding="utf-8")


def check(c, msg):
    if not c: raise AssertionError(msg)
    print("ok  ", msg)


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
tmp = tempfile.mkdtemp()
work, out = os.path.join(tmp, "case"), os.path.join(tmp, "out")
run_row = DB["runs"][0]

# --- fetch
r = run("fetch", work); check(r.returncode == 0, f"fetch exit 0 ({r.stderr.strip()[:200]})")
p = os.path.join(work, "in", "proposal", PROP)
check(open(p, "rb").read() == b"%PDF new", "fetch: newest proposal version (ASCII storage key file.pdf) saved under its original name")
check(os.path.exists(os.path.join(work, "in", "reply", "उत्तर.pdf")), "fetch: reply downloaded")
check(not os.path.exists(os.path.join(work, "in", "study")), "fetch: outputs not downloaded")
cj = json.load(open(os.path.join(work, "case.json"), encoding="utf-8"))
check(cj["case"]["cr_no"] == "130" and cj["instructions"] == run_row["instructions"] and cj["proposal_original_name"] == PROP, "case.json: case row + instructions + proposal name")
check(run_row["state"] == "running" and run_row["started_at"] and run_row["step"] == "पाने वाचत आहे", "fetch: runs PATCH running")

# --- step / log_url
r = run("step", "GR शोधत आहे"); check(r.returncode == 0 and run_row["step"] == "GR शोधत आहे", "step: runs.step")
r = run("log_url", "https://github.com/x/y/actions/runs/1"); check(run_row["log_url"].endswith("/runs/1"), "log_url: runs.log_url")

# --- finish with fake outputs
os.makedirs(out)
for n in ("CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx", "CR130_2026_Note_and_Letter.pdf", PROP, PROP + ".map.json"):
    open(os.path.join(out, n), "wb").write(b"x" + n.encode())
st = {"state": "done", "summary": "वेतननिश्चिती प्रस्ताव; माहिती-मागणी पत्र", "letter_needed": True,
      "essential_points": ["सेवापुस्तक उतारा"], "grs_attached": [{"code": "202204191549468012", "date": "19.04.2022", "title": "t", "pages": "12-13"}],
      "grs_missing": [{"date": "12.03.2014", "title": "t2"}],
      "case": {"cr_no": "999", "cr_year": 2026, "file_no": "संकीर्ण-2026/979/प्र.क्र.130/का.6", "subject": "दुसरा विषय", "category": "भत्ते"}}
DB["cases"][0].update(file_no=None, category="इतर")  # user left file no. and category empty at upload
json.dump(st, open(os.path.join(out, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
LOG.clear()
r = run("finish", out); check(r.returncode == 0, f"finish exit 0 ({r.stderr.strip()[:300]})")
ups = [l["path"] for l in LOG if l["m"] == "POST" and l["path"].startswith("/storage/v1/object/")]
check(sorted(ups) == sorted(["/storage/v1/object/outputs/7/study/v2/file.docx",
                             "/storage/v1/object/outputs/7/note_letter/v1/file.docx",
                             "/storage/v1/object/outputs/7/package_pdf/v1/file.pdf"]), f"finish: 3 uploads to outputs, ASCII keys file<ext>, versions ({ups})")
check(all(u.isascii() for u in ups), "finish: storage object keys are ASCII (Devanagari proposal name)")
check(STORE["outputs/7/package_pdf/v1/file.pdf"] == b"x" + PROP.encode(), "finish: package PDF content uploaded")
pdfh = [l for l in LOG if l["path"].endswith("package_pdf/v1/file.pdf") and l["m"] == "POST"][0]["h"]
check(pdfh.get("Content-Type") == "application/pdf" and pdfh.get("x-upsert") == "true", "finish: content-type + upsert")
new = [f for f in DB["case_files"] if f["id"] >= 100]
check({(f["kind"], f["version"], f["storage_path"].split("/")[0]) for f in new} == {("study", 2, "outputs"), ("note_letter", 1, "outputs"), ("package_pdf", 1, "outputs")}, "finish: case_files rows")
check({f["kind"]: (f["storage_path"], f["original_name"]) for f in new} == {
    "study": ("outputs/7/study/v2/file.docx", "CR130_2026_Study.docx"),
    "note_letter": ("outputs/7/note_letter/v1/file.docx", "CR130_2026_Note_and_Letter.docx"),
    "package_pdf": ("outputs/7/package_pdf/v1/file.pdf", PROP)}, "finish: case_files storage_path ASCII, original_name = real (Devanagari) name")
check(run_row["state"] == "done" and run_row["step"] == "तयार" and run_row["summary"] == st["summary"] and run_row["letter_needed"] is True
      and run_row["essential_points"] == st["essential_points"] and run_row["grs_attached"] == st["grs_attached"]
      and run_row["grs_missing"] == st["grs_missing"] and run_row["finished_at"], "finish: runs PATCH done + summary fields")
check(DB["cases"][0]["stage"] == "मसुदा तयार", "finish: cases.stage मसुदा तयार")
check(any(a["action"] == "run_done" for a in DB["activity"]), "finish: activity run_done")
c0 = DB["cases"][0]
check(c0["file_no"] == "संकीर्ण-2026/979/प्र.क्र.130/का.6" and c0["category"] == "भत्ते", "finish: empty file_no/category filled from PDF")
check(c0["cr_no"] == "130" and c0["subject"] == "विषय", "finish: fields the user typed are not overwritten")
check(any(a["action"] == "case_filled_from_pdf" for a in DB["activity"]), "finish: activity case_filled_from_pdf")

# --- fail case: missing outputs
run_row.update(state="running", step="तपासणी चालू"); n_files = len(DB["case_files"])
out2 = os.path.join(tmp, "out2"); os.makedirs(out2)
open(os.path.join(out2, "CR130_2026_Study.docx"), "wb").write(b"x")
open(os.path.join(out2, "CR130_2026_Proposal_with_GRs.pdf"), "wb").write(b"x")
json.dump({"state": "done", "summary": "s"}, open(os.path.join(out2, "status.json"), "w", encoding="utf-8"))
r = run("finish", out2); check(r.returncode == 1, "finish incomplete: exit 1")
check(run_row["state"] == "failed" and "Note_and_Letter" in run_row["step"] and "मूळ प्रस्ताव" in run_row["step"], f"finish incomplete: runs failed with reason ({run_row['step']})")
check(len(DB["case_files"]) == n_files, "finish incomplete: nothing uploaded / no rows")
check(any(a["action"] == "run_failed" for a in DB["activity"]), "fail: activity run_failed")

# --- explicit fail keeps the first (specific) reason
reason = run_row["step"]; r = run("fail", "इंजिन अयशस्वी")
check(r.returncode == 1 and run_row["step"] == reason, "fail: exit 1, earlier reason kept")
run_row.update(state="running")
r = run("fail", "claude step failed"); check(r.returncode == 1 and run_row["state"] == "failed" and run_row["step"] == "claude step failed", "fail: runs failed + step reason")

# --- claude_result: cost/turns/duration stored; error results -> Marathi reason + next step
def claude(obj, err="", rc="0", raw=None):
    run_row.update(state="running", step="तपासणी चालू")
    jf, ef = os.path.join(tmp, "claude.json"), os.path.join(tmp, "claude.err")
    open(jf, "w", encoding="utf-8").write(raw if raw is not None else json.dumps(obj))
    open(ef, "w", encoding="utf-8").write(err)
    return run("claude_result", jf, ef, rc)

r = claude({"type": "result", "subtype": "success", "is_error": False, "num_turns": 87, "duration_ms": 1234567, "total_cost_usd": 3.14159, "result": "पूर्ण"})
check(r.returncode == 0 and run_row["state"] == "running", f"claude_result success: exit 0, run still running ({r.stderr[:200]})")
check(run_row["cost_usd"] == 3.1416 and run_row["num_turns"] == 87 and run_row["duration_s"] == 1234.6, "claude_result: cost_usd, num_turns, duration_s stored")
r = claude({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 400, "duration_ms": 1000, "total_cost_usd": 9.5})
check(r.returncode == 1 and run_row["state"] == "failed" and "max turns" in run_row["step"] and "पुन्हा तयार करा" in run_row["step"]
      and run_row["num_turns"] == 400, f"claude_result max turns: failed + Marathi reason ({run_row['step']})")
r = claude({"type": "result", "subtype": "success", "is_error": True, "result": "Invalid API key · Please run /login"}, rc="1")
check(r.returncode == 1 and "Settings मधील Anthropic key" in run_row["step"], "claude_result auth error: key reason")
r = claude(None, err="API Error: 400 Your credit balance is too low to access the Anthropic API", rc="1", raw="")
check(r.returncode == 1 and "credit" in run_row["step"] and run_row["state"] == "failed", "claude_result no JSON + credit text: credit reason")
r = claude(None, err="", rc="124", raw="")
check(r.returncode == 1 and "वेळ संपली" in run_row["step"], "claude_result timeout (exit 124): Marathi time-out reason")
r = claude(None, err="something odd", rc="137", raw="not json")
check(r.returncode == 1 and "exit 137" in run_row["step"], f"claude_result unknown error: exit code in reason ({run_row['step']})")

# --- claude_result with the parallel Study-part-1 run: cost/turns summed, duration = wall clock (--wall)
p1f = os.path.join(tmp, "part1.json")
open(p1f, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 30,
                                                   "duration_ms": 400000, "total_cost_usd": 1.25}))
run_row.update(state="running", step="तपासणी चालू", warnings=[])
jf, ef = os.path.join(tmp, "claude.json"), os.path.join(tmp, "claude.err")
open(jf, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 79,
                                                  "duration_ms": 600000, "total_cost_usd": 3.32}))
open(ef, "w", encoding="utf-8").write("")
r = run("claude_result", jf, ef, "0", "--part1", p1f, "--wall", "655.4")
check(r.returncode == 0 and run_row["state"] == "running", f"claude_result main+part1: exit 0 ({r.stderr[:200]})")
check(run_row["cost_usd"] == 4.57 and run_row["num_turns"] == 109 and run_row["duration_s"] == 655.4,
      f"claude_result main+part1: cost/turns summed, duration = wall ({run_row['cost_usd']}, {run_row['num_turns']}, {run_row['duration_s']})")
check(run_row["warnings"] == [], "claude_result part1 success: no warning")
r = run("claude_result", jf, ef, "0", "--part1", p1f)
check(run_row["duration_s"] == 600.0 and run_row["num_turns"] == 109, "claude_result without --wall: duration = longer run")
r = run("claude_result", jf, ef, "0", "--part1", os.path.join(tmp, "absent.json"), "--wall", "700")
check(r.returncode == 0 and run_row["state"] == "running" and run_row["cost_usd"] == 3.32 and run_row["num_turns"] == 79
      and run_row["duration_s"] == 700.0, "claude_result part1 JSON absent: main only, not failed")
check(len(run_row["warnings"]) == 1 and "भाग 1" in run_row["warnings"][0], "claude_result part1 absent: warning recorded")
open(p1f, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 120, "total_cost_usd": 2.0}))
r = run("claude_result", jf, ef, "0", "--part1", p1f, "--wall", "800")
check(r.returncode == 0 and run_row["state"] == "running" and run_row["num_turns"] == 199 and run_row["cost_usd"] == 5.32,
      "claude_result part1 error alone: case not failed, its cost/turns still counted")
check(len(run_row["warnings"]) == 2 and "error_max_turns" in run_row["warnings"][1], "claude_result part1 error: warning with subtype")
open(jf, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 400, "total_cost_usd": 9.0}))
r = run("claude_result", jf, ef, "0", "--part1", p1f, "--wall", "900")
check(r.returncode == 1 and run_row["state"] == "failed" and "max turns" in run_row["step"] and run_row["num_turns"] == 520,
      "claude_result main error with part1: failed with the main run's reason, sums stored")

# --- deliver with warnings (A1 H1): status.json done + the three outputs -> an error result is only a warning
outd = os.path.join(tmp, "out_dw"); os.makedirs(outd)
for n in ("CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx", PROP):
    open(os.path.join(outd, n), "wb").write(b"x")
json.dump({"state": "done", "summary": "s"}, open(os.path.join(outd, "status.json"), "w", encoding="utf-8"))
open(jf, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 400, "total_cost_usd": 2.0}))
run_row.update(state="running", step="तपासणी चालू", warnings=[])
r = run("claude_result", jf, ef, "0", "--status", os.path.join(outd, "status.json"))
check(r.returncode == 0 and run_row["state"] == "running" and any(w.startswith("अभ्यास नीट संपला नाही (अभ्यास अपूर्ण — कमाल पायऱ्या") for w in run_row["warnings"]),
      f"claude_result max turns but done + outputs: delivered with a warning ({run_row['warnings']} {r.stderr[:200]})")
os.remove(os.path.join(outd, "CR130_2026_Note_and_Letter.docx"))
r = run("claude_result", jf, ef, "0", "--status", os.path.join(outd, "status.json"))
check(r.returncode == 1 and run_row["state"] == "failed", "claude_result max turns, an output missing: failed")
# --killed: no JSON -> estimated cost (BUDGET_USD) + warning; with outputs + done -> delivered
open(os.path.join(outd, "CR130_2026_Note_and_Letter.docx"), "wb").write(b"x")
run_row.update(state="running", step="तपासणी चालू", warnings=[], cost_usd=None)
open(jf, "w").write("")
r = run("claude_result", jf, ef, "124", "--killed", "--status", os.path.join(outd, "status.json"), BUDGET_USD="1.5")
check(r.returncode == 0 and run_row["cost_usd"] == 1.5 and any(w.startswith("खर्च अंदाजे") for w in run_row["warnings"])
      and any(w.startswith("अभ्यास नीट संपला नाही (वेळ संपली") for w in run_row["warnings"]),
      f"claude_result --killed: estimated cost stored, delivered ({run_row['cost_usd']} {run_row['warnings']})")
run_row.update(state="running", step="तपासणी चालू", warnings=[], cost_usd=None)
r = run("claude_result", jf, ef, "0", "--killed")
check(r.returncode == 1 and run_row["cost_usd"] == 0.75 and run_row["state"] == "failed" and "थांबवला" in run_row["step"],
      f"claude_result --killed, no outputs: default estimate 0.75, failed ({run_row['cost_usd']} {run_row['step']})")
# --first: cost of the failed first run before the fallback is added; --part1-no-cost: part 1 cost not added
f0 = os.path.join(tmp, "first.json")
json.dump({"type": "result", "subtype": "success", "is_error": True, "num_turns": 5, "total_cost_usd": 0.4}, open(f0, "w"))
open(jf, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 10, "total_cost_usd": 1.0}))
open(p1f, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 3, "total_cost_usd": 0.3}))
run_row.update(state="running", step="तपासणी चालू", warnings=[])
r = run("claude_result", jf, ef, "0", "--first", f0, "--part1", p1f, "--part1-no-cost")
check(r.returncode == 0 and run_row["cost_usd"] == 1.4 and run_row["num_turns"] == 15 and run_row["state"] == "running",
      f"claude_result --first added, --part1-no-cost not added ({run_row['cost_usd']}, {run_row['num_turns']})")
open(p1f, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True}))
r = run("claude_result", jf, ef, "0", "--part1", p1f, "--part1-no-cost")
check(r.returncode == 0 and any("भाग 1" in w for w in run_row["warnings"]), "claude_result --part1-no-cost: part-1 error still a warning")

# --- verify: runs verify_outputs with PREFIX / package / proposal pages. "Deliver with warnings": only HARD FAIL lines
#     (outputs unreadable, internal ids / repo paths, annotations on proposal pages) fail the case; others = warnings
fake = os.path.join(tmp, "fake_verify.py"); argf = os.path.join(tmp, "verify_args.json")
open(fake, "w", encoding="utf-8").write(
    "import json, os, sys\n"
    f"json.dump(sys.argv[1:], open({argf!r}, 'w', encoding='utf-8'), ensure_ascii=False)\n"
    "if os.environ.get('FAKE_FAIL') == 'soft':\n"
    "    print('FAIL: Study fonts — Study: 3 runs without DVOT-SurekhMR'); print('FAIL: page stamps — no stamp on page 4'); print('FIX THE FAILS ABOVE | pages 9')\n"
    "    sys.exit(1)\n"
    "elif os.environ.get('FAKE_FAIL') == 'hard':\n"
    "    print('FAIL: Note_and_Letter internal ids — internal id z6_0235'); print('FAIL: Study fonts — x'); print('FIX THE FAILS ABOVE | pages 9')\n"
    "    sys.exit(1)\n"
    "elif os.environ.get('FAKE_FAIL') == 'crash':\n"
    "    raise SystemExit('boom')\n"
    "else:\n"
    "    print('ALL OK | pages 9 | toc 3')\n")
st["prefix"] = "CR130_2026"; st["package_pdf"] = PROP; st["proposal_pages"] = 5
# reviewer approval missing / false -> SOFT: warning, verify_outputs still runs, case not failed
for rv, label in ((None, "no review"), ({"approved": False, "changes": 0, "reason": "पत्राचा निर्णय चुकीचा"}, "approved false")):
    st.pop("review", None)
    if rv: st["review"] = rv
    json.dump(st, open(os.path.join(out, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
    run_row.update(state="running", step="तपासणी चालू", warnings=[])
    if os.path.exists(argf): os.remove(argf)
    r = run("verify", out, work, VERIFY_SCRIPT=fake)
    check(r.returncode == 0 and run_row["state"] == "running" and os.path.exists(argf)
          and any(w.startswith("अंतिम पडताळणी (Opus) मान्यता नाही — वापरण्यापूर्वी तपासा: ") for w in run_row["warnings"])
          and (not rv or any("पत्राचा निर्णय चुकीचा" in w for w in run_row["warnings"])),
          f"verify: {label} -> delivered with the review warning ({run_row['warnings']})")
st["review"] = {"approved": True, "changes": 2, "corrections": ["नोंद परि.3 दिनांक 05.08.2026 केला", "पत्रातील पदनाम"]}
json.dump(st, open(os.path.join(out, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
run_row.update(state="running", step="तपासणी चालू", warnings=[])
r = run("verify", out, work, VERIFY_SCRIPT=fake)
a = json.load(open(argf, encoding="utf-8"))
check(r.returncode == 0 and run_row["state"] == "running" and "verify: ALL OK" in r.stdout and not run_row["warnings"],
      f"verify ALL OK: exit 0, no warning ({r.stderr[:200]})")
check(a[1] == "CR130_2026" and os.path.basename(a[2]) == PROP and a[0] == out, "verify: outdir, PREFIX, package PDF passed")
check(a[3] == "5", f"verify: proposal pages from status.json when the PDF cannot be read ({a[3]})")
check(a[4:] == ["--original-name", PROP], f"verify: --original-name = the newest proposal's original name ({a[4:]})")
# a real proposal file name that looks machine-made (live case: CR66_Proposal_with_GRs.pdf) is passed as is
cj0 = json.load(open(os.path.join(work, "case.json"), encoding="utf-8"))
work_m = os.path.join(tmp, "case_m"); out_m = os.path.join(tmp, "out_m"); os.makedirs(out_m)
MN = "CR66_Proposal_with_GRs.pdf"
json.dump({**cj0, "proposal_original_name": "11ae057d-" + MN, "inputs": []}, open(os.path.join(tmp, "cm.json"), "w", encoding="utf-8"))
os.makedirs(work_m); os.replace(os.path.join(tmp, "cm.json"), os.path.join(work_m, "case.json"))
open(os.path.join(out_m, MN), "wb").write(b"x"); open(os.path.join(out_m, "CR66_2026_Study.docx"), "wb").write(b"x")
json.dump({"state": "done", "prefix": "CR66_2026", "package_pdf": MN, "proposal_pages": 4, "review": {"approved": True, "changes": 0}},
          open(os.path.join(out_m, "status.json"), "w", encoding="utf-8"))
r = run("verify", out_m, work_m, VERIFY_SCRIPT=fake)
a = json.load(open(argf, encoding="utf-8"))
check(r.returncode == 0 and a[4:] == ["--original-name", MN] and os.path.basename(a[2]) == MN,
      f"verify: upload prefix stripped, machine-looking original name passed ({a[4:]})")
r = run("verify", out_m, VERIFY_SCRIPT=fake)
check(len(json.load(open(argf, encoding="utf-8"))) == 4, "verify without workdir: no --original-name")
# --case-meta (runner-written, from Supabase) wins over the engine-writable case.json
cmf = os.path.join(tmp, "case_meta.json")
json.dump({"proposal_original_name": "11ae057d-" + MN, "proposal_pages": 7}, open(cmf, "w", encoding="utf-8"))
r = run("verify", out_m, work_m, "--case-meta", cmf, VERIFY_SCRIPT=fake)
a = json.load(open(argf, encoding="utf-8"))
check(r.returncode == 0 and a[3] == "7" and a[4:] == ["--original-name", MN], f"verify --case-meta: pages + name from the meta file ({a})")
try:
    import pymupdf
    d = pymupdf.open()
    for _ in range(3): d.new_page()
    d.save(os.path.join(work, "in", "proposal", PROP)); d.close()
    r = run("verify", out, work, VERIFY_SCRIPT=fake)
    check(json.load(open(argf, encoding="utf-8"))[3] == "3", "verify: proposal pages = page count of the fetched proposal")
    # case_meta: original name from Supabase, pages from the fetched PDF
    cm2 = os.path.join(tmp, "cm2", "meta.json")
    r = run("case_meta", cm2, work)
    m2 = json.load(open(cm2, encoding="utf-8"))
    check(r.returncode == 0 and m2 == {"proposal_original_name": PROP, "proposal_pages": 3}, f"case_meta: name + pages ({m2} {r.stderr[:200]})")
except ImportError:
    print("skip  verify page count (pymupdf not installed)")
run_row.update(state="running", step="तपासणी चालू", warnings=[])
r = run("verify", out, work, VERIFY_SCRIPT=fake, FAKE_FAIL="soft")
check(r.returncode == 0 and run_row["state"] == "running"
      and "पडताळणी अपूर्ण — Study fonts: Study: 3 runs without DVOT-SurekhMR" in run_row["warnings"]
      and "पडताळणी अपूर्ण — page stamps: no stamp on page 4" in run_row["warnings"],
      f"verify SOFT FAIL lines: delivered, one 'पडताळणी अपूर्ण' warning per check ({run_row['warnings']})")
run_row.update(state="running", step="तपासणी चालू", warnings=[])
r = run("verify", out, work, VERIFY_SCRIPT=fake, FAKE_FAIL="hard")
check(r.returncode == 1 and run_row["state"] == "failed" and "internal ids" in run_row["step"] and "z6_0235" in run_row["step"]
      and "Study fonts" not in run_row["step"] and any("Study fonts" in w for w in run_row["warnings"]),
      f"verify HARD (confidentiality): case failed, soft lines still warnings ({run_row['step']})")
run_row.update(state="running", step="तपासणी चालू", warnings=[])
r = run("verify", out, work, VERIFY_SCRIPT=fake, FAKE_FAIL="crash")
check(r.returncode == 1 and run_row["state"] == "failed" and "boom" in run_row["step"], f"verify tool crash: hard ({run_row['step']})")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import engine_supabase as es0
hard, soft = es0.classify_verify(["OK: x", "FAIL: annotations on proposal pages (none) — proposal page 1 has annotations ['Square']",
                                  "FAIL: annotations (Highlight only) — page 9", "FAIL: Order_Draft repo paths — repo path 'pdf/'",
                                  "FAIL: package PDF opens — x: no such file", "FAIL: map.json (page count, marks) — mark not placed",
                                  "FAIL: letter ending (§4.5) — 'आपला,' line missing"])
check([c for c, _ in hard] == ["annotations on proposal pages (none)", "Order_Draft repo paths", "package PDF opens"]
      and [c for c, _ in soft] == ["annotations (Highlight only)", "map.json (page count, marks)", "letter ending (§4.5)"],
      f"classify_verify: hard = confidentiality / unreadable / proposal annotations ({hard} | {soft})")

# --- warn: non-fatal, appended
run_row.update(state="done", warnings=[])
r = run("warn", "नवीन GR रेपोमध्ये जतन झाले नाहीत"); r = run("warn", "दुसरी सूचना")
check(r.returncode == 0 and run_row["warnings"] == ["नवीन GR रेपोमध्ये जतन झाले नाहीत", "दुसरी सूचना"] and run_row["state"] == "done",
      "warn: runs.warnings appended, state unchanged")
check(any(a["action"] == "run_warning" for a in DB["activity"]), "warn: activity run_warning")

# --- newest proposal by upload time, not by name: a corrected proposal under a new name replaces the old one
NEWP = "दुरुस्त प्रस्ताव.pdf"   # sorts before PROP alphabetically
DB["case_files"].append({"id": 50, "case_id": 7, "kind": "proposal", "storage_path": f"proposals/7/proposal/v1/{NEWP}",
                         "original_name": NEWP, "version": 1, "created_at": "9"})
STORE[f"proposals/7/proposal/v1/{NEWP}"] = b"%PDF corrected"
work2 = os.path.join(tmp, "case2")
r = run("fetch", work2); check(r.returncode == 0, f"fetch with two proposal names: exit 0 ({r.stderr[:300]})")
cj = json.load(open(os.path.join(work2, "case.json"), encoding="utf-8"))
check(cj["proposal_original_name"] == NEWP and os.listdir(os.path.join(work2, "in", "proposal")) == [NEWP],
      "fetch: only the newest proposal (by created_at), under its own name")
check(open(os.path.join(work2, "in", "extra_doc", PROP), "rb").read() == b"%PDF new"
      and any(f.get("from_kind") == "proposal" and f["kind"] == "extra_doc" for f in cj["inputs"])
      and any("प्रस्तावाच्या 2 फाइल" in w for w in run_row.get("warnings") or []),
      f"fetch: the other proposal PDF fetched as extra_doc + warning (A1 H13) ({run_row.get('warnings')})")
out3 = os.path.join(tmp, "out3"); os.makedirs(out3)
for n in ("CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx", PROP):
    open(os.path.join(out3, n), "wb").write(b"x")
json.dump({"state": "done", "summary": "s"}, open(os.path.join(out3, "status.json"), "w", encoding="utf-8"))
run_row.update(state="running")
r = run("finish", out3)
check(r.returncode == 1 and "मूळ प्रस्ताव" in run_row["step"], "finish: package named after the OLD proposal is refused")

# --- optional outputs (02.11.2026): *_Order_Draft.docx -> order_draft, *_Parawise.docx -> parawise; previews ignored
out4 = os.path.join(tmp, "out4"); os.makedirs(out4)
for n in ("CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx", NEWP, "CR130_2026_Order_Draft.docx",
          "CR130_2026_Order_Draft.pdf", "CR130_2026_Parawise.docx", "CR130_2026_Parawise.pdf"):
    open(os.path.join(out4, n), "wb").write(b"x" + n.encode())
json.dump({"state": "done", "summary": "s", "outputs_extra": ["order_draft", {"kind": "parawise", "file": "CR130_2026_Parawise.docx"}]},
          open(os.path.join(out4, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
run_row.update(state="running", warnings=[]); LOG.clear()
r = run("finish", out4)
check(r.returncode == 0 and run_row["state"] == "done", f"finish extras: exit 0, done ({r.stderr[:300]})")
ups = sorted(l["path"] for l in LOG if l["m"] == "POST" and l["path"].startswith("/storage/v1/object/"))
check("/storage/v1/object/outputs/7/order_draft/v1/file.docx" in ups and "/storage/v1/object/outputs/7/parawise/v1/file.docx" in ups
      and len(ups) == 5 and all(u.isascii() for u in ups), f"finish extras: order_draft + parawise uploaded, ASCII keys, previews not a package ({ups})")
rows = {f["kind"]: f for f in DB["case_files"] if f["kind"] in ("order_draft", "parawise")}
check(rows["order_draft"]["original_name"] == "CR130_2026_Order_Draft.docx" and rows["parawise"]["original_name"] == "CR130_2026_Parawise.docx"
      and rows["parawise"]["storage_path"] == "outputs/7/parawise/v1/file.docx", "finish extras: case_files rows, original names kept")
check(not run_row["warnings"], f"finish extras: no warning ({run_row['warnings']})")
# migration 0006 not applied -> the enum refuses the kind: warning only, the three main outputs stored
os.remove(os.path.join(out4, "CR130_2026_Parawise.docx"))
REJECT_KINDS.add("order_draft"); run_row.update(state="running", warnings=[]); n_files = len(DB["case_files"])
r = run("finish", out4)
check(r.returncode == 0 and run_row["state"] == "done", f"finish extras, enum missing: still done ({r.stderr[:300]})")
check(len(DB["case_files"]) == n_files + 3, "finish extras, enum missing: the three main outputs stored")
check(any("शासन आदेश-मसुदा जतन झाला नाही" in w and "0006" in w for w in run_row["warnings"])
      and any("परिच्छेदनिहाय अभिप्राय" in w and "फाइल नाही" in w for w in run_row["warnings"]),
      f"finish extras: refused upload + listed-but-absent file -> warnings ({run_row['warnings']})")
check("outputs/7/order_draft/v2/file.docx" not in STORE, "finish extras, enum missing: orphan Storage object removed")
REJECT_KINDS.clear()

# --- model tiers + soft budget: config parsing (local command, no Supabase env), agents JSON, part1check, "मॉडेल: " lines
sys.path.insert(0, os.path.join(ROOT, "tools"))
import engine_supabase as es

c = es.engine_config({})
check(c == {"MODEL": "claude-opus-5-5", "MODEL_LIGHT": "claude-haiku-5-5", "MODEL_REVIEW": "claude-opus-5-5", "MODEL_STRONG": "",
            "EFFORT": "medium", "BUDGET_USD": "0.75", "ENGINE_PROVIDER": "", "ENGINE_MODEL": "", "ENGINE_MODEL_LIGHT": "",
            "PART1_PROVIDER": "claude", "PART1_MODEL": "", "GEMINI_MODEL": "gemini-2.5-flash", "FALLBACK_PROVIDER": "", "FALLBACK_MODEL": "", "FALLBACK_MODEL_LIGHT": "",
            "CLOUDFLARE_ACCOUNT_ID": "", "OLLAMA_BASE_URL": ""},
      f"config: defaults (drafter, light Haiku, reviewer Opus, no strong tier, soft budget 0.75) {c}")
c = es.engine_config({"model": "claude-sonnet-5-5", "model_review": "claude-opus-5-5"})
check(c["MODEL"] == "claude-sonnet-5-5" and c["MODEL_REVIEW"] == "claude-opus-5-5" and c["MODEL_LIGHT"] == "claude-haiku-5-5",
      f"config: drafter Sonnet + reviewer Opus (Abhi 01.11.2026) {c}")
check(es.engine_config({"model_review": "$(id)"})["MODEL_REVIEW"] == "claude-opus-5-5" and
      es.engine_config({"model_review": ""})["MODEL_REVIEW"] == "claude-opus-5-5", "config: invalid/empty model_review -> Opus default")
c = es.engine_config({"model": " claude-sonnet-5-5 ", "model_light": "claude-haiku-5-5", "model_strong": "claude-fable-5-1",
                      "effort": "HIGH", "budget_usd": "1.5"})
check(c["MODEL"] == "claude-sonnet-5-5" and c["MODEL_STRONG"] == "claude-fable-5-1" and c["EFFORT"] == "high"
      and c["BUDGET_USD"] == "1.50", f"config: three tiers, effort, budget string parsed {c}")
for bad in ({"model": "x; rm -rf /", "model_light": "$(id)", "budget_usd": "abc", "effort": "turbo"},
            {"model": 5, "model_light": None, "budget_usd": True}, {"budget_usd": -1}, {"budget_usd": 1e9}, {"budget_usd": float("nan")}):
    c = es.engine_config(bad)
    check(c["MODEL"] == "claude-opus-5-5" and c["MODEL_LIGHT"] == "claude-haiku-5-5" and c["BUDGET_USD"] == "0.75"
          and c["EFFORT"] == "medium", f"config: invalid values -> defaults ({bad})")
check(es.engine_config({"model_strong": "none"})["MODEL_STRONG"] == "" and es.engine_config({"model_strong": "OFF"})["MODEL_STRONG"] == ""
      and es.engine_config({"model": "claude-opus-5-5", "model_strong": "claude-opus-5-5"})["MODEL_STRONG"] == "",
      "config: model_strong none/off/same as main -> no escalation tier")
check(es.engine_config("not a dict")["MODEL"] == "claude-opus-5-5", "config: non-dict -> defaults")
cfgf = os.path.join(tmp, "cfg.json")
json.dump({"anthropic_api_key": "sk-secret", "model": "claude-opus-5-5", "model_light": "claude-haiku-5-5", "budget_usd": 0.9},
          open(cfgf, "w", encoding="utf-8"))
r = subprocess.run([sys.executable, TOOL, "config", cfgf], capture_output=True, text=True, encoding="utf-8",
                   env={k: v for k, v in os.environ.items() if not k.startswith("SUPABASE")})
check(r.returncode == 0 and r.stdout.splitlines() == ["MODEL=claude-opus-5-5", "MODEL_LIGHT=claude-haiku-5-5", "MODEL_REVIEW=claude-opus-5-5", "MODEL_STRONG=",
      "EFFORT=medium", "BUDGET_USD=0.90",
      "ENGINE_PROVIDER=", "ENGINE_MODEL=", "ENGINE_MODEL_LIGHT=", "PART1_PROVIDER=claude", "PART1_MODEL=", "GEMINI_MODEL=gemini-2.5-flash",
      "FALLBACK_PROVIDER=", "FALLBACK_MODEL=", "FALLBACK_MODEL_LIGHT=", "CLOUDFLARE_ACCOUNT_ID=", "OLLAMA_BASE_URL="] and "sk-secret" not in r.stdout, f"config CLI: KEY=VALUE lines, no secret, no Supabase env ({r.stdout!r} {r.stderr[:200]})")
r = subprocess.run([sys.executable, TOOL, "config", os.path.join(tmp, "absent.json")], capture_output=True, text=True, encoding="utf-8")
check(r.returncode == 0 and "MODEL=claude-opus-5-5" in r.stdout, "config CLI: unreadable file -> defaults")

# --- other providers (A: part 1 on Gemini; C: fallback through LiteLLM) — Abhi 02.11.2026
pc = es.provider_config
check(pc({"part1_provider": "gemini"})["PART1_PROVIDER"] == "claude", "A: gemini part 1 needs a Gemini key")
c = pc({"part1_provider": "gemini", "gemini_api_key": "k", "gemini_model": "gemini-2.5-pro"})
check(c["PART1_PROVIDER"] == "gemini" and c["PART1_MODEL"] == "gemini-2.5-pro" and c["FALLBACK_PROVIDER"] == "" and c["ENGINE_PROVIDER"] == "",
      f"A: gemini part 1 + model (older gemini_model setting) {c}")
# various providers, free models included (Abhi 02.11.2026)
c = pc({"engine_provider": "openrouter", "openrouter_api_key": "k", "fallback_provider": "openrouter"})
check(c["ENGINE_PROVIDER"] == "openrouter" and c["ENGINE_MODEL"] == "nvidia/nemotron-3.5-super-vl:free" and c["ENGINE_MODEL_LIGHT"] == "google/gemma-4-31b:free"
      and c["FALLBACK_PROVIDER"] == "", f"engine on OpenRouter free models; fallback = same provider -> off {c}")
check(pc({"engine_provider": "cloudflare", "cloudflare_api_token": "t"})["ENGINE_PROVIDER"] == "" and
      pc({"engine_provider": "cloudflare", "cloudflare_api_token": "t", "cloudflare_account_id": "a" * 32})["ENGINE_PROVIDER"] == "cloudflare",
      "Cloudflare needs token + account id")
c = pc({"engine_provider": "ollama", "ollama_base_url": "https://gpu.office.example:11434/", "engine_model": "gemma4:31b", "part1_provider": "ollama", "part1_model": "gemma4:12b"})
check(c["ENGINE_PROVIDER"] == "ollama" and c["OLLAMA_BASE_URL"] == "https://gpu.office.example:11434" and c["ENGINE_MODEL"] == "gemma4:31b"
      and c["PART1_PROVIDER"] == "ollama" and c["PART1_MODEL"] == "gemma4:12b", f"Ollama: URL only, models as given {c}")
check(pc({"engine_provider": "ollama", "ollama_base_url": "file:///etc"})["ENGINE_PROVIDER"] == "" and
      pc({"engine_provider": "groq", "groq_api_key": "k", "engine_model": "../../x"})["ENGINE_MODEL"] == "gpt-oss-120b",
      "bad Ollama URL -> off; unsafe model name -> provider default")
check(pc({"fallback_provider": "openai"})["FALLBACK_PROVIDER"] == "" and pc({"fallback_provider": "x", "x_api_key": "k"})["FALLBACK_PROVIDER"] == "",
      "C: fallback needs a known provider and its key")
c = pc({"fallback_provider": "gemini", "gemini_api_key": "k", "fallback_model": "$(id)", "fallback_model_light": "gemini-2.5-flash-lite"})
check(c["FALLBACK_PROVIDER"] == "gemini" and c["FALLBACK_MODEL"] == "gemini-2.5-pro" and c["FALLBACK_MODEL_LIGHT"] == "gemini-2.5-flash-lite",
      f"C: invalid model -> provider default {c}")
pf = es.provider_failure
for res, err, rc, want, label in (
        ({"is_error": True, "result": "API Error: 529 {\"type\":\"overloaded_error\"}"}, "", "1", True, "overloaded"),
        (None, "Credit balance is too low", "1", True, "no credit"),
        ({"is_error": True, "result": "Invalid API key · Please run /login"}, "", "1", True, "key refused"),
        ({"is_error": True, "result": "API Error: Connection error."}, "", "1", True, "connection"),
        ({"subtype": "error_max_turns", "is_error": True}, "429", "0", False, "max turns (case problem)"),
        (None, "overloaded", "124", False, "time-out"),
        ({"is_error": True, "result": "model: claude-x not_found_error"}, "", "1", False, "wrong model name"),
        ({"subtype": "error_during_execution", "is_error": True, "result": "The GR site returned 503 status; fetch failed"}, "", "1", False,
         "model's own text about a 503 (A2 LOW)"),
        ({"subtype": "error_during_execution", "is_error": True, "result": "x", "api_error_status": 529}, "", "1", True, "api_error_status 529")):
    check(pf(res, err, rc) is want, f"C: provider failure? {label} -> {want}")
jf2 = os.path.join(tmp, "fb.json"); ef2 = os.path.join(tmp, "fb.err")
json.dump({"type": "result", "subtype": "success", "is_error": False}, open(jf2, "w")); open(ef2, "w").write("")
r = subprocess.run([sys.executable, TOOL, "fallback_ok", jf2, ef2, "0"], capture_output=True, text=True)
check(r.returncode == 1 and "FALLBACK NO" in r.stdout, "fallback_ok: successful run -> no fallback")
json.dump({"type": "result", "subtype": "success", "is_error": True, "result": "API Error: 529 overloaded"}, open(jf2, "w"))
r = subprocess.run([sys.executable, TOOL, "fallback_ok", jf2, ef2, "1"], capture_output=True, text=True)
check(r.returncode == 0 and "FALLBACK YES" in r.stdout, "fallback_ok: overloaded -> fallback")
conf = {"MODEL": "claude-sonnet-5-5", "MODEL_LIGHT": "claude-haiku-5-5", "MODEL_REVIEW": "claude-opus-5-5", "MODEL_STRONG": "",
        "FALLBACK_PROVIDER": "gemini", "FALLBACK_MODEL": "gemini-2.5-pro", "FALLBACK_MODEL_LIGHT": "gemini-2.5-flash"}
lc = json.loads(es.litellm_config(conf))
routes = {d["model_name"]: d["litellm_params"]["model"] for d in lc["model_list"]}
check(routes == {"claude-sonnet-5-5": "gemini/gemini-2.5-pro", "claude-opus-5-5": "gemini/gemini-2.5-pro",
                 "claude-haiku-5-5": "gemini/gemini-2.5-flash", "claude-*": "gemini/gemini-2.5-flash"}
      and all(d["litellm_params"]["api_key"] == "os.environ/GEMINI_API_KEY" for d in lc["model_list"])
      and lc["litellm_settings"]["callbacks"] == "litellm_cost.handler"
      and lc["general_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY", f"C: LiteLLM routes, keys only by env name {routes}")
lc = json.loads(es.litellm_config({**conf, "FALLBACK_PROVIDER": "openai", "FALLBACK_MODEL": "gpt-6.1-sol", "FALLBACK_MODEL_LIGHT": "gpt-5.4-mini"}))
check(lc["model_list"][0]["litellm_params"] == {"model": "openai/gpt-6.1-sol", "api_key": "os.environ/OPENAI_API_KEY"}, "C: OpenAI routes")
lc = json.loads(es.litellm_config(conf, "ollama", "gemma4:31b", "gemma4:12b"))
check(lc["model_list"][0]["litellm_params"] == {"model": "ollama_chat/gemma4:31b", "api_base": "os.environ/OLLAMA_BASE_URL",
                                                 "api_key": "os.environ/OLLAMA_API_KEY"}, "Ollama route: api_base + key always by env name (A2 LOW)")
lc = json.loads(es.litellm_config(conf, "cloudflare", "@cf/x", "@cf/y"))
check(lc["model_list"][0]["litellm_params"] == {"model": "cloudflare/@cf/x", "api_key": "os.environ/CLOUDFLARE_API_KEY"}, "Cloudflare route")
# real cost from the gateway callback replaces Claude Code's Claude-priced estimate
gcf = os.path.join(tmp, "gw_cost.jsonl")
open(gcf, "w").write('{"model": "gemma-4-31b:free", "cost": 0, "in": 1000, "out": 100}\n{"model": "nemotron", "cost": 0.0, "in": 5, "out": 5}\nnot json\n')
check(es.gateway_cost(gcf) == {"gemma-4-31b:free": 0.0, "nemotron": 0.0} and es.gateway_cost(os.path.join(tmp, "absent")) is None, "gateway_cost: sums per model, bad lines skipped")
jgw = os.path.join(tmp, "gw_claude.json")
json.dump({"type": "result", "subtype": "success", "num_turns": 30, "total_cost_usd": 3.5, "modelUsage": {"claude-opus-5-5": {"costUSD": 3.5}}}, open(jgw, "w"))
run_row.update(state="running", warnings=[])
r = run("claude_result", jgw, os.path.join(tmp, "absent.err"), "0", "--gateway-cost", gcf, "--gateway-provider", "openrouter")
check(r.returncode == 0 and run_row["cost_usd"] == 0 and any("openrouter:gemma-4-31b:free $0.00" in w for w in run_row["warnings"]),
      f"claude_result via gateway: provider cost stored (free = $0), not the Claude estimate ({run_row.get('cost_usd')} {run_row['warnings']})")

ag = es.agents_json({"MODEL": "claude-sonnet-5-5", "MODEL_LIGHT": "claude-haiku-5-5", "MODEL_REVIEW": "claude-opus-5-5", "MODEL_STRONG": ""})
check(set(ag) == {"drafter", "study_writer", "related_writer", "reviewer"} and ag["drafter"]["model"] == "claude-sonnet-5-5"
      and ag["drafter"]["description"] and ag["drafter"]["prompt"], "agents: drafter on MODEL, no strong tier when not configured")
check(ag["study_writer"]["model"] == ag["related_writer"]["model"] == "claude-haiku-5-5"
      and all("extract_check" in ag[k]["description"] and "character for character" in ag[k]["prompt"] for k in ("study_writer", "related_writer"))
      and "copies" in ag["study_writer"]["description"], "agents: study_writer + related_writer on the cheap tier, verbatim rule, parts 5-6 copied")
check(ag["reviewer"]["model"] == "claude-opus-5-5" and "review.json" in ag["reviewer"]["prompt"] and "MINIMAL" in ag["reviewer"]["prompt"]
      and "§4.18" in ag["reviewer"]["prompt"], "agents: reviewer on MODEL_REVIEW, minimal edits, review.json")
check(es.agents_json({"MODEL": "claude-opus-5-5"})["reviewer"]["model"] == "claude-opus-5-5"
      and es.agents_json({"MODEL": "claude-opus-5-5"})["related_writer"]["model"] == "claude-haiku-5-5", "agents: reviewer/light defaults")
ag = es.agents_json({"MODEL": "claude-opus-5-5", "MODEL_STRONG": "claude-fable-5-1"})
check(ag["drafter_strong"]["model"] == "claude-fable-5-1" and "ENGINE_BRIEF" in ag["drafter_strong"]["prompt"], "agents: drafter_strong when configured")
agf = os.path.join(tmp, "agents.json")
r = subprocess.run([sys.executable, TOOL, "agents", agf], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, MODEL="claude-sonnet-5-5", MODEL_LIGHT="claude-haiku-5-5", MODEL_STRONG="claude-opus-5-5"))
aj = json.load(open(agf, encoding="utf-8"))
check(r.returncode == 0 and aj["drafter"]["model"] == "claude-sonnet-5-5" and aj["drafter_strong"]["model"] == "claude-opus-5-5"
      and aj["reviewer"]["model"] == "claude-opus-5-5" and aj["study_writer"]["model"] == "claude-haiku-5-5",
      f"agents CLI: file written from env ({r.stderr[:200]})")

facts = {"pages": 2, "facts": [
    {"page": 1, "document": "निर्देशपत्र", "items": [{"what": "नस्ती क्र.", "value": "संकीर्ण-2026/979/प्र.क्र.130/का.6", "clear": True},
                                                  {"what": "दिनांक", "value": "05.08.2026", "clear": True}]},
    {"page": 2, "document": "पत्र", "items": [{"what": "रक्कम", "value": "रु. १२,५००/-", "clear": True},
                                           {"what": "पद", "value": "लघुलेखक", "clear": True},
                                           {"what": "शेरा", "value": "अस्पष्ट", "clear": False}]}]}
p1 = {"heading": "भाग 1 — प्रस्तावाचे मराठी रूपांतर", "blocks": [
    {"subheading": "PDF पान 1 — निर्देशपत्र"}, {"para": "नस्ती क्र. संकीर्ण-2026/979/प्र.क्र.130/का.6, दिनांक 05.08.2026"},
    {"subheading": "PDF पान २ — पत्र"}, {"table": [["पद", "लघुलेखक"], ["रक्कम", "रु. 12,500/-"]]}]}
check(es.part1_check(facts, p1) == [], "part1check: numbers (Devanagari digits normalised), dates and posts match -> OK")
p1b = json.loads(json.dumps(p1)); p1b["blocks"][1]["para"] = "नस्ती क्र. संकीर्ण-2026/979/प्र.क्र.130/का.6, दिनांक 06.08.2026"
p1b["blocks"][3]["table"][0][1] = "लिपिक"
bad = es.part1_check(facts, p1b)
check(len(bad) == 2 and bad[0].startswith("page 1:") and "05.08.2026" in bad[0] and bad[1].startswith("page 2:"),
      f"part1check: wrong date and wrong post reported per page {bad}")
check(any("no part-1 section" in b for b in es.part1_check(facts, {"blocks": p1["blocks"][:2]})), "part1check: missing page section reported")
ff, pf = os.path.join(tmp, "facts.json"), os.path.join(tmp, "p1.json")
json.dump(facts, open(ff, "w", encoding="utf-8"), ensure_ascii=False); json.dump(p1b, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
r = subprocess.run([sys.executable, TOOL, "part1check", ff, pf], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check(r.returncode == 1 and "PART1 FAIL (2)" in r.stdout and r.stdout.count("MISMATCH") == 2, f"part1check CLI: exit 1 + MISMATCH lines ({r.stdout[:300]})")
json.dump(p1, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
r = subprocess.run([sys.executable, TOOL, "part1check", ff, pf], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check(r.returncode == 0 and "PART1 OK" in r.stdout, "part1check CLI: PART1 OK, exit 0")

check(es.short_model("claude-haiku-5-5") == "Haiku 5.5" and es.short_model("claude-opus-5") == "Opus 5", "short_model names")
stf = os.path.join(tmp, "status_ml.json")
json.dump({"state": "done", "model_log": [{"task": "पान 3", "from": "claude-opus-5-5", "to": "claude-fable-5-1", "reason": "हस्तलेख अस्पष्ट"},
                                          {"task": "भाग 1 + साधने", "from": "", "to": "claude-haiku-5-5", "reason": "यांत्रिक"}, "junk"]},
          open(stf, "w", encoding="utf-8"), ensure_ascii=False)
res = [{"total_cost_usd": 0.9, "modelUsage": {"claude-opus-5-5": {"costUSD": 0.8}, "claude-haiku-5-5": {"costUSD": 0.1}}}]
ls = es.model_lines(res, stf, 0.75)
check(ls[0] == "मॉडेल: पान 3 → Fable 5.1 (पूर्वी Opus 5.5) (हस्तलेख अस्पष्ट)" and ls[1] == "मॉडेल: भाग 1 + साधने → Haiku 5.5 (यांत्रिक)"
      and ls[2] == "मॉडेल: खर्च — Opus 5.5 $0.80, Haiku 5.5 $0.10" and ls[3].startswith("खर्च अंदाजापेक्षा जास्त — माहितीसाठी")
      and len(ls) == 4, f"model_lines: escalations, per-model cost, soft-budget warning {ls}")
check(not any(l.startswith("खर्च अंदाजापेक्षा") for l in es.model_lines(res, None, 2.0)), "model_lines: under budget -> no budget warning")
stv = os.path.join(tmp, "status_rv.json")
json.dump({"state": "done", "model_log": [], "review": {"approved": True, "changes": 1, "corrections": ["पत्रातील दिनांक 05.08.2026 केला", ""]}},
          open(stv, "w", encoding="utf-8"), ensure_ascii=False)
check(es.model_lines([], stv) == ["मॉडेल: Opus पडताळणी — पत्रातील दिनांक 05.08.2026 केला"], f"model_lines: reviewer corrections {es.model_lines([], stv)}")

# claude_result end to end: lines land in runs.warnings; over budget does NOT fail the run
run_row.update(state="running", step="तपासणी चालू", warnings=[])
open(jf, "w", encoding="utf-8").write(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 40,
                                                  "total_cost_usd": 1.2, "modelUsage": {"claude-opus-5-5": {"costUSD": 1.1},
                                                                                        "claude-haiku-5-5": {"costUSD": 0.1}}}))
r = run("claude_result", jf, ef, "0", "--wall", "300", "--status", stf, BUDGET_USD="0.75")
check(r.returncode == 0 and run_row["state"] == "running" and run_row["cost_usd"] == 1.2, f"claude_result over soft budget: not failed ({r.stderr[:200]})")
check([w for w in run_row["warnings"] if w.startswith("मॉडेल: ")] == ls[:2] + ["मॉडेल: खर्च — Opus 5.5 $1.10, Haiku 5.5 $0.10"]
      and any(w.startswith("खर्च अंदाजापेक्षा जास्त — माहितीसाठी") and "$1.20" in w for w in run_row["warnings"]),
      f"claude_result: मॉडेल lines + soft-budget warning stored {run_row['warnings']}")
r = claude({"type": "result", "subtype": "error_max_budget_usd", "is_error": True, "num_turns": 12, "total_cost_usd": 0.8})
check(r.returncode == 1 and run_row["step"].startswith("खर्च-मर्यादा ओलांडली"), f"claude_result budget stop: Marathi reason ({run_row['step']})")

# --- extracts: final verbatim guard -> mismatch fails the case; unverifiable / note-body quotes = warning lines
FONTF = next((f for f in ("/usr/share/fonts/truetype/freefont/FreeSerif.ttf", "/usr/share/fonts/opentype/freefont/FreeSerif.otf",
                          "C:/Windows/Fonts/mangal.ttf", "C:/Windows/Fonts/Nirmala.ttf") if os.path.exists(f)), None)
try:
    import pymupdf
except ImportError:
    pymupdf = None
if pymupdf and FONTF:
    LINE = "शासन सेवेत नियुक्त होणाऱ्या कर्मचाऱ्यांसाठी नवीन योजना लागू करण्यात येईल."
    ox = os.path.join(tmp, "out_x"); os.makedirs(ox)
    d = pymupdf.open(); d.new_page(); pg = d.new_page(); pg.insert_text((40, 100), LINE, fontsize=9, fontname="dv", fontfile=FONTF)
    d.save(os.path.join(ox, PROP)); d.close()
    json.dump({"state": "done", "package_pdf": PROP}, open(os.path.join(ox, "status.json"), "w", encoding="utf-8"))
    spx = os.path.join(tmp, "spec_x.json")
    json.dump({"related": [{"heading": "GR", "text": ["“" + LINE.replace("नवीन", "जुनी") + "”"], "source": "(पॅकेज PDF पृ. 2)"}]},
              open(spx, "w", encoding="utf-8"), ensure_ascii=False)
    run_row.update(state="running", step="तपासणी चालू", warnings=[])
    r = run("extracts", ox, spx, os.path.join(tmp, "absent_study.json"))
    check(r.returncode == 0 and run_row["state"] == "running"
          and any(w.startswith("पडताळणी अपूर्ण — उतारे: 1 उतारे") and "related[1]" in w for w in run_row["warnings"]),
          f"extracts: final mismatch in related -> delivered with a 'पडताळणी अपूर्ण' warning ({run_row['warnings']} {r.stderr[:200]})")
    # the same --extra sources as the in-run check: an extract marked "(पॅकेज PDF मध्ये नाही)" found in register/ = ok
    regdir = os.path.join(tmp, "reg_x"); os.makedirs(regdir)
    XL = "अतिरिक्त स्रोतातील हा उतारा पडताळणीसाठी पुरेसा लांब आहे असे समजावे."
    open(os.path.join(regdir, "r.md"), "w", encoding="utf-8").write("नोंद: " + XL + "\n")
    json.dump({"related": [{"heading": "GR", "text": ["“" + XL + "”"], "source": "(पॅकेज PDF मध्ये नाही)"}]},
              open(spx, "w", encoding="utf-8"), ensure_ascii=False)
    run_row.update(state="running", step="तपासणी चालू", warnings=[])
    r = run("extracts", ox, spx, os.path.join(tmp, "absent_study.json"), "--extra", regdir)
    check(r.returncode == 0 and run_row["warnings"] == [], f"extracts --extra: not-in-package extract found in the extra source ({run_row['warnings']})")
    check(len(es0.extra_sources()) >= 1 and all(os.path.exists(x) for x in es0.extra_sources())
          and any(x.endswith("register") for x in es0.extra_sources()), f"extra_sources: repo register/ (+ service-rules, OLDCASES, PRECEDENT when present) {es0.extra_sources()}")
    json.dump({"related": [{"heading": "GR", "text": ["“" + LINE + "”"], "source": "(पॅकेज PDF पृ. 2)"}]},
              open(spx, "w", encoding="utf-8"), ensure_ascii=False)
    run_row.update(state="running", step="तपासणी चालू", warnings=[])
    r = run("extracts", ox, spx, os.path.join(tmp, "absent_study.json"))
    check(r.returncode == 0 and run_row["state"] == "running" and run_row["warnings"] == []
          and not os.path.exists(os.path.join(ox, ".extracts.json")),
          f"extracts: all match -> no warning, no scratch file left ({run_row['warnings']})")
    # note body “…” quotes: checked against the cited पृ.N/प.वि. page, WARNING only (new check)
    json.dump({"note": {"first": "पत्रास अनुसरुन सादर.", "paras": ["शासन निर्णयात “" + LINE.replace("नवीन", "जुनी") + "” अशी तरतूद आहे (पृ.2/प.वि.)."]},
               "related": [{"heading": "GR", "text": ["“" + LINE + "”"], "source": "(पॅकेज PDF पृ. 2)"}]},
              open(spx, "w", encoding="utf-8"), ensure_ascii=False)
    r = run("extracts", ox, spx, os.path.join(tmp, "absent_study.json"))
    check(r.returncode == 0 and run_row["state"] == "running" and len(run_row["warnings"]) == 1
          and run_row["warnings"][0].startswith("मॉडेल: उतारा-तपासणी — नोंदीतील 1 अवतरणे मूळ PDF शी जुळली नाहीत"),
          f"extracts: note-body quote mismatch -> warning only ({run_row['warnings']} {r.stderr[:200]})")
else:
    print("skip  extracts (pymupdf or Devanagari font missing)")

# --- H1: secrets file instead of job env; progress through the Worker when no Supabase key is reachable
noenv = {k: v for k, v in os.environ.items() if not k.startswith("SUPABASE")}
sec = os.path.join(tmp, "secrets.env")
open(sec, "w", encoding="utf-8").write(f"SUPABASE_URL={BASE}\nSUPABASE_SERVICE_KEY={KEY}\n")
r = subprocess.run([sys.executable, TOOL, "step", "GR शोधत आहे"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(noenv, ENGINE_SECRETS=sec, CASE_ID="7", RUN_ID="11", PYTHONIOENCODING="utf-8"))
check(r.returncode == 0 and run_row["step"] == "GR शोधत आहे" and not WSTEPS, f"secrets file: runner-side command reaches Supabase without job env ({r.stderr[:200]})")
r = subprocess.run([sys.executable, TOOL, "step", "मसुदा तयार करत आहे"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(noenv, ENGINE_SECRETS=os.path.join(tmp, "absent.env"), CASE_ID="7", RUN_ID="11", RUN_TOKEN="rt-1",
                            WORKER=BASE, PYTHONIOENCODING="utf-8"))
check(r.returncode == 0 and WSTEPS == [{"auth": "Bearer rt-1", "body": {"run_id": 11, "step": "मसुदा तयार करत आहे"}}]
      and run_row["step"] == "GR शोधत आहे", f"step without Supabase key -> Worker /api/engine/step with the run token ({WSTEPS} {r.stderr[:200]})")
r = subprocess.run([sys.executable, TOOL, "step", "x"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(noenv, ENGINE_SECRETS=os.path.join(tmp, "absent.env"), CASE_ID="7", RUN_ID="11", PYTHONIOENCODING="utf-8"))
check(r.returncode == 0 and len(WSTEPS) == 1, "step with neither key nor token: no error (live status only)")

# --- H2: review gate reads the reviewer's own review.json, hashes and the CLI's modelUsage
import hashlib
rd = os.path.join(tmp, "rev"); os.makedirs(rd)
open(os.path.join(rd, "spec.json"), "w", encoding="utf-8").write('{"note": 1}')
open(os.path.join(rd, "study_part0.json"), "w", encoding="utf-8").write('{"heading": "भाग 0"}')
H_ = lambda n: hashlib.sha256(open(os.path.join(rd, n), "rb").read()).hexdigest()
cjf = os.path.join(tmp, "claude_rev.json")
def gate(review, usage, **envx):
    if review is None:
        if os.path.exists(os.path.join(rd, "review.json")): os.remove(os.path.join(rd, "review.json"))
    else:
        json.dump(review, open(os.path.join(rd, "review.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"type": "result", "subtype": "success", "modelUsage": usage}, open(cjf, "w", encoding="utf-8"))
    st_ok = {"state": "done", "prefix": "CR130_2026", "package_pdf": PROP, "proposal_pages": 5, "review": {"approved": True, "changes": 0}}
    json.dump(st_ok, open(os.path.join(out, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
    run_row.update(state="running", step="तपासणी चालू", warnings=[])
    return run("verify", out, work, "--review", rd, "--claude", cjf, VERIFY_SCRIPT=fake, MODEL_REVIEW="claude-opus-5-5", MODEL_LIGHT="claude-haiku-5-5", **envx)
used = {"claude-haiku-5-5": {"costUSD": 0.2}, "claude-opus-5-5[1m]": {"costUSD": 0.41}}
good = {"approved": True, "changes": 0, "spec_sha256": H_("spec.json"), "part0_sha256": H_("study_part0.json")}
for rv, us, label, want in (
        (None, used, "no review.json (status.json copy alone is not enough)", "review.json नाही"),
        ({**good, "approved": False, "reason": "पत्र नको"}, used, "review.json approved false", "पत्र नको"),
        ({k: v for k, v in good.items() if k != "spec_sha256"}, used, "no spec hash", "spec_sha256"),
        ({**good, "spec_sha256": "0" * 64}, used, "spec changed after approval", "spec.json बदलली"),
        ({**good, "part0_sha256": "0" * 64}, used, "part 0 changed after approval", "study_part0.json बदलली"),
        (good, {"claude-haiku-5-5": {"costUSD": 0.3}}, "reviewer model never ran", "प्रत्यक्ष चालले नाही")):
    r = gate(rv, us)
    check(r.returncode == 0 and run_row["state"] == "running"
          and any(w.startswith("अंतिम पडताळणी (Opus) मान्यता नाही — वापरण्यापूर्वी तपासा: ") and want in w for w in run_row["warnings"]),
          f"review gate: {label} -> delivered with the review warning ({run_row['warnings']})")
r = gate(good, used, MODEL="claude-sonnet-5-5")
check(r.returncode == 0 and run_row["state"] == "running" and not [w for w in run_row["warnings"] if "अंतिम पडताळणी" in w],
      f"review gate: approved, hashes match, Opus usage present -> no warning ({run_row['warnings']} {r.stderr[:200]})")
r = gate(good, used)
check(r.returncode == 0 and any("सिद्ध झाले नाही" in w and "drafter" in w for w in run_row["warnings"]),
      f"review gate: MODEL == MODEL_REVIEW, no subagent stats -> warning, not a silent pass ({run_row['warnings']})")
run_row.update(warnings=[])
r = run("verify", out, work, "--review", rd, "--claude", cjf, VERIFY_SCRIPT=fake, MODEL_REVIEW="claude-haiku-5-5", MODEL_LIGHT="claude-haiku-5-5")
check(r.returncode == 0 and any("orchestrator" in w for w in run_row["warnings"]),
      "review gate: reviewer = orchestrator model -> usage check skipped (hashes still checked), warning")
# subagent statistics in the CLI JSON (A2 MED): a reviewer subagent must have run
check(es0.subagent_runs({"subagent_stats": {"by_type": {"reviewer": 2, "drafter": 1}}}) == 2
      and es0.subagent_runs({"subagent_stats": {"by_type": {"drafter": {"count": 1}}}}) == 0
      and es0.subagent_runs({"subagent_stats": {"by_type": [{"subagent_type": "reviewer", "count": 1}]}}) == 1
      and es0.subagent_runs({}) is None, "subagent_runs: shapes parsed, absent -> None")
def gate_stats(stats):
    json.dump({"type": "result", "subtype": "success", "modelUsage": used, "subagent_stats": stats}, open(cjf, "w", encoding="utf-8"))
    run_row.update(state="running", warnings=[])
    return run("verify", out, work, "--review", rd, "--claude", cjf, VERIFY_SCRIPT=fake, MODEL_REVIEW="claude-opus-5-5", MODEL_LIGHT="claude-haiku-5-5")
r = gate_stats({"by_type": {"drafter": 3}})
check(r.returncode == 0 and any("subagent चालला नाही" in w for w in run_row["warnings"]), f"review gate: stats without reviewer -> warning ({run_row['warnings']})")
r = gate_stats({"by_type": {"reviewer": 1}})
check(r.returncode == 0 and not [w for w in run_row["warnings"] if "अंतिम पडताळणी" in w], f"review gate: reviewer subagent ran -> no warning ({run_row['warnings']})")
json.dump({"type": "result", "subtype": "success", "modelUsage": used}, open(cjf, "w", encoding="utf-8"))

# --- verify re-runs part1check on the FINAL Study part 1 (study.json "भाग 1") vs facts.json (QUALITY_AUDIT §7 M)
run_row.update(warnings=[])
r = gate(good, used)
check(r.returncode == 0 and any("facts.json नाही" in w for w in run_row["warnings"]),
      f"verify part1: facts.json absent -> warning only ({run_row['warnings']})")
json.dump(facts, open(os.path.join(rd, "facts.json"), "w", encoding="utf-8"), ensure_ascii=False)
stj = os.path.join(rd, "study.json")
json.dump({"parts": [{"heading": "भाग 0 — ब्रीफिंग", "blocks": []}, p1]}, open(stj, "w", encoding="utf-8"), ensure_ascii=False)
r = gate(good, used)
check(r.returncode == 0 and run_row["state"] == "running" and "PART1 OK" in r.stdout, f"verify part1: final part 1 matches facts -> OK ({r.stderr[:200]})")
json.dump({"parts": [{"heading": "भाग 0 — ब्रीफिंग", "blocks": []}, p1b]}, open(stj, "w", encoding="utf-8"), ensure_ascii=False)
if os.path.exists(argf): os.remove(argf)
r = gate(good, used)
pw = [w for w in run_row["warnings"] if w.startswith("पडताळणी अपूर्ण — भाग 1: भाग 1 (मराठी रूपांतर) तथ्यांशी जुळला नाही")]
check(r.returncode == 0 and run_row["state"] == "running" and pw and "05.08.2026" in pw[0] and os.path.exists(argf),
      f"verify part1: mismatch -> warning, verify_outputs still runs ({run_row['warnings']})")
# A1 H8: facts of a reply ("file": "reply_1") are not compared with the proposal's part 1
fr = json.loads(json.dumps(facts)); fr["facts"].append({"page": 1, "file": "reply_1", "items": [{"what": "दिनांक", "value": "09.09.2026", "clear": True}]})
check(es0.part1_check(fr, p1) == [], "part1check: reply facts skipped")
os.remove(stj)
json.dump(p1, open(os.path.join(rd, "study_part1.json"), "w", encoding="utf-8"), ensure_ascii=False)
r = gate(good, used)
check(r.returncode == 0 and "PART1 OK" in r.stdout, "verify part1: no study.json -> study_part1.json checked")

# --- strip_upload_prefix: a full UUID name is kept (A1 H12)
U = "3f2a9c1e-5b7d-4e2a-9c1e-1234567890ab.pdf"
check(es0.strip_upload_prefix(U) == U and es0.strip_upload_prefix("11ae057d-" + U) == U
      and es0.strip_upload_prefix("11ae057d-CR66.pdf") == "CR66.pdf" and es0.strip_upload_prefix("20261101-CR130.pdf") == "20261101-CR130.pdf",
      "strip_upload_prefix: UUID name kept, 8-hex prefix stripped, date kept")

# --- fetch refuses a non-PDF / password-protected proposal before any model runs (A2)
saved = list(DB["case_files"])
def fetch_with(data):
    DB["case_files"][:] = [{"id": 70, "case_id": 7, "kind": "proposal", "storage_path": "proposals/7/proposal/v1/x.pdf",
                            "original_name": "x.pdf", "version": 1, "created_at": "99"}]
    STORE["proposals/7/proposal/v1/x.pdf"] = data
    run_row.update(state="queued", step=None)
    return run("fetch", os.path.join(tmp, "case_rej"))
r = fetch_with(b"\xff\xd8\xff JPEG")
check(r.returncode == 1 and run_row["state"] == "failed" and run_row["step"].startswith("प्रस्ताव-फाइल PDF नाही"), f"fetch: non-PDF refused ({run_row['step']})")
try:
    import pymupdf
    d = pymupdf.open(); d.new_page(); encp = os.path.join(tmp, "enc.pdf")
    d.save(encp, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o"); d.close()
    r = fetch_with(open(encp, "rb").read())
    check(r.returncode == 1 and "पासवर्ड" in run_row["step"], f"fetch: password-protected PDF refused ({run_row['step']})")
except ImportError:
    print("skip  encrypted fetch (pymupdf missing)")
DB["case_files"][:] = saved

# --- finish: clean Marathi reason; two Study files; size limit; package first, rows after all uploads
o5 = os.path.join(tmp, "out5"); os.makedirs(o5)
json.dump({"state": "failed", "summary": "प्रस्तावाची पाने वाचता आली नाहीत — स्पष्ट स्कॅन अपलोड करा."}, open(os.path.join(o5, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
run_row.update(state="running")
r = run("finish", o5)
check(r.returncode == 1 and run_row["step"] == "प्रस्तावाची पाने वाचता आली नाहीत — स्पष्ट स्कॅन अपलोड करा.", f"finish failed state: only the Marathi summary ({run_row['step']})")
import time
for n in ("Case7_2026_Study.docx", "Case7_2026_Note_and_Letter.docx"):
    open(os.path.join(o5, n), "wb").write(b"old")
time.sleep(0.05)
for n in ("CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx", NEWP):
    open(os.path.join(o5, n), "wb").write(b"new " + n.encode())
json.dump({"state": "done", "summary": "s"}, open(os.path.join(o5, "status.json"), "w", encoding="utf-8"))
run_row.update(state="running", warnings=[]); LOG.clear(); nrows = len(DB["case_files"])
r = run("finish", o5)
new_rows = DB["case_files"][nrows:]
ups = [l["path"] for l in LOG if l["m"] == "POST" and l["path"].startswith("/storage/v1/object/")]
check(r.returncode == 0 and run_row["state"] == "done" and {f["original_name"] for f in new_rows} >= {"CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx"}
      and sum("एकाच प्रकारच्या 2 फाइल" in w for w in run_row["warnings"]) == 2, f"finish: two Study/Note files -> newest + warning ({run_row['warnings']} {r.stderr[:200]})")
posts = [l for l in LOG if l["m"] == "POST"]
first_row = next(i for i, l in enumerate(posts) if l["path"] == "/rest/v1/case_files")
check("package_pdf" in ups[0] and all(l["path"].startswith("/storage/") for l in posts[:first_row]) and first_row >= 3,
      f"finish: package uploaded first, case_files rows only after all three uploads ({[l['path'] for l in posts]})")
run_row.update(state="running", warnings=[]); nrows = len(DB["case_files"]); LOG.clear()
r = run("finish", o5, OUTPUT_MAX_BYTES="10")
check(r.returncode == 1 and run_row["state"] == "failed" and "MB पेक्षा मोठी" in run_row["step"] and len(DB["case_files"]) == nrows
      and not [l for l in LOG if l["m"] == "POST" and l["path"].startswith("/storage/")]
      and any(w.startswith("फाइल खूप मोठी") for w in run_row["warnings"]), f"finish: over the size limit -> warning + clear failure, nothing uploaded ({run_row['step']})")

srv.shutdown()
print("ALL TESTS PASSED")
