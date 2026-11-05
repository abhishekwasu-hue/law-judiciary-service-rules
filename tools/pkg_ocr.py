#!/usr/bin/env python3
"""pkg_ocr.py <package.pdf> <outdir> [--proposal-pages N --reuse DIR] [--dpi 110]
OCR of the returned package PDF with every page OCR'd only once (audit 05.11.2026 T-C). Output = the tools/prep_pages.py
layout that tools/extract_check.py --ocr-dir reads: <outdir>/p-NN.txt (text layer of package page NN),
<outdir>/p-NN.ocr.txt (OCR), <outdir>/pages.json {"pdf", "pdf_sha256" (of THIS package, so extract_check accepts it),
"pages", "dpi", "files": [{"page", "png": null, "png_small": null, "txt", "ocr"}], "ocr_lang", "ocr_error",
"has_text_layer", "reused_pages", "ocr_pages"}. No page images are kept.
- Pages 1..N (--proposal-pages) are the proposal pages: tools/pkg3.py puts the proposal first and leaves it untouched
  (only the "पृ. i / N" stamp is added). Their OCR is COPIED from --reuse = the tools/prep_pages.py directory of the
  proposal PDF, when that directory has OCR for exactly N pages (pages.json "pages" == N, ocr_lang set, every
  p-NN.ocr.txt present); otherwise those pages are OCR'd here too.
- Every other page (reply / extra PDFs, GR / rule pages) is rendered at --dpi and OCR'd here (tesseract, the language
  of prep_pages.ocr_lang, up to 4 threads).
Security (process-proposal.yml "Runner OCR of the package"): the runner passes --reuse ONLY its own copy of the
proposal OCR, made before the `engine` user exists ($RP/prop_ocr). It never reuses OCR the engine wrote
(/tmp/work/pkgpages, /tmp/case/pages after the engine ran): pages.json pdf_sha256 says which PDF a text belongs to, not
who wrote the text, so engine-written OCR could be made to "confirm" a forged extract.
Exit 0 also without tesseract (ocr_lang null unless reused OCR exists; extract_check then reports "unverifiable");
exit 1 when the package cannot be read, 2 on bad arguments."""
import glob, hashlib, json, os, re, shutil, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prep_pages  # noqa: E402  (ocr_lang, ocr_page; also imports pymupdf)

pymupdf = prep_pages.pymupdf


def reusable(reuse, n_prop):
    """{page: path of p-NN.ocr.txt} of a prep_pages.py dir with OCR for exactly n_prop pages, plus its ocr_lang;
    ({}, None) when it cannot be reused."""
    if not reuse or not n_prop or n_prop < 1:
        return {}, None
    try:
        with open(os.path.join(reuse, "pages.json"), encoding="utf-8") as f:
            info = json.load(f)
    except Exception:
        return {}, None
    if not isinstance(info, dict) or info.get("pages") != n_prop or not info.get("ocr_lang"):
        return {}, None
    got = {}
    for p in glob.glob(os.path.join(reuse, "p-*.ocr.txt")):
        m = re.search(r"p-0*(\d+)\.ocr\.txt$", os.path.basename(p))
        if m and os.path.isfile(p) and not os.path.islink(p):
            got[int(m.group(1))] = p
    if set(got) != set(range(1, n_prop + 1)):
        return {}, None
    return got, info["ocr_lang"]


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dpi, n_prop, reuse = 110, 0, None
    try:
        for opt in ("--dpi", "--proposal-pages", "--reuse"):
            if opt in argv:
                v = argv[argv.index(opt) + 1]
                args.remove(v)
                if opt == "--dpi":
                    dpi = int(v)
                elif opt == "--proposal-pages":
                    n_prop = int(v)
                else:
                    reuse = v
    except (IndexError, ValueError):
        print(__doc__); return 2
    if len(args) != 2:
        print(__doc__); return 2
    pdf, out = args
    try:
        doc = pymupdf.open(pdf)
    except Exception as e:
        print(f"pkg_ocr: cannot open {pdf}: {e}", file=sys.stderr); return 1
    n = len(doc)
    w = max(2, len(str(n)))
    os.makedirs(out, exist_ok=True)
    reused, rlang = reusable(reuse, n_prop) if n_prop <= n else ({}, None)
    files, has_text, todo = [], [], []
    for i, page in enumerate(doc):
        no, stem = i + 1, f"p-{i + 1:0{w}d}"
        txt = page.get_text("text") or ""
        with open(os.path.join(out, stem + ".txt"), "w", encoding="utf-8") as f:
            f.write(txt)
        has_text.append(bool(txt.strip()))
        rec = {"page": no, "png": None, "png_small": None, "txt": stem + ".txt", "ocr": None}
        if no in reused:
            shutil.copyfile(reused[no], os.path.join(out, stem + ".ocr.txt"))
            rec["ocr"] = stem + ".ocr.txt"
        else:
            todo.append(no)
        files.append(rec)
    exe, lang = prep_pages.ocr_lang()
    err, done = None, []
    if todo and exe and lang:
        tmp = tempfile.mkdtemp(prefix="pkg_ocr_")
        try:
            pngs = {}
            for no in todo:   # render in this thread (pymupdf documents are not shared between threads)
                pngs[no] = os.path.join(tmp, f"{no}.png")
                doc[no - 1].get_pixmap(dpi=dpi).save(pngs[no])

            def job(no):
                stem = f"p-{no:0{w}d}"
                prep_pages.ocr_page(exe, lang, pngs[no], os.path.join(out, stem + ".ocr.txt"))
                return no

            with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1))) as ex:
                for no in ex.map(job, todo):
                    files[no - 1]["ocr"] = f"p-{no:0{w}d}.ocr.txt"
                    done.append(no)
        except Exception as e:   # OCR is a cross-check only: never fatal
            err = str(e)[:300]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    elif todo and exe:
        err = "tesseract has no mar/eng language data"
    doc.close()
    sha = hashlib.sha256()
    with open(pdf, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            sha.update(b)
    info = {"pdf": os.path.basename(pdf), "pdf_sha256": sha.hexdigest(), "pages": n, "dpi": dpi, "small_dpi": None,
            "files": files, "ocr_lang": (lang if done else None) or (rlang if reused else None), "ocr_error": err,
            "has_text_layer": has_text, "reused_pages": sorted(reused), "ocr_pages": sorted(done)}
    with open(os.path.join(out, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(f"pkg_ocr: {n} page(s) -> {out} | reused {len(reused)} proposal page(s) | OCR {len(done)} page(s)"
          + (f" ({err})" if err else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
