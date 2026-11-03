#!/usr/bin/env python3
"""study_warnings.py append <study.docx> <warnings.json|->
Abhi, 03.11.2026: "हे इशारे नोटिंग मध्ये नको हे इशारे जी एक स्वतंत्र आपली स्टडी म्हणून डॉक्युमेंट फाईल असते त्याच्यामध्ये
द्या" — the final run warnings ("पडताळणी अपूर्ण — …", "अंतिम पडताळणी (Opus) मान्यता नाही — …", extract mismatches,
verify soft FAILs, status.json warnings) go INTO <PREFIX>_Study.docx, at the END of भाग 7 (no new "भाग 8" heading:
verify_outputs.py / lint_spec.part_no read every paragraph starting "भाग N" as a part heading):
    अंतिम तपासणीचे इशारे (वापरण्यापूर्वी तपासा)      (bold sub-heading)
    1. <warning as stored>
    2. …
No warning -> one line "कोणताही इशारा नाही.". Owner-only lines (model routing "मॉडेल: …", cost lines "खर्च …", AI-provider
lines "मुख्य AI …" / "राखीव AI …") are NOT written — they stay in the app for the owner (same rule as
dashboard-app/src/lib/format.ts isOwnerOnlyLine). Idempotent: an existing section is replaced. Every run in
DVOT-SurekhMR (ascii/hAnsi/cs/eastAsia); then clean_meta.clean_docx (author kept).
warnings.json = a JSON list of strings (or {"warnings": [...]}); "-" reads it from stdin.
Functions: study_lines(warnings) -> the lines written; append(path, warnings) -> that list."""
import json
import os
import re
import sys

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean_meta import clean_docx  # noqa: E402
from lint_spec import part_no  # noqa: E402 — the same "भाग N" heading rule as verify_outputs.py

F = "DVOT-SurekhMR"
HEADING = "अंतिम तपासणीचे इशारे (वापरण्यापूर्वी तपासा)"
NONE_LINE = "कोणताही इशारा नाही."
# owner-only lines (contract with dashboard-app/src/lib/format.ts OWNER_ONLY_PREFIXES — keep both identical)
OWNER_ONLY_PREFIXES = ("मॉडेल:", "खर्च", "मुख्य AI", "राखीव AI")


def is_owner_only(line):
    t = str(line or "").strip()
    return any(t.startswith(p) for p in OWNER_ONLY_PREFIXES)


def study_lines(warnings):
    """Final warnings for the Study: text as stored, trimmed, owner-only lines dropped, duplicates removed (order kept)."""
    out, seen = [], set()
    for w in warnings or []:
        t = re.sub(r"\s+", " ", str(w if not isinstance(w, dict) else w.get("text") or w.get("warning") or "")).strip()
        if not t or is_owner_only(t) or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _text(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def _para(text, bold=False, size=12):
    """A detached <w:p> with one DVOT-SurekhMR run (built through python-docx on a scratch paragraph)."""
    p = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:after"), "80")
    ppr.append(sp)
    if bold:  # keep the sub-heading with the first item
        ppr.append(OxmlElement("w:keepNext"))
    p.append(ppr)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    for k in ("ascii", "hAnsi", "cs", "eastAsia"):
        rf.set(qn("w:" + k), F)
    rpr.append(rf)
    if bold:
        rpr.append(OxmlElement("w:b"))
        rpr.append(OxmlElement("w:bCs"))
    for tag in ("w:sz", "w:szCs"):
        e = OxmlElement(tag)
        e.set(qn("w:val"), str(int(size * 2)))
        rpr.append(e)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    p.append(r)
    return p


def _blocks(body):
    return [el for el in body if el.tag in (qn("w:p"), qn("w:tbl"))]


def append(path, warnings):
    """Write (or replace) the warnings section at the end of भाग 7 of the Study; returns the lines written."""
    lines = study_lines(warnings)
    d = docx.Document(path)
    author = d.core_properties.author or None
    body = d.element.body
    blocks = _blocks(body)
    # idempotent: drop an earlier section (its heading up to the next part heading / end of the document)
    start = next((i for i, el in enumerate(blocks) if el.tag == qn("w:p") and _text(el).strip() == HEADING), None)
    if start is not None:
        for el in blocks[start:]:
            if el is not blocks[start] and el.tag == qn("w:p") and part_no(_text(el)) is not None:
                break
            body.remove(el)
        blocks = _blocks(body)
    # end of भाग 7 = before the next part heading after it (none in a normal Study), else the end of the body
    h7 = next((i for i, el in enumerate(blocks) if el.tag == qn("w:p") and part_no(_text(el)) == 7), None)
    anchor = None
    if h7 is not None:
        anchor = next((el for el in blocks[h7 + 1:] if el.tag == qn("w:p") and part_no(_text(el)) is not None), None)
    if anchor is None:
        anchor = body.find(qn("w:sectPr"))  # body-level section properties stay last
    new = [_para(HEADING, bold=True, size=13)]
    new += [_para(f"{i}. {t}") for i, t in enumerate(lines, 1)] if lines else [_para(NONE_LINE)]
    for el in new:
        if anchor is not None:
            anchor.addprevious(el)
        else:
            body.append(el)
    d.save(path)
    clean_docx(path, author)
    return lines


def _load(src):
    raw = sys.stdin.read() if src == "-" else open(src, encoding="utf-8-sig").read()
    obj = json.loads(raw or "[]")
    if isinstance(obj, dict):
        obj = obj.get("warnings") or []
    return obj if isinstance(obj, list) else []


def main(argv):
    if len(argv) != 3 or argv[0] != "append":
        sys.exit(__doc__)
    lines = append(argv[1], _load(argv[2]))
    print(f"study_warnings: {len(lines)} warning(s) written to {os.path.basename(argv[1])}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main(sys.argv[1:])
