-- 05.11.2026 (independent audit docs/AUDIT_2026-11-05.md, Part 7, S-F7 — the rest after migration 0015):
-- browser writes to `letters` limited to what the app does; members see only members of their own office.
--
-- Before:
--   * policy letters_write (FOR ALL, can_write()) let every owner/staff member insert, update or DELETE any letters row,
--     any column (also case_id / created_at), straight through PostgREST, skipping the Worker's checks.
--   * policy members_read (is_member()) let every member read every member row (e-mail, role, profile of all offices).
--
-- What the app really does (grep dashboard-app/src and cloudflare/worker.js, 05.11.2026):
--   * letters: the browser only READS (lib/data.tsx, pages/CaseDetail.tsx). Every write goes through the Worker with the
--     service role: POST /api/letters (case_id, ref_no, addressed_to, sent_date, reply_due, status), PATCH
--     /api/letters/:id (ref_no, addressed_to, sent_date, reply_due, reply_received_date, status) and the reply upload
--     (reply_received_date, status). Nothing deletes a letters row.
--   * members: the browser reads members in pages/CaseDetail.tsx (names of the people in the case history) and in
--     pages/Settings.tsx (member list; owner only). The own profile (/api/me) and the नस्ती page profile go through the
--     Worker (service role). Invites (POST /api/members) go through the Worker.
--
-- After:
--   1. letters_write dropped. New policies for owner/staff (can_write()): letters_ins (insert) and letters_upd (update),
--      both only for a case the member can see (EXISTS on `cases`, i.e. under the cases RLS); letters_del: owner only.
--      Seniors stay read-only (as before).
--   2. Trigger letters_guard (BEFORE INSERT OR UPDATE): for a browser request of a non-owner member (database role
--      authenticated / anon, my_role() <> 'owner')
--        - INSERT: reply_received_date must be empty (the app never sets it on create); created_at is set to now();
--        - UPDATE: only ref_no, addressed_to, sent_date, reply_due, reply_received_date, status may change (id, case_id,
--          created_at and any later column are refused);
--      refused with SQLSTATE 42501. The Worker / engine (service_role), the SQL editor (postgres) and the owner are not
--      limited. The status CHECK constraint stays as before.
--   3. members_read: a member sees their own row, the owner row(s), and members of the same office (members.office of
--      migration 0012, compared trimmed and case-insensitive; an empty office matches nobody). The owner still sees all
--      rows (also through policy members_owner). my_office() is SECURITY DEFINER (no RLS recursion on members).
-- Current app flows keep working: letter form, reply record and reminder are Worker calls (service role); the case
-- history shows the names of same-office members and the owner (another office's member: name left empty, as for an
-- unknown actor); Settings member list is owner-only.
-- Needs migration 0012 for members.office (added here too if missing, so the file also runs on its own).
-- Safe to run in the Supabase SQL editor any number of times (create or replace / drop … if exists).
-- Undo: drop policies letters_ins, letters_upd, letters_del and trigger letters_guard; re-create from migration 0001
--   create policy letters_write on letters for all using (can_write()) with check (can_write());
--   and replace members_read with: create policy members_read on members for select using (is_member());

alter table members add column if not exists office text;

-- ---------- letters ----------
create or replace function letters_guard_columns() returns trigger language plpgsql set search_path = public as $$
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
  if tg_op = 'INSERT' then
    if new.reply_received_date is not null then
      raise exception 'letters: reply_received_date cannot be set on a new letter here' using errcode = '42501';
    end if;
    new.created_at := now();
    return new;
  end if;
  select coalesce(array_agg(n.key order by n.key), '{}') into changed
  from jsonb_each(to_jsonb(new)) n
  join jsonb_each(to_jsonb(old)) o using (key)
  where n.value is distinct from o.value
    and n.key not in ('ref_no', 'addressed_to', 'sent_date', 'reply_due', 'reply_received_date', 'status');
  if array_length(changed, 1) > 0 then
    raise exception 'letters: these columns cannot be changed here (columns: %)', array_to_string(changed, ', ')
      using errcode = '42501';
  end if;
  return new;
end $$;

drop trigger if exists letters_guard on letters;
create trigger letters_guard before insert or update on letters for each row execute function letters_guard_columns();

drop policy if exists letters_write on letters;
drop policy if exists letters_ins on letters;
drop policy if exists letters_upd on letters;
drop policy if exists letters_del on letters;
create policy letters_ins on letters for insert
  with check (can_write() and exists (select 1 from cases c where c.id = letters.case_id));
create policy letters_upd on letters for update
  using (can_write() and exists (select 1 from cases c where c.id = letters.case_id))
  with check (can_write() and exists (select 1 from cases c where c.id = letters.case_id));
create policy letters_del on letters for delete using (my_role() = 'owner');

-- ---------- members ----------
create or replace function my_office() returns text language sql stable security definer set search_path = public as $$
  select nullif(lower(btrim(office)), '') from members where user_id = auth.uid()
$$;

drop policy if exists members_read on members;
create policy members_read on members for select using (
  is_member() and (
    user_id = auth.uid()
    or role = 'owner'
    or my_role() = 'owner'
    or (my_office() is not null and nullif(lower(btrim(office)), '') = my_office())
  )
);
