"""Unit tests for tools/fact_check.py (audit 05.11.2026 Q-F1: fact-anchor check of the note / letter against the cited
package page). Run: python3 -m pytest -q tests/test_fact_check.py"""
import glob, io, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pymupdf
import fact_check as fc

TOOL = os.path.join(ROOT, "tools", "fact_check.py")
FONTS = ["/usr/share/fonts/truetype/freefont/FreeSerif.ttf", "/usr/share/fonts/opentype/freefont/FreeSerif.otf",
         "C:/Windows/Fonts/mangal.ttf", "C:/Windows/Fonts/Nirmala.ttf"]
FONTFILE = next((f for f in FONTS if os.path.exists(f)), None)
FILL = "हा मजकूर पानावरील मजकूर-स्तर वापरण्यायोग्य होण्यासाठी पुरेसा लांब ठेवलेला आहे असे समजावे."


def wj(path, obj):
    with io.open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False)


def line(p, y, text):
    p.insert_text((40, y), text, fontsize=9, fontname="dv", fontfile=FONTFILE)


@unittest.skipUnless(FONTFILE, "no Devanagari font")
class FactCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.pdf = os.path.join(cls.tmp, "pkg.pdf")
        d = pymupdf.open()
        p = d.new_page()                                                                     # 1 covering letter
        line(p, 80, "प्रमुख जिल्हा व सत्र न्यायाधीश, भंडारा पत्र क्र.बी/विवेतन-एनजीबी/1080/2026, दि. 25.03.2026")
        line(p, 100, FILL)
        p = d.new_page()                                                                     # 2 application
        line(p, 80, "श्रीमती एन. जी. बारई यांचा अर्ज दिनांक ०४/०२/२०२६ — अतिरिक्त कार्यभार ०८/०५/२०२४ पासून")
        line(p, 100, "थकबाकी रक्कम रु. 1,27,24,560/- इतकी आहे. " + FILL)
        p = d.new_page()                                                                     # 3 office order
        line(p, 80, "कार्यालयीन आदेश क्र.108/2024 दि. 06.05.2024 " + FILL)
        d.new_page()                                                                         # 4 scanned (no text)
        p = d.new_page()                                                                     # 5 GR
        line(p, 80, "वित्त विभाग शासन निर्णय क्र.वेतन-1311/प्र.क्र.17/सेवा-3, दिनांक 27.12.2011 " + FILL)
        d.save(cls.pdf); d.close()
        wj(cls.pdf + ".map.json", {"प्रस्ताव": {"first_page": 1, "pages": [1, 2, 3, 4]},
                                   "वित्त विभाग GR दि. 27.12.2011": {"first_page": 5, "pages": [5]}})

    def run_spec(self, spec, *extra):
        sp = os.path.join(self.tmp, "spec.json"); wj(sp, spec)
        js = os.path.join(self.tmp, "out.json")
        r = subprocess.run([sys.executable, TOOL, self.pdf, "--spec", sp, "--no-ocr", "--json", js] + list(extra),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        with io.open(js, encoding="utf-8") as f: recs = json.load(f)
        return r, recs

    def recs(self, para, **kw):
        spec = {"note": {"first": kw.get("first", "पत्रास अनुसरून सादर."), "paras": para if isinstance(para, list) else [para]}}
        spec.update(kw.get("extra", {}))
        return fc.check(self.pdf, spec, no_ocr=True)

    def one(self, recs, kind):
        xs = [r for r in recs if r["kind"] == kind]
        self.assertEqual(len(xs), 1, recs)
        return xs[0]

    def test_date_ok_on_cited_page(self):
        r = self.one(self.recs("कार्यालयीन आदेश दि. 06.05.2024 रोजी निर्गमित करण्यात आला (पृ.3/प.वि.)."), "date")
        self.assertEqual((r["status"], r["pages"], r["mode"]), ("ok", [3], "sentence"))

    def test_date_found_elsewhere(self):
        r = self.one(self.recs("कार्यालयीन आदेश दि. 06.05.2024 रोजी निर्गमित करण्यात आला (पृ.1/प.वि.)."), "date")
        self.assertEqual((r["status"], r["found_on"]), ("elsewhere", [3]))

    def test_date_missing(self):
        r = self.one(self.recs("कार्यालयीन आदेश दि. 07.05.2024 रोजी निर्गमित करण्यात आला (पृ.3/प.वि.)."), "date")
        self.assertEqual(r["status"], "mismatch")

    def test_devanagari_and_slash_dates(self):
        recs = self.recs("श्रीमती एन. जी. बारई यांनी दि. 04.02.2026 रोजीचा अर्ज (पृ.2/प.वि.) सादर केला आहे. "
                         "त्यांनी दि. ०८.०५.२०२४ पासून कार्यभार सांभाळला आहे.")
        ds = [r for r in recs if r["kind"] == "date"]
        self.assertEqual([(r["status"], r["mode"]) for r in ds], [("ok", "sentence"), ("ok", "para")])
        self.assertEqual(self.one(recs, "name")["status"], "ok")

    def test_amount_indian_grouping(self):
        ok = self.one(self.recs("थकबाकीची रक्कम रु. 1,27,24,560/- इतकी आहे (पृ.2/प.वि.)."), "amount")
        self.assertEqual(ok["status"], "ok")
        bad = self.one(self.recs("थकबाकीची रक्कम रु. 1,27,24,650/- इतकी आहे (पृ.2/प.वि.)."), "amount")
        self.assertEqual(bad["status"], "mismatch")

    def test_letter_no(self):
        r = self.one(self.recs("कार्यालयीन आदेश क्र.108/2024 अन्वये कार्यभार सोपविला (पृ.3/प.वि.)."), "letter_no")
        self.assertEqual(r["status"], "ok")
        r = self.one(self.recs("कार्यालयीन आदेश क्र.109/2024 अन्वये कार्यभार सोपविला (पृ.3/प.वि.)."), "letter_no")
        self.assertEqual(r["status"], "mismatch")

    def test_page_range_ref(self):
        recs = self.recs("वित्त विभाग, शासन निर्णय क्र.वेतन-1311/प्र.क्र.17/सेवा-3, दि. 27.12.2011 मध्ये तरतूद आहे (पृ.4-5/प.वि.).")
        self.assertTrue(all(r["status"] == "ok" and r["pages"] == [4, 5] for r in recs), recs)
        self.assertEqual({r["kind"] for r in recs}, {"date", "letter_no"})

    def test_quotes_and_related_ignored(self):
        recs = self.recs("अर्जात “दिनांक 09.09.1999 रोजी रु. 5,55,555/- अदा केले” असे नमूद आहे (पृ.2/प.वि.).",
                         extra={"related": [{"heading": "GR", "text": ["दि. 01.01.2001"], "source": "(पृ.5/प.वि.)"}]})
        self.assertEqual(recs, [])

    def test_ref_no_and_page_refs_ignored(self):
        spec = {"note": {"first": "पत्रास अनुसरून सादर.", "paras": ["सबब, पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. "
                                                                  "संकिर्ण-2026/226/प्र.क्र.131/का.6 (पृ.12/प.वि.)"]},
                "letter": {"ref_no": "संकिर्ण-2026/226/प्र.क्र.131/का.6", "date": "__.__.2026", "subject": "विशेष वेतनाबाबत."}}
        self.assertEqual(fc.check(self.pdf, spec, no_ocr=True), [])

    def test_scanned_page_unverifiable(self):
        r = self.one(self.recs("आदेश दि. 06.05.2024 रोजीचा आहे (पृ.4/प.वि.)."), "date")
        self.assertEqual(r["status"], "unverifiable")

    def test_page_outside_package(self):
        r = self.one(self.recs("आदेश दि. 06.05.2024 रोजीचा आहे (पृ.40/प.वि.)."), "date")
        self.assertEqual(r["status"], "mismatch")

    def test_table_row_uses_ref_before_table(self):
        recs = self.recs(["सदर प्रकरणाची वस्तुस्थिती खालीलप्रमाणे आहे (पृ.3/प.वि.):-",
                          {"table": [["अ.क्र.", "तपशील", "दिनांक"], ["1", "कार्यभार आदेश", "06.05.2024"], ["2", "अर्ज", "01.01.2020"]]}])
        ds = [r for r in recs if r["kind"] == "date"]
        self.assertEqual([(r["mode"], r["status"]) for r in ds], [("table", "ok"), ("table", "mismatch")])
        self.assertIn("तक्ता ओळ 2", ds[1]["where"])

    def test_wide_letter_and_unreffed_para(self):
        spec = {"note": {"first": "सादर.", "paras": ["अर्ज दि. 04.02.2026 रोजीचा आहे.", "आदेश दि. 27.12.2011 रोजीचा आहे."]},
                "letter": {"ref_no": "संकिर्ण-2026/226/प्र.क्र.131/का.6",
                           "refs": ["आपले पत्र क्र.बी/विवेतन-एनजीबी/1080/2026, दि. 25.03.2026"]}}
        recs = fc.check(self.pdf, spec, no_ocr=True)
        self.assertTrue(all(r["mode"] == "wide" for r in recs), recs)
        st = {(r["where"], r["kind"]): r["status"] for r in recs}
        self.assertEqual(st[("टिप्पणी परि. 2", "date")], "ok")             # on proposal page 2
        self.assertEqual(st[("टिप्पणी परि. 3", "date")], "elsewhere")     # only on GR page 5
        self.assertEqual(st[("पत्र 1 refs", "letter_no")], "ok")
        self.assertEqual(st[("पत्र 1 refs", "date")], "ok")

    def test_sentence_split_keeps_abbreviations(self):
        t = "श्री. आर. टी. लाखे यांनी दि. 06.05.2024 रोजी कार्यभार सोडला (पृ.3/प.वि.). नंतरचा अर्ज (पृ.2/प.वि.) आहे."
        spans = fc.sentence_spans(t)
        self.assertEqual(len(spans), 2, spans)

    def test_stdout_has_no_case_text(self):
        det = os.path.join(self.tmp, "details.log")
        r, recs = self.run_spec({"note": {"first": "सादर.", "paras": [
            "श्रीमती एन. जी. बारई यांनी दि. 07.05.2024 रोजी रु. 9,99,999/- मागितले आहेत (पृ.2/प.वि.)."]}}, "--details", det)
        self.assertNotIn("07.05.2024", r.stdout)
        self.assertNotIn("9,99,999", r.stdout)
        self.assertNotIn("बारई", r.stdout)
        self.assertIn("WARN NOT FOUND टिप्पणी परि. 2 दिनांक पृ.2", r.stdout)
        self.assertIn("fact_check: 3 facts, ok 1, mismatch 2, unverifiable 0", r.stdout)
        with io.open(det, encoding="utf-8") as f: d = f.read()
        self.assertIn("07.05.2024", d)

    def test_bad_args_exit_2(self):
        r = subprocess.run([sys.executable, TOOL, self.pdf], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_ocr_dir_used_for_scanned_page(self):
        od = os.path.join(self.tmp, "ocr"); os.makedirs(od, exist_ok=True)
        with io.open(os.path.join(od, "p-04.ocr.txt"), "w", encoding="utf-8") as f:
            f.write("आदेश दिनांक ०६/०५/२०२४ " + FILL)
        spec = {"note": {"first": "सादर.", "paras": ["आदेश दि. 06.05.2024 रोजीचा आहे (पृ.4/प.वि.)."]}}
        r = [x for x in fc.check(self.pdf, spec, ocr_dir=od, no_ocr=True) if x["kind"] == "date"][0]
        self.assertEqual(r["status"], "ok")

    def test_engine_fact_lines(self):
        import engine_supabase as es
        recs = [{"where": "टिप्पणी परि. 3", "kind": "date", "pages": [5], "mode": "sentence", "status": "mismatch"},
                {"where": "टिप्पणी परि. 4", "kind": "amount", "pages": [6, 7], "mode": "para", "status": "elsewhere", "found_on": [9]},
                {"where": "पत्र 1 refs", "kind": "letter_no", "pages": [], "mode": "wide", "status": "mismatch"},
                {"where": "टिप्पणी परि. 5", "kind": "name", "pages": [2], "mode": "sentence", "status": "unverifiable"},
                {"where": "टिप्पणी परि. 3", "kind": "date", "pages": [5], "mode": "sentence", "status": "mismatch", "dup": True}]
        ls = es.fact_lines(recs)
        self.assertEqual(ls[0], "पडताळणी अपूर्ण — टिप्पणीतील तथ्य: टिप्पणी परि. 3 दिनांक पृ.5 वर आढळली नाही — वापरण्यापूर्वी तपासा")
        self.assertIn("पृ.6-7 वर आढळली नाही (पृ.9 वर आढळली)", ls[1])
        self.assertTrue(ls[2].startswith("मॉडेल: तथ्य-तपासणी — पान-संदर्भ नसलेली 1 तथ्ये"))
        self.assertTrue(ls[3].startswith("मॉडेल: तथ्य-तपासणी — 1 तथ्ये पडताळता आली नाहीत"))
        self.assertEqual(len(ls), 4)
        many = [dict(recs[0], where=f"टिप्पणी परि. {i}") for i in range(7)]
        ls = es.fact_lines(many)
        self.assertEqual(len(ls), 5)
        self.assertIn("आणखी 3 तथ्ये", ls[-1])


class Samples(unittest.TestCase):
    def test_every_sample_runs_on_a_dummy_package(self):
        tmp = tempfile.mkdtemp()
        pdf = os.path.join(tmp, "dummy.pdf")
        d = pymupdf.open()
        for i in range(130):
            d.new_page().insert_text((72, 100), f"Dummy package page {i + 1} with enough text for a usable text layer.", fontsize=10)
        d.save(pdf); d.close()
        for f in sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "*.json"))):
            with io.open(f, encoding="utf-8") as fh: spec = json.load(fh)
            recs = fc.check(pdf, spec, no_ocr=True)
            for r in recs:
                self.assertIn(r["status"], ("ok", "elsewhere", "mismatch", "unverifiable"), (f, r))
                self.assertIn(r["kind"], fc.KIND_LABEL, (f, r))
            # the Section's own letter ref_no is never a fact
            for L in ([spec.get("letter")] if isinstance(spec.get("letter"), dict) else []) + list(spec.get("letters") or []):
                if isinstance(L, dict) and L.get("ref_no"):
                    own = fc.X.norm(L["ref_no"])
                    self.assertFalse(any(r["kind"] == "letter_no" and r["key"] == own for r in recs), f)


if __name__ == "__main__":
    unittest.main()
