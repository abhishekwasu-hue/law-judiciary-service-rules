"""tools/consistency_check.py — cross-document consistency (audit 05.11.2026 Q-F15, INSTRUCTIONS §4.30(2))."""
import glob, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "consistency_check.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import consistency_check as C  # noqa: E402

SIGNERS = ["(अ.मा. वसू)", "क. अ. (अ.का.)", "अ.स. (श्री. वडनेरकर)", "उ.वि.स. नि. उ.स. (श्री. बोंद्रे)",
           "सचिव व व. वि. स. (श्री. बिले)"]


def spec(paras, **kw):
    s = {"note": {"first": "प्रमुख जिल्हा व सत्र न्यायाधीश, भंडारा यांच्या पृ.1/प.वि. वरील दि. 17.09.2026 रोजीच्या पत्रास अनुसरून सादर.",
                  "paras": paras, "signers": SIGNERS}}
    s.update(kw)
    return s


def letter(points, **kw):
    L = {"ref_no": "संकिर्ण-2026/226/प्र.क्र.131/का.6", "date": "__.__.2026", "to": ["प्रबंधक,"], "subject": "विषय",
         "refs": ["आपले पत्र दि. 17.09.2026"], "intro": "उपरोक्त विषयाबाबत …", "points": points}
    L.update(kw)
    return L


def run(sp, study=None):
    f, n, m = C.check(sp, study)
    return f


class Consistency(unittest.TestCase):
    def test_amount_differs_note_letter(self):
        sp = spec(["श्रीमती रेखा राणे यांना रु. 76,23,814/- इतके अतिप्रदान झाले आहे."],
                  letter=letter(["1. श्रीमती रेखा राणे यांना रु. 76,23,841/- इतके अतिप्रदान झाले आहे."]))
        f = run(sp)
        self.assertEqual([(x["check"], x["fact"], x["value"]) for x in f], [("only_in", "amount", "रु. 76,23,841/-")])
        self.assertEqual(f[0]["docs"], ["पत्र", "टिप्पणी"])
        self.assertEqual(f[0]["where"], ["letter.points[0]"])
        self.assertEqual(C.warning_text(f[0]), "पडताळणी अपूर्ण — विसंगती: रक्कम रु. 76,23,841/- टिप्पणीत नाही, पत्र / टिप्पणी")
        # the same amount, bare in a note table, Western grouping / Rs. in the letter -> present
        sp = spec([{"table": [["तपशील", "रक्कम (रु.)"], ["अतिप्रदान", "76,23,814"]]}],
                  letter=letter(["Rs. 7,623,814 इतके अतिप्रदान", "रु. ७६,२३,८१४/-"]))
        self.assertEqual(run(sp), [])

    def test_name_misspelt(self):
        sp = spec(["श्री. अनंत वडनेरकर यांनी अर्ज सादर केला आहे."],
                  letter=letter(["1. श्री. अनंत वडणेरकर यांच्या अर्जाबाबत."]))
        f = run(sp)
        self.assertEqual([(x["check"], x["value"]) for x in f], [("name", "अनंत वडनेरकर / अनंत वडणेरकर")])
        self.assertEqual(f[0]["docs"], ["टिप्पणी", "पत्र"])
        # surname-only form near the full name, inside the note itself
        f = run(spec(["श्री. अनंता लक्ष्मण देशमुख यांनी अर्ज केला.", "श्री. देसमुख यांचा अर्ज."]))
        self.assertEqual([x["check"] for x in f], ["name"])
        # spaces / dots / short form: the same name, no warning
        self.assertEqual(run(spec(["श्री. ह.ना. आपटे यांनी अर्ज केला.", "श्री. ह. ना. आपटे यांचा अर्ज.", "श्री. आपटे यांना."])), [])
        # different people (short names, distance > 1; different surnames) — no warning
        self.assertEqual(run(spec(["श्री. अनिल पाटील व श्री. सुनील पवार यांनी अर्ज केला."])), [])

    def test_date_only_in_order(self):
        sp = spec(["दि. 08.03.2021 रोजी निधन झाले."],
                  order={"type": "gr", "subject": "विषय", "ref_no": "संकिर्ण-2026/1/प्र.क्र.1/का.6", "date": "05.11.2026",
                         "read": ["वित्त विभाग, शासन परिपत्रक दि. 22.11.2021."],
                         "operative": ["दि. 08.03.2021 रोजी निधन झाले.", "दि. 09.03.2021 पासून लागू."]})
        f = run(sp)
        self.assertEqual(sorted(x["value"] for x in f), ["09.03.2021", "22.11.2021"])
        self.assertTrue(all(x["docs"] == ["शासन निर्णय-प्रारूप", "टिप्पणी"] for x in f))
        # the order's own issue date (date key) is not a fact; present in the note's related source -> fine
        sp["related"] = [{"heading": "वित्त विभाग, शासन परिपत्रक दि. 22.11.2021", "text": ["“…”"]}]
        self.assertEqual([x["value"] for x in run(sp)], ["09.03.2021"])

    def test_english_parawise_same_date_other_format(self):
        sp = spec(["रिट याचिका क्र. 35697/2026 (पृ.1/प.वि.) कृपया पहावी. याचिका दि. 13.10.2026 रोजी प्रतिज्ञापित केली आहे.",
                   "शासन निर्णय दि. 19.04.2022 नुसार रु. 1,20,000/- अदा केले."],
                  parawise={"case": "WRIT PETITION (L) NO. 35697 OF 2026", "petitioner": "Shri. Rekha Rane",
                            "paras": [{"para": "1", "remarks": "The petition was affirmed on 13th October 2026; the GR dated "
                                       "April 19, 2022 and 19/04/2022 granted Rs. 1,20,000/-."}]})
        self.assertEqual(run(sp), [])

    def test_case_number_differs(self):
        sp = spec(["रिट याचिका क्र. 35697/2026 कृपया पहावी."],
                  parawise={"case": "WRIT PETITION (L) NO. 35679 OF 2026", "paras": []})
        f = run(sp)
        self.assertEqual([(x["check"], x["fact"]) for x in f], [("case_no", "case")])
        self.assertIn("WP 35697/2026", f[0]["what"])
        # a precedent petition of another year / far number cited in the grounds is not a typo
        sp["parawise"]["case"] = "WRIT PETITION NO. 35697 OF 2026"
        sp["parawise"]["paras"] = [{"para": "5", "remarks": "as held in W.P. No. 4759 of 2022"}]
        self.assertEqual(run(sp), [])

    def test_quotes_ignored(self):
        sp = spec(["शासन निर्णयात “दि. 01.04.2010 पासून रु. 5,000/- देय” असे नमूद आहे."],
                  letter=letter(["1. संदर्भाधीन आदेशात “दि. 02.02.2002 रोजी रु. 9,999/- मंजूर” असे नमूद आहे."]))
        self.assertEqual(run(sp), [])

    def test_signer_chain_and_refs_ignored(self):
        sp = spec(["श्री. राजेश वडनेरकर यांनी अभिप्राय दिला."], letter=letter(["1. माहिती पृ.12,345/प.वि. वर.", "2. श्री. ____ यांचे."]))
        sp["note"]["signers"] = SIGNERS[:2] + ["अ.स. (श्री. वडणेरकर)"] + SIGNERS[3:]
        self.assertEqual(run(sp), [])

    def test_study_part0(self):
        study = {"parts": [{"heading": "भाग 0 — वरिष्ठांसाठी ब्रीफिंग", "blocks": [
            {"table": [["तपशील", "माहिती", "पृ./प.वि."], ["निधन", "दि. 08.03.2021", "(पॅकेज PDF पृ. 3)"],
                       ["सुनावणी", "दि. 20.11.2026", "—"]]}]},
            {"heading": "भाग 1 — मराठी रूपांतर", "blocks": [{"para": "दि. 01.01.1999"}]}]}
        f = run(spec(["दि. 08.03.2021 रोजी निधन झाले."]), study)
        self.assertEqual([(x["value"], x["docs"][0]) for x in f], [("20.11.2026", "अभ्यास भाग 0")])

    def test_post_differs(self):
        sp = spec([{"table": [["अ.क्र.", "नाव", "पद"], ["1", "श्रीमती रेखा राणे", "लघुलेखक (निम्न श्रेणी)"]]}],
                  letter=letter([{"table": [["नाव", "पदनाम"], ["श्रीमती रेखा राणे", "लिपिक"]]}]))
        f = run(sp)
        self.assertEqual([(x["check"], x["docs"]) for x in f], [("post", ["टिप्पणी", "पत्र"])])

    def test_cr_number(self):
        f = run(spec(["C R 131-2026 नुसार."], letter=letter(["संदर्भ C R 113-2026."])))
        self.assertEqual([(x["fact"], x["value"]) for x in f], [("cr", "113-2026")])

    def test_cli_details_and_json(self):
        sp = spec(["श्री. अनंत वडनेरकर यांनी रु. 1,00,000/- मागितले."],
                  letter=letter(["श्री. अनंत वडणेरकर यांनी रु. 1,10,000/- मागितले."]))
        with tempfile.TemporaryDirectory() as d:
            p, det, js = (os.path.join(d, x) for x in ("s.json", "det.txt", "f.json"))
            json.dump(sp, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            r = subprocess.run([sys.executable, "-I", TOOL, p, "--details", det, "--json", js], capture_output=True,
                               text=True, encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("consistency_check: 2 docs,", r.stdout)
            self.assertIn("2 warnings", r.stdout)
            self.assertNotIn("वडणेरकर", r.stdout)            # S-F3: no case text on stdout
            self.assertNotIn("1,10,000", r.stdout)
            self.assertIn("वडणेरकर", open(det, encoding="utf-8").read())
            recs = json.load(open(js, encoding="utf-8"))
            self.assertEqual(sorted(x["check"] for x in recs), ["name", "only_in"])
            r = subprocess.run([sys.executable, "-I", TOOL, os.path.join(d, "absent.json")], capture_output=True, text=True,
                               encoding="utf-8", timeout=60)
            self.assertEqual(r.returncode, 2)

    def test_samples_run(self):
        """Every approved sample is read without a crash (findings are reported, never an error)."""
        for f in sorted(glob.glob(os.path.join(ROOT, "samples", "specs", "*.json"))):
            sp = json.load(open(f, encoding="utf-8-sig"))
            find, ndocs, _ = C.check(sp)
            self.assertGreaterEqual(ndocs, 1, f)
            self.assertIsInstance(find, list, f)


if __name__ == "__main__":
    unittest.main()
