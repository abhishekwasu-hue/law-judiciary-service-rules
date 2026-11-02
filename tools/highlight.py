#!/usr/bin/env python3
"""highlight.py <package.pdf> <marks.json>   (edits the PDF in place; yellow highlights only — NEVER boxes)
Use after tools/pkg3.py when its text search cannot mark a page (scanned GR, legacy/garbled Devanagari font, or a
string that repeats elsewhere on the page). marks.json = list of:
  {"page": N, "mode": "lines", "y0": a, "y1": b}            text-layer lines whose top lies in [a,b] (PDF points, page N of the PACKAGE)
  {"page": N, "mode": "ocr",   "y0": a, "y1": b, "lang": "mar+eng"}
                                                            scanned page: OCR (tesseract) line boxes whose top lies in [a,b] (points);
                                                            "lang" optional — default mar+eng when tesseract has Marathi data, else eng
  {"page": N, "mode": "rect",  "rects": [[x0,y0,x1,y1],...]} explicit line rectangles (points) — one per printed line
Exit code 1 (PDF left unchanged) if any mark gets 0 highlights, a page is out of range, or tesseract fails.
Tips: get line positions with  python3 -c "import pymupdf as m;d=m.open('p.pdf');[print(round(l['bbox'][1]),''.join(s['text'] for s in l['spans'])[:60]) for b in d[N-1].get_text('dict')['blocks'] for l in b.get('lines',[])]"
Render the page afterwards and LOOK: highlight only the quoted lines.
map.json (A1 M): when <package.pdf>.map.json exists (tools/pkg3.py), every pkg3 mark that was NOT placed ("TEXT NOT
FOUND" / hits 0) on a page this run highlights gets status "highlighted (highlight.py)" and hits = the highlights placed
there, so verify_outputs.py no longer reports it. A mark of marks.json may name the pkg3 mark it replaces with "label"
and/or "text" (then only that record is updated); without them every unplaced record of that page is updated."""
import sys, json, os, csv, subprocess, tempfile, shutil
import pymupdf as m
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean_meta import clean_pdf  # noqa: E402 — C27 §4: blank PDF metadata / annotation author


def add(pg, r):
    a = pg.add_highlight_annot(r); a.set_colors(stroke=(1, 1, 0)); a.update()


def ocr_lang(want):
    if want:
        return want
    try:
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
        langs = set((r.stdout + r.stderr).split())
    except OSError:
        langs = set()
    return "mar+eng" if "mar" in langs else "eng"


def ocr_lines(pg, lang):
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract not installed (needed for mode 'ocr')")
    dpi = 150; k = 72 / dpi
    tmp = tempfile.mkdtemp()
    try:
        png = os.path.join(tmp, "p.png")
        pg.get_pixmap(dpi=dpi).save(png)
        r = subprocess.run(["tesseract", png, os.path.join(tmp, "o"), "-l", lang, "tsv"], capture_output=True, text=True)
        tsv = os.path.join(tmp, "o.tsv")
        if r.returncode != 0 or not os.path.exists(tsv):
            raise RuntimeError(f"tesseract failed (rc {r.returncode}, lang {lang}): {r.stderr.strip()[:300]}")
        with open(tsv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    L = {}
    for r in rows:
        if r["level"] == "5" and (r["text"] or "").strip():
            L.setdefault((r["block_num"], r["par_num"], r["line_num"]), []).append(r)
    out = []
    for ws in L.values():
        x0 = min(int(w["left"]) for w in ws); x1 = max(int(w["left"]) + int(w["width"]) for w in ws)
        top = sorted(int(w["top"]) for w in ws)[len(ws) // 2] * k
        out.append((top, m.Rect(x0 * k, top, x1 * k, top + 14)))
    return out


def main(pdf, mj):
    d = m.open(pdf); marks = json.load(open(mj, encoding="utf-8-sig")); total = 0; failed = []
    placed = []  # (page, highlights, mark)
    for i, mk in enumerate(marks):
        if not 1 <= mk["page"] <= len(d):
            failed.append((i, mk["page"], "page out of range")); continue
        pg = d[mk["page"] - 1]; n = 0
        if mk["mode"] == "lines":
            for b in pg.get_text("dict")["blocks"]:
                for l in b.get("lines", []):
                    t = "".join(s["text"] for s in l["spans"]).strip()
                    if t and mk["y0"] <= l["bbox"][1] <= mk["y1"]:
                        add(pg, m.Rect(l["bbox"])); n += 1
        elif mk["mode"] == "rect":
            for r in mk["rects"]:
                add(pg, m.Rect(r)); n += 1
        elif mk["mode"] == "ocr":
            for top, r in ocr_lines(pg, ocr_lang(mk.get("lang"))):
                if mk["y0"] <= top <= mk["y1"]:
                    add(pg, r); n += 1
        else:
            failed.append((i, mk["page"], f"unknown mode {mk['mode']!r}")); continue
        if n == 0:
            failed.append((i, mk["page"], f"0 highlights in mode {mk['mode']}"))
        else:
            placed.append((mk["page"], n, mk))
        total += n
    if failed:
        print("FAIL (PDF not changed):", failed, file=sys.stderr)
        return 1
    clean_pdf(d); tmpout = pdf + ".tmp"; d.save(tmpout, garbage=3, deflate=True); d.close(); os.replace(tmpout, pdf)
    print("highlights added:", total)
    n_map = update_map(pdf, placed)
    if n_map is not None:
        print("map.json marks updated:", n_map)
    return 0


def unplaced(rec):
    st = str(rec.get("status", ""))
    return "NOT FOUND" in st.upper() or ("hits" in rec and not rec["hits"] and st != "page not included")


def update_map(pdf, placed):
    """Mark the pkg3 records this run fixed as placed in <pdf>.map.json. -> records updated, None when no map."""
    mpath = pdf + ".map.json"
    if not os.path.exists(mpath):
        return None
    try:
        mp = json.load(open(mpath, encoding="utf-8-sig"))
    except Exception as e:
        print("WARNING: map.json not updated:", e, file=sys.stderr); return None
    n = 0
    for page, hits, mk in placed:
        for rec in mp.get("marks", []) or []:
            if rec.get("pdf_page") != page or not unplaced(rec):
                continue
            if mk.get("label") and rec.get("label") != mk["label"]:
                continue
            if mk.get("text") and rec.get("text") != mk["text"]:
                continue
            rec["status"] = "highlighted (highlight.py)"; rec["hits"] = hits; n += 1
    tmp = mpath + ".tmp"
    json.dump(mp, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, mpath)
    return n


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    try:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    except RuntimeError as e:
        print("FAIL:", e, file=sys.stderr); sys.exit(1)
