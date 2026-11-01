# Engine run (app B) — one case -> three files. Used by .github/workflows/process-proposal.yml (replaces HEADLESS_PROMPT.md)

Given at run time (end of this prompt): WORKDIR (inputs), OUTDIR (outputs), OLDCASES, PRECEDENT. Working directory =
repo root. CLAUDE.md is NOT loaded in this run (the workflow moves it aside): read only the files named under "Binding".

## Inputs
- `WORKDIR/case.json`: `case` (cr_no, cr_year, file_no, subject, category, employee_name, post, office, received_from,
  received_via, inward_date, stage), `instructions`, `proposal_original_name`, `inputs` (each with `kind`,
  `original_name`, `version`, `local_path` relative to WORKDIR), `files` (all earlier files of the case, metadata only).
- `WORKDIR/in/proposal/<original name>` = the proposal PDF. `WORKDIR/in/extra_doc/` = extra documents of the same case.
  `WORKDIR/in/reply/` = the office's answer to this Section's earlier information-request letter — read it as part of
  the record and prepare the NEXT note on the basis of the proposal + the reply (PROPOSAL_SOP Step 3: letter only if
  essential information is still missing; otherwise the note goes onward for approval).
- `instructions` (if not empty) = the user's correction for this re-run. Follow it exactly, within the binding rules.

## Binding
Read first, in this order, and follow exactly: INSTRUCTIONS.md, PROPOSAL_SOP.md, PROPOSAL_WORKFLOW.md, then
tools/PROPOSAL_PROMPT.md, the docstrings of tools/mkdocs.py, tools/build_note_letter.py, tools/build_study.py,
tools/pkg3.py, tools/highlight.py, tools/verify_outputs.py, tools/oldcases_text.py, and register/00-INDEX.md.
Do NOT read HANDOVER.md (session to-dos, out of scope here) or OWNER_RULES.md (its only part that applies here is
section A: study everything fully first, never guess, nothing of your own — already binding through INSTRUCTIONS §1).
Do PROPOSAL_SOP.md Steps 1–7 exactly as written. **Skip SOP Step 0b (प्रस्ताव कक्ष intake — this app replaces it) and
Step 8 (delivery, saving specs, commit/push — the workflow does the delivery, see below).** Step 0 is done by the
workflow: tools installed; the old-case corpus is already built (SOP Step 0.4) and the precedent library unzipped:
- `OLDCASES/index.tsv` + `OLDCASES/t/NNN.txt` = text of every old case note/letter (output of tools/oldcases_text.py);
  grep the index and texts for the subject (SOP Step 2.5).
- `PRECEDENT/` = precedent-library/Precedent-Library.zip unzipped: read `00-INDEX.docx` first, then the subject folder
  (INSTRUCTIONS §7.1); machine index `precedent-library/idx/*.json` in the repo.
- If a directory is missing or empty, build it yourself the same way (`python3 tools/oldcases_text.py OLDCASES`).
- **Medical reimbursement proposals (वैद्यकीय प्रतिपूर्ती): follow INSTRUCTIONS §8 — `medical-bill/` (`00-INDEX.docx`,
  `Medical-Bill-Samples.docx`, Format-1 / Format-2, `Public-Health-GRs.docx`).**
INSTRUCTIONS.md wins on any conflict.

## Rules for this run
1. Work ONLY on this one case. Never use another case's files as a source; old cases only as precedents (SOP Step 2.5).
2. No interaction is possible: never ask questions. Log every doubt (with a provisional default) in Study part 4 and
   part 7, and carry on. A GR still not found after SOP Step 2.3 goes into `grs_missing` (below) and the note/Study
   say "उपलब्ध नाही — मागवावे".
3. Nothing extra of your own (INSTRUCTIONS §4.13): no boxes, no markings; proposal scan pages unchanged; yellow
   highlights only on the quoted lines of the enclosed GR/rule pages.
4. Progress — run at each milestone (ignore an error from it, it is only the live status):
   `python3 tools/engine_supabase.py step "पाने वाचत आहे"` (Step 1), `"GR शोधत आहे"` (Step 2),
   `"मसुदा तयार करत आहे"` (Steps 3–4, 6), `"PDF बनवत आहे"` (Step 5), `"तपासणी चालू"` (Step 7).
5. Case identity: cr_no, cr_year, file_no, subject and category may be EMPTY in case.json (Abhi may skip them at upload;
   category "इतर" counts as not chosen). Take every empty one from the निर्देशपत्र (proposal page 1) exactly as written there;
   never guess — unreadable = leave it out. Report them in status.json `case` (rule 9).
   PREFIX = `CR<cr_no>_<cr_year>` from case.json, or from the निर्देशपत्र when empty (e.g. CR130_2026). Outputs in OUTDIR, nothing else there except the
   .map.json and LibreOffice previews:
   - `OUTDIR/<PREFIX>_Study.docx` (part 0 briefing + parts 1–7),
   - `OUTDIR/<PREFIX>_Note_and_Letter.docx`,
   - the package PDF under the ORIGINAL proposal file name = `proposal_original_name` exactly (INSTRUCTIONS §4.16;
     strip only a random upload prefix like `11ae057d-`). NEVER `<PREFIX>_Proposal_with_GRs.pdf`.
   Exactly one .pdf in OUTDIR besides `*_Note_and_Letter.pdf` / `*_Study.pdf` previews.
6. Verify (SOP Step 7): `python3 tools/verify_outputs.py OUTDIR <PREFIX> "OUTDIR/<original name>" <proposal pages>`
   must print ALL OK; fix and re-run until it does. Then the second read of every number and date against the page images.
   After you finish, the workflow runs the same command itself (PREFIX, package and proposal pages from status.json) and
   FAILS the case unless it prints ALL OK — so never write status.json "done" without ALL OK.
7. Scratch work in /tmp only, never in the repo. Do NOT git commit or push anything: the workflow commits only new GRs
   in pdf/gr (from tools/gr_request.py, SOP Step 2.3 — the session has internet, run it locally).
   Do not save specs to samples/specs/ (that is done only after Abhi approves).
8. Never print, echo or write any key or environment value (ANTHROPIC_API_KEY, SUPABASE_*).
9. Last action: write `OUTDIR/status.json` (UTF-8, Marathi text):
```json
{"state": "done",
 "summary": "<one Marathi line: what the proposal is and the proposed action>",
 "letter_needed": true,
 "essential_points": ["<each point asked in the letter; [] if no letter>"],
 "grs_attached": [{"code": "<सांकेतांक or rule-book name>", "date": "DD.MM.YYYY", "title": "<title>", "pages": "<package pages, e.g. 12-14>"}],
 "grs_missing": [{"date": "DD.MM.YYYY", "title": "<title as cited>"}],
 "prefix": "CR130_2026",
 "package_pdf": "<the package PDF file name in OUTDIR = proposal_original_name>",
 "proposal_pages": 7,
 "case": {"cr_no": "130", "cr_year": 2026, "file_no": "संकीर्ण-2026/979/प्र.क्र.130/का.6", "subject": "<as on the निर्देशपत्र>",
          "category": "<one of: वेतननिश्चिती, भत्ते, निवृत्तीवेतन, जुनी पेन्शन, विशेष वेतन, विमा/GPF, सेवा, न्यायिक वेतन, वैद्यकीय, इतर>"}}
```
   `prefix`, `package_pdf`, `proposal_pages` = exactly the PREFIX, package file name and proposal page count you gave
   verify_outputs.py (rule 6); the workflow re-runs it with these.
   If the case cannot be completed, write `{"state": "failed", "summary": "<reason>"}` instead.
10. Final reply: Marathi, as few words as possible.
