#!/usr/bin/env python3
"""edit_drafts.py — सुधारणा-चॅट (draft edit) job of app B (docs/DRAFT_EDIT_DESIGN.md points 4-5 + Addendum A, 04.11.2026).
Run by .github/workflows/edit-drafts.yml (repository_dispatch `edit_drafts`). Env as tools/engine_supabase.py: CASE_ID,
RUN_ID, SUPABASE_URL / SUPABASE_SERVICE_KEY / ANTHROPIC_API_KEY (env or the runner's ENGINE_SECRETS file), MODEL_EDIT
(default claude-sonnet-5-5), RUN_TOKEN + WORKER (progress through POST /api/engine/step; without them runs.step is
patched directly). Usage: python3 tools/edit_drafts.py [--work <dir>]   (default: a new temp dir).

What it does (one edit run = runs row kind 'edit', edit_target, edit_message, edit_attachments):
  1. Downloads the newest `spec` files (case_files kind spec: spec.json, enclosures.json), the newest output of each kind
     and the case row. No spec.json -> run failed "सुधारणा-फाइल नाही".
  2. Package (target `package`, or attachments / GR सांकेतांक in the message): attachments (runs.edit_attachments =
     case_files ids of this case; PDF as is, JPG/PNG/TIF… -> PDF pages with pymupdf, Word only when LibreOffice exists
     on the runner, else that file is left out with "Word फाइल … PDF करून जोडावी, ही विनंती") and GR codes (16-18 digits found by
     regex in the message, never by the model; pdf/gr/<code>.pdf of the checkout, else the official URL, else the
     archive.org mirror — the same URLs as tools/gr_request.py) are APPENDED at the end of the package: tools/pkg3.py
     on the proposal (from storage) + the saved enclosures.json (old paths resolved: repo paths in the checkout,
     /tmp/case/in/<kind>/<name> -> that case_files row) + the new items. The old pages must come out identical in
     number; their annotations are copied from the old package (highlights made with tools/highlight.py stay).
     Existing पृ.N/प.वि. stay valid; only the total "पृ. i / N" changes. No enclosures.json (case run before this
     change) -> refused "जुने प्रकरण — …". Target `package` = attach only: NO model call (cost 0).
  3. Otherwise ONE Anthropic Messages API call (urllib, POST /v1/messages, anthropic-version 2023-06-01, model
     MODEL_EDIT, structured JSON output) with a short fixed system prompt, the spec part of the target only
     (TARGET_KEYS) + tiny context (C R no., subject, package pages, new page ranges + capped text of attachments) and the
     message. Reply {"ops": [{"op", "path" (JSON pointer inside the part), "value_json"}], "summary", "refuse"}.
     Every path is checked to stay inside the target's keys (apply_ops); a "refuse" -> run done, edit_result.refused,
     nothing changed (a package built in step 2 is still kept).
  4. Whole-spec lint (tools/lint_spec.py lint_spec + lint_extras, pages = package pages): only NEW errors count (an old
     spec may carry errors of rules added later), plus the quote guard (a “…” extract changed although the message does
     not name it). Errors -> ONE retry with the error list; still failing -> run failed "सुधारणा नियमांत बसली नाही — …".
  5. Rebuilds only the affected outputs (OUTPUTS: the kinds whose spec keys changed and whose output exists) with the
     existing builders (--no-lint: lint was done in 4; no LibreOffice preview), checks them (verify_checks: fonts, no
     internal ids / repo paths (HARD -> failed), पृ. within the package pages, banned / warning / AI words, metadata;
     the Note_and_Letter through tools/verify_outputs.py), uploads the new versions (same original names, never
     overwriting an older version) + the new spec.json / enclosures.json (one version for both, as engine_supabase
     upload_spec), and sets the run done: summary, cost_usd, edit_result {summary, changes [{where, before, after}],
     files [kinds], cost_usd, attached [{title, pages}], notes?, refused?}. SOFT check results -> runs.warnings.
Never writes the repo; nothing the model returns is executed."""
import collections, copy, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import engine_supabase as E  # noqa: E402 — Supabase REST / storage helpers (one copy)
import lint_spec  # noqa: E402

# ---------------------------------------------------------------- targets, outputs
# target -> the spec keys it may change (real keys of samples/specs/*.json)
TARGET_KEYS = {"note": ("note", "related"), "letter": ("letter", "letters"), "order": ("order", "orders"),
               "parawise": ("parawise",), "affidavit": ("affidavit",), "lq": ("lq",), "package": ()}
TARGET_LABEL = {"note": "टिप्पणी", "letter": "पत्र", "order": "आदेश-प्रारूप", "parawise": "परिच्छेदनिहाय उत्तर",
                "affidavit": "शपथपत्र", "lq": "विधानमंडळ उत्तर", "package": "GR सह प्रस्ताव PDF"}
# output kind -> (file suffix, builder, spec keys the builder reads)
OUTPUTS = {"note_letter": ("_Note_and_Letter.docx", "build_note_letter.py", ("note", "related", "letter", "letters")),
           "order_draft": ("_Order_Draft.docx", "build_order.py", ("order", "orders")),
           "parawise": ("_Parawise.docx", "build_parawise.py", ("parawise",)),
           # the affidavit's reply defaults to parawise.paras (tools/build_affidavit.py)
           "affidavit": ("_Affidavit.docx", "build_affidavit.py", ("affidavit", "parawise")),
           "lq_answer": ("_LQ_Answer.docx", "build_lq.py", ("lq",))}
TARGET_KIND = {"note": "note_letter", "letter": "note_letter", "order": "order_draft", "parawise": "parawise",
               "affidavit": "affidavit", "lq": "lq_answer", "package": "package_pdf"}
EXTRA_LABEL = {"order_draft": "Order_Draft", "parawise": "Parawise", "affidavit": "Affidavit", "lq_answer": "LQ_Answer"}

DEFAULT_MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
# $ per million tokens (input, output) — claude-api skill model table (cached 2026-10-06); cache write 1.25 x input
# (5-minute), cache read 0.1 x input
PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-sonnet-5": (2.0, 10.0), "claude-sonnet-4-6": (3.0, 15.0),
          "claude-opus-5-5": (4.0, 20.0), "claude-opus-5": (5.0, 25.0), "claude-opus-4-8": (5.0, 25.0),
          "claude-opus-4-7": (5.0, 25.0), "claude-haiku-5-5": (0.1, 0.5), "claude-haiku-4-5": (1.0, 5.0),
          "claude-fable-5-1": (10.0, 50.0), "claude-fable-5": (10.0, 50.0)}
# server-side refusal fallback ("default" form, beta server-side-fallback-2026-07-01): models that accept it
FALLBACK_MODELS = ("claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1")
API_URL = "https://api.anthropic.com/v1/messages"
GR_CODE_RE = re.compile(r"(?<!\d)\d{16,18}(?!\d)")   # Addendum A: 16-18 digits, from the message by regex only
GR_URLS = ("https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{c}.pdf",   # tools/gr_request.py
           "https://archive.org/download/in.gov.maharashtra.gr.{c}/{c}.pdf",
           "https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/English/{c}.pdf")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp")
OFFICE_EXT = (".docx", ".doc", ".odt", ".rtf")
MAX_ATTACH = 5
ATTACH_TEXT_CAP = 12000   # characters of the attachments' text layer given to the model
QUOTE_RE = re.compile(r"“([^”]*)”")

OUT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["ops", "summary", "refuse"],
              "properties": {
                  "ops": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False, "required": ["op", "path", "value_json"],
                      "properties": {"op": {"type": "string", "enum": ["replace", "remove", "insert"]},
                                     "path": {"type": "string"}, "value_json": {"type": "string"}}}},
                  "summary": {"type": "string"}, "refuse": {"type": "string"}}}

SYSTEM = """You edit ONE part of the JSON spec from which the Marathi government drafts (noting, letters, orders,
parawise remarks, affidavit, legislature answer) of the Law & Judiciary Department, Desk-6, Government of Maharashtra are
built. The user is the Section Officer; the message tells you exactly what to change.

Rules (binding):
1. Change ONLY what the message asks, and only inside the given part. Leave every other word, number, para and table
   exactly as it is. Several changes in one message are allowed.
2. Text inside “…” is a verbatim extract (GR, rule, judgment, letter): never change, shorten or re-type it unless the
   message names that very text. New extracts only word for word from the attachment text given to you.
3. Use only facts that are in the part, in the context or in the message. Never invent a fact, date, amount, number or
   page; an unknown value is "____". No opinion, advice or conclusion of your own.
4. Keep the official Marathi forms: short sentences, one point each, a clear subject ("… यांनी … सादर केला आहे.");
   "श्रीमती" (never "सौ."), one space after "श्री." / "श्रीमती" / "दि." / "क्र."; "मा. उच्च न्यायालय", "मा. सर्वोच्च
   न्यायालय", "मा. न्यायमूर्ती" in own text (not in addresses); ":-" (never ".:-"); "करून", "अनुसरून", "प्रारूप",
   "शुद्धिपत्रक", "द्ध" (not "ध्द"); a request in a letter ends "…उपलब्ध करून देण्यात यावी, ही विनंती."; no "तात्काळ".
5. Page references only as "पृ.N/प.वि." (N, N-M or N,M) with N inside the package pages given in the context. Never
   write "पॅकेज", "इशारा", "स्रोत", "जसाच्या तसा", "अस्पष्ट", "टीप :", "मागवावे", "TODO", "AI", "model", "—" or "→".
6. Missing information / documents only in the ONE para "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:- (1) …; (2) ….",
   items inline in that para, never a table (§4.31, 05.11.2026), just before the last ("सबब, …") para; nowhere else
   remarks like "नमूद नाही" / "उपलब्ध नाही". The last para keeps an approved form.
   No words such as "दिसून येते", "माझ्या मते", "कदाचित", "ठरवावे".
7. Note paras: items of "paras" are strings (numbered automatically 2., 3., …; "first" is para 1 — never type a para
   number) or tables {"table": [[header cells], [row cells], …], "bold_last": false}. Keep the signer chain as it is.
   Para 1 of the टिप्पणी ("first") names each covering letter by its authority, date and पृ.N/प.वि. only and never
   carries a letter number (INSTRUCTIONS §4.29(1)); the same for every letter anywhere in the टिप्पणी (§4.29(5),
   §4.30(7), 05.11.2026): when you touch a para, drop any "क्र. …" of an incoming letter and keep the date (GR, petition
   and case numbers stay; a department's U.O. reference no. "अनौपचारिक संदर्भ क्र. …" and another desk's
   reference no. stay when the record has one; never add one or a "____" for it). A petition in the टिप्पणी / letter
   is "रिट याचिका क्र. <N>/<YYYY>", without "(लॉजिंग)" (05.11.2026).
   A letter table asks only for data; documents go in a numbered list after it.

Reply strictly as JSON: {"ops": [...], "summary": "...", "refuse": ""}.
- ops are applied in order (RFC 6902 semantics). "path" is a JSON pointer inside the given part, starting with one of
  its top-level keys, e.g. "/note/paras/3", "/letter/intro", "/related/0/text/1", "/parawise/paras/5/remarks".
  "replace": the path must exist; "remove": the path must exist; "insert": into a list at an index (the item is put
  before that index) or "-" (append), or a new key of an object. "value_json" = the new value as JSON text (a JSON
  string in quotes for text, an object or list for a table / item); "" for "remove".
- In "summary" / "refuse" call the note "टिप्पणी" (never "नोंद"; owner 04.11.2026).
- "summary": ONE line in Marathi saying what was changed, e.g. "टिप्पणीच्या परि. 5 मधील दिनांक दुरुस्त करण्यात आला आहे."
- If only PART of the message is outside this edit (e.g. "apply this in all future proposals", a change in another
  draft), DO the part that is inside with ops, and put ONLY the reason for the other part in "refuse" (it is shown as a
  note; the done part is kept). Never drop a doable change because another part of the message is outside the edit.
- "refuse": "" normally. A short Marathi reason, and no ops, when the WHOLE message needs a full new study: a GR or document
  that is not given, re-reading the proposal, a new kind of draft, or a change outside this part, e.g. "हा बदल करण्यासाठी
  प्रस्तावाचे पुन्हा वाचन आवश्यक आहे. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती."
- Language of "summary" and "refuse" (the reader is a senior officer): very respectful, formal office Marathi; honorific
  plural and "आपण"; passive statements ("… करण्यात आले आहे.") and the request form ("कृपया … वापरावे, ही विनंती."); every request or suggestion to the reader MUST start with "कृपया" (owner, 04.11.2026: "कृपया हा शब्द महत्त्वाचा आहे");
  never a command ending ("करा", "वापरा", "पाठवा", "लिहा", "जोडा"), never casual words, no apology, no filler."""


SPENT = [0.0]   # $ spent on model calls in this run (stored on the run also when it fails)


class Refused(Exception):
    """The edit cannot be done without a full run (Marathi reason) — run done, edit_result.refused, nothing changed."""


class EditFail(Exception):
    """The edit run failed (Marathi reason) — run failed."""


# ---------------------------------------------------------------- JSON pointer ops (path guard)
def parse_pointer(p):
    if not isinstance(p, str) or not p.startswith("/"):
        raise ValueError(f"path '{p}' is not a JSON pointer (must start with '/')")
    return [t.replace("~1", "/").replace("~0", "~") for t in p[1:].split("/")]


def _index(lst, tok, allow_end=False):
    if allow_end and tok == "-":
        return len(lst)
    if not re.fullmatch(r"0|[1-9]\d*", tok):
        raise ValueError(f"'{tok}' is not a list index")
    i = int(tok)
    if i > len(lst) - (0 if allow_end else 1):
        raise ValueError(f"index {i} outside the list (length {len(lst)})")
    return i


def _parent(doc, toks):
    cur = doc
    for t in toks[:-1]:
        if isinstance(cur, dict):
            if t not in cur:
                raise ValueError(f"'{t}' not found")
            cur = cur[t]
        elif isinstance(cur, list):
            cur = cur[_index(cur, t)]
        else:
            raise ValueError(f"'{t}': not inside an object or list")
    return cur


def get_at(doc, toks):
    cur = doc
    for t in toks:
        if isinstance(cur, dict):
            if t not in cur:
                raise ValueError(f"'{t}' not found")
            cur = cur[t]
        elif isinstance(cur, list):
            cur = cur[_index(cur, t)]
        else:
            raise ValueError(f"'{t}': not inside an object or list")
    return cur


def check_path(part, toks):
    """path guard: the op must stay INSIDE one top-level key of the part (never the part root or a whole key)."""
    if not toks or toks[0] not in part:
        raise ValueError(f"path outside the part (allowed: {', '.join('/' + k for k in part)})")
    if len(toks) < 2:
        raise ValueError(f"'/{toks[0]}' as a whole cannot be changed — give a path inside it")
    if any(t == "" for t in toks):
        raise ValueError("empty path segment")


def apply_ops(part, ops):
    """ops on a deep copy of the part -> (new part, changes [{op, path, toks, before, after, state}]); raises
    ValueError("op N: …") on any invalid op (nothing is half-applied: the caller keeps the original)."""
    doc = copy.deepcopy(part)
    changes = []
    if not isinstance(ops, list):
        raise ValueError("ops is not a list")
    for k, op in enumerate(ops, 1):
        try:
            if not isinstance(op, dict):
                raise ValueError("not an object")
            kind, path = op.get("op"), op.get("path")
            toks = parse_pointer(path)
            check_path(part, toks)
            state = copy.deepcopy(doc)
            if kind in ("replace", "insert"):
                if "value" in op:
                    val = op["value"]
                else:
                    vj = op.get("value_json")
                    if not isinstance(vj, str) or not vj.strip():
                        raise ValueError("value_json missing")
                    val = json.loads(vj)
            par, last = _parent(doc, toks), toks[-1]
            if kind == "replace":
                if isinstance(par, dict):
                    if last not in par:
                        raise ValueError(f"'{last}' not found")
                    before = par[last]; par[last] = val
                elif isinstance(par, list):
                    i = _index(par, last); before = par[i]; par[i] = val
                else:
                    raise ValueError("parent is not an object or list")
                after = val
            elif kind == "remove":
                if isinstance(par, dict):
                    if last not in par:
                        raise ValueError(f"'{last}' not found")
                    before = par.pop(last)
                elif isinstance(par, list):
                    before = par.pop(_index(par, last))
                else:
                    raise ValueError("parent is not an object or list")
                after = None
            elif kind == "insert":
                if isinstance(par, list):
                    par.insert(_index(par, last, allow_end=True), val)
                    if last == "-":
                        toks = toks[:-1] + [str(len(par) - 1)]
                elif isinstance(par, dict):
                    if last in par:
                        raise ValueError(f"'{last}' exists — use replace")
                    par[last] = val
                else:
                    raise ValueError("parent is not an object or list")
                before, after = None, val
            else:
                raise ValueError(f"unknown op '{kind}'")
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"op {k} ({op.get('op') if isinstance(op, dict) else '?'} "
                             f"{op.get('path') if isinstance(op, dict) else ''}): {e}")
        changes.append({"op": kind, "path": path, "toks": toks, "before": before, "after": after, "state": state})
    return doc, changes


# ---------------------------------------------------------------- human-readable changes
LETTER_FIELD = {"ref_no": "क्रमांक", "date": "दिनांक", "to": "प्रति", "subject": "विषय", "refs": "संदर्भ",
                "intro": "प्रारंभ", "points": "मुद्दे", "closing": "शेवट", "enclosure": "सोबत", "copies": "प्रत",
                "salutation": "संबोधन", "body": "मजकूर", "reminder": "स्मरणपत्र", "from": "प्रेषक"}
ORDER_FIELD = {"subject": "विषय", "ref_no": "क्रमांक", "date": "दिनांक", "read": "वाचा", "preamble": "प्रस्तावना",
               "operative": "आदेश-मजकूर", "copies": "प्रत", "concurrence": "सहमती", "additions": "भर",
               "forward_to": "यांजकडे", "purpose": "प्रयोजन", "cites": "संदर्भ"}


def text_of(v, cap=2000):
    """a value as readable text (table rows "a | b", list items one per line); "" for None."""
    if v is None:
        return ""
    if isinstance(v, str):
        s = v
    elif isinstance(v, dict) and isinstance(v.get("table"), list):
        s = "\n".join(" | ".join(str(c) for c in r) if isinstance(r, list) else str(r) for r in v["table"])
    else:
        s = "\n".join(t for _, t in lint_spec.strings(v, ""))
    return s if len(s) <= cap else s[:cap] + " …"


def note_para_label(paras, i, insert=False):
    if not isinstance(paras, list):
        return "टिप्पणी"
    strs_before = sum(1 for x in paras[:i] if isinstance(x, str))
    if insert:
        return f"टिप्पणी — नवीन परिच्छेद (परि. {1 + strs_before} नंतर)"
    if i < len(paras) and isinstance(paras[i], str):
        return f"टिप्पणी परि. {2 + strs_before}"
    return f"टिप्पणी तक्ता (परि. {1 + strs_before} नंतर)"


def where_of(ch):
    """{"toks", "state", "op"} -> e.g. "टिप्पणी परि. 5", "पत्र — विषय", "संबंधित माहिती क्र. 2"."""
    toks, st, ins = ch["toks"], ch["state"], ch["op"] == "insert"
    k = toks[0]
    rest = toks[1:]
    idx = lambda t: int(t) if re.fullmatch(r"\d+", t or "") else None
    if k == "note":
        n = st.get("note") or {}
        f = rest[0]
        if f == "first":
            return "टिप्पणी परि. 1"
        if f == "paras" and len(rest) > 1 and idx(rest[1]) is not None:
            return note_para_label(n.get("paras"), idx(rest[1]), insert=ins and len(rest) == 2)
        if f == "sub" and len(rest) > 1 and idx(rest[1]) is not None:
            return note_para_label(n.get("paras"), idx(rest[1])) + " चे उप-मुद्दे"
        return {"closing": "टिप्पणी शेवटचा परिच्छेद", "signers": "टिप्पणी सही-साखळी", "uo": "टिप्पणी — अनौपचारिक संदर्भ"}.get(f, "टिप्पणी")
    if k == "related":
        i = idx(rest[0])
        if i is None:
            return "संबंधित माहिती"
        sub = {"heading": " — शीर्षक", "text": " — उतारा", "source": " — संदर्भ-ओळ"}.get(rest[1] if len(rest) > 1 else "", "")
        return ("संबंधित माहिती — नवीन क्र. " if ins and len(rest) == 1 else "संबंधित माहिती क्र. ") + f"{i + 1}{sub}"
    if k in ("letter", "letters", "order", "orders"):
        many = k.endswith("s")
        base = "पत्र" if k.startswith("letter") else "आदेश-प्रारूप"
        if many:
            i = idx(rest[0])
            base += f" {i + 1}" if i is not None else ""
            rest = rest[1:]
        if not rest:
            return base + (" (नवीन)" if ins else "")
        fields = LETTER_FIELD if k.startswith("letter") else ORDER_FIELD
        lab = f"{base} — {fields.get(rest[0], rest[0])}"
        if len(rest) > 1 and idx(rest[1]) is not None:
            lab += f" {idx(rest[1]) + 1}"
        return lab
    if k == "parawise":
        if rest[0] == "paras" and len(rest) > 1 and idx(rest[1]) is not None:
            i = idx(rest[1])
            paras = (st.get("parawise") or {}).get("paras") or []
            it = paras[i] if i < len(paras) and not ins else None
            if isinstance(it, dict) and it.get("para"):
                return f"परिच्छेदनिहाय उत्तर — Para {it['para']}"
            return f"परिच्छेदनिहाय उत्तर ओळ {i + 1}" + (" (नवीन)" if ins and len(rest) == 2 else "")
        return f"परिच्छेदनिहाय उत्तर — {rest[0]}"
    if k == "affidavit":
        if rest[0] in ("paras", "reply") and len(rest) > 1 and idx(rest[1]) is not None:
            return f"शपथपत्र परि. {idx(rest[1]) + 1}"
        return f"शपथपत्र — {rest[0]}"
    if k == "lq":
        if rest[0] == "parts" and len(rest) > 1 and idx(rest[1]) is not None:
            return f"विधानमंडळ उत्तर खंड ({idx(rest[1]) + 1})"
        return f"विधानमंडळ उत्तर — {rest[0]}"
    return "/".join(toks)


def readable_changes(changes):
    return [{"where": where_of(c), "before": text_of(c["before"]), "after": text_of(c["after"])} for c in changes]


# ---------------------------------------------------------------- quote guard + lint
def quotes(v):
    return collections.Counter(q.strip() for q in QUOTE_RE.findall(text_of(v, cap=10 ** 7)) if q.strip())


def named_in(q, message):
    """the message names the quote: 3 consecutive words of it (or the whole short quote) occur in the message."""
    norm = lambda s: " ".join(re.sub(r"[“”\"'‘’]", " ", s).split())
    m, w = norm(message), norm(q).split()
    if len(w) < 3:
        return bool(w) and " ".join(w) in m
    return any(" ".join(w[i:i + 3]) in m for i in range(len(w) - 2))


def quote_problems(changes, message):
    P = []
    for c in changes:
        if c["op"] != "replace" or c["after"] in (None, "", [], {}):
            continue
        gone = quotes(c["before"]) - quotes(c["after"])
        for q in gone:
            if not named_in(q, message):
                P.append(f"{c['path']}: उतारा बदलला — “{q[:60]}…” हा शब्दशः उतारा आहे; संदेशात तो नमूद नाही, तो जसा होता "
                         "तसाच ठेवा (rule 2)")
    return P


def lint_errors(spec, pages):
    try:
        P = lint_spec.lint_spec(spec, pages) + lint_spec.lint_extras(spec)[0]
    except Exception as e:  # a crash of the linter is an error of the edit, never a pass
        P = [f"lint: crashed — {str(e)[:160]}"]
    return P


def _rule(p):
    return p.split(": ", 1)[1] if ": " in p else p


def new_lint_errors(before, after):
    """errors of `after` that `before` did not have (by rule text, paths ignored: inserts shift the indexes)."""
    left = collections.Counter(_rule(p) for p in before)
    out = []
    for p in after:
        r = _rule(p)
        if left[r] > 0:
            left[r] -= 1
        else:
            out.append(p)
    return out


# ---------------------------------------------------------------- model call
def post_json(url, body, headers, timeout=900):
    """one HTTPS POST -> (status, parsed JSON or text). Tests replace this function."""
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    try:
        return status, json.loads(raw)
    except Exception:
        return status, raw[:500].decode("utf-8", "replace")


def price_of(model, fallback):
    m = str(model or "")
    for k in sorted(PRICES, key=len, reverse=True):   # longest id first ("claude-sonnet-5-5" before "claude-sonnet-5")
        if m == k or m.startswith(k + "-"):
            return PRICES[k]
    return PRICES.get(fallback) or PRICES[DEFAULT_MODEL]


def cost_of(resp, model):
    u = resp.get("usage") if isinstance(resp, dict) else None
    if not isinstance(u, dict):
        return 0.0
    pi, po = price_of(resp.get("model"), model)
    n = lambda k: float(u.get(k) or 0)
    return (n("input_tokens") * pi + n("cache_creation_input_tokens") * pi * 1.25
            + n("cache_read_input_tokens") * pi * 0.1 + n("output_tokens") * po) / 1e6


def call_model(api_key, model, system, messages, max_tokens):
    """-> (response JSON, cost $). Retries 429 / 5xx / connection errors (3 tries); a 400 is tried once more without the
    structured-output format and the fallback beta (older models / proxies). Raises EditFail with a Marathi reason."""
    plain = False
    last = ""
    for attempt in range(4):
        body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages,
                "output_config": {"effort": EFFORT}}
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        if not plain:
            body["output_config"]["format"] = {"type": "json_schema", "schema": OUT_SCHEMA}
            if model in FALLBACK_MODELS:
                body["fallbacks"] = "default"
                headers["anthropic-beta"] = "server-side-fallback-2026-07-01"
        try:
            status, resp = post_json(API_URL, body, headers)
        except Exception as e:
            status, resp = 0, str(e)[:200]
        if status == 200 and isinstance(resp, dict):
            return resp, cost_of(resp, model)
        last = (resp.get("error", {}).get("message") if isinstance(resp, dict) and isinstance(resp.get("error"), dict)
                else str(resp))[:200]
        if status == 400 and not plain:
            plain = True; continue
        if status in (401, 403):
            raise EditFail("Anthropic key अमान्य आहे. कृपया Settings मधील key तपासून सुधारणा पुन्हा पाठवावी, ही विनंती.")
        if status in (0, 408, 409, 429) or status >= 500:
            time.sleep(min(60, 10 * (attempt + 1)) if not os.environ.get("EDIT_NO_SLEEP") else 0)
            continue
        break
    raise EditFail(f"सुधारणा-सेवा उपलब्ध होऊ शकली नाही (HTTP {status}: {last}). कृपया थोड्या वेळाने सुधारणा पुन्हा पाठवावी, ही विनंती."[:500])


def reply_of(resp):
    """response -> {"ops", "summary", "refuse"}; Refused / EditFail on refusal, truncation or unreadable JSON."""
    sr = resp.get("stop_reason")
    if sr == "refusal":
        raise Refused("ही सुधारणा करता आली नाही (सेवेने विनंती स्वीकारली नाही). कृपया संदेश वेगळ्या शब्दांत पाठवावा किंवा 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")
    if sr == "max_tokens":
        raise EditFail("बदल मोठा असल्याने सुधारणा पूर्ण होऊ शकली नाही. कृपया बदल लहान भागांत पाठवावा, ही विनंती.")
    txt = "".join(b.get("text", "") for b in resp.get("content") or [] if isinstance(b, dict) and b.get("type") == "text")
    t = txt.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        r = json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        try:
            r = json.loads(m.group(0)) if m else None
        except Exception:
            r = None
    if not isinstance(r, dict) or not isinstance(r.get("ops", []), list):
        raise EditFail("सुधारणेचे उत्तर वाचता आले नाही. कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.")
    return {"ops": r.get("ops") or [], "summary": str(r.get("summary") or "").strip(),
            "refuse": str(r.get("refuse") or "").strip()}


def user_content(ctx, part, message, retry_errors=None):
    if retry_errors is not None:
        return ("The ops above were applied to the ORIGINAL part (not to an already changed one) and the result breaks "
                "these rules:\n" + "\n".join(f"- {e}" for e in retry_errors[:30]) +
                "\nReply again with the COMPLETE corrected ops list (paths relative to the original part), the summary "
                "and refuse, as JSON.")
    return ("Context:\n" + json.dumps(ctx, ensure_ascii=False, indent=1) +
            "\n\nThe part (JSON; paths start with its keys):\n" + json.dumps(part, ensure_ascii=False) +
            "\n\nMessage of the Section Officer (change exactly this):\n" + message.strip())


def max_tokens_for(part):
    return int(min(32000, max(8000, len(json.dumps(part, ensure_ascii=False)))))


# ---------------------------------------------------------------- Supabase helpers (engine_supabase underneath)
def step(text):
    """Live progress. L-F1 (audit 05.11.2026): the edit job holds the Supabase service key, so the step is written
    DIRECTLY to Supabase (only while the run is queued / running, L-F8); the Worker route (run token) only without it."""
    if E.KEY or E.DB_TOKEN:   # S-F2 (isolation on): the same write through the Worker proxy (DB token)
        try:
            E.patch_run({"step": text[:200]})
        except Exception as e:
            print("edit_drafts step:", str(e)[:120], file=sys.stderr)
    elif os.environ.get("RUN_TOKEN") and os.environ.get("WORKER"):
        E.cmd_step_worker(text)


def download(row, dst):
    bucket, _, path = str(row["storage_path"]).partition("/")
    data = E.http("GET", f"{E.BASE}/storage/v1/object/{bucket}/{E.enc(path)}", raw=True)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(data)
    return dst


def newest_row(files, kind, name=None):
    rows = [f for f in files if f.get("kind") == kind and (name is None or f.get("original_name") == name)]
    return max(rows, key=lambda f: (f.get("version") or 0, f.get("id") or 0)) if rows else None


def download_url(url, timeout=120):
    """GET an official GR URL -> bytes (tests replace this function)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_gr(code, work):
    """pdf/gr/<code>.pdf of the checkout, else the official URL, else archive.org -> local path, or None."""
    if not GR_CODE_RE.fullmatch(code):
        return None
    p = os.path.join(REPO, "pdf", "gr", f"{code}.pdf")
    if os.path.isfile(p):
        return p
    for u in GR_URLS:
        try:
            b = download_url(u.format(c=code))
        except Exception:
            continue
        if b[:4] == b"%PDF":
            dst = os.path.join(work, "gr", f"{code}.pdf")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(b)
            return dst
    return None


def gr_title(code):
    try:
        for line in open(os.path.join(REPO, "pdf", "gr", "INDEX.tsv"), encoding="utf-8"):
            c = line.rstrip("\n").split("\t")
            if c[0] == code and len(c) > 3 and c[3].strip():
                return f"{c[3].strip()[:120]} (सांकेतांक {code})"
    except OSError:
        pass
    return f"शासन निर्णय (सांकेतांक {code})"


# ---------------------------------------------------------------- package (Addendum A)
def pdf_ok(path):
    import pymupdf
    try:
        with pymupdf.open(path) as d:
            return (not d.needs_pass) and len(d) > 0
    except Exception:
        return False


def attachment_pdf(row, work):
    """case_files row -> (local PDF path, None) or (None, Marathi note)."""
    name = str(row.get("original_name") or "file")
    ext = os.path.splitext(name)[1].lower()
    d = os.path.join(work, "att", str(row["id"]))
    src = download(row, os.path.join(d, E.fs_name(name)))
    if ext == ".pdf" or (ext not in IMAGE_EXT + OFFICE_EXT and open(src, "rb").read(5) == b"%PDF-"):
        return (src, None) if pdf_ok(src) else (None, f"{name}: PDF उघडली नाही (खराब / पासवर्ड-संरक्षित)")
    if ext in IMAGE_EXT + OFFICE_EXT:
        import prep_pages
        if ext in OFFICE_EXT and not (shutil.which("soffice") or shutil.which("soffice.exe")):
            return None, f"{name}: Word फाइल जोडता आली नाही. कृपया ती PDF करून जोडावी, ही विनंती."
        try:
            p = prep_pages.to_pdf(src, d)
        except Exception as e:
            return None, (f"{name}: Word फाइल जोडता आली नाही. कृपया ती PDF करून जोडावी, ही विनंती." if ext in OFFICE_EXT
                          else f"{name}: प्रतिमा PDF मध्ये बदलता आली नाही ({str(e)[:80]})")
        return (p, None) if pdf_ok(p) else (None, f"{name}: PDF मध्ये बदलता आली नाही")
    return None, f"{name}: हा फाइल-प्रकार जोडता येत नाही. कृपया PDF / JPG / PNG फाइल जोडावी, ही विनंती."


def case_input_map(files, exclude_ids, work):
    """local path "in/<kind>/<name>" of the full run's fetch (engine_supabase cmd_fetch layout) -> case_files row."""
    fs = [f for f in files if f.get("id") not in exclude_ids]
    inputs = E.inputs_of(fs)
    older = [dict(o, kind="extra_doc") for o in E.older_proposals(fs)]
    taken, out = set(), {}
    for f in inputs + older:
        dst = E.unique_dst(work, f["kind"], f["original_name"], taken)
        out[os.path.relpath(dst, work).replace("\\", "/")] = f
    return out


class Resolver:
    """paths of a saved enclosures.json -> local files (repo checkout / case inputs / case_files id / GR code)."""

    def __init__(self, files, exclude_ids, work):
        self.files, self.work = files, work
        self.inputs = case_input_map(files, exclude_ids, os.path.join(work, "case"))
        self.byid = {f.get("id"): f for f in files}

    def __call__(self, item, label):
        path = item if isinstance(item, str) else (item.get("path") or "")
        if isinstance(item, dict) and item.get("case_file_id") is not None:
            row = self.byid.get(item["case_file_id"])
            if row:
                p, _ = attachment_pdf(row, self.work)
                if p:
                    return p
        if isinstance(item, dict) and item.get("gr_code"):
            p = fetch_gr(str(item["gr_code"]), self.work)
            if p:
                return p
        p = str(path).replace("\\", "/")
        rel_case = rel_repo = None
        if p.startswith("/srv/engine/"):
            rel_repo = p[len("/srv/engine/"):]
        elif p.startswith("/tmp/case/"):
            rel_case = p[len("/tmp/case/"):]
        elif not p.startswith("/"):
            rel_case, rel_repo = (p, None) if p.startswith("in/") else (None, p)
        if rel_repo:
            full = os.path.realpath(os.path.join(REPO, rel_repo))
            if full.startswith(os.path.realpath(REPO) + os.sep) and os.path.isfile(full):
                return full
        if rel_case and rel_case in self.inputs:
            row = self.inputs[rel_case]
            return download(row, os.path.join(self.work, "case", rel_case))
        raise Refused(f"GR सह PDF मधील '{str(label)[:80]}' ची मूळ फाइल सापडली नाही. GR सह PDF पुन्हा तयार "
                      "करण्यासाठी कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")


def split_encs(raw):
    if isinstance(raw, dict):
        return list(raw.get("proposal_parts") or []), list(raw.get("enclosures") or [])
    if isinstance(raw, list):
        return [], list(raw)
    raise Refused("जुन्या GR सह PDF ची नोंद (enclosures.json) वाचता आली नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")


def page_range(pages):
    a, b = min(pages), max(pages)
    return f"पृ.{a}/प.वि." if a == b else f"पृ.{a}-{b}/प.वि."


def copy_annotations(old_pdf, new_pdf, n_old):
    """the old package's annotations (pkg3 + tools/highlight.py highlights) onto pages 1..n_old of the rebuilt package."""
    import pymupdf
    from clean_meta import clean_pdf
    old, new = pymupdf.open(old_pdf), pymupdf.open(new_pdf)
    try:
        for i in range(n_old):
            np_, op_ = new[i], old[i]
            for a in list(np_.annots()):
                np_.delete_annot(a)
            for a in op_.annots():
                if a.type[0] != pymupdf.PDF_ANNOT_HIGHLIGHT:
                    continue
                v = a.vertices or []
                quads = [pymupdf.Quad(*v[j:j + 4]) for j in range(0, len(v) - 3, 4)]
                if not quads:
                    continue
                h = np_.add_highlight_annot(quads=quads)
                h.set_colors(stroke=(a.colors or {}).get("stroke") or (1, 1, 0)); h.update()
        clean_pdf(new)
        tmp = new_pdf + ".tmp.pdf"
        new.save(tmp, garbage=3, deflate=True)
    finally:
        old.close(); new.close()
    os.replace(tmp, new_pdf)


def build_package(ctx, files, case_rows, work):
    """Addendum A -> {"pdf", "name", "pages", "attached", "notes", "enclosures", "text"} or None (nothing to attach)."""
    message, target = ctx["message"], ctx["target"]
    att_ids = [int(x) for x in (ctx.get("attachments") or []) if str(x).isdigit()][:MAX_ATTACH]
    rows = [f for f in files if f.get("id") in att_ids]
    codes = list(dict.fromkeys(GR_CODE_RE.findall(message)))[:MAX_ATTACH]
    if not rows and not codes:
        if target == "package":
            raise Refused("जोडावयाची फाइल किंवा GR सांकेतांक प्राप्त झालेला नाही. कृपया फाइल (📎) किंवा सांकेतांक द्यावा, ही विनंती.")
        return None
    enc_row = case_rows.get("enclosures")
    old_row, prop_row = case_rows.get("package_pdf"), E.newest_proposal(files)
    if not enc_row or not old_row or not prop_row:
        raise Refused("हे जुने प्रकरण आहे. GR सह PDF पुन्हा तयार करण्यासाठी कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")
    step("सुधारणा: जोडलेली कागदपत्रे तयार करण्यात येत आहेत")
    raw = json.load(open(download(enc_row, os.path.join(work, "old", "enclosures.json")), encoding="utf-8-sig"))
    parts, encs = split_encs(raw)
    new_items, notes = [], []
    for r in rows:
        p, why = attachment_pdf(r, work)
        if why:
            notes.append(why); continue
        title = os.path.splitext(E.strip_upload_prefix(E.safe_name(r.get("original_name") or "कागदपत्र")))[0]
        new_items.append((p, title, {"path": r.get("original_name"), "case_file_id": r["id"]}))
    for c in codes:
        p = fetch_gr(c, work)
        if not p:
            notes.append(f"GR {c} शासन संकेतस्थळावर / archive.org वर मिळाला नाही. कृपया त्याची PDF जोडावी, ही विनंती."); continue
        new_items.append((p, gr_title(c), {"path": f"pdf/gr/{c}.pdf", "gr_code": c}))
    if not new_items:
        raise Refused("; ".join(notes)[:500] or "जोडण्यायोग्य फाइल प्राप्त झालेली नाही.")
    step("सुधारणा: GR सह PDF नव्याने तयार करण्यात येत आहे")
    res = Resolver(files, set(att_ids), work)
    lp = lambda it: (it if isinstance(it, str) else it.get("label")) or (it if isinstance(it, str) else it.get("path"))
    run_parts = []
    for k, it in enumerate(parts):
        local = res(it, lp(it))
        run_parts.append(local if isinstance(it, str) else {**it, "path": local})
    run_encs = []
    for e in encs:
        if not isinstance(e, dict) or not e.get("path"):
            raise Refused("जुन्या GR सह PDF ची नोंद (enclosures.json) अपूर्ण आहे. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")
        run_encs.append({**e, "path": res(e, e.get("label") or e.get("path"))})
    used = {str(e.get("label") or e.get("path")) for e in encs} | {"प्रस्ताव", "marks", "proposal_parts"}
    used |= {str(lp(it)) for it in parts}
    saved_new = []
    for p, title, ref in new_items:
        lab, k = title, 2
        while lab in used:
            lab = f"{title} ({k})"; k += 1
        used.add(lab)
        run_encs.append({"path": p, "pages": "", "label": lab})
        saved_new.append({**ref, "pages": "", "label": lab})
    js = os.path.join(work, "new", "enclosures.run.json")
    os.makedirs(os.path.dirname(js), exist_ok=True)
    json.dump({"proposal_parts": run_parts, "enclosures": run_encs}, open(js, "w", encoding="utf-8"), ensure_ascii=False)
    prop = download(prop_row, os.path.join(work, "proposal", E.fs_name(prop_row["original_name"])))
    old_pdf = download(old_row, os.path.join(work, "old", "package.pdf"))
    name = old_row.get("original_name") or E.strip_upload_prefix(E.safe_name(prop_row["original_name"]))
    out = os.path.join(work, "new", E.fs_name(E.strip_upload_prefix(E.safe_name(name))))
    r = subprocess.run([sys.executable, os.path.join(HERE, "pkg3.py"), prop, js, out], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.isfile(out):
        raise EditFail(f"GR सह PDF नव्याने तयार होऊ शकली नाही (pkg3: {(r.stderr or r.stdout).strip()[-200:]}). कृपया सुधारणा पुन्हा पाठवावी, ही विनंती."[:500])
    import pymupdf
    mp = json.load(open(out + ".map.json", encoding="utf-8"))
    with pymupdf.open(old_pdf) as d:
        n_old = len(d)
    newlabs = [s["label"] for s in saved_new]
    old_pages = sum(len(v["pages"]) for k, v in mp.items() if isinstance(v, dict) and "pages" in v and k not in newlabs)
    if old_pages != n_old or any(min(mp[l]["pages"]) <= n_old for l in newlabs):
        raise Refused(f"जुन्या GR सह PDF ची पाने ({n_old}) नव्याने जुळली नाहीत ({old_pages}). कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")
    copy_annotations(old_pdf, out, n_old)
    with pymupdf.open(out) as d:
        total = len(d)
        attached, text = [], []
        for l in newlabs:
            pg = mp[l]["pages"]
            attached.append({"title": l, "pages": page_range(pg)})
            for n in pg:
                t = " ".join(d[n - 1].get_text("text").split())
                if t:
                    text.append(f"[{l} — पृ.{n}/प.वि.] {t}")
    joined = "\n".join(text)
    if len(joined) > ATTACH_TEXT_CAP:
        joined = joined[:ATTACH_TEXT_CAP] + " … (पुढील मजकूर कापला)"
    saved = ({**raw, "enclosures": encs + saved_new} if isinstance(raw, dict) else encs + saved_new)
    return {"pdf": out, "name": name, "pages": total, "old_pages": n_old, "attached": attached, "notes": notes,
            "enclosures": saved, "text": joined}


# ---------------------------------------------------------------- rebuild + checks
def no_preview_env():
    """builders write a LibreOffice preview when soffice is on PATH: not needed for an edit (contract point 4)."""
    env = dict(os.environ)
    keep = [d for d in env.get("PATH", "").split(os.pathsep)
            if d and not any(os.path.exists(os.path.join(d, x)) for x in ("soffice", "soffice.exe"))]
    env["PATH"] = os.pathsep.join(keep)
    return env


def prefix_of(name, suffix):
    return name[: -len(suffix)] if name and name.endswith(suffix) else ""


def affected_kinds(changed_keys, existing):
    return [k for k, (_, _, keys) in OUTPUTS.items() if k in existing and set(keys) & set(changed_keys)]


def rebuild(spec, kinds, existing, outdir):
    """-> {kind: (local path, upload name)}; EditFail when a builder fails."""
    sp = os.path.join(outdir, "spec.json")
    json.dump(spec, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    built = {}
    for kind in kinds:
        suffix, tool, _ = OUTPUTS[kind]
        name = existing[kind]["original_name"]
        pre = prefix_of(name, suffix) or f"Case{E.CASE}"
        r = subprocess.run([sys.executable, os.path.join(HERE, tool), sp, outdir, pre, "--no-lint"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=no_preview_env(), timeout=600)
        p = os.path.join(outdir, pre + suffix)
        if r.returncode != 0 or not os.path.isfile(p):
            raise EditFail(f"सुधारित {TARGET_LABEL.get(next((t for t, k in TARGET_KIND.items() if k == kind), ''), kind)} "
                           f"तयार होऊ शकले नाही ({tool}: {(r.stderr or r.stdout).strip()[-160:]}). कृपया सुधारणा पुन्हा "
                           "पाठवावी, ही विनंती."[:500])
        built[kind] = (p, name)
    return built


VERIFY_PACKAGE = ("package PDF opens", "page stamps", "bookmarks", "package PDF metadata", "annotations")
VERIFY_SKIP = ("Study", "status.json", "map.json", "package file name")


def verify_checks(outdir, built, pkg, desk, package_changed):
    """-> (hard [(check, detail)], soft [(check, detail)]) for the rebuilt files (and the rebuilt package)."""
    import docx
    hard, soft = [], []
    nl = built.get("note_letter")
    if nl or package_changed:
        vd = os.path.join(outdir, "verify")
        os.makedirs(vd, exist_ok=True)
        pre = "Edit"
        if nl:
            shutil.copy(nl[0], os.path.join(vd, f"{pre}_Note_and_Letter.docx"))
        cmd = [sys.executable, os.path.join(HERE, "verify_outputs.py"), vd, pre, pkg, "0"]
        if isinstance(desk, str) and E.DESK_ID_RE.match(desk) and desk != E.DEFAULT_DESK:
            cmd += ["--desk", desk]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        E.private_log("edit_verify.log", r.stdout or "")
        for l in E.log_safe_lines((r.stdout or "").splitlines()):   # S-F3: check names only in the Actions log
            print(l)
        h, s = E.classify_verify((r.stdout or "").splitlines())

        def keep(c):
            if c.startswith(VERIFY_SKIP):
                return False
            if c.startswith(VERIFY_PACKAGE):   # the package is checked only when it was rebuilt (else: unchanged)
                return package_changed or c == "package PDF opens"
            return bool(nl)
        hard += [x for x in h if keep(x[0])]
        soft += [x for x in s if keep(x[0])]
        if not any(l.startswith(("OK", "FAIL")) for l in (r.stdout or "").splitlines()):
            hard.append(("verify_outputs", ((r.stderr or "").strip().splitlines() or [f"exit {r.returncode}"])[-1]))
    extras = {k: v for k, v in built.items() if k != "note_letter"}
    if extras:
        import pymupdf
        import verify_outputs as V
        from clean_meta import docx_meta_problems
        with pymupdf.open(pkg) as d:
            N = len(d)
        for kind, (p, _) in extras.items():
            lab = EXTRA_LABEL[kind]
            X = docx.Document(p)
            xt = V.doc_text(X)
            for c, probs, is_hard in ((f"{lab} fonts", V.font_problems(X, lab), False),
                                      (f"{lab} internal ids", [f"internal id {x}" for x in lint_spec.id_hits(xt)], True),
                                      (f"{lab} repo paths", [f"'{x}'" for x in lint_spec.repo_hits(xt)], True),
                                      (f"{lab} पृ. references", lint_spec.ref_problems(xt, N, lab, skip_quotes=True), False),
                                      (f"{lab} no package / warning / AI words",
                                       [f"'{w}'" for w in lint_spec.draft_word_hits(xt)], False),
                                      (f"{lab} metadata (no tool / AI trace)", docx_meta_problems(p), False)):
                if probs:
                    (hard if is_hard else soft).append((c, "; ".join(map(str, probs[:4]))))
    return hard, soft


# Q-F20 (audit 05.11.2026): an edit of the note / related is checked like a full run's final extract guard
# (tools/extract_check.py, related + note-body “…” quotes vs the package pages; text layer only — no OCR in the edit job).
# Only mismatches the edit brought in are reported (the old ones are already in the full run's Study part 7).
QUOTE_NOTE = ("सुधारित टिप्पणीतील काही अवतरणे GR सह PDF मधील नमूद पानाशी शब्दशः जुळली नाहीत. कृपया वापरण्यापूर्वी "
              "ती मूळ पानाशी तपासावीत, ही विनंती.")


def quote_check(old_spec, new_spec, pkg):
    """-> mismatch records of new_spec that old_spec did not have ([] when the check cannot run: never fails the edit)."""
    try:
        import extract_check as X
        bad = lambda sp: [r for r in X.check(pkg, sp, no_ocr=True, note_body=True) if r.get("status") == "mismatch"]
        old = {(bool(r.get("warn_only")), r.get("extract")) for r in bad(old_spec)}
        return [r for r in bad(new_spec) if (bool(r.get("warn_only")), r.get("extract")) not in old]
    except Exception as e:
        print("edit_drafts: quote check not run:", type(e).__name__, file=sys.stderr)
        return []


def quote_warnings(recs):
    """mismatch records -> soft warning lines (runs.warnings; same texts as the full run, tools/engine_supabase.py)."""
    where = lambda xs: "; ".join(sorted({str(x.get("where")) for x in xs}))[:180]
    note = [r for r in recs if r.get("warn_only")]
    rel = [r for r in recs if not r.get("warn_only")]
    out = [E.note_quote_line(len(note), where(note))] if note else []
    if rel:
        out.append(E.soft_line("उतारे", f"{len(rel)} उतारे मूळ PDF शी शब्दशः जुळले नाहीत ({where(rel)}) — वापरण्यापूर्वी तपासणी आवश्यक"))
    return out


# ---------------------------------------------------------------- uploads
def upload_all(built, package, spec_path, enc_path):
    """objects first, rows only after every upload succeeded (engine_supabase finish rule). -> [{kind, name, version}]"""
    put = []
    try:
        if package:
            put.append(E.put_object("package_pdf", package["pdf"], package["name"]))
        for kind, (p, name) in built.items():
            put.append(E.put_object(kind, p, name))
        ver = E.next_version("spec")   # spec.json + enclosures.json: one version (engine_supabase upload_spec)
        for n, p in (("spec.json", spec_path), ("enclosures.json", enc_path)):
            if not p:
                continue
            path = E.spec_object(ver, n)   # …/spec/v<n>/r<this run>/<name> (L-F7)
            E.http("POST", f"{E.BASE}/storage/v1/object/outputs/{E.enc(path)}", open(p, "rb").read(),
                   {"Content-Type": "application/json", "x-upsert": "true"})
            put.append({"kind": "spec", "name": n, "version": ver, "path": path})
    except Exception as e:
        for u in put:
            E.drop_object(u["path"])
        raise EditFail(f"सुधारित फाइल जतन होऊ शकली नाही (Storage: {str(e)[:200]}). कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.")
    for u in put:
        E.insert_row(u)
    return [{"kind": u["kind"], "name": u["name"], "version": u["version"]} for u in put]


# ---------------------------------------------------------------- the job
# L-F7 (audit 05.11.2026): the spec rows of a run are inserted AFTER its note_letter / package rows (tools/engine_supabase.py
# finish and upload_all here; case_files ids are an identity column, so they grow). A newest spec row older than the
# newest note_letter / package row means the last run's spec upload failed: an edit would change an OLDER draft.
STALE_SPEC = ("या प्रकरणाची सुधारणा-फाइल शेवटच्या टिप्पणी व पत्रापेक्षा जुनी आहे (शेवटच्या प्रक्रियेत ती जतन होऊ शकली नाही). "
              "जुन्या मसुद्यावर बदल होऊ नये म्हणून ही सुधारणा करण्यात आलेली नाही. कृपया 'पुन्हा तयार करा' हा पर्याय "
              "वापरावा, ही विनंती.")


def stale_spec(spec_row, *outputs):
    """True when a newer note_letter / package_pdf row exists than the newest spec row (by id; created_at as a tie)."""
    key = lambda r: (int(r.get("id") or 0), str(r.get("created_at") or ""))
    return any(o and key(o) > key(spec_row) for o in outputs)


def spec_run_of(row):
    """The run that wrote a spec row (storage key …/spec/v<n>/r<run>/<name>, L-F7), or None (older key form)."""
    m = re.search(r"/spec/v\d+/r(\d+)/", str((row or {}).get("storage_path") or ""))
    return int(m.group(1)) if m else None


def load_run():
    run = (E.rest("GET", f"runs?id=eq.{E.RUN}&select=*") or [None])[0]
    case = (E.rest("GET", f"cases?id=eq.{E.CASE}&select=*") or [None])[0]
    if not run or not case or str(run.get("case_id")) != str(E.CASE):
        raise EditFail("सुधारणा-विनंती सापडली नाही. कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.")
    if run.get("kind") not in (None, "edit"):
        raise EditFail("ही सुधारणा-विनंती नाही (run kind). कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.")
    files = E.rest("GET", f"case_files?case_id=eq.{E.CASE}&select=*&order=created_at.asc") or []
    return run, case, files


def context_of(case, target, pages, package):
    ctx = {"target": TARGET_LABEL.get(target, target), "package_pages": f"1-{pages}" if pages else "____"}
    for k in ("cr_no", "cr_year", "file_no", "subject", "title"):
        if case.get(k) not in (None, ""):
            ctx[k] = case[k]
    if package:
        ctx["attached_now"] = [f"{a['title']}: {a['pages']}" for a in package["attached"]]
        ctx["attachment_text"] = package["text"]
    return ctx


def run_edit(work, api_key=None, model=None):
    t0 = time.time()
    if not E.patch_run({"state": "running", "started_at": E.now(), "step": "सुधारणा: फाइल्स प्राप्त करण्यात येत आहेत"}):
        # L-F8: the run was already failed / closed (sweep, cancel) — never resurrected, nothing is done
        print("edit_drafts: run is no longer queued/running — not started", file=sys.stderr)
        return None
    run, case, files = load_run()
    target = str(run.get("edit_target") or "").strip()
    message = str(run.get("edit_message") or "").strip()
    if target not in TARGET_KEYS:
        raise EditFail(f"सुधारणेचा भाग ('{target[:40]}') ओळखता आला नाही. कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.")
    if not message:
        raise Refused("संदेश प्राप्त झालेला नाही. कृपया अपेक्षित बदल नमूद करावा, ही विनंती.")
    ctx = {"target": target, "message": message, "attachments": run.get("edit_attachments") or []}
    spec_row = newest_row(files, "spec", "spec.json")
    if not spec_row:
        raise EditFail("या प्रकरणाची सुधारणा-फाइल नाही (जुने प्रकरण). कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")
    rows = {"enclosures": newest_row(files, "spec", "enclosures.json"), "package_pdf": newest_row(files, "package_pdf")}
    existing = {k: newest_row(files, k) for k in OUTPUTS}
    existing = {k: v for k, v in existing.items() if v}
    if stale_spec(spec_row, existing.get("note_letter"), rows["package_pdf"]):
        raise Refused(STALE_SPEC)
    if target != "package" and TARGET_KIND[target] not in existing:
        raise Refused(f"या प्रकरणात {TARGET_LABEL[target]} तयार झालेले नाही. कृपया 'पुन्हा तयार करा' मध्ये तो मसुदा निवडावा, ही विनंती.")
    spec = json.load(open(download(spec_row, os.path.join(work, "old", "spec.json")), encoding="utf-8-sig"))
    if not isinstance(spec, dict):
        raise EditFail("सुधारणा-फाइल (spec.json) वाचता आली नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")

    package = build_package(ctx, files, rows, work)
    if package:
        pkg, pages = package["pdf"], package["pages"]
    elif rows["package_pdf"]:
        import pymupdf
        pkg = download(rows["package_pdf"], os.path.join(work, "old", "package.pdf"))
        with pymupdf.open(pkg) as d:
            pages = len(d)
    else:
        raise EditFail("GR सह प्रस्ताव PDF सापडली नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")

    cost, summary, changes, refused, new_spec = 0.0, "", [], "", spec
    extra_notes = []   # out-of-scope parts of a message whose doable part was done
    if target != "package":   # attach-only (target package): no model call
        keys = [k for k in TARGET_KEYS[target] if k in spec and spec[k] not in (None, "", [], {})]
        if not keys:
            raise Refused(f"सुधारणा-फाइलमध्ये {TARGET_LABEL[target]} नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.")
        part = {k: spec[k] for k in keys}
        step("सुधारणा: बदल तयार करण्यात येत आहेत")
        key = api_key or E.lookup("ANTHROPIC_API_KEY")
        if not key:
            raise EditFail("सेटिंग्ज अपूर्ण आहेत. कृपया Settings मधील Anthropic key तपासावी, ही विनंती.")
        mdl = model or os.environ.get("MODEL_EDIT") or DEFAULT_MODEL
        if not E.MODEL_RE.fullmatch(mdl):
            mdl = DEFAULT_MODEL
        ctx_m = context_of(case, target, pages, package)
        messages = [{"role": "user", "content": user_content(ctx_m, part, message)}]
        before_errs = lint_errors(spec, pages)
        for attempt in (1, 2):
            resp, c = call_model(key, mdl, SYSTEM, messages, max_tokens_for(part))
            cost += c
            SPENT[0] = cost
            try:
                rep = reply_of(resp)
            except Refused as r:
                raise Refused(r.args[0], cost)
            # partly out of scope (owner 04.11.2026: the note edit was dropped because the message also said "apply in
            # all future proposals"): the doable ops are applied, the reason for the rest becomes a note, never a refusal
            if rep["refuse"] and not rep["ops"]:
                refused = rep["refuse"]; summary = rep["summary"] or refused
                break
            part_note = rep["refuse"]
            try:
                new_part, chs = apply_ops(part, rep["ops"])
                cand = {**spec, **new_part}
                errs = new_lint_errors(before_errs, lint_errors(cand, pages)) + quote_problems(chs, message)
            except ValueError as e:
                chs, errs = [], [str(e)]
            if not errs:
                new_spec, changes, summary = cand, chs, rep["summary"]
                if part_note:
                    extra_notes.append(part_note)
                break
            if attempt == 2:
                raise EditFail(f"सुधारणा नियमांत बसली नाही ({errs[0]}). कृपया बदल वेगळ्या शब्दांत पाठवावा, ही विनंती."[:500])
            print("edit_drafts: retry with", len(errs), "error(s) (details: runner-private log)", file=sys.stderr)   # S-F3
            E.private_log("edit_retry.log", "\n".join(errs))
            messages += [{"role": "assistant", "content": resp.get("content") or [{"type": "text", "text": "{}"}]},
                         {"role": "user", "content": user_content(None, None, None, retry_errors=errs)}]
        if not refused and not changes and not package:
            refused = summary or "संदेशानुसार करावयाचा बदल निश्चित होऊ शकला नाही. कृपया बदलावयाचा भाग स्पष्टपणे नमूद करावा, ही विनंती."

    if refused and not package:
        raise Refused(refused, cost)

    built, outdir = {}, os.path.join(work, "out")
    os.makedirs(outdir, exist_ok=True)
    if changes:
        changed_keys = {c["toks"][0] for c in changes}
        kinds = affected_kinds(changed_keys, existing)
        step("सुधारणा: सुधारित मसुदा तयार करण्यात येत आहे")
        built = rebuild(new_spec, kinds, existing, outdir)
    step("सुधारणा: तपासणी करण्यात येत आहे")
    hard, soft = verify_checks(outdir, built, pkg, E.case_desk(case), bool(package))
    qbad = quote_check(spec, new_spec, pkg) if changes and {c["toks"][0] for c in changes} & {"note", "related"} else []
    if hard:
        d = "; ".join(f"{c}: {x}" if x else c for c, x in hard[:3])
        raise EditFail(f"सुधारणेची पडताळणी पूर्ण झाली नाही ({d}); त्यामुळे कोणतीही फाइल जतन करण्यात आलेली नाही. कृपया सुधारणा पुन्हा पाठवावी, ही विनंती."[:500])
    step("सुधारणा: नवीन आवृत्ती जतन करण्यात येत आहे")
    sp = os.path.join(work, "new", "spec.json")
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    json.dump(new_spec, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ep = None
    if package:
        ep = os.path.join(work, "new", "enclosures.json")
        json.dump(package["enclosures"], open(ep, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif rows["enclosures"]:   # keep the pair spec.json / enclosures.json in one version
        ep = download(rows["enclosures"], os.path.join(work, "new", "enclosures.json"))
    uploaded = upload_all(built, package, sp if (changes or package) else None, ep if (changes or package) else None)
    files_kinds = [u["kind"] for u in uploaded if u["kind"] != "spec"]
    if package and not summary:
        summary = "GR सह PDF मध्ये खालील कागदपत्रे जोडण्यात आली आहेत: " + "; ".join(f"{a['title']} ({a['pages']})" for a in package["attached"])
    notes = (list(package["notes"]) if package else []) + extra_notes + ([QUOTE_NOTE] if qbad else [])
    er = {"summary": summary, "changes": readable_changes(changes), "files": files_kinds, "cost_usd": round(cost, 4),
          "attached": package["attached"] if package else []}
    if refused:
        er["refused"] = refused
    if notes:
        er["notes"] = notes
    if spec_run_of(spec_row):
        er["based_on_run"] = spec_run_of(spec_row)   # L-F7: the run whose spec was edited
    if not E.patch_run({"state": "done", "finished_at": E.now(), "step": "तयार", "summary": summary[:500],
                 "edit_result": er, "cost_usd": round(cost, 4), "duration_s": round(time.time() - t0, 1)}):
        print("edit_drafts: run is no longer running — new versions stored, state not changed", file=sys.stderr)   # L-F8
    warns = [E.soft_line(c, x) for c, x in soft[:8]] + [f"सुधारणा: {n}"[:300] for n in notes] + quote_warnings(qbad)
    if warns:
        try:
            E.add_warnings(warns)
        except Exception as e:
            print("edit_drafts: warnings not stored:", e, file=sys.stderr)
    try:
        E.activity("edit_done", {"run_id": int(E.RUN), "files": uploaded, "target": target})
    except Exception as e:
        print("edit_drafts: activity not stored:", e, file=sys.stderr)
    # S-F3: no case text (summary) in the Actions log
    print("edit done:", ", ".join(f"{u['kind']} v{u['version']}" for u in uploaded) or "no new file",
          f"| changes {len(changes)} | quote mismatches {len(qbad)} | ${cost:.4f}")
    return er


def finish_refused(reason, cost=0.0):
    er = {"summary": reason, "refused": reason, "changes": [], "files": [], "cost_usd": round(cost, 4), "attached": []}
    if not E.patch_run({"state": "done", "finished_at": E.now(), "step": "तयार", "summary": reason[:500], "edit_result": er,
                        "cost_usd": round(cost, 4)}):
        print("edit_drafts: run is no longer queued/running — state not changed", file=sys.stderr)   # L-F8
    try:
        E.activity("edit_refused", {"run_id": int(E.RUN), "reason": reason[:300]})
    except Exception:
        pass
    print(f"edit refused (reason stored on the run, {len(reason)} chars)")   # S-F3
    return er


def main(argv):
    work = None
    if "--work" in argv:
        i = argv.index("--work"); work = argv[i + 1] if i + 1 < len(argv) else None
    work = work or tempfile.mkdtemp(prefix="edit_")
    os.makedirs(work, exist_ok=True)
    E.init()
    try:
        run_edit(work)
    except Refused as r:
        finish_refused(str(r.args[0]), r.args[1] if len(r.args) > 1 else 0.0)
    except EditFail as f:
        if SPENT[0]:
            try:
                E.patch_run({"cost_usd": round(SPENT[0], 4)})
            except Exception:
                pass
        E.cmd_fail(str(f))
    except SystemExit:
        raise
    except Exception as e:
        E.cmd_fail(f"सुधारणा पूर्ण होऊ शकली नाही ({str(e)[:200]}). कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
