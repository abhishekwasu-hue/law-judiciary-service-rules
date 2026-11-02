#!/usr/bin/env python3
"""Build the AI-provider benchmark set (docs/AI_BENCHMARK.md) from PUBLIC documents only. No network.

Usage:  python3 tools/ai_benchmark_set.py [<out dir>] [--n 8] [--no-ocr-check] [--no-dummy]
  <out dir> default tests/benchmark_set
Writes:
  pages/<id>.png               page image at 110 dpi (the same dpi as tools/prep_pages.py)
  ground_truth/<id>.txt        the page's text (GR pages: the PDF's Unicode text layer, reading order sorted;
                               dummy pages: the exact text the page was made from)
  ground_truth/<id>.words.txt  GR pages only: the "confirmed" Devanagari words = text-layer words that tesseract also
                               reads on the image (multiset intersection, text order). Word recall is scored on these,
                               because Marathi GR text layers often carry font-mapping slips ("धवभाग" for "विभाग",
                               "पुरववठा") that the page image does not show.
  manifest.json                {"pages": [{"id", "source", "page", "pdf_sha256", "table", "kind", "common_word_rate",
                               "ocr_agreement"}], "settings": {...}}
  dummy_proposal/dummy_proposal.pdf   3-page SYNTHETIC proposal (image-only, like a scan): निर्देशपत्र-like cover,
                               a District Judge letter asking a pay benefit, a table. All names, places, numbers are fake
                               ("श्री. अ. ब. चाचणी", "चाचणीनगर"); every page is marked "चाचणी नमुना — खरी नस्ती नाही".
  dummy_proposal/facts.json    ground-truth facts of the dummy proposal (for Test B — full engine run)
GR pages: candidates = pages 1-6 of pdf/**/*.pdf (never case-docs/, medical-bill/, precedent-library/, samples/, the
old-case zips) with >= 120 Devanagari words, >= 15 digits, no legacy-font Latin-1 characters and a common-word rate
>= 0.12 (garbled legacy-font layers read "शासि", "र्ासन" and miss the common words). Order = sha1("<path>:<page>"),
so the choice is deterministic for the same repo. One page per folder (variety of departments / layouts). Each candidate is cross-checked against tesseract
(mar, 200 dpi): the share of its text-layer words that the OCR also reads must be >= 0.65, and at most 0.5 % of its
words may hold an impossible sign sequence (the same vowel sign / halant twice, a word starting with a vowel sign). The first accepted page with a ruled table (pymupdf find_tables, >= 3x3) is taken as the table
page; the rest are non-table pages."""
import collections, hashlib, json, os, re, shutil, subprocess, sys, tempfile

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from ai_benchmark import norm, words, word_recall  # noqa: E402

DPI = 110
EXCLUDE = ("case-docs", "medical-bill", "precedent-library", "samples", "प्रकरणे")
COMMON = set("शासन महाराष्ट्र निर्णय विभाग दिनांक यांच्या करण्यात आहे येत सदर शासकीय कर्मचारी वेतन मंत्रालय मुंबई "
             "क्रमांक संदर्भ प्रस्तावना असून आले आली करण्याबाबत येणार राहील पुढीलप्रमाणे तसेच अधिकारी सेवा या व त्या "
             "किंवा नाही अशा".split())
FONT_DIR = "/usr/share/fonts/truetype/freefont"
TEST_MARK = "चाचणी नमुना — खरी नस्ती नाही"


def candidates():
    out = []
    for dp, dn, fn in os.walk(os.path.join(ROOT, "pdf")):
        dn[:] = sorted(d for d in dn if not any(x in d for x in EXCLUDE))
        for f in sorted(fn):
            if not f.lower().endswith(".pdf"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), ROOT)
            try:
                doc = pymupdf.open(os.path.join(ROOT, rel))
            except Exception:
                continue
            for i in range(min(len(doc), 6)):
                t = doc[i].get_text()
                w = words(t)
                if len(w) < 120 or len(re.findall(r"\d", t)) < 15 or re.search(r"[À-ÿ]", t):
                    continue
                rate = sum(x in COMMON for x in w) / len(w)
                if rate >= 0.12:
                    out.append((hashlib.sha1(f"{rel}:{i + 1}".encode()).hexdigest(), rel, i + 1, round(rate, 3)))
            doc.close()
    return sorted(out)


def has_table(page):
    try:
        return any(t.row_count >= 3 and t.col_count >= 3 for t in page.find_tables().tables)
    except Exception:
        return False


IMPOSSIBLE = re.compile(r"([\u093E-\u094D])\1|^[\u093E-\u094D]")
MIN_OCR = 0.65


def impossible_rate(text):
    w = words(text)
    return sum(bool(IMPOSSIBLE.search(x)) for x in w) / len(w) if w else 1.0


def ocr_agreement(page):
    """(share of text-layer words also read by tesseract, confirmed words) or (None, None)."""
    exe = shutil.which("tesseract")
    if not exe:
        return None, None
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "p.png")
        page.get_pixmap(dpi=200).save(png)
        try:
            r = subprocess.run([exe, png, "stdout", "-l", "mar"], capture_output=True, timeout=600,
                               env=dict(os.environ, OMP_THREAD_LIMIT="1"))
        except subprocess.TimeoutExpired:
            return None, None
    tl, ocr = page.get_text("text", sort=True), r.stdout.decode("utf-8", "replace")
    left = collections.Counter(words(ocr))
    confirmed = []
    for w in words(tl):
        if left[w] > 0:
            left[w] -= 1; confirmed.append(w)
    return word_recall(tl, ocr), confirmed


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def pick_pages(n, ocr_check=True):
    chosen, used, table_done = [], set(), False
    for _h, rel, pno, rate in candidates():
        if len(chosen) >= n:
            break
        if os.path.dirname(rel) in used:
            continue
        doc = pymupdf.open(os.path.join(ROOT, rel))
        page = doc[pno - 1]
        tab = has_table(page)
        if not tab and not table_done and len(chosen) == n - 1:
            continue  # keep the last slot for a table page
        if tab and table_done:
            continue
        if impossible_rate(page.get_text()) > 0.005:
            continue
        agree, confirmed = ocr_agreement(page) if ocr_check else (None, None)
        if ocr_check and (agree is None or agree < MIN_OCR):
            continue
        used.add(os.path.dirname(rel))
        table_done = table_done or tab
        chosen.append({"source": rel, "page": pno, "table": tab, "common_word_rate": rate,
                       "ocr_agreement": None if agree is None else round(agree, 3), "_confirmed": confirmed})
    return chosen


# ---------------- synthetic dummy proposal (fake names / numbers only) ----------------
DUMMY_PAGES = [
    ("निर्देशपत्र", [
        TEST_MARK,
        "महाराष्ट्र शासन",
        "विधि व न्याय विभाग",
        "निर्देशपत्र",
        "C R 999/2026",
        "नस्ती क्र. संकिर्ण-2026/9999/प्र.क्र.999/का.6",
        "आवक क्र. 9876, दि. 21.09.2026",
        "विषय :- श्री. अ. ब. चाचणी, लिपिक, जिल्हा न्यायालय, चाचणीनगर यांना सुधारित आश्वासित प्रगती योजनेचा पहिला लाभ मंजूर करण्याबाबत.",
        "प्रेषक :- प्रमुख जिल्हा व सत्र न्यायाधीश, चाचणीनगर",
        "पत्र क्र. जा.क्र. चाचणी/999/2026, दि. 17.09.2026",
        "एकूण पाने : 3",
    ], None),
    ("जिल्हा न्यायाधीश यांचे पत्र", [
        TEST_MARK,
        "प्रमुख जिल्हा व सत्र न्यायाधीश, चाचणीनगर यांचे कार्यालय",
        "जा.क्र. चाचणी/999/2026",
        "दिनांक : 17.09.2026",
        "प्रति,",
        "प्रधान सचिव,",
        "विधि व न्याय विभाग, मंत्रालय, मुंबई - 400 032.",
        "विषय :- श्री. अ. ब. चाचणी, लिपिक यांना सुधारित आश्वासित प्रगती योजनेचा पहिला लाभ मंजूर करण्याबाबत.",
        "महोदय,",
        "उपरोक्त विषयान्वये आपणांस विनंती करण्यात येते की, श्री. अ. ब. चाचणी हे या कार्यालयात दि. 01.06.2014 रोजी लिपिक या पदावर नियुक्त झाले आहेत.",
        "त्यांची दि. 01.06.2024 रोजी 10 वर्षांची नियमित सेवा पूर्ण झाली आहे.",
        "त्यांचे सध्याचे मूळ वेतन रु. 35,400/- इतके आहे.",
        "सदर कर्मचाऱ्याच्या विरुद्ध कोणतीही विभागीय चौकशी प्रलंबित नाही.",
        "तरी, त्यांना सुधारित आश्वासित प्रगती योजनेचा पहिला लाभ दि. 01.06.2024 पासून मंजूर करण्यास शासनाची मान्यता मिळावी, ही विनंती.",
        "सोबत : तपशील तक्ता (1 पान).",
        "आपला विश्वासू,",
        "(क. ख. नमुना)",
        "प्रमुख जिल्हा व सत्र न्यायाधीश, चाचणीनगर",
    ], None),
    ("तपशील तक्ता", [
        TEST_MARK,
        "तपशील तक्ता",
    ], [
        ["अ.क्र.", "नाव", "पद", "नियुक्ती दिनांक", "10 वर्षे पूर्ण दिनांक", "सध्याचे मूळ वेतन (रु.)", "मागणी"],
        ["1", "श्री. अ. ब. चाचणी", "लिपिक", "01.06.2014", "01.06.2024", "35,400", "पहिला लाभ"],
        ["2", "श्रीमती ग. घ. उदाहरण", "लिपिक", "15.07.2015", "15.07.2025", "34,800", "पहिला लाभ"],
        ["3", "श्री. च. छ. नमुना", "वरिष्ठ लिपिक", "02.01.2006", "02.01.2016", "48,900", "दुसरा लाभ"],
    ]),
]
SIGN = ["(क. ख. नमुना)", "प्रमुख जिल्हा व सत्र न्यायाधीश, चाचणीनगर"]  # signature under the table

DUMMY_FACTS = {
    "note": "Synthetic test proposal. All names, places and numbers are fake. Use only for Test B (full engine run).",
    "facts": [
        {"field": "cr_no", "value": "999/2026", "page": 1},
        {"field": "file_no", "value": "संकिर्ण-2026/9999/प्र.क्र.999/का.6", "page": 1},
        {"field": "inward_no", "value": "9876", "page": 1},
        {"field": "inward_date", "value": "21.09.2026", "page": 1},
        {"field": "sender", "value": "प्रमुख जिल्हा व सत्र न्यायाधीश, चाचणीनगर", "page": 2},
        {"field": "route", "value": "direct (not through the High Court)", "check": False},
        {"field": "letter_no", "value": "जा.क्र. चाचणी/999/2026", "page": 2},
        {"field": "letter_date", "value": "17.09.2026", "page": 2},
        {"field": "employee", "value": "अ. ब. चाचणी", "page": 2},
        {"field": "post", "value": "लिपिक", "page": 2},
        {"field": "appointment_date", "value": "01.06.2014", "page": 2},
        {"field": "ten_years_date", "value": "01.06.2024", "page": 2},
        {"field": "basic_pay", "value": "35,400", "page": 2},
        {"field": "demand", "value": "सुधारित आश्वासित प्रगती योजनेचा पहिला लाभ", "page": 2},
        {"field": "benefit_from", "value": "01.06.2024", "page": 2},
        {"field": "table_row2_name", "value": "ग. घ. उदाहरण", "page": 3},
        {"field": "table_row2_appointment", "value": "15.07.2015", "page": 3},
        {"field": "table_row3_name", "value": "च. छ. नमुना", "page": 3},
        {"field": "table_row3_post", "value": "वरिष्ठ लिपिक", "page": 3},
        {"field": "table_row3_ten_years", "value": "02.01.2016", "page": 3},
        {"field": "table_row3_pay", "value": "48,900", "page": 3},
    ],
}


def dummy_html(lines, table, tail):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    h = "".join(f'<p class="{"mark" if l == TEST_MARK else ""}">{esc(l)}</p>' for l in lines)
    if table:
        h += "<table>" + "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in table) + "</table>"
        h += "".join(f'<p class="sign">{esc(l)}</p>' for l in tail)
    return h


def dummy_text(lines, table, tail):
    t = list(lines)
    if table:
        t += [" ".join(r) for r in table] + list(tail)
    return "\n".join(t) + "\n"


def build_dummy(out):
    """Pages drawn with FreeSerif (HarfBuzz shaping), then rasterised at 150 dpi into an image-only PDF (like a scan)."""
    css = ("@font-face{font-family:fs;src:url(FreeSerif.ttf);} @font-face{font-family:fs;font-weight:bold;src:url(FreeSerifBold.ttf);}"
           "body{font-family:fs;font-size:12.5pt;line-height:1.45} p{margin:0 0 6pt 0} .mark{font-weight:bold;text-align:right;font-size:10pt}"
           "table{border-collapse:collapse;margin-top:8pt} td{border:1px solid black;padding:3pt;font-size:11pt} .sign{text-align:right;margin-top:10pt}")
    arch = pymupdf.Archive(FONT_DIR)
    src = pymupdf.open()
    texts = []
    for i, (_name, lines, table) in enumerate(DUMMY_PAGES, 1):
        tail = SIGN if table else []
        page = src.new_page(width=595, height=842)
        page.insert_htmlbox(pymupdf.Rect(60, 50, 535, 800), dummy_html(lines, table, tail), css=css, archive=arch)
        texts.append(dummy_text(lines, table, tail))
    img = pymupdf.open()
    for page in src:
        pix = page.get_pixmap(dpi=150)
        p = img.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, pixmap=pix)
    d = os.path.join(out, "dummy_proposal")
    os.makedirs(d, exist_ok=True)
    pdf = os.path.join(d, "dummy_proposal.pdf")
    img.save(pdf, garbage=4, deflate=True)
    json.dump(DUMMY_FACTS, open(os.path.join(d, "facts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return pdf, texts


def main(argv):
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--n")]
    out = pos[0] if pos else os.path.join(ROOT, "tests", "benchmark_set")
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 8
    ocr = "--no-ocr-check" not in argv
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    os.makedirs(os.path.join(out, "ground_truth"), exist_ok=True)
    entries = []
    for k, c in enumerate(pick_pages(n, ocr), 1):
        pid = f"gr-{k:02d}"
        path = os.path.join(ROOT, c["source"])
        doc = pymupdf.open(path)
        page = doc[c["page"] - 1]
        page.get_pixmap(dpi=DPI).save(os.path.join(out, "pages", pid + ".png"))
        open(os.path.join(out, "ground_truth", pid + ".txt"), "w", encoding="utf-8").write(norm(page.get_text("text", sort=True)) + "\n")
        confirmed = c.pop("_confirmed")
        if confirmed:
            open(os.path.join(out, "ground_truth", pid + ".words.txt"), "w", encoding="utf-8").write(" ".join(confirmed) + "\n")
        entries.append(dict(id=pid, kind="gr", pdf_sha256=sha256(path), confirmed_words=len(confirmed or []), **c))
    if "--no-dummy" not in argv:
        pdf, texts = build_dummy(out)
        doc = pymupdf.open(pdf)
        for i, t in enumerate(texts, 1):
            pid = f"dummy-{i:02d}"
            doc[i - 1].get_pixmap(dpi=DPI).save(os.path.join(out, "pages", pid + ".png"))
            open(os.path.join(out, "ground_truth", pid + ".txt"), "w", encoding="utf-8").write(norm(t) + "\n")
            entries.append({"id": pid, "kind": "dummy", "source": "dummy_proposal/dummy_proposal.pdf", "page": i,
                            "table": DUMMY_PAGES[i - 1][2] is not None, "common_word_rate": None, "ocr_agreement": None})
    json.dump({"pages": entries, "settings": {"dpi": DPI, "n_gr": n, "ocr_check": ocr, "min_ocr_agreement": MIN_OCR, "max_impossible_rate": 0.005,
                                              "min_common_word_rate": 0.12}},
              open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    gr = [e for e in entries if e["kind"] == "gr"]
    print(f"benchmark set: {len(gr)} GR pages ({sum(e['table'] for e in gr)} with a table), "
          f"{len(entries) - len(gr)} dummy pages -> {out}")
    for e in entries:
        print(f"  {e['id']}: {e['source']} p.{e['page']}" + (" [table]" if e["table"] else "") +
              (f" ocr-agreement {e['ocr_agreement']}" if e["ocr_agreement"] is not None else ""))
    return 0 if len(gr) == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
