#!/usr/bin/env python3
"""work_type.py — work categories (C33, Abhi 04.11.2026: "इतर कामकाजाचे नमुने नव्याने देण्यात येईल फ्रेमवर्क तयार करून ठेवा").

Same pattern as tools/desk.py: one file per category, tools/work_types/<id>.json; adding a category = adding files, no code
change (see docs/WORK_TYPES.md). A case names one with cases.work_type -> case.json "work_type" (absent / null / "" = service).

Fields: id, label (Marathi), status ("ready" | "rules_pending"), default_drafts [..], allowed_drafts [..] (draft keys of
INSTRUCTIONS §4.28 = DRAFT_KEYS), rules_file (tools/work_rules/<id>.md), samples_dir (samples/work/<id>/),
required_samples [Marathi list of the samples the owner should give], pending_warning (Study / status warning used while
status is rules_pending; "" allowed for ready types).

prompt_block(id): text for the engine prompt — a ready type gives its rules file; a rules_pending type gives the
pending_warning and the instruction to use the general service rules (no invented rules, OWNER_RULES A.3 / A.5).

CLI: python3 tools/work_type.py list         -> id, status, label
     python3 tools/work_type.py show <id>    -> the validated json + prompt block
     python3 tools/work_type.py prompt [<id>] -> only the prompt block (no id / unknown id -> service)
     python3 tools/work_type.py check        -> validate every json and its files (exit 1 on a problem)"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TYPE_DIR = os.path.join(HERE, "work_types")
DEFAULT_WORK_TYPE = "service"
DRAFT_KEYS = ("letter", "reminder", "gr", "corrigendum", "circular", "memo", "notification", "parawise")  # engine_supabase.py
STATUSES = ("ready", "rules_pending")
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,40}$")


def type_ids():
    """ids of every category file in tools/work_types/ (sorted)."""
    try:
        return sorted(f[:-5] for f in os.listdir(TYPE_DIR) if f.endswith(".json") and ID_RE.match(f[:-5]))
    except OSError:
        return []


def _path(rel):
    """repo-relative path; outside the repo (the runner's root-owned snapshot /opt/engine-tools + /opt/engine-samples)
    "tools/…" resolves next to this file and "samples/…" in ../engine-samples."""
    p = os.path.join(ROOT, rel.rstrip("/"))
    if os.path.exists(p):
        return p
    # snapshot layout of process-proposal.yml: tools/ -> /opt/engine-tools, samples/ -> /opt/engine-samples
    for pre, base in (("tools/", HERE), ("samples/", os.path.join(os.path.dirname(HERE), "engine-samples"))):
        if rel.startswith(pre):
            q = os.path.join(base, rel[len(pre):].rstrip("/"))
            if os.path.exists(q):
                return q
    return p


def problems(t, check_files=True):
    """shape problems of one category ([] = ok)."""
    if not isinstance(t, dict):
        return ["not an object"]
    P = []
    for k in ("id", "label", "rules_file", "samples_dir"):
        if not isinstance(t.get(k), str) or not t[k].strip():
            P.append(f"{k}: required text")
    if t.get("status") not in STATUSES:
        P.append(f"status: one of {', '.join(STATUSES)}")
    for k in ("default_drafts", "allowed_drafts"):
        v = t.get(k)
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            P.append(f"{k}: required list of draft keys")
        else:
            bad = [x for x in v if x not in DRAFT_KEYS]
            if bad:
                P.append(f"{k}: unknown draft keys {bad} (INSTRUCTIONS §4.28: {', '.join(DRAFT_KEYS)})")
    if isinstance(t.get("default_drafts"), list) and isinstance(t.get("allowed_drafts"), list):
        extra = [x for x in t["default_drafts"] if x not in t["allowed_drafts"]]
        if extra:
            P.append(f"default_drafts not in allowed_drafts: {extra}")
    rs = t.get("required_samples")
    if not isinstance(rs, list) or not all(isinstance(x, str) and x.strip() for x in rs):
        P.append("required_samples: list of text")
    pw = t.get("pending_warning")
    if not isinstance(pw, str):
        P.append("pending_warning: text")
    elif t.get("status") == "rules_pending":
        if not pw.startswith("पडताळणी अपूर्ण — "):
            P.append("pending_warning: must start with 'पडताळणी अपूर्ण — ' (INSTRUCTIONS §4.26)")
        if not rs:
            P.append("required_samples: a rules_pending type must list the samples the owner should give")
    if check_files:
        if isinstance(t.get("rules_file"), str) and t["rules_file"].strip() and not os.path.isfile(_path(t["rules_file"])):
            P.append(f"rules_file: {t['rules_file']} does not exist")
        sd = t.get("samples_dir")
        if t.get("status") == "rules_pending" and isinstance(sd, str) and sd.strip() \
                and not os.path.isfile(os.path.join(_path(sd), "README.md")):
            P.append(f"samples_dir: {sd}README.md does not exist")
    return P


def load(type_id=None):
    """the category dict of type_id (None / "" = DEFAULT_WORK_TYPE). ValueError for an unknown id or a broken file."""
    if type_id is None or (isinstance(type_id, str) and not type_id.strip()):
        tid = DEFAULT_WORK_TYPE
    else:
        tid = type_id.strip() if isinstance(type_id, str) else type_id
    if not isinstance(tid, str) or not ID_RE.match(tid):
        raise ValueError(f"work_type '{type_id}': not a work type id (known: {', '.join(type_ids())})")
    path = os.path.join(TYPE_DIR, tid + ".json")
    if not os.path.exists(path):
        raise ValueError(f"work_type '{tid}': no file tools/work_types/{tid}.json (known: {', '.join(type_ids())})")
    with open(path, encoding="utf-8-sig") as f:
        t = json.load(f)
    P = problems(t)
    if isinstance(t, dict) and t.get("id") != tid:
        P.append(f"id '{t.get('id')}' != file name '{tid}'")
    if P:
        raise ValueError(f"work_type '{tid}': " + "; ".join(P))
    return t


def list_types():
    """[{id, label, status}] of every category (sorted by id; a broken file raises ValueError)."""
    return [{k: t[k] for k in ("id", "label", "status")} for t in (load(i) for i in type_ids())]


def default_drafts(type_id=None):
    """the draft keys pre-ticked for this category, in DRAFT_KEYS order."""
    d = load(type_id)["default_drafts"]
    return [k for k in DRAFT_KEYS if k in d]


def prompt_block(type_id=None):
    """the text the engine appends to its prompt for this category."""
    t = load(type_id)
    head = f"## Work type: {t['id']} ({t['label']}), status {t['status']}\n"
    if t["status"] == "ready":
        with open(_path(t["rules_file"]), encoding="utf-8") as f:
            return head + f.read().strip() + "\n"
    service = load(DEFAULT_WORK_TYPE)
    return (head
            + f"This category has no rules or samples yet ({t['samples_dir']} pending: {'; '.join(t['required_samples'])}).\n"
            + "Use the general service rules below; invent no category-specific rule (OWNER_RULES A.3 / A.5).\n"
            + "Add this exact line to status.json warnings and to the Study (end of part 7):\n"
            + t["pending_warning"] + "\n\n"
            + open(_path(service["rules_file"]), encoding="utf-8").read().strip() + "\n")


def check():
    """problems of every category file ([] = all ok)."""
    P = []
    ids = type_ids()
    if DEFAULT_WORK_TYPE not in ids:
        P.append(f"default work type '{DEFAULT_WORK_TYPE}' missing")
    for i in ids:
        try:
            load(i)
        except (ValueError, json.JSONDecodeError) as e:
            P.append(str(e))
    return P


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cmd = argv[1] if len(argv) > 1 else "list"
    if cmd == "list":
        for t in list_types():
            print(t["id"], "\t", t["status"], "\t", t["label"])
        return 0
    if cmd == "show" and len(argv) > 2:
        print(json.dumps(load(argv[2]), ensure_ascii=False, indent=1))
        print("\n--- prompt_block ---\n" + prompt_block(argv[2]))
        return 0
    if cmd == "prompt":
        tid = argv[2] if len(argv) > 2 else None
        if tid not in type_ids():
            tid = DEFAULT_WORK_TYPE
        print(prompt_block(tid), end="")
        return 0
    if cmd == "check":
        P = check()
        for p in P:
            print("PROBLEM:", p)
        print("WORK TYPES OK" if not P else f"WORK TYPES: {len(P)} problem(s)", f"({', '.join(type_ids())})")
        return 1 if P else 0
    print(__doc__.split("CLI:")[1])
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
