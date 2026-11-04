# कामकाजाच्या श्रेणी (Work types) — फ्रेमवर्क (C33, 04.11.2026)

मालक (Abhi, 04.11.2026): "इतर कामकाजाचे नमुने नव्याने देण्यात येईल फ्रेमवर्क तयार करून ठेवा".
नवीन श्रेणी जोडणे = फाइल्स जोडणे; Python कोडमध्ये बदल नाही (tools/desk.py च्या desk-profile पद्धतीप्रमाणे).

| id | श्रेणी | स्थिती | डिफॉल्ट मसुदे |
|---|---|---|---|
| service | सेवाविषयक प्रकरणे (डिफॉल्ट) | ready | letter |
| court | न्यायालयीन प्रकरणे | ready | parawise, letter |
| legislature | विधिमंडळ कामकाज | rules_pending | letter |
| procurement | खरेदी विषयक बाबी | rules_pending | letter |

`rules_pending` श्रेणीसाठी engine सर्वसाधारण (service) नियमांनुसार नोंद तयार करते व Study / warnings मध्ये
`pending_warning` ("पडताळणी अपूर्ण — <श्रेणी>: या श्रेणीचे स्वतंत्र नियम/नमुने अजून नाहीत; सर्वसाधारण नोंद तयार केली") देते.

## फाइल्स
- `tools/work_types/<id>.json` — id, label, status, default_drafts, allowed_drafts (INSTRUCTIONS §4.28 keys), rules_file,
  samples_dir, required_samples, pending_warning.
- `tools/work_rules/<id>.md` — ready: विद्यमान INSTRUCTIONS/SOP भागांचे संदर्भ; rules_pending: नमुन्यांवरून भरायचा साचा.
- `samples/work/<id>/README.md` — मालकाने कोणते नमुने द्यावेत व ते नियम कसे होतात.
- `tools/work_type.py` — `load(id)`, `list_types()`, `prompt_block(id)`, `default_drafts(id)`; CLI `list | show <id> | check`.
- `tests/test_work_types.py`.

## नवीन श्रेणी जोडण्याच्या 5 पायऱ्या
1. **json:** `tools/work_types/<id>.json` (आहे त्या फाइलची प्रत; id = फाइलनाव, लहान इंग्रजी अक्षरे). सुरुवातीला
   `"status": "rules_pending"`, `required_samples` भरा, `pending_warning` "पडताळणी अपूर्ण — <श्रेणी>: …" ने सुरू.
2. **rules md:** `tools/work_rules/<id>.md` — `legislature.md` चा साचा कॉपी करा; नमुने येईपर्यंत रिकामा (स्वतःचे नियम नाहीत —
   OWNER_RULES A.3/A.5).
3. **samples:** `samples/work/<id>/README.md` + नमुने; नमुन्यांवरून नियम भरल्यावर व मंजूर spec `samples/specs/` मध्ये
   आल्यावर `"status": "ready"`.
4. **Worker id-यादी:** `cloudflare/worker.js` → `export const WORK_TYPES = ['service', 'court', 'legislature', 'procurement'];`
   (DESK_IDS च्या शेजारी) — त्या यादीत id जोडा; cases insert/patch validation (`BAD_WORK_TYPE`, 400 मराठी संदेश) तीच यादी वापरते.
5. **App label:** `dashboard-app/src/lib/constants.ts` → `WORK_TYPES` (id, label, short) व `WORK_TYPE_TONE` (रंग); `WorkType`
   type आपोआप. नंतर `python3 tools/work_type.py check`, `python3 -m pytest -q tests/test_work_types.py`, worker tests, app build.

(Database: `cases.work_type` साधा text आहे, CHECK constraint नाही (`supabase/migrations/20261104000010_work_type_queue.sql`) —
नवीन id साठी migration नको.)

## Engine wiring (एकदाच, C33 engine agent)
- `tools/engine_supabase.py` case.json लिहिताना: `"work_type": cases.work_type` (null / अज्ञात → "service";
  `work_type.type_ids()` ने तपासा).
- workflow prompt मध्ये (process-proposal.yml, ENGINE_BRIEF नंतर) `work_type.prompt_block(id)` चा मजकूर: उदा.
  `$(python3 tools/work_type.py prompt "$(python3 -c 'import json;print(json.load(open("/tmp/case/case.json")).get("work_type") or "")')")`
  (CLI `prompt`: id नसल्यास / अज्ञात → service). rules_pending असल्यास `pending_warning` status.json warnings व Study भाग 7 मध्ये
  (engine finish मध्ये हमी हवी असल्यास: work_type rules_pending आणि warning नसेल तर जोडावा).

## English (short)
Add a category: (1) `tools/work_types/<id>.json`, (2) `tools/work_rules/<id>.md` (template until samples exist),
(3) `samples/work/<id>/` + README; flip status to "ready" once rules come from approved samples, (4) add the id to
`WORK_TYPES` in `cloudflare/worker.js`, (5) add id/label/tone to `WORK_TYPES` /
`WORK_TYPE_TONE` in `dashboard-app/src/lib/constants.ts`. Run `python3 tools/work_type.py check` and the tests.
