"""tools/font_rule.py — the common Word font rule (Abhi 20.11 / 21.11.2026, INSTRUCTIONS §4.2 / §4.49):
Marathi text DVOT-SurekhMR on all four rFonts attributes; English text ascii / hAnsi Times New Roman + cs / eastAsia
DVOT-SurekhMR; digits / punctuation alone follow the paragraph; mixed runs split; the _Affidavit is left alone.
Run: python3 -m pytest -q tests/test_font_rule.py"""
import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import font_rule as F  # noqa: E402

import docx  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

W = F.W
DEVA, ENG = F.DEVA_FONTS, F.ENGLISH_FONTS


def fonts_of(r):
    fo = r.find(f"{{{W}}}rPr/{{{W}}}rFonts")
    return {a: fo.get(f"{{{W}}}{a}") for a in F.ATTRS} if fo is not None else None


def body(path):
    with zipfile.ZipFile(path) as z:
        return etree.fromstring(z.read("word/document.xml"))


def runs(root):
    return [(F._run_text(r), fonts_of(r), r) for r in root.iter(f"{{{W}}}r") if F._run_text(r)]


class SegmentsTest(unittest.TestCase):
    def test_marathi_only(self):
        self.assertEqual(F.segments("दि. 17.09.2026 रोजी पृ.13/प.वि."), [("दि. 17.09.2026 रोजी पृ.13/प.वि.", False)])

    def test_english_inside_marathi(self):
        self.assertEqual(F.segments("सदर (purely temporary and ad-hoc) नियुक्ती"),
                         [("सदर ", False), ("(purely temporary and ad-hoc)", True), (" नियुक्ती", False)])
        self.assertEqual(F.segments("वेतनश्रेणी PB-2 (रु. 9300-34800) मध्ये"),
                         [("वेतनश्रेणी ", False), ("PB-2", True), (" (रु. 9300-34800) मध्ये", False)])
        self.assertEqual(F.segments("Rule 58(4)(a) नुसार"), [("Rule 58(4)(a)", True), (" नुसार", False)])

    def test_text_without_devanagari_is_one_piece(self):
        self.assertEqual(F.segments("Email ID :- lnjd.desk6-mh@mah.gov.in"), [("Email ID :- lnjd.desk6-mh@mah.gov.in", True)])
        self.assertEqual(F.segments("12.05.2026"), [("12.05.2026", False)])
        self.assertEqual(F.segments(""), [])

    def test_pieces_rejoin(self):
        for t in ("नियम “Rule 5” व B-4(1)/15/2009 दि. 01.01.2020 आणि Writ Petition No. 35697/2026.",
                  "(a) अ; (b) ब", "abc दि"):
            self.assertEqual("".join(p for p, _ in F.segments(t)), t)


class ExpectedTest(unittest.TestCase):
    def test_expected(self):
        self.assertEqual(F.expected("सदर कर्मचारी"), DEVA)
        self.assertEqual(F.expected("दि. 17.09.2026", "दि. 17.09.2026"), DEVA)
        self.assertEqual(F.expected("Times", "Times"), ENG)
        self.assertEqual(F.expected("Rule 5", "Rule 5 नुसार"), ENG)
        self.assertEqual(F.expected("2.", "2. सदर"), DEVA)        # digits alone follow a Marathi paragraph
        self.assertEqual(F.expected("2.", "2. The petitioner"), ENG)  # ... and an English one
        self.assertIsNone(F.expected("  ", "x"))
        self.assertIsNone(F.expected(""))
        self.assertEqual(ENG, {"ascii": "Times New Roman", "hAnsi": "Times New Roman",
                               "cs": "DVOT-SurekhMR", "eastAsia": "DVOT-SurekhMR"})
        self.assertEqual(set(DEVA.values()), {"DVOT-SurekhMR"})


class ApplyDocxTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "t.docx")
        d = docx.Document()
        p = d.add_paragraph()
        r = p.add_run("सदर नियुक्ती (purely temporary and ad-hoc) स्वरूपाची असून  Rule 58 नुसार")
        r.bold = True
        r.font.size = docx.shared.Pt(14)
        rf = r._r.get_or_add_rPr().get_or_add_rFonts()
        rf.set(qn("w:asciiTheme"), "minorHAnsi")
        d.add_paragraph("The petitioner was appointed on 12.05.2010.")
        p3 = d.add_paragraph()
        p3.add_run("2. ")
        p3.add_run("सदर कर्मचारी")
        p4 = d.add_paragraph()
        p4.add_run("12.05.2026")                       # an English paragraph of digits only
        p5 = d.add_paragraph()
        p5.add_run("दिनांक\tPB-2")                     # a tab inside a mixed run
        d.sections[0].header.paragraphs[0].add_run("पृ. 1 Page")
        # a run inside a hyperlink
        p6 = d.add_paragraph()
        h = etree.SubElement(p6._p, qn("w:hyperlink"))
        hr = etree.SubElement(h, qn("w:r"))
        ht = etree.SubElement(hr, qn("w:t"))
        ht.text = "ई-मेल lnjd.desk6-mh@mah.gov.in"
        # a field run (instrText) is never split
        p7 = d.add_paragraph()
        fr = etree.SubElement(p7._p, qn("w:r"))
        etree.SubElement(fr, qn("w:fldChar")).set(qn("w:fldCharType"), "begin")
        etree.SubElement(fr, qn("w:t")).text = "पान PAGE"
        d.save(self.path)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_apply_splits_and_sets_fonts(self):
        self.assertGreater(F.problems([body(self.path)]), 0)
        n = F.apply_docx(self.path)
        self.assertGreater(n, 0)
        root = body(self.path)
        self.assertEqual(F.problems([root]), 0)
        got = {t: f for t, f, _ in runs(root)}
        self.assertEqual(got["सदर नियुक्ती "], DEVA)
        self.assertEqual(got["(purely temporary and ad-hoc)"], ENG)
        self.assertEqual(got[" स्वरूपाची असून  "], DEVA)
        self.assertEqual(got["Rule 58"], ENG)
        self.assertEqual(got[" नुसार"], DEVA)
        self.assertEqual(got["The petitioner was appointed on 12.05.2010."], ENG)
        self.assertEqual(got["2. "], DEVA)
        self.assertEqual(got["12.05.2026"], ENG)
        self.assertEqual(got["ई-मेल "], DEVA)
        self.assertEqual(got["lnjd.desk6-mh@mah.gov.in"], ENG)
        self.assertEqual(got["पान PAGE"], DEVA)        # field run: whole text, not split
        # the split runs keep the rPr (bold, size), lose the theme font, keep xml:space on edge spaces
        split = [r for t, _, r in runs(root) if t in ("सदर नियुक्ती ", "(purely temporary and ad-hoc)", " नुसार")]
        for r in split:
            self.assertIsNotNone(r.find(f"{{{W}}}rPr/{{{W}}}b"))
            self.assertEqual(r.find(f"{{{W}}}rPr/{{{W}}}sz").get(qn("w:val")), "28")
            self.assertIsNone(r.find(f"{{{W}}}rPr/{{{W}}}rFonts").get(qn("w:asciiTheme")))
            t = r.find(f"{{{W}}}t")
            if t.text != t.text.strip():
                self.assertEqual(t.get("{http://www.w3.org/XML/1998/namespace}space"), "preserve")
        # the hyperlink still holds its runs
        self.assertEqual(len(root.findall(f".//{{{W}}}hyperlink/{{{W}}}r")), 2)
        # the tab stays in the Marathi run, PB-2 gets its own run
        tab_run = [r for t, _, r in runs(root) if t == "दिनांक"][0]
        self.assertIsNotNone(tab_run.find(f"{{{W}}}tab"))
        self.assertEqual(got["PB-2"], ENG)
        # paragraph texts unchanged
        texts = [("".join(x.text or "" for x in p.iter(f"{{{W}}}t"))) for p in root.iter(f"{{{W}}}p")]
        self.assertIn("सदर नियुक्ती (purely temporary and ad-hoc) स्वरूपाची असून  Rule 58 नुसार", texts)
        # header too
        with zipfile.ZipFile(self.path) as z:
            hdr = [n for n in z.namelist() if n.startswith("word/header")]
            self.assertTrue(hdr)
            self.assertEqual(F.problems([etree.fromstring(z.read(n)) for n in hdr]), 0)
        # python-docx still opens it
        self.assertIn("The petitioner", "\n".join(p.text for p in docx.Document(self.path).paragraphs))

    def test_idempotent(self):
        F.apply_docx(self.path)
        with zipfile.ZipFile(self.path) as z:
            first = z.read("word/document.xml")
        self.assertEqual(F.apply_docx(self.path), 0)
        with zipfile.ZipFile(self.path) as z:
            self.assertEqual(z.read("word/document.xml"), first)

    def test_unsplit_mixed_run_is_a_problem(self):
        root = body(self.path)
        for r in root.iter(f"{{{W}}}r"):
            F._set_fonts(r, DEVA)   # fonts right for Marathi, but the English stretch not split
        self.assertGreater(F.problems([root]), 0)

    def test_affidavit_untouched(self):
        import clean_meta
        aff = os.path.join(self.dir, "aff.docx")
        d = docx.Document()
        r = d.add_paragraph().add_run("The deponent states")
        rf = r._r.get_or_add_rPr().get_or_add_rFonts()
        for a in ("ascii", "hAnsi"):
            rf.set(qn("w:" + a), "Times New Roman")
        for a in ("cs", "eastAsia"):
            rf.set(qn("w:" + a), "Mangal")
        d.add_paragraph().add_run("सदर Rule")
        d.save(aff)
        before = body(aff)
        clean_meta.clean_docx(aff, None, fonts=False)
        self.assertEqual(etree.tostring(body(aff)), etree.tostring(before))
        clean_meta.clean_docx(aff, None)   # default: the rule applied
        self.assertEqual(F.problems([body(aff)]), 0)

    def test_performance_large_document(self):
        big = os.path.join(self.dir, "big.docx")
        d = docx.Document()
        for i in range(12000):   # about a 400-page Study
            d.add_paragraph(f"परिच्छेद {i}: सदर Rule 58(4) नुसार दि. 17.09.2026 रोजी PB-2 वेतनश्रेणीत (pay band) नियुक्ती.")
        d.save(big)
        t0 = time.time()
        F.apply_docx(big)
        self.assertEqual(F.problems([body(big)]), 0)
        self.assertLess(time.time() - t0, 60)


if __name__ == "__main__":
    unittest.main()
