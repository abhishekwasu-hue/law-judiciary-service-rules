# Legislature instruments (संसदीय आयुधे) — research for draft builders

Prepared: 04.11.2026. Scope: what a Mantralaya department (Law & Judiciary Dept, Desk-6) must prepare for each
legislative device of the Maharashtra Legislative Assembly (विधानसभा) and Council (विधानपरिषद).
Rule followed: official sources only; quotations verbatim with source, page and para/rule; anything not found is
marked **not found**. No conclusions beyond what the sources state. Question-answer drafting itself is being built
separately (tools/build_lq.py); it is covered here only so the table is complete.

---

## 0. Sources used (all official)

| Key | Source | Where | Notes |
|---|---|---|---|
| **MLA-R** | Maharashtra Legislative Assembly Rules, Twelfth Edition 2024 (English), HB 1377 | https://mls.org.in/pdf/VdnMadlSmitya/rules-assembly/12th-edition-english.pdf | Searchable text. Cited as rule no. + printed page (2 printed pages per PDF page). Marathi 13th edition (https://mls.org.in/pdf/VdnMadlSmitya/rules-assembly/13th-edition-marathi.pdf) downloaded but uses a legacy (non-Unicode) font; not extracted. |
| **MLC-R** | Maharashtra Legislative Council Rules, Tenth Edition 2024 (English), Hb 1373 | https://mls.org.in/pdf/VdnMadlSmitya/D-15/11th-edition-2024/English%20rule%20book%202024.pdf | Searchable. Cited as rule no. + printed page. Marathi edition (…/Marathi%20Rule%20Book%202024.pdf) legacy font; not extracted. |
| **SPK-DIR** | "महाराष्ट्र विधानसभा नियमांन्वये अध्यक्षांनी दिलेले निदेश" — पुनरीक्षित निदेश क्र. १ | https://mls.org.in/PDF2023/WINTER/speaker-direction.pdf (2 pp., OCR) | Order of business; gives Marathi names with rule numbers. |
| **CHR-DIR** | "महाराष्ट्र विधानपरिषद नियमांन्वये सभापतींनी दिलेले निदेश" — पुनरीक्षित निदेश क्र. १ | https://mls.org.in/PDF2023/WINTER/Instructions-given-by-the-Speaker.pdf (1 p., OCR) | Same, Council. |
| **CA-874** | Published calling attention notice + Minister's statement, Assembly, notice no. ८७४ (2023 budget session) | https://mls.org.in/PDF2024/monsoon/PATRAKBHAG2/874.pdf (1 p., OCR) | Example of the Legislature Secretariat's published layout — not a prescribed specimen. |
| **PAD-2026** | संसदीय कार्य विभाग, शासन परिपत्रक क्र. विमंअ-०२२३/प्र.क्र.१७४/कार्यासन पाच, दि. १६.०१.२०२६, "विधानमंडळाचे कामकाज हाताळतांना घ्यावयाच्या दक्षतेबाबत सुचना" (20 pp.), संकेतांक 202601161259134815 | https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/202601161259134815.pdf | **Current master circular.** Supersedes GR एलईजी-१०९८/प्र.क्र.५१/९८/पाच दि. ०२.१२.१९९८. Text OCR'd; numbers checked against the PDF text layer. |
| PAD-1998 | GR एलईजी-१०९८/प्र.क्र.५१/९८/पांच, दि. २.१२.१९९८ (संकेतांक 20060429152818001) | gr.maharashtra.gov.in …/Marathi/20060429152818001.pdf | **Superseded** by PAD-2026 (PAD-2026, p.1). Cited only for history. |
| PAD-2016 | शासन परिपत्रक विसआ-2016/प्र.क्र.11/सहा, दि. 16.11.2016 (201611161522463715) — assurance compliance submission | gr.maharashtra.gov.in …/Marathi/201611161522463715.pdf | Text layer. |
| PAD-2025-SL | शासन परिपत्रक संकीर्ण-२०२५/प्र.क्र.१४२/तीन, दि. ०५.०९.२०२५ (202509051757419715) — subordinate legislation committee | gr.maharashtra.gov.in …/Marathi/202509051757419715.pdf | OCR. |
| PAD-2006 | शासन परिपत्रक विउसू-२००६/५२७/चार, दि. ५.४.२००६ (20100208180818001) — special mention replies | gr.maharashtra.gov.in …/Marathi/20100208180818001.pdf | OCR, poor scan. |
| **MMOP** | Maharashtra Manual of Office Procedures, 2023 (GAD), Chapter 16 | pdf/08-gad-office-procedure/GAD_Maharashtra-Office-Procedure-Manual-2023-English.pdf | Printed page = PDF page. Ch.16 = pp. 92–96. |
| **TIP** | GAD, "टिप्पणी लेखन व पत्रव्यवहार" — प्रकरण १३ "विधानसभा/परिषद प्रश्न व सूचना" | pdf/08-gad-office-procedure/GAD_Tippani-Lekhan-va-Patravyavahar-Marathi.pdf | OCR + page images viewed. Ch.13 = PDF pp. 54–57 (printed ५०–५३). Printer's line "एच ४३६४-६ (५,०३५-२-९३)"; edition date not found. Time limits in it are older than the current rules. |
| **NPM** | GAD, "कार्यालयीन कार्यपद्धती नियमपुस्तिका" — प्रकरण तेरा, परिशिष्ट ३५ | pdf/08-gad-office-procedure/GAD_Karyalayin-Karyapaddhati-Niyampustika-Marathi.pdf | OCR + image. Ch.13 = PDF pp. 57–60 (printed ४८–५१); App. 35 = PDF p.111 (printed १०४). |
| SAH / KAK | GAD, सहायक माहिती पुस्तिका / कक्ष अधिकारी माहिती पुस्तिका | pdf/08-gad-office-procedure/GAD_Sahayak-Mahiti-Pustika.pdf, GAD_Kaksha-Adhikari-Mahiti-Pustika.pdf | Fully OCR'd. Only incidental mentions (priority marking, select file); **no legislature specimen formats**. |

Not used: Lok Sabha / Rajya Sabha rules (not needed — every point below is covered by Maharashtra sources). Not
reachable: www.mahalegislature.org.in returned HTTP 403.

### Rule-number map (from the rule books and the Presiding Officers' directions)

| Instrument | Assembly (MLA-R) | Council (MLC-R) |
|---|---|---|
| तारांकित प्रश्न / Starred question | 72(1), 74, 76, 77 | 70(1), 72, 74, 75 |
| अतारांकित प्रश्न / Unstarred | 72(2) | 70(2) |
| अल्पसूचना प्रश्न / Short notice question | 86, 87 | 84, 85 |
| पुरवणी प्रश्न / Supplementary questions | 90 | 88 |
| अर्धा-तास चर्चा / Half-an-hour discussion | 94 | 92 |
| स्थगन (तहकूब) प्रस्ताव / Adjournment motion | 97–100 | — (no adjournment motion; see 93) |
| Motion to discuss matter of urgent public importance ("नियम ९३ अन्वये सूचना") | — | 93–96 |
| अल्पकालीन चर्चा / Short-duration discussion | 101–104 | 97–100 |
| लक्षवेधी सूचना / Calling attention | 105 | 101 |
| विशेष उल्लेख / Special mention | — (no such rule found in MLA-R) | 101-A to 101-F |
| ठराव (अशासकीय) / Private members' resolutions | 106–109 | 102–105 |
| शासकीय ठराव / Government resolutions | 110 | 106 |
| विधेयके / Bills (incl. private members') | 111–159 | 107–154 |
| मंत्र्यांचे निवेदन / Statement by Minister | 47 | 46 |
| औचित्याचा मुद्दा / Point of order | 50 | 49 |
| Last-week-of-session motion | 292 | 259 |
| Discussion on matter of (general public) interest | 293–298 | 260, 265 |
| Suspension of rules | 57 | 289 |
| Cut motions / कपात सूचना | 256 | — (demands are voted in the Assembly only) |
| Supplementary demands / पुरवणी मागण्या | 260 | 230 (supplementary statement of expenditure) |
| आश्वासन समिती / Assurances Committee | 226–228 | 220–222 |
| लोकलेखा / PAC | 206–207 | 207 (representation) |
| अंदाज / Estimates | 208–210 | 208 (representation) |
| अधीनस्थ विधान / Subordinate Legislation | 219–222 | 206 (representation) |
| पंचायत राज | 239–240 | 212 (representation) |
| अशासकीय विधेयके व ठराव समिती | 214–218 | 201–203 |

The "नियम 93 / 97 / 101 / 260 / 289" of the request map as follows: **93** = Council motion on urgent public
importance (MLC-R 93); **97** = Assembly adjournment motion (MLA-R 97) and Council short-duration discussion
(MLC-R 97; CHR-DIR item (सदतीस) "अल्पकालीन चर्चा.(म.वि.प.नियम ९७ अन्वये)"); **101** = Assembly short-duration
discussion (MLA-R 101), Council calling attention (MLC-R 101), Council special mention (101-A; CHR-DIR item (पंचवीस)
"विशेष उल्लेख सूचना (नियम १०१ अ)"); **260** = Council discussion on a matter of public interest (MLC-R 260) and
Assembly supplementary demands (MLA-R 260); **289** = Council suspension of rules (MLC-R 289).

---

## 1. General duties common to all devices

**PAD-2026, शासन परिपत्रक (p.1–2):** "महाराष्ट्र विधानमंडळ सचिवालयाकडून सदर संसदीय आयुधे संबंधित मंत्रालयीन
विभागांना संगणक प्रणाळीवरुन थेट ऑनलाईन पध्दतीने व ऑफलाईन पध्दतीने (छापील प्रतीद्वारे) त्वरित कार्यवाहीसाठी
पाठविण्यात येतात … मंत्रालयीन विभागांनी सदर प्रकरणी सर्वप्राथम्याने कार्यवाही करुन महाराष्ट्र विधानमंडळ
सचिवालयाने त्यांच्या पत्रात उल्लेख केल्याप्रमाणे विहीत नमुन्यात व मुदतीत सदर माहिती … उपलब्ध करुन देण्याची
दक्षता घेतली पाहिजे. … संसदीय आयुधांची उत्तरे निर्गमित करताना महाराष्ट्र विधानमंडळ सचिवालयानी त्यांच्या पत्रात
दिलेल्या सूचनेप्रमाणे त्यांनी नमूद केल्याप्रमाणे विहीत नमुन्यात व मुदतीत तसेच त्यांनी नमूद केलेल्या प्रतींच्या
संख्येत उत्तरे पाठविण्याची दक्षता मंत्रालयीन विभागांनी घ्यावी."

→ The binding format/time/copies for each device are those stated **in the Legislature Secretariat's covering letter
for that device**. Those letters are not in the repo — **not found** (open point O-1).

**MMOP 16.1 (p.92):** the Assembly/Council Rules "should be treated as final authorities. Details given below are
merely for general guidance".

**MMOP 16.12 (p.96)** — review fortnightly/monthly; e-Samiksha portal; general time limits: "a) Starred question:-
… within the time limit prescribed by Maharashtra State Legislature. b) Unstarred question:- … within 30 days from the
date of receipt. c) Cut-Motions:- … reply of Minister to the concerned Member … within 30 days. d) Assurances: - …
assurance fulfilling report in a prescribed form … within 90 days from the date of receipt."

**MMOP 10.3(1) (p.66):** "Communications meant for the Legislative Assembly and Council Mantralaya and requiring
urgent or high-level attention shall be addressed to the Secretaries concerned and not to the Speaker and Chairman
directly. Similarly, no communication is to be addressed to the Chairman of any Legislature Committee directly."

**Transfer of a device to another department:** PAD-2026 §2.3 (p.3), §12.6–12.8 (p.10–11), §16 (p.12–13) and
Annexure-1 (p.20, Instructions 54 and 54A under Rules of Business): decision at Secretary level; accept/reject within
15 days ("मंत्रालयीन विभागांनी हस्तांतरणाची नस्ती कोणत्याही परिस्थितीत पंधरा दिवसांपेक्षा जास्त विभागात
निर्णयाविना प्रलंबित ठेवू नये", §16.3); disputes to GAD (प्रशासकीय नाविन्यता, उत्कृष्टता आणि सुशासन) per GAD
circulars काकाप-१८१९/प्र.क्र.२४/१८ (र.व का.) dt. 20.05.2019 and 07.09.2019 (those two circulars: **not in repo**).

**Registers:** PAD-2026 §17.1–17.3 (p.13–14) — coordination cell keeps separate registers of pending assurances and
pending devices, updated on the 1st and 15th of every month. MMOP 21.3 (p.117) and 21.11 (p.120) — desk register of
LA/LC questions and of resolutions. Official column layout of the question register: **NPM परिशिष्ट-३५** (see §3).

**Select file:** MMOP 14.3(2) (p.87): "A separate select file should be maintained for data collected and
supplementary notes prepared in connection with Legislative Assembly/Council questions and resolutions, cut motions,
etc.,". File indexing: MMOP 7.x (p.37) "LAQ or LAR or LCQ or LCR".

**Priority marking:** SAH PDF p.26 / KAK PDF p.22 list "विधानसभा किंवा विधान परिषद प्रश्न किंवा ठराव" as a priority
category.

---

## 2. Instrument by instrument

### 2.1 तारांकित प्रश्न — Starred question
1. **Rule.** MLA-R 72(1) (p.30): "A member who desires an oral answer to his question shall distinguish it by an
   asterisk. Such a question is called a starred question." Notice: MLA-R 74 (p.30) "not less than 30 clear days'
   notice"; MLA-R 76 (p.31) not listed "until eighteen days have expired from the day when notice … was received by the
   Minister". Supplementaries: MLA-R 90 (p.36). Council: MLC-R 70(1), 72, 74 (p.26–27).
2. **What the department prepares / time.**
   - PAD-2026 §2.1 (p.2–3): "महाराष्ट्र विधानसभा नियम क्र.७२(१) व महाराष्ट्र विधानपरिषद नियम क्र.७०(१) मधील
     तरतुदीनुसार, मंत्रालयीन विभागांकडून तारांकित प्रश्नांची उत्तरे विधानमंडळ सचिवालयास विहीत मुदतीत म्हणजेच तीस
     दिवसात पाठविणे आवश्यक आहे. … नोटीसीमध्ये प्रती पाठविण्याचा अंतीम दिनांक व उत्तराचा दिनांक व उत्तराच्या
     प्रतींची संख्या नमूद केलेली असते."
   - PAD-2026 §2.2 (p.3): if not sent by the due date, "विधानसभेचा प्रश्न असेल तर ४५० प्रती व विधानपरिषदेचा प्रश्न
     असेल तर २५० प्रती विधानमंडळ सचिवालयास पाठविण्यात याव्यात."
   - MMOP 16.3(2) (p.93): "A full note describing the present position in respect of each clause of the question should
     be put up and at the end of each paragraph the answer proposed should be given. A separate draft answer, clause by
     clause, should also be put up in the correspondence section on the basis of the note."
   - MMOP 16.3(3) (p.93): "When the question is a starred question or a short notice question, additional information
     … likely to be useful to the Minister-in-charge … should also be given on a separate page under the heading "Notes
     for supplementary questions”." NPM ¶106 (PDF p.58, printed ४९) uses the Marathi heading "“ पुरवणी प्रश्नांकरिता
     टिप्पणी ”".
   - TIP ¶13.4 (PDF p.55, printed ५१): "उत्तर निर्गमित केल्यानंतर पूरक टिप्पणी तयार करून त्यांच्या प्रती मंत्री,
     राज्यमंत्री, उप सचिव व कार्यासन अधिकारी यांच्या टेबलावर उत्तराच्या दिवसाच्या २ दिवस अगोदर तयार ठेवणे जरूर आहे."
     (The same para's "१० दिवस अगोदर" and "४०० प्रती" are older figures; current figures are PAD-2026 above.)
   - MMOP 16.3(4) (p.93): after issue, main papers to the Minister's Private Secretary; a responsible officer present in
     the House.
3. **Official specimen.** **Found — TIP ¶13.9, PDF p.56–57 (printed ५२–५३)**, "(तारांकित प्रश्नाचा नमुना)", layout
   (verbatim headings, sample content abridged):
   ```
                         (तारांकित प्रश्नाचा नमुना)
                                                   उत्तराचा दिनांक
   राजुरा (जिल्हा चंद्रपूर, तालुका राजुरा) येथे ग्रामीण रुग्णालय मंजूर करण्याची मागणी      [subject line]
   तारांकित प्रश्न क्रमांक ५०४७३.                         श्री. भाई सावंत
   श्रीयुत ........... (राजुरा)                           सार्वजनिक आरोग्य मंत्री
   विधानसभा सदस्य.
   सन्माननीय सार्वजनिक आरोग्य मंत्री पुढील गोष्टींचा खुलासा करतील काय :—
   (१) <question clause> … हे खरे आहे काय ;          (१) होय.
   (२) असल्यास, त्याबाबत शासनाने काय कार्यवाही      (२) ही बाब शासनाच्या विचाराधीन
       केली वा करणार आहे ?                              आहे.
   ────────
                     क्रमांक <file no.>
                     <विभाग>
                     मंत्रालय, मुंबई ४०० ०३२
                     दिनांक :
   प्रत, १० प्रतींसह सचिव, महाराष्ट्र विधानमंडळ सचिवालय, विधानभवन, मुंबई यांजकडे त्यांच्या क्रमांक ____,
   दिनांक ____ च्या संदर्भात अग्रेषित.
                                                   (अ. व. कडई)
                                                   शासनाचे अवर सचिव.
   ```
   followed on a separate page by:
   ```
                               पुरवणी टिप्पणी
                    विधानसभा तारांकित प्रश्न क्रमांक ५०४७३
         “ राजुरा जिल्हा चंद्रपूर येथे ग्रामीण रुग्णालय मंजूर करण्यासंबंधी”
   <background facts, figures, list of facilities, policy, action in hand>
   ```
   (Question in left column, answer in right column, clause by clause.) TIP ¶13.2 (PDF p.55): "तारांकित प्रश्न व त्याचे
   उत्तर याचा एक विशिष्ट नमुना आहे व त्याच नमुन्यात उत्तर देणे जरूर असते, उत्तरामध्ये सभागृहात उत्तर देण्याचा दिनांक
   न चुकता नमूद करणे जरूर असते." MMOP 16.3(4): answer "in the form prescribed by Maharashtra Legislature" — that
   current Legislature form itself: **not found** (O-1).
4. **Approval chain.** MMOP 16.3(4) (p.93): "The note and draft reply should he submitted to the Minister-in-charge
   through the Secretary of the Department." Specimen endorsement signed by "शासनाचे अवर सचिव" (TIP p.57).
   Cross-department question: MMOP 4.1(3)(a)-(b) (p.23) — answered by the Minister-in-charge of the department to which
   the Secretary, Maharashtra Legislature sent it, after consulting the other Minister(s).

### 2.2 अतारांकित प्रश्न — Unstarred question
1. **Rule.** MLA-R 72(2) (p.30): "No oral answers to them shall be given … Unless the Speaker otherwise directs, such
   questions shall be answered within thirty days from the date of the receipt thereof by Government". MLC-R 70(2) (p.26)
   same.
2. **Prepare / time.** PAD-2026 §3.1 (p.3): replies "विहीत मुदतीत म्हणजेच तीस दिवसात"; §3.2 (p.3–4): if not possible,
   "विभागांनी विधानमंडळ सचिवालयाकडे योग्य समर्थनासह मुदतवाढीसाठी विनंती करावी". No supplementary note needed: TIP ¶13.5
   (PDF p.55): "त्यांवर सभागृहात उप प्रश्न विचारले जात नाहीत व त्यामुळे पूरक टिप्पणीचीही जरुरी नसते." (Its "३
   महिन्याच्या आत" is superseded by the rule's 30 days.)
3. **Specimen.** TIP ¶13.5: "अतारांकित प्रश्नांच्या उत्तराचा नमुना हा तारांकित प्रश्नाप्रमाणेच असतो." → same as 2.1.
4. **Approval.** As 2.1 (MMOP 16.3(4)).

### 2.3 अल्पसूचना प्रश्न — Short notice question
1. **Rule.** MLA-R 86 (p.34): notice "not be earlier than seven days prior to the commencement of the Session"; 86(3):
   if the Minister does not agree to an immediate reply "he shall state reasons to the Speaker"; 86(4): "Every Short
   Notice Question shall be answered within seven days from the date of its receipt by Government, if the requisite
   information is available within the limits of Greater Mumbai and within fourteen days from that date if it is
   required to be obtained from outside Greater Mumbai." MLC-R 84(4) (p.30) same (7/14 days, "Greater Bombay").
2. **Prepare.** As starred (MLA-R 86(3): "In other respects the procedure … shall be the same as for starred
   questions"); "Notes for supplementary questions" required (MMOP 16.3(3)).
3. **Specimen.** TIP ¶13.7 (PDF p.56): "याचे उत्तरही तारांकित प्रश्नाप्रमाणेच द्यावे लागते." → format 2.1. PAD-2026 has
   no separate para on short notice questions.
4. **Approval.** As 2.1.

**Preliminary reference (सूचना प्रश्न) before admission.** PAD-2026 §1.1–1.3 (p.2): the Secretariat may ask "अ)
प्रश्नाधिन बाबी राज्य शासनाशी संबंधित आहेत काय? ब) प्रश्न वस्तुस्थितीवर आधारलेला आहे काय? क) प्रश्नासंदर्भात
वस्तुस्थिती काय आहे ? वगैरे."; reply point-wise within the given time; §1.3 "मंत्रालयीन विभागांनी विधानमंडळ सचिवालयास
प्रश्न स्वीकृत / अस्वीकृत करण्याबाबत आपले अभिप्राय नमूद करु नयेत." TIP ¶13.6 (PDF p.55–56): "या चौकशीचे उत्तर दोन
दिवसात द्यावे लागते." Format: **not found** (Secretariat letter decides).

### 2.4 लक्षवेधी सूचना — Calling attention (MLA-R 105 / MLC-R 101)
1. **Rule.** MLA-R 105(1) (p.43): "A member may, with the previous permission of the Speaker, call the attention of a
   Minister to any matter of urgent public importance and the Minister may make a brief statement or ask for time to
   make a statement at a later hour or date." (2) no debate, a few questions may be permitted; (3) max three per
   sitting; proviso: pending matters on the last day — "the ministers concerned shall lay on the Table of the Assembly
   the statements to be made by them." MLC-R 101 (p.37): max four; 45 minutes; un-reached statements laid on the Table.
2. **Prepare / time.**
   - PAD-2026 §4.1 (p.4): "मंत्रालयीन विभागांनी लक्षवेधी सूचना प्राप्त झाल्यानंतर याबाबतचे निवेदन तयार करण्याची दक्षता
     घ्यावी व … निवेदनाच्या प्रती विहीत मुदतीत व विहीत संख्येत महाराष्ट्र विधानमंडळ सचिवालयास देण्याची व्यवस्था करावी."
   - §4.2: currently 700 copies (Assembly) / 250 copies (Council), but as stated in the notice.
   - §4.3: "लक्षवेधी सूचनेच्या निवेदनामध्ये "अशा परिस्थितीत सन्मानीय सभासदांनी उपस्थित केलेली लक्षवेधी सूचना संयुक्तिक
     वाटत नाही." अशा प्रकारचे अभिप्राय विभागांनी देऊ नयेत. तसेच अशा तऱ्हेचे आक्षेपार्ह अभिप्राय निवेदनात येणार नाहीत
     याबाबत खबरदारी घेण्यात यावी."
   - §4.4: un-discussed statements tabled on the last day, else within one week of prorogation; "सदर निवेदने महाराष्ट्र
     विधानमंडळ सचिवालयास पाठवितांना त्या निवेदनांना “लक्षवेधी सूचना निवेदन" असे शीर्षक देण्यात यावे."
   - §4.5 (p.5): no calling attention may remain pending after the session.
   - MMOP 16.10 (p.95): "A full note describing the present position … shall put up and additional information …
     shall also give on a separate note under the heading “supplementary notes for Calling Attention Matters”." Main
     papers to the Minister's PS; responsible officer present in the House.
3. **Specimen.** GAD specimen: **not found.** Prescribed elements found: title "लक्षवेधी सूचना निवेदन" (PAD-2026 §4.4);
   separate "supplementary notes for Calling Attention Matters" (MMOP 16.10). Published layout (CA-874, Legislature
   Secretariat publication — an example, not a prescribed form):
   ```
   महाराष्ट्र विधानसभा
   सन २०२३ चे प्रथम (अर्थसंकल्पिय) अधिवेशन लक्षवेधी
   महाराष्ट्र विधानमंडळ नियम १०५ अन्वये सूचना क्र. ८७४
   मा.श्री.<name>, वि.स.स यांनी महाराष्ट्र विधानसभा नियम १०५ अन्वये दिलेली लक्षवेधी सुचना खालील प्रमाणे आहे :-
   “<text of notice> … सदरबाबत तातडीने कार्यवाही होण्याची आवश्यकता इ.”
   मा. मंत्री, <विभाग> यांचे निवेदन
   <statement paragraphs: GRs with dates, figures, action taken>
   ```
4. **Approval.** MMOP 16.10: note to Minister-in-charge (via Secretary is stated for questions in 16.3(4); 16.10 does
   not repeat the chain — **not stated**). The statement is the Minister's ("मा. मंत्री, … यांचे निवेदन", CA-874).

### 2.5 अर्धा-तास चर्चा — Half-an-hour discussion (MLA-R 94 / MLC-R 92)
1. **Rule.** MLA-R 94 (p.37): Tuesday/Thursday (or other days); notice ≥3 days with explanatory note signed by two other
   members; 94(5) "There shall be no formal motion … The member who has given notice may make a short statement and the
   Minister concerned shall reply briefly." MLC-R 92 (p.32–33): Monday–Thursday, same procedure.
2. **Prepare / time.** PAD-2026 §10 (p.8–9): "मंत्रालयीन विभागांनी अर्धा तास चर्चा सभागृहात उपस्थित होण्याच्या आदल्या
   दिवशीच याबाबतचे उत्तर मंत्री महोदयांच्या मान्यतेसाठी सादर करावे. तसेच सदर उत्तराच्या प्रती महाराष्ट्र विधानमंडळ
   सचिवालयास त्यांनी सूचित केल्यानुसार सादर कराव्यात." TIP ¶13.8 (PDF p.56): "मंत्र्यांच्या वापरासाठी जरूर ते टाचण
   तयार करावे लागते."
3. **Specimen.** **Not found.**
4. **Approval.** Minister's approval (PAD-2026 §10).

### 2.6 औचित्याचा मुद्दा — Point of order / point of propriety
1. **Rule.** MLA-R 50 (p.24) / MLC-R 49 (p.20): "(1) The Speaker shall decide all points of order which may arise and his
   decision shall be final. (2) Any member may at any time submit a point of order for the decision of the Speaker but
   in doing so shall confine himself to stating the point. (3) No discussion on any point of order shall be allowed
   except with the consent of the Speaker."
2. **Prepare / time.** PAD-2026 §11 (p.9): the Secretariat sends the points to departments; "मंत्रालयीन विभागांनी
   महाराष्ट्र विधानमंडळ सचिवालयाने सुचित केल्यानुसार कार्यवाही करुन संबंधित सदस्यांना मंत्री स्तरावरुन तीस दिवसांच्या
   विहित मुदतीत कळविण्याची कार्यवाही करावी व विधानमंडळ सदस्यांना पाठविलेल्या उत्तराची प्रत महाराष्ट्र विधानमंडळ
   सचिवालयाला पाठविण्याची दक्षता घ्यावी."
3. **Specimen.** **Not found.**
4. **Approval / signature.** Reply "मंत्री स्तरावरुन" to the member; copy to the Secretariat.

### 2.7 विशेष उल्लेख — Special mention (Council only, MLC-R 101-A to 101-F)
1. **Rule.** MLC-R 101-A (p.38): after calling attention, a matter "of serious nature and urgent public importance";
   notice by 5 p.m. the previous day; 101-B conditions (≤250 words, one issue, documents attached …); 101-E Minister's
   reply 2 minutes; 101-F (p.39): "It shall be binding on the Minister to send to the concerned member a reply in
   writing in regard to the subject raised as a Special Mention within a period of Thirty days eventhough the Minister
   has given a reply immediately in that regard."
2. **Prepare / time.** PAD-2026 §9 (p.8): "मंत्रालयीन विभागांनी विशेष उल्लेख म्हणून मांडल्या गेलेल्या विषयाचे उत्तर
   मंत्री महोदयांच्या स्वाक्षरीने संबंधित विधानपरिषद सदस्यास तीस दिवसांच्या आंत पाठविण्याची दक्षता घ्यावी व सदर
   उत्तराची प्रत महाराष्ट्र विधानमंडळ सचिवालयास पाठवावी." (Also PAD-2006 para 1–2.)
3. **Specimen.** **Not found.**
4. **Signature.** Minister.

### 2.8 नियम ९७ स्थगन (तहकूब) प्रस्ताव (Assembly) and नियम ९३ सूचना (Council)
1. **Rule.** MLA-R 97 (p.40): "A Motion for an adjournment of the business of the Assembly for the purpose of discussing
   a definite matter of urgent public importance may be made with the consent of the Speaker." 98 restrictions; 99
   written statement one hour before sitting; 29 members to rise; debate 16-00 to 18-00 (99(3), 100).
   MLC-R 93(1) (p.34): written statement to the Secretary one hour before the sitting; **93(2):** "While pronouncing a
   decision on a notice of motion moved under the said rule, if such notice is rejected, the directions shall be issued
   to the Government to make a statement by considering the urgency and public importance of the subject matter raised
   in the notice. A statement on such a notice shall be made within 6 days on the floor of the House. After the copies
   of said statement are distributed, permission shall be granted to the concerned members to ask one or two
   supplementary questions … the period for discussion on such statements shall not exceed 20 minutes." Form of the
   motion, MLC-R 96(1) (p.35): "“ This House expresses its grave concern over the act of commission/omission of
   Government in the following matter of urgent public importance, namely :— .........................”"
2. **Prepare / time.** PAD-2026 §8.2(अ) (p.7): when the Speaker orders "संबंधित बाबींवर शासनाने निवेदन करावे" without a
   time limit, "तसे निवेदन, आदेश दिलेल्या दिवसापासून विनाविलंब करणे आवश्यक आहे"; if delay is unavoidable, the Minister
   brings it to the Speaker's notice and takes permission. §8.2(ब): before the statement day, "निवेदनाच्या प्रती संबंधित
   मंत्रीमहोदयांच्या अथवा राज्यमंत्र्यांच्या स्वाक्षरीने मा.अध्यक्षांना देण्यात याव्यात"; copies to the Secretariat as
   instructed; "त्या पत्राची एक प्रत निवेदनाच्या प्रतीसह मा.मंत्री, संसदीय कार्य यांच्या माहितीसाठी पाठविण्यात यावी."
   §8.3 (p.7–8): same for Council rule 93 (to the Chairman). §8.4 (p.8): follow the Secretariat's instructions.
3. **Specimen.** **Not found** (only the Council motion wording, which is the member's).
4. **Signature.** Minister / Minister of State signs the copies given to the Presiding Officer (§8.2(ब), §8.3(ब)).

### 2.9 अल्पकालीन चर्चा — Short-duration discussion (MLA-R 101–104 / MLC-R 97–100)
1. **Rule.** MLA-R 101 (p.42): notice with explanatory note, two other members' signatures; 102: Speaker may call for
   information "from the member … and from the Minister"; up to 2½ hours (Council 98: 3 hours); 103: "There shall be no
   formal motion … the Minister shall reply briefly."
2. **Prepare.** PAD-2026 lists "अल्पकालीन चर्चा" among devices (p.1) but has **no separate paragraph**; department output
   **not found** beyond the general duty (§1 above) and MMOP 16.13(2) (officer present with papers).
3. **Specimen.** **Not found.** 4. **Approval.** **Not found.**

### 2.10 नियम २६० (Council) / नियम २९३ (Assembly) — discussion on a matter of public interest; last-week motions; नियम २८९
1. **Rule.** MLC-R 260 (p.94): "Save in so far as is otherwise provided in the Constitution or in these rules, no
   discussion of a matter of general public interest shall take place except on a motion made with the consent of the
   Chairman." MLA-R 293 (p.126) same with "Speaker"; MLA-R 294 notice, max five motions per member per term. Last week of
   session: MLA-R 292 / MLC-R 259 — "The Speaker shall before admitting the notice, ascertain the views of the Minister,
   to whose Department the motion relates." MLC-R 289 (p.102): "Any member may, with the consent of the Chairman, move
   that any rule may be suspended in its application to a particular motion before the Council …".
2. **Prepare.** **Not found** in PAD-2026 / MMOP / TIP / NPM (only the general duties). MLA-R 292(2)/MLC-R 259(2) imply the
   Minister's views are sought before admission — the form of those views: **not found**.
3. **Specimen.** **Not found.** 4. **Approval.** **Not found.**

### 2.11 मंत्र्यांचे निवेदन — Statement by a Minister (MLA-R 47 / MLC-R 46)
1. **Rule.** MLA-R 47 (p.24): "With the permission of the Speaker, a Minister may make a statement on a matter of public
   importance. On such statement no discussion shall be allowed but members may be permitted to ask questions …".
2. **Prepare.** PAD-2026 §15 (p.12): a special statement made in one House "तेच निवेदन त्याच दिवशी संबंधित
   मंत्रीमहोदयांनी दुसऱ्याही सभागृहात केलं पाहिजे याची कृपया दक्षता घ्यावी."
3. **Specimen.** **Not found.** 4. **Approval.** **Not found** (statement is the Minister's).

### 2.12 अशासकीय ठराव व अशासकीय विधेयक — Private members' resolutions and Bills
1. **Rule.** Resolutions: MLA-R 106 (p.44) 15 clear days' notice, ballot; 107 (p.45) admissibility; MLC-R 102 (p.40) 12
   clear days. Bills: MLA-R 111 (p.46) notice with copy of Bill and Statement of Objects and Reasons, 15 days; MLC-R 107.
   Committee on Private Members' Bills and Resolutions: MLA-R 214–218, MLC-R 201–203.
2. **Prepare / time.**
   - MMOP 16.6 (p.94): "a detailed note giving the relevant information in respect of the subject-matter should be put up,
     along with previous papers and files duly marked, to the Minister-in-charge through the secretary of the
     department. At the end of the note, an indication should be given whether the resolution if moved should be
     accepted, with some modification or should be opposed." (NPM ¶109, PDF p.58–59, same in Marathi: "टिप्पणीच्या
     अखेरीस प्रस्ताव मांडण्यात आल्यानंतर तो त्यात काही फेरफार करून स्वीकारावा किंवा कसे की त्यास विरोध करावा, हे
     सूचित करावे.")
   - MMOP 16.8 (p.94–95) — Non-official Bills: "(1) The Parliamentary Affairs Department shall send the copy of the
     Non-official Bill received from the Maharashtra Legislature to the Law and Judiciary Department for examining the
     legal and constitutional feasibility of the Bill … (2) The Law and Judiciary Department shall examine the legal and
     constitutional feasibility of the Non-official Bill and shall send the opinion to the Parliamentary Affairs
     Department and copy to the concerned Mantralaya Department. (3) Parliamentary Affairs Department shall forward the
     opinion of the Law and Judiciary Department to the Maharashtra Legislature. (4) A detailed note … (6) The concerned
     Mantralaya Department shall prepare the Cabinet Note and place the proposal of Bill for Cabinet approval when the
     Bill is selected in Ballet for consideration. (7) The final decision on action to be taken by the Council of
     Ministers. (8) If the Bill requires the recommendation of the Governor under Article 207 …, the Parliamentary Affairs
     Department shall obtain the recommendation of the Governor."
   - PAD-2026 §7.1 (p.5–6): start action as soon as notice is received, without waiting for the ballot; take the
     Minister-in-charge's approval to the note for the Cabinet; "(नियमित मंत्रिमंडळ प्रस्तावाप्रमाणे अशासकीय कामकाजाच्या
     टिप्पणीस मंत्रिमंडळ सचिव/मुख्यमंत्री यांची मान्यता घेण्याची आवश्यकता नाही.)"; give approved notes to the Chief
     Secretary's office before the Cabinet meeting. §7.2 (p.6): private members' business usually Friday; ballot usually
     Wednesday; steps (अ)–(इ) — get the likely Friday business from the Secretariat every Wednesday evening, inform
     Minister/MoS/Secretary, give Cabinet-note copies to the Chief Secretary's office, check the Committee's report every
     Thursday before the Cabinet meeting.
3. **Specimen.** **Not found** (no specimen of the note, of L&J's feasibility opinion, or of the Cabinet note for
   private business).
4. **Approval.** Note → Secretary → Minister-in-charge (MMOP 16.6); final decision Council of Ministers (MMOP 16.8(7)).

### 2.13 शासकीय विधेयक व शासकीय ठराव — Government Bills and resolutions (department's role)
1. **Rule.** Government resolutions: MLA-R 110 / MLC-R 106 — seven days' notice. Bills: MLA-R 114 (p.47) "(2) A Bill,
   other than Private Member’s Bill, involving expenditure shall be accompanied by a financial memorandum …"; MLA-R 121
   (p.50) Governor's recommendation under Art. 207 stated by the Minister-in-charge.
2. **Prepare.**
   - MMOP 16.7 (p.94): administrative department prepares the draft Bill and the "Statement of Objects and Reasons",
     shows it to other departments and to Finance if financial implications; "(2) The draft Bill and the Statement of
     Objects and Reasons should be sent to the Law and Judiciary Department for scrutiny along with relevant files. …
     (3) After the Bill is approved by the Minister-in-charge, arrangements should be made to obtain approval of the
     Council of Ministers. After approval of the Council of Ministers to the Bill, the Department should send the file
     along with draft Bill with a copy of Cabinet decision to the Law and Judiciary Department for further action
     regarding introduction of Bill in the House." Also MMOP 15.4 (p.90) (L&J consulted on expediency, competence,
     President's sanction, constitutional consistency) and 15.5 (p.90–91) ("forward two copies of draft typed on half
     margin with double spacing").
   - PAD-2026 §6 (p.5): "सादर होणाऱ्या विधेयकांमध्ये समाविष्ट असलेल्या सुधारणेसंबंधात संपूर्ण माहिती असलेली स्वयंस्पष्ट
     टिप्पणी संबंधित विभागाच्या सचिवांनी संबंधित मा.मंत्री / राज्यमंत्री महोदयांना सभागृहातील चर्चेपूर्वी तयार करुन
     द्यावी आणि त्या टिप्पणीची प्रत मुख्यमंत्री कार्यालय तसेच संसदीय कार्य मंत्री यांच्या कार्यालयास पाठवावी."
   - Government resolution: MMOP 16.5 (p.93–94) — complete information in the note to the Minister-in-charge through the
     Secretary; flag papers as in para 14.3.
3. **Specimen.** **Not found** in the sources used (no specimen of the self-contained note on a Bill or of the Statement
   of Objects and Reasons).
4. **Approval.** Secretary → Minister-in-charge → Council of Ministers (MMOP 16.7). Whether Desk-6 handles Bills is not
   stated in any source used — **not found**.

### 2.14 आश्वासने व आश्वासन समिती — Assurances and the Committee on Government Assurances
1. **Rule.** MLA-R 226 (p.92): Committee "to scrutinize the assurances, promises and undertakings, given by Ministers …
   on the floor of the Assembly and to report on— (a) the extent to which such assurances, promises and undertakings have
   been implemented ; and (b) where implemented, whether such implementation has taken place within the minimum time
   necessary for the purpose." MLA-R 228 (p.93): "The Secretary of the Department concerned shall, if required by the
   Committee, attend meeting of the Committee … and shall supply such information as the Committee may desire." MLC-R
   220–222 (p.81) same.
2. **Prepare / time.**
   - PAD-2026 §12.1 (p.9): the Committee fixes assurances from the proceedings; sent to departments through PAD.
   - §12.2 (p.9): "त्या आश्वासनांची पूर्तता आश्वासन दिल्या दिवसापासून नव्वद दिवसांच्या आत करणे आवश्यक आहे"; start on the
     day the assurance is given, without waiting for PAD's letter.
   - §12.3 (p.10): if 90 days not possible, explain to the Committee and seek extension.
   - §12.4 (p.10): "आश्वासन पूर्ततेची कार्यवाही पूर्ण झाल्यावर, सदर माहिती आश्वासनाशी सुसंगत व परिपूर्ण असेल अशातऱ्हेने
     विहीत विवरणपत्रात सर्व रकान्यात पूर्ण भरावी. विवरणपत्रातील सर्व रकाने विशेषत: रकाना क्रमांक ७, ८, ९ व १० मधील
     माहिती निश्चितपणे आणि परिपूर्ण भरण्याची भरण्याची दक्षता घ्यावी."
   - §12.5 (p.10): "(विधानसभा आश्वासनाबाबतीत ३५ प्रतीत व विधानपरिषद आश्वासनाबाबतीत २५ प्रतीत) संसदीय कार्य विभागाकडे
     पाठवावी. पूर्ततेची माहिती पाठवितांना त्या संदर्भात काढलेले शासन निर्णय, परिपत्रक, आदेश इत्यादींच्या प्रती आश्वासन
     पूर्ततेच्या विवरणपत्रासोबत जोडणे आवश्यक आहे."
   - §12.9 (p.11) — exemption: "विभागाच्या मा.मंत्री अथवा राज्यमंत्री महोदयांच्या स्तरावरून पत्राद्वारे मा. समिती प्रमुख,
     आश्वासन समिती यांच्या निदर्शनास आणून द्यावी व सदर आश्वासन वगळण्याची विनंती मा. समिती प्रमुख, आश्वासन समिती यांना
     करावी."
   - §12.10 (p.11): Secretary to attend Committee meetings in person; §12.11 / §18 (p.11, 14): permanent "आश्वासन व अन्य
     संसदीय आयुधे पूर्तता समिती" under the Secretary, meeting every 15 days (PAD circular विपआ २०२३/प्र.क्र.४२/चार dt.
     10.10.2025); §12.12: special drive for assurances pending > 2 years; §13 (p.12): "अधिक माहिती पटलावर ठेवली जाईल"
     assurances — lay in the same session or on the first day of the next.
   - PAD-2016 para 2(ड)–(ए) (p.1–2): soft copy (PDF) file name pattern "“2015(1)1184SED”" [session year, session no.,
     assurance no., dept. abbreviation in capitals, no spaces]; columns 6–10 must be filled consistent with columns 4–5;
     "त्यामध्ये केवळ “निरंक”, “प्रश्न उद्भवत नाही”, “------” (नुसती रेघ) असे नमूद करू नये अन्यथा, अशी माहिती असलेली
     विवरणपत्रे स्विकारण्यात येणार नाहीत".
   - MMOP 16.11 (p.95–96): "send copies of assurance fulfilling report in a prescribed format to the Parliamentary
     Affairs Department"; 16.12(3)(d): within 90 days.
3. **Specimen.** The "विहीत विवरणपत्र" (assurance compliance statement, at least 10 columns) is referred to but its
   column headings were **not found** in any source used (PAD circular dt. 26.05.2016 referred to in PAD-2016 was not
   found on the GR site mirror search). Historical: PAD-1998 परिशिष्ट-३ "आश्वासनांच्या नमुन्यांची प्रमाण यादी" (standard
   list of expressions treated as assurances, e.g. "(१) ह्या बाबींवर विचार करण्यात येत आहे.", "(४) माननीय सदस्यांना मी
   कळवीन.") — PAD-1998 is superseded and PAD-2026 does not reproduce the list.
4. **Approval / signature.** Compliance statement goes through the department's coordination branch to PAD (PAD-2016
   2(ब)); exemption request at Minister/MoS level (PAD-2026 §12.9).

### 2.15 विधिमंडळ समित्या — Legislature Committees (PAC, Estimates, Subordinate Legislation, Panchayat Raj etc.)
1. **Rules.** General: MLA-R 178 (p.75) "A Committee shall have power to send for persons, papers and records : …
   Provided further that, Government may decline to produce a document on the ground that its disclosure would be
   prejudicial to the safety or interest of the State."; 184 (p.77) completed part of a report may be made available to
   Government, confidential until presented. PAC: MLA-R 206–207 (p.83–84). Estimates: 208–210 (p.85–86) — includes
   "(b) to scrutinise the demands for supplementary grants". Subordinate Legislation: 219–222 (p.90–91); 222: "The
   Secretary of the Department concerned shall attend meetings of the Committee to assist it in its deliberations and
   shall supply such information as the Committee may desire." Panchayat Raj: 239–240 (p.98).
2. **Prepare / time.**
   - Subordinate legislation — PAD-2025-SL para 1(अ)–(ड), 2 (p.2–3): after Gazette publication (draft or final),
     "सदर राजपत्राच्या ३० प्रती जोडपत्राच्या उताऱ्यासह आणि स्पष्टीकरणात्मक टिप्पणीच्या ३० प्रतीसह सचिव, उपविधान समिती,
     महाराष्ट्र विधानमंडळ सचिवालय यांना पाठवाव्यात."; para 3: rules under an Act generally within six months of the
     Act; para 4: an Under Secretary-level officer to be personally responsible.
   - PAD-2026 §22 (p.17): Secretaries to attend meetings called by Committee chairpersons and the Presiding Officers (PAD
     circular बैठक-२०२५/प्र.क्र.५४/कार्या चार dt. 09.12.2025 — not in repo).
   - Annual reports of undertakings/boards: PAD-2026 §14 (p.12) — lay immediately after the year; if delayed, send
     reasons for delay with the copies.
3. **Specimen.** Questionnaire replies / written memoranda / action-taken replies to PAC, Estimates, PR or other
   committees: **not found** in any source used. Format of the "स्पष्टीकरणात्मक टिप्पणी" for subordinate legislation:
   **not found**.
4. **Approval.** Secretary attends and supplies information (MLA-R 222, 228); otherwise **not found**.

### 2.16 पुरवणी मागण्या — Supplementary demands
1. **Rule.** MLA-R 260 (p.114): supplementary statement laid on a day appointed by the Governor; voting not earlier than
   three days after; "(3) The discussion of a supplementary grant shall be confined to the items constituting the grant
   and no discussion shall be permitted on the original grants or on the policy underlying those grants." MLC-R 230
   (p.83) supplementary statement in the Council.
2. **Prepare.** Department's preparation of supplementary demands (Finance Department procedure): **not found** in the
   sources used. What is found: cut motions on supplementary demands (2.17); Estimates Committee scrutiny (MLA-R 209(1)(b));
   notes on points raised in the general budget discussion — MMOP 16.13(1) (p.96): "Such notes are generally put up to the
   Minister in charge through Mantralaya of the department and copies are sent to Minister (Finance) for his information."
3. **Specimen.** **Not found.** 4. **Approval.** As MMOP 16.13(1) for discussion notes; otherwise **not found**.

### 2.17 कपात सूचना — Cut motions (MLA-R 256)
1. **Rule.** MLA-R 256 (p.113): "(1) During the voting of demands for grants, motions may be moved to reduce any grant
   or to omit or to reduce any item in a grant but not to increase or to alter the destination of the grant. (2) Notice
   of not more than ten motions for one Department shall be given four clear days before the demand to which they relate
   is made. … (4) A member giving notice of any motion under this rule shall also indicate the subject which he wishes to
   raise on such motion."
2. **Prepare / time.**
   - MMOP 16.9 (p.95): "they shall prepare notes containing relevant information which it is considered will be useful
     to the Minister-in-charge, when the cut-motions are actually moved in the House."
   - PAD-2026 §5.1 (p.5): "स्वीकृत कपात सूचनांना, संबंधित मंत्रालयीन विभागांनी त्यांच्या मंत्री महोदयांच्या सहीने संबंधित
     विधानमंडळ सदस्यांना तीस दिवसांच्या आत लेखी उत्तरे पाठविण्याची दक्षता घ्यावी. तसेच विधानमंडळ सदस्यांना पाठविलेल्या
     उत्तराची एक प्रत महाराष्ट्र विधानमंडळ सचिवालय व वित्त विभागास (अर्थ-३) यांना पाठविण्याची कार्यवाही करावी." §5.2:
     follow Finance Dept and Secretariat instructions (not in repo).
3. **Specimen.** **Not found.**
4. **Signature.** Minister signs the reply (PAD-2026 §5.1).

### 2.18 प्रश्नोत्तराच्या पुस्तिकेसाठी माहिती / टिप्पणी / संक्षिप्त टिपणी — briefing for the Minister; "Note for supplementaries"
- MMOP 16.3(3) (p.93): separate page "Notes for supplementary questions" (starred and short notice).
- NPM ¶106 (PDF p.58): Marathi heading "पुरवणी प्रश्नांकरिता टिप्पणी".
- TIP ¶13.2 (PDF p.54): "प्रश्नाचा रोख लक्षात घेऊन, विचारण्यात येतील अशा संभाव्य उप प्रश्नांचे अंदाज बांधून, संपूर्ण
  माहिती देणारी एक पूरक टिप्पणी तयार करावी लागते." Specimen heading "पुरवणी टिप्पणी" (TIP p.57, layout in §2.1).
- MMOP 16.10 (p.95): "supplementary notes for Calling Attention Matters".
- TIP ¶13.8 (PDF p.56): half-hour discussion "टाचण".
- PAD-2026 §6 (p.5): "स्वयंस्पष्ट टिप्पणी" for Bills.
- MMOP (p.21, Ch.2): the Minister's PS/OSD prepares "summary of previously asked/replied to starred questions and
  briefing the Minister/ MoS accordingly".
- A separate official "प्रश्नोत्तराची पुस्तिका" (question-answer booklet) format for the department: **not found**.

---

## 3. Other official formats found

**NPM परिशिष्ट-३५ "विधानसभा/विधान परिषद प्रश्नांची नोंदवही" (प्रकरण चौदा, परिच्छेद ११६)** — PDF p.111, printed
१०४ (image viewed). Columns verbatim:
| (१) अनुक्रमांक | (२) विधानसभा/ विधान परिषद प्रश्न क्रमांक | (३) विधानसभा/ विधान परिषद सदस्याचे नाव | (४) विषय | (५) मिळाल्याची तारीख | (६) फाईल क्रमांक | (७) अहवालासाठी बोलावल्याची तारीख | (८) स्मरणपत्र पाठवल्याची तारीख | (९) शासनाकडे सादर करण्यासाठी अहवाल मिळाल्याची आणि उत्तर पाठवल्याची तारीख | (१०) शेरा |
|---|---|---|---|---|---|---|---|---|---|

Resolutions register: MMOP 21.11 (p.120) "The register may be maintained in any form considered suitable." Assurance /
pending-device registers (PAD-2026 §17): columns **not prescribed** in the circular.

---

## 4. Summary table

| # | Instrument | Rule (MLA / MLC) | Department output | Time limit (source) | Signs / approves | Official format found? |
|---|---|---|---|---|---|---|
| 1 | तारांकित प्रश्न | 72(1) / 70(1) | Note (clause-wise, proposed answer per para) + draft answer + "Notes for supplementary questions" | 30 days (PAD-2026 §2.1); by date in notice | Note via Secretary to Minister (MMOP 16.3(4)); endorsement by Under Secretary (TIP specimen) | **Yes** — TIP ¶13.9 (answer, endorsement, पुरवणी टिप्पणी); current Legislature form: not found |
| 2 | अतारांकित प्रश्न | 72(2) / 70(2) | Answer | 30 days (MLA-R 72(2); PAD-2026 §3.1) | As 1 | **Yes** — same as starred (TIP ¶13.5) |
| 3 | अल्पसूचना प्रश्न | 86 / 84 | Answer + supplementary note | 7 / 14 days (MLA-R 86(4), MLC-R 84(4)) | As 1 | **Yes** — same as starred (TIP ¶13.7) |
| 3a | सूचना प्रश्न (pre-admission reference) | — | Point-wise facts; no admit/reject opinion | Secretariat's date (PAD-2026 §1.2); 2 days (TIP ¶13.6, old) | not found | No |
| 4 | लक्षवेधी सूचना | 105 / 101 | Statement (निवेदन) + note + "supplementary notes for Calling Attention Matters" | Secretariat's date; pending ones on last day / within 1 week (PAD-2026 §4.4) | Minister's statement | **Partial** — title "लक्षवेधी सूचना निवेदन" + content bar (PAD-2026 §4.3–4.4); published layout example CA-874 |
| 5 | अर्धा-तास चर्चा | 94 / 92 | Reply for Minister's approval | Day before (PAD-2026 §10) | Minister approves | No |
| 6 | औचित्याचा मुद्दा | 50 / 49 | Reply to member, copy to Secretariat | 30 days (PAD-2026 §11) | Minister level | No |
| 7 | विशेष उल्लेख | — / 101-A–F | Written reply to member, copy to Secretariat | 30 days (MLC-R 101-F; PAD-2026 §9) | Minister | No |
| 8 | स्थगन प्रस्ताव (९७) / नियम ९३ सूचना | 97 / 93 | Government statement when ordered | Without delay (PAD-2026 §8.2); within 6 days for Council 93(2) | Minister/MoS signs copies to Presiding Officer | No |
| 9 | अल्पकालीन चर्चा | 101 / 97 | not found | not found | not found | No |
| 10 | नियम २६० / २९३ / २९२ / २५९ / २८९ | 292–293 / 259–260, 289 | not found (Minister's views sought under 292(2)/259(2)) | not found | not found | No |
| 11 | मंत्र्यांचे निवेदन | 47 / 46 | Statement; same day in both Houses | same day (PAD-2026 §15) | Minister | No |
| 12 | अशासकीय ठराव | 106–109 / 102–105 | Detailed note ending with accept / modify / oppose; Cabinet note | On receipt, before ballot (PAD-2026 §7.1) | Secretary → Minister → Cabinet | **Structure only** (MMOP 16.6 ending) |
| 13 | अशासकीय विधेयक | 111 / 107 | L&J: legal & constitutional feasibility opinion to PAD; admin dept: note + Cabinet note | On receipt (PAD-2026 §7.1) | L&J → PAD → Legislature; Cabinet decides | No |
| 14 | शासकीय विधेयक / ठराव | 110, 111–159 / 106, 107–154 | Draft Bill + SOR (admin dept); L&J scrutiny; self-contained note for Minister before debate | not stated | Secretary → Minister → Cabinet; copy of note to CMO and Parl. Affairs Minister | No |
| 15 | आश्वासने | 226–228 / 220–222 | Compliance statement (विहित विवरणपत्र) with GR copies; exemption letter | 90 days (PAD-2026 §12.2; MMOP 16.12) | Coordination branch → PAD; exemption at Minister level | **Partial** — file-name rule, copies (35/25), columns 4–10 rules; column headings not found |
| 16 | विधिमंडळ समित्या | 178, 206–244 / 206–222 | Information/evidence; Secretary attends; SL: 30 copies Gazette + explanatory note | SL: immediately after publication (PAD-2025-SL) | Secretary | No |
| 17 | पुरवणी मागण्या | 260 / 230 | not found (budget-discussion notes: MMOP 16.13(1)) | not found | not found | No |
| 18 | कपात सूचना | 256 / — | Notes for Minister; written replies to members, copy to Secretariat & Finance (अर्थ-३) | 30 days (PAD-2026 §5.1; MMOP 16.12) | Minister signs replies | No |
| 19 | Note for supplementaries / पुरवणी टिप्पणी | — | Separate page | 2 days before answer day (TIP ¶13.4) | with the note to Minister | **Yes** — TIP p.57 heading block |
| 20 | Question register | — | Desk register | weekly / twice weekly scrutiny (MMOP 21.3) | Desk Officer | **Yes** — NPM परिशिष्ट-३५ |

---

## 5. Recommended draft types to build (only where an official format was found)

1. **Starred / unstarred / short-notice answer sheet** (TIP ¶13.9 layout: उत्तराचा दिनांक; subject line; question no.,
   member, constituency vs. Minister; "सन्माननीय … मंत्री पुढील गोष्टींचा खुलासा करतील काय :—"; two-column clauses;
   endorsement "प्रत, __ प्रतींसह सचिव, महाराष्ट्र विधानमंडळ सचिवालय … यांजकडे त्यांच्या क्रमांक __, दिनांक __ च्या
   संदर्भात अग्रेषित." signed शासनाचे अवर सचिव). → This is the scope of tools/build_lq.py; listed only for alignment.
2. **पुरवणी टिप्पणी / Notes for supplementary questions** (separate page: "पुरवणी टिप्पणी" / "विधानसभा तारांकित प्रश्न
   क्रमांक __" / "“<subject>”" / body) — TIP p.57; MMOP 16.3(3); NPM ¶106 heading "पुरवणी प्रश्नांकरिता टिप्पणी".
3. **Note to Minister on a question** (structure from MMOP 16.3(2)/NPM ¶106: full note, each clause's present position,
   proposed answer at the end of each paragraph; submitted through the Secretary). Structure only, no page specimen.
4. **Calling attention statement** — partial: title "लक्षवेधी सूचना निवेदन" (PAD-2026 §4.4), content bar (§4.3), plus a
   separate "supplementary notes for Calling Attention Matters" (MMOP 16.10). Body layout only from the published CA-874
   example — build only if Abhi accepts that example as the model (O-2).
5. **Legislature question register** (NPM परिशिष्ट-३५, 10 columns).

Not recommended until a format is obtained: assurance compliance statement, cut-motion / special-mention / point-of-order
reply letters, adjournment/rule-93 statements, private-member resolution/Bill notes, committee replies, L&J feasibility
opinion on non-official Bills.

---

## 6. Open points (log; provisional default in brackets)

- **O-1** Legislature Secretariat's covering-letter formats (question answer form, copies, calling-attention notice) are
  binding (PAD-2026 p.2) but none are in the repo. [Default: ask Abhi for one recent letter of each device received by
  Desk-6; until then use the TIP specimen.]
- **O-2** Calling-attention statement body: no GAD specimen; only the Secretariat's published example. [Default: do not
  build beyond title + note + supplementary note.]
- **O-3** Assurance compliance statement (विहित विवरणपत्र) column headings — PAD circular dt. 26.05.2016 (विसआ-2016/प्र.क्र.11/सहा)
  not found. [Default: ask Abhi for a blank statement from the coordination branch.]
- **O-4** GAD circulars काकाप-१८१९/प्र.क्र.२४/१८ (र.व का.) dt. 20.05.2019 and 07.09.2019 (transfer of devices); PAD circulars
  विपआ-२०२३/प्र.क्र.३९/चार dt. 21.06.2023, विपआ २०२३/प्र.क्र.४२/चार dt. 10.10.2025 (GR code 202510101733094515 downloaded,
  not quoted here), बैठक-२०२५/प्र.क्र.५४ dt. 09.12.2025 — not in repo / not read in full.
- **O-5** Which of these devices Desk-6 actually handles (questions on court-staff service matters are certain from the
  project context; Bills / non-official Bill opinions are handled by L&J under MMOP 16.7–16.8 but the desk is not stated).
  [Default: build question drafts first.]
- **O-6** Marathi rule books (13th MLA / Council 2024 Marathi) are in a legacy font; Marathi rule titles above come from
  PAD-2026 and the Presiding Officers' directions, not from the Marathi rule books.
- **O-7** TIP and NPM time limits (10 days before answer, 3 months for unstarred, 30/400 copies) are older than MLA-R/MLC-R
  and PAD-2026; use PAD-2026 and the rules for time limits.
