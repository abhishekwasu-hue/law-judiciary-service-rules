# RULES_DIGEST — what loads automatically and what to open when needed (Abhi, 12.11.2026: "Ho गरजेनुसार kra")

The binding rules are unchanged: INSTRUCTIONS.md (full text, wins on any conflict), PROPOSAL_SOP.md, PROPOSAL_WORKFLOW.md,
OWNER_RULES.md. To save tokens on every message, only OWNER_RULES.md, this file and the compact rule form
tools/ENGINE_BRIEF.md (every INSTRUCTIONS / SOP rule, tagged [I4.n] / [SOPn]) load automatically. Open the full files
when the task needs them:

| Task | Open first (full text) |
|---|---|
| A new proposal (note, letter, orders, Study, package) | the skill's procedure (lj-seva / lj-nyayalayin / lj-vidhimandal / lj-kharedi) + PROPOSAL_SOP.md (whole, once) + the INSTRUCTIONS.md §4 items the brief tags for the drafts being made |
| A correction round on a saved case | INSTRUCTIONS §4.41 + only the §4 items the correction touches |
| Abhi corrects the style / gives a new rule | the whole INSTRUCTIONS.md §4 (to number the new item and avoid conflicts), then SOP, brief, samples (§8.4 of SOP) |
| App B / engine / प्रस्ताव कक्ष page / worker / pending work | HANDOVER.md, docs/DESK_WORKER.md, docs/PROPOSAL_DESK.md, docs/NEW_ACCOUNT_SETUP.md |
| Any doubt whether a brief line covers a case | the INSTRUCTIONS.md item its tag names |

tools/ENGINE_BRIEF.md section 0 ("never stop / never ask") applies to automatic engine runs only; in a chat session
INSTRUCTIONS §3.2 and §6 apply (ask only policy / preference questions; decide from GR / record what can be decided).

## Prepared material — use it before opening big files or page images (12.11.2026)
1. **Ready cards** docs/cards/00-INDEX.md -> the card for the demand type: governing GR paras verbatim with page / para,
   ready enclosure + highlight entries (verified with pkg3 / highlight.py), essential-information checklist, letter
   points, note skeleton, precedents, judgments, gaps. Re-check any quote marked "(OCR)" against the page image.
2. **Text cache** text/ (page-wise text of 597 service PDFs, 13,340 pages): `python3 tools/gr_text.py grep <regex>` /
   `show <pdf|code> <page>` before any OCR or page-image read of a repo PDF; look at the image only for the page you
   quote. New GRs: `OMP_THREAD_LIMIT=1 nice -n 15 python3 tools/build_text_cache.py`.
3. **Detailed GR studies** docs/gr_study/00-INDEX.md (9 topics) — open only the section of the GR in hand.
4. **Inventories**: pdf/gr/INDEX.tsv, docs/GR_INVENTORY.tsv (971 PDFs by subject / department), judgments
   pdf/judgments-service/ + docs/judgments/.

