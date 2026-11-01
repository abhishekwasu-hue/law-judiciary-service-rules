#!/usr/bin/env python3
"""verify_outputs.py <outdir> <PREFIX> <package.pdf> <proposal_page_count>
Checks (prints FAIL lines): DVOT-SurekhMR on every text run (Study, Note_and_Letter); letter present -> 'आपला,' and
'प्रत : निवड नस्ती'; no internal ids (z6_0235...); note body has no 'पॅकेज PDF'; every 'पृ.N/प.वि.' exists in the package;
package has page stamps 'पृ. N / total' on every page, bookmarks, NO annotations on proposal pages, only Highlight annots."""
import sys, re, docx, pymupdf as m
from docx.oxml.ns import qn
out, pre, pkg, npp = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
ok = True
def fail(s):
    global ok; ok = False; print("FAIL:", s)
def text_of(doc):
    t = "\n".join(p.text for p in doc.paragraphs)
    for tb in doc.tables:
        for r in tb.rows: t += "\n" + " | ".join(c.text for c in r.cells)
    return t
P = m.open(pkg); N = len(P)
for suf in ("Study", "Note_and_Letter"):
    f = f"{out}/{pre}_{suf}.docx"
    try: d = docx.Document(f)
    except Exception as e: fail(f"{f}: {e}"); continue
    bad = 0
    for el in d.element.body.iter(qn("w:r")):
        t = "".join(x.text or "" for x in el.iter(qn("w:t")))
        rp = el.find(qn("w:rPr")); fo = rp.find(qn("w:rFonts")) if rp is not None else None
        if t.strip() and (fo is None or fo.get(qn("w:cs")) != "DVOT-SurekhMR"): bad += 1
    if bad: fail(f"{suf}: {bad} runs without DVOT-SurekhMR")
    t = text_of(d)
    if re.search(r"z[67]_\d{4}", t): fail(f"{suf}: internal file id present")
    if suf == "Note_and_Letter":
        body = t.split("संबंधित माहिती (संदर्भासाठी)")[0]
        if "पॅकेज PDF" in body: fail("note body uses 'पॅकेज PDF' — use पृ.N/प.वि.")
        if "प्रति," in t and ("आपला," not in t or "निवड नस्ती" not in t): fail("letter ending missing")
        for a, b in re.findall(r"पृ\.\s*(\d+)(?:\s*-\s*(\d+))?\s*/प\.वि\.", t):
            if int(b or a) > N: fail(f"पृ.{a}{'-'+b if b else ''}/प.वि. beyond package ({N} pages)")
if not P.get_toc(): fail("package has no bookmarks")
for i, pg in enumerate(P):
    if f"/ {N}" not in pg.get_text() and f"/{N}" not in pg.get_text(): fail(f"page {i+1}: no page stamp")
    an = [a.type[1] for a in pg.annots()]
    if i < npp and an: fail(f"proposal page {i+1} has annotations")
    if any(x != "Highlight" for x in an): fail(f"page {i+1}: non-highlight annotation {set(an)}")
print("ALL OK" if ok else "FIX THE FAILS ABOVE", "| pages", N, "| toc", len(P.get_toc()))
