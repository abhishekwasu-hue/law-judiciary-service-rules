#!/usr/bin/env python3
"""clean_meta.py <file.docx|file.pdf> ...
Contract C27 §4 (Abhi, 02.11.2026: "वरिष्ठ अधिकाऱ्याला असे वाटू नये, की AI che kam aahe म्हणून") + lead's metadata
decision (research AI_TELLS §9: office .docx always carry an author; blank fields, the template's old dates / revision /
editing time and stale word counts are tells themselves). ONE definition used by the builders (mkdocs.py,
build_note_letter.py, build_order.py, build_parawise.py, build_study.py), the PDF tools (pkg3.py, highlight.py) and
verify_outputs.py.
  - docx core.xml: creator (author) and lastModifiedBy = the author given (spec key "doc_author") or env DOC_AUTHOR, else
    empty (the owner decides the name) — never a tool / AI name; title, subject, keywords, description (comments),
    category, contentStatus, identifier, language, version blank; created = modified = build time (UTC); revision 1;
    lastPrinted removed.
  - docx app.xml: Application "Microsoft Office Word"; TotalTime 0; stale statistics (Pages, Words, Characters, Lines,
    Paragraphs, CharactersWithSpaces) removed (Word recomputes them); Company, Manager blank.
  - PDF: Info dictionary (Producer, Creator, Author, Title, Subject, Keywords) blank, XMP metadata removed; annotation
    title (author) / subject / content removed.
Functions: clean_docx(path, author=None) (rewrites the file in place), clean_pdf(doc) (an open pymupdf.Document, before
save), docx_meta_problems(path) / pdf_meta_problems(doc) (verify: [] = clean)."""
import datetime
import os
import re
import shutil
import sys
import tempfile
import zipfile

CORE_BLANK = ("dc:title", "dc:subject", "cp:keywords", "dc:description", "cp:category", "cp:contentStatus",
              "dc:identifier", "dc:language", "cp:version")
CORE_AUTHOR = ("dc:creator", "cp:lastModifiedBy")
CORE_FIELDS = CORE_BLANK + CORE_AUTHOR
APP_NAME = "Microsoft Office Word"
APP_STATS = ("Pages", "Words", "Characters", "Lines", "Paragraphs", "CharactersWithSpaces")
APP_FIELDS = ("Company", "Manager")
NS = {"dc": "http://purl.org/dc/elements/1.1/", "dcterms": "http://purl.org/dc/terms/",
      "xsi": "http://www.w3.org/2001/XMLSchema-instance"}
PDF_FIELDS = ("producer", "creator", "author", "title", "subject", "keywords")
TRACE_RE = re.compile(r"python-docx|docxcompose|PyMuPDF|MuPDF|fitz|Claude|Anthropic|(?<![A-Za-z])AI(?![A-Za-z])|LLM|GPT|"
                      r"Gemini|generated|engine|automatic|model", re.I)


def _blank(xml, tag):
    """<tag ...>value</tag> -> <tag .../> (also self-closing tags left as they are)."""
    return re.sub(rf"<{re.escape(tag)}(\s[^>]*)?>.*?</{re.escape(tag)}>", lambda m: f"<{tag}{m.group(1) or ''}/>", xml,
                  flags=re.S)


def _field(xml, tag):
    """All values of <tag>…</tag> joined (a part may repeat a tag)."""
    return " ".join(v.strip() for v in re.findall(rf"<{re.escape(tag)}(?:\s[^>]*)?>(.*?)</{re.escape(tag)}>", xml, re.S)).strip()


def _drop(xml, tag):
    """Remove every <tag …>…</tag> / <tag …/> element."""
    t = re.escape(tag)
    return re.sub(rf"<{t}(?:\s[^>]*)?/>|<{t}(?:\s[^>]*)?>.*?</{t}>", "", xml, flags=re.S)


def _esc(v):
    return v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def doc_author(author=None):
    """The author to write: the given one, else env DOC_AUTHOR, else "" — a tool / AI name is never written."""
    for a in (author, os.environ.get("DOC_AUTHOR")):
        if isinstance(a, str) and a.strip() and not TRACE_RE.search(a):
            return a.strip()
    return ""


def clean_core(x, author="", now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for f in CORE_BLANK:
        x = _blank(x, f)
    for f in CORE_AUTHOR + ("cp:revision", "cp:lastPrinted", "dcterms:created", "dcterms:modified"):
        x = _drop(x, f)
    m = re.search(r"<cp:coreProperties\b[^>]*>", x)
    head = m.group(0)
    for k, v in NS.items():
        if f"xmlns:{k}=" not in head:
            head = head[:-1] + f' xmlns:{k}="{v}">'
    a = _esc(author)
    add = (f"<dc:creator>{a}</dc:creator><cp:lastModifiedBy>{a}</cp:lastModifiedBy><cp:revision>1</cp:revision>"
           f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
           f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>')
    return x[:m.start()] + head + add + x[m.end():]


def clean_app(x):
    for f in APP_STATS:
        x = _drop(x, f)
    for f in APP_FIELDS:
        x = _blank(x, f)
    x = _drop(x, "Application"); x = _drop(x, "TotalTime")
    m = re.search(r"<Properties\b[^>]*>", x)
    return x[:m.end()] + f"<TotalTime>0</TotalTime><Application>{APP_NAME}</Application>" + x[m.end():]


def clean_docx(path, author=None):
    """Office-like core / app properties for a saved .docx, in place (C27 §4)."""
    au = doc_author(author)
    fd, tmp = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    try:
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for it in zin.infolist():
                data = zin.read(it.filename)
                if it.filename == "docProps/core.xml":
                    data = clean_core(data.decode("utf-8"), au).encode("utf-8")
                elif it.filename == "docProps/app.xml":
                    data = clean_app(data.decode("utf-8")).encode("utf-8")
                zout.writestr(it, data)
        shutil.move(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def docx_meta_problems(path):
    """[] when the .docx carries no author/title/tool trace, no Word comments and no tracked changes (C27 §4)."""
    P = []
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:
        return [f"{os.path.basename(path)}: {e}"]
    with z:
        names = set(z.namelist())
        if "docProps/core.xml" in names:
            x = z.read("docProps/core.xml").decode("utf-8", "replace")
            for f in CORE_BLANK:
                v = _field(x, f)
                if v:
                    P.append(f"core property {f} = '{v[:40]}' (blank)")
            for f in CORE_AUTHOR:
                v = _field(x, f)
                if TRACE_RE.search(v):
                    P.append(f"core property {f} = '{v[:40]}' (tool / AI name)")
            if re.search(r"<cp:lastPrinted\b", x):
                P.append("core property cp:lastPrinted (template's old print date)")
            if _field(x, "dcterms:created") != _field(x, "dcterms:modified"):
                P.append("core created != modified (template's old dates)")
            rev = _field(x, "cp:revision")
            if rev and rev != "1":
                P.append(f"core revision {rev} (template's)")
        if "docProps/app.xml" in names:
            x = z.read("docProps/app.xml").decode("utf-8", "replace")
            v = _field(x, "Application")
            if v != APP_NAME:
                P.append(f"app Application = '{v[:40]}' (not '{APP_NAME}')")
            st = [f for f in APP_STATS if re.search(rf"<{f}\b", x)]
            if st:
                P.append(f"app stale statistics {st}")
            for f in APP_FIELDS:
                v = _field(x, f)
                if v:
                    P.append(f"app property {f} = '{v[:40]}'")
        if "word/comments.xml" in names and re.search(r"<w:comment\b", z.read("word/comments.xml").decode("utf-8", "replace")):
            P.append("Word comments present")
        for n in names:
            if re.fullmatch(r"word/(document|header\d*|footer\d*)\.xml", n):
                if re.search(r"<w:(ins|del|moveFrom|moveTo)\b", z.read(n).decode("utf-8", "replace")):
                    P.append(f"tracked changes in {n}")
    return P


def clean_pdf(doc):
    """Blank the Info dictionary + XMP metadata and every annotation's title/subject/content of an open pymupdf
    Document (call before save; C27 §4)."""
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
    for pg in doc:
        for a in pg.annots() or []:
            for key in ("T", "Subj", "Contents"):   # author (title) / subject / content; set_info ignores "" values
                if doc.xref_get_key(a.xref, key)[0] != "null":
                    doc.xref_set_key(a.xref, key, "null")


def pdf_meta_problems(doc):
    """[] when the PDF's metadata and annotations carry no tool / author trace (C27 §4)."""
    P = []
    md = doc.metadata or {}
    for k in PDF_FIELDS:
        v = (md.get(k) or "").strip()
        if v:
            P.append(f"PDF {k} = '{v[:40]}' (blank)")
    try:
        xmp = doc.get_xml_metadata() or ""
    except Exception:
        xmp = ""
    if TRACE_RE.search(xmp):
        P.append("PDF XMP metadata names the tool chain")
    for i, pg in enumerate(doc, 1):
        for a in pg.annots() or []:
            info = a.info
            for k in ("title", "subject", "content"):
                v = (info.get(k) or "").strip()
                if v:
                    P.append(f"page {i}: annotation {k} = '{v[:30]}' (blank)")
    return P


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    for p in argv[1:]:
        if p.lower().endswith(".docx"):
            clean_docx(p)
        elif p.lower().endswith(".pdf"):
            import pymupdf
            d = pymupdf.open(p); clean_pdf(d)
            tmp = p + ".tmp"; d.save(tmp, garbage=3, deflate=True); d.close(); os.replace(tmp, p)
        print("clean", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
