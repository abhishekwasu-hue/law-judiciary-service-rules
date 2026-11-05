# Work type: court (न्यायालयीन प्रकरणे) — status: ready

No new rules here. Court matters (GP/AGP/High Court/MAT notice on a writ petition, O.A., contempt, SLP) follow the existing
binding rules exactly (pointers, not copies — the rule text is in INSTRUCTIONS.md):

- INSTRUCTIONS.md §4.32 (०) (court-petition note, para 1; Abhi 05.11.2026, C3 option अ): a GP / AGP letter on record ->
  "<सहायक सरकारी वकील, …> यांच्या पृ.N/प.वि. वरील दि. __ रोजीच्या पत्रास अनुसरून सादर."; no such letter (petition received
  directly) -> just "सादर.". No incoming letter number anywhere in the note (§4.29(1), §4.36 C1).
- INSTRUCTIONS.md §4.32 (court-petition note): para 2 = the petition (petitioners, court, petition no., पृ.N/प.वि.) and
  ALL respondents in the petition's order as flowing sentences ("<R1> यांना प्रतिवादी क्र. 1, … करण्यात आले आहे"), with the
  verification date; para 3 = "सदर याचिकेद्वारे याचिकाकर्त्यांनी पुढीलप्रमाणे प्रमुख मागण्या केल्या आहेत (पृ.N/प.वि.):-" +
  table अ.क्र. | प्रार्थना | मागणी (each prayer in Marathi, petition order); the English prayers verbatim FIRST in
  `related`; story order and linking words (§4.32 (ई)); respectful plural, Marathi designations; the petition as "रिट याचिका क्र. <N>/<YYYY>" in the Marathi note and letter,
  no "(लॉजिंग)" (Abhi 05.11.2026; English parawise / affidavit case titles unchanged).
- INSTRUCTIONS.md §4.35 (joint affidavit): several State respondents -> ONE joint affidavit "शासनाच्या वतीने" on behalf of
  all of them (parawise / affidavit `on_behalf_of` = all State respondents; the GP letter asks the one joint draft; copy
  to the other State respondent department for information). The High Court administration (महाप्रबंधक / प्रबंधक), if a
  respondent, is NOT part of it: no remarks, no request, no copy on its behalf.
- PROPOSAL_SOP.md Step 4b "Court cases and order drafts" (para 1 from the GP/AGP letter, else "सादर.", `parawise` spec in the
  Section's office format, letter to the GP/AGP forwarding it, Rule 58(4) time limit).
- INSTRUCTIONS.md §3.1 (affidavit / parawise reply in English, explanation in Marathi), §4.28 / §4.33 (ticked drafts incl.
  parawise, affidavit), §4.30 (quality checks, respectful language to courts, every para and prayer answered), §4.27 and
  all other §4 items.
- Models: samples/specs/WP35697_2026_old-pension_finance-opinion.json (note: §4.32 paras 2/3) and
  samples/specs/WP35697_2026_parawise_GP-letter.json (parawise + GP letter: §4.35 joint affidavit); parawise office format
  only: samples/specs/COURT_wp_parawise_example.json. Research and decisions B1–B10: docs/COURT_AND_ORDERS_RESEARCH.md.
- Tools: tools/build_parawise.py, tools/lint_parawise.py, tools/build_affidavit.py, tools/lint_affidavit.py.
- Default drafts: parawise + letter (C33 contract; the existing court_notice suggestion logic stays).
