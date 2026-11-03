#!/usr/bin/env python3
"""engine_supabase.py — app B engine <-> Supabase (stdlib only). Used by .github/workflows/process-proposal.yml.
Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, CASE_ID, RUN_ID (keys come from the Worker at run time, masked; never stored).
Commands ("deliver with warnings", Abhi 02.11.2026: drafts are never thrown away — only HARD problems fail a case):
  fetch <workdir>     ALL proposal uploads: the NEWEST (by created_at, version, id) is "the proposal" ->
                      <workdir>/in/proposal/<original_name>; every other proposal name -> in/extra_doc/ + a warning
                      (A1 H13); newest version of each extra_doc / reply / approval / court_notice file ->
                      in/<kind>/<original_name> (approval, court_notice: C28, 03.11.2026). case.json "outputs" = the
                      drafts ticked for this run (runs.outputs in DRAFT_KEYS order; null = column missing or not set =
                      the engine's own choice) and "reminder_next" (§4.21 N: 1 + earlier done runs that ticked "reminder"). A proposal
                      that is not a PDF or is password-protected is refused at once (Marathi reason, no model run).
                      <workdir>/case.json (case row, files, run, instructions); runs: state=running, started_at, step.
  case_meta <out.json> [<workdir>]
                      runner-side, right after fetch: {proposal_original_name (newest proposal row in Supabase),
                      proposal_pages (page count of the fetched proposal PDF, null if unreadable), outputs (runs.outputs,
                      as in case.json)} — for verify --case-meta.
  step "<text>"       runs.step = text (live progress).
  note "<text>"       an INFORMATION line (not a warning) appended to runs.warnings with the UI's info prefix "मॉडेल: "
                      (added when missing) — shown only to the owner, never in the warning / red lists (dashboard-app
                      RunProgress MODEL_PREFIX, format.ts runWarningTexts); no Worker or schema change. Used for the
                      run's time split (tools/run_timeline.py --line). Never fails the run (exit 0).
  log_url <url>       runs.log_url = url (Actions run page).
  finish <outdir>     <outdir>/status.json + one *_Study.docx, one *_Note_and_Letter.docx (several, e.g. PREFIX changed:
                      the one of status.json `prefix`, else the newest by mtime + a warning) and one package .pdf (named
                      as the ORIGINAL proposal file, INSTRUCTIONS §4.16; previews *_Study.pdf / *_Note_and_Letter.pdf are
                      ignored). Sizes are checked first (> 50 MB, OUTPUT_MAX_BYTES -> warning + clear failure); the
                      package is uploaded FIRST, then Study, Note_and_Letter -> bucket outputs/<case>/<kind>/v<n>/file<ext>
                      (ASCII key; the real name only in case_files.original_name); case_files rows are inserted only after
                      all three uploads succeeded; runs done + summary fields, status.json `warnings`, cases.stage
                      "मसुदा तयार", activity run_done. status.json state not "done" -> fail with ONLY its Marathi summary.
                      Optional outputs (02.11.2026, docs/COURT_AND_ORDERS_RESEARCH.md B7–B9): *_Order_Draft.docx ->
                      kind "order_draft", *_Parawise.docx -> kind "parawise" (same ASCII key style), uploaded when
                      present (status.json `outputs_extra` = ["order_draft", "parawise"] or [{"kind", "file"}]; C28 draft
                      keys gr / corrigendum / circular / memo / notification count as order_draft, letter / reminder are
                      in the Note_and_Letter; a
                      listed kind whose file is absent -> warning); absence is fine; more than one of a kind, or a refused upload (enum value missing until
                      migration 0006 is applied) -> a runs.warnings line, never a failure.
  claude_result <claude.json> [<stderr file>] [<exit code>] [--part1 <part1.json>] [--part1-no-cost] [--first <first.json>]
                [--killed] [--wall <seconds>] [--status <status.json>] [--gateway-cost F --gateway-provider P]
                      Claude Code `--output-format json` result(s) -> runs.cost_usd and num_turns = SUM of the main run,
                      the parallel Study-part-1 run (--part1; with --part1-no-cost it went through the gateway: parsed for
                      warnings only, its cost is already in the gateway file) and the first, failed run before a provider
                      fallback (--first); duration_s = --wall, else the longest run. --killed (or rc 124/137/143) with no
                      JSON: an estimated cost_usd = BUDGET_USD (else 0.75) is stored + a warning. An error result of the
                      MAIN run (max turns, time-out, killed, budget, API …): when --status is "done" and the three outputs
                      exist in its directory -> only a warning "अभ्यास नीट संपला नाही (…) — तयार मसुदे जतन केले" (exit 0;
                      verify / extracts / finish still decide); otherwise fail with a Marathi reason + next step (exit 1).
                      A part-1 error alone is only a warning. Adds "मॉडेल: " lines (status.json model_log, review
                      corrections, per-model cost) and, over BUDGET_USD, the information line "खर्च अंदाजापेक्षा जास्त —
                      माहितीसाठी (…)".
  verify <outdir> [<workdir>] [--review <work dir>] [--claude <claude.json>] [--case-meta <meta.json>]
                      runs tools/verify_outputs.py <outdir> <PREFIX> "<package pdf>" <proposal pages> --original-name …
                      (PREFIX/package from status.json, else the file names; pages + original name from --case-meta
                      (runner-written) when given, else <workdir>/case.json + the fetched proposal, else status.json
                      `proposal_pages`, else map.json). FAIL lines are classified: HARD (exit 1, case failed) = an output
                      missing / unreadable ("… opens"), internal ids / repo paths (confidentiality), annotations on the
                      proposal pages, or verify_outputs itself not running; every other FAIL -> a runs.warnings line
                      "पडताळणी अपूर्ण — <check>: <detail>" (exit 0). "ALL OK" printed when clean. C28: every draft
                      ticked in runs.outputs (--case-meta `outputs`, else case.json) must exist — a missing one is a
                      SOFT warning "पडताळणी अपूर्ण — निवडलेला मसुदा तयार झाला नाही: <label>" (§4.26).
                      --review: review_gate (review.json + hashes; a "reviewer" subagent in the CLI's subagent statistics,
                      else MODEL_REVIEW in modelUsage) — not approved / hash mismatch / review.json missing -> warning
                      "अंतिम पडताळणी (Opus) मान्यता नाही — वापरण्यापूर्वी तपासा: <reason>"; reviewer = drafter or
                      orchestrator model without subagent statistics -> a warning (never a silent pass). part1check on the
                      FINAL Study part 1 vs <work>/facts.json (proposal facts only): mismatch -> "पडताळणी अपूर्ण — भाग 1: …".
  extracts <outdir> <spec.json> <study.json> [<ocr dir>] [--extra PATH ...]
                      tools/extract_check.py on the delivered `related` + Study part 3 (+ note body “…” quotes) vs the
                      package PDF, with the in-run --extra sources (register/, service-rules/, OLDCASES/t, PRECEDENT; A1
                      H7). Never fails the case: a MISMATCH -> "पडताळणी अपूर्ण — उतारे: …"; unverifiable / note-body
                      results -> "मॉडेल: उतारा-तपासणी — …" lines.
  config <cfg.json>   (local) the non-secret run settings from the Worker's /api/engine/config JSON as KEY=VALUE
                      lines for $GITHUB_ENV: MODEL (main tier = drafter, every quality-critical task; from Settings,
                      default claude-opus-5-5; Abhi's plan: Sonnet),
                      MODEL_LIGHT (mechanical tier + orchestrating session; default claude-haiku-5-5), MODEL_STRONG
                      (optional one-way escalation tier; default off), MODEL_REVIEW (final reviewer/approver;
                      default claude-opus-5-5), EFFORT (default medium), BUDGET_USD (SOFT,
                      default 0.75 — information only, never stops or degrades the run). Invalid values -> defaults.
  agents <out.json>   (local) Claude Code --agents JSON: drafter (MODEL), study_writer + related_writer
                      (MODEL_LIGHT), reviewer (MODEL_REVIEW) [+ drafter_strong (MODEL_STRONG)].
  part1check <facts.json> <study_part1.json>
                      (local) cheap-tier Study part 1 vs the main tier's facts: every number/date (and Devanagari
                      name/post) of a page must occur in that page's part-1 text; facts with "file" other than "proposal"
                      (reply_<n>, extra_<n>) are skipped. PART1 OK / MISMATCH lines, exit 1.
  warn "<text>"       runs.warnings += text (non-fatal, e.g. new GRs not pushed); activity run_warning.
  fail "<reason>"     runs: state failed, step reason, finished_at; activity run_failed; exit 1.
                      (If the run is already failed, the earlier, more specific reason is kept.)"""
import datetime, glob, json, mimetypes, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

INPUT_KINDS = ("proposal", "extra_doc", "reply", "approval", "court_notice")   # approval / court_notice: C28 (03.11.2026)
# C28 "कोणते मसुदे हवेत?" (INSTRUCTIONS §4.28, 03.11.2026): the drafts the user ticked for a run (runs.outputs), fixed order
DRAFT_KEYS = ("letter", "reminder", "gr", "corrigendum", "circular", "memo", "notification", "parawise")
DRAFT_LABEL = {"letter": "पत्र", "reminder": "स्मरणपत्र", "gr": "शासन निर्णय", "corrigendum": "शुद्धिपत्रक",
               "circular": "परिपत्रक", "memo": "ज्ञापन", "notification": "अधिसूचना", "parawise": "परिच्छेदनिहाय उत्तर"}
ORDER_KEYS = ("gr", "corrigendum", "circular", "memo", "notification")
# body heading paragraph that tools/build_order.py writes for each order type (BODY_HEAD there; kept equal)
ORDER_HEAD = {"gr": "शासन निर्णय :-", "corrigendum": "शासन शुद्धिपत्रक :-", "circular": "परिपत्रक :-",
              "memo": "ज्ञापन :-", "notification": "अधिसूचना"}
MIME = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


SECRETS_FILE = "/tmp/engine-secrets/secrets.env"


def secret_file_values():
    """KEY=VALUE lines of the workflow's secrets file (ENGINE_SECRETS, default /tmp/engine-secrets/secrets.env; dir 700,
    owned by the runner user). H1 (QUALITY_AUDIT §7): the Supabase service key is no longer put into the job env, so the
    Claude step (another unix user) can neither inherit nor read it; runner-side steps read it from this file."""
    path = os.environ.get("ENGINE_SECRETS") or SECRETS_FILE
    out = {}
    try:
        for line in open(path, encoding="utf-8"):
            k, sep, v = line.rstrip("\n").partition("=")
            if sep and k.strip(): out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def lookup(k):
    return os.environ.get(k, "").strip() or secret_file_values().get(k, "")


def has_supabase():
    return bool(lookup("SUPABASE_URL") and lookup("SUPABASE_SERVICE_KEY"))


def env(k):
    v = lookup(k)
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
    return ([p] if p else []) + newest(files, ("extra_doc", "reply", "approval", "court_notice"))


def norm_outputs(v):
    """runs.outputs -> the ticked draft keys in the fixed order (DRAFT_KEYS), or None (column missing / null = legacy
    automatic choice, C28). Unknown keys are dropped (the Worker validates them)."""
    if not isinstance(v, list):
        return None
    got = {x for x in v if isinstance(x, str)}
    return [k for k in DRAFT_KEYS if k in got]


def reminder_next(runs, this_run):
    """§4.21 number of the next स्मरणपत्र: 1 + earlier DONE runs of the case whose ticked outputs had "reminder"."""
    n = sum(1 for r in runs or [] if str(r.get("id")) != str(this_run) and r.get("state") == "done"
            and "reminder" in (norm_outputs(r.get("outputs")) or []))
    return n + 1


def older_proposals(files):
    """A1 H13: every OTHER proposal upload (newest version per name, a name other than the newest proposal's) — fetched
    too, as extra documents (e.g. a phone scan split in two PDFs), never silently dropped."""
    p = newest_proposal(files)
    if not p:
        return []
    return [f for f in newest(files, ("proposal",)) if f["original_name"] != p["original_name"]]


def proposal_problem(data):
    """A2: refuse a proposal the engine cannot read BEFORE any model runs. -> Marathi reason, or None.
    Not a PDF (no %PDF header in the first 1 KB) or password-protected (pymupdf needs_pass). A PDF pymupdf cannot open
    for another reason is left to prep_pages (pymupdf often repairs it) -> None."""
    if b"%PDF" not in (data or b"")[:1024]:
        return ("प्रस्ताव-फाइल PDF नाही — प्रस्ताव PDF स्वरूपात (स्कॅन PDF) अपलोड करा, नंतर पुन्हा तयार करा.")
    try:
        import pymupdf
    except ImportError:
        return None
    try:
        with pymupdf.open(stream=data, filetype="pdf") as d:
            if d.needs_pass or d.is_encrypted:
                return ("प्रस्ताव PDF पासवर्ड-संरक्षित आहे — पासवर्ड नसलेली प्रत अपलोड करा, नंतर पुन्हा तयार करा.")
    except Exception:
        return None
    return None


def unique_dst(work, kind, name, taken):
    dst = os.path.join(work, "in", kind, safe_name(name))
    stem, ext = os.path.splitext(dst)
    k = 2
    while dst in taken:
        dst = f"{stem} ({k}){ext}"; k += 1
    taken.add(dst)
    return dst


def cmd_fetch(work):
    case = (rest("GET", f"cases?id=eq.{CASE}&select=*") or [None])[0]
    run = (rest("GET", f"runs?id=eq.{RUN}&select=*") or [None])[0]
    if not case or not run or str(run["case_id"]) != CASE:
        raise RuntimeError("case/run not found or run not of this case")
    files = rest("GET", f"case_files?case_id=eq.{CASE}&select=*&order=created_at.asc") or []
    inputs = inputs_of(files)
    if not any(f["kind"] == "proposal" for f in inputs):
        return cmd_fail("प्रस्ताव PDF अपलोड केलेला नाही — प्रस्ताव अपलोड करा, नंतर पुन्हा तयार करा.")
    older = older_proposals(files)
    got, taken, warns = [], set(), []
    for f in inputs + [dict(o, kind="extra_doc", from_kind="proposal") for o in older]:
        bucket, _, path = f["storage_path"].partition("/")
        data = http("GET", f"{BASE}/storage/v1/object/{bucket}/{enc(path)}", raw=True)
        if f["kind"] == "proposal" and not f.get("from_kind"):
            why = proposal_problem(data)
            if why:
                return cmd_fail(why)
        dst = unique_dst(work, f["kind"], f["original_name"], taken)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(data)
        got.append({**f, "local_path": os.path.relpath(dst, work).replace("\\", "/")})
    prop = [f for f in got if f["kind"] == "proposal"]
    if older:
        warns.append(f"प्रस्तावाच्या {len(older) + 1} फाइल अपलोड आहेत — नवीनतम '{prop[0]['original_name']}' प्रस्ताव म्हणून घेतली; "
                     f"इतर ({', '.join(o['original_name'] for o in older)}) अतिरिक्त कागदपत्र म्हणून वाचल्या"[:300])
    outputs = norm_outputs(run.get("outputs"))   # absent column (migration 0008 not applied) -> None
    try:
        runs = rest("GET", f"runs?case_id=eq.{CASE}&select=*&order=id.asc") or []
    except Exception:
        runs = []
    info = {"case": case, "run": {"id": run["id"], "instructions": run.get("instructions") or "", "outputs": outputs},
            "instructions": run.get("instructions") or "",
            "outputs": outputs,
            "reminder_next": reminder_next(runs, run["id"]),
            "proposal_original_name": prop[0]["original_name"],
            "inputs": got,
            "files": [{k: f[k] for k in ("id", "kind", "original_name", "version", "storage_path", "created_at")} for f in files]}
    os.makedirs(work, exist_ok=True)
    json.dump(info, open(os.path.join(work, "case.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    patch_run({"state": "running", "started_at": now(), "step": "पाने वाचत आहे"})
    if warns:
        add_warnings(warns)
    print(f"fetched {len(got)} file(s) -> {work}/in")


def cmd_case_meta(args):
    """case_meta <out.json> [<workdir>] — runner-side, run right after `fetch` (before the Claude step): the proposal's
    original name from Supabase (newest proposal case_files row; nothing is downloaded) and its page count from the
    fetched proposal PDF in <workdir> (default /tmp/case) when it can be read -> {proposal_original_name,
    proposal_pages}. `verify --case-meta` uses this file instead of the engine-writable case.json."""
    outp = args[0]
    work = args[1] if len(args) > 1 else (os.environ.get("WORKDIR") or "/tmp/case")
    prop = newest_proposal(rest("GET", f"case_files?case_id=eq.{CASE}&kind=eq.proposal&select=*") or [])
    if not prop:
        raise RuntimeError("प्रस्ताव PDF अपलोड केलेला नाही")
    name = prop["original_name"]
    pages = None
    src = os.path.join(work, "in", "proposal", safe_name(name))
    if os.path.exists(src):
        try:
            import pymupdf
            with pymupdf.open(src) as d:
                pages = len(d)
        except Exception as e:
            print(f"engine_supabase case_meta: pages not read ({e})", file=sys.stderr)
    try:
        run = (rest("GET", f"runs?id=eq.{RUN}&select=*") or [{}])[0]
    except Exception:
        run = {}
    meta = {"proposal_original_name": name, "proposal_pages": pages, "outputs": norm_outputs(run.get("outputs"))}
    d = os.path.dirname(os.path.abspath(outp))
    os.makedirs(d, exist_ok=True)
    json.dump(meta, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("case_meta:", json.dumps(meta, ensure_ascii=False))


def storage_name(n):
    """Supabase Storage refuses non-ASCII object keys (400 InvalidKey): objects are stored as file<ext>."""
    ext = os.path.splitext(n)[1].lower()
    return "file" + (ext if re.fullmatch(r"\.[a-z0-9]{1,8}", ext) else "")


# The ONE definition of the upload system's random file-name prefix (INSTRUCTIONS §4.16, e.g. "11ae057d-"); also used by
# tools/verify_outputs.py. 8 hex characters + "-", at least one of them a letter a-f (case-insensitive), so a real name
# that starts with a date ("20261101-CR130.pdf") is kept.
UPLOAD_PREFIX = re.compile(r"^(?=[0-9a-f]{0,7}[a-f])[0-9a-f]{8}-", re.I)


# A full UUID file name (8-4-4-4-12 hex, e.g. "3f2a9c1e-5b7d-4e2a-9c1e-1234567890ab.pdf") is a machine-made name of its
# own (A1 H12): it is kept exactly as uploaded (ENGINE_PROMPT rule 5), never cut to "5b7d-4e2a-….pdf".
UUID_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\.[A-Za-z0-9]{1,8})?$", re.I)


def strip_upload_prefix(n):
    if UUID_NAME.match(os.path.basename(str(n))):
        return n
    return UPLOAD_PREFIX.sub("", n)


def package_pdfs(out):
    return [p for p in glob.glob(os.path.join(out, "*.pdf"))
            if not re.search(r"_(Study|Note_and_Letter|Note|Letter|Order_Draft|Parawise)\.pdf$", p)]  # previews


# optional outputs (02.11.2026): kind -> (file suffix, Marathi label for warnings)
EXTRA_OUTPUTS = (("order_draft", "_Order_Draft.docx", "शासन आदेश-मसुदा"),
                 ("parawise", "_Parawise.docx", "परिच्छेदनिहाय अभिप्राय"))


# Supabase Storage bucket `outputs` refuses objects over 50 MB (413; init.sql file_size_limit). OUTPUT_MAX_BYTES overrides
# (tests / a raised bucket limit).
def output_limit():
    try:
        return int(os.environ.get("OUTPUT_MAX_BYTES") or 50 * 1024 * 1024)
    except ValueError:
        return 50 * 1024 * 1024


def next_version(kind):
    prev = rest("GET", f"case_files?case_id=eq.{CASE}&kind=eq.{kind}&select=version&order=version.desc&limit=1") or []
    return prev[0]["version"] + 1 if prev else 1


def put_object(kind, p):
    """Storage upload only (no case_files row) -> {kind, name, version, path}."""
    name = os.path.basename(p)
    ver = next_version(kind)
    path = f"{CASE}/{kind}/v{ver}/{storage_name(name)}"  # ASCII object key; real name in original_name
    ctype = MIME.get(os.path.splitext(name)[1].lower()) or mimetypes.guess_type(name)[0] or "application/octet-stream"
    http("POST", f"{BASE}/storage/v1/object/outputs/{enc(path)}", open(p, "rb").read(),
         {"Content-Type": ctype, "x-upsert": "true"})
    return {"kind": kind, "name": name, "version": ver, "path": path}


def drop_object(path):
    try:  # best effort: an object without its row is an orphan
        http("DELETE", f"{BASE}/storage/v1/object/outputs/{enc(path)}")
    except Exception:
        pass


def insert_row(u):
    rest("POST", "case_files", {"case_id": int(CASE), "kind": u["kind"], "storage_path": f"outputs/{u['path']}",
                                "original_name": u["name"], "version": u["version"], "uploaded_by": None}, "return=minimal")


def upload_output(kind, p):
    u = put_object(kind, p)
    try:
        insert_row(u)
    except Exception:
        drop_object(u["path"])  # no row -> remove the orphan object (e.g. enum value missing before migration 0006)
        raise
    return {"kind": kind, "name": u["name"], "version": u["version"]}


def pick_newest(paths, prefix=""):
    """Several *_Study.docx / *_Note_and_Letter.docx (PREFIX changed mid-run, A1 M): the one of status.json `prefix`, else
    the newest by mtime. -> (path or None, warning or None)."""
    if not paths:
        return None, None
    if len(paths) == 1:
        return paths[0], None
    mine = [p for p in paths if prefix and os.path.basename(p).startswith(prefix + "_")]
    best = mine[0] if len(mine) == 1 else max(paths, key=lambda p: (os.path.getmtime(p), p))
    others = ", ".join(os.path.basename(p) for p in paths if p != best)
    return best, f"एकाच प्रकारच्या {len(paths)} फाइल सापडल्या — {os.path.basename(best)} जतन केली (इतर: {others})"[:300]


def listed_extras(st):
    """status.json `outputs_extra`: ["order_draft", "parawise"] or [{"kind": ..., "file": "<PREFIX>_Order_Draft.docx"}]."""
    v = st.get("outputs_extra") if isinstance(st, dict) else None
    out = {}
    for x in v if isinstance(v, list) else []:
        k, f = (x, None) if isinstance(x, str) else ((x.get("kind"), x.get("file") or x.get("name")) if isinstance(x, dict) else (None, None))
        if not isinstance(k, str):
            continue
        # C28: draft keys -> upload kinds (order kinds -> order_draft; letter / reminder live in the Note_and_Letter)
        k = "order_draft" if k in ORDER_KEYS else k
        if k in ("letter", "reminder"):
            continue
        if k not in out or (f and not out[k]):
            out[k] = f
    return out


def upload_extras(out, st=None):
    """Optional outputs: uploaded when present; every problem is a warning (returned), never a failure."""
    done, warns = [], []
    listed = listed_extras(st)
    for kind, suffix, label in EXTRA_OUTPUTS:
        found = sorted(glob.glob(os.path.join(out, "*" + suffix)))
        want = listed.get(kind)
        if want and os.path.basename(str(want)) in {os.path.basename(f) for f in found}:
            found = [os.path.join(out, os.path.basename(str(want)))] + [f for f in found if os.path.basename(f) != os.path.basename(str(want))]
        if not found:
            if kind in listed:
                warns.append(f"{label}: status.json मध्ये नोंद आहे पण *{suffix} फाइल नाही")
            continue
        if len(found) > 1:
            warns.append(f"{label}: {len(found)} फाइल सापडल्या — {os.path.basename(found[0])} जतन केली")
        try:
            done.append(upload_output(kind, found[0]))
        except Exception as e:
            warns.append(f"{label} जतन झाला नाही (Supabase migration 0006 लागू आहे का?) — {str(e)[:160]}")
    return done, warns


def cmd_finish(out):
    try:
        st = json.load(open(os.path.join(out, "status.json"), encoding="utf-8"))
    except Exception as e:
        return cmd_fail(f"status.json वाचता आले नाही ({str(e)[:120]}) — पुन्हा तयार करा.")
    if not isinstance(st, dict):
        return cmd_fail("status.json वाचता आले नाही — पुन्हा तयार करा.")
    if st.get("state") != "done":
        # A3 H: only the engine's own Marathi summary is shown to Abhi (no "status.json state = …" prefix)
        return cmd_fail(str(st.get("summary") or "").strip() or "अभ्यास पूर्ण झाला नाही — पुन्हा तयार करा.")
    prefix = str(st.get("prefix") or "").strip()
    study, w1 = pick_newest(glob.glob(os.path.join(out, "*_Study.docx")), prefix)
    nl, w2 = pick_newest(glob.glob(os.path.join(out, "*_Note_and_Letter.docx")), prefix)
    pdfs = package_pdfs(out)
    if len(pdfs) > 1 and st.get("package_pdf"):
        want = os.path.join(out, os.path.basename(str(st["package_pdf"])))
        pdfs = [p for p in pdfs if p == want] or pdfs
    prop = newest_proposal(rest("GET", f"case_files?case_id=eq.{CASE}&kind=eq.proposal&select=*") or [])
    names = {safe_name(prop["original_name"]), strip_upload_prefix(safe_name(prop["original_name"]))} if prop else set()
    probs = []
    if not study: probs.append("*_Study.docx नाही")
    if not nl: probs.append("*_Note_and_Letter.docx नाही")
    if len(pdfs) != 1: probs.append(f"पॅकेज PDF: {len(pdfs)}")
    elif os.path.basename(pdfs[0]) not in names:
        probs.append(f"package PDF नाव मूळ प्रस्ताव-फाइलचे नाही: {os.path.basename(pdfs[0])}")
    if probs:
        return cmd_fail("आउटपुट अपूर्ण — " + "; ".join(probs))
    # Abhi 03.11.2026 ("हे इशारे नोटिंग मध्ये नको … स्टडी … डॉक्युमेंट फाईल … त्याच्यामध्ये द्या"): the final warnings
    # (runs.warnings so far: verify / extracts / review / workflow lines + status.json warnings) go INTO the Study, end of
    # भाग 7, before it is uploaded; owner-only "मॉडेल:" / cost lines are left out by tools/study_warnings.py
    study_note = []
    try:
        cur_w = (rest("GET", f"runs?id=eq.{RUN}&select=warnings") or [{}])[0].get("warnings")
        st_w = st.get("warnings") if isinstance(st.get("warnings"), list) else []
        final_w = (cur_w if isinstance(cur_w, list) else []) + [str(x).strip()[:300] for x in st_w if str(x).strip()]
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from study_warnings import append as study_append
        study_append(study, final_w + [w for w in (w1, w2) if w])
    except Exception as e:
        print("engine_supabase: warnings not written into the Study:", e, file=sys.stderr)
        study_note = [f"तपासणीचे इशारे अभ्यास-फाइलमध्ये लिहिता आले नाहीत ({str(e)[:120]})"[:300]]
    main3 = (("package_pdf", pdfs[0]), ("study", study), ("note_letter", nl))  # package FIRST (largest, A2)
    lim = output_limit()
    big = [(os.path.basename(p), os.path.getsize(p)) for _, p in main3 if os.path.getsize(p) > lim]
    if big:
        txt = "; ".join(f"{n} {sz / 1048576:.1f} MB" for n, sz in big)
        try:
            add_warnings([f"फाइल खूप मोठी — जतन करण्याची मर्यादा {lim / 1048576:.0f} MB: {txt}"[:300]])
        except Exception as e:
            print("engine_supabase: size warning not stored:", e, file=sys.stderr)
        return cmd_fail(f"आउटपुट जतन झाले नाही — फाइल {lim / 1048576:.0f} MB पेक्षा मोठी ({txt}). "
                        "प्रस्ताव कमी resolution मध्ये स्कॅन करून पुन्हा अपलोड करा, नंतर पुन्हा तयार करा."[:500])
    # all objects first, rows only after every upload succeeded (A2: no orphan rows of a failed run)
    put = []
    try:
        for kind, p in main3:
            put.append(put_object(kind, p))
    except Exception as e:
        for u in put: drop_object(u["path"])
        return cmd_fail(f"आउटपुट जतन झाले नाही (Storage) — {str(e)[:200]} — पुन्हा तयार करा.")
    for u in put:
        insert_row(u)
    uploaded = [{"kind": u["kind"], "name": u["name"], "version": u["version"]} for u in put]
    extra, extra_warn = upload_extras(out, st)
    uploaded += extra
    lst = lambda k: st.get(k) if isinstance(st.get(k), list) else []
    patch_run({"state": "done", "finished_at": now(), "step": "तयार", "summary": st.get("summary") or "",
               "letter_needed": bool(st.get("letter_needed")), "essential_points": lst("essential_points"),
               "grs_attached": lst("grs_attached"), "grs_missing": lst("grs_missing")})
    rest("PATCH", f"cases?id=eq.{CASE}", {"stage": "मसुदा तयार"}, "return=minimal")
    fill_case(st.get("case"))
    sw = [str(x).strip()[:300] for x in lst("warnings") if str(x).strip()]  # engine notes for Abhi (e.g. C R not found)
    sw += [w for w in (w1, w2) if w]
    sw += [w[:300] for w in extra_warn] + study_note
    if sw:
        try:
            add_warnings(sw)
        except Exception as e:
            print("engine_supabase: status warnings not stored:", e, file=sys.stderr)
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
    if patch.get("cr_no") and (patch.get("cr_year") or cur.get("cr_year")):
        yr = patch.get("cr_year") or cur.get("cr_year")
        dup = rest("GET", f"cases?cr_no=eq.{patch['cr_no']}&cr_year=eq.{yr}&id=neq.{CASE}&select=id&limit=1") or []
        if dup:  # same C R/year already in another case: keep it out, still fill the rest, tell the user
            activity("case_cr_duplicate", {"cr": f"{patch['cr_no']}/{yr}", "existing_id": dup[0]["id"]})
            patch.pop("cr_no", None)
            patch.pop("cr_year", None)
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
    if sub == "error_max_budget_usd" or re.search(r"max.?budget|budget.{0,20}(exceeded|exhausted|reached)", low):
        return ("खर्च-मर्यादा ओलांडली — Claude Code ने अभ्यास थांबवला (इंजिन खर्च-मर्यादा कठोर ठेवत नाही; workflow तपासा),"
                " नंतर पुन्हा तयार करा.")
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


def claude_fields(results, wall=None):
    """runs fields from one or more Claude results: cost_usd and num_turns summed; duration_s = wall clock if known,
    else the longest run (the runs are parallel)."""
    costs = [r.get("total_cost_usd", r.get("cost_usd")) for r in results]
    costs = [float(c) for c in costs if isinstance(c, (int, float)) and not isinstance(c, bool)]
    turns = [r["num_turns"] for r in results if isinstance(r.get("num_turns"), int) and not isinstance(r.get("num_turns"), bool)]
    durs = [r["duration_ms"] / 1000 for r in results if isinstance(r.get("duration_ms"), (int, float))]
    fields = {}
    if costs: fields["cost_usd"] = round(sum(costs), 4)
    if turns: fields["num_turns"] = sum(turns)
    if wall is not None: fields["duration_s"] = round(wall, 1)
    elif durs: fields["duration_s"] = round(max(durs), 1)
    return fields


DEFAULTS = {"model": "claude-opus-5-5", "model_light": "claude-haiku-5-5", "model_review": "claude-opus-5-5", "model_strong": "",
            "effort": "medium", "budget_usd": 0.75}
EFFORTS = ("low", "medium", "high", "xhigh", "max")
OFF = ("none", "off", "no", "-", "0", "false")
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@\[\]/-]{1,99}")


def engine_config(cfg):
    """Non-secret run settings from the Worker config dict (keys model, model_light, model_review, model_strong,
    effort, budget_usd); every missing/invalid value -> DEFAULTS. Tiers (Abhi, 01.11.2026): MODEL = drafter (facts from
    the page images, letter-or-not, note body + letter, GR choice for the note, Study part 0; MODEL from Settings (default claude-opus-5-5;
    Abhi's plan: Sonnet)),
    MODEL_LIGHT = cheap tier (orchestrator, tools, builds, lint/verify fixes, Study parts 1-7 except 0, note `related`),
    MODEL_REVIEW = final reviewer/approver (Opus-class; checks and minimally corrects note + letter + part 0; the run
    is not "done" without its approval), MODEL_STRONG = optional one-way escalation tier above MODEL
    (empty / "none" = off). BUDGET_USD is SOFT: the run is never stopped or degraded for it; going over it only adds
    the information line "खर्च अंदाजापेक्षा जास्त — माहितीसाठी"."""
    cfg = cfg if isinstance(cfg, dict) else {}
    def model(k):
        v = cfg.get(k)
        v = v.strip() if isinstance(v, str) else ""
        if k == "model_strong" and v.lower() in OFF:
            return ""
        return v if MODEL_RE.fullmatch(v) else DEFAULTS[k]
    eff = cfg.get("effort")
    eff = eff.strip().lower() if isinstance(eff, str) and eff.strip().lower() in EFFORTS else DEFAULTS["effort"]
    bud = cfg.get("budget_usd")
    try:
        bud = float(bud) if bud is not None and not isinstance(bud, bool) and str(bud).strip() != "" else DEFAULTS["budget_usd"]
    except (TypeError, ValueError):
        bud = DEFAULTS["budget_usd"]
    if not (0.05 <= bud <= 50):  # also NaN
        bud = DEFAULTS["budget_usd"]
    strong = model("model_strong")
    main = model("model")
    if strong == main:
        strong = ""
    out = {"MODEL": main, "MODEL_LIGHT": model("model_light"), "MODEL_REVIEW": model("model_review"),
           "MODEL_STRONG": strong, "EFFORT": eff,
           "BUDGET_USD": f"{bud:.2f}"}
    out.update(provider_config(cfg))
    return out


# Other AI providers (Abhi 02.11.2026; docs/AI_PROVIDERS_RESEARCH.md). A: Study part 1 on Gemini (machine-checked by
# part1check). C: when the Claude run fails on the provider side (credit, key, overloaded, API error), the same engine
# run is repeated through a local LiteLLM gateway on the fallback provider. Paid API keys only (free tiers: no
# confidential data — Gemini terms). Defaults below are used when the Settings value is empty or invalid.
# Providers reachable through the LiteLLM gateway (Worker AI_PROVIDERS; research docs/AI_PROVIDERS_RESEARCH.md):
# LiteLLM model prefix, env name of its key, default (main, light) models. `ollama` = the office's own model server.
PROVIDERS = {
    "gemini": ("gemini/", "GEMINI_API_KEY", ("gemini-2.5-pro", "gemini-2.5-flash")),
    "openai": ("openai/", "OPENAI_API_KEY", ("gpt-6.1-sol", "gpt-5.4-mini")),
    "openrouter": ("openrouter/", "OPENROUTER_API_KEY", ("nvidia/nemotron-3.5-super-vl:free", "google/gemma-4-31b:free")),
    "groq": ("groq/", "GROQ_API_KEY", ("gpt-oss-120b", "qwen3.8-27b")),
    "mistral": ("mistral/", "MISTRAL_API_KEY", ("mistral-medium-latest", "mistral-small-latest")),
    "cerebras": ("cerebras/", "CEREBRAS_API_KEY", ("gpt-oss-120b", "qwen-3.8-27b")),
    "cloudflare": ("cloudflare/", "CLOUDFLARE_API_TOKEN", ("@cf/meta/llama-4-scout-17b-16e-instruct", "@cf/meta/llama-4-scout-17b-16e-instruct")),
    "ollama": ("ollama_chat/", "OLLAMA_API_KEY", ("gemma4:31b", "gemma4:12b")),
}
SETTINGS_KEY = {"cloudflare": "cloudflare_api_token"}  # Settings key name when not "<provider>_api_key"
FALLBACK_DEFAULTS = {p: v[2] for p, v in PROVIDERS.items()}  # kept for older callers/tests
PROVIDER_MODEL_RE = re.compile(r"@?[A-Za-z0-9][A-Za-z0-9._:/@-]{1,100}")
URL_RE = re.compile(r"https?://[A-Za-z0-9.-]+(:\d+)?(/[A-Za-z0-9._~/-]*)?")


def provider_ready(cfg, p):
    s = lambda k: cfg.get(k).strip() if isinstance(cfg.get(k), str) else ""
    if p not in PROVIDERS: return False
    if p == "ollama": return bool(URL_RE.fullmatch(s("ollama_base_url")))
    if p == "cloudflare" and not re.fullmatch(r"[0-9a-f]{32}", s("cloudflare_account_id")): return False
    return bool(s(SETTINGS_KEY.get(p, f"{p}_api_key")))


def provider_config(cfg):
    """Provider choices (keys themselves are never printed): ENGINE_PROVIDER ('' = Claude, else the provider that runs the
    whole engine through the gateway), ENGINE_MODEL(_LIGHT); FALLBACK_PROVIDER ('' or a provider ≠ ENGINE_PROVIDER, used when
    the main run fails on the provider side), FALLBACK_MODEL(_LIGHT); PART1_PROVIDER (claude or a provider) + PART1_MODEL
    (GEMINI_MODEL kept for older settings); CLOUDFLARE_ACCOUNT_ID, OLLAMA_BASE_URL. A provider counts only when its key
    (Ollama: its URL; Cloudflare: also the account id) is set; invalid model names -> the provider's defaults."""
    s = lambda k: cfg.get(k).strip() if isinstance(cfg.get(k), str) else ""
    m = lambda k, d: s(k) if PROVIDER_MODEL_RE.fullmatch(s(k)) and ".." not in s(k) else d
    pick = lambda k: s(k) if provider_ready(cfg, s(k)) else ""
    ep, fb, p1 = pick("engine_provider"), pick("fallback_provider"), pick("part1_provider")
    if fb == ep: fb = ""
    em, el = PROVIDERS[ep][2] if ep else ("", "")
    fm, fl = PROVIDERS[fb][2] if fb else ("", "")
    if p1 == "gemini":
        p1m = m("part1_model", "") or m("gemini_model", "gemini-2.5-flash")
    elif p1:
        p1m = m("part1_model", "")
    else:
        p1m = ""
    return {"ENGINE_PROVIDER": ep, "ENGINE_MODEL": m("engine_model", em) if ep else "", "ENGINE_MODEL_LIGHT": m("engine_model_light", el) if ep else "",
            "PART1_PROVIDER": p1 or "claude", "PART1_MODEL": p1m, "GEMINI_MODEL": m("gemini_model", "gemini-2.5-flash"),
            "FALLBACK_PROVIDER": fb, "FALLBACK_MODEL": m("fallback_model", fm) if fb else "", "FALLBACK_MODEL_LIGHT": m("fallback_model_light", fl) if fb else "",
            "CLOUDFLARE_ACCOUNT_ID": s("cloudflare_account_id") if re.fullmatch(r"[0-9a-f]{32}", s("cloudflare_account_id")) else "",
            "OLLAMA_BASE_URL": s("ollama_base_url").rstrip("/") if URL_RE.fullmatch(s("ollama_base_url")) else ""}


def provider_failure(res, err, rc):
    """True when a failed Claude run failed on the PROVIDER side (no credit, key refused, overloaded / rate limit,
    API 5xx, connection) — the case for the fallback provider (C). Not for the case's own problems (max turns, time-out,
    a wrong model name, review/verify failures)."""
    if str(rc) == "124" or str((res or {}).get("subtype") or "") in ("error_max_turns", "error_max_budget_usd"):
        return False
    low = api_error_text(res, err)[:6000].lower()
    return bool(re.search(r"credit balance|billing|insufficient.?(credit|fund|quota)|payment required|invalid.{0,12}api.?key|"
                          r"authentication_error|x-api-key|\b401\b|unauthori[sz]ed|rate.?limit|overloaded|\b429\b|\b529\b|"
                          r"\b5\d\d\b.{0,40}(error|status)|api_error|internal server error|service unavailable|"
                          r"econnrefused|econnreset|etimedout|connection error|fetch failed|network error", low))


CLI_ERR_LINE = re.compile(r"^\s*(API Error|Invalid API key|(Your )?credit balance|Please run /login|Not logged in|"
                          r"Authentication|Request failed|Connection error)", re.I)


def api_error_text(res, err):
    """A2 LOW: the text that may show a PROVIDER error — stderr, the CLI's `api_error_status`, and only those lines of
    the result that the CLI itself writes for an API failure ("API Error: 529 …", "Invalid API key …"). The model's own
    result text ("the GR site returned 503 status") never triggers the fallback."""
    r = res or {}
    parts = [str(err or "")]
    if r.get("api_error_status") not in (None, ""):
        parts.append(f"api_error status {r.get('api_error_status')}")
    parts += [l for l in str(r.get("result") or "").splitlines() if CLI_ERR_LINE.match(l)]
    return " ".join(p for p in parts if p)


def litellm_config(conf, provider=None, main=None, light=None):
    """LiteLLM proxy config (YAML text; JSON is valid YAML): every Claude model name the engine uses (MODEL, MODEL_REVIEW,
    MODEL_STRONG -> main; MODEL_LIGHT and any other claude-* -> light) is routed to `provider` (default: the fallback
    provider of `conf`). Keys/URLs are read by the proxy from its own env by NAME (never written here). Cost of every
    answer is appended by tools/litellm_cost.py (callback) to $LITELLM_COST_FILE."""
    provider = provider or conf["FALLBACK_PROVIDER"]
    main = main or conf["FALLBACK_MODEL"]; light = light or conf["FALLBACK_MODEL_LIGHT"]
    pre, keyenv, _ = PROVIDERS[provider]
    def dep(name, target):
        lp = {"model": pre + target}
        if provider == "ollama":
            lp["api_base"] = "os.environ/OLLAMA_BASE_URL"
            # A2 LOW: always by env NAME — the key lives in the secrets file / the gateway's env, not in this shell
            lp["api_key"] = "os.environ/OLLAMA_API_KEY"
        elif provider == "cloudflare":
            lp["api_key"] = "os.environ/CLOUDFLARE_API_KEY"  # LiteLLM's name; the workflow sets it from CLOUDFLARE_API_TOKEN
        else:
            lp["api_key"] = "os.environ/" + keyenv
        return {"model_name": name, "litellm_params": lp}
    names = []
    for k in ("MODEL", "MODEL_REVIEW", "MODEL_STRONG"):
        if conf.get(k) and conf[k] not in names: names.append(conf[k])
    ml = [dep(n, main) for n in names]
    if conf.get("MODEL_LIGHT") and conf["MODEL_LIGHT"] not in names:
        ml.append(dep(conf["MODEL_LIGHT"], light))
    ml.append(dep("claude-*", light))
    return json.dumps({"model_list": ml,
                       "litellm_settings": {"drop_params": True, "num_retries": 3, "request_timeout": 600, "callbacks": "litellm_cost.handler"},
                       "router_settings": {"disable_cooldowns": True},
                       "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"}}, indent=1)


def gateway_cost(path):
    """Sum of tools/litellm_cost.py lines ({"model", "cost", "in", "out"}) -> {model: cost}; None when the file is absent."""
    if not path or not os.path.exists(path): return None
    out = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        c = r.get("cost")
        out[str(r.get("model") or "?")] = out.get(str(r.get("model") or "?"), 0.0) + (float(c) if isinstance(c, (int, float)) and not isinstance(c, bool) else 0.0)
    return out


def cmd_fallback_ok(args):
    """fallback_ok <claude.json> <claude.err> <rc> -> exit 0 when the fallback provider should take over (C)."""
    res = read_claude_json(args[0]) if args else None
    err = open(args[1], encoding="utf-8", errors="replace").read()[-6000:] if len(args) > 1 and os.path.exists(args[1]) else ""
    rc = args[2] if len(args) > 2 else "0"
    failed = res is None or bool(res.get("is_error")) or res.get("subtype") not in (None, "success") or str(rc) not in ("", "0")
    ok = failed and provider_failure(res, err, rc)
    print("FALLBACK YES" if ok else "FALLBACK NO")
    sys.exit(0 if ok else 1)


def cmd_litellm_config(args):
    """litellm_config <out.yaml> [<provider> <main model> <light model>] (default: the fallback provider from env)."""
    conf = {k: os.environ.get(k, "").strip() for k in ("MODEL", "MODEL_LIGHT", "MODEL_REVIEW", "MODEL_STRONG",
                                                         "FALLBACK_PROVIDER", "FALLBACK_MODEL", "FALLBACK_MODEL_LIGHT")}
    prov, main, light = (args[1:4] + ["", "", ""])[:3] if len(args) >= 4 else (conf["FALLBACK_PROVIDER"], conf["FALLBACK_MODEL"], conf["FALLBACK_MODEL_LIGHT"])
    if prov not in PROVIDERS or not PROVIDER_MODEL_RE.fullmatch(main or "") or not PROVIDER_MODEL_RE.fullmatch(light or ""):
        print("litellm_config: no usable provider / model", file=sys.stderr); sys.exit(2)
    open(args[0], "w", encoding="utf-8").write(litellm_config(conf, prov, main, light))


def cmd_config(path):
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except Exception:
        cfg = {}
    for k, v in engine_config(cfg).items():
        print(f"{k}={v}")


VERBATIM = (" Extracts are copied character for character from the cited page (look at the page image where the "
            "text layer is garbled); never paraphrase, shorten or fill gaps; mark omissions with \"…\". Do not decide "
            "which GR applies and do not change the note body or the letter.")
REVIEW = (" You are the final approver. LOOK at the proposal page images (WORKDIR/pages/p-NN.png; OCR p-NN.ocr.txt as "
          "a cross-check) for every number, date, name and amount used in the note, the letter and Study part 0. Check "
          "rule compliance (INSTRUCTIONS §4 incl. §4.18; the lint_spec rules), that the letter-or-not decision follows "
          "PROPOSAL_SOP Step 3 / INSTRUCTIONS §4.15, and the official language. Correct /tmp/work/spec.json (note + "
          "letter, and `order` / `parawise` when present; not `related`) and /tmp/work/study_part0.json directly with "
          "MINIMAL edits (never restyle approved wording). Never refuse approval for missing case fields (C R no., file "
          "no., subject, category — ref_no blanks ____ are allowed) or for unclear pages ('अस्पष्ट' + a warning). "
          "Correct small problems directly. After your edits run `python3 tools/lint_spec.py /tmp/work/spec.json` and "
          "leave it LINT OK, then compute spec_sha256 / part0_sha256 (`sha256sum /tmp/work/spec.json "
          "/tmp/work/study_part0.json`) and write /tmp/work/review.json = {\"approved\": true|false, \"changes\": N, "
          "\"corrections\": [\"<Marathi: what changed>\"], \"spec_sha256\": \"…\", \"part0_sha256\": \"…\"} "
          "(+ \"reason\" and \"redraft\" when not approved). Set approved=false only for a substantive error you cannot "
          "correct by small edits, and then give `reason` (one Marathi line) and `redraft` (numbered points for the "
          "drafter). You are called at most twice (review + one re-review); a second approved=false is delivered to the "
          "user with your reason as a warning. You never write /tmp/out/status.json and never set any state \"failed\". "
          "The workflow compares the hashes with the delivered files, so nobody may change them after you; a later "
          "change needs a new review.")
DRAFTER = (" Never stop or refuse: write every output you can. Missing C R/file no. → PREFIX Case<id>_<year>, ref_no "
           "'संकिर्ण-<year>/____/प्र.क्र.____/का.6'; unclear → 'अस्पष्ट'. Each problem you cannot resolve → report it in "
           "one line starting 'पडताळणी अपूर्ण — <what, where>' for status.json `warnings`. On a redraft request, fix "
           "exactly the reviewer's `reason`/`redraft` points. Year: never copy 2026 from a sample. Rule 58(4)(a) "
           "recommendation only from the record, else '____'.")
WRITER = (" If an extract cannot be matched to its page, report it as 'पडताळणी अपूर्ण — उतारा …'; never invent text.")
NEVER_STOP = (" Never stop: a missing C R / file no. / date is \"____\", an unreadable page or value is \"अस्पष्ट\", a "
              "GR that cannot be fetched goes to grs_missing — each with a warning line, never a reason to stop, refuse "
              "or fail. Any \"ask the user / discuss first\" line of INSTRUCTIONS, SOP or the brief means: add the "
              "question to the warnings and continue. You never write a \"failed\" state; the run always ends with its "
              "outputs (state \"done\", problems in `warnings`).")


def agents_json(conf, brief="tools/ENGINE_BRIEF.md"):
    """Claude Code --agents definitions (pinned CLI: description, prompt, model per agent). The orchestrating session
    runs on MODEL_LIGHT; `drafter` (MODEL) = facts, letter-or-not, note body + letter, Study part 0; `study_writer`
    and `related_writer` (MODEL_LIGHT) = Study parts 2-4, 7 (5-6 copied) and the note's `related` extracts, checked by
    tools/extract_check.py (mismatches go back to drafter); `reviewer` (MODEL_REVIEW) = final check + approval;
    `drafter_strong` (MODEL_STRONG) only when configured. Prompts are fixed text (stable prefix for prompt caching)."""
    base = ("You are a subagent of the Law & Judiciary engine run (one case). The binding rules are " + brief +
            " (read it once, fully) and the tool docstrings in /tmp/work/TOOL_DOCS.md; INSTRUCTIONS.md wins on any doubt"
            " (grep the exact item). Nothing of your own; verbatim quotes with source; unreadable = \"अस्पष्ट\". "
            "Do exactly the task in the delegation message, write the files it names, and reply in at most 5 lines "
            "(files written, open doubts, anything you could not read). Batch independent tool calls in one message; "
            "never read a file twice; limit command output. No git, no questions, never print environment values."
            + NEVER_STOP)
    out = {"drafter": {
        "description": "Drafter. Read facts/numbers/dates/names/handwriting/stamps from the proposal page images; "
                       "letter-or-not decision; GR selection for the note body and the enclosures; note body and "
                       "letter spec; the optional spec `order` (order draft) / `parawise` (court remarks, English) "
                       "per the brief's court and order-draft rules; Study part 0; extracts and Study part 1 pages that failed their check; content "
                       "fixes that lint/verify still reports after 2 mechanical attempts.",
        "prompt": base + DRAFTER, "model": conf["MODEL"]}}
    if conf.get("MODEL_STRONG"):
        out["drafter_strong"] = {
            "description": "Escalation tier (one-way up, only per the escalation rules): a page or a content problem "
                           "the main tier reported as still unclear / still failing.",
            "prompt": base + DRAFTER, "model": conf["MODEL_STRONG"]}
    light = conf.get("MODEL_LIGHT") or DEFAULTS["model_light"]
    out["study_writer"] = {
        "description": "Cheap tier. Study parts 2, 3, 4, 7 from facts.json, the drafter's spec and the package pages; "
                       "parts 5-6 = exact copies of the spec's note and letter text (never redrafted). Part 3 extracts "
                       "verbatim from the package GR pages with source and \"(पॅकेज PDF पृ. N)\"; checked by "
                       "tools/extract_check.py.",
        "prompt": base + VERBATIM + WRITER, "model": light}
    out["related_writer"] = {
        "description": "Cheap tier. The note's \"संबंधित माहिती (संदर्भासाठी)\" (spec `related`): verbatim GR/rule/"
                       "precedent extracts; each source line = plain \"(GR no., date, page, para)\" ending \" (पृ.N/प.वि.)\" "
                       "from the package map, or with no page marker when the page is not in the package; headings and "
                       "sources never use the words \"स्रोत\" or \"जसाच्या तसा\"; never \"पॅकेज PDF\", warnings, remarks "
                       "or any mention of AI (INSTRUCTIONS §4.27); checked by tools/extract_check.py.",
        "prompt": base + VERBATIM + WRITER, "model": light}
    out["reviewer"] = {
        "description": "Final review and approval (Opus-class). Checks every number/date/name of the note, letter and "
                       "Study part 0 against the page images, the rules (INSTRUCTIONS §4 incl. §4.18, the brief), the "
                       "letter-or-not decision and the language; corrects spec/part-0 text with minimal edits, runs lint_spec, "
                       "then writes /tmp/work/review.json {approved, changes, corrections[], hashes; reason + redraft "
                       "when not approved}; called at most twice.",
        "prompt": base + REVIEW, "model": conf.get("MODEL_REVIEW") or DEFAULTS["model_review"]}
    return out


def cmd_agents(args):
    """agents <out.json> — writes agents_json(env MODEL, MODEL_LIGHT, MODEL_REVIEW, MODEL_STRONG)."""
    conf = {k: os.environ.get(k, "") for k in ("MODEL", "MODEL_LIGHT", "MODEL_REVIEW", "MODEL_STRONG")}
    conf["MODEL"] = conf["MODEL"] or DEFAULTS["model"]
    conf["MODEL_REVIEW"] = conf["MODEL_REVIEW"] or DEFAULTS["model_review"]
    json.dump(agents_json(conf), open(args[0], "w", encoding="utf-8"), ensure_ascii=False, indent=1)


NUM_RE = re.compile(r"\d+(?:[./-]\d+)*")
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def part1_check(facts, part1):
    """Part 1 (cheap tier) against the main tier's facts list: every number/date of every PROPOSAL facts item (no
    "file" key, or "file": "proposal"; reply_<n> / extra items are skipped) must occur in that page's part-1 text (Devanagari digits normalised); a Devanagari value without digits (name, post) must
    occur as written (spaces ignored). -> list of "page N: <what> = <value>" mismatches; [] = confirmed."""
    pages, cur = {}, None
    for b in (part1 or {}).get("blocks") or []:
        if not isinstance(b, dict): continue
        if "subheading" in b:
            m = re.search(r"पान\s*(\d+)", str(b["subheading"]).translate(DEV_DIGITS))
            cur = int(m.group(1)) if m else cur
        txt = json.dumps(b, ensure_ascii=False).translate(DEV_DIGITS)
        if cur is not None:
            pages[cur] = pages.get(cur, "") + "\n" + txt
    bad = []
    for f in (facts or {}).get("facts") or []:
        if not isinstance(f, dict): continue
        # A1 H8: facts of a reply / concurrence / extra document ("file": "reply_1", "extra", …) carry page numbers of
        # THAT file, not of the proposal — part 1 is the proposal's rendering, so only proposal facts are compared
        if str(f.get("file") or "proposal").strip().lower() not in ("proposal", "प्रस्ताव"): continue
        try: pg = int(f.get("page"))
        except (TypeError, ValueError): continue
        text = pages.get(pg)
        flat = re.sub(r"\s+", "", text or "")
        for it in f.get("items") or []:
            if not isinstance(it, dict): continue
            v = str(it.get("value") or "").strip()
            if not v or v == "अस्पष्ट" or it.get("clear") is False: continue
            vn = v.translate(DEV_DIGITS)
            nums = [n for n in NUM_RE.findall(vn) if len(n.replace(".", "").replace("/", "").replace("-", "")) >= 2]
            if text is None:
                bad.append(f"page {pg}: no part-1 section"); break
            if nums:
                miss = [n for n in nums if n not in text]
                if miss: bad.append(f"page {pg}: {it.get('what')} = {v} (missing {', '.join(miss)})")
            elif re.search(r"[\u0900-\u097F]", v) and re.sub(r"\s+", "", v) not in flat:
                bad.append(f"page {pg}: {it.get('what')} = {v}")
    return bad


def cmd_part1check(args):
    """part1check <facts.json> <study_part1.json> -> prints PART1 OK or the mismatches (exit 1)."""
    try:
        facts = json.load(open(args[0], encoding="utf-8")); p1 = json.load(open(args[1], encoding="utf-8"))
    except Exception as e:
        print("PART1 CHECK ERROR:", e); sys.exit(1)
    bad = part1_check(facts, p1)
    for l in bad: print("MISMATCH", l)
    print("PART1 OK" if not bad else f"PART1 FAIL ({len(bad)})")
    sys.exit(0 if not bad else 1)


def short_model(m):
    """claude-haiku-5-5 -> Haiku 5.5 (for the Marathi run lines)."""
    mm = re.fullmatch(r"claude-([a-z]+)-(\d+)(?:-(\d+))?(.*)", str(m or ""))
    return f"{mm.group(1).capitalize()} {mm.group(2)}{'.' + mm.group(3) if mm.group(3) else ''}" if mm else str(m or "?")


def model_lines(results, status_path=None, budget=None):
    """'मॉडेल: ' run lines (runs.warnings — no schema change; contract with the UI): each routing/escalation entry of
    status.json `model_log` [{task, from, to, reason}] (kept also when the run failed), one per-model cost line from
    the results' modelUsage, and the soft-budget warning when the total cost is over BUDGET_USD."""
    lines, log, review = [], [], {}
    if status_path and os.path.exists(status_path):
        try:
            st = json.load(open(status_path, encoding="utf-8"))
            log = st.get("model_log") or []
            review = st.get("review") if isinstance(st.get("review"), dict) else {}
        except Exception:
            log = []
    for e in log if isinstance(log, list) else []:
        if not isinstance(e, dict): continue
        t, fr, to, why = (str(e.get(k) or "").strip() for k in ("task", "from", "to", "reason"))
        if t and to:
            lines.append(f"मॉडेल: {t} → {short_model(to)}" + (f" (पूर्वी {short_model(fr)})" if fr else "")
                         + (f" ({why})" if why else ""))
    fam = (short_model(os.environ.get("MODEL_REVIEW") or DEFAULTS["model_review"]).split() or ["Opus"])[0]
    corr = review.get("corrections") if isinstance(review.get("corrections"), list) else []
    for c in corr:
        if str(c or "").strip():
            lines.append(f"मॉडेल: {fam} पडताळणी — {str(c).strip()}")
    cost = {}
    for r in results:
        mu = r.get("modelUsage") if isinstance(r.get("modelUsage"), dict) else {}
        for m, u in mu.items():
            c = u.get("costUSD") if isinstance(u, dict) else None
            if isinstance(c, (int, float)) and not isinstance(c, bool):
                cost[m] = cost.get(m, 0.0) + float(c)
    if cost:
        lines.append("मॉडेल: खर्च — " + ", ".join(f"{short_model(m)} ${c:.2f}" for m, c in sorted(cost.items(), key=lambda x: -x[1])))
    total = [r.get("total_cost_usd", r.get("cost_usd")) for r in results]
    total = sum(float(c) for c in total if isinstance(c, (int, float)) and not isinstance(c, bool))
    if budget is not None and total > budget:
        lines.append(f"खर्च अंदाजापेक्षा जास्त — माहितीसाठी (खर्च ${total:.2f} / अंदाज ${budget:.2f})")
    return [l[:300] for l in lines]


def add_warnings(lines):
    if not lines: return
    cur = (rest("GET", f"runs?id=eq.{RUN}&select=warnings") or [{}])[0]
    w = cur.get("warnings") if isinstance(cur.get("warnings"), list) else []
    patch_run({"warnings": w + lines})


def outputs_present(out):
    """The three outputs a delivery needs exist in <out> (Study, Note_and_Letter, one package PDF)."""
    if not out or not os.path.isdir(out):
        return False
    return bool(glob.glob(os.path.join(out, "*_Study.docx")) and glob.glob(os.path.join(out, "*_Note_and_Letter.docx"))
                and package_pdfs(out))


def status_done(status_path):
    try:
        st = json.load(open(status_path, encoding="utf-8-sig"))
    except Exception:
        return False
    return isinstance(st, dict) and st.get("state") == "done"


def killed_estimate():
    """Cost stored for a run Claude Code could not report (killed / timeout / cancel, no JSON): BUDGET_USD, else 0.75."""
    try:
        b = float(os.environ.get("BUDGET_USD") or 0)
    except ValueError:
        b = 0
    return round(b if b > 0 else DEFAULTS["budget_usd"], 4)


def cmd_claude_result(args):
    """claude_result <claude.json> [<stderr>] [<rc>] [--part1 F] [--part1-no-cost] [--first F] [--killed] [--wall S]
    [--status status.json] [--gateway-cost F --gateway-provider P]. "Deliver with warnings" (Abhi: drafts are never
    thrown away, A1 H1): when status.json is "done" and the three outputs exist, an error result of the main run (max
    turns, time-out, killed, budget, …) is only a warning; verify / extracts / finish still decide."""
    args = list(args)
    part1 = wall = status = first = None
    gw = gw_prov = None
    killed = part1_no_cost = False
    for flag in ("--killed", "--part1-no-cost"):
        while flag in args:
            args.remove(flag)
            if flag == "--killed": killed = True
            else: part1_no_cost = True
    for flag in ("--part1", "--wall", "--status", "--gateway-cost", "--gateway-provider", "--first"):
        if flag in args:
            k = args.index(flag); v = args[k + 1] if k + 1 < len(args) else ""; del args[k:k + 2]
            if flag == "--part1": part1 = v
            elif flag == "--status": status = v
            elif flag == "--gateway-cost": gw = v
            elif flag == "--gateway-provider": gw_prov = v
            elif flag == "--first": first = v
            else:
                try: wall = float(v)
                except ValueError: wall = None
    res = read_claude_json(args[0]) if args else None
    p1 = read_claude_json(part1) if part1 else None
    r0 = read_claude_json(first) if first else None   # the first, failed run before a provider fallback (A2 HIGH)
    gc = gateway_cost(gw)
    if res is not None and gc is not None:
        # the run went through the LiteLLM gateway: real cost by provider model (Claude Code priced it as Claude)
        res = dict(res, total_cost_usd=round(sum(gc.values()), 4),
                   modelUsage={(f"{gw_prov}:" if gw_prov else "") + m: {"costUSD": c} for m, c in gc.items()})
    err = ""
    if len(args) > 1 and os.path.exists(args[1]):
        err = open(args[1], encoding="utf-8", errors="replace").read()[-4000:]
    rc = args[2] if len(args) > 2 else "0"
    # part 1 through the gateway: its cost is already in the gateway cost file -> parsed for warnings only
    results = [r for r in (res, None if part1_no_cost else p1, r0) if r]
    fields = claude_fields(results, wall)
    warns = []
    if res is None and (killed or str(rc) in ("124", "137", "143")):
        est = killed_estimate()  # A2 HIGH: a killed run has no JSON; its spend must still count toward the month limit
        fields["cost_usd"] = round(fields.get("cost_usd", 0.0) + est, 4)
        warns.append(f"खर्च अंदाजे — Claude थांबवला गेला (निकाल नाही); अंदाजे ${est:.2f} नोंदवला")
    if fields:
        try:
            patch_run(fields)
        except Exception as e:
            print("engine_supabase: cost not stored:", e, file=sys.stderr)
    try:
        b = os.environ.get("BUDGET_USD")
        add_warnings(model_lines(results, status, float(b) if b else None) + warns)
    except Exception as e:
        print("engine_supabase: model lines not stored:", e, file=sys.stderr)
    if res:
        print("claude:", res.get("subtype"), "| turns", res.get("num_turns"), "| cost", res.get("total_cost_usd", res.get("cost_usd")))
    if p1:
        print("part1 :", p1.get("subtype"), "| turns", p1.get("num_turns"), "| cost", p1.get("total_cost_usd", p1.get("cost_usd")),
              "(cost not added: gateway)" if part1_no_cost else "")
    if r0:
        print("first :", r0.get("subtype"), "| turns", r0.get("num_turns"), "| cost", r0.get("total_cost_usd", r0.get("cost_usd")))
    if part1 and (p1 is None or p1.get("is_error") or p1.get("subtype") not in (None, "success")):
        try:
            cmd_warn("भाग 1 (समांतर रूपांतर) स्वतंत्रपणे पूर्ण झाला नाही — मुख्य अभ्यासाने लिहिला ("
                     + str((p1 or {}).get("subtype") or "निकाल नाही") + ").")
        except Exception as e:
            print("engine_supabase: part1 warning not stored:", e, file=sys.stderr)
    failed = (res is None or bool(res.get("is_error")) or res.get("subtype") not in (None, "success")
              or str(rc) not in ("", "0") or killed)
    if not failed:
        return
    reason = claude_reason(res, err, rc) if not (killed and res is None and str(rc) in ("", "0")) else \
        "Claude थांबवला गेला — अभ्यास पूर्ण झाला नाही. पुन्हा तयार करा."
    if status and status_done(status) and outputs_present(os.path.dirname(os.path.abspath(status))):
        # drafts exist and the engine said "done": deliver with a warning; the gates after this step still apply
        print("claude_result: run ended with an error, but status.json is done and the outputs exist -> deliver with warnings")
        try:
            why = re.sub(r"[\s.—]*(नंतर )?पुन्हा तयार करा.*$", "", reason).rstrip(" .,—")
            add_warnings([f"अभ्यास नीट संपला नाही ({why}) — तयार मसुदे जतन केले, वापरण्यापूर्वी तपासा"[:300]])
        except Exception as e:
            print("engine_supabase: warning not stored:", e, file=sys.stderr)
        return
    cmd_fail(reason)


def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""): h.update(b)
    return h.hexdigest()


def model_ran(results, model):
    """True when the CLI's own modelUsage (not model-written text) shows `model` with a cost > 0. Keys may carry a
    suffix (e.g. "claude-opus-5-5[1m]" or a date), so the configured id is matched as a prefix."""
    m = str(model or "").strip()
    for r in results:
        mu = r.get("modelUsage") if isinstance(r.get("modelUsage"), dict) else {}
        for k, u in mu.items():
            c = u.get("costUSD") if isinstance(u, dict) else None
            if str(k).startswith(m) and isinstance(c, (int, float)) and not isinstance(c, bool) and c > 0:
                return True
    return False


def subagent_runs(res, name="reviewer"):
    """Number of `name` subagent runs from the CLI result's own subagent statistics (A2 MED), or None when the result
    carries none. Accepted shapes: {"subagent_stats": {"by_type": {"reviewer": 2}}} / {"reviewer": {"count": 2}} /
    [{"type"|"subagent_type"|"name": "reviewer", "count"|"runs": 2}]."""
    st = (res or {}).get("subagent_stats")
    if not isinstance(st, dict):
        return None
    bt = st.get("by_type", st)
    n = None
    def num(v):
        if isinstance(v, bool): return None
        if isinstance(v, (int, float)): return int(v)
        if isinstance(v, dict):
            for k in ("count", "runs", "total", "invocations"):
                if isinstance(v.get(k), (int, float)) and not isinstance(v.get(k), bool): return int(v[k])
            return 1
        return None
    if isinstance(bt, dict):
        if not bt: return None
        n = num(bt.get(name)) if name in bt else 0
    elif isinstance(bt, list):
        if not bt: return None
        n = 0
        for x in bt:
            if isinstance(x, dict) and name in (x.get("type"), x.get("subagent_type"), x.get("name")):
                n += num({k: v for k, v in x.items() if k in ("count", "runs", "total", "invocations")}) or 1
    return n


def review_gate(review_dir, claude_json=None, notes=None):
    """H2 (QUALITY_AUDIT §7): the final approval is read from the reviewer's own /tmp/work/review.json (not the copy in
    status.json), must name the sha256 of the spec.json / study_part0.json it approved (any later change -> refused),
    and the CLI result must show the reviewer ran: a "reviewer" subagent in its subagent statistics when present (A2
    MED), else MODEL_REVIEW in modelUsage with a cost > 0 (skipped when MODEL_REVIEW is the orchestrator's own model).
    When usage cannot tell the reviewer apart (MODEL_REVIEW = MODEL or MODEL_LIGHT, no subagent statistics) a Marathi
    note is appended to `notes` (a warning, never a silent pass). -> None = OK, else a Marathi reason."""
    try:
        rv = json.load(open(os.path.join(review_dir, "review.json"), encoding="utf-8"))
    except Exception:
        return "reviewer ची review.json नाही (अंतिम पडताळणी झाली नाही)"
    if not isinstance(rv, dict) or rv.get("approved") is not True:
        why = str((rv or {}).get("reason") or "").strip() if isinstance(rv, dict) else ""
        return "reviewer ची मान्यता नाही" + (f" — {why}" if why else "")
    for name, key in (("spec.json", "spec_sha256"), ("study_part0.json", "part0_sha256")):
        fp = os.path.join(review_dir, name)
        if not os.path.exists(fp):
            if name == "spec.json": return "spec.json नाही"
            continue
        want = str(rv.get(key) or "").strip().lower()
        if not want:
            return f"review.json मध्ये {key} नाही (मान्य केलेली आवृत्ती ओळखता येत नाही)"
        if want != sha256_file(fp):
            return f"मान्यतेनंतर {name} बदलली — पुन्हा reviewer ची मान्यता आवश्यक"
    review_model = (os.environ.get("MODEL_REVIEW") or DEFAULTS["model_review"]).strip()
    light = (os.environ.get("MODEL_LIGHT") or DEFAULTS["model_light"]).strip()
    drafter = (os.environ.get("MODEL") or DEFAULTS["model"]).strip()
    if not claude_json:
        return None
    res = read_claude_json(claude_json)
    if res is None:
        return "Claude निकाल (claude.json) वाचता आला नाही — reviewer चालला का ते तपासता आले नाही"
    n = subagent_runs(res, "reviewer")
    if n is not None:
        return None if n > 0 else "reviewer subagent चालला नाही (CLI निकाल)"
    if review_model != light and not model_ran([res], review_model):
        return f"reviewer मॉडेल ({short_model(review_model)}) प्रत्यक्ष चालले नाही"
    if review_model in (light, drafter) and notes is not None:
        notes.append(f"अंतिम पडताळणी: reviewer प्रत्यक्ष चालला हे CLI निकालावरून सिद्ध झाले नाही "
                     f"(reviewer व {'orchestrator' if review_model == light else 'drafter'} एकच मॉडेल {short_model(review_model)}) — तपासा")
    return None


def part1_gate(work_dir):
    """QUALITY_AUDIT §7 M: part1check re-run by the workflow (not only by the model) on the FINAL Study part 1 — the
    "भाग 1" part of <work>/study.json (the build_study input), else <work>/study_part1.json — against the drafter's
    <work>/facts.json. -> (None, None) OK; ("warn", text) facts/part 1 absent; ("fail", Marathi reason)."""
    fp = os.path.join(work_dir, "facts.json")
    if not os.path.exists(fp):
        return "warn", "भाग 1 तपासणी (part1check) झाली नाही — facts.json नाही"
    try:
        facts = json.load(open(fp, encoding="utf-8-sig"))
    except Exception as e:
        return "fail", f"facts.json वाचता आली नाही ({str(e)[:80]})"
    p1 = None
    sp = os.path.join(work_dir, "study.json")
    if os.path.exists(sp):
        try:
            study = json.load(open(sp, encoding="utf-8-sig"))
        except Exception as e:
            return "fail", f"study.json वाचता आली नाही ({str(e)[:80]})"
        p1 = next((p for p in (study.get("parts") or []) if isinstance(p, dict)
                   and str(p.get("heading", "")).startswith("भाग 1")), None) if isinstance(study, dict) else None
        if p1 is None:
            return "fail", "study.json मध्ये भाग 1 नाही"
    else:
        try:
            p1 = json.load(open(os.path.join(work_dir, "study_part1.json"), encoding="utf-8-sig"))
        except Exception:
            return "warn", "भाग 1 तपासणी (part1check) झाली नाही — study.json / study_part1.json नाही"
    bad = part1_check(facts, p1)
    if bad:
        more = f"; … (+{len(bad) - 4})" if len(bad) > 4 else ""
        return "fail", f"भाग 1 (मराठी रूपांतर) तथ्यांशी जुळला नाही — {'; '.join(bad[:4])}{more}"
    return None, None


# verify classification ("deliver with warnings", Abhi 02.11.2026: drafts are never thrown away). HARD = the case fails:
# an output missing / unreadable, confidentiality (internal ids, repo paths in note/letter/Study/optional drafts),
# annotations on the proposal pages. Every other FAIL line of verify_outputs.py is SOFT -> a runs.warnings line.
HARD_CHECK = re.compile(r"^(?:Study opens|Note_and_Letter opens|package PDF opens|.*\binternal ids|.*\brepo paths|"
                        r"annotations on proposal pages)\b")
SOFT_PREFIX = "पडताळणी अपूर्ण — "


def review_label():
    return (short_model(os.environ.get("MODEL_REVIEW") or DEFAULTS["model_review"]).split() or ["Opus"])[0]


def review_warning(why):
    return f"अंतिम पडताळणी ({review_label()}) मान्यता नाही — वापरण्यापूर्वी तपासा: {why}"[:300]


def soft_line(check, detail):
    d = re.sub(r"\s+", " ", str(detail)).strip()[:160]
    return f"{SOFT_PREFIX}{check}: {d}"[:300]


def classify_verify(lines):
    """verify_outputs.py stdout lines -> (hard [(check, detail)], soft [(check, detail)])."""
    hard, soft = [], []
    for l in lines:
        if not l.startswith("FAIL"): continue
        body = l[5:].strip() if l.startswith("FAIL:") else l[4:].strip()
        check, _, detail = body.partition(" — ")
        (hard if HARD_CHECK.match(check) else soft).append((check.strip(), detail.strip()))
    return hard, soft


def read_case_meta(path):
    """--case-meta file (runner-written by `case_meta`): {proposal_original_name, proposal_pages}."""
    try:
        cm = json.load(open(path, encoding="utf-8-sig"))
    except Exception as e:
        print(f"engine_supabase verify: --case-meta not read ({e})", file=sys.stderr)
        return "", None
    name = safe_name(str(cm.get("proposal_original_name") or "")) if isinstance(cm, dict) else ""
    pg = cm.get("proposal_pages") if isinstance(cm, dict) else None
    pg = pg if isinstance(pg, int) and not isinstance(pg, bool) and pg > 0 else None
    return ("" if name == "file" else name), pg


def map_proposal_pages(pkg):
    try:
        mp = json.load(open(pkg + ".map.json", encoding="utf-8-sig"))
        return len(mp["प्रस्ताव"]["pages"])
    except Exception:
        return None


def docx_paragraphs(path):
    """Paragraph texts of a .docx (stdlib: zipfile + regex on word/document.xml); [] when unreadable."""
    import zipfile, html
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except Exception:
        return []
    return [html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", p)))
            for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]


def missing_drafts(out, prefix, outputs):
    """C28 (§4.28): ticked draft keys whose draft is not in OUTDIR -> Marathi labels. letter: a letter without a
    "स्मरणपत्र-N" heading in <PREFIX>_Note_and_Letter.docx; reminder: a "स्मरणपत्र-N" letter there; order kinds: the
    body heading of that type in <PREFIX>_Order_Draft.docx; parawise: <PREFIX>_Parawise.docx."""
    if not outputs:
        return []
    nl = [t.strip() for t in docx_paragraphs(os.path.join(out, f"{prefix}_Note_and_Letter.docx"))]
    letters = sum(1 for t in nl if re.match(r"क्रमांक\s*:?\s*-", t))
    reminders = sum(1 for t in nl if re.fullmatch(r"स्मरणपत्र-\d+", t))
    od = {t.strip() for t in docx_paragraphs(os.path.join(out, f"{prefix}_Order_Draft.docx"))}
    have = {"letter": letters - reminders > 0, "reminder": reminders > 0,
            "parawise": os.path.exists(os.path.join(out, f"{prefix}_Parawise.docx"))}
    have.update({k: ORDER_HEAD[k] in od for k in ORDER_KEYS})
    return [DRAFT_LABEL[k] for k in outputs if k in have and not have[k]]


def cmd_verify(args):
    """verify <outdir> [<workdir>] [--review <work dir>] [--claude <claude.json>] [--case-meta <meta.json>]
    HARD problems fail the case (exit 1); SOFT problems become "पडताळणी अपूर्ण — <check>: <detail>" warnings (exit 0)."""
    args = list(args)
    review_dir = claude_json = case_meta = None
    for flag in ("--review", "--claude", "--case-meta"):
        if flag in args:
            k = args.index(flag); v = args[k + 1] if k + 1 < len(args) else ""; del args[k:k + 2]
            if flag == "--review": review_dir = v
            elif flag == "--claude": claude_json = v
            else: case_meta = v
    out = args[0]
    work = args[1] if len(args) > 1 else ""
    try:
        st = json.load(open(os.path.join(out, "status.json"), encoding="utf-8"))
    except Exception as e:
        return cmd_fail(f"status.json वाचता आले नाही ({str(e)[:120]}) — पुन्हा तयार करा.")
    if not isinstance(st, dict) or st.get("state") != "done":
        return  # `finish` records the engine's own failure reason
    warns = []
    rv = st.get("review") if isinstance(st.get("review"), dict) else {}
    if review_dir:
        notes = []
        why = review_gate(review_dir, claude_json, notes)
        if why:
            warns.append(review_warning(why))
        elif rv.get("approved") is not True:
            warns.append(review_warning("status.json मध्ये मान्यता-नोंद नाही"))
        warns += notes
        kind, why = part1_gate(review_dir)
        if kind:
            print("verify:", why)
            warns.append(why if kind == "warn" else soft_line("भाग 1", why))
        else:
            print("verify: PART1 OK")
    elif rv.get("approved") is not True:
        warns.append(review_warning(str(rv.get("reason") or "").strip() or "review नोंद नाही"))
    prefix = str(st.get("prefix") or "").strip()
    sf = glob.glob(os.path.join(out, "*_Study.docx"))
    if not prefix or not os.path.exists(os.path.join(out, f"{prefix}_Study.docx")):
        best, _ = pick_newest(sf, prefix)
        prefix = os.path.basename(best)[: -len("_Study.docx")] if best else prefix
    pkg = os.path.join(out, os.path.basename(str(st["package_pdf"]))) if st.get("package_pdf") else ""
    if not pkg or not os.path.exists(pkg):
        pp = package_pdfs(out)
        pkg = pp[0] if len(pp) == 1 else ""
    pages = None
    orig = ""
    ticked = None   # C28: runs.outputs (runner-written case_meta first; case.json otherwise)
    if case_meta:
        orig, pages = read_case_meta(case_meta)
        try:
            ticked = norm_outputs(json.load(open(case_meta, encoding="utf-8-sig")).get("outputs"))
        except Exception:
            ticked = None
    elif work:
        try:
            cj = json.load(open(os.path.join(work, "case.json"), encoding="utf-8"))
            ticked = norm_outputs(cj.get("outputs"))
            orig = safe_name(str(cj.get("proposal_original_name") or ""))
            if orig == "file": orig = ""
            src = next(os.path.join(work, f["local_path"]) for f in cj["inputs"] if f["kind"] == "proposal")
            import pymupdf  # on the runner (tools/requirements-engine.txt)
            with pymupdf.open(src) as d:
                pages = len(d)
        except Exception as e:
            print(f"engine_supabase verify: proposal pages from status.json ({e})", file=sys.stderr)
    if orig and pkg and os.path.basename(pkg) == strip_upload_prefix(orig):
        orig = os.path.basename(pkg)  # the package keeps the name with only the upload prefix stripped
    if pages is None and str(st.get("proposal_pages") or "").strip().isdigit():
        pages = int(str(st["proposal_pages"]).strip())
    if not prefix or not pkg:
        add_warnings(warns)
        return cmd_fail("आउटपुट अपूर्ण — " + ", ".join(x for x, v in (("*_Study.docx", prefix), ("पॅकेज PDF", pkg)) if not v)
                        + " नाही — पुन्हा तयार करा.")
    if pages is None:
        pages = map_proposal_pages(pkg)
        warns.append(soft_line("प्रस्ताव-पाने", "पानांची संख्या माहीत नाही" + (f" — map.json वरून {pages}" if pages else "")))
        pages = pages or 0
    script = os.environ.get("VERIFY_SCRIPT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_outputs.py")
    cmd = [sys.executable, script, out, prefix, pkg, str(pages)] + (["--original-name", orig] if orig else [])
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    lines = (r.stdout or "").splitlines()
    print(r.stdout, end="")
    hard, soft = classify_verify(lines)
    clean = r.returncode == 0 and not hard and not soft and any(l.startswith("ALL OK") for l in lines)
    if not clean and not hard and not soft:
        # the tool itself did not run through: confidentiality is not confirmed -> hard
        errl = (r.stderr or "").strip().splitlines()
        hard = [("verify_outputs", errl[-1] if errl else f"exit {r.returncode}")]
    for lab in missing_drafts(out, prefix, ticked):   # §4.26: SOFT, never a failure
        warns.append(soft_line("निवडलेला मसुदा तयार झाला नाही", lab))
    if soft:
        warns += [soft_line(c, d) for c, d in soft[:8]]
        if len(soft) > 8: warns.append(f"{SOFT_PREFIX}आणखी {len(soft) - 8} तपासण्या")
    try:
        add_warnings(warns)
    except Exception as e:
        print("engine_supabase: verify warnings not stored:", e, file=sys.stderr)
    if hard:
        detail = "; ".join(f"{c}: {d}" if d else c for c, d in hard[:4])
        if len(hard) > 4: detail += f"; … (+{len(hard) - 4})"
        return cmd_fail(f"पडताळणी (verify_outputs) अयशस्वी — {detail} — पुन्हा तयार करा."[:500])
    if clean and not warns:
        print("verify: ALL OK")
    else:
        print(f"verify: delivered with {len(warns)} warning(s) (soft)")


def extra_sources(extra=()):
    """Sources for "(पॅकेज PDF मध्ये नाही)" extracts — the SAME as the in-run check (A1 H7): register/, service-rules/
    of the repo, OLDCASES/t (default /tmp/old/t) and PRECEDENT (default /tmp/precedent), plus any --extra given."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    old = os.environ.get("OLDCASES") or "/tmp/old"
    cand = [os.path.join(root, "register"), os.path.join(root, "service-rules"), os.path.join(old, "t"),
            os.environ.get("PRECEDENT") or "/tmp/precedent"] + list(extra)
    out = []
    for c in cand:
        if c and os.path.exists(c) and c not in out: out.append(c)
    return out


def cmd_extracts(args):
    """extracts <outdir> <spec.json> <study.json> [<ocr dir>] [--extra PATH ...] — final verbatim guard
    (tools/extract_check.py) on the delivered `related` + Study part 3 (+ the note body's “…” quotes, --note-body)
    against the package PDF, with the same --extra sources as the in-run check (extra_sources). Never fails the case
    ("deliver with warnings"): a MISMATCH is a "पडताळणी अपूर्ण — उतारे: …" warning; unverifiable extracts and every
    note-body result are "मॉडेल: उतारा-तपासणी — …" warning lines."""
    args = list(args)
    extra = []
    while "--extra" in args:
        k = args.index("--extra")
        if k + 1 < len(args): extra.append(args[k + 1])
        del args[k:k + 2]
    out, spec, study = args[:3]
    try:
        st = json.load(open(os.path.join(out, "status.json"), encoding="utf-8"))
    except Exception:
        st = {}
    if not isinstance(st, dict) or st.get("state") != "done":
        return
    pkg = os.path.join(out, os.path.basename(str(st.get("package_pdf") or "")))
    if not st.get("package_pdf") or not os.path.exists(pkg):
        pp = package_pdfs(out)
        pkg = pp[0] if len(pp) == 1 else ""
    if not pkg:
        return add_warnings(["मॉडेल: उतारा-तपासणी — पॅकेज PDF सापडली नाही, तपासणी झाली नाही"])
    cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract_check.py"), pkg, "--note-body"]
    cmd += ["--spec", spec] if os.path.exists(spec) else []
    cmd += ["--study", study] if os.path.exists(study) else []
    if len(cmd) == 4:
        return add_warnings(["मॉडेल: उतारा-तपासणी — spec/study सापडले नाहीत, तपासणी झाली नाही"])
    cmd += ["--ocr-dir", args[3]] if len(args) > 3 and os.path.isdir(args[3]) else []
    for x in extra_sources(extra):
        cmd += ["--extra", x]
    rj = os.path.join(out, ".extracts.json")
    r = subprocess.run(cmd + ["--json", rj], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout, end="")
    try:
        recs = json.load(open(rj, encoding="utf-8"))
    except Exception:
        return add_warnings([f"मॉडेल: उतारा-तपासणी — साधन चालले नाही (exit {r.returncode})"])
    finally:
        if os.path.exists(rj): os.remove(rj)
    main_r = [x for x in recs if not x.get("warn_only")]
    note_r = [x for x in recs if x.get("warn_only")]
    bad = [x for x in main_r if x.get("status") == "mismatch"]
    unv = [x for x in main_r if x.get("status") == "unverifiable"]
    nbad = [x for x in note_r if x.get("status") == "mismatch"]
    nunv = [x for x in note_r if x.get("status") == "unverifiable"]
    where = lambda xs: "; ".join(sorted({str(x.get("where")) for x in xs}))[:180]
    lines = []
    if bad:
        lines.append(soft_line("उतारे", f"{len(bad)} उतारे मूळ PDF शी जसेच्या तसे जुळले नाहीत ({where(bad)}) — वापरण्यापूर्वी तपासा"))
    if unv:
        lines.append(f"मॉडेल: उतारा-तपासणी — {len(unv)} उतारे पडताळता आले नाहीत (स्कॅन/विस्कळीत मजकूर-स्तर)")
    if nbad:
        lines.append(f"मॉडेल: उतारा-तपासणी — नोंदीतील {len(nbad)} अवतरणे मूळ PDF शी जुळली नाहीत ({where(nbad)}) — तपासावे")
    if nunv:
        lines.append(f"मॉडेल: उतारा-तपासणी — नोंदीतील {len(nunv)} अवतरणे पडताळता आली नाहीत (पृ.N/प.वि. नाही / स्कॅन)")
    add_warnings(lines)
    print("extracts:", "MISMATCH (warning)" if bad else "OK")


def cmd_warn(text):
    text = (text or "").strip()[:300]
    cur = (rest("GET", f"runs?id=eq.{RUN}&select=warnings") or [{}])[0]
    w = cur.get("warnings") if isinstance(cur.get("warnings"), list) else []
    patch_run({"warnings": w + [text]})
    activity("run_warning", {"run_id": int(RUN), "warning": text})


def cmd_note(text):
    """note "<text>": one owner-only information line in runs.warnings ("मॉडेल: " prefix = not a warning)."""
    text = " ".join((text or "").split())
    if not text:
        return
    if not text.startswith("मॉडेल:"):
        text = "मॉडेल: " + text
    try:
        add_warnings([text[:300]])
    except Exception as e:
        print("engine_supabase note:", e, file=sys.stderr)


def cmd_step_worker(text):
    """Progress text through the Worker (POST /api/engine/step with the run token) — used inside the Claude step, which
    has no Supabase key. Never fails the run: the step text is only the live status."""
    tok, worker, run = (os.environ.get(k, "").strip() for k in ("RUN_TOKEN", "WORKER", "RUN_ID"))
    if not (tok and re.match(r"https?://", worker) and run.isdigit()):
        print("engine_supabase step: no run token / worker", file=sys.stderr); return
    req = urllib.request.Request(f"{worker.rstrip('/')}/api/engine/step", method="POST",
                                 data=json.dumps({"run_id": int(run), "step": (text or "")[:200]}, ensure_ascii=False).encode("utf-8"),
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: r.read()
    except Exception as e:
        print("engine_supabase step (worker):", e, file=sys.stderr)


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
    if len(a) == 2 and a[0] == "config":  # local commands: no Supabase env needed
        return cmd_config(a[1])
    if len(a) == 2 and a[0] == "agents":
        return cmd_agents(a[1:])
    if len(a) == 3 and a[0] == "part1check":
        return cmd_part1check(a[1:])
    if len(a) >= 2 and a[0] == "fallback_ok":
        return cmd_fallback_ok(a[1:])
    if len(a) in (2, 5) and a[0] == "litellm_config":
        return cmd_litellm_config(a[1:])
    if len(a) < 2 or a[0] not in ("fetch", "step", "log_url", "finish", "fail", "claude_result", "verify", "warn",
                                  "extracts", "case_meta", "note"):
        print(__doc__); sys.exit(2)
    c, arg = a[0], " ".join(a[1:])
    if c == "step" and not has_supabase():
        return cmd_step_worker(arg)  # the Claude step runs without the Supabase key (H1)
    init()
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
        elif c == "note": cmd_note(arg)
        elif c == "extracts": cmd_extracts(a[1:])
        elif c == "case_meta": cmd_case_meta(a[1:])
    except SystemExit:
        raise
    except Exception as e:
        if c == "extracts":  # the final verbatim guard never fails the case ("deliver with warnings")
            try:
                add_warnings([f"मॉडेल: उतारा-तपासणी — साधन चालले नाही ({str(e)[:120]})"])
            except Exception:
                pass
            print(f"engine_supabase {c}: {e}", file=sys.stderr); sys.exit(0)
        if c in ("fetch", "finish", "claude_result", "verify", "case_meta"):
            cmd_fail(f"{c}: {e}")
        print(f"engine_supabase {c}: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
