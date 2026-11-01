#!/usr/bin/env python3
"""prep_pages.py <proposal.pdf> <outdir> [--dpi 110] [--no-ocr]
Pre-step for the engine (docs/QUALITY_AUDIT.md §5 item 1). No network. Per page NN (01, 02, ...):
  <outdir>/p-NN.png       page image at 110 dpi (pymupdf — no poppler needed); the model still LOOKS at every image
                          (PROPOSAL_SOP Step 1) — the text files below are only a cross-check.
  <outdir>/p-NN.txt       PDF text layer (empty file when the page has none, e.g. a scan)
  <outdir>/p-NN.ocr.txt   tesseract OCR, only when tesseract is installed (lang mar+eng if both installed, else eng /
                          whatever is available; the lang used is recorded)
  <outdir>/pages.json     {"pdf", "pages", "dpi", "files": [{"page", "png", "txt", "ocr"}], "ocr_lang", "ocr_error",
                           "has_text_layer": [bool per page]}
Exit 0 also when OCR is unavailable (ocr_lang = null); exit 1 only when the PDF cannot be read/rendered."""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

import pymupdf


def ocr_lang():
    """'mar+eng' / 'eng' / 'mar' / None — from `tesseract --list-langs`."""
    exe = shutil.which("tesseract")
    if not exe:
        return None, None
    try:
        r = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=30)
        langs = {l.strip() for l in (r.stdout + r.stderr).splitlines()[1:] if l.strip()}
    except Exception:
        return exe, None
    if {"mar", "eng"} <= langs:
        return exe, "mar+eng"
    for l in ("eng", "mar"):
        if l in langs:
            return exe, l
    return exe, None


def ocr_page(exe, lang, png, dst):
    r = subprocess.run([exe, png, "stdout", "-l", lang], capture_output=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip()[-200:] or f"exit {r.returncode}")
    open(dst, "wb").write(r.stdout)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dpi = 110
    if "--dpi" in argv:
        dpi = int(argv[argv.index("--dpi") + 1]); args.remove(str(dpi))
    if len(args) != 2:
        print(__doc__); return 2
    src, out = args
    os.makedirs(out, exist_ok=True)
    try:
        doc = pymupdf.open(src)
    except Exception as e:
        print(f"prep_pages: cannot open {src}: {e}", file=sys.stderr); return 1
    n = len(doc); w = max(2, len(str(n)))
    files, has_text = [], []
    for i, page in enumerate(doc):
        stem = f"p-{i + 1:0{w}d}"
        page.get_pixmap(dpi=dpi).save(os.path.join(out, stem + ".png"))
        txt = page.get_text("text") or ""
        open(os.path.join(out, stem + ".txt"), "w", encoding="utf-8").write(txt)
        has_text.append(bool(txt.strip()))
        files.append({"page": i + 1, "png": stem + ".png", "txt": stem + ".txt", "ocr": None})
    doc.close()
    exe, lang = (None, None) if "--no-ocr" in argv else ocr_lang()
    err = None
    if exe and lang:
        def job(f):
            dst = f["png"][:-4] + ".ocr.txt"
            ocr_page(exe, lang, os.path.join(out, f["png"]), os.path.join(out, dst))
            return dst
        try:
            with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1))) as ex:
                for f, dst in zip(files, ex.map(job, files)):
                    f["ocr"] = dst
        except Exception as e:  # OCR is only a cross-check: never fatal
            err = str(e)[:300]
    elif exe:
        err = "tesseract has no mar/eng language data"
    info = {"pdf": os.path.basename(src), "pages": n, "dpi": dpi, "files": files,
            "ocr_lang": lang if exe and lang and not err else None, "ocr_error": err, "has_text_layer": has_text}
    json.dump(info, open(os.path.join(out, "pages.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"prep_pages: {n} page(s) -> {out} | text layer on {sum(has_text)} | ocr {info['ocr_lang'] or 'none'}"
          + (f" ({err})" if err else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
