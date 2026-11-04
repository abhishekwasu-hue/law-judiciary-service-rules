"""Regression tests for tools/verify_outputs.py.
Run: py -m unittest tests.test_verify_outputs -v        (runner: python3 -m unittest tests.test_verify_outputs -v)
GOOD fixture = samples/specs/CR122 built with tools/build_note_letter.py + a Study built with tools/build_study.py
+ a small package PDF made here with pymupdf (stamps written directly, so the test does not depend on pkg3).
Then one must-FAIL fixture per rule."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import docx
import pymupdf as m
from docx.oxml.ns import qn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SPEC = os.path.join(ROOT, "samples", "specs", "CR122_2026_pay-fixation_info-letter.json")
PRE = "CR122"
NPP = 16          # proposal pages
NENC = 4          # enclosure pages -> package 20 pages (CR122 cites up to पृ.18)
FONTS = ["/usr/share/fonts/truetype/freefont/FreeSerif.ttf", "/usr/share/fonts/opentype/freefont/FreeSerif.otf",
         "C:/Windows/Fonts/mangal.ttf", "C:/Windows/Fonts/Nirmala.ttf"]
FONTFILE = next((f for f in FONTS if os.path.exists(f)), None)
# LINT_SKIP: the must-FAIL fixtures are built from deliberately bad specs, which the pre-build lint would refuse
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", LINT_SKIP="1")


sys.path.insert(0, TOOLS)
import lint_spec as L  # noqa: E402

def py(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", env=ENV)


def build_note(spec, outdir):
    sp = os.path.join(outdir, "_spec.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    r = py(os.path.join(TOOLS, "build_note_letter.py"), sp, outdir, PRE)
    assert r.returncode == 0, r.stderr
    os.remove(sp)
    pdf = os.path.join(outdir, f"{PRE}_Note_and_Letter.pdf")   # soffice preview, not under test
    if os.path.exists(pdf):
        os.remove(pdf)


def study_spec(spec):
    n = spec["note"]
    notes = [n["first"]] + [p for p in n["paras"] if isinstance(p, str)]
    parts = [{"heading": "भाग 0 — वरिष्ठांसाठी ब्रीफिंग", "blocks": [
                {"bullets": ["प्रस्ताव : बेलिफ पदावरील पदोन्नतीनंतरची वेतननिश्चिती (पृ.4-5/प.वि.)"]},
                {"table": [["तपशील", "माहिती", "पृ./प.वि."], ["विकल्प अर्ज", "24.01.2025", "15-16"]]}]},
             {"heading": "भाग 1 — प्रस्तावाचे मराठी रूपांतर", "blocks": [{"para": "पान 1 … (पॅकेज PDF पृ. 1)"}]},
             {"heading": "भाग 2 — गोषवारा", "blocks": [{"para": "गोषवारा"}]},
             {"heading": "भाग 3 — लागू तरतुदी", "blocks": [{"para": r["heading"]} for r in spec["related"]]},
             {"heading": "भाग 4 — शंका", "blocks": [{"para": "शंका"}]},
             {"heading": "भाग 5 — नोंद-मसुदा", "blocks": [{"para": t} for t in notes]},
             {"heading": "भाग 6 — पत्र-मसुदा", "blocks": [{"para": spec["letter"]["intro"]}]},
             {"heading": "भाग 7 — पडताळणी-नोंद", "blocks": [{"para": "पडताळणी"}]}]
    return {"title": "C R 122/2026 — अभ्यास-फाइल", "parts": parts}


def build_study(st, outdir):
    sp = os.path.join(outdir, "_study.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    r = py(os.path.join(TOOLS, "build_study.py"), sp, os.path.join(outdir, f"{PRE}_Study.docx"))
    assert r.returncode == 0, r.stderr
    os.remove(sp)


def build_pkg(path, stamp=True, skip_stamp_on=None, extra_page=False, annot_on_proposal=False, mark_status=None):
    d = m.open()
    total = NPP + NENC + (1 if extra_page else 0)
    for i in range(total):
        p = d.new_page()
        p.insert_text((72, 100), f"Page body {i + 1}", fontsize=12)
    for i, p in enumerate(d, 1):
        if stamp and i != skip_stamp_on:
            p.insert_text((p.rect.width / 2 - 25, p.rect.height - 12), f"पृ. {i} / {total}", fontsize=10,
                          fontname="dv", fontfile=FONTFILE)
    hp = d[NPP]  # first enclosure page
    a = hp.add_highlight_annot(hp.search_for("Page body")[0]); a.update()
    if annot_on_proposal:
        p0 = d[0]
        a = p0.add_highlight_annot(p0.search_for("Page body")[0]); a.update()
    d.set_toc([[1, "प्रस्ताव", 1], [1, "वित्त विभाग GR दि. 06.11.1984", NPP + 1]])
    d.save(path); d.close()
    mp = {"प्रस्ताव": {"first_page": 1, "pages": list(range(1, NPP + 1))},
          "वित्त विभाग GR दि. 06.11.1984": {"first_page": NPP + 1, "pages": list(range(NPP + 1, NPP + NENC + 1))},
          "marks": [mark_status or {"label": "वित्त विभाग GR दि. 06.11.1984", "pdf_page": NPP + 1, "status": "highlighted", "hits": 1}]}
    with open(path + ".map.json", "w", encoding="utf-8") as f:
        json.dump(mp, f, ensure_ascii=False)


PKGNAME = "17-09-2026 Bailiff pay fixation.pdf"


def set_text(path, old, new):
    d = docx.Document(path); n = 0
    for t in d.element.body.iter(qn("w:t")):
        if t.text and old in t.text:
            t.text = t.text.replace(old, new); n += 1
    assert n, f"'{old}' not found in {path}"
    d.save(path)


@unittest.skipIf(FONTFILE is None, "no Devanagari font for the page stamps")
class VerifyOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="verify_")
        with open(SPEC, encoding="utf-8") as f:
            cls.spec = json.load(f)
        cls.good = os.path.join(cls.tmp, "good"); os.makedirs(cls.good)
        build_note(cls.spec, cls.good)
        build_study(study_spec(cls.spec), cls.good)
        build_pkg(os.path.join(cls.good, PKGNAME))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def case(self, name):
        d = os.path.join(self.tmp, name)
        shutil.copytree(self.good, d)
        return d

    def run_verify(self, d, pkg=PKGNAME, npp=NPP, extra=()):
        r = py(os.path.join(TOOLS, "verify_outputs.py"), d, PRE, os.path.join(d, pkg), str(npp), *extra)
        return r.returncode, r.stdout + r.stderr

    def must_fail(self, d, needle, **kw):
        rc, out = self.run_verify(d, **kw)
        self.assertNotEqual(rc, 0, out)
        self.assertNotIn("ALL OK", out)
        fails = [ln for ln in out.splitlines() if ln.startswith("FAIL:")]
        self.assertTrue(any(needle in ln for ln in fails), f"expected FAIL containing '{needle}':\n{out}")

    def spec_with(self, fn):
        s = copy.deepcopy(self.spec); fn(s); return s

    # ---- GOOD ----
    def test_00_good_all_ok(self):
        rc, out = self.run_verify(self.good)
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)
        self.assertNotIn("FAIL:", out)

    # ---- must FAIL ----
    def test_internal_id_in_study(self):
        d = self.case("id")
        st = study_spec(self.spec); st["parts"][3]["blocks"].append({"para": "स्रोत z5_0100"})
        build_study(st, d)
        self.must_fail(d, "Study internal ids")

    def test_page_ref_beyond_package(self):
        d = self.case("p99")
        build_note(self.spec_with(lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " (पृ. 99 / प.वि.)")), d)
        self.must_fail(d, "page 99 outside package")

    def test_page_ref_list_in_study(self):
        d = self.case("p99s")
        st = study_spec(self.spec); st["parts"][2]["blocks"].append({"para": "पत्र (पृ.५ ते ७, 99/प.वि.)"})
        build_study(st, d)
        self.must_fail(d, "page 99 outside package")

    def test_aapli(self):
        d = self.case("aapli")
        set_text(os.path.join(d, f"{PRE}_Note_and_Letter.docx"), "आपला,", "आपली,")
        self.must_fail(d, "letter ending")

    def test_missing_signer(self):
        d = self.case("signer")
        build_note(self.spec_with(lambda s: s["note"]["signers"].pop(1)), d)
        self.must_fail(d, "note signer chain")

    def test_ams_without_finance(self):
        d = self.case("ams")
        build_note(self.spec_with(lambda s: s["note"]["signers"].append("अ.मु.स. (वित्त)")), d)
        self.must_fail(d, "अ.मु.स. (वित्त) <=> Finance")

    def test_banned_word(self):
        d = self.case("banned")
        build_note(self.spec_with(lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " असे दिसून येते.")), d)
        self.must_fail(d, "banned words")

    def test_repo_path_in_related(self):
        d = self.case("repo")
        build_note(self.spec_with(lambda s: s["related"][0].__setitem__("source", "register/PAY-01")), d)
        self.must_fail(d, "repo paths")

    def test_package_pdf_in_letter(self):
        d = self.case("pkgletter")
        build_note(self.spec_with(lambda s: s["letter"].__setitem__("intro", s["letter"]["intro"] + " (पॅकेज PDF पृ. 3)")), d)
        self.must_fail(d, "no 'पॅकेज' in Note_and_Letter")

    # ---- C27 (02.11.2026): no package / warning / AI word in the drafts; related "(पृ.N/प.वि.)"; blank metadata ----
    def test_package_marker_in_related_source(self):
        d = self.case("pkgrel")
        build_note(self.spec_with(lambda s: s["related"][0].__setitem__("source", "परि. 2 (पॅकेज PDF पृ. 3)")), d)
        self.must_fail(d, "no 'पॅकेज' in Note_and_Letter")
        self.must_fail(d, "संबंधित माहिती source ends with (पृ.N/प.वि.)")

    def test_related_source_marker_not_at_end(self):
        d = self.case("relmark")
        build_note(self.spec_with(lambda s: s["related"][0].__setitem__("source", "(पृ.6/प.वि.) परि. 2")), d)
        self.must_fail(d, "संबंधित माहिती source ends with (पृ.N/प.वि.)")

    def test_related_source_page_outside_package(self):
        d = self.case("relp99")
        build_note(self.spec_with(lambda s: s["related"][0].__setitem__("source", "परि. 2 (पृ.25/प.वि.)")), d)
        self.must_fail(d, "page 25 outside package")

    def test_draft_words_note_letter_related(self):
        for i, (w, where) in enumerate((("अस्पष्ट", "note"), ("इशारा", "letter"), ("Claude", "heading"),
                                        ("मॉडेल", "source"), ("TODO", "note"), ("स्वयंचलित", "letter"))):
            with self.subTest(word=w, where=where):
                d = self.case(f"dw{i}")
                def f(s, w=w, where=where):
                    if where == "note": s["note"]["paras"][0] += f" {w}"
                    elif where == "letter": s["letter"]["subject"] += f" {w}"
                    elif where == "heading": s["related"][0]["heading"] += f" {w}"
                    else: s["related"][0]["source"] = f"{w} " + s["related"][0]["source"]
                build_note(self.spec_with(f), d)
                self.must_fail(d, "no warning / working / AI words")

    def test_source_line_printed_without_srot(self):
        """Abhi 03.11.2026: the related source prints as "(…, पृ.N/प.वि.)" — no word "स्रोत"; verify still finds it."""
        d = self.case("srcplain")
        build_note(self.spec_with(lambda s: s["related"][0].__setitem__("source", "परि. 2 (पृ.25/प.वि.)")), d)
        x = docx.Document(os.path.join(d, f"{PRE}_Note_and_Letter.docx"))
        txt = [p.text.strip() for p in x.paragraphs]
        self.assertIn("(परि. 2, पृ.25/प.वि.)", txt)
        self.assertFalse([t for t in txt if "स्रोत" in t])
        self.must_fail(d, "page 25 outside package")

    def test_srot_and_jasachya_tasa_in_heading_source_fail(self):
        for i, (w, where) in enumerate((("स्रोत", "heading"), ("जसाच्या तसा", "source"), ("जसेच्या तसे", "note"),
                                        ("जशीच्या तशी", "letter"))):
            with self.subTest(word=w, where=where):
                d = self.case(f"srot{i}")
                def f(s, w=w, where=where):
                    if where == "note": s["note"]["paras"][0] += f" {w}"
                    elif where == "letter": s["letter"]["subject"] += f" {w}"
                    elif where == "heading": s["related"][0]["heading"] += f" {w}"
                    else: s["related"][0]["source"] = f"{w} " + s["related"][0]["source"]
                build_note(self.spec_with(f), d)
                self.must_fail(d, "no warning / working / AI words")
        d = self.case("srotok")   # verbatim extract text is exempt
        build_note(self.spec_with(lambda s: s["related"][0]["text"].append("उतारा जसाच्या तसा स्रोत")), d)
        rc, out = self.run_verify(d)
        self.assertIn("OK: no warning / working / AI words", out)

    def test_draft_words_in_extract_or_quote_ok(self):
        d = self.case("dwok")
        def f(s):
            s["related"][0]["text"].append("उतारा: अस्पष्ट मॉडेल इशारा")
            s["note"]["paras"][0] += " “वाचन अपूर्ण”"
        build_note(self.spec_with(f), d)
        rc, out = self.run_verify(d)
        self.assertIn("OK: no warning / working / AI words", out)

    def test_docx_metadata(self):
        d = self.case("meta")
        p = os.path.join(d, f"{PRE}_Note_and_Letter.docx")
        x = docx.Document(p); x.core_properties.author = "Claude"; x.save(p)
        self.must_fail(d, "Note_and_Letter metadata (no tool / AI trace)")
        p = os.path.join(d, f"{PRE}_Study.docx")
        x = docx.Document(p); x.core_properties.comments = "generated by python-docx"; x.save(p)
        self.must_fail(d, "Study metadata (no tool / AI trace)")

    def test_pdf_metadata(self):
        d = self.case("pdfmeta")
        p = os.path.join(d, PKGNAME)
        x = m.open(p); x.set_metadata({"producer": "PyMuPDF", "author": "AI"})
        pg = x[NPP]; a = next(pg.annots()); a.set_info(title="Claude"); a.update()
        x.save(p + ".t"); x.close(); os.replace(p + ".t", p)
        self.must_fail(d, "package PDF metadata (no tool / AI trace)")

    def test_extras_draft_words(self):
        d = self.case("x_words")
        make_extra(os.path.join(d, f"{PRE}_Order_Draft.docx"), ["शासन निर्णय (पॅकेज PDF पृ. 3)"])
        make_extra(os.path.join(d, f"{PRE}_Parawise.docx"), ["Para 1: TODO check the warning."])
        self.must_fail(d, "Order_Draft no package / warning / AI words")
        self.must_fail(d, "Parawise no package / warning / AI words")

    def test_431_missing_remark_outside_the_para(self):
        # §4.31 (Abhi 03.11.2026): a facts-table cell / another para with a missing-info remark fails (SOFT)
        d = self.case("miss431")
        def f(s):
            s["note"]["paras"][2]["table"][7][2] = "प्रस्तावात नमूद नाही"
            s["note"]["paras"][0] += " अर्जाची प्रत प्रस्तावासोबत नाही."
        build_note(self.spec_with(f), d)
        self.must_fail(d, "missing information in ONE para §4.31")
        import engine_supabase as E
        hard, soft = E.classify_verify(["FAIL: missing information in ONE para §4.31 (note body) — x"])
        self.assertEqual(hard, [])

    def test_431_two_missing_paras(self):
        d = self.case("two431")
        build_note(self.spec_with(lambda s: s["note"]["paras"].insert(1, "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:- (1) दिनांक.")), d)
        self.must_fail(d, "more than one")

    def test_c27_checks_are_soft(self):
        import engine_supabase as E
        lines = ["FAIL: no 'पॅकेज' in Note_and_Letter — x", "FAIL: no warning / working / AI words (note, …) — x",
                 "FAIL: संबंधित माहिती source ends with (पृ.N/प.वि.) or no page marker — x",
                 "FAIL: Note_and_Letter metadata (no tool / AI trace) — x", "FAIL: Study metadata (no tool / AI trace) — x",
                 "FAIL: package PDF metadata (no tool / AI trace) — x", "FAIL: Order_Draft no package / warning / AI words — x",
                 "FAIL: Parawise metadata (no tool / AI trace) — x"]
        hard, soft = E.classify_verify(lines)
        self.assertEqual(hard, [])
        self.assertEqual(len(soft), len(lines))

    def test_unstamped_page(self):
        d = self.case("stamp")
        build_pkg(os.path.join(d, PKGNAME), skip_stamp_on=5)
        self.must_fail(d, "page stamps")

    def test_separator_page(self):
        d = self.case("sep")
        build_pkg(os.path.join(d, PKGNAME), extra_page=True)
        self.must_fail(d, "separator")

    def test_generated_package_name(self):
        d = self.case("name")
        bad = f"{PRE}_Proposal_with_GRs.pdf"
        os.rename(os.path.join(d, PKGNAME), os.path.join(d, bad))
        os.rename(os.path.join(d, PKGNAME + ".map.json"), os.path.join(d, bad + ".map.json"))
        self.must_fail(d, "package file name", pkg=bad)

    def rename_pkg(self, d, new):
        os.rename(os.path.join(d, PKGNAME), os.path.join(d, new))
        os.rename(os.path.join(d, PKGNAME + ".map.json"), os.path.join(d, new + ".map.json"))

    def test_original_name_machine_like_ok(self):
        # §4.16: the uploaded proposal itself was named CR66_Proposal_with_GRs.pdf -> keep it, no FAIL
        d = self.case("orig_ok")
        self.rename_pkg(d, "CR66_Proposal_with_GRs.pdf")
        rc, out = self.run_verify(d, pkg="CR66_Proposal_with_GRs.pdf",
                                  extra=("--original-name", "11ae057d-CR66_Proposal_with_GRs.pdf"))
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)

    def test_original_name_mismatch(self):
        d = self.case("orig_bad")
        self.rename_pkg(d, "renamed.pdf")
        self.must_fail(d, "package file name", pkg="renamed.pdf", extra=("--original-name", "CR66_Proposal_with_GRs.pdf"))

    def test_original_name_date_prefix_kept(self):
        # a real name starting with an 8-digit date is not an upload prefix (only 8 hex chars with a letter a-f are)
        d = self.case("orig_date")
        self.rename_pkg(d, "20261101-CR130.pdf")
        rc, out = self.run_verify(d, pkg="20261101-CR130.pdf", extra=("--original-name", "20261101-CR130.pdf"))
        self.assertEqual(rc, 0, out)
        d = self.case("orig_date_bad")
        self.rename_pkg(d, "CR130.pdf")
        self.must_fail(d, "package file name", pkg="CR130.pdf", extra=("--original-name", "20261101-CR130.pdf"))

    def test_original_name_too_long_short_form_ok(self):
        # NAME_MAX (255 bytes; Devanagari 3 bytes a char): the package carries engine_supabase.fs_name of the original name
        sys.path.insert(0, TOOLS)
        from engine_supabase import fs_name, strip_upload_prefix
        full = "11ae057d-" + "132 2026 मा. शेट्टी आयोगाच्या शिफारशीनुसार दि. 01.04.2026 रोजी कनिष्ठ आणि वरिष्ठ सहायक अधिक्षकांचे वेतन एकवटत असल्यामुळे त्यांच्या वेतननिश्चिती संदर्भात मार्गदर्शन मिळणेबाबत._0001.pdf"
        self.assertGreater(len(full.encode("utf-8")), 255)
        short = fs_name(strip_upload_prefix(full))
        self.assertLessEqual(len(short.encode("utf-8")), 200)
        d = self.case("orig_long")
        self.rename_pkg(d, short)
        for name in (full, strip_upload_prefix(full)):
            rc, out = self.run_verify(d, pkg=short, extra=("--original-name", name))
            self.assertEqual(rc, 0, out)
            self.assertIn("ALL OK", out)
        d = self.case("orig_long_bad")
        self.rename_pkg(d, "x" + short)
        self.must_fail(d, "package file name", pkg="x" + short, extra=("--original-name", full))

    def write_status(self, d, **st):
        with open(os.path.join(d, "status.json"), "w", encoding="utf-8") as f:
            json.dump({"state": "done", **st}, f, ensure_ascii=False)

    def test_letter_needed_agrees(self):
        d = self.case("ln_ok")
        self.write_status(d, letter_needed=True)
        rc, out = self.run_verify(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("OK: status.json letter_needed", out)

    def test_letter_needed_false_but_letter(self):
        d = self.case("ln_false")
        self.write_status(d, letter_needed=False)
        self.must_fail(d, "letter_needed false but the Note_and_Letter has a letter")

    def test_letter_needed_missing(self):
        d = self.case("ln_missing")
        self.write_status(d)
        self.must_fail(d, "letter_needed not true/false")

    def test_letter_needed_true_but_no_letter(self):
        d = self.case("ln_noletter")
        build_note(self.spec_with(lambda s: s.pop("letter")), d)
        self.write_status(d, letter_needed=True)
        self.must_fail(d, "letter_needed true but the Note_and_Letter has no letter")

    def test_mark_not_found(self):
        d = self.case("mark")
        build_pkg(os.path.join(d, PKGNAME), mark_status={"label": "GR", "pdf_page": 17, "status": "TEXT NOT FOUND (scanned?) - give box"})
        self.must_fail(d, "mark not placed")

    def test_annotation_on_proposal(self):
        d = self.case("annot")
        build_pkg(os.path.join(d, PKGNAME), annot_on_proposal=True)
        self.must_fail(d, "annotations")

    def test_annotation_on_proposal_check_name(self):
        # the engine treats "annotations on proposal pages" as HARD, the Highlight-type rule as soft: separate checks
        d = self.case("annot2")
        build_pkg(os.path.join(d, PKGNAME), annot_on_proposal=True)
        self.must_fail(d, "annotations on proposal pages (none)")
        rc, out = self.run_verify(d)
        self.assertIn("OK: annotations (Highlight only)", out)

    def test_reply_parts_after_proposal(self):
        # A1 H9: reply pages appended right after the proposal (map "proposal_parts") — proposal count still = NPP,
        # and a count that includes them is accepted too; an annotation on a reply page is a proposal-side annotation
        d = self.case("reply")
        pkg = os.path.join(d, PKGNAME)
        build_pkg(pkg)
        mp = json.load(open(pkg + ".map.json", encoding="utf-8"))
        mp["प्रस्ताव"]["pages"] = list(range(1, NPP))
        mp["उत्तर-पत्र"] = {"first_page": NPP, "pages": [NPP], "kind": "reply"}
        mp["proposal_parts"] = ["उत्तर-पत्र"]
        json.dump(mp, open(pkg + ".map.json", "w", encoding="utf-8"), ensure_ascii=False)
        rc, out = self.run_verify(d, npp=NPP)
        self.assertEqual(rc, 0, out)
        rc, out = self.run_verify(d, npp=NPP - 1)
        self.assertEqual(rc, 0, out)

    def test_uuid_original_name_kept(self):
        d = self.case("uuid")
        u = "3f2a9c1e-5b7d-4e2a-9c1e-1234567890ab.pdf"
        os.rename(os.path.join(d, PKGNAME), os.path.join(d, u)); os.rename(os.path.join(d, PKGNAME + ".map.json"), os.path.join(d, u + ".map.json"))
        rc, out = self.run_verify(d, pkg=u, extra=("--original-name", u))
        self.assertEqual(rc, 0, out)

    def test_wrong_font_attribute(self):
        d = self.case("font")
        f = os.path.join(d, f"{PRE}_Note_and_Letter.docx")
        doc = docx.Document(f)
        run = next(r for r in doc.element.body.iter(qn("w:r")) if "".join(t.text or "" for t in r.iter(qn("w:t"))).strip())
        rf = run.find(qn("w:rPr")).find(qn("w:rFonts"))
        rf.set(qn("w:eastAsia"), "Mangal"); doc.save(f)
        self.must_fail(d, "Note_and_Letter fonts")

    def test_missing_part0(self):
        d = self.case("part0")
        st = study_spec(self.spec); st["parts"].pop(0)
        build_study(st, d)
        self.must_fail(d, "heading भाग 0 missing")

    # ---- §4.18 wording (note body + letter, outside “…” quotes) ----
    def intro_with(self, old, new):
        def f(s):
            assert old in s["letter"]["intro"]
            s["letter"]["intro"] = s["letter"]["intro"].replace(old, new)
        return self.spec_with(f)

    def test_sau_in_note(self):
        d = self.case("sau")
        build_note(self.spec_with(lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " सौ. ____ यांनी अर्ज केला.")), d)
        self.must_fail(d, "respectful wording §4.18")

    def test_unspaced_shri_in_letter(self):
        d = self.case("shri")
        build_note(self.intro_with("श्री. आर. एन.", "श्री.आर.एन."), d)
        self.must_fail(d, "letter: आदरार्थी उल्लेख")

    def test_tatkal_in_letter(self):
        d = self.case("tatkal")
        build_note(self.intro_with("सदर प्रकरणी", "सदर प्रकरणी तात्काळ"), d)
        self.must_fail(d, "letter: पत्राची भाषा")

    def test_intro_without_request(self):
        d = self.case("vinanti")
        build_note(self.intro_with(", ही विनंती", ""), d)
        self.must_fail(d, "letter intro request wording")

    def test_reply_letter_without_request_ok(self):
        # a conveying letter (no points, intro does not ask) needs no "ही विनंती" (lint_spec.requests_info)
        d = self.case("conv")
        def f(s):
            s["letter"]["points"] = []
            s["letter"]["intro"] = ("उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, "
                                    "सदर प्रकरणी वित्त विभागाचा अभिप्राय प्राप्त झाला आहे.")
        build_note(self.spec_with(f), d)
        rc, out = self.run_verify(d)
        self.assertIn("OK: letter intro request wording", out)

    def test_ma_not_checked_in_refs_and_copies(self):
        # §4.23: the letter's to / refs / copies are exempt (same as lint_spec); the body is checked
        d = self.case("ma_refs")
        def f(s):
            s["letter"]["refs"] = [s["letter"]["refs"][0] + " (प्रबंधक (अपील शाखा), उच्च न्यायालय, मुंबई)"]
        build_note(self.spec_with(f), d)
        rc, out = self.run_verify(d)
        self.assertIn('OK: "मा." before the High Court', out)
        d2 = self.case("ma_body")
        build_note(self.intro_with("सदर प्रकरणी", "उच्च न्यायालयाच्या पत्रानुसार सदर प्रकरणी"), d2)
        self.must_fail(d2, '"मा." before the High Court')

    def test_finance_closing_line_joined(self):
        # a separate closing "मान्यतेस्तव सादर." (note.closing) joins the last para, as in lint_spec (finance_route)
        sp = json.load(open(os.path.join(ROOT, "samples", "specs", "CR66_2026_finance-approval_no-letter.json"), encoding="utf-8"))
        sp["note"]["paras"][-1] = "सबब, उपरोक्त प्रस्तावास मान्यता मिळण्याबाबत सार्वजनिक आरोग्य विभागास विनंती करण्यास हरकत नसावी."
        sp["note"]["closing"] = "मान्यतेस्तव सादर."
        d = self.case("fin_closing")
        build_note(sp, d)
        rc, out = self.run_verify(d)
        self.assertIn("OK: अ.मु.स. (वित्त) <=> Finance last para", out)

    def test_quoted_sau_tatkal_ok(self):
        d = self.case("quoted")
        s = self.intro_with("सदर प्रकरणी", "सदर प्रकरणी “तात्काळ”")
        s["note"]["paras"][0] += " “सौ. ____ यांनी अर्ज केला.”"
        build_note(s, d)
        rc, out = self.run_verify(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)


    # ---- §4.19 Marathi forms (01.11.2026) ----
    def test_419_colon_dash_in_letter(self):
        d = self.case("colon419")
        build_note(self.intro_with("ही विनंती:-", "ही विनंती.:-"), d)
        self.must_fail(d, "official Marathi §4.19")

    def test_419_karun_in_letter(self):
        d = self.case("karun419")
        build_note(self.intro_with("करून", "करुन"), d)
        self.must_fail(d, "letter: शुद्धलेखन")

    def test_419_unspaced_date_in_note(self):
        d = self.case("date419")
        build_note(self.spec_with(lambda s: s["note"].__setitem__("first", s["note"]["first"].replace("दि. 17.09.2026", "दि.17.09.2026"))), d)
        self.must_fail(d, "note: संक्षेपचिन्हानंतर एक जागा")

    def test_419_quoted_ok(self):
        d = self.case("quoted419")
        s = self.spec_with(lambda s: s["note"]["paras"].__setitem__(0, s["note"]["paras"][0] + " “दि.17.09.2026 रोजी सादर करुन.:-”"))
        build_note(s, d)
        rc, out = self.run_verify(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)

    # ---- 02.11.2026: "अनुसरुन" error; WARN level never FAIL ----
    def test_anusarun_in_note_fails(self):
        d = self.case("anus_note")
        build_note(self.spec_with(lambda s: s["note"].__setitem__("first", s["note"]["first"].replace("अनुसरून", "अनुसरुन"))), d)
        self.must_fail(d, "note: शुद्धलेखन — 'अनुसरुन'")

    def test_anusarun_in_letter_fails(self):
        d = self.case("anus_letter")
        build_note(self.intro_with("अनुसरून", "अनुसरुन"), d)
        self.must_fail(d, "letter: शुद्धलेखन — 'अनुसरुन'")

    def test_warn_not_fail(self):
        d = self.case("warn")
        s = self.intro_with("सदर प्रकरणी", "सदर प्रकरणी आपणास")
        s["note"]["paras"][0] += " अर्ज करणेसाठी त्याने सादर केला. “देणेबाबत तिने”"
        s["letter"]["subject"] = s["letter"]["subject"].rstrip(".") + " मिळणेबाबत."
        build_note(s, d)
        rc, out = self.run_verify(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)
        self.assertNotIn("FAIL:", out)
        warns = [ln for ln in out.splitlines() if ln.startswith("WARN:")]
        for needle in ("note: शुद्धलेखन नियम 12 — 'करणेसाठी'", "note: शुद्धलेखन नियम 3 (आदरार्थी) — अधिकारी/व्यक्तीसाठी 'त्याने'",
                       "letter: शुद्धलेखन नियम 1–4 (अनुस्वार, आदरार्थी) — 'आपणास'", "letter: शुद्धलेखन नियम 12 — 'मिळणेबाबत'"):
            self.assertTrue(any(needle in w for w in warns), f"{needle}:\n{out}")
        self.assertFalse(any("देणेबाबत" in w or "'तिने'" in w for w in warns), out)   # quoted text exempt

    def test_good_has_no_warn(self):
        rc, out = self.run_verify(self.good)
        # C32 §4.34: CR122's related precedent extract is itself quoted with "..." (quote content never altered, §1.1)
        self.assertEqual([ln for ln in out.splitlines() if ln.startswith("WARN:") and "shortened quote" not in ln], [], out)

    def test_432_flow_warn_not_fail(self):
        # C32 §4.34 (Abhi 03.11.2026): relevance + एकसंध flow findings are SOFT notes (WARN), never a FAIL
        d = self.case("flow432")
        def f(s):
            t = s["note"]["paras"][2]["table"]; t[0].append("पृ./प.वि."); [r.append("12") for r in t[1:]]
            s["note"]["paras"][0] += " सदर पत्राची प्रत माहितीकरिता देण्यात आली आहे."
            s["note"]["paras"].insert(5, "अर्जात “वेतननिश्चिती” व “विकल्प … स्वीकारावा” असे नमूद आहे.")
            s["note"]["paras"].insert(6, "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-")
            s["note"]["sub"] = {"6": ["(1) पदोन्नती दि. 30.01.2010 रोजी झाली आहे (पृ.7/प.वि.).", "(2) विकल्प अर्ज दि. 24.01.2025 रोजी सादर झाला आहे."]}
        build_note(self.spec_with(f), d)
        rc, out = self.run_verify(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL OK", out)
        self.assertNotIn("FAIL:", out)
        warns = [ln for ln in out.splitlines() if ln.startswith("WARN:") and "(§4.34)" in ln]
        for needle in ("(table): table column 'पृ./प.वि.'", "forwarding detail 'माहितीकरिता देण्यात'", "quote-gluing",
                       "shortened quote", "'उपरोक्त वस्तुस्थिती' item carries a पृ./प.वि. reference"):
            self.assertTrue(any(needle in w for w in warns), f"{needle}:\n{out}")
        self.assertEqual(sum("'उपरोक्त वस्तुस्थिती' item" in w for w in warns), 1, out)   # only item (1)

    # ---- optional outputs (02.11.2026): <PREFIX>_Order_Draft.docx / <PREFIX>_Parawise.docx ----
    def test_extras_absent_no_lines(self):
        rc, out = self.run_verify(self.good)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Order_Draft", out); self.assertNotIn("Parawise", out)

    def test_extras_good(self):
        d = self.case("x_good")
        make_extra(os.path.join(d, f"{PRE}_Order_Draft.docx"), ["शासन निर्णय", "वाचा :- (पृ.17/प.वि.)"], header="क्रमांक ____")
        make_extra(os.path.join(d, f"{PRE}_Parawise.docx"), ["Para 1: The averments are factually correct (पृ.3/प.वि.)."])
        rc, out = self.run_verify(d)
        self.assertEqual(rc, 0, out)
        for ln in ("OK: Order_Draft fonts", "OK: Order_Draft internal ids", "OK: Order_Draft repo paths",
                   "OK: Order_Draft पृ. references", "OK: Parawise fonts", "OK: Parawise पृ. references"):
            self.assertIn(ln, out)

    def test_extras_font(self):
        d = self.case("x_font")
        make_extra(os.path.join(d, f"{PRE}_Parawise.docx"), ["Para 1"], font=False)
        self.must_fail(d, "Parawise fonts")

    def test_extras_header_font(self):
        d = self.case("x_hfont")
        make_extra(os.path.join(d, f"{PRE}_Order_Draft.docx"), ["शासन निर्णय"], header="क्रमांक", header_font=False)
        self.must_fail(d, "Order_Draft fonts")

    def test_extras_id_path_ref(self):
        d = self.case("x_bad")
        make_extra(os.path.join(d, f"{PRE}_Order_Draft.docx"), ["स्रोत z6_0235", "register/PAY-01", "(पृ.99/प.वि.)"])
        self.must_fail(d, "Order_Draft internal ids")
        self.must_fail(d, "Order_Draft repo paths")
        self.must_fail(d, "Order_Draft पृ. references")


def make_extra(path, paras, font=True, header=None, header_font=True):
    """A small Word file like build_order / build_parawise output: every run with DVOT-SurekhMR on all four rFonts."""
    def setf(run, ok):
        rpr = run._element.get_or_add_rPr()
        fo = rpr.find(qn("w:rFonts"))
        if fo is None:
            fo = rpr.makeelement(qn("w:rFonts"), {}); rpr.append(fo)
        for a in ("ascii", "hAnsi", "cs", "eastAsia"):
            fo.set(qn("w:" + a), "DVOT-SurekhMR" if ok else "Calibri")
    d = docx.Document()
    for t in paras:
        setf(d.add_paragraph().add_run(t), font)
    if header:
        hp = d.sections[0].header.paragraphs[0]
        setf(hp.add_run(header), header_font)
    d.save(path)
    import clean_meta
    clean_meta.clean_docx(path)   # as the builders do (C27 §4)


if __name__ == "__main__":
    unittest.main()
