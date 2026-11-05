-- 05.11.2026 (independent audit docs/AUDIT_2026-11-05.md, Part 4 + 8: L-F2, L-F3, L-F8/F13, L-F12, L-F16):
--   runs.step_at = when the run's progress text (`step`) last changed, or when it became 'running' (trigger below).
--     The Worker's sweep fails a 'running' run whose step has not changed for 2 h (runner lost); the 3.5 h limit stays.
--   runs_one_active_per_case = at most ONE queued/running run per case (full or edit). Two parallel /api/run (or run +
--     edit) calls could both pass the Worker's check-then-insert and start two paid runs; now the second insert gets
--     23505 and the Worker answers 409 run_active. Cases that already have several active rows: the newest one is kept
--     (a 'running' row before a 'queued' one, a dispatched row before a waiting one), the others are marked failed with
--     a Marathi reason and an activity row — before the index is built, so the index can be created.
--   case_files_version_key = unique (case_id, kind, original_name, version) — only when no duplicate rows exist (else
--     a NOTICE names the count and the index is skipped; the Worker's retry works either way).
--   Indexes: runs (state), runs (created_at), letters (case_id).
-- Safe to run in the Supabase SQL editor, any number of times (idempotent). Optional for the Worker: without it the
-- Worker keeps the 3.5 h limit alone and its own check-then-insert.

alter table runs add column if not exists last_step text;   -- migration 0007 (repeated so this file stands alone)
alter table runs add column if not exists step_at timestamptz;

create or replace function runs_keep_last_step() returns trigger language plpgsql as $$
begin
  if new.state in ('queued', 'running') and new.step is not null and new.step is distinct from old.step then
    new.last_step := new.step;
  elsif new.state = 'failed' and old.state in ('queued', 'running') and new.last_step is null and old.step is not null then
    new.last_step := old.step;
  end if;
  -- 0014: time of the last progress change (or of the start), read by the Worker's stuck-run sweep
  if new.state in ('queued', 'running')
     and (new.step is distinct from old.step or (new.state = 'running' and old.state is distinct from 'running')) then
    new.step_at := now();
  end if;
  return new;
end $$;

drop trigger if exists runs_last_step on runs;
create trigger runs_last_step before update on runs for each row execute function runs_keep_last_step();

-- duplicates of an active run per case → the extra rows failed (keep: running, then dispatched, then newest id)
do $$
declare
  has_dispatched boolean := exists (select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'runs' and column_name = 'dispatched_at');
  n int;
begin
  if has_dispatched then
    with ranked as (
      select id, case_id, row_number() over (partition by case_id
               order by (state = 'running') desc, (dispatched_at is not null) desc, id desc) as rn
      from runs where state in ('queued', 'running')),
    extra as (
      update runs r set state = 'failed', finished_at = now(),
        step = 'एकाच प्रकरणाची दुसरी प्रक्रिया आधीच चालू असल्याने ही प्रक्रिया थांबवली. कृपया आवश्यक असल्यास ''पुन्हा तयार करा'' वापरावे, ही विनंती.'
      from ranked k where r.id = k.id and k.rn > 1
      returning r.id, r.case_id)
    insert into activity (case_id, actor, action, detail)
      select case_id, null, 'run_failed', jsonb_build_object('run_id', id, 'reason', 'duplicate active run (migration 0014)') from extra;
  else
    with ranked as (
      select id, case_id, row_number() over (partition by case_id order by (state = 'running') desc, id desc) as rn
      from runs where state in ('queued', 'running')),
    extra as (
      update runs r set state = 'failed', finished_at = now(),
        step = 'एकाच प्रकरणाची दुसरी प्रक्रिया आधीच चालू असल्याने ही प्रक्रिया थांबवली. कृपया आवश्यक असल्यास ''पुन्हा तयार करा'' वापरावे, ही विनंती.'
      from ranked k where r.id = k.id and k.rn > 1
      returning r.id, r.case_id)
    insert into activity (case_id, actor, action, detail)
      select case_id, null, 'run_failed', jsonb_build_object('run_id', id, 'reason', 'duplicate active run (migration 0014)') from extra;
  end if;
  get diagnostics n = row_count;
  if n > 0 then raise notice 'migration 0014: % duplicate active run(s) marked failed', n; end if;
end $$;

create unique index if not exists runs_one_active_per_case on runs (case_id) where state in ('queued', 'running');

create index if not exists runs_state_idx on runs (state);
create index if not exists runs_created_at_idx on runs (created_at);
create index if not exists letters_case_id_idx on letters (case_id);

-- unique version per file name — only when the existing rows allow it
do $$
declare
  dup int;
begin
  if not exists (select 1 from pg_indexes where schemaname = 'public' and indexname = 'case_files_version_key') then
    select count(*) into dup from (
      select 1 from case_files group by case_id, kind, original_name, version having count(*) > 1) d;
    if dup = 0 then
      create unique index case_files_version_key on case_files (case_id, kind, original_name, version);
    else
      raise notice 'migration 0014: % duplicate (case_id, kind, original_name, version) group(s) in case_files — unique index NOT created', dup;
    end if;
  end if;
end $$;
