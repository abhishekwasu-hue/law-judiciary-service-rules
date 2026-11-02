# APP_B_DESIGN.md — "प्रस्ताव कक्ष" full-stack app (build prompt B) — design + decisions log

Prompt: `docs/APP_B_FULLSTACK_PROMPT.md`. Built on `app-b/proposal-desk-fullstack`, merged to `main` (cf0315d); all later work on main.
**Status 01.11.2026: LIVE** https://prastav-kaksha.abhi-desk.workers.dev — Supabase project `vxkktnymewcvcqysilgx`, Tokyo
(ap-northeast-1; Mumbai not offered at creation); migrations 0001–0004 applied by Abhi in the SQL editor. One stored file for all B research/decisions (OWNER_RULES A.11).

## Audit of the existing draft (01.11.2026)
- `cloudflare/worker.js` + `dashboard/index.html`: password header auth, files stored IN the repo (`inbox/`, `cases/`) through the GitHub contents API. → replace storage with Supabase; keep the idea "browser talks only to workers.dev".
- `.github/workflows/process-proposal.yml`: triggered by a push to `inbox/*.pdf`; runs `tools/run_headless.sh` (Claude Code headless, `tools/HEADLESS_PROMPT.md`). → keep the headless run; trigger by `repository_dispatch`; read/write Supabase.
- `tools/HEADLESS_PROMPT.md` rule 5 names the PDF `<PREFIX>_Proposal_with_GRs.pdf` — conflicts with INSTRUCTIONS §4.16 (original file name). → fix in the B engine prompt.
- Secrets today: Worker secrets `GH_TOKEN`, `DASH_PASSWORD`; repo secret `ANTHROPIC_API_KEY`.

## Owner rules for B
- 01.11.2026 (Abhi): **API key, Supabase and Cloudflare settings live in the app's Settings screen — nothing hard-coded.**
- Office: github.com blocked → the browser talks only to the Worker (workers.dev) and Supabase.

## Decisions (provisional defaults — Abhi may change; logged per OWNER_RULES A.9)
D1. **Settings store = Cloudflare KV namespace `SETTINGS`** bound to the Worker. Keys: `supabase_url`, `supabase_anon_key`,
    `supabase_service_key`, `github_repo`, `github_branch`, `github_token`, `anthropic_api_key`, `model`, `model_light`,
    `budget_usd`, `owner_email` (cloudflare/worker.js SECRET_KEYS + PLAIN_KEYS). Entered on the
    Settings screen (owner only). The Worker never returns a secret to the browser — only "set / not set" and the last 4 characters.
D2. **First-run setup without hard-coding.** While KV has no `owner_email`, the app shows "प्रारंभिक सेटअप". The Worker creates a
    random `setup_code` in KV on first request; Abhi reads it in the Cloudflare dashboard (Workers → KV → SETTINGS) and types it
    into the setup form with the Supabase values and his email. After that, setup is locked; Settings needs the owner login.
D3. **Login = Supabase Auth email OTP.** The Worker verifies each call's JWT with `GET <supabase_url>/auth/v1/user`. Roles in table
    `members` (owner / staff / senior read-only); the owner invites colleagues.
D4. **Engine keys reach GitHub Actions at run time, not as repo secrets.** On a run the Worker creates a run token
    (KV, 4 h TTL > 180 min job timeout) and sends `repository_dispatch` `{case_id, run_id, token, worker}`. The workflow calls
    `GET /api/engine/config` with the token, masks the values (`::add-mask::`) and gets: Anthropic key, model, model_light,
    budget_usd, Supabase URL + service key. The token is **single use for the config** (marked used on the first read; a 412
    "config incomplete" leaves it unused). After that it is good only for `POST /api/engine/fail` (marks THIS run failed with a
    reason; returns nothing secret) until it expires — used when the workflow has no Supabase env. Stuck runs (queued/running
    > 3.5 h) are failed by `POST /api/runs/sweep`, called by the app on load. Changing a key in Settings takes effect on the
    next run. Only the GitHub token (to dispatch) is used by the Worker itself.
D5. **Engine = GitHub Actions (prompt option a)**, Claude Code headless with the repo's CLAUDE.md, one proposal per run.
D6. **Data = Supabase** Postgres (tables per prompt §4, RLS on all), Storage private buckets `proposals`, `outputs`, `gr-library`,
    signed URLs 10 min issued by the Worker, Realtime on `cases` and `runs`.
D7. **Front end** = React + Vite + TypeScript + Tailwind, Recharts, pdf.js, docx-preview — exact versions pinned in package.json;
    built to `dashboard-app/dist`, served by the same Worker (static assets) → one workers.dev URL.

D8. (01.11.2026) **Supabase Storage keys are ASCII** (`file<ext>`, unique per upload) — live 400 InvalidKey on a Devanagari
    name; the original name is kept in `case_files` and used for downloads (§4.16). Engine output keys ASCII too.
D9. (01.11.2026) **Duplicate C R** at upload → Worker 409 `{error:"duplicate_cr", existing_id}`; the app shows a notice with a
    link to the existing case. The engine keeps filling other fields and records the duplicate.
D10. (01.11.2026) **Model tiers** (docs/QUALITY_AUDIT.md §6; Abhi: quality must not drop): orchestrating session on
    `model_light` (default claude-haiku-5-5; mechanical work, machine-checked); `drafter` subagent on `model` (default
    claude-opus-5-5) for all quality-critical work (facts from page images, letter decision, GR selection + verbatim quotes,
    note/letter, Study 0, 2, 3, 4, 7); optional `drafter_strong` (MODEL_STRONG, workflow env, off by default — not a Settings
    key) for one-way escalation. Study part 1 on the cheap tier is kept only if part1check matches the drafter's facts.
D11. (01.11.2026) **Budget is SOFT** — `budget_usd` (engine default 0.75; Worker accepts > 0 and ≤ 20; Abhi set 1.5): going
    over adds the warning "खर्च-मर्यादा ओलांडली — दर्जा राखण्यासाठी", never stops or degrades a run. Cost, turns and per-model
    use stored per run (migration 0004).
D12. (01.11.2026) **Engine speed/quality steps:** page pre-step (tools/prep_pages.py), compact rules tools/ENGINE_BRIEF.md,
    lint before build, verify re-run in the workflow; §4.18 language rule in samples + lint.
D13. (02.11.2026, Abhi: "Ek tab add karun he application, tyamdhe add kra") **"नस्ती डॅशबोर्ड" tab** — Abhi's
    नस्ती-स्थिती डॅशबोर्ड (Nasti-Dashboard.apk, Capacitor; its single page assets/public/index.html) copied UNCHANGED to
    `dashboard-app/public/nasti/index.html` (sha256 fa757418…) and shown at `/nasti` in a full-height iframe
    (`src/pages/NastiDashboard.tsx`; nav item 📊; phone bottom bar 6 columns). Its data stays in the browser's localStorage
    (same origin), not in Supabase; Android-only plugins fall back to browser download/share/copy. The static file is served
    without login (it holds code, no data). Needs a deploy (scripts/deploy.ps1) to go live.
D14. (02.11.2026, Abhi: "पहिले तीन H मुद्दे दुरुस्त करा") **Engine isolation (H1):** checkout without persisted
    credentials; keys only in the runner's 700 file `/tmp/engine-secrets/secrets.env` (ENGINE_SECRETS; read by
    engine_supabase.py), never in the job env; Claude runs as unix user `engine` (no sudo) on a bind mount `/srv/engine`
    with an explicit env (Anthropic key, run ids, run token, model names). Progress text via Worker `POST /api/engine/step`
    (run token, this run only). The commit step authenticates with `secrets.GITHUB_TOKEN` in that step only.
    **Review gate (H2):** verify reads `/tmp/work/review.json` itself; it must be approved and carry `spec_sha256` /
    `part0_sha256` equal to the final files, and the CLI's modelUsage must show MODEL_REVIEW ran (skipped only when it is
    the orchestrator's model). **One run per case (H3):** Worker `/api/run` → 409 `run_active` while a non-stale
    queued/running run exists; the app locks the button from the API reply.
D15. (02.11.2026, Abhi: "AI साठी A व C") **Other providers** (research: docs/AI_PROVIDERS_RESEARCH.md). Settings: secrets
    `gemini_api_key`, `openai_api_key`; plain `part1_provider` (''|claude|gemini), `gemini_model`, `fallback_provider`
    (''|gemini|openai), `fallback_model`, `fallback_model_light`. A key leaves the Worker only when its provider is chosen.
    **A:** `tools/gemini_part1.py` writes Study part 1 (one request per page, runner user; result in the Claude result
    format for cost lines); part1check gate unchanged. **C:** when the main Claude run fails on the provider side
    (`engine_supabase.py fallback_ok`), LiteLLM 1.105.1 (wheel sha256-checked) is started as the runner on 127.0.0.1:4000
    and the main run is repeated through it (all Claude model names → fallback models); warning on the case; all gates
    apply; cost recorded at Claude prices (approximate). Paid keys only. Not yet run with real Gemini/OpenAI keys.

## Open questions for Abhi (work continues on the defaults)
Q1. D1/D2 (keys in Cloudflare KV via Settings; setup code read once from the Cloudflare dashboard) — OK?
Q2. Accounts needed from Abhi (no code change): a Supabase project, a Cloudflare account, a GitHub fine-grained token
    (this repo: Actions R/W, Contents R/W, Metadata R), an Anthropic API key. All are typed into Settings, not into code.
Q3. Second AI provider as fallback — default: none.

## Build order and status
1. Supabase schema + storage + RLS — `supabase/migrations/20261101000001_init.sql`, seed `supabase/seed.sql` (tools/app_seed_gr.py) — DONE. Tested in PGlite with stub auth/storage schemas: owner insert OK, senior insert refused by RLS, senior read OK, non-member reads 0 rows, stage change logged in `activity`, 19 GR rows. Note: Marathi stage/category are text + CHECK (Postgres enum labels max 63 bytes).
2. Worker API + settings store — `cloudflare/worker.js`, `cloudflare/wrangler.toml` (no keys; KV id pasted at deploy) — DONE. Endpoints: public-config, setup, settings (owner, secrets masked), me, members (invite), cases, upload (original name, versions), run (dispatch), files/:id (signed 10 min), gr (fetch by सांकेतांक), search (register/), letters, engine/config (one-time run token). Test: `node --test cloudflare/test/worker.test.mjs` passes.
3. Engine — `.github/workflows/process-proposal.yml` (repository_dispatch process_proposal; keys fetched from the Worker per run and masked), `tools/engine_supabase.py` (fetch/step/log_url/finish/fail), `tools/ENGINE_PROMPT.md` (fixes the §4.16 file-name conflict of the old HEADLESS_PROMPT) — DONE; `py tests/engine_supabase_test.py` ALL TESTS PASSED (mock Supabase). Live run not verified (needs Abhi's accounts). NOTE: repository_dispatch uses the workflow on the default branch → merge to main before the first live run.
6. Deploy kit — `docs/APP_B_SETUP_MR.md` (Marathi), `scripts/deploy.ps1`, `supabase/config.toml`, daily DB backup `supabase/migrations/20261101000002_backup.sql` (pg_cron, last 30, tested in PGlite; Storage files not backed up) — DONE.
4. Front end `dashboard-app/` (React 18.3.1, Vite 5.4.11, TS 5.6.3, Tailwind 3.4.15, supabase-js 2.46.1, recharts 2.13.3, pdfjs-dist 4.8.69, docx-preview 0.3.3) — DONE, `npm run build` passes: setup, OTP login, Settings (keys masked), new proposal (per-file progress, Realtime run steps = engine's Marathi step texts), case list/Kanban/CSV, case detail 6 tabs, Home KPIs + charts, GR library, register search. Not run against a live Worker/Supabase. Limits: swipe actions not built (stage select instead), export CSV, signature-chain settings = note only.
5. Charts / Kanban / rest of prompt §6 — DONE inside step 4.
7. Live deploy — DONE 01.11.2026 (Abhi's accounts; URL and Supabase project above). First live runs ~10 min, $2.28–3.32
   (all on Opus, before D10/D11). Expected with tiers $1.0–1.8 — not yet measured. Later UX: auto-reload after deploys,
   Marathi errors, duplicate C R notice, live ETA from real run times.
