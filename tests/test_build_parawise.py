"""Tests for tools/build_parawise.py and tools/lint_parawise.py (court-case parawise remarks).
Run: python3 -m pytest -q tests/test_build_parawise.py   (Windows: py -m pytest -q tests/test_build_parawise.py)"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import lint_parawise as LP  # noqa: E402
import lint_spec  # noqa: E402

try:
    import docx
    from docx.oxml.ns import qn
except ImportError:  # pragma: no cover
    docx = None

WP = os.path.join(ROOT, "samples", "specs", "COURT_wp_parawise_example.json")
INFO = os.path.join(ROOT, "samples", "specs", "COURT_info_needed_example.json")
FONT = "DVOT-SurekhMR"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
ENV.pop("LINT_SKIP", None)


def load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def run(args):
    return subprocess.run([sys.executable] + args, env=ENV, capture_output=True, text=True, encoding="utf-8")


class TestLintParawise(unittest.TestCase):
    def setUp(self):
        self.spec = load(WP)

    def test_sample_clean(self):
        self.assertEqual(LP.lint_parawise(self.spec), [])
        self.assertEqual(LP.warnings_parawise(self.spec), [])

    def test_samples_pass_lint_spec(self):
        for p in (WP, INFO):
            with self.subTest(spec=os.path.basename(p)):
                self.assertEqual(lint_spec.lint_spec(load(p)), [])

    def test_info_sample_has_no_parawise(self):
        s = load(INFO)
        self.assertNotIn("parawise", s)
        self.assertIn("letter", s)
        self.assertEqual(LP.lint_parawise(s), [])

    def test_cryptic_remarks_rejected(self):
        for w in ("Denied.", "not admitted", "Admitted", "No comments.", "DENIED AND NOT ADMITTED", "Noted",
                  "The contents of this para are denied.", "Matter of record."):
            with self.subTest(remarks=w):
                s = copy.deepcopy(self.spec); s["parawise"]["paras"][1]["remarks"] = w
                P = LP.lint_parawise(s)
                self.assertTrue(any("paras[1].remarks: cryptic" in p for p in P), P)

    def test_elaborate_denial_accepted(self):
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"][1]["remarks"] = ("Denied. As per paragraph 3 of Government Resolution No. ____ dated "
                                                "__.__.____ the qualifying service is ____ years.")
        self.assertEqual(LP.lint_parawise(s), [])

    def test_empty_remarks_and_required_fields(self):
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"][0]["remarks"] = ""
        del s["parawise"]["court"]; s["parawise"]["respondents"] = []
        P = LP.lint_parawise(s)
        self.assertTrue(any(p.startswith("parawise.paras[0].remarks: required") for p in P), P)
        self.assertTrue(any(p.startswith("parawise.court:") for p in P), P)
        self.assertTrue(any(p.startswith("parawise.respondents:") for p in P), P)

    def test_recommendation(self):
        for v in ("", "maybe", None):
            with self.subTest(rec=v):
                s = copy.deepcopy(self.spec); s["parawise"]["recommendation"] = v
                self.assertTrue(any(p.startswith("parawise.recommendation:") for p in LP.lint_parawise(s)))
        s = copy.deepcopy(self.spec); s["parawise"]["recommendation"] = "not oppose"
        self.assertEqual(LP.lint_parawise(s), [])
        s["parawise"]["recommendation_reason"] = " "
        self.assertTrue(any(p.startswith("parawise.recommendation_reason:") for p in LP.lint_parawise(s)))

    def test_recommendation_blank_is_warning(self):
        """lead F1 (02.11.2026): "____" when the record gives no basis — WARN, not an error (Rule 58(4)(a))."""
        for v in ("____", " ________ "):
            s = copy.deepcopy(self.spec); s["parawise"]["recommendation"] = v; s["parawise"]["recommendation_reason"] = ""
            self.assertEqual(LP.lint_parawise(s), [], v)
            self.assertTrue(any(w.startswith("parawise.recommendation:") for w in LP.warnings_parawise(s)))
        s = copy.deepcopy(self.spec); s["parawise"]["recommendation"] = "_"
        self.assertTrue(any(p.startswith("parawise.recommendation:") for p in LP.lint_parawise(s)))
        s = copy.deepcopy(self.spec); s["parawise"]["recommendation"] = "oppose"
        self.assertFalse(any(w.startswith("parawise.recommendation:") for w in LP.warnings_parawise(s)))

    def test_ids_and_repo_paths(self):
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"][2]["remarks"] += " See z6_0235 and register/pay.md."
        P = LP.lint_parawise(s)
        self.assertTrue(any("internal id" in p for p in P), P)
        self.assertTrue(any("repo path" in p for p in P), P)

    def test_devanagari_warning(self):
        s = copy.deepcopy(self.spec)
        s["parawise"]["background"].append("याचिकाकर्ता ____ आहे.")
        s["parawise"]["paras"][0]["remarks"] += " Designation “वरिष्ठ लिपिक” as in the order."
        W = LP.warnings_parawise(s)
        self.assertEqual(len([w for w in W if "Devanagari" in w]), 1, W)
        self.assertEqual(LP.lint_parawise(s), [])   # warning only

    def test_draft_words(self):
        """C27 (02.11.2026): no "package PDF" / "पॅकेज" / "warning" / "TODO" / AI word in the parawise draft."""
        for w in ("package PDF", "पॅकेज", "warning", "TODO", "AI", "Claude", "model", "engine", "automatic", "generated"):
            with self.subTest(word=w):
                s = copy.deepcopy(self.spec); s["parawise"]["paras"][0]["remarks"] += f" See {w} p. 3."
                self.assertTrue(any("draft word" in p for p in LP.lint_parawise(s)), w)
        s = copy.deepcopy(self.spec); s["parawise"]["paras"][0]["remarks"] += " The order reads “warning issued”."
        self.assertEqual(LP.lint_parawise(s), [])   # inside quotes: verbatim

    def test_verification_type(self):
        s = copy.deepcopy(self.spec); s["parawise"]["verification"] = "yes"
        self.assertTrue(any("verification" in p for p in LP.lint_parawise(s)))

    def test_contempt_prone_warning_only(self):
        # §4.30 (03.11.2026): respectful language toward the Court — WARN, never an error; own text only
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"][1]["remarks"] = ("The learned Tribunal failed to consider paragraph ____ of Government "
                                                "Resolution No. ____ and passed an erroneous judgment; it is an illegal "
                                                "order and the Court must set it aside.")
        s["parawise"]["recommendation_reason"] = "The order is perverse."
        self.assertEqual(LP.lint_parawise(s), [])
        W = [w for w in LP.warnings_parawise(s) if "contempt-prone" in w]
        for phrase in ("erroneous judgment", "learned Tribunal failed", "illegal order", "Court must", "perverse"):
            self.assertTrue(any(f"'{phrase}'" in w for w in W), (phrase, W))
        # the petitioner's averment / relief and quoted text are not the Department's wording
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"][1]["averment"] = "The Tribunal failed to consider; the illegal order be quashed."
        s["parawise"]["relief_sought"] = "Quash the illegal order dated __.__.____."
        s["parawise"]["paras"][2]["remarks"] += " The petitioner alleges “the court failed to consider”."
        self.assertEqual([w for w in LP.warnings_parawise(s) if "contempt-prone" in w], [])

    def test_relief_and_table_structure(self):
        # §4.30: optional relief_sought (string) and background table items (2-6 columns, plain-text rows)
        s = copy.deepcopy(self.spec)
        s["parawise"]["relief_sought"] = "A direction to grant the ____ benefit with arrears."
        s["parawise"]["background"].append({"title": "Chronology", "table": [["Date", "Event"], ["__.__.2025", "x"]]})
        self.assertEqual(LP.lint_parawise(s), [])
        for bad in ({"table": [["Date"]]}, {"table": [["A", "B"], ["only one"]]}, {"rows": []}, 5,
                    {"table": [["A", "B"], ["x", 3]]}):
            with self.subTest(item=bad):
                t = copy.deepcopy(self.spec); t["parawise"]["background"].append(bad)
                self.assertTrue(any(p.startswith("parawise.background[4]: structure") for p in LP.lint_parawise(t)))
        t = copy.deepcopy(self.spec); t["parawise"]["relief_sought"] = ["x"]
        self.assertTrue(any(p.startswith("parawise.relief_sought:") for p in LP.lint_parawise(t)))

    def test_cli(self):
        r = run([os.path.join(TOOLS, "lint_parawise.py"), WP])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("LINT OK", r.stdout)
        r = run([os.path.join(TOOLS, "lint_parawise.py"), INFO])
        self.assertEqual(r.returncode, 1)


def all_text(d):
    out = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            out += [c.text for c in row.cells]
    return "\n".join(out)


def bad_fonts(d):
    roots = [d.element.body] + [part._element for s in d.sections for part in (s.header, s.footer)]
    bad = 0
    for root in roots:
        for el in root.iter(qn("w:r")):
            if not "".join(x.text or "" for x in el.iter(qn("w:t"))).strip():
                continue
            rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
            if f is None or any(f.get(qn("w:" + k)) != FONT for k in ("ascii", "hAnsi", "cs", "eastAsia")):
                bad += 1
    return bad


@unittest.skipIf(docx is None, "python-docx not installed")
class TestBuildParawise(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, spec_path, pre="T", extra=()):
        return run([os.path.join(TOOLS, "build_parawise.py"), spec_path, self.tmp, pre, *extra])

    def test_build_sample(self):
        r = self.build(WP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = os.path.join(self.tmp, "T_Parawise.docx")
        self.assertIn(out, r.stdout)
        d = docx.Document(out)
        pw = load(WP)["parawise"]
        text = all_text(d)
        for s in (pw["court"], pw["case"], "Versus", "… Petitioner(s)", "… Respondent(s)",
                  "PARAWISE REMARKS OF RESPONDENT NO. 2 (Law and Judiciary Department)",
                  "1. Brief facts", "2. Parawise remarks", "3. Documents enclosed", "4. Recommendation",
                  "The Department recommends that the petition be opposed", pw["recommendation_reason"],
                  "( ____ )", "Under Secretary to Government,", "Law and Judiciary Department,", "Mantralaya, Mumbai."):
            self.assertIn(s, text)
        self.assertNotIn("Verification", text)
        for e in pw["enclosures"]:
            self.assertIn(e, text)
        self.assertEqual(len(d.tables), 1)
        t = d.tables[0]
        self.assertEqual([c.text for c in t.rows[0].cells],
                         ["Para No.", "Averments in the petition (in brief)", "Remarks of the Department"])
        self.assertEqual(len(t.rows), 1 + len(pw["paras"]))
        for i, it in enumerate(pw["paras"], 1):
            self.assertEqual([c.text for c in t.rows[i].cells], [it["para"], it["averment"], it["remarks"]])
        self.assertTrue(all(r.bold for c in t.rows[0].cells for p in c.paragraphs for r in p.runs))
        self.assertEqual(bad_fonts(d), 0)
        sys.path.insert(0, TOOLS)
        import clean_meta
        self.assertEqual(clean_meta.docx_meta_problems(out), [])   # C27 §4: no python-docx / AI trace
        rf = d.styles["Normal"].element.rPr.rFonts
        self.assertEqual({rf.get(qn("w:" + k)) for k in ("ascii", "hAnsi", "cs", "eastAsia")}, {FONT})

    def test_build_relief_and_facts_table(self):
        # §4.30 (03.11.2026): "Relief sought:" line after "Submitted to", a chronology table inside Brief facts;
        # string facts keep their (1), (2) … numbering; the remarks table stays the last table
        s = load(WP)
        s["parawise"]["relief_sought"] = "A direction to grant the ____ benefit with effect from __.__.____."
        s["parawise"]["background"].insert(2, {"title": "Chronology", "table": [
            ["Date", "Event"], ["__.__.2025", "Representation"], ["__.__.2025", "Forwarded by the High Court"]]})
        sp = os.path.join(self.tmp, "spec.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        r = self.build(sp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = docx.Document(os.path.join(self.tmp, "T_Parawise.docx"))
        paras = [p.text for p in d.paragraphs]
        i_sub = next(i for i, t in enumerate(paras) if t.startswith("Submitted to:"))
        self.assertEqual(paras[i_sub + 1], "Relief sought:\t" + s["parawise"]["relief_sought"])
        self.assertIn("Chronology", paras)
        self.assertTrue(any(t.startswith("(3)\tThe Law and Judiciary Department informed") for t in paras), paras)
        self.assertEqual(len(d.tables), 2)
        self.assertEqual([c.text for c in d.tables[0].rows[0].cells], ["Date", "Event"])
        self.assertEqual(d.tables[1].rows[0].cells[0].text, "Para No.")
        self.assertEqual(bad_fonts(d), 0)

    def test_sample_has_no_relief_line(self):
        r = self.build(WP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = docx.Document(os.path.join(self.tmp, "T_Parawise.docx"))
        self.assertFalse(any(p.text.startswith("Relief sought") for p in d.paragraphs))
        if shutil.which("soffice"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "T_Parawise.pdf")), r.stderr)

    def test_not_oppose_and_verification(self):
        s = load(WP); s["parawise"]["recommendation"] = "not oppose"; s["parawise"]["verification"] = True
        s["parawise"]["enclosures"] = []
        p = os.path.join(self.tmp, "s.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        r = self.build(p, "V")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARN parawise.enclosures", r.stdout)
        text = all_text(docx.Document(os.path.join(self.tmp, "V_Parawise.docx")))
        self.assertIn("recommends that the petition be not opposed", text)
        self.assertIn("Verification", text)
        self.assertIn("Nil.", text)

    def test_blank_recommendation_builds(self):
        # lint allows recommendation "____" (warning): the build prints "____" for the owner to fill (no KeyError)
        s = load(WP); s["parawise"]["recommendation"] = "____"
        p = os.path.join(self.tmp, "b.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        r = self.build(p, "B")
        self.assertNotIn("KeyError", r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "B_Parawise.docx")), r.stdout + r.stderr)
        self.assertIn("____", all_text(docx.Document(os.path.join(self.tmp, "B_Parawise.docx"))))

    def test_refuses_without_parawise(self):
        r = self.build(INFO, "N")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no 'parawise' block", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "N_Parawise.docx")))

    def test_refuses_on_lint_errors(self):
        s = load(WP); s["parawise"]["paras"][0]["remarks"] = "Denied."
        p = os.path.join(self.tmp, "bad.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        r = self.build(p, "B")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cryptic", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "B_Parawise.docx")))
        r = self.build(p, "B", ("--no-lint",))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "B_Parawise.docx")))

    def test_court_samples_build_note_letter(self):
        for p, pre in ((WP, "W"), (INFO, "I")):
            with self.subTest(spec=os.path.basename(p)):
                r = run([os.path.join(TOOLS, "build_note_letter.py"), p, self.tmp, pre])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                d = docx.Document(os.path.join(self.tmp, f"{pre}_Note_and_Letter.docx"))
                text = "\n".join(x.text for x in d.paragraphs)
                self.assertIn("आपला,", text)
                self.assertIn("प्रत : निवड नस्ती", text)
                self.assertEqual(len(d.sections), 2)


if __name__ == "__main__":
    unittest.main()
