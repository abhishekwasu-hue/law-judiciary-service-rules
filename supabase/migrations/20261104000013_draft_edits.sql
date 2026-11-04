-- 04.11.2026 (draft edit — सुधारणा-चॅट; docs/DRAFT_EDIT_DESIGN.md points 1–3 + Addendum A. Abhi: "जेवढा संदेश दिला
--   तेवढेच काम होईल … सुधारित प्रत लगेच उपलब्ध होईल"; attachments / package edits: Addendum A):
--   file_kind 'spec' = the run's /tmp/work/spec.json (every draft is built from it) and enclosures.json (the package's
--     tools/pkg3.py list), kept by tools/engine_supabase.py finish as outputs/<case>/spec/v<n>/{spec.json,enclosures.json};
--     not shown in the app's file lists.
--   runs.kind = 'full' (the engine, process_proposal) or 'edit' (tools/edit_drafts.py, edit_drafts); an edit run is
--     dispatched at once (never waits in the C33 queue, and does not block it); one run per case (full or edit) stays.
--   runs.edit_target = note | letter | order | parawise | affidavit | lq | package; edit_message = the user's message
--   (1..2000 chars); edit_attachments = case_files ids sent with the message ([] / null = none); edit_result = what the
--   edit job did ({summary, changes [{where, before, after}], files [kinds], attached [{title, pages}], cost_usd} or
--   {refused}).
-- Until applied: finish only warns (spec not kept) and POST /api/edit answers 409 migration_missing. Idempotent.
alter type file_kind add value if not exists 'spec';
alter table runs add column if not exists kind text not null default 'full';
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'runs_kind_check' and conrelid = 'public.runs'::regclass) then
    alter table runs add constraint runs_kind_check check (kind in ('full', 'edit'));
  end if;
end $$;
alter table runs add column if not exists edit_target text;
alter table runs add column if not exists edit_message text;
alter table runs add column if not exists edit_attachments jsonb;
alter table runs add column if not exists edit_result jsonb;
