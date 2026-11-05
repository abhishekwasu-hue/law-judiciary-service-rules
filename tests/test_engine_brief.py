"""Drift checks for tools/ENGINE_BRIEF.md (the compact rule brief the engine reads instead of the full rule files).
Run: PYTHONIOENCODING=utf-8 py -m unittest tests.test_engine_brief
"""
import ast
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF = os.path.join(ROOT, "tools", "ENGINE_BRIEF.md")
LINT = os.path.join(ROOT, "tools", "lint_spec.py")
MAX_BYTES = 31744  # 05.11.2026 (audit R-F10/F11/F19, C-B): + the last-para forms lint accepts and the Finance route as lint reads it, rule58-only parawise fields, fixer cap; ~470 bytes compacted elsewhere, no rule dropped (31 KiB); 04.11.2026: merge with [I4.32] court note + [I4.33] new draft types (fits 30 KiB); 03.11.2026: +[I4.34] relevance + एकसंध flow (C32, owner on CR132 run 2: "vinakarna upyogache naslele sandarbh ... flow tutato"; [I4.29]/[I4.31] could not be cut without loss) (30 KiB); 03.11.2026: +[I4.29] detailed-note standard (12 elements) + research step (C30; owner accepted detail over brevity: "note khupch short jhali detail asayla pahije") (28 KiB); 03.11.2026: +[I4.28] ticked drafts (C28, owner instruction "user multiple option choose karel"; no existing rule could be cut without loss) (24 KiB); 02.11.2026: +section 0 "never stop — deliver with warnings" (caps, terminal states, C R fallback; A1 audit) (23 KiB); 01.11.2026: +§4.18 language rule, +§4.19 Marathi forms (14 KiB); 02.11.2026: +Marathi language rules section, owner instruction (18.5 KiB); 02.11.2026: +section 4b court cases / order drafts, owner instruction (21 KiB)


def lint_constant(name):
    """Literal value of a top-level constant in tools/lint_spec.py (parsed, not imported)."""
    with open(LINT, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in tools/lint_spec.py")


class EngineBriefTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BRIEF, "rb") as f:
            cls.raw = f.read()
        cls.text = cls.raw.decode("utf-8")

    def test_size(self):
        self.assertLessEqual(len(self.raw), MAX_BYTES, f"brief is {len(self.raw)} bytes")

    def test_every_section4_item_tagged(self):
        # audit 05.11 R-F8: the item numbers come from INSTRUCTIONS.md §4 itself (not a fixed 1-20 range)
        with open(os.path.join(ROOT, "INSTRUCTIONS.md"), encoding="utf-8") as f:
            ins = f.read()
        start = ins.index("\n## ४.")
        sec = ins[start:ins.index("\n## ", start + 5)]
        ids = [int(m.group(1)) for m in re.finditer(r"(?m)^(\d+)\.\s", sec)]
        self.assertGreaterEqual(len(ids), 35)
        missing = [n for n in ids if f"[I4.{n}]" not in self.text]
        self.assertEqual(missing, [], f"missing tags: {missing}")
        unknown = sorted({int(n) for n in re.findall(r"\[I4\.(\d+)\]", self.text)} - set(ids))
        self.assertEqual(unknown, [], f"tags without an INSTRUCTIONS item: {unknown}")

    def test_source_tags_present(self):
        for tag in ("[I1.1]", "[I1.2]", "[I1.3]", "[I1.4]", "[I3]", "[I8]",
                    "[SOP1]", "[SOP2]", "[SOP3]", "[SOP4]", "[SOP5]", "[SOP6]", "[SOP7]"):
            self.assertIn(tag, self.text)

    def test_banned_words_verbatim(self):
        banned = lint_constant("BANNED")
        self.assertTrue(banned)
        missing = [w for w in banned if f'"{w}"' not in self.text]
        self.assertEqual(missing, [], f"banned words missing: {missing}")

    def test_signers_verbatim(self):
        # C30 (03.11.2026): lint_spec.py takes SIGNERS / AMS from the default desk profile tools/desks/law-desk6.json
        # (no longer literals); the brief states the default (law-desk6) chain
        import json
        with open(os.path.join(ROOT, "tools", "desks", "law-desk6.json"), encoding="utf-8") as f:
            desk = json.load(f)
        signers, ams = desk["signers"], desk["finance_signer"]
        self.assertEqual(len(signers), 4)
        for s in signers + [ams]:
            self.assertIn(s, self.text)
        pos = [self.text.index(s) for s in signers]
        self.assertEqual(pos, sorted(pos), "signers out of order")

    def test_study_headings(self):
        part_re = re.compile(r"\s*भाग\s*([0-9०-९])(?![0-9०-९])")  # = tools/lint_spec.py PART_RE (verify's check)
        found = set()
        for m in re.finditer(r'"(भाग [0-7] — [^"]+)"', self.text):
            mt = part_re.match(m.group(1))
            if mt:
                found.add(int(mt.group(1)))
        self.assertEqual(found, set(range(8)), f"headings found: {sorted(found)}")
        self.assertIn("भाग 0 — वरिष्ठांसाठी ब्रीफिंग", self.text)

    def test_letter_and_ref_phrases(self):
        for p in ("आपला,", "प्रत : निवड नस्ती", "( राजेश वडनेरकर )", "अवर सचिव ,महाराष्ट्र शासन",
                  "संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6", "lnjd.desk6-mh@mah.gov.in",
                  "(पॅकेज PDF पृ. N)", "(पॅकेज PDF मध्ये नाही)", "पृ.N/प.वि.", "वाचन अपूर्ण / उपलब्ध नाही",
                  "संबंधित माहिती (संदर्भासाठी)", "--original-name", "tools/lint_spec.py"):
            self.assertIn(p, self.text)

    def test_last_para_forms_match_lint(self):
        # audit 05.11 R-F10/F11: the brief names the Finance route and the extra last-para forms as lint accepts them
        for p in ("वित्त विभागाच्या मान्यतेस्तव", "अभिप्रायास्तव", "सहमतीस्तव", "वित्त विभागास विनंती",
                  "नस्ती बंद करण्यास मान्यता असावी", "LAST_FORMS"):
            self.assertIn(p, self.text)
        lint = open(LINT, encoding="utf-8").read()
        for p in ("सहमतीस्तव", "अभिप्रायास्तव", "LAST_FORMS", "नस्ती"):
            self.assertIn(p, lint)

    def test_ends_with_doubt_line(self):
        self.assertTrue(self.text.rstrip().endswith("On any doubt, read the full source file named in the tag."))


if __name__ == "__main__":
    unittest.main()
