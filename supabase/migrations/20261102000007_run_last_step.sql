-- 02.11.2026 (A3 audit): a failed run's `step` holds the failure reason, so the app could not show WHERE the run stopped
-- (the red marker fell back to "रांगेत"). `last_step` keeps the last progress text written while the run was
-- queued/running; the app puts the red marker on that step. Written by a trigger, so the engine and the Worker need no
-- change. Optional: without it the app shows no step marker for old failed runs. Idempotent.
alter table runs add column if not exists last_step text;

create or replace function runs_keep_last_step() returns trigger language plpgsql as $$
begin
  if new.state in ('queued', 'running') and new.step is not null and new.step is distinct from old.step then
    new.last_step := new.step;
  elsif new.state = 'failed' and old.state in ('queued', 'running') and new.last_step is null and old.step is not null then
    new.last_step := old.step;
  end if;
  return new;
end $$;

drop trigger if exists runs_last_step on runs;
create trigger runs_last_step before update on runs for each row execute function runs_keep_last_step();
