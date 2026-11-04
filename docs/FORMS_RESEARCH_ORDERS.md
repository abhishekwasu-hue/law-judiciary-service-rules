# FORMS_RESEARCH_ORDERS — पृष्ठांकन / कार्यालयीन आदेश / प्रसिद्धीपत्रक / शासन पूरकपत्र (04.11.2026)

Task: four more order types in `tools/build_order.py` / `tools/lint_order.py` ("endorsement", "office_order", "press_note",
"addendum"). Rule: formats only from official GoM sources; every layout element traced to a specimen (page). One stored file
for this research (OWNER_RULES A.11). The five older types: docs/COURT_AND_ORDERS_RESEARCH.md (B1-B10), unchanged.

## 0. Sources and how they were read
| Short | File (repo `pdf/08-gad-office-procedure/`) | Page mapping | How read |
|---|---|---|---|
| NPM | GAD_Karyalayin-Karyapaddhati-Niyampustika-Marathi.pdf (कार्यालयीन कार्यपद्धतीची नियमपुस्तिका) | PDF 55-56 = printed 46-47 (para 102); PDF 101-105 = printed 94-98 (परिशिष्ट 26-32) | text layer garbled: pages rendered at 200 dpi, `tesseract -l mar+eng`, every specimen line checked on the page image |
| GADT | GAD_Tippani-Lekhan-va-Patravyavahar-Marathi.pdf (टिप्पणी लेखन व पत्रव्यवहार) | printed page = PDF page - 4 | same (OCR + images) |
| MMOP | GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf | 10.1 text PDF pp.64-65; App. 10.8 p.75, 10.10 p.77, 10.11 p.78 | text layer (/tmp/claude-0/ref/mmop.txt) |
| LJ-A1 | L&J "शासन निर्णय पूरकपत्र" क्र. सवमु-1521/1246/प्र.क्र.121/का.8, 17.01.2023, code 202301181508556412 | pp.1-3 | official mirror archive.org `in.gov.maharashtra.gr.<code>`; page images read |
| LJ-A2 | L&J "शासन निर्णय पूरकपत्र" क्र. सवअ-1319/1488/प्र.क्र.58/19/का.8, 21.10.2022, code 202210211643272612 | pp.1-3 | same |
| LJ-A3 | L&J "शासन पूरक पत्र" क्र. एचसीटी-5225/329/प्र.क्र.25 (भाग-1)/का.4, 24.12.2025, code 202512241441162012 | pp.1-2 | same |
| FD-A | Finance "पुरकपत्र" क्र. आप्रयो-1014/प्र.क्र.21/सेवा-3, 10.02.2015, code 201502101737353205 | pp.1-2 | same |

The four live addenda were downloaded only to the session scratch (not added to `pdf/gr/`; see open point 5).

NPM para 102 (PDF p.55-56, printed 46-47) lists the forms: "(६) पृष्ठांकन", "(१०) कार्यालयीन आदेश", "(११) प्रसिद्धी पत्रक"; GADT
प्रकरण 12 list (PDF p.34) the same ("कार्यालयीन आदेश", "पृष्ठांकन", "प्रसिद्धिपत्रक").

---

## 1. endorsement — पृष्ठांकन
**Use (verbatim).** NPM 102(6) (PDF p.55, printed 46): "पृष्ठांकनाचा नमुना परिशिष्ट २७ मध्ये दिला आहे. भारत सरकार, इतर राज्य
शासन किंवा राज्यातील इतर सरकारी अधिकारी यांच्याकडून आलेल्या पत्रांच्या प्रती सरकारी अधिकाऱ्यांना पाठवावयाच्या असतात त्यावेळी
हा नमुना वापरतात. … " माहितीसाठी ", " माहिती व मार्गदर्शन यांसाठी " किंवा यथास्थिती " आवश्यक कार्यवाहीसाठी " प्रती पाठवावयाच्या
असतात तेव्हा अशा पृष्ठांकनाचा वापर करतात." MMOP 10.1(5) (PDF p.64): "This form is used while copies of communications
received from Government of India, other State Government, or other Government officers in the State, are to be sent to
Government officers." GADT 12.23 (PDF p.45, printed 41): "दुसऱ्या प्रकारच्या पृष्ठांकनाचा वापर … प्रती माहितीसाठी किंवा आवश्यक
कार्यवाहीसाठी पाठविण्याकरिता केला जातो, यात सही शेवटी असते. याही पृष्ठांकनाची भाषा तृतीय पुरुषी असते."

**Specimen — NPM परिशिष्ट-27 "शासकीय पृष्ठांकनाचा नमुना" (PDF p.101, printed 94), line by line:**
```
(भारत सरकार, ………… मंत्रालय, नवी दिल्ली याच्या ………… या संबंधीच्या पत्र क्रमांक ………… दिनांक ………… या खाली.)
                                   क्रमांक …………
                                   ………… विभाग,
                                   मंत्रालय, मुंबई. …………
………… यांजकडे माहितीसाठी/आवश्यक कार्यवाहीसाठी/अभिप्रायासाठी अथवा निकालात काढण्यासाठी पाठविण्यात येत आहे.
                      महाराष्ट्राचे राज्यपाल यांच्या आदेशानुसार व नावाने,
                                        अ. ब. क.
                              अवर सचिव, महाराष्ट्र शासन,
                                   ………… विभाग.
```
MMOP App. 10.8 (PDF p.75) is the same form in English ("(Below copy of Government of India, Ministry of …'s letter No. …
dated the … and its accompaniments regarding … ] / No. … / … Department, / Mantralaya, Mumbai / Forwarded for
information/necessary action/remarks or disposal etc. to … / By order, etc. / A. B. C. / Under Secretary to the Government
of Maharashtra, / … Department."). GADT 12.24 / 12.25 (PDF pp.45-46): "(सामान्य प्रशासन विभागाच्या क्रमांक … दिनांक … च्या …
परिपत्रकाची प्रत)" / "क्रमांक : …, / महसूल व वन विभाग / मंत्रालय, मुंबई ४०० ०३२, दिनांक" / "महसूल व वन विभागातील सर्व उप सचिव,
विभागीय अधिकारी, अवर सचिव, कार्यासन अधिकारी यांना माहितीसाठी व उचित कार्यवाहीसाठी अग्रेषित." / "अवर सचिव, महाराष्ट्र शासन.";
GADT 12.22 (first kind, PDF p.45): after the endorsement line "याबाबत अर्जदारास उत्तर परस्पर देण्यात यावे."

**Layout decision (build_endorsement).**
| Element | Printed | Trace |
|---|---|---|
| first line | "(" + `forwarded` + " या खाली.)" | NPM परि.-27 line 1 |
| number block, right | "क्रमांक :- <ref_no>" / department / address / "दिनांक :- <date>" (left-aligned at 7 cm) | NPM परि.-27 lines 2-4 (date after "मंत्रालय, मुंबई."); "क्रमांक :-" / "दिनांक :-" form = the repo's other orders |
| no "महाराष्ट्र शासन" masthead, no subject, no वाचा | — | none in NPM परि.-27, MMOP 10.8, GADT 12.24/12.25 |
| forwarding sentence | "\t<forward_to> यांजकडे <purpose> पाठविण्यात येत आहे." | NPM परि.-27 verbatim; several recipients joined "अ, ब व क" (GADT 12.24 list form) |
| extra lines (optional `operative`) | unnumbered paragraphs | GADT 12.22 ("याबाबत अर्जदारास उत्तर परस्पर देण्यात यावे.") |
| authentication | Governor line + signer (desk default अवर सचिव) | NPM परि.-27; MMOP 10.8 "By order, etc." |
| प्रत list | only if `copies` given ("प्रत,"; last = निवड नस्ती) | not in the specimens; the Section's own file-copy practice (every Desk-6 order sample ends with निवड नस्ती) |
Lint: `forwarded` (bare text — no brackets / "या खाली"), `forward_to`, `purpose` ending "…साठी" (the specimen's options
माहितीसाठी / आवश्यक कार्यवाहीसाठी / अभिप्रायासाठी / निकालात काढण्यासाठी; NPM 102(6) "माहिती व मार्गदर्शन यांसाठी"), ref_no,
date required; website line refused (none in the specimen).

---

## 2. office_order — कार्यालयीन आदेश
**Use (verbatim).** NPM 102(10) (PDF p.56, printed 47): "कार्यालयीन आदेशाचा नमुना परिशिष्ट ३१ मध्ये दिला आहे. या नमुन्याचा वापर फार
मर्यादित आहे. एखाद्या सरकारी कार्यालयातील कर्मचाऱ्यांना एखादा निर्णय अंतर्गतरीत्या कळवण्यासाठीच केवळ या नमुन्याचा वापर करतात."
GADT 12.16 (PDF pp.41-42, printed 37-38): "कार्यालयाच्या अंतर्गत कामकाजाविषयी म्हणजे नेमणुका, ज्येष्ठता सूची, अंतर्गत पदोन्नती, विषय
सूची, कामाची विभागणी वगैरे बाबीतील सूचना आदेश किंवा निर्णय … कळविण्यासाठी कार्यालयीन आदेश काढले जातात. … त्यामुळे मंत्रालयीन
विभागांनीसुद्धा हे आदेश राज्यपालांच्या नावे काढण्याची जरुरी नाही. कार्यालयीन आदेशाचा विषय ज्ञापनाप्रमाणे शिरोभागी लिहून ज्यांना
हे आदेश अग्रेषित करावयाचे त्यांची नांवे शेवटी खाली लिहितात." MMOP 10.1(8) (PDF p.65): "… Therefore, there is, no salutation
or subscription. Copies are endorsed to all the persons/authority concerned."

**Specimen — NPM परिशिष्ट-31 "कार्यालयीन आदेशाचा नमुना" (PDF p.104, printed 97):**
```
                     महाराष्ट्र शासन,
                     ………… विभाग,
                     मंत्रालय, मुंबई, दिनांक …………
                     कार्यालयीन आदेश
     क्रमांक …………, सचिवांनी, ………… विभागातील ………… कार्यासनांमध्ये
कार्यवाही केली जाणाऱ्या विषयांच्या सूचीमध्ये पुढील फेरबद्दल करण्यास मान्यता दिली आहे.
                                              आदेशानुसार,
                                              अ. ब. क.
                                   अवर सचिव, महाराष्ट्र शासन,
                                              ………… विभाग.
```
GADT specimen (PDF pp.42-43, printed 38-39): subject "कामाचे विवरण पत्र सहायकांनी ठेवण्याबाबत" on top right; "कार्यालयीन आदेश /
क्रमांक ६४५/डीआएस १०८०/का ? / सार्वजनिक बांधकाम विभाग / मंत्रालय, मुंबई ४०० ०३२ / दिनांक"; paras unnumbered, "२.", "३.", "४.";
"अवर सचिव, महाराष्ट्र शासन."; then "सार्वजनिक बांधकाम विभागातील सर्व कार्यासन अधिकारी आणि शाखा प्रमुख यांना योग्य त्या
अंमलबजावणीसाठी." / "सर्व पर्यवेक्षक अधिकाऱ्यांना माहितीसाठी." MMOP App. 10.10 (PDF p.77): "Office Order, / No. … The Secretary
has approved the following modification in the list of subjects dealt with by desks in the … Department … / By order, /
Under Secretary to the Government of Maharashtra, / … Department."

**Layout decision (build_office_order).**
| Element | Printed | Trace |
|---|---|---|
| subject, centred bold on top | `subject` | GADT 12.16 "विषय ज्ञापनाप्रमाणे शिरोभागी" (memo subject centred, GADT 12.14) |
| masthead | "महाराष्ट्र शासन" / department / address / "दिनांक :- …" (no number line) | NPM परि.-31 |
| heading | "कार्यालयीन आदेश" centred bold | NPM परि.-31, GADT specimen |
| para 1 | "\tक्रमांक :- <ref_no>, <operative[0]>" | NPM परि.-31 ("क्रमांक …, सचिवांनी, …"); same handling as the अधिसूचना number |
| paras 2., 3. … | numbered; tables allowed | GADT specimen "२.", "३.", "४." |
| sign-off | "आदेशानुसार," + signer (no Governor line) | NPM परि.-31; MMOP 10.10 "By order,"; GADT 12.16 |
| recipients | `copies`, one paragraph each, no heading; last = निवड नस्ती | GADT specimen (lines "… यांना योग्य त्या अंमलबजावणीसाठी."); MMOP "Copies are endorsed" |
Lint: subject, ref_no, date, operative, copies required; operative may not contain a salutation / subscription ("महोदय",
"महोदया", "आपला,", "आपला विश्वासू") nor the tool lines ("आदेशानुसार,", "कार्यालयीन आदेश", Governor line); website line refused.

---

## 3. press_note — प्रसिद्धीपत्रक
**Use (verbatim).** NPM 102(11) (PDF p.56, printed 47): "प्रसिद्धीपत्रकाचा नमुना परिशिष्ट ३२ मध्ये दिला आहे. जेव्हा शासनाचा एखादा
महत्त्वाचा निर्णय जनतेला कळवायचा असेल त्यावेळी वृत्तपत्रांकरिता प्रसिद्धीपत्रक काढण्यात येते. प्रसिद्धीपत्रकाची शब्दयोजना अत्यंत
काळजीपूर्वक केली पाहिजे आणि जो निर्णय कळवायचा असेल तो निर्णय संक्षिप्त परंतु स्पष्ट शब्दांमध्ये नमूद केलेला असावा. शासकीय
अधिसूचना काढून केलेल्या नियमात काही औपचारिक सुधारणांचा निर्देश प्रसिद्धी पत्रकात करण्यात येतो. त्यावेळी त्या प्रसिद्धी पत्रकात
अशी अधिसूचना निर्गमित केल्याचा संदर्भ न चुकता नमूद करावा." MMOP 10.1(9) (PDF p.65) same in English ("… a reference to the
issue of such a notification should invariably be given in the press-note"). GADT 12.30 (PDF p.48, printed 44):
"प्रसिद्धिपत्रके ही माहिती व जनसंपर्क महासंचालनालयाकडून तयार करून वर्तमानपत्रांकडे प्रसिद्धीस देण्यात देतात. … संबंधित उप
सचिवांनी प्रसिद्धिपत्रक योग्य प्रकारे काढून घेणे जरूर असते." (GADT heading spells "प्रसिद्धिपत्रक"; NPM "प्रसिद्धीपत्रक" — the
tool uses the NPM spelling.)

**Specimen — NPM परिशिष्ट-32 "प्रसिद्धीपत्रकाचा नमुना" (PDF p.105, printed 98):**
```
                              प्रसिद्धीपत्रक
                                 पी-५०५
वैशाख ९, १८८०
एप्रिल २९, १९५८
                                                     दुपारी २-३० वाजता.
                          ग्रामपंचायत निवडणूक नियम
     मुंबई ग्रामपंचायत निवडणूक अधिनियम, १९४८ यात नियम ३६ हा नवीन नियम समाविष्ट करून सुधारणा करण्यात आली आहे. …
```
MMOP App. 10.11 (PDF p.78): "PRESS NOTE / P-505 / Vaishakh 9, 1880 (2-30 p.m. / April 29, 1958) / VILLAGE PANCHAYATS
ELECTION RULES / The Bombay Village Panchayats Elections Rules, 1948, have been amended introducing a new Rule 36. …".
No signature, no department line, no copy list in either specimen.

**Layout decision (build_press_note).**
| Element | Printed | Trace |
|---|---|---|
| heading | "प्रसिद्धीपत्रक" centred bold | परि.-32 |
| number | `number` centred (default "____"; sample "पी-____") | परि.-32 "पी-५०५" (number given by DGIPR) |
| Saka date / date | `saka_date` (default "____") / `date`, left | परि.-32 "वैशाख ९, १८८०" / "एप्रिल २९, १९५८" |
| release time | `time`, right (default "____ वाजता.") | परि.-32 "दुपारी २-३० वाजता." |
| title | `subject`, centred bold | परि.-32 "ग्रामपंचायत निवडणूक नियम" |
| text | `operative`, unnumbered paragraphs | परि.-32 |
| GR / notification reference | `cites`; each must also appear in the text | NPM 102(11), MMOP 10.1(9) |
| no masthead / signer / प्रत | — | परि.-32, App. 10.11 |
Lint: subject, date ("<month> DD, YYYY" as in the specimen, or the repo form), operative, cites (each quoted in operative)
required; ref_no not used; a प्रत list is refused; signer / ref_no / read … warn "not printed".

---

## 4. addendum — शासन पूरकपत्र
**Rule (verbatim).** GADT 12.9 (PDF p.37, printed 33): "शासन निर्णयामध्ये दुरुस्ती किंवा फेरफार करावयाचे झाल्यास शुद्धिपत्र
(Corrigendum), किंवा पूरकपत्र (Addendum) या स्वरूपात शासन निर्णयाच्या मसुद्याप्रमाणेच आदेश काढतात." No separate specimen in GADT,
NPM or MMOP (as for the शुद्धिपत्रक, COURT_AND_ORDERS_RESEARCH R4 §2) — so the GR specimen (NPM परि.-25; repo type "gr") is the form.

**Live official addenda (structure observed; page images read).**
- LJ-A1 (17.01.2023) p.1: subject top right ("शासन निर्णय पूरकपत्र / …देण्याबाबत."); "महाराष्ट्र शासन / विधि व न्याय विभाग /
  शासन निर्णय पूरकपत्र क्र. सवमु-1521/1246/प्र.क्र.121/का.8 / मादाम कामा मार्ग, हुतात्मा राजगुरु चौक, / मंत्रालय, मुंबई ४०० ०३२, /
  दिनांक : १७ जानेवारी, २०२३"; "संदर्भ:" list; "प्रस्तावना :-" ending "… पूरकपत्र निर्गमित करण्याची बाब शासनाच्या विचाराधीन होती."
  p.2: "शासन निर्णय पूरकपत्र:-"; para 2 "मूळ अट … "…" याऐवजी "…", याप्रमाणे सुधारित करण्यात येत आहे."; para 3
  "संदर्भ क्र. ८ येथे नमूद मूळ शासन निर्णयातील उर्वरित तरतुदी आहे तशाच लागू राहतील."
- LJ-A2 (21.10.2022) p.2: "शासन निर्णय पूरकपत्र :-"; last para "२. संदर्भ क्र. ४ येथे नमूद समक्रमांक दि. १३.१२.२०२१ रोजीच्या शासन
  निर्णयातील अटी व शर्ती आहे तशाच लागू राहतील ."
- LJ-A3 (24.12.2025) p.1: "शासन पूरक पत्र: एचसीटी-…/का.४"; "संदर्भ -"; "प्रस्तावना –"; "शासन पूरक पत्र –"; "सदर शासन पुरकपत्र
  महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात आला असून त्याचा संकेताक … असा आहे. हा आदेश डिजिटल
  स्वाक्षरीने साक्षांकित करुन काढण्यात येत आहे."; "महाराष्ट्राचे राज्यपाल यांच्या आदेशानुसार व नावाने."; signer; "प्रत," 1-13 ending
  "निवड नस्ती.".
- FD-A (10.02.2015) pp.1-2: "पुरकपत्र क्रमांकः आप्रयो-…"; "वाचा"; "प्रस्तावना-" ending "… पुढीलप्रमाणे पूरकपत्र निर्गमित करण्यांत
  येत आहे."; "पूरकपत्र:-"; numbered paras; "सदर पूरकपत्र महाराष्ट्र शासनाच्या www.maharashtra.gov.in या संकेतस्थळावर उपलब्ध करण्यात
  आला असून … हे पूरकपत्र डिजीटल स्वाक्षरीने साक्षांकित करुन काढण्यात येत आहे."; Governor line; signer; "प्रत,".

**Layout decision (build_into, type "addendum") — the corrigendum path with additions.**
| Element | Printed | Trace |
|---|---|---|
| subject, masthead | as GR: subject / "महाराष्ट्र शासन" / department / "शासन पूरकपत्र क्रमांक :- <ref_no>" / address / दिनांक | GADT 12.9; LJ-A1..A3, FD-A p.1. Label "शासन पूरकपत्र" = GADT spelling "पूरकपत्र" + "शासन" as in "शासन शुद्धिपत्रक" and LJ-A3 |
| वाचा | `read` (required) | GR specimen; FD-A "वाचा", LJ "संदर्भ" |
| प्रस्तावना :- | `preamble` (optional) | LJ-A1..A3, FD-A |
| heading | "शासन पूरकपत्र :-" | LJ-A1/A2 "शासन निर्णय पूरकपत्र :-", LJ-A3 "शासन पूरक पत्र –", FD-A "पूरकपत्र:-" |
| each addition | "\t<at> खालील मजकूर समाविष्ट करण्यात येत आहे:-" / "\t“<text>”" | mirrors the corrigendum's "<read> “…” असे नमूद … / या ऐवजी / “…” असे वाचावे." (repo, R4 §2 live L&J शुद्धिपत्रक); verb "समाविष्ट करून" = NPM परि.-32 text; ":-" form §4.19. **No official addendum uses a fixed insertion formula** (all four are free text) — this line is the Section's composed wording from official words; see open point 1 |
| para 2 | "संदर्भाधीन शासन निर्णयातील उर्वरित तरतुदी आहे तशाच लागू राहतील." (skipped if an operative para already says "लागू राहतील" / "कायम राहतील") | LJ-A1 para 3 verbatim, "संदर्भ क्र. ८ येथे नमूद मूळ" -> "संदर्भाधीन" |
| operative, concurrence | numbered 3., 4. … | GR specimen para 3 (NPM परि.-25) |
| website line | "सदर शासन पूरकपत्र … उपलब्ध करण्यात आले असून त्याचा संकेतांक ____ असा आहे. हे शासन पूरकपत्र डिजिटल स्वाक्षरीने साक्षांकित करून काढण्यात येत आहे." (default on) | LJ-A3, FD-A; decision B5 wording; neuter "आले / हे" for "पत्र" (FD-A has "आला … हे") |
| authentication, प्रत | Governor line + signer; "प्रत," list ending निवड नस्ती | LJ-A3, FD-A |
Lint: subject, ref_no, date, read, additions [{at, text}] (text without “…” — the tool adds them), copies required; website
line may not be switched off; "शासन पूरकपत्र :-" refused in operative; the own-text language rules (lint_spec) run on
`additions.at` and `additions.text`.

---

## 5. Common changes
- `tools/build_order.py`: TYPES + NUMBER_LABEL / BODY_HEAD / COPIES_HEAD / WEBSITE for the new types; `build_endorsement`,
  `build_office_order`, `build_press_note`; addendum branch in `build_into`; the five older types untouched (heading_block
  skips the number line also for office_order; preamble also for addendum). Font DVOT-SurekhMR on every run (all text goes
  through `Doc.p` -> `setfont`); metadata through `clean_docx` as before.
- `tools/lint_order.py`: per-type required keys; tool-added lines refused in operative (for the new types also a whole line
  "कार्यालयीन आदेश" / "प्रसिद्धीपत्रक" / "आदेशानुसार" / "अधिसूचना" and "या खाली.)"); WARN `NOT_PRINTED` for keys a specimen
  has no place for; C27 draft-word and §4.18-§4.25 language checks also on the new own-text keys.
- `tools/lint_spec.py`: the note's last para may name "पृष्ठांकनाचे / प्रसिद्धीपत्रकाचे / पूरकपत्राचे प्रारूप" (and
  "कार्यालयीन आदेशाचे" via "आदेशाचे"); `ORDER_NAMES` for the §4.28 "every draft named" warning.
- Samples `samples/specs/ORDER_{endorsement,office_order,press_note,addendum}_example.json` (Desk-6 themes, "____").
- Tests `tests/test_build_order.py` (build, layout, font, metadata, lint errors / warnings, §4.28 "orders" list).

## 6. Open points (provisional defaults in use; for Abhi / the lead)
1. **Addendum insertion line** "<at> खालील मजकूर समाविष्ट करण्यात येत आहे:-" is composed (no official fixed formula; live
   addenda are free text). Alternative: put the whole addition as free `operative` text (also accepted). Default: keep.
2. **Addendum label**: L&J itself uses "शासन निर्णय पूरकपत्र" (का.8, 2022/2023) and "शासन पूरक पत्र" (का.4, 2025); default
   "शासन पूरकपत्र" (GADT spelling). Finance 2015 spells "पुरकपत्र" (not linted).
3. **Endorsement wording** "यांजकडे" is the NPM परि.-27 word; GADT 12.25 uses "यांच्याकडे … अग्रेषित". Default: NPM.
4. **Engine wiring** (not in this task's files): `tools/engine_supabase.py` DRAFT_KEYS / ORDER_KEYS / ORDER_HEAD,
   the app's "कोणते मसुदे हवेत?" options, INSTRUCTIONS §4.28 / PROPOSAL_SOP Step 4b / ENGINE_BRIEF do not list the four new
   types yet. ORDER_HEAD for the new types = build_order.BODY_HEAD (endorsement has no body heading: detect by "या खाली.)").
5. The four live addenda (codes above) are not stored in `pdf/gr/` (+INDEX.tsv); add them if the Section wants the
   evidence in the repo.
6. Endorsement / press note: no प्रत list in the specimens — endorsement prints one only when `copies` is given; press note
   refuses it. Press-note number / Saka date / release time are DGIPR details, left "____".
