#!/usr/bin/env python3
"""prep_pages.py <proposal.pdf | reply.jpg/.png/.tif | reply.docx> <outdir> [--dpi 110] [--small-dpi 80] [--no-ocr]
Pre-step for the engine (docs/QUALITY_AUDIT.md §5 item 1). No network. Per page NN (01, 02, ...):
  <outdir>/p-NN.png       page image at 110 dpi (pymupdf — no poppler needed); the main run READS this image of every
                          page (PROPOSAL_SOP Step 1) — the text files below are only a cross-check.
  <outdir>/p-NN.sm.png    the same page at 80 dpi (--small-dpi; 0 = none): a thumbnail for quick overviews only
                          (page order, which page is which), never for reading values
Input that is not a PDF (A1 H9: replies sent as a photo or a Word file): an image (jpg, jpeg, png, tif, tiff, bmp,
gif, webp; one page per image frame) is converted with pymupdf, a .docx/.doc/.odt/.rtf with LibreOffice (private
profile, 180 s limit) to <outdir>/source.pdf first ("converted_pdf" in pages.json) — that PDF can be enclosed in the
package (tools/pkg3.py). A password-protected PDF is refused with a clear message (exit 1).
  <outdir>/p-NN.txt       PDF text layer (empty file when the page has none, e.g. a scan)
  <outdir>/p-NN.ocr.txt   tesseract OCR, only when tesseract is installed (lang mar+eng if both installed, else eng /
                          whatever is available; the lang used is recorded)
  <outdir>/pages.json     {"pdf", "pdf_sha256" (of the rendered PDF: extract_check.py ignores OCR of another file), "pages", "dpi", "small_dpi", "files": [{"page", "png", "png_small", "txt", "ocr"}],
                           "ocr_lang", "ocr_error",
                           "has_text_layer": [bool per page]}
Exit 0 also when OCR is unavailable (ocr_lang = null); exit 1 only when the PDF cannot be read/rendered."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

import pymupdf

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp")
OFFICE_EXT = (".docx", ".doc", ".odt", ".rtf")


def to_pdf(src, out):
    """Image / Word file -> <out>/source.pdf; returns its path (raises RuntimeError with a short reason)."""
    ext = os.path.splitext(src)[1].lower()
    dst = os.path.join(out, "source.pdf")
    if ext in IMAGE_EXT:
        with pymupdf.open(src) as img:  # every frame of the image -> one PDF page (img2pdf via pymupdf)
            data = img.convert_to_pdf()
        with pymupdf.open("pdf", data) as pdf:
            pdf.save(dst)
        return dst
    if ext in OFFICE_EXT:
        soffice = shutil.which("soffice") or shutil.which("soffice.exe")
        if not soffice:
            raise RuntimeError("LibreOffice (soffice) not installed — cannot convert " + ext)
        prof = tempfile.mkdtemp(prefix="lo_prep_")
        tmp = tempfile.mkdtemp(prefix="prep_conv_")
        try:
            r = subprocess.run([soffice, "-env:UserInstallation=file://" + prof.replace(os.sep, "/"), "--headless",
                                "--convert-to", "pdf", "--outdir", tmp, src], stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=180)
            got = os.path.join(tmp, os.path.splitext(os.path.basename(src))[0] + ".pdf")
            if r.returncode != 0 or not os.path.exists(got):
                raise RuntimeError(f"soffice conversion failed (rc {r.returncode})")
            shutil.move(got, dst)
        except subprocess.TimeoutExpired:
            raise RuntimeError("soffice conversion timed out (180 s)")
        finally:
            shutil.rmtree(prof, ignore_errors=True); shutil.rmtree(tmp, ignore_errors=True)
        return dst
    return src


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
    dpi, small = 110, 80
    if "--dpi" in argv:
        v = argv[argv.index("--dpi") + 1]; dpi = int(v); args.remove(v)
    if "--small-dpi" in argv:
        v = argv[argv.index("--small-dpi") + 1]; small = int(v); args.remove(v)
    if len(args) != 2:
        print(__doc__); return 2
    src, out = args
    os.makedirs(out, exist_ok=True)
    converted = None
    try:
        conv = to_pdf(src, out)
        if conv != src:
            converted, src = os.path.basename(conv), conv
    except Exception as e:
        print(f"prep_pages: cannot convert {src} to PDF: {e}", file=sys.stderr); return 1
    try:
        doc = pymupdf.open(src)
    except Exception as e:
        print(f"prep_pages: cannot open {src}: {e}", file=sys.stderr); return 1
    if doc.needs_pass:
        print(f"prep_pages: {src} is password-protected (encrypted PDF) — upload a copy without a password", file=sys.stderr)
        return 1
    n = len(doc); w = max(2, len(str(n)))
    files, has_text = [], []
    for i, page in enumerate(doc):
        stem = f"p-{i + 1:0{w}d}"
        page.get_pixmap(dpi=dpi).save(os.path.join(out, stem + ".png"))
        if small > 0:
            page.get_pixmap(dpi=small).save(os.path.join(out, stem + ".sm.png"))
        txt = page.get_text("text") or ""
        open(os.path.join(out, stem + ".txt"), "w", encoding="utf-8").write(txt)
        has_text.append(bool(txt.strip()))
        files.append({"page": i + 1, "png": stem + ".png", "png_small": stem + ".sm.png" if small > 0 else None,
                      "txt": stem + ".txt", "ocr": None})
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
    sha = hashlib.sha256()
    with open(src, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""): sha.update(b)
    info = {"pdf": os.path.basename(src), "pdf_sha256": sha.hexdigest(), "pages": n, "dpi": dpi, "small_dpi": small if small > 0 else None, "files": files,
            "ocr_lang": lang if exe and lang and not err else None, "ocr_error": err, "has_text_layer": has_text,
            "converted_pdf": converted}
    json.dump(info, open(os.path.join(out, "pages.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"prep_pages: {n} page(s) -> {out} | text layer on {sum(has_text)} | ocr {info['ocr_lang'] or 'none'}"
          + (f" ({err})" if err else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
