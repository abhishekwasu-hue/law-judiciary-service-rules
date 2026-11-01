#!/usr/bin/env python3
"""pkg.py <proposal.pdf> <enclosures.json> <out.pdf> <title>
Proposal scan first (unchanged), then per enclosure: separator page + selected ORIGINAL pages."""
import sys, json, os, subprocess, tempfile
from pypdf import PdfReader, PdfWriter
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

FONT = "FreeSerif"

def to_pdf(docx, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, docx], check=True, capture_output=True)
    return os.path.join(outdir, os.path.splitext(os.path.basename(docx))[0] + ".pdf")

def sep(lines, tmp, name):
    d = Document()
    for _ in range(8): d.add_paragraph()
    for text, size, bold in lines:
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold
        r.font.name = FONT
        rf = r._element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): rf.set(qn(a), FONT)
    f = os.path.join(tmp, name + ".docx"); d.save(f); return to_pdf(f, tmp)

def pages_of(spec, n):
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        else: out.append(int(part))
    return [p for p in out if 1 <= p <= n]

prop, js, out, title = sys.argv[1:5]
encs = json.load(open(js, encoding="utf-8"))
tmp = tempfile.mkdtemp(); w = PdfWriter()
pr = PdfReader(prop)
for pg in pr.pages: w.add_page(pg)
for i, e in enumerate(encs, 1):
    r = PdfReader(e["path"]); sel = pages_of(e["pages"], len(r.pages))
    for p in sel: w.add_page(r.pages[p - 1])
w.write(out); print(out, len(w.pages), "pages")
