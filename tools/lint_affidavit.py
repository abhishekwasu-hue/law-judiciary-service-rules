#!/usr/bin/env python3
"""lint_affidavit.py <spec.json>
Pre-build lint of the optional "affidavit" block of spec.json (affidavit in reply; tools/build_affidavit.py).
Prints one line per problem "affidavit.<path>: <rule> — <detail>"; "LINT OK" and exit 0 when there is none, exit 1
otherwise. Warnings are printed as "WARN affidavit.<path>: <message>" and never change the exit code.
Windows: `py tools/lint_affidavit.py ...`; runner: `python3 tools/lint_affidavit.py ...`.

Basis (docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md part A): Bombay High Court Appellate Side Rules, 1960, Chapter III Rules 1,
2, 4, 5, 10 (entitling, parties, numbered paragraphs, knowledge / belief, solemn declaration); Chapter XVII Rules 11-12
(answer to rule nisi = affidavit in reply); Rules for the Conduct of the Legal Affairs of Government, 1984, Rule 32
(reply "to each paragraph") and Rule 58 Note (ii) (no cryptic answers); INSTRUCTIONS §3.1 (English), §4.27 (no warning /
AI words), §4.30 (respectful language).

Errors
  - "affidavit" not an object; bench not one of bombay / nagpur / aurangabad / goa / kolhapur (unless "court" is
    given); case empty; respondents not a non-empty list of strings; petitioners / petitioner missing; on_behalf_of
    empty; deponent not an object; paras not a list of strings; paper_book not true/false
  - parawise reply: "reply" not a list, or empty while the spec has no "parawise"."paras" to take it from; a reply item
    neither {"section": "<text>"} nor {"para", "reply"} with both non-empty
  - cryptic reply ("denied", "not admitted", … alone — Rule 58 Note (ii); lint_parawise.cryptic)
  - internal ids / repo paths; C27 draft words (package / warning / working / AI words, "—", "→", web addresses)
Warnings
  - Devanagari outside “…” quotes (the affidavit is in English; Marathi GR text stays in quotes, §4.30 (4))
  - no reply row on the prayer clauses (Rule 58(3): every point of the petition)
  - a reply shorter than 8 words (Rule 58 Note (ii)); §4.30 contempt-prone wording (lint_parawise.contempt_hits)
Audit 05.11.2026: WARN Q-F12 — affidavit.on_behalf_of names the High Court Registry (Registrar / High Court / महाप्रबंधक /
प्रबंधक): the joint affidavit is on behalf of the State respondents only (INSTRUCTIONS §4.35; lint_spec.registry_hits).
S-F3: --details FILE (or env CASE_DETAILS_FILE) — full lines to FILE, quoted segments redacted on stdout.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint_spec  # noqa: E402
import lint_parawise  # noqa: E402

BENCHES = ("bombay", "nagpur", "aurangabad", "goa", "kolhapur")
DEV_RE = re.compile(r"[ऀ-ॿ]")
TEXT_KEYS = ("court", "case", "petitioner", "on_behalf_of", "title", "authority", "reply_heading", "prayer",
             "knowledge_paras", "sources", "belief_reasons", "place", "day", "month_year", "identified_by",
             "advocate_for", "bench")


def _txt(x):
    return x.strip() if isinstance(x, str) else ""


def reply_source(spec):
    """(path, items) of the parawise reply: the block's own "reply", else the spec's "parawise"."paras"."""
    af = spec["affidavit"]
    if isinstance(af.get("reply"), list) and af["reply"]:
        return "affidavit.reply", af["reply"], "reply"
    pw = spec.get("parawise") if isinstance(spec.get("parawise"), dict) else {}
    return "parawise.paras", (pw.get("paras") if isinstance(pw.get("paras"), list) else []), "remarks"


def lint_affidavit(spec):
    """Errors for spec["affidavit"]; [] when clean or absent."""
    if not isinstance(spec, dict) or "affidavit" not in spec:
        return []
    af = spec["affidavit"]
    if not isinstance(af, dict):
        return ["affidavit: structure — must be an object"]
    P = []
    for k in TEXT_KEYS:
        if k in af and not isinstance(af[k], str):
            P.append(f"affidavit.{k}: structure — must be a string")
    b = _txt(af.get("bench")).lower()
    if b and b not in BENCHES and not _txt(af.get("court")):
        P.append(f"affidavit.bench: structure — one of {', '.join(BENCHES)} (Appellate Side Rules Ch. III Rule 1), "
                 f"or give \"court\": '{af.get('bench')}'")
    if not _txt(af.get("case")):
        P.append("affidavit.case: required field — e.g. \"WRIT PETITION NO. ____ OF 2026\" (Ch. III Rule 2)")
    pets = af.get("petitioners")
    if pets is not None and not (isinstance(pets, list) and pets and all(_txt(x) for x in pets)):
        P.append("affidavit.petitioners: structure — non-empty list of names and descriptions (Ch. III Rule 2)")
    if pets is None and not _txt(af.get("petitioner")):
        P.append("affidavit.petitioners: required field — names and descriptions of the petitioner(s) (Ch. III Rule 2)")
    rs = af.get("respondents")
    if not isinstance(rs, list) or not rs or not all(_txt(r) for r in rs):
        P.append("affidavit.respondents: required field — non-empty list of names and descriptions (Ch. III Rule 2)")
    if not _txt(af.get("on_behalf_of")):
        P.append("affidavit.on_behalf_of: required field — e.g. \"Respondent Nos. 1 and 2\"")
    if "deponent" in af and not isinstance(af["deponent"], dict):
        P.append("affidavit.deponent: structure — {name, age?, designation, office?}")
    if "paras" in af and not (isinstance(af["paras"], list) and all(isinstance(x, str) for x in af["paras"])):
        P.append("affidavit.paras: structure — list of strings (numbered paragraphs, Ch. III Rule 4)")
    if "paper_book" in af and not isinstance(af["paper_book"], bool):
        P.append("affidavit.paper_book: structure — true / false")
    if "reply" in af and not isinstance(af["reply"], list):
        P.append("affidavit.reply: structure — list of {para, reply} / {\"section\": \"Grounds\"}")
    path, items, rk = reply_source(spec)
    if not items:
        P.append("affidavit.reply: required field — the parawise reply (Rule 32: reply to each paragraph); give "
                 "\"reply\" or a \"parawise\" block whose paras are used")
    for i, it in enumerate(items):
        ip = f"{path}[{i}]"
        if not isinstance(it, dict):
            P.append(f"{ip}: structure — must be an object {{para, {rk}}} or {{\"section\": …}}"); continue
        if "section" in it:
            if not _txt(it.get("section")) or set(it) - {"section"}:
                P.append(f"{ip}: structure — a separator row is {{\"section\": \"Grounds\"}} only")
            continue
        for k in ("para", rk):
            if not _txt(it.get(k)):
                P.append(f"{ip}.{k}: required field — '{k}' missing or empty")
        t = _txt(it.get(rk))
        if t and lint_parawise.cryptic(t):
            P.append(f"{ip}.{rk}: cryptic reply '{t}' — Rule 58 Note (ii): give the factual position with rule/GR "
                     "references")
    for p, t in lint_spec.strings(af, "affidavit"):
        for x in lint_spec.id_hits(t): P.append(f"{p}: internal id — '{x}'")
        for x in lint_spec.repo_hits(t): P.append(f"{p}: repo path/word — '{x}'")
        for w in lint_spec.draft_word_hits(t):
            P.append(f"{p}: draft word — '{w}' — no package / warning / working / AI word in the draft (C27)")
    return P


def warnings_affidavit(spec):
    """WARN-level findings for spec["affidavit"]; never errors."""
    if not isinstance(spec, dict) or not isinstance(spec.get("affidavit"), dict):
        return []
    af = spec["affidavit"]
    W = []
    for p, t in lint_spec.strings(af, "affidavit"):
        if DEV_RE.search(lint_spec.unquoted(t)):
            W.append(f"{p}: Devanagari outside quotes — the affidavit is in English (INSTRUCTIONS §3.1); put Marathi "
                     "GR text / names in “…”")
    path, items, rk = reply_source(spec)
    rows = [(i, it) for i, it in enumerate(items) if isinstance(it, dict) and "section" not in it]
    for i, it in rows:
        t = _txt(it.get(rk))
        if t and not lint_parawise.cryptic(t) and len(t.split()) < lint_parawise.MIN_WORDS:
            W.append(f"{path}[{i}].{rk}: short reply ({len(t.split())} words) — Rule 58 Note (ii): factual position")
        for phrase, fix in lint_parawise.contempt_hits(t):
            W.append(f"{path}[{i}].{rk}: contempt-prone wording '{phrase}' — use respectful language toward the Court "
                     f"(§4.30), e.g. {fix}")
    if rows and not any(re.search(r"\bprayer", _txt(it.get("para")), re.I) for _, it in rows):
        W.append(f"{path}: no 'Prayer' row — reply to the prayer clauses too (Rule 58(3))")
    for k in ("prayer", "authority"):
        for phrase, fix in lint_parawise.contempt_hits(_txt(af.get(k))):
            W.append(f"affidavit.{k}: contempt-prone wording '{phrase}' — e.g. {fix}")
    W += lint_parawise.registry_warnings(af, "affidavit")   # §4.35 (audit 05.11.2026 Q-F12)
    return W


def main(argv):
    argv = list(argv)
    lint_spec.set_details(lint_spec.details_arg(argv), "lint_affidavit " + " ".join(argv[1:]))   # audit S-F3
    if len(argv) != 2:
        print(__doc__); return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            spec = json.load(f)
    except Exception as e:
        print(f"{argv[1]}: JSON — {e}"); return 1
    if not isinstance(spec, dict) or "affidavit" not in spec:
        print(f"{argv[1]}: no 'affidavit' block"); return 1
    probs = lint_affidavit(spec)
    for p in probs:
        lint_spec.out(p)
    for w in warnings_affidavit(spec):
        lint_spec.out("WARN " + w)
    if not probs:
        print("LINT OK")
    return 1 if probs else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
