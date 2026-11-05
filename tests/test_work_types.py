"""C33 (04.11.2026): work categories tools/work_types/<id>.json (tools/work_type.py).
Run: python3 -m pytest -q tests/test_work_types.py"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import work_type as W  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def test_four_types_load():
    assert W.type_ids() == ["court", "legislature", "procurement", "service"]
    st = {t["id"]: t["status"] for t in W.list_types()}
    assert st == {"service": "ready", "court": "ready", "legislature": "rules_pending", "procurement": "rules_pending"}
    assert W.load("legislature")["label"] == "विधिमंडळ कामकाज"


def test_default_and_blank_is_service():
    assert W.load()["id"] == "service" and W.load("")["id"] == "service" and W.load(" court ")["id"] == "court"


@pytest.mark.parametrize("bad", ["nope", "../desks/law-desk6", "SERVICE", 5])
def test_unknown_id(bad):
    with pytest.raises(ValueError):
        W.load(bad)


def test_default_drafts():
    assert W.default_drafts("service") == ["letter"]
    assert W.default_drafts("court") == ["letter", "parawise"]
    for t in W.type_ids():
        assert set(W.default_drafts(t)) <= set(W.DRAFT_KEYS)


def test_check_ok_and_cli():
    assert W.check() == []
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "work_type.py"), "check"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "WORK TYPES OK" in r.stdout
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "work_type.py"), "prompt", "unknown"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "Work type: service" in r.stdout


def test_prompt_block_ready():
    b = W.prompt_block("court")
    assert "status ready" in b and "Step 4b" in b and "पडताळणी अपूर्ण" not in b


@pytest.mark.parametrize("tid,label", [("legislature", "विधिमंडळ कामकाज"), ("procurement", "खरेदी विषयक बाबी")])
def test_prompt_block_pending(tid, label):
    b = W.prompt_block(tid)
    warn = f"पडताळणी अपूर्ण — {label}: या श्रेणीचे स्वतंत्र नियम/नमुने अजून नाहीत; सर्वसाधारण नोंद तयार केली"
    assert W.load(tid)["pending_warning"] == warn
    assert warn in b and "## Work type: service" not in b and "INSTRUCTIONS.md" in b   # service rules appended


def test_problems_detects_bad_shape(tmp_path):
    t = dict(W.load("legislature"))
    assert W.problems(t) == []
    assert any("status" in p for p in W.problems(dict(t, status="done")))
    assert any("unknown draft" in p for p in W.problems(dict(t, default_drafts=["x"])))
    assert any("pending_warning" in p for p in W.problems(dict(t, pending_warning="ok")))
    assert any("rules_file" in p for p in W.problems(dict(t, rules_file="tools/work_rules/none.md")))
    assert any("allowed" in p for p in W.problems(dict(t, allowed_drafts=["memo"])))


def test_new_type_by_files_only(tmp_path, monkeypatch):
    d = tmp_path / "work_types"
    d.mkdir()
    for f in os.listdir(W.TYPE_DIR):
        (d / f).write_text(open(os.path.join(W.TYPE_DIR, f), encoding="utf-8").read(), encoding="utf-8")
    new = dict(W.load("procurement"), id="rti", label="माहिती अधिकार")
    (d / "rti.json").write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(W, "TYPE_DIR", str(d))
    assert "rti" in W.type_ids() and W.load("rti")["label"] == "माहिती अधिकार" and W.check() == []
    (d / "bad.json").write_text(json.dumps(dict(new, id="other")), encoding="utf-8")
    assert any("file name" in p for p in W.check())


def test_draft_keys_from_one_source():
    """audit 05.11 R-F9: DRAFT_KEYS come from tools/draft_keys.json (16 keys); every type allows them all, so the 8 new
    keys (04.11.2026) are allowed and legislature allows lq."""
    src = json.load(open(os.path.join(ROOT, "tools", "draft_keys.json"), encoding="utf-8"))["keys"]
    assert list(W.DRAFT_KEYS) == src and len(src) == 16
    for t in W.type_ids():
        assert W.load(t)["allowed_drafts"] == src
    assert "lq" in W.load("legislature")["allowed_drafts"]
    assert W.problems(dict(W.load("service"), allowed_drafts=src + ["nope"]))   # unknown key still refused
