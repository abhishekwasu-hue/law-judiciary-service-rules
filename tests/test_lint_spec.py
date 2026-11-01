"""Tests for tools/lint_spec.py (pre-build lint) and its wiring into build_note_letter.py / build_study.py.
Run: py -m unittest tests.test_lint_spec -v        (runner: python3 -m unittest tests.test_lint_spec -v)
GOOD = all samples/specs/*.json; then one must-fail case per rule (spec and study)."""
import copy
import glob
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
import lint_spec as L  # noqa: E402

SPECS = sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "*.json")))
CR122 = next(p for p in SPECS if os.path.basename(p).startswith("CR122_"))
CR66 = next(p for p in SPECS if os.path.basename(p).startswith("CR66_"))
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
ENV.pop("LINT_SKIP", None); ENV.pop("STUDY_ALLOW_MISSING_PART1", None)


def load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def run(args, env=ENV):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", env=env, cwd=ROOT)


def study(skip=()):
    parts = [{"heading": f"भाग {i} — शीर्षक", "blocks": [{"para": "मजकूर (पृ.4-5/प.वि.)"}]} for i in range(8) if i not in skip]
    parts[0]["blocks"] += [{"bullets": ["प्रस्ताव : चाचणी (पॅकेज PDF पृ. 3)"]},
                           {"table": [["तपशील", "माहिती", "पृ./प.वि."], ["दिनांक", "01.01.2026", "15-16"]]}]
    return {"title": "C R 1/2026 — अभ्यास-फाइल", "parts": parts}


class LintSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s122 = load(CR122); cls.s66 = load(CR66)

    def bad(self, base, fn, needle, path=None, pages=None):
        s = copy.deepcopy(base); fn(s)
        probs = L.lint_spec(s, pages)
        self.assertTrue(any(needle in p and (path is None or p.startswith(path + ":")) for p in probs),
                        f"expected '{needle}' at {path}: {probs}")
        return probs

    # ---- GOOD ----
    def test_all_samples_lint_ok(self):
        self.assertGreaterEqual(len(SPECS), 6)
        for p in SPECS:
            with self.subTest(spec=os.path.basename(p)):
                self.assertEqual(L.lint_spec(load(p)), [])
                r = run([os.path.join(TOOLS, "lint_spec.py"), p])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip(), "LINT OK")

    # ---- §4.18 language (01.11.2026) ----
    def test_sau_not_shrimati(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " सौ. एन. जी. बारई"),
                 "'सौ.' ऐवजी 'श्रीमती'", "note.paras[0]")

    def test_unspaced_initials(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " श्री.आर.टी.लाखे"),
                 "'श्री.' नंतर जागा", "note.paras[0]")

    def test_quoted_text_is_exempt(self):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][0] += " अर्जात “सौ.बारई यांनी तात्काळ” असे नमूद आहे."
        self.assertFalse([p for p in L.lint_spec(s) if "§4.18" in p])

    def test_letter_tatkal(self):
        def f(s):
            s["letter"]["intro"] = s["letter"]["intro"].replace("शासनास", "शासनास तात्काळ")
        self.bad(self.s122, f, "'तात्काळ' नको", "letter.intro")

    def test_letter_request_form(self):
        def f(s):
            s["letter"]["intro"] = s["letter"]["intro"].replace(", ही विनंती", "")
        self.bad(self.s122, f, "ही विनंती", "letter.intro")

    # ---- must fail: spec ----
    def test_banned_word(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " असे दिसून येते."),
                 "banned word", "note.paras[0]")

    def test_banned_word_in_letter_table(self):
        def f(s):
            s["letter"]["points"] = [{"table": [["अ.क्र.", "माहिती"], ["1", "कदाचित"]]}]
        self.bad(self.s122, f, "banned word", "letter.points[0].table[1][1]")

    def test_internal_id(self):
        self.bad(self.s122, lambda s: s["related"][0].__setitem__("source", "z6_0235"), "internal id", "related[0].source")

    def test_repo_path(self):
        self.bad(self.s122, lambda s: s["related"][0].__setitem__("source", "register/PAY-01"), "repo path", "related[0].source")

    def test_repo_word_marathi(self):
        self.bad(self.s122, lambda s: s["note"].__setitem__("first", "रेपो मधील " + s["note"]["first"]), "repo path", "note.first")

    def test_package_pdf_in_note(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " (पॅकेज PDF पृ. 3)"),
                 "'पॅकेज PDF'", "note.paras[0]")

    def test_package_pdf_in_letter(self):
        self.bad(self.s122, lambda s: s["letter"].__setitem__("intro", s["letter"]["intro"] + " (पॅकेज PDF पृ. 3)"),
                 "'पॅकेज PDF'", "letter.intro")

    def test_package_pdf_allowed_in_related(self):
        s = copy.deepcopy(self.s122); s["related"][0]["source"] += " (पॅकेज PDF पृ. 3)"
        self.assertEqual(L.lint_spec(s), [])

    def test_unparsed_reference(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " (पृ.5 व 7/प.वि.)"),
                 "unparsed reference", "note.paras[0]")

    def test_reversed_range(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " (पृ.9-5/प.वि.)"),
                 "reversed range", "note.paras[0]")

    def test_page_range_only_with_pages(self):
        s = copy.deepcopy(self.s122); s["note"]["paras"][0] += " (पृ. 99 / प.वि.)"
        self.assertEqual(L.lint_spec(s), [])
        self.assertTrue(any("page 99 outside package" in p for p in L.lint_spec(s, pages=20)))

    def test_accepted_reference_forms(self):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][0] += " (पृ.५ ते ७/प.वि.) (पृ. 5 / प.वि.) (पृ.5,7/प.वि.) (पृ.      /प.वि.)"
        self.assertEqual(L.lint_spec(s, pages=20), [])

    def test_first_para_not_saadar(self):
        self.bad(self.s122, lambda s: s["note"].__setitem__("first", s["note"]["first"].rstrip("सादर.")), "first para", "note.first")

    def test_last_para_wrong_form(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(len(s["note"]["paras"]) - 1, "सबब, कृपया आदेश द्यावेत."),
                 "last para")

    def test_last_para_from_closing(self):
        s = copy.deepcopy(self.s122); s["note"]["closing"] = s["note"]["paras"].pop()
        self.assertEqual(L.lint_spec(s), [])

    def test_missing_signer(self):
        self.bad(self.s122, lambda s: s["note"]["signers"].pop(1), "signer chain", "note.signers")

    def test_signer_order(self):
        self.bad(self.s122, lambda s: s["note"]["signers"].reverse(), "signer chain", "note.signers")

    def test_ams_without_finance(self):
        self.bad(self.s122, lambda s: s["note"]["signers"].append(L.AMS), "Finance last para")

    def test_finance_without_ams(self):
        self.bad(self.s66, lambda s: s["note"]["signers"].pop(), "Finance last para")

    def test_letter_ref_no(self):
        self.bad(self.s122, lambda s: s["letter"].__setitem__("ref_no", "संकिर्ण-2026/प्र.क्र.122/का.6"), "ref no.", "letter.ref_no")

    def test_letter_fields(self):
        for k in ("to", "subject", "refs"):
            with self.subTest(field=k):
                self.bad(self.s122, lambda s: s["letter"].pop(k), f"'{k}' missing", f"letter.{k}")

    def test_letter_intro_wording(self):
        self.bad(self.s122, lambda s: s["letter"].__setitem__("intro", "कृपया खालील माहिती पाठवावी.:-"), "intro wording", "letter.intro")

    def test_letter_intro_colon_dash(self):
        self.bad(self.s122, lambda s: s["letter"].__setitem__("intro", s["letter"]["intro"].rstrip(":-")), "':-'", "letter.intro")

    def test_no_note(self):
        self.assertTrue(L.lint_spec({"letter": {}}))

    # ---- study ----
    def test_study_good(self):
        self.assertEqual(L.lint_study(study()), [])

    def test_study_missing_part(self):
        for i in (0, 7):
            with self.subTest(part=i):
                self.assertTrue(any(f"भाग {i} missing" in p for p in L.lint_study(study(skip=(i,)))))

    def test_study_missing_part1_flag(self):
        self.assertTrue(any("भाग 1 missing" in p for p in L.lint_study(study(skip=(1,)))))
        self.assertEqual(L.lint_study(study(skip=(1,)), allow_missing_part1=True), [])
        self.assertTrue(L.lint_study(study(skip=(1, 2)), allow_missing_part1=True))

    def test_study_internal_id(self):
        st = study(); st["parts"][3]["blocks"].append({"para": "स्रोत z5_0100"})
        self.assertTrue(any(p.startswith("study.parts[3].blocks[1].para: internal id") for p in L.lint_study(st)))

    def test_study_ref_quote_skipped(self):
        st = study(); st["parts"][3]["blocks"].append({"para": "“जुन्या नस्तीत पृ.99/प.वि.”"})
        self.assertEqual(L.lint_study(st, pages=20), [])
        st["parts"][3]["blocks"].append({"para": "पत्र (पृ.५ ते ७, 99/प.वि.)"})
        self.assertTrue(any("page 99 outside package" in p for p in L.lint_study(st, pages=20)))

    def test_study_bad_heading(self):
        st = study(); st["parts"][2]["heading"] = "गोषवारा"
        self.assertTrue(any(p.startswith("study.parts[2].heading") for p in L.lint_study(st)))


class LintCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def dump(self, obj, name):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8-sig") as f:
            json.dump(obj, f, ensure_ascii=False)
        return p

    def test_cli_fail_lines_and_exit(self):
        s = load(CR122); s["note"]["paras"][0] += " असे दिसून येते."; s["note"]["signers"].pop()
        r = run([os.path.join(TOOLS, "lint_spec.py"), self.dump(s, "s.json"), "--pages", "20"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("LINT OK", r.stdout)
        self.assertIn("note.paras[0]: banned word", r.stdout)
        self.assertIn("note.signers: signer chain", r.stdout)

    def test_cli_study(self):
        p = self.dump(study(skip=(1,)), "st.json")
        r = run([os.path.join(TOOLS, "lint_spec.py"), CR122, "--study", p])
        self.assertEqual(r.returncode, 1); self.assertIn("भाग 1 missing", r.stdout)
        r = run([os.path.join(TOOLS, "lint_spec.py"), CR122, "--study", p, "--allow-missing-part1"])
        self.assertEqual(r.returncode, 0, r.stdout); self.assertIn("LINT OK", r.stdout)

    def test_build_note_letter_stops_on_lint(self):
        s = load(CR122); s["note"]["signers"].pop()
        r = run([os.path.join(TOOLS, "build_note_letter.py"), self.dump(s, "s.json"), self.tmp, "X"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("note.signers: signer chain", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "X_Note_and_Letter.docx")))

    def test_build_study_lint(self):
        p = self.dump(study(skip=(1,)), "st.json"); out = os.path.join(self.tmp, "X_Study.docx")
        r = run([os.path.join(TOOLS, "build_study.py"), p, out])
        self.assertEqual(r.returncode, 1); self.assertIn("भाग 1 missing", r.stdout)
        self.assertFalse(os.path.exists(out))
        r = run([os.path.join(TOOLS, "build_study.py"), p, out, "--allow-missing-part1"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertTrue(os.path.exists(out))
        os.remove(out)
        r = run([os.path.join(TOOLS, "build_study.py"), p, out], env=dict(ENV, STUDY_ALLOW_MISSING_PART1="1"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
