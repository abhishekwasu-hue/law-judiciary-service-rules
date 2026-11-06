---
name: "lj-prastav-desk6"
description: "Use when Abhi uploads a Law & Judiciary Desk-6 proposal, court petition or reply (PDF) to prepare the Marathi noting, letter, Study file and proposal PDF with GRs."
---

# विधि व न्याय विभाग, कार्यासन-6 — प्रस्ताव / याचिका तयार करणे

**हा skill फक्त कार्यपद्धत सांगतो; नोंद/पत्र/मसुद्यांचे सर्व नियम रेपोतील फाइल्समध्ये — फरक आढळल्यास रेपो जिंकतो.**

Abhi (कार्यासन अधिकारी, कार्यासन-6) PDF अपलोड करतो; सर्व पायऱ्या न विचारता शेवटपर्यंत कराव्यात. उत्तर मराठीत, थोडक्यात.

## 0. सुरुवात (प्रत्येक वेळी)
1. रेपो `abhishekwasu-hue/law-judiciary-service-rules`: सत्रात नसेल तर `add_repo` मग clone; असेल तर `git pull --rebase`.
2. **नियमांचा एकमेव स्रोत — आधी पूर्ण वाचा:** `OWNER_RULES.md`; `INSTRUCTIONS.md` §1–§3 व §4 चे **सर्व** क्रमांक (आज 1–39, नवे जोडले जातात — शेवटपर्यंत वाचा; §4.39 = अचूकता-तपासण्या A1–A8); `PROPOSAL_SOP.md`; `PROPOSAL_WORKFLOW.md`; `HANDOVER.md`; `tools/ENGINE_BRIEF.md`; `samples/specs/` (मंजूर नमुने).
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
- मुख्य पाने (निर्देशपत्र, मागणी/प्रार्थना, पक्षकार, तक्ते, शिक्के, हस्तलिखित शेरे, दिनांक, रकमा) **पान-प्रतिमा पाहून** दोनदा.
- पृष्ठ-संदर्भ = PDF पान क्रमांक (छापील / हस्तलिखित नव्हे).
- तथ्य-यादी: कोणी, कोणामार्फत, पत्रांचे दिनांक व पाने, मागणी, कर्मचारी/पद/दिनांक/रक्कम, जोडपत्रे, प्रस्तावातील या कार्यासनाची आधीची टिप्पणी/पत्र (§4.39 A4), याच विषयाची जुनी नस्ती.
- याचिका: याचिकाकर्ते, प्रतिवादी (क्रमाने), प्रार्थना (शब्दशः), निशाण्या व त्यांची पाने, आधारलेले निर्णय, प्रतिज्ञापन दिनांक.

## 3. तरतुदी, GR, पूर्वोदाहरणे (SOP Step 2; §4.14)
- रेपो: `register/`, `pdf/`, `pdf/gr/INDEX.tsv`, `service-rules/`, `precedent-library/` (unzip, `00-INDEX.docx`), `working-notes/CASE-REGISTER.md`, `medical-bill/`, `सन ... प्रकरणे.zip` (याच कर्मचाऱ्याची / विषयाची नस्ती — पूर्वीचा वित्त अभिप्राय).
- GR नसेल तर स्वतः मिळवा: archive.org `advancedsearch.php?q=collection:maharashtragr+AND+date:[…]` (सांकेतांकाचे शेवटचे 2 अंक: 12 विधि व न्याय, 05 वित्त); PDF `archive.org/download/in.gov.maharashtra.gr.<code>/<code>.pdf` किंवा `gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf`; नाहीतर `tools/gr-request.txt` + `python3 tools/gr_request.py` / push. → `pdf/gr/` + `INDEX.tsv`. तरीही नाही → सांकेतांक एका ओळीत विचारा, काम चालू.
- न्यायालयीन आदेश फक्त api.sci.gov.in / bombayhighcourt.nic.in (`pdf/sc/`); तृतीय-पक्ष स्रोत नाही (§1.3).
- उतारे मूळ पान-प्रतिमा पाहून शब्दशः (legacy font चा मजकूर-स्तर बिघडलेला).

## 4. पत्र की नस्ती? कोणते मसुदे? (SOP Step 3, 4b; §4.15, §4.28, §4.33)
- निर्णय SOP Step 3 प्रमाणे; Abhi ने मसुदे निवडले असल्यास नेमके तेच.
- spec-key → साधन → फाइल:
  - `letter` / `letters` (पत्र, स्मरणपत्र, `"kind": "do"`), `note.uo` → `tools/build_note_letter.py` → `<PREFIX>_Note_and_Letter.docx`
  - `order` / `orders` (gr, corrigendum, circular, memo, notification, endorsement, office_order, press_note, addendum) → `tools/build_order.py` → `_Order_Draft.docx`
  - `parawise` → `tools/build_parawise.py` → `_Parawise.docx`; `affidavit` → `tools/build_affidavit.py` → `_Affidavit.docx`; `lq` → `tools/build_lq.py` → `_LQ_Answer.docx`
- साधन जे छापते (पत्राची मांडणी §4.38, सही-साखळी `tools/desks/law-desk6.json`, शीर्षक-ओळी) ते spec मध्ये लिहू नका — lint नाकारते.

## 5. नोंद (spec.json)
- आधी प्रकरण पूर्ण समजून घ्या. जवळचा मंजूर नमुना घ्या; रचना व भाषा तशीच, फक्त तथ्ये बदला (वर्ष / क्रमांक नमुन्यातून नाहीत): याचिका → `WP35697_2026_old-pension_finance-opinion.json`; परिच्छेदनिहाय + सरकारी वकील पत्र → `WP35697_2026_parawise_GP-letter.json`; वित्त मान्यता → `CR66_*`; माहिती-मागणी → `CR131_*`; सविस्तर नोंद → `HTE_2026_*`.
- नियम: §1.1 व §4 (विशेषतः §4.6, §4.18–§4.39) — येथे पुन्हा लिहिलेले नाहीत. वारंवार चुकणारे मुद्दे (आजच्या नियमांप्रमाणे; शंका असल्यास रेपो पाहा):
  - नोंदीत आलेल्या पत्राचा क्रमांक कोठेही नाही — प्राधिकारी, दिनांक, पृ.N/प.वि.; आदेश क्र., GR क्र., याचिका क्र., अभिलेखावरील अनौपचारिक संदर्भ क्र. ठेवा (§4.36 C1).
  - एक क्रमांकित परिच्छेद = एक मुद्दा, तपशील `note.sub` मध्ये; परि. 2 "सदर पत्रान्वये …"; तक्ता फक्त संख्या / आकडेमोड व सेवातपशील, बाकी मुद्देनिहाय; "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-" यादी नाही — शेवट "उपरोक्त वस्तुस्थिती विचारात घेता, … सबब, …" (§4.37).
  - उपलब्ध नसलेली माहिती एकाच परिच्छेदात, सबबच्या आधी: "सदर प्रकरणी <प्राधिकारी> यांच्या दि. … रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:- (1) …; (2) …." — तक्ता नाही (§4.31 (अ), §4.36 C2).
  - याचिका: परि. 2 याचिका व प्रतिवादी सलग वाक्यांत; परि. 3 प्रार्थना "(अ) …; (आ) …" (`note.sub`), तक्ता नाही; मराठी नोंद/पत्रात "(लॉजिंग)" नाही (§4.32).
  - इशारे / "पॅकेज" / AI-शब्द नाहीत; अज्ञात → "____" (§4.27). "अ.मु.स. (वित्त)" फक्त नस्ती वित्त विभागाकडे जाताना (§4.6).
- **A1–A8 (§4.39)** प्रत्येक नोंद/पत्रावर: उतारा वाक्य-सुरुवातीपासून (नियम + परंतुक); "वरील …नुसार" फक्त उताऱ्यात जे आहे ते; मागवलेले मुद्दे तरतुदीच्या शब्दांनुसार, संदर्भ-पत्रांच्या प्रती नाहीत; आधीची टिप्पणी/पत्र कालक्रमात; "____ आहे" वाक्य माहिती-परिच्छेदाबाहेर नाही; तक्त्यानंतरचे वाक्य फक्त तक्त्यातील; नावाचे एकच रूप (अग्रेषण-पत्रातील); तक्त्यातील तथ्य वाक्यात पुन्हा नाही.

## 5b. न्यायालयीन याचिका (SOP Step 4b; §4.32, §4.35)
- परिच्छेदनिहाय अभिप्राय कार्यासनाच्या format मध्ये (`build_parawise.py` default), फक्त अभिलेखावरून; न वाचलेल्या निकालावर भाष्य नाही.
- अनेक शासकीय प्रतिवादी → एकत्रित शपथपत्र (`on_behalf_of`); उच्च न्यायालय प्रशासन त्यात नाही (§4.35).
- देणे (आधीच्या सत्रातील Abhi ची पसंती): एकच Word — परिच्छेदनिहाय अभिप्राय, टिप्पणी, पत्र (docxcompose; `<PREFIX>_Parawise_Note_and_Letter.docx`).

## 6. GR सह प्रस्ताव PDF (SOP Step 5; §4.7, §4.11, §4.13)
1. `enclosures.json`: प्रत्येक GR/निकालाचे पहिले पान + उद्धृत परिच्छेदांची पाने; प्रस्तावात आधीच असलेले पुन्हा नाहीत.
2. `python3 tools/pkg3.py <proposal.pdf> enclosures.json "<out>/<मूळ फाइलनाव>.pdf"`.
3. स्कॅन / legacy पाने: `tools/highlight.py` (lines / ocr / rect). **फक्त पिवळा highlight; चौकट नाही; प्रस्तावाच्या पानांवर काहीही नाही.**
4. पाने render करून पाहा; highlight फक्त उद्धृत ओळींवर. "पृ.N/प.वि." `<out>.map.json` वरून.

## 7. Build व तपासणी (SOP Step 6–7)
```
python3 tools/lint_spec.py spec.json --pages <एकूण पाने>        # LINT OK; WARN ओळीही वाचा
python3 tools/build_note_letter.py spec.json <out> <PREFIX>    # + build_order / build_parawise / build_affidavit / build_lq (निवडले असल्यास)
python3 tools/build_study.py study.json <out>/<PREFIX>_Study.docx
python3 tools/verify_outputs.py <out> <PREFIX> "<package pdf>" <प्रस्तावाची पाने>   # ALL OK
python3 tools/fact_check.py "<package pdf>" --spec spec.json --details <FILE>      # WARN
python3 tools/consistency_check.py spec.json --study study.json --details <FILE>   # WARN
```
- Study: भाग 0 (§4.17) + भाग 1–7 (`tools/PROPOSAL_PROMPT.md`); इशारे भाग 7 च्या शेवटी (`tools/study_warnings.py`, §4.26).
- प्रत्येक मसुद्याचे PDF-पूर्वावलोकन प्रत्येक पान पाहा (verify शपथपत्र / LQ तपासत नाही).
- दुसरे वाचन: प्रत्येक नाव, दिनांक, रक्कम, पान मूळ प्रतिमेशी; प्रत्येक "वरील …नुसार" उद्धृत पानाशी (A2).

## 8. देणे व नोंद ठेवणे (SOP Step 8)
1. फाइल पाठवा: `_Note_and_Letter.docx`, मूळ नावाची GR सह PDF, `_Study.docx`, निवडलेले मसुदे.
2. मराठीत 4–6 ओळी: प्रस्ताव काय, पत्र आहे/नाही व मुद्दे, जोडलेले GR (पाने), न मिळालेल्या GR चे दिनांक.
3. मंजूर spec `samples/specs/<CR/WP>_<वर्ष>_<प्रकार>.json`, नवे GR `pdf/gr/` — commit + push (scratch फाइल्स नाहीत).
4. **Abhi ची नवी सुधारणा:** आधी grep (दुसऱ्या सत्राने जोडली असल्यास पुन्हा नाही); `INSTRUCTIONS.md` §4 मध्ये नवा क्रमांक (दिनांक व त्याचे शब्द), `PROPOSAL_SOP.md`, `tools/ENGINE_BRIEF.md` (आकार-मर्यादा `tests/test_engine_brief.py`), गरजेनुसार lint / verify / samples; `pytest` चालवूनच push; Project मधील `claude/00-STANDING-INSTRUCTIONS.md` ला `INSTRUCTIONS.md` ची प्रत लिहा. नियम या skill मध्ये नव्हे, रेपोत.

## धडे
- स्कॅन PDF चा मजकूर-स्तर रिकामा — अंदाज नाही; OCR + पान-प्रतिमा.
- लांब पत्रव्यवहाराच्या याचिकांत आधीची नस्ती (C R क्र.) zip मध्ये शोधा.
- मागणी स्पष्ट नसेल (उदा. याचिकेची मूळ प्रत नाही) तर अंदाजावर नोंद नाही; मूळ प्रत मागा.
- नमुना spec बदलताना रेपोतील नवी आवृत्ती घेऊन त्यावरच बदल; नमुना व नियम यांत फरक → INSTRUCTIONS.md जिंकते.
- नवा मसुदा-प्रकार फक्त अधिकृत नमुन्यावरून (पान क्रमांकासह); नमुना नसल्यास Study मध्ये नोंद, स्वतः रचना नाही.
- skill मधील आठवण रेपोशी जुळत नसेल तर रेपोप्रमाणे करा व Abhi ला skill अद्ययावत करायला एका ओळीत सांगा.
