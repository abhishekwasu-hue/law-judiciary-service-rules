#!/usr/bin/env python3
"""build_order.py <spec.json> <outdir> <PREFIX> [--no-lint]
Draft of a Government order of the Section (शासन निर्णय / शासन शुद्धिपत्रक / शासन परिपत्रक / ज्ञापन / अधिसूचना) ->
<outdir>/<PREFIX>_Order_Draft.docx (+ <PREFIX>_Order_Draft.pdf preview via LibreOffice, warning only if absent).
First runs tools/lint_order.py on the spec and stops (exit 1, problems printed) on errors; --no-lint or env LINT_SKIP=1
skips it. Exit 1 when the spec has no "order" / "orders" key or a built text run is not DVOT-SurekhMR
(ascii/hAnsi/cs/eastAsia).
Several drafts (INSTRUCTIONS §4.28, 03.11.2026 — e.g. a शासन निर्णय and an अधिसूचना ticked together): spec "orders":
[{order}, {order}, …] (each in the "order" format below; a single "order" is still accepted, and "order" + "orders" are
built in that order). ONE <PREFIX>_Order_Draft.docx; each order after the first starts on a new page.

Layout: docs/COURT_AND_ORDERS_RESEARCH.md decisions B1-B7 — official specimens (NPM परिशिष्ट 23-26; GADT 12.5-12.19,
R4 §2) filled with the Section's own wording (R3 (b)). Page setup and styles from tools/templates/LETTER_TEMPLATE.docx
(no letterhead logo: an order is not a letter); margins A4 2.5 / 2.0 / 1.5 / 1.5 cm.

spec.json (only the "order" / "orders" keys are read; other keys such as "note" may sit beside them):
{"order": {
  "type": "gr" | "corrigendum" | "circular" | "memo" | "notification",
  "subject": "...बाबत.",                          # printed on top (GR / शुद्धिपत्रक / परिपत्रक) or top centre (ज्ञापन);
                                                   #   not printed for अधिसूचना
  "ref_no": "संकिर्ण-2026/____/प्र.क्र.____/का.6",
  "date": "__.__.2026" | "____ नोव्हेंबर, 2026",
  "read": ["विधि व न्याय विभाग, शासन निर्णय क्र. ..., दि. ..."],   # "वाचा :-" (one item inline, several numbered 1) 2))
  "preamble": ["..."],                             # "प्रस्तावना :-" (GR only)
  "operative": ["first para (unnumbered)", "second para -> 2.", {"table": [["अ.क्र.", "..."], ["1", "..."]]},
                {"sub": ["(अ) ...", "(आ) ..."]}],  # numbered 2., 3., ...; tables / sub-points are not numbered
                                                   # notification: operative[0] follows "क्रमांक :- <ref_no>, "
  "concurrence": "हा शासन निर्णय वित्त विभागाच्या अनौपचारिक संदर्भ क्रमांक ..., दिनांक ... अन्वये प्राप्त सहमतीनुसार निर्गमित करण्यात येत आहे.",
  "website_line": true,                            # gr / corrigendum / circular: default true (decision B5, संकेतांक blank);
                                                   #   memo / notification: default false
  "signer": {"name": "( राजेश वडनेरकर )", "designation": "अवर सचिव, महाराष्ट्र शासन"},   # default per decision B4;
                                                   #   notification: "( ____ )" / "उप विधि सल्लागार-नि-उप सचिव"
  "copies": ["...", "निवड नस्ती (कार्यासन-6)"],    # "प्रत," list (memo "प्रत :-", notification "प्रत सादर अग्रेषित :-")
  "addressee": "जिल्हा न्यायाधीश-1, जिल्हा न्यायालय, ____",    # memo: printed "प्रति," after the signer
  "corrections": [{"read": "संदर्भाधीन शासन निर्णयातील परिच्छेद 2 मध्ये", "instead_of": "...", "read_as": "..."}],
                                                   # corrigendum: "<read> “<instead_of>” असे नमूद करण्यात आले आहे." /
                                                   #   "या ऐवजी" / "“<read_as>” असे वाचावे."; then para 2 "... इतर तरतुदी
                                                   #   कायम राहतील." (added unless an operative para already says it)
  "gazette_part": "भाग ____",                      # notification: "(महाराष्ट्र शासन राजपत्र, <part> मध्ये प्रसिद्ध करावी.)"
  "english": {"ref_no": "Misc-2026/____/C.R.____/D-VI", "date": "____ November, 2026",
              "operative": ["In exercise of the powers conferred by ...", {"table": [[...]]}],
              "signer": {"name": "( ____ )", "designation": "Deputy Legal Adviser-cum-Deputy Secretary"},
              "copies": ["...", "Select file (Desk-6)"]}   # notification: English version on a new page
}}
The tool adds the heading block, "वाचा :-", "प्रस्तावना :-", "शासन निर्णय :-" / "शासन शुद्धिपत्रक :-" / "परिपत्रक :-" /
"ज्ञापन :-" / "अधिसूचना", the website line, "महाराष्ट्राचे राज्यपाल यांच्या आदेशानुसार व नावाने," and the signer — do not
write them in operative (lint_order.py refuses)."""
import os, sys, json, shutil, subprocess

import docx
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH as WA

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from clean_meta import clean_docx  # noqa: E402 — C27 §4
from mkdocs import FONT, setfont, fix_styles, nomirror, add_table, LET_T  # noqa: E402

TYPES = ("gr", "corrigendum", "circular", "memo", "notification")
DEPT = "विधि व न्याय विभाग,"
ADDRESS = "हुतात्मा राजगुरु चौक, मादाम कामा मार्ग, मंत्रालय, मुंबई-400 032"
GOVERNOR = "महाराष्ट्राचे राज्यपाल यांच्या आदेशानुसार व नावाने,"
GOVERNOR_EN = "By order and in the name of the Governor of Maharashtra,"
NUMBER_LABEL = {"gr": "शासन निर्णय क्रमांक :- ", "corrigendum": "शासन शुद्धिपत्रक क्रमांक :- ",
                "circular": "शासन परिपत्रक क्रमांक :- ", "memo": "क्रमांक :- ", "notification": "क्रमांक :- "}
BODY_HEAD = {"gr": "शासन निर्णय :-", "corrigendum": "शासन शुद्धिपत्रक :-", "circular": "परिपत्रक :-",
             "memo": "ज्ञापन :-", "notification": "अधिसूचना"}
COPIES_HEAD = {"gr": "प्रत,", "corrigendum": "प्रत,", "circular": "प्रत,", "memo": "प्रत :-",
               "notification": "प्रत सादर अग्रेषित :-"}
# decision B5 (docs/COURT_AND_ORDERS_RESEARCH.md); संकेतांक left blank in the draft
WEBSITE = {
    "gr": "सदर शासन निर्णय महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात आला असून त्याचा संकेतांक ____ असा आहे. हा शासन निर्णय डिजिटल स्वाक्षरीने साक्षांकित करून काढण्यात येत आहे.",
    "corrigendum": "सदर शासन शुद्धिपत्रक महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात आले असून त्याचा संकेतांक ____ असा आहे. हे शासन शुद्धिपत्रक डिजिटल स्वाक्षरीने साक्षांकित करून काढण्यात येत आहे.",
    "circular": "सदर शासन परिपत्रक महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात आले असून त्याचा संकेतांक ____ असा आहे. हे शासन परिपत्रक डिजिटल स्वाक्षरीने साक्षांकित करून काढण्यात येत आहे.",
    "memo": "सदर ज्ञापन महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात आले असून त्याचा संकेतांक ____ असा आहे. हे ज्ञापन डिजिटल स्वाक्षरीने साक्षांकित करून काढण्यात येत आहे.",
    "notification": "सदर अधिसूचना महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात आली असून तिचा संकेतांक ____ असा आहे. ही अधिसूचना डिजिटल स्वाक्षरीने साक्षांकित करून काढण्यात येत आहे.",
}
WEBSITE_DEFAULT = {"gr": True, "corrigendum": True, "circular": True, "memo": False, "notification": False}
SIGNER_DEFAULT = {"name": "( राजेश वडनेरकर )", "designation": "अवर सचिव, महाराष्ट्र शासन"}          # decision B4
SIGNER_NOTIF = {"name": "( ____ )", "designation": "उप विधि सल्लागार-नि-उप सचिव"}
SIGNER_EN = {"name": "( ____ )", "designation": "Deputy Legal Adviser-cum-Deputy Secretary"}
CORR_INSTEAD = "या ऐवजी"
CORR_CLOSING = "उपरोक्त बदलाव्यतिरिक्त संदर्भाधीन शासन निर्णयातील इतर तरतुदी कायम राहतील."
KEEP = "कायम राहतील"
EN_ADDRESS = ["Law and Judiciary Department,", "Hutatma Rajguru Chowk, Madam Cama Marg,", "Mantralaya, Mumbai-400 032."]
SIGN_INDENT = Cm(7.0)


def website_on(o):
    w = o.get("website_line")
    return WEBSITE_DEFAULT[o["type"]] if w is None else bool(w)


def signer(o):
    s = o.get("signer") or {}
    base = SIGNER_NOTIF if o["type"] == "notification" else SIGNER_DEFAULT
    return {"name": s.get("name") or base["name"], "designation": s.get("designation") or base["designation"]}


class Doc:
    def __init__(self):
        d = docx.Document(LET_T)
        body = d.element.body
        for el in list(body):
            if el.tag != qn("w:sectPr"):
                body.remove(el)
        fix_styles(d); nomirror(d)
        s = d.sections[0]
        s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.0), Cm(1.5), Cm(1.5)
        self.d, self.sect = d, body.find(qn("w:sectPr"))

    def p(self, text="", bold=False, align=WA.JUSTIFY, left=None, first=None, underline=False, after=4, size=12):
        par = self.d.add_paragraph()
        pf = par.paragraph_format
        pf.space_before = Pt(0); pf.space_after = Pt(after); pf.line_spacing = 1.15
        pf.left_indent = left if left is not None else Cm(0)
        pf.first_line_indent = first if first is not None else Cm(0)
        par.alignment = align
        r = par.add_run(text)
        r.bold = bold; r.underline = underline; r.font.size = Pt(size); setfont(r)
        return par

    def table(self, rows):
        add_table(self.d, self.sect, rows)
        self.p("", after=2)



def subject_block(D, o, centre=False):
    if o.get("subject"):
        D.p(o["subject"].strip(), bold=True, align=WA.CENTER if centre else WA.JUSTIFY, after=10)


def heading_block(D, o):
    """महाराष्ट्र शासन / विधि व न्याय विभाग, / <number> / address / दिनांक (R3 (b): 010, 041, 006; R4 §2)."""
    t = o["type"]
    D.p("महाराष्ट्र शासन", bold=True, align=WA.CENTER, after=0, size=13)
    if t == "memo":   # NPM परि.-23: क्रमांक before the department line (Section's memo 116)
        D.p(NUMBER_LABEL[t] + o["ref_no"], bold=True, align=WA.CENTER, after=0)
        D.p(DEPT, bold=True, align=WA.CENTER, after=0)
    else:
        D.p(DEPT, bold=True, align=WA.CENTER, after=0)
        if t != "notification":   # notification: the number opens the operative para (NPM परि.-26; 060)
            D.p(NUMBER_LABEL[t] + o["ref_no"], bold=True, align=WA.CENTER, after=0)
    D.p(ADDRESS, align=WA.CENTER, after=0)
    D.p("दिनांक :- " + o["date"], align=WA.CENTER, after=10)


def read_block(D, items, label="वाचा :-"):
    items = [x for x in (items or []) if isinstance(x, str) and x.strip()]
    if not items:
        return
    if len(items) == 1:
        D.p(f"{label} {items[0].strip()}", left=Cm(1.6), first=Cm(-1.6), after=8)
        return
    D.p(label, bold=True, after=2)
    for i, x in enumerate(items, 1):
        D.p(f"{i})\t{x.strip()}", left=Cm(1.6), first=Cm(-0.8), after=2)
    D.p("", after=4)


def numbered(D, items, start_unnumbered=True, k=2):
    """operative paras: first unnumbered (Section's drafts) then 2., 3., …; tables / sub-points not numbered. Returns next k."""
    first = start_unnumbered
    for it in items or []:
        if isinstance(it, dict) and "table" in it:
            D.table(it["table"]); continue
        if isinstance(it, dict) and "sub" in it:
            for s in it["sub"]:
                D.p(s, left=Cm(2.0), first=Cm(-0.8))
            continue
        if first:
            D.p("\t" + it.strip()); first = False
        else:
            D.p(f"{k}.\t{it.strip()}"); k += 1
    return k


def sign_block(D, governor, sg, extra=()):
    D.p(governor, align=WA.CENTER, left=SIGN_INDENT - Cm(3.0), after=24)
    D.p(sg["name"], align=WA.CENTER, left=SIGN_INDENT, after=0)
    D.p(sg["designation"], align=WA.CENTER, left=SIGN_INDENT, after=0)
    for x in extra:
        D.p(x, align=WA.CENTER, left=SIGN_INDENT, after=0)
    D.p("", after=6)


def copies_block(D, head, copies):
    copies = [c for c in (copies or []) if isinstance(c, str) and c.strip()]
    if not copies:
        return
    D.p(head, bold=True, after=2)
    for i, c in enumerate(copies, 1):
        D.p(f"{i}.\t{c.strip()}", left=Cm(1.2), first=Cm(-0.8), after=1)


def orders_of(spec):
    """The order objects of a spec in build order: "order", then each of "orders" (§4.28)."""
    if not isinstance(spec, dict):
        return []
    out = [spec["order"]] if isinstance(spec.get("order"), dict) else []
    return out + [o for o in (spec.get("orders") if isinstance(spec.get("orders"), list) else []) if isinstance(o, dict)]


def build(o, out):
    build_many([o], out, o.get("doc_author"))


def build_many(orders, out, author=None):
    """ONE docx: the orders one after the other, each after the first on a new page (§4.28)."""
    D = Doc()
    for i, o in enumerate(orders):
        n0 = len(D.d.paragraphs)
        build_into(D, o)
        if i and len(D.d.paragraphs) > n0:
            D.d.paragraphs[n0].paragraph_format.page_break_before = True   # paragraph property (see english_block)
    D.d.save(out); clean_docx(out, author)


def build_into(D, o):
    t = o["type"]
    if t != "notification":
        subject_block(D, o, centre=(t == "memo"))
    heading_block(D, o)
    if t == "notification":
        D.p(BODY_HEAD[t], bold=True, align=WA.CENTER, after=8, size=13)
    read_block(D, o.get("read"))
    if t == "gr" and o.get("preamble"):
        D.p("प्रस्तावना :-", bold=True, underline=True, after=4)
        for x in o["preamble"]:
            D.p("\t" + x.strip())
    if t != "notification":
        D.p(BODY_HEAD[t], bold=True, underline=True, align=WA.CENTER if t == "memo" else WA.LEFT, after=4)
    k = 2
    if t == "corrigendum":
        for c in o.get("corrections") or []:
            D.p(f"\t{c['read'].strip()} “{c['instead_of'].strip()}” असे नमूद करण्यात आले आहे.")
            D.p(CORR_INSTEAD, bold=True, align=WA.CENTER)
            D.p(f"\t“{c['read_as'].strip()}” असे वाचावे.")
        ops = [x for x in o.get("operative") or []]
        if not any(isinstance(x, str) and KEEP in x for x in ops):
            ops = [CORR_CLOSING] + ops
        k = numbered(D, ops, start_unnumbered=False, k=2)
    elif t == "notification":
        ops = list(o.get("operative") or [])
        if ops and isinstance(ops[0], str):
            ops[0] = f"{NUMBER_LABEL[t]}{o['ref_no']}, {ops[0].strip()}"
        k = numbered(D, ops)
    else:
        k = numbered(D, o.get("operative"))
    if o.get("concurrence"):
        D.p(f"{k}.\t{o['concurrence'].strip()}"); k += 1
    if website_on(o):
        D.p(f"{k}.\t{WEBSITE[t]}"); k += 1
    sg = signer(o)
    sign_block(D, GOVERNOR, sg, extra=("विधि व न्याय विभाग",) if t == "notification" else ())
    if t == "notification":
        D.p(f"(महाराष्ट्र शासन राजपत्र, {(o.get('gazette_part') or 'भाग ____').strip()} मध्ये प्रसिद्ध करावी.)",
            align=WA.LEFT, after=6)
    if t == "memo" and o.get("addressee"):
        D.p("प्रति,", after=0)
        for line in str(o["addressee"]).split("\n"):
            D.p(line.strip(), left=Cm(1.2), after=0)
        D.p("", after=4)
    copies_block(D, COPIES_HEAD[t], o.get("copies"))
    if t == "notification" and isinstance(o.get("english"), dict):
        english_block(D, o["english"])


def english_block(D, e):
    head = D.p("NOTIFICATION", bold=True, align=WA.CENTER, after=8, size=13)
    head.paragraph_format.page_break_before = True   # (a run-level page break made LibreOffice's converter fail)
    for line in EN_ADDRESS:
        D.p(line, align=WA.CENTER, after=0)
    D.p("Dated :- " + (e.get("date") or "____"), align=WA.CENTER, after=10)
    ops = list(e.get("operative") or [])
    if ops and isinstance(ops[0], str):
        ops[0] = f"No. {e.get('ref_no') or '____'}:- {ops[0].strip()}"
    numbered(D, ops)
    sg = {"name": (e.get("signer") or {}).get("name") or SIGNER_EN["name"],
          "designation": (e.get("signer") or {}).get("designation") or SIGNER_EN["designation"]}
    sign_block(D, GOVERNOR_EN, sg, extra=("Law and Judiciary Department",))
    copies_block(D, "Copy to –", e.get("copies"))


def bad_font_runs(path):
    d = docx.Document(path); bad = 0
    for el in d.element.body.iter(qn("w:r")):
        if not "".join(x.text or "" for x in el.iter(qn("w:t"))).strip():
            continue
        rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
        if f is None or any(f.get(qn("w:" + a)) != FONT for a in ("ascii", "hAnsi", "cs", "eastAsia")):
            bad += 1
    return bad



def soffice_pdf(soffice, src, outdir, timeout=180):
    """LibreOffice preview with a PRIVATE profile (parallel conversions by other agents do not collide, A2 LOW) and a
    time limit. -> (returncode, stderr text); rc 124 = timed out."""
    import tempfile
    prof = tempfile.mkdtemp(prefix="lo_preview_")
    try:
        r = subprocess.run([soffice, "-env:UserInstallation=file://" + prof.replace(os.sep, "/"), "--headless",
                            "--convert-to", "pdf", "--outdir", outdir, src],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        return r.returncode, r.stderr.decode(errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"soffice timed out after {timeout} s"
    finally:
        shutil.rmtree(prof, ignore_errors=True)

def preview(out, outdir):
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        print("WARNING: soffice not found — no PDF preview (docx is complete)", file=sys.stderr); return None
    rc, err = soffice_pdf(soffice, out, outdir)
    pdf = os.path.splitext(out)[0] + ".pdf"
    if rc != 0 or not os.path.exists(pdf):
        print("WARNING: soffice preview failed (rc", rc, ")", err[:300], file=sys.stderr)
        return None
    return pdf


def main(spec_path, outdir, pre, do_lint=True):
    with open(spec_path, encoding="utf-8-sig") as f:
        spec = json.load(f)
    orders = orders_of(spec)
    if not orders:
        print(f"{spec_path}: no \"order\" / \"orders\" key — nothing to build (tools/build_order.py docstring)", file=sys.stderr)
        return 1
    if do_lint:
        import lint_order
        probs = lint_order.lint_order(spec)
        for p in probs:
            print(p)
        for w in lint_order.lint_order_warnings(spec):
            print("WARN " + w)
        if probs:
            print("LINT FAILED — fix spec.json (tools/lint_order.py); nothing built", file=sys.stderr)
            return 1
    elif any(o.get("type") not in TYPES for o in orders):
        print(f"order.type must be one of {TYPES}", file=sys.stderr); return 1
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{pre}_Order_Draft.docx")
    build_many(orders, out, next((o["doc_author"] for o in orders if o.get("doc_author")), None) or spec.get("doc_author"))
    bad = bad_font_runs(out)
    print(out, "+".join(o["type"] for o in orders), "bad-font runs:", bad)
    pdf = preview(out, outdir)
    if pdf:
        print(pdf)
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
