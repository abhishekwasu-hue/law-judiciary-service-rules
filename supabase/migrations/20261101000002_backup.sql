-- प्रस्ताव कक्ष (app B) — daily backup (prompt §9). Pure SQL, no external keys.
-- Once a day all rows of the app tables are copied as JSON into `backups`; the last 30 are kept.
-- Restore/read: select taken_at, data->'cases' from backups order by taken_at desc limit 1;

create table if not exists backups (
  id bigint generated always as identity primary key,
  taken_at timestamptz not null default now(),
  data jsonb not null
);
create index if not exists backups_taken_at on backups (taken_at desc);

-- RLS on, no policies: only the service role / SQL editor can read backups (browser never).
alter table backups enable row level security;

create or replace function take_backup() returns bigint
language plpgsql security definer set search_path = public as $$
declare new_id bigint;
begin
  insert into backups (data)
  select jsonb_build_object(
    'cases',      coalesce((select jsonb_agg(to_jsonb(t)) from cases t), '[]'::jsonb),
    'case_files', coalesce((select jsonb_agg(to_jsonb(t)) from case_files t), '[]'::jsonb),
    'runs',       coalesce((select jsonb_agg(to_jsonb(t)) from runs t), '[]'::jsonb),
    'letters',    coalesce((select jsonb_agg(to_jsonb(t)) from letters t), '[]'::jsonb),
    'activity',   coalesce((select jsonb_agg(to_jsonb(t)) from activity t), '[]'::jsonb),
    'members',    coalesce((select jsonb_agg(to_jsonb(t)) from members t), '[]'::jsonb),
    'gr_library', coalesce((select jsonb_agg(to_jsonb(t)) from gr_library t), '[]'::jsonb)
  )
  returning id into new_id;

  -- keep only the newest 30
  delete from backups
  where id not in (select b.id from backups b order by b.taken_at desc, b.id desc limit 30);

  return new_id;
end $$;

-- Not callable from the browser (Supabase grants execute to anon/authenticated by default).
revoke execute on function take_backup() from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    execute 'revoke execute on function take_backup() from anon';
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    execute 'revoke execute on function take_backup() from authenticated';
  end if;
end $$;

-- Schedule: every day 20:30 UTC = 02:00 IST. Skipped (with a notice) where pg_cron is not available.
do $$
begin
  if exists (select 1 from pg_available_extensions where name = 'pg_cron') then
    create extension if not exists pg_cron;
    perform cron.schedule('prastav-daily-backup', '30 20 * * *', 'select public.take_backup()');
  else
    raise notice 'pg_cron not available: daily backup not scheduled (run select take_backup(); manually)';
  end if;
end $$;
