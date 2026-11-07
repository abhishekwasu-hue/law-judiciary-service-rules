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
| `runs`       | `String(id)`       | all `runs` columns: `state, step, last_step, step_at, started_at, finished_at, dispatched_at, instructions, outputs, kind ('full' / 'edit'), edit_target, edit_message, edit_attachments, edit_result, summary, letter_needed, essential_points, grs_attached, grs_missing, warnings, cost_usd, num_turns, duration_s, log_url, created_by, created_at`. |
| `letters`    | `String(id)`       | `case_id, ref_no, addressed_to, sent_date, reply_due, reply_received_date, status, created_at`. |
| `activity`   | `String(id)`       | `case_id, actor, action, detail, at` — one doc per row (25,000-doc artifact cap: prune old rows when it grows). |
| `members`    | `user_id`          | the viewer (claude.ai user id, or `owner` when the `user` capability is absent) as `role: 'owner'` + profile (`display_name, designation, office, mine`). |
| `gr_requests`| GR index `key` (or the 16–20 digit code) | written by the page: `{key, code, path, file, status: 'pending', at, by}`. Worker: set `status` `processing` → `done` / `failed`, and on success write `gr_files/<key>`. |
| `gr_files`   | GR index `key`     | `{store: 'asset', ref: <asset id> \| [<part ids>], name}` — the GR PDF on the page (`ref` array = base64 parts, see below). |

Values are plain JSON: timestamps ISO-8601 UTC strings (`new Date().toISOString()`), dates `YYYY-MM-DD`, numbers as JSON
numbers, jsonb columns as JSON, `null` for empty. The page reads whole collections and filters/sorts client-side.

`gr_library` is NOT a collection the page needs: `from('gr_library')` is served from the GR index asset
(`meta/gr_library {asset}` → `[{key, path, folder, topic, file, code, date "DD.MM.YYYY" | "", title, pages, size, url}]`,
built by `tools/desk_gr_index.py`), mapped to `{code: code || key, date: ISO | null, department: topic, title: title ||
file, source_url: url || null, storage_path: "asset:<ref>" when gr_files/<key> exists, used_in_cases: []}` (docs in a
`gr_library` collection, if any, override by code).

## meta docs

| doc                    | written by | content |
|------------------------|------------|---------|
| `meta/config`          | lead / owner | `{trigger_id: "trig_…"}` — the scheduled task the page fires (`mcp.callTool("Claude Code Remote", "fire_trigger", {trigger_id})`). |
| `meta/seq_<table>`     | page + worker | `{next: <int>, table, updated_at}` — id counter per numeric table. |
| `meta/gr_library`      | lead | `{asset: <id>}` — GR index JSON. |
| `meta/register_index`  | lead | `{asset: <id>}` — `[{path, title, text}]` of `register/*.md` for नियम-उतारे शोध. |

## Numeric ids

`allocId(table)`: take a short lease on `meta/seq_<table>` (`acquire`, 5 s, same holder per tab), read `next`, use
`n = max(next, highest id seen in the collection + 1)`, skip forward while `<table>/<n>` already exists, write
`next = n + 1`. **Worker:** when you create a row (output `case_files`, `activity`), read `meta/seq_<table>.next`, check
that `<table>/<next>` does not exist (else +1 until free), write the row, then write `next + 1`. One user, one worker
at a time: the existence check makes a collision impossible to overwrite a row.

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

The page creates `runs` docs with `state: 'queued'`, `dispatched_at: null`, then fires the trigger; on a successful
fire it sets `dispatched_at` (a failed fire leaves it queued with `dispatched_at: null` — the page shows "प्रतीक्षेत";
a later retry of "प्रक्रिया सुरू करा" fires again for that same run). Full run: also case `stage` `अभ्यास चालू` and an
activity `run_started`. Edit run (`kind: 'edit'`, `edit_target`, `edit_message`, `edit_attachments` [case_files ids]).

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
`runs.cost_usd`, limit $1000, `max_parallel` 1; login (always the owner); Supabase storage buckets.

## Test

`node src/lib/artifact/selftest.mjs` (from `dashboard-app/`) — bundles the layer with esbuild against an in-memory fake
of `window.claude` and checks every call shape above.
