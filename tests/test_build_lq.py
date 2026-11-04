"""Tests for tools/build_lq.py and tools/lint_lq.py (विधानमंडळ प्रश्नाचे उत्तर + पुरवणी टिप्पणी).
Run: python3 -m pytest -q tests/test_build_lq.py"""
import copy
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import lint_lq as LL  # noqa: E402
import lint_spec  # noqa: E402

docx = pytest.importorskip("docx")

SPEC = os.path.join(ROOT, "samples", "specs", "LQ_answer_example.json")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
ENV.pop("LINT_SKIP", None)


def load():
    with open(SPEC, encoding="utf-8-sig") as f:
        return json.load(f)


def run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", env=ENV)


def build(tmp_path, spec, pre="T"):
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    r = run([os.path.join(TOOLS, "build_lq.py"), str(sp), str(tmp_path), pre])
    return r, tmp_path / f"{pre}_LQ_Answer.docx"


def all_text(path):
    d = docx.Document(str(path))
    t = [p.text for p in d.paragraphs]
    for tb in d.tables:
        for row in tb.rows:
            for c in row.cells:
                t.append(c.text)
    return "\n".join(t)


def test_sample_lints_clean():
    s = load()
    assert LL.lint_lq(s) == [] and LL.warnings_lq(s) == []
    assert lint_spec.lint_spec(s) == [] and lint_spec.lint_warnings(s) == []
    r = run([os.path.join(TOOLS, "lint_spec.py"), SPEC])
    assert r.returncode == 0 and r.stdout.strip().splitlines() == ["LINT OK"], r.stdout + r.stderr


def test_build_sample(tmp_path):
    r, out = build(tmp_path, load())
    assert r.returncode == 0, r.stdout + r.stderr
    d = docx.Document(str(out))
    t = all_text(out)
    assert d.paragraphs[0].text.startswith("उत्तराचा दिनांक :")       # GADT 13.2: date at the very top
    for s in ("तारांकित प्रश्न क्रमांक ____.", "विधानसभा सदस्य.", "सन्माननीय ____ मंत्री पुढील गोष्टींचा खुलासा करतील काय :-",
              "(१) जिल्हा न्यायालय", "(१) हे अंशत: खरे आहे.", "(३) प्रश्न उद्भवत नाही.",
              "मंत्रालय, मुंबई ४०० ०३२", "प्रतींसह सचिव, महाराष्ट्र विधानमंडळ सचिवालय, विधानभवन, मुंबई यांजकडे",
              "च्या संदर्भात अग्रेषित.", "शासनाचे अवर सचिव.", "पुरवणी टिप्पणी", "विधानसभा तारांकित प्रश्न क्रमांक ____"):
        assert s in t, s
    # पुरवणी टिप्पणी on a new page
    sup = next(p for p in d.paragraphs if p.text == "पुरवणी टिप्पणी")
    assert sup.paragraph_format.page_break_before
    assert len(d.tables) == 2   # Q/A table + the supplementary table
    from build_parawise import bad_font_runs
    assert bad_font_runs(d) == 0
    assert "—" not in t


def test_unstarred_no_supplementary(tmp_path):
    s = load(); s["lq"]["kind"] = "unstarred"; s["lq"]["house"] = "council"; del s["lq"]["supplementary"]
    assert LL.warnings_lq(s) == []
    r, out = build(tmp_path, s)
    assert r.returncode == 0, r.stdout + r.stderr
    t = all_text(out)
    assert "अतारांकित प्रश्न क्रमांक" in t and "विधानपरिषद सदस्य." in t and "पुरवणी टिप्पणी" not in t


def test_joint_answer_kept_as_written(tmp_path):
    s = load(); s["lq"]["parts"][0]["a"] = "(१) व (२) होय, हे खरे आहे."; s["lq"]["parts"][1]["a"] = "(२) वरीलप्रमाणे."
    assert not any("parts[0]" in w for w in LL.warnings_lq(s))
    r, out = build(tmp_path, s)
    assert r.returncode == 0
    t = all_text(out)
    assert "(१) व (२) होय, हे खरे आहे." in t and "(१) (१) व" not in t


@pytest.mark.parametrize("mut,needle", [
    (lambda q: q.__setitem__("subject", ""), "lq.subject"),
    (lambda q: q.__setitem__("number", ""), "lq.number"),
    (lambda q: q.__setitem__("portfolio", ""), "lq.portfolio"),
    (lambda q: q.__setitem__("parts", []), "lq.parts"),
    (lambda q: q["parts"][0].__setitem__("a", ""), "lq.parts[0].a"),
    (lambda q: q["parts"][1].__setitem__("q", ""), "lq.parts[1].q"),
    (lambda q: q.__setitem__("house", "lok sabha"), "lq.house"),
    (lambda q: q.__setitem__("kind", "oral"), "lq.kind"),
    (lambda q: q.__setitem__("members", []), "lq.members"),
    (lambda q: q["supplementary"].append({"table": [["a"]]}), "lq.supplementary[3]"),
    (lambda q: q["parts"][0].__setitem__("a", "होय. हे उत्तर AI ने तयार केले."), "draft word"),
    (lambda q: q["supplementary"].append("पॅकेज PDF पृ. 3"), "draft word"),
])
def test_lint_errors(mut, needle):
    s = copy.deepcopy(load())
    mut(s["lq"])
    assert any(needle in p for p in LL.lint_lq(s)), LL.lint_lq(s)


def test_lint_warnings():
    s = copy.deepcopy(load())
    s["lq"]["parts"][0]["a"] = "पदभरती सुरू आहे."          # answer to "हे खरे आहे काय" without होय / नाही form
    del s["lq"]["supplementary"]
    w = "\n".join(LL.warnings_lq(s))
    assert "parts[0].a" in w and "supplementary" in w
    s["lq"]["kind"] = "unstarred"; s["lq"]["supplementary"] = ["x y z"]
    assert any("GADT 13.5" in x for x in LL.warnings_lq(s))


def test_refuses_without_block_and_on_lint_error(tmp_path):
    s = load(); del s["lq"]
    r, out = build(tmp_path, s)
    assert r.returncode == 1 and not out.exists()
    s = load(); s["lq"]["subject"] = ""
    r, out = build(tmp_path, s)
    assert r.returncode == 1 and not out.exists() and "LINT FAILED" in r.stderr


def test_last_para_form_and_extras():
    s = load()
    s["note"]["closing"] = "सबब, प्रकरण मान्यतेस्तव सादर."
    assert any("lq" in w for w in lint_spec.lint_warnings(s))
    s2 = load(); s2["lq"]["subject"] = ""
    probs, _ = lint_spec.lint_extras(s2)
    assert any("lq.subject" in p for p in probs)
