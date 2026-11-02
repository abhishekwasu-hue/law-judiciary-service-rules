#!/usr/bin/env python3
"""extract_check.py <package.pdf> [--spec spec.json] [--study study.json] [--ocr-dir DIR] [--no-ocr] [--note-body]
                    [--extra PATH ...] [--json out.json] [--log-out log.json] [--from MODEL] [--to MODEL]
Verbatim guard (INSTRUCTIONS §1.1) for extracts written on the cheap tier: every quoted extract in the note's
`related` ("संबंधित माहिती") and in Study part 3 ("भाग 3 — लागू तरतुदी") must occur in the text of the package page
it cites ("(पॅकेज PDF पृ. N)", "N-M", "N,M").
- Unit = one `related` item / one Study part-3 block (para, each bullet, each table row). Extracts = the “…” segments
  of the unit; a `related` text element without “…” counts as a whole extract (when >= 40 characters). Omissions
  ("…", "...", "[…]") split an extract into fragments; each fragment of >= 12 characters is checked.
- Pages = those cited in the unit, else those cited in the unit's section (the related item / the part-3 subheading).
- Match = the fragment occurs in the cited pages' text layer (concatenated in order) after normalising: NFC,
  Devanagari digits -> ASCII, whitespace / zero-width / quote / hyphen-dash characters removed, "|" -> "।".
- Unreliable text layer -> OCR: scanned page (no text layer), legacy font (a Devanagari extract on a page with almost
  no Devanagari text) or GARBLED Unicode (broken ToUnicode map — most gr.maharashtra.gov.in PDFs: "ििाराष्ट्र" for
  "महाराष्ट्र"; detected by invalid sign sequences, > 2 per 1000 Devanagari characters). OCR text: `--ocr-dir`
  (prep_pages.py layout: p-NN.ocr.txt, page N of the package), else tesseract via tools/prep_pages.py when installed
  (unless --no-ocr); an --ocr-dir whose pages.json pdf_sha256 is not the package's own (an earlier build) is ignored.
  OCR is noisy, so it is compared word by word (a word matches when a page word is >= 75 %
  similar): >= 85 % of the words = ok_ocr; < 60 % on a page whose OCR has >= 40 Devanagari words = mismatch (wrong
  para / paraphrase); anything else, weak OCR, or no OCR at all = "unverifiable" (never a failure).
- "(पॅकेज PDF मध्ये नाही)" / no page cited: searched in the --extra sources (.pdf text, .txt/.md, .docx text;
  directories recursively) -> ok_extra or mismatch; without --extra -> unverifiable.
--note-body: also the note body's verbatim “…” quotes (spec note.first + note.paras; pages = the para's "पृ.N/प.वि."
  refs, which cite the returned package) — WARNING only (new check): printed as "WARN MISMATCH …" / "WARN
  UNVERIFIABLE …", records carry "warn_only": true, never counted in EXTRACTS FAIL / --log-out.
Prints one line per problem ("MISMATCH …", "UNVERIFIABLE …"), then "EXTRACTS OK (checked N, unverifiable K)"
(exit 0) or "EXTRACTS FAIL (M mismatch)" (exit 1). --json = every record. --log-out = status.json `model_log`
entries for the mismatched units ({"task": "उतारा: …", "from": --from, "to": --to, "reason": "…"}) — those units go
back to the drafter (one-way escalation; workflow prints them as "मॉडेल: …" lines)."""
import difflib, glob, json, os, re, sys, tempfile, unicodedata, zipfile

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
DROP = re.compile(r"[\s​‌‍﻿­\"'“”‘’„«»`\-‐‑‒–—―]+")
QUOTE = re.compile(r"“([^“”]+)”")
OMIT = re.compile(r"\[\s*(?:…|\.{3,})?\s*\]|\(\s*(?:…|\.{3,})\s*\)|…|\.{3,}")
CITE = re.compile(r"पॅकेज\s*PDF\s*पृ\.?\s*([0-9०-९][0-9०-९,\s\-–]*)")
NOT_IN = re.compile(r"पॅकेज\s*PDF\s*मध्ये\s*नाही")
DEVA = re.compile(r"[ऀ-ॿ]")
MIN_FRAG, MIN_WHOLE, OCR_OK, OCR_BAD, OCR_WORDS = 12, 40, 0.85, 0.60, 40
SIGN = "ा-ौॢॣ"  # dependent vowel signs
INVALID = re.compile("[" + SIGN + "][" + SIGN + "]|्[" + SIGN + "]|" + r"(?:^|\s)[" + SIGN + "]")
WORD = re.compile(r"[ऀ-ॣ०-ॿ\w]+")


def norm(s):
    s = unicodedata.normalize("NFC", str(s or "")).translate(DEV_DIGITS).replace("|", "।")
    return DROP.sub("", s)


def pages_cited(text):
    """'(पॅकेज PDF पृ. 12-14)' -> [12, 13, 14]; Devanagari digits allowed."""
    out = []
    for m in CITE.finditer(str(text or "")):
        for part in m.group(1).translate(DEV_DIGITS).replace("–", "-").split(","):
            part = part.strip()
            if re.fullmatch(r"\d+\s*-\s*\d+", part):
                a, b = (int(x) for x in part.split("-"))
                out += list(range(a, b + 1)) if 0 < a <= b and b - a < 200 else []
            elif part.isdigit():
                out.append(int(part))
    return sorted(set(out))


def fragments(extract):
    """-> [(raw, normalised)] pieces between omission marks, normalised length >= MIN_FRAG."""
    return [(x, norm(x)) for x in OMIT.split(extract) if len(norm(x)) >= MIN_FRAG]


def garbled(text):
    dev = len(DEVA.findall(text))
    return dev > 0 and len(INVALID.findall(text)) * 1000 > 2 * dev


def words(text):
    t = unicodedata.normalize("NFC", str(text or "")).translate(DEV_DIGITS)
    return [w for w in WORD.findall(t) if len(w) >= 2]


def word_coverage(frag_raw, page_text):
    """Share of the extract's words that have a >= 75 % similar word on the page (OCR noise tolerant)."""
    fw, pw = words(frag_raw), words(page_text)
    if not fw: return 1.0
    pset = set(pw)
    hit = sum(1 for w in fw if w in pset or difflib.get_close_matches(w, pw, n=1, cutoff=0.75))
    return hit / len(fw)


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, (list, tuple)):
        for i in x: yield from strings(i)
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)


def units_related(spec):
    """-> [(where, [extracts], unit pages, section pages, not_in_package)] for spec['related']."""
    out = []
    for i, it in enumerate((spec or {}).get("related") or []):
        if not isinstance(it, dict): continue
        allt = " ".join(strings(it))
        ex = []
        texts = it.get("text") or []
        for t in ([texts] if isinstance(texts, str) else texts):
            if not isinstance(t, str): continue
            q = QUOTE.findall(t)
            if q: ex += q
            elif len(norm(CITE.sub("", t))) >= MIN_WHOLE: ex.append(CITE.sub("", t))
        pg = pages_cited(allt)
        where = f"related[{i + 1}] {str(it.get('heading') or '')[:60]}"
        out.append((where, ex, pg, pg, bool(NOT_IN.search(allt))))
    return out


NOTE_CITE = re.compile(r"पृ\.?\s*([0-9०-९][0-9०-९,\s\-–]*(?:\s*ते\s*[0-9०-९]+)?)\s*/\s*प\.\s*वि")


def note_pages(text):
    """'(पृ.24-25/प.वि.)', 'पृ. 5 ते 7 / प.वि.', 'पृ.5,7/प.वि.' -> package pages (the note body cites the returned PDF)."""
    out = []
    for m in NOTE_CITE.finditer(str(text or "")):
        out += pages_cited("पॅकेज PDF पृ. " + re.sub(r"\s*ते\s*", "-", m.group(1)))
    return sorted(set(out))


def units_note(spec):
    """Note body (spec note.first + note.paras): the verbatim “…” quotes of each para, pages = its पृ.N/प.वि. refs.
    WARNING-only units (new check, QUALITY_AUDIT §7): their mismatches never make EXTRACTS FAIL."""
    n = (spec or {}).get("note") or {}
    paras = [n.get("first")] + list(n.get("paras") or [])
    out = []
    for i, p in enumerate(paras):
        t = " ".join(strings(p)) if p is not None else ""
        q = QUOTE.findall(t)
        if q:
            pg = note_pages(t)
            out.append((f"नोंद परि. {i + 1}" if i else "नोंद परि. 1 (प्रारंभ)", q, pg, pg, False))
    return out


def units_part3(study):
    out = []
    for p in (study or {}).get("parts") or []:
        if not (isinstance(p, dict) and str(p.get("heading", "")).startswith("भाग 3")): continue
        sections, cur = [], {"name": "भाग 3", "units": []}
        sections.append(cur)
        for b in p.get("blocks") or []:
            if not isinstance(b, dict): continue
            if "subheading" in b:
                cur = {"name": str(b["subheading"])[:60], "units": []}; sections.append(cur)
                cur["units"].append(str(b["subheading"]))
            elif "para" in b: cur["units"].append(str(b["para"]))
            elif "bullets" in b: cur["units"] += [" ".join(strings(x)) for x in b["bullets"] or []]
            elif "table" in b: cur["units"] += [" ".join(strings(r)) for r in b["table"] or []]
        for s in sections:
            sp = pages_cited(" ".join(s["units"]))
            sn = any(NOT_IN.search(u) for u in s["units"])
            for u in s["units"]:
                q = QUOTE.findall(u)
                if q:
                    up = pages_cited(u)
                    out.append((f"भाग 3 > {s['name']}", q, up, sp, bool(NOT_IN.search(u)) or (not up and sn)))
    return out


def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""): h.update(b)
    return h.hexdigest()


def stale_ocr(ocr_dir, pdf):
    """True when <ocr_dir>/pages.json (prep_pages.py) names a pdf_sha256 other than the package's own: that OCR belongs
    to an earlier package build (page numbers may have moved). No pages.json / no sha -> not stale (older layout)."""
    try:
        with open(os.path.join(ocr_dir, "pages.json"), encoding="utf-8") as fh: want = json.load(fh).get("pdf_sha256")
    except Exception:
        return False
    return bool(want) and str(want).lower() != sha256_file(pdf)


class Pages:
    def __init__(self, pdf, ocr_dir=None, no_ocr=False):
        import pymupdf
        self.doc = pymupdf.open(pdf)
        self.n = len(self.doc)
        self.ocr_dir, self.no_ocr, self._ocr, self._tmp = ocr_dir, no_ocr, {}, None
        self.ocr_stale = False
        if ocr_dir and stale_ocr(ocr_dir, pdf):
            print(f"NOTE: --ocr-dir {ocr_dir} was made from another PDF (pages.json pdf_sha256 differs) — ignored",
                  file=sys.stderr)
            self.ocr_dir, self.ocr_stale = None, True

    def text(self, n):
        return self.doc[n - 1].get_text("text") or ""

    def usable(self, n, frag):
        t = norm(self.text(n))
        if len(t) < 50: return False
        if DEVA.search(frag) and len(DEVA.findall(t)) < 0.2 * len(re.findall(r"\w", t)): return False  # legacy font
        return not garbled(self.text(n))

    def ocr(self, n):
        if n in self._ocr: return self._ocr[n]
        txt = None
        if self.ocr_dir:
            for f in glob.glob(os.path.join(self.ocr_dir, "p-*.ocr.txt")):
                m = re.search(r"p-0*(\d+)\.ocr\.txt$", os.path.basename(f))
                if m and int(m.group(1)) == n:
                    with open(f, encoding="utf-8", errors="replace") as fh: txt = fh.read()
                    break
        if txt is None and not self.no_ocr:
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import prep_pages
                exe, lang = prep_pages.ocr_lang()
                if exe and lang:
                    self._tmp = self._tmp or tempfile.mkdtemp(prefix="xcheck_")
                    png, dst = os.path.join(self._tmp, f"p{n}.png"), os.path.join(self._tmp, f"p{n}.ocr.txt")
                    self.doc[n - 1].get_pixmap(dpi=200).save(png)
                    prep_pages.ocr_page(exe, lang, png, dst)
                    with open(dst, encoding="utf-8", errors="replace") as fh: txt = fh.read()
            except Exception:
                txt = None
        self._ocr[n] = txt
        return txt


def extra_text(paths):
    chunks = []
    def one(f):
        low = f.lower()
        try:
            if low.endswith(".pdf"):
                import pymupdf
                with pymupdf.open(f) as d: chunks.append(norm("".join(p.get_text("text") for p in d)))
            elif low.endswith((".txt", ".md", ".tsv")):
                with open(f, encoding="utf-8", errors="replace") as fh: chunks.append(norm(fh.read()))
            elif low.endswith(".docx"):
                with zipfile.ZipFile(f) as z: x = z.read("word/document.xml").decode("utf-8", "replace")
                chunks.append(norm("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", x))))
        except Exception:
            pass
    for p in paths or []:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                for f in sorted(fs): one(os.path.join(root, f))
        elif os.path.exists(p):
            one(p)
    return chunks


def check(pdf, spec=None, study=None, ocr_dir=None, no_ocr=False, extras=None, note_body=False):
    units = [u + (False,) for u in units_related(spec) + units_part3(study)]
    units += [u + (True,) for u in units_note(spec)] if note_body else []
    pages = Pages(pdf, ocr_dir, no_ocr)
    extra = None
    recs = []
    for where, exs, up, sp, notin, warn_only in units:
        pg = up or ([] if notin else sp)
        for ex in exs:
            for raw, fr in fragments(ex):
                rec = {"where": where, "pages": pg, "extract": fr[:120]}
                if warn_only: rec["warn_only"] = True
                if not pg:
                    if extras:
                        extra = extra if extra is not None else extra_text(extras)
                        ok = any(fr in c for c in extra)
                        rec.update(status="ok_extra" if ok else "mismatch",
                                   why="" if ok else "पॅकेजमध्ये नाही; दिलेल्या स्रोतांत सापडला नाही")
                    else:
                        rec.update(status="unverifiable", why="पॅकेज पान नमूद नाही / पॅकेजमध्ये नाही")
                    recs.append(rec); continue
                outside = [n for n in pg if not 1 <= n <= pages.n]
                if outside:
                    rec.update(status="mismatch", why=f"पॅकेजमध्ये पान नाही: {outside}"); recs.append(rec); continue
                if all(pages.usable(n, fr) for n in pg):
                    ok = fr in norm("".join(pages.text(n) for n in pg))
                    rec.update(status="ok" if ok else "mismatch", why="" if ok else "मजकूर-स्तराशी जुळला नाही")
                else:
                    o = [pages.ocr(n) for n in pg]
                    if all(x is None for x in o):
                        rec.update(status="unverifiable", why="स्कॅन/legacy-font/विस्कळीत मजकूर-स्तर, OCR उपलब्ध नाही")
                    else:
                        ocr = "\n".join(x or "" for x in o)
                        cov = 1.0 if fr in norm(ocr) else word_coverage(raw, ocr)
                        rec["ocr_coverage"] = round(cov, 2)
                        if cov >= OCR_OK:
                            rec.update(status="ok_ocr", why="")
                        elif cov < OCR_BAD and len([w for w in words(ocr) if DEVA.search(w)]) >= OCR_WORDS:
                            rec.update(status="mismatch", why=f"OCR शी जुळला नाही ({cov:.0%} शब्द)")
                        else:
                            rec.update(status="unverifiable", why=f"OCR कमकुवत / अंशतः जुळला ({cov:.0%} शब्द)")
                recs.append(rec)
    pages.doc.close()
    return recs


def model_log(recs, frm="", to=""):
    seen, out = set(), []
    for r in recs:
        if r["status"] == "mismatch" and not r.get("warn_only") and r["where"] not in seen:
            seen.add(r["where"])
            out.append({"task": f"उतारा: {r['where']}"[:120], "from": frm, "to": to,
                        "reason": "उतारा मूळ PDF शी जुळला नाही"})
    return out


def main(argv):
    a = list(argv)
    def opt(name, multi=False):
        vals = []
        while name in a:
            k = a.index(name); vals.append(a[k + 1] if k + 1 < len(a) else ""); del a[k:k + 2]
        return vals if multi else (vals[-1] if vals else None)
    no_ocr = "--no-ocr" in a
    if no_ocr: a.remove("--no-ocr")
    note_body = "--note-body" in a
    if note_body: a.remove("--note-body")
    spec_p, study_p, ocr_d, js, logp = (opt(x) for x in ("--spec", "--study", "--ocr-dir", "--json", "--log-out"))
    frm, to, extras = opt("--from") or "", opt("--to") or "", opt("--extra", True)
    if len(a) != 1 or not (spec_p or study_p):
        print(__doc__); return 2
    def load(p):
        if not p: return None
        with open(p, encoding="utf-8-sig") as fh: return json.load(fh)
    recs = check(a[0], load(spec_p), load(study_p), ocr_d, no_ocr, extras, note_body)
    for r in recs:
        if r["status"] in ("mismatch", "unverifiable"):
            pre = "WARN " if r.get("warn_only") else ""
            print(f"{pre}{r['status'].upper()} {r['where']} पृ.{r['pages']}: {r['extract'][:80]} — {r['why']}")
    for path, data in ((js, recs), (logp, model_log(recs, frm, to) if logp else None)):
        if path:
            with open(path, "w", encoding="utf-8") as fh: json.dump(data, fh, ensure_ascii=False, indent=1)
    bad = sum(r["status"] == "mismatch" and not r.get("warn_only") for r in recs)
    unv = sum(r["status"] == "unverifiable" and not r.get("warn_only") for r in recs)
    print(f"EXTRACTS FAIL ({bad} mismatch)" if bad else f"EXTRACTS OK (checked {len(recs)}, unverifiable {unv})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
