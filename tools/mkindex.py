#!/usr/bin/env python3
"""mkindex.py — lib2/idx/*.json मधून 00-INDEX.docx (फॉन्ट DVOT-SurekhMR) बनवते."""
import json, glob, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import libdoc

B = os.environ.get("LIB2", "lib2")
idx = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(B + "/idx/*.json"))]

secs = []
secs.append({"h": "वापरण्याची पद्धत", "level": 1, "paras": [
    "नवीन प्रस्ताव आल्यावर: (१) खालील 'विषय-सूची' मधून विषय निवडा; (२) त्या विषयाचे Word संग्रह उघडा; (३) त्यातील 'इतर विभागांचे अभिप्राय' व 'मार्गदर्शक GR' पाहून पूर्वीचा अभिप्राय/संदर्भ तपासा; (४) 'प्रमाणित मसुदा-परिच्छेद' टिप्पणी/पत्रात वापरा.",
    "या संग्रहात फक्त नस्तीतील नोंदी जसेच्या तसे आहेत; व्यक्तींची नावे व आजाराचे निदान वगळले आहे. पुन्हा अभिप्राय घ्यावा/न घ्यावा याचा निर्णय संग्रहात दिलेला नाही."]})

secs.append({"h": "१. विषय-सूची", "level": 1, "table": {
    "cols": ["अ.क्र.", "फोल्डर", "संग्रह (Word)", "प्रकरणे", "अभिप्राय", "GR/नियम"],
    "rows": [[i + 1, d.get("folder", ""), d.get("doc", ""), len(d.get("cases", [])), len(d.get("opinions", [])), len(d.get("grs", []))] for i, d in enumerate(idx)],
    "widths_cm": [1.2, 4.5, 5.3, 1.8, 1.8, 2.0]}})

rows = []
for d in idx:
    for c in d.get("cases", []):
        rows.append([c.get("case_no", ""), c.get("cid", ""), c.get("subject", ""), d.get("folder", ""), d.get("code", "")])
rows.sort(key=lambda r: r[1])
secs.append({"h": "२. प्रकरण → विषय नकाशा", "level": 1, "pagebreak": True, "table": {
    "cols": ["प्रकरण क्र.", "id", "विषय", "फोल्डर", "संग्रह"], "rows": rows, "widths_cm": [2.6, 1.6, 7.2, 4.0, 1.4]}})

orows = []
for d in idx:
    for o in d.get("opinions", []):
        orows.append([o.get("dept", ""), o.get("ref", ""), o.get("date", ""), o.get("subject", ""), o.get("case_no", ""), d.get("code", "") + " / " + str(o.get("section", ""))])
orows.sort(key=lambda r: (r[0], r[2]))
secs.append({"h": "३. इतर विभागांचे अभिप्राय — सूची", "level": 1, "pagebreak": True, "table": {
    "cols": ["विभाग", "संदर्भ क्र.", "दिनांक", "विषय", "प्रकरण", "संग्रह/विभाग"], "rows": orows, "widths_cm": [2.4, 3.2, 2.0, 5.0, 2.2, 2.2]}})

grows, seen = [], set()
for d in idx:
    for g in d.get("grs", []):
        k = (g.get("ref", ""), g.get("date", ""))
        if k in seen: continue
        seen.add(k); grows.append([g.get("ref", ""), g.get("date", ""), g.get("subject", ""), d.get("code", "")])
secs.append({"h": "४. मार्गदर्शक GR / नियम / न्यायनिर्णय — सूची", "level": 1, "pagebreak": True, "table": {
    "cols": ["क्रमांक", "दिनांक", "विषय", "संग्रह"], "rows": grows, "widths_cm": [4.5, 2.3, 8.0, 2.2]}})

for d in idx:
    st = d.get("subtopics", [])
    if st:
        secs.append({"h": f"५. उप-विषय — {d.get('code','')} {d.get('folder','')}", "level": 2,
                     "bullets": [f"{s['name']}: " + ", ".join(s.get("cases", [])) for s in st]})

libdoc.build({"title": "विषयनिहाय पूर्वोदाहरण-ग्रंथालय — मुख्य इंडेक्स",
              "subtitle": "विधि व न्याय विभाग, कार्यासन-६ — गोपनीय (अंतर्गत वापरासाठी)", "sections": secs},
             B + "/docs/00-INDEX.docx")
print("ok", len(idx), "groups", len(rows), "cases")
