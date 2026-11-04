# विधिमंडळ कामकाज (legislature) — नमुने येथे ठेवावेत

स्थिती: **rules_pending** (`tools/work_types/legislature.json`). नियम/नमुने येईपर्यंत engine सर्वसाधारण (सेवाविषयक) नियमांनुसार
नोंद तयार करते व अभ्यास-फाइलमध्ये इशारा देते.

## कोणते नमुने द्यावेत (मालक)
- तारांकित प्रश्न + उत्तर-प्रारूप + टिप्पणी
- अतारांकित प्रश्न + उत्तर
- लक्षवेधी सूचना + निवेदन
- आश्वासन-पूर्ती

प्रत्येक नमुन्यासाठी: जुनी मंजूर नस्ती (टिप्पणी + मसुदा, docx किंवा PDF) व लागू असल्यास तिचा मूळ प्रश्न/सूचना/प्रस्ताव.
नावे/गोपनीय तपशील असले तरी चालेल (रेपो private); नमुना मसुद्यात वापरताना नावे "____".

## कोठे
या फोल्डरमध्ये: `samples/work/legislature/<नमुन्याचे नाव>.docx` / `.pdf` (उदा. `01_tarankit-prashna.docx`).

## नमुन्यांचे नियम कसे होतात (Steps)
1. मालक नमुने (docx/pdf) या फोल्डरमध्ये ठेवतो (किंवा सत्रात देतो — Claude येथे commit करतो).
2. संशोधन-agent प्रत्येक नमुन्याची रचना काढतो: नोंदीचा परिच्छेद-क्रम, मसुदे, अत्यावश्यक घटक, मुदती, सही-साखळी — प्रत्येक
   मुद्दा नमुना-फाइल + पान/परिच्छेदासह (स्वतःचे नियम नाहीत — OWNER_RULES A.3/A.5).
3. `tools/work_rules/legislature.md` चे शीर्षक-भाग फक्त त्या स्रोतांवरून भरले जातात; मालक मान्यता देतो.
4. मंजूर नमुना-spec `samples/specs/<नाव>.json` म्हणून जोडला जातो (lint_spec OK); आवश्यक lint तपासण्या नियमांशी जोडून.
5. `tools/work_types/legislature.json` मध्ये `"status": "ready"` (व आवश्यक तर `default_drafts`); नंतर
   `python3 tools/work_type.py check` व `python3 -m pytest -q tests/test_work_types.py` (व पूर्ण tests) OK.

## English (short)
Put the owner's sample files here. A research agent extracts the structure with sources, fills tools/work_rules/legislature.md
(owner approves), a sample spec goes to samples/specs/, then flip status to "ready" in tools/work_types/legislature.json and run
`python3 tools/work_type.py check` + the tests.
