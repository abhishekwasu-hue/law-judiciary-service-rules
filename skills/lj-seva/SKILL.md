---
name: "lj-seva"
description: "Use whenever Abhi uploads a Law & Judiciary Desk-6 service-matter proposal (सेवाविषयक प्रकरण — pay fixation, ACP, pension, NPS, GPF, medical bill, recruitment, promotion, allowances, any High Court / district court staff matter) as a PDF or asks for its Marathi noting, letter, Study file or proposal PDF with GRs. Not for court petitions (lj-nyayalayin), legislature work (lj-vidhimandal) or procurement (lj-kharedi)."
---

# विधि व न्याय विभाग, कार्यासन-6 — सेवाविषयक प्रकरणे

**हा skill फक्त कार्यपद्धत सांगतो; नोंद/पत्र/मसुद्यांचे सर्व नियम रेपोतील फाइल्समध्ये — फरक आढळल्यास रेपो जिंकतो.**
श्रेणी: `service` (`tools/work_types/service.json`, नियम-संदर्भ `tools/work_rules/service.md`). याचिका आली तर `lj-nyayalayin`, विधानमंडळ प्रश्न → `lj-vidhimandal`, खरेदी → `lj-kharedi`.

Abhi (कार्यासन अधिकारी, कार्यासन-6) PDF अपलोड करतो; सर्व पायऱ्या न विचारता शेवटपर्यंत कराव्यात. उत्तर मराठीत, थोडक्यात.

## 0. सुरुवात (प्रत्येक वेळी)
1. रेपो `abhishekwasu-hue/law-judiciary-service-rules`: सत्रात नसेल तर `add_repo` मग clone; असेल तर `git pull --rebase`.
2. **नियमांचा एकमेव स्रोत — आधी पूर्ण वाचा:** `OWNER_RULES.md`; `INSTRUCTIONS.md` §1–§3 व §4 चे **सर्व** क्रमांक (नवे जोडले जातात — शेवटपर्यंत वाचा); `PROPOSAL_SOP.md`; `PROPOSAL_WORKFLOW.md`; `HANDOVER.md`; `tools/ENGINE_BRIEF.md`; `tools/work_rules/service.md`; `samples/specs/`.
3. साधने: `pip install pymupdf docxcompose python-docx --break-system-packages`; `soffice`, `pdftoppm`, `tesseract`. `mar.traineddata` नसेल तर `https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/mar.traineddata` → `/usr/share/tesseract-ocr/5/tessdata/`. जुन्या प्रकरणांचा मजकूर: `python3 tools/oldcases_text.py /tmp/old`.
4. Task list (प्रत्येक प्रस्ताव स्वतंत्र). OCR, GR शोध, मसुदे, Study — समांतर agents (OWNER_RULES A.13); lead म्हणून प्रत्येक diff तपासा.
5. Project मधील `claude/00-STANDING-INSTRUCTIONS.md` = `INSTRUCTIONS.md` ची प्रत; फरक असल्यास रेपो जिंकतो व प्रत रेपोवरून अद्ययावत करा.

## 1. अपलोड तपासा
- प्रत्येक फाइल उघडा. `.pdf.txt` मध्ये फक्त पान-शीर्षके (स्कॅन) → मूळ PDF एका ओळीत मागा, इतर काम चालू ठेवा.
- अनेक प्रस्ताव = स्वतंत्र प्रकरणे.
- संदर्भासाठी दिलेली जुनी नस्ती पूर्ण वाचा; वित्त / विधि शाखेचे अभिप्राय, शुद्धिपत्रके तथ्य म्हणून. अभिप्रायाचा दिनांक मूळ पानावरील सही-दिनांकावरून.
- Abhi "प्रस्तावाला लावा" म्हणाल्यास ती कागदपत्रे GR सह PDF च्या शेवटी enclosure (आधीचे पृ. क्रमांक बदलू नयेत), उद्धृत भागावर पिवळा highlight, नोंद सुधारा.
- मूळ फाइलनाव ठेवा; फक्त यादृच्छिक उपसर्ग `xxxxxxxx-` काढा (§4.16).

## 2. प्रस्ताव वाचा (प्रत्येक पान)
- `pdftoppm -r 150 -gray` + `tesseract -l eng` / `-l mar+eng` (मोठी PDF — background, समांतर).
- मुख्य पाने (निर्देशपत्र, मागणी, तक्ते, शिक्के, हस्तलिखित शेरे, दिनांक, रकमा) **पान-प्रतिमा पाहून** दोनदा.
- पृष्ठ-संदर्भ = PDF पान क्रमांक (छापील / हस्तलिखित नव्हे).
- तथ्य-यादी: कोणी, कोणामार्फत, पत्रांचे दिनांक व पाने, मागणी, कर्मचारी/पद/दिनांक/रक्कम, जोडपत्रे, प्रस्तावातील या कार्यासनाची आधीची टिप्पणी/पत्र (§4.39 A4), याच विषयाची जुनी नस्ती.

## 3. तरतुदी, GR, पूर्वोदाहरणे (SOP Step 2; §4.14)
- रेपो: `register/`, `pdf/`, `pdf/gr/INDEX.tsv`, `service-rules/`, `precedent-library/` (unzip, `00-INDEX.docx`), `working-notes/CASE-REGISTER.md`, `medical-bill/` (वैद्यकीय प्रतिपूर्ती — INSTRUCTIONS §8), `सन ... प्रकरणे.zip` (याच कर्मचाऱ्याची / विषयाची नस्ती — पूर्वीचा वित्त अभिप्राय).
- GR नसेल तर स्वतः मिळवा: archive.org `advancedsearch.php?q=collection:maharashtragr+AND+date:[…]` (सांकेतांकाचे शेवटचे 2 अंक: 12 विधि व न्याय, 05 वित्त); PDF `archive.org/download/in.gov.maharashtra.gr.<code>/<code>.pdf` किंवा `gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf`; नाहीतर `tools/gr-request.txt` + `python3 tools/gr_request.py` / push. → `pdf/gr/` + `INDEX.tsv`. तरीही नाही → सांकेतांक एका ओळीत विचारा, काम चालू.
- न्यायालयीन आदेश फक्त api.sci.gov.in / bombayhighcourt.nic.in (`pdf/sc/`); तृतीय-पक्ष स्रोत नाही (§1.3).
- उतारे मूळ पान-प्रतिमा पाहून शब्दशः (legacy font चा मजकूर-स्तर बिघडलेला).

## 4. पत्र की नस्ती? कोणते मसुदे? (SOP Step 3; §4.15, §4.28, §4.33)
- अत्यावश्यक माहिती कमी असेल तरच माहिती-मागणी पत्र; पूर्ण असल्यास नस्ती वित्त / सा.प्र.वि. कडे. Abhi ने मसुदे निवडले असल्यास नेमके तेच.
- spec-key → साधन → फाइल:
  - `letter` / `letters` (पत्र, स्मरणपत्र, `"kind": "do"`), `note.uo` → `tools/build_note_letter.py` → `<PREFIX>_Note_and_Letter.docx`
  - `order` / `orders` (gr, corrigendum, circular, memo, notification, endorsement, office_order, press_note, addendum) → `tools/build_order.py` → `_Order_Draft.docx`
- साधन जे छापते (पत्राची मांडणी §4.38, सही-साखळी `tools/desks/law-desk6.json`, शीर्षक-ओळी) ते spec मध्ये लिहू नका — lint नाकारते.

## 5. नोंद (spec.json)
- आधी प्रकरण पूर्ण समजून घ्या. जवळचा मंजूर नमुना घ्या; रचना व भाषा तशीच, फक्त तथ्ये बदला (वर्ष / क्रमांक नमुन्यातून नाहीत): वित्त मान्यता → `CR66_*`; माहिती-मागणी → `CR131_*` (उच्च न्यायालयामार्फत → `CR130_*`); सविस्तर नोंद → `HTE_2026_*`; वैद्यकीय → `medical-bill/Medical-Bill-Samples.docx`.
- नियम: §1.1 व §4 (विशेषतः §4.6, §4.18–§4.39 व पुढील) — येथे पुन्हा लिहिलेले नाहीत. वारंवार चुकणारे मुद्दे (शंका असल्यास रेपो पाहा):
  - नोंदीत आलेल्या पत्राचा क्रमांक कोठेही नाही — प्राधिकारी, दिनांक, पृ.N/प.वि.; आदेश क्र., GR क्र., अभिलेखावरील अनौपचारिक संदर्भ क्र. ठेवा (§4.36 C1).
  - एक क्रमांकित परिच्छेद = एक मुद्दा, तपशील `note.sub` मध्ये; परि. 2 "सदर पत्रान्वये …"; तक्ता फक्त संख्या / आकडेमोड व सेवातपशील, बाकी मुद्देनिहाय; शेवट "उपरोक्त वस्तुस्थिती विचारात घेता, … सबब, …" (§4.37).
  - उपलब्ध नसलेली माहिती एकाच परिच्छेदात, सबबच्या आधी: "सदर प्रकरणी <प्राधिकारी> यांच्या दि. … रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:- (1) …; (2) …." — तक्ता नाही (§4.31 (अ), §4.36 C2).
  - इशारे / "पॅकेज" / AI-शब्द नाहीत; अज्ञात → "____" (§4.27). "अ.मु.स. (वित्त)" फक्त नस्ती वित्त विभागाकडे जाताना (§4.6).
- **A1–A12 (§4.39)** प्रत्येक नोंद/पत्रावर: उतारा वाक्य-सुरुवातीपासून (नियम + परंतुक); "वरील …नुसार" फक्त उताऱ्यात जे आहे ते; मागवलेले मुद्दे तरतुदीच्या शब्दांनुसार, संदर्भ-पत्रांच्या प्रती नाहीत; आधीची टिप्पणी/पत्र कालक्रमात; "____ आहे" वाक्य माहिती-परिच्छेदाबाहेर नाही; तक्त्यानंतरचे वाक्य फक्त तक्त्यातील; नावाचे एकच रूप — मराठी आद्याक्षरे (§4.18); तक्त्यातील तथ्य वाक्यात पुन्हा नाही; एकच अभिप्राय एकदाच (A8); "संबंधित माहिती" मधील उतारे अक्षरशः (A9); अत्यावश्यक माहिती GR च्या प्रत्येक अट / पायरी व विहित प्रपत्राच्या स्तंभांवरून स्वतः ठरवावी, Abhi ला विचारू नये (A10); प्रकरणाचा टप्पा शेवटच्या दिनांकाच्या कागदपत्रावरून — शेवटचे या कार्यासनाचे पत्र व नंतर काही प्राप्त नसल्यास पत्र = स्मरणपत्र, टिप्पणीत माहिती-अभावाचा परिच्छेद नाही (A11); परि. 1 एकच वाक्य; इतर विभागाचा अनौ.सं.क्र. अभिलेखावर असल्यास दिनांकासह (A12).
- **§4.40:** परि. 1 मध्ये प्रकरण ज्या पत्रांवरून सुरू झाले ती सर्व पत्रे; प्रस्तावात आधीच असलेला GR पुन्हा जोडू नये; पत्राचा विषय प्रस्तावाच्या पत्रातील; एकच माहिती पुन्हा मागवू नये.

## 6. GR सह प्रस्ताव PDF (SOP Step 5; §4.7, §4.11, §4.13)
1. `enclosures.json`: प्रत्येक GR/निकालाचे पहिले पान + उद्धृत परिच्छेदांची पाने; प्रस्तावात आधीच असलेले पुन्हा नाहीत.
2. `python3 tools/pkg3.py <proposal.pdf> enclosures.json "<out>/<मूळ फाइलनाव>.pdf"`.
3. स्कॅन / legacy पाने: `tools/highlight.py` (lines / ocr / rect). **फक्त पिवळा highlight; चौकट नाही; प्रस्तावाच्या पानांवर काहीही नाही.**
4. पाने render करून पाहा; highlight फक्त उद्धृत ओळींवर. "पृ.N/प.वि." `<out>.map.json` वरून.

## 7. Build व तपासणी (SOP Step 6–7)
```
python3 tools/lint_spec.py spec.json --pages <एकूण पाने>        # LINT OK; WARN ओळीही वाचा
python3 tools/build_note_letter.py spec.json <out> <PREFIX>    # + build_order (निवडले असल्यास)
python3 tools/build_study.py study.json <out>/<PREFIX>_Study.docx
python3 tools/verify_outputs.py <out> <PREFIX> "<package pdf>" <प्रस्तावाची पाने>   # ALL OK
python3 tools/fact_check.py "<package pdf>" --spec spec.json --details <FILE>      # WARN
python3 tools/consistency_check.py spec.json --study study.json --details <FILE>   # WARN
```
- Study: भाग 0 (§4.17) + भाग 1–7 (`tools/PROPOSAL_PROMPT.md`); इशारे भाग 7 च्या शेवटी (`tools/study_warnings.py`, §4.26).
- प्रत्येक मसुद्याचे PDF-पूर्वावलोकन प्रत्येक पान पाहा.
- दुसरे वाचन: प्रत्येक नाव, दिनांक, रक्कम, पान मूळ प्रतिमेशी; प्रत्येक "वरील …नुसार" उद्धृत पानाशी (A2).

## 8. देणे व नोंद ठेवणे (SOP Step 8)
1. फाइल पाठवा: `_Note_and_Letter.docx`, मूळ नावाची GR सह PDF, `_Study.docx`, निवडलेले मसुदे.
2. मराठीत 4–6 ओळी: प्रस्ताव काय, पत्र आहे/नाही व मुद्दे, जोडलेले GR (पाने), न मिळालेल्या GR चे दिनांक.
3. मंजूर spec `samples/specs/<CR>_<वर्ष>_<प्रकार>.json`, नवे GR `pdf/gr/` — commit + push (scratch फाइल्स नाहीत).
4. **Abhi ची नवी सुधारणा:** आधी grep (दुसऱ्या सत्राने जोडली असल्यास पुन्हा नाही); `INSTRUCTIONS.md` §4 मध्ये नवा क्रमांक (दिनांक व त्याचे शब्द), `PROPOSAL_SOP.md`, `tools/ENGINE_BRIEF.md` (आकार-मर्यादा `tests/test_engine_brief.py`), गरजेनुसार lint / verify / samples; `pytest` चालवूनच push; Project मधील `claude/00-STANDING-INSTRUCTIONS.md` ला `INSTRUCTIONS.md` ची प्रत लिहा. नियम या skill मध्ये नव्हे, रेपोत.

## धडे
- स्कॅन PDF चा मजकूर-स्तर रिकामा — अंदाज नाही; OCR + पान-प्रतिमा.
- मागणी स्पष्ट नसेल तर अंदाजावर नोंद नाही; मूळ प्रत मागा.
- नमुना spec बदलताना रेपोतील नवी आवृत्ती घेऊन त्यावरच बदल; नमुना व नियम यांत फरक → INSTRUCTIONS.md जिंकते.
- skill मधील आठवण रेपोशी जुळत नसेल तर रेपोप्रमाणे करा व Abhi ला skill अद्ययावत करायला एका ओळीत सांगा.
