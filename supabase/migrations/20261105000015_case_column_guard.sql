-- 05.11.2026 (independent audit docs/AUDIT_2026-11-05.md, Part 7, S-F7): browser writes limited to what the app does.
--
-- Before: RLS policy cases_upd let every owner/staff member PATCH any column of `cases` straight through PostgREST
-- (e.g. cr_no, subject, desk, assigned_to), skipping the Worker's checks; and policy activity_ins let a member insert
-- any activity row (any action / detail) under their own id, so the case history could be forged.
--
-- What the app really writes from the browser (grep dashboard-app/src, 05.11.2026): only
--   sb().from('cases').update({ stage }) — lib/data.tsx setStage and pages/CaseDetail.tsx (stage menu).
-- Every other case change (create, edit fields, desk, work type, नस्ती no.) goes through the Worker (service role).
-- The browser never inserts into `activity`; rows come from the Worker (service role) and from the stage trigger below.
--
-- After:
--   1. Trigger cases_guard (BEFORE UPDATE, runs before cases_touch by name): for a browser request of a non-owner member
--      (database role authenticated / anon, my_role() <> 'owner') any change to a column other than `stage` (and
--      `updated_at`, which cases_touch sets anyway) is refused with SQLSTATE 42501. The Worker (service_role), the SQL
--      editor (postgres) and the owner are not limited. The stage CHECK constraint stays as before.
--   2. touch_case() becomes SECURITY DEFINER, so its 'stage_changed' activity row (actor = auth.uid(), unchanged) is
--      written without an insert policy for members.
--   3. Policy activity_ins dropped: members can no longer insert activity rows; reading (activity_read) unchanged.
-- Current app flows keep working: stage change from the case list / case page (allowed column; activity row by the
-- trigger), everything else through the Worker.
-- Safe to run in the Supabase SQL editor any number of times (create or replace / drop … if exists). Undo: re-create
-- policy activity_ins from migration 0001 and drop trigger cases_guard.

create or replace function cases_guard_columns() returns trigger language plpgsql set search_path = public as $$
declare
  changed text[];
begin
  -- Worker / engine (service_role), SQL editor (postgres) and other server roles: not limited
  if current_user not in ('authenticated', 'anon') then
    return new;
  end if;
  if my_role() = 'owner' then
    return new;
  end if;
  select coalesce(array_agg(n.key order by n.key), '{}') into changed
  from jsonb_each(to_jsonb(new)) n
  join jsonb_each(to_jsonb(old)) o using (key)
  where n.value is distinct from o.value
    and n.key not in ('stage', 'updated_at');
  if array_length(changed, 1) > 0 then
    raise exception 'cases: only the stage can be changed here (columns: %)', array_to_string(changed, ', ')
      using errcode = '42501';
  end if;
  return new;
end $$;

drop trigger if exists cases_guard on cases;
create trigger cases_guard before update on cases for each row execute function cases_guard_columns();

-- same body as migration 0001; now security definer (the activity row no longer needs a member insert policy)
create or replace function touch_case() returns trigger language plpgsql security definer set search_path = public as $$
begin
  new.updated_at := now();
  if tg_op = 'UPDATE' and new.stage is distinct from old.stage then
    insert into activity (case_id, actor, action, detail)
    values (new.id, auth.uid(), 'stage_changed', jsonb_build_object('from', old.stage, 'to', new.stage));
  end if;
  return new;
end $$;

drop policy if exists activity_ins on activity;
