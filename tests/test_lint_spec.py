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

    # ---- §4.31 missing information in ONE para (Abhi 03.11.2026) ----
    def miss_idx(self, s):
        return next(i for i, x in enumerate(s["note"]["paras"]) if isinstance(x, str) and x.startswith(L.MISSING_HEAD))

    def test_431_remark_phrases(self):
        for t in ("प्रती प्रस्तावासोबत जोडलेल्या नाहीत.", "प्रस्तावात नमूद नाही", "प्रस्तावात अशी वस्तुस्थिती नमूद नाही.",
                  "अर्जाची प्रत प्रस्तावासोबत नाही.", "प्रती प्रस्तावासोबत नाहीत", "आदेश उपलब्ध नाही.", "आदेशाची प्रत नाही.",
                  "अहवाल सादर केलेला नाही.", "प्रमाणपत्र सादर करण्यात आलेले नाही.", "कागदपत्रे जोडण्यात आलेली नाहीत.",
                  "क्रमांक नमूद केलेला नाही."):
            with self.subTest(t=t):
                self.assertTrue(L.MISSING_REMARK_RE.search(t), t)
        for t in ("प्रत्यक्ष कार्यभार स्वीकारला.", "पदोन्नती आदेशात विकल्पाबाबत नमूद नसल्याचे अर्जात नमूद आहे.", "____",
                  "उपलब्ध नसलेली माहिती", "सदर निवेदन शासनास प्राप्त झालेले नाही."):
            with self.subTest(ok=t):
                self.assertFalse(L.MISSING_REMARK_RE.search(t), t)

    def test_431_remark_in_other_para(self):
        self.bad(self.s122, lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " अर्जाची प्रत प्रस्तावासोबत नाही."),
                 "missing-info remark", "note.paras[0]")

    def test_431_remark_in_facts_table(self):
        self.bad(self.s122, lambda s: s["note"]["paras"][2]["table"][7].__setitem__(2, "प्रस्तावात नमूद नाही"),
                 "missing-info remark", "note.paras[2].table[7][2]")

    def test_431_remark_in_sub_first_closing(self):
        self.bad(self.s122, lambda s: s["note"].__setitem__("sub", {"1": ["(1) पाच पत्रांच्या प्रती जोडलेल्या नाहीत."]}),
                 "missing-info remark", "note.sub.1[0]")
        self.bad(self.s122, lambda s: s["note"].__setitem__("first", s["note"]["first"].replace("सादर.", "सादर. प्रत नाही. सादर.")),
                 "missing-info remark", "note.first")

    def test_431_condition_table_and_fact_summary(self):
        def f(s):
            s["note"]["paras"][4:4] = ["उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-",
                                        {"table": [["अट", "प्रस्तावातील स्थिती", "पृ."], ["(iv) …", "प्रस्तावात अशी वस्तुस्थिती नमूद नाही.", ""]]}]
        probs = self.bad(self.s122, f, "missing-info remark", "note.paras[5].table[1][1]")
        self.assertTrue(all("§4.31" in p for p in probs if "missing-info remark" in p))

    def test_431_two_missing_paras(self):
        def f(s):
            s["note"]["paras"].insert(1, "प्रस्तावासोबत खालील कागदपत्रे उपलब्ध नाहीत:- (1) आदेशाची प्रत.")
        self.bad(self.s122, f, "more than one")

    def test_431_inside_the_para_and_its_table_ok(self):
        def f(s):
            i = self.miss_idx(s)
            s["note"]["paras"][i] += " (4) अर्जाची प्रत प्रस्तावासोबत नाही."
            s["note"]["paras"].insert(i + 1, {"table": [["अ.क्र.", "माहिती"], ["1", "आदेशाची प्रत नाही; अहवाल सादर केलेला नाही"]]})
            s["note"].setdefault("sub", {})[str(i)] = ["(अ) प्रमाणपत्र जोडलेले नाही."]
        s = copy.deepcopy(self.s122); f(s)
        self.assertEqual([p for p in L.lint_spec(s) if "4.31" in p], [])
        self.assertEqual([w for w in L.lint_warnings(s) if "4.31" in w], [])

    def test_431_quoted_remark_ok(self):
        s = copy.deepcopy(self.s122)
        s["note"]["paras"][0] += " अर्जात “नामांकन उपलब्ध नाही” असे नमूद आहे."
        self.assertEqual([p for p in L.lint_spec(s) if "4.31" in p], [])

    def test_431_placement_warning(self):
        s = copy.deepcopy(self.s122)
        i = self.miss_idx(s); s["note"]["paras"].insert(1, s["note"]["paras"].pop(i))
        self.assertEqual([p for p in L.lint_spec(s) if "4.31" in p], [])
        self.assertTrue(any("just before the last" in w for w in L.lint_warnings(s)), L.lint_warnings(s))

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
                 "draft word — 'पॅकेज'", "note.paras[0]")

    def test_package_pdf_in_letter(self):
        self.bad(self.s122, lambda s: s["letter"].__setitem__("intro", s["letter"]["intro"] + " (पॅकेज PDF पृ. 3)"),
                 "draft word — 'पॅकेज'", "letter.intro")

    # ---- C27 (02.11.2026): no package / warning / AI word in the drafts; related source "(पृ.N/प.वि.)" ----
    def test_package_marker_in_related_source_fails(self):
        for marker in (" (पॅकेज PDF पृ. 3)", " (पॅकेज PDF मध्ये नाही)"):
            with self.subTest(marker=marker):
                probs = self.bad(self.s122, lambda s: s["related"][0].__setitem__("source", "परिच्छेद 2" + marker),
                                 "draft word — 'पॅकेज'", "related[0].source")
                self.assertTrue(any(p.startswith("related[0].source: page marker") for p in probs), probs)

    def test_package_in_related_heading_and_quote_fails(self):
        self.bad(self.s122, lambda s: s["related"][0].__setitem__("heading", s["related"][0]["heading"] + " (पॅकेज)"),
                 "draft word — 'पॅकेज'", "related[0].heading")
        self.bad(self.s122, self.add0(" “पॅकेज PDF”"), "draft word — 'पॅकेज'", "note.paras[0]")   # quotes do not exempt "पॅकेज"
        self.bad(self.s122, lambda s: s["related"][0]["text"].append("उतारा (पॅकेज PDF पृ. 3)"),
                 "draft word — 'पॅकेज PDF'", f"related[0].text[{len(self.s122['related'][0]['text'])}]")

    def test_related_source_marker_forms_ok(self):
        for src in ("दि. 06.11.1982, परि. 2 (पृ.6/प.वि.)", "नियम 13 (ब) (पृ.१७,१८/प.वि.)", "परि. 3 (पृ.6-7/प.वि.)",
                    "परि. 3 (पृ. 6 / प.वि.).", "शासन निर्णय पृ. 2-3, परि. 4 (पृ.9-10/प.वि.)", "शासन निर्णय दि. 06.11.1982, परि. 2"):
            with self.subTest(src=src):
                s = copy.deepcopy(self.s122); s["related"][0]["source"] = src
                self.assertEqual(L.lint_spec(s, pages=20), [])
                self.assertEqual(L.related_source_problems(src), [])

    def test_related_source_marker_not_at_end_or_twice(self):
        for src in ("(पृ.6/प.वि.) परि. 2", "परि. 2, पृ.6/प.वि.", "परि. 2 (पृ.6/प.वि.) (पृ.7/प.वि.)", "परि. 2 (पृ.  /प.वि.)"):
            with self.subTest(src=src):
                self.bad(self.s122, lambda s: s["related"][0].__setitem__("source", src), "page marker", "related[0].source")

    def test_related_source_page_range(self):
        s = copy.deepcopy(self.s122); s["related"][0]["source"] = "परि. 2 (पृ.25/प.वि.)"
        self.assertTrue(any("related[0].source" in p and "page 25 outside package" in p for p in L.lint_spec(s, pages=20)))

    def test_draft_words_each_fail(self):
        words = ["इशारा", "पडताळणी अपूर्ण", "मागवावे", "वाचन अपूर्ण", "अस्पष्ट", "पडताळलेले नाही", "टीप : तपासावे",
                 "टीप:", "warning", "TODO", "package PDF", "AI", "Claude", "Anthropic", "मॉडेल", "model", "स्वयंचलित",
                 "automatic", "engine", "प्रणालीने तयार", "generated", "LLM", "GPT", "Gemini",
                 "स्रोत:", "जसाच्या तसा", "जसेच्या तसे", "जशीच्या तशी"]   # last four: Abhi 03.11.2026
        for w in words:
            with self.subTest(word=w):
                self.bad(self.s122, self.add0(f" {w} "), "draft word", "note.paras[0]")
                self.bad(self.s122, lambda s: s["letter"].__setitem__("subject", s["letter"]["subject"] + f" {w}"),
                         "draft word", "letter.subject")
                self.bad(self.s122, lambda s: s["related"][0].__setitem__("heading", s["related"][0]["heading"] + f" {w}"),
                         "draft word", "related[0].heading")
                self.bad(self.s122, lambda s: s["related"][0].__setitem__("source", f"{w} " + s["related"][0]["source"]),
                         "draft word", "related[0].source")
                # verbatim: inside “…” quotes of own text and in the related extract text — exempt
                q = copy.deepcopy(self.s122); q["note"]["paras"][0] += f" “{w}”"; q["related"][0]["text"].append(f"उतारा {w}")
                self.assertFalse([p for p in L.lint_spec(q) if "draft word" in p])

    def test_tell_words(self):
        """lead (AI_TELLS): em dash, arrows, web addresses, "छापील पृ." in own text (not in quotes / extracts)."""
        for w in ("—", "→", "https://gr.maharashtra.gov.in", "www.example.com", "छापील पृ. 3"):
            with self.subTest(w=w):
                self.bad(self.s122, self.add0(f" अ {w} ब"), f"draft word — '", "note.paras[0]")
                self.bad(self.s122, lambda s: s["related"][0].__setitem__("source", f"परि. 2 {w}"), "draft word", "related[0].source")
                q = copy.deepcopy(self.s122); q["note"]["paras"][0] += f" “अ {w} ब”"; q["related"][0]["text"].append(f"उतारा {w}")
                self.assertFalse([p for p in L.lint_spec(q) if "draft word" in p])
        self.assertEqual(L.draft_word_hits("www.maharashtra.gov.in या संकेतस्थळावर"), [])   # official GR website line

    def test_draft_words_no_false_hits(self):
        for t in ("AIR 1990 SC 123", "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-", "MAIN", "remodelled", "टीपणी", "____"):
            with self.subTest(t=t):
                self.assertEqual(L.draft_word_hits(t), [])

    def test_shuddhipatrak_in_related_heading(self):
        self.bad(self.s122, lambda s: s["related"][0].__setitem__("heading", "वित्त विभाग, शासन शुद्धीपत्रक दि. 01.06.2015"),
                 "शुद्धिपत्रक", "related[0].heading")
        q = copy.deepcopy(self.s122); q["related"][0]["text"].append("शासन शुध्दीपत्रक (जसाच्या तसा)")
        self.assertFalse([p for p in L.lint_spec(q) if "§4.24" in p])

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


class AuditA1Fixes(unittest.TestCase):
    """02.11.2026 (independent audit A1): "मा." phrases, REF_NO spellings, last-para routes (H5), अ.मु.स. (वित्त) route
    (H6, §8.3), "ही विनंती" only in request letters, "ध्द" in names, L11 warn-only."""
    def setUp(self):
        self.s122 = load(CR122); self.s66 = load(CR66)

    def with_last(self, base, txt, ams=False):
        s = copy.deepcopy(base)
        s["note"]["paras"][max(i for i, x in enumerate(s["note"]["paras"]) if isinstance(x, str))] = txt
        s["note"]["signers"] = list(L.SIGNERS) + ([L.AMS] if ams else [])
        return s

    # ---- 1. "मा." ----
    def test_ma_phrases(self):
        cases = {"मा. प्रशासकीय न्यायमूर्ती समितीने": False, "मा.प्रशासकीय न्यायमूर्ती समिती": False,
                 "प्रशासकीय न्यायमूर्ती समिती": True, "मा. मुख्य न्यायमूर्ती यांनी": False,
                 "निवृत्त न्यायमूर्ती श्री. अ. ब. क": False, "सेवानिवृत्त न्यायमूर्ती यांची समिती": False, "निवृत्त मुख्य न्यायमूर्ती श्री. क": False,
                 "प्रबंधक (अपील शाखा), उच्च न्यायालय, मुंबई": False, "सहायक सरकारी वकील, उच्च न्यायालय, खंडपीठ औरंगाबाद": False,
                 "प्रबंधक (कार्मिक), उच्च न्यायालय (अपील शाखा), मुंबई": False, "उच्च न्यायालय, अपील शाखा, मुंबई": False,
                 "उच्च न्यायालय, खंडपीठ नागपूर": False, "उच्च न्यायालयाने कळविले": True,
                 "मा.प्रशासकीय मा. न्यायमूर्ती समितीने": True, "मा. मा. उच्च न्यायालय": True}
        for t, bad in cases.items():
            with self.subTest(t=t):
                self.assertEqual(bool(L.ma_hits(t)), bad, (t, L.ma_hits(t)))
                fx = L.fix_ma(t)
                self.assertEqual(L.ma_hits(fx), [], fx)
                self.assertNotIn("मा. मा.", fx); self.assertNotIn("प्रशासकीय मा.", fx)
        self.assertEqual(L.fix_ma("प्रशासकीय न्यायमूर्ती समितीने"), "मा. प्रशासकीय न्यायमूर्ती समितीने")
        self.assertEqual(L.fix_ma("मा. प्रशासकीय न्यायमूर्ती समितीने"), "मा. प्रशासकीय न्यायमूर्ती समितीने")
        self.assertEqual(L.fix_ma("मा.प्रशासकीय मा. न्यायमूर्ती समितीने"), "मा.प्रशासकीय न्यायमूर्ती समितीने")

    def test_ma_letter_address_fields_exempt(self):
        s = copy.deepcopy(self.s122)
        s["letter"]["refs"] = ["सहायक सरकारी वकील, उच्च न्यायालय, खंडपीठ औरंगाबाद यांचे पत्र क्र. 12, दि. 01.01.2026"]
        s["letter"]["copies"] = ["प्रबंधक, उच्च न्यायालय यांना माहितीसाठी"]
        self.assertEqual([p for p in L.lint_spec(s) if "§4.23" in p], [])
        s["letter"]["intro"] = s["letter"]["intro"].replace("उपरोक्त विषयाबाबत", "उपरोक्त विषयाबाबत उच्च न्यायालयाच्या")
        self.assertTrue(any(p.startswith("letter.intro") and "§4.23" in p for p in L.lint_spec(s)))

    def test_cr66_sample_text_repaired(self):
        txt = json.dumps(self.s66, ensure_ascii=False)
        self.assertNotIn("प्रशासकीय मा.", txt); self.assertNotIn("मा. मा.", txt)
        self.assertEqual(txt.count("मा. प्रशासकीय न्यायमूर्ती समिती"), 3)

    # ---- 2. REF_NO ----
    def test_ref_no_both_spellings(self):
        for rn in ("संकिर्ण-2026/979/प्र.क्र.130/का.6", "संकीर्ण-2026/979/प्र.क्र.130/का.6", "संकीर्ण-2027/____/प्र.क्र.____/का.6"):
            s = copy.deepcopy(self.s122); s["letter"]["ref_no"] = rn
            self.assertEqual([p for p in L.lint_spec(s) if "ref no." in p], [], rn)
        for rn in ("संकिरण-2026/979/प्र.क्र.130/का.6", "संकीर्ण-2026/प्र.क्र.130/का.6", "संकीर्ण-26/979/प्र.क्र.130/का.6"):
            s = copy.deepcopy(self.s122); s["letter"]["ref_no"] = rn
            self.assertTrue(any("ref no." in p for p in L.lint_spec(s)), rn)

    # ---- 3/4. last-para routes + अ.मु.स. (वित्त) ----
    ROUTES = {   # text -> AMS needed
        "सबब, उपरोक्त प्रस्ताव सामान्य प्रशासन विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे.": False,
        "सबब, उपरोक्त प्रस्ताव सामान्य प्रशासन विभागाच्या अभिप्रायार्थ सादर.": False,
        "सबब, उपरोक्त प्रस्ताव सामान्य प्रशासन विभागाच्या अभिप्रायास्तव सादर करण्यात येत आहे.": False,
        "सबब, उपरोक्त प्रस्ताव वित्त विभागाच्या अभिप्रायास्तव सादर करण्यात येत आहे.": True,
        "सबब, उपरोक्त प्रस्ताव वित्त विभागाच्या अभिप्रायार्थ सादर.": True,
        "सबब, प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर.": True,
        "सबब, सदर प्रस्ताव सामान्य प्रशासन विभाग व वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे.": True,
        "सबब, सदर प्रस्ताव सार्वजनिक आरोग्य विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे.": True,
        "प्रस्तुत प्रकरणातील उक्त वस्तुस्थिती विचारात घेता, श्रीमती ____ यांच्या वैद्यकीय खर्चाच्या प्रतिपूर्तीच्या प्रस्तावास "
        "“एक विशेष बाब” म्हणून मंजुरी देण्याकरिता सार्वजनिक आरोग्य विभागास विनंती करण्यास हरकत नसावी. मान्यतेस्तव सादर.": True,
        "सबब, श्री. ____ यांच्या प्रस्तावास मंजुरी देण्याकरिता सार्वजनिक आरोग्य विभागास पुन:श्च विनंती करण्यास हरकत नसावी.": True,
        "सबब, श्री. ____ यांना दि. 01.01.2026 पासून वेतनवाढ मंजूर करण्याचा प्रस्ताव मान्यतेस्तव सादर.": False,
        "सबब, सदर प्रकरणी पुढील कार्यवाही आवश्यक नसल्याने नस्ती बंद करण्यास मान्यता असावी.": False,
        "सबब, सदर प्रकरण नस्तीबंद करण्यास मान्यतेस्तव सादर.": False,
        "सबब, वित्त विभागाच्या अभिप्रायानुसार प्रबंधक, उच्च न्यायालय (अपील शाखा), मुंबई यांना कळविण्याबाबतच्या पत्राचे प्रारूप "
        "पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल.": False,
        "सबब, वित्त विभागाच्या सहमतीनुसार निर्गमित करावयाच्या शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.": False,
    }

    def test_last_para_routes(self):
        for t, ams in self.ROUTES.items():
            with self.subTest(t=t[:60]):
                self.assertEqual(L.lint_spec(self.with_last(self.s122, t, ams)), [], t)
                wrong = [p for p in L.lint_spec(self.with_last(self.s122, t, not ams)) if "Finance last para" in p]
                self.assertTrue(wrong, f"AMS {'absent' if ams else 'present'} must fail: {t}")

    def test_last_para_bare_closing(self):
        s = self.with_last(self.s122, "सबब, श्री. ____ यांच्या प्रस्तावास मंजुरी देण्याकरिता सार्वजनिक आरोग्य विभागास विनंती "
                                      "करण्यास हरकत नसावी.", True)
        s["note"]["closing"] = "मान्यतेस्तव सादर."
        self.assertEqual(L.lint_spec(s), [])

    def test_last_para_negatives(self):
        for t in ("सबब, कृपया आदेश द्यावेत.", "सबब, प्रस्ताव सामान्य प्रशासन विभागाकडे पाठवावा.",
                  "सबब, पत्राचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर.", "सबब, प्रस्ताव मान्यतेस्तव ठेवला आहे.",
                  "प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे.", "सबब, नस्ती बंद करावी.",
                  "सबब, सार्वजनिक आरोग्य विभागास विनंती करावी."):
            with self.subTest(t=t):
                self.assertTrue(any("last para" in p for p in L.lint_spec(self.with_last(self.s122, t))), t)

    def test_finance_route_helper(self):
        self.assertTrue(L.finance_route("… वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."))
        self.assertTrue(L.finance_route("… सार्वजनिक आरोग्य विभागास विनंती करण्यास हरकत नसावी."))
        self.assertFalse(L.finance_route("सबब, वित्त विभागाच्या दि. 11.09.2019 च्या शासन निर्णयानुसार … पत्राचे प्रारूप …"))
        self.assertFalse(L.finance_route("“वित्त विभागाच्या मान्यतेस्तव सादर”"))   # quoted text is not the route

    # ---- 5. "ही विनंती" only in request letters ----
    def test_reply_letter_without_request(self):
        s = copy.deepcopy(self.s122)
        s["letter"]["intro"] = ("उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, वित्त विभागाने सदर "
                                "प्रस्तावास सहमती दर्शविलेली नाही.")
        s["letter"]["points"] = []
        self.assertEqual([p for p in L.lint_spec(s) if "letter.intro" in p], [])
        s["letter"]["intro"] = ("उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, खालील माहिती "
                                "उपलब्ध करून देण्यात यावी.")
        self.assertTrue(any(L.REQUEST in p for p in L.lint_spec(s)))
        s = copy.deepcopy(self.s122); s["letter"]["intro"] = s["letter"]["intro"].replace(", ही विनंती", "")
        self.assertTrue(any(L.REQUEST in p for p in L.lint_spec(s)), "points present -> request form needed")

    # ---- 6. "ध्द" ----
    def test_dhd_names_and_quotes_exempt(self):
        D = "'ध्द'"
        for t in ("श्री. अ. ब. बुध्दे यांनी अर्ज सादर केला आहे.", "श्रीमती क. शुध्दे, लिपिक", "कै. म. बुध्दे यांच्या पत्नीस",
                  "डॉ. बुध्दे यांचे प्रमाणपत्र", "(श्री. बुध्दे)", "“शुध्द प्रत”"):
            self.assertFalse(any(D in m for m in L.style_hits(t)), t)
        for t in ("शुध्द प्रत", "श्री. अ. बुध्दे यांनी शुध्द प्रत सादर केली.", "विषय : सुधारित वेतन (शुध्द)"):
            self.assertTrue(any(D in m for m in L.style_hits(t)), t)
        s = copy.deepcopy(self.s122); s["note"]["paras"].insert(0, "श्री. र. ना. बुध्दे यांनी दि. 01.01.2026 रोजी अर्ज सादर केला आहे.")
        self.assertEqual(L.lint_spec(s), [])

    # ---- 7. L11 on a letter subject: WARN only ----
    def test_l11_subject_warn_only(self):
        s = copy.deepcopy(self.s122); s["letter"]["subject"] = "विशेष वेतन मिळणेबाबत."
        self.assertEqual(L.lint_spec(s), [])
        self.assertTrue(any(w.startswith("letter.subject") and "णेबाबत" in w for w in L.lint_warnings(s)))


if __name__ == "__main__":
    unittest.main()
