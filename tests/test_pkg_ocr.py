"""tools/pkg_ocr.py (audit 05.11.2026 T-C): every package page OCR'd once — proposal pages copied from the runner's own
prep_pages OCR, only the other pages OCR'd; output accepted by extract_check.py --ocr-dir (pdf_sha256 of the package).
Run: python3 -m pytest -q tests/test_pkg_ocr.py"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
pymupdf = pytest.importorskip("pymupdf")
import pkg_ocr  # noqa: E402
import prep_pages  # noqa: E402
import extract_check  # noqa: E402


def make_pdf(path, n):
    d = pymupdf.open()
    for i in range(n):
        d.new_page().insert_text((72, 72), f"page {i + 1}")
    d.save(path)
    d.close()


@pytest.fixture
def fake_ocr(monkeypatch):
    calls = []

    def ocr_page(exe, lang, png, dst):
        calls.append(os.path.basename(png))
        open(dst, "w", encoding="utf-8").write("OCR " + os.path.basename(png))
    monkeypatch.setattr(prep_pages, "ocr_lang", lambda: ("tesseract", "mar+eng"))
    monkeypatch.setattr(prep_pages, "ocr_page", ocr_page)
    return calls


def reuse_dir(tmp_path, n):
    r = tmp_path / "prop_ocr"
    r.mkdir()
    for i in range(1, n + 1):
        (r / f"p-{i:02d}.ocr.txt").write_text(f"PROPOSAL OCR {i}", encoding="utf-8")
    (r / "pages.json").write_text(json.dumps({"pages": n, "ocr_lang": "mar+eng"}), encoding="utf-8")
    return str(r)


def test_reuses_proposal_pages_and_ocrs_the_rest(tmp_path, fake_ocr):
    pdf, out = str(tmp_path / "pkg.pdf"), str(tmp_path / "out")
    make_pdf(pdf, 5)
    rc = pkg_ocr.main([pdf, out, "--proposal-pages", "2", "--reuse", reuse_dir(tmp_path, 2)])
    assert rc == 0
    info = json.load(open(os.path.join(out, "pages.json"), encoding="utf-8"))
    assert info["reused_pages"] == [1, 2] and info["ocr_pages"] == [3, 4, 5]
    assert sorted(fake_ocr) == ["3.png", "4.png", "5.png"]          # each page OCR'd once, proposal pages never
    assert open(os.path.join(out, "p-01.ocr.txt"), encoding="utf-8").read() == "PROPOSAL OCR 1"
    assert open(os.path.join(out, "p-04.ocr.txt"), encoding="utf-8").read() == "OCR 4.png"
    assert "page 3" in open(os.path.join(out, "p-03.txt"), encoding="utf-8").read()
    assert not extract_check.stale_ocr(out, pdf)                       # extract_check accepts it for THIS package
    assert not [f for f in os.listdir(out) if f.endswith(".png")]


@pytest.mark.parametrize("pages_json", [{"pages": 3, "ocr_lang": "mar+eng"}, {"pages": 2, "ocr_lang": None}])
def test_unusable_reuse_dir_means_full_ocr(tmp_path, fake_ocr, pages_json):
    pdf, out = str(tmp_path / "pkg.pdf"), str(tmp_path / "out")
    make_pdf(pdf, 4)
    r = reuse_dir(tmp_path, 2)
    open(os.path.join(r, "pages.json"), "w").write(json.dumps(pages_json))
    assert pkg_ocr.main([pdf, out, "--proposal-pages", "2", "--reuse", r]) == 0
    info = json.load(open(os.path.join(out, "pages.json"), encoding="utf-8"))
    assert info["reused_pages"] == [] and info["ocr_pages"] == [1, 2, 3, 4]


def test_missing_page_file_and_no_tesseract(tmp_path, monkeypatch):
    pdf, out = str(tmp_path / "pkg.pdf"), str(tmp_path / "out")
    make_pdf(pdf, 3)
    r = reuse_dir(tmp_path, 2)
    monkeypatch.setattr(prep_pages, "ocr_lang", lambda: (None, None))
    assert pkg_ocr.main([pdf, out, "--proposal-pages", "2", "--reuse", r]) == 0
    info = json.load(open(os.path.join(out, "pages.json"), encoding="utf-8"))
    assert info["reused_pages"] == [1, 2] and info["ocr_pages"] == [] and info["ocr_lang"] == "mar+eng"
    os.remove(os.path.join(r, "p-02.ocr.txt"))
    out2 = str(tmp_path / "out2")
    assert pkg_ocr.main([pdf, out2, "--proposal-pages", "2", "--reuse", r]) == 0
    assert json.load(open(os.path.join(out2, "pages.json")))["reused_pages"] == []


def test_bad_args_and_unreadable(tmp_path):
    assert pkg_ocr.main(["only-one"]) == 2
    assert pkg_ocr.main([str(tmp_path / "x.pdf"), str(tmp_path / "o"), "--dpi", "z"]) == 2
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    assert pkg_ocr.main([str(bad), str(tmp_path / "o")]) == 1
