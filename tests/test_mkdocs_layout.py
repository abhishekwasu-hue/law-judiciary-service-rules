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


def test_letter_layout_438(tmp_path):
    """INSTRUCTIONS §4.38 (Abhi 06.11.2026): विषय/संदर्भ bold block shifted right with hanging lines; requested points
    "(1)" … one sequence, inside the paragraph; later paragraphs "2."; "प्रत :-" once with numbered copies."""
    import json, docx
    sp = json.load(open(os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json"), encoding="utf-8"))
    L = sp["letter"]
    L["refs"] = ["1) आपले पत्र दि. 25.03.2026.", "2) या विभागाचे पत्र दि. 30.03.2026."]
    L["points"] = ["1)\tपहिली माहिती:-", {"table": [["अ.क्र.", "दिनांक"], ["1", ""]]},
                   "\tतसेच, खालील कागदपत्रे उपलब्ध करून देण्यात यावीत, ही विनंती:-", "1)\tआदेशाची प्रत;", "(2)\tअहवाल.",
                   "\tतसेच, एकत्रित प्रस्ताव सादर करण्यात यावा, ही विनंती."]
    L["copies"] = ["प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, भंडारा यांना आवश्यक कार्यवाहीसाठी"]
    out = str(tmp_path / "L.docx")
    import mkdocs as M
    M.build_letter(sp, out, L)
    ps = [p for p in docx.Document(out).paragraphs if p.text.strip()]
    tx = [p.text for p in ps]
    sub = next(p for p in ps if p.text.startswith("विषय :-\t"))
    assert sub.paragraph_format.left_indent.cm > 4 and sub.paragraph_format.first_line_indent.cm < 0
    from docx.oxml.ns import qn   # §4.44 (उ): label w:bCs + underline, the rest w:b (as in Abhi's letter)
    assert sub.runs[0]._element.rPr.find(qn("w:bCs")) is not None and all(r.bold for r in sub.runs[1:] if r.text.strip())
    assert any(t.startswith("संदर्भ :-\t1)\t") for t in tx) and "2)\tया विभागाचे पत्र दि. 30.03.2026." in tx
    pts = [t for t in tx if t.startswith("(")]
    assert [t.split("\t")[0] for t in pts] == ["(1)", "(2)", "(3)"]          # one sequence through the letter
    p1 = next(p for p in ps if p.text.startswith("(1)\t"))
    assert p1.paragraph_format.left_indent.cm > 2 and p1.paragraph_format.first_line_indent.cm < 0
    assert any(t.startswith("2.\tतसेच, एकत्रित प्रस्ताव") for t in tx)
    # §4.44 (ऊ) (13.11.2026) replaced §4.38 (ई): "प्रत :" once, the file copy first "1.", the other copies "2." …
    assert sum(t.startswith("प्रत ") for t in tx) == 1 and tx[-1].startswith("\t2. प्रमुख जिल्हा")
    assert tx[-2] == "प्रत :\t1. निवड नस्ती"


def test_letter_format_444(tmp_path):
    """INSTRUCTIONS §4.44 (Abhi 13.11.2026, his corrected Word letter of case 6): 4 cm left margin; bold phone / e-mail
    and number / date lines, undated draft ".MM.YYYY"; bold "प्रति,"; "मा." before the addressee; label word underlined;
    "मा.महोदय,"; letter table 8505 wide, indent 250, header centred, columns 709 / 5245 / 2551; two blank lines
    before the name; "प्रत : 1. निवड नस्ती" then "2...."."""
    import json, re, docx, datetime
    from docx.oxml.ns import qn
    sp = json.load(open(os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json"), encoding="utf-8"))
    L = sp["letter"]
    L["date"] = "__.__.2026"
    L["to"] = ["प्रबंधक (निरीक्षण-1),", "उच्च न्यायालय (अपील शाखा),", "मुंबई."]
    L["points"] = [{"table": [["अ.क्र.", "तपशील", "माहिती"], ["1", "मंजूर पदे", ""]]}]
    L.pop("copies", None)
    out = str(tmp_path / "L.docx")
    import mkdocs as M
    M.build_letter(sp, out, L)
    D = docx.Document(out)
    assert D.sections[-1].left_margin.twips == 2268
    ps = [p for p in D.paragraphs if p.text.strip()]
    tx = [p.text for p in ps]
    ph = next(p for p in ps if p.text.startswith("दूरध्वनी"))
    assert all(r.bold for r in ph.runs if r.text.strip())
    kr = next(p for p in ps if p.text.startswith("क्रमांक:-"))
    assert all(r.bold for r in kr.runs if r.text.strip()) and " " * 20 + "दिनांक  :- ." in kr.text
    assert re.search(r"दिनांक  :- \.\d\d\.\d{4}$", kr.text)
    assert next(p for p in ps if p.text == "प्रति,").runs[0].bold
    assert "\tमा.प्रबंधक (निरीक्षण-1)," in tx and "मा.महोदय," in tx
    sub = next(p for p in ps if p.text.startswith("विषय :-\t"))
    assert sub.runs[0].text == "विषय" and sub.runs[0].underline and not sub.runs[1].underline
    # run flags exactly as his file: label w:bCs + w:cs + w:u (no w:b); " :-" and text w:b + w:cs (no w:bCs)
    r0, r1, r2 = sub.runs[:3]
    assert r0.bold is None and r0._element.rPr.find(qn("w:bCs")) is not None and r0._element.rPr.find(qn("w:cs")) is not None
    for r in (r1, r2):
        assert r.bold and r._element.rPr.find(qn("w:bCs")) is None and r._element.rPr.find(qn("w:cs")) is not None
    t = D.tables[0]._tbl
    assert t.tblPr.find(qn("w:tblW")).get(qn("w:w")) == "8505" and t.tblPr.find(qn("w:tblInd")).get(qn("w:w")) == "250"
    assert [g.get(qn("w:w")) for g in t.find(qn("w:tblGrid"))] == ["709", "5245", "2551"]
    assert D.tables[0].rows[0].cells[1].paragraphs[0].alignment == 1
    allp = D.paragraphs
    ia = next(i for i, p in enumerate(allp) if p.text.strip() == "आपला,")
    assert [p.text.strip() for p in allp[ia + 1:ia + 3]] == ["", ""] and allp[ia + 3].text.strip().startswith("(")
    assert tx[-2:] == ["प्रत :\t1. निवड नस्ती", "\t2...."]
    # a full date is printed as given
    L["date"] = "05.12.2026"; M.build_letter(sp, out, L)
    assert any(p.text.endswith("दिनांक  :- 05.12.2026") for p in docx.Document(out).paragraphs)


def test_letter_refs_without_numbers_438(tmp_path):
    """CR50 (06.11.2026): several references written without "1)" markers are still numbered "1)", "2)" … (§4.38 (अ));
    a single unnumbered reference stays "संदर्भ :-\\t<text>"."""
    import json, docx
    import mkdocs as M
    sp = json.load(open(os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json"), encoding="utf-8"))
    for refs, want in ((["या कार्यासनाचे समक्रमांकाचे पत्र दि. 05.12.2024", "आपले पत्र दि. 03.03.2025"],
                        ["संदर्भ :-\t1)\tया कार्यासनाचे समक्रमांकाचे पत्र दि. 05.12.2024", "2)\tआपले पत्र दि. 03.03.2025"]),
                       (["आपले पत्र दि. 03.03.2025"], ["संदर्भ :-\tआपले पत्र दि. 03.03.2025"])):
        L = dict(sp["letter"], refs=refs)
        out = str(tmp_path / f"L{len(refs)}.docx")
        M.build_letter(sp, out, L)
        tx = [p.text for p in docx.Document(out).paragraphs]
        for w in want:
            assert w in tx, (w, tx)


def test_date_column_fits():
    """CR50: a DD.MM.YYYY cell must get a column wide enough not to wrap (digits measured at 0.62 em)."""
    import mkdocs as M
    w = M.col_widths([["अ.क्र.", "तपशील", "दिनांक"], ["1", "सिंधुदुर्ग जिल्हा न्यायालयाच्या आस्थापनेवर कनिष्ठ लिपिक पदावर प्रथम नियुक्ती " * 2, "24.08.2020"]], 15.0)
    assert w[2] >= 2.7, w
