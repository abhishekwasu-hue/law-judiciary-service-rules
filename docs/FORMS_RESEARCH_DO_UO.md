# FORMS_RESEARCH_DO_UO.md — अर्धशासकीय पत्र (D.O. letter) व अनौपचारिक संदर्भ (U.O. reference): अधिकृत नमुने (04.11.2026)

Scope: two new document types for Desk-6 — the अर्धशासकीय पत्र (spec letter `"kind": "do"`) and the अनौपचारिक संदर्भ block
at the foot of a note sent to another department (spec note `"uo"`). Only official GoM (GAD) sources. Every printed element
below traces to a specimen line with its page. Nothing else changes: the ordinary letter and the स्मरणपत्र (`"letters"`,
`"reminder"`) are built exactly as before.

## 1. Sources (all in the repo, `pdf/08-gad-office-procedure/`)

| Code | Source | File | How read |
|---|---|---|---|
| MMOP | GAD, *Maharashtra Manual of Office Procedures, 2023* (English) | `GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf` | text layer (pymupdf); Appendix 10.9 page image checked |
| GADT | GAD, *टिप्पणी लेखन व पत्रव्यवहार* (Marathi; specimen dated Jan. 1989) | `GAD_Tippani-Lekhan-va-Patravyavahar-Marathi.pdf` | legacy font: rendered 200 dpi, OCR `tesseract -l mar+eng`, page images read. Book p.N = PDF p.N+4 |
| NPM | GAD, *कार्यालयीन कार्यपद्धतीची नियमपुस्तिका* (Marathi) | `GAD_Karyalayin-Karyapaddhati-Niyampustika-Marathi.pdf` | legacy font: OCR + page images. Book p.77 = PDF p.84, book p.97 = PDF p.104 |
| N&C | GAD, *Noting and Correspondence in Mantralaya* (English, 1961) | `GAD_Noting-and-Correspondence-in-Mantralaya-English.pdf` | text layer + page image |

## 2. अर्धशासकीय पत्र (D.O. letter)

### 2.1 When it is used (rule text)
- MMOP §10.1(7), PDF p.64: "This form is generally used in correspondence by one Government officer with another with the
  purpose of drawing his/her personal attention in an official matter of importance and/or urgency. This form is also used
  when a series of official reminders fail to elicit the information called for. A specimen form of the demi-official
  letter is given in Appendix 10.09." (a) "Since demi-official letter is written in the first person in a personal and
  friendly tone, it should be addressed by an officer to another of similar level /rank as far as possible."
- MMOP §11.4(3), PDF p.80: "The subject should be mentioned invariably in all communications including reminders and demi
  official letters."
- MMOP §11.4(8), PDF p.80: "A communication addressed to a government officer or department should bear the name and
  designation of the officer sending the communications".
- GADT परि. 12.26, book p.43 (PDF p.47): "… किंवा कार्यालयीन स्मरणपत्रांचा उपयोग होत नसेल तर अर्धशासकीय पत्रांचा वापर करतात. …
  त्यामुळे संदर्भ व विषय निराळा काढून लिहिण्यास हरकत नाही."
- GADT परि. 12.27, book p.43: "सामान्यतः अशा पत्राची सुरुवात "प्रिय श्री." अशा अभिवादनाने करतात व शेवटी शुभेच्छा व्यक्त करून व
  "आपला स्नेहांकित" असे लिहून व स्वाक्षरी करून पत्र समाप्त करतात. लिहिणाऱ्या अधिकाऱ्याचे नाव सुरुवातीस पत्राच्या अगदी डाव्या
  कोपऱ्यात वर लिहितात तर ज्यांस पत्र लिहावयाचे त्या अधिकाऱ्याचे नाव व पदनाम पत्रांच्या शेवटी खाली डाव्या बाजूस लिहितात. सचिव व
  वरिष्ठ अधिकाऱ्यांच्या पदनामाचे छापील नमुने (पदनाम राजमुद्रेसह) उपलब्ध असतात व त्यावर अशी पत्रे टंकलिखित करावीत."
- GADT परि. 12.28, book p.43: "सर्वसाधारणपणे अर्धशासकीय पत्रे आपल्या स्तरावरील अधिकाऱ्यांनाच लिहावे. … वरिष्ठ अधिकाऱ्याला
  अर्धशासकीय पत्र काही कारणाने लिहिणे जरूरच असल्यास "प्रिय महोदय" असे संबोधितात".
- NPM परि. 102(9) (OCR, PDF p.56): "अर्धशासकीय पत्राचा नमुना परिशिष्ट ३० मध्ये दिला आहे. … स्मरणपत्रे पाठवूनही मागवलेली माहिती
  मिळाली नसेल तर अशा वेळीही या नमुन्याचा वापर करतात."

### 2.2 Specimens (verbatim lines, in print order)
**GADT specimen, परि. 12.29, book p.43–44 (PDF p.47–48)** — the model followed:
```
                                   अ.शा.पत्र क्र. इएसटी १२८०/२८४-का.१७
                                   सामान्य प्रशासन विभाग
                                   मंत्रालय, मुंबई ४०० ०३२
                                   दिनांक :
अ. ब. पाटील            (bold)
उप सचिव.
              विषय : ज्येष्ठता सूचीकरिता नवीन सूत्रे.        (bold, centre)
प्रिय श्री. नाईक,
      कृपया वरील विषयावरील या विभागाचे समक्रमांकाचे दिनांक १ डिसेंबर १९८८ चे पत्र व नंतरची स्मरणपत्रे पहावीत.
   २. या विषयावरील आपल्या कार्यालयाचा अहवाल अजूनही आलेला नाही. …
   ३. तेव्हा आपण या प्रकरणी जातीने लक्ष पुरवून आपला अहवाल … पाठवावा अशी मी विनंती करतो या प्रकरणी काही स्पष्टीकरण
      हवे असल्यास कृपया दूरध्वनि क्र. …… वर माझ्याशी संपर्क साधावा.
शुभेच्छा
                                              आपला स्नेहांकित,
                                              (अ. ब. पाटील)      (bold)
श्री. शिवदास नाईक,
संचालक, ……
…… पुणे.
```
**NPM परिशिष्ट-30 "अर्ध-शासकीय पत्राचा नमुना", book p.97 (PDF p.104)**: left "श्री. ……" / "अवर सचिव"; right "अर्ध-शासकीय पत्र क्र. ……" /
"…… विभाग." / "मंत्रालय, मुंबई." / "दिनांक ……"; "प्रिय श्री."; "कृपया माझे अर्ध-शासकीय पत्र क्रमांक …… आणि …… पहावे.";
right "आपला स्नेहांकित," / "(अ. ब. क.)"; foot left "श्री ……" / "अवर सचिव, महाराष्ट्र शासन," / "…… विभाग," / "मंत्रालय, मुंबई."

**MMOP Appendix 10.9, PDF p.76** (English, same structure): "Shri ____ / Under Secretary"; right "D. O. No. ____ / ____ Department. /
Mantralaya, Mumbai / Date ____"; "Dear Shri"; "Will you please refer to my demi-official letter No. ____ and ____";
"Yours sincerely, / ____"; foot "Shri ____ / Under Secretary to Government / ____ Department / Government of Maharashtra, /
Mantralay, Mumbai ."

### 2.3 Layout decisions (tools/mkdocs.py `build_do_letter`)
| Printed element | Source |
|---|---|
| "अ.शा.पत्र क्र. <ref_no>" right block, first line | GADT specimen p.43 ("अ.शा.पत्र क्र."); NPM p.97 / MMOP p.76 same place |
| department + address lines (desk profile `letter.office`: "विधि व न्याय विभाग," / "हुतात्मा राजगुरु चौक, … मंत्रालय, मुंबई-४०००३२.") | GADT p.43 "सामान्य प्रशासन विभाग / मंत्रालय, मुंबई ४०० ०३२"; the Desk-6 address is the one on the Section's letterhead |
| "दिनांक : <date>" | GADT p.43 "दिनांक :" |
| sender name (bold) and designation + "." at the left, after the number block | GADT p.43 ("अ. ब. पाटील" / "उप सचिव."); 12.27; MMOP §11.4(8). Default = the desk signer ("राजेश वडनेरकर", "अवर सचिव"; NPM p.97 also shows "अवर सचिव"); spec `from` overrides |
| "विषय : <subject>" bold, centre | GADT p.43; MMOP §11.4(3) (subject invariably); §4.10 bold + centre |
| optional "संदर्भ : …" lines | GADT 12.26 ("संदर्भ व विषय निराळा काढून लिहिण्यास हरकत नाही") |
| salutation "प्रिय श्री. ____," (or "प्रिय महोदय,") | GADT 12.27, 12.28, specimen p.43; NPM p.97 |
| body: 1st para unnumbered with indent, next paras "2.", "3." | GADT specimen p.43–44 (१st para, then "२.", "३.") |
| first person (मी / मला / माझ्या …) — lint error / verify FAIL if absent | MMOP §10.1(7)(a); GADT specimen "मी विनंती करतो", "माझ्याशी"; NPM "माझे अर्ध-शासकीय पत्र" |
| "शुभेच्छा" (left) | GADT 12.27 + specimen p.44 |
| "आपला स्नेहांकित," (right) | GADT 12.27, specimen p.44; NPM p.97 |
| "(<sender name>)" bold, right | GADT p.44 "(अ. ब. पाटील)"; NPM p.97 "(अ. ब. क.)" |
| addressee lines at the foot, left (spec `to`) | GADT 12.27 + p.44; NPM p.97; MMOP p.76 |
| no letterhead / logos, no "महोदय,", no "प्रति,", no "प्रत : …" line | none of the three specimens has them |
| page setup = LETTER_TEMPLATE, font DVOT-SurekhMR | §4.1, §4.2 (unchanged) |

Spec rules (tools/lint_spec.py `lint_do_letter`): ref_no = desk pattern; subject; `to`; `body` non-empty and first person;
salutation, when given, "प्रिय श्री./श्रीमती/महोदय/महोदया …"; ordinary-letter keys (`intro`, `points`, `closing`, `reminder`,
`copies`, `enclosure`) are errors on a D.O. letter; unknown `kind` is an error. §4.18/§4.19/§4.23/§4.27 rules apply as to every
letter. The note's last para must name it ("अर्धशासकीय पत्राचे प्रारूप …"; §4.28 WARN).
verify_outputs.py: the D.O. letter is found by its "अ.शा.पत्र क्र." line; checks number block (ref no. + दिनांक), विषय bold +
centre, "प्रिय …", "शुभेच्छा", "आपला स्नेहांकित,", "(name)", addressee after it, first person, new page/section. The ordinary
letter checks run only on the ordinary letter(s) (a spec may hold both in `letters`).

## 3. अनौपचारिक संदर्भ (U.O. reference)

### 3.1 Rule text
- MMOP §9.1(1), PDF p.57: "Inter- Departmental references shall ordinarily be made unofficially." §9.1(4): "Any file referred
  unofficially to another department shall have attached to it a note signed by the officer by whose direction it is
  referred, precisely specifying the points on which the opinion of the other department is sought … Wherever possible, the
  proposals shall be embodied in the form of a draft." (NPM परि. 37(4), PDF p.25, same in Marathi.)
- MMOP §9.3(1), PDF p.57: U.O. references to all departments except Finance and Law & Judiciary are marked directly to the
  Under Secretary / Deputy Secretary of the desk concerned.
- GADT परि. 5.2, book p.16 (PDF p.20): "अनौपचारिक संदर्भ करताना ज्या मुद्यांबाबत सल्ला किंवा संमती पाहिजे ते मुद्दे टिप्पणीच्या शेवटी
  स्पष्ट लिहावेत व शक्य तेथे आदेशांचे प्रारूपसुद्धा तयार करून संबंधित विभागाला दाखवावे." 5.6, book p.17 (PDF p.21): "सामान्यतः
  अनौपचारिक संदर्भ कार्यासन अधिकाऱ्यांच्या स्तरावर पाठवावा व शक्य तेथे संबंधित विभागाच्या अधिकाऱ्याचे नाव नमूद करून पाठवावा."
- Citation form of a U.O. no.: MMOP §9.5(6), PDF p.59 "unofficial reference No……… dated………"; GADT 5.8, book p.17 "वित्त
  विभागाच्या दिनांक …… च्या अनौपचारिक संदर्भ क्रमांक …… अन्वये"; NPM परि. 41(5), PDF p.27.

### 3.2 Specimen of the U.O. identification block
**NPM परिशिष्ट-8 "कागदपत्रे ठेवून घेण्यासंबंधीचे ज्ञापन" [प्रकरण पाच, परिच्छेद ४०(२)], book p.77 (PDF p.84)** — the only Marathi
official specimen found that prints a U.O. reference's identification lines; at the foot, left:
```
                                              ———————————— विभाग
… विभागाकडील, अनौपचारिक संदर्भ क्रमांक …… दिनांक …… १९ …… या विभागाकडे ठेवून घेण्यात आला आहे.
                                                  कार्यासन अधिकारी
विभागाकडे अनौपचारिक संदर्भ …………… कार्यासन ……………
क्रमांक …………… दिनांक …………… १९ ……
```
English counterpart: N&C Appendix IV (book p.19, PDF p.22) — "Superintendent, ——Branch, / ——Department" then "Unofficial
reference to the —— Department No. , dated 19 ..".

### 3.3 Layout decisions (tools/mkdocs.py `uo_lines`, printed after the note's signer chain, left)
| Printed line | Source |
|---|---|
| "<from>" — default the desk department "विधि व न्याय विभाग" | NPM p.77 "———विभाग" (issuing department); N&C p.19 "——Department" under the signer |
| "<to> विभागाकडे अनौपचारिक संदर्भ कार्यासन <desk>" — e.g. "वित्त विभागाकडे अनौपचारिक संदर्भ कार्यासन का.6" | NPM p.77 "…… विभागाकडे अनौपचारिक संदर्भ …… कार्यासन ……"; N&C p.19 "Unofficial reference to the —— Department" |
| "क्रमांक <no> दिनांक <date>" (unknown "____") | NPM p.77 "क्रमांक …… दिनांक …… १९ ……"; N&C "No. , dated" |

Lint (`uo_problems`): `uo` an object with keys to / no / date / desk / from; `to` required and ending "विभाग"; the note's last
para must send the file to that department (GADT 5.2: the points at the end of the note; MMOP §9.1(4)). The signer chain,
अ.मु.स. (वित्त) rule and last-para forms are unchanged (a U.O. reference to Finance: "सबब, … वित्त विभागाच्या अभिप्रायास्तव सादर
करण्यात येत आहे." + अ.मु.स. (वित्त)). verify_outputs: the three lines right after the signer chain ("अनौपचारिक संदर्भ block").

## 4. Samples, tests, previews
- `samples/specs/LETTER_do_example.json` — note + D.O. letter to प्रबंधक (कार्मिक), उच्च न्यायालय (अपील शाखा) after the letter and
  two reminders brought no reply (MMOP §10.1(7)); all unknowns "____".
- `samples/specs/NOTE_uo_reference_example.json` — note to वित्त विभाग for opinion on an allowance proposal, with the U.O. block.
- `tests/test_do_uo.py` — lint rules, build order of every element, ordinary letter + reminder unchanged, verify ALL OK on
  letter + D.O. letter, verify FAILs (subscription removed, U.O. no./date line removed).
- Previews built with `tools/build_note_letter.py` and LibreOffice; page images checked.

## 5. Open points (for Abhi)
1. The task brief named the D.O. closing "आपला,"; all official specimens have "आपला स्नेहांकित," (GADT 12.27 + p.44, NPM p.97), so
   that is printed (with "शुभेच्छा", GADT only). Change only on Abhi's word.
2. GADT 12.27: D.O. letters are typed on printed designation stationery "(पदनाम राजमुद्रेसह)". No such template is in the repo, so
   no emblem / letterhead is printed. If the Section has the अवर सचिव's D.O. paper, it can be added as a template.
3. Number label: GADT "अ.शा.पत्र क्र." is used; NPM writes "अर्ध-शासकीय पत्र क्र." — both official.
4. Sender designation default "अवर सचिव." (from the desk signer post); GADT 12.28 says a D.O. letter goes to an officer of the
   same level. The addressee level is the user's choice per case (spec `to`, `salutation` "प्रिय महोदय," for a senior officer).
5. U.O. block: no official specimen of a note-foot U.O. block exists in MMOP 2023 or GADT; the NPM परिशिष्ट-8 form foot is the
   official Marathi wording used. The "कार्यासन" blank is filled with the desk profile value ("का.6"), giving "कार्यासन का.6";
   Abhi may prefer "कार्यासन-6" (spec `uo.desk`).
6. The year "१९ …" of the old forms is replaced by the full date blank.
7. `tests/test_engine_brief.py::test_size` fails on the base commit too (ENGINE_BRIEF.md 29436 > 28672 bytes); not touched here
   (ENGINE_BRIEF.md is outside this task).
