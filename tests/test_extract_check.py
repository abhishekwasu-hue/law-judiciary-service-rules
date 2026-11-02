"""Unit tests for tools/extract_check.py (verbatim guard for cheap-tier extracts). Run: py -m unittest tests.test_extract_check"""
import io, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pymupdf
import extract_check as xc

FONTS = ["/usr/share/fonts/truetype/freefont/FreeSerif.ttf", "/usr/share/fonts/opentype/freefont/FreeSerif.otf",
         "C:/Windows/Fonts/mangal.ttf", "C:/Windows/Fonts/Nirmala.ttf"]
FONTFILE = next((f for f in FONTS if os.path.exists(f)), None)
GR_LINE = "शासन सेवेत दिनांक 01.11.2005 रोजी किंवा त्यानंतर नियुक्त होणाऱ्या कर्मचाऱ्यांसाठी नवीन योजना लागू करण्यात येईल."
GARBLED = ["ििाराष्ट्र शासन दर्वत्त दर्वभार् शासन दनणगय क्रिांक संकीणग",
           "दि. 01.11.2005 पूर्वी पिभरती जादिरात/अदिसूचना दनर्गदित झालेल्या प्रकरणी ककर्वा त्यानंतर",
           "अदिकारी/ किगचारी यांना केंद्र शासनाच्या ितीर्वर जुनी दनर्वृत्ती र्वेतन योजना लार्ू करणेबाबत ििाराष्ट्र ाा"]
OTHER = ("सदर योजनेचा लाभ घेण्यासाठी संबंधित कर्मचाऱ्यांनी विहित नमुन्यात विकल्प सादर करावा. विकल्प सादर करण्याची "
         "अंतिम मुदत सहा महिने राहील. विभाग प्रमुख किंवा कार्यालय प्रमुख यांनी विकल्प अर्जाची तपासणी करुन "
         "प्रस्तुत कर्मचारी या योजनेसाठी पात्र असल्याची खात्री करावी व त्यानंतर आदेश निर्गमित करावेत. "
         "हा शासन निर्णय महाराष्ट्र शासनाच्या संकेतस्थळावर उपलब्ध करण्यात आला असून त्याचा सांकेतांक असा आहे.")


def wj(path, obj):
    with io.open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False)


GR_LINE2 = "सदर आदेश वित्त विभागाच्या सहमतीने निर्गमित करण्यात येत आहे."


@unittest.skipUnless(FONTFILE, "no Devanagari font")
class ExtractCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.pdf = os.path.join(cls.tmp, "pkg.pdf")
        d = pymupdf.open()
        p = d.new_page(); p.insert_text((72, 100), "Proposal page 1 (scan)", fontsize=12)       # 1 proposal
        p = d.new_page()                                                                        # 2 GR text page
        p.insert_text((40, 100), GR_LINE, fontsize=9, fontname="dv", fontfile=FONTFILE)
        p.insert_text((40, 130), GR_LINE2, fontsize=9, fontname="dv", fontfile=FONTFILE)
        p = d.new_page()                                                                        # 3 scanned (image only)
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 50, 50), 0); pix.clear_with(200)
        p.insert_image(pymupdf.Rect(72, 72, 300, 300), pixmap=pix)
        p = d.new_page()                                                                        # 4 legacy font
        p.insert_text((40, 100), "kklu lsosr fnukad 01-11-2005 jksth fdaok R;kuarj fu;qDr gks.kk&;k deZpk&;kalkBh", fontsize=9)
        p = d.new_page()                                                                        # 5 other Devanagari text
        p.insert_text((40, 100), "महाराष्ट्र नागरी सेवा नियमांतील इतर तरतुदी या पानावर आहेत; वरील योजनेचा उल्लेख येथे नाही.", fontsize=9,
                      fontname="dv", fontfile=FONTFILE)
        p = d.new_page()                                                                        # 6 garbled Unicode (broken ToUnicode)
        for k, ln in enumerate(GARBLED):
            p.insert_text((40, 100 + 20 * k), ln, fontsize=9, fontname="dv", fontfile=FONTFILE)
        d.save(cls.pdf); d.close()

    def spec(self, text, pages="2"):
        return {"related": [{"heading": "वित्त विभाग शासन निर्णय", "text": text, "source": f"दि. 31.10.2005, परि. 2 (पृ.{pages}/प.वि.)"}]}

    def run_check(self, spec=None, study=None, **kw):
        return xc.check(self.pdf, spec, study, no_ocr=True, **kw)

    def test_match(self):
        r = self.run_check(self.spec(["“" + GR_LINE + "”", "“" + GR_LINE2 + "”"]))
        self.assertEqual([x["status"] for x in r], ["ok", "ok"])

    def test_mismatch(self):
        bad = GR_LINE.replace("नवीन", "जुनी")
        r = self.run_check(self.spec(["“" + bad + "”"]))
        self.assertEqual(r[0]["status"], "mismatch")
        log = xc.model_log(r, "claude-haiku-5-5", "claude-sonnet-5-5")
        self.assertEqual(len(log), 1)
        self.assertTrue(log[0]["task"].startswith("उतारा: related[1]") and log[0]["to"] == "claude-sonnet-5-5")

    def test_wrong_page_and_out_of_range(self):
        self.assertEqual(self.run_check(self.spec(["“" + GR_LINE + "”"], "5"))[0]["status"], "mismatch")
        r = self.run_check(self.spec(["“" + GR_LINE + "”"], "9"))
        self.assertTrue(r[0]["status"] == "mismatch" and "9" in r[0]["why"])

    def test_devanagari_digits_whitespace_omission(self):
        ex = GR_LINE.replace("01.11.2005", "०१.११.२००५").replace(" किंवा ", "  किंवा\n")
        ex = ex.replace("नियुक्त होणाऱ्या", "नियुक्त … होणाऱ्या")
        r = self.run_check(self.spec(["शासन निर्णय :- “" + ex + "”"], "२"))
        self.assertTrue(r and all(x["status"] == "ok" for x in r), r)

    def test_unverifiable_scanned_and_legacy(self):
        for pg in ("3", "4"):
            r = self.run_check(self.spec(["“" + GR_LINE + "”"], pg))
            self.assertEqual(r[0]["status"], "unverifiable", pg)
        self.assertFalse(any(x["status"] == "mismatch" for x in r))

    def test_ocr_fallback(self):
        od = os.path.join(self.tmp, "ocr"); os.makedirs(od, exist_ok=True)
        with io.open(os.path.join(od, "p-03.ocr.txt"), "w", encoding="utf-8") as f:
            f.write(GR_LINE.replace("ऱ्या", "र्या", 1))
        r = xc.check(self.pdf, self.spec(["“" + GR_LINE + "”"], "3"), None, ocr_dir=od, no_ocr=True)
        self.assertEqual(r[0]["status"], "ok_ocr")

    def test_note_body_quotes_warn_only(self):
        self.assertEqual(xc.note_pages("(पृ.2/प.वि.) व पृ. 4 ते 6 / प.वि. तसेच पृ.8,9/प.वि.; पृ.      /प.वि."), [2, 4, 5, 6, 8, 9])
        bad = GR_LINE.replace("नवीन", "जुनी")
        spec = {"note": {"first": "पत्रास अनुसरुन सादर.",
                         "paras": ["तरतूद “" + GR_LINE + "” अशी आहे (पृ.2/प.वि.).", "तरतूद “" + bad + "” (पृ.2/प.वि.)."]}}
        self.assertEqual(self.run_check(spec), [])          # note body is checked only with note_body=True
        r = self.run_check(spec, note_body=True)
        self.assertEqual([(x["where"], x["status"], x.get("warn_only")) for x in r],
                         [("नोंद परि. 2", "ok", True), ("नोंद परि. 3", "mismatch", True)])
        self.assertEqual(xc.model_log(r), [])                 # never sent back as a failing unit
        sp = os.path.join(self.tmp, "note_spec.json"); wj(sp, spec)
        out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "extract_check.py"), self.pdf, "--spec", sp,
                              "--note-body", "--no-ocr"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("WARN MISMATCH नोंद परि. 3", out.stdout)
        self.assertIn("EXTRACTS OK", out.stdout)

    def test_stale_ocr_ignored(self):
        # OCR made from an earlier package build (pages.json pdf_sha256 differs) must not verify the new package
        od = os.path.join(self.tmp, "ocr_stale"); os.makedirs(od, exist_ok=True)
        with io.open(os.path.join(od, "p-03.ocr.txt"), "w", encoding="utf-8") as f:
            f.write(GR_LINE)
        with io.open(os.path.join(od, "pages.json"), "w", encoding="utf-8") as f:
            json.dump({"pdf_sha256": "0" * 64}, f)
        r = xc.check(self.pdf, self.spec(["“" + GR_LINE + "”"], "3"), None, ocr_dir=od, no_ocr=True)
        self.assertEqual(r[0]["status"], "unverifiable", r)
        with io.open(os.path.join(od, "pages.json"), "w", encoding="utf-8") as f:
            json.dump({"pdf_sha256": xc.sha256_file(self.pdf)}, f)
        r = xc.check(self.pdf, self.spec(["“" + GR_LINE + "”"], "3"), None, ocr_dir=od, no_ocr=True)
        self.assertEqual(r[0]["status"], "ok_ocr", r)

    def test_garbled_page_ocr(self):
        self.assertTrue(xc.garbled(" ".join(GARBLED)) and not xc.garbled(GR_LINE + GR_LINE2))
        r = self.run_check(self.spec(["“" + GR_LINE + "”"], "6"))
        self.assertEqual(r[0]["status"], "unverifiable")
        od = os.path.join(self.tmp, "ocr6"); os.makedirs(od, exist_ok=True)
        with io.open(os.path.join(od, "p-06.ocr.txt"), "w", encoding="utf-8") as f:
            f.write(" ".join(["महाराष्ट्र शासन वित्त विभाग", GR_LINE.replace("कर्मचाऱ्यांसाठी", "कर्मचार्‍यांसाठी"), OTHER]))
        ok = xc.check(self.pdf, self.spec(["“" + GR_LINE + "”"], "6"), None, ocr_dir=od, no_ocr=True)
        self.assertEqual(ok[0]["status"], "ok_ocr", ok)
        para = "“राज्य शासनाच्या सर्व अधिकाऱ्यांना प्रवास भत्ता व दैनिक भत्ता सुधारित दराने देण्यास मंजुरी देण्यात आली आहे.”"
        bad = xc.check(self.pdf, self.spec([para], "6"), None, ocr_dir=od, no_ocr=True)
        self.assertEqual(bad[0]["status"], "mismatch", bad)

    def test_study_part3_and_not_in_package(self):
        study = {"parts": [{"heading": "भाग 0 — वरिष्ठांसाठी ब्रीफिंग", "blocks": [{"para": "“काहीही वेगळे लिहिलेले वाक्य येथे आहे”"}]},
                           {"heading": "भाग 3 — लागू तरतुदी", "blocks": [
                               {"subheading": "शासन निर्णय दि.31.10.2005 (पॅकेज PDF पृ. 2)"},
                               {"para": "“" + GR_LINE2 + "”"},
                               {"table": [["उतारा", "स्रोत"], ["“" + GR_LINE2.replace("सहमतीने", "मान्यतेने") + "”", "परि.3"]]},
                               {"subheading": "पूर्वोदाहरण (पॅकेज PDF मध्ये नाही)"},
                               {"para": "“पूर्वीच्या नस्तीतील वित्त विभागाचा अभिप्राय असा होता”"}]}]}
        r = self.run_check(None, study)
        self.assertEqual([x["status"] for x in r], ["ok", "mismatch", "unverifiable"])
        ex = os.path.join(self.tmp, "old.txt")
        with io.open(ex, "w", encoding="utf-8") as f:
            f.write("नोंद: पूर्वीच्या नस्तीतील वित्त विभागाचा अभिप्राय असा होता.")
        self.assertEqual(self.run_check(None, study, extras=[self.tmp])[2]["status"], "ok_extra")

    def test_cli(self):
        sp, lg = os.path.join(self.tmp, "spec.json"), os.path.join(self.tmp, "log.json")
        wj(sp, self.spec(["“" + GR_LINE.replace("नवीन", "जुनी") + "”"]))
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "extract_check.py"), self.pdf, "--spec", sp, "--no-ocr",
                            "--log-out", lg, "--from", "L", "--to", "M"], capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("EXTRACTS FAIL (1 mismatch)", r.stdout)
        with io.open(lg, encoding="utf-8") as f: self.assertEqual(json.load(f)[0]["from"], "L")
        wj(sp, self.spec(["“" + GR_LINE + "”"]))
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "extract_check.py"), self.pdf, "--spec", sp, "--no-ocr"],
                           capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(r.returncode, 0); self.assertIn("EXTRACTS OK (checked 1, unverifiable 0)", r.stdout)

    def test_related_marker_forms(self):
        """C27 (02.11.2026): the note's related source cites "(पृ.N/प.वि.)"; the older "(पॅकेज PDF पृ. N)" is still read;
        no marker -> the --extra sources (as "(पॅकेज PDF मध्ये नाही)"); a "पृ.N/प.वि." inside the extract text is ignored."""
        def sp(src, text=None):
            return {"related": [{"heading": "वित्त विभाग शासन निर्णय", "text": text or ["“" + GR_LINE + "”"], "source": src}]}
        for src in ("परि. 2 (पृ.2/प.वि.)", "परि. 2 (पृ.2,5/प.वि.)", "परि. 2 (पृ.२,५/प.वि.)", "परि. 2 (पॅकेज PDF पृ. 2)"):
            with self.subTest(src=src):
                r = self.run_check(sp(src))
                self.assertEqual(r[0]["status"], "ok", r)
        r = self.run_check(sp("शासन निर्णय दि. 31.10.2005, परि. 2"))
        self.assertEqual((r[0]["status"], r[0]["pages"]), ("unverifiable", []))
        ex = os.path.join(self.tmp, "gr_extra"); os.makedirs(ex, exist_ok=True)
        with io.open(os.path.join(ex, "gr.txt"), "w", encoding="utf-8") as f:
            f.write(GR_LINE)
        self.assertEqual(self.run_check(sp("शासन निर्णय दि. 31.10.2005, परि. 2"), extras=[ex])[0]["status"], "ok_extra")
        r = self.run_check(sp("परि. 2", ["“" + GR_LINE + " (पृ.5/प.वि.)”"]))   # an old file's own page ref inside the quote
        self.assertEqual(r[0]["pages"], [])

    def test_pages_cited(self):
        self.assertEqual(xc.pages_cited("(पॅकेज PDF पृ. 12-14) व (पॅकेज PDF पृ. १६,18)"), [12, 13, 14, 16, 18])


if __name__ == "__main__":
    unittest.main()
