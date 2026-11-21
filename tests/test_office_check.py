"""Office tasks (INSTRUCTIONS §4.48, Abhi 20.11.2026): tools/office_fonts.py (fonts + metadata fixer), tools/office_check.py
(output checks), tools/office_work.json. Run: python3 -m pytest -q tests/test_office_check.py"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import office_check as OC  # noqa: E402
import office_fonts as OF  # noqa: E402

docx = pytest.importorskip("docx")
openpyxl = pytest.importorskip("openpyxl")
pptx = pytest.importorskip("pptx")
pymupdf = pytest.importorskip("pymupdf")
CHECK = os.path.join(ROOT, "tools", "office_check.py")
FIX = os.path.join(ROOT, "tools", "office_fonts.py")
HAS_SOFFICE = bool(shutil.which("soffice") or shutil.which("libreoffice"))


def make_docx(p, text="सदर माहिती Annual report"):
    d = docx.Document(); d.add_paragraph(text); d.add_heading("शीर्षक", 1)
    d.sections[0].header.paragraphs[0].text = "कार्यालय"
    d.save(p)


def make_xlsx(p, check_sheet=True, div0=False):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "विवरण"
    ws.append(["जिल्हा", "पदे", "Total"]); ws.append(["पुणे", 5, "=B2*2"]); ws.append(["Mumbai", 3, "=B3/0" if div0 else "=B3*2"])
    ws.append(["एकूण", "=SUM(B2:B3)", "=SUM(C2:C3)"])
    if check_sheet:
        v = wb.create_sheet("पडताळणी"); v.append(["आकडा", "स्रोत"]); v.append(["विवरण!B2", "पत्र.pdf पृ. 1"])
    wb.save(p)


def make_pptx(p, text="Figures 2026"):
    pr = pptx.Presentation(); s = pr.slides.add_slide(pr.slide_layouts[1])
    s.shapes.title.text = "आढावा"; s.placeholders[1].text = text
    pr.save(p)


def make_pdf(p, text="Statement"):
    d = pymupdf.open(); d.new_page().insert_text((72, 72), text); d.set_metadata({"producer": "PyMuPDF"}); d.save(p)


def run_check(outdir, *a):
    return subprocess.run([sys.executable, CHECK, str(outdir), *a], capture_output=True, text=True,
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=600)


def levels(res, check_part, fname=None):
    return [r["level"] for r in res if check_part in r["check"] and (fname is None or r["file"] == fname)]


def test_config():
    c = json.load(open(os.path.join(ROOT, "tools", "office_work.json"), encoding="utf-8"))
    assert c["work_type"] == "office" and c["label"] == "कार्यालयीन काम" and c["output_kind"] == "office_output"
    assert c["outputs"] == {"xlsx": "Excel", "docx": "Word", "pptx": "PPT", "pdf": "PDF"}
    assert c["input_kinds"] == ["extra_doc", "template"] and c["check_sheet"] == OC.CHECK_SHEET
    assert c["steps"] == ["फाइल्स वाचत आहे", "माहिती जुळवत आहे", "फाइल तयार करत आहे", "तपासणी चालू"]
    assert c["fonts"]["docx_rfonts"] == OF.DOCX_FONTS and os.path.isfile(os.path.join(ROOT, c["rules_file"]))
    import build_affidavit   # the same Word font rule as the affidavit (C7) — one definition
    assert build_affidavit.FONTS == OF.DOCX_FONTS
    import work_type   # office is NOT a proposal category
    assert "office" not in work_type.type_ids()


def test_fixer_docx_pptx_pdf(tmp_path):
    make_docx(tmp_path / "a.docx"); make_pptx(tmp_path / "b.pptx"); make_pdf(tmp_path / "c.pdf")
    OC.run(str(tmp_path))
    res = list(OC.results)
    assert levels(res, "fonts", "a.docx") == ["FAIL"] and levels(res, "fonts", "b.pptx") == ["FAIL"]
    assert levels(res, "metadata", "a.docx") == ["FAIL"] and levels(res, "metadata", "c.pdf") == ["FAIL"]
    for f in ("a.docx", "b.pptx", "c.pdf"):
        OF.fix_file(str(tmp_path / f))
    OC.run(str(tmp_path))
    res = list(OC.results)
    assert [r for r in res if r["level"] == "FAIL"] == []
    # every run carries the decided fonts; the files still open
    d = docx.Document(str(tmp_path / "a.docx"))
    # the common rule (§4.49): the mixed run is split — Marathi DVOT-SurekhMR on all four, English ascii/hAnsi TNR
    from docx.oxml.ns import qn
    got = [(r.text, {k: r._element.rPr.rFonts.get(qn("w:" + k)) for k in OF.DOCX_FONTS}) for r in d.paragraphs[0].runs]
    assert got == [("सदर माहिती ", {k: OF.COMPLEX for k in OF.DOCX_FONTS}), ("Annual report", OF.DOCX_FONTS)], got
    with zipfile.ZipFile(tmp_path / "b.pptx") as z:
        x = z.read("ppt/slides/slide1.xml").decode()
        th = z.read("ppt/theme/theme1.xml").decode()
    assert '<a:latin typeface="Times New Roman"/><a:cs typeface="DVOT-SurekhMR"/>' in x
    assert 'script="Deva" typeface="DVOT-SurekhMR"' in th
    # second run changes nothing (idempotent)
    assert OF.fix_file(str(tmp_path / "a.docx"))["fonts"] == 0 and OF.fix_file(str(tmp_path / "b.pptx"))["fonts"] == 0


def test_fixer_xlsx_fonts_by_script(tmp_path):
    p = tmp_path / "v.xlsx"; make_xlsx(p)
    assert OC.xlsx_font_problems(str(p))
    OF.fix_file(str(p))
    assert OC.xlsx_font_problems(str(p)) == []
    wb = openpyxl.load_workbook(p); ws = wb["विवरण"]
    assert ws["A2"].font.name == "DVOT-SurekhMR" and ws["B2"].font.name == "Times New Roman"
    assert ws["C2"].value == "=B2*2" and ws["C3"].font.name == "Times New Roman"   # formulas kept
    with zipfile.ZipFile(p) as z:
        assert 'fullCalcOnLoad="1"' in z.read("xl/workbook.xml").decode()
    assert OF.fix_file(str(p))["fonts"] == 0
    assert OC.office_meta_problems(str(p)) == []


@pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice not installed")
def test_check_cli_all_ok_and_fail(tmp_path):
    out = tmp_path / "out"; out.mkdir()
    make_xlsx(out / "जिल्हानिहाय_विवरण.xlsx"); make_docx(out / "टिप्पणी.docx"); make_pptx(out / "आढावा.pptx")
    make_pdf(out / "विवरण.pdf")
    (out / "status.json").write_text("{}", encoding="utf-8")
    (out / "preview").mkdir(); make_pdf(out / "preview" / "x.pdf")          # previews are not outputs
    r = subprocess.run([sys.executable, FIX, *[str(out / f) for f in os.listdir(out) if f.endswith(OC.OUT_EXT)]],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    jp = tmp_path / "res.json"
    r = run_check(out, "--json", str(jp), "--expect", "xlsx,docx,pptx,pdf")
    assert r.returncode == 0 and r.stdout.strip().endswith("ALL OK"), r.stdout
    res = json.load(open(jp, encoding="utf-8"))
    assert {x["file"] for x in res} == {"जिल्हानिहाय_विवरण.xlsx", "टिप्पणी.docx", "आढावा.pptx", "विवरण.pdf"}
    assert levels(res, "recalculated") == ["OK"]
    # an error value after recalculation, a missing पडताळणी sheet, an asked type missing -> FAIL, exit 1
    make_xlsx(out / "जिल्हानिहाय_विवरण.xlsx", check_sheet=False, div0=True); OF.fix_file(str(out / "जिल्हानिहाय_विवरण.xlsx"))
    os.remove(out / "आढावा.pptx")
    r = run_check(out, "--json", str(jp), "--expect", "xlsx,pptx")
    assert r.returncode == 1 and "ALL OK" not in r.stdout
    res = json.load(open(jp, encoding="utf-8"))
    assert any("#DIV/0!" in x["detail"] for x in res if x["level"] == "FAIL")
    assert levels(res, "पडताळणी") == ["FAIL"]
    assert [x["hard"] for x in res if x["check"] == "asked output present"] == [True]


def test_ai_trace_is_hard_and_unreadable_is_hard(tmp_path):
    make_docx(tmp_path / "a.docx", "हा मसुदा Claude ने तयार केला"); OF.fix_file(str(tmp_path / "a.docx"))
    make_pptx(tmp_path / "b.pptx", "engine number list"); OF.fix_file(str(tmp_path / "b.pptx"))
    (tmp_path / "c.xlsx").write_bytes(b"not a zip")
    OC.run(str(tmp_path))
    res = list(OC.results)
    ai = [x for x in res if x["file"] == "a.docx" and x["check"] == "no AI trace in the text"]
    assert ai[0]["level"] == "FAIL" and ai[0]["hard"]
    assert levels(res, "working / automation", "b.pptx") == ["WARN"]                 # a generic word -> WARN only
    assert [x["hard"] for x in res if x["file"] == "c.xlsx" and x["check"] == "opens"] == [True]


def test_no_outputs_and_bad_expect(tmp_path):
    r = run_check(tmp_path)
    assert r.returncode == 0 and "no output files" in r.stdout and "ALL OK" in r.stdout
    assert run_check(tmp_path, "--expect", "csv").returncode == 2
