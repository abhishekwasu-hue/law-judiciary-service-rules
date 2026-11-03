"""Tests for tools/study_warnings.py (Abhi 03.11.2026: the run warnings go into the Study, end of भाग 7, not the noting).
Run: python3 -m unittest tests.test_study_warnings -v
Fixture = the GOOD fixture of tests/test_verify_outputs.py (CR122 note + Study + small package)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import docx
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_verify_outputs as TV  # noqa: E402

sys.path.insert(0, TV.TOOLS)
import study_warnings as SW  # noqa: E402
from lint_spec import part_no  # noqa: E402

WARNS = [
    "पडताळणी अपूर्ण — उतारे: संबंधित माहिती 2 मूळ GR शी जुळत नाही",
    "मॉडेल: पत्र → Opus 5 (पूर्वी Haiku 5)",
    "मॉडेल: खर्च — Opus 5 $1.20",
    "खर्च अंदाजापेक्षा जास्त — माहितीसाठी (खर्च $2.00 / अंदाज $1.50)",
    "मुख्य AI (gemini) सुरू झाले नाही — अभ्यास Claude ने केला.",
    "अंतिम पडताळणी (Opus) मान्यता नाही — पत्रातील तक्ता",
    "पडताळणी अपूर्ण — उतारे: संबंधित माहिती 2 मूळ GR शी जुळत नाही",   # duplicate
    "भाग 1 तपासणी मर्यादित प्रयत्नांनंतरही अपूर्ण",                      # starts with "भाग" -> must not become a heading
]
KEPT = [WARNS[0], WARNS[5], WARNS[7]]


def paras(path):
    return [p for p in docx.Document(path).element.body.iter(qn("w:p"))]


def text(p):
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


@unittest.skipIf(TV.FONTFILE is None, "no Devanagari font for the page stamps")
class StudyWarnings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="studywarn_")
        with open(TV.SPEC, encoding="utf-8") as f:
            spec = json.load(f)
        cls.good = os.path.join(cls.tmp, "good"); os.makedirs(cls.good)
        TV.build_note(spec, cls.good)
        TV.build_study(TV.study_spec(spec), cls.good)
        TV.build_pkg(os.path.join(cls.good, TV.PKGNAME))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def case(self, name):
        d = os.path.join(self.tmp, name)
        shutil.copytree(self.good, d)
        return d, os.path.join(d, f"{TV.PRE}_Study.docx")

    def section(self, path):
        ts = [text(p) for p in paras(path)]
        i = ts.index(SW.HEADING)
        return ts, i, [t for t in ts[i + 1:] if t.strip()]

    def test_lines_filter(self):
        self.assertEqual(SW.study_lines(WARNS), KEPT)
        self.assertEqual(SW.study_lines([]), [])
        self.assertEqual(SW.study_lines(None), [])

    def test_append_end_of_part7(self):
        d, st = self.case("append")
        SW.append(st, WARNS)
        ts, i, items = self.section(st)
        self.assertEqual(items, [f"{n}. {t}" for n, t in enumerate(KEPT, 1)])
        h7 = max(k for k, t in enumerate(ts) if part_no(t) == 7)
        self.assertGreater(i, h7, "section is after the भाग 7 heading")
        self.assertFalse([t for t in ts if part_no(t) == 8], "no भाग 8 heading")
        self.assertFalse([t for t in ts[i:] if part_no(t) is not None], "no part heading inside the section")
        body = docx.Document(st).element.body
        self.assertEqual(body[-1].tag, qn("w:sectPr"), "body sectPr stays last")
        joined = "\n".join(ts)
        for x in ("मॉडेल:", "खर्च", "मुख्य AI"):
            self.assertNotIn(x, joined, f"owner-only line '{x}' not in the Study")

    def test_idempotent(self):
        d, st = self.case("idem")
        SW.append(st, WARNS)
        SW.append(st, WARNS[:1])
        ts, i, items = self.section(st)
        self.assertEqual(ts.count(SW.HEADING), 1)
        self.assertEqual(items, [f"1. {WARNS[0]}"])
        SW.append(st, [])
        ts, i, items = self.section(st)
        self.assertEqual(ts.count(SW.HEADING), 1)
        self.assertEqual(items, [SW.NONE_LINE])

    def test_no_warnings_line(self):
        d, st = self.case("none")
        SW.append(st, ["मॉडेल: खर्च — Opus 5 $1.00"])
        _, _, items = self.section(st)
        self.assertEqual(items, ["कोणताही इशारा नाही."])

    def test_fonts_and_verify(self):
        d, st = self.case("verify")
        SW.append(st, WARNS)
        for r in docx.Document(st).element.body.iter(qn("w:r")):
            if not "".join(t.text or "" for t in r.iter(qn("w:t"))).strip():
                continue
            rf = r.find(qn("w:rPr") + "/" + qn("w:rFonts"))
            self.assertIsNotNone(rf)
            for k in ("ascii", "hAnsi", "cs", "eastAsia"):
                self.assertEqual(rf.get(qn("w:" + k)), "DVOT-SurekhMR")
        rc, out = self.run_verify(d)
        self.assertIn("OK: Study headings भाग 0-7", out)
        self.assertIn("OK: Study fonts", out)
        self.assertIn("OK: Study metadata (no tool / AI trace)", out)
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)

    def run_verify(self, d):
        r = TV.py(os.path.join(TV.TOOLS, "verify_outputs.py"), d, TV.PRE, os.path.join(d, TV.PKGNAME), str(TV.NPP))
        return r.returncode, r.stdout + r.stderr

    def test_cli_stdin(self):
        d, st = self.case("cli")
        r = subprocess.run([sys.executable, os.path.join(TV.TOOLS, "study_warnings.py"), "append", st, "-"],
                           input=json.dumps({"warnings": WARNS}, ensure_ascii=False), capture_output=True, text=True,
                           encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("3 warning(s)", r.stdout)
        _, _, items = self.section(st)
        self.assertEqual(len(items), 3)


if __name__ == "__main__":
    unittest.main()
