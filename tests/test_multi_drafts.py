"""C28 (INSTRUCTIONS §4.28, 03.11.2026 — "कोणते मसुदे हवेत?"): several drafts in one run.
build_order.py "orders" (one docx, each order on a new page), lint_order per item, mkdocs / build_note_letter "letters"
(letter + स्मरणपत्र each in its own section), lint_spec combined last para + AMS logic + "letters" paths.
Run from the repo root:  python3 -m pytest -q tests/test_multi_drafts.py"""
import copy, json, os, subprocess, sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SPECS = os.path.join(ROOT, "samples", "specs")
sys.path.insert(0, TOOLS)
docx = pytest.importorskip("docx")
from docx.oxml.ns import qn  # noqa: E402
import lint_spec  # noqa: E402
import lint_order  # noqa: E402
import build_order  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
MULTI = os.path.join(SPECS, "ORDER_multi_example.json")


def load(name):
    with open(os.path.join(SPECS, name), encoding="utf-8") as f:
        return json.load(f)


def run(args):
    return subprocess.run([sys.executable] + args, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8")


def reminder_of(letter):
    r = copy.deepcopy(letter)
    r["reminder"] = 1
    r["refs"] = ["या कार्यासनाचे समक्रमांकाचे पत्र दि. __.__.2026"] + letter["refs"]
    r["intro"] = ("उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, संदर्भाधीन पत्रान्वये मागविण्यात "
                  "आलेली माहिती अद्याप अप्राप्त आहे. सदर माहिती लवकरात लवकर शासनास उपलब्ध करून देण्यात यावी, ही विनंती.")
    r["points"] = []
    r.pop("closing", None)
    return r


# ---------------- orders ----------------
def test_multi_sample_lints_clean():
    s = load("ORDER_multi_example.json")
    assert lint_spec.lint_spec(s) == []
    assert lint_order.lint_order(s) == []
    assert lint_spec.lint_extras(s)[0] == []
    assert not [w for w in lint_spec.lint_warnings(s) if "§4.28" in w]


def test_lint_order_item_paths():
    s = load("ORDER_multi_example.json")
    s["orders"][1]["ref_no"] = "bad"
    s["orders"][0]["copies"] = ["x"]
    p = lint_order.lint_order(s)
    assert any(x.startswith("orders[1].ref_no") for x in p)
    assert any(x.startswith("orders[0].copies") for x in p)
    assert not any(x.startswith("order.") for x in p)
    s["orders"] = {"type": "gr"}
    assert any(x.startswith("orders: structure") for x in lint_order.lint_order(s))


def test_single_order_still_accepted():
    s = load("ORDER_gr_example.json")
    assert lint_order.lint_order(s) == []
    assert [o["type"] for o in build_order.orders_of(s)] == ["gr"]


def test_build_multi_one_docx_new_page(tmp_path):
    r = run([os.path.join(TOOLS, "build_order.py"), MULTI, str(tmp_path), "M"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "gr+notification" in r.stdout
    assert sorted(p.name for p in tmp_path.glob("*.docx")) == ["M_Order_Draft.docx"]
    d = docx.Document(str(tmp_path / "M_Order_Draft.docx"))
    ps = d.paragraphs
    heads = [i for i, p in enumerate(ps) if p.text.strip() == "महाराष्ट्र शासन"]
    assert len(heads) == 2                                     # one heading block per order
    second = next(i for i, p in enumerate(ps) if i > 0 and p.paragraph_format.page_break_before)
    assert second <= heads[1] and ps[0].paragraph_format.page_break_before is not True
    texts = [p.text.strip() for p in ps]
    assert "शासन निर्णय :-" in texts and "अधिसूचना" in texts and "NOTIFICATION" in texts
    assert texts.index("शासन निर्णय :-") < texts.index("अधिसूचना")
    props = d.core_properties
    assert (props.author or "") == "" and (props.title or "") == ""   # clean_meta still applied


# ---------------- letters ----------------
def letters_spec():
    s = load("CR131_2026_special-pay_info-letter.json")
    L = s.pop("letter")
    s["letters"] = [L, reminder_of(L)]
    return s


def test_lint_letters_ok_and_paths():
    s = letters_spec()
    assert lint_spec.lint_spec(s) == []
    s["letters"][1]["refs"] = ["आपले पत्र"]
    p = lint_spec.lint_spec(s)
    assert any(x.startswith("letters[1].refs[0]: स्मरणपत्र") for x in p)
    s = letters_spec(); s["letter"] = s["letters"][0]
    assert any(x.startswith("letters: structure") for x in lint_spec.lint_spec(s))


def test_build_letter_and_reminder(tmp_path):
    sp = tmp_path / "s.json"
    sp.write_text(json.dumps(letters_spec(), ensure_ascii=False), encoding="utf-8")
    r = run([os.path.join(TOOLS, "build_note_letter.py"), str(sp), str(tmp_path), "LR"])
    assert r.returncode == 0, r.stdout + r.stderr
    d = docx.Document(str(tmp_path / "LR_Note_and_Letter.docx"))
    assert len(d.sections) == 3                                 # note + letter + reminder
    for sec in d.sections[1:]:
        t = sec._sectPr.find(qn("w:type"))
        assert t is None or t.get(qn("w:val")) == "nextPage"
    texts = [p.text.strip() for p in d.paragraphs]
    assert sum(t.startswith("क्रमांक:-") for t in texts) == 2
    assert texts.count("स्मरणपत्र-1") == 1
    assert texts.index("स्मरणपत्र-1") > next(i for i, t in enumerate(texts) if t.startswith("क्रमांक:-"))
    assert texts.count("प्रत :\t1. निवड नस्ती") == 2 and texts.count("आपला,") == 2


def test_old_single_letter_spec_unchanged(tmp_path):
    r = run([os.path.join(TOOLS, "build_note_letter.py"), os.path.join(SPECS, "CR131_2026_special-pay_info-letter.json"),
             str(tmp_path), "ONE"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(docx.Document(str(tmp_path / "ONE_Note_and_Letter.docx")).sections) == 2


# ---------------- combined last para ----------------
def with_closing(text, signers_extra=()):
    s = load("ORDER_multi_example.json")
    s["note"]["closing"] = text
    s["note"]["signers"] = s["note"]["signers"] + list(signers_extra)
    return s


@pytest.mark.parametrize("text", [
    "सबब, पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.",
    "सबब, पत्राचे, शासन निर्णयाचे व अधिसूचनेचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.",
    "सबब, माहिती मागविण्याबाबतच्या पत्राचे व स्मरणपत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्रे निर्गमित करण्यात येतील.",
    "सबब, शासन निर्णयाचे प्रारूप व नियुक्त्यांबाबतच्या अधिसूचनेची मराठी व इंग्रजी प्रारूपे पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास शासन निर्णय व अधिसूचना निर्गमित करण्यात येतील.",
])
def test_combined_last_para_accepted(text):
    assert not [p for p in lint_spec.lint_spec(with_closing(text)) if "last para" in p]


def test_single_letter_form_still_needs_its_sentence():
    p = lint_spec.lint_spec(with_closing("सबब, पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."))
    assert any("last para" in x for x in p)


def test_combined_keeps_ams_logic():
    t = "सबब, पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."
    assert any("अ.मु.स." in x for x in lint_spec.lint_spec(with_closing(t, [lint_spec.AMS])))


def test_unnamed_draft_warning():
    s = with_closing("सबब, शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.")
    w = [x for x in lint_spec.lint_warnings(s) if "§4.28" in x]
    assert len(w) == 1 and "notification" in w[0]


# ---------------- more draft kinds (04.11.2026): engine detection on the real builders' output ----------------
def test_engine_detects_new_draft_kinds(tmp_path):
    """tools/engine_supabase.py missing_drafts finds each new kind in the files the real builders write (printed lines
    of build_order / mkdocs, file names of build_affidavit / build_lq), and does not mistake one kind for another."""
    import engine_supabase as E
    builds = [("build_order.py", "ORDER_endorsement_example.json", "E"), ("build_order.py", "ORDER_office_order_example.json", "O"),
              ("build_order.py", "ORDER_press_note_example.json", "P"), ("build_order.py", "ORDER_addendum_example.json", "A"),
              ("build_order.py", "ORDER_gr_example.json", "G"),
              ("build_note_letter.py", "LETTER_do_example.json", "D"), ("build_note_letter.py", "NOTE_uo_reference_example.json", "U"),
              ("build_note_letter.py", "CR131_2026_special-pay_info-letter.json", "L"),
              ("build_affidavit.py", "COURT_affidavit_example.json", "F"), ("build_lq.py", "LQ_answer_example.json", "Q")]
    for tool, spec, pre in builds:
        r = run([os.path.join(TOOLS, tool), os.path.join(SPECS, spec), str(tmp_path), pre])
        assert r.returncode == 0, f"{tool} {spec}: {r.stdout}{r.stderr}"
    made = {"E": "endorsement", "O": "office_order", "P": "press_note", "A": "addendum", "G": "gr", "D": "do_letter",
            "U": "uo_note", "L": "letter", "F": "affidavit", "Q": "lq"}
    checked = ["letter", "gr", "do_letter", "uo_note", "endorsement", "office_order", "press_note", "addendum", "affidavit", "lq"]
    for pre, key in made.items():
        miss = E.missing_drafts(str(tmp_path), pre, checked)
        assert miss == [E.DRAFT_LABEL[k] for k in checked if k != key], f"{pre} ({key}): {miss}"
