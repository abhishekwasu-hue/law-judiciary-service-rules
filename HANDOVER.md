# HANDOVER — state as of 04.11.2026 (App B live; eight new draft types added) (read after CLAUDE.md files)

## Done (all in this repo)
- Procedure: INSTRUCTIONS.md §4 items 1–18 (§4.18, 01.11.2026: sentence flow + respectful language), PROPOSAL_SOP.md, PROPOSAL_WORKFLOW.md, samples/specs/ (approved notes), tools/ (mkdocs, build_note_letter, build_study, pkg3, highlight, lint_spec, verify_outputs, gr_request, oldcases_text, prep_pages).
- Proposals delivered: C R 66, 122, 128, 130, 131, 133 /2026. GRs in pdf/gr/ (+INDEX.tsv), SC order in pdf/sc/, MCS (Pay) Rules 1981 in pdf/01-mcs-pay-rules-1981/. CR 128: 05.08.2026 and 19.04.2022 GRs downloaded; 4 others not on archive.org (see Pending 1).
- **App B (प्रस्ताव कक्ष full-stack) — LIVE** https://prastav-kaksha.abhi-desk.workers.dev. Supabase project `vxkktnymewcvcqysilgx`, Tokyo (ap-northeast-1; Mumbai not offered at creation). Migrations 0001–0005 applied by Abhi in the SQL editor (0003 optional case fields, 0004 reliability). Settings in Cloudflare KV `SETTINGS`: owner_email, supabase_*, github_repo/branch/token, anthropic_api_key, model, model_light, budget_usd (Abhi: 1.5). Design + decisions: docs/APP_B_DESIGN.md; setup (Marathi): docs/APP_B_SETUP_MR.md; audit + fixes: docs/QUALITY_AUDIT.md.
- Engine = GitHub Actions `repository_dispatch` on main (.github/workflows/process-proposal.yml): page pre-step (prep_pages.py), compact rules tools/ENGINE_BRIEF.md, 3 model tiers (cheap orchestrator `model_light`, Opus `drafter` for quality-critical work, optional `drafter_strong` escalation), Study part 1 on the cheap tier kept only if part1check matches, lint before build, verify re-run in the workflow, soft budget (warning only), cost/turns stored per run.
- App UX: auto-reload after deploys, Marathi errors, duplicate C R notice at upload (Worker 409 + link), ASCII Storage keys (original name kept), stuck-run sweep, live ETA.
- First live runs: ~10 min, $2.28–3.32 (before the cost work). Expected after tiers: $1.0–1.8 — not yet measured.
- Repo is private.
- Pack 3 decisions (Abhi, 01.11.2026): the confidential old-case zips stay in the repo and its git history (NOT removed; repo private); the old dashboard/ folder stays (NOT removed).

- 01.11.2026 style decisions (Abhi): keep full verbatim GR extracts in the note body and the detailed information-request note (GAD-manual options to shorten were declined); names as in the proposal (Marathi initials only if the proposal has them). Letter lint added: no तातडीने/त्वरित-type words, no bare command endings, 'कै.' spacing. Research: docs/STYLE_RESEARCH.md (GAD), docs/STYLE_RESEARCH_LETTERS.md (letters); docs/STYLE_RESEARCH_LANG.md pending. Open letter decisions: स्मरणपत्र support, extra copy line for HC route, 'मा.' usage.

- 02.11.2026: Abhi approved the CR131 sample built under §4.18–§4.20 (samples/specs/CR131_2026_special-pay_info-letter.json) — the model for letter tables (data only; documents listed after the table) and language.

- 02.11.2026 (PR #3, branch ccr-323f0225-1a76vj, NOT merged/deployed yet): "नस्ती डॅशबोर्ड" tab (Abhi's APK page, unchanged, /nasti); re-audit docs/QUALITY_AUDIT.md §7; three H fixes (APP_B_DESIGN D14: engine isolation, review gate with hashes, one run per case); other AI providers A + C (D15, docs/AI_PROVIDERS_RESEARCH.md). Engine latest commits (before this PR): drafter Sonnet, Opus final review gate, monthly spend limit $20 (hard).

- 02.11.2026 (Abhi: "1 होय, 2 होय, 3 होय, 4 होय"): INSTRUCTIONS §4.21 स्मरणपत्र, §4.22 प्रत-ओळ (HC route), §4.23 "मा.", §4.24 "शुद्धिपत्रक" — mkdocs (reminder, copies), lint, verify, ENGINE_BRIEF, samples CR66/122/128/130/131 updated.

- 02.11.2026 (Abhi's task "noting and drafting follow the official Marathi grammar, शुद्धलेखन and writing-style rules"; parallel agents):
  tools/ENGINE_BRIEF.md "Marathi language rules" (every line with its source: GADT परिशिष्ट 1 = शुद्धलेखन नियम 1–14, GR 10.11.2022
  परिशिष्ट दोन/तीन, circular 07.05.2018, GAD manual paras 26/51/53, राजभाषा परिचय 1988); INSTRUCTIONS §4.25 (numbered 25 because
  §4.21–4.24 already existed); lint/verify: 'अनुसरुन' error + WARN L11–L14; samples + SOP 'अनुसरून' (10 lines, extracts untouched);
  evidence docs/LANG_RULES_EVIDENCE.md (before/after images, verify ALL OK on all six samples with stand-in package/Study).
  Engine: the workflow puts tools/ENGINE_BRIEF.md into every prompt (process-proposal.yml "$(cat tools/ENGINE_BRIEF.md)") and
  build_note_letter.py refuses to build when lint fails; a real dry run of the workflow was not possible (needs a run token from the Worker).

- 02.11.2026 (Abhi: "independent audit … punha ase bug yayla nko", after live run #7 failed with drafts ready): independent audit (docs/QUALITY_AUDIT.md) + fix round, 5 parallel agents.
  Contract (INSTRUCTIONS §4.26): "failed" only when no output exists; otherwise "done" + status warnings "पडताळणी अपूर्ण — …";
  hard stops only: missing outputs, internal ids / repo paths, annotations on proposal pages. Review not approved → warning
  "अंतिम पडताळणी (Opus) मान्यता नाही — …". Retry caps: orchestrator 2 + drafter 2 + drafter_strong 1; reviewer 1 re-review.
  Workflow: read-only engine sandbox (scripts/engine/sandbox.sh), runner-private files ($RP), step time budget, killed-run cost,
  runner OCR, hash-locked LiteLLM (tools/requirements-litellm.txt). Lint: "मा." phrase rule (CR66 repaired), संकीर्ण, last-para
  routes + अ.मु.स. (वित्त) route, request-only "ही विनंती". Worker/app: Marathi errors, C R edit, CSP, run_worker_first.
  Tests: pytest 248 passed; engine_supabase_test ALL PASSED; worker 19/19; all 13 samples LINT OK.
  Owner actions: apply migration 0006 (if not done) and 0007 (optional), deploy, re-run case #7. First live run = test of the sandbox on a real runner.

- 02.11.2026 (Abhi: "Noting drafting mdhe kontahi ishara, package pdf ase शब्द नकोत"; "वरिष्ठ अधिकाऱ्याला असे वाटू नये, की AI che kam aahe"):
  INSTRUCTIONS §4.27 — drafts (note incl. संबंधित माहिती, letter, order/parawise) carry no warning/working words, no "पॅकेज",
  no AI words, no "—"/"→"/URLs; related source ends "(पृ.N/प.वि.)" (printed "(स्रोत: …, पृ.N/प.वि.)") or no marker; unknown -> "____";
  unavailable sources/discrepancies -> Study part 4/7 + warnings. Docx metadata office-like (tools/clean_meta.py: author from
  doc_author/DOC_AUTHOR, created=modified=build time, revision 1, no stale stats); PDF metadata blank. Research: docs/AI_TELLS.md
  (77 office notes + 90 letters vs our 6 samples). Evidence: docs/ai-tells-cr131-before-after.png. Tests 293 passed.

- 03.11.2026 (Abhi: "letter, shasan nirnay ase option … user multiple option choose karel"; "default letter asel"; plan approved "ok tayar kra"):
  INSTRUCTIONS §4.28 — per run the user ticks drafts (पत्र default; स्मरणपत्र, शासन निर्णय, शुद्धिपत्रक, परिपत्रक, ज्ञापन, अधिसूचना,
  परिच्छेदनिहाय उत्तर); suggestions by case stage (approval -> GR, reply -> none, no reply -> reminder, court notice -> parawise+letter);
  upload file types reply/approval/court_notice. runs.outputs (migration 0008); spec "orders": [..] (one Order_Draft.docx, new page each)
  and "letters": [..] (letter + reminder). Tests 309 passed; worker 21/21.

- 03.11.2026: run #8 (case 7) done in 44 min, $2.80 (Claude step 36.5 min). Abhi: warnings into the Study, not the noting
  (tools/study_warnings.py, end of भाग 7; app shows one neutral line). Per-stage timing (tools/run_timeline.py, stream-json
  stamped to $RP/*.stream.tsv, "Stage times (वेळ-तक्ता)" step, owner-only "मॉडेल: वेळ …" line) — read it on the next run.
  Circular 10.08.2021 (शासन शब्दकोश भाग-1) now in pdf/09-marathi-grammar-shuddhalekhan/ (Download extra PDFs, 20c55da) — Pending 7(e) closed.

- 04.11.2026 (Abhi: "पत्रासोबतच अधिसूचना शासन निर्णय पत्र अशा अनेक बाबी तयार करायचे असतात हे सुद्धा तयार करता यायला पाहिजे";
  all eight new types selected; ज्ञापन and स्मरणपत्र unchanged): eight new draft types, formats only from official specimens.
  Draft keys (app/engine `outputs`): do_letter (अर्धशासकीय पत्र, letter `"kind": "do"`, tools/mkdocs.py), uo_note
  (अनौपचारिक संदर्भ, note `"uo"` block), endorsement (पृष्ठांकन), office_order (कार्यालयीन आदेश), press_note
  (प्रसिद्धीपत्रक), addendum (शासन पूरकपत्र) — tools/build_order.py + lint_order.py; affidavit (शपथपत्र, English,
  tools/build_affidavit.py + lint_affidavit.py, <PREFIX>_Affidavit.docx); lq (विधानमंडळ प्रश्नाचे उत्तर, tools/build_lq.py +
  lint_lq.py, <PREFIX>_LQ_Answer.docx). Research (sources + pages + open points): docs/FORMS_RESEARCH_DO_UO.md,
  docs/FORMS_RESEARCH_ORDERS.md, docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md, docs/LEGISLATURE_INSTRUMENTS_RESEARCH.md. Samples:
  samples/specs/LETTER_do_example.json, NOTE_uo_reference_example.json, ORDER_{endorsement,office_order,press_note,
  addendum}_example.json, COURT_affidavit_example.json, LQ_answer_example.json. Docs: INSTRUCTIONS §4.28 list + new §4.33,
  PROPOSAL_SOP Step 3 / Step 4b, PROPOSAL_WORKFLOW §२.4, tools/ENGINE_BRIEF.md [I4.33] (brief also brought under the
  tests/test_engine_brief.py size limit: 29436 -> 28576 bytes, duplicates/provenance quotes removed, lines reflowed;
  no rule dropped). Gap: tools/verify_outputs.py does not check the _Affidavit / _LQ_Answer files yet.

- 06.11.2026 (CR 14/2026 run review): engine accuracy checks A1–A8 (tools/engine_supabase.py ACCURACY); four new lint WARNs
  (a quote opening mid-sentence, "____ आहे" duplicating a missing-info item, a copy of a reference letter asked again, one name
  in two forms); tools/mkdocs.py table widths from content + the signers kept with the closing para; runners pinned to
  ubuntu-24.04 after run #17 (Install tools timeout); letter layout INSTRUCTIONS §4.38 (Abhi: "अ मान्य, आ एकाच क्रमाने, इ तसेच
  ठेवा …"; basis the Department's letter dt. 30.03.2026 and the HC letter dt. 17.11.2025, CR 14 pp. 26, 4): विषय / संदर्भ
  bold incl. labels, right-shifted block (not centred); requested points "(1)", "(2)" … one sequence, indented; first letter
  para unnumbered, later "2.", "3."; "प्रत" once ("प्रत :-" + numbered lines ending "निवड नस्ती"); note unchanged. Rule text:
  INSTRUCTIONS §4.5/§4.10/§4.20/§4.22/§4.38, SOP Step 4/7, WORKFLOW §३/§४, ENGINE_BRIEF (size unchanged), PROPOSAL_PROMPT भाग 6.

- 06.11.2026 run #19 (case 9) failed after 14 min / $3.60 with "status.json वाचता आले नाही": the orchestrator called the
  drafter without `run_in_background: false` (CLI 2.1.300 starts subagents in the background by default) and ended its turn;
  the CLI stopped the drafter 10 min later. Fix: ENGINE_PROMPT — every Agent call passes `"run_in_background": false`
  explicitly; workflow — CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 in the engine env (the step timeout still bounds the run).
- 06.11.2026: skills/lj-prastav-desk6/SKILL.md — updated claude.ai skill (procedure + tools only; all drafting rules point to the repo files, stale rules removed) for Abhi to upload in place of his current skill.

## Pending
28. **Open (Abhi, 06.11.2026):** (a) A7 name-form default = the form in the covering letter (provisional; Abhi to confirm);
    (b) the CR133 sample carries the same "____ आहे" duplicate of a missing item — Abhi to decide whether to rewrite it.
27. **Self-hosted runner on Abhi's VPS (05.11.2026, Abhi: "Ok go ahead", "दोन्ही मान्य आहे"; no money for GitHub Actions):**
    deploy/vps-runner/ (Dockerfile pinned by digest, entrypoint, cleanup hooks, vps-setup.sh), docs/VPS_RUNNER.md (Marathi owner
    steps). All workflows: runs-on ${{ fromJSON(vars.RUNS_ON || '"ubuntu-latest"') }} — repo variable RUNS_ON =
    ["self-hosted","prastav"] moves jobs to the VPS; delete it to go back (Actions quota resets 1 December; AdvanceTradingPlatform
    used $296.80 of the $309.98 included in November). Container: --cpus 1.5 --memory 5g, SYS_ADMIN + apparmor unconfined for the
    sandbox bind mount, no NET_ADMIN (engine_isolation must stay off), cleanup wipes every job's files. Worker EDIT_STALE_MS 30 ->
    90 min (one runner: an edit can wait behind a full run). Owner steps: runner token, ONE command block on the VPS, variable
    RUNS_ON, Settings "एकाच वेळी चालणारे run" = 1, then Deploy app. Not yet verified on the VPS (image build, mount in container,
    setup-python, a full run).
26. **GitHub Actions blocked (05.11.2026 from 14:49 UTC):** every job fails at once with "The job was not started because recent
    account payments have failed or your spending limit needs to be increased" — engine runs, edits, tests and Deploy app cannot
    run until Abhi fixes GitHub → Settings → Billing and plans (payment / Actions spending limit). Nothing to deploy right now:
    no app / Worker change since the 14:00 deploy; the engine reads rules from main at run time. Tests workflow now runs on main
    pushes + PRs only (branch pushes were doubling the minutes).
25. **05.11.2026 owner rule decisions (INSTRUCTIONS §4.36) — on main + deployed:** C1 (आ) no incoming LETTER number anywhere in
    the note (order nos., GR / petition / C R nos., U.O. and other-desk reference nos. only when on record — kept); C2 (आ) +
    wording (आ): missing-info para "सदर प्रकरणी <प्राधिकारी> यांच्या दि. … रोजीच्या प्रस्तावाचे अवलोकन केले असता, त्यामध्ये खालील
    माहिती आढळून येत नाही:- (1) …; (2) …." inline; C3 (अ) court para 1 GP letter form / "सादर."; "(लॉजिंग)" dropped in Marathi
    note/letter; C4 no change; C5 (आ) old samples rewritten (CR66/122/128/130/133, COURT_*) — owner saw the comparison PDF;
    C7 (अ) affidavit Times New Roman (+ DVOT-SurekhMR for Marathi); cropped scan letters stay as plain words. Brief at
    31,740 / 31,744 bytes — next change needs compaction. **Open (Abhi):** flow decisions from docs/FLOW_RESEARCH.md —
    (1) one issue per numbered para with sub-points, (2) "उपरोक्त वस्तुस्थिती" list vs "उपरोक्त वस्तुस्थिती विचारात घेता," in
    the सबब para, (3) condition table vs linked condition sentences, (4) para 2 "सदर पत्रान्वये …". Owner asked for 2–3 of his
    own approved notes as flow models (not yet given).
24. **05.11.2026 second round (Abhi: "Yes go ahead", "Run multiple agent") — deployed:** Q-F1 tools/fact_check.py (note/letter
    dates, amounts, letter nos., names vs the cited package page; soft warnings ≤4 to Study part 7, wide-mode misses owner-only;
    inside workflow step "Check extracts"); Q-F15 tools/consistency_check.py (same facts across note / letter / orders / parawise /
    affidavit / lq / Study part 0; ≤6 soft warnings; step "Check consistency"); Q-F10 shortened quotes completed in 5 samples
    (CR130 table cells 1 and 3 left: proposal PDF not in repo; COURT_* Rule 58 page 71 cropped letters completed as plain words —
    asked Abhi whether to show them in [ ]); UI leftovers (run-state badge words, column headers, chart axis labels, toast with
    "पूर्ववत करा" also on the case page); small security (upload magic bytes, step text cleaning, OTP shouldCreateUser false +
    owner auth user at setup, migration 0015 cases column guard + activity insert only by trigger, pinned checkouts,
    hash-locked engine requirements); S-F1/S-F2 engine isolation behind KV engine_isolation (default off; docs/ENGINE_ISOLATION.md;
    egress allowlist: Worker, gr.maharashtra.gov.in, archive.org, sci.gov.in, bombayhighcourt.nic.in,
    finance.maharashtra.gov.in). Tests: pytest 630 passed, worker 54/54, all samples LINT OK, app build OK.
    **Owner actions:** migration 0015 (supabase/migrations/20261105000015_case_column_guard.sql); Supabase Auth: turn off
    "Allow new users to sign up". **Needs live runs:** fact/consistency warning rates on a real case; engine_isolation "on" test
    per docs/ENGINE_ISOLATION.md. Still open: letters_write for staff, members see all members (S-F7 rest).
23. **05.11.2026 owner decisions done:** (a) note signer chain §4.6 changed on Abhi's own note page ("asa bdal kra"):
    "(अ.मा. वसू)" (not bold) + "क. अ. (अ.का.)" on the right, then अ.स. (श्री. वडनेरकर) / उ.वि.स. नि. उ.स. (श्री. बोंद्रे) /
    सचिव व व. वि. स. (श्री. बिले) left; अ.मु.स. (वित्त) rule unchanged — desk profile signers_right/signers_plain, mkdocs,
    lint, brief, SOP, WORKFLOW, PROPOSAL_PROMPT, all 24 samples. (b) two runs at once: KV max_parallel_runs (1–3, default 2),
    Settings dropdown; risks: monthly spend can overshoot by ~1 run, double GitHub minutes / API load. (c) /nasti dark-mode
    selected tab colour (injected CSS, owner file untouched). (d) migration 0014 applied ("Success. No rows returned").
    WhatsApp share text keeps the case subject (Abhi 05.11.2026: "व्हाट्सअप वर प्रकरणाचा विषय ठेवायचा"; S-F18 closed, no change).
    Data region: stays Tokyo for now (Abhi 05.11.2026: "डाटाबेस टोकियोला आहे राहू द्या … नंतर कधीतरी विचार करूया सध्या
    आपला प्रोजेक्ट … टेस्टिंग मोडमध्ये आहे").
    **Audit 05.11 items NOT built yet:** Q-F1 fact-anchor check (every number/date/name of the note against the proposal
    pages), Q-F15 cross-document consistency (note / letter / orders / parawise / Study part 0), T-D reviewer fully parallel
    (partly), P7 PDF range loading (measured slower — dropped), Phase 4 security S-F1 (engine key via local gateway +
    outbound limit), S-F2 (case-scoped DB key), S-F4 (/nasti isolation + SheetJS upgrade, owner's file), S-F17 (repo zips),
    P8 (/nasti lazy-load), re-baseline of samples after rule decisions C1–C8.
22. **Audit 05.11 fix round (docs/AUDIT_2026-11-05.md; Abhi: "kam purn kra") — merged + deployed 05.11.2026** (live bundle
    index-Cf3VpA1S.js, inline #pk-config; engine UA "prastav-kaksha-engine/1" passes Cloudflare, Python default UA still 1010).
    Tests: pytest 589 passed, worker 46/46, all samples LINT OK, app tsc/build OK. **Owner action: apply migration 0014**
    (supabase/migrations/20261105000014_run_guards_indexes.sql). Not yet seen on a live run: no-wait-loop prompt, Sonnet
    fixer, per-agent cost line, OCR reuse, stale-spec guard — check on the next full run + edit. New WARNs on approved samples
    (40-word sentences, "पूर्वोदाहरण-ग्रंथालय" in sources, summary-list length) listed in tests/test_lint_spec.py
    AUDIT_KNOWN_WARNS — samples not rewritten (needs Abhi). Still open owner decisions: rule conflicts C1–C8, signer-chain
    change (permanent / per case), 2 runs at once, data residency, nasti page (owner's file: dark-mode tab contrast, SheetJS).
21. **UI audit + fix round (04.11.2026, docs/UI_AUDIT_2026-11-04.md; Abhi: "Run multiple agent"):** 5 parallel fix agents — wording/glossary + owner-only technical text (lib, Worker), case page (download strip, compact header, 3x2 tabs, duplicate-C R notice, single reply flow), new proposal (bug: extra files after start never uploaded — fixed; required-only form; draft picker fold), settings/GR/search/login, shell/home/cases + /nasti option C (phone full-screen, "← प्रस्ताव कक्ष" bar, compact नस्ती header via injected CSS). Defaults taken: /nasti option C; floating AI hidden on /cases/:id. Not verified on a real phone. Leftovers: RunStateBadge wording (S5 values), QueueCard dark-mode numbers, Charts axis label, Toast action button for undo.
20. **Terms (Abhi, 04.11.2026):** "टिप्पणी" = noting (app says टिप्पणी, not नोंद, wherever the note is meant; नोंदवही / नोंदवा / record-नोंद unchanged); "मसुदा" / draft = the pre-approval draft of a letter, शासन निर्णय, अधिसूचना etc. — the noting is not called a मसुदा. Case stage value "मसुदा तयार" left as is (stored DB value).
19. **Engine prompt size (04.11.2026, run #12 failed "Argument list too long"):** the main prompt (ENGINE_PROMPT 46.9 KB + ENGINE_BRIEF 30.6 KB + tool docstrings 85.5 KB + work type 0.9 KB = ~164 KB) exceeded the 128 KiB single-argv limit; fixed by passing it on stdin (commit 6a7d8c9; Abhi: "दुरुस्ती ठेवा"). **Done 04.11.2026 (Abhi: "इंजिन सूचनेचा आकार हा सूचनेनुसार असावा" → "हो करा"):** tools/tool_docs.py puts only the ticked drafts' tool docstrings into the prompt (letter-only run: 42 KB instead of 86 KB → prompt ~121 KB); every docstring stays in /tmp/work/TOOL_DOCS_ALL.md; outputs null → all. **Still open, after one successful live run:** Next improvement, to do after one successful live run (Abhi: "पुढील सुधारणेमध्ये वरील सुधारणा नोंदवून ठेवा विसरू नका"):** drop the inline tool docstrings from the prompt (the engine reads /tmp/work/TOOL_DOCS.md when it needs a tool) -> prompt ~78 KB; first read the run's वेळ-तक्ता and cost (cache-read vs fresh input tokens) to measure the real saving; risk = a tool rule not read -> check the drafts of the first run after the change.
18. **सुधारणा-चॅट (04.11.2026, docs/DRAFT_EDIT_DESIGN.md + Addendum A):** per-case chat (case picked + confirmed by the user; respectful Marathi), targets note / letter / order / parawise / affidavit / lq / GR सह PDF, attachments (PDF / images; Word refused — no LibreOffice on the runner), GR by सांकेतांक; one Sonnet call (`model_edit`, default claude-sonnet-5-5, no temperature — Sonnet 5.5 rejects it; effort medium, structured JSON) on the saved spec only; new file versions, old ones kept. Needs migration 0013 + deploy; works only for cases processed after this change (spec / enclosures saved by finish). Never run live yet — first real edit = the test (cost, time, language). Open points closed 05.11.2026: Settings field "सुधारणा-चॅटचे मॉडेल" (`model_edit`, owner-only, claude-* ids only — Worker CLAUDE_MODEL, app check, edit-drafts.yml, edit_drafts.py; a non-Claude KV value -> default); chat attachments are inputs of the next full run (kind `gr` rows — a GR fetched by सांकेतांक is now stored as one — + edit_attachments of done, not refused edit runs; case.json `"package": true`, images converted to `<image>.pdf` at fetch; ENGINE_PROMPT Inputs line; finish warns when one is missing from enclosures.json or enclosed twice; later edits resolve those paths); monthly reservation of an edit at the edit estimate confirmed by a /api/edit gate test.
17. **Bulk upload = one box per proposal (04.11.2026, Abhi: "एकाच प्रस्तावाच्या अनेक पीडीएफ वर्ड फाईल असू शकतात"):** each box = main PDF + that proposal's other files (PDF / Word / image, typed); several PDFs are never split into several proposals (also in एक प्रस्ताव: first PDF = proposal, rest = its other files). Needs a deploy.
16. **नस्ती अद्ययावत स्थिती (option आ, 04.11.2026):** apply migration 0012 (members profile + cases.nasti_no) and deploy. Decided on Abhi's "ज्या गोष्टी आवश्यक आहे त्या करा": name / designation on the नस्ती page follow the app profile (office / mine only when empty); profile visible to members (same office) kept; desktop sidebar "माझी माहिती" kept (no ⋯ menu on desktop); phone two bottom bars left as is (hiding the app nav would remove navigation).
15. **Merge 04.11.2026:** C33 relevance/flow rule renumbered INSTRUCTIONS §4.34 / brief [I4.34] (§4.32 = court-note para 2/3, §4.33 = new draft types, from the parallel session). Samples LETTER_do, NOTE_uo, WP35697 x2: पृ./प.वि. table column dropped and glued quotes split (§4.34 WARN); lint TRIVIA no longer flags the endorsement draft itself. Nasti integration: Abhi to choose option (अ)/(आ)/(इ) (scratch audit) — nothing built yet.
14. **Apply migrations 0010 (more_draft_kinds) + 0011 (work_type_queue: cases.work_type, runs.dispatched_at, queue index — C33 bulk upload / sequential queue / work categories) + deploy** (from the app/engine wiring of the eight new draft keys) — Abhi in the SQL editor,
    then Actions "Deploy app"; then one test run per new type.
13. **New draft types — open points for Abhi (04.11.2026; provisional defaults in brackets are in use, INSTRUCTIONS §4.33):**
    (a) D.O. letter (docs/FORMS_RESEARCH_DO_UO.md §5): closing — the brief said "आपला,", every official specimen has
    "आपला स्नेहांकित," (+ "शुभेच्छा") ["आपला स्नेहांकित,"]; D.O. stationery with emblem (GADT 12.27) not in the repo [none —
    give the अवर सचिव's D.O. paper if wanted]; label "अ.शा.पत्र क्र." (GADT) vs "अर्ध-शासकीय पत्र क्र." (NPM) [GADT]; sender
    "अवर सचिव." and addressee level per case [desk signer; `salutation` "प्रिय महोदय," for a senior].
    (b) U.O. block: "कार्यासन का.6" vs "कार्यासन-6" [का.6; `uo.desk`]; no official note-foot U.O. specimen, NPM परि.-8 form foot
    used [as built].
    (c) Orders (docs/FORMS_RESEARCH_ORDERS.md §6): addendum wording "<at> खालील मजकूर समाविष्ट करण्यात येत आहे:-" is composed
    (no official fixed formula) [keep; free `operative` text also accepted]; addendum label "शासन पूरकपत्र" vs L&J's own
    "शासन निर्णय पूरकपत्र" (का.8) / "शासन पूरक पत्र" (का.4) [शासन पूरकपत्र]; endorsement "यांजकडे" (NPM) vs "यांच्याकडे …
    अग्रेषित" (GADT 12.25) [NPM]; the four live addenda used as evidence not stored in pdf/gr/ [not stored]; press-note
    number / Saka date / time are DGIPR details ["____"].
    (d) Affidavit (FORMS_RESEARCH_AFFIDAVIT_LQ.md A4): O1 font — ASR XVII Rule 10(ii) Times New Roman / Georgia vs §4.2
    [DVOT-SurekhMR, 14]; O2 "aged about" (no source), nationality [age only when given; no nationality]; O3 [“the Deponent
    abovenamed”]; O4 rule's typo "known" [printed "know"]; O5 no filed Desk-6 affidavit — one would settle the authority
    para [RCLAG 58(6)(e) / MMOP 3.3 default]; O6 benches other than Bombay [jurat place from the Rule 1 bench text].
    (e) LQ answer (same file, B4): Q1 copies — GADT "१०", KKN "तीस", PAD-2026 late 450 / 250 [`copies` "____"]; Q2 signature
    "शासनाचे अवर सचिव." vs §4.5 form [specimen]; Q3 heading "पुरवणी टिप्पणी" vs "पुरवणी प्रश्नांकरिता टिप्पणी" [GADT]; Q4 extra
    signers (note goes to the Minister through the Secretary) [§4.6 chain]; Q5 current Legislature prescribed form not
    found [GADT 1993 specimen]; Q6 one past Desk-6 LQ answer would confirm the endorsement and file-no. form.
    (f) Legislature instruments (docs/LEGISLATURE_INSTRUMENTS_RESEARCH.md §6): O-1 Secretariat covering-letter formats not in
    repo [ask Abhi for one recent letter of each device; TIP specimen meanwhile]; O-2 calling-attention statement body has no
    GAD specimen [title + note + supplementary note only]; O-3 assurance compliance statement columns (PAD circular
    26.05.2016) not found [ask for a blank statement]; O-4 GAD/PAD circulars 2019–2025 not in repo / not read in full;
    O-5 which devices Desk-6 handles [question drafts first]; O-6 Marathi rule books in legacy font (titles from PAD-2026);
    O-7 time limits [PAD-2026 and the rules, not the older TIP / NPM figures].
12. **Next live run:** read the वेळ-तक्ता (job log last step) and tell Abhi which stage takes the time; check claude.err/stream size and that background agents show in the stream.
11. **Migration 0008** (runs.outputs + file kinds approval/court_notice) — Abhi to apply in the SQL editor, then deploy (app part already on main).
10. **AI-tells decisions — DECIDED 03.11.2026 (Abhi: "Default thewa, 4 madhe स्रोत/जसाच्या तसा kadha"): bracketed defaults final; (4) the words "स्रोत"/"जसाच्या तसा" removed from drafts (§4.27 (आ), lint) — docs/AI_TELLS.md:** (1) Word author name (DOC_AUTHOR) [empty];
   (2) signer forms "का.अ.(…)" / "अवर सचिव, महाराष्ट्र शासन" as in office files vs §4.5/§4.6 [current]; (3) subject/reference
   fully bold+centre (§4.10) vs office (label only bold) [current — Abhi 03.11.2026: "3 ठळक", full line bold stays]; (4) "संबंधित माहिती" block + words "स्रोत"/"जसाच्या तसा" (office
   never uses them) [keep block; drop the two words after decision]; (5) "(1)…; (2)…" lists vs office "."/"," [current];
   (6) linking words तथापि/त्यानुषंगाने/परंतु [use where fitting, one point per sentence kept].
   Items removed from samples' notes (still unavailable): CR122 — MCS Pay Rules 1981 rule 11 original, Finance circular 05.12.1985;
   CR128 — GRs 12.03.2014, 31.03.2018, 14.05.2021, 02.12.2022, 19.04.2022 (सचिव संवर्ग).
9. **After the audit fix round:** migration 0006/0007, deploy, re-run case #7; watch the first run (sandbox up/down/check lines in the log).
   Deploy from mobile: Actions → "Deploy app" (.github/workflows/deploy-app.yml; needs repo secrets CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID — not yet added by Abhi).
   02.11.2026: "Download extra PDFs" re-run — the 4 folder-09 PDFs still fail (archive.org 429, marathi.gov.in DNS from GitHub; archive.org reset from this session) → Abhi gives the PDFs (shabdakosh circular 10.08.2021 first).
7. **Language-rule conflicts — DECIDED 02.11.2026 (Abhi: "Default thewa"): the bracketed defaults below are final; only (e) still needs the PDF:**
   (a) GR 10.11.2022 अ.क्र. 6 puts a space before ":" ("उपलब्ध नाही :-"); §4.19 / samples use "नाही:-" [keep "नाही:-"].
   (b) GADT error list: "कलम ३ नुसार" wrong → "कलम ३ अनुसार"; samples' own text has "नियम 48 नुसार", "दि. … नुसार" (CR128/130/131/133) [no lint; unchanged].
   (c) "मंत्रिमंडळ" correct (GADT p.65); CR128 "मंत्रीमंडळासमोर" is inside a quoted extract [kept verbatim].
   (d) "एम.ए./पीएच.डी." and शुद्धलेखन rules 15–18 rest only on the non-official copy (STYLE_RESEARCH_LANG §5.2) [warning level only].
   (e) Circular 10.08.2021 (शासन शब्दकोश भाग-1) is not in the repo (pdf/FAILED-extra.txt; 403 from this session); 00-INDEX of folder 09 says it was obtained — wrong [fetch via the GR request Action / Abhi gives the PDF].
   (f) L11 (…णेबाबत) also warns on letter subjects taken from the proposal ("…मिळणेबाबत") [warning only; Abhi decides whether to convert subjects].
8. **Workflow dry run** of the new brief on GitHub: needs a real run (run token) — check the first live run's log [watch the next run].
0. **PR #3** — merged 02.11.2026 on Abhi's word; migration 0005 (`config_taken_at`) applied by Abhi 02.11.2026; deployed by Abhi 02.11.2026 (Worker version 78929fda…; live check: index-Cr79S6qR.js, /nasti/ serves the नस्ती page, /api/engine/step answers 403 bad token). Other providers (D16): choose in Settings → इतर AI; free hosted models are not confidential-safe (table there). First live run after merge = check of H1 on the real runner (engine user, sudo, bind mount) — watch the run; if it fails at "Process the proposal", the log line names the step. A/C need Abhi's paid Gemini/OpenAI keys in Settings; first real use on an approved case (CR131) and compare.
1. **C R 128/2026** — Abhi to give सांकेतांक for 4 GRs (12.03.2014, 31.03.2018, 14.05.2021, 02.12.2022) and the CR 128 proposal PDF (not in repo). Then download (gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf) and rebuild the package: proposal = CR 128 PDF; enclosures SC order pdf/sc/... p.1,2,20,34,35 (para 14 a–c highlighted, p.34), pdf/gr/202204191549468012.pdf p.1-2, pdf/gr/202301111807499612.pdf p.1-2, MJS Rules 2008 pdf/71-district-court-staff-recruitment-rules/... p.1,2,18,19,20, MCS Pension Rules 1982 pdf/80-retirement-age-group-d-reemployment/... p.11,12,22, then the new GRs; update पृ./प.वि. in samples/specs/CR128_*.json; rebuild with tools/build_note_letter.py.
2. **App A desk page** — Abhi 02.11.2026: KEEP App A (alongside App B). Live page = https://claude.ai/artifact/8cJP8wz6j5tYM5kRHK1rVx (RYzwfiGwJpbVxyD5C2rCy2 no longer exists — 404; SOP Step 0b + docs/PROPOSAL_DESK.md updated). Next: Abhi checks the three downloads on TEST-1, then Claude deletes TEST-1 (cases/TEST-1, outputs/TEST-1__*, assets bdb3fa89612a93be3a0df53ac37f98e9, cfa33bb4f301bb18e77e27aa9eb41fd6).
3. **Pack 3 decisions still open (Abhi)** — docs/QUALITY_AUDIT.md: which pdf/ folders the engine needs (sparse checkout); approve-before-save rule for samples/specs (App A: kept, item 2).
4. **First live run with the cost tiers** — confirm cost (run's "मॉडेल: खर्च" line), routing (drafter used for quality-critical work) and part1check mismatch rate.
5. **Style research** — letter/lang decisions F6, F7, F10, F5 done 02.11.2026 (§4.21–4.24); F8 (आपला विश्वासू) and F9 (महोदया) stay as they are (defaults). Also 02.11.2026: grammar/शुद्धलेखन research added (STYLE_RESEARCH_LANG.md §5; PDFs in pdf/09-marathi-grammar-shuddhalekhan/). Open for Abhi: "अनुसरुन"→"अनुसरून" in SOP/samples (rule 8.9), lint L11. Run Actions → "Download extra PDFs" for the 4 URLs the sandbox could not reach (pdf-list-extra.tsv, folder 09).
6. Study part 0 (§4.17) for C R 130, 131, 133 — only if Abhi asks.

## Network notes
- Session allowlist "All domains" (gr.maharashtra.gov.in, archive.org, sci.gov.in, finance.maharashtra.gov.in reachable). If blocked, use the GitHub Action "GR request" (push tools/gr-request.txt).
- Office network: GitHub/vercel blocked; Cloudflare (workers.dev) and Supabase work.
