# PROPOSAL_DESK.md — "प्रस्ताव कक्ष" claude.ai page (build prompt A)

- Page: https://claude.ai/artifact/RYzwfiGwJpbVxyD5C2rCy2 (private to Abhi). Source: `desk/proposal-desk.html`.
  Republish from this file with the Artifact tool (`url` = page link; read it first in a new session).
- Capabilities: `{"assets": {}, "db": {}, "downloads": true, "user": {"scopes": ["profile"]}}`.
- Processing procedure: PROPOSAL_SOP.md Step 0b.
- Note: another session (different claude.ai account) also published the old v1 page at https://claude.ai/artifact/8cJP8wz6j5tYM5kRHK1rVx. Abhi to choose ONE; then delete the other.

## Data
- `cases/<caseId>` (id `CR<no>-<year>`):
  - identity: `cr, year, file_no, subject, category, priority (सामान्य|तातडीचे)`
  - category: वेतननिश्चिती / भत्ते / निवृत्तीवेतन / जुनी पेन्शन / विशेष वेतन / विमा-GPF / सेवा / न्यायिक वेतन / वैद्यकीय / इतर
  - stage: प्राप्त → अभ्यास चालू → मसुदा तयार → वरिष्ठांकडे सादर → पत्र पाठवले (उत्तर प्रतीक्षेत) → माहिती प्राप्त → वित्त/सा.प्र.वि. कडे → अभिप्राय प्राप्त → निर्गमित → बंद
  - `status` queued|processing|done|failed, `reply_due` (YYYY-MM-DD, set with stage "पत्र पाठवले"; overdue = red chip)
  - files: `inputs [{asset_id, name (original), size, kind proposal|extra|reply}]`, `outputs [{kind study|note_letter|package_pdf, name, store asset|db, ref}]`
  - results: `summary, letter_needed, essential_points[], grs [{code, date, title, pages}], missing_grs[]`
  - housekeeping: `instruction, history [{at, stage, note}], created_at, updated_at`
- `outputs/<caseId>__<kind>__<n>` = `{case, kind, n, total, name, b64}` (b64 ≤ 190000 chars; built by `tools/desk_chunks.py`).
  The page reads chunk 0, then 1..total-1, and saves the Blob with `downloads.save`.
- Package PDF: an asset; the page fetches `/_blob/<ref>`.

## Test record (01.11.2026)
- Case `TEST-1` (sample 1-page PDF) run through Step 0b: input asset read back (sha256 equal); outputs built with
  build_note_letter.py (CR122 spec), build_study.py, pkg3.py; Word chunks written and read back → byte-identical, open in python-docx;
  package asset read back (2 pages, 2 bookmarks). 700 KB file → 5 chunks, byte-identical.
- Not verified by Claude: the page's own buttons in a browser (the in-app browser is not signed in to claude.ai).
