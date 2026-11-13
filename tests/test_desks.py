"""C30 part B (03.11.2026): desk profiles tools/desks/<id>.json (spec "desk", default law-desk6).
Run: python3 -m pytest -q tests/test_desks.py
- profiles load and are well formed; law-desk6 = the Desk-6 constants of tools/lint_spec.py / build_order.py
- default unchanged: a sample built without "desk" and with "desk": "law-desk6" gives the same document.xml
- hte-mashi5 (Higher & Technical Education, desk मशि-5): note + letter + order build with the profile's header, letterhead
  lines, signer chain, blank phone / e-mail ("____"), blank signature "(          )", copy line; lint OK; lint / verify
  refuse the Desk-6 chain / ref no. for it (and the other way round)
- engine: case.json desk from cases.desk (missing column / null / bad value -> law-desk6)"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

import docx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk  # noqa: E402
import lint_spec as L  # noqa: E402
import lint_order  # noqa: E402
import build_order  # noqa: E402
import test_verify_outputs as TV  # noqa: E402 — fixture helpers (Study, package PDF)

SPEC122 = os.path.join(ROOT, "samples", "specs", "CR122_2026_pay-fixation_info-letter.json")
SPEC66 = os.path.join(ROOT, "samples", "specs", "CR66_2026_finance-approval_no-letter.json")
SPEC_GR = os.path.join(ROOT, "samples", "specs", "ORDER_gr_example.json")
HTE = "hte-mashi5"
HTE_SIGNERS = ["का.अ. (मशि-5) (          )", "अ.स. (मशि-5) (          )", "उ.स. (मशि-5) (          )",
               "सह सचिव (उच्च शिक्षण) (          )", "मा. अ.मु.स. (उ.व तं.शि.)"]
HTE_REF = "____-2026/प्र.क्र.____/मशि-5"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def hte_spec(base=SPEC122):
    s = load(base)
    s["desk"] = HTE
    s["note"]["signers"] = list(HTE_SIGNERS)
    if s.get("letter"):
        s["letter"]["ref_no"] = HTE_REF
    return s


def py(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", env=ENV)


def write(spec, d, name="_spec.json"):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return p


def paras(path):
    d = docx.Document(path)
    out = []
    for el in d.element.body.iter():
        if el.tag.endswith("}p"):
            out.append("".join(t.text or "" for t in el.iter() if t.tag.endswith("}t")))
    return out


class Profiles(unittest.TestCase):
    def test_ids_and_shape(self):
        ids = desk.desk_ids()
        self.assertIn("law-desk6", ids)
        self.assertIn(HTE, ids)
        for i in ids:
            p = desk.load_desk(i)
            self.assertEqual(desk.profile_problems(p), [], i)
            self.assertEqual(p["id"], i)

    def test_default_is_desk6_constants(self):
        p = desk.load_desk(None)
        self.assertEqual(p["id"], "law-desk6")
        self.assertEqual(p["signers"], L.SIGNERS)
        self.assertEqual(p["finance_signer"], L.AMS)
        self.assertEqual(p["letter"]["email"], "lnjd.desk6-mh@mah.gov.in")
        self.assertEqual(p["note_header"], "विधि व न्याय विभाग/का.6")
        self.assertTrue(desk.letter_ref_re(p).fullmatch("संकिर्ण-2026/931/प्र.क्र.122/का.6"))
        self.assertTrue(desk.letter_ref_re(p).fullmatch("संकीर्ण-2026/____/प्र.क्र.____/का.6"))
        self.assertEqual(build_order.DEPT, "विधि व न्याय विभाग,")
        self.assertEqual(build_order.SIGNER_DEFAULT, {"name": "( राजेश वडनेरकर )", "designation": "अवर सचिव, महाराष्ट्र शासन"})
        self.assertEqual(desk.contact_line(p), "दूरध्वनी क्र. :- ०२२-२२793230\t\t             Email ID :- lnjd.desk6-mh@mah.gov.in")

    def test_hte_values(self):
        p = desk.load_desk(HTE)
        self.assertEqual(p["signers"], HTE_SIGNERS)
        self.assertEqual(p["finance_signer"], "मा. अ.मु.स. (वित्त)")
        self.assertEqual(p["note_header"], "उ.व तं.शि.वि. / मशि-5")
        self.assertEqual(desk.contact_line(p), "दूरध्वनी क्र. :- ____\t\t             Email ID :- ____")
        self.assertEqual(desk.letter_end_lines(p), ["(          )", "अवर सचिव, महाराष्ट्र शासन", "प्रत : 1. निवड नस्ती (मशि-5)"])
        self.assertTrue(desk.letter_ref_re(p).fullmatch(HTE_REF))
        self.assertTrue(desk.letter_ref_re(p).fullmatch("संकीर्ण-2026/प्र.क्र.12/मशि-5"))
        self.assertFalse(desk.letter_ref_re(p).fullmatch("संकिर्ण-2026/931/प्र.क्र.122/का.6"))

    def test_unknown_desk(self):
        with self.assertRaises(ValueError):
            desk.load_desk("no-such-desk")
        with self.assertRaises(ValueError):
            desk.load_desk("../etc")
        s = load(SPEC122); s["desk"] = "no-such-desk"
        self.assertTrue(any(x.startswith("desk: desk profile") for x in L.lint_spec(s)))
        o = load(SPEC_GR); o["desk"] = "no-such-desk"
        self.assertTrue(any("desk profile" in x for x in lint_order.lint_order(o)))

    def test_detect(self):
        self.assertEqual(desk.detect_desk(["", "उ.व तं.शि.वि. / मशि-5"]), HTE)
        self.assertEqual(desk.detect_desk(["विधि व न्याय विभाग/का.6"]), "law-desk6")
        self.assertIsNone(desk.detect_desk(["something else"]))


class Lint(unittest.TestCase):
    def test_hte_sample(self):
        p = os.path.join(ROOT, "samples", "specs", "HTE_2026_overpayment-waiver_finance-concurrence.json")
        if not os.path.exists(p):
            self.skipTest("HTE sample not present")
        s = load(p)
        self.assertEqual(L.lint_spec(s), [])
        self.assertEqual(lint_order.lint_order(s), [])

    def test_ma_case_title_party(self):   # §4.23 not on a party name in "<A> विरुद्ध <B>" (C30, 03.11.2026)
        for t in ("सिव्हील अपील क्र. 3500/2006 (पंजाब व हरियाणा उच्च न्यायालय व इतर विरुद्ध जगदेव सिंग) मध्ये निर्णय आहे.",
                  "रिट याचिका (अ. ब. क विरुद्ध उच्च न्यायालय, मुंबई व इतर) मध्ये निर्णय आहे.",
                  "Civil Appeal (High Court of Punjab v. Jagdev Singh) — पंजाब व हरियाणा उच्च न्यायालय vs जगदेव सिंग प्रकरण."):
            self.assertEqual(L.ma_hits(t), [], t)
        # still an error: the court itself (no title), and a title elsewhere in another bracket
        self.assertTrue(L.ma_hits("उच्च न्यायालयाने आदेश दिले आहेत."))
        self.assertTrue(L.ma_hits("उच्च न्यायालयाने रिट याचिका क्र. 1/2020 (अ विरुद्ध ब) मध्ये आदेश दिले आहेत."))

    def test_intimation_letter_needs_no_request(self):   # §4.28 (अ): status points only state facts
        L0 = {"points": ["1. प्रस्ताव वित्त विभागाच्या सहमतीसाठी सादर करण्यात आला आहे.", "2. निर्णय प्राप्त झाल्यानंतर अवगत करण्यात येईल."]}
        intro = "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, प्रकरणाची सद्यस्थिती पुढीलप्रमाणे आहे:-"
        self.assertFalse(L.requests_info(L0, intro))
        self.assertTrue(L.requests_info({"points": [{"table": [["अ.क्र.", "माहिती"], ["1", ""]]}]}, intro))
        self.assertTrue(L.requests_info({"points": ["1) सेवापुस्तकाची प्रत उपलब्ध करून देण्यात यावी."]}, intro))
        self.assertTrue(L.requests_info({"points": ["1) माहिती कळविण्यात यावी."]}, intro))
        self.assertTrue(L.requests_info({"points": [], "reminder": 1}, intro))
        self.assertTrue(L.requests_info({}, "उपरोक्त … माहिती उपलब्ध करून देण्यात यावी, ही विनंती:-"))

    def test_desk6_samples_unchanged(self):
        for f in (SPEC122, SPEC66):
            self.assertEqual(L.lint_spec(load(f)), [], f)

    def test_hte_ok(self):
        self.assertEqual(L.lint_spec(hte_spec()), [])

    def test_hte_with_desk6_chain_or_ref(self):
        s = hte_spec(); s["note"]["signers"] = list(L.SIGNERS)
        self.assertTrue(any("signer chain" in x for x in L.lint_spec(s)))
        s = hte_spec(); s["letter"]["ref_no"] = "संकिर्ण-2026/931/प्र.क्र.122/का.6"
        probs = L.lint_spec(s)
        self.assertTrue(any("ref_no" in x and "मशि-5" in x for x in probs), probs)

    def test_desk6_with_hte_chain(self):
        s = load(SPEC122); s["note"]["signers"] = list(HTE_SIGNERS)
        self.assertTrue(any("signer chain" in x for x in L.lint_spec(s)))
        s = load(SPEC122); s["letter"]["ref_no"] = HTE_REF
        self.assertTrue(any("ref_no" in x for x in L.lint_spec(s)))

    def test_hte_finance_route(self):
        s = hte_spec(SPEC66)   # CR66: no letter, last para to Finance, chain + finance signer
        s["note"]["signers"] = HTE_SIGNERS + ["मा. अ.मु.स. (वित्त)"]
        self.assertEqual(L.lint_spec(s), [])
        s["note"]["signers"] = HTE_SIGNERS + ["अ.मु.स. (वित्त)"]   # the Desk-6 form is wrong for this desk
        self.assertTrue(any("signer chain" in x for x in L.lint_spec(s)))
        s["note"]["signers"] = list(HTE_SIGNERS)                   # Finance route without the finance signer
        self.assertTrue(any("Finance last para" in x for x in L.lint_spec(s)))


def hte_order():
    s = load(SPEC_GR)
    s = {k: v for k, v in s.items() if k != "_comment"}
    s["desk"] = HTE
    s["note"]["signers"] = list(HTE_SIGNERS)
    s["order"]["ref_no"] = HTE_REF
    s["order"]["copies"] = [c for c in s["order"]["copies"][:-1]] + ["निवड नस्ती (मशि-5)"]
    s["order"].pop("signer", None)
    return s


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="desks_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def build_nl(self, spec, sub, pre="CR122"):
        d = os.path.join(self.tmp, sub); os.makedirs(d, exist_ok=True)
        r = py(os.path.join(TOOLS, "build_note_letter.py"), write(spec, d), d, pre)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for x in ("_spec.json", f"{pre}_Note_and_Letter.pdf"):
            if os.path.exists(os.path.join(d, x)):
                os.remove(os.path.join(d, x))
        return d, os.path.join(d, f"{pre}_Note_and_Letter.docx")

    def test_default_unchanged(self):
        _, a = self.build_nl(load(SPEC122), "def_a")
        s = load(SPEC122); s["desk"] = "law-desk6"
        _, b = self.build_nl(s, "def_b")
        xa = zipfile.ZipFile(a).read("word/document.xml"); xb = zipfile.ZipFile(b).read("word/document.xml")
        self.assertEqual(xa, xb)
        t = "\n".join(paras(a))
        for line in ("विधि व न्याय विभाग/का.6", "Email ID :- lnjd.desk6-mh@mah.gov.in", "( राजेश वडनेरकर )",
                     "अवर सचिव ,महाराष्ट्र शासन", "प्रत :", "1. निवड नस्ती", "हुतात्मा राजगुरु चौक, मादाम कामा मार्ग"):   # §4.38 copies numbered
            self.assertIn(line, t)

    def test_hte_note_letter(self):
        _, f = self.build_nl(hte_spec(), "hte")
        ps = [p.strip() for p in paras(f)]
        t = "\n".join(ps)
        self.assertEqual(next(p for p in ps if p), "उ.व तं.शि.वि. / मशि-5")
        for line in ("उच्च व तंत्र शिक्षण विभाग,", "मंत्रालय विस्तार भवन, मुंबई 400 032.", "दूरध्वनी क्र. :- ____",
                     "Email ID :- ____", "(          )", "अवर सचिव, महाराष्ट्र शासन", "निवड नस्ती (मशि-5)",
                     HTE_REF, "महाराष्ट्र शासन", "आपला,"):
            self.assertIn(line, t)
        for s in HTE_SIGNERS:
            self.assertIn(s, ps)
        for bad in ("वडनेरकर", "lnjd", "विधि व न्याय विभाग/", "का.6", "हुतात्मा राजगुरु"):
            self.assertNotIn(bad, t)

    @unittest.skipIf(TV.FONTFILE is None, "no Devanagari font for the page stamps")
    def test_hte_verify(self):
        d, _ = self.build_nl(hte_spec(), "hte_v")
        TV.build_study(TV.study_spec(hte_spec()), d)
        TV.build_pkg(os.path.join(d, TV.PKGNAME))
        args = [os.path.join(TOOLS, "verify_outputs.py"), d, "CR122", os.path.join(d, TV.PKGNAME), str(TV.NPP)]
        r = py(*args)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out)
        self.assertIn("ALL OK", out)
        self.assertIn("desk profile — hte-mashi5", out)
        r = py(*args, "--desk", HTE)
        self.assertEqual(r.returncode, 0, r.stdout)
        r = py(*args, "--desk", "law-desk6")   # Desk-6 rules on an HTE file: chain, ref no., e-mail, ending fail
        out = r.stdout
        self.assertNotEqual(r.returncode, 0, out)
        fails = [ln for ln in out.splitlines() if ln.startswith("FAIL:")]
        for needle in ("note signer chain", "letter ref no.", "letter ending"):
            self.assertTrue(any(needle in ln for ln in fails), f"{needle}:\n{out}")

    @unittest.skipIf(TV.FONTFILE is None, "no Devanagari font for the page stamps")
    def test_desk6_verify_wrong_desk(self):
        d, _ = self.build_nl(load(SPEC122), "d6_v")
        TV.build_study(TV.study_spec(load(SPEC122)), d)
        TV.build_pkg(os.path.join(d, TV.PKGNAME))
        args = [os.path.join(TOOLS, "verify_outputs.py"), d, "CR122", os.path.join(d, TV.PKGNAME), str(TV.NPP)]
        r = py(*args)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("desk profile — law-desk6", r.stdout)
        r = py(*args, "--desk", HTE)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("FAIL: note signer chain", r.stdout)

    def test_hte_order(self):
        s = hte_order()
        self.assertEqual(lint_order.lint_order(s), [])
        d = os.path.join(self.tmp, "ord"); os.makedirs(d, exist_ok=True)
        r = py(os.path.join(TOOLS, "build_order.py"), write(s, d), d, "HTE")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = "\n".join(p.strip() for p in paras(os.path.join(d, "HTE_Order_Draft.docx")))
        for line in ("उच्च व तंत्र शिक्षण विभाग", "मंत्रालय विस्तार भवन, मुंबई 400 032", "शासन निर्णय क्रमांक :- " + HTE_REF,
                     "(          )", "अवर सचिव, महाराष्ट्र शासन", "निवड नस्ती (मशि-5)"):
            self.assertIn(line, t)
        head = t.split("वाचा :-")[0]   # heading block (the sample's copy list names the Law dept. as an addressee)
        self.assertNotIn("विधि व न्याय विभाग", head)
        for bad in ("वडनेरकर", "हुतात्मा राजगुरु"):
            self.assertNotIn(bad, t)

    def test_hte_order_lint_desk6_ref(self):
        s = hte_order(); s["order"]["ref_no"] = "संकिर्ण-2026/____/प्र.क्र.____/का.6"
        probs = lint_order.lint_order(s)
        self.assertTrue(any("order.ref_no" in x and "मशि-5" in x for x in probs), probs)
        s = load(SPEC_GR); s["order"]["ref_no"] = HTE_REF   # Desk-6 order with an HTE number
        self.assertTrue(any("order.ref_no" in x for x in lint_order.lint_order(s)))

    def test_hte_notification_blanks(self):
        o = {"type": "notification", "desk": HTE}
        self.assertEqual(build_order.signer(o), {"name": "(          )", "designation": "____"})
        self.assertEqual(build_order.signer({"type": "gr"}), build_order.SIGNER_DEFAULT)


class Engine(unittest.TestCase):
    def test_case_desk(self):
        os.environ.setdefault("SUPABASE_URL", "http://localhost")
        import engine_supabase as E
        self.assertEqual(E.case_desk({}), "law-desk6")              # column missing (migration not applied)
        self.assertEqual(E.case_desk({"desk": None}), "law-desk6")
        self.assertEqual(E.case_desk({"desk": ""}), "law-desk6")
        self.assertEqual(E.case_desk({"desk": HTE}), HTE)
        self.assertEqual(E.case_desk({"desk": "../x"}), "law-desk6")
        self.assertEqual(E.DESK_ID_RE.pattern, desk.ID_RE.pattern)


if __name__ == "__main__":
    unittest.main()
