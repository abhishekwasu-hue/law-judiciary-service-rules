#!/usr/bin/env python3
"""Stdlib test for tools/engine_supabase.py: a local http.server mocks Supabase REST + Storage.
Runs fetch -> step -> finish (fake outputs), then a fail case (missing outputs). Run: py tests/engine_supabase_test.py"""
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
        out = sorted(out, key=lambda r: r.get(col) or 0, reverse=(d == "desc"))
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
                data["id"] = len(rows) + 100; rows.append(data); return self.send(201)
            if self.command == "PATCH":
                for r in match(rows, q): r.update(data)
                return self.send(204)
        self.send(400, {"error": "route"})

    do_GET = do_POST = do_PATCH = handle_any


def run(*args):
    env = dict(os.environ, SUPABASE_URL=BASE, SUPABASE_SERVICE_KEY=KEY, CASE_ID="7", RUN_ID="11", PYTHONIOENCODING="utf-8")
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
      "grs_missing": [{"date": "12.03.2014", "title": "t2"}]}
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

srv.shutdown()
print("ALL TESTS PASSED")
