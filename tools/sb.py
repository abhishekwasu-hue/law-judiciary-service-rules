#!/usr/bin/env python3
"""Supabase helper for GitHub Actions (stdlib only). Needs env SUPABASE_URL, SUPABASE_SERVICE_KEY.
  sb.py fetch <run_id>            download this run's proposal + reference docs into inbox/, write inbox/<PREFIX>.json, print PREFIX
  sb.py progress <run_id> <word>  live progress for the dashboard
  sb.py watch <run_id> <PREFIX>   loop: copy cases/<PREFIX>/progress.txt to the run (background)
  sb.py finish <run_id> <PREFIX>  upload outputs + status.json results, update run and case
  sb.py fail <run_id> <message>
  sb.py seed-gr                   only gr_library
  sb.py seed                      gr_library from pdf/gr/INDEX.tsv (+ PDFs to the gr-library bucket), register/*.md -> register_chunks
  sb.py backup                    export every table to the private 'backups' bucket
Case files never go into the git repo."""
import json, os, re, sys, time, glob, urllib.request, urllib.parse, urllib.error, datetime

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TABLES = ["members", "invites", "cases", "case_files", "runs", "letters", "gr_library", "activity", "settings"]


def req(method, path, body=None, headers=None, raw=False):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    data = None
    if body is not None and not isinstance(body, (bytes, bytearray)):
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    elif body is not None:
        data = bytes(body)
    h.update(headers or {})
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL + path, data=data, headers=h, method=method), timeout=300) as r:
                b = r.read()
                return b if raw else (json.loads(b) if b else None)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code < 500 or i == 3:
                raise RuntimeError(f"{method} {path}: {e.code} {msg}")
        except urllib.error.URLError:
            if i == 3: raise
        time.sleep(3 * (i + 1))


def rest(method, table, query="", body=None, prefer="return=representation"):
    return req(method, f"/rest/v1/{table}{('?' + query) if query else ''}", body, {"Prefer": prefer})


def one(table, query):
    r = rest("GET", table, query)
    return r[0] if r else None


def upload(bucket, path, file_path, ctype):
    with open(file_path, "rb") as f:
        req("POST", f"/storage/v1/object/{bucket}/{urllib.parse.quote(path)}", f.read(), {"Content-Type": ctype, "x-upsert": "true"}, raw=True)


def download(bucket, path, out):
    b = req("GET", f"/storage/v1/object/{bucket}/{urllib.parse.quote(path)}", raw=True)
    with open(out, "wb") as f:
        f.write(b)


def ascii_name(s):
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s or "").strip("_")
    return s or "file"


def gh_out(k, v):
    p = os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p, "a") as f:
            f.write(f"{k}={v}\n")


def fetch(run_id):
    run = one("runs", f"id=eq.{run_id}&select=*")
    case = one("cases", f"id=eq.{run['case_id']}&select=*")
    prefix = case["prefix"]
    os.makedirs("inbox", exist_ok=True)
    files = rest("GET", "case_files", f"case_id=eq.{case['id']}&select=*&order=version.desc,id.desc")
    prop = next((f for f in files if f["kind"] == "proposal"), None)
    if not prop:
        raise RuntimeError("no proposal file")
    download(prop["bucket"], prop["storage_path"], f"inbox/{prefix}.pdf")
    extras = []
    for i, f in enumerate([f for f in files if f["kind"] in ("extra_doc", "reply")], 1):
        ext = os.path.splitext(f["storage_path"])[1] or ".pdf"
        p = f"inbox/{prefix}_ref{i}{ext}"
        download(f["bucket"], f["storage_path"], p)
        extras.append(f"{p}  ({'उत्तर' if f['kind'] == 'reply' else 'संदर्भ'}: {f.get('original_name') or ''})")
    previous = []
    if run["mode"] != "study":
        os.makedirs(f"cases/{prefix}/previous", exist_ok=True)
        seen = set()
        for f in files:
            if f["kind"] in ("study", "note_letter") and f["kind"] not in seen:
                seen.add(f["kind"])
                p = f"cases/{prefix}/previous/{os.path.basename(f['storage_path'])}"
                download(f["bucket"], f["storage_path"], p); previous.append(p)
        letters = rest("GET", "letters", f"case_id=eq.{case['id']}&select=ref_no,addressed_to,sent_date,reply_due&order=id")
        if letters:
            previous.append("letters sent: " + json.dumps(letters, ensure_ascii=False))
    json.dump({"file_no": case.get("file_no") or "", "original_name": prop.get("original_name") or f"{prefix}.pdf", "mode": run["mode"], "extras": extras,
               "instructions": run.get("instructions") or "", "previous": previous},
              open(f"inbox/{prefix}.json", "w", encoding="utf-8"), ensure_ascii=False)
    log = f"{os.environ.get('GITHUB_SERVER_URL','')}/{os.environ.get('GITHUB_REPOSITORY','')}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"
    rest("PATCH", "runs", f"id=eq.{run_id}", {"state": "running", "progress": "reading", "log_url": log})
    if run["mode"] == "study" and case["stage"] in ("प्राप्त", "माहिती प्राप्त"):
        rest("PATCH", "cases", f"id=eq.{case['id']}", {"stage": "अभ्यास चालू"})
    gh_out("prefix", prefix)
    print(prefix)


def progress(run_id, word):
    rest("PATCH", "runs", f"id=eq.{run_id}", {"progress": word}, prefer="return=minimal")


def watch(run_id, prefix):
    last = None
    p = f"cases/{prefix}/progress.txt"
    while True:
        try:
            w = open(p, encoding="utf-8").read().strip().split()[0] if os.path.exists(p) else None
            if w and w != last:
                progress(run_id, w); last = w
        except Exception as e:
            print("watch:", e)
        time.sleep(20)


def next_version(case_id, kind):
    r = rest("GET", "case_files", f"case_id=eq.{case_id}&kind=eq.{kind}&select=version&order=version.desc&limit=1")
    return (r[0]["version"] + 1) if r else 1


def finish(run_id, prefix):
    run = one("runs", f"id=eq.{run_id}&select=*")
    case = one("cases", f"id=eq.{run['case_id']}&select=*")
    out = f"cases/{prefix}"
    st = {}
    try:
        st = json.load(open(f"{out}/status.json", encoding="utf-8"))
    except Exception:
        pass
    prop = one("case_files", f"case_id=eq.{case['id']}&kind=eq.proposal&select=original_name&order=version.desc&limit=1") or {}
    orig = os.path.basename(prop.get("original_name") or f"{prefix}.pdf")
    pkg = orig if os.path.exists(f"{out}/{orig}") else f"{prefix}_Proposal_with_GRs.pdf"
    wanted = [("study", f"{prefix}_Study.docx", None), ("note_letter", f"{prefix}_Note_and_Letter.docx", None),
              ("package_pdf", pkg, orig),
              ("reminder", f"{prefix}_Reminder.docx", None), ("cabinet_note", f"{prefix}_Cabinet_Note.docx", None)]
    uploaded = []
    for kind, name, orig in wanted:
        p = f"{out}/{name}"
        if not os.path.exists(p):
            continue
        v = next_version(case["id"], kind)
        sp = f"{case['id']}/v{v}/{kind}{os.path.splitext(name)[1]}"
        ctype = "application/pdf" if name.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        upload("outputs", sp, p, ctype)
        rest("POST", "case_files", "", {"case_id": case["id"], "run_id": int(run_id), "kind": kind, "bucket": "outputs",
                                        "storage_path": sp, "original_name": orig or name, "version": v,
                                        "size_bytes": os.path.getsize(p), "uploaded_by": None}, prefer="return=minimal")
        uploaded.append(kind)
    state = "done" if (st.get("state") == "done" and uploaded) else "failed"
    patch = {"state": state, "progress": "done" if state == "done" else "failed",
             "finished_at": datetime.datetime.utcnow().isoformat() + "Z",
             "summary": st.get("summary"), "doubts": st.get("doubts") or [],
             "error": None if state == "done" else (st.get("error") or "outputs missing")}
    if run["mode"] == "study":
        patch.update({"letter_needed": st.get("letter_needed"), "essential_points": st.get("essential_points") or [],
                      "grs_attached": st.get("grs_attached") or [], "grs_missing": st.get("grs_missing") or st.get("not_found") or [],
                      "briefing": st.get("briefing")})
    rest("PATCH", "runs", f"id=eq.{run_id}", patch, prefer="return=minimal")
    if state == "done" and run["mode"] == "study" and case["stage"] in ("प्राप्त", "अभ्यास चालू", "माहिती प्राप्त"):
        rest("PATCH", "cases", f"id=eq.{case['id']}", {"stage": "मसुदा तयार"}, prefer="return=minimal")
    for g in st.get("grs_attached") or []:
        code = str(g.get("code") or "").strip()
        if code:
            row = one("gr_library", f"code=eq.{urllib.parse.quote(code)}&select=used_in_cases")
            if row and case["id"] not in row["used_in_cases"]:
                rest("PATCH", "gr_library", f"code=eq.{urllib.parse.quote(code)}", {"used_in_cases": row["used_in_cases"] + [case["id"]]}, prefer="return=minimal")
    seed_gr()
    print(state, uploaded)
    if state != "done":
        sys.exit(1)


def fail(run_id, msg):
    rest("PATCH", "runs", f"id=eq.{run_id}", {"state": "failed", "progress": "failed", "error": msg[:500],
                                              "finished_at": datetime.datetime.utcnow().isoformat() + "Z"}, prefer="return=minimal")


def seed_gr():
    idx = "pdf/gr/INDEX.tsv"
    if not os.path.exists(idx):
        return
    rows = {}
    for i, line in enumerate(open(idx, encoding="utf-8")):
        if i == 0 or not line.strip():
            continue
        c = (line.rstrip("\n").split("\t") + [""] * 5)[:5]
        code = c[0].strip()
        pdf = f"pdf/gr/{code}.pdf"
        rec = {"code": code, "date": c[1][:10] or None, "department": c[2] or None, "title": c[3] or None,
               "source_url": f"https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{code}.pdf" if code.isdigit() else None,
               "storage_path": f"{ascii_name(code)}.pdf" if os.path.exists(pdf) else None}
        if rec["date"] and not re.match(r"^\d{4}-\d{2}-\d{2}$", rec["date"]):
            rec["date"] = None
        rows[code] = rec
    have = {r["code"] for r in rest("GET", "gr_library", "select=code&storage_path=not.is.null")}
    for code, rec in rows.items():
        if rec["storage_path"] and code not in have:
            upload("gr-library", rec["storage_path"], f"pdf/gr/{code}.pdf", "application/pdf")
    if rows:
        rest("POST", "gr_library", "on_conflict=code", list(rows.values()), prefer="resolution=merge-duplicates,return=minimal")
    print("gr_library:", len(rows))


def seed_register():
    chunks = []
    for path in sorted(glob.glob("register/*.md")):
        src = os.path.basename(path)
        heading, page, para, buf = None, None, 0, []

        def flush():
            nonlocal buf, para
            t = "\n".join(buf).strip()
            if len(t) > 20:
                para += 1
                m = re.findall(r"पृ\.?\s*([0-9०-९]+)", t)
                chunks.append({"source": src, "heading": heading, "page": m[0] if m else page, "para": para, "body": t[:6000]})
            buf = []
        for line in open(path, encoding="utf-8"):
            if line.startswith("#"):
                flush(); heading = line.strip("# \n")[:300]
                m = re.findall(r"पृ\.?\s*([0-9०-९]+)", heading); page = m[0] if m else None
            elif not line.strip():
                flush()
            else:
                buf.append(line.rstrip())
        flush()
    rest("DELETE", "register_chunks", "id=gt.0", prefer="return=minimal")
    for i in range(0, len(chunks), 500):
        rest("POST", "register_chunks", "", chunks[i:i + 500], prefer="return=minimal")
    print("register_chunks:", len(chunks))


def backup():
    day = datetime.date.today().isoformat()
    os.makedirs("/tmp/backup", exist_ok=True)
    for t in TABLES:
        rows, off = [], 0
        while True:
            r = req("GET", f"/rest/v1/{t}?select=*", None, {"Range": f"{off}-{off + 999}"})
            rows += r
            if len(r) < 1000:
                break
            off += 1000
        p = f"/tmp/backup/{t}.json"
        json.dump(rows, open(p, "w", encoding="utf-8"), ensure_ascii=False, default=str)
        upload("backups", f"{day}/{t}.json", p, "application/json")
        print(t, len(rows))


if __name__ == "__main__":
    if not URL or not KEY:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY missing")
    cmd, *a = sys.argv[1:]
    {"fetch": lambda: fetch(a[0]), "progress": lambda: progress(a[0], a[1]), "watch": lambda: watch(a[0], a[1]),
     "finish": lambda: finish(a[0], a[1]), "fail": lambda: fail(a[0], " ".join(a[1:])),
     "seed": lambda: (seed_gr(), seed_register()), "seed-gr": seed_gr, "backup": backup}[cmd]()
