#!/usr/bin/env python3
"""build_note_letter.py <spec.json> <outdir> <PREFIX> [--no-lint]
First runs the pre-build lint (tools/lint_spec.py) on spec.json and stops with exit 1 (problems printed) if it finds any;
--no-lint or env LINT_SKIP=1 skips it (test fixtures that build deliberately bad files).
spec.json -> <outdir>/<PREFIX>_Note_and_Letter.docx (note; if spec has "letter": the letter follows in its OWN section on a
new page, keeping LETTER_TEMPLATE's page setup — margins etc. — while the note keeps NOTE_TEMPLATE's). Several letters
(spec "letters": [..], e.g. a letter and a स्मरणपत्र; INSTRUCTIONS §4.28, 03.11.2026): each in its own section on a new page,
in the order of mkdocs.letters_of ("letter" first, then "letters").
Uses tools/mkdocs.py (Section templates, tables supported) + docxcompose.
Checks: every text run is DVOT-SurekhMR in all four rFonts attributes (ascii/hAnsi/cs/eastAsia); with a letter, 2 sections
whose margins equal the two templates (one letter section per letter). Exit code 1 if a check fails.
Also writes <outdir>/<PREFIX>_Note_and_Letter.pdf preview if LibreOffice (soffice) is available (warning only if absent/failed)."""
import os, sys, subprocess, tempfile, shutil, copy, json
import docx
from docx.oxml.ns import qn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean_meta import clean_docx  # noqa: E402 — C27 §4: blank core/app properties

FONT = "DVOT-SurekhMR"
HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "templates")
MARGINS = ("left_margin", "right_margin", "top_margin", "bottom_margin", "page_width", "page_height")


def margins(section):
    return tuple(getattr(section, a) for a in MARGINS)


def bad_font_runs(d):
    bad = 0
    for el in d.element.body.iter(qn("w:r")):
        t = "".join(x.text or "" for x in el.iter(qn("w:t")))
        if not t.strip():
            continue
        rp = el.find(qn("w:rPr")); f = rp.find(qn("w:rFonts")) if rp is not None else None
        if f is None or any(f.get(qn("w:" + k)) != FONT for k in ("ascii", "hAnsi", "cs", "eastAsia")):
            bad += 1
    return bad


def compose(note, let):
    """Note's sectPr -> section break in a last note paragraph; body sectPr <- letter's sectPr; then append the letter."""
    from docxcompose.composer import Composer
    body = note.element.body
    note_sp = body.find(qn("w:sectPr")); let_sp = let.element.body.find(qn("w:sectPr"))
    brk = note.add_paragraph()._p  # inserted before the body sectPr
    brk.get_or_add_pPr().append(copy.deepcopy(note_sp))
    new_sp = copy.deepcopy(let_sp)
    for t in new_sp.findall(qn("w:type")):
        new_sp.remove(t)
    typ = new_sp.makeelement(qn("w:type"), {qn("w:val"): "nextPage"}); new_sp.insert(0, typ)
    body.replace(note_sp, new_sp)
    c = Composer(note); c.append(let)
    return c.doc


def main(spec, outdir, pre):
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "mkdocs.py"), spec, tmp, pre], check=True)
        note = docx.Document(os.path.join(tmp, f"{pre}_Note.docx"))
        out = os.path.join(outdir, f"{pre}_Note_and_Letter.docx")
        os.makedirs(outdir, exist_ok=True)
        from mkdocs import letter_file
        lps = []
        while os.path.exists(letter_file(tmp, pre, len(lps))):
            lps.append(letter_file(tmp, pre, len(lps)))
        has_letter = bool(lps)
        doc = note
        for lp in lps:   # each letter: its own section, new page (§4.28)
            doc = compose(doc, docx.Document(lp))
        doc.save(out)
        try:
            author = json.load(open(spec, encoding="utf-8-sig")).get("doc_author")
        except Exception:
            author = None
        clean_docx(out, author)   # C27 §4 (docxcompose / python-docx leave no trace)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    d = docx.Document(out); ok = True
    bad = bad_font_runs(d)
    if bad:
        ok = False
    secs = d.sections
    want = [margins(docx.Document(os.path.join(TPL, "NOTE_TEMPLATE.docx")).sections[0])]
    if has_letter:
        # §4.44 (13.11.2026): an ordinary letter's left margin is set by mkdocs.build_letter (4.0 cm, Abhi's letter);
        # the अर्धशासकीय पत्र (kind "do") keeps LETTER_TEMPLATE's
        from mkdocs import LET_MARGIN_LEFT, letters_of
        from docx.shared import Twips
        lsec = margins(docx.Document(os.path.join(TPL, "LETTER_TEMPLATE.docx")).sections[0])
        lw = dict(zip(MARGINS, lsec)); lw["left_margin"] = Twips(LET_MARGIN_LEFT)
        kinds = [L.get("kind") if isinstance(L, dict) else None
                 for L in letters_of(json.load(open(spec, encoding="utf-8-sig")))]
        want += [lsec if (kinds[i] if i < len(kinds) else None) == "do" else tuple(lw[a] for a in MARGINS)
                 for i in range(len(lps))]
    got = [margins(s) for s in secs]
    if got != want:
        ok = False
        print("FAIL: section page setup", got, "!= templates", want, file=sys.stderr)
    print(out, f"{len(lps)} letter(s)" if has_letter else "NO letter", "sections:", len(secs), "bad-font runs:", bad)
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if soffice:
        rc, err = soffice_pdf(soffice, out, outdir)
        if rc != 0 or not os.path.exists(os.path.splitext(out)[0] + ".pdf"):
            print("WARNING: soffice preview failed (rc", rc, ")", err[:300], file=sys.stderr)
    else:
        print("WARNING: soffice not found — no PDF preview (docx is complete)", file=sys.stderr)
    return 0 if ok else 1



def soffice_pdf(soffice, src, outdir, timeout=180):
    """LibreOffice preview with a PRIVATE profile (parallel conversions by other agents do not collide, A2 LOW) and a
    time limit. -> (returncode, stderr text); rc 124 = timed out."""
    import tempfile
    prof = tempfile.mkdtemp(prefix="lo_preview_")
    try:
        r = subprocess.run([soffice, "-env:UserInstallation=file://" + prof.replace(os.sep, "/"), "--headless",
                            "--convert-to", "pdf", "--outdir", outdir, src],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        return r.returncode, r.stderr.decode(errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"soffice timed out after {timeout} s"
    finally:
        shutil.rmtree(prof, ignore_errors=True)

def lint(spec):
    """pre-build lint (same rules as verify_outputs.py); True when clean."""
    sys.path.insert(0, HERE)
    import lint_spec
    try:
        probs = lint_spec.lint_spec(lint_spec.load(spec))
    except Exception as e:
        probs = [f"{spec}: JSON — {e}"]
    for p in probs:
        print(p)
    if probs:
        print("LINT FAILED — fix spec.json (tools/lint_spec.py); nothing built", file=sys.stderr)
    return not probs


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if a != "--no-lint"]
    if len(args) != 3:
        sys.exit(__doc__)
    if "--no-lint" not in sys.argv and os.environ.get("LINT_SKIP") != "1" and not lint(args[0]):
        sys.exit(1)
    sys.exit(main(*args))
