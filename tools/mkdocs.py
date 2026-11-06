#!/usr/bin/env python3
"""mkdocs.py spec.json OUTDIR PREFIX
Builds <PREFIX>_Note.docx and <PREFIX>_Letter.docx in the Section's own format, cloned from
zip samples: C R 66-2025 टिप्पणी (z7_0274) and पत्र (z7_0273). Font DVOT-SurekhMR everywhere.

spec.json:
{
 "note": {
   "first": "text of para 1 (starts after a tab; ends with ... सादर.)",
   "paras": [{"table": [["अ.क्र.","..."],["1","..."]], "bold_last": false} or "para text without number (numbering 2., 3., ... added automatically)", ...],
   "sub": {"<para index in paras, 0-based>": ["(१) ...", "(२) ..."]},   # optional sub-points after that para (§4.37: one issue per numbered para, its facts here); a leading "(1)" / "(अ)" / "1)" marker hangs at 1 cm, the text at 2 cm
   "closing": "सबब, उपरोक्त माहिती तक्त्याच्या स्वरूपात कळविण्याबाबतच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल.",
              # or (no letter): "सबब, ... प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."  (PROPOSAL_SOP Step 4)
   "signers": ["(अ.मा. वसू)", "क. अ. (अ.का.)", "अ.स. (श्री. वडनेरकर)", "उ.वि.स. नि. उ.स. (श्री. बोंद्रे)", "सचिव व व. वि. स. (श्री. बिले)"]
              # add "अ.मु.स. (वित्त)" only when the file goes to Finance (INSTRUCTIONS §4.6)
 },
 "desk": "law-desk6",      # optional (C30, 03.11.2026) — desk profile tools/desks/<id>.json (note header, signer chain,
                           # letterhead lines, phone / e-mail, ref no. form, signature, copy line); absent = law-desk6
 "doc_author": "<name>",   # optional — Word author / last-modified-by (else env DOC_AUTHOR, else empty); tools/clean_meta.py
 "related": [ {"heading": "<GR/नियम/पूर्वोदाहरण शीर्षक>", "text": ["<verbatim extract paragraph>", "..."], "source": "<क्रमांक, दिनांक, पृ., परि.>"} ],   # शेवटी 'संबंधित माहिती'
 "letter": {   # optional — omit when no letter is needed (note only)
   "ref_no": "संकिर्ण-2026/प्र.क्र.116/का.6", "date": "__.__.2026",
   "to": ["प्रबंधक (वित्त व अर्थसंकल्प),", "उच्च न्यायालय (अपील शाखा),", "मुंबई."],
   "subject": "....", "refs": ["१) ...", "२) ..."],
   "intro": "उपरोक्त विषयाबाबत ... कळविण्यात येते की,",
   "points": ["1) ...", "2) ..."],
   "closing": "तरी, ... ही विनंती.",
   "enclosure": "",   # optional 'सोबत - ...'
   "reminder": 1,     # optional — स्मरणपत्र-N (INSTRUCTIONS §4.21): "स्मरणपत्र-1" printed above the क्रमांक line;
                      # refs[0] "या कार्यासनाचे समक्रमांकाचे पत्र दि. __"; intro "… माहिती अद्याप अप्राप्त आहे. … ही विनंती."
   "copies": ["प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, ठाणे यांना आवश्यक कार्यवाहीसाठी"]
                      # optional — "प्रत : <each>" above "प्रत : निवड नस्ती" (INSTRUCTIONS §4.22: letter via the High Court
                      # asking information from a District Judge)
 },
 # letter "kind": "do" — अर्धशासकीय पत्र (D.O. letter; GAD "टिप्पणी लेखन व पत्रव्यवहार" परि. 12.26–12.29 + specimen
 #   book p.43–44; NPM परिशिष्ट-30; MMOP 2023 §10.1(7), Appendix 10.9 — docs/FORMS_RESEARCH_DO_UO.md):
 #   {"kind": "do", "ref_no": "संकिर्ण-2026/____/प्र.क्र.____/का.6", "date": "__.__.2026",
 #    "from": {"name": "...", "designation": "..."},   # optional — default: desk signer name / post (e.g. "अवर सचिव")
 #    "subject": "...", "refs": [],                      # refs optional (12.26: may be written apart)
 #    "salutation": "प्रिय श्री. ____,",                 # or "प्रिय महोदय," (12.28)
 #    "body": ["first para (unnumbered)", "2nd para (printed '2.')", ...],   # first person (MMOP §10.1(7)(a))
 #    "to": ["श्री. ____,", "<पदनाम>,", "<कार्यालय>,", "<ठिकाण>."]}          # addressee at the foot, left
 #   prints: "अ.शा.पत्र क्र. <ref_no>" / department / address / "दिनांक : <date>" (right), sender name (bold) and
 #   designation (left), "विषय : …" (bold, centre), salutation, body, "शुभेच्छा", "आपला स्नेहांकित,", "(<name>)", addressee;
 #   no letterhead / logos, no "प्रत" line (the specimens have none). Works in "letter" and in "letters".
 # note "uo" — अनौपचारिक संदर्भ (the note sent to another department): {"to": "वित्त विभाग", "no": "____",
 #   "date": "____", "desk": optional (default desk profile, e.g. "का.6"), "from": optional (default desk department)}
 #   prints after the signers (left; NPM परिशिष्ट-8 form foot, book p.77): "<from>" / "<to>ाकडे अनौपचारिक संदर्भ
 #   कार्यासन <desk>" / "क्रमांक <no> दिनांक <date>"; the last para must send the file to that department (lint).
 "letters": [{...}, {...}]   # optional (INSTRUCTIONS §4.28, 03.11.2026) — several letters in one run, e.g. a letter and a
                      # स्मरणपत्र (each the same format as "letter"); built after "letter" (if both are given) in this order:
                      # <PREFIX>_Letter.docx, <PREFIX>_Letter_2.docx, … — build_note_letter.py puts each on a new page
}"""
import re
import sys, json, copy, os
import docx
from docx.oxml.ns import qn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean_meta import clean_docx  # noqa: E402 — C27 §4: blank core/app properties
from desk import desk_of, contact_line, sign_name as _sign_name, blank as _blank  # noqa: E402 — C30 desk profiles

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


TABLE_PT = 11   # table text size (pt)
CELL_PAD_CM = 0.40   # Word's default left + right cell margins (0.19 cm each) + the border
_ZERO = set(range(0x0900, 0x0903)) | {0x093A, 0x093C, 0x094D, 0x0962, 0x0963} | set(range(0x0941, 0x0949)) \
    | set(range(0x0951, 0x0958))
_HALF = {0x0903, 0x093E, 0x093F, 0x0940, 0x0949, 0x094A, 0x094B, 0x094C}


def text_em(s):
    """Approximate printed width of s in em (generous, so a token measured here fits in DVOT-SurekhMR / FreeSerif):
    Devanagari letters 0.62, spacing vowel signs 0.3, non-spacing signs / virama 0, digits 0.55, '.' ',' etc. 0.3."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o == 0x094D: w -= 0.27; continue   # virama: the consonant before it is a half form in a conjunct
        if o in _ZERO or o in (0x200C, 0x200D): continue
        if o in _HALF: w += 0.3
        elif 0x0900 <= o <= 0x097F: w += 0.62
        elif ch.isdigit(): w += 0.55
        elif ch in ".,:;'!|()[]/-": w += 0.3
        elif ch == " ": w += 0.25
        elif ch.isupper(): w += 0.68
        else: w += 0.52
    return w


def _em_cm(em, pt=TABLE_PT):
    return em * pt * 2.54 / 72.0


def text_width_cm(sect):
    """Text width of the section (page width - left - right margins - gutter) in cm; 15 cm when unknown."""
    try:
        sz, mar = sect.find(qn("w:pgSz")), sect.find(qn("w:pgMar"))
        tw = int(sz.get(qn("w:w"))) - int(mar.get(qn("w:left"))) - int(mar.get(qn("w:right"))) \
            - int(mar.get(qn("w:gutter")) or 0)
        return tw * 2.54 / 1440.0
    except Exception:
        return 15.0


def col_widths(rows, total):
    """Column widths (cm) summing to `total`: each column at least as wide as its longest unbreakable token of the data
    rows (dates DD.MM.YYYY, numbers, amounts like 1,23,456, words — never split); then, smallest need first and within
    60% of the spare width, as wide as its longest header word (header words split at "/" and "-"; long headers wrap);
    the rest shared in proportion to the length of the column's longest cell text."""
    ncol = max(len(r) for r in rows)
    cell = lambda r, j: str(r[j]) if j < len(r) else ""
    words = lambda t, hdr: re.split(r"[\s/-]+" if hdr else r"\s+", t)
    tok = lambda rs, j, hdr: max([_em_cm(text_em(w) * 1.08) for r in rs for w in words(cell(r, j), hdr) if w] or [0.0])
    data = rows[1:] or rows
    mins = [max(tok(data, j, False), 0.35) + CELL_PAD_CM for j in range(ncol)]
    if sum(mins) >= total:   # cannot fit even the data tokens: scale down (rare — very many columns)
        return [w * total / sum(mins) for w in mins]
    if len(rows) > 1:   # a column left empty to be filled in (letter's information table): room to write by hand
        for j in range(ncol):
            if not any(cell(r, j).strip() for r in data):
                mins[j] = max(mins[j], min(3.0, total / ncol))
        if sum(mins) >= total:
            return [w * total / sum(mins) for w in mins]
    budget = 0.6 * (total - sum(mins))
    need = [max(0.0, tok(rows[:1], j, True) + CELL_PAD_CM - mins[j]) for j in range(ncol)]
    for j in sorted(range(ncol), key=lambda j: need[j]):
        if need[j] <= budget:
            mins[j] += need[j]; budget -= need[j]
    nat = [max(mins[j], max(_em_cm(text_em(cell(r, j))) for r in rows) + CELL_PAD_CM) for j in range(ncol)]
    if sum(nat) <= total:   # everything fits on one line: share the spare width in proportion to the natural widths
        return [w * total / sum(nat) for w in nat]
    room, want = total - sum(mins), [nat[j] - mins[j] for j in range(ncol)]
    return [mins[j] + room * want[j] / sum(want) for j in range(ncol)]


def add_table(d, sect, rows, bold_last=False):
    """rows: list of lists (first row = header, bold). Bordered grid, DVOT-SurekhMR. Fixed layout, table width = the
    section's text width; column widths from content (col_widths) on the grid and on every cell."""
    from docx.oxml import OxmlElement
    from docx.shared import Cm, Pt
    ncol = max(len(r) for r in rows)
    t = d.add_table(rows=len(rows), cols=ncol)
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}"); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "000000"); b.append(x)
    tblPr.append(b)
    total = text_width_cm(sect)
    ws = col_widths(rows, total)
    t.autofit = False   # w:tblLayout fixed
    tw = tblPr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW"); tblPr.append(tw)
    tw.set(qn("w:w"), str(int(round(Cm(total).twips)))); tw.set(qn("w:type"), "dxa")
    for j in range(ncol): t.columns[j].width = Cm(ws[j])   # w:gridCol
    for i, r in enumerate(rows):
        for j in range(ncol):
            c = t.cell(i, j); c.text = ""; c.width = Cm(ws[j])   # w:tcW
            para = c.paragraphs[0]
            pf = para.paragraph_format; pf.space_before = Pt(0); pf.space_after = Pt(0); pf.line_spacing = 1.0
            pf.left_indent = Cm(0); pf.first_line_indent = Cm(0)
            run = para.add_run(str(r[j]) if j < len(r) else "")
            setfont(run); run.font.size = Pt(TABLE_PT)
            if i == 0 or (bold_last and i == len(rows) - 1): run.bold = True
    sect.addprevious(t._tbl)
    return t

UO_LABEL = "अनौपचारिक संदर्भ"   # GAD कार्यालयीन कार्यपद्धती नियमपुस्तिका, परिशिष्ट-8, book p.77 (PDF p.84) — foot of the
# form: "……… विभागाकडे अनौपचारिक संदर्भ ……… कार्यासन ………" / "क्रमांक ……… दिनांक ……… १९ ………" (docs/FORMS_RESEARCH_DO_UO.md)


def uo_dept_to(to):
    """"वित्त विभाग" -> "वित्त विभागाकडे" (the form's "……… विभागाकडे"); unknown -> "____ विभागाकडे"."""
    t = re.sub(r"\s*विभाग\s*$", "", _blank(to))
    return f"{t} विभागाकडे"


def uo_lines(spec):
    """The U.O. block of a note sent to another department as an अनौपचारिक संदर्भ (spec note "uo": {"to", "no", "date",
    "desk", "from"}) — the lines of the NPM परिशिष्ट-8 form foot: [sender department (the form's "———विभाग"),
    "<to> विभागाकडे अनौपचारिक संदर्भ कार्यासन <desk>", "क्रमांक <no> दिनांक <date>"]; [] without "uo".
    Unknown values -> "____"; "from" / "desk" default to the desk profile's department / desk."""
    n = spec.get("note") if isinstance(spec, dict) else None
    u = n.get("uo") if isinstance(n, dict) else None
    if not isinstance(u, dict) or not u:
        return []
    dk = desk_of(spec)
    frm = u.get("from") if isinstance(u.get("from"), str) and u["from"].strip() else dk["department"]
    desk = u.get("desk") if isinstance(u.get("desk"), str) and u["desk"].strip() else dk.get("desk")
    return [_blank(frm), f"{uo_dept_to(u.get('to'))} {UO_LABEL} कार्यासन {_blank(desk)}",
            f"क्रमांक {_blank(u.get('no'))} दिनांक {_blank(u.get('date'))}"]


SUB_MARK_RE = re.compile(r"^\s*(\(\s*(?:[0-9०-९]{1,3}|[अ-औ]|[a-z]{1,4})\s*\)|[0-9०-९]{1,3}\))\s*")


def build_note(spec, out):
    from docx.shared import Cm
    d = docx.Document(NOTE_T); body, P, sect = fresh(d); fix_styles(d)
    n = spec["note"]
    # prototypes from final version in the sample (items 38..53)
    hdr, first, numbered, close = P[38], P[39], P[40], P[46]
    sign = P[48]; blank = P[47]
    add(body, sect, hdr, d, desk_of(spec)["note_header"])
    add(body, sect, first, d, " \t" + n["first"])
    k = 2
    subs = n.get("sub", {})
    last = None   # the last body paragraph before the closing (None after a table)
    for i, t in enumerate(n["paras"]):
        if isinstance(t, dict):
            add_table(d, sect, t["table"], t.get("bold_last", False)); last = None; continue
        last = add(body, sect, numbered, d, f"{k}.\t{t}"); k += 1
        for s in subs.get(str(i), []):
            # INSTRUCTIONS §4.37 D1 (05.11.2026): a sub-point "(1) …" / "(अ) …" / "1) …" hangs like the office's Word
            # numbering — marker at 1 cm, text and its wrapped lines at 2 cm; an item without a marker stays as before
            m = SUB_MARK_RE.match(s)
            if m:
                last = add(body, sect, numbered, d, f"{m.group(1)}\t{s[m.end():]}", left=Cm(2.0), first=Cm(-1.0))
            else:
                last = add(body, sect, numbered, d, f"\t{s}", left=Cm(1.0), first=Cm(-0.0))
    # The signatures never stand alone on a page: the last body para ("सबब, …"), the blank line and every signer line but
    # the last keep with the next paragraph (Word / LibreOffice move them together; no page break is forced).
    closing = n.get("closing", "मान्यतेस्तव सादर.")
    if last is not None and "सबब" not in closing:   # a bare "मान्यतेस्तव सादर." closing: the "सबब, …" para is the one before
        last.paragraph_format.keep_with_next = True; last.paragraph_format.keep_together = True
    cp = add(body, sect, close, d, "\t " + closing)
    cp.paragraph_format.keep_with_next = True; cp.paragraph_format.keep_together = True
    add(body, sect, blank, d, " ").paragraph_format.keep_with_next = True
    # §4.6 (Abhi 05.11.2026, his own note page): the first `signers_right` lines of the desk chain — the preparer's name
    # "(अ.मा. वसू)" (not bold, `signers_plain`) and post "क. अ. (अ.का.)" — sit together on the right, centred on each other,
    # with no blank line between them; the rest of the chain stays on the left.
    dk = desk_of(spec)
    nright = int(dk.get("signers_right", 0) or 0)
    plain = set(dk.get("signers_plain", []) or [])
    for i, s in enumerate(n["signers"]):
        sp = add(body, sect, sign, d, s, bold=False if i in plain else None)
        sp.paragraph_format.right_indent = Cm(0)
        sp.paragraph_format.keep_with_next = i < len(n["signers"]) - 1
        if i < nright:
            sp.paragraph_format.left_indent = Cm(4); sp.alignment = 1   # right block, lines centred
            if i < nright - 1:
                sp.paragraph_format.line_spacing = 1.0   # the two right lines sit together (template: 2.5 lines)
            if i > 0:
                sp.paragraph_format.space_before = Cm(0)
            if i < nright - 1:
                sp.paragraph_format.space_after = Cm(0)
        else:
            sp.paragraph_format.left_indent = Cm(0); sp.alignment = 0   # left
    ul = uo_lines(spec)
    if ul:   # अनौपचारिक संदर्भ (note "uo"): the U.O. block at the foot of the note, left (docs/FORMS_RESEARCH_DO_UO.md)
        add(body, sect, blank, d, " ")
        for t in ul:
            up = add(body, sect, close, d, t, bold=False, left=Cm(0), first=Cm(0))
            up.paragraph_format.right_indent = Cm(0); up.alignment = 0
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
                # "… (पृ.9-10/प.वि.)" prints as "(…, पृ.9-10/प.वि.)" — no doubled ")" and no word "स्रोत" (Abhi 03.11.2026;
                # verify reverses it)
                src = re.sub(r"\s*\((पृ\.[^()]*?/\s*प\.वि\.)\)\s*$", r", \1", it["source"])
                add(body, sect, numbered, d, f"\t({src})", left=Cm(0.8))
    nomirror(d); d.save(out); clean_docx(out, spec.get("doc_author"))

def letters_of(spec):
    """The letters of a spec in build order: "letter" (one object), then each of "letters" (list; §4.28)."""
    out = [spec["letter"]] if isinstance(spec, dict) and spec.get("letter") else []
    ls = spec.get("letters") if isinstance(spec, dict) else None
    return out + [x for x in (ls if isinstance(ls, list) else []) if x]


def letter_file(od, pre, i):
    """i = 0-based position in letters_of(): <PREFIX>_Letter.docx, <PREFIX>_Letter_2.docx, …"""
    return os.path.join(od, f"{pre}_Letter.docx" if i == 0 else f"{pre}_Letter_{i + 1}.docx")


DO_REF_LABEL = "अ.शा.पत्र क्र."   # GADT p.43 (PDF p.47) specimen: "अ.शा.पत्र क्र. इएसटी १२८०/२८४-का.१७"
DO_WISH = "शुभेच्छा"              # GADT 12.27 + specimen p.44 (PDF p.48)
DO_SUBSCRIPTION = "आपला स्नेहांकित,"   # GADT 12.27 + specimen p.44 (PDF p.48)


def do_sender(L, dk):
    """(name, designation) of the D.O. letter's sender: letter.from, else the desk profile's signer (name without the
    brackets of sign_name; designation = sign_post up to the first ','); unknown -> "____"."""
    fr = L.get("from") if isinstance(L.get("from"), dict) else {}
    name = fr.get("name") if isinstance(fr.get("name"), str) and fr["name"].strip() else \
        re.sub(r"^\(\s*|\s*\)$", "", (dk.get("sign_name") or "").strip())
    desig = fr.get("designation") if isinstance(fr.get("designation"), str) and fr["designation"].strip() else \
        (dk.get("sign_post") or "").split(",")[0]
    return _blank(name), _blank(desig)


def build_do_letter(spec, out, L):
    """अर्धशासकीय पत्र (letter "kind": "do") — layout of the GAD specimen, टिप्पणी लेखन व पत्रव्यवहार परि. 12.26–12.29,
    book p.43–44 (PDF p.47–48); MMOP 2023 §10.1(7), Appendix 10.9 (PDF p.64, 76); docs/FORMS_RESEARCH_DO_UO.md.
    No letterhead / logos and no copy line (the specimen has none). Page setup = LETTER_TEMPLATE."""
    from docx.shared import Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH as WA
    d = docx.Document(LET_T); body, P, sect = fresh(d); fix_styles(d)
    dk = desk_of(spec)["letter"]
    RIGHT = Cm(5.5)   # the specimen's right-hand block (number, department, address, date); wide enough for the ref no.
    SUB = Cm(10.5)    # "आपला स्नेहांकित," and the signature name (right, specimen p.44)

    def line(proto, text, bold=None, left=None, align=None):
        p = add(body, sect, proto, d, text, bold=bold, left=left, first=Cm(0))
        p.paragraph_format.right_indent = Cm(0)
        if align is not None:
            p.alignment = align
        for r in p.runs:   # Devanagari bold is the complex-script flag w:bCs (as in the template's bold lines)
            rpr = r._element.get_or_add_rPr()
            for e in rpr.findall(qn("w:bCs")): rpr.remove(e)
            if bold:
                r.bold = True   # w:b in schema order; w:bCs right after it
                rpr.find(qn("w:b")).addnext(rpr.makeelement(qn("w:bCs"), {}))
        return p
    # right-hand block: D.O. number, department, address, date
    line(P[5], f"{DO_REF_LABEL} {L['ref_no']}", left=RIGHT)
    for ln in dk["office"]:
        line(P[5], ln, left=RIGHT)
    line(P[5], f"दिनांक : {L.get('date') or '____'}", left=RIGHT)
    add(body, sect, P[6], d, "")
    # sender (top left): name, designation
    name, desig = do_sender(L, dk)
    line(P[5], name, bold=True, left=Cm(0))
    line(P[5], desig + ".", left=Cm(0))
    add(body, sect, P[10], d, "")

    def ctr(p):
        p.alignment = WA.CENTER
        pf = p.paragraph_format; pf.left_indent = Cm(0); pf.right_indent = Cm(0); pf.first_line_indent = Cm(0)
        for r in p.runs: r.bold = True; setfont(r)
        return p
    ctr(add(body, sect, P[11], d, "विषय : " + L["subject"].strip(), bold=True))
    refs = [r for r in (L.get("refs") or []) if isinstance(r, str) and r.strip()]   # 12.26: संदर्भ may be written apart
    if refs:
        ctr(add(body, sect, P[13], d, "संदर्भ : " + refs[0].strip(), bold=True))
        for r in refs[1:]: ctr(add(body, sect, P[13], d, r.strip(), bold=True))
    add(body, sect, P[15], d, "")
    line(P[17], (L.get("salutation") or "प्रिय श्री. ____,").strip(), bold=False, left=Cm(0))
    k = 0   # paragraphs: the first unnumbered, then "2.", "3." … (specimen p.43–44); a {"table": …} item is not counted
    for t in L.get("body") or []:
        if isinstance(t, dict):
            add_table(d, sect, t["table"], t.get("bold_last", False)); continue
        k += 1
        add(body, sect, P[17], d, ("\t" if k == 1 else f"\t{k}.  ") + t.strip())
    add(body, sect, P[19], d, "")
    line(P[17], DO_WISH, left=Cm(0))
    line(P[18], DO_SUBSCRIPTION, left=SUB)
    add(body, sect, P[19], d, "")
    add(body, sect, P[19], d, "")
    line(P[20], f"({name})", bold=True, left=SUB)
    add(body, sect, P[19], d, "")
    for ln in L.get("to") or []:   # addressee: name and designation at the foot, left (12.27)
        line(P[17], ln.strip(), bold=False, left=Cm(0))
    nomirror(d); d.save(out); clean_docx(out, spec.get("doc_author"))


def build_letter(spec, out, L=None):
    from docx.shared import Cm
    L = spec["letter"] if L is None else L
    if isinstance(L, dict) and L.get("kind") == "do":
        return build_do_letter(spec, out, L)
    d = docx.Document(LET_T); body, P, sect = fresh(d); fix_styles(d)
    dk = desk_of(spec)["letter"]   # C30: the desk profile (tools/desks/<id>.json; spec "desk", default law-desk6)
    # 0..4 letterhead (0 holds the two logo drawings) ; 5 ref/date ; 6 blank
    from docx.text.paragraph import Paragraph as _P
    for i in range(0, 2):
        body_el = copy.deepcopy(P[i]); sect.addprevious(body_el)
        for r in _P(body_el, d).runs: setfont(r)
    # department / address lines: the template paragraph itself when the profile line equals it (Desk-6), else its text
    for j, line in enumerate(dk["office"]):
        proto = P[2] if j == 0 else P[3]
        body_el = copy.deepcopy(proto); sect.addprevious(body_el)
        if ("".join(r.text for r in _P(proto, d).runs)) != line:
            settext(body_el, line, d)
        for r in _P(body_el, d).runs: setfont(r)
    em = copy.deepcopy(P[4]); sect.addprevious(em)
    from docx.text.paragraph import Paragraph
    pe = Paragraph(em, d);
    if pe.runs:
        r0 = pe.runs[0]
        for r in pe.runs[1:]: r._element.getparent().remove(r._element)
        r0.text = contact_line(desk_of(spec)); setfont(r0)   # unknown phone / e-mail -> "____"
    rem = L.get("reminder")
    if rem:  # §4.21 स्मरणपत्र: heading above the क्रमांक line (the Section's old reminders, e.g. C R 170/2024)
        n_rem = int(rem) if str(rem).isdigit() and int(rem) > 0 else 1
        add(body, sect, P[5], d, f"स्मरणपत्र-{n_rem}", bold=True)
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
    add(body, sect, P[20], d, "\t\t\t\t\t\t\t         " + _sign_name(dk.get("sign_name")))
    add(body, sect, P[21], d, "\t\t\t\t\t\t       " + _blank(dk.get("sign_post")))
    if L.get("enclosure"): add(body, sect, P[17], d, L["enclosure"])
    for cp in L.get("copies") or []:  # §4.22
        if isinstance(cp, str) and cp.strip(): add(body, sect, P[17], d, "प्रत : " + cp.strip())
    add(body, sect, P[17], d, "प्रत : " + dk["copy_file"])
    nomirror(d); d.save(out); clean_docx(out, spec.get("doc_author"))

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8-sig")); od, pre = sys.argv[2], sys.argv[3]
    build_note(spec, os.path.join(od, f"{pre}_Note.docx"))
    for i, L in enumerate(letters_of(spec)): build_letter(spec, letter_file(od, pre, i), L)
    print("ok", pre)
