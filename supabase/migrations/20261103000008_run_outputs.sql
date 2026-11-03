-- 03.11.2026 (C28, Abhi: "letter, shasan nirnay ase option sudhha asayla pahije … user multiple option choose karel"):
--   runs.outputs = the drafts the user ticked for this run ("कोणते मसुदे हवेत?"), in fixed order, keys:
--   letter, reminder, gr, corrigendum, circular, memo, notification, parawise. NULL = legacy run (the engine decides
--   as before); an empty array = note only. Study, note and the package PDF are always made.
--   file_kind 'approval' (वित्त/सा.प्र.वि. मान्यता) and 'court_notice' (न्यायालयीन नोटीस): new upload types; the engine
--   fetches them like reply / extra documents.
-- Optional until applied: the Worker retries the run insert without `outputs` (the run then has the legacy behaviour),
-- and an upload of the two new kinds fails until the enum values exist. Idempotent.
alter table runs add column if not exists outputs text[];

alter type file_kind add value if not exists 'approval';
alter type file_kind add value if not exists 'court_notice';
