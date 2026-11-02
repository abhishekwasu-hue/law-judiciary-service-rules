-- 02.11.2026: two optional engine outputs (docs/COURT_AND_ORDERS_RESEARCH.md B7–B9):
--   order_draft = <PREFIX>_Order_Draft.docx (शासन आदेश-मसुदा: GR / शुद्धिपत्रक / परिपत्रक / ज्ञापन / अधिसूचना)
--   parawise    = <PREFIX>_Parawise.docx    (परिच्छेदनिहाय अभिप्राय, English — Rules 1984 r.58(3)/(4))
-- Apply before the first run that produces these files. Until then tools/engine_supabase.py finish only warns
-- (the three main outputs are still stored). Idempotent.
alter type file_kind add value if not exists 'order_draft';
alter type file_kind add value if not exists 'parawise';
