"""Tests for the 05.11.2026 audit fix round (docs/AUDIT_2026-11-05.md Part 3 / Part 9, Part 7 S-F3) in tools/lint_spec.py,
tools/lint_parawise.py, tools/lint_affidavit.py, tools/verify_outputs.py and tools/extract_check.py.
Run: python3 -m unittest tests.test_audit_fixes -v   (or python3 -m pytest -q tests/test_audit_fixes.py)
Ids: Q-F3 extract page scope, Q-F4 / Q-F5 verify parser bugs, Q-F6 / F8 / F9 / F11 / F12 / F19 / F21 WARN lints, Q-F7 /
R-F2 letter no. in note.first (ERROR), Q-F13 Affidavit / LQ_Answer files, Q-F14 --case-meta, Q-F17 highlight coverage,
S-F3 --details redaction."""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import pymupdf as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import lint_spec as L  # noqa: E402
import lint_parawise as LP  # noqa: E402
import lint_affidavit as LA  # noqa: E402
import extract_check as X  # noqa: E402
import verify_outputs as V  # noqa: E402
import test_verify_outputs as TV  # noqa: E402 — fixture builders (CR122 note, Study, stand-in package)

SPECS = os.path.join(ROOT, "samples", "specs")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8"); ENV.pop(L.DETAILS_ENV, None)


def sample(name):
    with open(os.path.join(SPECS, name), encoding="utf-8-sig") as f:
        return json.load(f)


def run(args, env=ENV):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", env=env, cwd=ROOT)


def new_warns(spec, base):
    return [w for w in L.lint_warnings(spec) if w not in set(L.lint_warnings(base))]


class LintAuditRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s131 = sample("CR131_2026_special-pay_info-letter.json")      # no audit WARN of its own
        cls.wp = sample("WP35697_2026_parawise_GP-letter.json")

    def spec(self):
        return copy.deepcopy(self.s131)

    # ---- Q-F7 / R-F2 (ERROR) ----
    def test_letter_no_in_first_is_error(self):
        s = self.spec()
        s["note"]["first"] = ("प्रमुख जिल्हा व सत्र न्यायाधीश, भंडारा यांच्या पृ.3-4/प.वि. वरील पत्र क्र. 1234/2026, "
                              "दि. 25.03.2026 रोजीच्या पत्रास अनुसरून सादर.")
        errs = [p for p in L.lint_spec(s) if p.startswith("note.first:") and "§4.29(1)" in p]
        self.assertEqual(len(errs), 1, L.lint_spec(s))
        s["note"]["first"] = s["note"]["first"].replace("पत्र क्र. 1234/2026", "जा. क्रमांक :- संकिर्ण/12/2026")
        self.assertTrue([p for p in L.lint_spec(s) if "§4.29(1)" in p])

    def test_first_without_letter_no_ok(self):
        for first in (self.s131["note"]["first"],
                      "सहायक सरकारी वकील यांच्या पृ.1/प.वि. वरील दि. 01.01.2026 रोजीच्या पत्रास अनुसरून सादर.",
                      "रिट याचिका क्र. 35697/2026 मधील सरकारी वकील यांच्या पृ.2/प.वि. वरील पत्रास अनुसरून सादर.",
                      "प्रमुख जिल्हा व सत्र न्यायाधीश यांच्या “क्र. 12/2026” पृ.3/प.वि. वरील पत्रास अनुसरून सादर.",
                      "अर्ज क्र. 5/2026 च्या अनुषंगाने पृ.3/प.वि. वरील पत्रास अनुसरून सादर."):
            with self.subTest(first=first[:30]):
                self.assertEqual(L.first_letter_no_problems(first), [])

    def test_no_sample_has_letter_no_in_first(self):
        for p in sorted(glob.glob(os.path.join(SPECS, "*.json"))):
            s = sample(os.path.basename(p))
            if isinstance(s.get("note"), dict):
                with self.subTest(spec=os.path.basename(p)):
                    self.assertEqual(L.first_letter_no_problems(s["note"].get("first") or ""), [])

    # ---- Q-F6 (WARN) ----
    def test_missing_remark_new_words_warn_not_error(self):
        s = self.spec()
        s["note"]["paras"][0] += " प्रस्तावात वचनपत्राचा उल्लेख नाही. आदेश आढळून येत नाही."
        self.assertEqual(L.lint_spec(s), L.lint_spec(self.s131))
        w = [x for x in new_warns(s, self.s131) if "missing-info remark" in x]
        self.assertEqual(len(w), 2, w)
        s["note"]["paras"][0] = self.s131["note"]["paras"][0] + " “… उल्लेख नाही …”"   # quotes exempt
        self.assertFalse([x for x in new_warns(s, self.s131) if "missing-info remark" in x])

    # ---- Q-F8 (WARN) ----
    def test_summary_items(self):
        mk = lambda k: [("x", "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-", [f"({i}) तथ्य" for i in range(1, k + 1)])]
        self.assertEqual(L.summary_problems(mk(3)), [])
        self.assertEqual(L.summary_problems(mk(6)), [])
        self.assertTrue(any("2 items" in w for w in L.summary_problems(mk(2))))
        self.assertTrue(any("7 items" in w for w in L.summary_problems(mk(7))))
        q = [("x", "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-", ["(1) a", "(2) “उतारा”", "(3) c"])]
        self.assertTrue(any("quote" in w for w in L.summary_problems(q)))
        inline = [("x", "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:- (1) अ; (2) ब; (3) क; (4) ड; (5) इ; (6) फ; (7) ग.", [])]
        self.assertTrue(any("7 items" in w for w in L.summary_problems(inline)))

    def test_summary_in_spec_table_rows(self):
        s = self.spec(); i = len(s["note"]["paras"]) - 1
        s["note"]["paras"][i:i] = ["उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-",
                                   {"table": [["अ.क्र.", "तथ्य"]] + [[str(k), "तथ्य"] for k in range(1, 9)]}]
        self.assertTrue([w for w in new_warns(s, self.s131) if "8 items" in w])

    # ---- Q-F9 (WARN) ----
    def test_long_sentence(self):
        long_ = " ".join(["शब्द"] * 41) + " आहे."
        self.assertTrue(L.long_sentence_warnings([("note.paras[0]", long_)]))
        self.assertFalse(L.long_sentence_warnings([("note.paras[0]", " ".join(["शब्द"] * 39) + " आहे.")]))
        # abbreviation dots do not end a sentence: "दि.", "क्र.", "श्री.", "प.वि.", initials
        t = ("श्री. ह. ना. आपटे यांनी दि. 17.09.2026 रोजी क्र. 108 चा अर्ज (पृ.3/प.वि.) सादर केला आहे. "
             + " ".join(["शब्द"] * 30) + ".")
        self.assertEqual(len(L.sentences(t)), 2)
        self.assertFalse(L.long_sentence_warnings([("x", t)]))
        # quoted text is not own text
        self.assertFalse(L.long_sentence_warnings([("x", "त्यात “" + " ".join(["शब्द"] * 60) + "” असे नमूद आहे.")]))

    def test_long_sentence_message_has_no_text(self):
        w = L.long_sentence_warnings([("note.paras[2]", " ".join(["गोपनीय"] * 45) + ".")])
        self.assertEqual(len(w), 1)
        self.assertNotIn("गोपनीय", w[0])
        self.assertIn("45 words", w[0])

    # ---- Q-F11 / Q-F12 (WARN) ----
    def test_court_shape_model_ok(self):
        self.assertEqual(L.court_shape_warnings(self.wp), [])

    def test_court_shape_bad(self):
        s = copy.deepcopy(self.wp)
        s["note"]["paras"][0] = s["note"]["paras"][0].replace("प्रतिवादी क्र.", "प्रतिवादी")
        self.assertTrue(any("para 2" in w for w in L.court_shape_warnings(s)))
        s = copy.deepcopy(self.wp); s["note"]["paras"][2]["table"][0][1] = "मुद्दा"
        self.assertTrue(any("para 3" in w for w in L.court_shape_warnings(s)))
        s = copy.deepcopy(self.wp); s.pop("parawise")   # not a court-reply spec: not checked
        self.assertEqual(L.court_shape_warnings(s), [])

    def test_registry_on_behalf_and_copies(self):
        s = copy.deepcopy(self.wp)
        self.assertEqual(LP.warnings_parawise(s), [w for w in LP.warnings_parawise(s) if "§4.35" not in w])
        s["parawise"]["on_behalf_of"] += " and Respondent No. 4 i.e. the Registrar General, High Court of Bombay"
        self.assertTrue([w for w in LP.warnings_parawise(s) if "§4.35" in w])
        s = copy.deepcopy(self.wp); s["letter"]["copies"].append("महाप्रबंधक, मा. उच्च न्यायालय, मुंबई यांना माहितीसाठी")
        self.assertTrue([w for w in L.lint_warnings(s) if "copies[1]" in w and "§4.35" in w])
        s = copy.deepcopy(self.wp); s["letter"]["copies"].append("सहायक सरकारी वकील, उच्च न्यायालय, खंडपीठ नागपूर यांना माहितीसाठी")
        self.assertFalse([w for w in L.lint_warnings(s) if "§4.35" in w])
        af = sample("COURT_affidavit_example.json")
        self.assertFalse([w for w in LA.warnings_affidavit(af) if "§4.35" in w])
        af["affidavit"]["on_behalf_of"] = "Respondent No. 3 i.e. the Registrar, High Court"
        self.assertTrue([w for w in LA.warnings_affidavit(af) if "§4.35" in w])

    # ---- Q-F19 (WARN) ----
    def test_demand(self):
        self.assertEqual(L.demand_warnings(self.s131), [])
        s = self.spec(); s["note"]["paras"][0] = "श्रीमती बारई या सहायक अधीक्षक पदावर कार्यरत आहेत."
        self.assertTrue(L.demand_warnings(s))
        s["note"]["first"] = "उप सचिव यांच्या दि. 01.01.2026 रोजीच्या निर्देशानुसार सादर."   # own initiative: not checked
        self.assertEqual(L.demand_warnings(s), [])

    # ---- Q-F21 (WARN) ----
    def test_library_ref(self):
        s = self.spec()
        s["related"][0]["source"] = "पत्र दि. 01.01.2025 (पूर्वोदाहरण-ग्रंथालय, संग्रह 08)"
        self.assertTrue([w for w in L.lint_warnings(s) if w.startswith("related[0].source:") and "ग्रंथालय" in w])

    def test_samples_no_new_errors(self):
        for p in sorted(glob.glob(os.path.join(SPECS, "*.json"))):
            s = sample(os.path.basename(p))
            if isinstance(s.get("note"), dict):
                with self.subTest(spec=os.path.basename(p)):
                    self.assertEqual(L.lint_spec(s), [])
                    self.assertEqual(L.lint_extras(s)[0], [])


class DetailsRedaction(unittest.TestCase):
    """S-F3: --details FILE / env CASE_DETAILS_FILE — no quoted case text on stdout, the full lines in the file."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_redact(self):
        self.assertEqual(L.redact("FAIL: x — 'गोपनीय नाव' and “उतारा”"), "FAIL: x — '<10 ch>' and '<5 ch>'")

    def test_lint_cli_details(self):
        s = sample("CR131_2026_special-pay_info-letter.json")
        s["letter"]["ref_no"] = "गोपनीय-क्रमांक"
        sp = os.path.join(self.tmp, "s.json"); json.dump(s, open(sp, "w", encoding="utf-8"), ensure_ascii=False)
        det = os.path.join(self.tmp, "d.log")
        r = run([os.path.join(TOOLS, "lint_spec.py"), sp, "--details", det])
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("गोपनीय", r.stdout)
        self.assertIn("letter.ref_no", r.stdout)
        self.assertIn("गोपनीय-क्रमांक", open(det, encoding="utf-8").read())
        r = run([os.path.join(TOOLS, "lint_spec.py"), sp])   # no details file: unchanged output
        self.assertIn("गोपनीय-क्रमांक", r.stdout)
        env = dict(ENV, **{L.DETAILS_ENV: os.path.join(self.tmp, "e.log")})
        r = run([os.path.join(TOOLS, "lint_spec.py"), sp], env=env)
        self.assertNotIn("गोपनीय", r.stdout)
        self.assertIn("गोपनीय-क्रमांक", open(os.path.join(self.tmp, "e.log"), encoding="utf-8").read())


class ExtractNoteScope(unittest.TestCase):
    """Q-F3: a note-body quote whose para cites no page uses the document's first mention / its enclosure pages."""
    def test_first_mention(self):
        mp = {"प्रस्ताव": {"first_page": 1, "pages": [1, 2, 3]}, "GR 01.01.2020": {"first_page": 4, "pages": [4, 5, 6]}}
        spec = {"note": {"first": "x यांच्या पृ.1/प.वि. वरील पत्रास अनुसरून सादर.", "paras": [
            "वित्त विभागाचा शासन निर्णय दि. 01.01.2020 (पृ.4/प.वि.) लागू आहे.",
            "सदर शासन निर्णय दि. 01.01.2020 च्या परिच्छेद 3 मध्ये “मजकूर येथे असा आहे की वेतन लागू राहील” असे नमूद आहे.",
            "इतर “दुसरा उतारा येथे असा आहे की काहीतरी” असे आहे."]}}
        u = X.units_note(spec, mp, 6)
        self.assertEqual(u[0][2], [4, 5, 6])
        self.assertIn("first_mention", u[0][0])
        self.assertEqual(u[1][2], [4, 5, 6])          # no document token: every enclosure page
        self.assertIn("enclosures", u[1][0])
        self.assertEqual(X.units_note(spec, None, 6)[1][2], list(range(1, 7)))   # no map: every package page

    def test_check_wide_search(self):
        tmp = tempfile.mkdtemp()
        try:
            pdf = os.path.join(tmp, "p.pdf"); d = m.open()
            for t in ("Proposal page text " * 5, "Government resolution page one text " * 3,
                      "The pay shall continue to apply to the post concerned until revised. " * 2):
                d.new_page().insert_text((40, 80), t[:90], fontsize=9)
            d.save(pdf); d.close()
            json.dump({"प्रस्ताव": {"first_page": 1, "pages": [1]}, "GR": {"first_page": 2, "pages": [2, 3]}},
                      open(pdf + ".map.json", "w"))
            spec = {"note": {"first": "सादर.", "paras": ["Para “The pay shall continue to apply to the post” here.",
                                                          "Para “This sentence is not in the package at all” here."]}}
            recs = X.check(pdf, spec, None, None, True, None, note_body=True)
            st = {r["where"].split(" [")[0]: r["status"] for r in recs}
            self.assertEqual(st["नोंद परि. 2"], "ok")
            self.assertEqual(st["नोंद परि. 3"], "mismatch")
            self.assertTrue(all(r.get("warn_only") for r in recs))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_short_where(self):
        self.assertEqual(X.short_where("related[3] वित्त विभाग शासन निर्णय"), "related[3]")
        self.assertEqual(X.short_where("नोंद परि. 4 [पाने: enclosures]"), "नोंद परि. 4")


class VerifyUnits(unittest.TestCase):
    def test_source_of_line(self):
        for line, want in (("(वित्त विभाग, Financial Publication No. III, पृ.40, पृ.20/प.वि.)",
                            "वित्त विभाग, Financial Publication No. III, पृ.40 (पृ.20/प.वि.)"),
                           ("(GR, पृ. 46, 47, 50, पृ.21,22,23/प.वि.)", "GR, पृ. 46, 47, 50 (पृ.21,22,23/प.वि.)"),
                           ("(शासन निर्णय, पृ.5/प.वि.)", "शासन निर्णय (पृ.5/प.वि.)"),
                           ("(GR पृ. 2)", "GR पृ. 2")):
            with self.subTest(line=line):
                self.assertEqual(V.source_of_line(line), want)
                self.assertEqual(L.related_source_problems(V.source_of_line(line)), [])

    def test_ref_meta(self):
        ln = "क्रमांक :- संकिर्ण-2026/979/प्र.क्र.130/का.6"
        self.assertEqual(V.ref_meta_problems(ln, {"file_no": "संकीर्ण-2026/979/प्र.क्र.130/का.6"}), [])
        self.assertEqual(V.ref_meta_problems(ln, {"file_no": "979", "cr_no": "130"}), [])
        self.assertEqual(V.ref_meta_problems(ln, {}), [])
        self.assertEqual(len(V.ref_meta_problems(ln, {"file_no": "2025/978", "cr_no": "131"})), 3)
        self.assertEqual(V.ref_meta_problems("क्रमांक :- संकिर्ण-2026/____/प्र.क्र.130/का.6", {"file_no": "2026/979"}), [])

    def test_summary_blocks(self):
        bl = [{"kind": "p", "text": "5. उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-"},
              {"kind": "p", "text": "(1) अ"}, {"kind": "tbl", "text": "अ.क्र. | तथ्य\n1 | ब\n2 | क"},
              {"kind": "p", "text": "6. पुढील"}, {"kind": "p", "text": "(1) इतर"}]
        e = V.summary_blocks(bl)
        self.assertEqual(len(e), 1); self.assertEqual(len(e[0][2]), 3)


@unittest.skipIf(TV.FONTFILE is None, "no Devanagari font for the page stamps")
class VerifyAuditFixes(unittest.TestCase):
    """Built CR122 fixture (tests/test_verify_outputs.py builders) + one change per fix."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vaudit_")
        cls.spec = json.load(open(TV.SPEC, encoding="utf-8"))
        cls.good = os.path.join(cls.tmp, "good"); os.makedirs(cls.good)
        TV.build_note(cls.spec, cls.good)
        TV.build_study(TV.study_spec(cls.spec), cls.good)
        TV.build_pkg(os.path.join(cls.good, TV.PKGNAME))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def case(self, name, spec=None):
        d = os.path.join(self.tmp, name)
        if spec is None:
            shutil.copytree(self.good, d)
        else:
            os.makedirs(d); TV.build_note(spec, d); TV.build_study(TV.study_spec(self.spec), d)
            TV.build_pkg(os.path.join(d, TV.PKGNAME))
        return d

    def verify(self, d, *extra, env=None):
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "verify_outputs.py"), d, TV.PRE,
                            os.path.join(d, TV.PKGNAME), str(TV.NPP), *extra], capture_output=True, text=True,
                           encoding="utf-8", env=env or TV.ENV)
        return r.returncode, r.stdout + r.stderr

    def test_q_f4_source_with_gr_page(self):
        s = copy.deepcopy(self.spec)
        src = s["related"][0]["source"]
        s["related"][0]["source"] = src.replace(" (पृ.", ", पृ. 40 (पृ.", 1) if " (पृ." in src else src + ", पृ. 40 (पृ.17/प.वि.)"
        rc, out = self.verify(self.case("f4", s))
        self.assertIn("OK: संबंधित माहिती source ends with (पृ.N/प.वि.) or no page marker", out)

    def test_q_f5_closing_para_finance(self):
        s = copy.deepcopy(self.spec); s.pop("letter", None)
        s["note"]["closing"] = "सबब, उपरोक्त प्रस्ताव वित्त विभागाच्या सहमतीस्तव सादर करण्यात येत आहे."
        s["note"]["signers"] = list(L.SIGNERS) + [L.AMS]
        rc, out = self.verify(self.case("f5", s))
        self.assertIn("OK: अ.मु.स. (वित्त) <=> Finance last para", out)
        s["note"]["signers"] = list(L.SIGNERS)
        rc, out = self.verify(self.case("f5b", s))
        self.assertIn("FAIL: अ.मु.स. (वित्त) <=> Finance last para", out)

    def test_q_f13_affidavit_lq(self):
        d = self.case("f13")
        TV.make_extra(os.path.join(d, f"{TV.PRE}_Affidavit.docx"), ["AFFIDAVIT IN REPLY (पृ.17/प.वि.)"])
        TV.make_extra(os.path.join(d, f"{TV.PRE}_LQ_Answer.docx"), ["उत्तराचा दिनांक"])
        rc, out = self.verify(d)
        for ln in ("OK: Affidavit fonts", "OK: Affidavit पृ. references", "OK: LQ_Answer fonts", "OK: LQ_Answer metadata"):
            self.assertIn(ln, out)
        TV.make_extra(os.path.join(d, f"{TV.PRE}_Affidavit.docx"), ["AFFIDAVIT drafted by Claude (पृ.99/प.वि.) z6_0235"],
                      font=False)
        rc, out = self.verify(d)
        self.assertEqual(rc, 1)
        for ln in ("FAIL: Affidavit fonts", "FAIL: Affidavit internal ids", "FAIL: Affidavit पृ. references",
                   "FAIL: Affidavit no package / warning / AI words"):
            self.assertIn(ln, out)

    def test_q_f14_case_meta(self):
        d = self.case("f14")
        ref = self.spec["letter"]["ref_no"]
        mt = os.path.join(d, "meta.json")
        json.dump({"file_no": ref}, open(mt, "w", encoding="utf-8"), ensure_ascii=False)
        rc, out = self.verify(d, "--case-meta", mt)
        self.assertIn("OK: letter ref no. = case file no. (--case-meta)", out)
        json.dump({"file_no": "1999/1"}, open(mt, "w", encoding="utf-8"))
        rc, out = self.verify(d, "--case-meta", mt)
        if V.LETTER_REF_PARTS_RE.search(ref) and "_" not in V.LETTER_REF_PARTS_RE.search(ref).group(1):
            self.assertIn("FAIL: letter ref no. = case file no. (--case-meta)", out)
        rc, out = self.verify(d)
        self.assertNotIn("case file no.", out)

    def test_q_f17_highlight(self):
        d = self.case("f17")
        rc, out = self.verify(d)
        self.assertIn("OK: highlight coverage", out)
        # a highlight on a GR page whose words are not in any quoted extract
        pk = os.path.join(d, TV.PKGNAME); doc = m.open(pk)
        pg = doc[TV.NPP + 1]
        pg.insert_text((72, 300), "Completely unrelated sentence about railway timetables and weather today.", fontsize=11)
        pg.insert_text((72, 320), "More filler words so the page text layer is long enough to be compared here.", fontsize=11)
        a = pg.add_highlight_annot(pg.search_for("Completely unrelated sentence about railway")[0]); a.update()
        doc.saveIncr(); doc.close()
        rc, out = self.verify(d)
        self.assertTrue([ln for ln in out.splitlines() if ln.startswith("WARN:") and "highlight not inside" in ln], out)
        self.assertEqual(rc, 0, out)   # WARN only

    def test_q_f17_skipped_without_highlights(self):
        d = self.case("f17b"); pk = os.path.join(d, TV.PKGNAME); doc = m.open(pk)
        for pg in doc:
            for a in list(pg.annots()):
                pg.delete_annot(a)
        doc.saveIncr(); doc.close()
        rc, out = self.verify(d)
        self.assertIn("OK: highlight coverage — skipped", out)

    def test_s_f3_details(self):
        d = self.case("sf3")
        TV.set_text(os.path.join(d, f"{TV.PRE}_Note_and_Letter.docx"), "( राजेश वडनेरकर )", "( गोपनीय नाव )")
        det = os.path.join(d, "details.log")
        rc, out = self.verify(d, "--details", det)
        self.assertIn("FAIL: letter ending (§4.5)", out)
        self.assertNotIn("राजेश", out)
        self.assertIn("राजेश वडनेरकर", open(det, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()


class OwnerDecisions05Nov(unittest.TestCase):
    """C1 / C2 (Abhi 05.11.2026, options आ; INSTRUCTIONS §4.29(1)/(5), §4.30(7), §4.31(अ), §4.36) + the U.O. exception."""

    def test_c1_letter_no_in_body_is_error(self):
        for t in ("प्रमुख जिल्हा व सत्र न्यायाधीश यांच्या पत्र क्र. 1234/2026 दि. 01.01.2026 नुसार माहिती प्राप्त झाली आहे.",
                  "महालेखापाल यांच्या क्र. लेखा/123/2026, दि. 12.03.2026 रोजीच्या पत्रान्वये कळविले आहे.",
                  "जिल्हा न्यायालयाच्या स्मरणपत्र क्र. 5/2026 द्वारे प्रस्ताव पुन्हा सादर झाला आहे."):
            with self.subTest(t=t[:30]):
                self.assertTrue(L.note_letter_no_hits(t), t)
                n = {"paras": ["x", {"table": [["अ", "ब"], ["1", t]]}], "sub": {}, "closing": "सबब, … मान्यतेस्तव सादर."}
                self.assertTrue([p for p in L.note_letter_no_problems(n) if "C1" in p and "note.paras[1]" in p])

    def test_c1_not_letter_numbers(self):
        for t in ("शासन निर्णय क्र. वेतन-1311/प्र.क्र.17/सेवा-3, दि. 01.01.2011 नुसार पत्र पाठविले.",
                  "रिट याचिका क्र. 35697/2026 मधील पत्र पाहावे.",
                  "प्र. क्र. 21/2024 बाबतचे पत्र.",
                  "या कार्यासनाचे पत्र क्र. संकिर्ण-2024/प्र.क्र.259/का.6 नुसार.",
                  "परिपत्रक क्र. 12/2020 नुसार.",
                  "दि. 01.01.2026 च्या पत्रातील मुद्दा क्र. 02 नुसार.",
                  "यांच्या “पत्र क्र. 1/2026” या पत्रान्वये.",
                  "यांच्या पृ.3/प.वि. वरील दि. 01.01.2026 रोजीच्या पत्रान्वये."):
            with self.subTest(t=t[:30]):
                self.assertEqual(L.note_letter_no_hits(t), [])

    def test_uo_and_other_desk_ref_kept(self):
        """Abhi 05.11.2026: a department's U.O. reference no. and another desk's reference no. stay in the note."""
        for t in ("वित्त विभागाच्या अनौपचारिक संदर्भ क्र. 123/2026/व्यय-5, दि. 01.01.2026 नुसार पत्र प्राप्त झाले.",
                  "सामान्य प्रशासन विभागाने अनौपचारिक संदर्भ क्रमांक 45/सेवा-4 अन्वये पत्राद्वारे कळविले.",
                  "सार्वजनिक आरोग्य विभागाच्या यु.ओ. क्र. 7/2026 नुसार पत्र.",
                  "कार्यासन-4 च्या संदर्भ क्र. 12/2026 नुसार पत्र प्राप्त झाले."):
            with self.subTest(t=t[:30]):
                self.assertEqual(L.note_letter_no_hits(t), [])
        first = "वित्त विभागाच्या अनौपचारिक संदर्भ क्र. 123/2026/व्यय-5, दि. 01.01.2026 अन्वये प्राप्त नस्तीस अनुसरून सादर."
        self.assertEqual(L.first_letter_no_problems(first), [])

    def test_c2_missing_info_inline(self):
        head = L.MISSING_HEAD + ":-"
        n = {"paras": ["तथ्य.", head, {"table": [["अ.क्र.", "माहिती"], ["1", "सेवानिवृत्तीचा दिनांक"]]},
                       "सबब, … मान्यतेस्तव सादर."]}
        P, W = L.missing_inline_problems(n)
        self.assertEqual(len(P), 1); self.assertIn("C2", P[0])
        self.assertEqual(len(W), 1); self.assertIn("table after the missing-info para", W[0])
        n["paras"] = ["तथ्य.", head + " (1) सेवानिवृत्तीचा दिनांक; (2) विकल्प अर्जाचा दिनांक.", "सबब, … मान्यतेस्तव सादर."]
        self.assertEqual(L.missing_inline_problems(n), ([], []))

    def test_c2_c1_in_lint_spec(self):
        s = sample("CR131_2026_special-pay_info-letter.json")
        i = next(i for i, x in enumerate(s["note"]["paras"]) if isinstance(x, str) and x.startswith(L.MISSING_HEAD))
        s["note"]["paras"][i] = L.MISSING_HEAD + ":- (1) विशेष वेतनाचा दिनांक; (2) आदेशाचा दिनांक."
        if isinstance(s["note"]["paras"][i + 1], dict):
            del s["note"]["paras"][i + 1]
        self.assertFalse([p for p in L.lint_spec(s) if "C2" in p])
        self.assertFalse([w for w in L.lint_warnings(s) if "table after the missing-info para" in w])
        s["note"]["paras"][0] += " प्रबंधक यांच्या पत्र क्र. 99/2026 नुसार."
        self.assertTrue([p for p in L.lint_spec(s) if p.startswith("note.paras[0]") and "C1" in p])

    def test_verify_has_c1_c2_checks(self):
        src = open(os.path.join(TOOLS, "verify_outputs.py"), encoding="utf-8").read()
        self.assertIn('"missing-info items inline §4.31(अ) C2 (note body)"', src)
        self.assertIn('"no incoming letter no. in the note §4.29 C1 (note body)"', src)

    def test_uo_blank_placeholder_warns(self):
        """Abhi 05.11.2026: "प्रत्येक वेळी अनौपचारिक संदर्भ असेलच असे नाही असल्यास ठेवावे" — no "____" U.O. number."""
        s = sample("CR131_2026_special-pay_info-letter.json")
        base = L.lint_warnings(s)
        s["note"]["paras"][0] += " वित्त विभागाच्या अनौपचारिक संदर्भ क्र. ____ नुसार."
        w = [x for x in L.lint_warnings(s) if x not in base]
        self.assertTrue([x for x in w if "blank U.O. reference no." in x], w)

    def test_lodging_word_warns(self):
        """Abhi 05.11.2026: "रिट याचिका क्र. N/YYYY" — no "(लॉजिंग)" in the Marathi note / letter (quotes exempt)."""
        s = sample("CR131_2026_special-pay_info-letter.json")
        base = L.lint_warnings(s)
        s["note"]["paras"][0] += " रिट याचिका (लॉजिंग) क्र. 123/2026 पहावी."
        self.assertTrue([x for x in L.lint_warnings(s) if x not in base and "लॉजिंग" in x])
        s["note"]["paras"][0] = sample("CR131_2026_special-pay_info-letter.json")["note"]["paras"][0] + " “WP (L) लॉजिंग”"
        self.assertFalse([x for x in L.lint_warnings(s) if x not in base and "लॉजिंग" in x])
