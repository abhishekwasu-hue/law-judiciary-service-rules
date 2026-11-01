# APP_B_DESIGN.md — "प्रस्ताव कक्ष" full-stack app (build prompt B) — design + decisions log

Prompt: `docs/APP_B_FULLSTACK_PROMPT.md`. Branch: `app-b/proposal-desk-fullstack`. One stored file for all B research/decisions (OWNER_RULES A.11).

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
    `supabase_service_key`, `github_repo`, `github_token`, `anthropic_api_key`, `model`, `owner_email`. Entered on the
    Settings screen (owner only). The Worker never returns a secret to the browser — only "set / not set" and the last 4 characters.
D2. **First-run setup without hard-coding.** While KV has no `owner_email`, the app shows "प्रारंभिक सेटअप". The Worker creates a
    random `setup_code` in KV on first request; Abhi reads it in the Cloudflare dashboard (Workers → KV → SETTINGS) and types it
    into the setup form with the Supabase values and his email. After that, setup is locked; Settings needs the owner login.
D3. **Login = Supabase Auth email OTP.** The Worker verifies each call's JWT with `GET <supabase_url>/auth/v1/user`. Roles in table
    `members` (owner / staff / senior read-only); the owner invites colleagues.
D4. **Engine keys reach GitHub Actions at run time, not as repo secrets.** On a run the Worker creates a one-time run token
    (KV, 3 h TTL) and sends `repository_dispatch` `{case_id, run_id, token}`. The workflow calls `GET /api/engine/config` with the
    token, masks the values (`::add-mask::`) and gets: Anthropic key, model, Supabase URL + service key. Changing a key in Settings
    takes effect on the next run. Only the GitHub token (to dispatch) is used by the Worker itself.
D5. **Engine = GitHub Actions (prompt option a)**, Claude Code headless with the repo's CLAUDE.md, one proposal per run.
D6. **Data = Supabase** Postgres (tables per prompt §4, RLS on all), Storage private buckets `proposals`, `outputs`, `gr-library`,
    signed URLs 10 min issued by the Worker, Realtime on `cases` and `runs`.
D7. **Front end** = React + Vite + TypeScript + Tailwind, Recharts, pdf.js, docx-preview — exact versions pinned in package.json;
    built to `dashboard-app/dist`, served by the same Worker (static assets) → one workers.dev URL.

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
4. Front end: upload → live status → three downloads + previews + Settings — TODO
5. Charts / Kanban / rest of prompt §6 — TODO
