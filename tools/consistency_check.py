#!/usr/bin/env python3
"""consistency_check.py <spec.json> [--study study.json] [--json OUT.json] [--details FILE]
Cross-document consistency (audit 05.11.2026 Q-F15; INSTRUCTIONS §4.30(2): dates, amounts, names, posts and numbers are
the same in the note, the letter(s), the order drafts, the parawise reply, the affidavit, the LQ answer and the Study
part 0 briefing). WARN only — the exit code is always 0 (a spec that cannot be read: exit 2).

Documents (spec keys; tools/mkdocs.py, build_order.py, build_parawise.py, build_affidavit.py, build_lq.py, build_study.py):
  टिप्पणी = note (first, sub, paras, closing; the related extracts only count as "present in the note");
  पत्र = letter / letters[i]; <type>-प्रारूप = order / orders[i]; परिच्छेदनिहाय उत्तर = parawise (English);
  शपथपत्र = affidavit (English); विधानमंडळ उत्तर = lq; अभ्यास भाग 0 = the "भाग 0" part of --study.
Skipped: the signer chain (note.signers, signer / designation keys), the documents' own ref_no / date / addressee lines,
  the U.O. block, "पृ.N/प.वि." and "पॅकेज PDF पृ. N" references, "____" blanks, and every “…” / "…" quote (verbatim
  sources keep their own wording); the related extracts are never a source of facts.
Facts: dates (DD.MM.YYYY, D/M/YYYY, D-M-YYYY, Devanagari digits; English "17th September 2026" / "September 17, 2026"),
  amounts (रु. / रुपये / Rs. / ₹ + a number, or an Indian / Western comma-grouped number), petition / case numbers
  (रिट याचिका / मूळ अर्ज / अवमान याचिका / विशेष अनुमती याचिका / अपील क्र. N/YYYY; W.P. / O.A. / C.P. / S.L.P. / Civil
  Appeal No. N of YYYY), C R numbers ("C R 131-2026"), person names (after श्री. / श्रीमती / श्रीम. / कै. / Shri / Smt.),
  posts (a table row with a name and a "पद" / "पदनाम" column).
Checks:
  (a) only_in   — a date / amount / C R no. of a draft or of the Study part 0 that is nowhere in the note (normalised);
  (b) name      — the same name spelled differently (spaces and dots ignored; one token at edit distance 1, or 2 for
                  tokens of 7+ characters; Devanagari compared with Devanagari, Latin with Latin — never across);
  (c) case_no   — the main petition number of a draft differs from the note's, or a petition number is one-two digits
                  away from one in the note (same year);
  (d) English documents (parawise, affidavit): dates, amounts and case numbers only;
  (e) post      — the same name with a different post in two table rows.
Output: one "WARN <check> <fact> '<value>': <doc> (<json path>) / <doc>" line per finding, then
  "consistency_check: N docs, M facts, W warnings". --details FILE (or env CASE_DETAILS_FILE; S-F3): full lines go to
  FILE, stdout has every '…' value replaced by its length. --json OUT.json: the findings as a list of
  {check, fact, value, docs: [A, B], where: [path, …], what} (for tools/engine_supabase.py `consistency`)."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lint_spec as L  # noqa: E402 — unquoted(), letters_of(), part_no(), REF_LOOSE / REF_PKG, details switch (S-F3)

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
NOTE = "टिप्पणी"
STUDY0 = "अभ्यास भाग 0"
ORDER_LABEL = {"gr": "शासन निर्णय", "corrigendum": "शुद्धिपत्रक", "circular": "परिपत्रक", "memo": "ज्ञापन",
               "notification": "अधिसूचना", "endorsement": "पृष्ठांकन", "office_order": "कार्यालयीन आदेश",
               "press_note": "प्रसिद्धीपत्रक", "addendum": "शासन पूरकपत्र"}
# keys whose values are not facts of the case: the document's own number / issue date / signature / addressee / layout
SKIP_KEYS = {"ref_no", "date", "signer", "signers", "designation", "desk", "kind", "type", "reminder", "bold_last",
             "website_line", "gazette_part", "number", "saka_date", "time", "uo", "to", "from", "salutation", "copies",
             "enclosure", "department", "ls_ref", "house", "bench", "deponent", "day", "month_year", "place",
             "identified_by", "advocate_for", "paper_book", "on_behalf_of", "layout", "doc_author", "_comment",
             "image", "width_cm", "heading"}
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                           "september", "october", "november", "december"])}
MONTHS.update({m[:3]: v for m, v in list(MONTHS.items())})
MONTHS["sept"] = 9
_MON = "|".join(sorted(MONTHS, key=len, reverse=True))

DATE_RE = re.compile(r"(?<![\d./-])(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?![\d])")
DATE_EN1 = re.compile(rf"(?<![\dA-Za-z])(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MON})\.?,?\s+(\d{{4}})(?!\d)", re.I)
DATE_EN2 = re.compile(rf"(?<![A-Za-z])({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})(?!\d)", re.I)
_GROUPED = r"\d{1,3}(?:,\d{2,3})*,\d{3}"   # Indian 76,23,814 / Western 7,623,814
AMT_PREFIX = re.compile(rf"(?:रु\.|रुपये|Rs\.?|INR|₹)\s*({_GROUPED}|\d+)(\.\d{{1,2}})?(?!\d|,\d)", re.I)
AMT_BARE = re.compile(rf"(?<![\d,./-])({_GROUPED})(\.\d{{1,2}})?(?!\d|,\d)")
CR_RE = re.compile(r"(?<![A-Za-zऀ-ॿ])C\.?\s?R\.?\s*(?:No\.?\s*)?(\d{1,4})\s*[-/]\s*(\d{4})(?!\d)")
_QUAL = r"(?:\s*\([^)]{0,20}\))*"
CASE_MR = re.compile(r"(रिट\s+याचिका|जनहित\s+याचिका|अवमान\s+याचिका|विशेष\s+अनुमती\s+याचिका|मूळ\s+अर्ज|"
                     r"(?:दिवाणी|सिव्हि?ल)\s+अपील|याचिका)" + _QUAL + r"\s*(?:क्र\.|क्रमांक)\s*(\d+)\s*(?:/|सन)\s*(\d{4})(?!\d)")
CASE_EN = re.compile(r"(?<![A-Za-z])(W\.?\s?P\.?|Writ\s+Petition|P\.?I\.?L\.?|Public\s+Interest\s+Litigation|"
                     r"C\.?\s?P\.?|Contempt\s+Petition|O\.?\s?A\.?|Original\s+Application|S\.?\s?L\.?\s?P\.?|"
                     r"Special\s+Leave\s+Petition|Civil\s+Appeal|C\.?\s?A\.?|Petition)" + _QUAL +
                     r"\s*(?:No\.?|Nos\.?|Number)\s*(\d+)\s*(?:/|of)\s*(\d{4})(?!\d)", re.I)
CASE_KIND = [(re.compile(p, re.I), k) for p, k in (
    (r"^(?:रिट|W\.?\s?P|Writ)", "WP"), (r"^(?:जनहित|P\.?I\.?L|Public)", "PIL"), (r"^(?:अवमान|C\.?\s?P\b|Contempt)", "CP"),
    (r"^(?:विशेष|S\.?\s?L|Special)", "SLP"), (r"^(?:मूळ|O\.?\s?A|Original)", "OA"),
    (r"^(?:दिवाणी|सिव्ह|Civil|C\.?\s?A\b)", "CA"))]

HON_MR = re.compile(r"(?<![ऀ-ॿ])(?:श्रीमती|श्रीम\.|श्री\.|कै\.)\s*")
HON_EN = re.compile(r"(?<![A-Za-z])(?:Shrimati|Smt\.?|Shri\.?|Mr\.|Mrs\.|Ms\.|Kum\.)\s*")
TOK_MR = re.compile(r"[ऀ-ॿ]+\.?")
TOK_EN = re.compile(r"[A-Z][A-Za-z]*\.?")
STOP_MR = {"हे", "ह्या", "या", "व", "आणि", "तसेच", "तथा", "किंवा", "ही", "हा", "इतर", "रोजी", "दि.", "क्र.", "येथे",
           "सदर", "त्यानंतर", "तथापि", "याबाबत", "त्यानुषंगाने", "उपरोक्त", "सबब", "शासन", "प्रस्ताव"}
STOP_EN = {"And", "Vs", "Vs.", "V.", "The", "Of", "Petitioner", "Respondent"}
INVISIBLE = re.compile("[‌‍़]")   # ZWNJ, ZWJ, nukta


def norm_num(s):
    return (s or "").translate(DEV_DIGITS)


def clean(text):
    """Own text of a string: quotes, पृ.N/प.वि. / पॅकेज PDF references and "____" blanks removed; Devanagari digits -> ASCII."""
    t = L.unquoted(text or "")
    t = L.REF_LOOSE.sub(" ", t)
    t = L.REF_PKG.sub(" ", t)
    t = re.sub(r"_{2,}", " ", t)
    return norm_num(t)


def dates(t):
    out = []
    for m in DATE_RE.finditer(t):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            out.append(f"{d:02d}.{mo:02d}.{y}")
    for rx, order in ((DATE_EN1, (1, 2, 3)), (DATE_EN2, (2, 1, 3))):
        for m in rx.finditer(t):
            d, mon, y = int(m.group(order[0])), MONTHS.get(m.group(order[1]).lower().rstrip(".")), int(m.group(order[2]))
            if mon and 1 <= d <= 31:
                out.append(f"{d:02d}.{mon:02d}.{y}")
    return out


def amounts(t):
    """Normalised amounts: digits only (commas dropped), ".NN" kept unless it is zero."""
    out, spans = [], []
    for m in AMT_PREFIX.finditer(t):
        out.append(_amt(m.group(1), m.group(2))); spans.append(m.span(1))
    tt = DATE_RE.sub(lambda m: " " * len(m.group(0)), t)
    for m in AMT_BARE.finditer(tt):
        if not any(a <= m.start(1) < b for a, b in spans):
            out.append(_amt(m.group(1), m.group(2)))
    return out


def _amt(n, dec):
    v = n.replace(",", "").lstrip("0") or "0"
    d = (dec or "").lstrip(".")
    return v if not d or int(d) == 0 else f"{v}.{d}"


def case_kind(label):
    for rx, k in CASE_KIND:
        if rx.search(label.strip()):
            return k
    return "P"   # a bare "याचिका" / "Petition": compatible with every kind


def cases(t):
    out = []
    for rx in (CASE_MR, CASE_EN):
        for m in rx.finditer(t):
            out.append((case_kind(m.group(1)), m.group(2).lstrip("0") or "0", m.group(3)))
    return out


def crs(t):
    return [f"{int(m.group(1))}-{m.group(2)}" for m in CR_RE.finditer(t)]


BASE_LETTER = re.compile(r"[\u0905-\u0939\u0958-\u0961]")   # independent vowels + consonants


def initial(w, latin):
    """"आर." / "व्ही." / "ह." / "R." — at most two base letters before the dot."""
    w = w.rstrip(".")
    return len(w) <= 2 if latin else len(BASE_LETTER.findall(w)) <= 2


def names(t, latin=False):
    """[(tokens, script)] of person names after an honorific."""
    out = []
    hon, tok_re, stop = (HON_EN, TOK_EN, STOP_EN) if latin else (HON_MR, TOK_MR, STOP_MR)
    for m in hon.finditer(t):
        pos, toks = m.end(), []
        while len(toks) < 4:
            mm = tok_re.match(t, pos)
            if not mm:
                break
            w = mm.group(0)
            if w in stop or w.rstrip(".") in stop or (not latin and w.startswith("यां")):
                break
            toks.append(INVISIBLE.sub("", w.rstrip(".")))
            pos = mm.end()
            if w.endswith(".") and not initial(w, latin):   # a full stop after a word (not an initial) ends the name
                break
            sp = re.match(r"[ \t]*", t[pos:]).group(0)
            if len(sp) > 2 or (not sp and not w.endswith(".")):   # "ह.ना." needs no space after an initial
                break
            pos += len(sp)
        toks = [x for x in toks if x]
        if toks:
            out.append((tuple(x.lower() if latin else x for x in toks), "lat" if latin else "dev"))
    return out


def walk(obj, path, skip=SKIP_KEYS):
    """(path, text, table-row or None) for each string; a table row is yielded once more as a whole (for posts)."""
    if isinstance(obj, str):
        yield path, obj, None
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from walk(x, f"{path}[{i}]", skip)
    elif isinstance(obj, dict):
        if isinstance(obj.get("table"), list):
            rows = [r for r in obj["table"] if isinstance(r, list)]
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    if isinstance(c, (str, int, float)):
                        yield f"{path}.table[{i}][{j}]", str(c), None
                if i and rows:
                    yield f"{path}.table[{i}]", (rows[0], r), "row"
        for k, v in obj.items():
            if k in skip or k == "table":
                continue
            yield from walk(v, f"{path}.{k}" if path else k, skip)


def documents(spec, study=None):
    """[(label, english?, [(path, value, kind)])] — the note first."""
    docs = []
    n = spec.get("note") if isinstance(spec.get("note"), dict) else {}
    docs.append((NOTE, False, list(walk({k: n[k] for k in ("first", "sub", "paras", "closing") if k in n}, "note"))))
    for p, Lt in L.letters_of(spec):
        lab = "अर्धशासकीय पत्र" if isinstance(Lt, dict) and Lt.get("kind") == "do" else "पत्र"
        docs.append((lab if p == "letter" else f"{lab} ({p})", False, list(walk(Lt, p))))
    orders = ([("order", spec["order"])] if isinstance(spec.get("order"), dict) else []) + \
             [(f"orders[{i}]", o) for i, o in enumerate(spec.get("orders") or []) if isinstance(o, dict)]
    for p, o in orders:
        lab = ORDER_LABEL.get(str(o.get("type") or ""), "आदेश") + "-प्रारूप"
        if len(orders) > 1:
            lab += f" ({p})"
        docs.append((lab, False, list(walk(o, p))))
    if isinstance(spec.get("parawise"), dict):
        docs.append(("परिच्छेदनिहाय उत्तर", True, list(walk(spec["parawise"], "parawise"))))
    if isinstance(spec.get("affidavit"), dict):
        docs.append(("शपथपत्र", True, list(walk(spec["affidavit"], "affidavit"))))
    if isinstance(spec.get("lq"), dict):
        docs.append(("विधानमंडळ उत्तर", False, list(walk(spec["lq"], "lq"))))
    if isinstance(study, dict):
        for i, part in enumerate(study.get("parts") or []):
            if isinstance(part, dict) and L.part_no(str(part.get("heading") or "")) == 0:
                docs.append((STUDY0, False, list(walk(part.get("blocks") or [], f"parts[{i}].blocks"))))
                break
    return docs


def facts_of(items, english):
    """{fact: [(value, path)]} of one document (own text only)."""
    f = {"date": [], "amount": [], "case": [], "cr": [], "name": [], "post": []}
    for path, val, kind in items:
        if kind == "row":
            head, row = val
            pc = [j for j, h in enumerate(head) if isinstance(h, str) and re.search(r"(?<![ऀ-ॿ])पद(?:नाम)?(?![ऀ-ॿ])|पदाचे\s+नाव", h)]
            if english or not pc:
                continue
            nm = [x for c in row if isinstance(c, str) for x in names(clean(c))]
            post = " ".join(clean(str(row[pc[0]]) if pc[0] < len(row) else "").split()).strip(" ,.;")
            if nm and post:
                f["post"].append(((nm[0][0], post), path))
            continue
        t = clean(val)
        f["date"] += [(x, path) for x in dates(t)]
        f["amount"] += [(x, path) for x in amounts(t)]
        f["case"] += [(x, path) for x in cases(t)]
        f["cr"] += [(x, path) for x in crs(t)]
        f["name"] += [(x, path) for x in names(t, latin=True)]
        if not english:
            f["name"] += [(x, path) for x in names(t)]
    return f


def presence(spec):
    """Every date / amount / case / C R anywhere in the note (body incl. quotes + related): a draft's fact is "present"."""
    n = spec.get("note") if isinstance(spec.get("note"), dict) else {}
    blob = norm_num(" ".join(v for _, v, k in walk({"n": {k: n[k] for k in ("first", "sub", "paras", "closing") if k in n},
                                                   "r": spec.get("related") or []}, "", set()) if k is None))
    blob = L.REF_LOOSE.sub(" ", blob)
    return {"date": set(dates(blob)), "amount": set(amounts(blob)), "case": set(cases(blob)), "cr": set(crs(blob))}


def lev(a, b, cap=3):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def near(a, b):
    """Two different name tokens that are one spelling apart (1 edit; 2 edits for 7+ characters)."""
    if a == b or min(len(a), len(b)) < 4:
        return False
    d = lev(a, b, 2)
    return d == 1 or (d == 2 and min(len(a), len(b)) >= 7)


def name_variant(a, b):
    """a, b = token tuples (same script). Same token count, every token equal but one near-match; or a surname-only
    name near the other's last token."""
    if a == b or "".join(a) == "".join(b):
        return False
    if len(a) == len(b):
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        return len(diff) == 1 and near(*diff[0])
    if min(len(a), len(b)) == 1:
        s, o = (a, b) if len(a) == 1 else (b, a)
        return near(s[0], o[-1])
    return False


def show_name(toks, script):
    return " ".join(toks) if script == "dev" else " ".join(x.title() for x in toks)


def show_case(c):
    return f"{c[0]} {c[1]}/{c[2]}"


def show_amount(v):
    n, _, d = v.partition(".")
    if len(n) > 3:   # Indian grouping
        head, tail = n[:-3], n[-3:]
        head = ",".join(re.findall(r"\d{1,2}(?=(?:\d{2})*$)", head))
        n = f"{head},{tail}"
    return f"रु. {n}{'.' + d if d else ''}/-"


def check(spec, study=None):
    docs = documents(spec, study)
    per = [(lab, en, facts_of(items, en)) for lab, en, items in docs]
    have = presence(spec)
    note_f = per[0][2]
    find = []
    nfacts = sum(len(v) for _, _, f in per for v in f.values())

    def add(chk, fact, value, a, b, where, what):
        key = (chk, fact, value, a, b)
        for x in find:
            if x["_k"] == key:
                x["where"] = sorted(set(x["where"]) | set(where)); return
        find.append({"_k": key, "check": chk, "fact": fact, "value": value, "docs": [a, b], "where": sorted(set(where)),
                     "what": what})

    # (a) only_in: dates / amounts / C R nos. of drafts and the Study part 0 that are nowhere in the note
    for lab, en, f in per[1:]:
        for fact, label in (("date", "दिनांक"), ("amount", "रक्कम"), ("cr", "C R क्र.")):
            for v, p in f[fact]:
                if v not in have[fact]:
                    shown = show_amount(v) if fact == "amount" else v
                    add("only_in", fact, shown, lab, NOTE, [p], f"{label} {shown} टिप्पणीत नाही")
    # (c) petition numbers
    note_cases = [c for c, _ in note_f["case"]]
    compat = lambda x, y: x[0] == y[0] or "P" in (x[0], y[0])
    for lab, en, f in per[1:]:
        if not f["case"]:
            continue
        for i, (c, p) in enumerate(f["case"]):
            if c in have["case"]:
                continue
            main = i == 0 and note_cases and compat(c, note_cases[0])
            typo = [n for n in note_cases if compat(c, n) and n[2] == c[2] and 0 < lev(n[1], c[1], 2) <= 2]
            if main or typo:
                other = note_cases[0] if main else typo[0]
                add("case_no", "case", f"{show_case(c)} / {show_case(other)}", lab, NOTE, [p],
                    f"याचिका क्रमांक वेगळा ({show_case(other)} / {show_case(c)})")
    # (b) names: every pair of spellings (same script), across all documents and within one
    occ = {}
    for lab, en, f in per:
        for (toks, sc), p in f["name"]:
            occ.setdefault((toks, sc), []).append((lab, p))
    keys = list(occ)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a[1] == b[1] and name_variant(a[0], b[0]):
                da, db = occ[a][0][0], occ[b][0][0]
                na, nb = show_name(*a), show_name(*b)
                add("name", "name", f"{na} / {nb}", da, db, [x[1] for x in occ[a][:2] + occ[b][:2]],
                    f"नावाचे वेगळे लेखन ({na} / {nb})")
    # (e) posts: one name, two posts
    posts = {}
    for lab, en, f in per:
        for (toks, post), p in f["post"]:
            posts.setdefault(toks, {}).setdefault(post, []).append((lab, p))
    for toks, pm in posts.items():
        ps = list(pm)   # first-seen order (note first)
        for i, x in enumerate(ps):
            for y in ps[i + 1:]:
                if re.sub(r"[\s.]", "", x) == re.sub(r"[\s.]", "", y):
                    continue
                nm = " ".join(toks)
                add("post", "post", f"{nm}: {x} / {y}", pm[x][0][0], pm[y][0][0], [pm[x][0][1], pm[y][0][1]],
                    f"{nm} यांचे पद वेगळे ({x} / {y})")
    for x in find:
        del x["_k"]
    return find, len(docs), nfacts


def warning_text(x):
    """The engine's soft warning (INSTRUCTIONS §4.26): "पडताळणी अपूर्ण — विसंगती: <what>, <doc A> / <doc B>"."""
    return f"पडताळणी अपूर्ण — विसंगती: {x['what']}, {x['docs'][0]} / {x['docs'][1]}"


def main(argv):
    args = list(argv)
    L.set_details(L.details_arg(args), "consistency_check " + " ".join(args))
    opt = {}
    for k in ("--study", "--json"):
        while k in args:
            i = args.index(k)
            opt[k] = args[i + 1] if i + 1 < len(args) else None
            del args[i:i + 2]
    if len(args) != 1:
        print(__doc__); return 2
    try:
        spec = L.load(args[0])
        assert isinstance(spec, dict)
    except Exception as e:
        print(f"consistency_check: spec not read ({e.__class__.__name__})"); return 2
    study = None
    if opt.get("--study") and os.path.exists(opt["--study"]):
        try:
            study = L.load(opt["--study"])
        except Exception as e:
            print(f"consistency_check: study not read ({e.__class__.__name__}) — Study part 0 skipped")
    find, ndocs, nfacts = check(spec, study)
    for x in find:
        L.out(f"WARN {x['check']} {x['fact']} '{x['value']}': {x['docs'][0]} ({', '.join(x['where'][:4])}) / {x['docs'][1]}")
    print(f"consistency_check: {ndocs} docs, {nfacts} facts, {len(find)} warnings")
    if opt.get("--json"):
        with open(opt["--json"], "w", encoding="utf-8") as f:
            json.dump(find, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
