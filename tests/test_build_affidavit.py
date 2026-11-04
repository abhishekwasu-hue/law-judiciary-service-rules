"""Tests for tools/build_affidavit.py and tools/lint_affidavit.py (affidavit in reply, Bombay HC Appellate Side).
Run: python3 -m pytest -q tests/test_build_affidavit.py"""
import copy
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import lint_affidavit as LA  # noqa: E402
import lint_spec  # noqa: E402

docx = pytest.importorskip("docx")
from docx.oxml.ns import qn  # noqa: E402

SPEC = os.path.join(ROOT, "samples", "specs", "COURT_affidavit_example.json")
PW = os.path.join(ROOT, "samples", "specs", "COURT_wp_parawise_example.json")
FONT = "DVOT-SurekhMR"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
ENV.pop("LINT_SKIP", None)


def load(p=SPEC):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", env=ENV)


def build(tmp_path, spec, pre="T"):
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    r = run([os.path.join(TOOLS, "build_affidavit.py"), str(sp), str(tmp_path), pre])
    return r, tmp_path / f"{pre}_Affidavit.docx"


def text_of(path):
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


def test_sample_lints_clean():
    s = load()
    assert LA.lint_affidavit(s) == []
    assert LA.warnings_affidavit(s) == []
    assert lint_spec.lint_spec(s) == []
    assert lint_spec.lint_warnings(s) == []
    r = run([os.path.join(TOOLS, "lint_spec.py"), SPEC])
    assert r.returncode == 0 and r.stdout.strip().splitlines() == ["LINT OK"], r.stdout + r.stderr


def test_build_sample(tmp_path):
    r, out = build(tmp_path, load())
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.exists()
    t = text_of(out)
    # Ch. III Rule 1 / 2: entitling, "In the matter of", parties
    assert "In the High Court of Judicature, Appellate Side, Bombay." in t
    assert "In the matter of WRIT PETITION NO. ____ OF 2026" in t
    assert "… Petitioners" in t and "… Respondents" in t and "Versus" in t
    assert "AFFIDAVIT IN REPLY ON BEHALF OF RESPONDENT NOS. 1 AND 2" in t
    # CPC Form 16-A opening
    assert "aged about ____ years, working as Deputy Secretary to Government" in t
    assert "do hereby state on solemn affirmation as under:-" in t
    # numbered paras (Rule 4), parawise reply with the Section's labels, Grounds separator, prayer
    assert "PARAWISE REPLY" in t and "Grounds" in t
    assert "Para No.1: Needs no comments" in t
    assert "Prayer Clauses (a) to (d): " in t
    assert "Hence, it is prayed that the same may be dismissed." in t
    # Rule 10 declaration + jurat + advocate line
    assert "the Deponent abovenamed do solemnly declare that what is stated above in paragraphs 1 to 3" in t
    assert "I believe the information to be true for the following reasons :-" in t
    assert "Solemnly declare at Mumbai above said this ____ day of ____ 2026" in t
    for ln in ("(Signature)", "Before me,", "Solemnly affirmed before me", "who is identified before me",
               "whom I personally know.", "High Court, Appellate Side, Bombay.", "Assistant Registrar.",
               "Advocate for Respondent Nos. 1 and 2"):
        assert ln in t, ln
    assert "—" not in t   # §4.27 (उ): no em dash in drafts


def test_numbering_consecutive(tmp_path):
    r, out = build(tmp_path, load())
    assert r.returncode == 0
    nums = [int(p.text.split(".")[0]) for p in docx.Document(str(out)).paragraphs
            if p.text[:3].rstrip(".\t").isdigit() and "\t" in p.text[:4]]
    assert nums == list(range(1, len(nums) + 1)) and len(nums) == 9


def test_layout_fonts_and_paper_book(tmp_path):
    r, out = build(tmp_path, load())
    assert r.returncode == 0
    d = docx.Document(str(out))
    s = d.sections[0]
    assert round(s.left_margin.cm, 1) == 5.0 and round(s.right_margin.cm, 1) == 3.0
    assert round(s.page_width.cm, 1) == 21.0
    ln = s._sectPr.find(qn("w:lnNumType"))
    assert ln is not None and ln.get(qn("w:countBy")) == "10"
    sys.path.insert(0, TOOLS)
    from build_parawise import bad_font_runs
    assert bad_font_runs(d) == 0
    sizes = {r.font.size.pt for p in d.paragraphs for r in p.runs if r.text.strip() and r.font.size}
    assert sizes == {14.0}
    assert d.core_properties.author in ("", None)


def test_paper_book_off_and_bench(tmp_path):
    s = load(); s["affidavit"]["paper_book"] = False; s["affidavit"]["bench"] = "aurangabad"
    r, out = build(tmp_path, s)
    assert r.returncode == 0, r.stdout + r.stderr
    d = docx.Document(str(out))
    assert d.sections[0]._sectPr.find(qn("w:lnNumType")) is None
    t = text_of(out)
    assert "In the High Court of Judicature, Bombay, at Aurangabad" in t
    assert "High Court, Bombay, at Aurangabad." in t


def test_reply_from_parawise_block(tmp_path):
    s = load(); del s["affidavit"]["reply"]
    s["parawise"] = load(PW)["parawise"]
    assert LA.lint_affidavit(s) == []
    r, out = build(tmp_path, s)
    assert r.returncode == 0, r.stdout + r.stderr
    t = text_of(out)
    first = s["parawise"]["paras"][0]["remarks"][:40]
    assert first in t and "Grounds" in t


def test_age_optional(tmp_path):
    s = load(); del s["affidavit"]["deponent"]["age"]
    r, out = build(tmp_path, s)
    assert r.returncode == 0
    assert "aged about" not in text_of(out).split("do hereby state")[0].split("AFFIDAVIT IN REPLY")[1]


@pytest.mark.parametrize("mut,needle", [
    (lambda a: a.__setitem__("case", ""), "affidavit.case"),
    (lambda a: a.__setitem__("respondents", []), "affidavit.respondents"),
    (lambda a: a.__setitem__("on_behalf_of", ""), "affidavit.on_behalf_of"),
    (lambda a: a.__setitem__("bench", "pune"), "affidavit.bench"),
    (lambda a: a.__setitem__("reply", []), "affidavit.reply"),
    (lambda a: a["reply"].__setitem__(0, {"para": "1", "reply": "Denied."}), "cryptic"),
    (lambda a: a["reply"].__setitem__(0, {"para": "", "reply": "x y z"}), ".para"),
    (lambda a: a["paras"].append("Prepared by the engine of AI."), "draft word"),
    (lambda a: a["paras"].append("See register/PAY-01.md"), "repo path"),
    (lambda a: a.__setitem__("paper_book", "yes"), "paper_book"),
    (lambda a: a["paras"].append("The order — dated ____."), "draft word"),
])
def test_lint_errors(mut, needle):
    s = copy.deepcopy(load())
    mut(s["affidavit"])
    probs = LA.lint_affidavit(s)
    assert any(needle in p for p in probs), probs


def test_lint_warnings():
    s = copy.deepcopy(load())
    s["affidavit"]["reply"] = [{"para": "1", "reply": "The learned Court failed to see the Rules."},
                               {"para": "2", "reply": "शासन निर्णय लागू आहे."},
                               {"para": "3", "reply": "Not correct as stated here."}]
    w = "\n".join(LA.warnings_affidavit(s))
    assert "contempt-prone" in w and "Devanagari" in w and "Prayer" in w and "short reply" in w


def test_refuses_without_block_and_on_lint_error(tmp_path):
    s = load(); del s["affidavit"]
    r, out = build(tmp_path, s)
    assert r.returncode == 1 and not out.exists()
    s = load(); s["affidavit"]["case"] = ""
    r, out = build(tmp_path, s)
    assert r.returncode == 1 and not out.exists() and "LINT FAILED" in r.stderr


def test_lint_spec_names_affidavit_in_last_para():
    s = load()
    s["note"]["closing"] = ("सबब, सरकारी वकील यांना पाठवावयाच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. "
                            "मान्य झाल्यास पत्र निर्गमित करण्यात येईल.")
    assert any("affidavit" in w for w in lint_spec.lint_warnings(s))
    s2 = load(); s2["affidavit"]["case"] = ""
    probs, _ = lint_spec.lint_extras(s2)
    assert any("affidavit.case" in p for p in probs)
