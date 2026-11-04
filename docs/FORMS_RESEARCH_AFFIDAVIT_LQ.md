# FORMS_RESEARCH_AFFIDAVIT_LQ — शपथपत्र (affidavit in reply) व विधानमंडळ प्रश्नाचे उत्तर: sources, layout, open points

Research date: 04.11.2026. Official sources and the Section's own drafts only (INSTRUCTIONS §1.3). Every printed element of
`tools/build_affidavit.py` and `tools/build_lq.py` is listed below with its source and page. Party / member names of the
sources are not copied (synthetic samples use "____").

Tools: `tools/build_affidavit.py` + `tools/lint_affidavit.py` (spec key `affidavit`, output `<PREFIX>_Affidavit.docx`);
`tools/build_lq.py` + `tools/lint_lq.py` (spec key `lq`, output `<PREFIX>_LQ_Answer.docx`). Both lints are called by
`tools/lint_spec.py` (EXTRA_LINTS); the note's last para may name "शपथपत्राचे प्रारूप" / "उत्तराचे प्रारूप" (lint_spec
ORDER_DRAFT_KINDS, drafts_unnamed). Samples: `samples/specs/COURT_affidavit_example.json`, `samples/specs/LQ_answer_example.json`.
Tests: `tests/test_build_affidavit.py`, `tests/test_build_lq.py`.

---

## A. Affidavit in reply (शपथपत्र) — Writ Petition, Bombay High Court

### A1. Sources

| # | Source | File / URL | Pages used |
|---|---|---|---|
| ASR3 | Bombay High Court Appellate Side Rules, 1960, Ch. III "Affidavits" (as updated 23.12.2025) | `pdf/07-court-litigation/BHC_Appellate-Side-Rules-1960_Ch03_Affidavits.pdf` (bombayhighcourt.gov.in → Rules & Manuals → Appellate Side, BHCASRules03.pdf) | p.1 Rules 1-5; p.2 Rules 5-9; p.3 Rule 10 form |
| ASR17 | Same Rules, Ch. XVII "Petitions under Articles 226 and 227 …" | `pdf/07-court-litigation/BHC_Appellate-Side-Rules-1960_Ch17_Writ-Petitions.pdf` (BHCASRules17.pdf) | p.7 Rule 10(i)-(ii); p.8 Rules 11, 12 |
| OS | Bombay High Court Original Side Rules, Ch. XII (Rules 191-194) and Forms 21, 102 | bombayhighcourt.gov.in/bhc/libweb/bhcrule/OSRules/ (ch12.pdf p.1; forms/No.21.pdf, No.102.pdf — scanned, read as images) | supporting only (Original Side) |
| CPC | Code of Civil Procedure, 1908, First Schedule, Appendix E, Form No. 16-A (L&J reprint) | `pdf/law-judiciary/acts-courts-litigation/Act_V_of_1908_CPC_L_and_J_reprint_binary_unreadable_by_tool.pdf` | PDF p.526 (printed 511) |
| RCLAG | Rules for the Conduct of the Legal Affairs of Government, 1984, Rules 32, 58 | already in `docs/COURT_AND_ORDERS_RESEARCH.md` R2 §B | Rule 58(6)(a), (e) |
| MMOP | Maharashtra Manual of Office Procedures, 2023 (English) | `pdf/08-gad-office-procedure/GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf` | PDF p.19 §3.3, p.20 §3.5 |
| SEC | The Section's own drafts: parawise remarks + note + letter to the GP in two Writ Petitions (2025, 2026) | given by Abhi (not in the repo; names not copied) | whole files read with python-docx |

### A2. Verbatim lines used

- **ASR3 Rule 1 (p.1)** "Every affidavit to be used in the High Court shall be entitled as follows : AT BOMBAY: "In the High Court of
  Judicature, Appellate Side, Bombay." AT NAGPUR: "In the High Court of Judicature, Bombay, at Nagpur" AT AURANGABAD: "In the High
  Court of Judicature, Bombay, at Aurangabad" AT GOA: "In the High Court of Judicature, Bombay, at Panaji, Goa." … AT KOLHAPUR: "In the
  High Court of Judicature, Bombay, Circuit Bench at Kolhapur"." → `bench` key, first line of the cause title.
- **ASR3 Rule 2 (p.1)** "An affidavit relating to a proceeding pending in this Court shall be entitled "in the matter of (state the
  proceeding and its number)" and shall set out the names and descriptions of the parties." → line "In the matter of WRIT PETITION NO.
  ____ OF 2026"; petitioners / respondents with descriptions; "… Petitioners", "Versus", "… Respondents".
- **ASR3 Rule 4 (p.1)** "Every affidavit containing any statement of facts shall be divided into paragraphs, and every paragraph shall
  be numbered consecutively and, as nearly as may be, shall be confined to a distinct portion of the subject." → paragraphs 1, 2, …
  run through the authority para, the preliminary paras, every parawise reply and the prayer.
- **ASR3 Rule 5 (pp.1-2)** "The declarant shall state what paragraphs or portions of his affidavit he swears or solemnly affirms to from
  his own knowledge and what paragraphs or portions he swears or solemnly affirms to on his own belief, stating the grounds of such
  belief." → `knowledge_paras`, `sources`, `belief_reasons`.
- **ASR3 Rule 8 (p.2)** identity of the declarant "known to the Officer personally or identified before him by a person whom he personally
  knows" → `identified_by` in the officer's block.
- **ASR3 Rule 10 (p.3)** form, printed exactly: "I .......... the Appellant/Respondent, Applicant/Opponent abovenamed do solemnly
  declare that what is stated above in paragraph is true to my own knowledge and that what is stated in the remaining paragraphs is
  true to the best of my information which I obtained from the following sources:— / I believe the information to be true for the
  following reasons :— / Solemnly declare at.......... above said this .......... day of.........20 / (Signature) / Before me, /
  Assistant Registrar, / Solemnly affirmed before me / by / who is identified before me / by / whom I personally known. / This day of 20
  / High Court, Appellate Side, Bombay. / Assistant Registrar."
- **ASR17 Rule 10(i) (p.7)** "Paper-books … shall include the petition … affidavits in support of the petition …, counter affidavits
  and affidavits in reply …"; **Rule 10(ii)** "… with double space between lines and use superior quality A4 size paper … Font – Times
  New Roman or Georgia, Font size 14 with inner margin of 5 cms and outer margin 3 cms. Every tenth line shall be numbered in the
  margin. The paper-book … shall be properly indexed and neatly bound with pages numbered consecutively."
- **ASR17 Rule 11 (p.8)** "An answer to rule nisi showing cause against such application shall be made by filing at least two days before
  the returnable date of the rule an affidavit in the office of the Registrar …"; **Rule 12** "… filing of the affidavit in reply …"
  → title "AFFIDAVIT IN REPLY ON BEHALF OF <RESPONDENT NOS. …>".
- **CPC Form 16-A (PDF p.526)** "I ………… of ………… on oath / solemn affirmation state as follows :— 1. My full name is …" → opening sentence
  "I, ____, … do hereby state on solemn affirmation as under:-" (un-numbered, as in the form; the numbered paragraphs follow).
- **OS Rules 193-194 (ch12.pdf p.1)** "Every affidavit shall be drawn up in the first person." "The occupation, nationality and the place
  of abode of every person making an affidavit shall be inserted therein." → "working as <designation>, <office>".
- **OS Form 102 (scanned)** "Sworn / Solemnly affirmed at … this … day of … 19 . Before me, Assistant, Master/Associate, High Court,
  Bombay. Advocate for ……" and **OS Form 21** "Solemnly affirmed at Bombay The … day of … 19 ." → line "Advocate for <respondents>".
- **RCLAG Rule 58(6)(a)** "The Government Pleader … shall then draft a counter affidavit"; **58(6)(e)** "The draft counter affidavit shall
  then be sworn in by the competent officer authorised to do so by the administrative department". **MMOP §3.3 (PDF p.19)** "Joint
  Secretary/ Deputy Secretary can also sign Orders, Financial Sanctions and affirm affidavits in High courts/ Supreme Courts."
  → default authority paragraph "I am working as … and I am the competent officer authorised to affirm this affidavit on behalf of …".
- **SEC (parawise drafts)** labels "Para No.1", "Para No.5 (a) to (e)", "Para No.21 to 24", "Ground (a)", "Prayer Clauses (a) to (h)"; a
  "Grounds" separator row; "Parawise submissions on behalf of Respondent Nos. 1 and 2 i.e. the State of Maharashtra, through the
  Principal Secretary, Law and Judiciary Department, Mantralaya, Mumbai …"; prayer row "Prayer Clause is denied. The petition is devoid
  of merits and liable to be dismissed. Hence, it is prayed that the same may be dismissed." (WP of 2025) → default prayer paragraph
  "The Petition is devoid of merits and liable to be dismissed. Hence, it is prayed that the same may be dismissed."
- **SEC (note and letter to the GP)**: the affidavit is "प्रतिवादी क्र.1 व 2 यांचे एकत्रित शपथपत्र", drafted on the basis of the parawise
  remarks ("सदर परिच्छेदनिहाय अभिप्रायांच्या अनुषंगाने … एकत्रित शपथपत्राचे प्रारुप तयार करुन शासन मान्यतेसाठी सादर करण्यात यावे") and
  the State's stand "सदर याचिका फेटाळण्यात यावी" → when `affidavit.reply` is absent the spec's `parawise.paras` remarks are used.
  The Section's drafts contain **no affidavit text** (the GP drafts it — RCLAG 58(6)(a)); so the affidavit's frame comes from ASR/CPC.

### A3. Layout decisions
1. A4; left (inner) margin 5 cm, right (outer) 3 cm; line spacing double; font size 14; footer page number; line numbers every 10th
   line (`w:lnNumType countBy=10`, continuous) — ASR17 Rule 10(ii). `"paper_book": false` removes the line numbers.
2. Font DVOT-SurekhMR on all four rFonts of every run (INSTRUCTIONS §4.2, lead's instruction) — see open point O1.
3. Cause title lines and the declaration block at 1.0-1.5 spacing so the Rule 10 right-hand block stays together (keep-with-next).
4. Rule 10 em dashes ":—" are written ":-" (INSTRUCTIONS §4.27 (उ): no "—" in drafts). "whom I personally known" of the printed rule is
   written "whom I personally know" (see O4).
5. Declarant in the Rule 10 sentence = "the Deponent abovenamed" (the officer is not himself the Respondent; "deponent" is the term of
   CPC s.139 / OS Form 102) — see O3.
6. Age: printed "aged about <age> years" only when `deponent.age` is given (lead's instruction; no official form requires the age —
   OS Rule 194 asks occupation, nationality, abode) — see O2.

### A4. Open points (provisional default in brackets)
- **O1** Font: ASR17 Rule 10(ii) names Times New Roman / Georgia for paper-books; repo rule §4.2 says DVOT-SurekhMR [DVOT-SurekhMR, size 14].
- **O2** "aged about … years" has no official source found; nationality (OS Rule 194) not printed [age printed only when given; no nationality].
- **O3** Rule 10 reads "the Appellant/Respondent … abovenamed"; the deponent signs for the State [“the Deponent abovenamed”].
- **O4** Rule 10 printed text "whom I personally known" (typo in the official PDF) [printed "know"].
- **O5** No Desk-6 affidavit specimen exists (R1 of COURT_AND_ORDERS_RESEARCH; the two drafts given are parawise only). One filed
  affidavit of the Section, if Abhi gives it, would settle wording such as the authority paragraph [default from RCLAG 58(6)(e)/MMOP 3.3].
- **O6** Benches other than Bombay: the officer's place line under the jurat is formed from the Rule 1 bench text (e.g. "High Court, Bombay,
  at Aurangabad."); the Rule 10 form shows only "High Court, Appellate Side, Bombay." [as built].

---

## B. विधानमंडळ प्रश्नाचे उत्तर (Legislative Assembly / Council question)

### B1. Sources

| # | Source | File / URL | Pages used |
|---|---|---|---|
| GADT | सा.प्र.वि., "टिप्पणी लेखन व पत्रव्यवहार", प्रकरण 13 "विधानसभा/परिषद प्रश्न व सूचना" | `pdf/08-gad-office-procedure/GAD_Tippani-Lekhan-va-Patravyavahar-Marathi.pdf` (legacy font → rendered at 220 dpi, OCR mar+eng, page images read) | PDF p.54-57 (printed 50-53); specimen 13.9 on PDF p.56-57 |
| KKN | सा.प्र.वि., "कार्यालयीन कार्यपद्धती नियमपुस्तिका" (Marathi), प्रकरण तेरा, परि. 104-107 | `pdf/08-gad-office-procedure/GAD_Karyalayin-Karyapaddhati-Niyampustika-Marathi.pdf` (OCR + page image) | PDF p.57-58 (printed 48-49) |
| MMOP | Maharashtra Manual of Office Procedures, 2023, Ch. 16 | `pdf/08-gad-office-procedure/GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf` | PDF p.92-93 §16.3-16.4; p.96 §16.12 |
| MLS | महाराष्ट्र विधानसभा, "तारांकित प्रश्नोत्तरांची यादी" (23.06.2026) and "अतारांकित प्रश्नोत्तरांची ३८ वी यादी" (2026) | mls.org.in/PDF2026/monsoon/Yadi/23-ASSEMBLY.pdf; mls.org.in/unstarred list/monsoon-session-2026/unstarred_question_yaadi_38.pdf (not stored: members' names) | pp.1-2 each (images read) |

### B2. Verbatim lines used
- **GADT 13.2 (PDF p.55, printed 51)** "तारांकित प्रश्न व त्याचे उत्तर याचा एक विशिष्ट नमुना आहे व त्याच नमुन्यात उत्तर देणे जरूर असते. उत्तरामध्ये
  अगदी वर सभागृहात उत्तर देण्याचा दिनांक न चुकता नमूद करणे जरूर असते." → first line "उत्तराचा दिनांक : …" (right).
- **GADT 13.4 (p.55)** "एका ठराविक नमुन्यातच उत्तर टंकलिखित करून सभागृहातील उत्तराच्या दिनांकाच्या १० दिवस अगोदर पाठवावे लागते. … उत्तर निर्गमित
  केल्यानंतर पूरक टिप्पणी तयार करून …".
- **GADT 13.5 (p.55)** "अतारांकित प्रश्नांना उत्तरे लेखी देतात … त्यामुळे पूरक टिप्पणीचीही जरुरी नसते. … अतारांकित प्रश्नांच्या उत्तराचा नमुना हा तारांकित
  प्रश्नाप्रमाणेच असतो." → unstarred: same form, no पुरवणी टिप्पणी (lint WARN if given).
- **GADT 13.7 (p.56)** short notice: "… याचे उत्तरही तारांकित प्रश्नाप्रमाणेच द्यावे लागते." → same form + पुरवणी टिप्पणी.
- **GADT 13.9 specimen (PDF p.56-57, printed 52-53)** "(तारांकित प्रश्नाचा नमुना) / उत्तराचा दिनांक / <subject, bold, between rules> /
  तारांकित प्रश्न क्रमांक ५०४७३. श्रीयुत ………… (राजुरा) विधानसभा सदस्य. | श्री. ………… <portfolio> मंत्री / सन्माननीय <portfolio> मंत्री पुढील गोष्टींचा
  खुलासा करतील काय :— / (१) … हे खरे आहे काय ; | (१) होय. / (२) असल्यास, त्याबाबत शासनाने काय कार्यवाही केली वा करणार आहे ? | (२) ही बाब
  शासनाच्या विचाराधीन आहे. / ——— / क्रमांक …… / <विभाग> / मंत्रालय, मुंबई ४०० ०३२ / दिनांक : / प्रत, १० प्रतींसह सचिव, महाराष्ट्र विधानमंडळ
  सचिवालय, विधानभवन, मुंबई यांजकडे त्यांच्या क्रमांक ……, दिनांक ……… च्या संदर्भात अग्रेषित. / (अ. ब. ……) / शासनाचे अवर सचिव. /
  पुरवणी टिप्पणी / विधानसभा तारांकित प्रश्न क्रमांक ५०४७३ / “ <subject>संबंधी ” / <supplementary facts, lists>".
  → this is the page layout of `<PREFIX>_LQ_Answer.docx` (two-column question | answer table, endorsement, signature, new page पुरवणी टिप्पणी).
- **KKN परि. 106 (PDF p.58, printed 49)** "प्रश्नाच्या प्रत्येक खंडाच्या संबंधातील विद्यमान परिस्थितीचे वर्णन करणारी संपूर्ण टिप्पणी प्रस्तुत करण्यात यावी ; आणि
  प्रत्येक परिच्छेदाच्या शेवटी प्रस्तावित उत्तर देण्यात यावे. तसेच या टिप्पणीच्या आधारे, प्रत्येक खंडाचे उत्तर प्रस्तुत करणारा उत्तरांचा एक स्वतंत्र मसुदा
  पत्रव्यवहार विभागामध्ये प्रस्तुत करण्यात यावा. (जेव्हा प्रश्न तारांकित किंवा अल्प मुदतीच्या सूचनेचा असेल तेव्हा … जादा माहिती देखील “ पुरवणी
  प्रश्नांकरिता टिप्पणी ” या शीर्षाखाली एका स्वतंत्र पानावर देण्यात यावी.) अशी टिप्पणी व उत्तराचा मसुदा विभागाच्या सचिवामार्फत प्रभारी मंत्र्यास सादर करावा.
  … महाराष्ट्र विधानमंडळ सचिवालयाने विहित केलेल्या नमून्यामध्ये प्रश्न व उत्तर यांच्या तीस प्रती …" → the sample note: one para per
  खंड ending "प्रस्तावित उत्तर : …"; `supplementary_heading` option.
- **MMOP §16.3(2)-(4) (PDF p.92-93)** "A full note describing the present position in respect of each clause of the question should be put up
  and at the end of each paragraph the answer proposed should be given. A separate draft answer, clause by clause …"; "(3) … on a separate
  page under the heading "Notes for supplementary questions""; "(4) … answer in the form prescribed by Maharashtra Legislature should be sent
  to Maharashtra Legislature officially, by quoting reference to its previous letter." **§16.12(3)(b) (p.96)** unstarred: "within 30 days".
- **MLS lists (2026)** opening "सन्माननीय मुख्यमंत्री पुढील गोष्टींचा खुलासा करतील काय :-"; sub-questions "(१) …, हे खरे आहे काय, (२) असल्यास, …, हे
  ही खरे आहे काय, … (५) नसल्यास, विलंबाची कारणे काय आहेत ?"; answers "(१) व (२) होय, हे खरे आहे.", "(३) हे खरे नाही.", "(१) व (२) हे अंशत: खरे
  आहे.", "(५) प्रश्न उद्भवत नाही."; starred entries "(१) * ३७७०४ <members> :", unstarred "(१) ४८ (२७-०४-२०२५). <members> :" and the answer line
  "श्री. <Minister> (१५-०४-२०२६) : …". → the answer forms checked by `lint_lq` (WARN) and the joint-answer form "(१) व (२) …".

### B3. Layout decisions
1. A4, margins as the Section's parawise office format (L 1800 / R 1440 twips); DVOT-SurekhMR 12 pt.
2. Clause numbers in Devanagari digits "(१)", "(२)" as in both specimens; the user's text is printed as written.
3. ":—" of the 1993 specimen is ":-" (the 2026 MLS lists print ":-"; INSTRUCTIONS §4.27 (उ)).
4. पुरवणी टिप्पणी on a new page, heading "पुरवणी टिप्पणी" (GADT specimen); printed only when `supplementary` is given; lint warns when a starred /
   short-notice answer has none, and when an unstarred one has one.
5. The file's note (टिप्पणी) is the usual note built by `tools/build_note_letter.py` (signer chain §4.6, last para "सबब, … प्रश्न क्रमांक ____ च्या उत्तराचे
   प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर.").

### B4. Open points (provisional default in brackets)
- **Q1** Number of copies with the answer: GADT specimen "१० प्रतींसह" (13.4: 400 copies if late), KKN 106/107 "तीस प्रती" [`copies` "____" — the
  Section fills the number the Legislature Secretariat now prescribes].
- **Q2** Signature: specimen "शासनाचे अवर सचिव." vs the Section's letters "( राजेश वडनेरकर ) / अवर सचिव ,महाराष्ट्र शासन" (§4.5) [specimen form;
  `signer` / `designation` overridable].
- **Q3** Supplementary page heading "पुरवणी टिप्पणी" (GADT) vs "पुरवणी प्रश्नांकरिता टिप्पणी" (KKN 106) [GADT; `supplementary_heading`].
- **Q4** The note goes to the Minister-in-charge through the Secretary (KKN 106, MMOP 16.3(4)); the note's signer chain still follows §4.6
  (lint_spec) [§4.6 chain; Abhi to say whether the LQ note needs extra signers].
- **Q5** The current Legislature Secretariat prescribed form (KKN "विहित केलेल्या नमून्यामध्ये") was not available from mls.org.in; the GADT
  specimen (1993) is used [GADT specimen].
- **Q6** The Section has no stored LQ answer of its own; one past answer of Desk-6 would confirm the endorsement line and file-number form.

## C. Pre-existing test failure (not part of this work)
`tests/test_engine_brief.py::test_size` fails on main before and after this change (tools/ENGINE_BRIEF.md 29436 bytes > 28672); the brief was
not edited (out of scope).
