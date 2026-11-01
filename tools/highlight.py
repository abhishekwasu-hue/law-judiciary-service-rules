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
Render the page afterwards and LOOK: highlight only the quoted lines."""
import sys, json, os, csv, subprocess, tempfile, shutil
import pymupdf as m


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
        total += n
    if failed:
        print("FAIL (PDF not changed):", failed, file=sys.stderr)
        return 1
    tmpout = pdf + ".tmp"; d.save(tmpout, garbage=3, deflate=True); d.close(); os.replace(tmpout, pdf)
    print("highlights added:", total)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    try:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    except RuntimeError as e:
        print("FAIL:", e, file=sys.stderr); sys.exit(1)
