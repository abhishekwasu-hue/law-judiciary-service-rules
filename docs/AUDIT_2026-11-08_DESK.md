# AUDIT 08.11.2026 — प्रस्ताव कक्ष page v4/v5 (App B UI on the artifact) — Abhi: "Audit kra"

Three independent read-only audits (parallel agents): A = data layer (dashboard-app/src/lib/artifact), W = worker procedure
(docs/DESK_WORKER.md, tools/desk_publish.py), E = end-to-end use of the built page in a harness (93 screenshots,
scratchpad e2e/). Checks run: selftest 10/10, tsc OK, build + build:artifact OK, pytest desk/case tests 10 passed.
Live: scheduled task permission_mode auto; the 07.11 GR test wrote db docs and uploaded an asset unattended (W-H2 partly
verified; asset delete not tested).

## High
| ID | Finding | Fix |
|---|---|---|
| A-H1 = E-F1/F2 | A failed fire (consent not yet given, timeout) leaves the run `queued`, `dispatched_at` null; UI treats it active forever: no start button, edits refused (409) until 3.5 h | page: failed fire -> run marked so the UI shows "पुन्हा सुरू करा"; edit runs re-fire too |
| A-H2 | fire_trigger only works for the task's own account; other viewers stuck | per-account `meta/config.triggers` (done 08.11, a860317) + owner-only message for others |
| W-H1 | Lock race at worker end: a run queued in the gap is never processed | re-check queue after writing idle |
| W-H2 | Unattended approvals: writes OK (verified), asset delete not verified | make asset deletes best-effort / drop them |
| E-F3 | GR ग्रंथालय: "उघडा" disabled for 963/964 GRs (no file yet) — request path unreachable | enable as "पानावर मागवा" -> gr_requests + fire |
| E-F4 | Settings page misleading (saves nothing, $1000 vs $20 text, key names, invites) | hide / replace Settings in artifact mode with a short info card |

## Medium
A-M1 every viewer treated as owner (role from user.me ignored) · A-M2 no db rules: any contributor can write meta/runs ·
A-M3 id allocation can overwrite under concurrency (page + worker) · A-M4 whole-collection reads, activity growth vs 25,000-doc
cap · A-M5 db error codes not mapped (generic text) · A-M6 ambiguous mcp errors treated as not fired ·
W-M1 id conflict needs re-upload (ids in part names) · W-M2 full-run package name not passed (§4.16 risk) · W-M3 verify without
--original-name/--desk/--case-meta · W-M4 no reviewer pass / Study part 7 coverage table · W-M5 edits blocked by old lint
errors · W-M6 git push failure handling · W-M7 edit fallback enclosure paths · W-M8 src/ name collisions · W-M9 GR request
stuck "processing" · W-M10 SOP Step 0b/9 still describe the old page model ·
E-F5 fire failure wording (approval_required) · E-F6 WhatsApp link wrong in artifact (origin, no #/) · E-F7 CSV export bypasses
downloads · E-F8 go-to-page lands one page early on long PDFs · E-F9 db-missing messages contradictory · E-F10 register search
snippets show file header.

## Low
A-L1..L8 (listener leak on fast unmount, terminal snapshot error, upload not transactional, downloads rate_limited silent,
object URLs not revoked, pdf worker from CDN without SRI, empty search 503, docx detached render) · W-L1..L8 (kinds not
validated, untouched drafts re-versioned, based_on_run empty, part-size text, edit warnings lost, engine parity details, GRs
not committed (intended), lock edge cases) · E-F11..F18 (bulk failure count, logout no-op, half-made case on bad extra file,
GR request text with no mcp, GR page claims used_in_cases, edit_result shape undocumented, reminder toast wording, phone: AI
button overlaps two fields, नस्ती header cut).

## Works (E)
All pages/tabs, Word + 349-page PDF viewers, bookmarks, all downloads byte-exact, single + bulk new proposal (rows + fire),
live run progress, edit chat end-to-end incl. version 2 + diff, stage/letters/reply/eOffice no., Ctrl K, dark mode, AI
assistant, GR add by code, register search, नस्ती iframe; phone: no sideways scroll on any page.

## Fix round 08.11.2026 — status (commits 4294651 worker, 3c8311c data layer, b3cb233 UI; every finding re-verified in code first)
Checks: data-layer selftest 19/19 (local); worker tests (desk_publish, case_state, lint_compare) 16 passed (local); CI
"Tests" (full pytest + `tsc --noEmit`) green on 4294651 and 3c8311c. Not run here (no npm packages, installs blocked):
`npm run build`, `npm run build:artifact`, local `tsc`, pytest with pymupdf/docx. E2E: approximate esbuild harness (React 19,
router/recharts/docx shims, tailwind 4) with a fake `window.claude`, 1366x900 + 390x844: BEFORE 7 PASS / 12 FAIL, AFTER
17 PASS / 2 "FAIL" (the Settings check matches the words "खर्च-मर्यादा" / "सदस्य" inside the new info card — screenshot shows
no setting fields).

| ID | Status | Where |
|---|---|---|
| A-H1 = E-F1/F2 | fixed | runs `dispatch_error` / `dispatch_unsure` / `dispatch_tries`; `POST /api/run/<id>/fire` (full + edit); `run_waiting` 409; UI `runNeedsFire` + "▶ पुन्हा सुरू करा" (RunProgress, EditChat, CaseTabs, NewProposal, QueueCard, Layout) |
| A-H2 | fixed (a860317) + `no_trigger` message; the owner's trigger is never fired for another account | lib/artifact/api.ts fireWorker |
| W-H1 | fixed | DESK_WORKER §6 re-query after idle |
| W-H2 | fixed — no unattended deletes, `run_failed.orphan_assets` | DESK_WORKER §3.4 / §5 / §7 |
| E-F3 | fixed | GrLibrary "पानावर मागवा", `POST /api/gr/request`, `GET /api/gr/requests` |
| E-F4 | fixed (+ E-F12 logout hidden) | Settings info card; Layout, Home, NewProposal, BulkUpload |
| A-M1 | fixed — owner / staff (can data.write) / senior (read-only) | db.ts viewer, api.ts getMe / ownerRow / patchMe; UI hides write entries |
| A-M2 | fixed — db rules in the capabilities JSON (docs/PROPOSAL_DESK.md); page writes nothing under `meta/` | publish pending (owner account) |
| A-M3 | fixed — page even ids (lease `locks/seq_<table>`), worker odd ids; no `meta/seq_*` writes | db.ts allocId, README, DESK_WORKER §1, desk_publish `rows --first-id` |
| A-M4 | fixed (reads + realtime window); pruning pending | db.ts |
| A-M5 | fixed | runtime.ts db errors → Marathi `db_<code>` |
| A-M6 | fixed | api.ts classifyMcp |
| W-M1..W-M9 | fixed | DESK_WORKER, desk_publish.py, case_state.py, tools/lint_compare.py |
| W-M10 | fixed (SOP Step 0b / Step 9 page part, PROPOSAL_DESK v2/v3 marked superseded) | |
| E-F5 | fixed | fireFailText + humanError |
| E-F6 | fixed — page link (VITE_PAGE_URL) + case no. | CaseTabs |
| E-F7 | fixed | Cases CSV via artifactSaveFile |
| E-F8 | fixed, artifact build only (normal build unchanged) | PdfViewer pin while pages render |
| E-F9 | fixed (data layer texts) / partly (UI: Home card) | runtime.ts NO_DB_TEXT, Home |
| E-F10 | fixed | searchDocs bodyStart |
| Low fixed | A-L4, A-L5, A-L7, W-L1, W-L5, E-F12, E-F17 | |
| Low pending | A-L1, L2, L3, L6, L8; W-L2–L4, L6–L8; E-F11, E-F13–E-F16, E-F18 | HANDOVER Pending 29 |
| Not confirmed | none | |
