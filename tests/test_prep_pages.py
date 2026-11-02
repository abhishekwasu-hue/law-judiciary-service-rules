#!/usr/bin/env python3
"""Test for tools/prep_pages.py: a 3-page PDF (one page with a text layer) -> 3 PNGs (+ 3 small 80 dpi PNGs), 3 .txt, pages.json;
OCR skipped cleanly when tesseract is missing (forced with an empty PATH). Run: py tests/test_prep_pages.py"""
import json, os, subprocess, sys, tempfile

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "prep_pages.py")


def check(c, msg):
    if not c: raise AssertionError(msg)
    print("ok  ", msg)


tmp = tempfile.mkdtemp()
pdf = os.path.join(tmp, "प्रस्ताव.pdf")
d = pymupdf.open()
for i in range(3):
    p = d.new_page(width=595, height=842)
    if i == 1:
        p.insert_text((72, 100), "Letter No. 123 dated 05.08.2026", fontsize=12)
    else:
        p.draw_rect(pymupdf.Rect(50, 50, 200, 200), color=(0, 0, 0))  # image-only page (like a scan)
d.save(pdf); d.close()


def run(out, path=None, *extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if path is not None: env["PATH"] = path
    return subprocess.run([sys.executable, TOOL, pdf, out, *extra], env=env, capture_output=True, text=True, encoding="utf-8")


# --- without tesseract (PATH emptied: shutil.which finds nothing)
out = os.path.join(tmp, "pages")
r = run(out, path=os.path.join(tmp, "nobin"))
check(r.returncode == 0, f"exit 0 without tesseract ({r.stderr.strip()[:200]})")
names = sorted(os.listdir(out))
check([n for n in names if n.endswith(".png") and not n.endswith(".sm.png")] == ["p-01.png", "p-02.png", "p-03.png"], "3 PNGs p-01..p-03")
check([n for n in names if n.endswith(".sm.png")] == ["p-01.sm.png", "p-02.sm.png", "p-03.sm.png"], "3 small PNGs p-NN.sm.png")
ws = pymupdf.Pixmap(os.path.join(out, "p-01.sm.png")).width
check(abs(ws - 595 * 80 / 72) <= 2, f"small PNG rendered at 80 dpi (width {ws})")
check([n for n in names if n.endswith(".txt")] == ["p-01.txt", "p-02.txt", "p-03.txt"], "3 text-layer files, no .ocr.txt")
w = pymupdf.Pixmap(os.path.join(out, "p-01.png")).width
check(abs(w - 595 * 110 / 72) <= 2, f"PNG rendered at 110 dpi (width {w})")
check("05.08.2026" in open(os.path.join(out, "p-02.txt"), encoding="utf-8").read(), "text layer of page 2 written")
check(open(os.path.join(out, "p-01.txt"), encoding="utf-8").read().strip() == "", "page without text: empty .txt")
info = json.load(open(os.path.join(out, "pages.json"), encoding="utf-8"))
check(info["pages"] == 3 and info["has_text_layer"] == [False, True, False], "pages.json: pages + has_text_layer")
check([f["png"] for f in info["files"]] == ["p-01.png", "p-02.png", "p-03.png"] and all(f["ocr"] is None for f in info["files"]),
      "pages.json: files[], ocr null")
import hashlib
check(info.get("pdf_sha256") == hashlib.sha256(open(pdf, "rb").read()).hexdigest(), "pages.json: pdf_sha256 of the rendered PDF")
check(info["ocr_lang"] is None and info["dpi"] == 110 and info["pdf"] == "प्रस्ताव.pdf", "pages.json: ocr_lang null, dpi, pdf name")
check(info["small_dpi"] == 80 and [f["png_small"] for f in info["files"]] == ["p-01.sm.png", "p-02.sm.png", "p-03.sm.png"],
      "pages.json: small_dpi + png_small")
out4 = os.path.join(tmp, "pages_nosmall")
r = run(out4, os.path.join(tmp, "nobin"), "--small-dpi", "0", "--dpi", "90")
info4 = json.load(open(os.path.join(out4, "pages.json"), encoding="utf-8"))
check(r.returncode == 0 and not any(n.endswith(".sm.png") for n in os.listdir(out4)) and info4["small_dpi"] is None
      and all(f["png_small"] is None for f in info4["files"]) and info4["dpi"] == 90
      and abs(pymupdf.Pixmap(os.path.join(out4, "p-01.png")).width - 595 * 90 / 72) <= 2,
      f"--small-dpi 0 --dpi 90: no small PNGs, full PNG at 90 dpi ({r.stderr.strip()[:200]})")

# --- fake tesseract (exercises the OCR path where tesseract is not installed): lists mar+eng, echoes lang + image
fb = os.path.join(tmp, "fakebin"); os.makedirs(fb)
fpy = os.path.join(fb, "fake_tess.py")
open(fpy, "w", encoding="utf-8").write(
    "import sys\n"
    "a = sys.argv[1:]\n"
    "if a == ['--list-langs']: print('List of available languages (3):'); print('eng'); print('mar'); print('osd'); sys.exit(0)\n"
    "print('OCR', a[a.index('-l') + 1], a[0].replace(chr(92), '/').split('/')[-1])\n")
if os.name == "nt":
    open(os.path.join(fb, "tesseract.bat"), "w").write(f'@"{sys.executable}" "{fpy}" %*\n')
else:
    t = os.path.join(fb, "tesseract"); open(t, "w").write(f'#!/bin/sh\nexec "{sys.executable}" "{fpy}" "$@"\n'); os.chmod(t, 0o755)
out3 = os.path.join(tmp, "pages_fake")
r = run(out3, fb + os.pathsep + os.environ.get("PATH", ""))
info = json.load(open(os.path.join(out3, "pages.json"), encoding="utf-8"))
check(r.returncode == 0 and info["ocr_lang"] == "mar+eng" and [f["ocr"] for f in info["files"]] == ["p-01.ocr.txt", "p-02.ocr.txt", "p-03.ocr.txt"],
      f"fake tesseract: ocr_lang mar+eng, 3 .ocr.txt ({r.stdout.strip()} {r.stderr.strip()[:200]})")
check(open(os.path.join(out3, "p-03.ocr.txt"), encoding="utf-8").read().split() == ["OCR", "mar+eng", "p-03.png"], "fake tesseract: per-page OCR text")
r = run(os.path.join(tmp, "pages_noocr"), fb + os.pathsep + os.environ.get("PATH", ""), "--no-ocr")
check(r.returncode == 0 and not any(n.endswith(".ocr.txt") for n in os.listdir(os.path.join(tmp, "pages_noocr"))), "--no-ocr: no OCR files")

# --- with tesseract, if installed here (the runner installs tesseract-ocr + tesseract-ocr-mar)
import shutil
if shutil.which("tesseract"):
    out2 = os.path.join(tmp, "pages_ocr")
    r = run(out2)
    info = json.load(open(os.path.join(out2, "pages.json"), encoding="utf-8"))
    check(r.returncode == 0 and info["ocr_lang"] in ("mar+eng", "eng", "mar") and all(f["ocr"] for f in info["files"]),
          f"OCR files + ocr_lang recorded ({info['ocr_lang']})")
    check("123" in open(os.path.join(out2, "p-02.ocr.txt"), encoding="utf-8").read(), "OCR reads page 2")
else:
    print("skip  OCR run (tesseract not installed)")

# --- unreadable PDF -> exit 1
bad = os.path.join(tmp, "bad.pdf"); open(bad, "wb").write(b"not a pdf")
r = subprocess.run([sys.executable, TOOL, bad, os.path.join(tmp, "x")], capture_output=True, text=True)
check(r.returncode == 1, "unreadable PDF: exit 1")
print("ALL TESTS PASSED")
