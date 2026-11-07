# PROPOSAL_DESK.md — "प्रस्ताव कक्ष" claude.ai page (App A)

- Page: https://claude.ai/artifact/8cJP8wz6j5tYM5kRHK1rVx (private to Abhi). Source: `desk/proposal-desk.html`.
  Republish from this file with the Artifact tool (`url` = page link; read it first in a new session). Version 2 (07.11.2026)
  replaced the old v1 page another session had published there (its db was empty).
- Capabilities: `{"assets": {}, "db": {}, "downloads": true, "user": {"scopes": ["profile"]}}` (carried forward; omit on republish).
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
- Not verified by Claude: the live page's buttons in a browser (the in-app browser is not signed in to claude.ai).
