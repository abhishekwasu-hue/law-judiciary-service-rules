"""tools/case_state.py — save / load / list keep one proposal's state so a correction round never re-reads it."""
import json, os, subprocess, sys, shutil

import pytest

try:
    import pymupdf
except ImportError:   # save / load / _localise need no pymupdf; only the page count does
    pymupdf = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "case_state.py")
SAMPLE = os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json")
CID = "_TEST_case_state"
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def pdf(path, pages=1):
    if pymupdf is None:
        open(path, "wb").write(PDF + b"%" + str(pages).encode() + b"\n"); return
    d = pymupdf.open()
    for _ in range(pages):
        d.new_page()
    d.save(path)


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "work"; w.mkdir()
    shutil.copy(SAMPLE, w / "spec.json")
    ext = tmp_path / "outside.pdf"
    pdf(ext)
    (w / "enclosures.json").write_text(json.dumps([{"path": str(ext), "pages": "1", "label": "x", "marks": []}]),
                                      encoding="utf-8")
    prop = tmp_path / "prop.pdf"
    pdf(prop, 2)
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
    assert meta["prefix"] == "T" and meta["proposal_pages"] == (2 if pymupdf else None)
    enc = json.load(open(os.path.join(cdir, "enclosures.json"), encoding="utf-8"))
    assert enc[0]["path"] == f"cases/{CID}/src/outside.pdf"          # outside source copied in, path repo-relative
    assert os.path.exists(os.path.join(ROOT, enc[0]["path"]))
    out = tmp_path / "loaded"
    assert run("load", CID, str(out)).returncode == 0
    assert (out / "spec.json").exists() and (out / "proposal.pdf").exists()
    assert CID in run("list").stdout


def test_save_requires_spec(tmp_path):
    w = tmp_path / "w"; w.mkdir()
    p = tmp_path / "p.pdf"; pdf(p)
    r = run("save", CID, "--work", str(w), "--proposal", str(p), "--package-name", "p.pdf", "--prefix", "T")
    assert r.returncode != 0
    shutil.rmtree(os.path.join(ROOT, "cases", CID), ignore_errors=True)


def test_src_basename_collision(work, tmp_path):
    """W-M8: two different outside files with one basename never overwrite each other; same content is reused."""
    w, prop = work
    a, b = tmp_path / "a", tmp_path / "b"; a.mkdir(); b.mkdir()
    (a / "gr.pdf").write_bytes(PDF + b"%A\n"); (b / "gr.pdf").write_bytes(PDF + b"%B\n")
    c = tmp_path / "c"; c.mkdir(); (c / "gr.pdf").write_bytes(PDF + b"%A\n")   # same bytes as a/gr.pdf
    enc = [{"path": str(x / "gr.pdf"), "pages": "1", "label": "x", "marks": []} for x in (a, b, c)]
    (w / "enclosures.json").write_text(json.dumps(enc), encoding="utf-8")
    r = run("save", CID, "--work", str(w), "--proposal", str(prop), "--package-name", "p.pdf", "--prefix", "T")
    assert r.returncode == 0, r.stderr
    got = [e["path"] for e in json.load(open(os.path.join(ROOT, "cases", CID, "enclosures.json"), encoding="utf-8"))]
    assert got[0] == f"cases/{CID}/src/gr.pdf" and got[2] == got[0]
    assert got[1] != got[0] and got[1].startswith(f"cases/{CID}/src/gr~") and got[1].endswith(".pdf")
    assert open(os.path.join(ROOT, got[0]), "rb").read().endswith(b"%A\n")
    assert open(os.path.join(ROOT, got[1]), "rb").read().endswith(b"%B\n")


def test_rebuild_passes_verify_args_and_lint_baseline(work, tmp_path, monkeypatch):
    """W-M3 / W-M5: rebuild forwards --original-name / --desk / --case-meta to verify and uses lint_compare with
    --lint-baseline (commands recorded, nothing built)."""
    w, prop = work
    assert run("save", CID, "--work", str(w), "--proposal", str(prop), "--package-name", "p.pdf",
               "--prefix", "T").returncode == 0
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import case_state as CS
    cmds = []
    monkeypatch.setattr(CS, "_run", lambda c: cmds.append(c) or 0)
    out = tmp_path / "out"; out.mkdir(); pdf(out / "p.pdf")   # existing package: no pkg3 run
    base = tmp_path / "before.json"; shutil.copy(SAMPLE, base)
    assert CS.rebuild([CID, str(out), "--original-name", "प्रस्ताव.pdf", "--desk", "law-desk6",
                       "--case-meta", str(tmp_path / "m.json"), "--lint-baseline", str(base)]) == 0
    assert os.path.basename(cmds[0][1]) == "lint_compare.py" and cmds[0][2] == str(base)
    v = cmds[-1]
    assert os.path.basename(v[1]) == "verify_outputs.py"
    assert v[-6:] == ["--original-name", "प्रस्ताव.pdf", "--desk", "law-desk6", "--case-meta", str(tmp_path / "m.json")]
    cmds.clear()
    assert CS.rebuild([CID, str(out)]) == 0
    assert os.path.basename(cmds[0][1]) == "lint_spec.py" and "--original-name" not in cmds[-1]
