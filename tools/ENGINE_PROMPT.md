# Engine run (app B) — one case -> three files. Used by .github/workflows/process-proposal.yml (replaces HEADLESS_PROMPT.md)

Given at run time (end of this prompt): WORKDIR (inputs), OUTDIR (outputs). Working directory = repo root.

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
Read first, in this order, and follow exactly: CLAUDE.md (OWNER_RULES.md, INSTRUCTIONS.md, PROPOSAL_SOP.md,
PROPOSAL_WORKFLOW.md, HANDOVER.md), then tools/PROPOSAL_PROMPT.md, the docstrings of tools/mkdocs.py,
tools/build_note_letter.py, tools/build_study.py, tools/pkg3.py, tools/highlight.py, tools/verify_outputs.py, and
register/00-INDEX.md. Do PROPOSAL_SOP.md Steps 1–7 exactly as written (Step 0 tools are already installed; Step 8
delivery is done by the workflow, see below). INSTRUCTIONS.md wins on any conflict.

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
5. PREFIX = `CR<cr_no>_<cr_year>` from case.json (e.g. CR130_2026). Outputs in OUTDIR, nothing else there except the
   .map.json and LibreOffice previews:
   - `OUTDIR/<PREFIX>_Study.docx` (part 0 briefing + parts 1–7),
   - `OUTDIR/<PREFIX>_Note_and_Letter.docx`,
   - the package PDF under the ORIGINAL proposal file name = `proposal_original_name` exactly (INSTRUCTIONS §4.16;
     strip only a random upload prefix like `11ae057d-`). NEVER `<PREFIX>_Proposal_with_GRs.pdf`.
   Exactly one .pdf in OUTDIR besides `*_Note_and_Letter.pdf` / `*_Study.pdf` previews.
6. Verify (SOP Step 7): `python3 tools/verify_outputs.py OUTDIR <PREFIX> "OUTDIR/<original name>" <proposal pages>`
   must print ALL OK; fix and re-run until it does. Then the second read of every number and date against the page images.
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
 "grs_missing": [{"date": "DD.MM.YYYY", "title": "<title as cited>"}]}
```
   If the case cannot be completed, write `{"state": "failed", "summary": "<reason>"}` instead.
10. Final reply: Marathi, as few words as possible.
