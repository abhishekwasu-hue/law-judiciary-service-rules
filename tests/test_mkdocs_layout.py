"""Layout of the note built by tools/mkdocs.py: table column widths from content, and the signer chain kept on the page
of the last body para (live run CR 14/2026: "28.02.19 / 70" split in a 7-column table; signers alone on a new page)."""
import os, sys, tempfile, shutil, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import docx
    from docx.oxml.ns import qn
    import mkdocs
except ImportError:   # python-docx missing
    docx = None

SERVICE = [["अ.क्र.", "नाव व पदनाम", "जन्म दिनांक", "सेवेतील नियुक्तीचा दिनांक",
            "वयाची 35 वर्षे पूर्ण होण्यापूर्वी शासकीय सेवेत प्रवेश", "विभागीय चौकशी/कार्यवाही",
            "शारीरिकदृष्ट्या सेवेत राहण्यास पात्र"],
           ["1", "श्री. सिद्धेश्वर शरणप्पा कुर्ले, लघुलेखक (श्रेणी-1), जिल्हा न्यायालय, सोलापूर", "28.02.1970",
            "14.09.1998", "होय", "नाही", "होय"]]
SIGNERS = ["(अ.मा. वसू)", "क. अ. (अ.का.)", "अ.स. (श्री. वडनेरकर)", "उ.वि.स. नि. उ.स. (श्री. बोंद्रे)",
           "सचिव व व. वि. स. (श्री. बिले)"]


def _cm(tw):
    return int(tw) * 2.54 / 1440.0


@unittest.skipIf(docx is None, "python-docx not installed")
class TestNoteLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, paras, closing):
        spec = {"desk": "law-desk6", "note": {"first": "पत्रास अनुसरून सादर.", "paras": paras, "closing": closing,
                                                "signers": SIGNERS}}
        out = os.path.join(self.tmp, "n.docx")
        mkdocs.build_note(spec, out)
        return docx.Document(out)

    def test_col_widths_dates_fit(self):
        ws = mkdocs.col_widths(SERVICE, 15.0)
        self.assertAlmostEqual(sum(ws), 15.0, places=6)
        date = mkdocs._em_cm(mkdocs.text_em("28.02.1970")) + 0.38   # text + Word's default cell margins
        self.assertGreater(ws[2], date); self.assertGreater(ws[3], date)
        self.assertGreater(ws[1], ws[4])   # the long name column gets more of the spare width
        amounts = [["अ.क्र.", "रक्कम"], ["1", "1,23,45,678"]]
        self.assertGreater(mkdocs.col_widths(amounts, 15.0)[1], mkdocs._em_cm(mkdocs.text_em("1,23,45,678")))

    def test_empty_fill_in_column_has_room(self):
        rows = [["अ.क्र.", "तपशील", "माहिती"], ["1", "पद प्रथम रिक्त झाल्याचा दिनांक " * 3, ""]]
        self.assertGreaterEqual(mkdocs.col_widths(rows, 14.5)[2], 3.0)

    def test_table_grid_and_cells_text_width(self):
        d = self.build(["सेवा तपशील खालीलप्रमाणे आहे:-", {"table": SERVICE}], "सबब, प्रस्ताव मान्यतेस्तव सादर.")
        sec = d.sections[0]
        text_w = (sec.page_width - sec.left_margin - sec.right_margin) * 2.54 / 914400
        tbl = d.tables[0]._tbl
        grid = [_cm(g.get(qn("w:w"))) for g in tbl.tblGrid.findall(qn("w:gridCol"))]
        self.assertEqual(len(grid), 7)
        self.assertAlmostEqual(sum(grid), text_w, delta=0.05)
        self.assertAlmostEqual(_cm(tbl.tblPr.find(qn("w:tblW")).get(qn("w:w"))), text_w, delta=0.05)
        self.assertEqual(tbl.tblPr.find(qn("w:tblLayout")).get(qn("w:type")), "fixed")
        for row in d.tables[0].rows:
            for j, c in enumerate(row.cells):
                self.assertAlmostEqual(c.width.cm, grid[j], delta=0.02)

    def test_signers_keep_with_last_para(self):
        closing = "उपरोक्त वस्तुस्थिती विचारात घेता, … सबब, पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."
        d = self.build(["सदर पत्रान्वये … विनंती केली आहे."], closing)
        ps = d.paragraphs
        ci = next(i for i, p in enumerate(ps) if "सबब" in p.text)
        si = [next(i for i, p in enumerate(ps) if p.text.strip() == s) for s in SIGNERS]
        self.assertTrue(ps[ci].paragraph_format.keep_with_next)
        self.assertTrue(ps[ci].paragraph_format.keep_together)
        for i in range(ci + 1, si[-1]):   # blank line + every signer but the last
            self.assertTrue(ps[i].paragraph_format.keep_with_next, ps[i].text)
        self.assertFalse(ps[si[-1]].paragraph_format.keep_with_next)
        self.assertFalse(any(p.paragraph_format.page_break_before for p in ps[:si[-1] + 1]))

    def test_bare_closing_chains_the_sabab_para(self):
        d = self.build(["सबब, प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."], "मान्यतेस्तव सादर.")
        ps = d.paragraphs
        sab = next(p for p in ps if "सबब" in p.text)
        self.assertTrue(sab.paragraph_format.keep_with_next)


if __name__ == "__main__":
    unittest.main()
