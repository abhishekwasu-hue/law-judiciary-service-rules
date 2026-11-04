-- 04.11.2026 (नस्ती link): the owner's offline नस्ती page (/nasti/) asks name / designation / office again on every
--   device; the main app now stores them once per member, and a case can carry the eOffice नस्ती number so the case
--   and the नस्ती page entry can be linked.
--   members.display_name / designation / office = the member's own profile (PATCH /api/me, own row only, via the
--   Worker's service role; each at most 120 characters, validated in the Worker).
--   members.mine = the नस्ती page's "आपल्याकडे असलेले स्थान" list (e.g. "कार्यासन-६, माझ्याकडे").
--   cases.nasti_no = the eOffice file / receipt no. as shown on the नस्ती page (free text, at most 100 characters,
--   validated in the Worker; NULL = not linked).
-- Optional until applied: GET /api/me returns an empty profile, PATCH /api/me answers 409 migration_missing, and the
-- case is saved without `nasti_no`. The daily backup (migration 0002, to_jsonb of whole rows) covers the new columns
-- without change. Idempotent.
alter table members add column if not exists display_name text,
                    add column if not exists designation text,
                    add column if not exists office text,
                    add column if not exists mine text;
alter table cases add column if not exists nasti_no text;
