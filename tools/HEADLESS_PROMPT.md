# Headless run — one proposal -> three files (used by .github/workflows/process-proposal.yml)

Variables given at run time: PREFIX, PROPOSAL_PDF (inbox/<PREFIX>.pdf), OUTDIR (cases/<PREFIX>), FILE_NO (optional, from inbox/<PREFIX>.json), ORIGINAL_NAME (the user's original proposal file name), MODE (study | reminder | cabinet), EXTRA_DOCS (reference material / replies uploaded by the user for THIS proposal — read every one; they are part of this proposal), USER_INSTRUCTIONS (corrections the user asked for on a re-run — follow them), PREVIOUS_OUTPUTS (earlier versions of this proposal's outputs, if any).

Binding: CLAUDE.md (OWNER_RULES.md, INSTRUCTIONS.md, PROPOSAL_SOP.md, PROPOSAL_WORKFLOW.md) — read them first, in that order; follow PROPOSAL_SOP.md step by step. Also tools/PROPOSAL_PROMPT.md, tools/mkdocs.py and tools/pkg3.py docstrings, register/00-INDEX.md.

Rules for this run:
1. Work ONLY on this one proposal. Never use any other proposal in inbox/ or cases/ as a source or precedent.
2. Do exactly what INSTRUCTIONS.md and PROPOSAL_WORKFLOW.md describe — nothing extra. No boxes, no markings or extra work of your own; the proposal scan pages stay unchanged; marking only where pkg3.py puts it on the enclosed GR/rule pages.
3. No interaction is possible: never ask questions. Log doubts (with a provisional default) in Study part 4/7 and carry on.
4. Render every proposal page to PNG (pdftoppm -r 150) and look at each page image before writing anything. Unclear = "अस्पष्ट".
5. Outputs, written into OUTDIR: <PREFIX>_Study.docx, <PREFIX>_Note_and_Letter.docx, and the returned proposal PDF named exactly ORIGINAL_NAME (INSTRUCTIONS §4.16; + the .map.json from pkg3.py).
6. Verify before finishing (PROPOSAL_SOP Step 7): `python3 tools/verify_outputs.py OUTDIR PREFIX "OUTDIR/ORIGINAL_NAME" <proposal pages>` must print ALL OK.
7. Keep scratch work in /tmp, not in the repo. Write OUTDIR/status.json at the end: {"state":"done","summary":"<one Marathi line: what the proposal is>","doubts":["..."],"not_found":["..."]}
8. A needed GR not in pdf/ or pdf/gr/: run `python3 tools/gr_request.py` after adding a `code`/`search` line to tools/gr-request.txt (INSTRUCTIONS §4.14); commit pdf/gr. Only if still not found write "उपलब्ध नाही — मागवावे".
9. Reply in Marathi, in as few words as possible.

Dashboard additions (proposal desk):
10. Progress: at each phase write ONE word into OUTDIR/progress.txt (overwrite): reading → searching_grs → drafting → building_pdf → verifying. The dashboard shows it live.
11. In OUTDIR/status.json also write: "letter_needed": true/false, "essential_points": ["..."] (the points the letter asks for; [] if no letter), "grs_attached": [{"code":"...","label":"...","first_page":N}], "grs_missing": ["..."], and "briefing": {"bullets": ["..."] (Study part 0, same words), "burden": [{"name":"<establishment>","amount":<rupees>}] or [], "periods": [{"label":"...","from":"YYYY-MM-DD","to":"YYYY-MM-DD","type":"service"|"break"}] or [], "claims": [{"item":"...","claimed":<rupees>,"admissible":<rupees or null>}] or []}. Only facts already in the Study; empty lists when the proposal has no such data.
12. MODE=reminder: do not redo the Study. Using PREVIOUS_OUTPUTS (the earlier Note_and_Letter), draft only a reminder letter (स्मरणपत्र) in the Section's letter format (tools/templates/LETTER_TEMPLATE.docx) to OUTDIR/<PREFIX>_Reminder.docx, citing the earlier letter's number and date. status.json: {"state":"done","summary":"..."}.
13. MODE=cabinet: using the Study and Note in PREVIOUS_OUTPUTS, draft a cabinet note (मंत्रिमंडळ टिप्पणी) to OUTDIR/<PREFIX>_Cabinet_Note.docx, font DVOT-SurekhMR. Take its format ONLY from the official manuals in pdf/08-gad-office-procedure/ (Maharashtra Office Procedure Manual 2023, कार्यालयीन कार्यपद्धती नियमपुस्तिका, कार्यनियमावली) — find the cabinet-note format there and follow its headings exactly, citing the manual and page in Study-style doubts. If the format is not found there, write "मंत्रिमंडळ टिप्पणीचा अधिकृत नमुना संग्रहात उपलब्ध नाही" in status.json doubts and do not invent one. Tables only, no charts.
