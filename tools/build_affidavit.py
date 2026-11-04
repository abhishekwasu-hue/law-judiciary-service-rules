#!/usr/bin/env python3
"""build_affidavit.py <spec.json> <outdir> <PREFIX> [--no-lint]
AFFIDAVIT IN REPLY (शपथपत्र) on behalf of the State in a Writ Petition (English, Bombay High Court, Appellate Side) from
the optional "affidavit" block of spec.json -> <outdir>/<PREFIX>_Affidavit.docx (+ <PREFIX>_Affidavit.pdf preview when
LibreOffice is available; paths printed). Refuses (exit 1) when the spec has no "affidavit" block, or when
tools/lint_affidavit.py finds errors (unless --no-lint or env LINT_SKIP=1).

Every element and its source (docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md, part A, has the verbatim lines with page numbers):
  [ASR III-1]  court line — Bombay High Court Appellate Side Rules, 1960, Chapter III, Rule 1 (entitling, per bench);
  [ASR III-2]  "In the matter of <proceeding and its number>" + names and descriptions of the parties (Rule 2);
  [ASR III-4]  every paragraph numbered consecutively, one distinct portion of the subject each (Rule 4);
  [ASR III-5]  the declarant states which paragraphs are from his own knowledge and which on belief, with the grounds
               of belief (Rule 5) — printed through the Rule 10 declaration;
  [ASR III-10] the solemn declaration (Rule 10 form): "I … abovenamed do solemnly declare that what is stated above in
               paragraph … is true to my own knowledge and that what is stated in the remaining paragraphs is true to
               the best of my information which I obtained from the following sources:- … I believe the information to
               be true for the following reasons :- … Solemnly declare at … above said this … day of … 20…",
               "(Signature)", "Before me," and the officer's block "Solemnly affirmed before me by … who is identified
               before me by … whom I personally know. This … day of … 20… High Court, Appellate Side, Bombay.
               Assistant Registrar." (the em dash of the printed rule is written ":-", INSTRUCTIONS §4.27 (उ));
  [ASR XVII-11/12] the answer to rule nisi is an affidavit; "affidavit in reply" (Chapter XVII, Rules 10(i), 11, 12);
  [ASR XVII-10(ii)] paper-book layout: A4, double space, font size 14, inner margin 5 cm, outer margin 3 cm, pages
               numbered, "every tenth line shall be numbered in the margin" ("paper_book": false switches the line
               numbers off). Font: DVOT-SurekhMR on every run (INSTRUCTIONS §4.2; the rule names Times New Roman /
               Georgia — open point O1 of the research file);
  [CPC 16-A]   opening "I, …, … state on solemn affirmation as follows:-" (Code of Civil Procedure, 1908, First
               Schedule, Appendix E, Form No. 16-A, L&J reprint p. 511) — written "… do hereby state on solemn
               affirmation as under:-";
  [OS 102]     "Advocate for …" under the jurat (Bombay High Court Original Side Rules, Form No. 102);
  [RCLAG 58(6)(e)] the counter affidavit is sworn "by the competent officer authorised to do so by the administrative
               department" (Rules for the Conduct of the Legal Affairs of Government, 1984) and [MMOP 3.3] Joint
               Secretary / Deputy Secretary "affirm affidavits in High courts" (Maharashtra Manual of Office
               Procedures, 2023, PDF p. 19) — the authority paragraph;
  [SECTION]    the Section's own parawise drafts (two Writ Petitions, 2025-2026; names never copied): the label form
               "Para No.1", "Para No.5 (a) to (e)", "Ground (a)", "Prayer Clauses (a) to (h)", the "Grounds" separator,
               the "on behalf of Respondent Nos. 1 and 2 i.e. the State of Maharashtra, through …" wording, and the
               prayer "The Petition is devoid of merits and liable to be dismissed. Hence, it is prayed that the same
               may be dismissed." (the State's stand "सदर याचिका फेटाळण्यात यावी" in the Section's letter to the GP).

"affidavit": {
  "bench": "bombay" | "nagpur" | "aurangabad" | "goa" | "kolhapur",   # [ASR III-1]; default "bombay"
  "court": "...",                         # optional; replaces the Rule 1 line (e.g. a future bench)
  "case": "WRIT PETITION NO. ____ OF 2026",
  "petitioners": ["Shri. ____, aged ____, working as ____, ____"],     # names and descriptions [ASR III-2]
  "respondents": ["The State of Maharashtra, through the Principal Secretary, Law and Judiciary Department, Mantralaya,
                   Mumbai 400 032", ...],
  "on_behalf_of": "Respondent Nos. 1 and 2",          # whose affidavit (title, authority para, advocate line)
  "title": "...",                         # optional; default "AFFIDAVIT IN REPLY ON BEHALF OF <ON_BEHALF_OF>"
  "deponent": {"name": "____", "age": "____", "designation": "____",
               "office": "Law and Judiciary Department, Government of Maharashtra, Mantralaya, Mumbai 400 032"},
                                          # "age" optional (printed "aged about <age> years" only when given)
  "authority": "...",                     # optional; replaces the default authority paragraph (para 1)
  "paras": ["preliminary submission", ...],           # numbered paragraphs before the parawise reply
  "reply_heading": "PARAWISE REPLY",      # optional
  "reply": [{"para": "1" | "5 (a) to (e)" | "Ground (a)" | "Prayer Clauses (a) to (h)", "reply": "..."},
            {"section": "Grounds"}, ...], # omitted -> the spec's "parawise"."paras" (their "remarks") are used
  "prayer": "...",                        # optional; default = the Section's prayer sentence [SECTION]
  "knowledge_paras": "1 to 3",            # optional; default "1 to <last>" (all paragraphs)
  "sources": "the official record of the ____ Department",           # optional; default "____"
  "belief_reasons": "...",                # optional; default "____"
  "place": "Mumbai", "day": "____", "month_year": "____ 2026",        # optional
  "identified_by": "____", "advocate_for": "...",                     # optional; advocate_for default = on_behalf_of
  "paper_book": true                      # optional; false = no line numbers
}
A numeric reply label ("1", "21 to 24", "5 (a) to (e)") prints as "Para No.<label>"; any other label as given.
"\\n" inside a reply / paragraph = a new (un-numbered) paragraph."""
import json
import os
import shutil
import subprocess
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH as WA
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_parawise import FONT, bad_font_runs, fix_styles, para_label, setfont  # noqa: E402
from clean_meta import clean_docx  # noqa: E402 — C27 §4: blank core/app properties

# [ASR III-1] entitling per bench (verbatim, without the quotation marks of the rule)
COURTS = {
    "bombay": "In the High Court of Judicature, Appellate Side, Bombay.",
    "nagpur": "In the High Court of Judicature, Bombay, at Nagpur",
    "aurangabad": "In the High Court of Judicature, Bombay, at Aurangabad",
    "goa": "In the High Court of Judicature, Bombay, at Panaji, Goa.",
    "kolhapur": "In the High Court of Judicature, Bombay, Circuit Bench at Kolhapur",
}
# [ASR III-10] the officer's place line under the jurat (the rule's form names the Appellate Side, Bombay)
OFFICE_LINE = {"bombay": "High Court, Appellate Side, Bombay."}
DEF_OFFICE = "Law and Judiciary Department, Government of Maharashtra, Mantralaya, Mumbai 400 032"
DEF_REPLY_HEAD = "PARAWISE REPLY"
# [SECTION] verbatim from the Section's parawise draft (prayer row)
DEF_PRAYER = "The Petition is devoid of merits and liable to be dismissed. Hence, it is prayed that the same may be dismissed."
BLANK = "____"
SIZE = 14            # [ASR XVII-10(ii)] font size 14
LINE = 2.0           # [ASR XVII-10(ii)] double space
FIRST = Cm(1.27)     # first-line indent of a numbered paragraph's continuation text


def _s(x):
    return x.strip() if isinstance(x, str) else ""


def court_line(af):
    return _s(af.get("court")) or COURTS.get(_s(af.get("bench")).lower() or "bombay", COURTS["bombay"])


def title_of(af):
    return _s(af.get("title")) or f"AFFIDAVIT IN REPLY ON BEHALF OF {(_s(af.get('on_behalf_of')) or BLANK).upper()}"


def petitioners(af):
    p = af.get("petitioners")
    if isinstance(p, str):
        p = [p]
    if not p and _s(af.get("petitioner")):
        p = [af["petitioner"]]
    return [_s(x) for x in (p or []) if _s(x)] or [BLANK]


def deponent_sentence(af):
    """[CPC 16-A] "I, …, … do hereby state on solemn affirmation as under:-" (first person, [OS 193/194] occupation and
    place of work)."""
    dp = af.get("deponent") if isinstance(af.get("deponent"), dict) else {}
    name = _s(dp.get("name")) or BLANK
    age = _s(dp.get("age"))
    desig = _s(dp.get("designation")) or BLANK
    office = (_s(dp.get("office")) or DEF_OFFICE).rstrip(",.")
    agep = f", aged about {age} years" if age else ""
    return f"I, {name}{agep}, working as {desig}, {office}, do hereby state on solemn affirmation as under:-"


def authority_text(af):
    """[RCLAG 58(6)(e)] / [MMOP 3.3]: the deponent is the competent officer authorised by the administrative department."""
    if _s(af.get("authority")):
        return af["authority"].strip()
    dp = af.get("deponent") if isinstance(af.get("deponent"), dict) else {}
    desig = _s(dp.get("designation")) or BLANK
    ob = _s(af.get("on_behalf_of")) or BLANK
    return (f"I am working as {desig} in the {(_s(dp.get('office')) or DEF_OFFICE).split(',')[0].strip()} and I am the "
            f"competent officer authorised to affirm this affidavit on behalf of {ob}. I have perused the record of the "
            f"case maintained in the Department and I am conversant with the facts of the case. I am filing this "
            f"affidavit in reply to the Writ Petition.")


def reply_items(spec):
    af = spec["affidavit"]
    if isinstance(af.get("reply"), list) and af["reply"]:
        return af["reply"]
    pw = spec.get("parawise") if isinstance(spec.get("parawise"), dict) else {}
    out = []
    for it in pw.get("paras") or []:   # the Section's parawise remarks become the parawise reply (its practice)
        if isinstance(it, dict) and _s(it.get("section")):
            out.append({"section": it["section"]})
        elif isinstance(it, dict):
            out.append({"para": it.get("para", ""), "reply": it.get("remarks", "")})
    return out


def _pp(d, text="", bold=False, align=WA.JUSTIFY, left=None, first=None, after=0, before=0, keep=False, size=SIZE,
        line=LINE):
    p = d.add_paragraph()
    pf = p.paragraph_format; pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = line
    if left is not None: pf.left_indent = Cm(left)
    if first is not None: pf.first_line_indent = first
    if keep: pf.keep_with_next = True
    if align is not None: p.alignment = align
    if text:
        setfont(p.add_run(text), size, bold)
    else:   # empty paragraph: its mark carries the font/size too
        rpr = p._p.get_or_add_pPr().makeelement(qn("w:rPr"), {})
        rf = rpr.makeelement(qn("w:rFonts"), {qn("w:" + a): FONT for a in ("ascii", "hAnsi", "cs", "eastAsia")})
        sz = rpr.makeelement(qn("w:sz"), {qn("w:val"): str(size * 2)})
        rpr.append(rf); rpr.append(sz); p._p.get_or_add_pPr().append(rpr)
    return p


def parties(d, lines, label):
    """[ASR III-2] names and descriptions of the parties; '… <label>' right-aligned under the last line."""
    for ln in lines:
        _pp(d, ln, align=WA.JUSTIFY, line=1.5)
    _pp(d, "… " + label, bold=True, align=WA.RIGHT, after=6, line=1.5)


def numbered(d, n, text, label=None):
    """[ASR III-4] '<n>.' + tab + text; '\\n' = a following un-numbered paragraph."""
    chunks = [c.strip() for c in str(text or "").split("\n") if c.strip()] or [BLANK]
    p = _pp(d, left=1.27, first=Cm(-1.27))
    setfont(p.add_run(f"{n}.\t"), SIZE)
    if label:
        setfont(p.add_run(f"{label}: "), SIZE, True)
    setfont(p.add_run(chunks[0]), SIZE)
    for c in chunks[1:]:
        _pp(d, c, left=1.27, first=FIRST)


def footer_page_no(section):
    """[ASR XVII-10(ii)] pages numbered consecutively: centred PAGE field (no other text)."""
    p = section.footer.paragraphs[0]; p.alignment = WA.CENTER
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = setfont(p.add_run(), 11)
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)


def line_numbers(section):
    """[ASR XVII-10(ii)] "Every tenth line shall be numbered in the margin." -> w:lnNumType countBy=10 (continuous)."""
    sp = section._sectPr
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:countBy"), "10"); ln.set(qn("w:restart"), "continuous"); ln.set(qn("w:distance"), "283")
    order = ("w:pgNumType", "w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg", "w:textDirection",
             "w:bidi", "w:rtlGutter", "w:docGrid")
    nxt = next((sp.find(qn(t)) for t in order if sp.find(qn(t)) is not None), None)
    nxt.addprevious(ln) if nxt is not None else sp.append(ln)


def build(spec, out):
    af = spec["affidavit"]
    d = docx.Document(); fix_styles(d)
    d.styles["Normal"].font.size = Pt(SIZE)
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)              # A4
    s.left_margin, s.right_margin = Cm(5.0), Cm(3.0)              # inner 5 cm, outer 3 cm
    s.top_margin = s.bottom_margin = Cm(2.0)
    width = 21.0 - 5.0 - 3.0
    footer_page_no(s)
    if af.get("paper_book", True) is not False:
        line_numbers(s)
    bench = _s(af.get("bench")).lower() or "bombay"
    case = _s(af.get("case")) or BLANK
    # cause title
    _pp(d, court_line(af), bold=True, align=WA.CENTER, line=1.5)
    _pp(d, f"In the matter of {case}", bold=True, align=WA.CENTER, after=10, line=1.5)
    pets = petitioners(af)
    parties(d, [f"{i}. {x}" for i, x in enumerate(pets, 1)] if len(pets) > 1 else pets,
            "Petitioners" if len(pets) > 1 else "Petitioner")
    _pp(d, "Versus", bold=True, align=WA.CENTER, before=4, after=6, line=1.5)
    rs = [_s(r) for r in af.get("respondents") or [] if _s(r)] or [BLANK]
    parties(d, [f"{i}. {r}" for i, r in enumerate(rs, 1)] if len(rs) > 1 else rs,
            "Respondents" if len(rs) > 1 else "Respondent")
    _pp(d, title_of(af), bold=True, align=WA.CENTER, before=10, after=10, keep=True, line=1.5)
    # opening sentence (un-numbered) and the numbered paragraphs
    _pp(d, deponent_sentence(af), first=FIRST)
    n = 0
    n += 1; numbered(d, n, authority_text(af))
    for x in af.get("paras") or []:
        if _s(x):
            n += 1; numbered(d, n, x)
    items = reply_items(spec)
    if items:
        _pp(d, _s(af.get("reply_heading")) or DEF_REPLY_HEAD, bold=True, align=WA.CENTER, before=6, keep=True)
    for it in items:
        if isinstance(it, dict) and _s(it.get("section")):
            _pp(d, it["section"].strip(), bold=True, align=WA.CENTER, keep=True); continue
        if not isinstance(it, dict):
            continue
        n += 1; numbered(d, n, it.get("reply") or it.get("remarks") or "", label=para_label(it.get("para")))
    n += 1; numbered(d, n, _s(af.get("prayer")) or DEF_PRAYER)
    last = n
    # [ASR III-10] solemn declaration
    _pp(d, before=6)
    kp = _s(af.get("knowledge_paras")) or (f"1 to {last}" if last > 1 else "1")
    dp = af.get("deponent") if isinstance(af.get("deponent"), dict) else {}
    name = _s(dp.get("name")) or BLANK
    _pp(d, f"I, {name}, the Deponent abovenamed do solemnly declare that what is stated above in paragraphs {kp} is "
           f"true to my own knowledge and that what is stated in the remaining paragraphs is true to the best of my "
           f"information which I obtained from the following sources:- {(_s(af.get('sources')) or BLANK).rstrip('.')}.",
        first=FIRST, keep=True)
    _pp(d, f"I believe the information to be true for the following reasons :- "
           f"{(_s(af.get('belief_reasons')) or BLANK).rstrip('.')}.", first=FIRST, keep=True)
    place = _s(af.get("place")) or "Mumbai"
    day = _s(af.get("day")) or BLANK
    my = _s(af.get("month_year")) or f"{BLANK} 20__"
    _pp(d, f"Solemnly declare at {place} above said this {day} day of {my}", first=FIRST, keep=True)
    _pp(d, keep=True, line=1.0)
    blk = width - 7.5   # the right-hand block of the Rule 10 form (7.5 cm wide)
    _pp(d, "(Signature)", align=WA.LEFT, left=blk + 1.5, line=1.0, keep=True)
    _pp(d, "Before me,", align=WA.LEFT, left=blk + 1.5, line=1.0, after=8, keep=True)
    ident = _s(af.get("identified_by")) or BLANK
    office_line = OFFICE_LINE.get(bench) or f"High Court, {court_line(af).replace('In the High Court of Judicature, ', '').rstrip('.')}."
    for ln in ("Assistant Registrar,", "Solemnly affirmed before me", f"by {name}", "who is identified before me",
               f"by {ident}", "whom I personally know.", f"This {BLANK} day of {my}", office_line):
        _pp(d, ln, align=WA.LEFT, left=blk, line=1.0, keep=True)
    _pp(d, "Assistant Registrar.", align=WA.LEFT, left=blk + 1.5, line=1.0, before=4, keep=True)
    _pp(d, line=1.0, keep=True)
    _pp(d, f"Advocate for {_s(af.get('advocate_for')) or _s(af.get('on_behalf_of')) or BLANK}", align=WA.LEFT, line=1.0,
        before=12)
    st = d.settings.element
    for e in st.findall(qn("w:mirrorMargins")):
        st.remove(e)
    d.save(out); clean_docx(out, spec.get("doc_author"))
    return last


def lint(spec):
    import lint_affidavit
    probs = lint_affidavit.lint_affidavit(spec)
    for p in probs:
        print(p)
    for w in lint_affidavit.warnings_affidavit(spec):
        print("WARN " + w)
    if probs:
        print("LINT FAILED — fix the 'affidavit' block (tools/lint_affidavit.py); nothing built", file=sys.stderr)
    return not probs


def to_pdf(out, outdir):
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        print("WARNING: soffice not found — no PDF preview (docx is complete)", file=sys.stderr); return
    import tempfile   # private LibreOffice profile: parallel conversions do not collide
    prof = tempfile.mkdtemp(prefix="lo_affidavit_")
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


def main(spec_path, outdir, pre, do_lint=True):
    with open(spec_path, encoding="utf-8-sig") as f:
        spec = json.load(f)
    if not isinstance(spec, dict) or not isinstance(spec.get("affidavit"), dict):
        print(f"{spec_path}: no 'affidavit' block — nothing built (affidavit in reply only)", file=sys.stderr)
        return 1
    if do_lint and not lint(spec):
        return 1
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{pre}_Affidavit.docx")
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
