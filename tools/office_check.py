#!/usr/bin/env python3
"""office_check.py <outdir> [--json OUT.json] [--expect xlsx,docx,pptx,pdf] — checks the outputs of an office task
(INSTRUCTIONS §4.48, tools/work_rules/office.md, docs/DESK_WORKER.md §3b). Run it after tools/office_fonts.py.

Files checked: every top-level *.xlsx / *.docx / *.pptx / *.pdf of <outdir> (the same set tools/desk_publish.py --office
uploads; status.json, files starting with "." or "~$" and the subfolder preview/ are not outputs; any other top-level file
-> WARN "not an output"). --expect = the run's `outputs`: an asked type with no file -> FAIL [HARD].

  every file  opens (FAIL [HARD] when not); AI names in its text (Claude, Anthropic, AI, LLM, GPT, Gemini -> FAIL [HARD];
              the other lint_spec AI_WORDS (model, engine, automatic, generated, मॉडेल, स्वयंचलित, प्रणालीने तयार), TODO and
              "पडताळणी अपूर्ण" -> WARN); metadata (docx: clean_meta.docx_meta_problems; xlsx / pptx: the same core rules + an
              Office-like Application, no tool name; pdf: clean_meta.pdf_meta_problems) -> FAIL.
  .docx       fonts: every text run in body, headers, footers, footnotes, endnotes and every rFonts of styles.xml (incl.
              docDefaults, which must exist) = ascii / hAnsi Times New Roman, cs / eastAsia DVOT-SurekhMR, no theme font.
  .xlsx       recalculated with LibreOffice headless (a converted copy in a temp dir; the file itself is not changed): no
              #REF! #DIV/0! #VALUE! #NAME? #N/A #NUM! #NULL! in any cell (soffice missing / conversion failed -> WARN); a
              sheet "पडताळणी" with at least 2 filled rows when any other sheet has a number or a formula; fonts: a cell with
              Devanagari text -> DVOT-SurekhMR, other filled cells -> Times New Roman (rich-text runs per run).
  .pptx       fonts: every text run / field: a:latin Times New Roman, a:cs DVOT-SurekhMR.
  .pdf        at least one page; fonts used neither Times New Roman nor DVOT-SurekhMR -> WARN (rendered with fallback fonts).
Prints one "OK: …" / "WARN: …" / "FAIL: …" / "FAIL [HARD]: …" line per check and "ALL OK" when nothing FAILs; exit 1 on a
FAIL. --json writes [{file, check, level (OK|WARN|FAIL), hard, detail}] (the worker turns every soft FAIL / WARN into a
run warning "पडताळणी अपूर्ण — <file>: <check>: <detail>"; a HARD one is fixed, never delivered)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clean_meta as CM  # noqa: E402
import office_fonts as OF  # noqa: E402
from lint_spec import AI_WORDS  # noqa: E402 — the ONE AI word list (C27 §4; verify_outputs / lint_spec use it)

OUT_EXT = (".xlsx", ".docx", ".pptx", ".pdf")
HARD_AI = ("AI", "Claude", "Anthropic", "LLM", "GPT", "Gemini")
SOFT_WORDS = [(lab, rx) for lab, rx in AI_WORDS if lab not in HARD_AI] + [
    ("TODO", re.compile(r"(?<![A-Za-z])TODO(?![A-Za-z])")), ("पडताळणी अपूर्ण", re.compile(r"पडताळणी\s+अपूर्ण"))]
XL_ERRORS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!")
TOOL_RE = re.compile(CM.TRACE_RE.pattern + r"|openpyxl|python-pptx|LibreOffice|soffice|XlsxWriter|reportlab|OpenOffice", re.I)
CHECK_SHEET = "पडताळणी"
W, A, S = OF.W, OF.A, OF.S

results = []


def rec(fname, check, problems, hard=False, level=None):
    """problems [] = OK; level WARN never fails."""
    lv = "OK" if not problems else (level or "FAIL")
    detail = "; ".join(problems[:6]) + (f"; … (+{len(problems) - 6})" if len(problems) > 6 else "")
    results.append({"file": fname, "check": check, "level": lv, "hard": bool(hard and lv == "FAIL"), "detail": detail})
    tag = "FAIL [HARD]" if hard and lv == "FAIL" else lv
    print(f"{tag}: {fname}: {check}" + (f" — {detail}" if detail else ""))


def outputs(outdir):
    """(output files, other top-level files) of outdir, sorted."""
    files, other = [], []
    for f in sorted(os.listdir(outdir)):
        p = os.path.join(outdir, f)
        if not os.path.isfile(p) or f.startswith((".", "~$")) or f == "status.json":
            continue
        (files if f.lower().endswith(OUT_EXT) else other).append(p)
    return files, other


def word_hits(text):
    hard = [lab for lab, rx in AI_WORDS if lab in HARD_AI and rx.search(text)]
    soft = [lab for lab, rx in SOFT_WORDS if rx.search(text)]
    return hard, soft


def words_check(fname, text):
    hard, soft = word_hits(text)
    rec(fname, "no AI trace in the text", [f"'{x}'" for x in hard], hard=True)
    if soft:
        rec(fname, "working / automation words", [f"'{x}'" for x in soft], level="WARN")


def zip_parts(path, pattern):
    with zipfile.ZipFile(path) as z:
        return {n: OF._parse(z.read(n)) for n in z.namelist() if re.fullmatch(pattern, n)}


def office_meta_problems(path):
    """.xlsx / .pptx: clean_meta core rules + Application without a tool name."""
    P = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "docProps/core.xml" in names:
            x = z.read("docProps/core.xml").decode("utf-8", "replace")
            for f in CM.CORE_BLANK:
                v = CM._field(x, f)
                if v:
                    P.append(f"core property {f} = '{v[:40]}' (blank)")
            for f in CM.CORE_AUTHOR:
                v = CM._field(x, f)
                if TOOL_RE.search(v):
                    P.append(f"core property {f} = '{v[:40]}' (tool / AI name)")
            if re.search(r"<cp:lastPrinted\b", x):
                P.append("core property cp:lastPrinted")
        if "docProps/app.xml" in names:
            x = z.read("docProps/app.xml").decode("utf-8", "replace")
            for f in ("Application", "AppVersion", "Company", "Manager"):
                v = CM._field(x, f)
                if f in ("Company", "Manager") and v:
                    P.append(f"app property {f} = '{v[:40]}'")
                elif v and TOOL_RE.search(v):
                    P.append(f"app {f} = '{v[:40]}' (tool name)")
        if "docProps/custom.xml" in names and TOOL_RE.search(z.read("docProps/custom.xml").decode("utf-8", "replace")):
            P.append("custom properties name the tool chain")
    return P


# ---------------------------------------------------------------- docx
def check_docx(p, f):
    try:
        import docx
        docx.Document(p)
        parts = zip_parts(p, r"word/(document|styles|header\d*|footer\d*|footnotes|endnotes|comments)\.xml")
    except Exception as e:
        rec(f, "opens", [str(e)[:120]], hard=True); return
    rec(f, "opens", [])
    text, bad, bad_st = [], 0, 0
    want = OF.DOCX_FONTS
    for name, root in parts.items():
        if name == "word/styles.xml":
            dd = root.find(f"{{{W}}}docDefaults/{{{W}}}rPrDefault/{{{W}}}rPr/{{{W}}}rFonts")
            if dd is None:
                bad_st += 1
            for rf in root.iter(f"{{{W}}}rFonts"):
                if any(rf.get(f"{{{W}}}{k}") not in (None, v) for k, v in want.items()) or \
                        any(rf.get(f"{{{W}}}{k}") is not None for k in OF.THEME_ATTRS):
                    bad_st += 1
            continue
        text.append("".join(t.text or "" for t in root.iter(f"{{{W}}}t")))
        for r in root.iter(f"{{{W}}}r"):
            t = "".join(x.text or "" for x in r.iter(f"{{{W}}}t"))
            if not t.strip():
                continue
            rf = r.find(f"{{{W}}}rPr/{{{W}}}rFonts")
            if rf is None or any(rf.get(f"{{{W}}}{k}") != v for k, v in want.items()) or \
                    any(rf.get(f"{{{W}}}{k}") is not None for k in OF.THEME_ATTRS):
                bad += 1
    P = []
    if bad:
        P.append(f"{bad} text run(s) without ascii/hAnsi = {OF.LATIN}, cs/eastAsia = {OF.COMPLEX}")
    if bad_st:
        P.append(f"{bad_st} style / docDefaults font(s) not per the rule")
    rec(f, "fonts (Times New Roman + DVOT-SurekhMR)", P)
    words_check(f, "\n".join(text))
    rec(f, "metadata (no tool / AI trace)", CM.docx_meta_problems(p))


# ---------------------------------------------------------------- xlsx
def recalc_copy(p, tmp):
    """LibreOffice headless conversion xlsx -> xlsx (recalculates); -> the copy's path, or (None, reason)."""
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return None, "LibreOffice (soffice) not installed"
    src = os.path.join(tmp, "src"); os.makedirs(src)
    q = os.path.join(src, "book" + os.path.splitext(p)[1]); shutil.copy(p, q)
    out = os.path.join(tmp, "out"); os.makedirs(out)
    prof = "file://" + os.path.join(tmp, "profile")
    try:
        subprocess.run([exe, f"-env:UserInstallation={prof}", "--headless", "--norestore", "--convert-to", "xlsx",
                        "--outdir", out, q], capture_output=True, timeout=180)
    except Exception as e:
        return None, f"LibreOffice failed: {str(e)[:80]}"
    r = os.path.join(out, "book.xlsx")
    return (r, None) if os.path.isfile(r) else (None, "LibreOffice produced no file")


def check_xlsx(p, f):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(p)
    except Exception as e:
        rec(f, "opens", [str(e)[:120]], hard=True); return
    rec(f, "opens", [])
    text, numeric = [], []
    for ws in wb.worksheets:
        text.append(ws.title)
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if v is None:
                    continue
                if isinstance(v, str) and v.startswith("=") or (isinstance(v, (int, float)) and not isinstance(v, bool)):
                    if ws.title != CHECK_SHEET:
                        numeric.append(f"{ws.title}!{c.coordinate}")
                if isinstance(v, str) and not v.startswith("="):
                    text.append(v)
    # recalculation
    tmp = tempfile.mkdtemp(prefix="office_check_")
    try:
        r, why = recalc_copy(p, tmp)
        if not r:
            rec(f, "formulas recalculated (LibreOffice)", [why], level="WARN")
        else:
            errs = []
            wv = openpyxl.load_workbook(r, data_only=True)
            for ws in wv.worksheets:
                for row in ws.iter_rows():
                    for c in row:
                        if isinstance(c.value, str) and c.value.strip() in XL_ERRORS:
                            errs.append(f"{ws.title}!{c.coordinate} {c.value.strip()}")
            rec(f, "formulas recalculated, no error values", errs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # पडताळणी sheet
    if numeric:
        P = []
        if CHECK_SHEET not in wb.sheetnames:
            P.append(f"no sheet '{CHECK_SHEET}' (figures e.g. {', '.join(numeric[:3])})")
        else:
            ws = wb[CHECK_SHEET]
            filled = sum(1 for row in ws.iter_rows(values_only=True) if any(v not in (None, "") for v in row))
            if filled < 2:
                P.append(f"sheet '{CHECK_SHEET}' has {filled} filled row(s)")
        rec(f, f"sheet '{CHECK_SHEET}' lists the figures' sources", P)
    rec(f, "fonts (Devanagari -> DVOT-SurekhMR, else Times New Roman)", xlsx_font_problems(p))
    words_check(f, "\n".join(text) + "\n" + dml_text(p, r"xl/(charts|drawings)/[^/]+\.xml"))
    rec(f, "metadata (no tool / AI trace)", office_meta_problems(p))


def xlsx_font_problems(p):
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        rd = lambda n: OF._parse(z.read(n))   # noqa: E731
        sst = rd("xl/sharedStrings.xml") if "xl/sharedStrings.xml" in names else None
        st = rd("xl/styles.xml") if "xl/styles.xml" in names else None
        sheets = {n: rd(n) for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)}
    sis = sst.findall(f"{{{S}}}si") if sst is not None else []
    fonts = [OF._font_name(x) for x in st.find(f"{{{S}}}fonts")] if st is not None and st.find(f"{{{S}}}fonts") is not None else []
    xfs = [int(x.get("fontId") or 0) for x in st.find(f"{{{S}}}cellXfs")] if st is not None and st.find(f"{{{S}}}cellXfs") is not None else []
    bad, bad_runs, scheme = [], 0, 0
    if st is not None:
        scheme = sum(1 for x in st.iter(f"{{{S}}}font") if x.find(f"{{{S}}}scheme") is not None
                     and OF._font_name(x) in (OF.LATIN, OF.COMPLEX))

    def runs_bad(el):
        n = 0
        for r in el.findall(f"{{{S}}}r"):
            rf = r.find(f"{{{S}}}rPr/{{{S}}}rFont")
            if rf is not None and rf.get("val") != (OF.COMPLEX if OF.deva(OF._text(r, f"{{{S}}}t")) else OF.LATIN):
                n += 1
        return n
    for si in sis:
        bad_runs += runs_bad(si)
    for name, root in sheets.items():
        for c in root.iter(f"{{{S}}}c"):
            t = c.get("t")
            if c.find(f"{{{S}}}v") is None and c.find(f"{{{S}}}is") is None and c.find(f"{{{S}}}f") is None:
                continue
            txt = ""
            if t == "s":
                try:
                    txt = OF._text(sis[int(c.find(f"{{{S}}}v").text)], f"{{{S}}}t")
                except (AttributeError, ValueError, IndexError, TypeError):
                    txt = ""
            elif t == "inlineStr" and c.find(f"{{{S}}}is") is not None:
                txt = OF._text(c.find(f"{{{S}}}is"), f"{{{S}}}t"); bad_runs += runs_bad(c.find(f"{{{S}}}is"))
            elif t == "str" and c.find(f"{{{S}}}v") is not None:
                txt = c.find(f"{{{S}}}v").text or ""
            want = OF.COMPLEX if OF.deva(txt) else OF.LATIN
            si = int(c.get("s") or 0)
            fid = xfs[si] if 0 <= si < len(xfs) else 0
            have = fonts[fid] if 0 <= fid < len(fonts) else None
            if have != want:
                bad.append(f"{name.rsplit('/', 1)[-1][:-4]}!{c.get('r')} {have} (want {want})")
    P = []
    if bad:
        P.append(f"{len(bad)} cell(s): " + ", ".join(bad[:4]))
    if bad_runs:
        P.append(f"{bad_runs} rich-text run(s) with the wrong font")
    if scheme:
        P.append(f"{scheme} font(s) with a theme scheme (Excel shows the theme font)")
    return P


def dml_text(p, pattern):
    try:
        parts = zip_parts(p, pattern)
    except Exception:
        return ""
    return "\n".join("".join(t.text or "" for t in root.iter(f"{{{A}}}t")) for root in parts.values())


# ---------------------------------------------------------------- pptx
def check_pptx(p, f):
    try:
        import pptx
        pptx.Presentation(p)
        parts = zip_parts(p, r"ppt/(slides|notesSlides|charts|diagrams)/[^/]+\.xml")
    except Exception as e:
        rec(f, "opens", [str(e)[:120]], hard=True); return
    rec(f, "opens", [])
    bad = 0
    for root in parts.values():
        for tag in ("r", "fld"):
            for r in root.iter(f"{{{A}}}{tag}"):
                t = "".join(x.text or "" for x in r.iter(f"{{{A}}}t"))
                if not t.strip():
                    continue
                rp = r.find(f"{{{A}}}rPr")
                la = rp.find(f"{{{A}}}latin") if rp is not None else None
                cs = rp.find(f"{{{A}}}cs") if rp is not None else None
                if la is None or cs is None or la.get("typeface") != OF.LATIN or cs.get("typeface") != OF.COMPLEX:
                    bad += 1
    rec(f, "fonts (latin Times New Roman, cs DVOT-SurekhMR)",
        [f"{bad} text run(s) without a:latin {OF.LATIN} / a:cs {OF.COMPLEX}"] if bad else [])
    words_check(f, "\n".join("".join(t.text or "" for t in root.iter(f"{{{A}}}t")) for root in parts.values()))
    rec(f, "metadata (no tool / AI trace)", office_meta_problems(p))


# ---------------------------------------------------------------- pdf
def check_pdf(p, f):
    try:
        import pymupdf
        d = pymupdf.open(p)
        if d.needs_pass or d.page_count < 1:
            raise ValueError("password-protected" if d.needs_pass else "no pages")
    except Exception as e:
        rec(f, "opens", [str(e)[:120]], hard=True); return
    rec(f, "opens", [])
    text = "\n".join(pg.get_text() for pg in d)
    used = {str(x[3]) for pg in d for x in pg.get_fonts()}
    if text.strip() and not any(re.search(r"Times|Surekh", u, re.I) for u in used):
        rec(f, "fonts", [f"rendered with {', '.join(sorted(used)[:3]) or 'unknown'} (Times New Roman / DVOT-SurekhMR "
                         "not installed where it was made)"], level="WARN")
    words_check(f, text)
    rec(f, "metadata (no tool / AI trace)", CM.pdf_meta_problems(d))
    d.close()


CHECKS = {".docx": check_docx, ".xlsx": check_xlsx, ".pptx": check_pptx, ".pdf": check_pdf}


def run(outdir, expect=()):
    del results[:]
    if not os.path.isdir(outdir):
        rec(os.path.basename(outdir) or outdir, "output folder exists", ["missing"], hard=True)
        return results
    files, other = outputs(outdir)
    for e in expect:
        if not any(x.lower().endswith("." + e) for x in files):
            rec(f"*.{e}", "asked output present", [f"no .{e} file"], hard=True)
    for o in other:
        rec(os.path.basename(o), "not an output (left out of the upload)", ["ignored"], level="WARN")
    for p in files:
        f = os.path.basename(p)
        if os.path.getsize(p) == 0:
            rec(f, "opens", ["empty file"], hard=True); continue
        CHECKS[os.path.splitext(p)[1].lower()](p, f)
    return results


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = list(argv[1:])
    jp = expect = None
    if "--json" in args:
        i = args.index("--json"); jp = args[i + 1]; del args[i:i + 2]
    if "--expect" in args:
        i = args.index("--expect"); expect = args[i + 1]; del args[i:i + 2]
    if len(args) != 1:
        print(__doc__); return 2
    want = [x.strip().lower().lstrip(".") for x in (expect or "").split(",") if x.strip()]
    bad = [x for x in want if "." + x not in OUT_EXT]
    if bad:
        print(f"office_check: unknown --expect {','.join(bad)} (xlsx, docx, pptx, pdf)"); return 2
    res = run(os.path.abspath(args[0]), want)
    if jp:
        with open(jp, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    fails = [r for r in res if r["level"] == "FAIL"]
    if not res:
        print("office_check: no output files")
    print("ALL OK" if not fails else f"{len(fails)} FAIL ({sum(r['hard'] for r in fails)} HARD)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
