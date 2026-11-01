#!/usr/bin/env python3
"""engine_supabase.py — app B engine <-> Supabase (stdlib only). Used by .github/workflows/process-proposal.yml.
Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, CASE_ID, RUN_ID (keys come from the Worker at run time, masked; never stored).
Commands:
  fetch <workdir>     the NEWEST proposal (by created_at, version, id — a corrected proposal under a new name replaces
                      the old one) + newest version of each extra_doc / reply file ->
                      <workdir>/in/<kind>/<original_name>; <workdir>/case.json (case row, files, run, instructions);
                      runs: state=running, started_at, step "पाने वाचत आहे".
  step "<text>"       runs.step = text (live progress).
  log_url <url>       runs.log_url = url (Actions run page).
  finish <outdir>     <outdir>/status.json + exactly one *_Study.docx, one *_Note_and_Letter.docx and one package .pdf
                      (named as the ORIGINAL proposal file, INSTRUCTIONS §4.16; LibreOffice previews *_Study.pdf /
                      *_Note_and_Letter.pdf are ignored) -> bucket outputs/<case>/<kind>/v<n>/<name>, case_files rows,
                      runs done + summary fields, cases.stage "मसुदा तयार", activity run_done. Incomplete -> fail.
  claude_result <claude.json> [<stderr file>] [<exit code>]
                      Claude Code `--output-format json` result -> runs.cost_usd, num_turns, duration_s. An error result
                      (max turns, API key, credit, ...) -> fail with a Marathi reason + next step; exit 1.
  verify <outdir> [<workdir>]
                      runs tools/verify_outputs.py <outdir> <PREFIX> "<package pdf>" <proposal pages> (PREFIX/package
                      from status.json `prefix` / `package_pdf`, else from the file names; proposal pages = page count
                      of the fetched proposal, else status.json `proposal_pages`). Not ALL OK -> fail with the FAIL lines.
  warn "<text>"       runs.warnings += text (non-fatal, e.g. new GRs not pushed); activity run_warning.
  fail "<reason>"     runs: state failed, step reason, finished_at; activity run_failed; exit 1.
                      (If the run is already failed, the earlier, more specific reason is kept.)"""
import datetime, glob, json, mimetypes, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

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


def upload_order(f):
    return (str(f.get("created_at") or ""), f.get("version") or 0, f.get("id") or 0)


def newest_proposal(files):
    """The one proposal of the case = the latest upload of kind proposal (any name), not the alphabetically last."""
    props = [f for f in files if f["kind"] == "proposal"]
    return max(props, key=upload_order) if props else None


def inputs_of(files):
    p = newest_proposal(files)
    return ([p] if p else []) + newest(files, ("extra_doc", "reply"))


def cmd_fetch(work):
    case = (rest("GET", f"cases?id=eq.{CASE}&select=*") or [None])[0]
    run = (rest("GET", f"runs?id=eq.{RUN}&select=*") or [None])[0]
    if not case or not run or str(run["case_id"]) != CASE:
        raise RuntimeError("case/run not found or run not of this case")
    files = rest("GET", f"case_files?case_id=eq.{CASE}&select=*&order=created_at.asc") or []
    inputs = inputs_of(files)
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
            "proposal_original_name": prop[0]["original_name"],
            "inputs": got,
            "files": [{k: f[k] for k in ("id", "kind", "original_name", "version", "storage_path", "created_at")} for f in files]}
    os.makedirs(work, exist_ok=True)
    json.dump(info, open(os.path.join(work, "case.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    patch_run({"state": "running", "started_at": now(), "step": "पाने वाचत आहे"})
    print(f"fetched {len(got)} file(s) -> {work}/in")


def strip_upload_prefix(n):
    return re.sub(r"^[0-9a-f]{8}-", "", n)


def package_pdfs(out):
    return [p for p in glob.glob(os.path.join(out, "*.pdf"))
            if not re.search(r"_(Study|Note_and_Letter|Note|Letter)\.pdf$", p)]


def cmd_finish(out):
    try:
        st = json.load(open(os.path.join(out, "status.json"), encoding="utf-8"))
    except Exception as e:
        return cmd_fail(f"status.json वाचता आले नाही: {e}")
    if st.get("state") != "done":
        return cmd_fail(f"status.json state = {st.get('state')!r}: {st.get('summary') or ''}")
    study = glob.glob(os.path.join(out, "*_Study.docx"))
    nl = glob.glob(os.path.join(out, "*_Note_and_Letter.docx"))
    pdfs = package_pdfs(out)
    prop = newest_proposal(rest("GET", f"case_files?case_id=eq.{CASE}&kind=eq.proposal&select=*") or [])
    names = {safe_name(prop["original_name"]), strip_upload_prefix(safe_name(prop["original_name"]))} if prop else set()
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


def claude_reason(res, err, rc):
    """Marathi reason + next step for a failed Claude Code run (res = parsed JSON result or None)."""
    sub = str((res or {}).get("subtype") or "")
    txt = " ".join(str(x) for x in ((res or {}).get("result"), err) if x)[:4000]
    low = txt.lower()
    if str(rc) == "124":  # `timeout` in the workflow stopped Claude
        return "वेळ संपली — अभ्यास ठरलेल्या वेळेत पूर्ण झाला नाही. पुन्हा तयार करा."
    if sub == "error_max_turns":
        return "अभ्यास अपूर्ण — कमाल पायऱ्या (max turns) संपल्या. पुन्हा तयार करा (आवश्यक तर सूचना थोडक्यात द्या)."
    if re.search(r"credit balance|billing|insufficient.?(credit|fund|quota)|payment required", low):
        return "Anthropic खात्यात credit शिल्लक नाही — credit तपासा/भरा, नंतर पुन्हा तयार करा."
    if re.search(r"invalid.{0,12}api.?key|authentication_error|x-api-key|\b401\b|unauthori[sz]ed|please run /login|not logged in", low):
        return "Anthropic key अमान्य — Settings मधील Anthropic key तपासा, नंतर पुन्हा तयार करा."
    if re.search(r"model.{0,40}(not.?found|not_found_error|does not exist|invalid)|not_found_error.{0,40}model", low):
        return "मॉडेलचे नाव चुकीचे — Settings मधील model तपासा (रिकामे ठेवल्यास डिफॉल्ट), नंतर पुन्हा तयार करा."
    if re.search(r"rate.?limit|overloaded|\b429\b|\b529\b", low):
        return "Anthropic सेवा व्यस्त (rate limit / overloaded) — थोड्या वेळाने पुन्हा तयार करा."
    tail = re.sub(r"\s+", " ", txt).strip()[:150]
    what = sub or (f"exit {rc}" if str(rc) not in ("", "0") else "error")
    return f"अभ्यास अयशस्वी ({what})" + (f": {tail}" if tail else "") + " — पुन्हा तयार करा."


def read_claude_json(path):
    try:
        raw = open(path, encoding="utf-8", errors="replace").read().strip()
    except Exception:
        return None
    res = None
    try:
        res = json.loads(raw)
    except ValueError:  # extra lines: take the last JSON object line
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    res = json.loads(line); break
                except ValueError:
                    continue
    if isinstance(res, list):  # a message list: the result is the last "result" item
        res = next((x for x in reversed(res) if isinstance(x, dict) and x.get("type") == "result"), None)
    return res if isinstance(res, dict) else None


def cmd_claude_result(args):
    res = read_claude_json(args[0]) if args else None
    err = ""
    if len(args) > 1 and os.path.exists(args[1]):
        err = open(args[1], encoding="utf-8", errors="replace").read()[-4000:]
    rc = args[2] if len(args) > 2 else "0"
    if res:
        cost = res.get("total_cost_usd", res.get("cost_usd"))
        fields = {}
        if isinstance(cost, (int, float)): fields["cost_usd"] = round(float(cost), 4)
        if isinstance(res.get("num_turns"), int): fields["num_turns"] = res["num_turns"]
        if isinstance(res.get("duration_ms"), (int, float)): fields["duration_s"] = round(res["duration_ms"] / 1000, 1)
        if fields:
            try:
                patch_run(fields)
            except Exception as e:
                print("engine_supabase: cost not stored:", e, file=sys.stderr)
        print("claude:", res.get("subtype"), "| turns", res.get("num_turns"), "| cost", cost)
    failed = res is None or bool(res.get("is_error")) or res.get("subtype") not in (None, "success") or str(rc) not in ("", "0")
    if failed:
        cmd_fail(claude_reason(res, err, rc))


def cmd_verify(args):
    out = args[0]
    work = args[1] if len(args) > 1 else ""
    try:
        st = json.load(open(os.path.join(out, "status.json"), encoding="utf-8"))
    except Exception as e:
        return cmd_fail(f"status.json वाचता आले नाही: {e}")
    if st.get("state") != "done":
        return  # `finish` records the engine's own failure reason
    prefix = str(st.get("prefix") or "").strip()
    if not prefix:
        sf = glob.glob(os.path.join(out, "*_Study.docx"))
        prefix = os.path.basename(sf[0])[: -len("_Study.docx")] if len(sf) == 1 else ""
    pkg = os.path.join(out, os.path.basename(str(st["package_pdf"]))) if st.get("package_pdf") else ""
    if not pkg or not os.path.exists(pkg):
        pp = package_pdfs(out)
        pkg = pp[0] if len(pp) == 1 else ""
    pages = None
    if work:
        try:
            cj = json.load(open(os.path.join(work, "case.json"), encoding="utf-8"))
            src = next(os.path.join(work, f["local_path"]) for f in cj["inputs"] if f["kind"] == "proposal")
            import pymupdf  # on the runner (tools/requirements-engine.txt)
            with pymupdf.open(src) as d:
                pages = len(d)
        except Exception as e:
            print(f"engine_supabase verify: proposal pages from status.json ({e})", file=sys.stderr)
    if pages is None and str(st.get("proposal_pages") or "").strip().isdigit():
        pages = int(str(st["proposal_pages"]).strip())
    missing = [x for x, v in (("PREFIX", prefix), ("package PDF", pkg), ("proposal pages", pages)) if not v]
    if missing:
        return cmd_fail("पडताळणी करता आली नाही — माहिती नाही: " + ", ".join(missing))
    script = os.environ.get("VERIFY_SCRIPT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_outputs.py")
    r = subprocess.run([sys.executable, script, out, prefix, pkg, str(pages)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    lines = (r.stdout or "").splitlines()
    print(r.stdout, end="")
    fails = [l for l in lines if l.startswith("FAIL")]
    if r.returncode == 0 and not fails and any(l.startswith("ALL OK") for l in lines):
        print("verify: ALL OK")
        return
    if fails:
        detail = "; ".join(l[5:].strip() if l.startswith("FAIL:") else l for l in fails[:6])
        if len(fails) > 6: detail += f"; … (+{len(fails) - 6})"
    else:
        errl = (r.stderr or "").strip().splitlines()
        detail = errl[-1] if errl else f"exit {r.returncode}"
    cmd_fail(f"पडताळणी (verify_outputs) अयशस्वी — {detail}"[:500])


def cmd_warn(text):
    text = (text or "").strip()[:300]
    cur = (rest("GET", f"runs?id=eq.{RUN}&select=warnings") or [{}])[0]
    w = cur.get("warnings") if isinstance(cur.get("warnings"), list) else []
    patch_run({"warnings": w + [text]})
    activity("run_warning", {"run_id": int(RUN), "warning": text})


def cmd_fail(reason):
    reason = (reason or "अयशस्वी").strip()[:500]
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
    if len(a) < 2 or a[0] not in ("fetch", "step", "log_url", "finish", "fail", "claude_result", "verify", "warn"):
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
        elif c == "claude_result": cmd_claude_result(a[1:])
        elif c == "verify": cmd_verify(a[1:])
        elif c == "warn": cmd_warn(arg)
    except SystemExit:
        raise
    except Exception as e:
        if c in ("fetch", "finish", "claude_result", "verify"):
            cmd_fail(f"{c}: {e}")
        print(f"engine_supabase {c}: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
