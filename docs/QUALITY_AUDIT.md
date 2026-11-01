# QUALITY_AUDIT.md — productivity + output-quality audit (01.11.2026)

Read-only audits. Pack 1 + Pack 2 FIXED 01.11.2026 (tests: tests/test_tools.py 10, tests/test_verify_outputs.py 17, tests/engine_supabase_test.py, cloudflare/test/worker.test.mjs 3; migration 0004). Pack 3 open. Abhi chooses what to fix (OWNER_RULES A.5/A.6). Severity H/M/L, effort S/M/L.

## 1. Procedure, rules and quality gates
| Sev | Where | Problem | Fix | Eff |
|---|---|---|---|---|
| H | tools/PROPOSAL_PROMPT.md:12-15,35 | Stale: other-machine paths, font "Mangal" (vs §4.2 DVOT-SurekhMR), "no network" (vs SOP 2.3), output path clashing with ENGINE rule 5 — yet ENGINE_PROMPT and §4.8 point the run to it | Rewrite those lines to repo paths, DVOT-SurekhMR, build_study.py | S |
| H | tools/PROPOSAL_PROMPT.md:28 | Part 5 signer chain = 5 people with blanks + advice wording ("…अभिप्राय घेणे आवश्यक") — contradicts §4.6 and SOP banned advice | Use the §4.6 chain and the two SOP last-para forms | S |
| H | ENGINE_PROMPT.md:19 + SOP:16 | Engine skips Step 0 → old-case corpus (oldcases_text.py) never built, precedent-library zip never unzipped → no precedent search in automatic runs | Make both explicit engine/workflow steps | S |
| M | INSTRUCTIONS:29 vs SOP:76 vs PROPOSAL_PROMPT:30 | Three different letter ref_no forms | Align §4.5 to the SOP/spec form `संकिर्ण-2026/<file no>/प्र.क्र.<n>/का.6` | S |
| M | PROPOSAL_PROMPT:30 vs SOP:78 | Letter intro "कळविण्यात येत आहे की" vs "कळविण्यात येते की" (all specs) | Use the SOP wording | S |
| M | ENGINE_PROMPT:16-17 | Engine re-reads HANDOVER (session to-dos) and inherits SOP Step 0b/8.3 via CLAUDE.md — wasted tokens, conflicting steps | Drop HANDOVER from engine reads; say "skip Step 0b and Step 8" | S |
| M | SOP:125, samples/specs/CR128 | Spec saved before approval; CR128 spec is provisional (4 GRs missing) but sits among approved templates | Save specs only after Abhi's OK; mark CR128 provisional | S |
| M | samples/specs/CR122, CR128 `related` sources | Repo paths (register/PAY-01, service-rules/01, "repo (pdf/…)") printed in the note for seniors | Remove; add a check in verify_outputs | S |
| M | verify_outputs.py:132 | पृ. range check only matches N or N-M; "पृ.6, 12/प.वि." etc. unchecked | Widen regex or ban comma lists | S |
| L | samples/specs/CR66 | Explanatory aside / "विचारात घेता" near the commentary ban (ban list is open-ended) | Closed banned-word list + check | S |
| L | SOP:74 vs INSTRUCTIONS:40 | Two forms for "(पॅकेज PDF पृ. N)"; specs vary | One fixed form + fixed "not in package" phrase | S |
| L | tools/mkdocs.py:12-13 | Docstring example shows wrong signers/closing | Use §4.6 example | S |
| L | SOP commands | `python3` vs Windows `py`; "add_repo" wording | One-line note | S |

verify_outputs.py checks today: font (w:cs only), "आपला," + "निवड नस्ती", z6/z7 ids, no "पॅकेज PDF" in note body, पृ. upper bound, "/ N" stamp (weak), bookmarks, no annotations on proposal pages, highlight-only.
Not checked (automatable): signer chain/order and अ.मु.स.(वित्त) ⇔ Finance last para; "आपली" absent; signature/phone/email lines; ref_no pattern; विषय/संदर्भ bold+centre; letter on new page; banned words; first/last para forms; Study भाग 0-7 headings; package file name = original (§4.16); page count = proposal + enclosures (no separator pages); proposal pages unchanged; each marked enclosure has a highlight; पृ.N matches map.json; status.json letter_needed ⇔ letter present; all four font attributes.
Missing engine guidance: criteria Finance vs GAD vs reply-on-opinion; no approved sample for GAD note, reply-on-opinion, or second note after a reply; medical-bill/ not named in ENGINE_PROMPT.

## 2. Tools code (ran: build_note_letter on CR122, build_study, pkg3 on real GRs, verify_outputs, oldcases_text)
| Sev | Where | Problem | Evidence | Fix | Eff |
|---|---|---|---|---|---|
| H | pkg3.py:71-74 | Page stamp "पृ. N / एकूण" often NOT written, silently — insert_textbox result never checked; white strip still drawn | local: return -0.73 / -5.18 even on blank A4; real 11-page package had 0 stamps. Runner (FreeSerif) unverified | insert_text at fixed baseline or taller box; fail if <0 | S |
| H | build_note_letter.py:21-23 | Letter prints with the NOTE's margins (docxcompose keeps one sectPr) | letter template L5.5/R1.0 cm vs note L4.75/R1.25; composed CR122 = 1 section | Insert note sectPr as section break before the letter | S |
| H | verify_outputs.py:29 | Internal-id check only z6_/z7_; corpus uses z1_…z8_ | Study with z5_0100 passed | regex `z\d_\d{4}` | S |
| M | verify_outputs.py:34-35 | पृ. regex misses `पृ. 5 / प.वि.`, lists, "ते"; पृ.0 passes | tested | widen; require 1≤N | S |
| M | verify_outputs.py:30-35 | Study not range-checked; letter part skips "पॅकेज PDF" check | Study पृ.99 on 3-page package passed | check Study and letter too | S |
| M | verify_outputs.py:26 | Font check reads only w:cs | code (builders do set all four today) | check all four + headers/footers | S |
| M | verify_outputs.py:38 | Stamp check = substring "/ N" (any GR text passes; English "Page i / N" passes) | fake package passed | exact `पृ. i / N` in bottom strip | S |
| M | verify_outputs.py (missing) | map.json never read: "TEXT NOT FOUND" marks, multi-hits, proposal page-count mismatch pass | pkg3 reported TEXT NOT FOUND, verify silent | FAIL on those | S |
| M | pkg3.py:24-49 | Reversed/out-of-range page spec adds no pages silently; bookmark + map wrong | "5-3" test | raise on empty selection | S |
| M | pkg3.py:62-64 | Still offers red "box" annotations (against §4.13) | docstring l.8,14 | remove box mode | S |
| M | process-proposal.yml commit step | push-retry loop ends on `sleep 5` → failed push passes silently, new GRs lost | shell logic | explicit ok flag / exit 1 | S |
| M | process-proposal.yml | Workflow never runs verify_outputs itself; trusts the model | — | add verify step before finish | S |
| M | engine_supabase.py:83-90,113 | Corrected proposal under a new name → two proposals; "original name" = alphabetically last | code | pick newest by created_at | S |
| M | gr_request.py:74-75 | not-found/error lines moved to "done", never retried; PDF saved without INDEX row if meta fails | code | keep failed lines; write INDEX first | S |
| L | build_note_letter.py:32-33 | soffice preview rc ignored; DVOT font absent on runner (preview layout differs; docx fine) | apt list | check rc; note it | S |
| L | highlight.py | "lines" mode with 0 matches is silent; tesseract rc ignored; no Marathi OCR data on runner | code, workflow | fail on 0; install tesseract-ocr-mar | S |
| L | mkdocs/build_study/pkg3/highlight | JSON with BOM crashes | build_study crashed on PowerShell JSON | utf-8-sig | S |
| L | build_proposal.py, pkg2.py, run_headless.sh | Old/superseded (build_proposal adds separator pages, breaks §4.7) | docstrings | archive | S |
Speed: oldcases_text fine (194 docx in 8 s); cost is checkout (934 MB history + 1.1 GB pdf/) and per-run installs.
Tests: only engine_supabase has one. Smallest useful per tool listed in the agent report: build all 6 specs (fonts, "आपला,", letter margins); pkg3 stamps/bookmarks/map; highlight ≥1 Highlight only; verify must-FAIL fixtures; build_study fonts; gr_request parse (network mocked); app_seed_gr; desk_chunks round-trip; oldcases_text.

## 4. Priority (proposed — Abhi to choose)
- **Pack 1 — output quality (all S, ~1 session):** pkg3 stamp + page-spec + no box; letter margins; verify_outputs hardened (ids, refs, stamps, map.json, fonts, Study, file name, signer chain, banned words); workflow runs verify itself; PROPOSAL_PROMPT + rule-text alignment; engine builds old-case corpus; regression tests for these tools.
- **Pack 2 — reliability / cost (mostly S):** stuck-run fix; `fetch-depth: 1`; cost/turns stored per run; Marathi failure reason (no GitHub log needed); one-time token; drop runs_ins/files_ins; push-loop fix; newest-proposal pick; gr_request retries; engine reads only INSTRUCTIONS/SOP/WORKFLOW; install caching.
- **Pack 3 — needs Abhi's decision:** which pdf/ folders the engine needs (sparse checkout); confidential zips in history (keep vs rewrite); delete superseded files and App A (desk page, TEST-1); approve-before-save rule for samples/specs (CR128 provisional); keep Supabase key out of the Claude step (M).

## 3. App B operations and repo hygiene
| Sev | Where | Problem | Fix | Eff |
|---|---|---|---|---|
| H | process-proposal.yml:79-82, CaseTabs.tsx:62,82 | A run can stay queued/running forever → case locked (re-run disabled): cancel/timeout skips `if: failure()`; config-step failure leaves no Supabase env so `fail` records nothing; no stale-run sweep | `if: failure() \|\| cancelled()`; Worker marks runs older than ~3.5 h failed; re-enable button for stale runs | S |
| H | process-proposal.yml:23-24 | `fetch-depth: 0` downloads ~934 MB history every run | `fetch-depth: 1` | S |
| M | pdf/ (1.2 GB, 952 files) | Most folders unrelated to service rules (GAD 98 MB, food 90, housing 64 incl. one 53.7 MB PDF, FRBM 63…) all checked out per run | Sparse checkout of needed folders — Abhi decides which | M |
| M | process-proposal.yml:58-63 | apt/pip/npm installed fresh each run; claude-code unpinned | Cache (setup-python/node cache, apt cache or image); pin claude-code | M |
| M | process-proposal.yml:74-76 | No cost record or cap (`--max-turns 400`, 180 min) | `--output-format json` → store cost/turns/duration in `runs` | S |
| M | process-proposal.yml:82, RunProgress.tsx | Failure tells Abhi to open GitHub logs (blocked at office); generic reason | Put the claude error (max turns / key / credit) in the reason + fixed Marathi next step | S |
| M | process-proposal.yml:48-51,74 | Claude runs with skip-permissions + internet on untrusted PDFs while the Supabase service key and Anthropic key are in its env | Keep service key out of the Claude step (progress via Worker + run token) | M |
| M | worker.js:73,123-127 | "One-time" engine token reusable for 3 h, returns keys | Delete token after first config read | S |
| M | repo root zips (7 × सन…प्रकरणे.zip ~12.5 MB, Medical bill zip 2.4 MB) | Confidential case files in git history; no root .gitignore | Abhi decides: keep (private) or remove + rewrite history; add .gitignore | M |
| L | init.sql:132 `runs_ins` | Members can insert runs directly → stuck queued | Drop policy (Worker uses service role) | S |
| L | init.sql:129 `files_ins` + worker.js:223 | Arbitrary storage_path signed by Worker (no access beyond member buckets) | Drop policy or whitelist buckets | S |
| L | worker.js:190 | Size check on content-length only; orphan object if case missing | Check case exists first | S |
| L | ENGINE_PROMPT:16-17 | Engine loads CLAUDE.md → OWNER_RULES (trading/Ayurveda), HANDOVER to-dos | Read only INSTRUCTIONS/SOP/WORKFLOW | S |
| L | dashboard/, HEADLESS_PROMPT.md, run_headless.sh, bulk-download workflows | Superseded files | Archive/delete after Abhi confirms; decide if App A stays | S |
Stale HANDOVER: item 4 says B "not deployed" (it is live); item 5 done; App A items (TEST-1, two pages) — still relevant?; CR128 pending.
Flow per proposal: upload → auto-run → download. Leaves the app only on failure (GitHub log) or stuck run.

## 5. Run time (independent audit 01.11.2026 — estimates, no live timings yet)
Estimate for 15 pages / 3 GRs: setup 4–7 min + model 40–100 min ≈ 50–110 min (~100–200 turns); model turns ≈ 85–90%. Biggest single output: Study part 1 (full Marathi rendering, ~15–30k tokens). Rules read by the engine ≈ 75–125 KB, largely repeated across INSTRUCTIONS/SOP/WORKFLOW/PROPOSAL_PROMPT.
| # | Change | Saves (est.) | Quality risk | Eff |
|---|---|---|---|---|
| 1 | Pre-step script: page PNGs + text layer + Marathi OCR before Claude (model still looks at every page) | 3–8 min | none | S |
| 2 | One compact engine brief generated from the rule files + check that it matches them | 5–12 | low–med | M |
| 3 | Study part 1 (page-wise rendering) in parallel with GR search/note/PDF | 10–20 | low | M |
| 4 | GR pre-lookup script (dates/codes → INDEX.tsv / archive.org candidates; Claude decides) | 3–10 | low | M |
| 5 | Lint spec/Study JSON with verify's checks before building (fewer fix loops) | 2–6 | none | S |
| 6 | Prebuilt container image for installs | 2–4 | none | M |
| 7 | Partial checkout of pdf/ | 1–2 | med | M |
| 8 | Faster model for part 1 only | 5–10 | med | S |
| 9 | Docstrings only, not whole tool files | 1–2 | none | S |
Keep LibreOffice (preview check). Lower max-turns does not speed a successful run. Priority suggested: 1, 3, 2, 5, 4, 6. UI ETA default set to 70 min until real medians exist.

## 6. Cost per run — model tiers (01.11.2026; quality first)
Prices (claude-api skill, models table cached 2026-10-06, $/MTok): Opus 5.5 in 4 / out 20, cache read 0.20, 5-min write 5;
Sonnet 5.5 2 / 10, read 0.20, write 2.50; Haiku 5.5 0.10 / 0.50 (prompt ≤100K; 0.50 / 2.50 above), read 0.1x, write 1.25x.
Images ≈ 1 token per 28×28 px: A4 page at 110 dpi ≈ 1,490 tokens, at 80 dpi ≈ 790.
Owner rule (Abhi): quality must not drop — quality-critical work stays on the main tier (Opus-class, the model of the
approved outputs); the budget is SOFT (over it = warning "खर्च-मर्यादा ओलांडली — दर्जा राखण्यासाठी", never a stop).

**Where the $ went (old design, estimate calibrated to the live run $3.32 / 79 turns, all on Opus 5.5)**
| Item | Tokens (est.) | $ | Share |
|---|---|---|---|
| Cache reads: 79 turns × ~75k avg context (rules files ~40k, 15 page images ~22k, tool output) | ~5.9M | ~1.2 | ~36 % |
| Cache writes: each new tool result written once | ~150k | ~0.75 | ~23 % |
| Output incl. thinking: Study part 1 ~20k, Study/spec ~25k, thinking ~25k | ~70k | ~1.4 | ~41 % |
Per-model split was not recorded for that run (now stored: "मॉडेल: खर्च — …" line from modelUsage).

**Routing (task → tier → why quality is unaffected)**
| Task | Tier | Why |
|---|---|---|
| Facts from page images (numbers, dates, names, stamps, handwriting), letter-or-not, GR selection + verbatim quotes, note + letter spec, Study parts 0, 2, 3, 4, 7 | `drafter` subagent = MODEL (default claude-opus-5-5) | same tier as approved outputs; every page read at 110 dpi |
| Escalation (unclear page after the main tier; lint/verify still failing after 2 main-tier attempts) | `drafter_strong` = MODEL_STRONG (optional, off by default) | one-way up only |
| Orchestration, text/OCR first pass, GR search/fetch, precedent grep, pkg3/highlight/builds, lint/verify runs, page numbers from map.json, Study parts 5–6 copied from the spec | orchestrating session = MODEL_LIGHT (claude-haiku-5-5) | mechanical; results machine-checked (LINT OK, ALL OK, workflow re-verify) |
| Lint/verify fixes | light, max 2 attempts → drafter | content fixes go up |
| Study part 1 (page rendering) | helper run on MODEL_LIGHT | kept only if `part1check` matches the drafter's facts (every number/date/name per page); failing pages redone by drafter |
Other free levers: compact brief + tool docstrings in the prompt (stable prefix, cached; no Read of rule files/tool
sources), 5-minute cache writes forced (FORCE_PROMPT_CACHING_5M), tool set limited (no WebSearch/WebFetch/sub-sub-agents),
batched tool calls, no re-reads, lint before builds. Gates unchanged.

**Expected cost per typical proposal (15 pages, 3 GRs) — estimate, not yet measured live**
| Part | $ |
|---|---|
| drafter (Opus 5.5): ~20 turns × ~45k avg context, ~80k writes, ~20–35k output | 0.9–1.5 |
| orchestrator (Haiku 5.5): ~50 turns, mostly under 100K prompt | 0.05–0.30 |
| part-1 helper (Haiku 5.5) | 0.02–0.05 |
| escalations (part-1 pages redone, content fixes) when needed | 0–0.4 |
| **Total** | **≈ 1.0–1.8** (was 2.3–3.3) |
≈ $0.50 is NOT reachable without moving quality-critical drafting off the Opus-class tier (its output tokens alone
cost ~$0.4–0.7). Real floor with the quality rule ≈ $1.0. Setting `model` = claude-sonnet-5-5 would give roughly
$0.5–0.9 but changes the drafting model — only after a side-by-side check against approved notes (Abhi's decision).
Unverified until a live run: subagent `model` honoured by the pinned CLI 2.1.300 (schema has it), Haiku as
orchestrator following the routing, real turn counts, part1check false-mismatch rate.
