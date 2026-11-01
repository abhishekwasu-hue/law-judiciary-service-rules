# Build prompt A — "प्रस्ताव कक्ष" (Proposal Desk) page inside claude.ai
Give this whole file, as one message, to a NEW Claude session (claude.ai or Claude Code) that has the Artifact tool.
UI text in Marathi (Devanagari); code in English.

---

## 0. Before building
1. Add the GitHub repo `abhishekwasu-hue/law-judiciary-service-rules` (main) and clone it.
2. Read, in this order: `CLAUDE.md`, `OWNER_RULES.md`, `INSTRUCTIONS.md`, `PROPOSAL_SOP.md`, `HANDOVER.md`.
3. The page is the front desk of that procedure: proposals come IN through the page, and the three output files go OUT through the page.

## 1. What to build — and what NOT to build
- **Build:** one hand-written HTML artifact page with runtime capabilities. It must actually upload, store, list and download files.
- **Do NOT use the "Dashboard" Artifact type.** It cannot upload or download files; an earlier attempt failed because of this.
- **Do NOT make a mock-up** or fill the page with sample data.
- **Load skills first:** `artifact-capabilities` (read the `.d.ts` files of `db`, `assets`, `downloads`, `user`) and the page-design guidance (quickstart, intent "other"). Do this before writing code.

## 2. Capabilities
`{"assets": {}, "db": {}, "downloads": true, "user": {"scopes": ["profile"]}}`

## 3. Storage design (mandatory — platform limits)
- **`assets`:** accepts PDF, images and text files only, up to 20 MiB each. It does NOT accept .docx. Use it for:
  - the proposal PDFs and extra documents uploaded by the user (input);
  - the returned "proposal with GRs" PDF (output).
- **Word outputs** (`<PREFIX>_Study.docx`, `<PREFIX>_Note_and_Letter.docx`): store them in `db` as base64 text.
  - Chunk documents: `outputs/<caseId>__<kind>__<n>`, with fields `{case, kind, n, total, name, b64}`, each chunk < 200 KiB (the db document cap is 256 KiB).
  - On download, the page reassembles the chunks into a Blob and calls `downloads.save({filename, data: blob})`.
- **`db` collection `cases/<caseId>`:**
  - Identity: `cr`, `year`, `file_no` (निर्देशपत्र), `subject`, `category` (वेतननिश्चिती / भत्ते / निवृत्तीवेतन / जुनी पेन्शन / विशेष वेतन / विमा-GPF / सेवा / न्यायिक वेतन / वैद्यकीय / इतर), `priority`.
  - Workflow: `stage` (प्राप्त → अभ्यास चालू → मसुदा तयार → वरिष्ठांकडे सादर → पत्र पाठवले (उत्तर प्रतीक्षेत) → माहिती प्राप्त → वित्त/सा.प्र.वि. कडे → अभिप्राय प्राप्त → निर्गमित → बंद), `status` (queued | processing | done | failed), `reply_due`.
  - Files: `inputs: [{asset_id, name, size}]` (keep the ORIGINAL file name), `outputs: [{kind: study|note_letter|package_pdf, name, store: "asset"|"db", ref}]`.
  - Results: `summary` (1 line), `letter_needed` (bool), `essential_points: []`, `grs: [{code, date, title, pages}]`, `missing_grs: []`.
  - Housekeeping: `instruction` (the user's text for a re-run), `history: [{at, stage, note}]`, `created_at`, `updated_at`.
- Never hard-code records in the page. Show a designed empty state when the store is empty.

## 4. Screens (single page, mobile-first, ≥ 400 px clean)
1. **Header.** Name "प्रस्ताव कक्ष". KPI chips (count per stage; red chip for replies past `reply_due`). A primary "+ नवीन प्रस्ताव" button.
2. **New proposal form.** On submit, the case gets status `queued`, and the page shows: "प्रकरण नोंदले. Claude ला सांगा: 'प्रस्ताव कक्षातील नवीन प्रस्ताव तयार कर'".
   - **Files:** drag-and-drop or picker for the proposal PDF (required) and extra documents (optional). Show a progress bar per file.
   - **Fields:** C R no., year, file no., subject, category, priority, and an optional instruction box.
3. **Case list.** Cards on mobile, a table on desktop. Search; filters by stage, category and year. A pill shows each case's status. Each card shows:
   - the summary;
   - the letter yes/no flag and the essential points;
   - attached GRs, and "सांकेतांक हवा" for missing GRs;
   - **three download buttons** when `status = done`: "अभ्यास", "टिप्पणी व पत्र", "GR सह प्रस्ताव";
   - "स्थिती बदला" (stage select, adds a history entry);
   - "सुधारणा करून पुन्हा तयार करा" (text box → `instruction`, `status = queued`);
   - "उत्तर जोडा" (upload a reply PDF → `stage = माहिती प्राप्त`, `status = queued`);
   - a history timeline.
4. **Small charts.** Hand-drawn inline SVG: cases by stage (bar) and by category (donut), from `db` only.
5. **Footer hint:** how processing works (one line).

## 5. Design
- **Look:** calm, professional government look. Deep navy with a restrained saffron accent. Fonts: Mukta for body text and Tiro Devanagari Marathi for headings (Google Fonts, with fallbacks).
- **Theme:** light and dark themes through tokens.
- **Status colors by meaning:** green = done, amber = waiting, red = overdue/failed, blue = processing.
- **Mobile:** no horizontal scroll; tap targets ≥ 44 px.
- **Rendering data:** render values with `textContent`, never `innerHTML`.

## 6. After publishing — how Claude processes a queued case (write this into the repo's PROPOSAL_SOP.md as "Step 0b — intake from प्रस्ताव कक्ष")
1. **Find queued cases:** `ArtifactData` `query` collection `cases` where `status == "queued"`, then set `status = processing`.
2. **Get the inputs:** for each input asset, `Artifact` `read` with `url` = page URL and `path` = asset id. This saves the PDF locally; restore its original file name.
3. **Make the three files:** run `PROPOSAL_SOP.md` Steps 1–7 exactly. The `instruction` field, if set, is the user's correction.
4. **Upload the package PDF:** `Artifact` publish with `url` = page URL, `asset: true`, `file_path` = the PDF. Note the returned id.
5. **Store the Word files:** base64-encode each .docx, split it into < 200 KiB chunks, and write them with an `ArtifactData` `batch` to `outputs/...`.
6. **Close the case:** `ArtifactData` `update` the case — `outputs`, `summary`, `letter_needed`, `essential_points`, `grs`, `missing_grs`, `status = done`, `stage = मसुदा तयार`, plus a `history` entry.
7. **Report:** tell the user in Marathi, in 3–4 lines per case.

## 7. Verify (one pass, then hand over)
- Publish.
- Then do a real end-to-end test with one small sample PDF:
  - upload it through the page logic, or seed one case + asset yourself;
  - process it per §6;
  - confirm all three downloads reassemble (list the `outputs` chunks; check the .docx opens with python-docx);
  - delete the test case afterwards.
- Report what was exercised.
- Commit `PROPOSAL_SOP.md` Step 0b and `HANDOVER.md` updates to the repo, with the page URL.
