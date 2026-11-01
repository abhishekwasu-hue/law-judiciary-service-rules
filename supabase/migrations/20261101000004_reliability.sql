-- Reliability / cost (docs/QUALITY_AUDIT.md Pack 2, 01.11.2026).
-- 1. Per-run cost record from Claude Code's JSON result (engine_supabase.py claude_result) + non-fatal warnings
--    (e.g. new GRs could not be pushed to the repo).
-- 2. Members may no longer insert runs / case_files directly: the Worker (service role, bypasses RLS) does both,
--    after its own checks. A direct browser insert could leave a run "queued" forever.

alter table runs add column if not exists cost_usd numeric(10, 4);
alter table runs add column if not exists num_turns int;
alter table runs add column if not exists duration_s numeric(10, 1);
alter table runs add column if not exists warnings jsonb not null default '[]';

drop policy if exists runs_ins on runs;
drop policy if exists files_ins on case_files;
