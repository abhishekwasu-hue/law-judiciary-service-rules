#!/usr/bin/env python3
"""desk.py — desk profiles (C30 part B, 03.11.2026: one office's note / letter / order values per file).

Profiles: tools/desks/<id>.json. "law-desk6" (default) = the Law & Judiciary Department, Desk-6 values used until now;
"hte-mashi5" = Higher & Technical Education Department, desk मशि-5 (model note of Abhi, 03.11.2026). A spec picks one with
the key "desk" (absent / null / "" = law-desk6). The owner adds a desk by adding a json file of the same shape.

Fields: id, label (Marathi), department, desk, note_header, signers[] (the note's signer chain, in order),
finance_signer (added last only when the file goes to Finance, INSTRUCTIONS §4.6),
letter {office[] (letterhead lines after "महाराष्ट्र शासन"), phone, email, ref_pattern (regex, full match), ref_hint,
        sign_name, sign_post, copy_file},
order {department, office, ref_pattern, ref_hint, copy_file, signer {name, designation},
       signer_notification {name, designation}, notification_department,
       english {office[], department, signer {name, designation}}}.
A value that is not known is stored as "" / null / [] and printed as a blank to fill by hand (Abhi 03.11.2026: "je mahiti
nahi ti blank sodaychi"): phone / e-mail / designation / English lines -> "____", a signature name -> "(          )".

CLI: python3 tools/desk.py            -> list the profiles (id, label)
     python3 tools/desk.py <id>       -> print the profile (validated)"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESK_DIR = os.path.join(HERE, "desks")
DEFAULT_DESK = "law-desk6"
BLANK = "____"
BLANK_NAME = "(          )"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
_CACHE = {}


def desk_ids():
    """ids of every profile in tools/desks/ (sorted)."""
    try:
        return sorted(f[:-5] for f in os.listdir(DESK_DIR) if f.endswith(".json") and ID_RE.match(f[:-5]))
    except OSError:
        return []


def profile_problems(p):
    """shape problems of one profile ([] = ok)."""
    P = []
    if not isinstance(p, dict):
        return ["profile: not an object"]
    for k in ("id", "label", "department", "desk", "note_header", "finance_signer"):
        if not isinstance(p.get(k), str) or not p[k].strip():
            P.append(f"{k}: required text")
    sg = p.get("signers")
    if not isinstance(sg, list) or not sg or not all(isinstance(x, str) and x.strip() for x in sg):
        P.append("signers: required list of text")
    L = p.get("letter")
    if not isinstance(L, dict):
        P.append("letter: required object")
    else:
        if not isinstance(L.get("office"), list) or not L["office"]:
            P.append("letter.office: required list of letterhead lines")
        for k in ("ref_pattern", "ref_hint", "sign_post", "copy_file"):
            if not isinstance(L.get(k), str) or not L[k].strip():
                P.append(f"letter.{k}: required text")
        for k in ("phone", "email", "sign_name"):
            if L.get(k) is not None and not isinstance(L.get(k), str):
                P.append(f"letter.{k}: text or null")
    O = p.get("order")
    if not isinstance(O, dict):
        P.append("order: required object")
    else:
        for k in ("department", "office", "ref_pattern", "ref_hint", "copy_file"):
            if not isinstance(O.get(k), str) or not O[k].strip():
                P.append(f"order.{k}: required text")
    for path, rx in (("letter.ref_pattern", (L or {}).get("ref_pattern") if isinstance(L, dict) else None),
                     ("order.ref_pattern", (O or {}).get("ref_pattern") if isinstance(O, dict) else None)):
        if isinstance(rx, str):
            try:
                re.compile(rx)
            except re.error as e:
                P.append(f"{path}: bad regex ({e})")
    return P


def load_desk(desk_id=None):
    """The profile dict of desk_id (None / "" = DEFAULT_DESK). ValueError for an unknown id or a broken profile."""
    did = (desk_id or DEFAULT_DESK).strip() if isinstance(desk_id, str) or desk_id is None else desk_id
    if not isinstance(did, str) or not ID_RE.match(did):
        raise ValueError(f"desk '{desk_id}': not a desk id (tools/desks/: {', '.join(desk_ids())})")
    if did in _CACHE:
        return _CACHE[did]
    path = os.path.join(DESK_DIR, did + ".json")
    if not os.path.exists(path):
        raise ValueError(f"desk '{did}': no profile tools/desks/{did}.json (known: {', '.join(desk_ids())})")
    with open(path, encoding="utf-8-sig") as f:
        p = json.load(f)
    probs = profile_problems(p)
    if p.get("id") != did:
        probs.append(f"id '{p.get('id')}' != file name '{did}'")
    if probs:
        raise ValueError(f"desk '{did}': profile — " + "; ".join(probs))
    _CACHE[did] = p
    return p


def desk_id_of(spec):
    """the desk id a spec names (key "desk"; absent / null / "" -> DEFAULT_DESK)."""
    d = spec.get("desk") if isinstance(spec, dict) else None
    return d.strip() if isinstance(d, str) and d.strip() else DEFAULT_DESK


def desk_of(spec):
    """the profile of a spec (key "desk")."""
    return load_desk(desk_id_of(spec))


def blank(v):
    """a known value as is; unknown ("" / None) -> "____"."""
    return v.strip() if isinstance(v, str) and v.strip() else BLANK


def sign_name(v):
    """a signature name; unknown -> "(          )" (the model note's blank)."""
    return v.strip() if isinstance(v, str) and v.strip() else BLANK_NAME


def letter_ref_re(p):
    return re.compile(p["letter"]["ref_pattern"])


def order_ref_re(p):
    return re.compile(p["order"]["ref_pattern"])


def contact_line(p):
    """the letterhead phone / e-mail line (unknown values -> "____")."""
    L = p["letter"]
    return f"दूरध्वनी क्र. :- {blank(L.get('phone'))}\t\t\t\t   Email ID :- {blank(L.get('email'))}"


def letter_end_lines(p):
    """the letter's closing lines that verify_outputs checks (whitespace as printed; compare after ns())."""
    L = p["letter"]
    return [sign_name(L.get("sign_name")), blank(L.get("sign_post")), "प्रत : " + L["copy_file"]]


def detect_desk(texts):
    """the desk id whose note_header is the first non-blank line of texts (a built Note_and_Letter), else None."""
    first = next((re.sub(r"\s+", " ", t).strip() for t in texts if t and t.strip()), "")
    for did in desk_ids():
        try:
            p = load_desk(did)
        except ValueError:
            continue
        if re.sub(r"\s+", " ", p["note_header"]).strip() == first:
            return did
    return None


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) > 1:
        print(json.dumps(load_desk(sys.argv[1]), ensure_ascii=False, indent=1))
    else:
        for i in desk_ids():
            print(i, "\t", load_desk(i)["label"])
