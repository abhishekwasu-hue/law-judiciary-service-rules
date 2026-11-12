"""Tests for tools/gr_text.py (text cache search) and the page-quality test of tools/build_text_cache.py."""
import io, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import gr_text  # noqa: E402

CACHE = ("=== पृ. 1 (textlayer) ===\nGOVERNMENT OF MAHARASHTRA\nशासन निर्णय क्रमांक वेतन-1311\n\n"
         "=== पृ. 2 (ocr) ===\nसदर शासन निर्णय महाराष्ट्र शासनाच्या संकेतस्थळावर उपलब्ध आहे.\n\n"
         "=== पृ. 3 (pending) ===\n")


def make(tmp_path):
    d = tmp_path / "text" / "gr"
    d.mkdir(parents=True)
    (d / "201612021708269510.txt").write_text(CACHE, encoding="utf-8")
    (tmp_path / "text" / "INDEX.tsv").write_text(
        "path\tpages\ttextlayer\tocr\treused\tpending\tstatus\tpdf_bytes\tavg_score\n"
        "pdf/gr/201612021708269510.pdf\t3\t1\t1\t0\t1\tpartial\t10\t0.5\n", encoding="utf-8")
    return str(tmp_path / "text")


def test_grep_lines_and_filters(tmp_path):
    td = make(tmp_path)
    out = io.StringIO()
    assert gr_text.grep("शासन निर्णय", td, out=out) == 2
    lines = out.getvalue().splitlines()
    assert lines[0] == "pdf/gr/201612021708269510.pdf p1: शासन निर्णय क्रमांक वेतन-1311"
    assert lines[1].startswith("pdf/gr/201612021708269510.pdf p2: ")
    out = io.StringIO()
    assert gr_text.grep("government", td, icase=True, out=out) == 1
    assert gr_text.grep("शासन", td, source="ocr", out=io.StringIO()) == 1
    assert gr_text.grep("शासन", td, path_glob="pdf/other/*", out=io.StringIO()) == 0


def test_show_by_path_and_code(tmp_path):
    td = make(tmp_path)
    out = io.StringIO()
    assert gr_text.show("pdf/gr/201612021708269510.pdf", 2, td, out=out) == 0
    assert out.getvalue().startswith("=== pdf/gr/201612021708269510.pdf पृ. 2 (ocr) ===\nसदर")
    out = io.StringIO()
    assert gr_text.show("201612021708269510", 3, td, out=out) == 0 and "(pending)" in out.getvalue()
    assert gr_text.show("201612021708269510", 9, td, out=io.StringIO()) == 1
    assert gr_text.show("nothing", 1, td, out=io.StringIO()) == 1


def test_status(tmp_path):
    td = make(tmp_path)
    out = io.StringIO()
    assert gr_text.status(td, out=out) == 0
    assert "pages 3: textlayer 1, ocr 1 (reused 0), pending 1; PDFs not done 1" in out.getvalue()


def test_page_quality():
    import pytest
    pytest.importorskip("fitz")
    import build_text_cache as b
    good = "सदर प्रकरणी शासन निर्णय दिनांक 10 जून 2019 नुसार त्यांच्या सेवेचा कालावधी विचारात घेण्यात यावा. " * 3
    assert b.accept(good)
    assert not b.accept(good.replace("निर्णय", "ननणणय"))          # ि -> न garbling
    assert not b.accept(good.replace("त्यांच्या", "तयांचया"))     # lost half forms
    assert b.accept("The Government servant shall be entitled to pension under rule 10. " * 3)
    assert not b.accept("´ÖÆüÖ¸üÖ™Òü ¿ÖÖÃÖ­Ö ´ÖÆüÖ¸üÖ™Òü ¿ÖÖÃÖ­Ö " * 5)  # legacy font mapping
    assert not b.accept("12")                                   # scanned page: no text
