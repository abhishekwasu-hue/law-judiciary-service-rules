#!/usr/bin/env python3
"""verify_outputs.py <outdir> <PREFIX> "<package pdf>" <proposal pages> [--original-name NAME] [--desk ID]
                    [--case-meta meta.json] [--details FILE]
Quality gate for one proposal's three outputs (PROPOSAL_SOP.md Step 7; rules INSTRUCTIONS.md §4).
Prints one line per check ("OK: ..." / "FAIL: ...", plus "WARN: ..." lines that never fail) and "ALL OK" only when
every check passes; exit code 1 otherwise.
Rule constants / regexes / shared checks: tools/lint_spec.py (same rules as the pre-build lint).
Windows: `py tools/verify_outputs.py ...`; runner: `python3 tools/verify_outputs.py ...`.

Checks
 Word (<PREFIX>_Study.docx, <PREFIX>_Note_and_Letter.docx):
  - fonts: every text run (body, tables, text boxes, headers, footers) has w:rFonts ascii, hAnsi, cs, eastAsia = DVOT-SurekhMR
    and no theme-font override attribute
  - no internal file ids (z<digit>_<4 digits>) anywhere
  - पृ. references "पृ.N/प.वि." (also "पृ. N / प.वि.", lists 5,7, ranges 5-7 / 5 ते 7, Devanagari digits) and
    "पॅकेज PDF पृ. N": every N with 1 <= N <= package pages; a पृ.…/प.वि. that cannot be parsed fails.
    Text inside “ ” is skipped in the "संबंधित माहिती" part and in the Study (verbatim quotes of old files carry their own page nos.)
 Note body and letter, WARN only (lint_spec.warn_hits, outside quotes; printed "WARN: …", never FAIL, ALL OK unaffected):
  शुद्धलेखन नियम 12 '…णेसाठी/…णेबाबत/…णेकरिता', नियम 14 halant before an abbreviation dot, नियम 3 'त्याने/तिने…',
  नियम 1–4 'आपणास' / 'यांनां'
 Note (start of Note_and_Letter up to "संबंधित माहिती (संदर्भासाठी)" or the letter):
  - signer chain = INSTRUCTIONS §4.6 names in order, "अ.मु.स. (वित्त)" last
  - "अ.मु.स. (वित्त)" present  <=>  the last numbered para (+ a separate closing line "मान्यतेस्तव सादर.") sends the file
    to Finance / Public Health (lint_spec.finance_route); a full closing para above the signers (spec note.closing "सबब,
    …", one of lint_spec.LAST_FORMS) is the last para itself, as in lint_spec.last_para (audit Q-F5)
 Note body and letter: no BANNED word
 C27 (02.11.2026; all SOFT — delivered with a "पडताळणी अपूर्ण" warning):
  - no "पॅकेज" anywhere in the Note_and_Letter (संबंधित माहिती too; the Study keeps "पॅकेज PDF पृ. N")
  - no warning / working / AI word (lint_spec.draft_word_hits: इशारा, पडताळणी अपूर्ण, मागवावे, वाचन अपूर्ण, अस्पष्ट,
    पडताळलेले नाही, टीप :, warning, TODO, package PDF; AI, Claude, Anthropic, मॉडेल, model, स्वयंचलित, automatic, engine,
    प्रणालीने तयार, generated, LLM, GPT, Gemini) outside “…” quotes in the note body, the संबंधित माहिती heading (bold
    numbered line) and source lines, and the letter; the verbatim extracts are exempt; also "स्रोत", "जसाच्या तसा",
    "जसेच्या तसे", "जशीच्या तशी" (Abhi 03.11.2026)
  - source line = the last paragraph "(…)" of each numbered संबंधित माहिती item (before the next bold numbered heading or
    the end); it ends with "(पृ.N/प.वि.)" (printed "(…, पृ.N/प.वि.)") or carries no page marker
    (lint_spec.related_source_problems); the printed form is read back on the LAST "पृ." (audit 05.11.2026 Q-F4: a
    source naming the GR's own page "(…, पृ.40, पृ.20/प.वि.)" is fine)
  - metadata (tools/clean_meta.py): Study, Note_and_Letter, Order_Draft, Parawise — core properties blank, app.xml
    Application without a tool name, no Word comments, no tracked changes; package PDF — Info dictionary blank, no tool
    name in XMP, no annotation title/subject/content
 Note body and letter (§4.18, text outside “…” quotes only): no 'सौ.'; 'श्री.' followed by a space; letter: no 'तात्काळ'
 Note body and letter (§4.19, outside quotes, lint_spec.lang_hits): no '.:-', no 'करुन' / 'प्रारुप' / 'अनुसरुन', a space after
  'दि.' / 'क्र.' / 'प्र. क्र.' in running text (file nos. / codes with '/' or '-' skipped); missing-info para 'नाही:-'
 Note body (C1 / C2, Abhi 05.11.2026, options आ): no incoming letter number (lint_spec.note_letter_no_hits — "क्र." /
  "क्रमांक" + a number near a पत्र-word, outside quotes; GR / case / own file numbers excepted); the missing-info para lists
  its items inline "(1) …; (2) …." (FAIL when not; WARN for a table right after it)
 Note body (§4.31, 03.11.2026; lint_spec.missing_scatter, outside quotes): missing information / documents only in ONE para
  "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-" (+ its table / unnumbered sub-points); no "नमूद नाही / जोडलेले नाही /
  उपलब्ध नाही / प्रस्तावासोबत नाही / प्रत नाही / सादर केलेली नाही" remark elsewhere; not two such paras (SOFT);
  WARN when that para is not just before the last (numbered or "सबब,") para
 Note body (C32 §4.34, 03.11.2026; lint_spec.flow_warnings, WARN only — never FAIL, ALL OK unaffected): a table
  header with a "पृ./प.वि." / "पृ." column; "पृष्ठांकन" / "माहितीकरिता देण्यात" outside quotes; quote-gluing "तसेच, “" /
  "” व “"; an "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-" item with "पृ.N/प.वि."; a quoted “…” with "…" / "..." (also in
  संबंधित माहिती)
 Note_and_Letter (whole file): no repo paths (register/, service-rules/, precedent-library/, pdf/, repo, रेपो)
 Letter (when present: a "प्रति," or "क्रमांक :-" paragraph):
  - starts on a new page / new section (page break or section break before the letterhead)
  - ref no. संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6 ; e-mail lnjd.desk6-mh@mah.gov.in on the letterhead
  - विषय and संदर्भ paragraphs: centred, every run bold
  - intro paragraph (starting "उपरोक्त विषयाबाबत") contains "ही विनंती" outside quotes (§4.18) when the letter asks for
    information (lint_spec.requests_info: a table / numbered points, a reminder, or "… उपलब्ध करून देण्यात यावी")
  - "आपला," present, signature "आपली," absent ("आपली पत्रे" in संदर्भ is allowed); lines "( राजेश वडनेरकर )", "अवर सचिव ,महाराष्ट्र शासन", "प्रत : निवड नस्ती"
 अर्धशासकीय पत्र (spec letter "kind": "do"; found by its "अ.शा.पत्र क्र." line; docs/FORMS_RESEARCH_DO_UO.md): new page /
  section; number line = "अ.शा.पत्र क्र. <desk ref no.>" + "दिनांक" line; विषय bold + centre; "प्रिय …,"; body in the first
  person; "शुभेच्छा", "आपला स्नेहांकित,", "(<sender>)" and the addressee lines after it. The ordinary-letter checks above
  run only on the ordinary letter(s).
 Note "uo" (अनौपचारिक संदर्भ): the three lines right after the signer chain — "<department>" / "<to> विभागाकडे अनौपचारिक
  संदर्भ कार्यासन <desk>" / "क्रमांक … दिनांक …"; they are left out of the signer-chain check.
 Desk (C30, 03.11.2026): the signer chain, finance signer, ref no. form, letterhead e-mail (checked only when the
  profile has one; a blank "____" is fine) and the letter's ending lines come from the desk profile tools/desks/<id>.json:
  --desk ID, else the profile whose note_header is the note's first line, else law-desk6 (the Desk-6 values above)
 status.json (when <outdir>/status.json exists): `letter_needed` is true/false and true <=> a letter is present
 Study: headings भाग 0 … भाग 7
 Optional outputs (02.11.2026; only when the file exists — absent = no line, ALL OK unaffected):
  <PREFIX>_Order_Draft.docx (शासन आदेश-मसुदा), <PREFIX>_Parawise.docx (परिच्छेदनिहाय अभिप्राय, English) and (audit
  05.11.2026 Q-F13) <PREFIX>_Affidavit.docx (शपथपत्र) / <PREFIX>_LQ_Answer.docx (विधानमंडळ प्रश्नाचे उत्तर):
  fonts (four rFonts = DVOT-SurekhMR incl. headers/footers; the _Affidavit file instead: ascii / hAnsi = Times New Roman,
  cs / eastAsia = DVOT-SurekhMR — Abhi 05.11.2026, C7 option अ, INSTRUCTIONS §4.2 / §4.36), no internal ids, no repo paths, पृ. references within
  1..package pages (text inside “ ” skipped); C27: no "पॅकेज" / warning / AI word (outside quotes), metadata blank
 Package PDF:
  - file name is the original proposal name (not *_Proposal_with_GRs.pdf); with --original-name NAME: the file name must
    equal NAME minus a random upload prefix like "11ae057d-" (engine_supabase.strip_upload_prefix: 8 hex characters
    with at least one letter a-f, so "20261101-CR130.pdf" is kept as is; the *_Proposal_with_GRs.pdf ban is then skipped, §4.16)
    or its disk-safe short form (engine_supabase.fs_name: names over 200 UTF-8 bytes cut + "~<6 hex>", NAME_MAX)
  - every page carries exactly "पृ. i / N" in the bottom 40 pt strip; bookmarks present
  - <pdf>.map.json: proposal pages == <proposal pages>; total pages == proposal + enclosure pages (no separator pages);
    no mark with status "TEXT NOT FOUND" / "page not included" or hits == 0 (works with or without per-mark "hits")
    reply / concurrence letters appended after the proposal (map.json "proposal_parts", tools/pkg3.py --also) count as
    proposal-side pages: proposal pages == <proposal pages> or proposal + reply pages == <proposal pages>
  - "annotations on proposal pages (none)": no annotation on proposal (and reply-part) pages;
    "annotations (Highlight only)": only Highlight annotations elsewhere
 Audit 05.11.2026 additions:
  - Q-F8 (WARN): the note's "उपरोक्त वस्तुस्थिती" list has 3 to 6 items (sub-point paragraphs / table data rows) and no “…”
  - Q-F6 (WARN): "उल्लेख नाही" / "आढळून येत नाही" outside the missing-info para (lint_spec.missing_scatter warnings)
  - Q-F14 (--case-meta meta.json; FAIL, soft): every letter number line "…-<year>/<file no>/प्र.क्र.<n>/…" against the case
    row: file_no ("संकीर्ण-2026/979/प्र.क्र.130/का.6", "2026/979" or "979") year + number, प्र.क्र. vs file_no's प्र.क्र. /
    cr_no; "____" blanks not compared; no file_no / cr_no in the meta = nothing compared
  - Q-F17 (WARN): each cited "पृ.N/प.वि." reference whose pages all lie after the proposal has a Highlight on one of
    them; each Highlight on an enclosure page has >= 50 % of its words in the note's extracts (related + body quotes);
    pages with an unusable text layer skipped; a package with no Highlight at all -> "OK: highlight coverage — skipped"
  - S-F3: --details FILE (or env CASE_DETAILS_FILE): full lines to FILE, stdout with each quoted segment replaced by its
    length (lint_spec.out / redact) — check names, block / page numbers and counts stay
 The engine (tools/engine_supabase.py verify) treats only these FAILs as HARD (case failed): "… opens" (Study,
 Note_and_Letter, package PDF), "… internal ids", "… repo paths", "annotations on proposal pages"; every other FAIL is
 delivered with a "पडताळणी अपूर्ण — …" warning.
"""
import json
import os
import re
import sys

import docx
import pymupdf as m
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

FONT = "DVOT-SurekhMR"
FONT_ATTRS = ("ascii", "hAnsi", "cs", "eastAsia")
THEME_ATTRS = ("asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# shared rule definitions — ONE copy, in tools/lint_spec.py (pre-build lint uses the same rules)
from lint_spec import (AMS, BANNED, BARE_CLOSING_RE, FIN, ID_RE, LH_EMAIL, RELATED, REF_NO, REPO_RE, REQUEST,  # noqa: E402,F401
                       MISSING_FORM, MISSING_HEAD, SIGNERS, banned_hits, desk_signers, finance_problems, heading_problems, id_hits,
                       lang_hits, ma_hits, ns, num, part_no, ref_problems, repo_hits, requests_info, signer_problems,
                       style_hits, unquoted, warn_hits, PKG_WORD, draft_word_hits, related_source_problems,
                       missing_scatter, flow_warnings, DO_FIRST_PERSON_RE, SUMMARY_HEAD_RE, summary_problems,
                       NUMLIST, LAST_FORMS, out, redact, details_arg, set_details, details_active,
                       MISSING_HEAD_RE, MISSING_INLINE_RE, MISSING_INLINE_MSG, note_letter_no_hits)
from mkdocs import DO_WISH, DO_SUBSCRIPTION  # noqa: E402 — अर्धशासकीय पत्र ending (GAD specimen)
INTRO_HEAD = "उपरोक्त विषयाबाबत"  # letter intro paragraph (lint_spec.INTRO_START begins with it)
UO_LINE_RE = re.compile(r"^\S.*विभागाकडे\s+अनौपचारिक\s+संदर्भ\s+कार्यासन(?:\s|$)")   # note "uo" block (mkdocs.uo_lines)
DO_LINE_RE = re.compile(r"^\s*अ\.\s*शा\.\s*पत्र\s+क्र\.")   # अर्धशासकीय पत्र number line (mkdocs.DO_REF_LABEL)
from build_affidavit import FONTS as AFFIDAVIT_FONTS  # noqa: E402 — C7 (05.11.2026): Times New Roman + DVOT-SurekhMR (cs/eastAsia)
from clean_meta import docx_meta_problems, pdf_meta_problems  # noqa: E402 — C27 §4 (no tool / AI trace in metadata)
import desk as _desk  # noqa: E402 — C30 (03.11.2026): desk profiles tools/desks/<id>.json
from engine_supabase import strip_upload_prefix, name_forms  # noqa: E402 — the ONE upload-prefix rule (§4.16) + NAME_MAX short form

results = []


def check(name, problems):
    """problems: list of strings (empty = OK)."""
    results.append(not problems)
    if problems:
        shown = "; ".join(problems[:6]) + (f"; … (+{len(problems) - 6})" if len(problems) > 6 else "")
        # S-F3: with a details file only the problem text is redacted (the check name stays — engine_supabase parses it)
        out(f"FAIL: {name} — {shown}", f"FAIL: {name} — {redact(shown)}")
    else:
        print(f"OK: {name}")






def warn(msg):
    """WARN-level finding: printed as "WARN: …", does not count as a FAIL (ALL OK still possible)."""
    out(f"WARN: {msg}")


def el_text(el):
    return "".join(x.text or "" for x in el.iter(qn("w:t")))


def blocks_of(d):
    """body-level blocks in order: dicts kind(p/tbl), el, text, brk (page/section break inside or before it)."""
    out = []
    for el in d.element.body:
        tag = el.tag.split("}")[1]
        if tag not in ("p", "tbl"):
            continue
        brk = False
        if tag == "p":
            brk = any(b.get(qn("w:type")) == "page" for b in el.iter(qn("w:br")))
            ppr = el.find(qn("w:pPr"))
            if ppr is not None and (ppr.find(qn("w:sectPr")) is not None or ppr.find(qn("w:pageBreakBefore")) is not None):
                brk = True
            text = el_text(el)
        else:
            text = "\n".join(" | ".join(el_text(c) for c in r.iter(qn("w:tc"))) for r in el.iter(qn("w:tr")))
        out.append({"kind": tag, "el": el, "text": text, "brk": brk})
    return out


def font_problems(d, label, fonts=None):
    """fonts: {rFonts attribute: font} expected on every text run (default: the four attributes = DVOT-SurekhMR)."""
    fonts = fonts or {a: FONT for a in FONT_ATTRS}
    roots = [d.element.body]
    for part in d.part.package.iter_parts():
        if re.search(r"/word/(header|footer)\d*\.xml$", str(part.partname)):
            roots.append(part.element)
    bad = 0
    for root in roots:
        for r in root.iter(qn("w:r")):
            t = "".join(x.text or "" for x in r.iter(qn("w:t")))
            if not t.strip():
                continue
            rp = r.find(qn("w:rPr")); fo = rp.find(qn("w:rFonts")) if rp is not None else None
            if fo is None or any(fo.get(qn("w:" + a)) != v for a, v in fonts.items()) or any(fo.get(qn("w:" + a)) is not None for a in THEME_ATTRS):
                bad += 1
    if not bad:
        return []
    if len(set(fonts.values())) == 1:
        return [f"{label}: {bad} text runs without {FONT} on all four rFonts attributes"]
    want = ", ".join(f"{a}={v}" for a, v in fonts.items())
    return [f"{label}: {bad} text runs without rFonts {want}"]




# optional outputs (02.11.2026, docs/COURT_AND_ORDERS_RESEARCH.md B7–B9): file suffix -> label in the check lines
EXTRA_DOCS = (("_Order_Draft.docx", "Order_Draft"), ("_Parawise.docx", "Parawise"),
              # audit 05.11.2026 Q-F13: tools/build_affidavit.py / tools/build_lq.py outputs
              ("_Affidavit.docx", "Affidavit"), ("_LQ_Answer.docx", "LQ_Answer"))


def doc_text(d):
    """All text of a document: body blocks (paragraphs, tables) + headers/footers."""
    parts = [b["text"] for b in blocks_of(d)]
    for part in d.part.package.iter_parts():
        if re.search(r"/word/(header|footer)\d*\.xml$", str(part.partname)):
            parts.append(el_text(part.element))
    return "\n".join(parts)


def p_centred(p):
    a = p.alignment
    if a is None and p.style is not None:
        a = p.style.paragraph_format.alignment
    return a == WD_ALIGN_PARAGRAPH.CENTER


def p_bold(p):
    for r in p.runs:
        if not r.text.strip():
            continue
        b = r.bold
        if b is None and p.style is not None:
            b = p.style.font.bold
        if not b:
            return False
    return True


def letter_body_for_ma(texts):
    """§4.23 "मा." check on the letter: the विषय line and the body from "महोदय" on — not the addressee block (प्रति, …),
    the संदर्भ lines or the प्रत : copy lines (same exemptions as lint_spec: letter.to / refs / copies)."""
    out, state = [], "head"
    for t in texts:
        n = ns(t)
        if n.startswith("विषय"): state = "subject"
        elif n.startswith("संदर्भ"): state = "refs"
        elif n.startswith("महोदय") or n.startswith("प्रिय"): state = "body"   # "प्रिय …," = अर्धशासकीय पत्र
        if state == "subject" or (state == "body" and not n.startswith("प्रत")):
            out.append(t)
    return "\n".join(out)


def letter_info(blocks, letter_txt):
    """What lint_spec.requests_info needs from a built letter: points (a table or numbered "1)" points) / reminder."""
    if any(b["kind"] == "tbl" for b in blocks):
        pts = [{"table": []}]
    else:   # numbered points ("1) …" / "1. …"); they ask only with ask wording (lint_spec.points_ask, C30)
        pts = [b["text"] for b in blocks if b["kind"] == "p" and re.match(r"\s*[0-9०-९]+\s*[).]", b["text"])]
    return {"points": pts, "reminder": "स्मरणपत्र-" in letter_txt}


def new_page_before(bl, start):
    """a page / section break right before block start (blank paragraphs in between allowed)."""
    prev = start - 1
    while prev > 0 and not ns(bl[prev]["text"]) and not bl[prev]["brk"]:
        prev -= 1
    return any(b["brk"] for b in bl[max(prev, 0):start + 1])


def do_letter_problems(blocks, doc, dk):
    """[(check name, problems)] for one अर्धशासकीय पत्र (letter "kind": "do"), blocks from its "अ.शा.पत्र क्र." line.
    Layout of the GAD specimen (टिप्पणी लेखन व पत्रव्यवहार परि. 12.27–12.29, book p.43–44, PDF p.47–48): number +
    department + date block, "विषय" bold + centre, salutation "प्रिय …", "शुभेच्छा", "आपला स्नेहांकित,", "(<sender>)", the
    addressee lines after it; MMOP 2023 §10.1(7)(a) first person (PDF p.64), §11.4(3) subject (PDF p.80)."""
    ps = [Paragraph(b["el"], doc.element.body) for b in blocks if b["kind"] == "p"]
    lt = [ns(p.text) for p in ps]
    out, pr = [], []
    first = lt[0] if lt else ""
    if not DO_LINE_RE.match(first) or not _desk.letter_ref_re(dk).search(first):
        pr.append(f"D.O. no. not 'अ.शा.पत्र क्र. {dk['letter']['ref_hint']}': '{first}'")
    if not any(t.startswith("दिनांक") for t in lt[:8]):
        pr.append("'दिनांक :' line missing in the number block")
    out.append(("अर्धशासकीय पत्र number / department block", pr))
    vb = []
    vi = next((i for i, t in enumerate(lt) if t.startswith("विषय")), None)
    si = next((i for i, t in enumerate(lt) if t.startswith("प्रिय")), None)
    if vi is None:
        vb.append("'विषय' paragraph missing (MMOP §11.4(3))")
    else:
        for p in ps[vi:(si if si is not None and si > vi else vi + 1)]:
            if not p.text.strip(): continue
            if not p_centred(p): vb.append(f"not centred: '{ns(p.text)[:40]}'")
            if not p_bold(p): vb.append(f"not bold: '{ns(p.text)[:40]}'")
    out.append(("अर्धशासकीय पत्र विषय bold + centre", vb))
    en = []
    if si is None: en.append("salutation 'प्रिय …,' missing")
    for w in (DO_WISH, DO_SUBSCRIPTION):
        if w not in lt: en.append(f"'{w}' line missing")
    ci = lt.index(DO_SUBSCRIPTION) if DO_SUBSCRIPTION in lt else None
    sig = next((i for i in range(ci + 1, len(lt)) if lt[i]), None) if ci is not None else None
    if ci is not None and (sig is None or not re.fullmatch(r"\(.+\)", lt[sig])):
        en.append(f"sender's name '(…)' missing after '{DO_SUBSCRIPTION}'")
    if sig is not None and not any(lt[sig + 1:]):
        en.append("addressee (name, designation, office) missing at the foot")
    if si is not None and ci is not None and not DO_FIRST_PERSON_RE.search(unquoted("\n".join(lt[si + 1:ci]))):
        en.append("body not in the first person (MMOP §10.1(7)(a))")
    out.append(("अर्धशासकीय पत्र salutation / ending / addressee", en))
    return out


def source_of_line(t):
    """A printed related source line "(…, पृ.N/प.वि.)" (mkdocs) -> the spec form "… (पृ.N/प.वि.)" for
    lint_spec.related_source_problems. Audit Q-F4: anchored on the LAST "पृ." — the GR's own page may come before it
    ("(…, पृ.40, पृ.20/प.वि.)" -> "…, पृ.40 (पृ.20/प.वि.)")."""
    return re.sub(r",\s*(पृ\.(?:(?!पृ\.)[^()])*?/\s*प\.वि\.)$", r" (\1)", re.sub(r"^\((?:स्रोत:\s*)?|\)$", "", t))


def summary_blocks(blocks):
    """lint_spec.summary_problems entries from the note's docx blocks: each "उपरोक्त वस्तुस्थिती" paragraph, its items = the
    paragraphs (sub-points) and table data rows after it up to the next numbered / "सबब," paragraph (audit Q-F8)."""
    out_, cur = [], None
    for i, b in enumerate(blocks):
        t = ns(b["text"])
        if not t:
            continue
        if b["kind"] == "p" and SUMMARY_HEAD_RE.search(unquoted(t)):
            cur = (f"note block {i + 1}", t, []); out_.append(cur); continue
        if cur is None:
            continue
        if b["kind"] == "p" and re.match(r"[0-9०-९]+\.|सबब\s*,", t):
            cur = None; continue
        if b["kind"] == "tbl":
            cur[2].extend(r for r in b["text"].split("\n")[1:] if r.strip(" |"))
        else:
            cur[2].append(t)
    return out_


FILE_NO_RE = re.compile(r"(?<![0-9])((?:19|20)[0-9]{2})\s*/\s*([0-9]+)(?![0-9])")
LETTER_REF_PARTS_RE = re.compile(r"-\s*([0-9_]{2,4})\s*/\s*([0-9_]+)\s*/\s*प्र\.\s*क्र\.\s*([0-9_]+)\s*/")


def ref_meta_problems(line, meta):
    """audit Q-F14: the letter number "संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6" against the case row (--case-meta
    file_no, e.g. "संकीर्ण-2026/979/प्र.क्र.130/का.6" / "2026/979" / "979"; cr_no). Blanks "____" are not compared."""
    m = LETTER_REF_PARTS_RE.search(line)
    if not m:
        return []
    year, fno, crn = m.groups()
    fn = str(meta.get("file_no") or "").strip()
    want_year = want_no = None
    fm = FILE_NO_RE.search(fn)
    if fm:
        want_year, want_no = fm.groups()
    elif re.fullmatch(r"[0-9]+", fn):
        want_no = fn
    pm = re.search(r"प्र\.\s*क्र\.\s*([0-9]+)", fn)
    want_cr = pm.group(1) if pm else (str(meta.get("cr_no")).strip() if meta.get("cr_no") not in (None, "") else None)
    P = []
    if want_year and "_" not in year and year != want_year:
        P.append(f"letter no. year {year} != file no. year {want_year}")
    if want_no and "_" not in fno and fno.lstrip("0") != want_no.lstrip("0"):
        P.append(f"letter no. file no. {fno} != case file no. {want_no}")
    if want_cr and want_cr.isdigit() and "_" not in crn and crn.lstrip("0") != want_cr.lstrip("0"):
        P.append(f"letter no. प्र.क्र. {crn} != C R no. {want_cr}")
    return P


def _cited_groups(texts):
    """[(reference, [pages])] of every "पृ.N/प.वि." in texts (quotes skipped)."""
    out_ = []
    for t in texts:
        for mt in re.finditer(r"पृ\.((?:(?!पृ\.)[^/\n]){0,40}?)/\s*प\.वि\.", unquoted(t or "")):
            inner = mt.group(1).strip()
            if not re.fullmatch(NUMLIST, inner):
                continue
            pages = []
            for part in re.split(r"\s*,\s*", inner):
                ends = [num(x) for x in re.split(r"\s*(?:-|–|ते)\s*", part) if x.strip()]
                pages += list(range(ends[0], ends[-1] + 1)) if len(ends) == 2 and ends[1] - ends[0] < 400 else ends
            out_.append((mt.group(0), pages))
    return out_


def highlight_findings(P, proposal_pages, ctx):
    """audit Q-F17 (WARN only): (status text, warnings). (a) each cited reference whose pages all lie after the proposal
    (GR / enclosure pages) has a Highlight on at least one of them; (b) each Highlight on an enclosure page lies inside a
    quoted extract of the note (its words >= 50 % in the related extracts / note-body quotes). Skipped when the package
    has no Highlight at all (stand-in / unmarked package); (b) skips pages whose text layer is unusable (scan, legacy
    font, garbled ToUnicode — tools/extract_check.py rules)."""
    import extract_check as X
    hl = {}
    for i, pg in enumerate(P, 1):
        rs = [a.rect for a in pg.annots() if a.type[1] == "Highlight"]
        if rs:
            hl[i] = rs
    if not hl:
        return "skipped: the package has no highlight annotations (no data to compare)", []
    W = []
    groups = _cited_groups([ctx.get("note", "")] + list(ctx.get("sources") or []))
    seen = set()
    for ref, pages in groups:
        enc = [p for p in pages if 1 <= p <= len(P) and p not in proposal_pages]
        key = tuple(enc)
        if not enc or len(enc) != len(pages) or key in seen:
            continue
        seen.add(key)
        if not any(p in hl for p in enc):
            W.append(f"cited GR page(s) {ref.replace('/प.वि.', '').replace('पृ.', '')} — no highlight on the quoted lines "
                     f"(§4.11)")
    corpus = " ".join([ctx.get("related", "")] + re.findall(r"“([^”]*)”", ctx.get("note", "")))
    cw = set(X.words(corpus))
    checked = 0
    for p, rects in sorted(hl.items()):
        if p in proposal_pages:
            continue
        pg = P[p - 1]
        full = pg.get_text("text") or ""
        letters = len(re.findall(r"\w", full)) or 1
        legacy = len(X.DEVA.findall(full)) < 0.2 * letters and len(re.findall(r"[\u00a0-\u00ff]", full)) > 0.03 * letters
        if len(X.norm(full)) < 50 or X.garbled(full) or legacy:   # scan / garbled ToUnicode / legacy Devanagari font
            continue
        for r in rects:
            hw = X.words(pg.get_textbox(r) or "")
            if len(hw) < 3:
                continue
            checked += 1
            cov = sum(1 for w in hw if w in cw) / len(hw)
            if cov < 0.5:
                W.append(f"page {p}: highlight not inside any quoted extract ({int(cov * 100)} % of its {len(hw)} words "
                         f"in the note's extracts; §4.13)")
    return f"{len(hl)} highlighted page(s), {len(seen)} cited GR reference(s), {checked} highlight(s) compared", W


def main(argv):
    argv = list(argv); orig = None; desk_arg = None; meta = None
    set_details(details_arg(argv), "verify_outputs " + " ".join(argv[1:]))   # audit S-F3
    if "--case-meta" in argv:   # audit Q-F14: the case row (file_no, cr_no, cr_year) — engine_supabase case_meta
        i = argv.index("--case-meta")
        if i + 1 >= len(argv):
            print(__doc__); return 2
        try:
            meta = json.load(open(argv[i + 1], encoding="utf-8-sig"))
        except Exception as e:
            check("case meta opens", [f"{argv[i + 1]}: {e.__class__.__name__}"]); meta = {}
        del argv[i:i + 2]
    if "--desk" in argv:   # C30: desk profile id (else detected from the note's header line, else law-desk6)
        i = argv.index("--desk")
        if i + 1 >= len(argv):
            print(__doc__); return 2
        desk_arg = argv[i + 1]; del argv[i:i + 2]
    if "--original-name" in argv:
        i = argv.index("--original-name")
        if i + 1 >= len(argv):
            print(__doc__); return 2
        orig = argv[i + 1]; del argv[i:i + 2]
    if len(argv) != 5:
        print(__doc__); return 2
    out, pre, pkg, npp = argv[1], argv[2], argv[3], int(argv[4])
    hl_ctx = None
    try:
        P = m.open(pkg); N = len(P)
    except Exception as e:
        check("package PDF opens", [f"{pkg}: {e}"]); P = None; N = 0

    # ---------------- Study ----------------
    fs = os.path.join(out, f"{pre}_Study.docx")
    try:
        S = docx.Document(fs)
    except Exception as e:
        check("Study opens", [f"{fs}: {e}"]); S = None
    if S is not None:
        sb = blocks_of(S); st = "\n".join(b["text"] for b in sb)
        check("Study fonts", font_problems(S, "Study"))
        check("Study internal ids", [f"internal id {x}" for x in id_hits(st)])
        check("Study पृ. references", ref_problems(st, N, "Study", skip_quotes=True))
        have = set()
        for b in sb:
            k = part_no(b["text"])
            if b["kind"] == "p" and k is not None:
                have.add(k)
        check("Study headings भाग 0-7", heading_problems(have))
        check("Study metadata (no tool / AI trace)", docx_meta_problems(fs))

    # ---------------- Note and Letter ----------------
    fn = os.path.join(out, f"{pre}_Note_and_Letter.docx")
    try:
        NL = docx.Document(fn)
    except Exception as e:
        check("Note_and_Letter opens", [f"{fn}: {e}"]); NL = None
    if NL is not None:
        bl = blocks_of(NL); n = len(bl)
        txt = lambda a, b: "\n".join(x["text"] for x in bl[a:b])
        rel = next((i for i, b in enumerate(bl) if b["kind"] == "p" and ns(b["text"]) == RELATED), None)
        kram = next((i for i, b in enumerate(bl) if b["kind"] == "p" and re.match(r"\s*क्रमांक\s*:?\s*-", b["text"])), None)
        prati = next((i for i, b in enumerate(bl) if b["kind"] == "p" and ns(b["text"]) == "प्रति,"), None)
        # अर्धशासकीय पत्र (letter "kind": "do"): first line "अ.शा.पत्र क्र. …" (GAD specimen p.43, PDF p.47)
        do_i = next((i for i, b in enumerate(bl) if b["kind"] == "p" and DO_LINE_RE.match(b["text"])), None)
        has_std = kram is not None or prati is not None
        has_letter = has_std or do_i is not None
        lstart = std_start = None
        if has_std:
            anchor = kram if kram is not None else prati
            std_start = anchor
            for j in range(anchor - 1, max(-1, anchor - 9), -1):
                if ns(bl[j]["text"]) == "महाराष्ट्र शासन":
                    std_start = j; break
        if has_letter:
            lstart = min(x for x in (std_start, do_i) if x is not None)
        note_end = rel if rel is not None else (lstart if lstart is not None else n)
        rel_end = lstart if lstart is not None else n
        note_txt = txt(0, note_end)
        letter_txt = txt(lstart, n) if has_letter else ""
        rel_txt = txt(rel, rel_end) if rel is not None else ""
        alltxt = txt(0, n)

        check("Note_and_Letter fonts", font_problems(NL, "Note_and_Letter"))
        check("Note_and_Letter internal ids", [f"internal id {x}" for x in id_hits(alltxt)])
        check("Note_and_Letter repo paths", [f"repo path/word '{x}'" for x in repo_hits(alltxt)])
        check("Note_and_Letter पृ. references",
              ref_problems(note_txt, N, "note") + ref_problems(rel_txt, N, "संबंधित माहिती", skip_quotes=True)
              + ref_problems(letter_txt, N, "letter"))
        # C27 (02.11.2026): no "पॅकेज" anywhere in the Note_and_Letter (संबंधित माहिती too — its sources cite "(पृ.N/प.वि.)")
        pk = [f"{where}: '{PKG_WORD}' — use पृ.N/प.वि." for where, t in (("note", note_txt), ("संबंधित माहिती", rel_txt),
                                                                        ("letter", letter_txt)) if PKG_WORD in t]
        check("no 'पॅकेज' in Note_and_Letter", pk)
        # C27: warning / working / AI words outside “…” quotes — note body, related heading + source lines, letter
        # (the verbatim related extracts are exempt)
        # source line (03.11.2026, no word "स्रोत"): the LAST paragraph of each numbered item (before the next bold numbered
        # heading or the end) when it reads "(…)"; ", पृ.N/प.वि.)" is reversed to " (पृ.N/प.वि.)" for the marker check
        rel_own, rel_src = [], []
        if rel is not None:
            items = []
            for b in bl[rel + 1:rel_end]:
                if b["kind"] != "p" or not ns(b["text"]):
                    continue
                t = ns(b["text"])
                if re.match(r"[0-9]+\.", t) and p_bold(Paragraph(b["el"], NL._body)):
                    rel_own.append(t); items.append([])
                elif items:
                    items[-1].append(t)
            for paras in items:
                if paras and re.match(r"^\(.*\)$", paras[-1]):
                    t = paras[-1]
                    rel_own.append(t)
                    rel_src.append(source_of_line(t))
        check("no warning / working / AI words (note, संबंधित माहिती heading/source, letter)",
              [f"{where}: '{w}'" for where, t in (("note", note_txt), ("संबंधित माहिती", "\n".join(rel_own)),
                                                 ("letter", letter_txt))
               for w in draft_word_hits(t) if w != PKG_WORD])
        check("संबंधित माहिती source ends with (पृ.N/प.वि.) or no page marker",
              [f"'{x[:50]}': {p_.split(' — ')[0]}" for x in rel_src for p_ in related_source_problems(x)])
        check("Note_and_Letter metadata (no tool / AI trace)", docx_meta_problems(fn))
        check("banned words (note body, letter)",
              [f"{where}: '{w}'" for where, t in (("note", note_txt), ("letter", letter_txt)) for w in banned_hits(t)])

        check("respectful wording §4.18 (note body, letter)",
              [f"{where}: {x}" for where, t, isl in (("note", note_txt, False), ("letter", letter_txt, True))
               for x in style_hits(t, letter=isl)])
        # §4.23 "मा." — the letter's addressee block (before "विषय") is excepted
        lbody = letter_body_for_ma([b["text"] for b in bl[lstart:]] if has_letter else [])
        check('"मा." before the High Court and judges §4.23 (note body, letter)',
              [f"{where}: {x}" for where, t in (("note", note_txt), ("letter", lbody)) for x in ma_hits(t)])

        # §4.19 (मराठी भाषा विभाग GR दि. 10.11.2022): same helpers as the pre-build lint, text outside quotes
        lg = [f"{where}: {x}" for where, t in (("note", note_txt), ("letter", letter_txt)) for x in lang_hits(t)]
        lg += [f"note: missing-info para — form '{MISSING_FORM}'" for b in bl[:note_end] if b["kind"] == "p"
               and re.sub(r"^[0-9०-९]+\.\s*", "", ns(unquoted(b["text"]))).startswith(MISSING_HEAD)
               and not re.sub(r"^[0-9०-९]+\.\s*", "", ns(b["text"])).startswith(MISSING_HEAD + ":-")]
        check("official Marathi §4.19 (note body, letter)", lg)
        # §4.31 (Abhi 03.11.2026): missing information / documents only in ONE missing-info para (its table / unnumbered
        # sub-points belong to it); a numbered or "सबब," paragraph starts a new para (SOFT, like every non-HARD check)
        nseq = [(f"note block {i + 1}", b["text"], b["kind"] == "p" and bool(re.match(r"[0-9०-९]+\.|सबब\s*,", ns(b["text"]))))
                for i, b in enumerate(bl[:note_end]) if ns(b["text"])]
        mp, mw = missing_scatter(nseq)
        check("missing information in ONE para §4.31 (note body)", mp)
        for x in mw:
            warn(x)
        # C2 (Abhi 05.11.2026, option आ): the missing-info para lists its items inline "(1) …; (2) …." — not a table
        nb = [b for b in bl[:note_end] if ns(b["text"])]
        mi = []
        for i, b in enumerate(nb):
            t = re.sub(r"^[0-9०-९]+\.\s*", "", ns(b["text"]))
            if b["kind"] == "p" and MISSING_HEAD_RE.match(ns(unquoted(t))):
                if not MISSING_INLINE_RE.search(t):
                    mi.append(f"note: {MISSING_INLINE_MSG}")
                if i + 1 < len(nb) and nb[i + 1]["kind"] == "tbl":
                    warn(f"note: table after the missing-info para — {MISSING_INLINE_MSG}")
        check("missing-info items inline §4.31(अ) C2 (note body)", mi)
        # C1 (Abhi 05.11.2026, option आ): no incoming letter number anywhere in the note body (lint_spec.note_letter_no_hits;
        # outside quotes and पृ.N/प.वि.; GR / case / own file numbers excepted)
        check("no incoming letter no. in the note §4.29 C1 (note body)",
              [f"note block {i + 1}: '{x}'" for i, b in enumerate(bl[:note_end]) for x in note_letter_no_hits(b["text"])])
        # C32 §4.34 (Abhi 03.11.2026; lint_spec.flow_warnings): relevance + एकसंध flow — SOFT notes printed as WARN, never
        # a FAIL: "पृ./प.वि." table column, "पृष्ठांकन" / "माहितीकरिता देण्यात", quote-gluing, a page ref in an
        # "उपरोक्त वस्तुस्थिती" item, a shortened quote (note body and संबंधित माहिती)
        nheads = [(f"note block {i + 1} (table)", b["text"].split("\n", 1)[0].split(" | "))
                  for i, b in enumerate(bl[:note_end]) if b["kind"] == "tbl" and b["text"]]
        for x in flow_warnings(nseq, nheads, [("संबंधित माहिती", rel_txt)] if rel_txt else []):
            warn(x)
        # audit Q-F8: "उपरोक्त वस्तुस्थिती" list — 3 to 6 items (sub-point paragraphs / table data rows), no “…” quote
        for x in summary_problems(summary_blocks(bl[:note_end])):
            warn(x)
        # WARN level (lint_spec.warn_hits: शुद्धलेखन नियम 1–4, 3, 12, 14) — printed, never a FAIL
        for where, t in (("note", note_txt), ("letter", letter_txt)):
            for x in warn_hits(t):
                warn(f"{where}: {x}")

        # signer chain + Finance (C30: the desk profile's chain — --desk, else detected from the note header line)
        ne = [b for b in bl[:note_end] if b["kind"] == "p" and ns(b["text"])]
        ntexts = [ns(b["text"]) for b in ne]
        did = desk_arg or _desk.detect_desk(ntexts[:1]) or _desk.DEFAULT_DESK
        try:
            dk = _desk.load_desk(did)
        except ValueError as e:
            check("desk profile", [str(e)]); dk = _desk.load_desk(None)
        print(f"OK: desk profile — {dk['id']}")
        # अनौपचारिक संदर्भ (note "uo"; NPM परिशिष्ट-8 form foot, mkdocs.uo_lines): [department,
        # "<to> विभागाकडे अनौपचारिक संदर्भ कार्यासन <desk>", "क्रमांक <no> दिनांक <date>"] after the signers
        ui = next((i for i, t in enumerate(ntexts) if UO_LINE_RE.search(t)), None)
        if ui is not None:
            up = []
            if ui == 0 or not ntexts[ui - 1].endswith("विभाग"): up.append("sender department line missing above the U.O. line")
            if ui + 1 >= len(ntexts) or not re.match(r"क्रमांक\s+\S.*\sदिनांक\s+\S", ntexts[ui + 1]):
                up.append("'क्रमांक … दिनांक …' line missing below the U.O. line")
            k0 = 0
            while ui - 2 - k0 >= 0 and ntexts[ui - 2 - k0] in desk_signers(dk)[0] + [desk_signers(dk)[1]]:
                k0 += 1
            if not k0: up.append("U.O. block not right after the signer chain")
            check("अनौपचारिक संदर्भ block (note foot)", up)
            ntexts = ntexts[:max(ui - 1, 0)] + ntexts[ui + 2:]
        D_SIGNERS, D_AMS = desk_signers(dk)
        has_ams = D_AMS in ntexts
        k = 0
        while k < len(ntexts) and ntexts[len(ntexts) - 1 - k] in D_SIGNERS + [D_AMS]:
            k += 1
        sig_start = len(ntexts) - k
        tail = ntexts[sig_start:]
        sp = signer_problems(tail, has_ams, dk)
        stray = [t for t in ntexts[:sig_start] if t in D_SIGNERS + [D_AMS]]
        if stray: sp.append(f"signer lines outside the signer block: {stray}")
        check("note signer chain (§4.6)", sp)
        numbered = [t for t in ntexts[:sig_start] if re.match(r"[0-9०-९]+\.", t)]
        last = numbered[-1] if numbered else (ntexts[sig_start - 1] if sig_start else "")
        # a separate closing line "मान्यतेस्तव सादर." (spec note.closing, Format-1/2) belongs to the last para (as in lint_spec)
        if numbered and sig_start and BARE_CLOSING_RE.match(ntexts[sig_start - 1]):
            last = last + " " + ntexts[sig_start - 1]
        # audit Q-F5: a full closing para (spec note.closing "सबब, …", printed unnumbered right above the signers) is the
        # last para, as lint_spec.last_para reads it
        elif numbered and sig_start and not re.match(r"[0-9०-९]+\.", ntexts[sig_start - 1]) \
                and any(r.match(ntexts[sig_start - 1]) for r in LAST_FORMS):
            last = ntexts[sig_start - 1]
        check("अ.मु.स. (वित्त) <=> Finance last para", finance_problems(last, has_ams, dk))

        # status.json `letter_needed` (engine; reported to the app) must agree with the built file
        sj = os.path.join(out, "status.json")
        if os.path.exists(sj):
            try:
                ln = json.load(open(sj, encoding="utf-8-sig")).get("letter_needed")
            except Exception as e:
                ln = e
            if isinstance(ln, bool):
                check("status.json letter_needed = letter in Note_and_Letter",
                      [] if ln == has_letter else [f"letter_needed {str(ln).lower()} but the Note_and_Letter "
                                                   + ("has a letter" if has_letter else "has no letter")])
            else:
                check("status.json letter_needed = letter in Note_and_Letter",
                      [f"status.json letter_needed not true/false ({ln!r})"[:120]])

        # letter: ordinary letters / स्मरणपत्र from std_start; अर्धशासकीय पत्र from do_i — each up to the other or the end
        if not has_letter:
            print("OK: letter — none (note only)")
        if do_i is not None:
            do_end = std_start if (has_std and std_start > do_i) else n
            for cname, probs in do_letter_problems(bl[do_i:do_end], NL, dk):
                check(cname, probs)
            check("अर्धशासकीय पत्र on a new page / section",
                  [] if new_page_before(bl, do_i) else ["no page or section break before the D.O. number line"])
        if has_std:
            std_end = do_i if (do_i is not None and do_i > std_start) else n
            std_txt = txt(std_start, std_end)
            lb = bl[std_start:std_end]
            lp = [Paragraph(b["el"], NL.element.body) for b in lb if b["kind"] == "p"]
            lt = [ns(p.text) for p in lp]
            pr = []
            if kram is None: pr.append("'क्रमांक :-' line missing")
            elif not _desk.letter_ref_re(dk).search(bl[kram]["text"]):
                pr.append(f"ref no. not {dk['letter']['ref_hint']}: '{ns(bl[kram]['text'])}'")

            if prati is None: pr.append("'प्रति,' missing")
            lh_email = (dk["letter"].get("email") or "").strip()   # checked only when the profile has one (C30)
            if lh_email and lh_email not in std_txt: pr.append(f"letterhead e-mail {lh_email} missing")
            check("letter ref no. / letterhead", pr)
            check("letter on a new page / section",
                  [] if new_page_before(bl, std_start) else ["no page or section break before the letterhead"])
            vb = []
            vi = next((i for i, t in enumerate(lt) if t.startswith("विषय")), None)
            mi = next((i for i, t in enumerate(lt) if t.startswith("महोदय")), None)
            if vi is None: vb.append("'विषय' paragraph missing")
            if not any(t.startswith("संदर्भ") for t in lt): vb.append("'संदर्भ' paragraph missing")
            if vi is not None:
                for p in lp[vi:(mi if mi is not None and mi > vi else vi + 1)]:
                    if not p.text.strip(): continue
                    if not p_centred(p): vb.append(f"not centred: '{ns(p.text)[:40]}'")
                    if not p_bold(p): vb.append(f"not bold: '{ns(p.text)[:40]}'")
            check("letter विषय/संदर्भ bold + centre", vb)
            intro = next((t for t in lt if t.startswith(INTRO_HEAD)), None)
            rq = []
            if intro is None: rq.append("intro paragraph 'उपरोक्त विषयाबाबत …' missing")
            elif requests_info(letter_info(lb, std_txt), intro) and REQUEST not in unquoted(intro): rq.append(f"intro lacks '{REQUEST}' — '…उपलब्ध करून देण्यात यावी, {REQUEST}.'")
            check("letter intro request wording §4.18", rq)
            en = []
            if "आपला," not in lt: en.append("'आपला,' line missing")
            if any(re.fullmatch(r"आपली\s*,?", t) for t in lt) or re.search(r"आपली\s*,", std_txt):
                en.append("signature 'आपली,' present (must be 'आपला,')")  # "आपली पत्रे" in संदर्भ is grammatical
            for line in _desk.letter_end_lines(dk):   # C30: signature / post / copy line of the desk profile
                if ns(line) not in lt: en.append(f"line '{ns(line)}' missing")
            check("letter ending (§4.5)", en)
        if meta and has_letter:   # audit Q-F14: every letter's number line against the case row (--case-meta)
            lines = [ns(b["text"]) for b in bl[lstart:] if b["kind"] == "p"
                     and (re.match(r"\s*क्रमांक\s*:?\s*-", b["text"]) or DO_LINE_RE.match(b["text"]))]
            check("letter ref no. = case file no. (--case-meta)",
                  [x for ln in lines for x in ref_meta_problems(ln, meta)])
        hl_ctx = {"note": note_txt, "related": rel_txt, "sources": rel_src}

    # ---------------- optional outputs (order draft, parawise) ----------------
    for suffix, label in EXTRA_DOCS:
        fx = os.path.join(out, f"{pre}{suffix}")
        if not os.path.exists(fx):
            continue
        try:
            X = docx.Document(fx)
        except Exception as e:
            check(f"{label} opens", [f"{fx}: {e}"]); continue
        xt = doc_text(X)
        check(f"{label} fonts", font_problems(X, label, AFFIDAVIT_FONTS if label == "Affidavit" else None))
        check(f"{label} internal ids", [f"internal id {x}" for x in id_hits(xt)])
        check(f"{label} repo paths", [f"repo path/word '{x}'" for x in repo_hits(xt)])
        check(f"{label} पृ. references", ref_problems(xt, N, label, skip_quotes=True))
        check(f"{label} no package / warning / AI words", [f"'{w}'" for w in draft_word_hits(xt)])
        check(f"{label} metadata (no tool / AI trace)", docx_meta_problems(fx))

    # ---------------- Package PDF ----------------
    if P is not None:
        if orig is not None:  # §4.16: the original name is kept even if it looks machine-made
            want = strip_upload_prefix(os.path.basename(orig))
            check("package file name = original proposal name",
                  [] if os.path.basename(pkg) in name_forms(orig)
                  else [f"'{os.path.basename(pkg)}' != original name '{want}'"])
        else:
            check("package file name = original proposal name",
                  [f"'{os.path.basename(pkg)}' is a generated name"] if re.search(r"_Proposal_with_GRs\.pdf$", pkg, re.I) else [])
        stp = []
        for i, pg in enumerate(P, 1):
            r = pg.rect
            strip = ns(pg.get_text("text", clip=m.Rect(r.x0, r.y1 - 40, r.x1, r.y1)))
            if f"पृ. {i} / {N}" not in strip:
                stp.append(f"page {i}")
        check(f"page stamps 'पृ. i / {N}' (bottom strip)", [f"no stamp on {', '.join(stp[:10])}{' …' if len(stp) > 10 else ''}"] if stp else [])
        check("bookmarks", [] if P.get_toc() else ["package has no bookmarks"])
        check("package PDF metadata (no tool / AI trace)", pdf_meta_problems(P))
        mpath = pkg + ".map.json"
        mp_pr = []
        unmarked = set(range(1, npp + 1))  # pages that must carry no annotation: the proposal (+ reply parts, below)
        try:
            mp = json.load(open(mpath, encoding="utf-8-sig"))
        except Exception as e:
            mp = None; mp_pr.append(f"{mpath}: {e}")
        if mp is not None:
            ents = {k: v for k, v in mp.items() if isinstance(v, dict) and "pages" in v}
            prop = mp.get("प्रस्ताव") or next((v for v in ents.values() if v.get("first_page") == 1), None)
            # reply / concurrence letters appended right after the proposal (pkg3 --also / "proposal_parts")
            parts = [ents[k] for k in (mp.get("proposal_parts") or []) if k in ents]
            part_pages = [p for v in parts for p in v["pages"]]
            if prop is not None:
                unmarked |= set(prop["pages"])
            unmarked |= set(part_pages)
            if prop is None: mp_pr.append("no proposal entry in map")
            elif len(prop["pages"]) != npp and len(prop["pages"]) + len(part_pages) != npp:
                mp_pr.append(f"map has {len(prop['pages'])} proposal pages"
                             + (f" (+{len(part_pages)} reply pages)" if part_pages else "") + f", given {npp}")
            tot = sum(len(v["pages"]) for v in ents.values())
            if tot != N: mp_pr.append(f"package has {N} pages but proposal + enclosures = {tot} (separator/extra pages?)")
            for mk in mp.get("marks", []) or []:
                stt = str(mk.get("status", ""))
                if "NOT FOUND" in stt.upper() or stt == "page not included" or ("hits" in mk and not mk["hits"]):
                    mp_pr.append(f"mark not placed: {mk.get('label', '')} p.{mk.get('pdf_page', mk.get('src_page', '?'))} ({stt or 'hits 0'})")
        check("map.json (page count, marks)", mp_pr)
        an_prop, an_kind = [], []
        for i, pg in enumerate(P):
            an = [a.type[1] for a in pg.annots()]
            if (i + 1) in unmarked and an: an_prop.append(f"proposal page {i + 1} has annotations {sorted(set(an))}")
            elif any(x != "Highlight" for x in an): an_kind.append(f"page {i + 1}: non-highlight annotation {sorted(set(an))}")
        # two checks: annotations on the proposal pages are HARD for the engine (engine_supabase HARD_CHECK); the type rule is soft
        check("annotations on proposal pages (none)", an_prop)
        check("annotations (Highlight only)", an_kind)
        # audit Q-F17 (WARN only): every cited GR page range has a highlight; every highlight lies in a quoted extract
        if hl_ctx is not None:
            msg, ws = highlight_findings(P, unmarked, hl_ctx)
            print(f"OK: highlight coverage — {msg}")
            for x in ws:
                warn(x)

    ok = all(results)
    print("ALL OK" if ok else "FIX THE FAILS ABOVE", "| pages", N, "| toc", len(P.get_toc()) if P is not None else 0)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
