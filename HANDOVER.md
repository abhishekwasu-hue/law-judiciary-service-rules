# HANDOVER — state as of 01.11.2026 (App B live, cost tiers, §4.18) (read after CLAUDE.md files)

## Done (all in this repo)
- Procedure: INSTRUCTIONS.md §4 items 1–18 (§4.18, 01.11.2026: sentence flow + respectful language), PROPOSAL_SOP.md, PROPOSAL_WORKFLOW.md, samples/specs/ (approved notes), tools/ (mkdocs, build_note_letter, build_study, pkg3, highlight, lint_spec, verify_outputs, gr_request, oldcases_text, prep_pages).
- Proposals delivered: C R 66, 122, 128, 130, 131, 133 /2026. GRs in pdf/gr/ (+INDEX.tsv), SC order in pdf/sc/, MCS (Pay) Rules 1981 in pdf/01-mcs-pay-rules-1981/. CR 128: 05.08.2026 and 19.04.2022 GRs downloaded; 4 others not on archive.org (see Pending 1).
- **App B (प्रस्ताव कक्ष full-stack) — LIVE** https://prastav-kaksha.abhi-desk.workers.dev. Supabase project `vxkktnymewcvcqysilgx`, Tokyo (ap-northeast-1; Mumbai not offered at creation). Migrations 0001–0004 applied by Abhi in the SQL editor (0003 optional case fields, 0004 reliability). Settings in Cloudflare KV `SETTINGS`: owner_email, supabase_*, github_repo/branch/token, anthropic_api_key, model, model_light, budget_usd (Abhi: 1.5). Design + decisions: docs/APP_B_DESIGN.md; setup (Marathi): docs/APP_B_SETUP_MR.md; audit + fixes: docs/QUALITY_AUDIT.md.
- Engine = GitHub Actions `repository_dispatch` on main (.github/workflows/process-proposal.yml): page pre-step (prep_pages.py), compact rules tools/ENGINE_BRIEF.md, 3 model tiers (cheap orchestrator `model_light`, Opus `drafter` for quality-critical work, optional `drafter_strong` escalation), Study part 1 on the cheap tier kept only if part1check matches, lint before build, verify re-run in the workflow, soft budget (warning only), cost/turns stored per run.
- App UX: auto-reload after deploys, Marathi errors, duplicate C R notice at upload (Worker 409 + link), ASCII Storage keys (original name kept), stuck-run sweep, live ETA.
- First live runs: ~10 min, $2.28–3.32 (before the cost work). Expected after tiers: $1.0–1.8 — not yet measured.
- Repo is private.
- Pack 3 decisions (Abhi, 01.11.2026): the confidential old-case zips stay in the repo and its git history (NOT removed; repo private); the old dashboard/ folder stays (NOT removed).

- 01.11.2026 style decisions (Abhi): keep full verbatim GR extracts in the note body and the detailed information-request note (GAD-manual options to shorten were declined); names as in the proposal (Marathi initials only if the proposal has them). Letter lint added: no तातडीने/त्वरित-type words, no bare command endings, 'कै.' spacing. Research: docs/STYLE_RESEARCH.md (GAD), docs/STYLE_RESEARCH_LETTERS.md (letters); docs/STYLE_RESEARCH_LANG.md pending. Open letter decisions: स्मरणपत्र support, extra copy line for HC route, 'मा.' usage.

- 02.11.2026: Abhi approved the CR131 sample built under §4.18–§4.20 (samples/specs/CR131_2026_special-pay_info-letter.json) — the model for letter tables (data only; documents listed after the table) and language.

## Pending
1. **C R 128/2026** — Abhi to give सांकेतांक for 4 GRs (12.03.2014, 31.03.2018, 14.05.2021, 02.12.2022) and the CR 128 proposal PDF (not in repo). Then download (gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf) and rebuild the package: proposal = CR 128 PDF; enclosures SC order pdf/sc/... p.1,2,20,34,35 (para 14 a–c highlighted, p.34), pdf/gr/202204191549468012.pdf p.1-2, pdf/gr/202301111807499612.pdf p.1-2, MJS Rules 2008 pdf/71-district-court-staff-recruitment-rules/... p.1,2,18,19,20, MCS Pension Rules 1982 pdf/80-retirement-age-group-d-reemployment/... p.11,12,22, then the new GRs; update पृ./प.वि. in samples/specs/CR128_*.json; rebuild with tools/build_note_letter.py.
2. **App A desk page** (claude.ai artifact) — Abhi decides: keep RYzwfiGwJpbVxyD5C2rCy2 or 8cJP8wz6j5tYM5kRHK1rVx, or retire App A (App B is live). If kept: Abhi checks the three downloads on TEST-1, then Claude deletes TEST-1 (cases/TEST-1, outputs/TEST-1__*, assets bdb3fa89612a93be3a0df53ac37f98e9, cfa33bb4f301bb18e77e27aa9eb41fd6).
3. **Pack 3 decisions still open (Abhi)** — docs/QUALITY_AUDIT.md: which pdf/ folders the engine needs (sparse checkout); approve-before-save rule for samples/specs; App A keep/retire (item 2).
4. **First live run with the cost tiers** — confirm cost (run's "मॉडेल: खर्च" line), routing (drafter used for quality-critical work) and part1check mismatch rate.
5. **Style research** in progress (docs/STYLE_RESEARCH*.md) → Abhi chooses rules → then INSTRUCTIONS §4 + samples.
6. Study part 0 (§4.17) for C R 130, 131, 133 — only if Abhi asks.

## Network notes
- Session allowlist "All domains" (gr.maharashtra.gov.in, archive.org, sci.gov.in, finance.maharashtra.gov.in reachable). If blocked, use the GitHub Action "GR request" (push tools/gr-request.txt).
- Office network: GitHub/vercel blocked; Cloudflare (workers.dev) and Supabase work.
