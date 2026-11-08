# NEW_ACCOUNT_SETUP.md — work from another claude.ai account (Abhi, 08.11.2026: "dusrya acount login session mdhun suddha kam karu shaklo pahije")

Everything needed is in this repo. Only four things live inside a claude.ai account and must be set up once per account:
the skills, the scheduled task, the प्रस्ताव कक्ष page (or access to it) and the Project memory. Nothing else.

| What | Where in the repo | Per account? |
|---|---|---|
| Rules, procedure | OWNER_RULES.md, INSTRUCTIONS.md, PROPOSAL_SOP.md, PROPOSAL_WORKFLOW.md, HANDOVER.md (CLAUDE.md loads them) | no |
| Tools, templates, GRs, register, samples | tools/, pdf/, register/, service-rules/, samples/, precedent-library/ | no |
| Case state (every proposal) | cases/<id>/ (case_state.py) | no |
| Skills (4 work types) | skills/lj-seva, lj-nyayalayin, lj-vidhimandal, lj-kharedi /SKILL.md | **yes** — upload |
| Page (App B UI) source + build | dashboard-app/ (`npm run build:artifact`), data layer contract dashboard-app/src/lib/artifact/README.md, docs/PROPOSAL_DESK.md | page = **yes** (or share) |
| Worker procedure | docs/DESK_WORKER.md | no |
| Scheduled task text | docs/DESK_TASK_PROMPT.md | **yes** — create |
| GR index / register index for the page | tools/desk_gr_index.py, tools/desk_register_index.py | built per page |

## Option 1 — same page, second account (recommended: one set of cases)
1. Account 1 (the owner) opens the page → Share → invite account 2's e-mail as **Editor** (the page's db rules give write
   access to Editors only; a Contributor or Viewer can read but not start work or change anything).
2. Account 2 session (any chat/code session with this repo): create the scheduled task from docs/DESK_TASK_PROMPT.md
   (PAGE_URL = the shared page); note its id `trig_…`.
3. `meta/config` is owner-only (db rule `{"path":"meta","write":"owner"}`), so account 2 cannot write it: account 2 opens
   the page once (this writes its `members/<viewer id>` doc) and gives its `trig_…` id to the owner. The owner's session
   (account 1) then writes `meta/config.triggers[<account-2 viewer id>] = "<its trig id>"` (ArtifactData update on
   `meta/config`, pinned; viewer id = account 2's `members` doc id). The page fires the viewer's own task (a task can be
   fired only by its own account; src/lib/artifact/api.ts fireWorker); without that entry account 2 sees the
   "work can be started only from the owner's account" message.
4. Upload the four skills (step S below).

## Option 2 — own page in the second account
1. `cd dashboard-app && npm ci && npm run build:artifact`.
2. Publish `dashboard-app/dist-artifact/index.html` as a NEW artifact with files `icon.svg`, `icon-192.png`,
   `manifest.webmanifest`, `nasti/index.html` (from dist-artifact/) and capabilities
   `{"assets":{},"db":{"rules":[{"path":"","read":"view","write":"admin"},{"path":"meta","write":"owner"},{"path":"meta/worker","write":"admin"}]},"downloads":true,"user":{"scopes":["profile"]},"mcp":{"servers":[{"server":"Claude Code Remote","tools":["fire_trigger"]}]}}`.
3. Seed: `python tools/desk_gr_index.py gr.json` and `python tools/desk_register_index.py reg.json` → upload both as
   assets → `meta/gr_library {asset}`, `meta/register_index {asset}`.
4. Create the scheduled task (docs/DESK_TASK_PROMPT.md with the new PAGE_URL) → `meta/config {trigger_id}`.
5. Cases are separate from account 1's page (page data is not in git; drafts and state are — cases/<id>/).
6. Upload the four skills (step S).

## S — skills
Upload skills/<name>/SKILL.md for lj-seva, lj-nyayalayin, lj-vidhimandal, lj-kharedi in claude.ai (Settings → Skills), or
ask the session to propose them (propose_skills, kind new, content = the repo file). The repo copy is the master; after a
change here, update the account copy.

## Chat path (no page)
Any account: start a session with this repo, upload the proposal PDF in chat — the skill + CLAUDE.md rules do the rest
(INSTRUCTIONS §4.41); state goes to cases/<id>/ and is shared through git.

## One message to paste in a new account's session (does Option 1 or 2 for you)
"law-judiciary-service-rules रेपो घ्या, docs/NEW_ACCOUNT_SETUP.md वाचा आणि या खात्यासाठी Option <1|2> पूर्ण करा: skills, scheduled task व पान. पूर्ण झाल्यावर मराठीत 3 ओळींत सांगा."
