# cases/ — प्रकरणांची स्थिती-फाइल (INSTRUCTIONS §4.41)

एक प्रस्ताव = एक फोल्डर `cases/<id>/` (id = PREFIX, उदा. `CR131_2026`, `WP35697_2026`). खाजगी रेपो — गोपनीय (Abhi, 07.11.2026).

| फाइल | काय |
|---|---|
| `case.json` | prefix, GR सह PDF चे मूळ नाव, प्रस्तावाची पाने, जतन-वेळ |
| `spec.json` | टिप्पणी, पत्र व इतर मसुदे (साधनांचा spec) |
| `study.json` | Study फाइल |
| `enclosures.json`, `marks.json` | GR सह PDF ची रचना व highlight |
| `proposal.pdf` | मूळ प्रस्ताव |
| `src/` | रेपोबाहेरून जोडलेली कागदपत्रे (उदा. जुनी नस्ती) |
| `history.tsv` | प्रत्येक जतन / सुधारणेची एक ओळ |

साधन: `python3 tools/case_state.py save | load | rebuild | list` (docstring पहा).
