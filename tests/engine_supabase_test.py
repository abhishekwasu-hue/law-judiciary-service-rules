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
        {"id": 2, "case_id": 7, "kind": "proposal", "storage_path": f"proposals/7/proposal/v2/{PROP}", "original_name": PROP, "version": 2, "created_at": "2"},
        {"id": 3, "case_id": 7, "kind": "reply", "storage_path": "proposals/7/reply/v1/उत्तर.pdf", "original_name": "उत्तर.pdf", "version": 1, "created_at": "3"},
        {"id": 4, "case_id": 7, "kind": "study", "storage_path": "outputs/7/study/v1/CR130_2026_Study.docx", "original_name": "CR130_2026_Study.docx", "version": 1, "created_at": "4"},
    ],
    "activity": [],
}
STORE = {f"proposals/7/proposal/v1/{PROP}": b"%PDF old", f"proposals/7/proposal/v2/{PROP}": b"%PDF new",
         "proposals/7/reply/v1/उत्तर.pdf": b"%PDF reply"}
LOG = []


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
        if self.headers.get("apikey") != KEY or self.headers.get("Authorization") != f"Bearer {KEY}":
            return self.send(401, {"error": "auth"})
        if path.startswith("/storage/v1/object/"):
            key = path[len("/storage/v1/object/"):]
            if self.command == "GET":
                return self.send(200, raw=STORE[key]) if key in STORE else self.send(404, {"error": "nf"})
            STORE[key] = body; return self.send(200, {"Key": key})
        if path.startswith("/rest/v1/"):
            t = path[len("/rest/v1/"):]; rows = DB[t]
            if self.command == "GET": return self.send(200, match(rows, q))
            data = json.loads(body)
            if self.command == "POST":
                data["id"] = len(rows) + 100; data.setdefault("created_at", "8"); rows.append(data); return self.send(201)
            if self.command == "PATCH":
                for r in match(rows, q): r.update(data)
                return self.send(204)
        self.send(400, {"error": "route"})

    do_GET = do_POST = do_PATCH = handle_any


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
check(open(p, "rb").read() == b"%PDF new", "fetch: newest proposal version, original name")
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
check(sorted(ups) == sorted([f"/storage/v1/object/outputs/7/study/v2/CR130_2026_Study.docx",
                             "/storage/v1/object/outputs/7/note_letter/v1/CR130_2026_Note_and_Letter.docx",
                             f"/storage/v1/object/outputs/7/package_pdf/v1/{PROP}"]), "finish: 3 uploads to outputs, original names, versions")
check(STORE[f"outputs/7/package_pdf/v1/{PROP}"] == b"x" + PROP.encode(), "finish: package PDF content uploaded")
pdfh = [l for l in LOG if l["path"].endswith(PROP) and l["m"] == "POST"][0]["h"]
check(pdfh.get("Content-Type") == "application/pdf" and pdfh.get("x-upsert") == "true", "finish: content-type + upsert")
new = [f for f in DB["case_files"] if f["id"] >= 100]
check({(f["kind"], f["version"], f["storage_path"].split("/")[0]) for f in new} == {("study", 2, "outputs"), ("note_letter", 1, "outputs"), ("package_pdf", 1, "outputs")}, "finish: case_files rows")
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

# --- verify: runs verify_outputs with PREFIX / package / proposal pages; FAIL lines become the reason
fake = os.path.join(tmp, "fake_verify.py"); argf = os.path.join(tmp, "verify_args.json")
open(fake, "w", encoding="utf-8").write(
    "import json, os, sys\n"
    f"json.dump(sys.argv[1:], open({argf!r}, 'w', encoding='utf-8'), ensure_ascii=False)\n"
    "if os.environ.get('FAKE_FAIL'):\n"
    "    print('FAIL: Study: 3 runs without DVOT-SurekhMR'); print('FAIL: page 4: no page stamp'); print('FIX THE FAILS ABOVE | pages 9')\n"
    "else:\n"
    "    print('ALL OK | pages 9 | toc 3')\n")
st["prefix"] = "CR130_2026"; st["package_pdf"] = PROP; st["proposal_pages"] = 5
json.dump(st, open(os.path.join(out, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
run_row.update(state="running", step="तपासणी चालू")
r = run("verify", out, work, VERIFY_SCRIPT=fake)
a = json.load(open(argf, encoding="utf-8"))
check(r.returncode == 0 and run_row["state"] == "running", f"verify ALL OK: exit 0 ({r.stderr[:200]})")
check(a[1] == "CR130_2026" and os.path.basename(a[2]) == PROP and a[0] == out, "verify: outdir, PREFIX, package PDF passed")
check(a[3] == "5", f"verify: proposal pages from status.json when the PDF cannot be read ({a[3]})")
try:
    import pymupdf
    d = pymupdf.open()
    for _ in range(3): d.new_page()
    d.save(os.path.join(work, "in", "proposal", PROP)); d.close()
    r = run("verify", out, work, VERIFY_SCRIPT=fake)
    check(json.load(open(argf, encoding="utf-8"))[3] == "3", "verify: proposal pages = page count of the fetched proposal")
except ImportError:
    print("skip  verify page count (pymupdf not installed)")
r = run("verify", out, work, VERIFY_SCRIPT=fake, FAKE_FAIL="1")
check(r.returncode == 1 and run_row["state"] == "failed" and "DVOT-SurekhMR" in run_row["step"] and "page 4" in run_row["step"],
      f"verify FAIL: case failed with the FAIL lines ({run_row['step']})")

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
out3 = os.path.join(tmp, "out3"); os.makedirs(out3)
for n in ("CR130_2026_Study.docx", "CR130_2026_Note_and_Letter.docx", PROP):
    open(os.path.join(out3, n), "wb").write(b"x")
json.dump({"state": "done", "summary": "s"}, open(os.path.join(out3, "status.json"), "w", encoding="utf-8"))
run_row.update(state="running")
r = run("finish", out3)
check(r.returncode == 1 and "मूळ प्रस्ताव" in run_row["step"], "finish: package named after the OLD proposal is refused")

srv.shutdown()
print("ALL TESTS PASSED")
