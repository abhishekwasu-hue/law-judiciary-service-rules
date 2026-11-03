-- 03.11.2026 (C30, Abhi: "ho tayar karto" — he also prepares proposals of OTHER departments / desks):
--   cases.desk = the desk profile of the case (tools/desks/<id>.json): 'law-desk6' (विधि व न्याय विभाग, कार्यासन-6) or
--   'hte-mashi5' (उच्च व तंत्र शिक्षण विभाग, मशि-5). NULL = law-desk6 (every case before this migration). The Worker
--   validates the id (DESK_IDS); the engine writes it into case.json "desk".
-- Optional until applied: the Worker saves the case without `desk` (the case then uses law-desk6). Idempotent.
alter table cases add column if not exists desk text;
