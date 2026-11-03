"""Tests for tools/build_parawise.py and tools/lint_parawise.py (court-case parawise remarks).
Default layout = the Section's office format (Abhi, 03.11.2026; the sample spec); "layout": "rule58" = the earlier
layout (fixture RULE58 below = the former sample block).
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


# the former sample block, kept as the "layout": "rule58" fixture
RULE58 = {'layout': 'rule58',
 'court': 'IN THE HIGH COURT OF JUDICATURE AT BOMBAY, BENCH AT AURANGABAD',
 'case': 'WRIT PETITION NO. ____ OF 2026',
 'petitioner': 'Shri A. B. Chachani (synthetic test petitioner), ____, District and Sessions Court, ____',
 'respondents': ['The State of Maharashtra, through the Secretary, ____ Department, Mantralaya, Mumbai',
                 'The Principal Secretary and Legal Remembrancer, Law and Judiciary Department, Mantralaya, Mumbai',
                 'The Registrar General, High Court of Judicature at Bombay'],
 'respondent_no': '2',
 'department': 'Law and Judiciary Department',
 'subject': 'Parawise remarks of Respondent No. 2 on the Writ Petition seeking grant of the ____ benefit to the '
            'petitioner with effect from __.__.____.',
 'prepared_for': 'Assistant Government Pleader, High Court of Judicature at Bombay, Bench at Aurangabad',
 'background': ['The petitioner is working as ____ in the District and Sessions Court, ____. He submitted a '
                'representation dated __.__.2025 seeking the ____ benefit with effect from __.__.____.',
                'The representation was forwarded to the Government by the High Court under its letter dated '
                '__.__.2025.',
                'The Law and Judiciary Department informed the High Court under letter No. ____ dated __.__.2025 '
                'that the petitioner does not fulfil the condition of ____ laid down in Government Resolution No. '
                '____ dated __.__.____ (copy at Document No. 1).',
                'Aggrieved thereby, the petitioner has filed the present Writ Petition. The Law and Judiciary '
                'Department is Respondent No. 2.'],
 'paras': [{'para': '1 to 3',
            'averment': "Description of the parties, the petitioner's appointment as ____ on __.__.____ and his "
                        'service particulars.',
            'remarks': "The particulars of the petitioner's appointment and service are a matter of the official "
                       'record of the District and Sessions Court, ____. As per that record, the petitioner was '
                       'appointed as ____ by order dated __.__.____ and joined on __.__.____. The remaining '
                       'averments are not within the knowledge of this Respondent and the petitioner may be put to '
                       'strict proof thereof.'},
           {'para': '4',
            'averment': 'The petitioner claims that he completed the qualifying service of ____ years on __.__.____ '
                        'and became eligible for the ____ benefit.',
            'remarks': 'Government Resolution No. ____ dated __.__.____ (copy at Document No. 1), paragraph ____, '
                       'prescribes ____ years of regular service and the condition of ____ for the grant of the ____ '
                       'benefit. As per the service record received from the High Court with its letter dated '
                       "__.__.2025, the petitioner's regular service is counted from __.__.____; the period from "
                       '__.__.____ to __.__.____ was on an ad hoc basis and is not counted as regular service under '
                       'paragraph ____ of the said Government Resolution. Hence the claim that he completed the '
                       'qualifying service on __.__.____ is not correct.'},
           {'para': '5 and 6',
            'averment': 'The petitioner states that his representation dated __.__.2025 was not considered and that '
                        'similarly placed employees were granted the benefit.',
            'remarks': 'The representation dated __.__.2025 was received through the High Court and was considered. '
                       'The Department communicated its decision to the High Court under letter No. ____ dated '
                       '__.__.2025 (copy at Document No. 2), stating the reason for rejection with reference to '
                       'paragraph ____ of Government Resolution No. ____ dated __.__.____. The petitioner has not '
                       'named the employees said to be similarly placed; the benefit is granted only to employees '
                       'who fulfil the conditions of the said Government Resolution.'},
           {'para': '7 (Grounds A to D)',
            'averment': 'Grounds: the rejection is arbitrary and violates Articles 14 and 16 of the Constitution of '
                        'India.',
            'remarks': 'The decision was taken by applying the uniform conditions laid down in Government Resolution '
                       'No. ____ dated __.__.____, which apply equally to all employees of the cadre. No '
                       'discrimination has been made against the petitioner. The Government Resolution itself has '
                       'not been challenged in the petition.'},
           {'para': '8 (Prayer)',
            'averment': 'The petitioner prays for a direction to grant the ____ benefit with effect from __.__.____ '
                        'with arrears.',
            'remarks': 'In view of the remarks on paragraphs 4 to 7 above, the petitioner is not entitled to the '
                       'benefit from the date claimed. The prayer is not maintainable and deserves to be rejected.'}],
 'enclosures': ['Copy of Government Resolution No. ____ dated __.__.____ (conditions for the grant of the ____ '
                'benefit).',
                "Copy of the Law and Judiciary Department's letter No. ____ dated __.__.2025 to the High Court.",
                'Copy of the service particulars of the petitioner received from the High Court with its letter '
                'dated __.__.2025.'],
 'recommendation': 'oppose',
 'recommendation_reason': 'The petitioner does not fulfil the condition of ____ years of regular service prescribed '
                          'in paragraph ____ of Government Resolution No. ____ dated __.__.____ on the date claimed, '
                          'and the decision was communicated with reasons under letter dated __.__.2025.',
 'officer': '( ____ )',
 'place': 'Mumbai',
 'date': '__.__.2026',
 'verification': False}


def rule58_spec():
    s = load(WP); s["parawise"] = copy.deepcopy(RULE58)
    return s


def write(spec, d, name):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return p


def run(args):
    return subprocess.run([sys.executable] + args, env=ENV, capture_output=True, text=True, encoding="utf-8")


class TestLintOffice(unittest.TestCase):
    """Default layout: the Section's office format (Sr. No. | Para No. | Remarks)."""
    def setUp(self):
        self.spec = load(WP)

    def test_sample_is_office_and_clean(self):
        pw = self.spec["parawise"]
        self.assertNotIn("layout", pw)
        self.assertEqual(LP.layout(pw), "office")
        self.assertEqual(LP.lint_parawise(self.spec), [])
        self.assertEqual(LP.warnings_parawise(self.spec), [])
        self.assertTrue(any(it.get("section") == "Grounds" for it in pw["paras"]))

    def test_required_fields(self):
        for k in ("case", "petitioner", "on_behalf_of"):
            with self.subTest(key=k):
                s = copy.deepcopy(self.spec); del s["parawise"][k]
                self.assertTrue(any(p.startswith(f"parawise.{k}:") for p in LP.lint_parawise(s)))
        s = copy.deepcopy(self.spec); del s["parawise"]["on_behalf_of"]
        s["parawise"]["intro"] = "Parawise submissions on behalf of Respondent No. 2, in this petition."
        self.assertEqual(LP.lint_parawise(s), [])   # "intro" replaces the whole sentence
        s = copy.deepcopy(self.spec); s["parawise"]["paras"] = []
        self.assertTrue(any(p.startswith("parawise.paras:") for p in LP.lint_parawise(s)))

    def test_averment_optional(self):
        s = copy.deepcopy(self.spec)
        for it in s["parawise"]["paras"]:
            it.pop("averment", None)
        self.assertEqual(LP.lint_parawise(s), [])
        s["parawise"]["paras"][0]["remarks"] = ""
        self.assertTrue(any(p.startswith("parawise.paras[0].remarks: required") for p in LP.lint_parawise(s)))

    def test_section_row_structure(self):
        for bad in ({"section": ""}, {"section": "Grounds", "remarks": "x"}):
            with self.subTest(item=bad):
                s = copy.deepcopy(self.spec); s["parawise"]["paras"].insert(1, bad)
                self.assertTrue(any(p.startswith("parawise.paras[1]: structure") for p in LP.lint_parawise(s)))

    def test_cryptic_and_words(self):
        s = copy.deepcopy(self.spec); s["parawise"]["paras"][0]["remarks"] = "Denied."
        self.assertTrue(any("paras[0].remarks: cryptic" in p for p in LP.lint_parawise(s)))
        s = copy.deepcopy(self.spec); s["parawise"]["paras"][0]["remarks"] += " See z6_0235, register/pay.md, TODO."
        P = LP.lint_parawise(s)
        for w in ("internal id", "repo path", "draft word"):
            self.assertTrue(any(w in p for p in P), (w, P))

    def test_no_prayer_row_warns(self):
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"] = [it for it in s["parawise"]["paras"] if "Prayer" not in it.get("para", "")]
        self.assertEqual(LP.lint_parawise(s), [])
        self.assertTrue(any("no 'Prayer' row" in w for w in LP.warnings_parawise(s)))

    def test_rule58_keys_warn_and_layout_value(self):
        s = copy.deepcopy(self.spec); s["parawise"]["recommendation"] = "oppose"; s["parawise"]["enclosures"] = ["x"]
        self.assertEqual(LP.lint_parawise(s), [])
        self.assertTrue(any("belong to \"layout\": \"rule58\"" in w for w in LP.warnings_parawise(s)))
        s = copy.deepcopy(self.spec); s["parawise"]["layout"] = "fancy"
        self.assertTrue(any(p.startswith("parawise.layout:") for p in LP.lint_parawise(s)))
        s["parawise"]["layout"] = "office"
        self.assertEqual(LP.lint_parawise(s), [])

    def test_labels_and_contempt(self):
        s = copy.deepcopy(self.spec)
        for lab in ("Para No.3", "21 to 24", "5 (a) to (e)", "Ground (k)", "Prayer Clauses (a) to (h)"):
            s["parawise"]["paras"][0]["para"] = lab
            self.assertFalse(any("para label" in w for w in LP.warnings_parawise(s)), lab)
        s["parawise"]["paras"][0]["para"] = "first para"
        self.assertTrue(any("para label" in w for w in LP.warnings_parawise(s)))
        s = copy.deepcopy(self.spec)
        s["parawise"]["paras"][2]["remarks"] += " The learned Tribunal failed to consider the record."
        s["parawise"]["paras"][3]["averment"] = "The Court failed to consider; the illegal order be quashed."
        W = [w for w in LP.warnings_parawise(s) if "contempt-prone" in w]
        self.assertEqual(len(W), 1, W); self.assertIn("paras[2].remarks", W[0])
        self.assertEqual(LP.lint_parawise(s), [])


class TestLintParawise(unittest.TestCase):
    """"layout": "rule58" (the earlier Rule 58 layout)."""
    def setUp(self):
        self.spec = rule58_spec()

    def test_sample_clean(self):
        self.assertEqual(LP.layout(self.spec["parawise"]), "rule58")
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
        d = tempfile.mkdtemp()
        try:
            r = run([os.path.join(TOOLS, "lint_parawise.py"), write(self.spec, d, "r58.json")])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("LINT OK", r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)
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
        self.r58 = write(rule58_spec(), self.tmp, "r58.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, spec_path, pre="T", extra=()):
        return run([os.path.join(TOOLS, "build_parawise.py"), spec_path, self.tmp, pre, *extra])

    def test_build_office_sample(self):
        """Default = the Section's office format (Abhi 03.11.2026): title, party line, submissions line, ONE table
        Sr. No. | Para No. | Remarks; "Grounds" separator row un-numbered; averments not printed."""
        r = self.build(WP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = os.path.join(self.tmp, "T_Parawise.docx")
        self.assertIn(out, r.stdout)
        d = docx.Document(out)
        pw = load(WP)["parawise"]
        P = [p for p in d.paragraphs if p.text.strip()]
        self.assertEqual(P[0].text, "Para wise Explanation in WRIT PETITION NO. ____ OF 2026.")
        self.assertEqual(P[1].text, "Shri. A. B. Chachani Vs. The State of Maharashtra and Ors.")
        self.assertTrue(P[2].text.startswith("Parawise submissions on behalf of Respondent No. 2 i.e. the State of"))
        self.assertTrue(P[2].text.endswith("in respect of contentions raised by the present petitioner, in this petition."))
        self.assertTrue(P[-1].text.strip().startswith("*****"))
        self.assertEqual(P[0].alignment, 1)   # centre
        self.assertTrue(all(r.bold for r in P[0].runs + P[1].runs))
        self.assertEqual({r.font.size.pt for r in P[0].runs + P[1].runs}, {16.0})
        self.assertEqual({r.font.size.pt for r in P[2].runs}, {13.0})
        self.assertEqual(len(d.tables), 1)
        t = d.tables[0]
        self.assertEqual([c.text for c in t.rows[0].cells], ["Sr. No.", "Para No.", "Remarks"])
        self.assertTrue(all(r.bold for c in t.rows[0].cells for p in c.paragraphs for r in p.runs))
        self.assertEqual(len(t.rows), 1 + len(pw["paras"]))
        n = 0
        for row, it in zip(t.rows[1:], pw["paras"]):
            cells = [c.text for c in row.cells]
            if "section" in it:
                self.assertEqual(cells, ["", "", "Grounds"])
                self.assertTrue(all(r.bold for r in row.cells[2].paragraphs[0].runs))
                continue
            n += 1
            self.assertEqual(cells[0], f"{n}.")
            want = ("Para No." + it["para"]) if it["para"][0].isdigit() else it["para"]
            self.assertEqual(cells[1], want)
            self.assertEqual(cells[2], it["remarks"])
        text = all_text(d)
        for it in pw["paras"]:
            if it.get("averment"):
                self.assertNotIn(it["averment"], text)
        for s in ("Brief facts", "Recommendation", "Documents enclosed", "Averments"):
            self.assertNotIn(s, text)
        grid = [int(g.get(qn("w:w"))) for g in t._tbl.tblGrid.iter(qn("w:gridCol"))]
        self.assertEqual(grid, [959, 1276, 6080])
        self.assertEqual(t._tbl.tblPr.find(qn("w:tblInd")).get(qn("w:w")), "567")
        sec = d.sections[0]
        self.assertEqual((sec.left_margin.twips, sec.right_margin.twips, sec.page_width.twips), (1800, 1440, 11906))
        self.assertFalse(any(p.text.strip() for p in sec.footer.paragraphs))
        self.assertEqual(bad_fonts(d), 0)
        import clean_meta
        self.assertEqual(clean_meta.docx_meta_problems(out), [])

    def test_build_rule58(self):
        r = self.build(self.r58)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = os.path.join(self.tmp, "T_Parawise.docx")
        self.assertIn(out, r.stdout)
        d = docx.Document(out)
        pw = RULE58
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
        s = rule58_spec()
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
        r = self.build(self.r58)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = docx.Document(os.path.join(self.tmp, "T_Parawise.docx"))
        self.assertFalse(any(p.text.startswith("Relief sought") for p in d.paragraphs))
        if shutil.which("soffice"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "T_Parawise.pdf")), r.stderr)

    def test_not_oppose_and_verification(self):
        s = rule58_spec(); s["parawise"]["recommendation"] = "not oppose"; s["parawise"]["verification"] = True
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
        s = rule58_spec(); s["parawise"]["recommendation"] = "____"
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
