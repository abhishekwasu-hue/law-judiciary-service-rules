#!/usr/bin/env python3
"""lint_parawise.py <spec.json>
Pre-build lint of the optional "parawise" block of spec.json (court-case parawise remarks; tools/build_parawise.py).
Prints one line per problem "parawise.<path>: <rule> — <detail>"; "LINT OK" and exit 0 when there is none, exit 1
otherwise. Warnings are printed as "WARN parawise.<path>: <message>" and never change the exit code.
Windows: `py tools/lint_parawise.py ...`; runner: `python3 tools/lint_parawise.py ...`.

Basis (docs/COURT_AND_ORDERS_RESEARCH.md, decision B8; R2 §B): Rules for the Conduct of the Legal Affairs of
Government, 1984 — Rule 58(3) parawise report "on all the points raised in the Writ Petition and affidavit";
Rule 58(4)(a) recommendation whether the petition "should or should not be opposed"; Rule 58(4) Note (ii) the report
"should not contain cryptic answers such as 'not admitted' or 'denied' but should contain elaborate factual position and
should be invariably accompanied by copies of relevant notifications, rules and orders"; Rule 32 replies "to each
paragraph"; Rule 58(6) the Government Pleader drafts the counter affidavit (so "verification" defaults to false).
INSTRUCTIONS §3.1: the parawise text is in English.

Two layouts (tools/build_parawise.py): DEFAULT = the Section's office format (Abhi, 03.11.2026: "ok tar format mi dilelya
parawise cha thewa") — table "Sr. No. | Para No. | Remarks"; "layout": "rule58" = the earlier Rule 58 layout.

Errors — default (office) layout
  - "parawise" is not an object; "layout" not "office" / "rule58"; required text fields empty: case, petitioner,
    on_behalf_of (or intro); respondent / intro present but not a string; paras (non-empty list)
  - every paras item: either {"section": "<text>"} (separator row, e.g. "Grounds") or {para, remarks[, averment]} with
    "para" and "remarks" non-empty ("averment" is optional and not printed)
  - cryptic remarks (as below); internal ids / repo paths; C27 draft words (as below)
Warnings — default (office) layout
  - no "Prayer" row (Rule 58(3): every point of the petition, the prayer clauses included)
  - keys of the rule58 layout present (court, respondents, respondent_no, subject, prepared_for, relief_sought,
    background, enclosures, recommendation, recommendation_reason, officer, designation, place, date, verification) —
    not printed in the office format
  - Devanagari outside quotes; remarks shorter than 8 words; para label not "1", "21 to 24", "5 (a) to (e)",
    "Para No.1", "Ground (a)", "Prayer Clauses (a) to (h)"; §4.30 contempt-prone wording in the remarks (as below)

Errors — "layout": "rule58"
  - "parawise" is not an object; required text fields empty: court, case, petitioner, respondent_no, subject,
    prepared_for; respondents (non-empty list of str); paras (non-empty list)
  - every para: "para" (e.g. "1", "1 to 3"), "averment" and "remarks" non-empty
  - remarks only a cryptic word ("denied", "not admitted", "admitted", "no comments", "noted", "not denied",
    "denied and not admitted", "matter of record", …) — Rule 58 Note (ii)
  - recommendation not "oppose" / "not oppose" / "____"; recommendation_reason empty (not required with "____")
  - background not a list of str / table items, enclosures not a list of str; verification not a bool;
    relief_sought present but not a string; a background table item ({"title"?, "table"}) not 2-6 columns of
    plain-text rows (INSTRUCTIONS §4.30, 03.11.2026)
  - internal ids / repo paths anywhere (lint_spec.id_hits / repo_hits)
  - C27 (02.11.2026): "पॅकेज" anywhere; outside quotes "package PDF", "warning", "TODO", the other warning / working words
    and the AI words (lint_spec.draft_word_hits)
Warnings — "layout": "rule58"
  - recommendation "____" (blank: no basis in the record — the Section fills it; Rule 58(4)(a) still applies)
  - Devanagari outside “…” / "…" quotes (the parawise text is English; names/designations in quotes are fine)
  - remarks shorter than 8 words (Note (ii): "elaborate factual position")
  - no enclosures (Note (ii): "invariably accompanied by copies of relevant notifications, rules and orders")
  - background empty; para label not of the forms "1", "1 to 3", "1-3", "1, 2", optionally followed by "(…)"
  - INSTRUCTIONS §4.30 (03.11.2026, owner: raise the quality of our drafts): contempt-prone / order-like wording toward
    the court in the Department's own text (remarks, background, recommendation_reason; not the averment or
    relief_sought summaries of the petition, not “…” quotes) — e.g. "erroneous judgment", "the Court failed to", "illegal order",
    "perverse", "the Court must" — with a respectful form to use instead (CONTEMPT_PRONE; common drafting usage,
    basis: Contempt of Courts Act, 1971, s. 2(c); WARNING only, never an error)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint_spec  # noqa: E402  (id_hits, repo_hits, strings, unquoted)

REQ_TEXT = ("court", "case", "petitioner", "respondent_no", "subject", "prepared_for")
RECS = ("oppose", "not oppose")
CRYPTIC = {
    "denied", "not admitted", "admitted", "no comments", "no comment", "noted", "not denied", "nil",
    "denied and not admitted", "not admitted and denied", "admitted to the extent", "matter of record",
    "matter of record and needs no reply", "needs no reply", "no reply", "not applicable", "na", "n a",
    "false", "incorrect", "wrong", "denied in toto", "strictly denied", "vehemently denied",
}
CRYPTIC_PREFIX = re.compile(r"^(?:the\s+)?(?:contents?|averments?|allegations?|statements?)\s+(?:of|in)\s+"
                            r"(?:this|the|these|said)\s+(?:para(?:graph)?s?)\s+(?:is|are)\s+", re.I)
DEV_RE = re.compile(r"[ऀ-ॿ]")
PARA_RE = re.compile(r"\d+[A-Za-z]?(?:\s*(?:to|-|–|,|and)\s*\d+[A-Za-z]?)*(?:\s*\([^)]*\))?")
MIN_WORDS = 8
TABLE_COLS = (2, 6)
# §4.30 (03.11.2026): short list of contempt-prone / order-like phrases toward a court (common drafting usage; basis
# Contempt of Courts Act, 1971, s. 2(c) "scandalises … the authority of any court"). WARN only: (regex, respectful form).
_CT = r"(?:hon'?ble\s+|learned\s+)?(?:high\s+)?(?:court|tribunal|bench|judge)"
CONTEMPT_PRONE = [
    (re.compile(r"\berroneous(?:ly)?\s+(?:judg(?:e)?ment|order|decision|finding|direction)s?\b", re.I),
     "'with respect, the Department submits that the order may be reconsidered in view of <rule/GR/fact>'"),
    (re.compile(_CT + r"\s+(?:has\s+|had\s+)?(?:failed|ignored|overlooked|erred|misread|misdirected)\b", re.I),
     "'it is respectfully submitted that <fact/provision> was not placed before the Hon'ble Court'"),
    (re.compile(r"\b(?:illegal|unlawful|void|bad\s+in\s+law)\s+(?:judg(?:e)?ment|order|direction|decision)s?\b", re.I),
     "'the Department respectfully submits that the order is not in accordance with <rule/GR>'"),
    (re.compile(r"\b(?:perverse|biased|absurd|non-application\s+of\s+mind|without\s+(?:any\s+)?application\s+of\s+mind)\b",
                re.I),
     "state the factual / legal position respectfully, without characterising the order"),
    (re.compile(_CT + r"\s+(?:must|should|shall|is\s+directed\s+to|ought\s+to)\b", re.I),
     "'the Hon'ble Court may be pleased to …' (a request, never an order)"),
]
OWN_TEXT_KEYS = ("remarks", "background", "recommendation_reason")   # relief_sought = the petitioner's prayer (like the averment)


BLANK_RE = re.compile(r"^_{2,}$")


def rec_blank(rec):
    """True for the blank "____" recommendation (02.11.2026, lead F1: Rule 58(4)(a) recommendation only from the record;
    otherwise "____" for the Section to fill + a warning)."""
    return isinstance(rec, str) and bool(BLANK_RE.match(rec.strip()))


def _txt(x):
    return x.strip() if isinstance(x, str) else ""


def cryptic(remarks):
    """True when the remarks are only a cryptic word such as 'Denied.' (Rule 58 Note (ii))."""
    t = re.sub(r"[^a-z ]+", " ", CRYPTIC_PREFIX.sub("", remarks.strip().lower()))
    t = re.sub(r"\s+", " ", t).strip()
    return t in CRYPTIC or t == ""


def contempt_hits(text):
    """§4.30: (phrase found, respectful form) for each CONTEMPT_PRONE pattern outside quotes."""
    u = lint_spec.unquoted(text or "")
    return [(m.group(0), fix) for rx, fix in CONTEMPT_PRONE for m in [rx.search(u)] if m]


def _bg_table_problem(it):
    """None when a background item is a valid §4.30 table {"title"?: str, "table": [[str…]…]}, else the reason."""
    if set(it) - {"title", "table"}:
        return f"unknown keys {sorted(set(it) - {'title', 'table'})}"
    if "title" in it and not isinstance(it["title"], str):
        return "title must be a string"
    rows = it.get("table")
    if not isinstance(rows, list) or len(rows) < 2 or not all(isinstance(r, list) for r in rows):
        return "table must be a list of at least 2 rows (header + data), each a list"
    n = len(rows[0])
    if not TABLE_COLS[0] <= n <= TABLE_COLS[1]:
        return f"{n} columns — use {TABLE_COLS[0]} to {TABLE_COLS[1]}"
    if any(len(r) != n for r in rows) or not all(isinstance(c, str) for r in rows for c in r):
        return "every row needs the header's column count, plain-text cells"
    return None


def _strings(pw):
    return list(lint_spec.strings(pw, "parawise"))


LAYOUTS = ("office", "rule58")
OFFICE_REQ = ("case", "petitioner")
RULE58_ONLY = ("court", "respondents", "respondent_no", "department", "subject", "prepared_for", "relief_sought",
               "background", "enclosures", "recommendation", "recommendation_reason", "officer", "designation",
               "place", "date", "verification")
OFFICE_LABEL_RE = re.compile(r"(?:Para(?:graph)?s?\s*No\.?\s*)?\d+[A-Za-z]?(?:\s*(?:to|-|–|,|and)\s*\d+[A-Za-z]?)*"
                             r"(?:\s*\([A-Za-z0-9]+\)(?:\s*(?:to|-|–|,|and)\s*\([A-Za-z0-9]+\))*)?"
                             r"|(?:Grounds?|Prayer(?:\s+Clauses?)?)\b.*", re.I)


def layout(pw):
    """"rule58" when the spec says so, else the default office format (same rule as tools/build_parawise.py)."""
    return "rule58" if isinstance(pw, dict) and str(pw.get("layout") or "").strip().lower() == "rule58" else "office"


def _common(pw, P):
    for path, t in _strings(pw):
        for x in lint_spec.id_hits(t): P.append(f"{path}: internal id — '{x}'")
        for x in lint_spec.repo_hits(t): P.append(f"{path}: repo path/word — '{x}'")
        # C27 (02.11.2026): no "package PDF" / "पॅकेज", "warning", "TODO" or AI word (outside quotes)
        for w in lint_spec.draft_word_hits(t):
            P.append(f"{path}: draft word — '{w}' — no package / warning / working / AI word in the draft (C27)")


def _lint_office(pw):
    P = []
    for k in OFFICE_REQ:
        if not _txt(pw.get(k)):
            P.append(f"parawise.{k}: required field — '{k}' missing or empty (office format; the earlier layout needs "
                     "\"layout\": \"rule58\")")
    if not _txt(pw.get("on_behalf_of")) and not _txt(pw.get("intro")):
        P.append("parawise.on_behalf_of: required field — 'on_behalf_of' (e.g. \"Respondent Nos. 1 and 2 i.e. the State "
                 "of Maharashtra, through …\") missing or empty")
    for k in ("respondent", "intro", "on_behalf_of"):
        if k in pw and not isinstance(pw[k], str):
            P.append(f"parawise.{k}: structure — must be a string")
    paras = pw.get("paras")
    if not isinstance(paras, list) or not paras:
        P.append("parawise.paras: required field — non-empty list of {para, remarks} / {\"section\": \"Grounds\"} "
                 "(Rule 58(3): all the points raised in the petition)")
        paras = []
    for i, it in enumerate(paras):
        path = f"parawise.paras[{i}]"
        if not isinstance(it, dict):
            P.append(f"{path}: structure — must be an object {{para, remarks}} or {{\"section\": …}}"); continue
        if "section" in it:
            if not _txt(it.get("section")) or set(it) - {"section"}:
                P.append(f"{path}: structure — a separator row is {{\"section\": \"Grounds\"}} only")
            continue
        for k in ("para", "remarks"):
            if not _txt(it.get(k)):
                P.append(f"{path}.{k}: required field — '{k}' missing or empty")
        if "averment" in it and not isinstance(it["averment"], str):
            P.append(f"{path}.averment: structure — must be a string (optional, not printed)")
        rm = _txt(it.get("remarks"))
        if rm and cryptic(rm):
            P.append(f"{path}.remarks: cryptic remark '{rm}' — Rule 58 Note (ii): not 'denied' / 'not admitted' alone; "
                     "give the factual position with rule/GR references")
    _common(pw, P)
    return P


def _warn_office(pw):
    W = []
    for path, t in _strings(pw):
        if DEV_RE.search(lint_spec.unquoted(t)):
            W.append(f"{path}: Devanagari outside quotes — the parawise remarks are in English (INSTRUCTIONS §3.1); "
                     "put Marathi names/designations in “…”")
    rows = [it for it in pw.get("paras") or [] if isinstance(it, dict) and "section" not in it]
    for i, it in enumerate(pw.get("paras") or []):
        if not isinstance(it, dict) or "section" in it:
            continue
        rm = _txt(it.get("remarks"))
        if rm and not cryptic(rm) and len(rm.split()) < MIN_WORDS:
            W.append(f"parawise.paras[{i}].remarks: short remark ({len(rm.split())} words) — Rule 58 Note (ii): "
                     "factual position")
        lab = _txt(it.get("para"))
        if lab and not OFFICE_LABEL_RE.fullmatch(lab):
            W.append(f"parawise.paras[{i}].para: para label '{lab}' — use '1', '21 to 24', '5 (a) to (e)', "
                     "'Ground (a)', 'Prayer Clauses (a) to (h)'")
        for phrase, fix in contempt_hits(it.get("remarks") if isinstance(it.get("remarks"), str) else ""):
            W.append(f"parawise.paras[{i}].remarks: contempt-prone wording '{phrase}' — use respectful language toward "
                     f"the Court (§4.30), e.g. {fix}")
    if rows and not any(re.search(r"\bprayer", _txt(it.get("para")), re.I) for it in rows):
        W.append("parawise.paras: no 'Prayer' row — answer the prayer clauses too (Rule 58(3); office format row "
                 "\"Prayer Clauses (a) to (…)\")")
    extra = [k for k in RULE58_ONLY if k in pw]
    if extra:
        W.append(f"parawise: keys {extra} belong to \"layout\": \"rule58\" — not printed in the office format")
    return W


def lint_parawise(spec):
    """Errors for spec["parawise"] (list of "parawise.<path>: <rule> — <detail>"); [] when clean or absent."""
    if not isinstance(spec, dict) or "parawise" not in spec:
        return []
    pw = spec["parawise"]
    if not isinstance(pw, dict):
        return ["parawise: structure — must be an object"]
    if "layout" in pw and str(pw.get("layout") or "").strip().lower() not in LAYOUTS:
        return [f"parawise.layout: structure — 'office' (default) or 'rule58': '{pw.get('layout')}'"]
    if layout(pw) == "office":
        return _lint_office(pw)
    P = []
    for k in REQ_TEXT:
        if not _txt(pw.get(k)):
            P.append(f"parawise.{k}: required field — '{k}' missing or empty")
    rs = pw.get("respondents")
    if not isinstance(rs, list) or not rs or not all(_txt(r) for r in rs):
        P.append("parawise.respondents: required field — non-empty list of respondent names")
    enc = pw.get("enclosures", [])
    if not isinstance(enc, list) or not all(isinstance(x, str) for x in enc):
        P.append("parawise.enclosures: structure — must be a list of strings")
    bg = pw.get("background", [])
    if not isinstance(bg, list):
        P.append("parawise.background: structure — must be a list of strings (or §4.30 table items)")
    else:
        for i, x in enumerate(bg):
            if isinstance(x, str):
                continue
            why = _bg_table_problem(x) if isinstance(x, dict) else "must be a string or a table item"
            if why:
                P.append(f"parawise.background[{i}]: structure — {why} (§4.30 table: {{\"title\", \"table\"}})")
    if "relief_sought" in pw and not isinstance(pw["relief_sought"], str):
        P.append("parawise.relief_sought: structure — must be a string (§4.30: the relief prayed for, in brief)")
    if "verification" in pw and not isinstance(pw["verification"], bool):
        P.append("parawise.verification: structure — must be true/false (default false: the GP drafts the counter "
                 "affidavit, Rule 58(6))")
    paras = pw.get("paras")
    if not isinstance(paras, list) or not paras:
        P.append("parawise.paras: required field — non-empty list of {para, averment, remarks} (Rule 58(3): all the "
                 "points raised in the petition)")
        paras = []
    for i, it in enumerate(paras):
        path = f"parawise.paras[{i}]"
        if not isinstance(it, dict):
            P.append(f"{path}: structure — must be an object {{para, averment, remarks}}"); continue
        for k in ("para", "averment", "remarks"):
            if not _txt(it.get(k)):
                P.append(f"{path}.{k}: required field — '{k}' missing or empty")
        rm = _txt(it.get("remarks"))
        if rm and cryptic(rm):
            P.append(f"{path}.remarks: cryptic remark '{rm}' — Rule 58 Note (ii): not 'denied' / 'not admitted' alone; "
                     "give the elaborate factual position with rule/GR references")
    rec = pw.get("recommendation")
    blank = rec_blank(rec)
    if not blank and (not isinstance(rec, str) or rec.strip().lower() not in RECS):
        P.append(f"parawise.recommendation: recommendation — must be 'oppose' or 'not oppose' (Rule 58(4)(a)), or "
                 f"'____' when the record gives no basis: '{rec}'")
    if not blank and not _txt(pw.get("recommendation_reason")):
        P.append("parawise.recommendation_reason: recommendation — reason missing (Rule 58(4)(a)/(b))")
    _common(pw, P)
    return P


def warnings_parawise(spec):
    """WARN-level findings for spec["parawise"]; never errors."""
    if not isinstance(spec, dict) or not isinstance(spec.get("parawise"), dict):
        return []
    pw = spec["parawise"]
    if layout(pw) == "office":
        return _warn_office(pw)
    W = []
    for path, t in _strings(pw):
        if DEV_RE.search(lint_spec.unquoted(t)):
            W.append(f"{path}: Devanagari outside quotes — the parawise remarks are in English (INSTRUCTIONS §3.1); "
                     "put Marathi names/designations in “…”")
    for i, it in enumerate(pw.get("paras") or []):
        if not isinstance(it, dict):
            continue
        rm = _txt(it.get("remarks"))
        if rm and not cryptic(rm) and len(rm.split()) < MIN_WORDS:
            W.append(f"parawise.paras[{i}].remarks: short remark ({len(rm.split())} words) — Rule 58 Note (ii): "
                     "elaborate factual position")
        lab = _txt(it.get("para"))
        if lab and not PARA_RE.fullmatch(lab):
            W.append(f"parawise.paras[{i}].para: para label '{lab}' — use '1', '1 to 3', '1, 2'")
    if rec_blank(pw.get("recommendation")):
        W.append("parawise.recommendation: recommendation '____' — the record gives no basis; the Section fills "
                 "'oppose' / 'not oppose' and the reason (Rule 58(4)(a)/(b))")
    if not pw.get("enclosures"):
        W.append("parawise.enclosures: no documents enclosed — Rule 58 Note (ii): copies of relevant notifications, "
                 "rules and orders")
    if not pw.get("background"):
        W.append("parawise.background: brief facts empty")
    for k in OWN_TEXT_KEYS:   # §4.30: respectful language toward the court (own text only, not the averments)
        src = [(f"parawise.paras[{i}].{k}", it.get(k)) for i, it in enumerate(pw.get("paras") or [])
               if isinstance(it, dict)] if k == "remarks" else list(lint_spec.strings(pw.get(k), f"parawise.{k}"))
        for path, t in src:
            if not isinstance(t, str):
                continue
            for phrase, fix in contempt_hits(t):
                W.append(f"{path}: contempt-prone wording '{phrase}' — use respectful language toward the Court "
                         f"(§4.30), e.g. {fix}")
    return W


def main(argv):
    if len(argv) != 2:
        print(__doc__); return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            spec = json.load(f)
    except Exception as e:
        print(f"{argv[1]}: JSON — {e}"); return 1
    if not isinstance(spec, dict) or "parawise" not in spec:
        print(f"{argv[1]}: no 'parawise' block"); return 1
    probs = lint_parawise(spec)
    for p in probs:
        print(p)
    for w in warnings_parawise(spec):
        print("WARN " + w)
    if not probs:
        print("LINT OK")
    return 1 if probs else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
