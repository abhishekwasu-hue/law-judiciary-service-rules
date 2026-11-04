# सुधारणा-चॅट (draft edit) — design / contract (04.11.2026)

Owner request (Abhi, 04.11.2026): "प्रस्तावावर कार्यवाही पूर्ण केल्यानंतर … विशिष्ट पत्रामध्ये … नोटमध्ये … पॅराग्राफ मध्ये जर
बदल करायचा असेल किंवा एखाद दोन लाईन कट करायचे असेल … चॅट बॉक्स असणं गरजेचं आहे आणि जेवढा संदेश दिला तेवढेच काम होईल
म्हणजे आपले टोकन्स खर्च होणार नाही आणि सुधारित प्रत लगेच उपलब्ध होईल". Plan accepted: model **Sonnet**; **several changes in
one message = one edit run**, any number of edits one after another. Study edits: not in phase 1 (default, no answer given).

## Facts (code, 04.11.2026)
- Only way to change a draft today: "पुन्हा तयार करा" + instruction = the full engine (measured 21–44 min, $2.80–3.87).
- Every draft (note, letter(s), orders, parawise, affidavit, LQ answer) is built from ONE `/tmp/work/spec.json`; it was not
  kept after the run.

## Design
1. **Keep the spec.** `tools/engine_supabase.py finish` also uploads `/tmp/work/spec.json` as file kind `spec`
   (bucket path `<case>/spec/v<n>/spec.json`, a `case_files` row, original_name `spec.json`). Not shown in the app's file lists.
2. **Migration 0013** `supabase/migrations/20261104000013_draft_edits.sql` (idempotent):
   `alter type file_kind add value if not exists 'spec';`
   `runs`: `kind text not null default 'full'` (check in ('full','edit')), `edit_target text`, `edit_message text`,
   `edit_result jsonb`.
3. **Worker** `POST /api/edit {case_id, target, message}` (writer roles only):
   - target ∈ `note | letter | order | parawise | affidavit | lq` ("नोंद", "पत्र", "आदेश-प्रारूप", "परिच्छेदनिहाय उत्तर",
     "शपथपत्र", "विधानमंडळ उत्तर"); message 1..2000 chars (trimmed).
   - 409 `no_spec` (reason "या प्रकरणाची सुधारणा-फाइल नाही (जुने प्रकरण) — 'पुन्हा तयार करा' वापरा") when the case has no `spec` file;
     409 `run_active` when a run (full or edit) of the case is queued/running; monthly limit → same refusal as /api/run.
   - creates a `runs` row `kind='edit'`, `edit_target`, `edit_message`, `dispatched_at = now()` (never waits in the full-run
     queue; the queue's "active run" check ignores `kind='edit'`), dispatches `repository_dispatch` **`edit_drafts`** with the
     same payload/token scheme as `process_proposal`; `/api/engine/config` answers it the same way plus `model_edit`
     (KV setting, default `claude-sonnet-5-5`). Activity log `edit_requested`.
   - Missing columns (0013 not applied) → 409 `migration_missing` "Supabase मध्ये migration 0013 लागू करा".
4. **Workflow** `.github/workflows/edit-drafts.yml` (on `repository_dispatch: [edit_drafts]`, concurrency per case,
   timeout 20 min): checkout, Python 3.12 + `pip install python-docx docxcompose pymupdf` (pip cache), LibreOffice NOT needed
   unless the builders require it for the preview (skip previews), masked config fetch (same pattern as process-proposal.yml),
   `python3 tools/edit_drafts.py`. Failure → `/api/engine/fail` with a Marathi reason. No Claude Code, no sandbox: one Messages
   API call that returns JSON; nothing the model writes is executed.
5. **`tools/edit_drafts.py`:**
   - download the latest `spec` file, the package PDF (for the पृ. range check) and the case meta;
   - one Anthropic Messages API call (model `model_edit`, temperature 0) with: a short fixed system prompt (change ONLY what
     the message asks, in the chosen target; never touch quotes “…” unless the message names that text; keep §4.18–§4.34 forms;
     unknown → "____"; reply strictly as JSON), the spec part of the target (+ the minimal context it needs), the message;
   - reply = `{"ops": [{"op": "replace"|"remove"|"insert", "path": "<JSON pointer>", "value"?}], "summary": "<Marathi, one line>",
     "refuse"?: "<Marathi reason>"}`; `refuse` when the message needs a full run (new GR, re-reading the proposal, a new draft
     type) → run done with `edit_result.refused`, no file change;
   - apply the ops to a copy of the spec (paths only inside the target's keys), `lint_spec.py`; lint errors → ONE retry with the
     errors; still failing → run failed "सुधारणा नियमांत बसली नाही — <first error>", nothing uploaded;
   - rebuild only the affected file(s) with the existing builders (`build_note_letter.py` for note/letter, `build_order.py`,
     `build_parawise.py`, `build_affidavit.py`, `build_lq.py`), `clean_meta`, the verify checks that apply to those files;
   - upload new versions of the changed output kinds + the new spec version; `runs` row: state done, `summary` = the model's
     summary, `edit_result` = `{summary, changes: [{where, before, after}], files: [kinds], cost_usd}`; `cost_usd` from the
     reply's usage.
6. **App** (case page): panel "✏️ सुधारणा" — target select (only targets whose output exists), textarea, send; the case's
   edit runs as a chat (message, state, summary, before (red) / after (green) per change, links to the new file versions);
   "नवीन आवृत्ती" downloads; old versions stay listed. No spec → the panel says to use "पुन्हा तयार करा". Edit runs are not
   shown as full runs (progress card / queue / "पुन्हा तयार करा").

## Not in phase 1
Study edits; edits that need the proposal, GRs or a new draft type (full run); cases processed before this change (no spec).

## Addendum A (04.11.2026, Abhi: "साधारणता सुधारणा या स्टडी फाईल मध्ये करायची गरज पडत नाही, जीआर सह पीडीएफ यामध्ये एखादा आणखी कागदपत्र किंवा जीआर युजरला अटॅच करायचा असल्यास … चॅट बॉक्समध्ये डॉक्युमेंट अपलोड करायची सुद्धा सुविधा पाहिजे … चॅट बॉक्स हा … Claude session … धर्तीवर")
- Study edits: not needed (decided).
- **Attachments in the chat (📎, drag-drop, several files):** each file is uploaded first with the existing upload API
  (`kind` `gr` for a GR / rule PDF, else `extra_doc`; PDF / JPG / PNG; Word only if the edit job can convert it, else a
  Marathi refusal "PDF करून जोडा"), then `POST /api/edit {case_id, target, message, attachments: [case_files.id, …]}`
  (≤ 5, each must belong to the case; the files' rows are created by the upload as today).
- **New target `package`** ("GR सह प्रस्ताव PDF"). The message may also name GRs by सांकेतांक (16–18 digits, found by regex
  in the message, not by the model) → downloaded from the official URL
  `https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf` (else archive.org mirror).
- **Persist `enclosures.json`** with the spec (same kind `spec`, original_name `enclosures.json`), so the package can be
  rebuilt with `tools/pkg3.py` (proposal from storage + saved enclosures + the new ones appended at the END → existing
  पृ.N/प.वि. stay valid; only the total in "पृ. i / N" changes; bookmarks for the new items; no highlights on the new items
  unless the message gives exact lines). New package version keeps the original file name (§4.16).
- **Order in the edit job:** attachments + GR codes → rebuild package → the new page ranges are known → ONE model call that
  gets the target part of the spec, the message, the new page ranges ("<title>: पृ.a-b/प.वि.") and the text layer of the
  attached files (capped, for quoting) → spec ops (e.g. a new para / related extract citing the new pages) → lint → rebuild →
  upload. Message that only attaches (no text change asked) → no model call at all (cost 0).
- `edit_result` gets `attached: [{title, pages}]`.
