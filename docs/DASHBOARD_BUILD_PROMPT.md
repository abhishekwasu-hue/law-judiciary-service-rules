# Build prompt — "प्रस्ताव कक्ष" (Proposal Desk) dashboard
Give this whole file, as one message, to the coding session (Claude Code) or the design tool. All UI text must be in Marathi (Devanagari);
code, comments and identifiers in English.

---

## 1. Who it is for and what it does
The user is the Section Officer, Desk-6 (कार्यासन-6), Law & Judiciary Department, Government of Maharashtra. Every week he receives
service-matter proposals (scanned PDFs) from the High Court and District Courts: pay fixation, allowances, pension, old-pension option,
special pay, insurance (DLI), retirement age, etc.

For each proposal, the system already has a working back-end process. It lives in the GitHub repo
`abhishekwasu-hue/law-judiciary-service-rules`; its rules are in `CLAUDE.md`, `INSTRUCTIONS.md` and `PROPOSAL_WORKFLOW.md`.
That process produces three files:
1. `<PREFIX>_Study.docx`: part 0 is a bullet briefing for seniors, followed by parts 1–7 (Marathi rendering, gist, provisions, doubts, drafts, verification).
2. `<PREFIX>_Note_and_Letter.docx`: the ready government note (टिप्पणी) in the Section's own format. A letter follows only if essential information is missing.
3. The proposal PDF returned with the relevant GR/rule pages attached. It keeps its **original file name** and has page stamps, bookmarks and yellow highlights on the quoted lines.

The dashboard is the professional front end for this workflow. Build exactly what is specified; do not add workflow rules.

## 2. Hard constraints
- **Office network:** github.com, *.github.io and vercel.app are blocked. Cloudflare (workers.dev / pages.dev) and Supabase (supabase.co) work.
  The browser must therefore talk only to the Cloudflare Worker and Supabase. GitHub may be used server-side only.
- **Confidential data** (employee names, service records):
  - Supabase Storage buckets must be private and served through signed URLs.
  - Every table needs Row Level Security.
  - Only authenticated users get access. The first user is the owner; the owner can invite colleagues.
- **Devices:** works on the office desktop (Windows/Chrome) and on a mobile phone (PWA, installable) with the same features.
- **Language and font:**
  - Marathi UI.
  - Devanagari web font: Noto Sans Devanagari, or Mukta for body text.
  - Official documents keep the font DVOT-SurekhMR. The documents are produced by the back end; the dashboard must not alter them.
- **Pinned versions:** use exact library versions.

## 3. Architecture (keep it simple)
- **Front end:** Cloudflare Pages, React + Vite + TypeScript, Tailwind. Use shadcn/ui-style components and Recharts for charts. Include a PDF viewer (pdf.js) and a DOCX preview (docx-preview).
- **API:** one Cloudflare Worker (`/api/*`) holds all secrets: SUPABASE_SERVICE_KEY, GITHUB_TOKEN and ANTHROPIC_API_KEY (if needed).
- **Data:** Supabase provides Postgres, Auth (email + OTP), Storage (private buckets `proposals`, `outputs`, `gr-library`) and Realtime (for status updates).
- **Processing engine:** GitHub Actions in the repo above.
  1. The Worker triggers the run with `repository_dispatch` (event `process_proposal`, payload `{case_id}`).
  2. The workflow downloads the proposal from Supabase Storage.
  3. It runs Claude Code headless with the repo's `CLAUDE.md`. Reuse the existing `tools/HEADLESS_PROMPT.md`, `tools/run_headless.sh`, `tools/mkdocs.py`, `tools/pkg3.py` and `tools/gr_request.py`.
  4. It uploads the three outputs plus `status.json` to Supabase Storage and updates the `cases` row.
- **Reuse:** the repo already contains a first draft — `dashboard/`, `cloudflare/worker.js` and `.github/workflows/process-proposal.yml`, which currently keeps files in the repo. Replace the file storage with Supabase. Keep the processing logic.

## 4. Data model (Supabase)
- **`cases`**:
  - Identity: `id`, `cr_no`, `cr_year`, `file_no`, `subject` (Marathi), `category` (enum: वेतननिश्चिती, भत्ते, निवृत्तीवेतन, जुनी पेन्शन, विशेष वेतन, विमा/GPF, सेवा, न्यायिक वेतन, वैद्यकीय, इतर).
  - People and source: `employee_name`, `post`, `office`, `received_from`, `received_via` (High Court / direct), `inward_date`.
  - Workflow: `stage` (enum, §5), `priority`, `due_date`, `assigned_to`.
  - Metadata: `created_at`, `updated_at`.
- **`case_files`**: `case_id`, `kind` (proposal / extra_doc / study / note_letter / package_pdf / gr / reply), `storage_path`, `original_name`, `version`, `uploaded_by`, `created_at`.
- **`runs`**: `case_id`, `started_at`, `finished_at`, `state` (queued / running / done / failed), `instructions` (free text the user adds for a re-run), `log_url`, `summary`, `letter_needed` (bool), `essential_points` (jsonb), `grs_attached` (jsonb), `grs_missing` (jsonb).
- **`letters`**: `case_id`, `ref_no`, `addressed_to`, `sent_date`, `reply_due`, `reply_received_date`, `status`.
- **`gr_library`**: `code` (सांकेतांक), `date`, `department`, `title`, `storage_path`, `source_url`, `used_in_cases` (int[]). Seed it from the repo's `pdf/gr/INDEX.tsv`.
- **`activity`**: an audit log of who did what, and when.

## 5. Case stages (Kanban + timeline)
प्राप्त → अभ्यास चालू → मसुदा तयार → वरिष्ठांकडे सादर → पत्र पाठवले (माहिती प्रतीक्षेत) → माहिती प्राप्त → वित्त/सा.प्र.वि. कडे → अभिप्राय प्राप्त → आदेश/पत्र निर्गमित → बंद.
Every change of stage is logged with date and user. A case can be moved by drag-and-drop or from the detail page.

## 6. Screens
1. **मुख्य पृष्ठ (Home):**
   - KPI cards: नवीन, अभ्यास चालू, उत्तर प्रतीक्षेत, वित्त विभागाकडे, या महिन्यात बंद.
   - "आज करायचे" list: overdue replies and items due in the next 7 days.
   - Recent activity.
   - Charts:
     - cases by category (donut);
     - cases by stage (horizontal bar);
     - monthly received vs. closed (line);
     - average days per stage (bar);
     - pending replies by office (bar).
   - Every chart is clickable and filters the list.
2. **नवीन प्रस्ताव (Upload):**
   - Drag-and-drop the proposal PDF and optional extra documents.
   - Form fields: C R no., year, file no. (निर्देशपत्र), subject (auto-filled from the PDF's first page if possible, editable), category, priority.
   - "अभ्यास सुरू करा" button: creates the case and triggers the run.
   - Shows live progress through Realtime: queued → reading pages → searching GRs → drafting → building PDF → verifying → done.
3. **प्रकरणे (Case list):** table and Kanban views; search and filters (category, stage, office, year, overdue); bulk export to Excel.
4. **प्रकरण तपशील (Case detail):** tabs —
   - **ब्रीफिंग:** Study part 0 rendered as cards, plus small charts where the data allows (e.g., financial burden by establishment, service-period timeline/Gantt with breaks highlighted, amounts claimed vs. admissible). A one-click "वरिष्ठांसाठी प्रिंट" A4 view.
   - **टिप्पणी व पत्र:**
     - DOCX preview and download.
     - If there is a letter, show the list of essential points it asks for.
     - Re-run button "सुधारणा करून पुन्हा तयार करा" with a text box for the user's instructions (stored in `runs.instructions` and passed to the headless run).
     - Version history with a diff between versions.
   - **प्रस्ताव + GR:**
     - pdf.js viewer with the PDF bookmarks shown as a side panel; the existing highlights stay visible.
     - Download keeps the original file name.
     - List of attached GRs, each with a link to its page.
   - **अभ्यास (Study):** full DOCX preview and download.
   - **पत्रव्यवहार:** letters sent, reply due date, reminder button (drafts a reminder letter through the same back end), upload of the reply. Uploading a reply moves the case to "माहिती प्राप्त" and offers to re-run the study with the reply included.
   - **इतिहास:** audit log and stage timeline.
5. **GR ग्रंथालय:**
   - Search by सांकेतांक, date, department or keyword.
   - Open the PDF; see which cases used it.
   - "GR जोडा" by सांकेतांक: the Worker fetches the official PDF from gr.maharashtra.gov.in or the archive.org mirror into Storage.
6. **नोंदवही शोध:** full-text search over the repo's `register/*.md` (verified extracts) via a Worker endpoint. Results show source, page and para.
7. **सेटिंग्ज:** users and roles (owner, desk staff, read-only senior); signature chain names used in notes; default letter addressee list; notification preferences (email / web push for overdue replies and finished runs).

## 7. UX quality bar
- Calm, professional government look:
  - deep navy primary color with saffron accent used sparingly;
  - light and dark mode;
  - large readable Devanagari type;
  - generous spacing.
- Status colors by meaning: green = done/closed, amber = waiting, red = overdue/failed, blue = in progress.
- **Interactivity:**
  - skeleton loaders, toasts and optimistic updates;
  - keyboard shortcuts on desktop (n = new proposal, / = search);
  - command palette (Ctrl+K);
  - swipe actions on mobile cards.
- Empty states with a one-line hint. No long prose on screens; details hidden behind expanders.
- Accessibility: WCAG AA contrast and visible focus states. Mobile: no horizontal scroll and 44 px tap targets.

## 8. Charts — where they belong
- **Dashboard and the Study briefing (part 0):** yes. Use them to brief seniors quickly. Recharts in the app; matplotlib PNG with a Devanagari font when embedded in the DOCX.
  - Pie/donut: composition only, e.g., financial burden by establishment.
  - Bar: comparisons.
  - Line: trends.
  - Gantt/timeline: service periods and breaks.
- **Official note (टिप्पणी) and letter:** **no charts**. Use tables only (the Section's format and the Finance Department's reading habits). The back end already produces these tables.

## 9. Security and operations
- Supabase RLS on every table.
- The Worker validates the Supabase JWT on every call.
- Signed URLs expire after 10 minutes.
- No secrets in the browser.
- Daily backup: a Supabase scheduled function exports DB rows to Storage.
- The GitHub repo should be made **private** (it currently contains old case files).
- Rate-limit uploads; maximum PDF size 50 MB.

## 10. Deliverables from the builder
1. Front end (Cloudflare Pages).
2. Worker with endpoints: `/api/cases`, `/api/upload`, `/api/run`, `/api/files/:id`, `/api/gr`, `/api/search`, `/api/letters`.
3. Supabase SQL migrations with RLS policies and seed data from `pdf/gr/INDEX.tsv`.
4. Updated `.github/workflows/process-proposal.yml`, driven by `repository_dispatch` and using Supabase Storage.
5. A one-page Marathi setup guide covering: Cloudflare deploy; Supabase project; and the secrets — Worker: GITHUB_TOKEN, SUPABASE_*; GitHub repo: ANTHROPIC_API_KEY.
6. A test run on one sample proposal, with screenshots of Home, Case detail and mobile view.
