# Handover — प्रस्ताव कक्ष (Proposal Desk) dashboard v2

Date: 01.11.2026 · Branch: `dashboard-v2` (do NOT merge into `main` until the front end is built and tested end to end)
Spec: `docs/DASHBOARD_BUILD_PROMPT.md` · Processing rules: `OWNER_RULES.md`, `INSTRUCTIONS.md`, `PROPOSAL_SOP.md`, `PROPOSAL_WORKFLOW.md`

## 1. स्थिती (मराठी)

| भाग | फाइल | स्थिती |
|---|---|---|
| Supabase schema | `supabase/migrations/20261101000001_init.sql` | पूर्ण. टेबल्स, RLS, private buckets (`proposals`, `outputs`, `gr-library`, `backups`), roles (owner/desk/senior + invite), stage-change audit log, सरासरी-दिवस view, नोंदवही शोध, Realtime. **खऱ्या Postgres 16 वर चाचणी झाली:** desk लिहू शकतो, senior फक्त वाचू शकतो, बाहेरच्या व्यक्तीला आणि anon ला 0 ओळी दिसतात, शोध चालतो. |
| Cloudflare Worker | `cloudflare/worker.js`, `cloudflare/wrangler.toml` | लिहिलेला आहे, अजून चालवलेला नाही. Endpoints: `/api/upload`, `/api/run`, `/api/files/:id`, `/api/gr`, `/api/search`, `/api/letters`, `/api/cases`, `/api/me`, `/api/config`. प्रत्येक call ला JWT तपासणी, 50 MB मर्यादा, तासाला 40 uploads, 10 मिनिटांचे signed URL. |
| प्रक्रिया | `.github/workflows/process-proposal.yml`, `tools/sb.py` | लिहिलेले आहे, अजून चालवलेले नाही. `repository_dispatch` ने सुरू होते → Supabase मधून proposal उतरवते → `tools/run_headless.sh` → outputs परत Supabase मध्ये. केस-फाइल्स repo मध्ये जात नाहीत. |
| Deploy / backup | `.github/workflows/deploy.yml`, `backup.yml`, `tools/deploy_auth.py` | लिहिलेले आहे, अजून चालवलेले नाही. Secrets वरून: Supabase migration, auth (OTP), seed, test user आणि Worker deploy. |
| GR मागणी | `.github/workflows/gr-request.yml` | Dashboard कडून `fetch_gr` event येतो; नवीन GR Supabase मध्ये sync होतो. |
| Headless | `tools/HEADLESS_PROMPT.md`, `tools/run_headless.sh` | MODE (study/reminder/cabinet), संदर्भ कागदपत्रे, पुन्हा-चालवण्याच्या सूचना, ORIGINAL_NAME, progress.txt आणि status.json मधील ब्रीफिंग डेटा जोडले; PROPOSAL_SOP आणि `verify_outputs.py` शी जुळवले. |
| Front end | `app/` | **बाकी.** फक्त config फाइल्स आहेत (package.json, vite, tailwind, tsconfig, index.html, icon). एकही पान बनलेले नाही. |

### बाकी काम
1. Front end (`app/`) — सर्वात मोठा भाग.
2. जुना `dashboard/` फोल्डर काढणे (आता `app/dist` वापरले जाईल).
3. एका पानाचा मराठी setup guide.
4. Secrets भरल्यानंतर deploy, खरी end-to-end चाचणी आणि स्क्रीनशॉट्स (अपलोड फॉर्म, live progress, केस-तपशील, 390 px मोबाईल).

### घेतलेले निर्णय (बदलता येतील)
- **Pages ऐवजी एकच Worker:** app आणि API एकाच Worker वरून चालतात. एकच domain असल्यामुळे सोपे.
- **Storage मधील फाइलनाव:** Supabase storage key मध्ये मराठी अक्षरे चालत नाहीत. म्हणून key इंग्रजीत ठेवली आहे आणि मूळ नाव `case_files.original_name` मध्ये साठवले आहे. Download करताना फाइल **मूळ नावानेच** येते (§4.16).
- **मंत्रिमंडळ टिप्पणी:** फक्त बटण दाबल्यावर बनते (mode `cabinet`). Format फक्त `pdf/08-gad-office-procedure/` मधील अधिकृत manuals मधून घेतला जाईल; तिथे सापडला नाही तर "उपलब्ध नाही" असे लिहिले जाईल, स्वतःचा format बनवला जाणार नाही.
- **Roles:** invite केलेल्या email ला त्याचा role मिळतो; पहिला user owner होतो; इतरांना access नाही.

### Abhi यांनी करायचे
GitHub → Settings → Secrets and variables → Actions मध्ये हे secrets भरा:
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_PROJECT_REF`, `SUPABASE_DB_PASSWORD`, `SUPABASE_ACCESS_TOKEN`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GH_DISPATCH_TOKEN` (फक्त हा repo; Contents + Actions = Read/Write), `ANTHROPIC_API_KEY`, आणि चाचणीसाठी `E2E_TEST_PASSWORD`.
Repo **private** करा (त्यात जुन्या प्रकरणांच्या zip फाइल्स आहेत).

## 2. Prompt for the next Claude Code session (one message)

```
Repo abhishekwasu-hue/law-judiciary-service-rules, branch dashboard-v2. Read OWNER_RULES.md, INSTRUCTIONS.md, PROPOSAL_SOP.md, docs/DASHBOARD_BUILD_PROMPT.md and docs/HANDOVER_DASHBOARD_V2.md first.
DONE and tested: supabase/migrations/20261101000001_init.sql (RLS verified on Postgres 16 with stub auth/storage schemas).
DONE, not yet run: cloudflare/worker.js + wrangler.toml (Worker serves app/dist + /api/*: upload [signed upload URLs to bucket proposals/<case_id>/, original_name kept in case_files], run [inserts runs row, repository_dispatch process_proposal {case_id, run_id}], files/:id [10-min signed URL, ?download=1 uses the original name], files?ids= [batch for ZIP], gr, search [rpc search_register], letters, letters/:id/remind, cases, me, config [returns SUPABASE_URL/ANON_KEY]); tools/sb.py; tools/deploy_auth.py; .github/workflows/{process-proposal,deploy,backup,gr-request}.yml; tools/HEADLESS_PROMPT.md + tools/run_headless.sh (MODE study|reminder|cabinet, EXTRA_DOCS, USER_INSTRUCTIONS, ORIGINAL_NAME, progress.txt words reading→searching_grs→drafting→building_pdf→verifying, status.json keys letter_needed, essential_points, grs_attached, grs_missing, briefing{bullets,burden,periods,claims}).
Outputs land in bucket outputs/<case_id>/v<N>/<kind>.<ext>; case_files.kind: study, note_letter, package_pdf (original proposal name), reminder, cabinet_note.
TODO: build app/ (React 18.3.1 + Vite 5.4.11 + TS 5.6.3 + Tailwind 3.4.17 + supabase-js 2.47.10 + recharts 2.15.0 + pdfjs-dist 4.10.38 + docx-preview 0.3.3 + jszip 3.10.1 + exceljs 4.4.0 + diff 5.2.0 + vite-plugin-pwa 0.21.1 + @fontsource/noto-sans-devanagari 5.1.0; package.json/vite/tailwind config already written). Marathi UI, one responsive PWA for desktop and 390 px mobile with a bottom bar. Get Supabase config from /api/config. Screens per DASHBOARD_BUILD_PROMPT §6. Priority: (1) "+ नवीन प्रस्ताव" page and button (Home, case list, mobile bottom bar): proposal PDF required + extra docs (PDF/JPG/PNG, max 50 MB), fields C R no/year/file no/subject/category/priority, "अभ्यास सुरू करा" → /api/upload → PUT files to the signed URLs → /api/run → Realtime stepper on runs.progress; (2) case detail and row icons when the run is done: downloads for Study, Note+Letter, PDF with original name; docx-preview and pdf.js with an outline panel; ZIP of all files; "सुधारणा करून पुन्हा तयार करा" re-run with instructions (runs.instructions) and a version list; reply upload (kind reply → stage माहिती प्राप्त + offer re-run); cabinet-note button (mode cabinet). Then Home KPIs/charts, Kanban, GR library, register search, settings (invites/roles). Login: email OTP code, plus password for the e2e user e2e.desk@proposal-desk.test.
Then: delete old dashboard/, write a 1-page Marathi setup guide, self-review every diff, push, run the Deploy workflow, run one real end-to-end test, take screenshots (upload form, live progress, case detail, 390 px mobile), and list the changed files.
```
