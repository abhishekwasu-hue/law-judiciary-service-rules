#!/usr/bin/env python3
"""build_study.py <study.json> <out.docx>   — builds <PREFIX>_Study.docx (A4, 2 cm margins, DVOT-SurekhMR everywhere).
study.json = {"title": "C R 130/2026 — अभ्यास-फाइल", "parts": [
   {"heading": "भाग 0 — वरिष्ठांसाठी ब्रीफिंग", "blocks": [
       {"bullets": ["प्रस्ताव : ...", "मागणी : ..."]},
       {"table": [["तपशील","माहिती","पृ./प.वि."], ["...","...","..."]]},
       {"para": "free paragraph"},
       {"subheading": "(ई) मंजुरीच्या अटी"},
       {"image": "chart.png", "width_cm": 14}          # optional chart (briefing only)
   ]},
   {"heading": "भाग 1 — प्रस्तावाचे मराठी रूपांतर", "blocks": [...]}, ... ]}
Each part starts on a new page. Order and content of parts: INSTRUCTIONS.md §4.8, §4.17 and tools/PROPOSAL_PROMPT.md."""
import sys, json
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
F = "DVOT-SurekhMR"
spec = json.load(open(sys.argv[1], encoding="utf-8-sig")); out = sys.argv[2]
d = Document(); s = d.sections[0]; s.page_width, s.page_height = Cm(21), Cm(29.7)
for a in ("left_margin", "right_margin", "top_margin", "bottom_margin"): setattr(s, a, Cm(2))
def rf(el):
    rpr = el.get_or_add_rPr(); r = rpr.find(qn("w:rFonts"))
    if r is None: r = OxmlElement("w:rFonts"); rpr.append(r)
    for k in ("ascii", "hAnsi", "cs", "eastAsia"): r.set(qn("w:" + k), F)
for st in d.styles:
    try:
        if st.type in (1, 2, 3): st.font.name = F; rf(st.element)
    except Exception: pass
def run(p, t, b=False, size=12):
    r = p.add_run(t); r.bold = b; r.font.size = Pt(size); r.font.name = F; rf(r._r); return r
def para(t, b=False, size=12, indent=None, style=None):
    p = d.add_paragraph(style=style) if style else d.add_paragraph()
    run(p, t, b, size); p.paragraph_format.space_after = Pt(4)
    if indent: p.paragraph_format.left_indent = Cm(indent)
    return p
para(spec.get("title", ""), b=True, size=16)
for i, part in enumerate(spec["parts"]):
    if i: run(d.add_paragraph(), "").add_break(WD_BREAK.PAGE)
    para(part["heading"], b=True, size=14)
    for blk in part.get("blocks", []):
        if "subheading" in blk: para(blk["subheading"], b=True, size=12)
        elif "para" in blk: para(blk["para"])
        elif "bullets" in blk:
            for x in blk["bullets"]: para("•  " + x, indent=0.5)
        elif "table" in blk:
            rows = blk["table"]; t = d.add_table(rows=len(rows), cols=max(len(r) for r in rows)); t.style = "Table Grid"
            for ri, r in enumerate(rows):
                for ci, v in enumerate(r):
                    c = t.cell(ri, ci); c.text = ""; run(c.paragraphs[0], str(v), b=(ri == 0), size=11)
            d.add_paragraph()
        elif "image" in blk:
            d.add_picture(blk["image"], width=Cm(blk.get("width_cm", 14)))
d.save(out); print("ok", out)
