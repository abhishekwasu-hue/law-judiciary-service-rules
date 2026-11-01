-- प्रस्ताव कक्ष (app B) — schema, RLS, storage. Design: docs/APP_B_DESIGN.md (D3, D6).
-- Browser = authenticated members (RLS). Worker/engine = service role (bypasses RLS).

-- Marathi labels exceed Postgres' 63-byte enum-label limit → text + CHECK.
create type file_kind as enum ('proposal','extra_doc','study','note_letter','package_pdf','gr','reply');
create type run_state as enum ('queued','running','done','failed');
create type member_role as enum ('owner','staff','senior');

create table members (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  role member_role not null default 'staff',
  created_at timestamptz not null default now()
);

create table cases (
  id bigint generated always as identity primary key,
  cr_no text not null,
  cr_year int not null,
  file_no text,
  subject text not null,
  category text not null default 'इतर' check (category in ('वेतननिश्चिती','भत्ते','निवृत्तीवेतन','जुनी पेन्शन','विशेष वेतन','विमा/GPF','सेवा','न्यायिक वेतन','वैद्यकीय','इतर')),
  employee_name text, post text, office text, received_from text,
  received_via text check (received_via in ('High Court','direct')),
  inward_date date,
  stage text not null default 'प्राप्त' check (stage in ('प्राप्त','अभ्यास चालू','मसुदा तयार','वरिष्ठांकडे सादर','पत्र पाठवले (माहिती प्रतीक्षेत)','माहिती प्राप्त','वित्त/सा.प्र.वि. कडे','अभिप्राय प्राप्त','आदेश/पत्र निर्गमित','बंद')),
  priority text not null default 'सामान्य' check (priority in ('सामान्य','तातडीचे')),
  due_date date,
  assigned_to uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cr_no, cr_year)
);

create table case_files (
  id bigint generated always as identity primary key,
  case_id bigint not null references cases(id) on delete cascade,
  kind file_kind not null,
  storage_path text not null,          -- bucket/path, e.g. proposals/12/1/<original name>.pdf
  original_name text not null,         -- INSTRUCTIONS §4.16: never renamed
  version int not null default 1,
  uploaded_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);
create index on case_files (case_id, kind);

create table runs (
  id bigint generated always as identity primary key,
  case_id bigint not null references cases(id) on delete cascade,
  state run_state not null default 'queued',
  step text,                            -- live progress: reading pages / searching GRs / drafting / building PDF / verifying
  started_at timestamptz, finished_at timestamptz,
  instructions text,
  log_url text,
  summary text,
  letter_needed boolean,
  essential_points jsonb not null default '[]',
  grs_attached jsonb not null default '[]',
  grs_missing jsonb not null default '[]',
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);
create index on runs (case_id, created_at desc);

create table letters (
  id bigint generated always as identity primary key,
  case_id bigint not null references cases(id) on delete cascade,
  ref_no text, addressed_to text,
  sent_date date, reply_due date, reply_received_date date,
  status text not null default 'पाठवले' check (status in ('मसुदा','पाठवले','उत्तर प्राप्त','स्मरणपत्र')),
  created_at timestamptz not null default now()
);

create table gr_library (
  code text primary key,               -- सांकेतांक
  date date,
  department text,
  title text,
  storage_path text,
  source_url text,
  used_in_cases bigint[] not null default '{}'
);

create table activity (
  id bigint generated always as identity primary key,
  case_id bigint references cases(id) on delete cascade,
  actor uuid references auth.users(id),
  action text not null,                 -- e.g. stage_changed, file_uploaded, run_started
  detail jsonb not null default '{}',
  at timestamptz not null default now()
);
create index on activity (case_id, at desc);

-- updated_at + stage-change audit
create function touch_case() returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  if tg_op = 'UPDATE' and new.stage is distinct from old.stage then
    insert into activity (case_id, actor, action, detail)
    values (new.id, auth.uid(), 'stage_changed', jsonb_build_object('from', old.stage, 'to', new.stage));
  end if;
  return new;
end $$;
create trigger cases_touch before update on cases for each row execute function touch_case();

-- membership helpers (security definer: avoid RLS recursion on members)
create function my_role() returns member_role language sql stable security definer set search_path = public as $$
  select role from members where user_id = auth.uid()
$$;
create function is_member() returns boolean language sql stable as $$ select my_role() is not null $$;
create function can_write() returns boolean language sql stable as $$ select my_role() in ('owner','staff') $$;

alter table members enable row level security;
alter table cases enable row level security;
alter table case_files enable row level security;
alter table runs enable row level security;
alter table letters enable row level security;
alter table gr_library enable row level security;
alter table activity enable row level security;

create policy members_read on members for select using (is_member());
create policy members_owner on members for all using (my_role() = 'owner') with check (my_role() = 'owner');

create policy cases_read on cases for select using (is_member());
create policy cases_ins on cases for insert with check (can_write());
create policy cases_upd on cases for update using (can_write()) with check (can_write());

create policy files_read on case_files for select using (is_member());
create policy files_ins on case_files for insert with check (can_write());

create policy runs_read on runs for select using (is_member());
create policy runs_ins on runs for insert with check (can_write());

create policy letters_read on letters for select using (is_member());
create policy letters_write on letters for all using (can_write()) with check (can_write());

create policy gr_read on gr_library for select using (is_member());

create policy activity_read on activity for select using (is_member());
create policy activity_ins on activity for insert with check (can_write() and actor = auth.uid());

-- Storage: private buckets; browsers get signed URLs from the Worker only (no storage policies for authenticated users).
insert into storage.buckets (id, name, public, file_size_limit)
values ('proposals','proposals',false,52428800), ('outputs','outputs',false,52428800), ('gr-library','gr-library',false,52428800)
on conflict (id) do nothing;

-- Realtime for live status
alter publication supabase_realtime add table cases, runs;
