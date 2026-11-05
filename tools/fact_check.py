#!/usr/bin/env python3
"""fact_check.py <package.pdf> --spec spec.json [--ocr-dir DIR] [--no-ocr] [--json out.json] [--details FILE]
Fact-anchor check (audit 05.11.2026 Q-F1; INSTRUCTIONS §1.1, §4.27, §4.34(ई)): the dates, amounts, letter / file numbers
and person names written in the note's OWN text (note.first, note.paras incl. table cells, note.sub, note.closing) and in
the letter(s) must occur on the package page they cite. WARNING level only (§4.26): exit 0 unless the tool itself
cannot run (exit 2 = bad arguments / unreadable spec or PDF).
- Facts (outside “…” quotes; `related` = "संबंधित माहिती" is never read; the page refs themselves are masked):
  दिनांक  DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY (ASCII or Devanagari digits; "__.__.2026" skipped);
  रक्कम   "रु. 1,27,24,560/-", "₹ …", "Rs. …", "15,000/-", any Indian-grouped number "1,27,24,560";
  पत्र-क्र. a token with "/" and a digit ("बी/विवेतन-एनजीबी/1080/2026", "वेतन-1311/प्र.क्र.17/सेवा-3"; a leading
          "क्र." dropped) — NOT the Section's own letter ref_no(s), "पृ.N/प.वि.", dates, "…/-" amounts, "____";
  नाव     the surname after "श्री." / "श्रीमती" / "कै." (initials skipped; stops at a comma, bracket or "यां…" word).
- Cited pages: the "(पृ.N/प.वि.)" / "पृ.N-M/प.वि." / "पृ.3, 5, 7/प.वि." refs of the fact's sentence (mode "sentence");
  else the nearest earlier ref in the same para ("para"); a table row / sub-point without a ref uses the refs of the para
  just before it ("table" / "sub"); else (§4.34(ई): a page only at first mention; letters carry no refs) the proposal
  pages of <package>.map.json ("wide"; whole package without a map).
- Page text: the text layer when usable (tools/extract_check.py Pages.usable: not scanned / legacy font / garbled) PLUS
  the OCR (--ocr-dir = tools/pkg_ocr.py / prep_pages.py layout p-NN.ocr.txt, ignored when its pages.json pdf_sha256 is
  another PDF's; else tesseract via prep_pages for the CITED pages only, unless --no-ocr). A match in either = found.
  Wide / elsewhere searches never run tesseract (text layer + --ocr-dir only).
- Match (normalised: NFC, Devanagari digits -> ASCII, spaces / commas / hyphens): date = the same day, month, year
  (a 2-digit page year matches its last two digits; separators . / -); amount = the same value (commas, spaces, "/-",
  ".00" ignored); letter no. = the normalised token occurs, or every digit group of it occurs as a number on the page
  (OCR tolerant); name = the surname occurs, or (OCR) a page word >= 80 % similar. A Devanagari name on a page with
  < 30 % Devanagari words (an English page) = unverifiable.
- Status per fact: ok / elsewhere (not on the cited pages, found on page X) / mismatch (not found; also a cited page
  outside the package) / unverifiable (no usable text or OCR). Identical (kind, value, pages) facts are checked once.
stdout (audit S-F3): position, kind, pages and status only — never the fact text; the full lines with the value go to
--details FILE (or env CASE_DETAILS_FILE). Last line: "fact_check: N facts, ok A, mismatch B, unverifiable C
(elsewhere D, wide W)" — B counts elsewhere + mismatch. --json = every record (with the value; a runner-private file).
Engine: tools/engine_supabase.py `facts` (workflow step "Check extracts", on the runner's own OCR $RP/pkgpages)."""
import difflib, functools, json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_check as X  # noqa: E402  (norm, note_pages, Pages, stale_ocr, strings)

DEV = X.DEV_DIGITS
QUOTE_SPAN = re.compile(r"“[^“”]*”")
PAGE_REF = re.compile(r"\(?\s*पृ\.?\s*[0-9०-९ ,\-–ते]*\s*/\s*प\.\s*वि\.?\s*\)?")
NOTE_DATE = re.compile(r"(?<![0-9./-])([0-9]{1,2})([./-])([0-9]{1,2})\2((?:19|20)[0-9]{2})(?![0-9])")
PAGE_DATE = re.compile(r"(?<![0-9])([0-9]{1,2})\s*[./-]\s*([0-9]{1,2})\s*[./-]\s*((?:19|20)?[0-9]{2})(?![0-9])")
AMT_PRE = re.compile(r"(?:रु\.?|₹|Rs\.?)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")
AMT_SUF = re.compile(r"(?<![0-9.,/])([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*/-")
AMT_GRP = re.compile(r"(?<![0-9.,/])([0-9]{1,3}(?:,[0-9]{2})*,[0-9]{3}(?:\.[0-9]{1,2})?)(?![0-9,])")
TOKEN = re.compile(r"[^\s,;:\[\]“”\"']+/[^\s,;:\[\]“”\"']+")
LEAD = re.compile(r"^(?:क्रमांक|क्रं\.?|क्र\.?|नं\.?|No\.?)\s*")
NAME = re.compile(r"(?<![ऀ-ॿ])(श्रीमती|श्री\.|कै\.)\s*")
DWORD = re.compile(r"[ऀ-ॣ॥-ॿ]+\.?")
STOP = {"हे", "व", "आणि", "या", "ही", "हा", "तसेच", "रा.", "हयात", "यांजकडे"}
SENT_ABBR = {"क्र", "श्री", "परि", "प्र", "क्रं", "सं", "शा", "नि", "डॉ", "मा", "रु", "दि", "पृ", "वि", "प"}
LAT = re.compile(r"[A-Za-z]{2,}")
KIND_LABEL = {"date": "दिनांक", "amount": "रक्कम", "letter_no": "पत्र-क्र.", "name": "नाव"}


def dnum(s):
    return unicodedata.normalize("NFC", str(s or "")).translate(DEV)


def sentence_spans(t):
    """[(start, end)] of the sentences of t: a "." / "।" / "?" ending a word that is not an abbreviation (<= 2 code points,
    a word with an inner ".", or SENT_ABBR) and followed by white space or the end."""
    out, s = [], 0
    for m in re.finditer(r"[.।?](?=\s|$)", t):
        if t[m.start()] == ".":
            w = re.search(r"(\S*)$", t[:m.start()]).group(1)
            w = w.lstrip("(“\"'")
            if w.endswith((")", "”")) or re.fullmatch(r"[0-9०-९][0-9०-९.,/\-]*[0-9०-९]", w) and len(w) >= 3:
                pass   # "… (पृ.3/प.वि.)." / "…”." / "… दि. 25.03.2026." / "… 1,300." end a sentence
            elif len(w) <= 2 or "." in w or w in SENT_ABBR:
                continue
        out.append((s, m.end())); s = m.end()
    if s < len(t):
        out.append((s, len(t)))
    return out


def refs_in(t):
    """[(pos, [pages])] of the पृ.N/प.वि. refs in t (positions in t)."""
    return [(m.start(), X.note_pages(m.group(0))) for m in X.NOTE_CITE.finditer(t) if X.note_pages(m.group(0))]


def facts_in(t, skip_tokens=()):
    """Facts of one text (quotes and page refs already masked): [(pos, kind, value, key)]; key = normalised compare value."""
    d = str(t).translate(DEV)   # same length as t (positions shared)
    out, taken = [], []
    def free(a, b):
        return not any(a < y and x < b for x, y in taken)
    for m in NOTE_DATE.finditer(d):
        dd, mm, yy = int(m.group(1)), int(m.group(3)), int(m.group(4))
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            out.append((m.start(), "date", t[m.start():m.end()], (dd, mm, yy))); taken.append(m.span())
    for rx in (AMT_PRE, AMT_SUF, AMT_GRP):
        for m in rx.finditer(d):
            a, b = m.span(1)
            if not free(a, b): continue
            v = amount_value(m.group(1))
            if v:
                out.append((a, "amount", t[m.start():m.end()].strip(), v)); taken.append((a, b))
    for m in TOKEN.finditer(t):
        a, b = m.span()
        raw = unparen(m.group(0)).rstrip(".,;:-–")
        raw = re.sub(r"/-$", "", raw)
        tok = LEAD.sub("", raw.lstrip(".-–/"))
        if not re.search(r"[0-9०-९]", tok) or "__" in tok or "प.वि" in tok or not free(a, b) or raw.endswith("/-"):
            continue
        if m.group(0).endswith("/-") or re.fullmatch(r"[0-9०-९]{1,2}[./-][0-9०-९]{1,2}[./-][0-9०-९]{2,4}", tok):
            continue
        if X.norm(tok) in skip_tokens or any(X.norm(tok) in s for s in skip_tokens if len(X.norm(tok)) >= 8):
            continue
        if len(X.norm(tok)) < 3:
            continue
        out.append((a, "letter_no", tok, X.norm(tok))); taken.append((a, b))
    for m in NAME.finditer(t):
        rest = t[m.end():m.end() + 80]
        words, pos = [], 0
        for w in re.finditer(r"\S+", rest):
            x = w.group(0)
            core = re.match(r"[ऀ-ॣ॥-ॿ.]+", x)
            if not core or x.startswith(("यां", "ह्यां")) or x in STOP: break
            words.append(core.group(0))
            if core.group(0) != x: break   # comma / bracket glued to the word ends the name
        sur = [w for w in words if not w.endswith(".") and len(w) >= 3]
        if sur:
            out.append((m.start(), "name", sur[-1], X.norm(sur[-1])))
    return sorted(out)


def unparen(x):
    """Drop unbalanced outer brackets of a token: "(क्र.बी-4/36/2010)" -> "क्र.बी-4/36/2010"; "ब(जन)-1001/…" kept."""
    x = x.strip()
    while x.startswith("(") and x.count("(") > x.count(")"): x = x[1:]
    x = re.sub(r"[.,;:]+$", "", x)
    while x.endswith(")") and x.count(")") > x.count("("): x = re.sub(r"[.,;:]+$", "", x[:-1])
    if x.startswith("(") and x.endswith(")"): x = x[1:-1]
    return x


def amount_value(s):
    s = dnum(s).replace(",", "").strip()
    try:
        v = float(s)
    except ValueError:
        return None
    return int(v) if v >= 1 else None


@functools.lru_cache(maxsize=1024)
def page_numbers(text):
    """All numbers of a page text (commas / spaces next to commas dropped) -> set of ints."""
    d = re.sub(r"(?<=[0-9])\s*,\s*(?=[0-9])", "", dnum(text))
    out = set()
    for m in re.finditer(r"[0-9]+(?:\.[0-9]+)?", d):
        try: out.add(int(float(m.group(0))))
        except ValueError: pass
    return out


@functools.lru_cache(maxsize=1024)
def page_dates(text):
    out = set()
    for m in PAGE_DATE.finditer(dnum(text)):
        dd, mm, yy = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= dd <= 31 and 1 <= mm <= 12:
            out.add((dd, mm, int(yy) if len(yy) == 4 else -int(yy)))   # -yy = a 2-digit year
    return out


def found(kind, key, text, ocr=False):
    if not text: return False
    if kind == "date":
        ds = page_dates(text)
        return key in ds or (key[0], key[1], -(key[2] % 100)) in ds
    if kind == "amount":
        return key in page_numbers(text)
    if kind == "letter_no":
        if key in norm_c(text): return True
        runs = [int(x) for x in re.findall(r"[0-9]+", dnum(key))]
        return bool(runs) and all(r in page_numbers(text) for r in runs)
    if kind == "name":
        if key in norm_c(text): return True
        if ocr:
            pw = [w for w in X.words(text) if X.DEVA.search(w)]
            return bool(difflib.get_close_matches(key, pw, n=1, cutoff=0.8))
        return False
    return False


@functools.lru_cache(maxsize=1024)
def norm_c(text):
    return X.norm(text)


@functools.lru_cache(maxsize=1024)
def english_page(text):
    ws = X.words(text)
    if len(ws) < 20: return False
    dev = sum(1 for w in ws if X.DEVA.search(w))
    return dev < 0.3 * len(ws)


class Texts:
    """Package page texts: the usable text layer + OCR (cited pages may run tesseract; wide searches never do)."""
    def __init__(self, pdf, ocr_dir=None, no_ocr=False):
        self.p = X.Pages(pdf, ocr_dir, no_ocr)
        self.n = self.p.n
        self._cheap = {}

    def cheap_ocr(self, n):
        if n in self._cheap: return self._cheap[n]
        if self.p.ocr_dir:
            nb, self.p.no_ocr = self.p.no_ocr, True
            try: t = self.p.ocr(n)
            finally: self.p.no_ocr = nb
            self.p._ocr.pop(n, None) if t is None else None
        else:
            t = self.p._ocr.get(n)
        if t is not None:
            self._cheap[n] = t
        return t

    def sources(self, n, kind, value, allow_tess):
        """[(text, is_ocr)] of page n that can decide this fact."""
        out = []
        probe = value if kind == "name" else "0"
        if self.p.usable(n, probe):
            out.append((self.p.text(n), False))
        o = self.p.ocr(n) if allow_tess else self.cheap_ocr(n)
        if o:
            out.append((o, True))
        return out

    def close(self):
        self.p.doc.close()


def proposal_pages(mp, n):
    ents = X.doc_entries(mp)
    pp = sorted(set(p for _, pages, prop in ents if prop for p in pages))
    return [p for p in pp if 1 <= p <= n] or list(range(1, n + 1))


def units(spec):
    """-> [(where, text, context_refs)] of the note's and letters' own text. context_refs = the pages of the para just
    before a table / sub-point (§4.34(ई): the ref is in the sentence before the table)."""
    n = (spec or {}).get("note") or {}
    out = []
    paras = [n.get("first")] + list(n.get("paras") or [])
    prev_refs = []
    for i, p in enumerate(paras):
        where = f"टिप्पणी परि. {i + 1}"
        if isinstance(p, dict) and "table" in p:
            for r, row in enumerate(p.get("table") or []):
                if r == 0: continue   # header row
                out.append((f"{where} तक्ता ओळ {r}", " | ".join(X.strings(row)), prev_refs))
            continue
        t = " ".join(X.strings(p)) if p is not None else ""
        if not t.strip(): continue
        out.append((where, t, []))
        rr = [pg for _, pgs in refs_in(QUOTE_SPAN.sub(lambda m: " " * len(m.group(0)), t)) for pg in pgs]
        prev_refs = sorted(set(rr)) or prev_refs
        sub = (n.get("sub") or {})
        for key in (str(i - 1),) if i else ():
            for k, s in enumerate(sub.get(key) or [] if isinstance(sub, dict) else []):
                out.append((f"{where} उप-मुद्दा {k + 1}", " ".join(X.strings(s)), prev_refs))
    c = n.get("closing")
    if c:
        out.append(("टिप्पणी शेवटचा परि.", " ".join(X.strings(c)), []))
    letters = ([spec["letter"]] if isinstance(spec.get("letter"), dict) else []) + \
              [x for x in (spec.get("letters") or []) if isinstance(x, dict)]
    for j, L in enumerate(letters, 1):
        for f in ("subject", "refs", "intro", "points", "body", "closing"):
            if L.get(f):
                out.append((f"पत्र {j} {f}", " ".join(X.strings(L[f])), []))
    return out


def own_refs(spec):
    letters = ([spec.get("letter")] if isinstance(spec.get("letter"), dict) else []) + list(spec.get("letters") or [])
    return {X.norm(LEAD.sub("", str(L.get("ref_no")))) for L in letters if isinstance(L, dict) and L.get("ref_no")}


def collect(spec):
    """-> [{where, kind, value, key, pages, mode}] (pages before range checks)."""
    skip = own_refs(spec)
    out = []
    for where, t, ctx in units(spec):
        m = QUOTE_SPAN.sub(lambda q: " " * len(q.group(0)), t)
        refs = refs_in(m)
        m2 = PAGE_REF.sub(lambda q: " " * len(q.group(0)), m)
        spans = sentence_spans(m)
        for pos, kind, val, key in facts_in(m2, skip):
            sp = next(((a, b) for a, b in spans if a <= pos < b), (0, len(m)))
            pg = sorted(set(p for r, ps in refs if sp[0] <= r < sp[1] for p in ps))
            mode = "sentence"
            if not pg:
                earlier = [ps for r, ps in refs if r < pos]
                if earlier:
                    pg, mode = earlier[-1], "para"
                elif ctx:
                    pg, mode = list(ctx), ("table" if "तक्ता" in where else "sub")
                else:
                    mode = "wide"
            out.append({"where": where, "kind": kind, "value": val, "key": key, "pages": pg, "mode": mode})
    return out


def check(pdf, spec, ocr_dir=None, no_ocr=False):
    facts = collect(spec)
    tx = Texts(pdf, ocr_dir, no_ocr)
    try:
        with open(pdf + ".map.json", encoding="utf-8-sig") as fh: mp = json.load(fh)
    except Exception:
        mp = None
    prop = proposal_pages(mp, tx.n)
    recs, seen = [], {}
    try:
        for f in facts:
            key = (f["kind"], json.dumps(f["key"], ensure_ascii=False), tuple(f["pages"]), f["mode"])
            if key in seen:
                r = dict(seen[key]); r["where"] = f["where"]; r["dup"] = True; recs.append(r); continue
            r = {k: f[k] for k in ("where", "kind", "value", "pages", "mode")}
            r["key"] = f["key"] if not isinstance(f["key"], tuple) else list(f["key"])
            wide = f["mode"] == "wide"
            cited = prop if wide else f["pages"]
            outside = [p for p in cited if not 1 <= p <= tx.n]
            if outside:
                r.update(status="mismatch", why=f"पॅकेजमध्ये पान नाही: {outside}")
                recs.append(r); seen[key] = r; continue
            src, english, hit = 0, False, None
            for p in cited:
                for text, ocr in tx.sources(p, f["kind"], f["value"], not wide):
                    if f["kind"] == "name" and english_page(text):
                        english = True; continue
                    src += 1
                    if found(f["kind"], f["key"], text, ocr):
                        hit = p; break
                if hit: break
            if hit:
                r.update(status="ok", found_on=[hit], why="")
            elif src == 0:   # the cited page cannot be read: a hit elsewhere proves nothing (no false "elsewhere")
                r.update(status="unverifiable", why="इंग्रजी पान (नाव देवनागरीत)" if english else
                         "स्कॅन/legacy-font/विस्कळीत मजकूर-स्तर, OCR उपलब्ध नाही")
            else:
                other = []
                for p in range(1, tx.n + 1):
                    if p in cited: continue
                    if any(found(f["kind"], f["key"], t, o) for t, o in tx.sources(p, f["kind"], f["value"], False)
                           if not (f["kind"] == "name" and english_page(t))):
                        other.append(p)
                if other:
                    r.update(status="elsewhere", found_on=other[:5], why=f"नमूद पानावर नाही; पृ.{other[:5]} वर आढळले")
                else:
                    r.update(status="mismatch", why="नमूद पानावर आढळले नाही")
            recs.append(r); seen[key] = r
    finally:
        tx.close()
    return recs


def pages_label(pg):
    pg = sorted(set(pg or []))
    if not pg: return "पृ.-"
    if len(pg) > 1 and pg == list(range(pg[0], pg[-1] + 1)):
        return f"पृ.{pg[0]}-{pg[-1]}"
    return "पृ." + ",".join(str(p) for p in pg[:6]) + ("…" if len(pg) > 6 else "")


def summary(recs):
    ok = sum(r["status"] == "ok" for r in recs)
    bad = sum(r["status"] in ("mismatch", "elsewhere") for r in recs)
    unv = sum(r["status"] == "unverifiable" for r in recs)
    els = sum(r["status"] == "elsewhere" for r in recs)
    wide = sum(r["mode"] == "wide" for r in recs)
    return f"fact_check: {len(recs)} facts, ok {ok}, mismatch {bad}, unverifiable {unv} (elsewhere {els}, wide {wide})"


def main(argv):
    a = list(argv)
    import lint_spec   # audit S-F3: --details FILE / env CASE_DETAILS_FILE
    details = lint_spec.details_arg(a)
    def opt(name):
        v = None
        while name in a:
            k = a.index(name); v = a[k + 1] if k + 1 < len(a) else ""; del a[k:k + 2]
        return v
    no_ocr = "--no-ocr" in a
    if no_ocr: a.remove("--no-ocr")
    spec_p, ocr_d, js = opt("--spec"), opt("--ocr-dir"), opt("--json")
    if len(a) != 1 or not spec_p:
        print(__doc__); return 2
    try:
        with open(spec_p, encoding="utf-8-sig") as fh: spec = json.load(fh)
        recs = check(a[0], spec if isinstance(spec, dict) else {}, ocr_d, no_ocr)
    except Exception as e:
        print(f"fact_check: tool error ({e.__class__.__name__})", file=sys.stderr); return 2
    lines = []
    for r in recs:
        if r["status"] == "ok" or r.get("dup"): continue
        tag = {"mismatch": "WARN NOT FOUND", "elsewhere": "WARN ELSEWHERE", "unverifiable": "UNVERIFIABLE"}[r["status"]]
        tail = f" (पृ.{','.join(map(str, r['found_on']))} वर)" if r["status"] == "elsewhere" else ""
        wide = " [पान-संदर्भ नाही: प्रस्तावाची पाने]" if r["mode"] == "wide" else ""
        shown = f"{tag} {r['where']} {KIND_LABEL[r['kind']]} {pages_label(r['pages'])}{tail}{wide}"
        lines.append((shown, f"{shown}: {r['value']} — {r['why']}"))
    if details:
        try:
            with open(details, "a", encoding="utf-8") as fh:
                fh.write("== fact_check " + " ".join(argv) + "\n" + "".join(full + "\n" for _, full in lines))
        except OSError:
            print("details file not writable — output redacted only", file=sys.stderr)
    for shown, _ in lines:
        print(shown)
    if js:
        with open(js, "w", encoding="utf-8") as fh: json.dump(recs, fh, ensure_ascii=False, indent=1)
    print(summary(recs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
