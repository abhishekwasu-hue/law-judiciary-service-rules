"""tools/desk_sync.py — chunks + assets.txt + case_patch.json for the प्रस्ताव कक्ष page."""
import base64, json, os, shutil, subprocess, sys

import pymupdf
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "desk_sync.py")
SAMPLE = os.path.join(ROOT, "samples", "specs", "CR131_2026_special-pay_info-letter.json")
CID = "_TEST_desk_sync"
PRE = "T131"


@pytest.fixture
def case(tmp_path):
    cdir = os.path.join(ROOT, "cases", CID); os.makedirs(cdir, exist_ok=True)
    shutil.copy(SAMPLE, os.path.join(cdir, "spec.json"))
    json.dump({"case_id": CID, "prefix": PRE, "package_name": "pkg.pdf"},
              open(os.path.join(cdir, "case.json"), "w", encoding="utf-8"))
    out = tmp_path / "out"; out.mkdir()
    (out / f"{PRE}_Note_and_Letter.docx").write_bytes(os.urandom(200_000))   # 266668 b64 chars -> 2 chunks
    d = pymupdf.open(); d.new_page(); d.save(out / "pkg.pdf")
    yield out, tmp_path / "sync"
    shutil.rmtree(cdir, ignore_errors=True)


def run(*a):
    return subprocess.run([sys.executable, TOOL, *a], cwd=ROOT, capture_output=True, text=True)


def test_sync_shapes(case):
    out, sync = case
    r = run(CID, str(out), str(sync))
    assert r.returncode == 0, r.stderr
    chunks = sorted(os.listdir(sync / "chunks"))
    assert chunks == [f"{CID}__note_letter__0.json", f"{CID}__note_letter__1.json"]
    docs = [json.load(open(sync / "chunks" / c, encoding="utf-8")) for c in chunks]
    assert all(d["total"] == 2 and d["kind"] == "note_letter" and d["case"] == CID for d in docs)
    assert base64.b64decode("".join(d["b64"] for d in docs)) == (out / f"{PRE}_Note_and_Letter.docx").read_bytes()
    assert (sync / "assets.txt").read_text(encoding="utf-8").splitlines() == [str(out / "pkg.pdf")]   # no N&L pdf
    p = json.load(open(sync / "case_patch.json", encoding="utf-8"))
    assert p["path"] == "chat" and p["case_id"] == CID
    assert p["outputs"] == [
        {"kind": "note_letter", "name": f"{PRE}_Note_and_Letter.docx", "store": "db", "ref": f"{CID}__note_letter"},
        {"kind": "package_pdf", "name": "pkg.pdf", "store": "asset", "ref": "__ASSET__pkg.pdf"}]
    spec = json.load(open(SAMPLE, encoding="utf-8-sig"))
    ids = {x["id"]: x for x in p["paras"]}
    assert ids["note.p1"]["label"] == "टिप्पणी परि. 2" and ids["note.p1"]["text"] == spec["note"]["paras"][0][:160]
    # sub "0" belongs to paras[0] (0-based key, as mkdocs.build_note reads it)
    assert ids["note.p1.s1"]["text"] == " ".join(spec["note"]["sub"]["0"][0].split())[:160]
    assert ids["note.p1.s1"]["label"] == "टिप्पणी परि. 2 (1)"
    assert len([i for i in ids if i.startswith("note.p") and ".s" not in i]) == len(spec["note"]["paras"])
    assert sum(1 for i in ids if ".s" in i) == sum(len(v) for v in spec["note"]["sub"].values())
    # rerun with a smaller docx: stale chunk __1 removed
    (out / f"{PRE}_Note_and_Letter.docx").write_bytes(b"x")
    assert run(CID, str(out), str(sync)).returncode == 0
    assert sorted(os.listdir(sync / "chunks")) == [f"{CID}__note_letter__0.json"]
    assert ids["letter.pt1"]["label"] == "पत्र तक्ता" and ids["letter.pt2"]["label"] == "पत्र मुद्दा 2"
    assert all(len(x["text"]) <= 160 for x in p["paras"])


def test_study_and_preview_pdf(case):
    out, sync = case
    (out / f"{PRE}_Study.docx").write_bytes(b"study")
    d = pymupdf.open(); d.new_page(); d.save(out / f"{PRE}_Note_and_Letter.pdf")
    assert run(CID, str(out), str(sync)).returncode == 0
    assert os.path.exists(sync / "chunks" / f"{CID}__study__0.json")
    assert len((sync / "assets.txt").read_text(encoding="utf-8").splitlines()) == 2
    kinds = [o["kind"] for o in json.load(open(sync / "case_patch.json", encoding="utf-8"))["outputs"]]
    assert kinds == ["note_letter", "study", "package_pdf", "note_letter_pdf"]


def test_missing(case, tmp_path):
    out, sync = case
    r = run("_no_such_case", str(out), str(sync))
    assert r.returncode != 0 and "not found" in r.stderr
    os.remove(out / f"{PRE}_Note_and_Letter.docx")
    r = run(CID, str(out), str(sync))
    assert r.returncode != 0 and "Note_and_Letter.docx" in r.stderr


def test_split_b64_roundtrip(tmp_path):
    import base64, importlib.util
    spec = importlib.util.spec_from_file_location("desk_sync", os.path.join(ROOT, "tools", "desk_sync.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.PART_CHARS = 1000
    src = tmp_path / "big.pdf"; src.write_bytes(os.urandom(2500))
    parts = m.split_b64(str(src), "C", "package_pdf", str(tmp_path / "parts"))
    assert len(parts) == 4
    joined = b"".join(base64.b64decode(open(p).read()) for p in parts)
    assert joined == src.read_bytes()
