#!/usr/bin/env python3
"""engine_supabase.py — app B engine <-> Supabase (stdlib only). Used by .github/workflows/process-proposal.yml.
Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, CASE_ID, RUN_ID (keys come from the Worker at run time, masked; never stored).
Commands:
  fetch <workdir>     newest version of each input file (case_files kinds proposal / extra_doc / reply) ->
                      <workdir>/in/<kind>/<original_name>; <workdir>/case.json (case row, files, run, instructions);
                      runs: state=running, started_at, step "पाने वाचत आहे".
  step "<text>"       runs.step = text (live progress).
  log_url <url>       runs.log_url = url (Actions run page).
  finish <outdir>     <outdir>/status.json + exactly one *_Study.docx, one *_Note_and_Letter.docx and one package .pdf
                      (named as the ORIGINAL proposal file, INSTRUCTIONS §4.16; LibreOffice previews *_Study.pdf /
                      *_Note_and_Letter.pdf are ignored) -> bucket outputs/<case>/<kind>/v<n>/<name>, case_files rows,
                      runs done + summary fields, cases.stage "मसुदा तयार", activity run_done. Incomplete -> fail.
  fail "<reason>"     runs: state failed, step reason, finished_at; activity run_failed; exit 1.
                      (If the run is already failed, the earlier, more specific reason is kept.)"""
import datetime, glob, json, mimetypes, os, re, sys, urllib.error, urllib.parse, urllib.request

INPUT_KINDS = ("proposal", "extra_doc", "reply")
MIME = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def env(k):
    v = os.environ.get(k, "").strip()
    if not v:
        print(f"engine_supabase: env {k} missing", file=sys.stderr); sys.exit(2)
    return v


BASE = CASE = RUN = KEY = None


def init():
    global BASE, CASE, RUN, KEY
    BASE, KEY = env("SUPABASE_URL").rstrip("/"), env("SUPABASE_SERVICE_KEY")
    CASE, RUN = env("CASE_ID"), env("RUN_ID")
    if not (CASE.isdigit() and RUN.isdigit()):
        print("engine_supabase: CASE_ID / RUN_ID must be numeric", file=sys.stderr); sys.exit(2)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def http(method, url, body=None, headers=None, raw=False):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    h.update(headers or {})
    data = body
    if body is not None and not isinstance(body, (bytes, bytearray)):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            out = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")
    if raw:
        return out
    return json.loads(out) if out.strip() else None


def rest(method, path, body=None, prefer=None):
    return http(method, f"{BASE}/rest/v1/{path}", body, {"Prefer": prefer} if prefer else None)


def enc(path):
    return "/".join(urllib.parse.quote(s, safe="") for s in path.split("/"))


def patch_run(fields):
    rest("PATCH", f"runs?id=eq.{RUN}", fields, "return=minimal")


def activity(action, detail):
    rest("POST", "activity", {"case_id": int(CASE), "actor": None, "action": action, "detail": detail}, "return=minimal")


def safe_name(n):
    n = os.path.basename(n.replace("\\", "/")).strip()
    return n if n not in ("", ".", "..") else "file"


def newest(files, kinds):
    best = {}
    for f in files:
        if f["kind"] in kinds:
            k = (f["kind"], f["original_name"])
            if k not in best or (f["version"], f["id"]) > (best[k]["version"], best[k]["id"]):
                best[k] = f
    return sorted(best.values(), key=lambda f: (f["kind"], f["original_name"]))


def cmd_fetch(work):
    case = (rest("GET", f"cases?id=eq.{CASE}&select=*") or [None])[0]
    run = (rest("GET", f"runs?id=eq.{RUN}&select=*") or [None])[0]
    if not case or not run or str(run["case_id"]) != CASE:
        raise RuntimeError("case/run not found or run not of this case")
    files = rest("GET", f"case_files?case_id=eq.{CASE}&select=*&order=created_at.asc") or []
    inputs = newest(files, INPUT_KINDS)
    if not any(f["kind"] == "proposal" for f in inputs):
        raise RuntimeError("प्रस्ताव PDF अपलोड केलेला नाही")
    got = []
    for f in inputs:
        bucket, _, path = f["storage_path"].partition("/")
        data = http("GET", f"{BASE}/storage/v1/object/{bucket}/{enc(path)}", raw=True)
        dst = os.path.join(work, "in", f["kind"], safe_name(f["original_name"]))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(data)
        got.append({**f, "local_path": os.path.relpath(dst, work).replace("\\", "/")})
    prop = [f for f in got if f["kind"] == "proposal"]
    info = {"case": case, "run": {"id": run["id"], "instructions": run.get("instructions") or ""},
            "instructions": run.get("instructions") or "",
            "proposal_original_name": prop[-1]["original_name"],
            "inputs": got,
            "files": [{k: f[k] for k in ("id", "kind", "original_name", "version", "storage_path", "created_at")} for f in files]}
    os.makedirs(work, exist_ok=True)
    json.dump(info, open(os.path.join(work, "case.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    patch_run({"state": "running", "started_at": now(), "step": "पाने वाचत आहे"})
    print(f"fetched {len(got)} file(s) -> {work}/in")


def strip_upload_prefix(n):
    return re.sub(r"^[0-9a-f]{8}-", "", n)


def cmd_finish(out):
    try:
        st = json.load(open(os.path.join(out, "status.json"), encoding="utf-8"))
    except Exception as e:
        return cmd_fail(f"status.json वाचता आले नाही: {e}")
    if st.get("state") != "done":
        return cmd_fail(f"status.json state = {st.get('state')!r}: {st.get('summary') or ''}")
    study = glob.glob(os.path.join(out, "*_Study.docx"))
    nl = glob.glob(os.path.join(out, "*_Note_and_Letter.docx"))
    pdfs = [p for p in glob.glob(os.path.join(out, "*.pdf"))
            if not re.search(r"_(Study|Note_and_Letter|Note|Letter)\.pdf$", p)]
    props = newest(rest("GET", f"case_files?case_id=eq.{CASE}&kind=eq.proposal&select=*") or [], ("proposal",))
    names = {safe_name(f["original_name"]) for f in props} | {strip_upload_prefix(safe_name(f["original_name"])) for f in props}
    probs = []
    if len(study) != 1: probs.append(f"*_Study.docx: {len(study)}")
    if len(nl) != 1: probs.append(f"*_Note_and_Letter.docx: {len(nl)}")
    if len(pdfs) != 1: probs.append(f"package .pdf: {len(pdfs)}")
    elif os.path.basename(pdfs[0]) not in names:
        probs.append(f"package PDF नाव मूळ प्रस्ताव-फाइलचे नाही: {os.path.basename(pdfs[0])}")
    if probs:
        return cmd_fail("आउटपुट अपूर्ण — " + "; ".join(probs))
    uploaded = []
    for kind, p in (("study", study[0]), ("note_letter", nl[0]), ("package_pdf", pdfs[0])):
        name = os.path.basename(p)
        prev = rest("GET", f"case_files?case_id=eq.{CASE}&kind=eq.{kind}&select=version&order=version.desc&limit=1") or []
        ver = prev[0]["version"] + 1 if prev else 1
        path = f"{CASE}/{kind}/v{ver}/{name}"
        ctype = MIME.get(os.path.splitext(name)[1].lower()) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        http("POST", f"{BASE}/storage/v1/object/outputs/{enc(path)}", open(p, "rb").read(),
             {"Content-Type": ctype, "x-upsert": "true"})
        rest("POST", "case_files", {"case_id": int(CASE), "kind": kind, "storage_path": f"outputs/{path}",
                                    "original_name": name, "version": ver, "uploaded_by": None}, "return=minimal")
        uploaded.append({"kind": kind, "name": name, "version": ver})
    lst = lambda k: st.get(k) if isinstance(st.get(k), list) else []
    patch_run({"state": "done", "finished_at": now(), "step": "तयार", "summary": st.get("summary") or "",
               "letter_needed": bool(st.get("letter_needed")), "essential_points": lst("essential_points"),
               "grs_attached": lst("grs_attached"), "grs_missing": lst("grs_missing")})
    rest("PATCH", f"cases?id=eq.{CASE}", {"stage": "मसुदा तयार"}, "return=minimal")
    fill_case(st.get("case"))
    activity("run_done", {"run_id": int(RUN), "files": uploaded})
    print("finished:", ", ".join(f"{u['kind']} v{u['version']} {u['name']}" for u in uploaded))


CATS = {"वेतननिश्चिती", "भत्ते", "निवृत्तीवेतन", "जुनी पेन्शन", "विशेष वेतन", "विमा/GPF", "सेवा", "न्यायिक वेतन", "वैद्यकीय", "इतर"}


def fill_case(found):
    """Fill only the identity fields the user left empty at upload (category: only while it is "इतर")."""
    if not isinstance(found, dict):
        return
    cur = (rest("GET", f"cases?id=eq.{CASE}&select=cr_no,cr_year,file_no,subject,category") or [{}])[0]
    patch = {}
    for k in ("cr_no", "cr_year", "file_no", "subject"):
        v = found.get(k)
        if v not in (None, "") and cur.get(k) in (None, ""):
            v = str(v).strip()
            if k == "cr_no" and not v.isdigit(): continue
            if k == "cr_year":
                if not re.fullmatch(r"\d{4}", v): continue
                v = int(v)
            patch[k] = v
    if found.get("category") in CATS and cur.get("category") in (None, "", "इतर"):
        patch["category"] = found["category"]
    if not patch:
        return
    try:
        rest("PATCH", f"cases?id=eq.{CASE}", patch, "return=minimal")
    except Exception as e:  # e.g. the same C R no./year already exists
        activity("case_fill_skipped", {"fields": patch, "reason": str(e)[:200]})
        return
    activity("case_filled_from_pdf", {"fields": patch})


def cmd_fail(reason):
    reason = (reason or "अयशस्वी").strip()[:300]
    try:
        cur = (rest("GET", f"runs?id=eq.{RUN}&select=state,step") or [{}])[0]
        if cur.get("state") == "failed":
            print("run already failed:", cur.get("step"), file=sys.stderr); sys.exit(1)
        patch_run({"state": "failed", "step": reason, "finished_at": now()})
        activity("run_failed", {"run_id": int(RUN), "reason": reason})
    except Exception as e:
        print("engine_supabase: could not record failure:", e, file=sys.stderr)
    print("FAILED:", reason, file=sys.stderr)
    sys.exit(1)


def main(a):
    if len(a) < 2 or a[0] not in ("fetch", "step", "log_url", "finish", "fail"):
        print(__doc__); sys.exit(2)
    init()
    c, arg = a[0], " ".join(a[1:])
    if c == "fail":
        cmd_fail(arg)
    try:
        if c == "fetch": cmd_fetch(arg)
        elif c == "step": patch_run({"step": arg[:200]})
        elif c == "log_url": patch_run({"log_url": arg})
        elif c == "finish": cmd_finish(arg)
    except SystemExit:
        raise
    except Exception as e:
        if c in ("fetch", "finish"):
            cmd_fail(f"{c}: {e}")
        print(f"engine_supabase {c}: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
