#!/usr/bin/env python3
"""mkdocs.py spec.json OUTDIR PREFIX
Builds <PREFIX>_Note.docx and <PREFIX>_Letter.docx in the Section's own format, cloned from
zip samples: C R 66-2025 टिप्पणी (z7_0274) and पत्र (z7_0273). Font DVOT-SurekhMR everywhere.

spec.json:
{
 "note": {
   "first": "text of para 1 (starts after a tab; ends with ... सादर.)",
   "paras": [{"table": [["अ.क्र.","..."],["1","..."]], "bold_last": false} or "para text without number (numbering 2., 3., ... added automatically)", ...],
   "sub": {"<para index in paras, 0-based>": ["(१) ...", "(२) ..."]},   # optional lettered/numbered sub-points after that para
   "closing": "मान्यतेस्तव सादर.",
   "signers": ["का.अ. (श्री. वसू)", "अ.स. (        )", ...]
 },
 "related": [ {"heading": "<GR/नियम/पूर्वोदाहरण शीर्षक>", "text": ["<जसाच्या तसा उतारा परिच्छेद>", "..."], "source": "<क्रमांक, दिनांक, पृ., परि.>"} ],   # शेवटी 'संबंधित माहिती'
 "letter": {   # optional — omit when no letter is needed (note only)
   "ref_no": "संकिर्ण-2026/प्र.क्र.116/का.6", "date": "__.__.2026",
   "to": ["प्रबंधक (वित्त व अर्थसंकल्प),", "उच्च न्यायालय (अपील शाखा),", "मुंबई."],
   "subject": "....", "refs": ["१) ...", "२) ..."],
   "intro": "उपरोक्त विषयाबाबत ... कळविण्यात येते की,",
   "points": ["1) ...", "2) ..."],
   "closing": "तरी, ... ही विनंती.",
   "enclosure": ""    # optional 'सोबत - ...'
 }
}"""
import sys, json, copy, os
import docx
from docx.oxml.ns import qn

FONT = "DVOT-SurekhMR"
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
NOTE_T, LET_T = os.path.join(T, "NOTE_TEMPLATE.docx"), os.path.join(T, "LETTER_TEMPLATE.docx")

def setfont(run):
    rpr = run._element.get_or_add_rPr(); rf = rpr.get_or_add_rFonts()
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None: del rf.attrib[qn(a)]

def settext(p_el, text, doc, bold=None):
    """keep first run's formatting; replace text; drop other runs (keeps drawings untouched if text is None)."""
    from docx.text.paragraph import Paragraph
    p = Paragraph(p_el, doc)
    runs = p.runs
    if not runs:
        r = p.add_run(text)
    else:
        r = runs[0]
        for extra in runs[1:]:
            extra._element.getparent().remove(extra._element)
        r.text = text
    if bold is not None: r.bold = bold
    setfont(r)
    return p

def fix_styles(doc):
    for st in doc.styles:
        try:
            if st.font is not None and st.type in (1, 2):
                st.font.name = FONT
                rpr = st.element.get_or_add_rPr(); rf = rpr.get_or_add_rFonts()
                for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): rf.set(qn(a), FONT)
        except Exception: pass

def nomirror(doc):
    st = doc.settings.element
    for e in st.findall(qn("w:mirrorMargins")): st.remove(e)

def fresh(doc):
    body = doc.element.body
    protos = [copy.deepcopy(p) for p in body.findall(qn("w:p"))]
    for p in body.findall(qn("w:p")): body.remove(p)
    sect = body.find(qn("w:sectPr"))
    return body, protos, sect

def add(body, sect, proto, doc, text, bold=None, left=None, first=None):
    el = copy.deepcopy(proto); sect.addprevious(el)
    p = settext(el, text, doc, bold)
    if left is not None: p.paragraph_format.left_indent = left
    if first is not None: p.paragraph_format.first_line_indent = first
    return p


def add_table(d, sect, rows, bold_last=False):
    """rows: list of lists (first row = header, bold). Bordered grid, DVOT-SurekhMR."""
    from docx.oxml import OxmlElement
    ncol = max(len(r) for r in rows)
    t = d.add_table(rows=len(rows), cols=ncol)
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "000000"); b.append(x)
    tblPr.append(b)
    from docx.shared import Cm, Pt
    # column widths: serial column narrow, rest proportional to longest text (min 2 cm), total 16 cm
    lens = [max(len(str(r[j])) if j < len(r) else 0 for r in rows) for j in range(ncol)]
    first = 1.5 if ncol > 2 else 0
    rest = 16.0 - first
    wts = [max(l, 10) ** 0.5 for l in (lens[1:] if first else lens)]
    ws = ([first] if first else []) + [max(2.4, rest * w / sum(wts)) for w in wts]
    k = 16.0 / sum(ws); ws = [w * k for w in ws]
    t.autofit = False
    for j in range(ncol): t.columns[j].width = Cm(ws[j])
    for i, r in enumerate(rows):
        for j in range(ncol):
            c = t.cell(i, j); c.text = ""; c.width = Cm(ws[j])
            para = c.paragraphs[0]
            pf = para.paragraph_format; pf.space_before = Pt(0); pf.space_after = Pt(0); pf.line_spacing = 1.0
            pf.left_indent = Cm(0); pf.first_line_indent = Cm(0)
            run = para.add_run(str(r[j]) if j < len(r) else "")
            setfont(run); run.font.size = Pt(11)
            if i == 0 or (bold_last and i == len(rows) - 1): run.bold = True
    sect.addprevious(t._tbl)
    return t

def build_note(spec, out):
    from docx.shared import Cm
    d = docx.Document(NOTE_T); body, P, sect = fresh(d); fix_styles(d)
    n = spec["note"]
    # prototypes from final version in the sample (items 38..53)
    hdr, first, numbered, close = P[38], P[39], P[40], P[46]
    sign = P[48]; blank = P[47]
    add(body, sect, hdr, d, "विधि व न्याय विभाग/का.6")
    add(body, sect, first, d, " \t" + n["first"])
    k = 2
    subs = n.get("sub", {})
    for i, t in enumerate(n["paras"]):
        if isinstance(t, dict):
            add_table(d, sect, t["table"], t.get("bold_last", False)); continue
        add(body, sect, numbered, d, f"{k}.\t{t}"); k += 1
        for s in subs.get(str(i), []):
            add(body, sect, numbered, d, f"\t{s}", left=Cm(1.0), first=Cm(-0.0))
    add(body, sect, close, d, "\t " + n.get("closing", "मान्यतेस्तव सादर."))
    add(body, sect, blank, d, " ")
    for s in n["signers"]:
        sp = add(body, sect, sign, d, s)
        sp.paragraph_format.left_indent = Cm(0); sp.paragraph_format.right_indent = Cm(0)
        sp.alignment = 0  # left
    rel = spec.get("related", [])
    if rel:
        from docx.enum.text import WD_BREAK
        pb = add(body, sect, blank, d, "")
        pb.runs[0].add_break(WD_BREAK.PAGE) if pb.runs else pb.add_run().add_break(WD_BREAK.PAGE)
        add(body, sect, hdr, d, "संबंधित माहिती (संदर्भासाठी)", bold=True)
        for j, it in enumerate(rel, 1):
            add(body, sect, numbered, d, f"{j}.\t{it['heading']}", bold=True)
            for tx in it.get("text", []):
                add(body, sect, numbered, d, f"\t{tx}", left=Cm(0.8))
            if it.get("source"):
                add(body, sect, numbered, d, f"\t(स्रोत: {it['source']})", left=Cm(0.8))
    nomirror(d); d.save(out)

def build_letter(spec, out):
    from docx.shared import Cm
    d = docx.Document(LET_T); body, P, sect = fresh(d); fix_styles(d)
    L = spec["letter"]
    # 0..4 letterhead (0 holds the two logo drawings) ; 5 ref/date ; 6 blank
    from docx.text.paragraph import Paragraph as _P
    for i in range(0, 4):
        body_el = copy.deepcopy(P[i]); sect.addprevious(body_el)
        for r in _P(body_el, d).runs: setfont(r)
    em = copy.deepcopy(P[4]); sect.addprevious(em)
    from docx.text.paragraph import Paragraph
    pe = Paragraph(em, d);
    if pe.runs:
        r0 = pe.runs[0]
        for r in pe.runs[1:]: r._element.getparent().remove(r._element)
        r0.text = "दूरध्वनी क्र. :- ०२२-२२793230\t\t\t\t   Email ID :- lnjd.desk6-mh@mah.gov.in"; setfont(r0)
    add(body, sect, P[5], d, f"क्रमांक:-{L['ref_no']}                                  दिनांक  :- {L['date']}")
    add(body, sect, P[6], d, "")
    add(body, sect, P[7], d, "प्रति,")
    for line in L["to"]: add(body, sect, P[8], d, "\t" + line)
    add(body, sect, P[10], d, "")
    # विषय व संदर्भ: bold + centre (Abhi's standing rule)
    from docx.enum.text import WD_ALIGN_PARAGRAPH as WA
    def ctr(p):
        p.alignment = WA.CENTER
        pf = p.paragraph_format; pf.left_indent = Cm(0); pf.right_indent = Cm(0); pf.first_line_indent = Cm(0)
        for r in p.runs: r.bold = True; setfont(r)
        return p
    ctr(add(body, sect, P[11], d, "विषय :- " + L["subject"].strip(), bold=True))
    refs = L["refs"]
    if refs:
        ctr(add(body, sect, P[13], d, "संदर्भ :- " + refs[0].strip(), bold=True))
        for r in refs[1:]: ctr(add(body, sect, P[13], d, r.strip(), bold=True))
    add(body, sect, P[15], d, "")
    add(body, sect, P[16], d, "महोदय,")
    add(body, sect, P[17], d, "\t" + L["intro"])
    for pt in L["points"]:
        if isinstance(pt, dict):
            add_table(d, sect, pt["table"], pt.get("bold_last", False)); continue
        add(body, sect, P[17], d, pt, left=Cm(1.0), first=Cm(-1.0))
    if L.get("closing"): add(body, sect, P[17], d, "\t" + L["closing"])
    add(body, sect, P[18], d, "\t\t\t\t\t\t\t      \t     आपला,")
    add(body, sect, P[19], d, "")
    add(body, sect, P[20], d, "\t\t\t\t\t\t\t         ( राजेश वडनेरकर )")
    add(body, sect, P[21], d, "\t\t\t\t\t\t       अवर सचिव ,महाराष्ट्र शासन")
    if L.get("enclosure"): add(body, sect, P[17], d, L["enclosure"])
    add(body, sect, P[17], d, "प्रत : निवड नस्ती")
    nomirror(d); d.save(out)

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8")); od, pre = sys.argv[2], sys.argv[3]
    build_note(spec, os.path.join(od, f"{pre}_Note.docx"))
    if spec.get("letter"): build_letter(spec, os.path.join(od, f"{pre}_Letter.docx"))
    print("ok", pre)
