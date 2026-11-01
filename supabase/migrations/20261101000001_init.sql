-- Proposal Desk (प्रस्ताव कक्ष) — schema, RLS, storage, realtime.
-- Every table has RLS. The browser uses the anon key + user JWT; only the Worker / Actions use the service key.

create extension if not exists pg_trgm;

-- ---------- roles ----------
create table public.members (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  display_name text,
  role text not null check (role in ('owner','desk','senior')),
  notify jsonb not null default '{"email":true,"push":true}'::jsonb,
  created_at timestamptz not null default now()
);
create table public.invites (
  email text primary key,
  role text not null check (role in ('desk','senior')),
  invited_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create or replace function public.my_role() returns text
language sql stable security definer set search_path = public as
$$ select role from public.members where user_id = auth.uid() $$;
create or replace function public.is_member() returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.members where user_id = auth.uid()) $$;
create or replace function public.is_writer() returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.members where user_id = auth.uid() and role in ('owner','desk')) $$;
create or replace function public.is_owner() returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.members where user_id = auth.uid() and role = 'owner') $$;

-- An invited e-mail gets its invited role; otherwise the first user becomes owner; anyone else gets no access.
create or replace function public.on_auth_user_created() returns trigger
language plpgsql security definer set search_path = public as $$
declare inv public.invites;
begin
  select * into inv from public.invites where email = lower(new.email);
  if found then
    insert into public.members(user_id, email, role) values (new.id, lower(new.email), inv.role);
    delete from public.invites where email = inv.email;
  elsif not exists (select 1 from public.members where role = 'owner') then
    insert into public.members(user_id, email, role) values (new.id, lower(new.email), 'owner');
  end if;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.on_auth_user_created();

-- ---------- cases ----------
create table public.cases (
  id bigint generated always as identity primary key,
  prefix text unique,
  cr_no text,
  cr_year int,
  file_no text,
  subject text,
  category text not null default 'इतर' check (category in
    ('वेतननिश्चिती','भत्ते','निवृत्तीवेतन','जुनी पेन्शन','विशेष वेतन','विमा/GPF','सेवा','न्यायिक वेतन','वैद्यकीय','इतर')),
  employee_name text,
  post text,
  office text,
  received_from text,
  received_via text check (received_via in ('उच्च न्यायालय','थेट')),
  inward_date date default current_date,
  stage text not null default 'प्राप्त' check (stage in
    ('प्राप्त','अभ्यास चालू','मसुदा तयार','वरिष्ठांकडे सादर','पत्र पाठवले (माहिती प्रतीक्षेत)','माहिती प्राप्त',
     'वित्त/सा.प्र.वि. कडे','अभिप्राय प्राप्त','आदेश/पत्र निर्गमित','बंद')),
  priority text not null default 'सामान्य' check (priority in ('तातडीचे','उच्च','सामान्य')),
  due_date date,
  assigned_to uuid references auth.users(id),
  closed_at timestamptz,
  created_by uuid references auth.users(id) default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index cases_stage_idx on public.cases(stage);
create index cases_cat_idx on public.cases(category);

create table public.case_files (
  id bigint generated always as identity primary key,
  case_id bigint not null references public.cases(id) on delete cascade,
  run_id bigint,
  kind text not null check (kind in ('proposal','extra_doc','study','note_letter','package_pdf','cabinet_note','gr','reply','reminder','briefing')),
  bucket text not null default 'proposals' check (bucket in ('proposals','outputs','gr-library')),
  storage_path text not null,
  original_name text,
  version int not null default 1,
  size_bytes bigint,
  uploaded_by uuid references auth.users(id) default auth.uid(),
  created_at timestamptz not null default now()
);
create index case_files_case_idx on public.case_files(case_id, kind, version desc);

create table public.runs (
  id bigint generated always as identity primary key,
  case_id bigint not null references public.cases(id) on delete cascade,
  mode text not null default 'study' check (mode in ('study','reminder','cabinet')),
  state text not null default 'queued' check (state in ('queued','running','done','failed')),
  progress text not null default 'queued',
  instructions text,
  requested_by uuid references auth.users(id) default auth.uid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  log_url text,
  summary text,
  letter_needed boolean,
  essential_points jsonb not null default '[]'::jsonb,
  grs_attached jsonb not null default '[]'::jsonb,
  grs_missing jsonb not null default '[]'::jsonb,
  doubts jsonb not null default '[]'::jsonb,
  briefing jsonb,
  error text
);
create index runs_case_idx on public.runs(case_id, started_at desc);
alter table public.case_files add constraint case_files_run_fk foreign key (run_id) references public.runs(id) on delete set null;

create table public.letters (
  id bigint generated always as identity primary key,
  case_id bigint not null references public.cases(id) on delete cascade,
  ref_no text,
  addressed_to text,
  sent_date date,
  reply_due date,
  reply_received_date date,
  reply_file_id bigint references public.case_files(id) on delete set null,
  status text not null default 'पाठवले' check (status in ('मसुदा','पाठवले','स्मरणपत्र पाठवले','उत्तर प्राप्त','रद्द')),
  created_at timestamptz not null default now()
);
create index letters_case_idx on public.letters(case_id);

create table public.gr_library (
  code text primary key,
  date date,
  department text,
  title text,
  storage_path text,
  source_url text,
  used_in_cases bigint[] not null default '{}',
  added_at timestamptz not null default now()
);
create index gr_title_trgm on public.gr_library using gin (title gin_trgm_ops);

create table public.activity (
  id bigint generated always as identity primary key,
  case_id bigint references public.cases(id) on delete cascade,
  actor uuid default auth.uid(),
  actor_email text,
  action text not null,
  detail jsonb not null default '{}'::jsonb,
  at timestamptz not null default now()
);
create index activity_case_idx on public.activity(case_id, at desc);
create index activity_at_idx on public.activity(at desc);

create table public.settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
insert into public.settings(key, value) values
  ('signature_chain', '["कक्ष अधिकारी","अवर सचिव","उप सचिव","सह सचिव"]'::jsonb),
  ('addressees', '["प्रबंधक (प्रशासन), उच्च न्यायालय, मुंबई","प्रबंधक, उच्च न्यायालय, नागपूर खंडपीठ","प्रबंधक, उच्च न्यायालय, औरंगाबाद खंडपीठ"]'::jsonb)
on conflict do nothing;

-- Register (verified extracts) for full-text search; filled by the deploy workflow from register/*.md
create table public.register_chunks (
  id bigint generated always as identity primary key,
  source text not null,
  heading text,
  page text,
  para int,
  body text not null
);
create index register_body_trgm on public.register_chunks using gin (body gin_trgm_ops);

-- ---------- triggers ----------
create or replace function public.touch_case() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.updated_at := now();
  if tg_op = 'UPDATE' and new.stage is distinct from old.stage then
    if new.stage = 'बंद' then new.closed_at := now(); elsif old.stage = 'बंद' then new.closed_at := null; end if;
    insert into public.activity(case_id, actor, actor_email, action, detail)
    values (new.id, auth.uid(), (select email from public.members where user_id = auth.uid()),
            'stage', jsonb_build_object('from', old.stage, 'to', new.stage));
  end if;
  return new;
end $$;
create trigger cases_touch before update on public.cases for each row execute function public.touch_case();

create or replace function public.log_case_insert() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.activity(case_id, actor, actor_email, action, detail)
  values (new.id, auth.uid(), (select email from public.members where user_id = auth.uid()),
          'created', jsonb_build_object('stage', new.stage, 'subject', new.subject));
  return new;
end $$;
create trigger cases_log_insert after insert on public.cases for each row execute function public.log_case_insert();

-- Average days per stage, from the stage-change log (RLS of the caller applies)
create or replace view public.stage_durations with (security_invoker = true) as
with ev as (
  select c.id as case_id, 'प्राप्त'::text as stage, c.created_at as at from public.cases c
  union all
  select a.case_id, a.detail->>'to', a.at from public.activity a where a.action = 'stage'
), seq as (
  select case_id, stage, at, lead(at) over (partition by case_id order by at) as next_at from ev
)
select stage, round(avg(extract(epoch from (coalesce(next_at, now()) - at)) / 86400.0)::numeric, 1) as avg_days, count(*) as n
from seq where stage <> 'बंद' group by stage;

-- Register search: every word must appear; ranked by matches
create or replace function public.search_register(q text, lim int default 40)
returns table(id bigint, source text, heading text, page text, para int, body text)
language sql stable security invoker set search_path = public as $$
  select r.id, r.source, r.heading, r.page, r.para, r.body
  from public.register_chunks r
  where (select bool_and(r.body ilike '%' || w || '%') from unnest(regexp_split_to_array(trim(q), '\s+')) w where w <> '')
  order by length(r.body) asc
  limit least(greatest(lim, 1), 100)
$$;

-- ---------- RLS ----------
alter table public.members enable row level security;
alter table public.invites enable row level security;
alter table public.cases enable row level security;
alter table public.case_files enable row level security;
alter table public.runs enable row level security;
alter table public.letters enable row level security;
alter table public.gr_library enable row level security;
alter table public.activity enable row level security;
alter table public.settings enable row level security;
alter table public.register_chunks enable row level security;

create policy members_read on public.members for select using (public.is_member());
create policy members_self_update on public.members for update using (user_id = auth.uid() or public.is_owner())
  with check (public.is_owner() or (user_id = auth.uid() and role = public.my_role()));
create policy members_owner_delete on public.members for delete using (public.is_owner() and user_id <> auth.uid());
create policy invites_owner on public.invites for all using (public.is_owner()) with check (public.is_owner());

do $$ declare t text; begin
  foreach t in array array['cases','case_files','runs','letters','gr_library','activity','settings','register_chunks'] loop
    execute format('create policy %1$s_read on public.%1$s for select using (public.is_member())', t);
  end loop;
  foreach t in array array['cases','case_files','runs','letters','gr_library','activity'] loop
    execute format('create policy %1$s_insert on public.%1$s for insert with check (public.is_writer())', t);
    execute format('create policy %1$s_update on public.%1$s for update using (public.is_writer()) with check (public.is_writer())', t);
  end loop;
  foreach t in array array['cases','case_files','letters','gr_library'] loop
    execute format('create policy %1$s_delete on public.%1$s for delete using (public.is_owner())', t);
  end loop;
end $$;
create policy settings_owner_write on public.settings for all using (public.is_owner()) with check (public.is_owner());

-- ---------- storage: private buckets, no client policies (signed URLs from the Worker only) ----------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types) values
  ('proposals', 'proposals', false, 52428800, array['application/pdf','image/jpeg','image/png']),
  ('outputs', 'outputs', false, 104857600, null),
  ('gr-library', 'gr-library', false, 52428800, array['application/pdf']),
  ('backups', 'backups', false, null, null)
on conflict (id) do update set public = false;

-- ---------- realtime ----------
alter publication supabase_realtime add table public.cases, public.runs, public.activity, public.letters;
