"""Tests for tools/clean_meta.py (contract C27 §4, 02.11.2026: no tool / AI trace in the metadata of the delivered
files) and its use by the builders. Run: python3 -m pytest -q tests/test_clean_meta.py"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import clean_meta as CM  # noqa: E402

try:
    import docx
except ImportError:  # pragma: no cover
    docx = None
try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
ENV.pop("LINT_SKIP", None)


@unittest.skipIf(docx is None, "python-docx not installed")
class DocxMeta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_python_docx_default_is_flagged_then_cleaned(self):
        p = os.path.join(self.tmp, "a.docx")
        d = docx.Document(); d.add_paragraph("x")
        d.core_properties.author = "Claude"; d.core_properties.title = "AI draft"; d.core_properties.comments = "generated"
        d.save(p)
        probs = CM.docx_meta_problems(p)
        self.assertTrue(any("dc:creator" in x and "Claude" in x for x in probs), probs)
        self.assertTrue(any("dc:title" in x for x in probs), probs)
        self.assertTrue(any("Application" in x for x in probs), probs)
        CM.clean_docx(p)
        self.assertEqual(CM.docx_meta_problems(p), [])
        cp = docx.Document(p).core_properties
        self.assertEqual((cp.author, cp.title, cp.comments, cp.last_modified_by), ("", "", "", ""))
        self.assertEqual(docx.Document(p).paragraphs[0].text, "x")   # content kept

    def test_office_like_properties(self):
        """lead's decision (AI_TELLS §9): author from doc_author / DOC_AUTHOR, created = modified, revision 1, no
        lastPrinted, Application "Microsoft Office Word", no stale statistics."""
        import zipfile
        tpl = os.path.join(TOOLS, "templates", "NOTE_TEMPLATE.docx")
        p = os.path.join(self.tmp, "n.docx")
        import shutil
        shutil.copy(tpl, p)
        probs = CM.docx_meta_problems(p)
        for k in ("lastPrinted", "created != modified", "revision", "stale statistics"):
            self.assertTrue(any(k in x for x in probs), (k, probs))
        CM.clean_docx(p, "श्रीम. कऱ्हाडे")
        self.assertEqual(CM.docx_meta_problems(p), [])
        cp = docx.Document(p).core_properties
        self.assertEqual((cp.author, cp.last_modified_by, cp.revision), ("श्रीम. कऱ्हाडे", "श्रीम. कऱ्हाडे", 1))
        self.assertEqual(cp.created, cp.modified)
        self.assertIsNone(cp.last_printed)
        with zipfile.ZipFile(p) as z:
            app = z.read("docProps/app.xml").decode()
        self.assertIn("<Application>Microsoft Office Word</Application>", app)
        self.assertIn("<TotalTime>0</TotalTime>", app)
        self.assertNotIn("<Words>", app); self.assertNotIn("<CharactersWithSpaces>", app)
        # env DOC_AUTHOR; a tool / AI name is never written
        old = os.environ.get("DOC_AUTHOR")
        try:
            os.environ["DOC_AUTHOR"] = "कार्यासन-6"
            CM.clean_docx(p); self.assertEqual(docx.Document(p).core_properties.author, "कार्यासन-6")
            CM.clean_docx(p, "Claude"); self.assertEqual(docx.Document(p).core_properties.author, "कार्यासन-6")
            os.environ["DOC_AUTHOR"] = "python-docx"
            CM.clean_docx(p); self.assertEqual(docx.Document(p).core_properties.author, "")
        finally:
            if old is None: os.environ.pop("DOC_AUTHOR", None)
            else: os.environ["DOC_AUTHOR"] = old
        self.assertEqual(CM.docx_meta_problems(p), [])

    def test_app_application_python_docx_flagged(self):
        import zipfile
        p = os.path.join(self.tmp, "b.docx"); q = os.path.join(self.tmp, "c.docx")
        docx.Document().save(p)
        with zipfile.ZipFile(p) as zi, zipfile.ZipFile(q, "w") as zo:
            for it in zi.infolist():
                data = zi.read(it.filename)
                if it.filename == "docProps/app.xml":
                    data = data.decode().replace("</Properties>", "<Application>python-docx</Application></Properties>").encode()
                zo.writestr(it, data)
        self.assertTrue(any("python-docx" in x for x in CM.docx_meta_problems(q)))
        CM.clean_docx(q)
        self.assertFalse(any("Application" in x for x in CM.docx_meta_problems(q)))

    def test_tracked_changes_and_comments_flagged(self):
        import zipfile
        p = os.path.join(self.tmp, "d.docx"); q = os.path.join(self.tmp, "e.docx")
        docx.Document().save(p); CM.clean_docx(p)
        with zipfile.ZipFile(p) as zi, zipfile.ZipFile(q, "w") as zo:
            for it in zi.infolist():
                data = zi.read(it.filename)
                if it.filename == "word/document.xml":
                    data = data.decode().replace("<w:body>", '<w:body><w:p><w:ins w:id="1" w:author="x"/></w:p>').encode()
                zo.writestr(it, data)
            zo.writestr("word/comments.xml", '<w:comments xmlns:w="w"><w:comment w:id="0"/></w:comments>')
        probs = CM.docx_meta_problems(q)
        self.assertTrue(any("tracked changes" in x for x in probs), probs)
        self.assertTrue(any("comments" in x for x in probs), probs)

    def test_builders_leave_no_trace(self):
        """build_note_letter (mkdocs + docxcompose) and build_study: core/app properties blank."""
        spec = sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "CR122_*.json")))[0]
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "build_note_letter.py"), spec, self.tmp, "M"],
                           capture_output=True, text=True, encoding="utf-8", env=ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(CM.docx_meta_problems(os.path.join(self.tmp, "M_Note_and_Letter.docx")), [])
        st = os.path.join(self.tmp, "study.json")
        with open(st, "w", encoding="utf-8") as f:
            json.dump({"title": "C R 1/2026", "parts": [{"heading": f"भाग {i} — शीर्षक", "blocks": [{"para": "मजकूर"}]}
                                                       for i in range(8)]}, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "M_Study.docx")
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "build_study.py"), st, out],
                           capture_output=True, text=True, encoding="utf-8", env=ENV)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(CM.docx_meta_problems(out), [])


@unittest.skipIf(pymupdf is None, "pymupdf not installed")
class PdfMeta(unittest.TestCase):
    def test_flagged_then_cleaned(self):
        d = pymupdf.open(); pg = d.new_page(); pg.insert_text((72, 100), "Some quoted line")
        d.set_metadata({"producer": "PyMuPDF", "author": "Claude", "title": "AI package"})
        a = pg.add_highlight_annot(pg.search_for("quoted")); a.set_info(title="Claude", content="AI note"); a.update()
        probs = CM.pdf_meta_problems(d)
        for k in ("producer", "author", "title", "annotation title", "annotation content"):
            self.assertTrue(any(k in x for x in probs), (k, probs))
        CM.clean_pdf(d)
        p = os.path.join(tempfile.mkdtemp(), "x.pdf"); d.save(p); d.close()
        d = pymupdf.open(p)
        self.assertEqual(CM.pdf_meta_problems(d), [])
        self.assertEqual([a.type[1] for a in d[0].annots()], ["Highlight"])   # the highlight itself stays


if __name__ == "__main__":
    unittest.main()
