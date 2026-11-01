#!/usr/bin/env python3
"""build_note_letter.py <spec.json> <outdir> <PREFIX>
spec.json -> <outdir>/<PREFIX>_Note_and_Letter.docx (note; if spec has "letter": the letter follows in its OWN section on a
new page, keeping LETTER_TEMPLATE's page setup — margins etc. — while the note keeps NOTE_TEMPLATE's).
Uses tools/mkdocs.py (Section templates, tables supported) + docxcompose.
Checks: every text run is DVOT-SurekhMR in all four rFonts attributes (ascii/hAnsi/cs/eastAsia); with a letter, 2 sections
whose margins equal the two templates. Exit code 1 if a check fails.
Also writes <outdir>/<PREFIX>_Note_and_Letter.pdf preview if LibreOffice (soffice) is available (warning only if absent/failed)."""
import os, sys, subprocess, tempfile, shutil, copy
import docx
from docx.oxml.ns import qn

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
        lp = os.path.join(tmp, f"{pre}_Letter.docx")
        has_letter = os.path.exists(lp)
        (compose(note, docx.Document(lp)) if has_letter else note).save(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    d = docx.Document(out); ok = True
    bad = bad_font_runs(d)
    if bad:
        ok = False
    secs = d.sections
    want = [margins(docx.Document(os.path.join(TPL, "NOTE_TEMPLATE.docx")).sections[0])]
    if has_letter:
        want.append(margins(docx.Document(os.path.join(TPL, "LETTER_TEMPLATE.docx")).sections[0]))
    got = [margins(s) for s in secs]
    if got != want:
        ok = False
        print("FAIL: section page setup", got, "!= templates", want, file=sys.stderr)
    print(out, "letter" if has_letter else "NO letter", "sections:", len(secs), "bad-font runs:", bad)
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if soffice:
        r = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", outdir, out],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if r.returncode != 0 or not os.path.exists(os.path.splitext(out)[0] + ".pdf"):
            print("WARNING: soffice preview failed (rc", r.returncode, ")", r.stderr.decode(errors="replace")[:300], file=sys.stderr)
    else:
        print("WARNING: soffice not found — no PDF preview (docx is complete)", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:4]))
