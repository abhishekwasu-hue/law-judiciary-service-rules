"""Tests for tools/build_order.py and tools/lint_order.py (order drafts: GR / शुद्धिपत्रक / परिपत्रक / ज्ञापन / अधिसूचना).
Run from the repo root:  python3 -m pytest -q tests/test_build_order.py"""
import copy, json, os, subprocess, sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SPECS = os.path.join(ROOT, "samples", "specs")
sys.path.insert(0, TOOLS)
docx = pytest.importorskip("docx")
from docx.oxml.ns import qn  # noqa: E402
import lint_order  # noqa: E402
import build_order  # noqa: E402

FONT = "DVOT-SurekhMR"
TYPES = ["gr", "corrigendum", "circular", "memo", "notification"]
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def sample(t):
    with open(os.path.join(SPECS, f"ORDER_{t}_example.json"), encoding="utf-8") as f:
        return json.load(f)


def run(args):
    return subprocess.run([sys.executable] + args, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8")


def texts(d):
    out = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            out += [c.text for c in row.cells]
    return out


def font_problems(d):
    bad = []
    for el in d.element.body.iter(qn("w:r")):
        t = "".join(x.text or "" for x in el.iter(qn("w:t")))
        if not t.strip():
            continue
        rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
        if f is None or any(f.get(qn("w:" + a)) != FONT for a in ("ascii", "hAnsi", "cs", "eastAsia")):
            bad.append(t)
    return bad


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    od = tmp_path_factory.mktemp("orders")
    out = {}
    for t in TYPES:
        r = run([os.path.join(TOOLS, "build_order.py"), os.path.join(SPECS, f"ORDER_{t}_example.json"), str(od), f"S_{t}"])
        assert r.returncode == 0, r.stdout + r.stderr
        p = od / f"S_{t}_Order_Draft.docx"
        assert p.exists()
        out[t] = docx.Document(str(p))
    return out


@pytest.mark.parametrize("t", TYPES)
def test_samples_lint_clean(t):
    assert lint_order.lint_order(sample(t)) == []
    r = run([os.path.join(TOOLS, "lint_order.py"), os.path.join(SPECS, f"ORDER_{t}_example.json")])
    assert r.returncode == 0 and "LINT OK" in r.stdout


@pytest.mark.parametrize("t", TYPES)
def test_common_layout(built, t):
    d = built[t]; tx = texts(d); o = sample(t)["order"]
    assert "महाराष्ट्र शासन" in tx
    assert "विधि व न्याय विभाग," in tx
    assert build_order.ADDRESS in tx
    assert f"दिनांक :- {o['date']}" in tx
    assert build_order.GOVERNOR in tx                        # authentication, added by the tool
    sg = build_order.signer(o)
    i = tx.index(build_order.GOVERNOR)
    assert tx[i + 1] == sg["name"] and tx[i + 2] == sg["designation"]
    copies = [x for x in tx if x.split("\t")[0].rstrip(".").isdigit() and "निवड नस्ती" in x]
    assert copies and copies[-1].endswith("निवड नस्ती (कार्यासन-6)")
    assert build_order.COPIES_HEAD[t] in tx
    assert font_problems(d) == []


@pytest.mark.parametrize("t,label", [("gr", "शासन निर्णय क्रमांक :- "), ("corrigendum", "शासन शुद्धिपत्रक क्रमांक :- "),
                                     ("circular", "शासन परिपत्रक क्रमांक :- "), ("memo", "क्रमांक :- ")])
def test_number_line_and_subject(built, t, label):
    tx = texts(built[t]); o = sample(t)["order"]
    assert label + o["ref_no"] in tx
    assert tx[0] == o["subject"]                             # subject on top


def test_gr_headings_and_website(built):
    tx = texts(built["gr"])
    for h in ("वाचा :-", "प्रस्तावना :-", "शासन निर्णय :-"):
        assert h in tx
    assert tx.index("प्रस्तावना :-") < tx.index("शासन निर्णय :-") < tx.index(build_order.GOVERNOR)
    web = [x for x in tx if "www.maharashtra.gov.in" in x]
    assert len(web) == 1 and "संकेतांक ____" in web[0] and "डिजिटल स्वाक्षरीने साक्षांकित करून" in web[0]
    o = sample("gr")["order"]
    assert "\t" + o["operative"][0] in tx                    # first operative para unnumbered
    assert any(x.startswith("2.\t") for x in tx)
    assert any(x.endswith(o["concurrence"]) for x in tx)
    assert len(built["gr"].tables) == 1


@pytest.mark.parametrize("t", ["corrigendum", "circular"])
def test_website_line_default(built, t):
    assert any("www.maharashtra.gov.in" in x for x in texts(built[t]))


def test_corrigendum_body(built):
    tx = texts(built["corrigendum"]); c = sample("corrigendum")["order"]["corrections"][0]
    assert "शासन शुद्धिपत्रक :-" in tx
    assert build_order.CORR_INSTEAD in tx
    assert f"\t“{c['read_as']}” असे वाचावे." in tx
    assert any(x.endswith(f"“{c['instead_of']}” असे नमूद करण्यात आले आहे.") for x in tx)
    assert any("इतर तरतुदी कायम राहतील." in x for x in tx)


def test_memo_layout(built):
    tx = texts(built["memo"]); o = sample("memo")["order"]
    assert "ज्ञापन :-" in tx
    assert "प्रति," in tx and o["addressee"] in tx
    assert not any("www.maharashtra.gov.in" in x for x in tx)    # memo default: no website line
    assert any("असे कळविण्याचा मला आदेश आहे." in x for x in tx)


def test_notification_layout(built):
    d = built["notification"]; tx = texts(d); o = sample("notification")["order"]
    assert "अधिसूचना" in tx
    assert any(x.startswith(f"\tक्रमांक :- {o['ref_no']}, ") for x in tx)
    assert "उप विधि सल्लागार-नि-उप सचिव" in tx
    assert any("राजपत्र, भाग ____ मध्ये प्रसिद्ध करावी." in x for x in tx)
    for h in ("NOTIFICATION", build_order.GOVERNOR_EN, "Copy to –"):
        assert h in tx
    assert tx.index("अधिसूचना") < tx.index("NOTIFICATION")
    head = next(p for p in d.paragraphs if p.text == "NOTIFICATION")
    assert head.paragraph_format.page_break_before
    assert len(d.tables) == 2


# ---------------- lint negatives ----------------
def probs(spec):
    return "\n".join(lint_order.lint_order(spec))


def test_lint_no_order():
    assert "no 'order'" in probs({"note": {}})


def test_lint_bad_type_and_ref_and_date():
    s = sample("gr"); s["order"]["type"] = "letter"
    assert "type" in probs(s)
    s = sample("gr"); s["order"]["ref_no"] = "संकिर्ण-2026/12/प्र.क्र.5/कार्या-6"
    assert "order.ref_no" in probs(s)
    s = sample("gr"); s["order"]["ref_no"] = "संकीर्ण-2026/979/प्र.क्र.130/का.6"   # audit A1: both spellings
    assert "order.ref_no" not in probs(s)
    s = sample("gr"); s["order"]["date"] = "1 Nov 2026"
    assert "order.date" in probs(s)


def test_lint_gr_required_parts():
    for k in ("read", "preamble", "operative", "subject", "copies"):
        s = sample("gr"); s["order"][k] = []  if k != "subject" else ""
        assert f"order.{k}" in probs(s), k


def test_lint_website_off_and_tool_lines():
    s = sample("gr"); s["order"]["website_line"] = False
    assert "website line" in probs(s)
    s = sample("gr"); s["order"]["operative"].append("महाराष्ट्राचे राज्यपाल यांच्या आदेशानुसार व नावाने,")
    assert "Governor line" in probs(s)
    s = sample("circular"); s["order"]["website_line"] = False
    assert "website line" in probs(s)
    s = sample("memo"); s["order"]["website_line"] = False
    assert probs(s) == ""


def test_lint_copies_end():
    s = sample("gr"); s["order"]["copies"] = s["order"]["copies"][:-1]
    assert "निवड नस्ती" in probs(s)


def test_lint_language_rules():
    s = sample("gr"); s["order"]["preamble"] = ["दि.12.03.2026 रोजीच्या पत्रानुसार प्रस्ताव प्राप्त झाला आहे."]
    assert "संक्षेपचिन्हानंतर" in probs(s)
    s = sample("gr"); s["order"]["operative"][2] = "वेतननिश्चिती करुन देयके अदा करावीत."
    assert "करून" in probs(s)
    s = sample("gr"); s["order"]["preamble"] = ["उच्च न्यायालयाच्या पत्रानुसार प्रस्ताव प्राप्त झाला आहे."]
    assert "§4.23" in probs(s)
    s = sample("corrigendum"); s["order"]["subject"] = "शुध्दीपत्रकाबाबत."
    assert "§4.24" in probs(s) or "ध्द" in probs(s)
    # quoted text and the address part are exempt
    s = sample("gr"); s["order"]["preamble"] = ["“दि.12.03.2026 करुन” असे पत्रात नमूद आहे."]
    assert probs(s) == ""
    s = sample("gr"); s["order"]["copies"].insert(0, "प्रबंधक, उच्च न्यायालय, मुंबई")
    assert probs(s) == ""


def test_lint_corrigendum_corrections():
    s = sample("corrigendum"); s["order"]["corrections"] = []
    assert "order.corrections" in probs(s)
    s = sample("corrigendum"); s["order"]["corrections"][0]["read_as"] = "“श्री. ____”"
    assert "quotes" in probs(s)


def test_lint_memo_form():
    s = sample("memo"); s["order"]["operative"][0] = "वैद्यकीय खर्चाच्या प्रतिपूर्तीस मंजुरी देण्यात येत आहे."
    assert "ज्ञापन form" in probs(s)
    s = sample("memo"); del s["order"]["addressee"]
    assert "order.addressee" in probs(s)


def test_lint_notification():
    s = sample("notification"); s["order"]["operative"][0] = "महाराष्ट्र शासन खालील नियुक्त्या करीत आहे."
    assert "enabling provision" in probs(s)
    s = sample("notification"); del s["order"]["english"]
    assert "order.english" in probs(s)
    s = sample("notification"); s["order"]["english"]["operative"][0] = "The Government appoints the following officers."
    assert "english.operative[0]" in probs(s)


def test_warnings():
    s = sample("gr"); s["order"]["preamble"] = ["प्रस्ताव मंजूर करणेबाबत शासनास विनंती करण्यात आली आहे."]
    assert any("L11" in w or "नियम 12" in w for w in lint_order.lint_order_warnings(s))
    s = sample("gr"); del s["order"]["concurrence"]
    assert any("concurrence" in w for w in lint_order.lint_order_warnings(s))
    assert lint_order.lint_order_warnings(sample("gr")) == []


# ---------------- CLI ----------------
def test_cli_no_order(tmp_path):
    p = tmp_path / "s.json"; p.write_text(json.dumps({"note": {}}), encoding="utf-8")
    r = run([os.path.join(TOOLS, "build_order.py"), str(p), str(tmp_path), "X"])
    assert r.returncode == 1 and "no \"order\"" in r.stderr


def test_cli_refuses_on_lint_error_unless_no_lint(tmp_path):
    s = sample("gr"); s["order"]["website_line"] = False
    p = tmp_path / "s.json"; p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    r = run([os.path.join(TOOLS, "build_order.py"), str(p), str(tmp_path), "X"])
    assert r.returncode == 1 and "LINT FAILED" in r.stderr and not (tmp_path / "X_Order_Draft.docx").exists()
    r = run([os.path.join(TOOLS, "build_order.py"), str(p), str(tmp_path), "X", "--no-lint"])
    assert r.returncode == 0, r.stderr
    tx = texts(docx.Document(str(tmp_path / "X_Order_Draft.docx")))
    assert not any("www.maharashtra.gov.in" in x for x in tx)


def test_signer_defaults():
    o = copy.deepcopy(sample("gr")["order"]); o.pop("signer", None)
    assert build_order.signer(o) == build_order.SIGNER_DEFAULT
    o = copy.deepcopy(sample("notification")["order"]); o.pop("signer", None)
    assert build_order.signer(o)["designation"] == "उप विधि सल्लागार-नि-उप सचिव"


def test_lint_order_ma_and_dhd_exemptions():
    """audit A1 (02.11.2026): one "मा." before the title phrase; "निवृत्त न्यायमूर्ती"; "ध्द" in a person's name."""
    s = sample("gr")
    s["order"]["preamble"] = ["मा. प्रशासकीय न्यायमूर्ती समितीने व निवृत्त न्यायमूर्ती श्री. अ. ब. बुध्दे यांच्या समितीने शिफारस केली आहे."]
    assert not [p for p in lint_order.lint_order(s) if "§4.23" in p or "ध्द" in p]
    s["order"]["preamble"] = ["प्रशासकीय न्यायमूर्ती समितीने शुध्द प्रत सादर केली आहे."]
    P = lint_order.lint_order(s)
    assert any("§4.23" in p for p in P) and any("ध्द" in p for p in P)


# ---- C27 (02.11.2026): no package / warning / AI word in the order draft; blank metadata ----
@pytest.mark.parametrize("w", ["पॅकेज", "इशारा", "पडताळणी अपूर्ण", "मागवावे", "अस्पष्ट", "टीप :", "TODO", "warning",
                               "AI", "Claude", "मॉडेल", "स्वयंचलित", "engine", "generated", "GPT"])
def test_lint_draft_words(w):
    s = sample("gr"); s["order"]["preamble"] = [f"प्रस्ताव प्राप्त झाला आहे {w}."]
    assert "draft word" in probs(s)
    if w != "पॅकेज":   # "पॅकेज" is an error even inside quotes
        s = sample("gr"); s["order"]["preamble"] = [f"“{w}” असे पत्रात नमूद आहे."]
        assert "draft word" not in probs(s)
    s = sample("notification"); s["order"]["english"]["operative"].append(f"Note {w} here.")
    assert "draft word" in probs(s)


@pytest.mark.parametrize("t", TYPES)
def test_built_metadata_blank(built, t, tmp_path):
    sys.path.insert(0, TOOLS)
    import clean_meta
    cp = built[t].core_properties
    assert (cp.author, cp.last_modified_by, cp.title, cp.subject, cp.keywords, cp.comments, cp.category) == ("",) * 7
    p = tmp_path / "x.docx"; built[t].save(str(p)); clean_meta.clean_docx(str(p))
    assert clean_meta.docx_meta_problems(str(p)) == []
