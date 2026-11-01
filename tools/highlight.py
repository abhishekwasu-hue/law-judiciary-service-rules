#!/usr/bin/env python3
"""highlight.py <package.pdf> <marks.json>   (edits the PDF in place; yellow highlights only — NEVER boxes)
Use after tools/pkg3.py when its text search cannot mark a page (scanned GR, legacy/garbled Devanagari font, or a
string that repeats elsewhere on the page). marks.json = list of:
  {"page": N, "mode": "lines", "y0": a, "y1": b}            text-layer lines whose top lies in [a,b] (PDF points, page N of the PACKAGE)
  {"page": N, "mode": "ocr",   "y0": a, "y1": b}            scanned page: OCR (tesseract eng) line boxes whose top lies in [a,b] (points)
  {"page": N, "mode": "rect",  "rects": [[x0,y0,x1,y1],...]} explicit line rectangles (points) — one per printed line
Tips: get line positions with  python3 -c "import pymupdf as m;d=m.open('p.pdf');[print(round(l['bbox'][1]),''.join(s['text'] for s in l['spans'])[:60]) for b in d[N-1].get_text('dict')['blocks'] for l in b.get('lines',[])]"
Render the page afterwards and LOOK: highlight only the quoted lines."""
import sys, json, os, csv, subprocess, tempfile
import pymupdf as m
pdf, mj = sys.argv[1], sys.argv[2]
d = m.open(pdf); marks = json.load(open(mj, encoding="utf-8")); n = 0
def add(pg, r):
    global n
    a = pg.add_highlight_annot(r); a.set_colors(stroke=(1, 1, 0)); a.update(); n += 1
for mk in marks:
    pg = d[mk["page"] - 1]
    if mk["mode"] == "lines":
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).strip()
                if t and mk["y0"] <= l["bbox"][1] <= mk["y1"]: add(pg, m.Rect(l["bbox"]))
    elif mk["mode"] == "rect":
        for r in mk["rects"]: add(pg, m.Rect(r))
    elif mk["mode"] == "ocr":
        dpi = 150; k = 72 / dpi
        tmp = tempfile.mkdtemp(); png = os.path.join(tmp, "p.png")
        pg.get_pixmap(dpi=dpi).save(png)
        subprocess.run(["tesseract", png, os.path.join(tmp, "o"), "-l", "eng", "tsv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = list(csv.DictReader(open(os.path.join(tmp, "o.tsv")), delimiter="\t", quoting=csv.QUOTE_NONE)); L = {}
        for r in rows:
            if r["level"] == "5" and r["text"].strip(): L.setdefault((r["block_num"], r["par_num"], r["line_num"]), []).append(r)
        for ws in L.values():
            x0 = min(int(w["left"]) for w in ws); x1 = max(int(w["left"]) + int(w["width"]) for w in ws)
            top = sorted(int(w["top"]) for w in ws)[len(ws) // 2] * k
            if mk["y0"] <= top <= mk["y1"]: add(pg, m.Rect(x0 * k, top, x1 * k, top + 14))
tmpout = pdf + ".tmp"; d.save(tmpout, garbage=3, deflate=True); os.replace(tmpout, pdf)
print("highlights added:", n)
