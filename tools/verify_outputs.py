#!/usr/bin/env python3
"""verify_outputs.py <outdir> <PREFIX> "<package pdf>" <proposal pages> [--original-name NAME]
Quality gate for one proposal's three outputs (PROPOSAL_SOP.md Step 7; rules INSTRUCTIONS.md §4).
Prints one line per check ("OK: ..." / "FAIL: ...") and "ALL OK" only when every check passes; exit code 1 otherwise.
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
 Note (start of Note_and_Letter up to "संबंधित माहिती (संदर्भासाठी)" or the letter):
  - signer chain = INSTRUCTIONS §4.6 names in order, "अ.मु.स. (वित्त)" last
  - "अ.मु.स. (वित्त)" present  <=>  last numbered para contains "वित्त विभागाच्या मान्यतेस्तव"
 Note body and letter: no "पॅकेज PDF" (allowed only in "संबंधित माहिती" and the Study); no BANNED word
 Note body and letter (§4.18, text outside “…” quotes only): no 'सौ.'; 'श्री.' followed by a space; letter: no 'तात्काळ'
 Note body and letter (§4.19, outside quotes, lint_spec.lang_hits): no '.:-', no 'करुन' / 'प्रारुप', a space after
  'दि.' / 'क्र.' / 'प्र. क्र.' in running text (file nos. / codes with '/' or '-' skipped); missing-info para 'नाही:-'
 Note_and_Letter (whole file): no repo paths (register/, service-rules/, precedent-library/, pdf/, repo, रेपो)
 Letter (when present: a "प्रति," or "क्रमांक :-" paragraph):
  - starts on a new page / new section (page break or section break before the letterhead)
  - ref no. संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6 ; e-mail lnjd.desk6-mh@mah.gov.in on the letterhead
  - विषय and संदर्भ paragraphs: centred, every run bold
  - intro paragraph (starting "उपरोक्त विषयाबाबत") contains "ही विनंती" outside quotes (§4.18)
  - "आपला," present, signature "आपली," absent ("आपली पत्रे" in संदर्भ is allowed); lines "( राजेश वडनेरकर )", "अवर सचिव ,महाराष्ट्र शासन", "प्रत : निवड नस्ती"
 status.json (when <outdir>/status.json exists): `letter_needed` is true/false and true <=> a letter is present
 Study: headings भाग 0 … भाग 7
 Package PDF:
  - file name is the original proposal name (not *_Proposal_with_GRs.pdf); with --original-name NAME: the file name must
    equal NAME minus a random upload prefix like "11ae057d-" (engine_supabase.strip_upload_prefix: 8 hex characters
    with at least one letter a-f, so "20261101-CR130.pdf" is kept as is; the *_Proposal_with_GRs.pdf ban is then skipped, §4.16)
  - every page carries exactly "पृ. i / N" in the bottom 40 pt strip; bookmarks present
  - <pdf>.map.json: proposal pages == <proposal pages>; total pages == proposal + enclosure pages (no separator pages);
    no mark with status "TEXT NOT FOUND" / "page not included" or hits == 0 (works with or without per-mark "hits")
  - no annotation on proposal pages; only Highlight annotations elsewhere
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
from lint_spec import (AMS, BANNED, FIN, ID_RE, LH_EMAIL, RELATED, REF_NO, REPO_RE, REQUEST,  # noqa: E402,F401
                       MISSING_FORM, MISSING_HEAD, SIGNERS, banned_hits, finance_problems, heading_problems, id_hits,
                       lang_hits, ns, num, part_no, ref_problems, repo_hits, signer_problems, style_hits, unquoted)
INTRO_HEAD = "उपरोक्त विषयाबाबत"  # letter intro paragraph (lint_spec.INTRO_START begins with it)
from engine_supabase import strip_upload_prefix  # noqa: E402 — the ONE upload-prefix rule (§4.16)

results = []


def check(name, problems):
    """problems: list of strings (empty = OK)."""
    results.append(not problems)
    if problems:
        shown = "; ".join(problems[:6]) + (f"; … (+{len(problems) - 6})" if len(problems) > 6 else "")
        print(f"FAIL: {name} — {shown}")
    else:
        print(f"OK: {name}")






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


def font_problems(d, label):
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
            if fo is None or any(fo.get(qn("w:" + a)) != FONT for a in FONT_ATTRS) or any(fo.get(qn("w:" + a)) is not None for a in THEME_ATTRS):
                bad += 1
    return [f"{label}: {bad} text runs without {FONT} on all four rFonts attributes"] if bad else []




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


def main(argv):
    argv = list(argv); orig = None
    if "--original-name" in argv:
        i = argv.index("--original-name")
        if i + 1 >= len(argv):
            print(__doc__); return 2
        orig = argv[i + 1]; del argv[i:i + 2]
    if len(argv) != 5:
        print(__doc__); return 2
    out, pre, pkg, npp = argv[1], argv[2], argv[3], int(argv[4])
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
        has_letter = kram is not None or prati is not None
        lstart = None
        if has_letter:
            anchor = kram if kram is not None else prati
            lstart = anchor
            for j in range(anchor - 1, max(-1, anchor - 9), -1):
                if ns(bl[j]["text"]) == "महाराष्ट्र शासन":
                    lstart = j; break
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
        pk = []
        if "पॅकेज PDF" in note_txt: pk.append("note body uses 'पॅकेज PDF' — use पृ.N/प.वि.")
        if "पॅकेज PDF" in letter_txt: pk.append("letter uses 'पॅकेज PDF'")
        check("'पॅकेज PDF' only in संबंधित माहिती", pk)
        check("banned words (note body, letter)",
              [f"{where}: '{w}'" for where, t in (("note", note_txt), ("letter", letter_txt)) for w in banned_hits(t)])

        check("respectful wording §4.18 (note body, letter)",
              [f"{where}: {x}" for where, t, isl in (("note", note_txt, False), ("letter", letter_txt, True))
               for x in style_hits(t, letter=isl)])

        # §4.19 (मराठी भाषा विभाग GR दि. 10.11.2022): same helpers as the pre-build lint, text outside quotes
        lg = [f"{where}: {x}" for where, t in (("note", note_txt), ("letter", letter_txt)) for x in lang_hits(t)]
        lg += [f"note: missing-info para — form '{MISSING_FORM}'" for b in bl[:note_end] if b["kind"] == "p"
               and re.sub(r"^[0-9०-९]+\.\s*", "", ns(unquoted(b["text"]))).startswith(MISSING_HEAD)
               and not re.sub(r"^[0-9०-९]+\.\s*", "", ns(b["text"])).startswith(MISSING_HEAD + ":-")]
        check("official Marathi §4.19 (note body, letter)", lg)

        # signer chain + Finance
        ne = [b for b in bl[:note_end] if b["kind"] == "p" and ns(b["text"])]
        ntexts = [ns(b["text"]) for b in ne]
        has_ams = AMS in ntexts
        k = 0
        while k < len(ntexts) and ntexts[len(ntexts) - 1 - k] in SIGNERS + [AMS]:
            k += 1
        sig_start = len(ntexts) - k
        tail = ntexts[sig_start:]
        sp = signer_problems(tail, has_ams)
        stray = [t for t in ntexts[:sig_start] if t in SIGNERS + [AMS]]
        if stray: sp.append(f"signer lines outside the signer block: {stray}")
        check("note signer chain (§4.6)", sp)
        numbered = [t for t in ntexts[:sig_start] if re.match(r"[0-9०-९]+\.", t)]
        last = numbered[-1] if numbered else (ntexts[sig_start - 1] if sig_start else "")
        check("अ.मु.स. (वित्त) <=> Finance last para", finance_problems(last, has_ams))

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

        # letter
        if not has_letter:
            print("OK: letter — none (note only)")
        else:
            lb = bl[lstart:]
            lp = [Paragraph(b["el"], NL.element.body) for b in lb if b["kind"] == "p"]
            lt = [ns(p.text) for p in lp]
            pr = []
            if kram is None: pr.append("'क्रमांक :-' line missing")
            elif not REF_NO.search(bl[kram]["text"]): pr.append(f"ref no. not संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6: '{ns(bl[kram]['text'])}'")
            if prati is None: pr.append("'प्रति,' missing")
            if LH_EMAIL not in letter_txt: pr.append(f"letterhead e-mail {LH_EMAIL} missing")
            check("letter ref no. / letterhead", pr)
            prev = lstart - 1
            while prev > 0 and not ns(bl[prev]["text"]) and not bl[prev]["brk"]:
                prev -= 1
            newpage = any(b["brk"] for b in bl[max(prev, 0):lstart + 1])
            check("letter on a new page / section", [] if newpage else ["no page or section break before the letterhead"])
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
            elif REQUEST not in unquoted(intro): rq.append(f"intro lacks '{REQUEST}' — '…उपलब्ध करून देण्यात यावी, {REQUEST}.'")
            check("letter intro request wording §4.18", rq)
            en = []
            if "आपला," not in lt: en.append("'आपला,' line missing")
            if any(re.fullmatch(r"आपली\s*,?", t) for t in lt) or re.search(r"आपली\s*,", letter_txt):
                en.append("signature 'आपली,' present (must be 'आपला,')")  # "आपली पत्रे" in संदर्भ is grammatical
            for line in ("( राजेश वडनेरकर )", "अवर सचिव ,महाराष्ट्र शासन", "प्रत : निवड नस्ती"):
                if line not in lt: en.append(f"line '{line}' missing")
            check("letter ending (§4.5)", en)

    # ---------------- Package PDF ----------------
    if P is not None:
        if orig is not None:  # §4.16: the original name is kept even if it looks machine-made
            want = strip_upload_prefix(os.path.basename(orig))
            check("package file name = original proposal name",
                  [] if os.path.basename(pkg) == want else [f"'{os.path.basename(pkg)}' != original name '{want}'"])
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
        mpath = pkg + ".map.json"
        mp_pr = []
        try:
            mp = json.load(open(mpath, encoding="utf-8-sig"))
        except Exception as e:
            mp = None; mp_pr.append(f"{mpath}: {e}")
        if mp is not None:
            ents = {k: v for k, v in mp.items() if isinstance(v, dict) and "pages" in v}
            prop = mp.get("प्रस्ताव") or next((v for v in ents.values() if v.get("first_page") == 1), None)
            if prop is None: mp_pr.append("no proposal entry in map")
            elif len(prop["pages"]) != npp: mp_pr.append(f"map has {len(prop['pages'])} proposal pages, given {npp}")
            tot = sum(len(v["pages"]) for v in ents.values())
            if tot != N: mp_pr.append(f"package has {N} pages but proposal + enclosures = {tot} (separator/extra pages?)")
            for mk in mp.get("marks", []) or []:
                stt = str(mk.get("status", ""))
                if "NOT FOUND" in stt.upper() or stt == "page not included" or ("hits" in mk and not mk["hits"]):
                    mp_pr.append(f"mark not placed: {mk.get('label', '')} p.{mk.get('pdf_page', mk.get('src_page', '?'))} ({stt or 'hits 0'})")
        check("map.json (page count, marks)", mp_pr)
        an_pr = []
        for i, pg in enumerate(P):
            an = [a.type[1] for a in pg.annots()]
            if i < npp and an: an_pr.append(f"proposal page {i + 1} has annotations {sorted(set(an))}")
            elif any(x != "Highlight" for x in an): an_pr.append(f"page {i + 1}: non-highlight annotation {sorted(set(an))}")
        check("annotations (none on proposal, Highlight only)", an_pr)

    ok = all(results)
    print("ALL OK" if ok else "FIX THE FAILS ABOVE", "| pages", N, "| toc", len(P.get_toc()) if P is not None else 0)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
