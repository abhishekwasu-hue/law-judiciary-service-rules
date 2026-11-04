#!/usr/bin/env python3
"""build_lq.py <spec.json> <outdir> <PREFIX> [--no-lint]
विधानमंडळ प्रश्नाचे उत्तर (Legislative Assembly / Council question: starred, unstarred, short notice) — the answer form
and, for a starred / short-notice question, the "पुरवणी टिप्पणी" on a new page — from the optional "lq" block of
spec.json -> <outdir>/<PREFIX>_LQ_Answer.docx (+ <PREFIX>_LQ_Answer.pdf preview when LibreOffice is available).
Refuses (exit 1) when the spec has no "lq" block, or when tools/lint_lq.py finds errors (unless --no-lint or env
LINT_SKIP=1). The file's own note (टिप्पणी: present position clause by clause, answer proposed at the end of each
paragraph — MMOP 2023 §16.3(2)) comes from the same spec's "note" via tools/build_note_letter.py.

Sources (verbatim lines with pages: docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md part B):
  [GADT 13.9]  सा.प्र.वि., "टिप्पणी लेखन व पत्रव्यवहार" (pdf/08-gad-office-procedure/GAD_Tippani-Lekhan-va-Patravyavahar-
               Marathi.pdf), प्रकरण 13, परि. 13.9 "(तारांकित प्रश्नाचा नमुना)" PDF pp. 56-57 (printed 52-53): the layout
               printed here — "उत्तराचा दिनांक" at the top right; the subject line (bold) between rules; left "तारांकित
               प्रश्न क्रमांक …" / "श्रीयुत … (मतदारसंघ)" / "विधानसभा सदस्य.", right the Minister's name and portfolio;
               "सन्माननीय <portfolio> पुढील गोष्टींचा खुलासा करतील काय :-"; each sub-question (१), (२) … on the left and its
               answer (१), (२) … on the right; then "क्रमांक …" / "<विभाग>" / "मंत्रालय, मुंबई ४०० ०३२" / "दिनांक :";
               "प्रत, … प्रतींसह सचिव, महाराष्ट्र विधानमंडळ सचिवालय, विधानभवन, मुंबई यांजकडे त्यांच्या क्रमांक …, दिनांक …
               च्या संदर्भात अग्रेषित."; the signature "( … )" / "शासनाचे अवर सचिव."; then "पुरवणी टिप्पणी" / "विधानसभा
               तारांकित प्रश्न क्रमांक …" / "“ <subject> ”" and the supplementary information;
  [GADT 13.2]  "तारांकित प्रश्न व त्याचे उत्तर याचा एक विशिष्ट नमुना आहे व त्याच नमुन्यात उत्तर देणे जरूर असते. उत्तरामध्ये
               अगदी वर सभागृहात उत्तर देण्याचा दिनांक न चुकता नमूद करणे जरूर असते." (PDF p. 55, printed 51);
  [GADT 13.5]  unstarred: "… त्यामुळे पूरक टिप्पणीचीही जरुरी नसते. … अतारांकित प्रश्नांच्या उत्तराचा नमुना हा तारांकित
               प्रश्नाप्रमाणेच असतो." (PDF p. 55) -> no पुरवणी टिप्पणी unless the spec gives one;
  [GADT 13.7]  short notice: "… याचे उत्तरही तारांकित प्रश्नाप्रमाणेच द्यावे लागते." (PDF p. 56);
  [KKN 106]   सा.प्र.वि., "कार्यालयीन कार्यपद्धती नियमपुस्तिका" (Marathi), परि. 106 (PDF pp. 57-58, printed 48-49):
               "प्रश्नाच्या प्रत्येक खंडाच्या संबंधातील विद्यमान परिस्थितीचे वर्णन करणारी संपूर्ण टिप्पणी … प्रत्येक परिच्छेदाच्या
               शेवटी प्रस्तावित उत्तर …", a separate clause-by-clause draft answer, and "“पुरवणी प्रश्नांकरिता टिप्पणी” या
               शीर्षाखाली एका स्वतंत्र पानावर";
  [MMOP 16.3]  Maharashtra Manual of Office Procedures, 2023, §16.3(2)-(4) (PDF pp. 92-93): "A separate draft answer, clause
               by clause"; for a starred / short notice question "additional information … on a separate page under the
               heading "Notes for supplementary questions"" (= पुरवणी टिप्पणी); "answer in the form prescribed by
               Maharashtra Legislature";
  [MLS]        the Legislature's printed lists (mls.org.in, प्रश्नोत्तरांची यादी, 2026): the opening "सन्माननीय … पुढील
               गोष्टींचा खुलासा करतील काय :-" and the answer forms "होय, हे खरे आहे.", "हे खरे नाही.", "हे अंशत: खरे आहे.",
               "प्रश्न उद्भवत नाही.".

"lq": {
  "house": "assembly" | "council",                 # विधानसभा / विधानपरिषद (default assembly)
  "kind": "starred" | "unstarred" | "short_notice", # तारांकित / अतारांकित / अल्पसूचना (default starred)
  "number": "____",                                 # प्रश्न क्रमांक
  "answer_date": "__.__.2026",                      # उत्तराचा दिनांक (top right)
  "subject": "____ बाबत",                           # the question's title
  "members": ["श्री. ____ (____)"],                 # सदस्यांची नावे (मतदारसंघ) — "____" until known
  "minister": "श्री. ____", "portfolio": "____ मंत्री",
  "parts": [{"q": "…, हे खरे आहे काय,", "a": "होय, हे खरे आहे."}, …],
          # "a" printed as "(n) a"; an "a" that starts with "(" is printed as written (e.g. "(१) व (२) होय, हे खरे आहे.")
          # "\n" in "a" = a following paragraph of the answer
  "ref_no": "संकिर्ण-2026/____/प्र.क्र.____/का.6", "department": "विधि व न्याय विभाग", "date": "",
  "ls_ref": "____", "ls_date": "", "copies": "____",  # Legislature Secretariat letter no./date; number of copies
  "signer": "( ____ )", "designation": "शासनाचे अवर सचिव.",
  "supplementary": ["…", {"title"?: "…", "table": [["…", "…"], …]}]   # पुरवणी टिप्पणी (starred / short notice)
  "supplementary_heading": "पुरवणी टिप्पणी"        # optional; KKN para 106 calls the page "पुरवणी प्रश्नांकरिता टिप्पणी"
}"""
import json
import os
import sys

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH as WA
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_parawise import FONT, bad_font_runs, borders, fix_styles, setfont  # noqa: E402
from build_affidavit import to_pdf  # noqa: E402
from clean_meta import clean_docx  # noqa: E402

HOUSE = {"assembly": "विधानसभा", "council": "विधानपरिषद"}
KIND = {"starred": "तारांकित", "unstarred": "अतारांकित", "short_notice": "अल्पसूचना"}
BLANK = "____"
DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
DEF_DEPT = "विधि व न्याय विभाग"
DEF_DESIG = "शासनाचे अवर सचिव."
SIZE = 12
TEXT_W = 11906 - 1800 - 1440          # twips: A4, margins as tools/build_parawise.py (office format)
COLS = (TEXT_W // 2 + 300, TEXT_W - (TEXT_W // 2 + 300))


def _s(x):
    return x.strip() if isinstance(x, str) else ""


def dev(n):
    return str(n).translate(DEV_DIGITS)


def labels(lq):
    house = HOUSE.get(_s(lq.get("house")).lower() or "assembly", HOUSE["assembly"])
    kind = KIND.get(_s(lq.get("kind")).lower() or "starred", KIND["starred"])
    return house, kind


def has_supplementary(lq):
    """[GADT 13.9 / 13.7 / MMOP 16.3(3)] starred and short notice: पुरवणी टिप्पणी; unstarred only when given [GADT 13.5]."""
    sup = [x for x in lq.get("supplementary") or [] if (isinstance(x, dict) and x.get("table")) or _s(x)]
    return bool(sup)


def _p(container, text="", bold=False, align=WA.JUSTIFY, left=None, first=None, after=0, before=0, size=SIZE,
       line=1.15, p=None, underline=False):
    p = p if p is not None else container.add_paragraph()
    pf = p.paragraph_format; pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = line
    if left is not None: pf.left_indent = Twips(left)
    if first is not None: pf.first_line_indent = Twips(first)
    if align is not None: p.alignment = align
    if text:
        r = setfont(p.add_run(text), size, bold)
        if underline: r.underline = True
    else:
        rpr = p._p.get_or_add_pPr().makeelement(qn("w:rPr"), {})
        rf = rpr.makeelement(qn("w:rFonts"), {qn("w:" + a): FONT for a in ("ascii", "hAnsi", "cs", "eastAsia")})
        sz = rpr.makeelement(qn("w:sz"), {qn("w:val"): str(size * 2)})
        rpr.append(rf); rpr.append(sz); p._p.get_or_add_pPr().append(rpr)
    return p


def cell_lines(c, lines, bold=False, align=WA.JUSTIFY, first_hanging=False):
    """lines into a cell; first_hanging: '(n) text' with the text hanging after the number."""
    for k, ln in enumerate(lines):
        p = c.paragraphs[0] if k == 0 else c.add_paragraph()
        _p(c, ln, bold=bold, align=align, after=3, p=p,
           left=(454 if first_hanging and k == 0 else (454 if first_hanging else None)),
           first=(-454 if first_hanging and k == 0 else None))


def rule_below(p, sz=8):
    """a horizontal rule under a paragraph (the lines of the specimen)."""
    pPr = p._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr"); x = OxmlElement("w:bottom")
    x.set(qn("w:val"), "single"); x.set(qn("w:sz"), str(sz)); x.set(qn("w:space"), "1"); x.set(qn("w:color"), "000000")
    b.append(x)
    nxt = next((pPr.find(qn(t)) for t in ("w:shd", "w:tabs", "w:spacing", "w:ind", "w:jc", "w:rPr")
                if pPr.find(qn(t)) is not None), None)
    nxt.addprevious(b) if nxt is not None else pPr.append(b)


def no_borders(tbl):
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "nil"); b.append(x)
    pr = tbl._tbl.tblPr
    nxt = next((pr.find(qn(f"w:{t}")) for t in ("shd", "tblLayout", "tblCellMar", "tblLook")
                if pr.find(qn(f"w:{t}")) is not None), None)
    nxt.addprevious(b) if nxt is not None else pr.append(b)


def cell_border(c, side):
    tcPr = c._tc.get_or_add_tcPr()
    bs = tcPr.find(qn("w:tcBorders"))
    if bs is None:
        bs = OxmlElement("w:tcBorders"); tcPr.append(bs)
    x = OxmlElement(f"w:{side}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "8"); x.set(qn("w:color"), "000000")
    bs.append(x)


def answer_text(n, a):
    a = _s(a)
    if not a:
        return []
    chunks = [c.strip() for c in a.split("\n") if c.strip()]
    if not chunks[0].startswith("("):
        chunks[0] = f"({dev(n)}) {chunks[0]}"
    return chunks


def qa_table(d, lq):
    house, kind = labels(lq)
    parts = [x for x in lq.get("parts") or [] if isinstance(x, dict)]
    t = d.add_table(rows=3 + len(parts), cols=2)
    t.autofit = False; no_borders(t)
    for j, w in enumerate(COLS):
        t.columns[j].width = Twips(w)
    # row 0: subject (bold, centre; rule below)
    a, b = t.cell(0, 0), t.cell(0, 1)
    m = a.merge(b)
    _p(m, _s(lq.get("subject")) or BLANK, bold=True, align=WA.CENTER, after=4, p=m.paragraphs[0])
    for c in (t.cell(0, 0), t.cell(0, 1)):
        cell_border(c, "bottom")
    # row 1: number / members / house  |  minister / portfolio (rule below)
    mem = [_s(x) for x in lq.get("members") or [] if _s(x)] or [f"श्री. {BLANK} ({BLANK})"]
    left = [f"{kind} प्रश्न क्रमांक {_s(lq.get('number')) or BLANK}."] + mem + [f"{house} सदस्य."]
    cell_lines(t.cell(1, 0), left, align=WA.LEFT)
    cell_lines(t.cell(1, 1), [_s(lq.get("minister")) or f"श्री. {BLANK}", _s(lq.get("portfolio")) or f"{BLANK} मंत्री"],
               align=WA.LEFT)
    for c in (t.cell(1, 0), t.cell(1, 1)):
        cell_border(c, "bottom")
    # row 2: the opening of the question
    port = _s(lq.get("portfolio")) or f"{BLANK} मंत्री"
    cell_lines(t.cell(2, 0), [f"सन्माननीय {port} पुढील गोष्टींचा खुलासा करतील काय :-"], align=WA.LEFT)
    cell_lines(t.cell(2, 1), [""])
    # rows 3..: (n) question | (n) answer
    for i, pt in enumerate(parts, 1):
        q = _s(pt.get("q")) or BLANK
        cell_lines(t.cell(2 + i, 0), [f"({dev(i)}) {q}"], first_hanging=True)
        cell_lines(t.cell(2 + i, 1), answer_text(i, pt.get("a")) or [""], first_hanging=True)
    for r in t.rows:
        for j, w in enumerate(COLS):
            r.cells[j].width = Twips(w)
    return t


def supp_block(d, lq):
    """पुरवणी टिप्पणी on a new page [GADT 13.9; MMOP 16.3(3)]."""
    house, kind = labels(lq)
    p = _p(d, _s(lq.get("supplementary_heading")) or "पुरवणी टिप्पणी", bold=True, align=WA.CENTER, after=2)
    p.paragraph_format.page_break_before = True
    _p(d, f"{house} {kind} प्रश्न क्रमांक {_s(lq.get('number')) or BLANK}", align=WA.CENTER, after=2)
    _p(d, f"“{(_s(lq.get('subject')) or BLANK).rstrip('.')}”", align=WA.CENTER, after=10)
    for it in lq.get("supplementary") or []:
        if isinstance(it, dict) and it.get("table"):
            if _s(it.get("title")):
                _p(d, it["title"].strip(), bold=True, after=2)
            rows = it["table"]; n = len(rows[0]); w = TEXT_W // n
            t = d.add_table(rows=len(rows), cols=n)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False; borders(t)
            for i, row in enumerate(rows):
                for j in range(n):
                    c = t.cell(i, j)
                    _p(c, str(row[j]) if j < len(row) else "", bold=(i == 0), align=WA.CENTER if i == 0 else WA.LEFT,
                       after=2, p=c.paragraphs[0])
                    c.width = Twips(w)
            _p(d, after=4)
        elif _s(it):
            for ch in [c.strip() for c in it.split("\n") if c.strip()]:
                _p(d, ch, first=720, after=6, line=1.5)


def build(spec, out):
    lq = spec["lq"]
    d = docx.Document(); fix_styles(d)
    s = d.sections[0]
    s.page_width, s.page_height = Twips(11906), Twips(16838)
    s.left_margin, s.right_margin = Twips(1800), Twips(1440)
    s.top_margin, s.bottom_margin = Twips(1134), Twips(1135)
    # [GADT 13.2] the date of answer at the very top
    _p(d, f"उत्तराचा दिनांक : {_s(lq.get('answer_date')) or BLANK}", align=WA.RIGHT, after=8)
    qa_table(d, lq)
    rp = _p(d, before=6, after=10, left=3500, line=1.0)
    pf = rp.paragraph_format; pf.right_indent = Twips(3500)
    rule_below(rp)
    # forwarding endorsement [GADT 13.9]
    right = 4300
    for ln in (f"क्रमांक {_s(lq.get('ref_no')) or BLANK}", _s(lq.get("department")) or DEF_DEPT,
               "मंत्रालय, मुंबई ४०० ०३२", f"दिनांक : {_s(lq.get('date'))}".rstrip()):
        _p(d, ln, align=WA.LEFT, left=right, after=0)
    _p(d, f"प्रत, {_s(lq.get('copies')) or BLANK} प्रतींसह सचिव, महाराष्ट्र विधानमंडळ सचिवालय, विधानभवन, मुंबई यांजकडे "
          f"त्यांच्या क्रमांक {_s(lq.get('ls_ref')) or BLANK}, दिनांक {_s(lq.get('ls_date')) or BLANK} च्या संदर्भात अग्रेषित.",
       first=720, before=10, after=24, line=1.5)
    _p(d, _s(lq.get("signer")) or f"( {BLANK} )", align=WA.CENTER, left=right, after=0)
    _p(d, _s(lq.get("designation")) or DEF_DESIG, align=WA.CENTER, left=right, after=0)
    if has_supplementary(lq):
        supp_block(d, lq)
    st = d.settings.element
    for e in st.findall(qn("w:mirrorMargins")):
        st.remove(e)
    d.save(out); clean_docx(out, spec.get("doc_author"))


def lint(spec):
    import lint_lq
    probs = lint_lq.lint_lq(spec)
    for p in probs:
        print(p)
    for w in lint_lq.warnings_lq(spec):
        print("WARN " + w)
    if probs:
        print("LINT FAILED — fix the 'lq' block (tools/lint_lq.py); nothing built", file=sys.stderr)
    return not probs


def main(spec_path, outdir, pre, do_lint=True):
    with open(spec_path, encoding="utf-8-sig") as f:
        spec = json.load(f)
    if not isinstance(spec, dict) or not isinstance(spec.get("lq"), dict):
        print(f"{spec_path}: no 'lq' block — nothing built (legislature question answer only)", file=sys.stderr)
        return 1
    if do_lint and not lint(spec):
        return 1
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{pre}_LQ_Answer.docx")
    build(spec, out)
    bad = bad_font_runs(docx.Document(out))
    print(out, "bad-font runs:", bad)
    to_pdf(out, outdir)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if a != "--no-lint"]
    if len(args) != 3:
        sys.exit(__doc__)
    sys.exit(main(*args, do_lint="--no-lint" not in sys.argv and os.environ.get("LINT_SKIP") != "1"))
