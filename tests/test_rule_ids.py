"""Single-source rule ids (audit 05.11.2026 Part 9, R-F8 / R-F9 / R-F15 / R-F17): the §4 item numbers of INSTRUCTIONS.md are
the permanent ids. Every [I4.n] tag and every §4.n / §४.n reference in the engine / rule files must name an existing item,
the brief must tag every item, and the draft keys exist once (tools/draft_keys.json) with every copy equal to it.
Run: python3 -m pytest -q tests/test_rule_ids.py"""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
REF_FILES = ("tools/ENGINE_PROMPT.md", "tools/ENGINE_BRIEF.md", "tools/PROPOSAL_PROMPT.md", "PROPOSAL_SOP.md",
             "PROPOSAL_WORKFLOW.md", "INSTRUCTIONS.md", "tools/work_rules/court.md", "tools/work_rules/service.md",
             "tools/engine_supabase.py")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def section4_ids():
    """item numbers of INSTRUCTIONS.md "## ४." (top-level "N. " lines up to the next "## " heading)."""
    text = read("INSTRUCTIONS.md")
    start = text.index("\n## ४.")
    end = text.index("\n## ", start + 5)
    return [int(m.group(1)) for m in re.finditer(r"(?m)^(\d+)\.\s", text[start:end])]


def test_section4_ids_contiguous():
    ids = section4_ids()
    assert ids == list(range(1, len(ids) + 1)), ids
    assert len(ids) >= 35


def test_brief_tags_every_item():
    brief = read("tools/ENGINE_BRIEF.md")
    missing = [n for n in section4_ids() if f"[I4.{n}]" not in brief]
    assert missing == [], f"brief lacks tags {missing}"


def test_tags_and_section_refs_exist():
    ids = set(section4_ids())
    bad = []
    for rel in REF_FILES:
        t = read(rel).translate(DEV)
        for m in re.finditer(r"\[I4\.(\d+)\]", t):
            if int(m.group(1)) not in ids:
                bad.append(f"{rel}: [I4.{m.group(1)}]")
        for m in re.finditer(r"§\s?4\.(\d+)", t):
            if int(m.group(1)) not in ids:
                bad.append(f"{rel}: §4.{m.group(1)}")
    assert bad == [], bad


def test_service_rules_name_every_item():
    n = max(section4_ids())
    assert f"§4 items 1–{n}" in read("tools/work_rules/service.md")


def test_court_rules_point_to_4_32_and_4_35():
    t = read("tools/work_rules/court.md")
    for p in ("§4.32", "§4.35", "WP35697_2026_old-pension_finance-opinion.json", "WP35697_2026_parawise_GP-letter.json"):
        assert p in t, p
    e = read("tools/ENGINE_PROMPT.md")
    court = e[e.index("**Court mode**"):e.index("**Order drafts**")]
    for p in ("§4.32", "§4.35", "WP35697_2026_old-pension_finance-opinion.json", "WP35697_2026_parawise_GP-letter.json"):
        assert p in court, p


def test_proposal_prompt_para1_without_letter_no():
    t = read("tools/PROPOSAL_PROMPT.md")
    assert "(प्राधिकारी, क्र., दि., पृ." not in t
    assert "(प्राधिकारी, दि., पृ.N/प.वि.; पत्राचा क्रमांक नको" in t
    assert "प्रस्तावातील स्थिती / पृ." not in t       # no पृ. column in the condition table (§4.34 (ई))
    for p in ("§४.२६", "§४.३०", "§४.३१", "§४.३२", "§४.३३", "§४.३४", "§४.३५"):
        assert p in t, p


def test_brief_ref_no_year_placeholder():
    b = read("tools/ENGINE_BRIEF.md")
    assert "संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6" in b
    assert "संकिर्ण-2026/<file no>" not in b


# ---- draft keys: one source -------------------------------------------------------------------------------------------
def draft_source():
    return json.loads(read("tools/draft_keys.json"))


def py_constant(rel, name):
    for node in ast.parse(read(rel)).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not in {rel}")


def js_list(text, name):
    m = re.search(rf"(?:const|export const)\s+{name}\s*=\s*\[(.*?)\]", text, re.S)
    assert m, name
    return re.findall(r"'([a-z_]+)'", m.group(1))


def test_draft_keys_equal_everywhere():
    src = draft_source()
    keys = src["keys"]
    assert len(keys) == 16 and len(set(keys)) == 16
    assert list(py_constant("tools/engine_supabase.py", "DRAFT_KEYS")) == keys
    assert py_constant("tools/engine_supabase.py", "DRAFT_LABEL") == src["labels"]
    assert js_list(read("cloudflare/worker.js"), "DRAFT_KEYS") == keys
    ts = read("dashboard-app/src/lib/constants.ts")
    assert js_list(ts, "DRAFT_KEYS") == keys
    m = re.search(r"DRAFT_LABEL: Record<DraftKey, string> = \{(.*?)\};", ts, re.S)
    assert dict(re.findall(r"([a-z_]+): '([^']+)'", m.group(1))) == src["labels"]
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import work_type
    assert list(work_type.DRAFT_KEYS) == keys


def test_work_types_allow_every_key_and_legislature_lq():
    keys = draft_source()["keys"]
    for t in ("service", "court", "legislature", "procurement"):
        allowed = json.loads(read(f"tools/work_types/{t}.json"))["allowed_drafts"]
        assert allowed == keys, t
    assert "lq" in json.loads(read("tools/work_types/legislature.json"))["allowed_drafts"]
