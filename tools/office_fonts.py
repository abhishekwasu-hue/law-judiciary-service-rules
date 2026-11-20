#!/usr/bin/env python3
"""office_fonts.py FILE [FILE ...] — office-task outputs (INSTRUCTIONS §4.48, Abhi 20.11.2026): fonts per the decision and
blank metadata, IN PLACE. Run it on every .docx / .xlsx / .pptx / .pdf the worker built (anthropic docx / xlsx / pptx / pdf
skills, openpyxl, python-docx, python-pptx, LibreOffice) before tools/office_check.py. Config: tools/office_work.json
"fonts" (Latin = Times New Roman, complex script = DVOT-SurekhMR).

  .docx  every run / paragraph-mark / style / docDefaults / numbering rPr in document, styles, headers, footers,
         footnotes, endnotes, comments, numbering: w:rFonts ascii = hAnsi = Times New Roman, cs = eastAsia = DVOT-SurekhMR
         (theme-font attributes removed; a run without rPr gets one); theme fonts latin / cs / Deva set likewise.
  .pptx  every a:rPr / a:defRPr / a:endParaRPr (slides, layouts, masters, notes, charts, presentation defaults; a run or
         field without rPr gets one): a:latin = Times New Roman, a:cs = DVOT-SurekhMR, in schema order; theme likewise.
  .xlsx  a cell style has ONE font (no complex-script slot): a cell whose text has Devanagari -> DVOT-SurekhMR, every other
         cell -> Times New Roman (style cloned when needed, font `scheme` / `charset` dropped so the name rules); rich-text
         runs per run; theme latin = Times New Roman, cs / Deva = DVOT-SurekhMR; drawing / chart text as .pptx; a workbook
         with formulas gets calcPr fullCalcOnLoad="1" (Excel recalculates on opening).
  .pdf   fonts are fixed in its source file; only metadata (clean_meta.clean_pdf).
  metadata: .docx clean_meta.clean_docx; .xlsx / .pptx the same core rules (clean_meta.clean_core) + app.xml Application
         "Microsoft Excel" / "Microsoft Office PowerPoint", TotalTime 0, stale statistics dropped, Company / Manager blank.
Functions: fix_file(path) -> {"fonts": n changed elements, "meta": True}; deva(text)."""
import os
import re
import shutil
import sys
import tempfile
import zipfile

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clean_meta as CM  # noqa: E402 — C27 §4: the ONE metadata definition

LATIN = "Times New Roman"
COMPLEX = "DVOT-SurekhMR"
DOCX_FONTS = {"ascii": LATIN, "hAnsi": LATIN, "cs": COMPLEX, "eastAsia": COMPLEX}   # = build_affidavit.FONTS
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DEVA_RE = re.compile(r"[ऀ-ॿ꣠-ꣿ᳐-᳿]")
THEME_ATTRS = ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme")
APP_NAMES = {".xlsx": "Microsoft Excel", ".pptx": "Microsoft Office PowerPoint", ".docx": CM.APP_NAME}
APP_STATS = CM.APP_STATS + ("Slides", "Notes", "HiddenSlides", "MMClips", "TotalTime")


def deva(text):
    return bool(DEVA_RE.search(text or ""))


def w(tag):
    return f"{{{W}}}{tag}"


def a(tag):
    return f"{{{A}}}{tag}"


def s(tag):
    return f"{{{S}}}{tag}"


def _local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _parse(data):
    return etree.fromstring(data, etree.XMLParser(remove_blank_text=False, resolve_entities=False, huge_tree=True))


def _dump(root):
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def rewrite(path, fn):
    """fn(part name, bytes) -> bytes (or None = unchanged) for every zip part; the file is replaced in place."""
    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1], dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    try:
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            names = zin.namelist()
            for it in zin.infolist():
                data = zin.read(it.filename)
                new = fn(it.filename, data, zin, names)
                zout.writestr(it, data if new is None else new)
        shutil.move(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------- Word
def _docx_rfonts(rpr):
    rf = rpr.find(w("rFonts"))
    if rf is None:
        rf = etree.Element(w("rFonts"))
        pos = 0
        for i, ch in enumerate(rpr):
            if _local(ch) in ("ins", "del", "moveFrom", "moveTo", "rStyle"):
                pos = i + 1
        rpr.insert(pos, rf)
    n = 0
    for k, v in DOCX_FONTS.items():
        if rf.get(w(k)) != v:
            rf.set(w(k), v); n = 1
    for k in THEME_ATTRS:
        if rf.get(w(k)) is not None:
            del rf.attrib[w(k)]; n = 1
    return n


def fix_word_xml(root, styles=False):
    n = 0
    for r in root.iter(w("r")):
        if r.find(w("rPr")) is None:
            r.insert(0, etree.Element(w("rPr"))); n += 1
    if styles:
        dd = root.find(w("docDefaults"))
        if dd is None:
            dd = etree.Element(w("docDefaults")); root.insert(0, dd); n += 1
        rd = dd.find(w("rPrDefault"))
        if rd is None:
            rd = etree.Element(w("rPrDefault")); dd.insert(0, rd); n += 1
        if rd.find(w("rPr")) is None:
            rd.append(etree.Element(w("rPr"))); n += 1
    for rpr in list(root.iter(w("rPr"))):
        n += _docx_rfonts(rpr)
    return n


# ---------------------------------------------------------------- DrawingML (pptx, charts, drawings, themes)
LATIN_AFTER = ("ea", "cs", "sym", "hlinkClick", "hlinkMouseOver", "rtl", "extLst")
CS_AFTER = ("sym", "hlinkClick", "hlinkMouseOver", "rtl", "extLst")


def _dml_set(rpr, tag, face, before):
    el = rpr.find(a(tag))
    if el is not None:
        if el.get("typeface") == face and len(el.attrib) == 1:
            return 0
        for k in list(el.attrib):
            del el.attrib[k]
        el.set("typeface", face)
        return 1
    el = etree.Element(a(tag)); el.set("typeface", face)
    for i, ch in enumerate(rpr):
        if _local(ch) in before:
            rpr.insert(i, el); return 1
    rpr.append(el)
    return 1


def fix_dml_xml(root):
    n = 0
    for tag in ("r", "fld"):
        for r in root.iter(a(tag)):
            if r.find(a("rPr")) is None:
                r.insert(0, etree.Element(a("rPr"))); n += 1
    for tag in ("rPr", "defRPr", "endParaRPr"):
        for rpr in list(root.iter(a(tag))):
            n += _dml_set(rpr, "latin", LATIN, LATIN_AFTER)
            n += _dml_set(rpr, "cs", COMPLEX, CS_AFTER)
    return n


def fix_theme_xml(root):
    n = 0
    for kind in ("majorFont", "minorFont"):
        for f in root.iter(a(kind)):
            n += _dml_set(f, "latin", LATIN, ("ea", "cs", "font", "extLst"))
            n += _dml_set(f, "cs", COMPLEX, ("font", "extLst"))
            dv = [x for x in f.findall(a("font")) if x.get("script") == "Deva"]
            if dv:
                if dv[0].get("typeface") != COMPLEX:
                    dv[0].set("typeface", COMPLEX); n += 1
            else:
                el = etree.Element(a("font")); el.set("script", "Deva"); el.set("typeface", COMPLEX)
                ext = f.find(a("extLst"))
                (ext.addprevious(el) if ext is not None else f.append(el)); n += 1
    return n


# ---------------------------------------------------------------- Excel
def _text(el, ns_t):
    return "".join(x.text or "" for x in el.iter(ns_t))


def _font_name(font):
    nm = font.find(s("name"))
    return nm.get("val") if nm is not None else None


def _set_font_name(font, face):
    nm = font.find(s("name"))
    if nm is None:
        nm = etree.SubElement(font, s("name"))
    nm.set("val", face)
    for t in ("scheme", "charset"):
        for x in font.findall(s(t)):
            font.remove(x)


def fix_xlsx(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        parts = {n: z.read(n) for n in names}
    n = 0
    sst_texts = []
    sst = _parse(parts["xl/sharedStrings.xml"]) if "xl/sharedStrings.xml" in parts else None
    if sst is not None:
        for si in sst.findall(s("si")):
            sst_texts.append(_text(si, s("t")))
            for r in si.findall(s("r")):
                rpr = r.find(s("rPr"))
                if rpr is None:
                    continue
                face = COMPLEX if deva(_text(r, s("t"))) else LATIN
                rf = rpr.find(s("rFont"))
                if rf is None:
                    rf = etree.Element(s("rFont")); rpr.insert(0, rf)
                if rf.get("val") != face:
                    rf.set("val", face); n += 1
                for x in rpr.findall(s("scheme")) + rpr.findall(s("charset")):
                    rpr.remove(x); n += 1
    st = _parse(parts["xl/styles.xml"]) if "xl/styles.xml" in parts else None
    if st is None:   # no styles part: nothing to restyle (openpyxl / Excel always write one)
        return n
    fonts_el, xfs_el = st.find(s("fonts")), st.find(s("cellXfs"))
    if fonts_el is None:
        fonts_el = etree.SubElement(st, s("fonts"))
    if not len(fonts_el):
        etree.SubElement(fonts_el, s("font"))
    if xfs_el is None:
        xfs_el = etree.SubElement(st, s("cellXfs"))
    if not len(xfs_el):
        x = etree.SubElement(xfs_el, s("xf")); x.set("fontId", "0")
    fonts, xfs = list(fonts_el), list(xfs_el)
    for f in fonts:   # names rule (scheme would make Excel show the theme font instead)
        if _font_name(f) not in (LATIN, COMPLEX) or f.find(s("scheme")) is not None or f.find(s("charset")) is not None:
            _set_font_name(f, COMPLEX if _font_name(f) == COMPLEX else LATIN); n += 1
    font_cache, xf_cache = {}, {}

    def font_for(fid, face):
        fid = fid if 0 <= fid < len(fonts) else 0
        if _font_name(fonts[fid]) == face:
            return fid
        key = (fid, face)
        if key not in font_cache:
            nf = etree.fromstring(etree.tostring(fonts[fid])); _set_font_name(nf, face)
            fonts_el.append(nf); fonts.append(nf); font_cache[key] = len(fonts) - 1
        return font_cache[key]

    def xf_for(si, face):
        si = si if 0 <= si < len(xfs) else 0
        fid = int(xfs[si].get("fontId") or 0)
        nf = font_for(fid, face)
        if nf == fid:
            return si
        key = (si, face)
        if key not in xf_cache:
            nx = etree.fromstring(etree.tostring(xfs[si])); nx.set("fontId", str(nf)); nx.set("applyFont", "1")
            xfs_el.append(nx); xfs.append(nx); xf_cache[key] = len(xfs) - 1
        return xf_cache[key]

    has_formula = False
    out = {}
    for name in names:
        if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name):
            continue
        root = _parse(parts[name])
        for c in root.iter(s("c")):
            t = c.get("t")
            if c.find(s("f")) is not None:
                has_formula = True
            if t == "s":
                v = c.find(s("v"))
                try:
                    txt = sst_texts[int(v.text)]
                except (AttributeError, ValueError, IndexError, TypeError):
                    txt = ""
            elif t == "inlineStr":
                isel = c.find(s("is"))
                txt = _text(isel, s("t")) if isel is not None else ""
                if isel is not None:
                    for r in isel.findall(s("r")):
                        rpr = r.find(s("rPr"))
                        if rpr is not None:
                            rf = rpr.find(s("rFont"))
                            if rf is None:
                                rf = etree.Element(s("rFont")); rpr.insert(0, rf)
                            rf.set("val", COMPLEX if deva(_text(r, s("t"))) else LATIN)
            elif t == "str":
                v = c.find(s("v"))
                txt = v.text if v is not None and v.text else ""
            else:
                txt = ""
            face = COMPLEX if deva(txt) else LATIN
            old = int(c.get("s") or 0)
            new = xf_for(old, face)
            if new != old or (c.get("s") is None and new != 0):
                c.set("s", str(new)); n += 1
        out[name] = _dump(root)
    fonts_el.set("count", str(len(fonts))); xfs_el.set("count", str(len(xfs)))
    out["xl/styles.xml"] = _dump(st)
    if sst is not None:
        out["xl/sharedStrings.xml"] = _dump(sst)
    for name in names:
        if re.fullmatch(r"xl/theme/theme\d*\.xml", name):
            root = _parse(parts[name]); n += fix_theme_xml(root); out[name] = _dump(root)
        elif re.fullmatch(r"xl/(charts|drawings)/[^/]+\.xml", name):
            root = _parse(parts[name]); k = fix_dml_xml(root)
            if k:
                n += k; out[name] = _dump(root)
    if has_formula and "xl/workbook.xml" in parts:
        wb = _parse(parts["xl/workbook.xml"])
        cp = wb.find(s("calcPr"))
        if cp is None:
            cp = etree.Element(s("calcPr"))
            pos = 0
            for i, ch in enumerate(wb):
                if _local(ch) in ("fileVersion", "fileSharing", "workbookPr", "workbookProtection", "bookViews", "sheets",
                                  "functionGroups", "externalReferences", "definedNames"):
                    pos = i + 1
            wb.insert(pos, cp)
        if cp.get("fullCalcOnLoad") != "1":
            cp.set("fullCalcOnLoad", "1"); n += 1
        out["xl/workbook.xml"] = _dump(wb)
    rewrite(path, lambda nm, data, *_: out.get(nm))
    return n


# ---------------------------------------------------------------- per type
def fix_docx(path):
    cnt = [0]

    def fn(name, data, *_):
        if re.fullmatch(r"word/(document|styles|header\d*|footer\d*|footnotes|endnotes|comments|numbering)\.xml", name):
            root = _parse(data); cnt[0] += fix_word_xml(root, styles=name == "word/styles.xml"); return _dump(root)
        if re.fullmatch(r"word/theme/theme\d*\.xml", name):
            root = _parse(data); cnt[0] += fix_theme_xml(root); return _dump(root)
        if re.fullmatch(r"word/(charts|diagrams)/[^/]+\.xml", name):
            root = _parse(data); cnt[0] += fix_dml_xml(root); return _dump(root)
        return None
    rewrite(path, fn)
    # text runs: the common rule of tools/font_rule.py (Marathi text incl. its digits DVOT-SurekhMR x4, English text
    # Times New Roman ascii / hAnsi) — the same rule as the proposal Word files (Abhi 20.11.2026, §4.2 / §4.48 (इ))
    import font_rule
    cnt[0] += font_rule.apply_docx(path)
    return cnt[0]


def fix_pptx(path):
    cnt = [0]

    def fn(name, data, *_):
        if not (name.startswith("ppt/") and name.endswith(".xml")):
            return None
        if re.fullmatch(r"ppt/theme/theme\d*\.xml", name):
            root = _parse(data); cnt[0] += fix_theme_xml(root); return _dump(root)
        if b"drawingml/2006/main" not in data:
            return None
        root = _parse(data); k = fix_dml_xml(root); cnt[0] += k
        return _dump(root) if k else None
    rewrite(path, fn)
    return cnt[0]


def clean_app_xml(x, app):
    for f in APP_STATS:
        x = CM._drop(x, f)
    for f in CM.APP_FIELDS:
        x = CM._blank(x, f)
    x = CM._drop(x, "Application"); x = CM._drop(x, "AppVersion")
    m = re.search(r"<Properties\b[^>]*>", x)
    if not m:
        return x
    return x[:m.end()] + f"<TotalTime>0</TotalTime><Application>{app}</Application>" + x[m.end():]


def clean_office_meta(path, author=None):
    """.xlsx / .pptx: clean_meta's core rules + an Office-like app.xml (C27 §4)."""
    app = APP_NAMES[os.path.splitext(path)[1].lower()]
    au = CM.doc_author(author)

    def fn(name, data, *_):
        if name == "docProps/core.xml":
            return CM.clean_core(data.decode("utf-8"), au).encode("utf-8")
        if name == "docProps/app.xml":
            return clean_app_xml(data.decode("utf-8"), app).encode("utf-8")
        return None
    rewrite(path, fn)


def fix_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        n = fix_docx(path); CM.clean_docx(path)
    elif ext == ".xlsx":
        n = fix_xlsx(path); clean_office_meta(path)
    elif ext == ".pptx":
        n = fix_pptx(path); clean_office_meta(path)
    elif ext == ".pdf":
        import pymupdf
        d = pymupdf.open(path); CM.clean_pdf(d)
        tmp = path + ".tmp"; d.save(tmp, garbage=3, deflate=True); d.close(); os.replace(tmp, path)
        n = 0
    else:
        raise ValueError(f"{os.path.basename(path)}: not a .docx / .xlsx / .pptx / .pdf")
    return {"fonts": n, "meta": True}


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    rc = 0
    for p in argv[1:]:
        try:
            r = fix_file(p)
            print(f"fixed {os.path.basename(p)}: {r['fonts']} font element(s) changed, metadata cleaned")
        except Exception as e:   # one bad file never stops the others; office_check reports it
            print(f"FAIL {os.path.basename(p)}: {e}"); rc = 1
    return rc


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv))
