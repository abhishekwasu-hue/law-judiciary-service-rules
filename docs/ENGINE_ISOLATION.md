# ENGINE_ISOLATION.md — इंजिनचे विलगीकरण (audit 05.11.2026 S-F1, S-F2; Part 7 rows F1, F2)

## मालकांसाठी थोडक्यात (मराठी)

**सेटिंग:** Cloudflare KV `SETTINGS` मधील key `engine_isolation`. मूल्य `on` = चालू; रिकामे / `off` = बंद
(डिफॉल्ट — आजची पद्धत जशीच्या तशी). Settings API (`PUT /api/settings`, `{"engine_isolation": "on"}`) हे मूल्य
स्वीकारते; ॲपच्या Settings पानावर अजून वेगळे बटण नाही — Cloudflare dashboard → Workers → KV → SETTINGS मध्ये key
`engine_isolation` = `on` टाकता येते.

**`on` केल्यावर काय बदलते:**
- Anthropic ची खरी key इंजिनपर्यंत (Claude चालवणारा `engine` user) पोहोचत नाही. runner वर स्थानिक LiteLLM gateway
  (127.0.0.1:4001) key स्वतःकडे ठेवून विनंत्या Anthropic कडे पुढे पाठवतो; इंजिनला फक्त त्या gateway ची तात्पुरती key.
- इंजिनला इंटरनेट बंद. फक्त: स्थानिक gateway, Worker (प्रगती-संदेश), gr.maharashtra.gov.in व archive.org (GR
  उतरवण्यासाठी). इतर कोणतीही साइट (sci.gov.in, bombayhighcourt.nic.in, finance.maharashtra.gov.in सुद्धा) बंद.
- जुन्या प्रकरणांच्या मूळ zip फाइल्स (`सन … प्रकरणे.zip`, `precedent-library/*.zip`) व `.git` इंजिनला दिसत नाहीत;
  इंजिनला फक्त उघडलेला मजकूर (/tmp/old) व ग्रंथालय (/tmp/precedent) — पूर्वीप्रमाणेच.
- GitHub run (इंजिन व सुधारणा-चॅट दोन्ही) ला Supabase ची service key मिळत नाही. फाइल्स आणणे / जतन करणे / प्रगती
  Worker मार्फत, त्या एका प्रकरणापुरत्या मर्यादित एका-वेळच्या टोकनने (दुसऱ्या प्रकरणाचे काहीही वाचता / बदलता येत नाही).
- काहीही सुरू झाले नाही (gateway / proxy / iptables) तर run थांबतो — कारण: "इंजिनचे सुरक्षित नेटवर्क-वातावरण … तयार
  झाले नाही"; key उघडी ठेवून चालवले जात नाही.

**एकदा तपासणी (test run):**
1. KV `engine_isolation` = `on`.
2. एक लहान, आधी यशस्वी झालेले प्रकरण "पुन्हा तयार करा".
3. GitHub log मध्ये "Process the proposal" step: `engine isolation: on`, `sandbox: raw zips hidden …`,
   `egress test: ok direct internet blocked`, `ok proxy refused example.com`, `isolation: on (key gateway :4001 …)`.
4. निकाल पूर्वीसारखा: तिन्ही फाइल, खर्चाची ओळ, प्रगती-संदेश बदलत राहतात. एक सुधारणा-चॅट पाठवून तीही चालते हे पाहा.
5. ठीक असल्यास `on` ठेवा.

**परत पूर्वीसारखे (rollback):** KV `engine_isolation` = `off` (किंवा key काढा). पुढचा run लगेच जुन्या पद्धतीने —
deploy किंवा कोड-बदल लागत नाही.

---

## Technical detail (English)

### Flag and default
- KV `engine_isolation` (Worker `PLAIN_KEYS`; Settings PUT accepts `on` / `off` / empty). `isolationOn(cfg)` = value `on`
  (case-insensitive). Anything else = off.
- Off: `/api/engine/config` answers exactly as before (no new fields, no KV `run_db:*`), the workflows write the same
  secrets file (tests/test_engine_isolation.py runs both config steps with a fake curl and compares with the step of the
  commit before the change), every new block of the Claude step is inside `if [ "${ENGINE_ISOLATION:-}" = on ]`, and
  `engine_supabase.py` uses the service key whenever it is present.

### S-F2 — no service key on the runner (process-proposal.yml and edit-drafts.yml)
- `/api/engine/config` with isolation on: no `supabase_service_key`; `engine_isolation: "on"` and `db_token` = a NEW random
  token, KV `run_db:<token>` = `{run_id, case_id, exp}` (exp = the run token's expiry). The run token itself is unchanged
  (single use for config, then step / fail / next only) — the `engine` user still gets only the run token; the DB token
  goes only into the runner's 700 secrets file (`ENGINE_DB_TOKEN=`).
- `tools/engine_supabase.py`: `proxy_mode()` = no service key + `ENGINE_DB_TOKEN` + `WORKER` → `BASE =
  <WORKER>/api/engine/sb`, Authorization `Bearer <db token>`, no `apikey`. URL paths after BASE are unchanged
  (`/rest/v1/…`, `/storage/v1/object/…`), so fetch, case_meta, step, warn, note, log_url, finish, claude_result, verify,
  facts, consistency, fail and `tools/edit_drafts.py` all work unchanged. `edit_drafts.step()` writes directly in this
  mode too.
- Worker `/api/engine/sb/*` (`engineSb`, `engineRestCheck`, `engineStorageCheck`, all in cloudflare/worker.js):
  - token: KV `run_db:` only (a run token is refused), not expired;
  - REST tables: `runs` (GET by `id=eq.<run>` or `case_id=eq.<case>`; PATCH by `id=eq.<run>`, fields
    `RUN_PATCH_FIELDS`, state only running / done / failed), `cases` (GET / PATCH `id=eq.<case>`, PATCH fields stage,
    cr_no, cr_year, file_no, subject, category; plus fill_case's duplicate check: `select=id`, `id=neq.<case>`, cr_no +
    cr_year), `case_files` (GET `case_id=eq.<case>`; POST rows of this case, output kinds only, `storage_path`
    `outputs/<case>/<kind>/v<n>/[r<run>/]<ascii name>`), `activity` (POST, this case, actor null);
  - query: only select (no embedding — no parentheses), order, limit and the listed filter columns; no `or` / `and` /
    `not`;
  - Storage: POST / DELETE only `outputs/<case>/…` (types pdf, docx, json, octet-stream; 50 MB as the bucket);
    GET own outputs or an object that a `case_files` row of this case names (the case's uploads in proposals /
    gr-library);
  - forwarded with the service key; Supabase's status and body are passed back.
  - **A new runs / cases field written by the engine tools must be added to `RUN_PATCH_FIELDS` /
    `CASE_PATCH_FIELDS`**, or the proxy answers 403 (the run then fails / misses that field).

### S-F1 (a) — the Anthropic key stays with the runner
- In the Claude step (isolation on, Claude as the engine provider): a second LiteLLM proxy from the existing hash-locked
  venv (`tools/requirements-litellm.txt`), runner user, `127.0.0.1:4001`, config `{"general_settings": {"master_key":
  "os.environ/LITELLM_MASTER_KEY"}}`, its own random master key (masked), `ANTHROPIC_API_KEY` only in its own env.
- `engine` gets `ANTHROPIC_BASE_URL=http://127.0.0.1:4001/anthropic` + `ANTHROPIC_AUTH_TOKEN=<master key>`. LiteLLM's
  Anthropic **pass-through** route forwards `/anthropic/v1/messages` (and count_tokens etc.) to api.anthropic.com
  unchanged: any model name (Opus / Sonnet / Haiku from config, subagent models), prompt caching, beta headers, query
  `?beta=true`, streaming. It adds `x-api-key` itself and does not forward the master key. Cost: Claude Code's own
  `total_cost_usd` as before (no gateway cost file).
- Checked locally (05.11.2026, litellm 1.105.1 from the lock file, mock upstream via `ANTHROPIC_API_BASE`): request with
  the master key → upstream got `x-api-key=<real key>`, no Authorization, beta + version headers and model name kept,
  SSE stream passed through; no key → 500, wrong key → 400; `/model/new` with the master key → "No DB Connected" (no
  model / key management without a DB); an unknown-model chat with `api_base` in the body made no outbound request.
- An engine-provider gateway (`ENGINE_PROVIDER`, :4000) already keeps that provider's key outside `engine`; then no
  :4001 gateway is started. The fallback gateway (:4000) works as before.

### S-F1 (b) — outbound limit
- `tools/egress_proxy.py` (stdlib, runner user, root-owned snapshot, `127.0.0.1:3128`): CONNECT tunnels / absolute-URI
  HTTP to the Worker host, `gr.maharashtra.gov.in`, `archive.org` (+ sub-domains: download mirrors), ports 80 / 443,
  public addresses only; everything else 403, logged as "DENY host:port" (`$RP/egress.log`, names only).
- `scripts/engine/egress.sh up 4000,4001,3128`: iptables `OUTPUT -m owner --uid-owner engine -j ENGINE_OUT`; ENGINE_OUT
  accepts only TCP to 127.0.0.1 on those ports, rejects the rest; IPv6 all rejected. ACL deny for `engine` on the
  systemd-resolved varlink / D-Bus system sockets (no DNS over local sockets). `egress.sh test` (as `engine`): direct
  internet must fail, example.com via the proxy must be refused (both fatal), DNS still resolving = owner note only.
- `engine` env adds `HTTPS_PROXY` / `HTTP_PROXY` (both cases), `NO_PROXY=127.0.0.1,localhost`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` (no telemetry / update checks that would be blocked anyway).
- Checked locally (root container): rules installed, direct internet + other loopback ports refused for `engine`,
  example.com refused by the proxy, gr.maharashtra.gov.in through the proxy answered, root unaffected, `down` removes all.
- `iso_stop` (after `sandbox.sh down`) stops the gateway and proxy and removes the rules.

### S-F1 (c) — raw old-case zips
- `SANDBOX_HIDE_RAW=1 sandbox.sh up …` (isolation on): read-only empty placeholders bind-mounted over `<mount>/*.zip`,
  `<mount>/precedent-library/*.zip` and `<mount>/.git` (the shallow pack holds the same zips); self-test fails the setup
  when one is still readable. `down` unmounts them with `umount -R`. The workspace itself is untouched (checked locally).
- The extracted corpora `/tmp/old` (oldcases_text.py) and `/tmp/precedent` stay readable: every proposal run uses them
  (SOP Step 2.5, ENGINE_PROMPT PRECEDENT / OLDCASES). Making even those per-run optional needs a rule for "which run
  needs them" — not decided.

### What still needs a live runner test (cannot be checked outside GitHub Actions)
1. Claude Code `2.1.300` through `ANTHROPIC_BASE_URL=…/anthropic` (pass-through) with HTTPS_PROXY set: subagents,
   caching, streaming, real cost line.
2. iptables owner match + setfacl on ubuntu-latest (nft backend), the DNS line of `egress.sh test`.
3. `engine` tools through the proxy: `gr_request.py` (urllib) to gr.maharashtra.gov.in / archive.org redirects,
   `engine_supabase.py step` to the Worker (Cloudflare accepts the UA through the tunnel).
4. The Worker proxy end to end on real Supabase: fetch, finish (uploads up to 50 MB through the Worker — Worker request
   body limit 100 MB on the free plan), spec upload, edit run.
5. Time cost of the second gateway start (venv install ~1–2 min when the fallback gateway is not used).

### Residual risks (on)
- `engine` holds the gateway master key: it can send any request to Anthropic through the gateway (cost; data goes only
  to Anthropic). Without a DB the LiteLLM admin routes cannot add models or keys.
- `engine` still holds the run token: progress text / fail of THIS run only, as before.
- The Worker host is allowed: `engine` can reach every public Worker route (all need a user JWT, run token or DB token).
- gr.maharashtra.gov.in / archive.org are allowed hosts: an upload channel to archive.org (account needed) is not
  blocked by host name.

### Files
cloudflare/worker.js (setting, config, `/api/engine/sb`), tools/engine_supabase.py (`proxy_mode`, init, http),
tools/edit_drafts.py (step), tools/egress_proxy.py, scripts/engine/egress.sh, scripts/engine/sandbox.sh (hide_raw),
.github/workflows/process-proposal.yml (config step, Claude step), .github/workflows/edit-drafts.yml (config step).
Tests: cloudflare/test/worker.test.mjs (last test), tests/engine_supabase_test.py (proxy section),
tests/test_engine_isolation.py.
