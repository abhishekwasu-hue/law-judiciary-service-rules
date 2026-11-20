#!/usr/bin/env python3
"""font_rule.py — the ONE font rule for Word text (Abhi 20.11.2026, INSTRUCTIONS §4.2 / §4.48 (इ): "इंग्रजी मजकुरासाठी
डिफॉल्ट फॉन्ट Times New Roman", "हे सगळे इकडे कॉमन असू द्या" — common to every Word file: note, letter, Study, orders,
parawise, LQ, office-task outputs).

Rule (per piece of text):
  * Devanagari text (and the digits / punctuation inside a Marathi sentence, e.g. "दि. 17.09.2026", "पृ.13/प.वि.")
    -> DVOT-SurekhMR on all four w:rFonts attributes (ascii, hAnsi, cs, eastAsia) — unchanged from before;
  * English text (a stretch that starts with a Latin letter: words, "PB-2", "B-4(1)/15/2009", "Email ID", an e-mail
    address) -> ascii = hAnsi = Times New Roman, cs = eastAsia = DVOT-SurekhMR;
  * a run of only digits / punctuation -> Times New Roman when its paragraph has no Devanagari (an English paragraph),
    else DVOT-SurekhMR.
A run that mixes Devanagari and English is split at the English stretches (same rPr, only the fonts differ), so an
English phrase inside a Marathi sentence ("(purely temporary and ad-hoc)") is Times New Roman. Runs holding a field,
drawing, object or footnote reference are not split (fonts by their whole text).

Functions: apply_docx(path, parts=DEFAULT_PARTS) rewrites a saved .docx in place -> number of runs changed;
apply_root(root) on one lxml part root; expected(run_text, para_text) -> dict of the four attributes, or None (any font
accepted: empty / whitespace-only); segments(text) -> [(piece, english)]. Used by tools/clean_meta.clean_docx (every
builder), tools/office_fonts.py, tools/verify_outputs.py and tools/office_check.py."""
import copy
import os
import re
import shutil
import sys
import tempfile
import zipfile

from lxml import etree

DEVA_FONT = "DVOT-SurekhMR"
LATIN_FONT = "Times New Roman"
ATTRS = ("ascii", "hAnsi", "cs", "eastAsia")
THEME_ATTRS = ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme")
DEVA_FONTS = {a: DEVA_FONT for a in ATTRS}
ENGLISH_FONTS = {"ascii": LATIN_FONT, "hAnsi": LATIN_FONT, "cs": DEVA_FONT, "eastAsia": DEVA_FONT}
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
DEVA_RE = re.compile(r"[ऀ-ॿ꣠-ꣿ᳐-᳿]")
LATIN_RE = re.compile(r"[A-Za-z]")
# an English stretch: starts with a Latin letter; words / codes joined by spaces and the punctuation of English text,
# numbers and codes; ends on a letter / digit (or a closing bracket / dot that belongs to it)
ENG_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[ \t.,;'’&/:@_+%#()\[\]\-]+[A-Za-z0-9]+)*[.)\]]?")
SPLITTABLE = {"t", "tab", "br", "cr", "noBreakHyphen", "softHyphen"}
DEFAULT_PARTS = re.compile(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml")


def w(tag):
    return f"{{{W}}}{tag}"


def deva(text):
    return bool(DEVA_RE.search(text or ""))


def segments(text):
    """[(piece, english)] — English stretches (ENG_RE) of a text that has Devanagari; a text without Devanagari is one
    piece (english = it has a Latin letter)."""
    if not text:
        return []
    if not deva(text):
        return [(text, bool(LATIN_RE.search(text)))]
    out, i = [], 0
    for m in ENG_RE.finditer(text):
        if m.start() > i:
            out.append((text[i:m.start()], False))
        out.append((m.group(0), True))
        i = m.end()
    if i < len(text):
        out.append((text[i:], False))
    return out


def expected(run_text, para_text=""):
    """The four fonts a run with this text must carry (after apply_*), or None when any font is accepted."""
    if not (run_text or "").strip():
        return None
    if deva(run_text):
        return DEVA_FONTS
    if LATIN_RE.search(run_text):
        return ENGLISH_FONTS
    return DEVA_FONTS if deva(para_text) else ENGLISH_FONTS


def _set_fonts(r, fonts):
    """rFonts of run r = fonts (theme attributes removed); returns True when something changed."""
    rpr = r.find(w("rPr"))
    if rpr is None:
        rpr = etree.Element(w("rPr"))
        r.insert(0, rpr)
    fo = rpr.find(w("rFonts"))
    if fo is None:
        fo = etree.Element(w("rFonts"))
        rpr.insert(0, fo)   # rFonts is the first child of rPr (after rStyle, which python-docx rarely writes)
        st = rpr.find(w("rStyle"))
        if st is not None:
            rpr.remove(fo)
            st.addnext(fo)
    changed = False
    for a in THEME_ATTRS:
        if fo.get(w(a)) is not None:
            del fo.attrib[w(a)]
            changed = True
    for a, v in fonts.items():
        if fo.get(w(a)) != v:
            fo.set(w(a), v)
            changed = True
    return changed


def _run_text(r):
    return "".join(t.text or "" for t in r.iter(w("t")))


def _para_text(r, cache):
    p = r.getparent()
    while p is not None and p.tag != w("p"):
        p = p.getparent()
    if p is None:
        return ""
    k = id(p)
    if k not in cache:
        cache[k] = "".join(t.text or "" for t in p.iter(w("t")))
    return cache[k]


def _new_t(text):
    t = etree.Element(w("t"))
    t.text = text
    if text != text.strip() or "  " in text:
        t.set(f"{{{XML_NS}}}space", "preserve")
    return t


def _split(r, para):
    """Replace run r by runs whose text is homogeneous (English / not); returns the number of runs written."""
    rpr = r.find(w("rPr"))
    kids = [c for c in r if c.tag != w("rPr")]
    pieces = []   # [(fonts, [elements])]
    for c in kids:
        if c.tag == w("t"):
            for txt, eng in segments(c.text or ""):
                f = ENGLISH_FONTS if eng else (DEVA_FONTS if deva(txt) or deva(para) or not txt.strip() else ENGLISH_FONTS)
                if not txt.strip() and pieces:
                    f = pieces[-1][0]   # spaces stay with the text before them
                if pieces and pieces[-1][0] is f:
                    pieces[-1][1].append(_new_t(txt))
                else:
                    pieces.append((f, [_new_t(txt)]))
        else:
            if pieces:
                pieces[-1][1].append(c)
            else:
                pieces.append((DEVA_FONTS if deva(para) else ENGLISH_FONTS, [c]))
    if len(pieces) <= 1:
        f = pieces[0][0] if pieces else DEVA_FONTS
        return 1 if _set_fonts(r, f) else 0
    parent = r.getparent()
    at = parent.index(r)
    for k, (f, els) in enumerate(pieces):
        nr = etree.Element(w("r"))
        for a_, v in r.attrib.items():
            nr.set(a_, v)
        if rpr is not None:
            nr.append(copy.deepcopy(rpr))
        for e in els:
            nr.append(e)
        _merge_ts(nr)
        _set_fonts(nr, f)
        parent.insert(at + k, nr)
    parent.remove(r)
    return len(pieces)


def _merge_ts(r):
    """Adjacent w:t of one run joined (keeps the XML small)."""
    prev = None
    for c in list(r):
        if c.tag == w("t") and prev is not None and prev.tag == w("t"):
            prev.text = (prev.text or "") + (c.text or "")
            if prev.text != prev.text.strip() or "  " in prev.text:
                prev.set(f"{{{XML_NS}}}space", "preserve")
            r.remove(c)
            continue
        prev = c


def apply_root(root):
    """Apply the rule to every text run under root; returns the number of runs changed / written."""
    n = 0
    cache = {}
    for r in list(root.iter(w("r"))):
        txt = _run_text(r)
        if not txt.strip():
            continue
        para = _para_text(r, cache)
        kids = {etree.QName(c).localname for c in r if c.tag != w("rPr")}
        if deva(txt) and kids <= SPLITTABLE and any(e for t, e in segments(txt)):
            n += _split(r, para)
        else:
            f = expected(txt, para) or DEVA_FONTS
            if deva(txt):
                f = DEVA_FONTS
            n += 1 if _set_fonts(r, f) else 0
    return n


def apply_docx(path, parts=DEFAULT_PARTS):
    """Rewrite a saved .docx in place (document, headers, footers, footnotes, endnotes); returns runs changed."""
    total = 0
    fd, tmp = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    try:
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for it in zin.infolist():
                data = zin.read(it.filename)
                if parts.fullmatch(it.filename):
                    root = etree.fromstring(data)
                    k = apply_root(root)
                    if k:
                        total += k
                        data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
                zout.writestr(it, data)
        shutil.move(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return total


def problems(root_iter):
    """Number of text runs (from an iterable of lxml roots) whose fonts break the rule."""
    bad = 0
    for root in root_iter:
        cache = {}
        for r in root.iter(w("r")):
            txt = _run_text(r)
            want = expected(txt, _para_text(r, cache))
            if want is None:
                continue
            rpr = r.find(w("rPr"))
            fo = rpr.find(w("rFonts")) if rpr is not None else None
            if fo is None or any(fo.get(w(a)) is not None for a in THEME_ATTRS):
                bad += 1
                continue
            got = {a: fo.get(w(a)) for a in ATTRS}
            if got != want and not (not deva(txt) and not LATIN_RE.search(txt) and got in (DEVA_FONTS, ENGLISH_FONTS)):
                bad += 1
    return bad


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        print(p, apply_docx(p))
