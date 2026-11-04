#!/usr/bin/env python3
"""lint_lq.py <spec.json>
Pre-build lint of the optional "lq" block of spec.json (विधानमंडळ प्रश्नाचे उत्तर; tools/build_lq.py).
Prints one line per problem "lq.<path>: <rule> — <detail>"; "LINT OK" and exit 0 when there is none, exit 1 otherwise.
Warnings are printed as "WARN lq.<path>: <message>" and never change the exit code.

Basis (docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md part B): सा.प्र.वि. "टिप्पणी लेखन व पत्रव्यवहार" प्रकरण 13 (परि. 13.2: one
prescribed form, the date of answer at the very top; 13.5: no पूरक टिप्पणी for an unstarred question; 13.9: the
specimen); MMOP 2023 §16.3(2)-(3) (draft answer clause by clause; "Notes for supplementary questions" for starred / short
notice); the Legislature's printed lists (answer forms "होय, हे खरे आहे.", "हे खरे नाही.", "हे अंशत: खरे आहे.", "प्रश्न
उद्भवत नाही."); INSTRUCTIONS §4.27 (no warning / AI words, "____" for unknowns).

Errors
  - "lq" not an object; house not assembly / council; kind not starred / unstarred / short_notice
  - subject, number, portfolio empty; parts not a non-empty list of {q, a} with "q" non-empty (every sub-question)
  - a part without an answer "a" (MMOP 16.3(2): the draft answer is given clause by clause)
  - members not a non-empty list of strings; supplementary not a list of strings / table items
  - internal ids / repo paths; C27 draft words (package / warning / working / AI words, "—", "→", web addresses)
Warnings
  - starred / short-notice question without "supplementary" (GADT 13.9, MMOP 16.3(3): पुरवणी टिप्पणी)
  - unstarred question with "supplementary" (GADT 13.5: not needed)
  - an answer to a "… हे खरे आहे काय" sub-question that does not open with होय / नाही / हे खरे / हे अंशत: खरे / प्रश्न
    उद्भवत नाही or a joint "(१) व (२) …" form (the Legislature's printed answer forms)
  - Latin letters outside “…” in the answer text (the answer is in Marathi; names of schemes in brackets are fine)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint_spec  # noqa: E402

HOUSES = ("assembly", "council")
KINDS = ("starred", "unstarred", "short_notice")
TEXT_KEYS = ("house", "kind", "number", "answer_date", "subject", "minister", "portfolio", "ref_no", "department",
             "date", "ls_ref", "ls_date", "copies", "signer", "designation", "supplementary_heading")
TRUE_Q = re.compile(r"खरे\s+आहे\s+काय")
ANS_OPEN = re.compile(r"^\s*(?:\([०-९0-9]+\)\s*(?:(?:,|व|ते)\s*\([०-९0-9]+\)\s*)*)?"
                      r"(?:होय|नाही|हे\s+(?:ही\s+)?खरे|हे\s+अंशत:?\s+खरे|अंशत:?\s+खरे|प्रश्न\s+उद्भवत\s+नाही)")
LATIN = re.compile(r"[A-Za-z]{3,}")


def _txt(x):
    return x.strip() if isinstance(x, str) else ""


def lint_lq(spec):
    """Errors for spec["lq"]; [] when clean or absent."""
    if not isinstance(spec, dict) or "lq" not in spec:
        return []
    lq = spec["lq"]
    if not isinstance(lq, dict):
        return ["lq: structure — must be an object"]
    P = []
    for k in TEXT_KEYS:
        if k in lq and not isinstance(lq[k], str):
            P.append(f"lq.{k}: structure — must be a string")
    if _txt(lq.get("house")) and _txt(lq.get("house")).lower() not in HOUSES:
        P.append(f"lq.house: structure — 'assembly' (विधानसभा) or 'council' (विधानपरिषद): '{lq.get('house')}'")
    if _txt(lq.get("kind")) and _txt(lq.get("kind")).lower() not in KINDS:
        P.append(f"lq.kind: structure — 'starred' / 'unstarred' / 'short_notice': '{lq.get('kind')}'")
    for k, what in (("subject", "the question's title"), ("number", "प्रश्न क्रमांक ('____' until known)"),
                    ("portfolio", "e.g. 'मुख्यमंत्री' / '____ मंत्री'")):
        if not _txt(lq.get(k)):
            P.append(f"lq.{k}: required field — {what}")
    mem = lq.get("members")
    if mem is not None and not (isinstance(mem, list) and mem and all(_txt(x) for x in mem)):
        P.append("lq.members: structure — non-empty list of names (e.g. 'श्री. ____ (____)')")
    parts = lq.get("parts")
    if not isinstance(parts, list) or not parts:
        P.append("lq.parts: required field — every sub-question {q, a} in order (MMOP 16.3(2): clause by clause)")
        parts = []
    for i, pt in enumerate(parts):
        if not isinstance(pt, dict):
            P.append(f"lq.parts[{i}]: structure — must be an object {{q, a}}"); continue
        if not _txt(pt.get("q")):
            P.append(f"lq.parts[{i}].q: required field — the sub-question as received")
        if not _txt(pt.get("a")):
            P.append(f"lq.parts[{i}].a: required field — the answer to this sub-question (MMOP 16.3(2))")
    sup = lq.get("supplementary")
    if sup is not None:
        if not isinstance(sup, list):
            P.append("lq.supplementary: structure — list of paragraphs / table items")
        else:
            for i, x in enumerate(sup):
                if isinstance(x, str):
                    continue
                rows = x.get("table") if isinstance(x, dict) else None
                if not (isinstance(rows, list) and len(rows) >= 2 and all(isinstance(r, list) for r in rows)
                        and all(isinstance(c, str) for r in rows for c in r)
                        and len({len(r) for r in rows}) == 1 and 2 <= len(rows[0]) <= 6):
                    P.append(f"lq.supplementary[{i}]: structure — a string or {{\"title\"?, \"table\": [[header…], "
                             "[row…]]}} (2-6 columns, plain text)")
    for p, t in lint_spec.strings(lq, "lq"):
        for x in lint_spec.id_hits(t): P.append(f"{p}: internal id — '{x}'")
        for x in lint_spec.repo_hits(t): P.append(f"{p}: repo path/word — '{x}'")
        for w in lint_spec.draft_word_hits(t):
            P.append(f"{p}: draft word — '{w}' — no package / warning / working / AI word in the draft (C27)")
    return P


def warnings_lq(spec):
    """WARN-level findings for spec["lq"]; never errors."""
    if not isinstance(spec, dict) or not isinstance(spec.get("lq"), dict):
        return []
    lq = spec["lq"]
    W = []
    kind = _txt(lq.get("kind")).lower() or "starred"
    sup = [x for x in lq.get("supplementary") or [] if (isinstance(x, dict) and x.get("table")) or _txt(x)] \
        if isinstance(lq.get("supplementary"), list) else []
    if kind in ("starred", "short_notice") and not sup:
        W.append("lq.supplementary: none — a starred / short-notice answer is followed by the पुरवणी टिप्पणी "
                 "(GADT 13.9; MMOP 16.3(3) 'Notes for supplementary questions')")
    if kind == "unstarred" and sup:
        W.append("lq.supplementary: given for an unstarred question — GADT 13.5: 'पूरक टिप्पणीचीही जरुरी नसते'")
    for i, pt in enumerate(lq.get("parts") or []):
        if not isinstance(pt, dict):
            continue
        q, a = _txt(pt.get("q")), _txt(pt.get("a"))
        if q and a and TRUE_Q.search(q) and not ANS_OPEN.match(a):
            W.append(f"lq.parts[{i}].a: the sub-question asks 'हे खरे आहे काय' — open the answer with 'होय, हे खरे "
                     "आहे.' / 'हे खरे नाही.' / 'हे अंशत: खरे आहे.' / 'प्रश्न उद्भवत नाही.' (the Legislature's printed forms)")
        if a and LATIN.search(lint_spec.unquoted(re.sub(r"\([^)]*\)", "", a))):
            W.append(f"lq.parts[{i}].a: Latin letters outside quotes / brackets — the answer is in Marathi")
    return W


def main(argv):
    if len(argv) != 2:
        print(__doc__); return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            spec = json.load(f)
    except Exception as e:
        print(f"{argv[1]}: JSON — {e}"); return 1
    if not isinstance(spec, dict) or "lq" not in spec:
        print(f"{argv[1]}: no 'lq' block"); return 1
    probs = lint_lq(spec)
    for p in probs:
        print(p)
    for w in warnings_lq(spec):
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
