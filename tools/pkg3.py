#!/usr/bin/env python3
"""pkg3.py <proposal.pdf> <enclosures.json> <out.pdf>
Proposal returned WITH its GRs (Abhi's standing rule):
  - proposal scan first (unchanged), then only the selected ORIGINAL pages of each GR/rule/judgment
  - NO separator / title / index pages
  - every page stamped at the bottom: "पृ. N / एकूण"
  - PDF bookmarks (outline): proposal + each enclosure -> click jumps to its first page
  - marking: quoted text highlighted in yellow (search on the text layer); for scanned pages give a box
  - writes <out>.map.json : {label: {"first_page": N, "pages": [..]}, "marks": [...]} -> cite "(पॅकेज PDF पृ. N)" in the note

enclosures.json:
[ {"path": "pdf/xx/GR-2019.pdf", "pages": "1-3,7", "label": "वित्त विभाग GR दि. 01.03.2019",
   "marks": [ {"page": 2, "text": "exact words from the GR text layer"},          # yellow highlight
              {"page": 3, "box": [x0, y0, x1, y1]} ] } ]                           # red box (scanned page), points
"page" in marks = page number INSIDE the source PDF.
Needs: pip install pymupdf --break-system-packages
"""
import sys, json
import pymupdf as fitz

FONTFILES = ["/usr/share/fonts/truetype/freefont/FreeSerif.ttf", "/usr/share/fonts/opentype/freefont/FreeSerif.otf"]


def pages_of(spec, n):
    out = []
    for part in str(spec or f"1-{n}").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [p for p in out if 1 <= p <= n]


def main(prop, js, out):
    encs = json.load(open(js, encoding="utf-8"))
    dst = fitz.open(); toc = []; mp = {}; report = []
    src = fitz.open(prop)
    dst.insert_pdf(src)
    toc.append([1, "प्रस्ताव", 1]); mp["प्रस्ताव"] = {"first_page": 1, "pages": list(range(1, len(src) + 1))}
    for e in encs:
        s = fitz.open(e["path"]); sel = pages_of(e.get("pages"), len(s))
        start = len(dst) + 1; where = {}
        for p in sel:
            dst.insert_pdf(s, from_page=p - 1, to_page=p - 1); where[p] = len(dst)
        label = e.get("label") or e["path"]
        toc.append([1, label, start]); mp[label] = {"first_page": start, "pages": [where[p] for p in sel]}
        for m in e.get("marks", []):
            sp = m.get("page")
            if sp not in where:
                report.append({"label": label, "src_page": sp, "status": "page not included"}); continue
            pg = dst[where[sp] - 1]
            if m.get("text"):
                hits = pg.search_for(m["text"])
                if hits:
                    a = pg.add_highlight_annot(hits); a.set_colors(stroke=(1, 1, 0)); a.update()
                    report.append({"label": label, "pdf_page": where[sp], "status": "highlighted", "hits": len(hits)})
                else:
                    report.append({"label": label, "pdf_page": where[sp], "status": "TEXT NOT FOUND (scanned?) - give box"})
            if m.get("box"):
                r = fitz.Rect(*m["box"]); a = pg.add_rect_annot(r); a.set_colors(stroke=(1, 0, 0)); a.set_border(width=1.5); a.update()
                report.append({"label": label, "pdf_page": where[sp], "status": "boxed"})
    tot = len(dst)
    ff = next((f for f in FONTFILES if __import__("os").path.exists(f)), None)
    for i, pg in enumerate(dst, 1):
        t = f"पृ. {i} / {tot}"; r = pg.rect
        box = fitz.Rect(r.width / 2 - 60, r.height - 22, r.width / 2 + 60, r.height - 6)
        pg.draw_rect(box, color=None, fill=(1, 1, 1), overlay=True)
        if ff:
            pg.insert_textbox(box, t, fontsize=10, fontname="fs", fontfile=ff, align=1)
        else:
            pg.insert_textbox(box, f"Page {i} / {tot}", fontsize=10, align=1)
    dst.set_toc(toc); dst.save(out, garbage=3, deflate=True)
    mp["marks"] = report
    json.dump(mp, open(out + ".map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out, tot, "pages;", sum(1 for r in report if r["status"] in ("highlighted", "boxed")), "marks;",
          [r for r in report if r["status"] not in ("highlighted", "boxed")])


if __name__ == "__main__":
    main(*sys.argv[1:4])
