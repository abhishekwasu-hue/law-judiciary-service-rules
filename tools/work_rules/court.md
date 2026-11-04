# Work type: court (न्यायालयीन प्रकरणे) — status: ready

No new rules here. Court matters (GP/AGP/High Court/MAT notice on a writ petition, O.A., contempt, SLP) follow the existing
binding rules exactly:

- PROPOSAL_SOP.md Step 4b "Court cases and order drafts" (note para 1 from the GP/AGP letter, "पार्श्वभूमी थोडक्यात
  खालीलप्रमाणे आहे:-", `parawise` spec in the Section's office format, letter to the GP/AGP forwarding it, Rule 58(4) time limit).
- INSTRUCTIONS.md §3.1 (affidavit / parawise reply in English, explanation in Marathi), §4.28 (parawise draft),
  §4.30 (quality checks, respectful language to courts, every para and prayer answered), §4.27 and all other §4 items.
- Research and decisions B1–B10: docs/COURT_AND_ORDERS_RESEARCH.md. Model: samples/specs/COURT_wp_parawise_example.json.
- Tools: tools/build_parawise.py, tools/lint_parawise.py.
- Default drafts: parawise + letter (C33 contract; the existing court_notice suggestion logic stays).
