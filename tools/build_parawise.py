#!/usr/bin/env python3
"""build_parawise.py <spec.json> <outdir> <PREFIX> [--no-lint]
Court-case PARAWISE REMARKS (English, INSTRUCTIONS §3.1) from the optional "parawise" block of spec.json ->
<outdir>/<PREFIX>_Parawise.docx (+ <PREFIX>_Parawise.pdf preview when LibreOffice is available; paths printed).
Refuses (exit 1) when the spec has no "parawise" block, or when tools/lint_parawise.py finds errors (unless --no-lint or
env LINT_SKIP=1). The court-mode NOTE and LETTER come from the same spec's "note"/"letter" via tools/build_note_letter.py.

Two layouts ("parawise"."layout"):

DEFAULT = the Section's own office format (Abhi, 03.11.2026: "format parawise cha asach asto" / "ok tar format mi dilelya
parawise cha thewa"; reference: the Section's parawise of W.P. in C R 103-2026 — only its FORMAT is used, never its
content; docs/COURT_AND_ORDERS_RESEARCH.md B8 "SUPERSEDED"):
  A4, margins L 3.175 / R 2.54 / T,B 2.0 cm, no header/footer, line spacing 1.5, font DVOT-SurekhMR on every run;
  title "Para wise Explanation in <case>." (16 pt bold, centre);
  party line "<petitioner> Vs. <respondent>" (16 pt bold);
  "Parawise submissions on behalf of <on_behalf_of>, in respect of contentions raised by the present petitioner(s),
  in this petition." (13 pt) — or "intro" (the whole sentence) when given;
  ONE table "Sr. No. | Para No. | Remarks" (12 pt; header bold; widths 959 / 1276 / 6080 twips, indent 567 twips,
  single borders): one row per para / sub-para / ground / formal para / prayer clauses, Sr. No. 1., 2., … ;
  an item {"section": "Grounds"} prints an un-numbered separator row (text bold, centre, in the Remarks column);
  then a closing line of asterisks.
"parawise": {
  "case": "WRIT PETITION NO. ____ OF 2026",
  "petitioner": "Shri. ____ & Ors.",                  # as in the petition's cause title
  "respondent": "The State of Maharashtra and Ors.",  # optional; this is the default
  "on_behalf_of": "Respondent Nos. 1 and 2 i.e. the State of Maharashtra, through the Principal Secretary, Law and
                   Judiciary Department, Mantralaya, Mumbai",
  "intro": "...",                                     # optional; replaces the whole "Parawise submissions …" sentence
  "paras": [{"para": "1" | "5 (a) to (e)" | "21 to 24" | "Ground (a)" | "Prayer Clauses (a) to (h)",
             "averment": "optional, NOT printed (the drafter's own pointer to the petition text)",
             "remarks": "..."},                      # "\n" = a new paragraph inside the cell
            {"section": "Grounds"}, ...]
}
  A numeric label ("1", "21 to 24", "5 (a) to (e)") prints as "Para No.<label>"; any other label prints as given.

"layout": "rule58" = the earlier layout (kept; used only when the spec says so):
Layout rule58 (docs/COURT_AND_ORDERS_RESEARCH.md decision B8 original; Rules for the Conduct of the Legal
Affairs of Government, 1984: Rule 58(3) parawise report on all points, Rule 58(4)(a) recommendation, Rule 58(4) Note (ii)
elaborate factual position + copies of rules/orders, Rule 32 reply to each paragraph, Rule 58(6) the Government Pleader
drafts the counter affidavit):
  court / case no. (bold, centre); parties "<petitioner> … Petitioner(s) / Versus / 1. … 2. … … Respondent(s)";
  title "PARAWISE REMARKS OF RESPONDENT NO. <n> (<department>)"; Subject; Submitted to;
  1. Brief facts (numbered); 2. Parawise remarks — table "Para No. | Averments in the petition (in brief) | Remarks of the
  Department"; 3. Documents enclosed (numbered; "Nil" when none); 4. Recommendation (Rule 58(4)(a)); [Verification —
  only when "verification": true]; Place/Date + signature block. Font DVOT-SurekhMR on all four rFonts attributes of
  every run (§4.2), incl. the footer page number.

"parawise": {
  "layout": "rule58",
  "court": "IN THE HIGH COURT OF JUDICATURE AT BOMBAY, BENCH AT AURANGABAD",
  "case": "WRIT PETITION NO. ____ OF 2026",
  "petitioner": "...", "respondents": ["The State of Maharashtra, through ...", "..."],
  "respondent_no": "2",                       # which respondent the State/department is
  "department": "Law and Judiciary Department",   # optional; default = this; used in the title
  "subject": "... (English)",
  "prepared_for": "Assistant Government Pleader, High Court of Judicature at Bombay, Bench at Aurangabad",
  "relief_sought": "... (English, in brief: what the petitioner prays for)",   # optional (03.11.2026, INSTRUCTIONS §4.30): printed
                                              # after "Submitted to" as "Relief sought:" so the reader sees the demand first
  "background": ["brief facts (English)", ...,
                 {"title": "Chronology", "table": [["Date", "Event"], ["__.__.____", "..."]]}],
                                              # optional (03.11.2026, INSTRUCTIONS §4.30): a background item may be a table (chronology,
                                              # service, amounts; first row = header, 2-6 columns, plain text cells);
                                              # tables are not numbered, string items keep their (1), (2) … numbers
  "paras": [{"para": "1" | "1 to 3", "averment": "brief", "remarks": "elaborate factual position with rule/GR refs"}],
  "enclosures": ["Copy of Government Resolution ... dated ...", ...],     # Rule 58(4) / Note (ii)
  "recommendation": "oppose" | "not oppose", "recommendation_reason": "...",
  "officer": "( ____ )",                      # optional; department officer to brief the GP
  "designation": ["Under Secretary to Government,", "Law and Judiciary Department,", "Mantralaya, Mumbai."],  # optional
  "place": "Mumbai", "date": "__.__.2026",    # optional
  "verification": false                       # optional; true adds a verification paragraph with blanks
}"""
import os
import shutil
import subprocess
import sys
import json

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH as WA
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re

from docx.shared import Cm, Length, Pt, Twips

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from clean_meta import clean_docx  # noqa: E402 — C27 §4: blank core/app properties
FONT = "DVOT-SurekhMR"
TITLE = "PARAWISE REMARKS OF RESPONDENT NO. {n} ({dept})"
HEAD = ["Para No.", "Averments in the petition (in brief)", "Remarks of the Department"]
WIDTHS = (2.4, 5.4, 8.7)   # cm; text width 16.5 cm (A4, 2.25 cm side margins)
DEF_DEPT = "Law and Judiciary Department"
DEF_DESIG = ["Under Secretary to Government,", "Law and Judiciary Department,", "Mantralaya, Mumbai."]
SECTIONS = ("1. Brief facts", "2. Parawise remarks", "3. Documents enclosed", "4. Recommendation")
REC_TEXT = {
    "oppose": "The Department recommends that the petition be opposed (Rule 58(4)(a) of the Rules for the Conduct of "
              "the Legal Affairs of Government, 1984).",
    "not oppose": "The Department recommends that the petition be not opposed (Rule 58(4)(a) of the Rules for the "
                  "Conduct of the Legal Affairs of Government, 1984).",
}
VERIFY = ("I, ____, ____ in the {dept}, Government of Maharashtra, Mantralaya, Mumbai, do hereby state that what is "
          "stated in the foregoing paragraphs is true to the best of my knowledge and information derived from the "
          "official record, and I believe the same to be true.")


def setfont(run, size=None, bold=None):
    rpr = run._element.get_or_add_rPr(); rf = rpr.get_or_add_rFonts()
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    return run


def fix_styles(d):
    for st in d.styles:
        try:
            if st.type in (1, 2) and st.font is not None:
                st.font.name = FONT
                rf = st.element.get_or_add_rPr().get_or_add_rFonts()
                for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                    rf.set(qn(a), FONT)
        except Exception:
            pass
    d.styles["Normal"].font.size = Pt(12)


def para(container, text="", bold=False, align=None, size=12, before=0, after=6, left=None, first=None, keep=False):
    p = container.add_paragraph()
    pf = p.paragraph_format; pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = 1.15
    if left is not None: pf.left_indent = Cm(left)
    if first is not None: pf.first_line_indent = Cm(first)
    if keep: pf.keep_with_next = True
    if align is not None: p.alignment = align
    if text:
        setfont(p.add_run(text), size, bold)
    return p


def right_tab(p, pos_cm=16.5):
    tabs = p._p.get_or_add_pPr().makeelement(qn("w:tabs"), {})
    t = tabs.makeelement(qn("w:tab"), {qn("w:val"): "right", qn("w:pos"): str(int(pos_cm * 567))})
    tabs.append(t); p._p.get_or_add_pPr().append(tabs)


def party(d, lines, label):
    """lines left, '… <label>' at the right margin on the last line."""
    for i, ln in enumerate(lines):
        p = para(d, after=0 if i < len(lines) - 1 else 6, left=0.0)
        setfont(p.add_run(ln), 12)
        if i == len(lines) - 1:
            right_tab(p); setfont(p.add_run("\t… " + label), 12, True)


def borders(tbl):
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "000000")
        b.append(x)
    pr = tbl._tbl.tblPr
    nxt = next((pr.find(qn(f"w:{t}")) for t in ("shd", "tblLayout", "tblCellMar", "tblLook")
                if pr.find(qn(f"w:{t}")) is not None), None)
    nxt.addprevious(b) if nxt is not None else pr.append(b)   # schema order of w:tblPr


def cell_text(c, text, bold=False, align=None):
    for r in list(c.paragraphs[0].runs):   # a new cell has one empty paragraph; no empty runs left behind
        r._r.getparent().remove(r._r)
    chunks = str(text).split("\n")
    for k, ch in enumerate(chunks):
        p = c.paragraphs[0] if k == 0 else c.add_paragraph()
        pf = p.paragraph_format; pf.space_before = Pt(1); pf.space_after = Pt(3); pf.line_spacing = 1.1
        if align is not None: p.alignment = align
        elif not bold: p.alignment = WA.JUSTIFY
        setfont(p.add_run(ch), 11, bold)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr(); h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)


def remarks_table(d, paras):
    t = d.add_table(rows=1 + len(paras), cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False; borders(t)
    for j, w in enumerate(WIDTHS):
        t.columns[j].width = Cm(w)
    for j, h in enumerate(HEAD):
        cell_text(t.cell(0, j), h, bold=True, align=WA.CENTER)
    repeat_header(t.rows[0])
    for i, it in enumerate(paras, 1):
        vals = (it.get("para", ""), it.get("averment", ""), it.get("remarks", ""))
        for j, v in enumerate(vals):
            cell_text(t.cell(i, j), v, align=WA.CENTER if j == 0 else None)
    for r in t.rows:
        for j, w in enumerate(WIDTHS):
            r.cells[j].width = Cm(w)
    return t


def facts_table(d, item):
    """INSTRUCTIONS §4.30 (03.11.2026): an optional table inside "1. Brief facts" — {"title"?: str, "table": [[header…], [row…], …]}."""
    if _s(item.get("title")):
        para(d, item["title"].strip(), bold=True, left=1.0, before=2, after=2, keep=True)
    rows = item["table"]; n = len(rows[0]); w = 15.5 / n
    t = d.add_table(rows=len(rows), cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False; borders(t)
    for i, row in enumerate(rows):
        for j in range(n):
            cell_text(t.cell(i, j), row[j] if j < len(row) else "", bold=(i == 0), align=WA.CENTER if i == 0 else WA.LEFT)
            t.cell(i, j).width = Cm(w)
    repeat_header(t.rows[0])
    para(d, after=2)
    return t


def _s(x):
    return x.strip() if isinstance(x, str) else ""


def footer_page_no(section):
    p = section.footer.paragraphs[0]; p.alignment = WA.CENTER
    setfont(p.add_run("Page "), 10)
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = setfont(p.add_run(), 10)
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)


def build_rule58(spec, out):
    pw = spec["parawise"]
    d = docx.Document(); fix_styles(d)
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = Cm(2.25); s.top_margin = Cm(2.0); s.bottom_margin = Cm(2.0)
    footer_page_no(s)
    dept = (pw.get("department") or DEF_DEPT).strip()
    para(d, pw["court"].strip(), bold=True, align=WA.CENTER, after=2)
    para(d, pw["case"].strip(), bold=True, align=WA.CENTER, after=12)
    party(d, [pw["petitioner"].strip()], "Petitioner(s)")
    para(d, "Versus", bold=True, align=WA.CENTER, before=2, after=6)
    rs = [r.strip() for r in pw["respondents"]]
    party(d, [f"{i}. {r}" for i, r in enumerate(rs, 1)] if len(rs) > 1 else rs, "Respondent(s)")
    para(d, TITLE.format(n=pw["respondent_no"].strip(), dept=dept), bold=True, align=WA.CENTER, before=10, after=8)
    heads = [("Subject", "subject"), ("Submitted to", "prepared_for")]
    if _s(pw.get("relief_sought")):
        heads.append(("Relief sought", "relief_sought"))   # §4.30: the demand / relief stated first
    for lab, key in heads:
        p = para(d, align=WA.JUSTIFY, left=3.0, first=-3.0, after=4)
        setfont(p.add_run(f"{lab}:\t"), 12, True); setfont(p.add_run(pw[key].strip()), 12)
    # 1. Brief facts (strings numbered; §4.30 table items unnumbered)
    para(d, SECTIONS[0], bold=True, before=8, after=4, keep=True)
    bg = [b for b in pw.get("background") or [] if (isinstance(b, dict) and b.get("table")) or _s(b)]
    i = 0
    for b in bg:
        if isinstance(b, dict):
            facts_table(d, b); continue
        i += 1
        p = para(d, align=WA.JUSTIFY, left=1.0, first=-0.75, after=4)
        setfont(p.add_run(f"({i})\t{b.strip()}"), 12)
    if not bg:
        para(d, "Nil.", left=1.0)
    # 2. table
    para(d, SECTIONS[1], bold=True, before=8, after=4, keep=True)
    remarks_table(d, pw["paras"])
    # 3. enclosures
    para(d, SECTIONS[2], bold=True, before=10, after=4, keep=True)
    enc = [e for e in pw.get("enclosures") or [] if e.strip()]
    for i, e in enumerate(enc, 1):
        p = para(d, align=WA.JUSTIFY, left=1.0, first=-0.75, after=2)
        setfont(p.add_run(f"{i}.\t{e.strip()}"), 12)
    if not enc:
        para(d, "Nil.", left=1.0)
    # 4. recommendation
    para(d, SECTIONS[3], bold=True, before=10, after=4, keep=True)
    rec = pw["recommendation"].strip().lower()
    # "____" (or anything without a record basis) = left blank for the Section to fill (lint WARN, never a KeyError)
    para(d, REC_TEXT.get(rec, "____"), align=WA.JUSTIFY, left=1.0, after=4)
    if (pw.get("recommendation_reason") or "").strip():
        para(d, pw["recommendation_reason"].strip(), align=WA.JUSTIFY, left=1.0, after=4)
    if pw.get("verification") is True:
        para(d, "Verification", bold=True, before=10, after=4, keep=True)
        para(d, VERIFY.format(dept=dept), align=WA.JUSTIFY, left=1.0)
    # place/date + signature
    para(d, f"Place: {(pw.get('place') or 'Mumbai').strip()}", before=18, after=0)
    para(d, f"Date: {(pw.get('date') or '__.__.____').strip()}", after=18)
    desig = pw.get("designation") or DEF_DESIG
    desig = [desig] if isinstance(desig, str) else desig
    for ln in [(pw.get("officer") or "( ____ )").strip()] + [x.strip() for x in desig]:
        para(d, ln, align=WA.CENTER, left=8.5, after=0)
    st = d.settings.element
    for e in st.findall(qn("w:mirrorMargins")):
        st.remove(e)
    d.save(out); clean_docx(out, spec.get("doc_author"))


# ---------------- DEFAULT layout: the Section's office format (Abhi, 03.11.2026) ----------------
OFF_HEAD = ("Sr. No.", "Para No.", "Remarks")
OFF_WIDTHS = (959, 1276, 6080)          # twips, as in the Section's format
OFF_TBL_IND = 567                        # twips
OFF_REMARK_FIRST = Pt(30)                # first-line indent of each remarks paragraph
OFF_STARS = "    " + "*" * 67           # closing line under the table
DEF_RESP = "The State of Maharashtra and Ors."
NUM_LABEL = re.compile(r"\d+[A-Za-z]?(?:\s*(?:to|-|–|,|and)\s*\d+[A-Za-z]?)*"
                       r"(?:\s*\([A-Za-z0-9]+\)(?:\s*(?:to|-|–|,|and)\s*\([A-Za-z0-9]+\))*)?")


def layout(pw):
    """"rule58" only when the spec says so; otherwise the Section's office format (default)."""
    return "rule58" if isinstance(pw, dict) and str(pw.get("layout") or "").strip().lower() == "rule58" else "office"


def para_label(lab):
    """'1' / '21 to 24' / '5 (a) to (e)' -> 'Para No.1' …; 'Ground (a)', 'Prayer Clauses …', 'Para No.3' as given."""
    lab = str(lab or "").strip()
    return f"Para No.{lab}" if NUM_LABEL.fullmatch(lab) else lab


def opara(container, text="", size=12, bold=False, align=WA.JUSTIFY, left=None, first=None, after=0, p=None):
    p = p if p is not None else container.add_paragraph()
    pf = p.paragraph_format; pf.space_before = Pt(0); pf.space_after = Pt(after); pf.line_spacing = 1.5
    if left is not None: pf.left_indent = Twips(left)
    if first is not None: pf.first_line_indent = first if isinstance(first, Length) else Twips(first)
    if align is not None: p.alignment = align
    if text:
        setfont(p.add_run(text), size, bold)
    else:   # empty paragraph: its mark carries the font/size too
        rpr = p._p.get_or_add_pPr().makeelement(qn("w:rPr"), {})
        rf = rpr.makeelement(qn("w:rFonts"), {qn("w:" + a): FONT for a in ("ascii", "hAnsi", "cs", "eastAsia")})
        sz = rpr.makeelement(qn("w:sz"), {qn("w:val"): str(size * 2)})
        rpr.append(rf); rpr.append(sz); p._p.get_or_add_pPr().append(rpr)
    return p


def ocell(c, text, bold=False, align=WA.JUSTIFY, left=None, first=None, after=0):
    chunks = [x for x in str(text or "").split("\n")] or [""]
    for k, ch in enumerate(chunks):
        p = c.paragraphs[0] if k == 0 else c.add_paragraph()
        opara(c, ch.strip(), 12, bold, align, left, first, after, p=p)


def office_table(d, items):
    rows = len(items) + 1
    t = d.add_table(rows=rows, cols=3)
    t.autofit = False; borders(t)
    pr = t._tbl.tblPr
    ind = pr.makeelement(qn("w:tblInd"), {qn("w:w"): str(OFF_TBL_IND), qn("w:type"): "dxa"})
    nxt = next((pr.find(qn(f"w:{x}")) for x in ("tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook")
                if pr.find(qn(f"w:{x}")) is not None), None)
    nxt.addprevious(ind) if nxt is not None else pr.append(ind)
    for j, w in enumerate(OFF_WIDTHS):
        t.columns[j].width = Twips(w)
    ocell(t.cell(0, 0), OFF_HEAD[0], bold=True, left=340)
    ocell(t.cell(0, 1), OFF_HEAD[1], bold=True, left=340)
    ocell(t.cell(0, 2), OFF_HEAD[2], bold=True, align=WA.CENTER)
    n = 0
    for i, it in enumerate(items, 1):
        if isinstance(it, dict) and _s(it.get("section")):
            ocell(t.cell(i, 0), ""); ocell(t.cell(i, 1), "")
            ocell(t.cell(i, 2), it["section"].strip(), bold=True, align=WA.CENTER, after=12)
            continue
        n += 1
        ocell(t.cell(i, 0), f"{n}.", left=340)
        ocell(t.cell(i, 1), para_label(it.get("para")), align=WA.LEFT)
        ocell(t.cell(i, 2), it.get("remarks", ""), first=OFF_REMARK_FIRST)
    for r in t.rows:
        for j, w in enumerate(OFF_WIDTHS):
            r.cells[j].width = Twips(w)
    return t


def build_office(spec, out):
    pw = spec["parawise"]
    d = docx.Document(); fix_styles(d)
    s = d.sections[0]
    s.page_width, s.page_height = Twips(11906), Twips(16838)
    s.left_margin, s.right_margin = Twips(1800), Twips(1440)
    s.top_margin, s.bottom_margin = Twips(1134), Twips(1135)
    s.header_distance = s.footer_distance = Twips(708)
    case = pw["case"].strip().rstrip(".")
    opara(d, f"Para wise Explanation in {case}.", 16, True, WA.CENTER, left=567, first=510)
    pet = pw["petitioner"].strip()
    resp = (_s(pw.get("respondent")) or DEF_RESP).rstrip()
    opara(d, f"{pet} Vs. {resp}", 16, True, WA.JUSTIFY, left=720, first=720)
    plural = bool(re.search(r"(?:&|\band)\s*(?:Ors|Others)\b", pet, re.I))
    intro = _s(pw.get("intro")) or (
        f"Parawise submissions on behalf of {(_s(pw.get('on_behalf_of')) or '____').rstrip(',.')}, in respect of contentions raised "
        f"by the present {'petitioners' if plural else 'petitioner'}, in this petition.")
    opara(d, intro, 13, False, WA.JUSTIFY, left=567, first=510)
    opara(d, "", 13)
    office_table(d, pw["paras"])
    opara(d, "", 12)
    opara(d, OFF_STARS, 12)
    st = d.settings.element
    for e in st.findall(qn("w:mirrorMargins")):
        st.remove(e)
    d.save(out); clean_docx(out, spec.get("doc_author"))


def build(spec, out):
    """Default: the Section's office format; "layout": "rule58" = the earlier Rule 58 layout."""
    (build_rule58 if layout(spec["parawise"]) == "rule58" else build_office)(spec, out)


def bad_font_runs(d):
    """text runs (body, headers, footers) whose four rFonts attributes are not all DVOT-SurekhMR."""
    roots = [d.element.body] + [part._element for s in d.sections for part in (s.header, s.footer)]
    bad = 0
    for root in roots:
        for el in root.iter(qn("w:r")):
            t = "".join(x.text or "" for x in el.iter(qn("w:t")))
            if not t.strip():
                continue
            rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
            if f is None or any(f.get(qn("w:" + k)) != FONT for k in ("ascii", "hAnsi", "cs", "eastAsia")):
                bad += 1
    return bad


def lint(spec):
    import lint_parawise
    probs = lint_parawise.lint_parawise(spec)
    for p in probs:
        print(p)
    for w in lint_parawise.warnings_parawise(spec):
        print("WARN " + w)
    if probs:
        print("LINT FAILED — fix the 'parawise' block (tools/lint_parawise.py); nothing built", file=sys.stderr)
    return not probs


def main(spec_path, outdir, pre, do_lint=True):
    with open(spec_path, encoding="utf-8-sig") as f:
        spec = json.load(f)
    if not isinstance(spec, dict) or not isinstance(spec.get("parawise"), dict):
        print(f"{spec_path}: no 'parawise' block — nothing built (court-case parawise remarks only)", file=sys.stderr)
        return 1
    if do_lint and not lint(spec):
        return 1
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{pre}_Parawise.docx")
    build(spec, out)
    bad = bad_font_runs(docx.Document(out))
    print(out, "bad-font runs:", bad)
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if soffice:
        import tempfile   # private LibreOffice profile: parallel conversions (other sessions/agents) do not collide
        prof = tempfile.mkdtemp(prefix="lo_parawise_")
        try:
            r = subprocess.run([soffice, "-env:UserInstallation=file://" + prof.replace(os.sep, "/"), "--headless",
                                "--convert-to", "pdf", "--outdir", outdir, out],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
        except subprocess.TimeoutExpired:
            r = subprocess.CompletedProcess([], 124, b"", b"soffice timed out after 180 s")
        finally:
            shutil.rmtree(prof, ignore_errors=True)
        pdf = os.path.splitext(out)[0] + ".pdf"
        if r.returncode == 0 and os.path.exists(pdf):
            print(pdf)
        else:
            print("WARNING: soffice preview failed (rc", r.returncode, ")", r.stderr.decode(errors="replace")[:300],
                  file=sys.stderr)
    else:
        print("WARNING: soffice not found — no PDF preview (docx is complete)", file=sys.stderr)
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
