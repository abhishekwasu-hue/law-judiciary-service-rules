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
    "सबब, … पत्राचे प्रारुप पृ.  /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल." or
    "सबब, … वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."
  - note.signers == INSTRUCTIONS §4.6 chain (+ "अ.मु.स. (वित्त)" last); "अ.मु.स. (वित्त)" present <=> last para has
    "वित्त विभागाच्या मान्यतेस्तव"
  - letter (when present): ref_no संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6; to, subject, refs present; intro starts
    "उपरोक्त विषयाबाबत संदर्भाधीन", contains "आपणांस कळविण्यात येते की," and ends with ":-" when there are points
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
LAST_LETTER_RE = re.compile(r"^सबब\s*,.*पत्राचे\s+प्रारुप\s+पृ\.[^/]{0,40}/\s*प\.वि\.\s*वर\s+मान्यतेस्तव\s+सादर\s*\.\s*"
                            r"मान्य\s+झाल्यास\s+पत्र\s+निर्गमित\s+करण्यात\s+येईल\s*\.$", re.S)
LAST_FIN_RE = re.compile(r"^सबब\s*,.*वित्त\s+विभागाच्या\s+मान्यतेस्तव\s+सादर\s+करण्यात\s+येत\s+आहे\s*\.$", re.S)
INTRO_START = "उपरोक्त विषयाबाबत संदर्भाधीन"
INTRO_HAS = "आपणांस कळविण्यात येते की,"


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
        P.append(f"{lpath}: last para — not one of the SOP forms ('सबब, … पत्राचे प्रारुप पृ.  /प.वि. वर मान्यतेस्तव सादर. "
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
            if L.get("points") and not it.endswith(":-"):
                P.append("letter.intro: intro wording — must end with ':-' before the points")
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
