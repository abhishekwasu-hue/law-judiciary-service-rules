# Engine run (app B) — one case -> three files. Used by .github/workflows/process-proposal.yml (replaces HEADLESS_PROMPT.md)

Given at run time (end of this prompt): WORKDIR (inputs), OUTDIR (outputs), OLDCASES, PRECEDENT, MODEL, MODEL_LIGHT,
MODEL_STRONG (empty = no escalation tier), BUDGET_USD (soft). Working directory =
repo root. CLAUDE.md is NOT loaded in this run (the workflow moves it aside). Prompt layout (stable first, for prompt
caching): this file, then tools/ENGINE_BRIEF.md, then the tool docstrings, then the run variables (last).

## Inputs
- `WORKDIR/case.json`: `case` (cr_no, cr_year, file_no, subject, category, employee_name, post, office, received_from,
  received_via, inward_date, stage), `instructions`, `proposal_original_name`, `inputs` (each with `kind`,
  `original_name`, `version`, `local_path` relative to WORKDIR), `files` (all earlier files of the case, metadata only).
- `WORKDIR/in/proposal/<original name>` = the proposal PDF. `WORKDIR/in/extra_doc/` = extra documents of the same case.
  `WORKDIR/in/reply/` = the office's answer to this Section's earlier information-request letter — read it as part of
  the record and prepare the NEXT note on the basis of the proposal + the reply (PROPOSAL_SOP Step 3: letter only if
  essential information is still missing; otherwise the note goes onward for approval).
- `instructions` (if not empty) = the user's correction for this re-run. Follow it exactly, within the binding rules.
- `WORKDIR/pages/` = the proposal already split by the workflow (tools/prep_pages.py): `p-NN.png` (110 dpi — the image
  every page is read from), `p-NN.sm.png` (80 dpi — only for your own look at rendered GR/package pages, never for
  reading the proposal), `p-NN.txt` (text layer), `p-NN.ocr.txt` (tesseract OCR, lang in `pages.json` `ocr_lang`),
  `pages.json` (`files[]`: `png`, `png_small`, `txt`, `ocr`; `has_text_layer[]`). Reply PDFs:
  `WORKDIR/pages_reply_<n>/` (same layout; `pages.json` `pdf` = file). Missing/incomplete -> render yourself
  (`python3 tools/prep_pages.py <pdf> <dir>`). Text layer / OCR are a first pass and cross-check only: every number,
  date, name and amount comes from the IMAGE (read by the drafter); where they differ, the image wins.

## Model tiers — who does what (quality first; cost is saved only where quality is unaffected)
You are the ORCHESTRATOR and run on the mechanical tier (MODEL_LIGHT). Every quality-critical task is delegated with
the Agent tool to the subagent `drafter` (main tier = MODEL, the Opus-class model that produced the approved outputs).
A subagent `drafter_strong` (MODEL_STRONG) exists only when configured. Quality-critical work is NEVER done by you and
NEVER moved down a tier for cost: the budget is SOFT (going over it only adds a warning; never stop or degrade).

| Task | Tier | Why quality is unaffected |
|---|---|---|
| Text layer / OCR read, GR citations list, GR search + fetch (gr_request.py), precedent grep, candidate GR page text | you (light) | finding/fetching only; nothing quoted or decided by you |
| Facts list from the page IMAGES (numbers, dates, names, stamps, handwriting) | drafter (main) | same tier as the approved outputs; every page image |
| Letter or not; GR selection; verbatim quotes; enclosures.json marks; note + letter spec; Study parts 0, 2, 3, 4, 7 | drafter (main) | same tier |
| Study part 1 page rendering | helper run (light), then `part1check` vs the drafter's facts | kept only when every number/date/name matches; failing pages are redone by drafter |
| pkg3 / highlight / build_note_letter / build_study / lint / verify runs; Study parts 5–6 copied from the spec; page numbers from map.json | you (light) | scripts; results machine-checked (LINT OK, ALL OK) |
| Fixing lint/verify lines | you, max 2 attempts; then drafter | content fixes go up after 2 failed attempts |

### Order
1. Read the TEXT of all pages in ONE Bash call (`.txt` where `has_text_layer`, else `.ocr.txt`), case.json, inputs.
   Do SOP Step 2 search work: list the GRs/rules/orders cited (from the text), look them up (pdf/gr/INDEX.tsv,
   register/, service-rules/, pdf/), fetch missing ones (brief rules; tools/gr_request.py), grep OLDCASES and
   PRECEDENT for the subject. Write `/tmp/work/candidates.md`: per candidate GR — code, date, title, repo path, and
   the text of the pages that may hold the needed para (pymupdf text, page numbers); precedent hits (file, lines).
   Never decide which GR applies or quote anything yourself.
2. Delegate D1 to `drafter` (ONE Agent call; give paths, not content): "Read the brief and TOOL_DOCS. LOOK at every
   proposal page image WORKDIR/pages/p-NN.png (full 110 dpi; several Reads per message); reply PDFs likewise. Write
   /tmp/work/facts.json (format below) — every number/date/name/amount from the IMAGE, `clear:false` where not sure.
   Using /tmp/work/candidates.md, the GR PDFs and precedents: decide letter or not, select the GR pages, write
   /tmp/work/enclosures.json (pkg3 format; marks = exact text lines unique on the page), /tmp/work/spec.json (note +
   letter + related; पृ.N computed from the package order: proposal pages 1..n, then the enclosure pages in order),
   /tmp/work/study_core.json (parts 0, 2, 3, 4, 7 as build_study blocks), /tmp/work/status_core.json (summary,
   letter_needed, essential_points, grs_attached, grs_missing, case). List unclear pages in facts.json `unclear`."
   facts.json = `{"pages": n, "facts": [{"page": N, "document": "...", "items": [{"what": "...", "value": "<as on
   the image>", "clear": true}]}], "unclear": ["<page: what>"]}`.
3. Build: pkg3 -> compare `<pdf>.map.json` with the drafter's पृ.N (fix only page numbers, mechanically); assemble
   study.json = part 0 + part 1 + parts 2–4 + part 5 (note text from spec) + part 6 (letter text from spec) + part 7;
   lint; build_note_letter; build_study; verify. Progress steps (rule 4) as before.

### Study part 1
- Wait for `/tmp/work/study_part1.done` / `.failed` with ONE Bash loop (Bash timeout 600000 ms, at most 4 calls).
- `.done` + valid -> `python3 tools/engine_supabase.py part1check /tmp/work/facts.json /tmp/work/study_part1.json`.
  PART1 OK -> insert UNCHANGED as parts[1]. MISMATCH lines -> delegate to `drafter`: redo exactly those pages of
  part 1 from the images (or all of part 1 if more than a third of the pages fail) and log the escalation.
- `.failed` / invalid / missing -> delegate the whole of part 1 to `drafter` (rule (c) below).

### Escalation rules (one way up; log every one)
(a) Facts: a page in facts.json `unclear`, an item `clear:false`, or a handwritten/stamp page whose OCR is empty —
    the drafter already reads at the main tier; if it still reports the page unclear and `drafter_strong` exists,
    delegate ONLY those pages to `drafter_strong` (full image, crop/zoom by rendering at higher dpi with pymupdf).
    Still unclear -> "अस्पष्ट".
(b) lint / verify still failing after 2 fix attempts by you -> `drafter` (give the printed lines + file paths); still
    failing after 2 drafter attempts -> `drafter_strong` if it exists.
(c) A cheap-tier output fails its structural check (study_part1.json invalid, part1check MISMATCH) -> `drafter`.
Never move a task down. Budget is SOFT: never skip an escalation for cost; the workflow records the warning.
Log in status.json `model_log` (list): `{"task": "<Marathi, e.g. भाग 1 पान 3>", "from": "<model id>", "to": "<model id>",
"reason": "<Marathi, e.g. हस्तलेख अस्पष्ट / lint 2 वेळा अयशस्वी / part1check जुळले नाही>"}` — also the fixed routing:
one entry `{"task": "तथ्ये, नोंद, पत्र, GR उतारे, भाग 0", "from": "", "to": MODEL, "reason": "मुख्य (दर्जा)"}` and one
`{"task": "भाग 1 + साधने", "from": "", "to": MODEL_LIGHT, "reason": "यांत्रिक"}`. Model ids are in the run variables.

### Cost rules (they never override a quality rule)
- Few turns: independent tool calls in ONE message; shell steps combined in one Bash call; each JSON in one Write.
- Limit output (`| head -60`, `grep -m`, `cut -c1-300`); never cat a whole large file, PDF dump or zip listing.
- The brief (tools/ENGINE_BRIEF.md) and the tool docstrings (/tmp/work/TOOL_DOCS.md) are below / in /tmp/work: do not
  Read the tool .py files or the full rule files, except a grep of one exact item on a real doubt.
- Never Read the same file twice. Give subagents file paths, never paste file contents into the delegation.

## Lint before building
Before every build run `python3 tools/lint_spec.py spec.json --study study.json --pages <package pages>` (docstring in
tools/lint_spec.py; same checks as verify_outputs.py) and fix every line it prints until "LINT OK".
build_note_letter.py and build_study.py lint again themselves and exit 1 on a rule problem.

## Binding
The binding rules are `tools/ENGINE_BRIEF.md` (appended BELOW this prompt; subagents Read the file) and the tool
docstrings (appended below and saved as /tmp/work/TOOL_DOCS.md). Full rule files (INSTRUCTIONS.md, PROPOSAL_SOP.md,
PROPOSAL_WORKFLOW.md, tools/PROPOSAL_PROMPT.md) stay the authority: grep the exact item on a real doubt; INSTRUCTIONS.md
wins on any conflict. register/00-INDEX.md = index of verified extracts. Do NOT read HANDOVER.md or OWNER_RULES.md.
Do PROPOSAL_SOP.md Steps 1–7 through the tier split above. **Skip SOP Step 0b and Step 8 (the workflow delivers).**
Step 0 is done by the workflow:
- `OLDCASES/index.tsv` + `OLDCASES/t/NNN.txt` = text of every old case note/letter (tools/oldcases_text.py).
- `PRECEDENT/` = precedent-library/Precedent-Library.zip unzipped: `00-INDEX.docx` first (python-docx text), then
  the subject folder; machine index `precedent-library/idx/*.json`.
- Missing/empty -> build it yourself the same way (`python3 tools/oldcases_text.py OLDCASES`).
- **Medical reimbursement proposals (वैद्यकीय प्रतिपूर्ती): INSTRUCTIONS §8 — `medical-bill/`** (the drafter uses the
  same-type sample wording).

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
     strip only a random upload prefix like `11ae057d-`). Never invent a new name such as `<PREFIX>_Proposal_with_GRs.pdf`
     — but when the original name itself looks machine-made (e.g. the uploaded file really is `CR66_Proposal_with_GRs.pdf`
     or `..._0001.pdf`), keep it exactly as uploaded; never "correct" it.
   Exactly one .pdf in OUTDIR besides `*_Note_and_Letter.pdf` / `*_Study.pdf` previews.
6. Verify (SOP Step 7): `python3 tools/verify_outputs.py OUTDIR <PREFIX> "OUTDIR/<original name>" <proposal pages> --original-name "<proposal_original_name>"`
   must print ALL OK; fix and re-run until it does. Then the second read of every number and date in the note, letter
   and Study part 0 against the page images — delegated to `drafter` (main tier; it fixes only wrong numbers/dates).
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
 "model_log": [{"task": "तथ्ये, नोंद, पत्र, GR उतारे, भाग 0", "from": "", "to": "<MODEL>", "reason": "मुख्य (दर्जा)"}],
 "case": {"cr_no": "130", "cr_year": 2026, "file_no": "संकीर्ण-2026/979/प्र.क्र.130/का.6", "subject": "<as on the निर्देशपत्र>",
          "category": "<one of: वेतननिश्चिती, भत्ते, निवृत्तीवेतन, जुनी पेन्शन, विशेष वेतन, विमा/GPF, सेवा, न्यायिक वेतन, वैद्यकीय, इतर>"}}
```
   `prefix`, `package_pdf`, `proposal_pages` = exactly the PREFIX, package file name and proposal page count you gave
   verify_outputs.py (rule 6); the workflow re-runs it with these.
   If the case cannot be completed, write `{"state": "failed", "summary": "<reason>", "model_log": [...]}` instead.
   `model_log` = the routing/escalation log (see "Escalation rules"); always included.
10. Final reply: Marathi, as few words as possible.
