# Headless run — one proposal -> three files (used by .github/workflows/process-proposal.yml)

Variables given at run time: PREFIX, PROPOSAL_PDF (inbox/<PREFIX>.pdf), OUTDIR (cases/<PREFIX>), FILE_NO (optional, from inbox/<PREFIX>.json).

Binding: CLAUDE.md (OWNER_RULES.md, INSTRUCTIONS.md, PROPOSAL_WORKFLOW.md) — read them first, in that order. Also tools/PROPOSAL_PROMPT.md, tools/mkdocs.py and tools/pkg3.py docstrings, register/00-INDEX.md.

Rules for this run:
1. Work ONLY on this one proposal. Never use any other proposal in inbox/ or cases/ as a source or precedent.
2. Do exactly what INSTRUCTIONS.md and PROPOSAL_WORKFLOW.md describe — nothing extra. No boxes, no markings or extra work of your own; the proposal scan pages stay unchanged; marking only where pkg3.py puts it on the enclosed GR/rule pages.
3. No interaction is possible: never ask questions. Log doubts (with a provisional default) in Study part 4/7 and carry on.
4. Render every proposal page to PNG (pdftoppm -r 150) and look at each page image before writing anything. Unclear = "अस्पष्ट".
5. Outputs, written into OUTDIR (ASCII names): <PREFIX>_Study.docx, <PREFIX>_Note_and_Letter.docx, <PREFIX>_Proposal_with_GRs.pdf (+ the .map.json from pkg3.py).
6. Verify before finishing: fonts DVOT-SurekhMR on every run, "आपला,", "प्रत : निवड नस्ती", no internal file ids, page stamps and bookmarks in the PDF, every "(पॅकेज PDF पृ. N)" matches the map.
7. Keep scratch work in /tmp, not in the repo. Write OUTDIR/status.json at the end: {"state":"done","summary":"<one Marathi line: what the proposal is>","doubts":["..."],"not_found":["..."]}
8. A needed GR not in pdf/ or pdf/gr/: run `python3 tools/gr_request.py` after adding a `code`/`search` line to tools/gr-request.txt (INSTRUCTIONS §4.14); commit pdf/gr. Only if still not found write "उपलब्ध नाही — मागवावे".
9. Reply in Marathi, in as few words as possible.
