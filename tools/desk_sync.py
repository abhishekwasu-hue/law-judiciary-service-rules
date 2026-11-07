#!/usr/bin/env python3
"""desk_sync.py — prepare one rebuilt case for the claude.ai "प्रस्ताव कक्ष" page (chunks, assets, case patch).

Usage: python tools/desk_sync.py <case_id> <outdir> <syncdir>
  <outdir>  = the folder `case_state.py rebuild <case_id> <outdir>` wrote into.
Writes into <syncdir>:
  chunks/<case_id>__<kind>__<n>.json  desk_chunks docs (kind note_letter; study when <PREFIX>_Study.docx exists)
                                      -> ArtifactData batch set, collection "outputs", doc_id = file stem
  assets.txt                          absolute paths to upload as page assets (package PDF, Note_and_Letter PDF; only
                                      those that exist). A file over 19 MiB goes as base64 text parts (parts/…b64.<n>.txt),
                                      output store "asset_parts", ref = list; the page decodes and joins them.
  case_patch.json                     {"path":"chat","case_id", "outputs":[...], "paras":[...]}; asset outputs carry
                                      ref "__ASSET__<basename>" to be replaced by the uploaded asset url
Paragraph ids (for targeting corrections; index-based on spec.json, label = the number printed in the note):
  note.first             note["first"]          (printed 1.)
  note.p<i+1>            note["paras"][i]       (printed i+2 when no table precedes; tables are unnumbered)
  note.p<i+1>.s<j>       note["sub"][str(i)][j-1]  (sub keys are 0-based indexes into paras — mkdocs.build_note)
  letter.p<n> / letter.pt<n> / letter.intro   letter["paras"|"body"][n-1] / letter["points"][n-1] (a table -> label
                         "पत्र तक्ता"; labels use the spec position, the printed "(n)" renumbering may differ) / letter["intro"]
Exit 1 with a message if the case or the Note_and_Letter docx is missing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(ROOT, "cases")
sys.path.insert(0, HERE)
from desk_chunks import CHUNK  # noqa: E402  (same chunk size as desk_chunks.py)

TEXT_MAX = 160
ASSET_MAX = 19 * 1024 * 1024      # page asset cap is 20 MiB
PART_CHARS = 15 * 1024 * 1024     # base64 chars per text part


def split_b64(path, case_id, kind, partdir):
    """A file over ASSET_MAX -> <partdir>/<case>__<kind>.b64.<n>.txt (base64 text, PART_CHARS each); returns paths."""
    import base64
    os.makedirs(partdir, exist_ok=True)
    stem = f"{case_id}__{kind}.b64."
    for old in os.listdir(partdir):
        if old.startswith(stem):
            os.remove(os.path.join(partdir, old))
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    out = []
    for n, i in enumerate(range(0, len(b64), PART_CHARS)):
        q = os.path.join(partdir, f"{stem}{n}.txt")
        with open(q, "w", encoding="ascii") as f:
            f.write(b64[i:i + PART_CHARS])
        out.append(q)
    return out


def write_chunks(path, case_id, kind, chunkdir):
    """Same logic/record as desk_chunks.main; returns (outputs record, number of chunks)."""
    import base64
    name = os.path.basename(path)
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    parts = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)] or [""]
    ref = f"{case_id}__{kind}"
    for old in os.listdir(chunkdir):   # stale chunks of an earlier sync of this case/kind
        if old.startswith(ref + "__") and old.endswith(".json"):
            os.remove(os.path.join(chunkdir, old))
    for n, p in enumerate(parts):
        with open(os.path.join(chunkdir, f"{ref}__{n}.json"), "w", encoding="utf-8") as f:
            json.dump({"case": case_id, "kind": kind, "n": n, "total": len(parts), "name": name, "b64": p}, f,
                      ensure_ascii=False)
    return {"kind": kind, "name": name, "store": "db", "ref": ref}, len(parts)


def _t(s):
    return " ".join(str(s).split())[:TEXT_MAX]


def para_targets(spec):
    out = []
    n = spec.get("note") or {}
    if n.get("first"):
        out.append({"id": "note.first", "label": "टिप्पणी परि. 1", "text": _t(n["first"])})
    subs = n.get("sub") or {}
    k = 2  # printed number of the next numbered para (mkdocs.build_note)
    for i, t in enumerate(n.get("paras") or []):
        if isinstance(t, dict):
            out.append({"id": f"note.p{i + 1}", "label": "टिप्पणी तक्ता", "text": "[तक्ता]"})
            pk = None
        else:
            out.append({"id": f"note.p{i + 1}", "label": f"टिप्पणी परि. {k}", "text": _t(t)})
            pk = k; k += 1
        for j, s in enumerate(subs.get(str(i)) or [], 1):
            lab = f"टिप्पणी परि. {pk} ({j})" if pk else f"टिप्पणी तक्ता ({j})"
            out.append({"id": f"note.p{i + 1}.s{j}", "label": lab, "text": _t(s)})
    L = spec.get("letter")
    if isinstance(L, dict):
        if L.get("intro"):
            out.append({"id": "letter.intro", "label": "पत्र प्रस्तावना", "text": _t(L["intro"])})
        for key in ("paras", "body"):
            for i, t in enumerate(L.get(key) or [], 1):
                if isinstance(t, str):
                    out.append({"id": f"letter.p{i}", "label": f"पत्र परि. {i}", "text": _t(t)})
        for i, t in enumerate(L.get("points") or [], 1):   # i = 1-based position in letter.points (tables included)
            if isinstance(t, dict):
                out.append({"id": f"letter.pt{i}", "label": "पत्र तक्ता", "text": "[तक्ता]"})
            else:
                out.append({"id": f"letter.pt{i}", "label": f"पत्र मुद्दा {i}", "text": _t(t)})
    return out


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    cid, outdir, sync = argv[0], os.path.abspath(argv[1]), os.path.abspath(argv[2])
    cdir = os.path.join(CASES, cid)
    cj, sj = os.path.join(cdir, "case.json"), os.path.join(cdir, "spec.json")
    if not (os.path.exists(cj) and os.path.exists(sj)):
        sys.exit(f"desk_sync: case {cid} not found (need {cj} and {sj})")
    meta = json.load(open(cj, encoding="utf-8"))
    spec = json.load(open(sj, encoding="utf-8-sig"))
    prefix = meta["prefix"]
    nl = os.path.join(outdir, f"{prefix}_Note_and_Letter.docx")
    if not os.path.exists(nl):
        sys.exit(f"desk_sync: {nl} missing — run case_state.py rebuild {cid} {outdir} first")
    chunkdir = os.path.join(sync, "chunks")
    os.makedirs(chunkdir, exist_ok=True)
    outputs, summary = [], []
    rec, nc = write_chunks(nl, cid, "note_letter", chunkdir); outputs.append(rec); summary.append(f"note_letter {nc} chunk(s)")
    st = os.path.join(outdir, f"{prefix}_Study.docx")
    if os.path.exists(st):
        rec, nc = write_chunks(st, cid, "study", chunkdir); outputs.append(rec); summary.append(f"study {nc} chunk(s)")
    assets = []
    for kind, fn in (("package_pdf", meta.get("package_name")), ("note_letter_pdf", f"{prefix}_Note_and_Letter.pdf")):
        p = os.path.join(outdir, fn) if fn else None
        if p and os.path.exists(p):
            if os.path.getsize(p) <= ASSET_MAX:
                assets.append(p)
                outputs.append({"kind": kind, "name": fn, "store": "asset", "ref": f"__ASSET__{fn}"})
            else:   # over the page's asset cap: exact bytes as base64 text parts, joined again by the page
                parts = split_b64(p, cid, kind, os.path.join(sync, "parts"))
                assets += parts
                outputs.append({"kind": kind, "name": fn, "store": "asset_parts",
                                "ref": [f"__ASSET__{os.path.basename(x)}" for x in parts]})
    with open(os.path.join(sync, "assets.txt"), "w", encoding="utf-8") as f:
        f.write("".join(a + "\n" for a in assets))
    paras = para_targets(spec)
    patch = {"path": "chat", "case_id": cid, "outputs": outputs, "paras": paras}
    with open(os.path.join(sync, "case_patch.json"), "w", encoding="utf-8") as f:
        json.dump(patch, f, ensure_ascii=False, indent=1)
    print(f"desk_sync {cid}: {', '.join(summary)}; {len(assets)} asset(s); {len(paras)} para target(s) -> {sync}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
