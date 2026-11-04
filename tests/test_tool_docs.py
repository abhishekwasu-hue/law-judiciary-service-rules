"""tools/tool_docs.py — prompt carries only the docstrings of the ticked drafts' tools (owner 04.11.2026)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import tool_docs as TD  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_letter_only_core():
    assert TD.select(["letter"]) == list(TD.CORE)
    assert TD.select([]) == list(TD.CORE)


def test_groups():
    assert "build_order" in TD.select(["gr"]) and "build_lq" not in TD.select(["gr"])
    a = TD.select(["affidavit"])
    assert {"build_affidavit", "lint_affidavit", "build_parawise", "lint_parawise"} <= set(a)
    assert {"build_lq", "lint_lq"} <= set(TD.select(["lq"]))
    assert "build_order" in TD.select(["endorsement"])


def test_none_means_all():
    assert TD.select(None) == list(TD.ALL)


def test_cli_sizes(tmp_path):
    meta = tmp_path / "m.json"
    meta.write_text(json.dumps({"outputs": ["letter"]}), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "tool_docs.py"), str(tmp_path), str(meta)],
                       capture_output=True, text=True, check=True)
    sel = (tmp_path / "TOOL_DOCS.md").read_bytes()
    full = (tmp_path / "TOOL_DOCS_ALL.md").read_bytes()
    assert b"tools/build_lq.py" not in sel and b"tools/build_lq.py" in full and b"tools/mkdocs.py" in sel
    assert len(sel) < len(full) - 30000
    # no meta file -> every tool
    subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "tool_docs.py"), str(tmp_path), str(tmp_path / "x.json")],
                   capture_output=True, text=True, check=True)
    assert (tmp_path / "TOOL_DOCS.md").read_bytes() == full
