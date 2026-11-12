# PROPOSAL_SOP.md — step-by-step procedure for every proposal (binding; any model, any session)

Owner: Abhi, Section Officer (कार्यासन अधिकारी), Law & Judiciary Department, Desk-6 (कार्यासन-6), Govt of Maharashtra.
When he sends a proposal PDF, do ALL steps below without asking. He must never have to explain this again.
The rules are in INSTRUCTIONS.md §4 (items 1–42); this file is the order of work + the tools. If anything here conflicts with
INSTRUCTIONS.md, INSTRUCTIONS.md wins. Reply to him in Marathi, few words.

The quality standard = the approved notes in `samples/specs/` (C R 66, 122, 128, 130, 131, 133 of 2026). Match them.

---

## Step 0 — Before starting
1. Read OWNER_RULES.md, INSTRUCTIONS.md, this file. Several proposals in one message = separate cases; never mix them.
2. Make a task list (one task per proposal).
3. Commands: on Windows run the tools with `py`, in the runner / Linux with `python3` (same arguments; 01.11.2026 सुसंगती).
4. Tools needed: `pip install pymupdf docxcompose python-docx --break-system-packages`; `soffice` (LibreOffice) and `tesseract` are used for checking/OCR.
5. Build the old-case text corpus once per session: `python3 tools/oldcases_text.py /tmp/old` (grep `/tmp/old/index.tsv`).
6. Proposals uploaded in the "प्रस्ताव कक्ष" page: see Step 0b.

## Step 0b — intake from प्रस्ताव कक्ष
> **Superseded for page version 4 (App B UI, 08.11.2026):** the page's work is done by the scheduled task per
> docs/DESK_WORKER.md. The text below describes the old v2 / v3 page and is kept for reference only.
Page: https://claude.ai/artifact/Hqf9Y7iKkDzNntsVCxXcB4 (source `desk/proposal-desk.html`; data model `docs/PROPOSAL_DESK.md`).
Trigger: Abhi says "प्रस्ताव कक्षातील नवीन प्रस्ताव तयार कर". Pin every write with `if_version`.
1. **Find queued cases:** `ArtifactData` `query` collection `cases` where `status == "queued"`; set `status = "processing"`, `stage = "अभ्यास चालू"`.
2. **Get the inputs:** for each `inputs[]` item, `Artifact` `read` with `url` = page URL and `path` = `asset_id`. Copy the saved file to its ORIGINAL `name` (§4.16). `kind`: proposal / extra / reply (a reply = the office's answer to our letter → next note).
3. **Make the three files:** Steps 1–7 below, exactly. `instruction`, if set, is Abhi's correction for this run.
4. **Upload the package PDF:** `Artifact` publish with `url` = page URL, `asset: true`, `file_path` = the PDF → output `{kind:"package_pdf", name, store:"asset", ref:<asset id>}`.
5. **Store the Word files** (assets refuse .docx): `python tools/desk_chunks.py <file.docx> <caseId> <study|note_letter> <scratch dir>` → write the chunk files with `ArtifactData` `batch` (op set, collection `outputs`, doc_id = file stem, `file_path`); the tool prints the `outputs[]` record. Overwrite or delete old chunks of the same case/kind first.
6. **Close the case:** `ArtifactData` `update` — `outputs`, `summary` (1 line), `letter_needed`, `essential_points`, `grs` [{code, date, title, pages}], `missing_grs`, `status = "done"`, `stage = "मसुदा तयार"`, `updated_at`, and a `history` entry {at, stage, note}. On error: `status = "failed"` + history note.
7. **Report** in Marathi, 3–4 lines per case (Step 8.2).

## Step 1 — Read the proposal (every page, as images)
1. `pdftoppm -r 110 -png <proposal.pdf> pg/p` and LOOK at every page image. Read stamps, inward nos., handwritten remarks, dates and amounts twice. Unclear → "अस्पष्ट" in the Study; "____" in the note/letter (§4.27).
2. Note: निर्देशपत्र (page 1) gives C R no., file no. (e.g. संकीर्ण-2026/**979**/प्र.क्र.130/का.6) and subject. A "पृथक पत्र" sheet is a proposal page too (keep it).
3. Write a facts list: who sent, through whom (High Court or direct), letter nos./dates with page nos., the demand, the employee/post/dates/amounts, enclosures, and any earlier file of this Section on the same matter (e.g. "स्मरणपत्र क्र. संकिर्ण-2024/प्र.क्र.259/का.6").
4. Keep the original proposal file name (strip only the random upload prefix like `11ae057d-`). The returned PDF uses this name (§4.16).

## Step 2 — Find the provisions and precedents
1. List every GR / rule / circular / court order mentioned in the proposal, plus those needed to decide it.
2. Look in the repo: `pdf/`, `pdf/gr/INDEX.tsv`, `register/*.md` (verified extracts), `service-rules/`, `precedent-library/` (unzip; 00-INDEX), `medical-bill/` for medical cases.
3. Missing GR → fetch it yourself (§4.14). No need to ask the user.
   - **Code known:** official URL `https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf`.
   - **Code unknown:** search the archive.org mirror by date and department: `https://archive.org/advancedsearch.php?q=collection:maharashtragr AND date:[YYYY-MM-DD TO YYYY-MM-DD]&fl[]=identifier&fl[]=description&fl[]=subject&rows=500&output=json`.
     - The `description` field holds the title.
     - The PDF is at `https://archive.org/download/in.gov.maharashtra.gr.<code>/<code>.pdf`.
     - The last 2 digits of the code identify the department, e.g. 05 = Finance, 12 = Law & Judiciary.
   - **Helper:** add `code …` / `search …` / `dept …` lines to `tools/gr-request.txt` and run `python3 tools/gr_request.py`. Run it locally if the session has internet; otherwise push the file and the GitHub Action does it. Files land in `pdf/gr/` + `INDEX.tsv`.
   - **Rule books:** official site `finance.maharashtra.gov.in` → Publications/Handbook. MCS (Pay) Rules 1981 is already in `pdf/01-mcs-pay-rules-1981/`.
   - **Court orders:** official sites only (api.sci.gov.in, bombayhighcourt.nic.in). Never third-party sites.
   - **Mirror gaps:** the archive.org mirror lacks many 2026 and some older Law & Judiciary GRs, and the GR site's search has a captcha. If a GR is still not found, ask Abhi for its सांकेतांक in ONE line and continue with everything else. (Automatic engine run, App B: no interaction — the question goes into status.json `warnings` + Study part 4 instead; tools/ENGINE_PROMPT.md rule 2.)
4. Read the GR page images before quoting. Quote verbatim, with GR no., date, page and para.
5. Precedents: grep `/tmp/old/index.tsv` and the texts for the subject. Look for earlier Finance/GAD opinions on the same point, and for an earlier file of the same employee. Old-case names and internal ids (z6_0235…) never go into the note.

## Step 3 — Decide: letter or no letter (§4.15)
- **Letter:** only if information ESSENTIAL to decide or approve is missing. Ask only that, as an empty table. Never ask for documents the department already has (its own GRs, official court orders).
  - Addressee: as the proposal came. Via the High Court (प्रबंधक …, उच्च न्यायालय (अपील शाखा), मुंबई) if it came through the HC; otherwise the District Judge directly.
- **No letter:** if the proposal is complete. The note then goes onward with a proposal for approval:
  - Finance (वित्त विभागाच्या मान्यतेस्तव), adding "अ.मु.स. (वित्त)" to the signers — model: CR66 sample;
  - or GAD (सा.प्र.वि.);
  - or a reply letter on the basis of an existing opinion.
- **Drafts ticked by Abhi (INSTRUCTIONS §4.28, 03.11.2026 — "कोणते मसुदे हवेत?"):** case.json / the desk choice `outputs`
  (letter, reminder, gr, corrigendum, circular, memo, notification, parawise; since 04.11.2026 also do_letter, uo_note,
  endorsement, office_order, press_note, addendum, affidavit, lq — Step 4b "New draft types", INSTRUCTIONS §4.33).
  Given → make EXACTLY those besides the note (Study, note, package always; nothing ticked → note only); null → decide as above. Letter ticked but nothing essential
  missing → a letter fitting the demand (reply / forwarding / intimation) + warning; letter not ticked but essential
  information missing → no letter + warning "माहिती कमी — पत्र सुचवले (निवडलेले नाही)". Letter + reminder → spec
  `letters` [letter, reminder] (one Note_and_Letter, each on a new page); several orders → spec `orders` [..] (one
  Order_Draft, each on a new page). The last para names every draft made.

## Step 4 — Write the note (टिप्पणी) — spec.json
Copy the structure of the nearest sample in `samples/specs/` and fill your facts. Rules:
- **Language (INSTRUCTIONS §4.18, 01.11.2026):** short sentences, one point each, clear subject (who did what); "श्रीमती" (not "सौ."), one space after "श्री."/"श्रीमती"; the person's name in Marathi initials (circular 07.05.2018: "ह.ना. आपटे", not "एच.एन.आपटे"): look through the whole proposal; a Devanagari full name anywhere → Marathi initials from it (proposal "एस. एस. कुर्ले" + full name "सिद्धेश्वर शरणप्पा कुर्ले" → "श्री. सि. श. कुर्ले"); no Devanagari name anywhere → the proposal's English-initials form; never invented (Abhi 06.11.2026 "अ मान्य"); missing-information list inline "(1) …; (2) …." in its para, never a table (INSTRUCTIONS §4.31 (अ), Abhi 05.11.2026 C2 option आ); letter: no "तात्काळ", request form "…उपलब्ध करून देण्यात यावी, ही विनंती." Quotes stay verbatim. lint_spec.py checks this.
- **Marathi forms (INSTRUCTIONS §4.19, 01.11.2026; Marathi Language Dept GR कपासू-2020/प्र.क्र.56/भाषा-2, दि. 10.11.2022):** outside “…” quotes — a space after an abbreviation dot in running text ("दि. 17.09.2026", "क्र. 108", "प्र. क्र. 21/2024"); ":-" never ".:-"; "करून" not "करुन", "प्रारूप" not "प्रारुप". Left exactly: quotes and related extracts, "पृ.N/प.वि." / "पॅकेज PDF पृ. N", file/letter nos. and any token with '/' or '-' ("संकिर्ण-2026/226/प्र.क्र.131/का.6"), the signer chain, date digits, decimals, GR codes. lint_spec.py and verify_outputs.py check this.
- **Para 1:** "<authority> यांच्या पृ.__/प.वि. वरील दि. __ रोजीच्या पत्रास अनुसरून सादर." (or "…पत्रासोबत प्राप्त … पत्रास अनुसरून सादर.")
- **No incoming letter number anywhere in the note (INSTRUCTIONS §4.29(1)/(5), §4.30(7), §4.36; Abhi 05.11.2026 C1 option आ):** every covering / authority / opinion letter is cited by authority + date + पृ.N/प.वि. only (its wording may be quoted “…”). Kept: the U.O. reference no. (अनौपचारिक संदर्भ क्र.) of any department (Finance, GAD, Public Health …) and another desk's (कार्यासन) reference no. — written only when the record has one; never invented, no "____" U.O. line when there is none (Abhi 05.11.2026: "प्रत्येक वेळी अनौपचारिक संदर्भ असेलच असे नाही असल्यास ठेवावे टिप्पणीमध्ये"). Not affected: order nos. (आदेश क्र., कार्यालयीन आदेश क्र., promotion / pay-fixation order nos. — kept, Abhi 05.11.2026 "आदेशाचे क्रमांक ठेवा"), GR nos./सांकेतांक, petition/case nos., C R no., the Section's own file no., the letter's `ref_no` and `refs` ("आपले पत्र क्र. …, दि. …"), quotes and `related`. lint_spec.py ERROR, verify_outputs.py.
- **Body:** numbered paras, DETAILED (INSTRUCTIONS §4.29, Abhi 03.11.2026: "note khupch short jhali detail asayla pahije"): the 12 elements in order where they apply (every covering letter in para 1; background/service table; the documents that create the issue verbatim; benefit/amount/period tables; each authority's letter verbatim (date + पृ.N/प.वि., no letter no.); present status; complaint/court timeline; replies to earlier queries; every applicable GR para + rules + SC/HC judgments verbatim in the body, each condition linked to the proposal's fact in sentences / sub-points (no condition table, §4.37); the last para "उपरोक्त वस्तुस्थिती विचारात घेता, …" with the decisive facts (no separate fact-summary list, §4.37); the exact demand + action after approval; the drafts) — no fact or condition of the proposal left out; sentences stay short (§4.18); letters stay concise (§4.15). Model: samples/specs/HTE_2026_overpayment-waiver_finance-concurrence.json.
- **Relevance + एकसंध flow (INSTRUCTIONS §4.34, Abhi 03.11.2026 on CR132: "vinakarna upyogache naslele sandarbh noting mdhe dakhwile aahet, tasech paragraph cha wachtana flow tutato"):** only references needed to decide the demand (no endorsement/पृष्ठांकन nos., "प्रत … माहितीकरिता" lines, the office's own reminder history — at most one clause in para 1/2 —, copy lines, meta lines); covering letters once, in para 1; each fact ONCE in the body (table OR quote OR sentence), quotes only where the wording matters; office order (reference → "सदर पत्रान्वये" who asks what → background → issue → provisions with linked conditions → missing info → "उपरोक्त वस्तुस्थिती विचारात घेता, … सबब, …") with linking openers ("सदर प्रकरणी", "त्यानुषंगाने", "याबाबत", "तथापि"); one quote per sentence (no "तसेच, “…” व “…”"); पृ.N/प.वि. once per document at first mention, no "पृ./प.वि." table column; quotes never cut with "…". lint/verify WARN.
- **Quality checks (INSTRUCTIONS §4.30, Abhi 03.11.2026 — inside the existing drafts, nothing new):** every demand/contention/condition answered; no contradictory dates/amounts/names/posts across proposal, note, letter, drafts, parawise; the demand in one sentence right after para 1 (parawise `relief_sought` — only with `"layout": "rule58"`); GR/rule text in its original language; respectful language to courts (lint_parawise WARN); tables only for figures and the service-detail table (§4.37; parawise `background` — rule58 layout only); GP/other-department opinions as recorded (date + पृ.N/प.वि., no letter no.), never treated as binding. Engine reviewer: coverage table + contradictions -> Study part 7 only.
  - Figures (amounts, arrears, recovery, burden, pay / pay scales, post counts, period calculations) and the service-detail table (name, post, appointment date, period) go in TABLES: a `{"table": [[...],[...]], "bold_last": true}` item in `note.paras`, with a lead-in ending ":-" that names the content and a look-back sentence after ("वरील तक्त्यात दर्शविल्यानुसार …"). Everything descriptive is point-wise (§4.37 (इ)).
- **Flow (INSTRUCTIONS §4.37, Abhi 05.11.2026: "तक्ता टेबल यामध्ये माहिती संख्या विषयक आकडेमोड असेल तरच योग्य वाटते बंद थेरॉटिकल असल्यास मुद्देनिहाय असणे चांगले वाटते"; "प्रार्थना अ, सेवा अ, 1अ 2अ 4अ"; research docs/FLOW_RESEARCH.md):**
  - D1: one issue per numbered para (demand / background / authority letters / provisions / earlier opinion / missing info / सबब); its facts as sub-points `note.sub` {"<para index>": ["(1) …", "(2) …"]} (or "(अ) …") under a lead-in ending ":-"; about 5–8 numbered paras for an ordinary proposal (office median 5); each numbered para opens with an office linking word (INSTRUCTIONS §4.37 (ऊ) table); not the same opener in two consecutive paras.
  - D2: no separate list "उपरोक्त वस्तुस्थिती पुढीलप्रमाणे आहे:-"; the last para opens "उपरोक्त वस्तुस्थिती विचारात घेता, …" — the decisive facts in one or two short sentences, then "सबब, …" with one of the endings below ("सबब, उपरोक्त वस्तुस्थिती विचारात घेता, …" also fine). A facts opener "सदर प्रकरणाची वस्तुस्थिती खालीलप्रमाणे आहे:-" near para 2–3 is the office form and allowed.
  - D3: conditions → "… मध्ये असे नमूद करण्यात आले आहे की, “…”" → "वरील अटीनुसार …" → "परंतु, सदर प्रकरणात …" (C R 2-2026), never an "अट / प्रस्तावातील स्थिती" table; duties, demands, chronology (one step per sentence: "त्यानुसार / त्यानुषंगाने / तथापि / तद्नंतर / दरम्यान"), objections, opinions point-wise.
  - D4: para 2 opens "सदर पत्रान्वये …" ("उपरोक्त पत्रान्वये …" when para 1 cites several letters) — who asks what, one sentence (court notes: §4.32 (अ) instead).
  - Quotes: "… मध्ये असे नमूद करण्यात आले आहे की, “…”" / "“…” असे नमूद आहे." (not "खालीलप्रमाणे तरतूद आहे"); carry the short subject forward ("सदर कर्मचारी", "श्रीमती ____ यांनी"); one point per sentence (§4.18); no opinion links ("दिसून येते", "अशा परिस्थितीत … शक्यता", "उचित होईल" — §1.1).
  - lint / verify WARN (never errors): "जुने रूप §4.37" (old list, condition table), prayers table "§4.37 मुद्देनिहाय", a descriptive table, more than 10 numbered paras, para 2 not "सदर / उपरोक्त पत्रान्वये".
  - GR/rule text verbatim in “ ” with "(पृ.N/प.वि.)".
  - Earlier record of the same matter = stated as a fact with its reference.
- **Accuracy checks A1–A12 (INSTRUCTIONS §4.39, 06.11.2026, CR 14 / CR 50 runs):** quotes from the provision's sentence start (rule + proviso together); "वरील …नुसार" says only what the quote says; information / documents asked per the provision's own words, no copy of a merely cited letter; this Section's own earlier note / letter in the proposal stated in the chronology; no "… ____ आहे." body sentence (only the missing-info para); the sentence after a table states only what the table shows; one form of each name (Marathi initials per §4.18); a table fact not repeated in a sentence, no one-fact para repeating a table; A9 `related` extracts character-identical to the page and to the body quote (§4.19 spelling never inside quotes). A10: the essential items are decided from the governing GR itself — every condition / procedure step against the record: facts that decide which clause applies (e.g. the date a status applies from, an earlier review when the GR says "once") and every column of the GR's prescribed form missing or blank in the proposal; basis in Study part 4; never ask Abhi whether an item is essential. A11: the case stage = the last dated document of the whole proposal (noting + file parts); this Section's own letter last with nothing after it -> the letter it answered is closed (not "सदर पत्रान्वये … मागविण्यात आले आहे"), the fitting letter is a reminder (§4.21) for what that letter asked (new items only when a quoted provision needs them; never a court case's status); no missing-info para in that stage, the last para states no reply is on record. Para 1 = one sentence "… पत्रांस अनुसरून सादर.". A12: another department's U.O. no. (अनौ.सं.क्र.) on record -> written with its date where its opinion is cited. A8 also: one opinion / fact once, not in several sub-points. lint WARN for A1, A3, A5, A7, A9.
- **CR 14 run 2 decisions (INSTRUCTIONS §4.40, Abhi 06.11.2026):** (अ) para 1 cites every letter the case started from, earlier rounds included; (आ) a GR / rule already inside the proposal is not enclosed again — cite its proposal pages; (इ) the letter's subject = the subject of the proposal's (latest) letter, not the निर्देशपत्र, not composed (§4.19 spelling forms only); (ई) each item of information / document asked once (lint WARN "§4.15 एकच माहिती पुन्हा मागवली").
- **Page references:** only "पृ.N/प.वि.", where N = page in the returned PDF (proposal pages 1..n, then the attached GR pages). Never "पॅकेज PDF" anywhere in the note (body or related) or the letter (INSTRUCTIONS §4.27).
- **No warnings in the drafts (INSTRUCTIONS §4.27, 02.11.2026):** unclear/unknown value → "____"; a GR/source not available is not mentioned in the note (Study part 4 + `warnings`); discrepancy remarks → Study part 4/7. Outside “…” quotes and related extract text, never: "पॅकेज", "इशारा", "पडताळणी अपूर्ण", "मागवावे", "वाचन अपूर्ण", "अस्पष्ट", "पडताळलेले नाही", own "टीप :", "warning", "TODO", "स्रोत", "जसाच्या तसा"/"जसेच्या तसे" (Abhi 03.11.2026; the related source line prints as "(…, पृ.N/प.वि.)"). Applies to order/parawise drafts too. The missing-information para "सदर प्रकरणी … यांच्या दि. … रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:- …" is allowed. No trace of AI in the drafts or the returned PDF (Abhi: "वरिष्ठ अधिकाऱ्याला असे वाटू नये, की AI che kam aahe म्हणून"): no "AI", "Claude", "मॉडेल", "स्वयंचलित", "engine", "प्रणालीने तयार" etc. (full list §4.27 (उ)); docx/PDF metadata blank.
- **Banned words:** no commentary or theory, no arithmetic explanations, no advice. Closed list (checked by `tools/verify_outputs.py` in the note body and the letter; keep both lists identical — 01.11.2026 सुसंगती): "दिसून येते", "असे दिसते", "पडताळणी केली असता", "माझ्या मते", "मला वाटते", "असे वाटते", "ठरवावे", "कदाचित", "बहुधा".
- **Missing information para (Abhi 05.11.2026, office flow):** "सदर प्रकरणी <sending authority, e.g. प्रबंधक (अपील शाखा), मा. उच्च न्यायालय, मुंबई> यांच्या दि. <DD.MM.YYYY> रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील माहिती आढळून येत नाही:- (1)…; (2)…." — authority + date only (no letter no., C1), "मा." per §4.23, unknown date "__.__.____" (the old opener "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:-" is no longer used: lint / verify WARN "जुने रूप"); items inline in that para, never a table after it (INSTRUCTIONS §4.31 (अ), Abhi 05.11.2026 C2 option आ; lint ERROR without the inline "(1)", WARN for a table after it; the letter's table §4.20 is unchanged). ONE such para only, just before the last (सबब) para, essential items only (§4.15) (INSTRUCTIONS §4.31, Abhi 03.11.2026): nowhere else in the note (other paras, facts / condition tables, "उपरोक्त वस्तुस्थिती") a "नमूद नाही / जोडलेले नाही / उपलब्ध नाही / प्रस्तावासोबत नाही / प्रत नाही / सादर केलेली नाही" remark; a missing value in a table is "____". lint_spec.py checks this.
- **Last para, one of:**
  - Every form may be preceded by "उपरोक्त वस्तुस्थिती विचारात घेता, <decisive facts>." (§4.37 D2; lint reads the para from its "सबब,").
  - "सबब, उपरोक्त माहिती तक्त्याच्या स्वरूपात … कळविण्याबाबतच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल."
  - "सबब, … प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."
  - Also accepted by `tools/lint_spec.py` (LAST_FORMS; audit 05.11 R-F10, the text here = what lint accepts): several drafts
    in one para (§4.28: "… पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."); an order draft
    (Step 4b); to a department "सबब, … <वित्त / सामान्य प्रशासन / …> विभागाच्या मान्यतेस्तव / मान्यतेसाठी / अभिप्रायास्तव /
    अभिप्रायार्थ / सहमतीस्तव सादर (करण्यात येत आहे)." (U.O. reference §4.33); medical Format-2 (§8.3) "… सार्वजनिक आरोग्य
    विभागास विनंती करण्यास हरकत नसावी. मान्यतेस्तव सादर."; approval within the department, no draft, "सबब, … मान्यतेस्तव
    सादर."; file closure "सबब, … नस्ती बंद करण्यास मान्यता असावी."
- **Signers** (`note.signers`, in order): (अ.मा. वसू) / क. अ. (अ.का.) [these two on the right, the name not bold — the tool places them from the desk profile] / अ.स. (श्री. वडनेरकर) / उ.वि.स. नि. उ.स. (श्री. बोंद्रे) / सचिव व व. वि. स. (श्री. बिले) (INSTRUCTIONS §4.6, 05.11.2026). Add "अ.मु.स. (वित्त)" only when the last para sends the file to Finance — "वित्त विभागाच्या मान्यतेस्तव / अभिप्रायास्तव /
  सहमतीस्तव …" or "वित्त विभागास विनंती …" — or to the Public Health Department (§8.3); this is the route lint and verify read
  (audit 05.11 R-F11).
- **`related`** ("संबंधित माहिती (संदर्भासाठी)"): verbatim extracts. Each source ends with " (पृ.N/प.वि.)" (several pages: "(पृ.N-M/प.वि.)" / "(पृ.N,M/प.वि.)") when the page is in the returned PDF; otherwise NO page marker (just GR no./date/page/para). The Study keeps "(पॅकेज PDF पृ. N)" / "(पॅकेज PDF मध्ये नाही)" (INSTRUCTIONS §4.27, 02.11.2026). No repo paths (register/, service-rules/, pdf/ …) and no internal ids in `related`.
- **Letter (`letter`):**
  - `ref_no`: "संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6" (e.g. "संकिर्ण-2026/…"; year = the year of the file no. on the निर्देशपत्र, never copied from a sample); `date`: "__.__.<current year>".
  - `to`; `subject`; `refs` ("आपले पत्र क्र. …, दि. …").
  - `intro`: "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, सदर प्रकरणी पुढील कार्यवाहीसाठी खालील माहिती … उपलब्ध करून देण्यात यावी, ही विनंती:-"
  - `points`: an empty table or a few short points.
  - **Table = data only (INSTRUCTIONS §4.20, 02.11.2026):** the table asks only for data to fill in (dates, figures, periods, yes/no, numbers). Documents (copy of an order, report, certificate — "प्रत", "प्रमाणपत्र", "अहवाल") go after the table: a point "	तसेच, खालील कागदपत्रे उपलब्ध करून देण्यात यावीत, ही विनंती:-" then the documents as points (the tool numbers them; the lead-in line stays unnumbered). A row mixing both is split (data in the table, the document in the list). Model: CR131 sample. lint_spec.py checks this.
  - **Reminder (INSTRUCTIONS §4.21, 02.11.2026):** `letter.reminder: N` prints "स्मरणपत्र-N" above the क्रमांक line; same file no.; refs[0] "या कार्यासनाचे समक्रमांकाचे पत्र दि. __"; intro "… संदर्भाधीन पत्रान्वये मागविण्यात आलेली माहिती अद्याप अप्राप्त आहे. सदर माहिती लवकरात लवकर शासनास उपलब्ध करून देण्यात यावी, ही विनंती."
  - **Copy line (§4.22, §4.38 (ई)):** letter to the High Court asking information "प्रमुख जिल्हा व सत्र न्यायाधीश, <place> यांच्याकडून प्राप्त करून" → `letter.copies: ["प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, <place> यांना आवश्यक कार्यवाहीसाठी"]`; the tool prints "प्रत" once: "प्रत :-", "1) <copy>", "2) निवड नस्ती" (only the file copy → "प्रत : निवड नस्ती"). Models: CR122, CR130.
  - **"मा." (§4.23):** own text of note and letter: "मा. उच्च न्यायालय…", "मा. मुंबई उच्च न्यायालय", "मा. मुख्य न्यायमूर्ती / मा. न्यायमूर्ती / मा. प्रशासकीय न्यायाधीश"; not in the addressee block, not in an office designation "उच्च न्यायालय (… शाखा)", not in quotes or related. **"शुद्धिपत्रक" (§4.24).**
  - **Layout (INSTRUCTIONS §4.38, Abhi 06.11.2026 on the CR 14 letter: "अ मान्य, आ एकाच क्रमाने, इ तसेच ठेवा"; basis: the Department's letter dt. 30.03.2026 and the HC letter dt. 17.11.2025):** the tool prints it all, the drafter writes no layout characters or point markers:
    - विषय / संदर्भ bold (labels "विषय :-" / "संदर्भ :-" too), not centred: a block shifted right (label 2.5 cm, text 4.4 cm, wrapped lines under the text); each reference on its own line ("1)" at 4.4 cm, text 5.2 cm). D.O. letter unchanged.
    - requested points "(1)", "(2)" … in ONE sequence through the letter (table point and documents list continue it), indented (number 1.27 cm, text 2.2 cm); any marker in the spec is renumbered; a lead-in ending ":-" stays unnumbered.
    - first para ("उपरोक्त विषयाबाबत …") unnumbered; every later body para (separate request para, closing) "2.", "3." … at the margin.
    - "आपला," + signature, then the copy line (above). The note is unchanged (its sub-points and the inline "(1) …; (2) …." missing-info items stay).
- **Build:** `python3 tools/build_note_letter.py spec.json <outdir> <PREFIX>`. This writes `<PREFIX>_Note_and_Letter.docx` + a PDF preview. LOOK at the preview pages.

## Step 4b — Court cases and order drafts (02.11.2026; research + decisions B1–B10: docs/COURT_AND_ORDERS_RESEARCH.md)
Both are optional keys of the same spec.json; engine detail: tools/ENGINE_PROMPT.md "Court cases and order drafts".
- **Court cases** (GP/AGP/High Court/MAT notice on a writ petition, O.A., contempt, SLP):
  - Note (B9; INSTRUCTIONS §4.32 (०), Abhi 05.11.2026 C3 option अ): para 1 "<सहायक सरकारी वकील, …> यांच्या पृ.N/प.वि. वरील
    दि. __ रोजीच्या पत्रास अनुसरून सादर." when a GP / AGP letter is on record; no such letter (petition received directly)
    -> just "सादर."; then
    "पार्श्वभूमी थोडक्यात खालीलप्रमाणे आहे:-" and numbered facts with पृ.N/प.वि.
  - Para 2 / para 3 (INSTRUCTIONS §4.32, Abhi 03.11.2026): para 2 = flowing sentences: "<petitioners> यांनी … दाखल केलेली रिट
    याचिका क्र. __ (पृ.) कृपया पहावी. सदर याचिकेत <R1> यांना प्रतिवादी क्र. 1, <R2> यांना प्रतिवादी क्र. 2, … आणि <Rn> यांना प्रतिवादी
    क्र. N करण्यात आले आहे (पृ.)." + verification date (no choppy list); the petition is "रिट याचिका क्र. <N>/<YYYY>" in the Marathi note and letter, never "(लॉजिंग)" (Abhi 05.11.2026; English parawise / affidavit titles unchanged); story order and linking words for all paras
    (§4.32 (ई)); para 3 =
    "सदर याचिकेद्वारे याचिकाकर्त्यांनी पुढीलप्रमाणे प्रमुख मागण्या केल्या आहेत (पृ.N/प.वि.):-" + sub-points "(अ) …; (आ) …"
    (`note.sub`; each prayer in Marathi, petition order; no prayers table — Abhi 05.11.2026 "प्रार्थना अ", §4.37); the English
    prayers verbatim go FIRST in `related`. Respectful plural, Marathi
    designations, short sentences. Model: samples/specs/WP35697_2026_old-pension_finance-opinion.json.
  - Facts suffice → spec `parawise` (English; B8; Rules 1984 Rule 58(3) every point, Rule 58(4) Note (ii) elaborate
    facts + documents enclosed, recommendation oppose / not oppose — from the record only, the one exception to "no opinion"; no record basis → "____" + warning) → `python3 tools/build_parawise.py spec.json <outdir>
    <PREFIX>` → `<PREFIX>_Parawise.docx`; letter to the GP/AGP forwarding it.
  - **Format (Abhi 03.11.2026: "ok tar format mi dilelya parawise cha thewa"):** ALWAYS the Section's office format (default of build_parawise.py): "Para wise Explanation in <case>.", "<petitioner> Vs. <respondent>", "Parawise submissions on behalf of …", one table Sr. No. | Para No. | Remarks — `paras` [{para, remarks}] for every para / sub-para, `{"section": "Grounds"}`, each ground, formal paras, "Prayer Clauses …"; model samples/specs/COURT_wp_parawise_example.json. The Rule 58 layout (relief, brief facts, enclosures, recommendation) only with `"layout": "rule58"`.
  - **Joint affidavit (INSTRUCTIONS §4.35, Abhi 04.11.2026):** several State respondents → parawise on behalf of all of them and the GP letter asks ONE joint affidavit draft "शासनाच्या वतीने"; copy to the other respondent department. The High Court Registry, if a respondent, is not part of it (no remarks, no copy). Model: samples/specs/WP35697_2026_parawise_GP-letter.json.
  - Essential facts missing → information letter first (§4.15).
  - Rule 58(4): to the GP within two weeks of receipt / before the date in the notice; the hearing date goes in Study part 0.
- **Order drafts** (B7: only when the decision / Finance-GAD concurrence is on record, or Abhi asks — ticking it in
  "कोणते मसुदे हवेत?" is asking; without concurrence on record it is still drafted + warning, §4.28): spec `order`
  (gr / corrigendum / circular / memo / notification), or `orders` [..] for several (§4.28; model
  samples/specs/ORDER_multi_example.json) → `python3 tools/build_order.py spec.json <outdir> <PREFIX>` →
  ONE `<PREFIX>_Order_Draft.docx` (each order on a new page). Note's last para: "सबब, … शासन निर्णयाचे (ज्ञापनाचे /
  शुद्धिपत्रकाचे / परिपत्रकाचे / अधिसूचनेचे) प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."; several drafts in one para,
  e.g. "सबब, … पत्राचे प्रारूप व शासन निर्णयाचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर." (lint_spec.py).
- **New draft types (04.11.2026, INSTRUCTIONS §4.33 — when to use each, what the tool prints, open-point defaults;
  research: docs/FORMS_RESEARCH_DO_UO.md, FORMS_RESEARCH_ORDERS.md, FORMS_RESEARCH_AFFIDAVIT_LQ.md,
  LEGISLATURE_INSTRUMENTS_RESEARCH.md).** Draft key → spec → tool → file:
  - `do_letter` (अर्धशासकीय पत्र) → `letter` / `letters` item `{"kind": "do", …}` (first-person `body`, `to` at the foot) →
    `tools/build_note_letter.py` → `<PREFIX>_Note_and_Letter.docx`; model samples/specs/LETTER_do_example.json.
  - `uo_note` (अनौपचारिक संदर्भ) → `note.uo` `{to, no, date}`; last para sends the file to that department →
    `tools/build_note_letter.py` (block after the signers); model NOTE_uo_reference_example.json.
  - `endorsement` (पृष्ठांकन), `office_order` (कार्यालयीन आदेश), `press_note` (प्रसिद्धीपत्रक), `addendum` (शासन पूरकपत्र) →
    `order` / `orders` item with that `type` → `tools/build_order.py` → `<PREFIX>_Order_Draft.docx`; models
    ORDER_endorsement_example.json, ORDER_office_order_example.json, ORDER_press_note_example.json, ORDER_addendum_example.json.
  - `affidavit` (शपथपत्र, English) → spec `affidavit` (reply defaults to `parawise.paras`) → `tools/build_affidavit.py spec.json
    <outdir> <PREFIX>` → `<PREFIX>_Affidavit.docx`; model COURT_affidavit_example.json.
  - `lq` (विधानमंडळ प्रश्नाचे उत्तर) → spec `lq` → `tools/build_lq.py spec.json <outdir> <PREFIX>` → `<PREFIX>_LQ_Answer.docx`
    (+ पुरवणी टिप्पणी for starred / short notice); the note: one para per clause ending "प्रस्तावित उत्तर : …"; model
    LQ_answer_example.json.
  - Last para names each: "अर्धशासकीय पत्राचे / पृष्ठांकनाचे / कार्यालयीन आदेशाचे / प्रसिद्धीपत्रकाचे / शासन पूरकपत्राचे /
    शपथपत्राचे / … प्रश्न क्रमांक ____ च्या उत्तराचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."; U.O.: "सबब, … <विभाग>
    विभागाच्या अभिप्रायास्तव सादर करण्यात येत आहे." Never write the lines the tool prints (lint refuses).
    Lints: lint_order.py, lint_affidavit.py, lint_lq.py (via lint_spec.py). verify_outputs.py does not yet check the
    Affidavit / LQ_Answer files: look at their PDF previews.
- Unknown details (petition no., date, संकेतांक, Gazette part) → "____"; never stop.
- Checks: `tools/lint_spec.py` (calls tools/lint_order.py / tools/lint_parawise.py), `tools/verify_outputs.py` (fonts,
  ids, repo paths, पृ. ranges of both files). App: kinds `order_draft` / `parawise` (Supabase migration 0006).

## Step 5 — Build the returned proposal PDF (GR सह प्रस्ताव)
1. Choose only the relevant pages of each GR/rule/order: page 1 (title, number, date) + the pages with the quoted paras.
2. Write `enclosures.json` (see the `tools/pkg3.py` docstring). Marks = exact text-layer line strings that occur only once on the page.
3. `python3 tools/pkg3.py <proposal.pdf> enclosures.json "<outdir>/<ORIGINAL FILE NAME>.pdf"`. This gives page stamps and bookmarks, and leaves the proposal pages untouched.
4. Pages pkg3 cannot mark (scanned GR, legacy/garbled font, repeated strings): use `python3 tools/highlight.py <pdf> marks.json` (modes: lines / ocr / rect). Yellow highlights on the quoted lines only. NEVER boxes. Nothing on the proposal pages.
5. Render the GR pages to PNG and LOOK. The highlights must sit exactly on the quoted lines and nothing else.
6. Set the note's "पृ.N/प.वि." from the package map (`<pdf>.map.json`).

## Step 6 — Study file (`<PREFIX>_Study.docx`) — `tools/build_study.py study.json <out.docx>`
1. **Part 0 — वरिष्ठांसाठी ब्रीफिंग** (§4.17). Bullets only, 1–2 pages:
   - the proposal in one line;
   - a key-facts table;
   - the GR and its exact condition (पृ./प.वि.);
   - each approval condition: पूर्ण / अपूर्ण / माहिती नाही;
   - the competent authority and its basis;
   - financial burden;
   - earlier similar case / Finance-GAD opinion;
   - the proposed action and the essential points asked;
   - likely questions from seniors, with answers.
   - Optional simple chart: a matplotlib PNG with a Devanagari font. No charts in the note or letter.
2. **Parts 1–7** per tools/PROPOSAL_PROMPT.md: Marathi rendering page-wise, gist, provisions (verbatim + source), doubts, note draft, letter draft, verification note.
3. **Final warnings (Abhi 03.11.2026):** at finish the engine writes the run's final warnings into the Study, end of भाग 7, under "अंतिम तपासणीचे इशारे (वापरण्यापूर्वी तपासा)" (`tools/study_warnings.py append`; model/cost lines owner-only, kept in the app) — never with the note/letter.

## Step 7 — Verify (must print ALL OK)
`python3 tools/verify_outputs.py <outdir> <PREFIX> "<package pdf>" <number of proposal pages>`. It prints one line per check (01.11.2026 सुसंगती; tests: `tests/test_verify_outputs.py`):
- fonts: ascii/hAnsi/cs/eastAsia = DVOT-SurekhMR on every text run, incl. headers/footers (Study, note, letter);
- no internal ids (`z<digit>_<4 digits>`) anywhere; no repo paths (register/, service-rules/, precedent-library/, pdf/, repo) in the note/letter;
- every "पृ.N/प.वि." (also lists 5,7, ranges 5-7 / 5 ते 7, Devanagari digits) in note, letter and Study and "पॅकेज PDF पृ. N" in the Study is within 1..package pages;
- no "पॅकेज PDF" and no warning word (§4.27 list) anywhere in the note (body + related) or the letter; no banned word (Step 4 list) in the note body or the letter;
- note signer chain = INSTRUCTIONS §4.6 in order; "अ.मु.स. (वित्त)" present only when the last para sends the file to Finance ("वित्त विभागाच्या मान्यतेस्तव / अभिप्रायास्तव / सहमतीस्तव …", "वित्त विभागास विनंती …") or to the Public Health Department;
- letter: new page/section; ref no. `संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6`; e-mail; विषय/संदर्भ bold, shifted-right block (§4.38); "आपला," (no "आपली,"); "( राजेश वडनेरकर )", "अवर सचिव ,महाराष्ट्र शासन", "प्रत : निवड नस्ती" (or "प्रत :-" + numbered lines ending "निवड नस्ती", §4.38);
- Study headings भाग 0 … भाग 7;
- package: original file name (not `*_Proposal_with_GRs.pdf`); exactly "पृ. i / N" in the bottom strip of every page; bookmarks; page count = proposal + enclosure pages of `<pdf>.map.json` (no separator pages); no mark "TEXT NOT FOUND"/0 hits; no annotation on proposal pages; only Highlight annotations; docx core properties and PDF metadata blank, no AI/tool names (§4.27).
- facts (WARN only, audit Q-F1): `python3 tools/fact_check.py "<package pdf>" --spec spec.json [--ocr-dir DIR] --details FILE` — every date / amount / letter no. / name of the note and letter (outside “…”) must occur on the पृ.N/प.वि. page it cites (no ref in the para: the proposal pages); NOT FOUND / ELSEWHERE lines = check that fact against the page image.
- consistency (WARN only, audit Q-F15, §4.30(2)): `python3 tools/consistency_check.py spec.json [--study study.json] --details FILE` — every date / amount / C R no. of the letter(s), order drafts, parawise, affidavit, LQ answer and Study part 0 (outside “…”) must also be in the note; one name spelled two ways, a different petition no. or two posts for one name = WARN; English drafts: dates, amounts, case nos. only.

Then a second read of every number and date against the page images.

## Step 8 — Deliver and report
1. Send three files per proposal: `<PREFIX>_Study.docx`, `<PREFIX>_Note_and_Letter.docx`, and the PDF under its original name.
2. Report in Marathi, 4–6 lines or a small table:
   - what the proposal is;
   - letter yes/no and its essential points;
   - GRs attached (pages);
   - only if still missing: the GR dates whose सांकेतांक is needed.
3. Save the approved spec as `samples/specs/<CR>_<year>_<type>.json`. Save downloaded GRs in `pdf/gr/` with an `INDEX.tsv` line. Commit and push. **Never commit a session's scratch files.**
4. If Abhi corrects the style, add the correction to INSTRUCTIONS.md §4 (a new numbered item, dated). Also update this SOP and the samples, so the correction is permanent.

## Step 9 — Saved case state and correction rounds (INSTRUCTIONS §4.41, Abhi 07.11.2026)
One proposal = one chat (the main path; the प्रस्ताव कक्ष engine stays as it is). After the first round:
`python3 tools/case_state.py save <id> --work <dir> --proposal <pdf> --package-name "<original name>.pdf" --prefix <PREFIX> --note "<stage>"`
(state in `cases/<id>/`, commit + push) and send the preview pages from `python3 tools/case_state.py rebuild <id> <out> --package`
(`<out>/preview/*.png`). A correction never re-reads the proposal: `load` (new chat) -> edit spec / study / enclosures only ->
`save --note "सुधारणा: …"` -> `rebuild` (`--package` only when the PDF changes) -> LINT OK + verify ALL OK -> send only the
changed file + new preview. First round: OCR text of all pages first; page images only of cited / text-less / stamp pages.
> **The page part below is superseded for page version 4 (App B UI, 08.11.2026):** page runs and corrections follow
> docs/DESK_WORKER.md; the old v2 / v3 text is kept for reference only.
प्रस्ताव कक्ष page (docs/PROPOSAL_DESK.md, §4.41 (उ)) after each round: `python3 tools/desk_sync.py <id> <out> <sync>` ->
upload every path in `<sync>/assets.txt` (Artifact publish, `asset: true`, url = page) -> put the returned ids in place of
`__ASSET__<name>` in `case_patch.json` outputs -> ArtifactData batch: `outputs` = `<sync>/chunks/*.json` (set), `cases/<id>`
= case fields + patch (path "chat", stage, history). "प्रस्ताव कक्षातील सुधारणा कर": ArtifactData query `edits` where
status == "pending" -> each one (target, para id = spec position, message, attachments `/_blob/<id>`) done as a correction
round -> sync again -> update the edit {status "done" | "failed", reply (one Marathi line: what changed), done_at}.
