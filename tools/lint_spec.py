#!/usr/bin/env python3
"""lint_spec.py <spec.json> [--study study.json] [--pages N] [--allow-missing-part1]
Pre-build lint: checks spec.json (note/letter, format: tools/mkdocs.py docstring) and study.json (tools/build_study.py
docstring) against the rules that tools/verify_outputs.py checks on the built files (PROPOSAL_SOP.md Step 4,
INSTRUCTIONS.md §4), so problems are fixed before building. spec.json may be "-" to lint only --study.
Prints one line per problem "<JSON path>: <rule> — <detail>"; "LINT OK" and exit 0 when there is none, exit 1 otherwise.
Windows: `py tools/lint_spec.py ...`; runner: `python3 tools/lint_spec.py ...`.

Rules (spec.json)
  - no internal file ids (z<digit>_<4 digits>) and no repo paths (register/, service-rules/, precedent-library/, pdf/,
    repo, रेपो) in any note / related / letter text
  - no BANNED word and no "पॅकेज PDF" in the note body (first, paras, sub, closing) or the letter ("पॅकेज PDF" is allowed
    in related and the Study)
  - पृ. references: same accepted forms as verify_outputs ("पृ.N/प.वि.", "पृ. N / प.वि.", lists, ranges, Devanagari
    digits, blank "पृ.      /प.वि."); "“…”" quotes are skipped in related; page range 1..N only with --pages N
  - note.first ends with "सादर."
  - last note para (note.closing if not blank, else the last text item of note.paras) is one of the two SOP forms:
    "सबब, … पत्राचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल." or
    "सबब, … वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."
  - note.signers == INSTRUCTIONS §4.6 chain (+ "अ.मु.स. (वित्त)" last); "अ.मु.स. (वित्त)" present <=> last para has
    "वित्त विभागाच्या मान्यतेस्तव"
  - §4.19 (text outside quotes; note body, letter, related heading/source — not the verbatim related text): no '.:-'
    (use ':-'), 'करून' not 'करुन', 'प्रारूप' not 'प्रारुप', one space after 'दि.' / 'क्र.' / 'प्र. क्र.' in running text
    (file/letter nos. and other tokens with '/' or '-' left exactly); missing-info para starts
    "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-"
  - letter (when present): ref_no संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6; to, subject, refs present; intro starts
    "उपरोक्त विषयाबाबत संदर्भाधीन", contains "आपणांस कळविण्यात येते की," and ends with ":-" when there are points
  - §4.20: no document (प्रत / प्रमाणपत्र / अहवाल) in a data row of a letter.points table (outside quotes); documents go
    after the table as a numbered list introduced by DOC_INTRO
  - §4.21 स्मरणपत्र (letter.reminder): refs[0] has "या कार्यासनाचे समक्रमांकाचे पत्र", intro has "अद्याप अप्राप्त" and
    "ही विनंती"
  - §4.22 letter to the High Court that asks information from a District Judge ("प्रमुख जिल्हा व सत्र न्यायाधीश, <place>
    यांच्याकडून"): letter.copies has "प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, <place> यांना आवश्यक
    कार्यवाहीसाठी"
  - §4.23 "मा." (note body and letter outside quotes; not the addressee block letter.to): before मुख्य न्यायमूर्ती /
    न्यायमूर्ती / प्रशासकीय न्यायाधीश, and before उच्च न्यायालय… (the court itself; an office designation
    "उच्च न्यायालय (… शाखा)" excepted)
  - §4.24 "शुद्धिपत्रक" (not शुध्दिपत्रक / शुद्धीपत्रक / शुद्धपत्रक)
Rules (study.json): parts with headings भाग 0 … भाग 7 (--allow-missing-part1: भाग 1 may be absent); no internal ids;
  पृ. references as above ("“…”" skipped).
The constants and check functions below are the ONE definition shared with tools/verify_outputs.py."""
import json
import re
import sys

# ---------------- shared rule definitions (also used by verify_outputs.py) ----------------
SIGNERS = ["का. अ. (श्रीम. कऱ्हाडे)", "अ.स. (श्री. वडनेरकर)", "उ.वि.स. नि. उ.स. (श्री. बोंद्रे)", "प्र.स. व वि.प. (श्री. खटी)"]
AMS = "अ.मु.स. (वित्त)"
FIN = "वित्त विभागाच्या मान्यतेस्तव"
# closed list (PROPOSAL_SOP.md Step 4 "Banned words") — keep both lists identical
BANNED = ["दिसून येते", "असे दिसते", "पडताळणी केली असता", "माझ्या मते", "मला वाटते", "असे वाटते", "ठरवावे", "कदाचित", "बहुधा"]
RELATED = "संबंधित माहिती (संदर्भासाठी)"
PKG = "पॅकेज PDF"
ID_RE = re.compile(r"z\d_\d{4}")
REPO_RE = re.compile(r"(register/|service-rules/|precedent-library/|(?<![A-Za-z])pdf/|(?<![A-Za-z])repo(?![A-Za-z])|रेपो)", re.I)
D = r"[0-9०-९]+"
NUMLIST = rf"{D}(?:\s*(?:-|–|ते|,)\s*{D})*"
REF_LOOSE = re.compile(r"पृ\.([^/\n]{0,40}?)/\s*प\.वि\.")
REF_PKG = re.compile(rf"पॅकेज PDF\s*पृ\.\s*({NUMLIST})")
REF_NO = re.compile(r"संकिर्ण-[0-9]{4}/[0-9]+/प्र\.क्र\.[0-9]+/का\.6")
QUOTE_RE = re.compile(r"“[^”]*”")
PART_RE = re.compile(r"\s*भाग\s*([0-9०-९])(?![0-9०-९])")
LH_EMAIL = "lnjd.desk6-mh@mah.gov.in"
# last-para forms (PROPOSAL_SOP Step 4), tolerant of the wording between the fixed parts
LAST_LETTER_RE = re.compile(r"^सबब\s*,.*पत्राचे\s+प्रारूप\s+पृ\.[^/]{0,40}/\s*प\.वि\.\s*वर\s+मान्यतेस्तव\s+सादर\s*\.\s*"
                            r"मान्य\s+झाल्यास\s+पत्र\s+निर्गमित\s+करण्यात\s+येईल\s*\.$", re.S)
LAST_FIN_RE = re.compile(r"^सबब\s*,.*वित्त\s+विभागाच्या\s+मान्यतेस्तव\s+सादर\s+करण्यात\s+येत\s+आहे\s*\.$", re.S)
INTRO_START = "उपरोक्त विषयाबाबत संदर्भाधीन"
INTRO_HAS = "आपणांस कळविण्यात येते की,"
MISSING_HEAD = "प्रस्तावासोबत खालील माहिती उपलब्ध नाही"  # missing-information para (PROPOSAL_SOP Step 4)
MISSING_FORM = MISSING_HEAD + ":- (1)…; (2)…"
# INSTRUCTIONS §4.20 (02.11.2026): letter table only for data to fill in; documents after the table as a numbered list
DOC_RE = re.compile(r"प्रत(?![्िृ])|प्रमाणपत्र|अहवाल")   # प्रत / प्रती(सह) — not प्रत्यक्ष, प्रतिनियुक्ती
DOC_INTRO = "तसेच, खालील कागदपत्रे उपलब्ध करून देण्यात यावीत, ही विनंती:-"
DOC_MSG = "कागदपत्रे तक्त्यात नको — तक्त्यानंतर यादीत (§4.20)"


def num(s):
    return int(s.translate(str.maketrans("०१२३४५६७८९", "0123456789")))


def ns(s):
    return re.sub(r"\s+", " ", s).strip()


def ref_problems(text, npages, label, skip_quotes=False):
    """पृ. reference problems in text; npages None = syntax / reversed-range only (no package range check)."""
    if skip_quotes:
        text = QUOTE_RE.sub(" ", text)
    probs = []
    lists = []
    for mt in REF_LOOSE.finditer(text):
        inner = mt.group(1).strip()
        if not re.search(r"[0-9०-९]", inner):
            continue  # blank placeholder "पृ.      /प.वि." or table header "पृ./प.वि."
        if not re.fullmatch(NUMLIST, inner):
            probs.append(f"{label}: unparsed reference '{mt.group(0)}'"); continue
        lists.append((mt.group(0), inner))
    for mt in REF_PKG.finditer(text):
        lists.append((mt.group(0), mt.group(1)))
    for whole, inner in lists:
        for part in re.split(r"\s*,\s*", inner):
            ends = [num(x) for x in re.split(r"\s*(?:-|–|ते)\s*", part) if x.strip()]
            if len(ends) == 2 and ends[0] > ends[1]:
                probs.append(f"{label}: reversed range '{whole}'")
            if npages is not None:
                for n in ends:
                    if not 1 <= n <= npages:
                        probs.append(f"{label}: '{whole}' — page {n} outside package (1-{npages})")
    return probs


QUOTE_RE = re.compile(r"“[^”]*”|\"[^\"]*\"")
def unquoted(text):
    """Text outside “…” quotes (verbatim extracts keep their own wording)."""
    return QUOTE_RE.sub(" ", text or "")


# INSTRUCTIONS §4.18 (01.11.2026): respectful, clear official Marathi
STYLE_RULES = [
    (re.compile(r"सौ\."), "आदरार्थी उल्लेख — 'सौ.' ऐवजी 'श्रीमती' (§4.18)"),
    (re.compile(r"(?<![ऀ-ॿ])कै\.(?=\S)"), "आदरार्थी उल्लेख — 'कै.' नंतर एक जागा (§4.18)"),
    # मराठी भाषा विभाग GR कपासू-2020/प्र.क्र.56/भाषा-2, दि.10.11.2022 (docs/STYLE_RESEARCH_LANG.md)
    (re.compile(r"ध्द"), "शुद्धलेखन — 'ध्द' ऐवजी 'द्ध' (मराठी भाषा विभाग GR दि.10.11.2022)"),
    (re.compile(r"(?<![ऀ-ॿ])श्री\.(?=[^\s(])"), "आदरार्थी उल्लेख — 'श्री.' नंतर एक जागा; नाव प्रस्तावात आहे तसे (§4.18)"),
    (re.compile(r"शुद्धीपत्र|शुद्धपत्र|शुध्दिपत्र|शुध्दीपत्र"), "शुद्धलेखन — 'शुद्धिपत्रक' (§4.24)"),
]
LETTER_STYLE_RULES = [
    # GAD टिप्पणी लेखन व पत्रव्यवहार 12.3: letters to courts in "विशेष सौजन्यपूर्वक भाषा" (docs/STYLE_RESEARCH_LETTERS.md)
    (re.compile(r"अतितात्काळ|तात्काळ|तातडीने|त्वरित|ताबडतोब|विनाविलंब|अविलंब|सत्वर"),
     "पत्राची भाषा — 'तात्काळ / तातडीने / त्वरित…' नको; 'लवकरात लवकर' वापरा (§4.18)"),
    (re.compile(r"(?:करावी|करावा|करावे|द्यावी|द्यावा|द्यावे|यावी|यावीत|यावे|पाठवावी|पाठवावे|कळवावे)\s*\.(?!:-)"),
     "पत्राची भाषा — थेट आदेशात्मक शेवट; '…, ही विनंती.' अशी विनंतीपूर्वक मांडणी हवी (§4.18)"),
]
REQUEST = "ही विनंती"


def style_hits(text, letter=False):
    t = unquoted(text)
    out = [msg for rx, msg in STYLE_RULES if rx.search(t)]
    if letter:
        out += [msg for rx, msg in LETTER_STYLE_RULES if rx.search(t)]
    return out


# INSTRUCTIONS §4.19 (01.11.2026) — मराठी भाषा विभाग GR कपासू-2020/प्र.क्र.56/भाषा-2, दि. 10.11.2022 (परिशिष्ट तीन,
# अ.क्र. 23: संक्षेपचिन्हानंतर जागा). Applied to text outside “…” quotes only; one definition for lint, verify and the
# sample normaliser (fix_lang).
SPELL_419 = {"करुन": "करून", "प्रारुप": "प्रारूप"}
COLON_DASH_RE = re.compile(r"(?<!प\.वि)(?<!क्र)(?<!दि)\.:-")   # ".:-" -> ":-" (abbreviation dots such as प.वि. kept)
ABBR_PREFIXES = ("प्र.क्र.", "क्र.", "दि.")                         # running-text abbreviations that take a space
CODE_RE = re.compile(r"/|[0-9A-Za-zऀ-ॿ_]-[0-9A-Za-zऀ-ॿ_]")      # file/letter nos., codes: left exactly
OPEN_CH = "(“‘[\"'"
ABBR_NEXT = re.compile(r"[0-9०-९A-Za-zऀ-ॿ_(]")


def _abbr_fix_token(tok):
    """Spaced form of one whitespace token, or None when it needs no change (§4.19 abbreviation rule)."""
    core = tok.lstrip(OPEN_CH); lead = tok[:len(tok) - len(core)]
    pre = next((p for p in ABBR_PREFIXES if core.startswith(p)), None)
    if pre is None or CODE_RE.search(core):
        return None
    rest = core[len(pre):]
    spaced = "प्र. क्र." if pre == "प्र.क्र." else pre
    if rest and ABBR_NEXT.match(rest):
        return lead + spaced + " " + rest
    return lead + spaced + rest if spaced != pre else None


def abbr_hits(text):
    """Tokens in running text with no space after 'दि.' / 'क्र.' / 'प्र.क्र.' (quotes, codes with '/' or '-' skipped)."""
    return [mt.group(0) for mt in re.finditer(r"\S+", unquoted(text)) if _abbr_fix_token(mt.group(0)) is not None]


def _fix_plain(t):
    for a, b in SPELL_419.items():
        t = t.replace(a, b)
    t = COLON_DASH_RE.sub(":-", t)
    return re.sub(r"\S+", lambda mt: _abbr_fix_token(mt.group(0)) or mt.group(0), t)


def fix_lang(text):
    """text with the §4.19 forms applied outside “…” / "…" quotes (quoted extracts unchanged)."""
    out, pos = [], 0
    for mt in QUOTE_RE.finditer(text):
        out += [_fix_plain(text[pos:mt.start()]), mt.group(0)]; pos = mt.end()
    out.append(_fix_plain(text[pos:]))
    return "".join(out)


def lang_hits(text):
    """§4.19 problems in text (outside quotes)."""
    t = unquoted(text); out = []
    for a, b in SPELL_419.items():
        if a in t: out.append(f"शुद्धलेखन — '{a}' ऐवजी '{b}' (§4.19)")
    if COLON_DASH_RE.search(t): out.append("विरामचिन्ह — '.:-' ऐवजी ':-' (§4.19)")
    hits = abbr_hits(text)
    if hits: out.append(f"संक्षेपचिन्हानंतर एक जागा — 'दि. 17.09.2026', 'क्र. 108', 'प्र. क्र.' (§4.19): {hits[:3]}")
    return out


# INSTRUCTIONS §4.23 (Abhi, 02.11.2026): "मा." before the High Court and judges (Section practice; docs/STYLE_RESEARCH_LETTERS.md F10)
MA_JUDGE_RE = re.compile(r"मुख्य\s+न्यायमूर्ती|(?<!मुख्य )(?<!मुख्य)न्यायमूर्ती|प्रशासकीय\s+न्यायाधीश")
MA_COURT_RE = re.compile(r"(?<![ऀ-ॿ])(?:मुंबई\s+)?उच्च\s+न्यायालय(?!\s*\()")   # "मा. मुंबई उच्च न्यायालय"   # "उच्च न्यायालय (अपील शाखा)" = office designation: excepted
MA_BEFORE = re.compile(r"मा\.\s?$")


def _ma_spans(t, court=True):
    rxs = (MA_JUDGE_RE, MA_COURT_RE) if court else (MA_JUDGE_RE,)
    return sorted((m.start(), m.group(0)) for rx in rxs for m in rx.finditer(t) if not MA_BEFORE.search(t[max(0, m.start() - 4):m.start()]))


def ma_hits(text, court=True):
    """§4.23: occurrences outside quotes without "मा." before them."""
    hits = [w for _, w in _ma_spans(unquoted(text), court)]
    return [f"आदरार्थी उल्लेख — 'मा. {sorted(set(hits))[0]}' (मा. उच्च न्यायालय / मा. न्यायमूर्ती; §4.23)"] if hits else []


def fix_ma(text, court=True):
    """text with "मा. " inserted where §4.23 needs it (outside quotes)."""
    def fix(t):
        for pos, _ in reversed(_ma_spans(t, court)):
            t = t[:pos] + "मा. " + t[pos:]
        return t
    out, pos = [], 0
    for mt in QUOTE_RE.finditer(text):
        out += [fix(text[pos:mt.start()]), mt.group(0)]; pos = mt.end()
    out.append(fix(text[pos:]))
    return "".join(out)


# §4.21 स्मरणपत्र / §4.22 copy to the District Judge when the letter goes through the High Court
REMINDER_REF = "या कार्यासनाचे समक्रमांकाचे पत्र"
REMINDER_HAS = "अद्याप अप्राप्त"
DJ_FROM_RE = re.compile(r"प्रमुख\s+जिल्हा\s+व\s+सत्र\s+न्यायाधीश\s*,\s*([^\s,]+)\s+यांच्याकडून")
COPY_END = "यांना आवश्यक कार्यवाहीसाठी"


def dj_copy(place):
    return f"प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, {place} {COPY_END}"


def banned_hits(text):
    return [w for w in BANNED if w in text]


def id_hits(text):
    return sorted(set(ID_RE.findall(text)))


def repo_hits(text):
    return sorted(set(mt.group(0) for mt in REPO_RE.finditer(text)))


def signer_problems(tail, has_ams):
    """tail = the signer lines in order (§4.6)."""
    exp = SIGNERS + ([AMS] if has_ams else [])
    return [] if list(tail) == exp else [f"signer block {list(tail)} != {exp}"]


def finance_problems(last, has_ams):
    fin = FIN in last
    return [] if fin == has_ams else [f"'{AMS}' {'present' if has_ams else 'absent'} but last para "
                                      f"{'contains' if fin else 'lacks'} '{FIN}'"]


def part_no(text):
    mt = PART_RE.match(text or "")
    return num(mt.group(1)) if mt else None


def heading_problems(have, allow_missing=()):
    return [f"heading भाग {i} missing" for i in range(8) if i not in have and i not in allow_missing]


# ---------------- spec walking ----------------
def strings(obj, path):
    """(path, text) for every string inside obj (lists, dicts, table rows)."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from strings(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k == "bold_last":
                continue
            yield from strings(v, f"{path}.{k}" if path else k)


def lint_spec(spec, pages=None):
    P = []
    if not isinstance(spec, dict) or not isinstance(spec.get("note"), dict):
        return ["note: structure — spec has no 'note' object"]
    n = spec["note"]
    body = [x for k in ("first", "paras", "sub", "closing") if k in n for x in strings(n[k], f"note.{k}")]
    related = list(strings(spec.get("related", []), "related"))
    L = spec.get("letter")
    letter = list(strings(L, "letter")) if L else []
    signers = list(strings(n.get("signers", []), "note.signers"))

    for path, t in body + related + letter + signers:
        for x in id_hits(t): P.append(f"{path}: internal id — '{x}'")
        for x in repo_hits(t): P.append(f"{path}: repo path/word — '{x}'")
    for path, t in body + letter:
        for w in banned_hits(t): P.append(f"{path}: banned word — '{w}'")
        if PKG in t: P.append(f"{path}: 'पॅकेज PDF' only in संबंधित माहिती — use पृ.N/प.वि.")
    for path, t in body:
        P += [f"{path}: {m}" for m in style_hits(t)]
    for path, t in letter:
        P += [f"{path}: {m}" for m in style_hits(t, letter=True)]
    for path, t in body + [(pth, t) for pth, t in letter if not pth.startswith("letter.to")]:
        P += [f"{path}: {m}" for m in ma_hits(t)]
    rel_own = [(pth, t) for pth, t in related if not re.search(r"\.text(\[|$)", pth)]  # extracts (.text) are verbatim
    for path, t in body + letter + rel_own:
        P += [f"{path}: {m}" for m in lang_hits(t)]
    for path, t in body:
        if ns(unquoted(t)).startswith(MISSING_HEAD) and not ns(t).startswith(MISSING_HEAD + ":-"):
            P.append(f"{path}: missing-info para — form '{MISSING_FORM}' (§4.19)")
    for path, t in body + letter:
        P += [f"{path}: पृ. reference — {x.split(': ', 1)[1]}" for x in ref_problems(t, pages, path)]
    for path, t in related:
        P += [f"{path}: पृ. reference — {x.split(': ', 1)[1]}" for x in ref_problems(t, pages, path, skip_quotes=True)]

    # first / last para
    first = n.get("first")
    if not isinstance(first, str) or not first.strip():
        P.append("note.first: structure — first para missing")
    elif not first.strip().endswith("सादर."):
        P.append("note.first: first para — must end with 'सादर.'")
    paras = n.get("paras", [])
    if not isinstance(paras, list):
        P.append("note.paras: structure — must be a list"); paras = []
    closing = n.get("closing")
    if isinstance(closing, str) and closing.strip():
        lpath, last = "note.closing", closing
    else:
        idx = [i for i, x in enumerate(paras) if isinstance(x, str)]
        lpath, last = (f"note.paras[{idx[-1]}]", paras[idx[-1]]) if idx else ("note.paras", "")
    lastn = ns(last)
    if not (LAST_LETTER_RE.match(lastn) or LAST_FIN_RE.match(lastn)):
        P.append(f"{lpath}: last para — not one of the SOP forms ('सबब, … पत्राचे प्रारूप पृ.  /प.वि. वर मान्यतेस्तव सादर. "
                 f"मान्य झाल्यास पत्र निर्गमित करण्यात येईल.' / 'सबब, … वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे.')")

    # signers + Finance
    sg = n.get("signers")
    if not isinstance(sg, list):
        P.append("note.signers: signer chain (§4.6) — missing"); sg = []
    sg = [ns(x) if isinstance(x, str) else x for x in sg]
    has_ams = AMS in sg
    P += [f"note.signers: signer chain (§4.6) — {x}" for x in signer_problems(sg, has_ams)]
    P += [f"{lpath}: अ.मु.स. (वित्त) <=> Finance last para — {x}" for x in finance_problems(lastn, has_ams)]

    # letter
    if L:
        if not isinstance(L, dict):
            return P + ["letter: structure — must be an object"]
        rn = L.get("ref_no")
        if not isinstance(rn, str) or not REF_NO.fullmatch(rn.strip()):
            P.append(f"letter.ref_no: ref no. — not संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6: '{rn}'")
        for k in ("to", "refs"):
            v = L.get(k)
            if not isinstance(v, list) or not any(isinstance(x, str) and x.strip() for x in v):
                P.append(f"letter.{k}: letter field — '{k}' missing or empty")
        if not isinstance(L.get("subject"), str) or not L["subject"].strip():
            P.append("letter.subject: letter field — 'subject' missing or empty")
        intro = L.get("intro")
        if not isinstance(intro, str) or not intro.strip():
            P.append("letter.intro: letter field — 'intro' missing or empty")
        else:
            it = ns(intro)
            if not it.startswith(INTRO_START):
                P.append(f"letter.intro: intro wording — must start with '{INTRO_START}'")
            if INTRO_HAS not in it:
                P.append(f"letter.intro: intro wording — must contain '{INTRO_HAS}'")
            if REQUEST not in it:
                P.append(f"letter.intro: पत्राची भाषा — माहिती मागताना '…, {REQUEST}.' अशी विनंतीपूर्वक मांडणी हवी (§4.18)")
            if L.get("points") and not it.endswith(":-"):
                P.append("letter.intro: intro wording — must end with ':-' before the points")
        # §4.21 स्मरणपत्र
        if L.get("reminder"):
            r0 = (L.get("refs") or [""])[0] if isinstance(L.get("refs"), list) else ""
            if REMINDER_REF not in ns(str(r0)):
                P.append(f"letter.refs[0]: स्मरणपत्र (§4.21) — संदर्भ '{REMINDER_REF} दि. __'")
            if isinstance(intro, str) and (REMINDER_HAS not in intro or REQUEST not in intro):
                P.append(f"letter.intro: स्मरणपत्र (§4.21) — '… माहिती {REMINDER_HAS} आहे. … {REQUEST}.'")
        # §4.22 via the High Court, information from a District Judge -> copy line
        to_txt = " ".join(x for x in (L.get("to") or []) if isinstance(x, str))
        if "उच्च न्यायालय" in to_txt:
            copies = [ns(x) for x in (L.get("copies") or []) if isinstance(x, str)]
            for place in {m.group(1) for path, t in letter for m in DJ_FROM_RE.finditer(ns(unquoted(t)))}:
                if not any(place in c and c.endswith(COPY_END) for c in copies):
                    P.append(f"letter.copies: प्रत (§4.22) — '{dj_copy(place)}'")
        pts = L.get("points") if isinstance(L.get("points"), list) else []
        for i, pt in enumerate(pts):
            if isinstance(pt, dict) and isinstance(pt.get("table"), list):
                for r, row in enumerate(pt["table"][1:], 1):
                    for c, cell in enumerate(row if isinstance(row, list) else []):
                        if isinstance(cell, str) and DOC_RE.search(unquoted(cell)):
                            P.append(f"letter.points[{i}].table[{r}][{c}]: {DOC_MSG} — '{DOC_INTRO}'")
    return P


def lint_study(study, pages=None, allow_missing_part1=False):
    P = []
    if not isinstance(study, dict) or not isinstance(study.get("parts"), list):
        return ["study.parts: structure — study has no 'parts' list"]
    have = set()
    for i, part in enumerate(study["parts"]):
        h = part.get("heading") if isinstance(part, dict) else None
        k = part_no(h) if isinstance(h, str) else None
        if k is None:
            P.append(f"study.parts[{i}].heading: study heading — not 'भाग N …': '{h}'")
        else:
            have.add(k)
    P += [f"study.parts: study headings भाग 0-7 — {x}" for x in heading_problems(have, (1,) if allow_missing_part1 else ())]
    for path, t in strings(study, "study"):
        for x in id_hits(t): P.append(f"{path}: internal id — '{x}'")
        P += [f"{path}: पृ. reference — {x.split(': ', 1)[1]}" for x in ref_problems(t, pages, path, skip_quotes=True)]
    return P


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def main(argv):
    args = argv[1:]
    spec_path = study_path = None; pages = None; allow1 = False
    try:
        while args:
            a = args.pop(0)
            if a == "--study": study_path = args.pop(0)
            elif a == "--pages": pages = int(args.pop(0))
            elif a == "--allow-missing-part1": allow1 = True
            elif a.startswith("--") or spec_path is not None: raise ValueError(a)
            else: spec_path = a
    except (IndexError, ValueError):
        print(__doc__); return 2
    if spec_path is None:
        print(__doc__); return 2
    probs = []
    for path, fn in ((spec_path if spec_path != "-" else None, lambda o: lint_spec(o, pages)),
                     (study_path, lambda o: lint_study(o, pages, allow1))):
        if path is None:
            continue
        try:
            obj = load(path)
        except Exception as e:
            probs.append(f"{path}: JSON — {e}"); continue
        probs += fn(obj)
    for p in probs:
        print(p)
    if not probs:
        print("LINT OK")
    return 1 if probs else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
