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

Errors
  - "parawise" is not an object; required text fields empty: court, case, petitioner, respondent_no, subject,
    prepared_for; respondents (non-empty list of str); paras (non-empty list)
  - every para: "para" (e.g. "1", "1 to 3"), "averment" and "remarks" non-empty
  - remarks only a cryptic word ("denied", "not admitted", "admitted", "no comments", "noted", "not denied",
    "denied and not admitted", "matter of record", …) — Rule 58 Note (ii)
  - recommendation not "oppose" / "not oppose" / "____"; recommendation_reason empty (not required with "____")
  - background / enclosures not a list of str; verification not a bool
  - internal ids / repo paths anywhere (lint_spec.id_hits / repo_hits)
Warnings
  - recommendation "____" (blank: no basis in the record — the Section fills it; Rule 58(4)(a) still applies)
  - Devanagari outside “…” / "…" quotes (the parawise text is English; names/designations in quotes are fine)
  - remarks shorter than 8 words (Note (ii): "elaborate factual position")
  - no enclosures (Note (ii): "invariably accompanied by copies of relevant notifications, rules and orders")
  - background empty; para label not of the forms "1", "1 to 3", "1-3", "1, 2", optionally followed by "(…)"
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


def _strings(pw):
    return list(lint_spec.strings(pw, "parawise"))


def lint_parawise(spec):
    """Errors for spec["parawise"] (list of "parawise.<path>: <rule> — <detail>"); [] when clean or absent."""
    if not isinstance(spec, dict) or "parawise" not in spec:
        return []
    pw = spec["parawise"]
    if not isinstance(pw, dict):
        return ["parawise: structure — must be an object"]
    P = []
    for k in REQ_TEXT:
        if not _txt(pw.get(k)):
            P.append(f"parawise.{k}: required field — '{k}' missing or empty")
    rs = pw.get("respondents")
    if not isinstance(rs, list) or not rs or not all(_txt(r) for r in rs):
        P.append("parawise.respondents: required field — non-empty list of respondent names")
    for k in ("background", "enclosures"):
        v = pw.get(k, [])
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            P.append(f"parawise.{k}: structure — must be a list of strings")
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
    for path, t in _strings(pw):
        for x in lint_spec.id_hits(t): P.append(f"{path}: internal id — '{x}'")
        for x in lint_spec.repo_hits(t): P.append(f"{path}: repo path/word — '{x}'")
    return P


def warnings_parawise(spec):
    """WARN-level findings for spec["parawise"]; never errors."""
    if not isinstance(spec, dict) or not isinstance(spec.get("parawise"), dict):
        return []
    pw = spec["parawise"]; W = []
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
