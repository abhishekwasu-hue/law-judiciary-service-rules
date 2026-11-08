#!/usr/bin/env python3
"""desk_publish.py — App B outputs of one run -> page assets + case_files / run rows for the प्रस्ताव कक्ष page in
artifact mode (docs/DESK_WORKER.md). Same rules as tools/engine_supabase.py finish / tools/edit_drafts.py upload_all:
package FIRST, then Study, Note_and_Letter, optional drafts, spec.json + enclosures.json LAST (one version for both);
every row gets the next version of its kind and a new id; rows only after every upload succeeded.

  plan <case_id> <outdir> <run_id> <syncdir> --files FILES.json [--work DIR] [--kinds k1,k2]
       [--package-name NAME] [--add KIND=PATH[::NAME]] ... [--no-spec]
       FILES.json  = this case's case_files rows as read from the page (list, or {doc_id: row}); used for versions and
                     the package's original name (newest package_pdf row, else the newest proposal row, §4.16).
       --package-name = the package's original name (full run: case.json `package_file`); a name ending in
                     "_Proposal_with_GRs.pdf" is refused (§4.16).
       --next-id   = accepted and ignored (ids are assigned by `rows --first-id`; a warning on stderr).
       --work      = the dir holding spec.json / enclosures.json (default <outdir>/..; absent -> no spec rows).
       --kinds     = only these output kinds (edit run: the rebuilt kinds; known kinds only, else exit 1); default = a
                     full run: package_pdf, study, note_letter (all three required -> exit 1) + every optional draft present.
       --add       = an extra row, e.g. gr=/tmp/w/201805171732241512.pdf::201805171732241512.pdf (edit run GR).
       Writes <syncdir>/uploads.json [{path, kind, name, type}] (upload order; type = the asset content type) and
       <syncdir>/uploads.txt (paths only), <syncdir>/plan.json (rows waiting for ids and asset ids), and for a full run
       with <outdir>/status.json <syncdir>/run_patch.json (run fields as engine_supabase finish sets them; `warnings` =
       the status.json lines only — the worker appends them to the run's current list).
       Store (dashboard-app/src/lib/artifact/README.md "File storage"): a PDF <= 19 MiB -> one asset
       (application/pdf); everything else (.docx — page assets refuse Word files —, spec.json / enclosures.json, a PDF
       > 19 MiB) -> base64 text parts <syncdir>/parts/<case>__r<run>_<n>_<kind>_v<version>.b64.<k>.txt (text/plain,
       desk_sync.split_b64; every part decodes on its own; no row id in the name, so a renumber needs no re-upload),
       row field asset_parts = [ids] in order. Rows also carry content_type and size_bytes.
  rows <syncdir> --assets ASSETS.json --first-id N [--now ISO]
       ASSETS.json = {"<uploaded path or its basename>": "<asset id>", ...} (from the Artifact publish results).
       N           = the first case_files id, ODD (the worker's half of the id space, contract §6 / DESK_WORKER §1): the
                     smallest odd number above the highest case_files id; the rows get N, N+2, N+4 …; an even N -> exit 1.
                     A create refused because the doc exists -> re-read the highest id and run `rows` again with the new
                     N (same assets, no re-upload).
       Writes <syncdir>/writes.json = ArtifactData batch entries (op set, collection case_files, doc_id = String(id),
       inline data; new documents -> no if_version; storage_path "asset:<id>" + asset_id, or "asset-parts:<n>" +
       asset_parts, as the page's storeBlob writes them), prints the uploaded list [{kind, name, version}] for the
       activity row on stdout and the ids used on stderr. Exit 1 when an asset id is missing (nothing must be written then).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from desk_sync import ASSET_MAX, split_b64  # noqa: E402  (same 19 MiB cap and part size as the chat sync)

MAIN3 = (("package_pdf", None), ("study", "_Study.docx"), ("note_letter", "_Note_and_Letter.docx"))
# engine_supabase.EXTRA_OUTPUTS (kind -> file suffix)
EXTRA = (("order_draft", "_Order_Draft.docx"), ("parawise", "_Parawise.docx"), ("affidavit", "_Affidavit.docx"),
         ("lq_answer", "_LQ_Answer.docx"))
PREVIEW_RE = ("_Study.pdf", "_Note_and_Letter.pdf", "_Note.pdf", "_Letter.pdf", "_Order_Draft.pdf", "_Parawise.pdf",
              "_Affidavit.pdf", "_LQ_Answer.pdf")
SPEC_FILES = ("spec.json", "enclosures.json")
KINDS = {k for k, _ in MAIN3} | {k for k, _ in EXTRA}
BAD_PKG = "_Proposal_with_GRs.pdf"


def _rows(v):
    if isinstance(v, dict):
        v = list(v.values())
    return [r for r in (v or []) if isinstance(r, dict)]


def _order(r):
    return (str(r.get("created_at") or ""), int(r.get("version") or 0), int(r.get("id") or 0))


def next_version(files, kind):
    vs = [int(r.get("version") or 0) for r in files if r.get("kind") == kind]
    return (max(vs) + 1) if vs else 1


def package_name(files, given=None):
    """§4.16: the package keeps the original proposal name (upload prefix stripped)."""
    if given:
        return given
    for kind in ("package_pdf", "proposal"):
        rs = [r for r in files if r.get("kind") == kind and r.get("original_name")]
        if rs:
            n = max(rs, key=_order)["original_name"]
            if kind == "proposal":
                import engine_supabase as E
                n = E.strip_upload_prefix(E.safe_name(n))
            return n
    return None


def package_pdfs(out):
    return sorted(os.path.join(out, f) for f in os.listdir(out)
                  if f.lower().endswith(".pdf") and not f.endswith(PREVIEW_RE))


def pick(out, suffix, prefix=""):
    found = sorted(f for f in os.listdir(out) if f.endswith(suffix))
    mine = [f for f in found if prefix and f.startswith(prefix + "_")]
    f = mine[0] if len(mine) == 1 else (max(found, key=lambda x: os.path.getmtime(os.path.join(out, x))) if found else None)
    return os.path.join(out, f) if f else None


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def ctype(name):
    """content_type field of a row (the file's own type, not the parts' text/plain)."""
    e = os.path.splitext(name)[1].lower()
    return {".pdf": "application/pdf", ".json": "application/json", ".docx": DOCX}.get(e, "application/octet-stream")


def collect(case_id, out, files, work, kinds, pkg_name, adds, no_spec, status):
    """-> [(kind, local path, row name)] in upload order; exits on a missing main output of a full run."""
    prefix = str(status.get("prefix") or "").strip()
    got, missing = [], []
    want = set(kinds) if kinds else None
    for kind, suffix in MAIN3:
        if want is not None and kind not in want:
            continue
        if kind == "package_pdf":
            pdfs = package_pdfs(out)
            if len(pdfs) > 1 and status.get("package_pdf"):
                pdfs = [p for p in pdfs if os.path.basename(p) == os.path.basename(str(status["package_pdf"]))] or pdfs
            if len(pdfs) != 1:
                missing.append(f"package PDF: {len(pdfs)}"); continue
            got.append((kind, pdfs[0], package_name(files, pkg_name) or os.path.basename(pdfs[0])))
        else:
            p = pick(out, suffix, prefix)
            if not p:
                missing.append("*" + suffix); continue
            got.append((kind, p, os.path.basename(p)))
    if missing:
        sys.exit("desk_publish: outputs missing — " + "; ".join(missing))
    for kind, suffix in EXTRA:
        if want is not None and kind not in want:
            continue
        p = pick(out, suffix, prefix)
        if p:
            got.append((kind, p, os.path.basename(p)))
        elif want is not None:
            sys.exit(f"desk_publish: {kind} asked but *{suffix} missing")
    for a in adds:
        kind, _, rest = a.partition("=")
        path, _, name = rest.partition("::")
        if not (kind and path and os.path.isfile(path)):
            sys.exit(f"desk_publish: bad --add {a}")
        got.append((kind, os.path.abspath(path), name or os.path.basename(path)))
    if not no_spec and work:
        for n in SPEC_FILES:
            p = os.path.join(work, n)
            if os.path.isfile(p):
                got.append(("spec", os.path.abspath(p), n))
    return got


def plan(argv):
    def opt(name, default=None, many=False):
        vals = []
        while name in argv:
            i = argv.index(name); vals.append(argv[i + 1]); del argv[i:i + 2]
        return vals if many else (vals[-1] if vals else default)
    files_p, next_id = opt("--files"), opt("--next-id")
    if next_id is not None:
        print("desk_publish plan: --next-id is ignored (ids are assigned by `rows --first-id`)", file=sys.stderr)
    work, kinds, pkg = opt("--work"), opt("--kinds"), opt("--package-name")
    adds = opt("--add", many=True)
    no_spec = "--no-spec" in argv
    if no_spec:
        argv.remove("--no-spec")
    if len(argv) != 4 or not files_p:
        sys.exit(__doc__)
    if pkg and pkg.endswith(BAD_PKG):
        sys.exit(f"desk_publish: package name must be the original proposal name, not *{BAD_PKG} (§4.16)")
    cid, out, run_id, sync = argv[0], os.path.abspath(argv[1]), argv[2], os.path.abspath(argv[3])
    files = [r for r in _rows(json.load(open(files_p, encoding="utf-8"))) if str(r.get("case_id")) == str(cid)]
    work = os.path.abspath(work) if work else os.path.dirname(out)
    st_p = os.path.join(out, "status.json")
    status = json.load(open(st_p, encoding="utf-8")) if os.path.isfile(st_p) else {}
    status = status if isinstance(status, dict) else {}
    kinds = [k.strip() for k in (kinds or "").split(",") if k.strip()] or None
    bad = [k for k in (kinds or []) if k not in KINDS]
    if bad:
        sys.exit(f"desk_publish: unknown --kinds {','.join(bad)} (known: {','.join(sorted(KINDS))})")
    items = collect(cid, out, files, work, kinds, pkg, adds, no_spec, status)
    os.makedirs(sync, exist_ok=True)
    uploads, rows, vers = [], [], {}
    for pos, (kind, path, name) in enumerate(items):
        if kind not in vers:
            vers[kind] = next_version(files, kind)   # spec.json + enclosures.json share one version
        big = os.path.getsize(path) > ASSET_MAX
        meta = {"content_type": ctype(name), "size_bytes": os.path.getsize(path)}
        if not path.lower().endswith(".pdf") or big:   # contract: only a PDF <= 19 MiB is one asset
            parts = split_b64(path, cid, f"r{run_id}_{pos:02d}_{kind}_v{vers[kind]}", os.path.join(sync, "parts"))
            for q in parts:
                uploads.append({"path": q, "kind": kind, "name": name, "type": "text/plain"})
            rows.append({"kind": kind, "name": name, "version": vers[kind], "store": "asset_parts",
                         "paths": parts, **meta})
        else:
            uploads.append({"path": path, "kind": kind, "name": name, "type": "application/pdf"})
            rows.append({"kind": kind, "name": name, "version": vers[kind], "store": "asset", "paths": [path],
                         **meta})
    json.dump(uploads, open(os.path.join(sync, "uploads.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(sync, "uploads.txt"), "w", encoding="utf-8") as f:
        f.write("".join(u["path"] + "\n" for u in uploads))
    json.dump({"case_id": int(cid) if str(cid).isdigit() else cid, "run_id": run_id, "rows": rows},
              open(os.path.join(sync, "plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if status and not kinds:
        lst = lambda k: status.get(k) if isinstance(status.get(k), list) else []
        patch = {"state": "done", "step": "तयार", "summary": status.get("summary") or "",
                 "letter_needed": bool(status.get("letter_needed")), "essential_points": lst("essential_points"),
                 "grs_attached": lst("grs_attached"), "grs_missing": lst("grs_missing"),
                 "warnings": [str(x).strip()[:300] for x in lst("warnings") if str(x).strip()],
                 "status_state": status.get("state"), "case": status.get("case") if isinstance(status.get("case"), dict) else None}
        json.dump(patch, open(os.path.join(sync, "run_patch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"desk_publish plan {cid}: {len(rows)} row(s), {len(uploads)} upload(s) -> {sync}")
    return 0


def rows_cmd(argv):
    assets_p = now = first = None
    if "--first-id" in argv:
        i = argv.index("--first-id"); first = argv[i + 1]; del argv[i:i + 2]
    if "--assets" in argv:
        i = argv.index("--assets"); assets_p = argv[i + 1]; del argv[i:i + 2]
    if "--now" in argv:
        i = argv.index("--now"); now = argv[i + 1]; del argv[i:i + 2]
    if len(argv) != 1 or not assets_p or not str(first or "").isdigit():
        sys.exit(__doc__)
    nid = int(first)
    if nid % 2 == 0:
        sys.exit(f"desk_publish rows: --first-id {nid} is even — the worker takes odd ids only (the page takes even ones)")
    sync = os.path.abspath(argv[0])
    pl = json.load(open(os.path.join(sync, "plan.json"), encoding="utf-8"))
    ids = json.load(open(assets_p, encoding="utf-8"))
    if not now:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    def aid(p):
        v = ids.get(p) or ids.get(os.path.basename(p))
        if not v:
            sys.exit(f"desk_publish rows: no asset id for {os.path.basename(p)} — write nothing")
        return str(v)
    writes, done, used = [], [], []
    for r in pl["rows"]:
        got = [aid(p) for p in r["paths"]]
        data = {"id": nid, "case_id": pl["case_id"], "kind": r["kind"], "original_name": r["name"],
                "version": r["version"], "uploaded_by": None, "created_at": now,
                "content_type": r.get("content_type"), "size_bytes": r.get("size_bytes")}
        if r["store"] == "asset":
            data.update(storage_path=f"asset:{got[0]}", asset_id=got[0], asset_parts=None)
        else:
            data.update(storage_path=f"asset-parts:{len(got)}", asset_id=None, asset_parts=got)
        writes.append({"op": "set", "collection": "case_files", "doc_id": str(nid), "data": data})
        done.append({"kind": r["kind"], "name": r["name"], "version": r["version"]})
        used.append(nid); nid += 2
    json.dump(writes, open(os.path.join(sync, "writes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(done, ensure_ascii=False))
    print("desk_publish rows: case_files ids " + ",".join(map(str, used)), file=sys.stderr)
    return 0


def main(argv):
    if argv[:1] == ["plan"]:
        return plan(argv[1:])
    if argv[:1] == ["rows"]:
        return rows_cmd(argv[1:])
    sys.exit(__doc__)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
