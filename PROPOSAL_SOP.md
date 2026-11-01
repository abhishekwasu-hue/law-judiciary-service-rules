# PROPOSAL_SOP.md — step-by-step procedure for every proposal (binding; any model, any session)

Owner: Abhi, Section Officer (कार्यासन अधिकारी), Law & Judiciary Department, Desk-6 (कार्यासन-6), Govt of Maharashtra.
When he sends a proposal PDF, do ALL steps below without asking. He must never have to explain this again.
The rules are in INSTRUCTIONS.md §4 (items 1–17); this file is the order of work + the tools. If anything here conflicts with
INSTRUCTIONS.md, INSTRUCTIONS.md wins. Reply to him in Marathi, few words.

The quality standard = the approved notes in `samples/specs/` (C R 66, 122, 128, 130, 131, 133 of 2026). Match them.

---

## Step 0 — Before starting
1. Read OWNER_RULES.md, INSTRUCTIONS.md, this file. Several proposals in one message = separate cases; never mix them.
2. Make a task list (one task per proposal).
3. Tools needed: `pip install pymupdf docxcompose python-docx --break-system-packages`; `soffice` (LibreOffice) and `tesseract` are used for checking/OCR.
4. Build the old-case text corpus once per session: `python3 tools/oldcases_text.py /tmp/old` (grep `/tmp/old/index.tsv`).

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
   - **Mirror gaps:** the archive.org mirror lacks many 2026 and some older Law & Judiciary GRs, and the GR site's search has a captcha. If a GR is still not found, ask Abhi for its सांकेतांक in ONE line and continue with everything else.
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
- **Para 1:** "<authority> यांच्या पृ.__/प.वि. वरील दि.__ रोजीच्या पत्रास अनुसरुन सादर." (or "…पत्रासोबत प्राप्त … पत्रास अनुसरुन सादर.")
- **Body:** short numbered paras.
  - Facts, posts, periods and amounts go in TABLES: a `{"table": [[...],[...]], "bold_last": true}` item in `note.paras`.
  - GR/rule text verbatim in “ ” with "(पृ.N/प.वि.)".
  - Earlier record of the same matter = stated as a fact with its reference.
- **Page references:** only "पृ.N/प.वि.", where N = page in the returned PDF (proposal pages 1..n, then the attached GR pages). Never "पॅकेज PDF" in the note body.
- **Banned words:** no commentary or theory — no "दिसून येते", "पडताळणी केली असता", "माझ्या मते", no arithmetic explanations, no "ठरवावे" advice.
- **Missing information para:** "प्रस्तावासोबत खालील माहिती उपलब्ध नाही.:- (1)…; (2)…".
- **Last para, one of:**
  - "सबब, उपरोक्त माहिती तक्त्याच्या स्वरूपात … कळविण्याबाबतच्या पत्राचे प्रारुप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र निर्गमित करण्यात येईल."
  - "सबब, … प्रस्ताव वित्त विभागाच्या मान्यतेस्तव सादर करण्यात येत आहे."
- **Signers** (`note.signers`, in order): का. अ. (श्रीम. कऱ्हाडे) / अ.स. (श्री. वडनेरकर) / उ.वि.स. नि. उ.स. (श्री. बोंद्रे) / प्र.स. व वि.प. (श्री. खटी). Add "अ.मु.स. (वित्त)" only when the file goes to Finance.
- **`related`** ("संबंधित माहिती (संदर्भासाठी)"): verbatim extracts. Each source ends with "पॅकेज PDF पृ. N".
- **Letter (`letter`):**
  - `ref_no`: "संकिर्ण-2026/<file no>/प्र.क्र.<n>/का.6"; `date`: "__.__.2026".
  - `to`; `subject`; `refs` ("आपले पत्र क्र.…, दि.…").
  - `intro`: "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरुन आपणांस कळविण्यात येते की, सदर प्रकरणी पुढील कार्यवाहीसाठी खालील माहिती … उपलब्ध करुन देण्यात यावी.:-"
  - `points`: an empty table or a few short points.
  - The tool adds the subject/reference block (bold, centred), "आपला," + signature and "प्रत : निवड नस्ती".
- **Build:** `python3 tools/build_note_letter.py spec.json <outdir> <PREFIX>`. This writes `<PREFIX>_Note_and_Letter.docx` + a PDF preview. LOOK at the preview pages.

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
`python3 tools/verify_outputs.py <outdir> <PREFIX> "<package pdf>" <number of proposal pages>`. It checks:
- fonts (DVOT-SurekhMR on every run);
- letter ending;
- no internal ids;
- no "पॅकेज PDF" in the note body;
- every पृ./प.वि. is within the package;
- page stamps and bookmarks;
- no annotation on proposal pages;
- only Highlight annotations.

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
