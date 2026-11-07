#!/usr/bin/env python3
"""case_state.py — one proposal = one saved case folder, so a correction round never re-reads the proposal
(Abhi, 07.11.2026: "पर्टिक्युलरली त्या प्रस्तावा संदर्भातच चॅटिंग होईल ... क्रेडिट्स वाचतील"; decisions: state in the
private repo under cases/, chat is the main path, engine stopped).

  save    <case_id> --work DIR --proposal PDF --package-name NAME --prefix PREFIX [--note TEXT]
          copies DIR/{spec,study,enclosures,marks}.json (those present) + the proposal PDF into cases/<case_id>/;
          enclosure / proposal_parts sources outside the repo are copied to cases/<case_id>/src/ and their paths
          rewritten (repo-relative); writes case.json and appends one line to history.tsv.
  load    <case_id> <workdir>
          copies the saved files into <workdir> (paths in enclosures.json stay repo-relative; run from the repo root)
          and prints case.json.
  rebuild <case_id> <outdir> [--package] [--no-study]
          rebuilds from the saved state only: (--package: pkg3 + highlight marks.json) -> lint -> every builder whose
          spec key is present (note/letter always; order(s), parawise, affidavit, lq) -> Study -> verify_outputs ->
          preview PNGs of the Note_and_Letter PDF in <outdir>/preview/. Exit code = verify's exit code (or the first
          failing step). Without --package the package PDF of the last rebuild in <outdir> (or cases/<id>/package.pdf
          if saved there) is reused, so a note-only correction costs one build.
  list    print saved cases (id, prefix, saved_at, last history note).

Run from the repo root. The proposal PDF is confidential: cases/ lives only in this private repo (Abhi 07.11.2026).
"""
import sys, os, json, shutil, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "cases")
STATE = ["spec.json", "study.json", "enclosures.json", "marks.json"]


def _arg(args, name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default


def _flag(args, name):
    if name in args:
        args.remove(name); return True
    return False


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _inside_repo(p):
    ap = os.path.abspath(os.path.join(ROOT, p) if not os.path.isabs(p) else p)
    return ap.startswith(ROOT + os.sep), ap


def _localise(path, cdir):
    """Return a repo-relative path for an enclosure source; copy it into cases/<id>/src/ when outside the repo."""
    inside, ap = _inside_repo(path)
    if inside and not ap.startswith(cdir + os.sep):
        return os.path.relpath(ap, ROOT)
    if inside:
        return os.path.relpath(ap, ROOT)
    if not os.path.exists(ap):
        sys.exit(f"case_state: enclosure source not found: {path}")
    os.makedirs(os.path.join(cdir, "src"), exist_ok=True)
    dst = os.path.join(cdir, "src", os.path.basename(ap))
    shutil.copy2(ap, dst)
    return os.path.relpath(dst, ROOT)


def _rewrite_enclosures(enc, cdir):
    items = enc if isinstance(enc, list) else enc.get("enclosures", [])
    for e in items:
        e["path"] = _localise(e["path"], cdir)
    if isinstance(enc, dict):
        parts = []
        for p in enc.get("proposal_parts", []):
            if isinstance(p, str):
                parts.append(_localise(p, cdir))
            else:
                p["path"] = _localise(p["path"], cdir); parts.append(p)
        if parts:
            enc["proposal_parts"] = parts
    return enc


def save(args):
    cid = args.pop(0)
    work = _arg(args, "--work"); prop = _arg(args, "--proposal")
    pkg = _arg(args, "--package-name"); prefix = _arg(args, "--prefix"); note = _arg(args, "--note", "saved")
    if not (work and prop and pkg and prefix):
        sys.exit("save: --work, --proposal, --package-name and --prefix are required")
    cdir = os.path.join(CASES, cid); os.makedirs(cdir, exist_ok=True)
    files = []
    for f in STATE:
        src = os.path.join(work, f)
        if not os.path.exists(src):
            continue
        data = json.load(open(src, encoding="utf-8"))
        if f == "enclosures.json":
            data = _rewrite_enclosures(data, cdir)
        json.dump(data, open(os.path.join(cdir, f), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        files.append(f)
    if "spec.json" not in files:
        sys.exit("save: spec.json missing in --work")
    if os.path.abspath(prop) != os.path.abspath(os.path.join(cdir, "proposal.pdf")):
        shutil.copy2(prop, os.path.join(cdir, "proposal.pdf"))
    try:
        import pymupdf
        npages = pymupdf.open(os.path.join(cdir, "proposal.pdf")).page_count
    except Exception:
        npages = None
    meta = {"case_id": cid, "prefix": prefix, "package_name": pkg, "proposal_pages": npages,
            "files": files + ["proposal.pdf"], "saved_at": _now()}
    old = os.path.join(cdir, "case.json")
    if os.path.exists(old):
        meta = {**json.load(open(old, encoding="utf-8")), **meta}
    json.dump(meta, open(old, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(cdir, "history.tsv"), "a", encoding="utf-8") as h:
        h.write(f"{_now()}\t{note}\n")
    print(json.dumps(meta, ensure_ascii=False, indent=1))


def load(args):
    cid, work = args[0], args[1]
    cdir = os.path.join(CASES, cid)
    if not os.path.isdir(cdir):
        sys.exit(f"load: no saved case {cid}")
    os.makedirs(work, exist_ok=True)
    for f in STATE + ["proposal.pdf", "case.json"]:
        if os.path.exists(os.path.join(cdir, f)):
            shutil.copy2(os.path.join(cdir, f), os.path.join(work, f))
    print(open(os.path.join(cdir, "case.json"), encoding="utf-8").read())


def _run(cmd):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def rebuild(args):
    cid, out = args.pop(0), os.path.abspath(args.pop(0))
    do_pkg = _flag(args, "--package"); no_study = _flag(args, "--no-study")
    cdir = os.path.join(CASES, cid)
    meta = json.load(open(os.path.join(cdir, "case.json"), encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    T = lambda n: os.path.join(ROOT, "tools", n)  # noqa: E731
    py = sys.executable
    spec = os.path.join(cdir, "spec.json"); prefix = meta["prefix"]
    pkg = os.path.join(out, meta["package_name"])
    if do_pkg or not os.path.exists(pkg):
        saved = os.path.join(cdir, "package.pdf")
        if not do_pkg and os.path.exists(saved):
            shutil.copy2(saved, pkg)
            if os.path.exists(saved + ".map.json"):
                shutil.copy2(saved + ".map.json", pkg + ".map.json")
        else:
            enc = os.path.join(cdir, "enclosures.json")
            if not os.path.exists(enc):
                sys.exit("rebuild: no enclosures.json saved — cannot build the package")
            rc = _run([py, T("pkg3.py"), os.path.join(cdir, "proposal.pdf"), enc, pkg])
            if rc:
                return rc
            marks = os.path.join(cdir, "marks.json")
            if os.path.exists(marks) and _run([py, T("highlight.py"), pkg, marks]):
                return 1
    total = None
    try:
        import pymupdf
        total = pymupdf.open(pkg).page_count
    except Exception:
        pass
    lint = [py, T("lint_spec.py"), spec] + (["--pages", str(total)] if total else [])
    if _run(lint):
        return 1
    s = json.load(open(spec, encoding="utf-8"))
    builders = [("build_note_letter.py", True)]
    builders += [("build_order.py", "order" in s or "orders" in s), ("build_parawise.py", "parawise" in s),
                 ("build_affidavit.py", "affidavit" in s), ("build_lq.py", "lq" in s)]
    for b, want in builders:
        if want and _run([py, T(b), spec, out, prefix, "--no-lint"]):
            return 1
    study = os.path.join(cdir, "study.json")
    if not no_study and os.path.exists(study):
        if _run([py, T("build_study.py"), study, os.path.join(out, prefix + "_Study.docx")]):
            return 1
    rc = _run([py, T("verify_outputs.py"), out, prefix, pkg, str(meta.get("proposal_pages") or 0)])
    prev = os.path.join(out, prefix + "_Note_and_Letter.pdf")
    if os.path.exists(prev):
        import pymupdf
        pd = os.path.join(out, "preview"); os.makedirs(pd, exist_ok=True)
        d = pymupdf.open(prev)
        for i, pg in enumerate(d):
            pg.get_pixmap(dpi=80).save(os.path.join(pd, f"{prefix}_p{i + 1:02d}.png"))
        print(f"preview: {d.page_count} page(s) -> {pd}")
    return rc


def list_cases(_):
    if not os.path.isdir(CASES):
        return 0
    for cid in sorted(os.listdir(CASES)):
        cj = os.path.join(CASES, cid, "case.json")
        if not os.path.exists(cj):
            continue
        m = json.load(open(cj, encoding="utf-8"))
        h = os.path.join(CASES, cid, "history.tsv")
        last = open(h, encoding="utf-8").read().strip().splitlines()[-1] if os.path.exists(h) else ""
        print(f"{cid}\t{m.get('prefix')}\t{m.get('saved_at')}\t{last}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("save", "load", "rebuild", "list"):
        sys.exit(__doc__)
    cmd = a.pop(0)
    sys.exit({"save": save, "load": load, "rebuild": rebuild, "list": list_cases}[cmd](a) or 0)
