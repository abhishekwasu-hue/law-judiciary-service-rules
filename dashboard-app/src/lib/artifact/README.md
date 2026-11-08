# Artifact data layer — storage contract

The artifact build (`npm run build:artifact`, `import.meta.env.VITE_BACKEND === 'artifact'`) runs the unchanged app UI
inside one claude.ai artifact page. `sb()` returns `db.ts` (a supabase-js-compatible client over the artifact `db`
capability) and `api()` / `uploadFile` / `fileBytes` / `fileUrl` / `downloadFile` go to `api.ts` (in-page versions of
`cloudflare/worker.js`). The normal build is unchanged (the artifact modules are tree-shaken out of it).

Capabilities the page must declare: `db`, `assets`, `downloads`, `mcp` (server `Claude Code Remote`, tool
`fire_trigger`), `user`.

This file is the contract the cloud worker (the session the trigger starts) reads and writes against.

## Collections (one per SQL table, same name; fields = the SQL columns incl. later migrations)

| collection   | doc id             | notes |
|--------------|--------------------|-------|
| `cases`      | `String(id)`       | columns of `cases` (+ `desk`, `work_type`, `nasti_no`). Defaults: category `इतर`, stage `प्राप्त`, priority `सामान्य`. |
| `case_files` | `String(id)`       | `case_id, kind, storage_path, original_name, version, uploaded_by, created_at` + file fields below. `kind` = the `file_kind` enum values (`proposal, extra_doc, reply, approval, court_notice, gr` uploads; outputs `study, note_letter, package_pdf, order_draft, parawise, affidavit, lq_answer, spec`). |
| `runs`       | `String(id)`       | all `runs` columns: `state, step, last_step, step_at, started_at, finished_at, dispatched_at, instructions, outputs, kind ('full' / 'edit'), edit_target, edit_message, edit_attachments, edit_result, summary, letter_needed, essential_points, grs_attached, grs_missing, warnings, cost_usd, num_turns, duration_s, log_url, created_by, created_at`; page-only (the worker ignores them): `dispatch_error, dispatch_unsure, dispatch_tries` (see Run lifecycle). |
| `letters`    | `String(id)`       | `case_id, ref_no, addressed_to, sent_date, reply_due, reply_received_date, status, created_at`. |
| `activity`   | `String(id)`       | `case_id, actor, action, detail, at` — one doc per row. Limited reads go to the store newest-first (`orderBy(<col>, dir).limit(n)`, + `where` for simple filters such as `case_id == <number>`); the realtime channel watches `orderBy('at','desc').limit(200)`. Pruning old rows (25,000-doc cap) is still pending. |
| `members`    | `user_id`          | the viewer (claude.ai user id, or `owner` when the `user` capability is absent) + profile (`display_name, designation, office, mine`). `role` = `owner` (user.isOwner(), or no `user` capability), `staff` (can('data.write') true / null), `senior` (read-only). Written only by a viewer who may write; never `owner` for a non-owner (an old such row is corrected). |
| `gr_requests`| GR index `key` (or the 16–20 digit code) | written by the page (`POST /api/gr/request`, opening an unstored GR, `POST /api/gr`): `{key, code, path, file, status: 'pending', at, by}` — new, `failed`, or `processing` older than 30 min re-opened as `pending`. Worker: set `status` `processing` (+ `processing_at`) → `done` / `failed` (+ `reply`), and on success write `gr_files/<key>`. |
| `locks`      | `seq_<table>`      | lease docs of the page's id allocation (`acquire`, 5 s); no data. |
| `gr_files`   | GR index `key`     | `{store: 'asset', ref: <asset id> \| [<part ids>], name}` — the GR PDF on the page (`ref` array = base64 parts, see below). |

Values are plain JSON: timestamps ISO-8601 UTC strings (`new Date().toISOString()`), dates `YYYY-MM-DD`, numbers as JSON
numbers, jsonb columns as JSON, `null` for empty. The page reads whole collections and filters/sorts client-side, except
limited `activity` reads (above). db rejections reach the UI as Marathi text with code `db_<code>` (runtime.ts).

`gr_library` is NOT a collection the page needs: `from('gr_library')` is served from the GR index asset
(`meta/gr_library {asset}` → `[{key, path, folder, topic, file, code, date "DD.MM.YYYY" | "", title, pages, size, url}]`,
built by `tools/desk_gr_index.py`), mapped to `{code: code || key, date: ISO | null, department: topic, title: title ||
file, source_url: url || null, storage_path: "asset:<ref>" when gr_files/<key> exists, used_in_cases: []}` (docs in a
`gr_library` collection, if any, override by code).

## meta docs

| doc                    | written by | content |
|------------------------|------------|---------|
| `meta/config`          | lead / owner | `{trigger_id: "trig_…"}` — the scheduled task the page fires (`mcp.callTool("Claude Code Remote", "fire_trigger", {trigger_id})`). |
| `meta/config` `triggers` | owner | `{<viewer id>: "trig_…"}` — a second account's own scheduled task (a task fires only from its own account; a non-owner without an entry gets `no_trigger`, the owner's `trigger_id` is never called for them). |
| `meta/seq_<table>`     | (legacy) | old id counters — read only (`next - 1` is a floor for new ids); nobody writes them any more. |
| `meta/gr_library`      | lead | `{asset: <id>}` — GR index JSON. |
| `meta/register_index`  | lead | `{asset: <id>}` — `[{path, title, text}]` of `register/*.md` for नियम-उतारे शोध. |

## Numeric ids

Page and worker take disjoint ids: the page EVEN ids only, the worker ODD ids only, so a page write and a worker write
can never take the same id; "highest id = newest" still holds (both take ids above every existing id). Nobody writes
under `meta/` for ids (`meta` is owner-only).

* **Page** `allocId(table)`: lease `locks/seq_<table>` (`acquire`, holder = tab id, 5 s; a throwing acquire is retried,
  not taken as granted; not granted after ~7 s → ApiError 503 with a Marathi "busy, try again" reason). Then `n` = the
  smallest even number above max(highest id from a fresh `orderBy('id','desc').limit(1)` read, the highest id this tab
  has seen, legacy `meta/seq_<table>.next - 1` if that doc exists); `n += 2` while `<table>/<n>` exists.
* **Worker**: `n` = the smallest odd number above the highest id (ArtifactData query order_by id desc limit 1); several
  rows → n, n+2, n+4 …; rows are created without `if_version` (the server refuses a create on an existing doc: re-read,
  renumber, redo); no `meta/seq_*` writes.

## File storage (case_files rows and gr_files)

* `storage_path: "asset:<id>"`, `asset_id: <id>` — one artifact asset, for `application/pdf`, `image/jpeg`,
  `image/png` up to 19 MiB. Read at `"/_blob/" + id`.
* `storage_path: "asset-parts:<n>"`, `asset_parts: [<id>, …]`, `asset_id: null` — anything else (Word `.doc/.docx`,
  `.tif`, `spec.json`, PDFs over 19 MiB): the raw bytes cut into 14,400,000-byte pieces, each piece base64-encoded on
  its own and uploaded as a `text/plain` asset. Bytes = concat(base64decode(part) for part in order).
* also `content_type`, `size_bytes`. `original_name` is the name the user sees and downloads (§4.16, never renamed).

Worker outputs (`study`, `note_letter`, `package_pdf`, `order_draft`, `parawise`, `affidavit`, `lq_answer`, `spec`
with `original_name: "spec.json"`) use the same fields; the edit chat needs the `spec` row of the last full run.

## Run lifecycle (what the worker must set)

The page creates `runs` docs with `state: 'queued'`, `dispatched_at: null`, then fires the trigger. Every firing
(new run, `POST /api/run/<id>/fire`, the re-fire of a waiting full run by `POST /api/run`) adds 1 to `dispatch_tries`:
* success → `dispatched_at` = now, `dispatch_error` null, `dispatch_unsure` null;
* definite failure → `dispatched_at` stays null, `dispatch_error` = code (`approval_required`, `no_trigger`,
  `mcp_unavailable`, `server_not_connected`, `not_in_manifest`, `blocked_by_policy`, `needs_reauth`, `tool_error`,
  `error` …), answer ApiError 502 `trigger_failed` {reason (Marathi, `fireFailText(code)`), detail, run_id, code};
* ambiguous (`upstream_error` without `retryable`, `cancelled`, `server_unavailable`: the task may have started) →
  `dispatched_at` = now, `dispatch_unsure` true.
A full run's first successful firing also sets case `stage` `अभ्यास चालू` and an activity `run_started` (once per run).
A new edit while a run of the case is still waiting (`queued`, `dispatched_at` null) → 409 `run_waiting` {run_id,
reason}. Edit run (`kind: 'edit'`, `edit_target`, `edit_message`, `edit_attachments` [case_files ids]).

The worker, for each `queued` run (oldest first):
1. `state: 'running'`, `started_at`, then progress in `step` (Marathi text containing a `RUN_STEPS` key, see
   `../constants.ts`) — keep `last_step` = the last `step` while queued/running and `step_at` = now when `step` changes
   (the SQL trigger did this; the page's own writes do it too).
2. outputs: `case_files` rows as above.
3. finish: `state: 'done'` (or `'failed'` only when nothing was produced, INSTRUCTIONS §4.26) with `finished_at`,
   `summary`, `letter_needed`, `essential_points`, `grs_attached`, `grs_missing`, `warnings`, `cost_usd`, `num_turns`,
   `duration_s`; edit runs `edit_result` `{summary, changes, files, refused?, attached?, notes?}`. On failure put the
   Marathi reason in `step` and keep `last_step` = the step it failed at.
4. case `stage` `मसुदा तयार` after a done full run, and an `activity` row (`run_done` / `run_failed`).
   A case stage change must also add `activity {action: 'stage_changed', detail: {from, to}}` and bump
   `cases.updated_at` (touch_case trigger).

`isStale` (3.5 h since dispatch / creation) makes the page stop treating a run as active; nothing sweeps it.

## Hidden / no-op in this build

Settings (API keys, models, budgets, GitHub, Supabase) GET `{}` / PUT `{ok:true}`; member invites refused (use the
page's share menu); setup; stuck-run sweep; monthly budget / settings gates; `/api/spend` = this month's
`runs.cost_usd`, limit $1000, `max_parallel` 1; login (the claude.ai viewer, role per `members` above); Supabase storage buckets.

## Page endpoints added for the artifact build

* `POST /api/run/<id>/fire` {} → the updated run row (re-fire of a `queued` full or edit run); 502 `trigger_failed`
  {reason, detail, run_id, code}; 409 `run_not_waiting` {reason}.
* `POST /api/gr/request` {code} | {key} → `{status: 'pending' | 'processing' | 'done', fired, reason?, code?}`.
* `GET /api/gr/requests` → `[{key, code, status, at, reply}]`, newest first.
* `/api/search?q=` with no search term → `[]` (no index needed).

## Test

`node src/lib/artifact/selftest.mjs` (from `dashboard-app/`) — bundles the layer with esbuild against an in-memory fake
of `window.claude` and checks every call shape above.
