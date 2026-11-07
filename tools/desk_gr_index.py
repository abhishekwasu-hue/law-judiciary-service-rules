"""desk_gr_index.py — JSON index of every PDF under pdf/ for the read-only "GR ग्रंथालय" tab.
Usage: python tools/desk_gr_index.py <out.json> [--root REPO_ROOT]

Each entry: key, path, folder, topic, file, code, date, title, pages, size, url.
Titles are never invented: INDEX.tsv title, else the first-page "विषय" text if it is real Unicode, else "".
URLs are official only (gr.maharashtra.gov.in for a GR code, else a *.gov.in / *.nic.in link from pdf-list*.tsv)."""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
from urllib.parse import urlparse

import pymupdf

GR_URL = "https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{}.pdf"
CODE_RE = re.compile(r"^(\d{16,20})(?![0-9A-Za-z])")   # not a hex hash like 1005…dd63…
GARBAGE_RE = re.compile(r"[\u0080-˿ -⁯-]{3,}")   # Latin-1/ext/modifier/punct/PUA runs
SUBJ_LABEL = re.compile(r"(?<![\u0900-\u097F])विषय\s*[:ः\-–—]+")   # the "विषय :-" label, not विषयक / विषयी
SUBJ_END = re.compile(r"(संदर्भ|प्रस्तावना|वाचा\s*[:-]|शासन\s+निर्णय\s*[:-])")


def parse_code(name):
    """(code, 'DD.MM.YYYY') from a file name starting with a 16-20 digit GR सांकेतांक; ('', '') otherwise."""
    m = CODE_RE.match(name)
    if not m:
        return "", ""
    code = m[1]
    try:
        d = datetime.date(int(code[:4]), int(code[4:6]), int(code[6:8]))
        date = d.strftime("%d.%m.%Y") if 1950 <= d.year <= 2100 else ""
    except ValueError:
        date = ""
    return code, date


def is_readable(text):
    """True only for real Unicode Devanagari/English text (no legacy-font garbage)."""
    if not text or GARBAGE_RE.search(text):
        return False
    letters = [c for c in text if c.isalpha() or "ऀ" <= c <= "ॿ"]
    if len(letters) < 3:
        return False
    good = sum(1 for c in letters if "ऀ" <= c <= "ॿ" or ("A" <= c <= "Z") or ("a" <= c <= "z"))
    bad = len(letters) - good
    return good / len(letters) >= 0.6 and bad < 5


def subject_from_text(text):
    """Text after the 'विषय :-' label (one line, <=200 chars) if readable, else ''."""
    m = SUBJ_LABEL.search(text)
    if not m:
        return ""
    s = " ".join(text[m.end():].split())
    s = s.lstrip(" :-–—.ः")
    m = SUBJ_END.search(s)
    if m and m.start() > 10:
        s = s[:m.start()]
    s = s[:200].strip(" ,.-–—")
    return s if is_readable(s) else ""


def official_url(url):
    host = (urlparse(url).hostname or "").lower()
    return url if host and (host.endswith(".gov.in") or host.endswith(".nic.in")
                            or host == "gr.maharashtra.gov.in") else ""


def folder_topic(root, folder, cache):
    if folder not in cache:
        topic = " ".join(re.sub(r"^\d+-", "", folder).replace("-", " ").split())
        md = os.path.join(root, "service-rules", folder + ".md")
        if folder and os.path.isfile(md):
            with open(md, encoding="utf-8-sig") as f:
                for line in f:
                    if line.startswith("# "):
                        topic = line[2:].strip() or topic
                        break
        cache[folder] = topic
    return cache[folder]


def load_index_titles(root):
    titles, p = {}, os.path.join(root, "pdf", "gr", "INDEX.tsv")
    if os.path.isfile(p):
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                code, t = (r.get("code") or "").strip(), " ".join((r.get("title") or "").split())
                if code and t and code not in titles and is_readable(t) \
                        and not re.fullmatch(r"Maharashtra GR: #\d+", t):
                    titles[code] = t
    return titles


def load_urls(root):
    """{(slug, filename): url} and {filename: url} from pdf-list.tsv / pdf-list-extra.tsv (official hosts only)."""
    by_pair, by_name = {}, {}
    for n in ("pdf-list.tsv", "pdf-list-extra.tsv"):
        p = os.path.join(root, n)
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8-sig") as f:
            for line in f:
                parts = line.rstrip("\r\n").split("\t")
                if len(parts) < 3:
                    continue
                slug, url, fn = parts[0].strip(), official_url(parts[1].strip()), parts[2].strip()
                if url:
                    by_pair.setdefault((slug, fn), url)
                    by_name.setdefault(fn, url)
    return by_pair, by_name


def pdf_info(path):
    """(page_count, first-page text); (0, '') if unreadable."""
    try:
        with pymupdf.open(path) as d:
            n = d.page_count
            return n, (d[0].get_text() if n else "")
    except Exception:
        return 0, ""


def build(root):
    pymupdf.TOOLS.mupdf_display_errors(False)
    pdf_root = os.path.join(root, "pdf")
    titles, (url_pair, url_name), topics = load_index_titles(root), load_urls(root), {}
    out = []
    for dp, dns, fns in os.walk(pdf_root):
        dns.sort()
        for fn in sorted(fns):
            if not fn.lower().endswith(".pdf"):
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            sub = os.path.relpath(full, pdf_root).replace(os.sep, "/").split("/")
            folder = sub[0] if len(sub) > 1 else ""
            code, date = parse_code(fn)
            pages, text = pdf_info(full)
            title = titles.get(code, "") if code else ""
            if not title:
                title = subject_from_text(text)
            url = GR_URL.format(code) if code else (url_pair.get((folder, fn)) or url_name.get(fn, ""))
            out.append({"key": hashlib.sha1(rel.encode("utf-8")).hexdigest()[:16], "path": rel,
                        "folder": folder, "topic": folder_topic(root, folder, topics), "file": fn,
                        "code": code, "date": date, "title": title, "pages": pages,
                        "size": os.path.getsize(full), "url": url})

    def ymd(e):
        return int(e["date"][6:] + e["date"][3:5] + e["date"][:2]) if e["date"] else 0
    out.sort(key=lambda e: e["file"])
    out.sort(key=ymd, reverse=True)
    out.sort(key=lambda e: e["folder"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    rows = build(os.path.abspath(a.root))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    print(f"total {len(rows)} | with code {sum(1 for r in rows if r['code'])} | "
          f"with title {sum(1 for r in rows if r['title'])} | with url {sum(1 for r in rows if r['url'])} -> {a.out}")


if __name__ == "__main__":
    sys.exit(main())
