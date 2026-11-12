#!/usr/bin/env python3
"""Build / resume the page-wise text cache of the repo's service-related PDFs (text/).

Why: later sessions grep cached text (tools/gr_text.py) instead of OCR-ing or opening page images.

Scope (rescanned on every run, so new PDFs are picked up):
  * rows of docs/GR_INVENTORY.tsv with service_related == "होय";
  * every pdf/gr/*.pdf listed in pdf/gr/INDEX.tsv (column `code`);
  * every pdf/judgments-service/**/*.pdf.
Order: PDFs cited in docs/gr_study/*.md and pdf/gr first (most used), then judgments, then the rest.

Output:
  text/<pdf path relative to pdf/, .pdf -> .txt>, one file per PDF; every page starts with a line
      === पृ. N (textlayer|ocr) ===
  (a page still waiting for OCR is written `=== पृ. N (pending) ===` with an empty body);
  text/INDEX.tsv: path, pages, textlayer, ocr, reused, pending, status (done/partial), pdf_bytes, avg_score.
  The .txt files are the resume state: a later run keeps every textlayer / ocr page already written (as long as the
  PDF's byte size and page count are unchanged) and only OCRs the pending ones.

Text source per page — quality score of the PDF text layer (`score()`, 0..1, higher = better):
  * letters = Devanagari letters + ASCII letters on the page;
  * bad = 5 x broken Devanagari sequences (two dependent vowel signs in a row, virama + vowel sign, a vowel sign at a
    word start — the usual legacy-font / wrong-order symptoms; same pattern as tools/extract_check.py)
        + characters of legacy-font mappings (Latin-1 Supplement / Latin Extended U+00C0-U+024F, private use
        U+E000-U+F8FF, U+FFFD, control characters)
        + 3 x ASCII "words" carrying Kruti-Dev style symbols inside the word (; ' [ ] { } ~ ` | \\ ^ +)
          when the page has no Devanagari at all;
  * score = 1 - bad / letters (clamped to 0..1); a page with fewer than 40 letters scores 0 (scanned page / image).
  * MARK = the Unicode-but-wrong-glyph garbling of Maharashtra GR text layers ("ननणणय" for निर्णय, "नवभाग" for
    विभाग, "तया"/"मधये" for त्या/मध्ये, "ाां", "ूं", "ऄ" …) — also 5 x each in `bad`.
  Text layer used when `accept()`: score >= GOOD (0.97) and, on a page with >= 20 Devanagari letters, no MARK at all
  and a ि share of 0.02-0.06 (tesseract range); otherwise the page is OCR-ed. Measured 12.11.2026 on 12,497 pages:
  most Marathi text layers of the GR PDFs are garbled in this way, so Marathi pages are mostly OCR-ed while English
  text layers (rules, judgments) are used as they are.
OCR: pdftoppm -r 200 -gray of that one page, then `tesseract img - -l mar+eng --psm 6`, run under nice -n 15 with
  OMP_THREAD_LIMIT=1, one tesseract at a time.
Reuse: page OCR text left by earlier study agents under /tmp is taken first, only where the (pdf, page) mapping is
  certain (`reuse_map()`): the directory is tied to the PDF by the agent's own script list (A-pay, C2, D2) or by the
  exact PDF file name (D1), the file name carries the page number of a full / per-page render, and the number of page
  files equals the PDF's page count (or the agent marked the directory DONE).

Usage:
  python3 tools/build_text_cache.py                 # text layer pass + OCR of all pending pages (resumable)
  python3 tools/build_text_cache.py --no-ocr        # text layer + reuse only (fast), pending pages left
  python3 tools/build_text_cache.py --max-minutes 60
  python3 tools/build_text_cache.py --survey        # print per-PDF scores, write nothing
  python3 tools/build_text_cache.py --only 'pdf/gr/*'
Run it as a low-priority background job (one tesseract at a time):
  OMP_THREAD_LIMIT=1 nohup nice -n 15 python3 tools/build_text_cache.py > /tmp/text_cache.log 2>&1 &
Only one run at a time (text/.lock). Progress: python3 tools/gr_text.py status.
"""
import argparse, csv, glob, os, re, subprocess, sys, tempfile, time, unicodedata, warnings

warnings.filterwarnings("ignore")
import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "text")
GOOD, MIN_LETTERS = 0.97, 40
HDR = re.compile(r"^=== पृ\. (\d+) \((textlayer|ocr|pending)\) ===$", re.M)
SIGN = "ा-ौॢॣ"
INVALID = re.compile("[" + SIGN + "][" + SIGN + "]|्[" + SIGN + "]|" + r"(?:^|\s)[" + SIGN + "]")
DEVL = re.compile(r"[ऄ-ह क़-ॡ ॲ-ॿ]".replace(" ", ""))
SUSP = re.compile("[À-ɏ-�\x00-\x08\x0b\x0c\x0e-\x1f]")
KRUTI = re.compile(r"[A-Za-z][;'\[\]{}~`|\\^+][A-Za-z]")
# Unicode-but-wrong-glyph garbling seen in Maharashtra GR text layers (ि -> न/व, lost half forms, ा doubled, अ -> ऄ):
# e.g. "ननणणय" (निर्णय), "नवभाग"/"ववभाग" (विभाग), "वदनाांक" (दिनांक), "तया"/"मधये" (त्या/मध्ये), "याूंनी" (यांनी).
MARK = re.compile(r"ऄ|ूं|ाां|ष्ट्[ठय]|(?:^|\s)(?:वव|नन)|णण|मधय|(?:^|\s)तया|णया|लया(?:\s|$)|महणून"
                  r"|(?:^|\s)व(?:दनां|नर्ण)|अ[वद]धकार|नवभाग|ववभाग")


def stats(text):
    """-> (score, devanagari letters, garble markers, share of ि among Devanagari letters)."""
    t = unicodedata.normalize("NFC", text or "")
    dev = len(DEVL.findall(t))
    return score(t), dev, len(MARK.findall(t)), (t.count("ि") / dev if dev else 0.0)


def accept(text):
    """True when the text layer is used: score >= GOOD and, on a page with >= 20 Devanagari letters, no garble marker
    and (pages with > 300 Devanagari letters) a ि share inside 0.02-0.06 (range of tesseract output on 497 OCR pages:
    p5 0.022, p95 0.057; the ि -> न garbling drops it near 0, the ष -> ि garbling pushes it above 0.07)."""
    s, dev, m, ir = stats(text)
    if s < GOOD: return False
    if dev < 20: return True
    return m == 0 and (dev <= 300 or 0.02 <= ir <= 0.06)


def score(text):
    t = unicodedata.normalize("NFC", text or "")
    dev = len(DEVL.findall(t))
    letters = dev + sum(c.isascii() and c.isalpha() for c in t)
    if letters < MIN_LETTERS:
        return 0.0
    bad = 5 * (len(INVALID.findall(t)) + len(MARK.findall(t))) + len(SUSP.findall(t))
    if dev == 0:
        bad += 3 * sum(1 for w in t.split() if KRUTI.search(w))
    return max(0.0, min(1.0, 1 - bad / letters))


def rel_out(pdf):
    r = os.path.relpath(pdf, "pdf") if pdf.startswith("pdf/") else pdf
    return os.path.join(OUT, os.path.splitext(r)[0] + ".txt")


def scope():
    os.chdir(ROOT)
    paths = []
    with open("docs/GR_INVENTORY.tsv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r.get("service_related") == "होय":
                paths.append(r["path"])
    if os.path.exists("pdf/gr/INDEX.tsv"):
        with open("pdf/gr/INDEX.tsv", encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                c = (r.get("code") or "").strip()
                if c:
                    paths.append("pdf/gr/%s.pdf" % c)
    paths += sorted(glob.glob("pdf/judgments-service/**/*.pdf", recursive=True))
    seen, out = set(), []
    for p in paths:
        if p not in seen and os.path.isfile(p):
            seen.add(p); out.append(p)
    cited = set()
    for md in glob.glob("docs/gr_study/*.md"):
        s = open(md, encoding="utf-8", errors="ignore").read()
        cited |= set(re.findall(r"pdf/[^\s`|)\]\"']+?\.pdf", s))
        cited |= {"code:" + c for c in re.findall(r"\b(\d{18,20})\b", s)}
    def rank(p):
        b = os.path.splitext(os.path.basename(p))[0]
        if p in cited or "code:" + b in cited: return 0
        if p.startswith("pdf/gr/"): return 1
        if p.startswith("pdf/judgments-service/"): return 2
        return 3
    return sorted(out, key=lambda p: (rank(p), p)), rank


def npages(pdf):
    try:
        with fitz.open(pdf) as d: return len(d)
    except Exception:
        return 0


def reuse_map():
    """-> {(pdf, page): ocr text file} for directories whose mapping is certain."""
    m, T = {}, "/tmp"
    def add(pdf, d, rx, done_ok):
        if not os.path.isfile(pdf): return
        n = npages(pdf)
        files = {}
        for f in os.listdir(d):
            x = re.fullmatch(rx, f)
            if x and os.path.getsize(os.path.join(d, f)) > 0:
                files[int(x.group(1))] = os.path.join(d, f)
        if not files or max(files) > n: return
        if len(files) != n and not (done_ok and os.path.exists(os.path.join(d, "DONE"))): return
        for k, f in files.items(): m[(pdf, k)] = f
    lst = T + "/gri/study/A_pay_da_allow.tsv"
    if os.path.exists(lst):
        rows = [l.split("\t")[0] for l in open(lst, encoding="utf-8").read().splitlines()]
        for d in glob.glob(T + "/A-pay/ocr/*"):
            i = os.path.basename(d)
            if i.isdigit() and 0 < int(i) <= len(rows):
                add(rows[int(i) - 1], d, r"p-0*(\d+)\.txt", False)
    lst = T + "/C2-service-conditions/list.tsv"
    if os.path.exists(lst):
        idx = dict(l.split("\t")[:2] for l in open(lst, encoding="utf-8").read().splitlines() if "\t" in l)
        for d in glob.glob(T + "/C2-service-conditions/ocr/*"):
            p = idx.get(os.path.basename(d))
            if p: add(p, d, r"p(\d+)\.txt", True)
    lst = T + "/D2/scripts/list.txt"
    if os.path.exists(lst):
        idx = {l.split()[1]: l.split()[0] for l in open(lst, encoding="utf-8").read().splitlines() if len(l.split()) == 2}
        for d in glob.glob(T + "/D2/ocr/*"):
            p = idx.get(os.path.basename(d))
            if p: add(p, d, r"p(\d+)\.txt", True)
    allpdf = {}
    for p in glob.glob("pdf/**/*.pdf", recursive=True):
        allpdf.setdefault(os.path.splitext(os.path.basename(p))[0], []).append(p)
    for d in glob.glob(T + "/D1/ocr/*"):
        hits = allpdf.get(os.path.basename(d), [])
        if len(hits) == 1: add(hits[0], d, r"p-0*(\d+)\.png\.ocr\.txt", False)
    return m


def clean(t):
    t = unicodedata.normalize("NFC", t or "").replace("\r", "")
    t = HDR.sub(lambda x: x.group(0).replace("===", "= = ="), t)  # never let page text fake a header
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def read_cache(path):
    """-> {page: (source, text)}"""
    if not os.path.exists(path): return {}
    s = open(path, encoding="utf-8").read()
    ms = list(HDR.finditer(s)); out = {}
    for i, x in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(s)
        out[int(x.group(1))] = (x.group(2), s[x.end():end].strip("\n"))
    return out


def write_cache(path, pages):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for k in sorted(pages):
            src, t = pages[k]
            f.write("=== पृ. %d (%s) ===\n%s\n" % (k, src, t + "\n" if t else ""))
    os.replace(tmp, path)


def load_index():
    p = os.path.join(OUT, "INDEX.tsv")
    if not os.path.exists(p): return {}
    with open(p, encoding="utf-8") as f:
        return {r["path"]: r for r in csv.DictReader(f, delimiter="\t")}


FIELDS = ["path", "pages", "textlayer", "ocr", "reused", "pending", "status", "pdf_bytes", "avg_score"]


def save_index(idx):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, "INDEX.tsv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for k in sorted(idx): w.writerow({c: idx[k].get(c, "") for c in FIELDS})
    os.replace(tmp, os.path.join(OUT, "INDEX.tsv"))


def textlayer_pass(pdf, reuse, old_row):
    """Fill text-layer pages and reused OCR pages; returns (pages dict, avg score)."""
    out = rel_out(pdf)
    size = str(os.path.getsize(pdf))
    pages = read_cache(out)
    with fitz.open(pdf) as d:
        n = len(d)
        if old_row and (old_row.get("pdf_bytes") != size or old_row.get("pages") != str(n)):
            pages = {}
        pages = {k: v for k, v in pages.items() if 1 <= k <= n}
        scores = []
        for i in range(n):
            k = i + 1
            if k in pages and pages[k][0] != "pending":
                continue
            try:
                t = d[i].get_text("text")
            except Exception:
                t = ""
            s = score(t); scores.append(s)
            if accept(t):
                pages[k] = ("textlayer", clean(t))
            elif (pdf, k) in reuse:
                pages[k] = ("ocr", clean(open(reuse[(pdf, k)], encoding="utf-8", errors="ignore").read()))
            else:
                pages[k] = ("pending", "")
    write_cache(out, pages)
    return pages, n, (sum(scores) / len(scores) if scores else None)


REUSE_MAP = {}  # filled by main(): {(pdf, page): file} of reusable OCR pages


def row_for(pdf, pages, n, avg, old):
    c = {"textlayer": 0, "ocr": 0, "pending": 0}
    for s, _ in pages.values(): c[s] += 1
    r = sum(1 for k, (s, _) in pages.items() if s == "ocr" and (pdf, k) in REUSE_MAP)
    return {"path": pdf, "pages": n, "textlayer": c["textlayer"], "ocr": c["ocr"],
            "reused": r, "pending": c["pending"],
            "status": "done" if c["pending"] == 0 else ("partial" if c["textlayer"] + c["ocr"] else "pending"),
            "pdf_bytes": os.path.getsize(pdf),
            "avg_score": ("%.3f" % avg) if avg is not None else (old or {}).get("avg_score", "")}


def ocr_page(pdf, k, tmpdir):
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    base = os.path.join(tmpdir, "pg")
    for f in glob.glob(base + "*"): os.remove(f)
    subprocess.run(["nice", "-n", "15", "pdftoppm", "-r", "200", "-gray", "-png", "-f", str(k), "-l", str(k),
                    pdf, base], env=env, check=False, timeout=300, capture_output=True)
    imgs = glob.glob(base + "*.png")
    if not imgs: return None
    try:
        r = subprocess.run(["nice", "-n", "15", "tesseract", imgs[0], "-", "-l", "mar+eng", "--psm", "6"],
                           env=env, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        return None
    finally:
        for f in imgs: os.remove(f)
    return r.stdout.decode("utf-8", "ignore") if r.returncode == 0 else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--only", help="glob of pdf paths to process")
    a = ap.parse_args(argv)
    t0 = time.time()
    pdfs, rank = scope()
    full = set(pdfs)
    if a.only:
        import fnmatch
        pdfs = [p for p in pdfs if fnmatch.fnmatch(p, a.only)]
    if a.survey:
        for p in pdfs:
            with fitz.open(p) as d:
                tx = [pg.get_text("text") for pg in d]
            s = [score(x) for x in tx]
            good = sum(accept(x) for x in tx)
            print("%s\t%d\t%d\t%.3f" % (p, len(s), good, sum(s) / max(1, len(s))))
        return 0
    import fcntl
    os.makedirs(OUT, exist_ok=True)
    lock = open(os.path.join(OUT, ".lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another build_text_cache.py run holds text/.lock; stop it first"); return 1
    reuse = reuse_map()
    REUSE_MAP.update(reuse)
    idx = load_index()
    live = set()
    for p in pdfs:
        try:
            pages, n, avg = textlayer_pass(p, reuse, idx.get(p))
        except Exception as e:
            print("SKIP", p, e, file=sys.stderr); continue
        idx[p] = row_for(p, pages, n, avg, idx.get(p)); live.add(p)
    for k in list(idx):
        if k not in full: del idx[k]  # left the scope / file removed
    save_index(idx)
    print("text layer pass: %d PDFs, %.0f s" % (len(live), time.time() - t0), flush=True)
    if a.no_ocr: return 0
    with tempfile.TemporaryDirectory() as tmp:
        for p in sorted(live, key=lambda p: (rank(p), p)):
            if idx[p]["status"] == "done": continue
            out = rel_out(p); pages = read_cache(out)
            for k in sorted(k for k, v in pages.items() if v[0] == "pending"):
                if a.max_minutes and time.time() - t0 > a.max_minutes * 60:
                    save_index(idx); print("time limit reached"); return 0
                t = ocr_page(p, k, tmp)
                if t is None: continue
                pages[k] = ("ocr", clean(t))
                write_cache(out, pages)
                idx[p] = row_for(p, pages, idx[p]["pages"], None, idx[p])
            save_index(idx)
            print("ocr done", p, idx[p]["status"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
