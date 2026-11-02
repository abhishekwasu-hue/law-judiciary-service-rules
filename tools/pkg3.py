#!/usr/bin/env python3
"""pkg3.py <proposal.pdf> <enclosures.json> <out.pdf>
Proposal returned WITH its GRs (Abhi's standing rule, INSTRUCTIONS.md §4.7, §4.11, §4.13):
  - proposal scan first (unchanged), then only the selected ORIGINAL pages of each GR/rule/judgment
  - NO separator / title / index pages
  - every page stamped at the bottom: "पृ. N / एकूण" — the stamp is read back after writing; exit code 1 if any page lacks it.
    Enclosure pages: centred on a small white strip. Proposal pages: no fill/background (nothing hidden, §4.13) — the
    stamp is written in the first clear spot of the bottom 24 pt strip (centre, right, left)
  - PDF bookmarks (outline): proposal + each enclosure -> click jumps to its first page
  - marking: quoted text highlighted in yellow ONLY (search on the text layer). Never boxes. Pages whose text layer cannot be
    searched (scanned GR, legacy/garbled font, repeated strings): use tools/highlight.py on the finished package.
  - writes <out>.map.json : {label: {"first_page": N, "pages": [..]}, "marks": [one record per mark, with "hits"]}
    -> cite "(पॅकेज PDF पृ. N)" in the note's संबंधित माहिती

enclosures.json:
[ {"path": "pdf/xx/GR-2019.pdf", "pages": "1-3,7", "label": "वित्त विभाग GR दि. 01.03.2019",
   "marks": [ {"page": 2, "text": "exact words from the GR text layer"} ] } ]       # yellow highlight
"page" in marks = page number INSIDE the source PDF. "pages" must select at least one page; reversed ranges ("5-3"),
page 0 or pages beyond the source's length raise an error; so does a duplicate "label" (each label is one map.json key).
Each mark record in map.json: {label, src_page, pdf_page, text, hits, status}; status "highlighted" (hits >= 1),
"TEXT NOT FOUND" (hits 0 -> use highlight.py) or "page not included".
Needs: pip install pymupdf --break-system-packages. Stamp font: FreeSerif (runner) or a Windows Devanagari font (local).
"""
import sys, json, os
import pymupdf as fitz

FONTFILES = [
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "/usr/share/fonts/opentype/freefont/FreeSerif.otf",
    r"C:\Windows\Fonts\mangal.ttf",
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\Nirmala.ttf",
]
STAMP_SIZE = 10
STRIP = 24  # bottom strip height (points) in which the stamp is written and read back


def pages_of(spec, n, label=""):
    """'1-3,7' -> [1,2,3,7]; raises ValueError on an empty, reversed or out-of-range selection."""
    spec = str(spec).strip() if spec not in (None, "") else f"1-{n}"
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = (int(x) for x in part.split("-", 1))
            if a > b:
                raise ValueError(f"{label}: reversed page range '{part}'")
            rng = list(range(a, b + 1))
        else:
            rng = [int(part)]
        bad = [p for p in rng if not 1 <= p <= n]
        if bad:
            raise ValueError(f"{label}: page(s) {bad} outside 1-{n} in '{spec}'")
        out += rng
    if not out:
        raise ValueError(f"{label}: page spec '{spec}' selects no page")
    return out


def stamp_font():
    for f in FONTFILES:
        if os.path.exists(f):
            fo = fitz.Font(fontfile=f)
            if all(fo.has_glyph(ord(c)) for c in "पृ.0123456789/"):
                return f, fo
    raise RuntimeError("no Devanagari font for the page stamp (need FreeSerif or mangal/Nirmala): " + ", ".join(FONTFILES))


def stamp_text(i, tot):
    return f"पृ. {i} / {tot}"


def ink(pg, rect):
    """Share of non-white pixels of the page inside rect (rendered at 50 dpi, grey) — 0.0 = an empty margin."""
    try:
        pix = pg.get_pixmap(clip=rect, dpi=50, colorspace=fitz.csGRAY, alpha=False)
    except Exception:
        return 1.0
    px = pix.samples
    return sum(1 for b in px if b < 200) / len(px) if px else 1.0


def stamp_page(pg, i, tot, ff, fo, proposal=False):
    """Write 'पृ. i / tot' in the bottom strip. Enclosure pages: centred on a small white strip. Proposal scan pages
    (INSTRUCTIONS §4.13: unchanged): NO fill — the stamp goes to the first clear spot of the bottom strip (centre, right,
    left; least ink if none is clear), so a bottom-centre page no. / remark of the scan is never covered. Tokens are
    written separately so the text layer has plain spaces (many fonts map U+0020 and U+00A0 to one glyph and extract the
    space as NBSP)."""
    toks = stamp_text(i, tot).split(" ")
    sp = fo.text_length(" ", STAMP_SIZE)
    width = sum(fo.text_length(t, STAMP_SIZE) for t in toks) + sp * (len(toks) - 1)
    r = pg.rect
    x = r.width / 2 - width / 2; y = r.height - 10
    box = lambda x0: fitz.Rect(x0 - 6, r.height - STRIP + 2, x0 + width + 6, r.height - 4)
    if proposal:
        spots = [x, r.width - width - 24, 24]
        scores = [ink(pg, box(c)) for c in spots]
        x = next((c for c, s in zip(spots, scores) if s < 0.005), spots[scores.index(min(scores))])
    else:
        pg.draw_rect(box(x), color=None, fill=(1, 1, 1), overlay=True)
    for t in toks:
        pg.insert_text((x, y), t, fontsize=STAMP_SIZE, fontname="pkgstamp", fontfile=ff)
        x += fo.text_length(t, STAMP_SIZE) + sp


def read_stamp(pg):
    r = pg.rect
    t = pg.get_text("text", clip=fitz.Rect(0, r.height - STRIP, r.width, r.height))
    return " ".join(t.replace("\xa0", " ").split())


def main(prop, js, out):
    encs = json.load(open(js, encoding="utf-8-sig"))
    dst = fitz.open(); toc = []; mp = {}; report = []
    src = fitz.open(prop)
    dst.insert_pdf(src)
    toc.append([1, "प्रस्ताव", 1]); mp["प्रस्ताव"] = {"first_page": 1, "pages": list(range(1, len(src) + 1))}
    for e in encs:
        label = e.get("label") or e["path"]
        if label in mp or label == "marks":
            raise ValueError(f"duplicate enclosure label '{label}' (map.json keys must be unique; 'प्रस्ताव' and 'marks' "
                             "are reserved) — give each enclosure its own label")
        s = fitz.open(e["path"]); sel = pages_of(e.get("pages"), len(s), label)
        start = len(dst) + 1; where = {}
        for p in sel:
            dst.insert_pdf(s, from_page=p - 1, to_page=p - 1); where[p] = len(dst)
        toc.append([1, label, start]); mp[label] = {"first_page": start, "pages": [where[p] for p in sel]}
        for m in e.get("marks", []):
            if m.get("box"):
                raise ValueError(f"{label}: 'box' marks are not allowed (INSTRUCTIONS §4.13) — use tools/highlight.py")
            sp = m.get("page")
            rec = {"label": label, "src_page": sp, "text": m.get("text", "")}
            if sp not in where:
                report.append({**rec, "pdf_page": None, "hits": 0, "status": "page not included"}); continue
            pg = dst[where[sp] - 1]
            hits = pg.search_for(m["text"]) if m.get("text") else []
            if hits:
                a = pg.add_highlight_annot(hits); a.set_colors(stroke=(1, 1, 0)); a.update()
            report.append({**rec, "pdf_page": where[sp], "hits": len(hits),
                           "status": "highlighted" if hits else "TEXT NOT FOUND"})
    tot = len(dst)
    ff, fo = stamp_font()
    nprop = len(mp["प्रस्ताव"]["pages"])
    for i, pg in enumerate(dst, 1):
        stamp_page(pg, i, tot, ff, fo, proposal=i <= nprop)
    missing = [i for i, pg in enumerate(dst, 1) if stamp_text(i, tot) not in read_stamp(pg)]
    dst.set_toc(toc); dst.save(out, garbage=3, deflate=True)
    mp["marks"] = report
    json.dump(mp, open(out + ".map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out, tot, "pages;", sum(1 for r in report if r["status"] == "highlighted"), "marks highlighted;",
          [r for r in report if r["status"] != "highlighted"])
    if missing:
        print("FAIL: page stamp not readable on pages", missing, "font", ff, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:4]))
