"""tool_docs.py <workdir> [<case-meta.json>] — write the tool docstrings for the engine prompt.

Owner 04.11.2026 ("इंजिन सूचनेचा आकार हा सूचनेनुसार असावा" → "हो करा"): the prompt carries only the docstrings of the tools
the ticked drafts need. Always: the noting / letter / Study / package / checking tools. Only when ticked: order tools
(gr, corrigendum, circular, memo, notification, endorsement, office_order, press_note, addendum), parawise tools
(parawise, affidavit — the affidavit reply defaults to parawise.paras), affidavit tools, LQ tools.
case-meta `outputs` missing / null (old style: the engine decides the drafts) -> every tool.

Writes <workdir>/TOOL_DOCS.md (selected, goes into the prompt) and <workdir>/TOOL_DOCS_ALL.md (every tool, for a real doubt).
A tool file that is absent is skipped. Prints the selected tool names and sizes.
"""
import ast
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = ("mkdocs", "build_note_letter", "build_study", "pkg3", "highlight", "lint_spec", "verify_outputs", "extract_check",
        "oldcases_text")
ORDER_KEYS = {"gr", "corrigendum", "circular", "memo", "notification", "endorsement", "office_order", "press_note", "addendum"}
GROUPS = (
    (ORDER_KEYS, ("build_order", "lint_order")),
    ({"parawise", "affidavit"}, ("build_parawise", "lint_parawise")),
    ({"affidavit"}, ("build_affidavit", "lint_affidavit")),
    ({"lq"}, ("build_lq", "lint_lq")),
)
ALL = CORE + tuple(t for _, ts in GROUPS for t in ts)


def select(outputs):
    """outputs (list of draft keys, or None = decide in the run) -> tool names in prompt order."""
    if outputs is None:
        return list(ALL)
    keys = set(outputs)
    picked = list(CORE)
    for need, tools in GROUPS:
        if keys & need:
            picked += [t for t in tools if t not in picked]
    return picked


def doc(name, tools_dir=HERE):
    p = os.path.join(tools_dir, f"{name}.py")
    if not os.path.exists(p):
        return None
    return ast.get_docstring(ast.parse(io.open(p, encoding="utf-8").read())) or ""


def write(path, names, tools_dir=HERE):
    n = 0
    with io.open(path, "w", encoding="utf-8") as out:
        for t in names:
            d = doc(t, tools_dir)
            if d is None:
                continue
            block = f"### tools/{t}.py\n{d}\n\n"
            out.write(block)
            n += len(block.encode("utf-8"))
    return n


def outputs_of(meta_path):
    try:
        meta = json.load(open(meta_path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    o = meta.get("outputs")
    return o if isinstance(o, list) else None


def main(argv):
    if len(argv) < 2:
        print(__doc__.splitlines()[0], file=sys.stderr)
        return 2
    work = argv[1]
    outputs = outputs_of(argv[2]) if len(argv) > 2 else None
    names = select(outputs)
    n_sel = write(os.path.join(work, "TOOL_DOCS.md"), names)
    n_all = write(os.path.join(work, "TOOL_DOCS_ALL.md"), ALL)
    print(f"tool_docs: outputs={outputs} -> {len(names)} tools, {n_sel} bytes in the prompt (all {n_all})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
