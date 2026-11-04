-- 04.11.2026 (C28 / INSTRUCTIONS §4.28, more tickable drafts): two more optional engine outputs:
--   affidavit = <PREFIX>_Affidavit.docx  (शपथपत्र — affidavit in reply, English; tools/build_affidavit.py,
--               docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md part A)
--   lq_answer = <PREFIX>_LQ_Answer.docx  (विधानमंडळ प्रश्नाचे उत्तर; tools/build_lq.py, docs/FORMS_RESEARCH_AFFIDAVIT_LQ.md)
-- The other new draft keys (do_letter, uo_note -> inside <PREFIX>_Note_and_Letter.docx; endorsement, office_order,
-- press_note, addendum -> inside <PREFIX>_Order_Draft.docx, kind order_draft) need no new kind; runs.outputs (text[],
-- migration 0008) has no value constraint, so the new keys are stored as they are.
-- Apply before the first run that produces these files. Until then tools/engine_supabase.py finish only warns
-- (the three main outputs are still stored). Idempotent.
alter type file_kind add value if not exists 'affidavit';
alter type file_kind add value if not exists 'lq_answer';
