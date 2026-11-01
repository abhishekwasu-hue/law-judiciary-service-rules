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
MAX_BYTES = 13 * 1024  # 01.11.2026: +§4.18 language rule


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
        missing = [n for n in range(1, 19) if f"[I4.{n}]" not in self.text]
        self.assertEqual(missing, [], f"missing tags: {missing}")

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
        signers = lint_constant("SIGNERS")
        self.assertEqual(len(signers), 4)
        for s in signers + [lint_constant("AMS")]:
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
                  "संकिर्ण-2026/<file no>/प्र.क्र.<n>/का.6", "lnjd.desk6-mh@mah.gov.in",
                  "(पॅकेज PDF पृ. N)", "(पॅकेज PDF मध्ये नाही)", "पृ.N/प.वि.", "वाचन अपूर्ण / उपलब्ध नाही",
                  "संबंधित माहिती (संदर्भासाठी)", "--original-name", "tools/lint_spec.py"):
            self.assertIn(p, self.text)

    def test_ends_with_doubt_line(self):
        self.assertTrue(self.text.rstrip().endswith("On any doubt, read the full source file named in the tag."))


if __name__ == "__main__":
    unittest.main()
