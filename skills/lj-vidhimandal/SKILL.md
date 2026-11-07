---
name: "lj-vidhimandal"
description: "Use whenever Abhi uploads Law & Judiciary Desk-6 legislature work (विधिमंडळ कामकाज) — starred / unstarred / short-notice question (तारांकित / अतारांकित प्रश्न), calling-attention notice (लक्षवेधी), assurance (आश्वासन) or a Legislature Secretariat letter — or asks for its noting or answer draft. Not for service proposals (lj-seva) or court matters (lj-nyayalayin)."
---

# विधि व न्याय विभाग, कार्यासन-6 — विधिमंडळ कामकाज

**हा skill फक्त कार्यपद्धत सांगतो; नोंद/पत्र/मसुद्यांचे सर्व नियम रेपोतील फाइल्समध्ये — फरक आढळल्यास रेपो जिंकतो.**
श्रेणी: `legislature` (`tools/work_types/legislature.json`, नियम-साचा `tools/work_rules/legislature.md` — **status rules_pending**). सेवाविषयक → `lj-seva`, न्यायालयीन → `lj-nyayalayin`, खरेदी → `lj-kharedi`.

Abhi (कार्यासन अधिकारी, कार्यासन-6) कागदपत्रे अपलोड करतो; सर्व पायऱ्या न विचारता शेवटपर्यंत कराव्यात. उत्तर मराठीत, थोडक्यात.

## 0. सुरुवात (प्रत्येक वेळी)
1. रेपो `abhishekwasu-hue/law-judiciary-service-rules`: सत्रात नसेल तर `add_repo` मग clone; असेल तर `git pull --rebase`.
2. **नियमांचा एकमेव स्रोत — आधी पूर्ण वाचा:** `OWNER_RULES.md`; `INSTRUCTIONS.md` §1–§3 व §4 चे **सर्व** क्रमांक (नवे जोडले जातात — शेवटपर्यंत वाचा); `PROPOSAL_SOP.md`; `PROPOSAL_WORKFLOW.md`; `HANDOVER.md`; `tools/ENGINE_BRIEF.md`; `tools/work_rules/legislature.md`; `samples/specs/`.
3. साधने: `pip install pymupdf docxcompose python-docx --break-system-packages`; `soffice`, `pdftoppm`, `tesseract`. `mar.traineddata` नसेल तर `https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/mar.traineddata` → `/usr/share/tesseract-ocr/5/tessdata/`. जुन्या प्रकरणांचा मजकूर: `python3 tools/oldcases_text.py /tmp/old`.
4. Task list (प्रत्येक प्रस्ताव स्वतंत्र). OCR, GR शोध, मसुदे, Study — समांतर agents (OWNER_RULES A.13); lead म्हणून प्रत्येक diff तपासा.
5. Project मधील `claude/00-STANDING-INSTRUCTIONS.md` = `INSTRUCTIONS.md` ची प्रत; फरक असल्यास रेपो जिंकतो व प्रत रेपोवरून अद्ययावत करा.

## सामाईक मसुदा-रचना (चारही श्रेणींना लागू — मूळ नियम INSTRUCTIONS मध्ये; येथे फक्त आठवण)
- **फॉन्ट:** सर्व Word फाइल्स DVOT-SurekhMR (ascii / hAnsi / cs / eastAsia चारही); अपवाद इंग्रजी शपथपत्र — Times New Roman 14, मराठी उताऱ्यांसाठी DVOT-SurekhMR (§4.2, §4.33 (ए)).
- **साचा व आकार:** टिप्पणी व पत्र फक्त `tools/templates/NOTE_TEMPLATE.docx` / `LETTER_TEMPLATE.docx` मधून (`tools/mkdocs.py`) — लेटरहेड, समास, अक्षराचा आकार साच्याप्रमाणे, तक्त्यातील अक्षर 11 pt; साचा किंवा आकार हाताने बदलू नये (§4.3, §7.3).
- **फाइल-रचना:** टिप्पणी व पत्र एकाच Word मध्ये, पत्र नव्या पानावर (§4.1); GR सह प्रस्ताव PDF मूळ फाइलनावाने (§4.16); प्रत्येक प्रकरणाची `_Study.docx` (§4.8, §4.17).
- **सही:** टिप्पणीची सही-साखळी §4.6 (desk profile `tools/desks/law-desk6.json`; अ.मु.स. (वित्त) फक्त वित्त विभागाकडे जाताना); पत्र "आपला," → ( राजेश वडनेरकर ) / अवर सचिव ,महाराष्ट्र शासन → "प्रत" एकदाच (§4.5, §4.38 (ई)).
- **पत्राची मांडणी:** विषय / संदर्भ ठळक, उजवीकडे सरकवलेला गट; मागवलेले मुद्दे "(1)", "(2)" एकाच क्रमाने; पहिला परिच्छेद क्रमांकाविना, पुढे "2.", "3." — साधन छापते (§4.10, §4.38).
- **टिप्पणीची रचना:** 12 घटक (§4.29); एक क्रमांकित परिच्छेद = एक मुद्दा, उप-मुद्दे `note.sub`; तक्ता फक्त संख्या / आकडेमोड व सेवातपशील; उपलब्ध नसलेली माहिती एकाच परिच्छेदात; शेवट "उपरोक्त वस्तुस्थिती विचारात घेता, … सबब, …" (§4.31, §4.37); आलेल्या पत्राचा क्रमांक नाही (§4.36 C1); पृष्ठ-संदर्भ फक्त "पृ.N/प.वि." (§4.27 (अ)).
- **मराठी भाषाशैली:** छोटी वाक्ये, एका वाक्यात एक मुद्दा, कर्ता स्पष्ट; "श्रीमती", "मा. उच्च न्यायालय", नावे मराठी आद्याक्षरांत (§4.18, §4.23); "दि. " / "क्र. " नंतर जागा, ":-", करून, अनुसरून, प्रारूप, शुद्धिपत्रक, "द्ध" (§4.19, §4.24, §4.25; `tools/ENGINE_BRIEF.md` "Marathi language rules"); पत्रात "…उपलब्ध करून देण्यात यावी, ही विनंती." (§4.18); उतारे शब्दशः, शुद्धलेखन-बदल नाही (§1.1, A9).
- **मागमूस नाही:** इशारे, "पॅकेज", "स्रोत", AI-शब्द, "—", "→" नाहीत; अज्ञात → "____"; docx / PDF गुणधर्म रिकामे (§4.27, `tools/clean_meta.py`). तपासणी: `lint_spec.py` व `verify_outputs.py` ALL OK.

## 1. अपलोड तपासा
- प्रत्येक फाइल उघडा. `.pdf.txt` मध्ये फक्त पान-शीर्षके (स्कॅन) → मूळ PDF एका ओळीत मागा, इतर काम चालू ठेवा.
- अनेक प्रस्ताव = स्वतंत्र प्रकरणे.
- संदर्भासाठी दिलेली जुनी नस्ती पूर्ण वाचा; वित्त / विधि शाखेचे अभिप्राय, शुद्धिपत्रके तथ्य म्हणून. अभिप्रायाचा दिनांक मूळ पानावरील सही-दिनांकावरून.
- Abhi "प्रस्तावाला लावा" म्हणाल्यास ती कागदपत्रे GR सह PDF च्या शेवटी enclosure (आधीचे पृ. क्रमांक बदलू नयेत), उद्धृत भागावर पिवळा highlight, नोंद सुधारा.
- मूळ फाइलनाव ठेवा; फक्त यादृच्छिक उपसर्ग `xxxxxxxx-` काढा (§4.16).

## 2. प्रश्न / सूचना वाचा (प्रत्येक पान)
- `pdftoppm -r 150 -gray` + `tesseract -l mar+eng`; मुख्य पाने **पान-प्रतिमा पाहून** दोनदा.
- प्रकार (तारांकित / अतारांकित / अल्पसूचना / लक्षवेधी / आश्वासन इ.), सभागृह, प्रश्न क्रमांक, सदस्य, मंत्री, उत्तराचा दिनांक, प्रत्येक खंड (१), (२) … शब्दशः, विधानमंडळ सचिवालयाचे पत्र (दिनांक, पान).
- प्रत्येक खंडाचे उत्तर देणारी तथ्ये अभिलेखावरून (GR, आकडेवारी, पत्रव्यवहार) — पान क्रमांकासह. पृष्ठ-संदर्भ = PDF पान क्रमांक.

## 3. तरतुदी, GR, पूर्वोदाहरणे (SOP Step 2; §4.14)
- रेपो: `register/`, `pdf/`, `pdf/gr/INDEX.tsv`, `service-rules/`, `precedent-library/` (unzip, `00-INDEX.docx`), `working-notes/CASE-REGISTER.md`, `सन ... प्रकरणे.zip` (याच कर्मचाऱ्याची / विषयाची नस्ती — पूर्वीचा वित्त अभिप्राय).
- GR नसेल तर स्वतः मिळवा: archive.org `advancedsearch.php?q=collection:maharashtragr+AND+date:[…]` (सांकेतांकाचे शेवटचे 2 अंक: 12 विधि व न्याय, 05 वित्त); PDF `archive.org/download/in.gov.maharashtra.gr.<code>/<code>.pdf` किंवा `gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf`; नाहीतर `tools/gr-request.txt` + `python3 tools/gr_request.py` / push. → `pdf/gr/` + `INDEX.tsv`. तरीही नाही → सांकेतांक एका ओळीत विचारा, काम चालू.
- न्यायालयीन आदेश फक्त api.sci.gov.in / bombayhighcourt.nic.in (`pdf/sc/`); तृतीय-पक्ष स्रोत नाही (§1.3).
- उतारे मूळ पान-प्रतिमा पाहून शब्दशः (legacy font चा मजकूर-स्तर बिघडलेला).

## 4. श्रेणी-नियम व मसुदे (§4.28, §4.33 (ऐ))
- **नियम अजून नाहीत (status rules_pending):** या श्रेणीचे स्वतंत्र नियम / नमुने रेपोत नाहीत. स्वतःचे नियम किंवा रचना कधीही रचू नये (OWNER_RULES A.3/A.5). तोपर्यंत टिप्पणी सर्वसाधारण नियमांनुसार (INSTRUCTIONS §4, `tools/work_rules/service.md`) आणि Study भाग 7 च्या शेवटी `tools/work_types/legislature.json` मधील `pending_warning`.
- **Abhi ने नमुने दिले की** (जुनी मंजूर नस्ती: टिप्पणी + मसुदा, PDF / Word): `samples/work/legislature/` मध्ये ठेवा; `samples/work/legislature/README.md` च्या पायऱ्यांप्रमाणे प्रत्येक नमुन्याची रचना (परिच्छेद-क्रम, मसुदे, अत्यावश्यक घटक, मुदती, सही-साखळी) नमुना-फाइल + पानासह `tools/work_rules/legislature.md` मध्ये भरा; Abhi च्या मान्यतेनंतर मंजूर spec `samples/specs/`, `"status": "ready"`, `python3 tools/work_type.py check` + tests, push; नंतर हा skill अद्ययावत करायला Abhi ला एका ओळीत सांगा.
- हवे असलेले नमुने: `tools/work_types/legislature.json` → `required_samples`.
- **जे आधीच तयार आहे — विधानमंडळ प्रश्नाचे उत्तर (`lq`):** तारांकित / अतारांकित / अल्पसूचना प्रश्नाचे उत्तर अधिकृत GADT 13.9 नमुन्यावरून — spec `lq` → `tools/build_lq.py spec.json <out> <PREFIX>` → `<PREFIX>_LQ_Answer.docx` (तारांकित / अल्पसूचनासाठी नव्या पानावर "पुरवणी टिप्पणी"); नमुना `samples/specs/LQ_answer_example.json`; तपशील, उत्तर-रूपे व डिफॉल्ट INSTRUCTIONS §4.33 (ऐ); संशोधन `docs/LEGISLATURE_INSTRUMENTS_RESEARCH.md`, `docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md`.
- लक्षवेधी सूचना, आश्वासन-पूर्ती इ. साधनांसाठी नमुना नाही — टिप्पणीच फक्त; त्याचे निवेदन / विवरणपत्र स्वतः रचू नये; Study भाग 4 मध्ये नोंद.
- साधन जे छापते (शीर्षक-ओळी, "सन्माननीय … खुलासा करतील काय :-", अग्रेषण-ओळ) ते spec मध्ये लिहू नका — lint नाकारते.

## 5. टिप्पणी (spec.json)
- प्रत्येक खंडाचा स्वतंत्र परिच्छेद — तथ्ये अभिलेखावरून, शेवटी "प्रस्तावित उत्तर : …" (§4.33 (ऐ)); शेवटचा परिच्छेद "सबब, … प्रश्न क्रमांक ____ च्या उत्तराचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.".
- मुदत (तारांकित / अतारांकित 30 दिवस, अल्पसूचना 7 / 14 दिवस — §4.33 (ऐ)) Study भाग 0 मध्ये.
- सर्वसाधारण नियम: §1.1, §4.18–§4.27, §4.29–§4.31, §4.36, §4.37, §4.39 (A1–A12), §4.40. उत्तर-रूपे फक्त अभिलेखातील तथ्यांवरून; स्वतःचे मत / अंदाज नाही; अज्ञात → "____".

## 6. GR सह प्रस्ताव PDF (SOP Step 5; §4.7, §4.11, §4.13)
1. `enclosures.json`: प्रत्येक GR/निकालाचे पहिले पान + उद्धृत परिच्छेदांची पाने; प्रस्तावात आधीच असलेले पुन्हा नाहीत.
2. `python3 tools/pkg3.py <proposal.pdf> enclosures.json "<out>/<मूळ फाइलनाव>.pdf"`.
3. स्कॅन / legacy पाने: `tools/highlight.py` (lines / ocr / rect). **फक्त पिवळा highlight; चौकट नाही; प्रस्तावाच्या पानांवर काहीही नाही.**
4. पाने render करून पाहा; highlight फक्त उद्धृत ओळींवर. "पृ.N/प.वि." `<out>.map.json` वरून.

## 7. Build व तपासणी (SOP Step 6–7)
```
python3 tools/lint_spec.py spec.json --pages <एकूण पाने>        # LINT OK; WARN ओळीही वाचा
python3 tools/build_note_letter.py spec.json <out> <PREFIX>    # + build_lq (lq असल्यास)
python3 tools/build_study.py study.json <out>/<PREFIX>_Study.docx
python3 tools/verify_outputs.py <out> <PREFIX> "<package pdf>" <प्रस्तावाची पाने>   # ALL OK
python3 tools/fact_check.py "<package pdf>" --spec spec.json --details <FILE>      # WARN
python3 tools/consistency_check.py spec.json --study study.json --details <FILE>   # WARN
```
- Study: भाग 0 (§4.17) + भाग 1–7 (`tools/PROPOSAL_PROMPT.md`); इशारे भाग 7 च्या शेवटी (`tools/study_warnings.py`, §4.26).
- प्रत्येक मसुद्याचे PDF-पूर्वावलोकन प्रत्येक पान पाहा (verify LQ उत्तर तपासत नाही).
- दुसरे वाचन: प्रत्येक नाव, दिनांक, रक्कम, पान मूळ प्रतिमेशी; प्रत्येक "वरील …नुसार" उद्धृत पानाशी (A2).

## 8. देणे व नोंद ठेवणे (SOP Step 8)
1. फाइल पाठवा: `_Note_and_Letter.docx`, मूळ नावाची GR सह PDF, `_Study.docx`, निवडलेले मसुदे.
2. मराठीत 4–6 ओळी: प्रस्ताव काय, पत्र आहे/नाही व मुद्दे, जोडलेले GR (पाने), न मिळालेल्या GR चे दिनांक.
3. मंजूर spec `samples/specs/<CR>_<वर्ष>_<प्रकार>.json`, नवे GR `pdf/gr/` — commit + push (scratch फाइल्स नाहीत).
4. **Abhi ची नवी सुधारणा:** आधी grep (दुसऱ्या सत्राने जोडली असल्यास पुन्हा नाही); `INSTRUCTIONS.md` §4 मध्ये नवा क्रमांक (दिनांक व त्याचे शब्द), `PROPOSAL_SOP.md`, `tools/ENGINE_BRIEF.md` (आकार-मर्यादा `tests/test_engine_brief.py`), गरजेनुसार lint / verify / samples; `pytest` चालवूनच push; Project मधील `claude/00-STANDING-INSTRUCTIONS.md` ला `INSTRUCTIONS.md` ची प्रत लिहा. नियम या skill मध्ये नव्हे, रेपोत.

## 9. स्थिती-फाइल व सुधारणा-फेरी (INSTRUCTIONS §4.41)
- एक प्रस्ताव = एक चॅट. प्रकरण-ओळख `<CR/WP>_<वर्ष>` (उदा. `CR131_2026`) = PREFIX.
- **पहिल्या फेरीत खर्च कमी:** सर्व पानांचा OCR मजकूर आधी वाचा; पान-प्रतिमा फक्त टिप्पणी / पत्र / भाग 0 मध्ये उद्धृत होणाऱ्या पानांच्या, मजकूर नसलेल्या आवश्यक पानांच्या व मागणी / टप्प्यावर परिणाम करणाऱ्या शिक्के-हस्तलिखिताच्या (§4.41).
- **पहिली फेरी पूर्ण झाल्यावर:** `python3 tools/case_state.py save <id> --work <कामाचा फोल्डर> --proposal <प्रस्ताव.pdf> --package-name "<मूळ फाइलनाव>.pdf" --prefix <PREFIX> --note "<टप्पा>"` (spec, study, enclosures, marks व प्रस्ताव `cases/<id>/` मध्ये) → commit + push.
- **Preview:** `python3 tools/case_state.py rebuild <id> <out> --package` टिप्पणी व पत्राची पाने `<out>/preview/*.png` मध्ये देते — फाइल्ससोबत ती SendUserFile (render) ने पाठवा; Abhi पाहून सूचना देतो.
- **सुधारणा-फेरी (Abhi ची सूचना आली की):** प्रस्ताव पुन्हा वाचू नका, OCR व संशोधन पुन्हा नाही (सूचनेत नवीन GR / कागद असेल तेवढेच).
  1. नवी चॅट असल्यास `python3 tools/case_state.py load <id> <work>`; जुनी असल्यास तोच फोल्डर.
  2. सूचना फक्त spec.json / study.json / enclosures.json मध्ये लागू करा; एखादे तथ्य तपासायचे असल्यास फक्त त्या उद्धृत पानाची प्रतिमा.
  3. `python3 tools/case_state.py save <id> … --note "सुधारणा: <थोडक्यात>"`.
  4. `python3 tools/case_state.py rebuild <id> <out>` (GR सह PDF बदलले असल्यास `--package`) — LINT OK, verify ALL OK.
  5. फक्त बदललेली फाइल + नवीन preview पाठवा; commit + push; उत्तर 1–2 ओळी — काय बदलले.
- सूचना पुढील सर्व प्रकरणांना लागू होणारी (नियम) असल्यास §8.4 प्रमाणे `INSTRUCTIONS.md` मध्ये.

## धडे
- स्कॅन PDF चा मजकूर-स्तर रिकामा — अंदाज नाही; OCR + पान-प्रतिमा.
- नमुना spec बदलताना रेपोतील नवी आवृत्ती घेऊन त्यावरच बदल; नमुना व नियम यांत फरक → INSTRUCTIONS.md जिंकते.
- skill मधील आठवण रेपोशी जुळत नसेल तर रेपोप्रमाणे करा व Abhi ला skill अद्ययावत करायला एका ओळीत सांगा.
