"""अर्धशासकीय पत्र (letter "kind": "do") and अनौपचारिक संदर्भ (note "uo") — docs/FORMS_RESEARCH_DO_UO.md.
mkdocs / build_note_letter build, lint_spec rules, verify_outputs checks; the existing letter / reminder unchanged.
Run from the repo root:  python3 -m pytest -q tests/test_do_uo.py"""
import copy
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SPECS = os.path.join(ROOT, "samples", "specs")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
docx = pytest.importorskip("docx")
import lint_spec  # noqa: E402
import mkdocs  # noqa: E402
import test_verify_outputs as TV  # noqa: E402 — the verify fixture helpers (CR122 + Study + package)

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
DO = os.path.join(SPECS, "LETTER_do_example.json")
UO = os.path.join(SPECS, "NOTE_uo_reference_example.json")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run(args, env=ENV):
    return subprocess.run([sys.executable] + args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")


def texts(path):
    return [p.text.strip() for p in docx.Document(path).paragraphs]


# ---------------- lint ----------------
def test_samples_lint_clean():
    for p in (DO, UO):
        s = load(p)
        assert lint_spec.lint_spec(s) == [], p
        assert not [w for w in lint_spec.lint_warnings(s) if "§4.28" in w], p


@pytest.mark.parametrize("change,needle", [
    (lambda L: L.update(body=["कृपया या विभागाचे पत्र पहावे.", "माहिती लवकर पाठवावी."]), "first person"),
    (lambda L: L.update(salutation="महोदय,"), ".salutation"),
    (lambda L: L.update(to=[]), ".to"),
    (lambda L: L.update(subject=""), ".subject"),
    (lambda L: L.update(ref_no="bad"), ".ref_no"),
    (lambda L: L.update(intro="उपरोक्त विषयाबाबत …"), ".intro"),
    (lambda L: L.update(reminder=1), ".reminder"),
    (lambda L: L.update(kind="xyz"), ".kind"),
])
def test_do_lint_rules(change, needle):
    s = load(DO)
    change(s["letter"])
    assert any(needle in p for p in lint_spec.lint_spec(s)), lint_spec.lint_spec(s)


def test_do_in_letters_list_and_last_para_naming():
    s = load(DO)
    s["letters"] = [s.pop("letter")]
    assert lint_spec.lint_spec(s) == []
    s["note"]["paras"][-1] = s["note"]["paras"][-1].replace("अर्धशासकीय पत्राचे", "पत्राचे")
    assert any("अर्धशासकीय पत्र" in w and "§4.28" in w for w in lint_spec.lint_warnings(s))


def test_uo_lint_rules():
    s = load(UO)
    s["note"]["uo"]["to"] = "सामान्य प्रशासन विभाग"      # last para sends to Finance only
    assert any("अनौपचारिक संदर्भ" in p and "last para" in p for p in lint_spec.lint_spec(s))
    s = load(UO); s["note"]["uo"]["to"] = "वित्त"
    assert any(p.startswith("note.uo.to") for p in lint_spec.lint_spec(s))
    s = load(UO); s["note"]["uo"]["x"] = "1"
    assert any(p.startswith("note.uo.x") for p in lint_spec.lint_spec(s))
    s = load(UO); s["note"]["uo"] = "वित्त विभाग"
    assert any(p.startswith("note.uo:") for p in lint_spec.lint_spec(s))
    s = load(UO); s["note"]["uo"]["no"] = "TODO"           # §4.27 words also in the U.O. block
    assert any("note.uo.no" in p and "draft word" in p for p in lint_spec.lint_spec(s))


# ---------------- build ----------------
def test_build_do(tmp_path):
    r = run([os.path.join(TOOLS, "build_note_letter.py"), DO, str(tmp_path), "D"])
    assert r.returncode == 0, r.stdout + r.stderr
    d = docx.Document(str(tmp_path / "D_Note_and_Letter.docx"))
    assert len(d.sections) == 2
    t = [p.text.strip() for p in d.paragraphs]
    i = next(k for k, x in enumerate(t) if x.startswith("अ.शा.पत्र क्र. संकिर्ण-2026/"))
    let = t[i:]
    # GAD specimen order: number block, sender, विषय, salutation, body, शुभेच्छा, आपला स्नेहांकित, (name), addressee
    order = [let.index(x) for x in ("विधि व न्याय विभाग,", "राजेश वडनेरकर", "अवर सचिव.")]
    assert order == sorted(order)
    vi = next(k for k, x in enumerate(let) if x.startswith("विषय : "))
    si = let.index("प्रिय श्री. ____,")
    assert vi < si < let.index("शुभेच्छा") < let.index("आपला स्नेहांकित,") < let.index("(राजेश वडनेरकर)") < let.index("श्री. ____,")
    assert let[-1] == "मुंबई."
    assert "महोदय," not in let and "प्रति," not in let and not any(x.startswith("प्रत :") for x in let)
    assert not any(x.startswith("क्रमांक:-") for x in let)
    assert any(x.startswith("2.") for x in let) and any(x.startswith("3.") for x in let)


def test_build_uo(tmp_path):
    r = run([os.path.join(TOOLS, "build_note_letter.py"), UO, str(tmp_path), "U"])
    assert r.returncode == 0, r.stdout + r.stderr
    t = [x for x in texts(str(tmp_path / "U_Note_and_Letter.docx")) if x]
    k = t.index("अ.मु.स. (वित्त)")
    assert t[k + 1:k + 4] == ["विधि व न्याय विभाग", "वित्त विभागाकडे अनौपचारिक संदर्भ कार्यासन का.6",
                              "क्रमांक ____ दिनांक __.__.2026"]


def test_uo_lines_defaults():
    s = {"note": {"uo": {"to": "वित्त विभाग"}}}
    assert mkdocs.uo_lines(s) == ["विधि व न्याय विभाग", "वित्त विभागाकडे अनौपचारिक संदर्भ कार्यासन का.6",
                                  "क्रमांक ____ दिनांक ____"]
    assert mkdocs.uo_lines({"note": {}}) == []


def test_existing_letter_and_reminder_unchanged(tmp_path):
    s = load(os.path.join(SPECS, "CR131_2026_special-pay_info-letter.json"))
    L = s.pop("letter"); R = copy.deepcopy(L)
    R.update(reminder=1, refs=["या कार्यासनाचे समक्रमांकाचे पत्र दि. __.__.2026"] + L["refs"], points=[],
             intro="उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, संदर्भाधीन पत्रान्वये मागविण्यात "
                   "आलेली माहिती अद्याप अप्राप्त आहे. सदर माहिती लवकरात लवकर शासनास उपलब्ध करून देण्यात यावी, ही विनंती.")
    s["letters"] = [L, R]
    assert lint_spec.lint_spec(s) == []
    sp = tmp_path / "s.json"; sp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    r = run([os.path.join(TOOLS, "build_note_letter.py"), str(sp), str(tmp_path), "LR"])
    assert r.returncode == 0, r.stdout + r.stderr
    t = texts(str(tmp_path / "LR_Note_and_Letter.docx"))
    assert t.count("स्मरणपत्र-1") == 1 and t.count("आपला,") == 2 and "आपला स्नेहांकित," not in t


# ---------------- verify_outputs ----------------
@pytest.fixture(scope="module")
def vdir(tmp_path_factory):
    if TV.FONTFILE is None:
        pytest.skip("no Devanagari font for the page stamps")
    base = tmp_path_factory.mktemp("v")
    spec = load(TV.SPEC)
    do = load(DO)["letter"]
    spec2 = copy.deepcopy(spec)
    spec2["letters"] = [spec2.pop("letter"), do]               # ordinary letter + D.O. letter (TV.ENV skips the lint)
    TV.build_note(spec2, str(base))
    TV.build_study(TV.study_spec(spec), str(base))
    TV.build_pkg(os.path.join(str(base), TV.PKGNAME))
    return base, spec


def verify(d):
    r = run([os.path.join(TOOLS, "verify_outputs.py"), str(d), TV.PRE, os.path.join(str(d), TV.PKGNAME), str(TV.NPP)],
            env=TV.ENV)
    return r.returncode, r.stdout + r.stderr


def test_verify_letter_plus_do_all_ok(vdir):
    rc, out = verify(vdir[0])
    assert rc == 0 and "ALL OK" in out, out
    assert "OK: अर्धशासकीय पत्र salutation / ending / addressee" in out
    assert "OK: letter ending (§4.5)" in out


def test_verify_do_missing_subscription_fails(vdir, tmp_path):
    d = tmp_path / "c"; shutil.copytree(vdir[0], d)
    TV.set_text(str(d / f"{TV.PRE}_Note_and_Letter.docx"), "आपला स्नेहांकित,", "आपला,")
    rc, out = verify(d)
    assert rc != 0 and any("अर्धशासकीय पत्र salutation" in ln for ln in out.splitlines() if ln.startswith("FAIL:")), out


def test_verify_uo_block(vdir, tmp_path):
    spec = copy.deepcopy(vdir[1])
    spec["note"]["uo"] = {"to": "वित्त विभाग", "no": "____", "date": "____"}
    d = tmp_path / "u"; d.mkdir()
    TV.build_note(spec, str(d))
    TV.build_study(TV.study_spec(vdir[1]), str(d))
    TV.build_pkg(os.path.join(str(d), TV.PKGNAME))
    rc, out = verify(d)
    assert "OK: अनौपचारिक संदर्भ block (note foot)" in out, out
    assert "OK: note signer chain (§4.6)" in out, out
    TV.set_text(str(d / f"{TV.PRE}_Note_and_Letter.docx"), "क्रमांक ____ दिनांक ____", "____")
    rc, out = verify(d)
    assert any("अनौपचारिक संदर्भ block" in ln for ln in out.splitlines() if ln.startswith("FAIL:")), out
