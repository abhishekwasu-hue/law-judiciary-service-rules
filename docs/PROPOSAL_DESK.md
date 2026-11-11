# PROPOSAL_DESK.md — "प्रस्ताव कक्ष" claude.ai page (App A)

**Version 4 (08.11.2026; Abhi: "app B mdhe jasa ui hota to as it is घ्या"): the page IS App B's UI.** Source = dashboard-app/
built with `npm run build:artifact` (vite.artifact.config.ts + scripts/artifact-postbuild.mjs) -> dashboard-app/dist-artifact/
index.html, published with files icon.svg, icon-192.png, manifest.webmanifest, nasti/index.html. Data layer:
dashboard-app/src/lib/artifact (contract README there: collections = the Supabase tables). Worker: docs/DESK_WORKER.md
(App B model) via the scheduled task. Live data migrated: case 1 = WP35697_2026 (state cases/desk-1/). The sections below
(v2/v3 simple page, desk/proposal-desk.html) are the previous version, kept for reference.

- Capabilities (v4, 08.11.2026 fix round; declared at publish, omit on a republish to keep):
  `{"assets":{},"db":{"rules":[{"path":"","read":"view","write":"admin"},{"path":"meta","write":"owner"},{"path":"meta/worker","write":"admin"}]},"downloads":true,"user":{"scopes":["profile"]},"mcp":{"servers":[{"server":"Claude Code Remote","tools":["fire_trigger"]}]}}`
  — everyone with access reads; writes need Editor ("admin") access, so a Contributor / Viewer is read-only; `meta/*`
  (config, gr_library, register_index) only the owner; `meta/worker` (the worker lock) any Editor. Ids: page even, worker
  odd (contract README "Numeric ids"); no `meta/seq_*` writes any more.
- Per-account task ids: `meta/config.triggers[<viewer id>] = "trig_…"` (owner-written; docs/NEW_ACCOUNT_SETUP.md Option 1).

> **Superseded for page version 4 (App B UI).** Everything below (v2 / v3 page, its `cases` / `outputs` / `edits` data model,
> capabilities `"db": {}`) describes the old simple page and is kept for reference only. The working procedure for v4 is
> docs/DESK_WORKER.md; the data contract is dashboard-app/src/lib/artifact/README.md.

- Page: https://claude.ai/artifact/Hqf9Y7iKkDzNntsVCxXcB4 (private to Abhi). Source: `desk/proposal-desk.html`.
  Republish from this file with the Artifact tool (`url` = page link; read it first in a new session). Version 2 (07.11.2026)
  replaced the old v1 page another session had published there (its db was empty).
- Capabilities (v3, superseded — see v4 above): `{"assets": {}, "db": {}, "downloads": true, "user": {"scopes": ["profile"]}, "mcp": {"servers": [{"server": "Claude Code Remote", "tools": ["fire_trigger"]}]}}` (omit on republish to keep).
- "▶ काम सुरू करा" (v3, 07.11.2026; Abhi: "मला सर्व ऑपरेट त्या पानावरूनच करायची आहे"): the page calls `fire_trigger` for the
  scheduled task "प्रस्ताव कक्ष — काम" (id in `meta/config.trigger_id`); a fresh cloud session follows docs/DESK_WORKER.md and
  writes `meta/worker` {state running|idle, step, note, at}. First press asks the viewer to allow the connector.
- GR ग्रंथालय view: list = asset JSON from `tools/desk_gr_index.py` (pointer `meta/gr_library.asset`); "पानावर मागवा" writes
  `gr_requests/<key>` (pending), the worker uploads the PDF and writes `gr_files/<key>` {store, ref, name}.
- Work happens in chat (INSTRUCTIONS §4.41, PROPOSAL_SOP Step 0b / Step 9); the page shows it and collects corrections.
  The प्रस्ताव कक्ष app (App B, dashboard-app) and its engine are unchanged.

## Page (v2, 07.11.2026 — features ported from dashboard-app)
- Register: stage chips, search / stage / category / year filters, cards on phones, table on desktop, charts, intake form.
- Workspace (one open case): stage track; tabs टिप्पणी व पत्र (Note_and_Letter PDF, pdf.js 4.8.69 as in PdfViewer; Word view
  via docx-preview 0.3.3 when no PDF) · GR सह प्रस्ताव (bookmarks, go to page, lazy page render) · अभ्यास (Word view) ·
  सुधारणा (as EditChat: draft, optional paragraph, message, up to 5 files) · माहिती व कार्यवाही (stage change, reply upload,
  downloads, history).

## Data
- `cases/<caseId>` (page intake id `CR<no>-<year>`; chat cases use the `cases/<id>` folder name):
  - identity: `cr, year, file_no, subject, category, priority (सामान्य|तातडीचे)`, `path` ("chat" for chat cases), `case_id`
  - stage: प्राप्त → अभ्यास चालू → मसुदा तयार → वरिष्ठांकडे सादर → पत्र पाठवले (उत्तर प्रतीक्षेत) → माहिती प्राप्त → वित्त/सा.प्र.वि. कडे → अभिप्राय प्राप्त → निर्गमित → बंद
  - `status` queued|processing|done|failed, `reply_due` (YYYY-MM-DD)
  - files: `inputs [{asset_id, name, size, kind proposal|extra|reply}]`,
    `outputs [{kind note_letter|study|note_letter_pdf|package_pdf, name, store db|asset|asset_parts, ref}]`
  - `paras [{id, label, text}]` — correction targets from `tools/desk_sync.py` (id = position in spec.json)
  - results: `summary, letter_needed, essential_points[], grs [{code, date, title, pages}], missing_grs[]`
  - housekeeping: `instruction, history [{at, stage, note}], created_at, updated_at`
- `outputs/<caseId>__<kind>__<n>` = `{case, kind, n, total, name, b64}` (Word files; b64 ≤ 190000 chars).
- Assets: PDFs ≤ 19 MiB as one asset (`ref` = id); bigger PDFs as base64 text parts (`store` asset_parts, `ref` = [ids]),
  joined byte-exact by the page.
- `edits/<caseId>__<t>` = `{case, target note|letter|order|parawise|affidavit|lq|package|study, para, para_label, message,
  attachments [{asset_id, name, size}], status pending|done|failed, reply, at, done_at}`.

## Test record
- 01.11.2026 (v1 shape): TEST-1 through Step 0b, Word chunks byte-identical.
- 07.11.2026 (v2): local Playwright run with a mocked `window.claude` on WP35697_2026 — desktop 1300 px and phone 390 px,
  no script errors, no horizontal scroll; Note_and_Letter PDF (12 pages) and package PDF (349 pages, 8 bookmarks) render;
  a correction is stored as `edits` pending. Live page: WP35697_2026 written (case + 1 Word chunk + 4 assets; uploaded
  sha256 = local sha256).
- 07.11.2026 (v3): mocked run of GR view + start button (desktop / phone, no errors); live worker test: GR request
  59da26ab2297826f fired via the task -> run finished in ~2 min, `gr_files` + request done + `meta/worker` note written.
- Not verified by Claude: the live page's buttons in a browser (the in-app browser is not signed in to claude.ai).
