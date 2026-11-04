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

## Pending
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
