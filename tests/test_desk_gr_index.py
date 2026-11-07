"""tools/desk_gr_index.py — JSON index of pdf/ for the read-only "GR ग्रंथालय" tab."""
import hashlib, json, os, subprocess, sys

import pymupdf
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "desk_gr_index.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import desk_gr_index as g  # noqa: E402

CODE = "202204191549468012"
FONT = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"


def mkpdf(path, text="", pages=1):
    d = pymupdf.open()
    for i in range(pages):
        p = d.new_page()
        if i == 0 and text:
            if os.path.isfile(FONT):
                p.insert_font(fontname="fs", fontfile=FONT)
                p.insert_text((50, 72), text, fontname="fs", fontsize=11)
            else:
                p.insert_text((50, 72), text)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d.save(path)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path
    mkpdf(r / "pdf" / "gr" / f"{CODE}.pdf", pages=2)
    mkpdf(r / "pdf" / "06-dcps-nps" / "201805171732241512.pdf", "विषय :- न्यायिक अधिकाऱ्यांच्या वेतनातून कपात थांबविण्याबाबत. संदर्भ :- 1) x")
    mkpdf(r / "pdf" / "06-dcps-nps" / "rules.pdf", pages=3)
    mkpdf(r / "pdf" / "06-dcps-nps" / "vjti.pdf")
    mkpdf(r / "pdf" / "sc" / "SC_WPC_643_2015_AIJA_order_27-03-2018.pdf")
    (r / "pdf" / "06-dcps-nps" / "notes.md").write_text("x", encoding="utf-8")
    (r / "pdf" / "06-dcps-nps" / "broken.pdf").write_bytes(b"not a pdf")
    (r / "service-rules").mkdir()
    (r / "service-rules" / "06-dcps-nps.md").write_text("intro\n# DCPS / NPS rules\n## sub\n", encoding="utf-8")
    (r / "pdf" / "gr" / "INDEX.tsv").write_text(
        "code\tdate\tdepartment\ttitle\trequest\n"
        f"{CODE}\t2022-04-19\tL&J\tUpgradation of Pay Scales of Group A\tx\n", encoding="utf-8")
    (r / "pdf-list.tsv").write_text(
        "06-dcps-nps\thttps://cdnbbsr.s3waas.gov.in/a/rules.pdf\trules.pdf\n"
        "sc\thttps://archive.org/download/x/SC_WPC_643_2015_AIJA_order_27-03-2018.pdf\tSC_WPC_643_2015_AIJA_order_27-03-2018.pdf\n",
        encoding="utf-8")
    (r / "pdf-list-extra.tsv").write_text(
        "06-dcps-nps\thttps://vjti.ac.in/wp-content/uploads/vjti.pdf\tvjti.pdf\n", encoding="utf-8")
    return r


def test_parse_code_and_date():
    assert g.parse_code(f"{CODE}.pdf") == (CODE, "19.04.2022")
    assert g.parse_code("20091218144749001.pdf") == ("20091218144749001", "18.12.2009")   # 17 digits
    assert g.parse_code("202213451549468012.pdf") == ("202213451549468012", "")          # month 13 -> no date
    assert g.parse_code("SC_WPC_643_2015.pdf") == ("", "")
    assert g.parse_code("2023041797.pdf") == ("", "")                                    # too short
    assert g.parse_code("1005033517124335dd63750c7312b397.pdf") == ("", "")              # hex hash, not a code
    assert g.parse_code("agri_202308011629399301.pdf") == ("", "")                       # code not at the start


def test_garbage_title_rejected():
    assert g.is_readable("दि. 01.11.2005 पूर्वी जाहिरात निर्गमित झालेल्या प्रकरणी")
    assert g.is_readable("Upgradation of Pay Scales of Group A")
    assert not g.is_readable("Œ¸ü¿ÖÖ¸üß ¼ÖÖ¸üŸÖß ¯Ö¤")       # legacy-font garbage
    assert not g.is_readable("ˆÖ¾Ö¤ü ¿ÖÖÃÖ­Ö †ÖÆêü")
    assert not g.is_readable("12.05.2019 / 45")
    assert g.subject_from_text("शासन निर्णय\nविषय :- Œ¸ü¿ÖÖ¸üß ¼ÖÖ¸üŸÖß ¯Ö¤ü\n") == ""
    assert g.subject_from_text("वित्त विषयक कामकाज करण्याकरिता") == ""   # विषयक is not the label
    assert g.subject_from_text("विषय :- वेतनवाढ मंजूर   करण्याबाबत.\nसंदर्भ :- 1) शासन निर्णय") == "वेतनवाढ मंजूर करण्याबाबत"


def test_third_party_url_rejected():
    assert g.official_url("https://cdnbbsr.s3waas.gov.in/a.pdf")
    assert g.official_url("https://www.indiacode.nic.in/a.pdf")
    assert g.official_url("https://gr.maharashtra.gov.in/a.pdf")
    for u in ("https://archive.org/download/x/y.pdf", "https://vjti.ac.in/a.pdf", "https://www.livelaw.in/a.pdf",
              "https://gov.in.example.com/a.pdf", "https://www.midcindia.org/a.pdf"):
        assert g.official_url(u) == "", u


def test_build_on_fixture_repo(repo, tmp_path):
    out = tmp_path / "idx.json"
    r = subprocess.run([sys.executable, TOOL, str(out), "--root", str(repo)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "total 6 | with code 2 |" in r.stdout and "with url 3" in r.stdout
    rows = json.load(open(out, encoding="utf-8"))
    by = {x["file"]: x for x in rows}
    assert "notes.md" not in by and len(rows) == 6
    assert [x["folder"] for x in rows] == sorted(x["folder"] for x in rows)
    gr = by[f"{CODE}.pdf"]
    assert gr["key"] == hashlib.sha1(f"pdf/gr/{CODE}.pdf".encode()).hexdigest()[:16]
    assert gr["path"] == f"pdf/gr/{CODE}.pdf" and gr["folder"] == "gr" and gr["topic"] == "gr"
    assert gr["code"] == CODE and gr["date"] == "19.04.2022" and gr["pages"] == 2
    assert gr["title"] == "Upgradation of Pay Scales of Group A"                       # from INDEX.tsv
    assert gr["url"] == f"https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{CODE}.pdf"
    dc = by["201805171732241512.pdf"]
    assert dc["topic"] == "DCPS / NPS rules" and dc["date"] == "17.05.2018"
    if os.path.isfile(FONT):
        assert dc["title"] == "न्यायिक अधिकाऱ्यांच्या वेतनातून कपात थांबविण्याबाबत"     # from the first page
    assert by["rules.pdf"]["url"] == "https://cdnbbsr.s3waas.gov.in/a/rules.pdf" and by["rules.pdf"]["pages"] == 3
    assert by["vjti.pdf"]["url"] == ""                                                 # third-party host
    sc = by["SC_WPC_643_2015_AIJA_order_27-03-2018.pdf"]
    assert sc["code"] == "" and sc["url"] == "" and sc["title"] == ""                  # archive.org dropped
    assert by["broken.pdf"]["pages"] == 0 and by["broken.pdf"]["size"] == 9
    dcps = [x["file"] for x in rows if x["folder"] == "06-dcps-nps"]
    assert dcps[0] == "201805171732241512.pdf" and dcps[1:] == ["broken.pdf", "rules.pdf", "vjti.pdf"]   # date desc, then file
