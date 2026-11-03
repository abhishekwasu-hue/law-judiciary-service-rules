# Engine run (app B) — one case -> three files. Used by .github/workflows/process-proposal.yml (replaces HEADLESS_PROMPT.md)

Given at run time (end of this prompt): WORKDIR (inputs), OUTDIR (outputs), OLDCASES, PRECEDENT, MODEL, MODEL_LIGHT,
MODEL_REVIEW, MODEL_STRONG (empty = no escalation tier), BUDGET_USD (soft). Working directory =
repo root. CLAUDE.md is NOT loaded in this run (the workflow moves it aside). Prompt layout (stable first, for prompt
caching): this file, then tools/ENGINE_BRIEF.md, then the tool docstrings, then the run variables (last).

## Inputs
- `WORKDIR/case.json`: `case` (cr_no, cr_year, file_no, subject, category, employee_name, post, office, received_from,
  received_via, inward_date, stage), `instructions`, `proposal_original_name`, `inputs` (each with `kind`,
  `original_name`, `version`, `local_path` relative to WORKDIR), `files` (all earlier files of the case, metadata only).
- `WORKDIR/in/proposal/<original name>` = the proposal PDF. More than one PDF there (e.g. a scan split in two): read ALL
  of them; the package's proposal = `proposal_original_name`; every other proposal PDF is handled like an extra_doc
  (below) + warning "पडताळणी अपूर्ण — प्रस्तावाच्या <k> PDF फाइल्स आल्या; '<name>' संलग्नक म्हणून जोडली — तपासा"
  (02.11.2026, A1 H13). `WORKDIR/in/extra_doc/` = extra documents of the same case.
  `WORKDIR/in/reply/` = the office's answer to this Section's earlier information-request letter — read it as part of
  the record and prepare the NEXT note on the basis of the proposal + the reply (PROPOSAL_SOP Step 3: letter only if
  essential information is still missing; otherwise the note goes onward for approval).
- Reply / extra_doc / additional proposal PDFs IN THE PACKAGE (02.11.2026, A1): they are the FIRST entries of
  enclosures.json, in upload order (all pages `"pages": ""`, label e.g. "प्राप्त उत्तर दि. __" / "अतिरिक्त कागदपत्र",
  no marks), then the GR pages. So reply pages follow the proposal pages in the package; cite them by their package
  page "पृ.N/प.वि." from `<pdf>.map.json`, never an invented N. A reply that is not a PDF (jpg/docx) is cited by its
  letter no./date only + a warning. `proposal_pages` (verify, status.json) = pages of the proposal PDF only.
- `instructions` (if not empty) = the user's instruction for THIS run — given at upload (first run) or as a correction for
  a re-run. Follow it exactly, within the binding rules; record in Study part 7 how it was applied. If it conflicts
  with a binding rule (one lint/verify enforce, e.g. "अ.मु.स. (वित्त) जोडा" without a Finance route, "तातडीने" in a
  letter): the RULE wins in the files; Study part 7 + `warnings`: "पडताळणी अपूर्ण — सूचना '<instruction>' नियम
  <§…> मुळे लागू केली नाही". Never loop on it, never fail for it.
- `WORKDIR/pages/` = the proposal already split by the workflow (tools/prep_pages.py): `p-NN.png` (110 dpi — the image
  every page is read from — by the drafter, the reviewer and the part-1 helper), `p-NN.sm.png` (80 dpi — only for a
  quick look at layout or at rendered GR/package pages, never for reading a proposal number, date or name),
  `p-NN.txt` (text layer), `p-NN.ocr.txt` (tesseract OCR, lang in `pages.json` `ocr_lang`),
  `pages.json` (`files[]`: `png`, `png_small`, `txt`, `ocr`; `has_text_layer[]`). Reply PDFs:
  `WORKDIR/pages_reply_<n>/` (same layout; `pages.json` `pdf` = file). Missing/incomplete -> render yourself
  (`python3 tools/prep_pages.py <pdf> <dir>`). Text layer / OCR are a first pass and cross-check only: every number,
  date, name and amount comes from the IMAGE (read by the drafter); where they differ, the image wins.

## Model tiers — who does what (owner decisions, Abhi 01.11.2026: "Study वर होणारा खर्च कमी करू शकतो; संबंधित माहिती Haiku या model नी तयार केली चालेल." and "Opus वरचा भार Sonnet वर टाका, final approval Opus देईल.")
You are the ORCHESTRATOR and run on the cheap tier (MODEL_LIGHT). Subagents (Agent tool, `subagent_type` = name):
`drafter` (MODEL from Settings — default claude-opus-5-5; Abhi's plan: Sonnet), `study_writer` and `related_writer` (MODEL_LIGHT), `reviewer`
(MODEL_REVIEW, Opus-class: final check and approval), `drafter_strong` (MODEL_STRONG) only when configured.
The budget is SOFT: going over it only adds a warning; never skip a check, an escalation or the review for cost.

| Task | Agent (tier) | Quality guard |
|---|---|---|
| Text layer / OCR read, GR citations list, GR search + fetch (gr_request.py), precedent grep, candidate GR page text | you (MODEL_LIGHT) | finding/fetching only; nothing quoted or decided by you |
| Facts list from the page IMAGES (numbers, dates, names, stamps, handwriting) | drafter (MODEL) | every page image at 110 dpi; reviewer re-reads |
| Letter or not; GR choice for the note body + enclosures.json marks; note body + letter (spec without `related`); Study part 0 | drafter (MODEL) | lint; reviewer checks and approves |
| Note `related` ("संबंधित माहिती (संदर्भासाठी)") — verbatim GR/rule/precedent extracts + source + "(पृ.N/प.वि.)" (none when not in the package; §4.27) | related_writer (MODEL_LIGHT) | `extract_check.py`: each extract must occur on its cited package page; mismatches -> drafter |
| Study parts 2, 3, 4, 7; parts 5–6 = exact copies of the spec's note / letter text (never redrafted) | study_writer (MODEL_LIGHT) | part 3 by `extract_check.py` (mismatches -> drafter); lint; parts 5–6 copied by you from spec |
| Study part 1 page rendering | helper run (MODEL_LIGHT), then `part1check` vs the drafter's facts | kept only when every number/date/name matches; failing pages -> drafter |
| Final review: every number/date/name of note, letter, part 0 vs the images; INSTRUCTIONS §4 incl. §4.18; letter-or-not; language; minimal direct corrections | reviewer (MODEL_REVIEW) | 1 review + 1 re-review max; not approved -> delivered with warning (Order step 7) |
| pkg3 / highlight / build_note_letter / build_study / lint / verify / extract_check runs; page numbers from map.json | you (MODEL_LIGHT) | scripts; LINT OK, ALL OK, EXTRACTS OK |
| Fixing lint/verify/extract lines | you 2 attempts -> drafter 2 -> drafter_strong 1 (if set) | then "पडताळणी अपूर्ण" warning and go on (rule 9) |

Expected cost per typical proposal (15 pages, 3 GRs; estimate, not yet measured live; prices of docs/QUALITY_AUDIT.md
§6, $/MTok: Opus 5.5 4/20, Sonnet 5.5 2/10, Haiku 5.5 0.10/0.50; cache read 0.20 / 0.20 / 0.01):
| Part | $ |
|---|---|
| drafter (MODEL; figures for Abhi's plan Sonnet 5.5 — about 2× with the default Opus 5.5): ~14 turns × ~45k context, ~70k cache writes, ~12–20k output (no Study 2–4/7, no `related`) | 0.35–0.60 |
| reviewer (Opus 5.5): ~8 turns, 15 page images + spec + part 0 + brief (~60k writes), ~4–8k output | 0.35–0.60 |
| study_writer + related_writer (Haiku 5.5): ~30 turns, ~30k output | 0.05–0.15 |
| orchestrator + part-1 helper (Haiku 5.5) | 0.07–0.35 |
| escalations (extract mismatches, part-1 pages, content fixes) when needed | 0–0.30 |
| **Total** | **≈ 0.8–2.0, typical ≈ 1.2** (previous tier design 1.0–1.8, typical ≈ 1.4; all-Opus 2.3–3.3) |

### Order
1. Read the TEXT of all pages in ONE Bash call (`.txt` where `has_text_layer`, else `.ocr.txt`), case.json, inputs.
   Do SOP Step 2 search work: list the GRs/rules/orders cited (from the text), look them up (pdf/gr/INDEX.tsv,
   register/, service-rules/, pdf/), fetch missing ones (brief rules; tools/gr_request.py), grep OLDCASES and
   PRECEDENT for the subject. Write `/tmp/work/candidates.md`: per candidate GR — code, date, title, repo path, and
   the text of the pages that may hold the needed para (pymupdf text, page numbers); precedent hits (file, lines).
   Never decide which GR applies or quote anything yourself.
2. D1 -> `drafter` (ONE Agent call; give paths, not content): "Read the brief and TOOL_DOCS. LOOK at every proposal
   page image WORKDIR/pages/p-NN.png (full 110 dpi; several Reads per message); reply PDFs likewise. Write
   /tmp/work/facts.json (format below) — every number/date/name/amount from the IMAGE, `clear:false` where not sure.
   Using /tmp/work/candidates.md, the GR PDFs and precedents: decide letter or not, select the GR pages, write
   /tmp/work/enclosures.json (pkg3 format; marks = exact text lines unique on the page), /tmp/work/spec.json (note +
   letter, `related` = []; पृ.N computed from the package order: proposal pages 1..n, then the enclosure pages in
   order), /tmp/work/study_part0.json (part 0 as a build_study part), /tmp/work/status_core.json (summary,
   letter_needed, essential_points, grs_attached, grs_missing, case) — in spec.json also `parawise` / `order` when
   the brief's court / order-draft rules call for them — and /tmp/work/related_plan.md (which GR/rule/
   precedent paras the note's `related` should carry, with file + page; no quotes needed). List unclear pages in
   facts.json `unclear`."
   facts.json = `{"pages": n, "facts": [{"file": "proposal", "page": N, "document": "...", "items": [{"what": "...",
   "value": "<as on the image>", "clear": true}]}], "unclear": ["<page: what>"]}`. `file` = "proposal" (page = proposal
   page; the only entries part1check compares), "reply_<n>" / "extra_<n>" (page = page inside that file).
3. pkg3 -> compare `<pdf>.map.json` with the drafter's पृ.N (fix only page numbers, mechanically). If any enclosed
   page has no usable text layer (scan / legacy font / garbled Unicode — most gr.maharashtra.gov.in PDFs), run
   `python3 tools/prep_pages.py "OUTDIR/<package>" /tmp/work/pkgpages --small-dpi 0` once (OCR for extract_check).
4. In ONE message, two Agent calls (they run in parallel):
   - `related_writer`: "Read the brief, /tmp/work/related_plan.md, /tmp/work/spec.json and OUTDIR/<package> +
     its .map.json. Write /tmp/work/related.json = the spec `related` list (verbatim extracts in “…”, source, each
     ending " (पृ.N/प.वि.)" from the map, or with no page marker when the page is not in the package; never
     "पॅकेज PDF", warnings, remarks, "स्रोत" or "जसाच्या तसा" — INSTRUCTIONS §4.27)."
   - `study_writer`: "Read the brief, facts.json, spec.json, study_part0.json, candidates.md and the package. Write
     /tmp/work/study_rest.json = parts 2, 3, 4, 7 (build_study parts; part 3 extracts verbatim in “…” with
     "(पॅकेज PDF पृ. N)" or "(पॅकेज PDF मध्ये नाही)"; unavailable GRs, discrepancies, cautions in parts 4/7)."
5. Merge `related.json` into spec.json `related`. Assemble study.json = part 0 + part 1 + parts 2–4 + part 5 (note
   text copied from spec) + part 6 (letter text copied from spec) + part 7. Run
   `python3 tools/extract_check.py "OUTDIR/<package>" --spec /tmp/work/spec.json --study /tmp/work/study.json
   [--ocr-dir /tmp/work/pkgpages] --extra OLDCASES/t --extra PRECEDENT --extra register --extra service-rules
   [--extra <each GR/rule PDF quoted but not enclosed>] --log-out /tmp/work/xlog.json --from MODEL_LIGHT --to MODEL`.
   EXTRACTS FAIL -> delegate the MISMATCH units (printed lines) to `drafter` (correct those extracts from the
   page/image; one-way, never back to the cheap tier), merge, re-run; append xlog.json entries to `model_log`. Cap:
   2 drafter rounds (+1 `drafter_strong` if set). Still MISMATCH -> keep the unit unchanged (its source ending stays
   as written), warning "पडताळणी अपूर्ण — उतारा मूळ पानाशी जुळला नाही: <where, पृ.>", go on.
   UNVERIFIABLE lines are not failures. The workflow repeats this check on the delivered files and reports what is
   left as warnings.
6. lint -> build_note_letter [-> build_parawise / build_order when spec has `parawise` / `order`] -> build_study ->
   write a draft OUTDIR/status.json (rule 9, without `review`) -> verify (rule 6). Fix ladder: Escalation (b); its end
   state: rule 9. A PREFIX change (C R found later) -> delete the old-PREFIX files in OUTDIR before rebuilding.
7. D-final -> `reviewer` (ONE Agent call): "Read the brief, /tmp/work/facts.json, /tmp/work/spec.json,
   /tmp/work/study_part0.json; LOOK at the page images WORKDIR/pages/p-NN.png. Check and correct per your
   definition; after your edits run `python3 tools/lint_spec.py /tmp/work/spec.json` until LINT OK, then write the
   hashes and /tmp/work/review.json." If `changes` > 0: copy the corrected part 0 / note / letter text into
   study.json (parts 0, 5, 6), then lint -> build -> extract_check -> verify again. Copy review.json into status.json
   `review` = {"approved", "changes", "corrections"[, "reason"]}.
   Caps (02.11.2026, Abhi: drafts are never thrown away): at most 1 review + 1 re-review per run.
   - approved false -> ONE redraft round: `drafter` gets the reviewer's `reason` (and `redraft` points) and fixes
     spec / part 0 / part 1; lint -> build -> extract_check -> verify; then the one re-review. Still false -> deliver:
     state "done", `review` {"approved": false, "changes", "corrections", "reason"}, warning "अंतिम पडताळणी (Opus)
     मान्यता नाही — वापरण्यापूर्वी तपासा: <reason>".
   - No review.json at all (reviewer failed) -> the same delivery, reason "reviewer चालला नाही".
   The reviewer writes `spec_sha256` / `part0_sha256` (the files it approved) into review.json; the workflow reads
   /tmp/work/review.json itself, recomputes both hashes and checks the CLI usage shows MODEL_REVIEW ran. So after the
   review NEVER change /tmp/work/spec.json or /tmp/work/study_part0.json. If verify still needs a change there: make
   it and use the re-review if it is still unused; otherwise leave the files, warning "पडताळणी अपूर्ण — <line>".
   Never write or edit review.json yourself.
Progress steps (rule 4) as before.

### Study part 1
- Wait for `/tmp/work/study_part1.done` / `.failed` with ONE Bash loop (Bash timeout 600000 ms, at most 4 calls).
- `.done` + valid -> `python3 tools/engine_supabase.py part1check /tmp/work/facts.json /tmp/work/study_part1.json`.
  PART1 OK -> insert UNCHANGED as parts[1]. MISMATCH lines -> delegate to `drafter`: redo exactly those pages of
  part 1 from the images (or all of part 1 if more than a third of the pages fail) and log the escalation.
- `.failed` / invalid / missing -> keep the valid pages of a partial study_part1.json (a page whose only para is
  "[भाग 1 वेळेअभावी अपूर्ण — मूळ पान पाहावे]" is not done); delegate the rest (or all) of
  part 1 to `drafter` (rule (c) below).
- After ANY part-1 write (drafter redo, drafter_strong, merge) run part1check again (A1 H11). Cap: 2 drafter rounds
  (+1 drafter_strong); still MISMATCH -> keep the text, warning "पडताळणी अपूर्ण — भाग 1 पान <N>: part1check जुळले नाही".
- Time budget (A1 H10; long / English proposals): your first Bash call writes `date +%s > /tmp/work/t0`. When part 1
  is still not complete for all pages after 90 minutes of the run, or the drafter's part-1 work has used about 40
  turns, stop part-1 work: deliver the pages done; each page not done keeps its subheading "PDF पान N — <document>" and
  one para "[भाग 1 वेळेअभावी अपूर्ण — मूळ पान पाहावे]"; warning "पडताळणी अपूर्ण — भाग 1: पाने <N–M> चे रूपांतर वेळेअभावी
  झाले नाही". Pages used by the note/letter (निर्देशपत्र, forwarding letters) are done first. Never fail for part 1;
  otherwise part 1 stays complete and verbatim (INSTRUCTIONS §4.8 "जसेच्या तसे"; no summary of a page).
- Whoever writes it, part 1 keeps one subheading "PDF पान N — <document>" per page. The workflow re-runs part1check
  on the FINAL part 1 (study.json "भाग 1") against /tmp/work/facts.json and reports a mismatch as a warning.

### Escalation rules (one way up; log every one)
(a) Facts: a page in facts.json `unclear`, an item `clear:false`, or a handwritten/stamp page whose OCR is empty —
    the drafter already reads every image; if it still reports the page unclear and `drafter_strong` exists,
    delegate ONLY those pages to `drafter_strong` (full image, crop/zoom by rendering at higher dpi with pymupdf).
    Still unclear -> "अस्पष्ट" in the Study, "____" in the note/letter (§4.27).
(b) lint / verify still failing after 2 fix attempts by you -> `drafter` (give the printed lines + file paths); still
    failing after 2 drafter attempts -> `drafter_strong` if it exists.
(c) A cheap-tier output fails its check (study_part1.json invalid, part1check MISMATCH, extract_check MISMATCH in
    `related` or Study part 3, related.json / study_rest.json missing or invalid) -> `drafter` (only the failing units).
(d) End of every ladder (02.11.2026): per problem at most you 2 + drafter 2 + drafter_strong 1 (if set) attempts; then
    stop editing that item, add "पडताळणी अपूर्ण — <what, where>" (the printed line) to status.json `warnings` and go
    on with the next step. Never loop, never fail for it (rule 9).
Never move a task down. Budget is SOFT: never skip an escalation for cost; the workflow adds an information line
"खर्च अंदाजापेक्षा जास्त — माहितीसाठी" (not an error).
Log in status.json `model_log` (list): `{"task": "<Marathi, e.g. भाग 1 पान 3>", "from": "<model id>", "to": "<model id>",
"reason": "<Marathi, e.g. हस्तलेख अस्पष्ट / lint 2 वेळा अयशस्वी / part1check जुळले नाही / उतारा मूळ PDF शी जुळला नाही>"}`
— also the fixed routing: `{"task": "तथ्ये, नोंद, पत्र, भाग 0", "from": "", "to": MODEL, "reason": "मसुदा"}`,
`{"task": "भाग 1-7 (0 वगळून), संबंधित माहिती, साधने", "from": "", "to": MODEL_LIGHT, "reason": "स्वस्त स्तर; उतारे यंत्र-तपासणी"}`
and `{"task": "अंतिम पडताळणी व मान्यता", "from": "", "to": MODEL_REVIEW, "reason": "अंतिम मान्यता"}`. Model ids are in
the run variables. The reviewer's corrections go to status.json `review.corrections` (the workflow prints them as
"मॉडेल: Opus पडताळणी — …").

### Cost rules (they never override a quality rule)
- Few turns: independent tool calls in ONE message; shell steps combined in one Bash call; each JSON in one Write.
- Limit output (`| head -60`, `grep -m`, `cut -c1-300`); never cat a whole large file, PDF dump or zip listing.
- The brief (tools/ENGINE_BRIEF.md) and the tool docstrings (/tmp/work/TOOL_DOCS.md) are below / in /tmp/work: do not
  Read the tool .py files or the full rule files, except a grep of one exact item on a real doubt.
- Never Read the same file twice. Give subagents file paths, never paste file contents into the delegation.

## Court cases and order drafts — two optional outputs (02.11.2026; docs/COURT_AND_ORDERS_RESEARCH.md B1–B10)
Abhi, 02.11.2026: "court case aslyas parawise tayar krne note ani letter tayar krne"; "shasan nirnayacha masuda tayar
kne, adhisuchna, dhynapan tayar krne". Both live in the SAME spec.json as the note (the `drafter` writes them in D1, the
`reviewer` checks them and its spec hash covers them). Builders: `python3 tools/build_parawise.py spec.json OUTDIR PREFIX`
-> `OUTDIR/<PREFIX>_Parawise.docx`; `python3 tools/build_order.py spec.json OUTDIR PREFIX` -> `OUTDIR/<PREFIX>_Order_Draft.docx`
(spec format: their docstrings in TOOL_DOCS). `tools/lint_spec.py` lints the `order` / `parawise` keys too (it calls
tools/lint_order.py / tools/lint_parawise.py); build them in step 6 after build_note_letter, before verify.

**Court mode** (the proposal is a court matter: a notice/letter of a Government Pleader / AGP / सरकारी वकील, the High
Court or MAT about a writ petition (रिट याचिका), O.A. (मूळ अर्ज), contempt (अवमान याचिका), SLP — look for these words
on the page images):
- Note (B9, Section's contempt file): para 1 "<सहायक सरकारी वकील, मा. उच्च न्यायालय, …> यांच्या पृ.N/प.वि. वरील दि. __
  रोजीच्या पत्रास अनुसरून सादर."; then "पार्श्वभूमी थोडक्यात खालीलप्रमाणे आहे:-" and numbered facts with पृ.N/प.वि.
  (court order, GRs, earlier opinions, earlier letters); the hearing date as stated in the notice.
- Facts suffice -> spec `parawise` (English; B8; Rules for the Conduct of the Legal Affairs of Government 1984,
  Rule 58(3): a parawise report on ALL points of the petition; Rule 58(4) Note (ii): never cryptic "denied" /
  "not admitted" — elaborate factual position with rule/GR/order references, copies of those documents listed as
  enclosed; Rule 58(4)(a): recommendation oppose / not oppose with the reason from the record — the one stated
  exception to "no opinion of your own"; no record basis -> "____" for the Section + warning) + a letter to the
  GP/AGP forwarding it (to = the GP/AGP as in the notice; intro "उपरोक्त विषयाबाबत संदर्भाधीन पत्रास अनुसरून आपणांस
  कळविण्यात येते की, सदर याचिकेतील परिच्छेदनिहाय अभिप्राय (इंग्रजी) व संबंधित शासन निर्णयांच्या प्रती सोबत
  पाठविण्यात येत आहेत. … , ही विनंती."; copy to the RLA / JS-DS of L&J (Nagpur/Aurangabad bench) only where Rule 58(4)
  applies). Last para (lint form (a)): "सबब, रिट याचिका क्र. ____ मधील परिच्छेदनिहाय अभिप्राय (इंग्रजी) व ते <सहायक
  सरकारी वकील> यांना पाठविण्याबाबतच्या पत्राचे प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर. मान्य झाल्यास पत्र
  निर्गमित करण्यात येईल."
- Essential facts missing (§4.15) -> NO `parawise`; the information-letter first (to the HC / District Court as usual).
- Time limit: Rule 58(4) — papers to the GP within two weeks of receipt, in any case before the date in the notice.
  Study part 0 (अ)/(आ) states the hearing date and that limit; (ऐ) the action.
- Signers: the §4.6 chain (B10, Abhi to confirm).

**Order drafts** (B7) — spec `order` (type gr / corrigendum / circular / memo / notification) ONLY when the record shows
the decision or concurrence is in hand (Finance / GAD concurrence received, approval given, a reply that completes the
case) or `instructions` asks for it. Otherwise no `order` (a Finance/GAD note or a letter instead — Step 3). GR for
general orders; ज्ञापन for a sanction to named/limited officers (GADT 12.10, 12.12); शुद्धिपत्रक to correct an issued
order; अधिसूचना for statutory notifications (B6: Marathi + English). Concurrence para with the Finance/GAD reference as
in the record (R3). The note's last para then (lint form (c), R3 (c)): "सबब, … <शासन निर्णयाचे / ज्ञापनाचे /
शुद्धिपत्रकाचे / परिपत्रकाचे / अधिसूचनेचे> प्रारूप पृ.      /प.वि. वर मान्यतेस्तव सादर." (notification in two languages: "… अधिसूचनेची मराठी व इंग्रजी
प्रारूपे पृ.      /प.वि. वर मान्यतेस्तव सादर."; optionally "मान्य झाल्यास
… निर्गमित करण्यात येईल."); no "अ.मु.स. (वित्त)" unless the file goes to Finance.

**Never stop for missing order / court details** (as rule 5 for the C R no.): unknown petition no., date, GP name,
संकेतांक, Gazette part, notification signer -> "____"; log them in Study part 4 / 7 and status.json `warnings`.
status.json `outputs_extra` lists what was built, e.g. `[{"kind": "parawise", "file": "<PREFIX>_Parawise.docx"},
{"kind": "order_draft", "file": "<PREFIX>_Order_Draft.docx"}]` (`[]` / absent = none). The workflow uploads the files
(kinds "parawise", "order_draft") and verify_outputs.py checks them (fonts, ids, repo paths, पृ. ranges).

## Lint before building
Before every build run `python3 tools/lint_spec.py spec.json --study study.json --pages <package pages>` (docstring in
tools/lint_spec.py; same checks as verify_outputs.py) and fix every line it prints until "LINT OK" (ladder:
Escalation (b); end state (d) — then build anyway and record the lines as warnings).
build_note_letter.py and build_study.py lint again themselves and exit 1 on a rule problem. Only after the ladder's
end state (d), build with `--no-lint` so the draft is delivered, and put the remaining lint lines in `warnings`.

## Binding
The binding rules are `tools/ENGINE_BRIEF.md` (appended BELOW this prompt; subagents Read the file) and the tool
docstrings (appended below and saved as /tmp/work/TOOL_DOCS.md). Full rule files (INSTRUCTIONS.md, PROPOSAL_SOP.md,
PROPOSAL_WORKFLOW.md, tools/PROPOSAL_PROMPT.md) stay the authority: grep the exact item on a real doubt; INSTRUCTIONS.md
wins on any conflict of CONTENT (sources, format, language). This run has NO interaction (A1 H14): rules 2, 5 and 9
below override every ask / discuss / stop line of the rule files — INSTRUCTIONS §3.2 "आधी वापरकर्त्याशी चर्चा",
PROPOSAL_SOP Step 2.3 "ask its सांकेतांक in ONE line", the brief. Such a question becomes a status.json `warnings`
line + a Study part 4 question, and the work goes on. register/00-INDEX.md = index of verified extracts. Do NOT read HANDOVER.md or OWNER_RULES.md.
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
   part 7, and carry on. "Ask"/"discuss" in any rule file = a `warnings` line + a Study part 4 question. A GR still not
   found after SOP Step 2.3 goes into `grs_missing` (below) + warning "पडताळणी अपूर्ण — GR सापडला नाही: <date, title>
   (सांकेतांक द्यावा)", and the Study (part 3/4) says "उपलब्ध नाही — मागवावे"; the note does not mention it (§4.27).
3. Nothing extra of your own (INSTRUCTIONS §4.13): no boxes, no markings; proposal scan pages unchanged; yellow
   highlights only on the quoted lines of the enclosed GR/rule pages.
3a. Drafts look hand-made (INSTRUCTIONS §4.27, Abhi 02.11.2026): the note (body + related), letter, order/parawise
   drafts and the package PDF never carry a warning, a working remark, "पॅकेज PDF", or any mention of AI / model /
   automation / engine (word list: tools/ENGINE_BRIEF.md [I4.27]); unknown values = "____". Warnings, remarks and
   unavailable sources go only to the Study (parts 4/7) and status.json `warnings`. Tell every sub-agent this.
4. Progress — run at each milestone (ignore an error from it, it is only the live status; this step has no Supabase key —
   the command sends the text through the Worker with the run token):
   `python3 tools/engine_supabase.py step "पाने वाचत आहे"` (Step 1), `"GR शोधत आहे"` (Step 2),
   `"मसुदा तयार करत आहे"` (Steps 3–4, 6), `"PDF बनवत आहे"` (Step 5), `"तपासणी चालू"` (Step 7).
5. Case identity: cr_no, cr_year, file_no, subject and category may be EMPTY in case.json (Abhi may skip them at upload;
   category "इतर" counts as not chosen). Take every empty one from the निर्देशपत्र (proposal page 1) exactly as written there;
   never guess — unreadable = leave it out. Report them in status.json `case` (rule 9).
   PREFIX = `CR<cr_no>_<cr_year>` from case.json, or from the निर्देशपत्र when empty (e.g. CR130_2026). Look for the C R no.
   on EVERY page image before giving up (cover sheet, inward stamp, file no. "संकीर्ण-YYYY/<file>/प्र.क्र.<n>/का.6").
   **A missing C R no. / year / file no. is NEVER a reason to stop or to write state "failed" (Abhi, 02.11.2026).** If it
   is in neither case.json nor any page: PREFIX = `Case<case id from case.json>_<year of the proposal's latest letter, else
   the current year>` (e.g. Case7_2026); letter `ref_no` = `संकिर्ण-<year>/____/प्र.क्र.____/का.6` (blanks for the Section
   to fill by hand). Year in ref_no / date: never copied from a sample — ref_no year = the year of the file no. on the
   निर्देशपत्र, date "__.__.<current year>". Add "पडताळणी अपूर्ण — C R क्रमांक प्रस्तावात सापडला नाही — प्रकरणाच्या तपशिलात भरावा; पत्र-क्रमांक हाताने भरावा"
   to status.json `warnings`; then do EVERY remaining step (note, letter, Study, package, verify, reviewer) as usual.
   Outputs in OUTDIR, nothing else there except the
   .map.json and LibreOffice previews:
   - `OUTDIR/<PREFIX>_Study.docx` (part 0 briefing + parts 1–7),
   - `OUTDIR/<PREFIX>_Note_and_Letter.docx`,
   - optional: `OUTDIR/<PREFIX>_Order_Draft.docx`, `OUTDIR/<PREFIX>_Parawise.docx` (section "Court cases and order drafts"),
   - the package PDF under the ORIGINAL proposal file name = `proposal_original_name` exactly (INSTRUCTIONS §4.16;
     strip only a random upload prefix like `11ae057d-`). Never invent a new name such as `<PREFIX>_Proposal_with_GRs.pdf`
     — but when the original name itself looks machine-made (e.g. the uploaded file really is `CR66_Proposal_with_GRs.pdf`
     or `..._0001.pdf`), keep it exactly as uploaded; never "correct" it.
   Exactly one .pdf in OUTDIR besides `*_Note_and_Letter.pdf` / `*_Study.pdf` / `*_Order_Draft.pdf` / `*_Parawise.pdf` previews.
6. Verify (SOP Step 7): `python3 tools/verify_outputs.py OUTDIR <PREFIX> "OUTDIR/<original name>" <proposal pages> --original-name "<proposal_original_name>"`
   must print ALL OK; fix by the ladder (Escalation (b), end state (d)). The second read of every number and date in
   the note, letter and Study part 0 against the page images is the `reviewer`'s final review (Order step 7).
   After you finish, the workflow runs the same command itself (PREFIX, package and proposal pages from status.json):
   its FAIL lines become warnings, except HARD ones that fail the case — missing outputs, internal ids / repo paths,
   annotations on proposal pages. Those are always fixable (build the file; delete the id/path/annotation): fix them.
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
 "outputs_extra": [],
 "warnings": ["पडताळणी अपूर्ण — <what, where>"],
 "model_log": [{"task": "तथ्ये, नोंद, पत्र, भाग 0", "from": "", "to": "<MODEL>", "reason": "मसुदा"}],
 "review": {"approved": true, "changes": 1, "corrections": ["<Marathi: what the reviewer changed>"]},
 "case": {"cr_no": "130", "cr_year": 2026, "file_no": "संकीर्ण-2026/979/प्र.क्र.130/का.6", "subject": "<as on the निर्देशपत्र>",
          "category": "<one of: वेतननिश्चिती, भत्ते, निवृत्तीवेतन, जुनी पेन्शन, विशेष वेतन, विमा/GPF, सेवा, न्यायिक वेतन, वैद्यकीय, इतर>"}}
```
   `outputs_extra` = the optional files built (section "Court cases and order drafts"), `[]` when none.
   `prefix`, `package_pdf`, `proposal_pages` = exactly the PREFIX, package file name and proposal page count you gave
   verify_outputs.py (rule 6); the workflow re-runs it with these.
   Terminal states (02.11.2026, Abhi: "drafts must never be thrown away"; "punha ase bug yayla nko"):
   - "failed" ONLY when no output could be produced at all (proposal pages unreadable, nothing built):
     `{"state": "failed", "summary": "<reason>", "warnings": [...], "model_log": [...]}`.
   - "done" in EVERY other case. Each unresolved problem = one Marathi `warnings` line "पडताळणी अपूर्ण — <what,
     where>": lint/verify/extract/part1 not clean after the caps, C R/file no. missing (rule 5), GR not found (rule 2),
     an instruction that conflicts with a binding rule, part 1 incomplete for time, review not approved (Order step 7:
     "अंतिम पडताळणी (Opus) मान्यता नाही — वापरण्यापूर्वी तपासा: <reason>"). `warnings` = [] when clean.
   - Write status.json, then run verify once more (its letter_needed check reads it); a new non-HARD FAIL -> warning.
   Missing case fields (C R no., file no., subject, category) are never a reason — use the rule 5 fallback.
   `model_log` = the routing/escalation log (see "Escalation rules"); always included.
10. Final reply: Marathi, as few words as possible.
