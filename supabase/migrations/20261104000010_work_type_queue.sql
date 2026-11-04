-- 04.11.2026 (C33, Abhi: "किमान पाच प्रस्ताव एका वेळेला अपलोड … काम मात्र सिक्वेन्सनेस … वन बाय वन";
--   "मेन डॅशबोर्ड वर अशी कॅटेगरी कामाची"):
--   cases.work_type = the work category of the case: 'service' (सेवाविषयक प्रकरणे), 'court' (न्यायालयीन प्रकरणे),
--   'legislature' (विधिमंडळ कामकाज), 'procurement' (खरेदी विषयक बाबी). NULL = service (every case before this migration).
--   The Worker validates the id (WORK_TYPES); the engine writes it into case.json "work_type".
--   runs.dispatched_at = when the Worker handed the run to GitHub Actions. Runs wait in a queue (state 'queued',
--   dispatched_at NULL) while another run of ANY case is active; the Worker dispatches them one by one, oldest first
--   (claim = conditional PATCH … &dispatched_at=is.null).
-- Optional until applied: the Worker saves the case without `work_type` (service) and dispatches every run immediately,
-- as before. Idempotent.
alter table cases add column if not exists work_type text;
-- every run that exists when the column is first added was dispatched at once (the old behaviour): it is marked
-- dispatched, never treated as waiting in the queue. Only on the first apply (a re-run must not touch real queue rows).
do $$
begin
  if not exists (select 1 from information_schema.columns
                 where table_schema = 'public' and table_name = 'runs' and column_name = 'dispatched_at') then
    alter table runs add column dispatched_at timestamptz;
    update runs set dispatched_at = created_at;
  end if;
end $$;

create index if not exists runs_queue_idx on runs (created_at, id) where state = 'queued' and dispatched_at is null;
