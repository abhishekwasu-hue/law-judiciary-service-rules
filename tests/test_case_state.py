"""tools/case_state.py — save / load / list keep one proposal's state so a correction round never re-reads it."""
import json, os, subprocess, sys, shutil

import pymupdf
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "case_state.py")
SAMPLE = os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json")
CID = "_TEST_case_state"


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "work"; w.mkdir()
    shutil.copy(SAMPLE, w / "spec.json")
    ext = tmp_path / "outside.pdf"
    d = pymupdf.open(); d.new_page(); d.save(ext)
    (w / "enclosures.json").write_text(json.dumps([{"path": str(ext), "pages": "1", "label": "x", "marks": []}]),
                                      encoding="utf-8")
    prop = tmp_path / "prop.pdf"
    d = pymupdf.open(); d.new_page(); d.new_page(); d.save(prop)
    yield w, prop
    shutil.rmtree(os.path.join(ROOT, "cases", CID), ignore_errors=True)


def run(*a):
    return subprocess.run([sys.executable, TOOL, *a], cwd=ROOT, capture_output=True, text=True)


def test_save_load_list(work, tmp_path):
    w, prop = work
    r = run("save", CID, "--work", str(w), "--proposal", str(prop), "--package-name", "p.pdf", "--prefix", "T")
    assert r.returncode == 0, r.stderr
    cdir = os.path.join(ROOT, "cases", CID)
    meta = json.load(open(os.path.join(cdir, "case.json"), encoding="utf-8"))
    assert meta["proposal_pages"] == 2 and meta["prefix"] == "T"
    enc = json.load(open(os.path.join(cdir, "enclosures.json"), encoding="utf-8"))
    assert enc[0]["path"] == f"cases/{CID}/src/outside.pdf"          # outside source copied in, path repo-relative
    assert os.path.exists(os.path.join(ROOT, enc[0]["path"]))
    out = tmp_path / "loaded"
    assert run("load", CID, str(out)).returncode == 0
    assert (out / "spec.json").exists() and (out / "proposal.pdf").exists()
    assert CID in run("list").stdout


def test_save_requires_spec(tmp_path):
    w = tmp_path / "w"; w.mkdir()
    p = tmp_path / "p.pdf"; d = pymupdf.open(); d.new_page(); d.save(p)
    r = run("save", CID, "--work", str(w), "--proposal", str(p), "--package-name", "p.pdf", "--prefix", "T")
    assert r.returncode != 0
    shutil.rmtree(os.path.join(ROOT, "cases", CID), ignore_errors=True)
