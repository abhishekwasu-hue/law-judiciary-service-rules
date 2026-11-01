"""Regression tests for the output-building tools (stdlib unittest).
Run from the repo root:  py -m unittest tests.test_tools -v   (python3 on Linux)
Tests that need a missing module/binary/file are skipped, not failed."""
import base64, csv, glob, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
TPL = os.path.join(TOOLS, "templates")
FONT = "DVOT-SurekhMR"
GR_PDF = os.path.join(ROOT, "pdf", "gr", "201307101257022705.pdf")  # real GR with a Unicode text layer
GR_QUOTE = "यांना ठोक भरपाई मंजूर करण्याबाबत."
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

try:
    import pymupdf
except ImportError:
    pymupdf = None
try:
    import docx
    from docx.oxml.ns import qn
except ImportError:
    docx = None
try:
    import docxcompose  # noqa: F401
except ImportError:
    docxcompose = None


def run(args, cwd=ROOT):
    return subprocess.run([sys.executable] + args, cwd=cwd, env=ENV, capture_output=True, text=True, encoding="utf-8")


def jdump(obj, path, enc="utf-8"):
    with open(path, "w", encoding=enc) as f:
        json.dump(obj, f, ensure_ascii=False)


def jload(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def bad_font_runs(d):
    bad = 0
    for el in d.element.body.iter(qn("w:r")):
        if not "".join(x.text or "" for x in el.iter(qn("w:t"))).strip():
            continue
        rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
        if f is None or any(f.get(qn("w:" + k)) != FONT for k in ("ascii", "hAnsi", "cs", "eastAsia")):
            bad += 1
    return bad


def page_setup(s):
    return (s.left_margin, s.right_margin, s.top_margin, s.bottom_margin, s.page_width, s.page_height)


class TmpCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


@unittest.skipIf(docx is None or docxcompose is None, "python-docx / docxcompose not installed")
class TestBuildNoteLetter(TmpCase):
    def test_all_sample_specs(self):
        specs = sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "*.json")))
        self.assertGreaterEqual(len(specs), 6)
        note_m = page_setup(docx.Document(os.path.join(TPL, "NOTE_TEMPLATE.docx")).sections[0])
        let_m = page_setup(docx.Document(os.path.join(TPL, "LETTER_TEMPLATE.docx")).sections[0])
        self.assertNotEqual(note_m, let_m)
        for sp in specs:
            with self.subTest(spec=os.path.basename(sp)):
                pre = "T" + os.path.basename(sp).split("_")[0]
                r = run([os.path.join(TOOLS, "build_note_letter.py"), sp, self.tmp, pre])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                d = docx.Document(os.path.join(self.tmp, f"{pre}_Note_and_Letter.docx"))
                self.assertEqual(bad_font_runs(d), 0)
                has_letter = bool(jload(sp).get("letter"))
                text = "\n".join(p.text for p in d.paragraphs)
                if has_letter:
                    self.assertIn("आपला,", text)
                    self.assertIn("प्रत : निवड नस्ती", text)
                    self.assertEqual(len(d.sections), 2)
                    self.assertEqual(page_setup(d.sections[0]), note_m)
                    self.assertEqual(page_setup(d.sections[1]), let_m)
                else:
                    self.assertNotIn("आपला,", text)
                    self.assertEqual(len(d.sections), 1)
                    self.assertEqual(page_setup(d.sections[0]), note_m)

    def test_bom_spec(self):
        sp = sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "*.json")))[0]
        bom = os.path.join(self.tmp, "bom.json")
        with open(bom, "w", encoding="utf-8-sig") as f:
            f.write(read_text(sp).lstrip("﻿"))
        r = run([os.path.join(TOOLS, "build_note_letter.py"), bom, self.tmp, "BOM"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


@unittest.skipIf(pymupdf is None, "pymupdf not installed")
class TestPkg3AndHighlight(TmpCase):
    def make_proposal(self, n=2):
        d = pymupdf.open()
        for i in range(n):
            pg = d.new_page(); pg.insert_text((72, 100), f"Proposal page {i + 1}")
        p = os.path.join(self.tmp, "proposal.pdf"); d.save(p); return p

    def build(self, pages="1"):
        if not os.path.exists(GR_PDF):
            self.skipTest("GR PDF not in checkout")
        prop = self.make_proposal()
        enc = os.path.join(self.tmp, "enc.json")
        jdump([{"path": GR_PDF, "pages": pages, "label": "GR 10.07.2013",
                "marks": [{"page": 1, "text": GR_QUOTE}]}], enc, "utf-8-sig")
        out = os.path.join(self.tmp, "प्रस्ताव मूळ नाव.pdf")
        return run([os.path.join(TOOLS, "pkg3.py"), prop, enc, out]), out

    def test_stamp_bookmarks_map(self):
        r, out = self.build("1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = pymupdf.open(out); n = len(d)
        self.assertEqual(n, 3)
        for i, pg in enumerate(d, 1):
            rect = pg.rect
            strip = pg.get_text("text", clip=pymupdf.Rect(0, rect.height - 24, rect.width, rect.height))
            self.assertIn(f"पृ. {i} / {n}", " ".join(strip.split()), f"page {i}: {strip!r}")
        toc = d.get_toc()
        self.assertEqual([t[2] for t in toc], [1, 3])
        mp = jload(out + ".map.json")
        self.assertEqual(mp["प्रस्ताव"]["pages"], [1, 2])
        self.assertEqual(mp["GR 10.07.2013"], {"first_page": 3, "pages": [3]})
        self.assertEqual(len(mp["marks"]), 1)
        self.assertEqual(mp["marks"][0]["status"], "highlighted")
        self.assertGreaterEqual(mp["marks"][0]["hits"], 1)
        annots = [a.type[1] for pg in d for a in pg.annots()]
        self.assertTrue(annots and set(annots) == {"Highlight"}, annots)
        self.assertEqual([a for pg in d.pages(0, 2) for a in pg.annots()], [])  # nothing on the proposal pages

    def test_bad_page_specs_raise(self):
        sys.path.insert(0, TOOLS)
        try:
            import pkg3
        finally:
            sys.path.remove(TOOLS)
        for spec in ("3-1", "0", "5", "9-10", ","):
            with self.subTest(spec=spec):
                self.assertRaises(ValueError, pkg3.pages_of, spec, 4, "x")
        self.assertEqual(pkg3.pages_of("1-2,4", 4), [1, 2, 4])
        self.assertEqual(pkg3.pages_of(None, 3), [1, 2, 3])
        r, _ = self.build("2-1")
        self.assertNotEqual(r.returncode, 0)

    def test_box_mark_refused(self):
        if not os.path.exists(GR_PDF):
            self.skipTest("GR PDF not in checkout")
        prop = self.make_proposal()
        enc = os.path.join(self.tmp, "enc.json")
        jdump([{"path": GR_PDF, "pages": "1", "marks": [{"page": 1, "box": [10, 10, 50, 50]}]}], enc)
        r = run([os.path.join(TOOLS, "pkg3.py"), prop, enc, os.path.join(self.tmp, "o.pdf")])
        self.assertNotEqual(r.returncode, 0)

    def test_highlight_lines(self):
        r, out = self.build("1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = pymupdf.open(out)
        tops = [l["bbox"][1] for b in d[2].get_text("dict")["blocks"] for l in b.get("lines", [])
                if "".join(s["text"] for s in l["spans"]).strip()]
        before = sum(1 for _ in d[2].annots()); d.close()
        mj = os.path.join(self.tmp, "marks.json")
        jdump([{"page": 3, "mode": "lines", "y0": tops[0] - 1, "y1": tops[0] + 1}], mj, "utf-8-sig")
        r = run([os.path.join(TOOLS, "highlight.py"), out, mj])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = pymupdf.open(out)
        types = [a.type[1] for pg in d for a in pg.annots()]
        self.assertGreater(sum(1 for _ in d[2].annots()), before)
        self.assertEqual(set(types), {"Highlight"})
        d.close()
        # a mark that matches nothing must fail and leave the PDF unchanged
        size = os.path.getsize(out)
        jdump([{"page": 3, "mode": "lines", "y0": -50, "y1": -40}], mj)
        r = run([os.path.join(TOOLS, "highlight.py"), out, mj])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(os.path.getsize(out), size)


@unittest.skipIf(docx is None, "python-docx not installed")
class TestBuildStudy(TmpCase):
    def test_fonts(self):
        spec = {"title": "C R 1/2026 — अभ्यास-फाइल", "parts": [
            {"heading": "भाग 0 — वरिष्ठांसाठी ब्रीफिंग", "blocks": [
                {"bullets": ["प्रस्ताव : चाचणी", "Mixed English 123"]},
                {"table": [["तपशील", "माहिती"], ["दिनांक", "01.01.2026"]]},
                {"subheading": "(ई) अटी"}, {"para": "परिच्छेद"}]},
            {"heading": "भाग 1 — मराठी रूपांतर", "blocks": [{"para": "पान 1"}]}]}
        sj = os.path.join(self.tmp, "study.json"); out = os.path.join(self.tmp, "X_Study.docx")
        with open(sj, "w", encoding="utf-8-sig") as f:
            json.dump(spec, f, ensure_ascii=False)
        r = run([os.path.join(TOOLS, "build_study.py"), sj, out])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = docx.Document(out)
        self.assertEqual(bad_font_runs(d), 0)
        self.assertIn("भाग 0 — वरिष्ठांसाठी ब्रीफिंग", "\n".join(p.text for p in d.paragraphs))


class TestDeskChunks(TmpCase):
    def test_round_trip(self):
        src = os.path.join(self.tmp, "C_Study.docx")
        data = os.urandom(400_000)
        with open(src, "wb") as f:
            f.write(data)
        od = os.path.join(self.tmp, "chunks")
        r = run([os.path.join(TOOLS, "desk_chunks.py"), src, "CR1", "study", od])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertEqual(rec, {"kind": "study", "name": "C_Study.docx", "store": "db", "ref": "CR1__study"})
        docs = [jload(p) for p in glob.glob(os.path.join(od, "CR1__study__*.json"))]
        docs.sort(key=lambda x: x["n"])
        self.assertGreater(len(docs), 1)
        self.assertTrue(all(x["total"] == len(docs) and len(x["b64"]) < 200 * 1024 for x in docs))
        self.assertEqual(base64.b64decode("".join(x["b64"] for x in docs)), data)


class TestAppSeedGr(TmpCase):
    def test_seed(self):
        tsv = os.path.join(self.tmp, "INDEX.tsv"); out = os.path.join(self.tmp, "seed.sql")
        rows = [["code", "date", "department", "title", "request"],
                ["201909111812520805", "2019-09-11", "Finance Department", "ठोक भरपाई (O'Brien)", "C R 66/2026"],
                ["20051126114919001", "", "Law", "¸üÖ•µÖ ¿ÖÖÃÖ−ÖÖ“µÖÖ", ""],
                ["SC_2024_x", "2024-01-02", "Supreme Court", "Order", ""]]
        with open(tsv, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t").writerows(rows)
        r = run([os.path.join(TOOLS, "app_seed_gr.py"), tsv, out])
        self.assertEqual(r.returncode, 0, r.stderr)
        sql = read_text(out).splitlines()[1:]
        self.assertEqual(len(sql), 3)
        self.assertIn("'ठोक भरपाई (O''Brien)'", sql[0])
        self.assertIn("Marathi/201909111812520805.pdf", sql[0])
        self.assertIn("'2005-11-26'", sql[1])           # date from the code
        self.assertIn("'Law', null,", sql[1])           # legacy-font garbage title dropped
        self.assertIn("'gr-library/SC_2024_x.pdf', null)", sql[2])  # no GR-site URL for court orders


@unittest.skipIf(docx is None, "python-docx not installed")
class TestOldCasesText(TmpCase):
    def test_zip_with_docx(self):
        d = docx.Document(); d.add_paragraph("वेतननिश्चिती टिप्पणी")
        t = d.add_table(rows=1, cols=2); t.cell(0, 0).text = "अ"; t.cell(0, 1).text = "ब"
        dp = os.path.join(self.tmp, "n.docx"); d.save(dp)
        with zipfile.ZipFile(os.path.join(self.tmp, "सन 2024 प्रकरणे.zip"), "w") as z:
            z.write(dp, "C R 1-2024/टिप्पणी.docx")
            z.writestr("C R 1-2024/~$lock.docx", b"x")
            z.writestr("C R 1-2024/a.pdf", b"x")
        r = run([os.path.join(TOOLS, "oldcases_text.py"), "out"], cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "1 files")
        idx = read_text(os.path.join(self.tmp, "out", "index.tsv")).split("\t")
        self.assertEqual(idx[1:], ["सन 2024 प्रकरणे.zip", "C R 1-2024/टिप्पणी.docx"])
        txt = read_text(os.path.join(self.tmp, "out", "t", "001.txt"))
        self.assertIn("वेतननिश्चिती टिप्पणी", txt)
        self.assertIn("अ | ब", txt)


if __name__ == "__main__":
    unittest.main()
