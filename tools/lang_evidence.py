#!/usr/bin/env python3
"""lang_evidence.py — before/after evidence for language-rule changes to samples/specs/*.json (docs/LANG_RULES_EVIDENCE.md).

  python3 tools/lang_evidence.py build <outdir> [spec.json ...] [--no-lint]
      Builds each spec (default: samples/specs/*.json) with tools/build_note_letter.py into <outdir> (PREFIX = first two
      "_" parts of the file name, e.g. CR122_2026), renders every page of the LibreOffice preview PDF to
      <outdir>/<PREFIX>_pNN.png at 70 dpi (pdftoppm), and writes <outdir>/<PREFIX>.txt = the docx text in body order
      (one line per paragraph; each table cell on its own line as "[T<t> r<r> c<c>] text").
  python3 tools/lang_evidence.py compare <before> <after> [--img <dir>] [--md <file>]
      (b) paragraph-by-paragraph diff of the .txt files -> markdown table "| sample | location | before | after |"
          (changed words in **bold**, a few words of context) on stdout, also written to --md if given;
      (c) with --img: side-by-side PNG (BEFORE | AFTER) of every page whose image changed -> <dir>/<PREFIX>_pNN_sbs.png;
      (d) guard: every “…” / "..." quoted span and the whole "संबंधित माहिती (संदर్భాసాఠీ)" section must be identical
          before and after -> prints "OK: …" or "FAIL: …" per sample. Exit code 1 if any guard FAILs.
Needs: python-docx, Pillow, pdftoppm (poppler), soffice (LibreOffice) for the preview.
"""
import difflib
import glob
import os
import re
import subprocess
import sys

import docx
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RELATED = "संबंधित माहिती (संदर्भासाठी)"
QUOTE_RE = re.compile(r"“[^”]*”|\"[^\"]*\"")
DPI = 70
CTX = 6  # words of context around a change


def prefix_of(spec):
    return "_".join(os.path.basename(spec).split("_")[:2]).removesuffix(".json")


def el_text(el):
    return "".join(x.text or "" for x in el.iter(qn("w:t")))


def docx_lines(path):
    """docx body text in order: paragraphs, then table cells (row by row)."""
    out, t = [], 0
    for el in docx.Document(path).element.body:
        tag = el.tag.split("}")[1]
        if tag == "p":
            out.append(re.sub(r"\s*\n\s*", " ⏎ ", el_text(el)))
        elif tag == "tbl":
            t += 1
            for ri, tr in enumerate(el.iter(qn("w:tr")), 1):
                for ci, tc in enumerate(tr.iter(qn("w:tc")), 1):
                    out.append(f"[T{t} r{ri} c{ci}] " + " ".join(el_text(p) for p in tc.iter(qn("w:p"))))
    return out


def build(outdir, specs, no_lint):
    os.makedirs(outdir, exist_ok=True)
    rc = 0
    for spec in specs:
        pre = prefix_of(spec)
        cmd = [sys.executable, os.path.join(HERE, "build_note_letter.py"), spec, outdir, pre] + (["--no-lint"] if no_lint else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(f"FAIL build {pre}:\n{r.stdout}{r.stderr}"); rc = 1; continue
        dx = os.path.join(outdir, f"{pre}_Note_and_Letter.docx"); pdf = dx[:-5] + ".pdf"
        with open(os.path.join(outdir, f"{pre}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(docx_lines(dx)) + "\n")
        for old in glob.glob(os.path.join(outdir, f"{pre}_p*.png")):
            os.remove(old)
        if os.path.exists(pdf):
            tmp = os.path.join(outdir, f".{pre}_tmp")
            subprocess.run(["pdftoppm", "-r", str(DPI), "-png", pdf, tmp], check=True)
            for png in glob.glob(tmp + "-*.png"):
                n = int(re.search(r"-(\d+)\.png$", png).group(1))
                os.replace(png, os.path.join(outdir, f"{pre}_p{n:02d}.png"))
        else:
            print(f"WARNING {pre}: no PDF preview — no page images")
        npng = len(glob.glob(os.path.join(outdir, f"{pre}_p*.png")))
        print(f"built {pre}: {dx} ({npng} page images)")
    return rc


def sections(lines):
    """location label per line: note / संबंधित माहिती / letter, with the paragraph number inside that part."""
    part, k, labs = "note", 0, []
    for i, ln in enumerate(lines):
        s = re.sub(r"\s+", " ", ln).strip()
        if s == RELATED:
            part, k = "संबंधित माहिती", 0
        elif part != "letter" and s == "महाराष्ट्र शासन" and any(
                re.match(r"\s*(क्रमांक\s*:?\s*-|प्रति,)", x) for x in lines[i + 1:i + 10]):
            part, k = "letter", 0
        if not ln.startswith("[T"):
            k += 1
        cell = re.match(r"\[(T\d+ r\d+ c\d+)\]", ln)
        labs.append((part, f"{part} ¶{k}" + (f" {cell.group(1)}" if cell else "")))
    return labs


def md(s):
    return s.replace("|", "\\|")


def excerpt(a, b):
    """word-level diff -> (before excerpt, after excerpt) with changed words in bold and CTX words of context."""
    wa, wb = a.split(" "), b.split(" ")
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    keep_a, keep_b, bold_a, bold_b = set(), set(), set(), set()
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        bold_a.update(range(i1, i2)); bold_b.update(range(j1, j2))
        keep_a.update(range(max(0, i1 - CTX), min(len(wa), i2 + CTX)))
        keep_b.update(range(max(0, j1 - CTX), min(len(wb), j2 + CTX)))

    def show(words, keep, bold):
        out, last = [], -2
        for i in sorted(keep):
            if i != last + 1:
                out.append("…")
            out.append(f"**{words[i]}**" if i in bold and words[i] else words[i]); last = i
        if last != len(words) - 1 and out:
            out.append("…")
        return " ".join(out) or "(—)"
    return show(wa, keep_a, bold_a), show(wb, keep_b, bold_b)


def compare(before, after, imgdir, mdfile):
    rows, rc = [], 0
    pres = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(before, "*.txt")))
    for pre in pres:
        fa = os.path.join(after, pre + ".txt")
        if not os.path.exists(fa):
            print(f"FAIL: {pre} — no after text"); rc = 1; continue
        A = open(os.path.join(before, pre + ".txt"), encoding="utf-8").read().splitlines()
        B = open(fa, encoding="utf-8").read().splitlines()
        la, lb = sections(A), sections(B)
        sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                a = A[i1 + k] if i1 + k < i2 else ""
                b = B[j1 + k] if j1 + k < j2 else ""
                loc = (la[i1 + k] if i1 + k < i2 else lb[j1 + k])[1]
                ea, eb = excerpt(a, b) if a and b else (a or "(—)", b or "(—)")
                rows.append(f"| {pre} | {md(loc)} | {md(ea)} | {md(eb)} |")
        # (d) guard: quoted spans + संबंधित माहिती unchanged
        qa = [q for ln in A for q in QUOTE_RE.findall(ln)]
        qb = [q for ln in B for q in QUOTE_RE.findall(ln)]
        ra = [ln for ln, (p, _) in zip(A, la) if p == "संबंधित माहिती"]
        rb = [ln for ln, (p, _) in zip(B, lb) if p == "संबंधित माहिती"]
        probs = []
        if qa != qb:
            diffq = [q for q in qa if q not in qb][:3]
            probs.append(f"quoted spans changed ({len(qa)} before, {len(qb)} after; e.g. {[q[:60] for q in diffq]})")
        if ra != rb:
            probs.append(f"'{RELATED}' section changed ({len(ra)} lines before, {len(rb)} after)")
        if probs:
            print(f"FAIL: {pre} — " + "; ".join(probs)); rc = 1
        else:
            print(f"OK: {pre} — {len(qa)} quoted spans and {len(ra)} संबंधित माहिती lines unchanged")
        if imgdir:
            rc |= side_by_side(before, after, pre, imgdir)
    table = ["| sample | location | before | after |", "|---|---|---|---|"] + (rows or ["| — | — | (no differences) | |"])
    text = "\n".join(table)
    print(text)
    if mdfile:
        with open(mdfile, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return rc


def side_by_side(before, after, pre, imgdir):
    from PIL import Image, ImageChops, ImageDraw
    os.makedirs(imgdir, exist_ok=True)
    pa = sorted(glob.glob(os.path.join(before, f"{pre}_p*.png")))
    pb = sorted(glob.glob(os.path.join(after, f"{pre}_p*.png")))
    made = 0
    for i in range(max(len(pa), len(pb))):
        ia = Image.open(pa[i]).convert("RGB") if i < len(pa) else None
        ib = Image.open(pb[i]).convert("RGB") if i < len(pb) else None
        if ia is not None and ib is not None and ia.size == ib.size and ImageChops.difference(ia, ib).getbbox() is None:
            continue
        w = max(x.size[0] for x in (ia, ib) if x is not None); h = max(x.size[1] for x in (ia, ib) if x is not None)
        gap, top = 12, 22
        c = Image.new("RGB", (2 * w + gap, h + top), "white"); dr = ImageDraw.Draw(c)
        for k, (im, lab) in enumerate(((ia, "BEFORE"), (ib, "AFTER"))):
            x = k * (w + gap)
            dr.text((x + 4, 4), f"{lab}  {pre} p.{i + 1}", fill=(200, 0, 0) if k == 0 else (0, 128, 0))
            if im is not None:
                c.paste(im, (x, top))
        dr.line([(w + gap // 2, 0), (w + gap // 2, h + top)], fill=(120, 120, 120), width=2)
        c.save(os.path.join(imgdir, f"{pre}_p{i + 1:02d}_sbs.png"), optimize=True); made += 1
    print(f"{pre}: {made} changed page(s) -> {imgdir}")
    return 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(argv) < 2 or argv[1] not in ("build", "compare"):
        print(__doc__); return 2
    if argv[1] == "build":
        rest = [a for a in argv[2:] if a != "--no-lint"]
        if not rest:
            print(__doc__); return 2
        specs = rest[1:] or sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "*.json")))
        return build(rest[0], specs, "--no-lint" in argv)
    args, opt = [], {}
    it = iter(argv[2:])
    for a in it:
        if a in ("--img", "--md"):
            opt[a] = next(it, None)
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__); return 2
    return compare(args[0], args[1], opt.get("--img"), opt.get("--md"))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
