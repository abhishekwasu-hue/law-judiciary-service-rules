#!/usr/bin/env python3
"""build_note_letter.py <spec.json> <outdir> <PREFIX>
spec.json -> <outdir>/<PREFIX>_Note_and_Letter.docx (note; if spec has "letter": page break + letter on letterhead).
Uses tools/mkdocs.py (Section templates, tables supported) + docxcompose. Checks that every text run is DVOT-SurekhMR.
Also writes <outdir>/<PREFIX>_Note_and_Letter.pdf preview if LibreOffice (soffice) is available."""
import os, sys, subprocess, tempfile, shutil
import docx
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_BREAK
from docx.oxml.ns import qn
spec, outdir, pre = sys.argv[1], sys.argv[2], sys.argv[3]
here = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp()
subprocess.run([sys.executable, os.path.join(here, "mkdocs.py"), spec, tmp, pre], check=True)
note = docx.Document(os.path.join(tmp, f"{pre}_Note.docx"))
out = os.path.join(outdir, f"{pre}_Note_and_Letter.docx")
os.makedirs(outdir, exist_ok=True)
lp = os.path.join(tmp, f"{pre}_Letter.docx")
if os.path.exists(lp):
    from docxcompose.composer import Composer
    let = docx.Document(lp); let.sections[0].start_type = WD_SECTION.NEW_PAGE
    note.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    c = Composer(note); c.append(let); c.save(out)
else:
    note.save(out)
d = docx.Document(out); bad = 0
for el in d.element.body.iter(qn("w:r")):
    t = "".join(x.text or "" for x in el.iter(qn("w:t")))
    rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
    if t.strip() and (f is None or f.get(qn("w:cs")) != "DVOT-SurekhMR"): bad += 1
print(out, "letter" if os.path.exists(lp) else "NO letter", "bad-font runs:", bad)
if shutil.which("soffice"):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
shutil.rmtree(tmp, ignore_errors=True)
