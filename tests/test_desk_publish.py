"""tools/desk_publish.py — App B run outputs -> upload list + case_files rows for the artifact-mode page."""
import base64, json, os, subprocess, sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "desk_publish.py")
PRE = "CR9_2026"
PROP = "11ae057d-प्रस्ताव CR 9.pdf"
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"   # desk_publish never parses it


def run(*a):
    return subprocess.run([sys.executable, TOOL, *a], cwd=ROOT, capture_output=True, text=True)


@pytest.fixture
def full(tmp_path):
    out, work = tmp_path / "out", tmp_path / "work"
    out.mkdir(); work.mkdir()
    (out / "प्रस्ताव CR 9.pdf").write_bytes(PDF)
    (out / f"{PRE}_Note_and_Letter.pdf").write_bytes(b"%PDF preview")          # preview: ignored
    (out / f"{PRE}_Study.docx").write_bytes(os.urandom(5000))
    (out / f"{PRE}_Note_and_Letter.docx").write_bytes(os.urandom(7000))
    (out / f"{PRE}_Order_Draft.docx").write_bytes(os.urandom(100))
    (work / "spec.json").write_text("{}", encoding="utf-8")
    (work / "enclosures.json").write_text("[]", encoding="utf-8")
    json.dump({"state": "done", "summary": "स", "letter_needed": True, "essential_points": ["अ"], "prefix": PRE,
               "grs_attached": [], "grs_missing": [], "warnings": ["पडताळणी अपूर्ण — x", " "]},
              open(out / "status.json", "w", encoding="utf-8"), ensure_ascii=False)
    files = [{"id": 3, "case_id": 7, "kind": "proposal", "original_name": PROP, "version": 1, "created_at": "2026-11-07"},
             {"id": 4, "case_id": 7, "kind": "study", "original_name": "old.docx", "version": 2, "created_at": "2026-11-07"},
             {"id": 5, "case_id": 8, "kind": "note_letter", "original_name": "x", "version": 9, "created_at": "2026-11-07"}]
    fp = tmp_path / "files.json"; json.dump(files, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    return out, work, fp, tmp_path / "sync"


def test_full_run_plan_and_rows(full):
    out, work, fp, sync = full
    r = run("plan", "7", str(out), "21", str(sync), "--files", str(fp), "--next-id", "40", "--work", str(work))
    assert r.returncode == 0, r.stderr
    assert "--next-id is ignored" in r.stderr                                       # old flag accepted, warned
    pl = json.load(open(sync / "plan.json", encoding="utf-8"))
    rows = pl["rows"]
    assert "seq_next" not in pl and all("id" not in x for x in rows)                # ids only at `rows` time
    # package first, spec last; versions per kind of THIS case only (case 8's note_letter v9 ignored)
    assert [(x["kind"], x["version"]) for x in rows] == [
        ("package_pdf", 1), ("study", 3), ("note_letter", 1), ("order_draft", 1), ("spec", 1), ("spec", 1)]
    assert rows[0]["name"] == "प्रस्ताव CR 9.pdf" and rows[0]["store"] == "asset"   # §4.16: prefix stripped
    assert rows[1]["store"] == "asset_parts"                                         # docx -> base64 text parts
    up = json.load(open(sync / "uploads.json", encoding="utf-8"))
    assert {u["type"] for u in up} == {"application/pdf", "text/plain"}   # contract: only a PDF <= 19 MiB is direct
    assert all(x["store"] == "asset_parts" for x in rows[1:])
    assert len({p for x in rows for p in x["paths"]}) == len(up)            # spec.json / enclosures.json parts distinct
    assert (sync / "uploads.txt").read_text(encoding="utf-8").splitlines() == [u["path"] for u in up]
    patch = json.load(open(sync / "run_patch.json", encoding="utf-8"))
    assert patch["state"] == "done" and patch["letter_needed"] is True and patch["warnings"] == ["पडताळणी अपूर्ण — x"]
    assert patch["summary"] == "स"                                          # grs_missing [] -> summary unchanged
    st = json.load(open(out / "status.json", encoding="utf-8")); st["grs_missing"] = ["दि. 01.02.2020 शा.नि."]
    json.dump(st, open(out / "status.json", "w", encoding="utf-8"), ensure_ascii=False)
    assert run("plan", "7", str(out), "21", str(sync), "--files", str(fp), "--work", str(work)).returncode == 0
    patch = json.load(open(sync / "run_patch.json", encoding="utf-8"))
    assert patch["summary"] == "GR मिळाले नाहीत: दि. 01.02.2020 शा.नि. — स"   # §4.46: shown first
    # parts decode back to the exact docx bytes
    parts = rows[2]["paths"]
    assert base64.b64decode("".join(open(p, encoding="ascii").read() for p in parts)) == \
        (out / f"{PRE}_Note_and_Letter.docx").read_bytes()
    ids = {os.path.basename(u["path"]): f"{i:032x}" for i, u in enumerate(up)}
    ap = sync / "assets.json"; json.dump(ids, open(ap, "w"))
    r = run("rows", str(sync), "--assets", str(ap), "--first-id", "41", "--now", "2026-11-07T10:00:00+00:00")
    assert r.returncode == 0, r.stderr
    w = json.load(open(sync / "writes.json", encoding="utf-8"))
    assert [x["data"]["id"] for x in w] == [41, 43, 45, 47, 49, 51]                 # odd ids, step 2
    assert "41,43,45,47,49,51" in r.stderr
    # a refused create -> renumber with the same assets, no re-upload
    r2 = run("rows", str(sync), "--assets", str(ap), "--first-id", "55")
    assert r2.returncode == 0, r2.stderr
    w2 = json.load(open(sync / "writes.json", encoding="utf-8"))
    assert [x["doc_id"] for x in w2] == ["55", "57", "59", "61", "63", "65"]
    assert [x["data"]["storage_path"] for x in w2] == [x["data"]["storage_path"] for x in w]
    w = json.load(open(sync / "writes.json", encoding="utf-8"))
    assert all(x["op"] == "set" and x["collection"] == "case_files" and "if_version" not in x for x in w)
    assert w[0]["data"]["asset_parts"] is None and w[0]["data"]["content_type"] == "application/pdf"
    assert w[1]["data"]["asset_id"] is None and w[1]["data"]["size_bytes"] == 5000
    assert w[0]["doc_id"] == "55" and w[0]["data"]["storage_path"] == f"asset:{0:032x}" and w[0]["data"]["case_id"] == 7
    assert w[2]["data"]["asset_parts"] and w[2]["data"]["storage_path"] == f"asset-parts:{len(w[2]['data']['asset_parts'])}"
    assert json.loads(r.stdout)[1] == {"kind": "study", "name": f"{PRE}_Study.docx", "version": 3}


def test_missing_asset_id_writes_nothing(full):
    out, work, fp, sync = full
    assert run("plan", "7", str(out), "21", str(sync), "--files", str(fp), "--work", str(work)).returncode == 0
    ap = sync / "assets.json"; json.dump({}, open(ap, "w"))
    r = run("rows", str(sync), "--assets", str(ap), "--first-id", "1")
    assert r.returncode != 0 and not (sync / "writes.json").exists()


def test_rows_refuses_even_or_missing_first_id(full):
    out, work, fp, sync = full
    assert run("plan", "7", str(out), "21", str(sync), "--files", str(fp), "--work", str(work)).returncode == 0
    up = json.load(open(sync / "uploads.json", encoding="utf-8"))
    ap = sync / "assets.json"; json.dump({os.path.basename(u["path"]): "a" * 32 for u in up}, open(ap, "w"))
    r = run("rows", str(sync), "--assets", str(ap), "--first-id", "40")
    assert r.returncode != 0 and "even" in r.stderr and not (sync / "writes.json").exists()
    assert run("rows", str(sync), "--assets", str(ap)).returncode != 0


def test_package_name_given_and_proposal_with_grs_refused(full):
    out, work, fp, sync = full
    r = run("plan", "7", str(out), "21", str(sync), "--files", str(fp), "--work", str(work),
            "--package-name", "प्रस्ताव CR 9 (मूळ).pdf")
    assert r.returncode == 0, r.stderr
    assert json.load(open(sync / "plan.json", encoding="utf-8"))["rows"][0]["name"] == "प्रस्ताव CR 9 (मूळ).pdf"
    r = run("plan", "7", str(out), "21", str(sync), "--files", str(fp), "--package-name", "CR9_2026_Proposal_with_GRs.pdf")
    assert r.returncode != 0 and "_Proposal_with_GRs.pdf" in r.stderr


def test_unknown_kind_refused(full):
    out, work, fp, sync = full
    r = run("plan", "7", str(out), "22", str(sync), "--files", str(fp), "--kinds", "note_leter")
    assert r.returncode != 0 and "unknown --kinds" in r.stderr


def test_missing_main_output_fails(full):
    out, work, fp, sync = full
    os.remove(out / f"{PRE}_Study.docx")
    r = run("plan", "7", str(out), "21", str(sync), "--files", str(fp))
    assert r.returncode != 0 and "_Study.docx" in r.stderr


def test_edit_run_kinds_and_add(full, tmp_path):
    out, work, fp, sync = full
    gr = tmp_path / "201805171732241512.pdf"; gr.write_bytes(PDF)
    r = run("plan", "7", str(out), "22", str(sync), "--files", str(fp), "--work", str(work),
            "--kinds", "note_letter", "--add", f"gr={gr}")
    assert r.returncode == 0, r.stderr
    rows = json.load(open(sync / "plan.json", encoding="utf-8"))["rows"]
    assert [x["kind"] for x in rows] == ["note_letter", "gr", "spec", "spec"]
    assert not (sync / "run_patch.json").exists()   # edit run: the worker writes edit_result itself


def test_office_run(tmp_path):
    """INSTRUCTIONS §4.48 / DESK_WORKER §3b: every office output file -> one office_output row, version per name."""
    out = tmp_path / "out"; out.mkdir(); (out / "preview").mkdir()
    (out / "जिल्हानिहाय_विवरण.xlsx").write_bytes(os.urandom(3000))
    (out / "आढावा.pptx").write_bytes(os.urandom(2000))
    (out / "विवरण.pdf").write_bytes(PDF)
    (out / "preview" / "x.pdf").write_bytes(PDF)          # previews / other files are not outputs
    (out / "notes.txt").write_text("x", encoding="utf-8")
    json.dump({"state": "done", "summary": "स" * 2500, "letter_needed": True, "essential_points": ["अ"],
               "grs_missing": ["x"], "warnings": ["पडताळणी अपूर्ण — y", ""]},
              open(out / "status.json", "w", encoding="utf-8"), ensure_ascii=False)
    files = [{"id": 3, "case_id": 9, "kind": "office_output", "original_name": "जिल्हानिहाय_विवरण.xlsx", "version": 2},
             {"id": 5, "case_id": 9, "kind": "template", "original_name": "नमुना.xlsx", "version": 1},
             {"id": 7, "case_id": 4, "kind": "office_output", "original_name": "आढावा.pptx", "version": 5}]
    fp = tmp_path / "files.json"; json.dump(files, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    sync = tmp_path / "sync"
    r = run("plan", "9", str(out), "31", str(sync), "--files", str(fp), "--office")
    assert r.returncode == 0, r.stderr
    rows = json.load(open(sync / "plan.json", encoding="utf-8"))["rows"]
    got = {x["name"]: (x["kind"], x["version"], x["store"], x["content_type"]) for x in rows}
    assert got == {
        "जिल्हानिहाय_विवरण.xlsx": ("office_output", 3, "asset_parts",
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "आढावा.pptx": ("office_output", 1, "asset_parts",          # case 4's row is another case
                       "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "विवरण.pdf": ("office_output", 1, "asset", "application/pdf")}
    patch = json.load(open(sync / "run_patch.json", encoding="utf-8"))
    assert patch["letter_needed"] is None and patch["essential_points"] == [] and patch["grs_missing"] == []
    assert patch["grs_attached"] == [] and patch["case"] is None and patch["state"] == "done" and patch["step"] == "तयार"
    assert len(patch["summary"]) == 2000 and patch["warnings"] == ["पडताळणी अपूर्ण — y"]
    up = json.load(open(sync / "uploads.json", encoding="utf-8"))
    ap = sync / "assets.json"; json.dump({os.path.basename(u["path"]): f"{i:032x}" for i, u in enumerate(up)}, open(ap, "w"))
    r = run("rows", str(sync), "--assets", str(ap), "--first-id", "11")
    assert r.returncode == 0, r.stderr
    w = json.load(open(sync / "writes.json", encoding="utf-8"))
    assert [x["data"]["kind"] for x in w] == ["office_output"] * 3 and [x["data"]["id"] for x in w] == [11, 13, 15]
    # answer only (outputs []): no file -> 0 rows, run_patch still written; proposal flags refused with --office
    for f in ("जिल्हानिहाय_विवरण.xlsx", "आढावा.pptx", "विवरण.pdf"):
        os.remove(out / f)
    r = run("plan", "9", str(out), "32", str(sync), "--files", str(fp), "--office")
    assert r.returncode == 0 and json.load(open(sync / "plan.json", encoding="utf-8"))["rows"] == []
    assert (sync / "run_patch.json").exists()
    r = run("plan", "9", str(out), "32", str(sync), "--files", str(fp), "--office", "--kinds", "study")
    assert r.returncode != 0 and "--office" in r.stderr
