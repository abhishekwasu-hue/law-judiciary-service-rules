#!/usr/bin/env python3
"""lint_order.py <spec.json>
Pre-build lint of spec["order"] (format: tools/build_order.py docstring; layout decisions B1-B7 in
docs/COURT_AND_ORDERS_RESEARCH.md). Prints one line per problem "<JSON path>: <rule> — <detail>"; "LINT OK" and exit 0
when there is none, exit 1 otherwise. Warnings are printed "WARN <JSON path>: <message>" and never change the exit code.
Functions: lint_order(spec) -> [problems], lint_order_warnings(spec) -> [warnings].

Rules
  - order.type one of gr / corrigendum / circular / memo / notification
  - required: ref_no, date, copies (all); subject (all but notification); read + preamble + operative (gr);
    read + corrections [{read, instead_of, read_as}] (corrigendum); operative (circular, memo, notification);
    addressee (memo); english {ref_no, operative, copies} (notification)
  - ref_no "संकिर्ण-<year>/<file no or ____>/प्र.क्र.<n or ____>/का.6" ("संकीर्ण-" also accepted: the file no. as the
    निर्देशपत्र writes it — audit A1, 02.11.2026); date "__.__.2026" / "DD.MM.YYYY" /
    "____ <month>, 2026" / "DD <month>, YYYY"
  - website line (decision B5) not switched off for gr / corrigendum / circular
  - the tool adds the Governor line ("महाराष्ट्राचे राज्यपाल यांच्या आदेशानुसार व नावाने,"), the website line and the
    body headings: operative / preamble must not contain them
  - copies: last item contains "निवड नस्ती"
  - memo: operative[0] in the specimen form ("… असे कळविण्याचा मला आदेश आहे." or "… यांना कळविण्यात येते की, …")
  - notification: operative[0] cites the enabling provision ("…कलम … अन्वये / द्वारे प्रदान करण्यात आलेल्या
    अधिकारांचा वापर करून …" — GADT 12.17); english.operative[0] "In exercise of the powers conferred by …"
  - signer {name, designation} strings when given
  - language (own Marathi text outside “…” quotes — subject, read, preamble, operative, concurrence, corrections.read,
    copies, addressee): tools/lint_spec.py lang_hits (§4.19), style_hits (§4.18/§4.24/§4.25), ma_hits (§4.23 — not on
    copies / addressee: address part; the same "मा." / "ध्द" exemptions as lint_spec: one "मा." before a title phrase,
    "निवृत्त न्यायमूर्ती", office designations "<पद>, उच्च न्यायालय", person names after श्री./श्रीमती/कै./डॉ.). corrections.instead_of / read_as are verbatim text of the original order: not
    checked. The english block is not checked for Marathi rules.
  - C27 (02.11.2026): lint_spec.draft_word_hits on the own text and the english block — no "पॅकेज", no warning /
    working word, no AI / automation word (outside “…” quotes)
WARN: lint_spec.warn_hits on the same own text; gr / memo without a concurrence para (specimen para 3: Finance
concurrence or delegated powers)."""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint_spec  # noqa: E402  (reused, not edited)

TYPES = ("gr", "corrigendum", "circular", "memo", "notification")
REF_RE = re.compile(r"^(?:संकिर्ण|संकीर्ण)-[0-9]{4}/(?:[0-9]+|_{2,})/प्र\.क्र\.(?:[0-9]+|_{2,})/का\.6$")
DATE_RE = re.compile(r"^(?:[0-9_]{2}\.[0-9_]{2}\.[0-9]{4}|(?:[0-9]{1,2}|_{2,})\s+[ऀ-ॿ]+,\s*[0-9]{4})$")
GOV = "राज्यपाल यांच्या आदेशानुसार"
WEB = "www.maharashtra.gov.in"
HEADS = ("प्रस्तावना :-", "शासन निर्णय :-", "शासन शुद्धिपत्रक :-", "परिपत्रक :-", "ज्ञापन :-")
SELECT = "निवड नस्ती"
MEMO_RE = re.compile(r"कळविण्याचा\s+मला\s+आदेश\s+आहे|कळविण्यात\s+येते\s+की")
ENABLE_RE = re.compile(r"कलम.*(?:अन्वये|द्वारे)\s+प्रदान\s+करण्यात\s+आलेल्या\s+अधिकारा(?:ंचा|चा)\s+वापर\s+करून", re.S)
ENABLE_EN = re.compile(r"In exercise of the powers conferred by", re.I)


def _s(x):
    return isinstance(x, str) and x.strip() != ""


def _texts(items, path):
    """(path, text) for strings in a list of str / {"table"} / {"sub"} items."""
    for i, it in enumerate(items or []):
        if isinstance(it, str):
            yield f"{path}[{i}]", it
        elif isinstance(it, dict):
            for k in ("table", "sub"):
                if k in it:
                    yield from lint_spec.strings(it[k], f"{path}[{i}].{k}")


def own_text(o):
    """(path, text, check_ma) — the Section's own Marathi text of the order."""
    out = []
    if _s(o.get("subject")): out.append(("order.subject", o["subject"], True))
    for k in ("read", "preamble", "operative"):
        out += [(p, t, True) for p, t in _texts(o.get(k), f"order.{k}")]
    if _s(o.get("concurrence")): out.append(("order.concurrence", o["concurrence"], True))
    for i, c in enumerate(o.get("corrections") or []):
        if isinstance(c, dict) and _s(c.get("read")):
            out.append((f"order.corrections[{i}].read", c["read"], True))
    out += [(f"order.copies[{i}]", c, False) for i, c in enumerate(o.get("copies") or []) if isinstance(c, str)]
    if _s(o.get("addressee")): out.append(("order.addressee", o["addressee"], False))
    return out


def lint_order(spec):
    P = []
    o = spec.get("order") if isinstance(spec, dict) else None
    if not isinstance(o, dict):
        return ["order: structure — spec has no 'order' object"]
    t = o.get("type")
    if t not in TYPES:
        return [f"order.type: type — '{t}' not one of {list(TYPES)}"]

    def need(key, kind="str"):
        v = o.get(key)
        ok = _s(v) if kind == "str" else (isinstance(v, list) and any(_s(x) or isinstance(x, dict) for x in v))
        if not ok:
            P.append(f"order.{key}: required for {t} — missing or empty")
        return ok

    if need("ref_no") and not REF_RE.match(o["ref_no"].strip()):
        P.append(f"order.ref_no: क्रमांक — '{o['ref_no']}' not 'संकिर्ण-<year>/<file no or ____>/प्र.क्र.<n or ____>/का.6'")
    if need("date") and not DATE_RE.match(o["date"].strip()):
        P.append(f"order.date: दिनांक — '{o['date']}' not '__.__.2026' / '____ <month>, 2026'")
    if t != "notification": need("subject")
    need("copies", "list")
    if t == "gr":
        need("read", "list"); need("preamble", "list"); need("operative", "list")
    elif t == "corrigendum":
        need("read", "list")
        cs = o.get("corrections")
        if not isinstance(cs, list) or not cs:
            P.append("order.corrections: required for corrigendum — missing or empty")
        else:
            for i, c in enumerate(cs):
                for k in ("read", "instead_of", "read_as"):
                    if not (isinstance(c, dict) and _s(c.get(k))):
                        P.append(f"order.corrections[{i}].{k}: required — missing or empty")
                    elif k != "read" and re.search(r"[“”]", c[k]):
                        P.append(f"order.corrections[{i}].{k}: quotes — the tool adds “…”; give the bare text")
    else:
        need("operative", "list")
    if t in ("gr", "corrigendum", "circular") and o.get("website_line") is False:
        P.append(f"order.website_line: website line — required for {t} (decision B5)")
    sg = o.get("signer")
    if sg is not None and not (isinstance(sg, dict) and all(_s(sg.get(k)) for k in ("name", "designation"))):
        P.append("order.signer: signer — {name, designation} strings")
    copies = [c for c in (o.get("copies") or []) if _s(c)]
    if copies and SELECT not in copies[-1]:
        P.append(f"order.copies: प्रत list — last item must be '{SELECT} (कार्यासन-6)'")
    for path, x in list(_texts(o.get("operative"), "order.operative")) + list(_texts(o.get("preamble"), "order.preamble")):
        if GOV in x:
            P.append(f"{path}: Governor line — added by the tool; remove it")
        if WEB in x:
            P.append(f"{path}: website line — added by the tool (website_line); remove it")
        if any(h in x for h in HEADS):
            P.append(f"{path}: heading — body headings are added by the tool")
    ops = o.get("operative") or []
    first = ops[0] if ops and isinstance(ops[0], str) else ""
    if t == "memo":
        need("addressee")
        if ops and not MEMO_RE.search(first):
            P.append("order.operative[0]: ज्ञापन form — '… असे कळविण्याचा मला आदेश आहे.' or '… यांना कळविण्यात येते की, …' (NPM परि.-23)")
    if t == "notification":
        if ops and not ENABLE_RE.search(first):
            P.append("order.operative[0]: enabling provision — '…कलम … अन्वये प्रदान करण्यात आलेल्या अधिकारांचा वापर करून …' (GADT 12.17)")
        e = o.get("english")
        if not isinstance(e, dict):
            P.append("order.english: required for notification — English version (decision B6)")
        else:
            if not _s(e.get("ref_no")): P.append("order.english.ref_no: required — missing or empty")
            eops = e.get("operative") or []
            if not eops or not isinstance(eops[0], str):
                P.append("order.english.operative: required — missing or empty")
            elif not ENABLE_EN.search(eops[0]):
                P.append("order.english.operative[0]: enabling provision — 'In exercise of the powers conferred by …'")
            ec = [c for c in (e.get("copies") or []) if _s(c)]
            if not ec: P.append("order.english.copies: required — missing or empty")
            for path, x in _texts(eops, "order.english.operative"):
                if "Governor of Maharashtra" in x:
                    P.append(f"{path}: Governor line — added by the tool; remove it")
    for path, x, ma in own_text(o):
        for m in lint_spec.id_hits(x): P.append(f"{path}: internal id — '{m}'")
        for m in lint_spec.repo_hits(x): P.append(f"{path}: repo path — '{m}'")
        P += [f"{path}: {m}" for m in lint_spec.lang_hits(x)]
        P += [f"{path}: {m}" for m in lint_spec.style_hits(x)]
        if ma:
            P += [f"{path}: {m}" for m in lint_spec.ma_hits(x)]
    # C27 (02.11.2026): no warning / working / package / AI word in the draft (own Marathi text and the English block)
    eng = o.get("english") if isinstance(o.get("english"), dict) else {}
    for path, x in [(p_, x_) for p_, x_, _ in own_text(o)] + list(lint_spec.strings(eng, "order.english")):
        P += [f"{path}: draft word — '{w}' — {lint_spec.DRAFT_MSG}" for w in lint_spec.draft_word_hits(x)]
    return P


def lint_order_warnings(spec):
    o = spec.get("order") if isinstance(spec, dict) else None
    if not isinstance(o, dict):
        return []
    W = [f"{path}: {m}" for path, x, _ in own_text(o) for m in lint_spec.warn_hits(x)]
    if o.get("type") in ("gr", "memo") and not _s(o.get("concurrence")):
        W.append("order.concurrence: no concurrence para — specimen para 3 (Finance concurrence or delegated powers; NPM परि.-23/25)")
    return W


def main(argv):
    if len(argv) != 2:
        print(__doc__); return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            spec = json.load(f)
    except Exception as e:
        print(f"{argv[1]}: JSON — {e}"); return 1
    probs = lint_order(spec)
    for p in probs: print(p)
    for w in lint_order_warnings(spec): print("WARN " + w)
    if not probs: print("LINT OK")
    return 1 if probs else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
