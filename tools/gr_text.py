#!/usr/bin/env python3
"""Search / show the page-wise text cache of the repo's service-related PDFs (text/, built by tools/build_text_cache.py).

Use this instead of OCR-ing a GR or opening its page images: every cached page is either the PDF's own text layer
(where it is not garbled) or tesseract OCR (mar+eng, 200 dpi). Quote a GR in a note only after checking the page
image of the cited page (OCR can misread a digit or a matra) — the cache is for finding the page.

Commands:
  python3 tools/gr_text.py grep <regex> [--path-glob G] [-i] [--source ocr|textlayer] [--max N]
      -> one line per hit: "<pdf path> p<N>: <line text>"  (regex is Python `re`, matched line by line; the pattern
         and the text are both NFC-normalised; G is an fnmatch glob on the pdf path, e.g. 'pdf/gr/*')
  python3 tools/gr_text.py show <pdf> <page>
      -> the cached text of that page, after its header line "=== पृ. N (textlayer|ocr|pending) ===".
         <pdf> = repo path (pdf/gr/201612021708269510.pdf), the path without "pdf/", or a bare file stem / GR code.
  python3 tools/gr_text.py status
      -> totals from text/INDEX.tsv (PDFs, pages, textlayer / ocr / reused / pending, PDFs not yet done).

Cache layout: text/<pdf path relative to pdf/ with .pdf -> .txt>; each page starts with
  === पृ. N (textlayer|ocr) ===      (a page not yet OCR-ed: "(pending)", empty body).
Directory override (tests): --text-dir DIR or env GR_TEXT_DIR.
"""
import argparse, csv, fnmatch, glob, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDR = re.compile(r"^=== पृ\. (\d+) \((textlayer|ocr|pending)\) ===$", re.M)


def text_dir(arg=None):
    return arg or os.environ.get("GR_TEXT_DIR") or os.path.join(ROOT, "text")


def pdf_of(txt, tdir):
    rel = os.path.relpath(txt, tdir)
    return "pdf/" + os.path.splitext(rel)[0] + ".pdf"


def pages(txt):
    """-> [(page, source, text)] of one cache file."""
    s = open(txt, encoding="utf-8").read()
    ms = list(HDR.finditer(s))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(s)
        out.append((int(m.group(1)), m.group(2), s[m.end():end].strip("\n")))
    return out


def files(tdir):
    return sorted(f for f in glob.glob(os.path.join(tdir, "**", "*.txt"), recursive=True))


def grep(pattern, tdir, path_glob=None, icase=False, source=None, limit=0, out=sys.stdout):
    rx = re.compile(unicodedata.normalize("NFC", pattern), re.I if icase else 0)
    n = 0
    for f in files(tdir):
        pdf = pdf_of(f, tdir)
        if path_glob and not fnmatch.fnmatch(pdf, path_glob):
            continue
        for k, src, t in pages(f):
            if source and src != source:
                continue
            for line in t.splitlines():
                if rx.search(line):
                    out.write("%s p%d: %s\n" % (pdf, k, line.strip()))
                    n += 1
                    if limit and n >= limit:
                        return n
    return n


def find_txt(pdf, tdir):
    p = pdf[4:] if pdf.startswith("pdf/") else pdf
    cand = os.path.join(tdir, os.path.splitext(p)[0] + ".txt")
    if os.path.isfile(cand):
        return cand
    stem = os.path.splitext(os.path.basename(p))[0]
    hits = [f for f in files(tdir) if os.path.splitext(os.path.basename(f))[0] == stem]
    return hits[0] if len(hits) == 1 else None


def show(pdf, page, tdir, out=sys.stdout):
    f = find_txt(pdf, tdir)
    if not f:
        sys.stderr.write("not in the cache: %s\n" % pdf); return 1
    for k, src, t in pages(f):
        if k == page:
            out.write("=== %s पृ. %d (%s) ===\n%s\n" % (pdf_of(f, tdir), k, src, t)); return 0
    sys.stderr.write("page %d not in %s\n" % (page, f)); return 1


def status(tdir, out=sys.stdout):
    p = os.path.join(tdir, "INDEX.tsv")
    if not os.path.exists(p):
        sys.stderr.write("no INDEX.tsv in %s\n" % tdir); return 1
    rows = list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))
    tot = {c: sum(int(r.get(c) or 0) for r in rows) for c in ("pages", "textlayer", "ocr", "reused", "pending")}
    out.write("PDFs %d, pages %d: textlayer %d, ocr %d (reused %d), pending %d; PDFs not done %d\n" % (
        len(rows), tot["pages"], tot["textlayer"], tot["ocr"], tot["reused"], tot["pending"],
        sum(r.get("status") != "done" for r in rows)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text-dir")
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("grep"); g.add_argument("regex"); g.add_argument("--path-glob"); g.add_argument("-i", action="store_true")
    g.add_argument("--source", choices=["ocr", "textlayer"]); g.add_argument("--max", type=int, default=0)
    s = sp.add_parser("show"); s.add_argument("pdf"); s.add_argument("page", type=int)
    sp.add_parser("status")
    a = ap.parse_args(argv)
    td = text_dir(a.text_dir)
    if a.cmd == "grep":
        return 0 if grep(a.regex, td, a.path_glob, a.i, a.source, a.max) else 1
    if a.cmd == "show":
        return show(a.pdf, a.page, td)
    return status(td)


if __name__ == "__main__":
    sys.exit(main())
