# PROPOSAL_SOP.md — step-by-step procedure for every proposal (binding; any model, any session)

Owner: Abhi, Section Officer (कार्यासन अधिकारी), Law & Judiciary Department, Desk-6 (कार्यासन-6), Govt of Maharashtra.
When he sends a proposal PDF, do ALL steps below without asking. He must never have to explain this again.
The rules are in INSTRUCTIONS.md §4 (items 1–26); this file is the order of work + the tools. If anything here conflicts with
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
Page: https://claude.ai/artifact/8cJP8wz6j5tYM5kRHK1rVx (source `desk/proposal-desk.html`; data model `docs/PROPOSAL_DESK.md`).
Trigger: Abhi says "प्रस्ताव कक्षातील नवीन प्रस्ताव तयार कर". Pin every write with `if_version`.
1. **Find queued cases:** `ArtifactData` `query` collection `cases` where `status == "queued"`; set `status = "processing"`, `stage = "अभ्यास चालू"`.
2. **Get the inputs:** for each `inputs[]` item, `Artifact` `read` with `url` = page URL and `path` = `asset_id`. Copy the saved file to its ORIGINAL `name` (§4.16). `kind`: proposal / extra / reply (a reply = the office's answer to our letter → next note).
3. **Make the three files:** Steps 1–7 below, exactly. `instruction`, if set, is Abhi's correction for this run.
4. **Upload the package PDF:** `Artifact` publish with `url` = page URL, `asset: true`, `file_path` = the PDF → output `{kind:"package_pdf", name, store:"asset", ref:<asset id>}`.
5. **Store the Word files** (assets refuse .docx): `python tools/desk_chunks.py <file.docx> <caseId> <study|note_letter> <scratch dir>` → write the chunk files with `ArtifactData` `batch` (op set, collection `outputs`, doc_id = file stem, `file_path`); the tool prints the `outputs[]` record. Overwrite or delete old chunks of the same case/kind first.
6. **Close the case:** `ArtifactData` `update` — `outputs`, `summary` (1 line), `letter_needed`, `essential_points`, `grs` [{code, date, title, pages}], `missing_grs`, `status = "done"`, `stage = "मसुदा तयार"`, `updated_at`, and a `history` entry {at, stage, note}. On error: `status = "failed"` + history note.
7. **Report** in Marathi, 3–4 lines per case (Step 8.2).

## Step 1 — Read the proposal (every page, as images)
1. `pdftoppm -r 110 -png <proposal.pdf> pg/p` and LOOK at every page image. Read stamps, inward nos., handwritten remarks, dates and amounts twice. Unclear → "अस्पष्ट".
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

## Step 4 — Write the note (टिप्पणी) — spec.json
Copy the structure of the nearest sample in `samples/specs/` and fill your facts. Rules:
- **Language (INSTRUCTIONS §4.18, 01.11.2026):** short sentences, one point each, clear subject (who did what); "श्रीमती" (not "सौ."), one space after "श्री."/"श्रीमती"; the person's name as found in the proposal — the Marathi-initials form (e.g. "ह. ना. आपटे") if the proposal has it, otherwise exactly as written there; missing-information list as a table; letter: no "तात्काळ", request form "…उपलब्ध करून देण्यात यावी, ही विनंती." Quotes stay verbatim. lint_spec.py checks this.
- **Marathi forms (INSTRUCTIONS §4.19, 01.11.2026; Marathi Language Dept GR कपासू-2020/प्र.क्र.56/भाषा-2, दि. 10.11.2022):** outside “…” quotes — a space after an abbreviation dot in running text ("दि. 17.09.2026", "क्र. 108", "प्र. क्र. 21/2024"); ":-" never ".:-"; "करून" not "करुन", "प्रारूप" not "प्रारुप". Left exactly: quotes and related extracts, "पृ.N/प.वि." / "पॅकेज PDF पृ. N", file/letter nos. and any token with '/' or '-' ("संकिर्ण-2026/226/प्र.क्र.131/का.6"), the signer chain, date digits, decimals, GR codes. lint_spec.py and verify_outputs.py check this.
- **Para 1:** "<authority> यांच्या पृ.__/प.वि. वरील दि. __ रोजीच्या पत्रास अनुसरून सादर." (or "…पत्रासोबत प्राप्त … पत्रास अनुसरून सादर.")
- **Body:** short numbered paras.
  - Facts, posts, periods and amounts go in TABLES: a `{"table": [[...],[...]], "bold_last": true}` item in `note.paras`.
  - GR/rule text verbatim in “ ” with "(पृ.N/प.वि.)".
  - Earlier record of the same matter = stated as a fact with its reference.
- **Page references:** only "पृ.N/प.वि.", where N = page in the returned PDF (proposal pages 1..n, then the attached GR pages). Never "पॅकेज PDF" in the note body or the letter.
- **Banned words:** no commentary or theory, no arithmetic explanations, no advice. Closed list (checked by `tools/verify_outputs.py` in the note body and the letter; keep both lists identical — 01.11.2026 सुसंगती): "दिसून येते", "असे दिसते", "पडताळणी केली असता", "माझ्या मते", "मला वाटते", "असे वाटते", "ठरवावे", "कदाचित", "बहुधा".
- **Missing information para:** "प्रस्तावासोबत खालील माहिती उपलब्ध नाही:- (1)…; (2)…".
- **Last para, one of:**
  - "सबब, उपरोक्त माहिती तक्त्याच्या स्वरूपात … कळविण्याबाबतच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल."
  - "सबब, … प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."
- **Signers** (`note.signers`, in order): का. अ. (श्रीम. कऱ्हाडे) / अ.स. (श्री. वडनेरकर) / उ.वि.स. नि. उ.स. (श्री. बोंद्रे) / प्र.स. व वि.प. (श्री. खटी). Add "अ.मु.स. (वित्त)" only when the file goes to Finance.
- **`related`** ("संबंधित माहिती (संदर्भासाठी)"): verbatim extracts. Each source ends with exactly "(पॅकेज PDF पृ. N)" (several pages: "(पॅकेज PDF पृ. N-M)" / "(पॅकेज PDF पृ. N,M)"), or "(पॅकेज PDF मध्ये नाही)" when the page is not in the package (01.11.2026 सुसंगती). No repo paths (register/, service-rules/, pdf/ …) and no internal ids in `related`.
- **Letter (`letter`):**
  - `ref_no`: "संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6" (e.g. "संकिर्ण-2026/…"; year = the year of the file no. on the निर्देशपत्र, never copied from a sample); `date`: "__.__.<current year>".
  - `to`; `subject`; `refs` ("आपले पत्र क्र. …, दि. …").
  - `intro`: "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस कळविण्यात येते की, सदर प्रकरणी पुढील कार्यवाहीसाठी खालील माहिती … उपलब्ध करून देण्यात यावी, ही विनंती:-"
  - `points`: an empty table or a few short points.
  - **Table = data only (INSTRUCTIONS §4.20, 02.11.2026):** the table asks only for data to fill in (dates, figures, periods, yes/no, numbers). Documents (copy of an order, report, certificate — "प्रत", "प्रमाणपत्र", "अहवाल") go after the table: a point "	तसेच, खालील कागदपत्रे उपलब्ध करून देण्यात यावीत, ही विनंती:-" then numbered points "1)	… आदेशाची प्रत;". A row mixing both is split (data in the table, the document in the list). Model: CR131 sample. lint_spec.py checks this.
  - **Reminder (INSTRUCTIONS §4.21, 02.11.2026):** `letter.reminder: N` prints "स्मरणपत्र-N" above the क्रमांक line; same file no.; refs[0] "या कार्यासनाचे समक्रमांकाचे पत्र दि. __"; intro "… संदर्भाधीन पत्रान्वये मागविण्यात आलेली माहिती अद्याप अप्राप्त आहे. सदर माहिती लवकरात लवकर शासनास उपलब्ध करून देण्यात यावी, ही विनंती."
  - **Copy line (§4.22):** letter to the High Court asking information "प्रमुख जिल्हा व सत्र न्यायाधीश, <place> यांच्याकडून प्राप्त करून" → `letter.copies: ["प्रमुख जिल्हा व सत्र न्यायाधीश, जिल्हा व सत्र न्यायालय, <place> यांना आवश्यक कार्यवाहीसाठी"]` (printed above "प्रत : निवड नस्ती"). Models: CR122, CR130.
  - **"मा." (§4.23):** own text of note and letter: "मा. उच्च न्यायालय…", "मा. मुंबई उच्च न्यायालय", "मा. मुख्य न्यायमूर्ती / मा. न्यायमूर्ती / मा. प्रशासकीय न्यायाधीश"; not in the addressee block, not in an office designation "उच्च न्यायालय (… शाखा)", not in quotes or related. **"शुद्धिपत्रक" (§4.24).**
  - The tool adds the subject/reference block (bold, centred), "आपला," + signature and "प्रत : निवड नस्ती".
- **Build:** `python3 tools/build_note_letter.py spec.json <outdir> <PREFIX>`. This writes `<PREFIX>_Note_and_Letter.docx` + a PDF preview. LOOK at the preview pages.

## Step 4b — Court cases and order drafts (02.11.2026; research + decisions B1–B10: docs/COURT_AND_ORDERS_RESEARCH.md)
Both are optional keys of the same spec.json; engine detail: tools/ENGINE_PROMPT.md "Court cases and order drafts".
- **Court cases** (GP/AGP/High Court/MAT notice on a writ petition, O.A., contempt, SLP):
  - Note (B9): para 1 "<सहायक सरकारी वकील, …> यांच्या पृ.N/प.वि. वरील दि. __ रोजीच्या पत्रास अनुसरून सादर."; then
    "पार्श्वभूमी थोडक्यात खालीलप्रमाणे आहे:-" and numbered facts with पृ.N/प.वि.
  - Facts suffice → spec `parawise` (English; B8; Rules 1984 Rule 58(3) every point, Rule 58(4) Note (ii) elaborate
    facts + documents enclosed, recommendation oppose / not oppose — from the record only, the one exception to "no opinion"; no record basis → "____" + warning) → `python3 tools/build_parawise.py spec.json <outdir>
    <PREFIX>` → `<PREFIX>_Parawise.docx`; letter to the GP/AGP forwarding it.
  - Essential facts missing → information letter first (§4.15).
  - Rule 58(4): to the GP within two weeks of receipt / before the date in the notice; the hearing date goes in Study part 0.
- **Order drafts** (B7: only when the decision / Finance-GAD concurrence is on record, or Abhi asks): spec `order`
  (gr / corrigendum / circular / memo / notification) → `python3 tools/build_order.py spec.json <outdir> <PREFIX>` →
  `<PREFIX>_Order_Draft.docx`. Note's last para: "सबब, … शासन निर्णयाचे (ज्ञापनाचे / शुद्धिपत्रकाचे / परिपत्रकाचे /
  अधिसूचनेचे) प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर."
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

## Step 7 — Verify (must print ALL OK)
`python3 tools/verify_outputs.py <outdir> <PREFIX> "<package pdf>" <number of proposal pages>`. It prints one line per check (01.11.2026 सुसंगती; tests: `tests/test_verify_outputs.py`):
- fonts: ascii/hAnsi/cs/eastAsia = DVOT-SurekhMR on every text run, incl. headers/footers (Study, note, letter);
- no internal ids (`z<digit>_<4 digits>`) anywhere; no repo paths (register/, service-rules/, precedent-library/, pdf/, repo) in the note/letter;
- every "पृ.N/प.वि." (also lists 5,7, ranges 5-7 / 5 ते 7, Devanagari digits) and "पॅकेज PDF पृ. N" in note, letter and Study is within 1..package pages;
- no "पॅकेज PDF" in the note body or the letter; no banned word (Step 4 list) in the note body or the letter;
- note signer chain = INSTRUCTIONS §4.6 in order; "अ.मु.स. (वित्त)" present only when the last para contains "वित्त विभागाच्या मान्यतेस्तव";
- letter: new page/section; ref no. `संकिर्ण-<year>/<file no>/प्र.क्र.<n>/का.6`; e-mail; विषय/संदर्भ bold + centre; "आपला," (no "आपली,"); "( राजेश वडनेरकर )", "अवर सचिव ,महाराष्ट्र शासन", "प्रत : निवड नस्ती";
- Study headings भाग 0 … भाग 7;
- package: original file name (not `*_Proposal_with_GRs.pdf`); exactly "पृ. i / N" in the bottom strip of every page; bookmarks; page count = proposal + enclosure pages of `<pdf>.map.json` (no separator pages); no mark "TEXT NOT FOUND"/0 hits; no annotation on proposal pages; only Highlight annotations.

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
