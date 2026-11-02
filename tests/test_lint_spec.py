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


def raw_load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def load(p):
    return raw_load(p)


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
            if "note" not in raw_load(p):   # 02.11.2026: order-only examples (ORDER_*) — tools/lint_order.py, tests/test_build_order.py
                continue
            with self.subTest(spec=os.path.basename(p)):
                self.assertEqual(L.lint_spec(raw_load(p)), [])
                self.assertEqual(L.lint_warnings(raw_load(p)), [])   # approved samples: no WARN-level finding
                r = run([os.path.join(TOOLS, "lint_spec.py"), p])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.stdout.strip().splitlines(), ["LINT OK"])

    # ---- §4.18 language (01.11.2026) ----
    def test_sau_not_shrimati(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " सौ. एन. जी. बारई"),
                 "'सौ.' ऐवजी 'श्रीमती'", "note.paras[0]")

    def test_unspaced_initials(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " श्री.आर.टी.लाखे"),
                 "'श्री.' नंतर एक जागा", "note.paras[0]")

    def test_quoted_text_is_exempt(self):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][0] += " अर्जात “सौ.बारई यांनी तात्काळ” असे नमूद आहे."
        self.assertFalse([p for p in L.lint_spec(s) if "§4.18" in p])

    def test_letter_tatkal(self):
        def f(s):
            s["letter"]["intro"] = s["letter"]["intro"].replace("शासनास", "शासनास तात्काळ")
        self.bad(self.s122, f, "'तात्काळ / तातडीने", "letter.intro")

    def test_letter_request_form(self):
        def f(s):
            s["letter"]["intro"] = s["letter"]["intro"].replace(", ही विनंती", "")
        self.bad(self.s122, f, "ही विनंती", "letter.intro")

    def test_letter_urgent_words(self):
        def f(s):
            s["letter"]["intro"] = s["letter"]["intro"].replace("शासनास", "शासनास त्वरित")
        self.bad(self.s122, f, "'लवकरात लवकर' वापरा", "letter.intro")

    def test_letter_bare_command(self):
        def f(s):
            s["letter"]["points"] = ["आदेशाची प्रत सादर करावी."]
        self.bad(self.s122, f, "थेट आदेशात्मक शेवट", "letter.points[0]")

    def test_kai_space(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " कै.मिलिंद"),
                 "'कै.' नंतर एक जागा", "note.paras[0]")

    # ---- §4.19 Marathi forms (01.11.2026, मराठी भाषा विभाग GR दि. 10.11.2022) ----
    def add0(self, txt):
        return lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + txt)

    def test_colon_dash(self):
        self.bad(self.s122, self.add0(" तपशील खालीलप्रमाणे आहे.:-"), "'.:-' ऐवजी ':-'", "note.paras[0]")

    def test_karun_spelling(self):
        self.bad(self.s122, self.add0(" अर्ज सादर करुन"), "'करुन' ऐवजी 'करून'", "note.paras[0]")
        self.bad(self.s122, lambda s: s["letter"].__setitem__("intro", s["letter"]["intro"].replace("करून", "करुन")),
                 "'करुन' ऐवजी 'करून'", "letter.intro")

    def test_prarup_spelling(self):
        def f(s):
            i = max(i for i, x in enumerate(s["note"]["paras"]) if isinstance(x, str))
            s["note"]["paras"][i] = s["note"]["paras"][i].replace("प्रारूप", "प्रारुप")
        probs = self.bad(self.s122, f, "'प्रारुप' ऐवजी 'प्रारूप'")
        self.assertTrue(any("last para" in p for p in probs), probs)

    def test_abbrev_space_date(self):
        self.bad(self.s122, self.add0(" दि.17.09.2026 रोजी"), "संक्षेपचिन्हानंतर एक जागा", "note.paras[0]")

    def test_abbrev_space_kra(self):
        self.bad(self.s122, self.add0(" पत्र क्र.108 अन्वये"), "संक्षेपचिन्हानंतर एक जागा", "note.paras[0]")
        self.bad(self.s122, self.add0(" (प्र.क्र. 21/2024)"), "संक्षेपचिन्हानंतर एक जागा", "note.paras[0]")
        self.bad(self.s122, lambda s: s["letter"]["refs"].__setitem__(0, s["letter"]["refs"][0] + " दि.01.01.2026"),
                 "संक्षेपचिन्हानंतर एक जागा", "letter.refs[0]")

    def test_missing_info_para_form(self):
        def f(s):
            i = next(i for i, x in enumerate(s["note"]["paras"]) if isinstance(x, str) and x.startswith(L.MISSING_HEAD))
            s["note"]["paras"][i] = s["note"]["paras"][i].replace(L.MISSING_HEAD + ":-", L.MISSING_HEAD + " -")
        self.bad(self.s122, f, "missing-info para")

    def test_419_exclusions_ok(self):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][0] += (" पत्र क्र.संकिर्ण-2026/226/प्र.क्र.131/का.6, क्र.वेतन-1311/प्र.क्र.17/सेवा-3 (पृ.6/प.वि.):-"
                                  " (पृ.6/प.वि.:-) दर 1.5 टक्के, सांकेतांक 202211101530029233 (पॅकेज PDF पृ. 3).")
        self.assertFalse([p for p in L.lint_spec(s) if "§4.19" in p])
        self.assertEqual(s["note"]["signers"], L.SIGNERS)

    def test_419_quoted_text_is_exempt(self):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][0] += " नियमात “दि.17.09.2026 रोजी पत्र क्र.108 चे प्रारुप तपासणी करुन खालीलप्रमाणे.:-” असे आहे."
        s["related"][0]["text"].append("जसाच्या तसा उतारा: दि.01.01.2020 पासून सादर करुन.:-")
        self.assertFalse([p for p in L.lint_spec(s) if "§4.19" in p])

    def test_fix_lang(self):
        t = "दि.17.09.2026 च्या पत्र क्र.108 नुसार (प्र.क्र. 21/2024) प्रारुप तयार करुन, खालीलप्रमाणे आहे.:- “दि.01.01.2020 करुन.:-” क्र.बी-4/36/2010 (पृ.6/प.वि.).:-"
        self.assertEqual(L.fix_lang(t), "दि. 17.09.2026 च्या पत्र क्र. 108 नुसार (प्र. क्र. 21/2024) प्रारूप तयार करून, खालीलप्रमाणे आहे:- "
                                        "“दि.01.01.2020 करुन.:-” क्र.बी-4/36/2010 (पृ.6/प.वि.):-")
        self.assertEqual(L.lang_hits(L.fix_lang(t)), [])

    # ---- §4.21–§4.24 (Abhi, 02.11.2026) ----
    def test_reminder(self):
        s = load(CR122)
        s["letter"]["reminder"] = 1
        P = L.lint_spec(s)
        self.assertTrue(any("स्मरणपत्र (§4.21)" in p and p.startswith("letter.refs[0]") for p in P), P)
        self.assertTrue(any("स्मरणपत्र (§4.21)" in p and p.startswith("letter.intro") for p in P), P)
        s["letter"]["refs"] = ["या कार्यासनाचे समक्रमांकाचे पत्र दि. 20.10.2026"]
        s["letter"]["intro"] = ("उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, संदर्भाधीन पत्रान्वये मागविण्यात "
                                "आलेली माहिती अद्याप अप्राप्त आहे. सदर माहिती लवकरात लवकर शासनास उपलब्ध करून देण्यात यावी, ही विनंती.")
        s["letter"]["points"] = []
        self.assertEqual([p for p in L.lint_spec(s) if "§4.21" in p], [])

    def test_copy_line_via_high_court(self):
        s = load(CR122)
        self.assertEqual([p for p in L.lint_spec(s) if "§4.22" in p], [], "approved sample has the copy line")
        s["letter"].pop("copies")
        P = [p for p in L.lint_spec(s) if "§4.22" in p]
        self.assertEqual(len(P), 1); self.assertIn("जिल्हा व सत्र न्यायालय, औरंगाबाद यांना आवश्यक कार्यवाहीसाठी", P[0])
        s["letter"]["to"] = ["प्रमुख जिल्हा व सत्र न्यायाधीश,", "जिल्हा व सत्र न्यायालय,", "औरंगाबाद."]
        self.assertEqual([p for p in L.lint_spec(s) if "§4.22" in p], [], "direct letter to the District Judge: no copy line")

    def test_ma_rule(self):
        cases = {"उच्च न्यायालयाच्या पत्रानुसार": True, "मा. उच्च न्यायालयाच्या": False, "मा.उच्च न्यायालय, मुंबई": False,
                 "प्रबंधक, उच्च न्यायालय (अपील शाखा), मुंबई": False, "मुख्य न्यायमूर्ती यांनी": True, "मा. मुख्य न्यायमूर्ती": False,
                 "न्यायमूर्ती श्री. अ": True, "“उच्च न्यायालयाने”": False, "प्रशासकीय न्यायाधीश समिती": True,
                 "मा. मुंबई उच्च न्यायालयाच्या": False}
        for t, bad in cases.items():
            self.assertEqual(bool(L.ma_hits(t)), bad, t)
            self.assertEqual(L.ma_hits(L.fix_ma(t)), [], t)
        self.assertEqual(L.fix_ma("मुंबई उच्च न्यायालयाच्या संघटनेने"), "मा. मुंबई उच्च न्यायालयाच्या संघटनेने")
        s = load(CR122)
        s["note"]["paras"].insert(0, "उच्च न्यायालयाच्या दि. 01.01.2026 च्या पत्रानुसार माहिती प्राप्त आहे.")
        self.assertTrue(any("§4.23" in p and p.startswith("note.paras[0]") for p in L.lint_spec(s)))
        self.assertEqual([p for p in L.lint_spec(load(CR122)) if p.startswith("letter.to") and "§4.23" in p], [], "addressee block excepted")

    def test_shuddhipatrak(self):
        self.assertTrue(any("§4.24" in m for m in L.style_hits("शासन शुद्धीपत्रकानुसार")))
        self.assertFalse(any("§4.24" in m for m in L.style_hits("शासन शुद्धिपत्रकानुसार")))
        self.assertFalse(any("§4.24" in m for m in L.style_hits("“शासन शुद्धीपत्रक”")), "quotes verbatim")

    # ---- §4.20 letter table = data only (02.11.2026) ----
    def test_doc_in_letter_table(self):
        s131 = load(next(p for p in SPECS if os.path.basename(p).startswith("CR131_")))
        for word in ("आदेशाची प्रत", "छायांकित प्रती", "कार्यालय प्रमुखांचे प्रमाणपत्र", "कार्यभार हस्तांतरण अहवाल"):
            with self.subTest(word=word):
                self.bad(s131, lambda s: s["letter"]["points"][0]["table"][1].__setitem__(1, "दिनांक व " + word),
                         "कागदपत्रे तक्त्यात नको", "letter.points[0].table[1][1]")

    def test_doc_list_after_table_ok(self):
        s131 = load(next(p for p in SPECS if os.path.basename(p).startswith("CR131_")))
        pts = s131["letter"]["points"]
        self.assertIsInstance(pts[0], dict)
        self.assertEqual(pts[1].strip(), L.DOC_INTRO)
        self.assertTrue(all(isinstance(x, str) and L.DOC_RE.search(x) for x in pts[2:]))
        s = copy.deepcopy(s131)
        s["letter"]["points"][0]["table"][1][1] = "प्रत्यक्ष स्वीकारल्याचा दिनांक (प्रतिनियुक्ती आदेशात “आदेशाची प्रत” नमूद)"
        self.assertFalse([p for p in L.lint_spec(s) if "§4.20" in p])

    def test_mixed_points_render_in_order(self):
        import docx
        out = tempfile.mkdtemp(prefix="cr131_")
        s131 = os.path.join(out, "cr131.json")
        with open(s131, "w", encoding="utf-8") as f:
            json.dump(load(next(p for p in SPECS if os.path.basename(p).startswith("CR131_"))), f, ensure_ascii=False)
        try:
            r = run([os.path.join(TOOLS, "build_note_letter.py"), s131, out, "T131"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            d = docx.Document(os.path.join(out, "T131_Note_and_Letter.docx"))
            body = [el for el in d.element.body if el.tag.endswith("}p") or el.tag.endswith("}tbl")]
            text = lambda el: "".join(t.text or "" for t in el.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
            i = next(k for k, el in enumerate(body) if text(el).strip() == L.DOC_INTRO)
            prev = next(el for el in reversed(body[:i]) if el.tag.endswith("}tbl") or text(el).strip())
            self.assertTrue(prev.tag.endswith("}tbl"), "document list must follow the letter table")
            self.assertIn("पद प्रथम रिक्त झाल्याचा दिनांक", text(prev))
            items = [text(el).strip() for el in body[i + 1:i + 6]]
            self.assertTrue(items[0].startswith("1)") and items[4].startswith("5)"), items)
        finally:
            shutil.rmtree(out, ignore_errors=True)

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


class LintSpelling(unittest.TestCase):
    """02.11.2026: error level 'ध्द' / 'करुन' / 'प्रारुप' / 'अनुसरुन'; WARN level L11–L14 (STYLE_RESEARCH_LANG §5.2)."""
    @classmethod
    def setUpClass(cls):
        cls.s122 = load(CR122)

    def spec(self, para=None, intro=None, subject=None, related_text=None, related_heading=None):
        s = copy.deepcopy(self.s122)
        if para is not None: s["note"]["paras"][0] += para
        if intro is not None: s["letter"]["intro"] = s["letter"]["intro"].replace("सदर प्रकरणी", "सदर प्रकरणी " + intro)
        if subject is not None: s["letter"]["subject"] = subject
        if related_text is not None: s["related"][0]["text"] = [related_text]
        if related_heading is not None: s["related"][0]["heading"] += related_heading
        return s

    def errs(self, s, needle):
        return [p for p in L.lint_spec(s) if needle in p]

    def warns(self, s, needle=""):
        return [p for p in L.lint_warnings(s) if needle in p]

    # ---- ERROR level ----
    def test_errors_all_four(self):
        for bad, good, needle in (("शुध्द", "शुद्ध", "'ध्द'"), ("करुन", "करून", "'करुन'"), ("प्रारुप", "प्रारूप", "'प्रारुप'"),
                                  ("अनुसरुन", "अनुसरून", "'अनुसरुन'")):
            with self.subTest(word=bad):
                self.assertTrue([p for p in self.errs(self.spec(para=f" {bad}"), needle) if p.startswith("note.paras[0]:")])
                self.assertTrue([p for p in self.errs(self.spec(intro=bad), needle) if p.startswith("letter.intro:")])
                self.assertFalse(self.errs(self.spec(para=f" {good}", intro=good), needle))
                self.assertFalse(self.errs(self.spec(para=f" “{bad}”", intro=f"“{bad}”"), needle))   # quotes exempt

    def test_anusarun_error(self):
        s = self.spec(para=" पत्रास अनुसरुन सादर.")
        self.assertIn("note.paras[0]: शुद्धलेखन — 'अनुसरुन' ऐवजी 'अनुसरून' (§4.19)", L.lint_spec(s))
        self.assertEqual(L.fix_lang("पत्रास अनुसरुन “अनुसरुन”"), "पत्रास अनुसरून “अनुसरुन”")

    def test_anusarun_quoted_and_related_text_exempt(self):
        s = self.spec(para=" “पत्रास अनुसरुन सादर”", related_text="“…पत्रास अनुसरुन…” अनुसरुन")
        self.assertFalse(self.errs(s, "'अनुसरुन'"))
        s = self.spec(related_heading=" — पत्रास अनुसरुन")   # related heading is the Section's own text: checked
        self.assertTrue([p for p in self.errs(s, "'अनुसरुन'") if p.startswith("related[0].heading")])

    # ---- WARN level ----
    def test_l11_rule12(self):
        for w, fx in (("करणेसाठी", "करण्यासाठी"), ("देणेबाबत", "देण्याबाबत"), ("पाठविणेकरिता", "पाठविण्याकरिता")):
            with self.subTest(word=w):
                self.assertEqual(self.warns(self.spec(para=f" अर्ज {w} सादर.")),
                                 [f"note.paras[0]: शुद्धलेखन नियम 12 — '{w}' ऐवजी '{fx}' (प्रस्तावातील विषय-रूप असले तरी "
                                  f"सूचना) (STYLE_RESEARCH_LANG §5.2)"])
                self.assertFalse(self.warns(self.spec(para=f" अर्ज {fx} सादर.")))
        self.assertTrue(self.warns(self.spec(subject="वेतननिश्चिती मिळणेबाबत."), "letter.subject: शुद्धलेखन नियम 12"))
        self.assertFalse(self.warns(self.spec(para=" देणे व घेणे बाबत")))

    def test_l12_rule14(self):
        self.assertTrue(self.warns(self.spec(para=" श्री. ____, एम्.ए., पीएच्.डी."), "'एम्.' ऐवजी 'एम.'"))
        self.assertTrue(self.warns(self.spec(para=" बी्.कॉम"), "नियम 14"))
        self.assertFalse(self.warns(self.spec(para=" श्री. ____, एम.ए., पीएच.डी., क्र. 108, दि. 17.09.2026")))

    def test_l13_rule3(self):
        for w, fx in (("त्याने", "त्यांनी"), ("तिने", "त्यांनी"), ("त्याचे", "त्यांचे"), ("तिला", "त्यांना"),
                      ("त्याच्या", "त्यांच्या")):
            with self.subTest(word=w):
                self.assertTrue(self.warns(self.spec(para=f" {w} अर्ज केला."), f"'{w}' ऐवजी '{fx}'"))
        self.assertFalse(self.warns(self.spec(para=" त्यांनी अर्ज केला; त्यांच्या सेवेचा; त्याच्यासाठी नाही")))

    def test_l14_anusvar(self):
        self.assertTrue(self.warns(self.spec(intro="आपणास"), "'आपणास' ऐवजी 'आपणांस'"))
        self.assertTrue(self.warns(self.spec(para=" श्री. ____ यांनां कळविले."), "'यांनां' ऐवजी 'यांना'"))
        self.assertFalse(self.warns(self.spec(para=" श्री. ____ यांना आपणांस कळविले.")))

    def test_warn_quotes_related_exempt(self):
        s = self.spec(para=" “करणेसाठी त्याने आपणास एम्.ए.”", related_text="करणेबाबत त्याने आपणास",
                      related_heading=" — लागू करणेबाबत (जसाच्या तसा)")
        self.assertEqual(L.lint_warnings(s), [])

    def test_warnings_are_not_errors(self):
        s = self.spec(para=" करणेसाठी त्याने आपणास एम्.ए.")
        self.assertEqual(L.lint_spec(s), L.lint_spec(self.s122))
        self.assertEqual(len(L.lint_warnings(s)), 4)

    def test_fix_warn(self):
        t = "अर्ज करणेसाठी त्याने आपणास यांनां एम्.ए. “करणेबाबत त्याने”"
        self.assertEqual(L.fix_warn(t), "अर्ज करण्यासाठी त्यांनी आपणांस यांना एम.ए. “करणेबाबत त्याने”")
        self.assertEqual(L.warn_hits(L.fix_warn(t)), [])
        self.assertEqual(L.warn_hits("“करणेबाबत त्याने”"), [])


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

    def test_cli_warn_exit_0(self):
        s = load(CR122); s["note"]["paras"][0] += " अर्ज करणेसाठी सादर."
        r = run([os.path.join(TOOLS, "lint_spec.py"), self.dump(s, "w.json")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARN note.paras[0]: शुद्धलेखन नियम 12 — 'करणेसाठी' ऐवजी 'करण्यासाठी'", r.stdout)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "LINT OK")
        s["note"]["signers"].pop()   # an error + a warning -> exit 1, both printed
        r = run([os.path.join(TOOLS, "lint_spec.py"), self.dump(s, "w2.json")])
        self.assertEqual(r.returncode, 1); self.assertIn("WARN note.paras[0]", r.stdout); self.assertNotIn("LINT OK", r.stdout)

    def test_cli_anusarun_exit_1(self):
        s = load(CR122); s["note"]["paras"][0] += " पत्रास अनुसरुन सादर."
        r = run([os.path.join(TOOLS, "lint_spec.py"), self.dump(s, "a.json")])
        self.assertEqual(r.returncode, 1); self.assertIn("note.paras[0]: शुद्धलेखन — 'अनुसरुन'", r.stdout)

    def test_cli_study(self):
        p = self.dump(study(skip=(1,)), "st.json"); cr122 = self.dump(load(CR122), "cr122.json")
        r = run([os.path.join(TOOLS, "lint_spec.py"), cr122, "--study", p])
        self.assertEqual(r.returncode, 1); self.assertIn("भाग 1 missing", r.stdout)
        r = run([os.path.join(TOOLS, "lint_spec.py"), cr122, "--study", p, "--allow-missing-part1"])
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


class LintOrderParawise(unittest.TestCase):
    """02.11.2026: order-draft last para (docs/COURT_AND_ORDERS_RESEARCH.md R3 (c), B7) and the lazy hooks to
    tools/lint_order.py / tools/lint_parawise.py for the optional spec keys "order" / "parawise"."""
    def setUp(self):
        self.s122 = load(CR122)

    def with_last(self, txt):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][max(i for i, x in enumerate(s["note"]["paras"]) if isinstance(x, str))] = txt
        return s

    def test_order_draft_last_para_forms(self):
        for kind in ("शासन निर्णयाचे प्रारूप", "शुद्धिपत्रकाचे प्रारूप", "शासन शुद्धिपत्रकाचे प्रारूप", "परिपत्रकाचे प्रारूप",
                     "ज्ञापनाचे प्रारूप", "अधिसूचनेचे प्रारूप", "अधिसूचनेची मराठी व इंग्रजी प्रारूपे"):
            for tail in ("", " मान्य झाल्यास निर्गमित करण्यात येईल.", " मान्य झाल्यास शासन निर्णय निर्गमित करण्यात येईल."):
                t = f"सबब, वित्त विभागाच्या उपरोक्त अभिप्रायानुसार {kind} पृ.      /प.वि. वर मान्यतेस्तव सादर.{tail}"
                self.assertEqual(L.lint_spec(self.with_last(t)), [], t)

    def test_order_draft_last_para_still_strict(self):
        for t in ("सबब, प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर.", "सबब, शासन निर्णयाचे प्रारूप सादर.",
                  "सबब, शासन निर्णयाचे प्रारुप पृ.  /प.वि. वर मान्यतेस्तव सादर.",
                  "सबब, अधिसूचनेची प्रारूपे पृ.  /प.वि. वर मान्यतेस्तव सादर.",
                  "सबब, शासन निर्णयाचे प्रारूप पृ.  /प.वि. वर सादर.",
                  "सबब, शासन निर्णयाचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर. कृपया पाहावे."):
            self.assertTrue(any("last para" in p for p in L.lint_spec(self.with_last(t))), t)

    def test_existing_forms_unchanged(self):
        for p in SPECS:
            if os.path.basename(p).startswith("CR"):
                self.assertEqual(L.lint_spec(load(p)), [], p)

    def test_extras_absent_keys(self):
        self.assertEqual(L.lint_extras(self.s122), ([], []))

    def test_extras_missing_module_is_warning(self):
        s = copy.deepcopy(self.s122); s["order"] = {"type": "gr"}
        old = L.EXTRA_LINTS
        try:
            L.EXTRA_LINTS = (("order", "no_such_lint_module_xyz", ()),)
            probs, warns = L.lint_extras(s)
        finally:
            L.EXTRA_LINTS = old
        self.assertEqual(probs, [])
        self.assertTrue(any("not available" in w for w in warns), warns)

    def test_extras_called_with_problems_and_warnings(self):
        import types
        mod = types.ModuleType("fake_lint_xyz")
        mod.fake_lint_xyz = lambda spec: ["order.title: problem"]
        mod.fake_warn_xyz = lambda spec: ["order.title: warn"]
        sys.modules["fake_lint_xyz"] = mod
        old = L.EXTRA_LINTS
        try:
            L.EXTRA_LINTS = (("order", "fake_lint_xyz", ("fake_warn_xyz",)),)
            s = copy.deepcopy(self.s122); s["order"] = {"type": "gr"}
            self.assertEqual(L.lint_extras(s), (["order.title: problem"], ["order.title: warn"]))
            mod.fake_lint_xyz = lambda spec: 1 / 0
            probs, _ = L.lint_extras(s)
            self.assertTrue(any("crashed" in p for p in probs), probs)
        finally:
            L.EXTRA_LINTS = old
            sys.modules.pop("fake_lint_xyz", None)

    def test_cli_runs_extra_lint(self):
        d = tempfile.mkdtemp()
        try:
            s = copy.deepcopy(self.s122); s["parawise"] = {"rows": []}
            sp = os.path.join(d, "spec.json")
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False)
            r = run([os.path.join(TOOLS, "lint_spec.py"), sp])
            # with tools/lint_parawise.py present its lines (if any) are added; absent -> one WARN, exit 0
            if not os.path.exists(os.path.join(TOOLS, "lint_parawise.py")):
                self.assertEqual(r.returncode, 0, r.stdout)
                self.assertIn("WARN parawise", r.stdout)
            self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
            self.assertNotIn("Traceback", r.stderr)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
