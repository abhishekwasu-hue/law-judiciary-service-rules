# HANDOVER — state as of 01.11.2026 (read after CLAUDE.md files)

## Done (all in this repo)
- Procedure: INSTRUCTIONS.md §4 items 1–17, PROPOSAL_SOP.md (step-by-step), PROPOSAL_WORKFLOW.md, samples/specs/ (approved notes), tools/ (mkdocs, build_note_letter, build_study, pkg3, highlight, verify_outputs, gr_request, oldcases_text).
- Proposals delivered: C R 66, 122, 128, 130, 131, 133 /2026 (three files each, sent to Abhi). GRs used are in pdf/gr/ (+INDEX.tsv), SC order in pdf/sc/, MCS (Pay) Rules 1981 full in pdf/01-mcs-pay-rules-1981/.
- Dashboard build prompt for a real app: docs/DASHBOARD_BUILD_PROMPT.md (option B, to be given by Abhi to a Claude Code session).

## Pending
1. **C R 128/2026** — 6 Law & Judiciary GRs not on archive.org (GR site search has captcha). Abhi will give their सांकेतांक: 05.08.2026 (judicial officers' retirement age 62), 12.03.2014, 31.03.2018, 14.05.2021, 02.12.2022, 19.04.2022 (secretary cadre, संकीर्ण-2021/98/प्र.क्र.32). Then: download (gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf), add to the package after the existing enclosures (the package's spec/enclosures were in the old session's scratch — rebuild: proposal = Abhi's CR 128 PDF; enclosures: SC order pdf/sc/... pages 1,2,20,34,35 (para 14 a–c highlighted, p.34), pdf/gr/202204191549468012.pdf p1-2, pdf/gr/202301111807499612.pdf p1-2, MJS Rules 2008 pdf/71-district-court-staff-recruitment-rules/... pages 1,2,18,19,20, MCS Pension Rules 1982 pdf/80-retirement-age-group-d-reemployment/... pages 11,12,22), highlight the posts, update पृ./प.वि. in samples/specs/CR128_*.json and rebuild with tools/build_note_letter.py. Ask Abhi to re-attach the CR 128 proposal PDF if needed.
2. **Study part 0 (briefing for seniors, §4.17)** — not yet in the Study files of C R 130, 131, 133 (made before the rule). Add only if Abhi asks.
3. **Option A — "प्रस्ताव कक्ष" claude.ai page (Abhi asked for it; not built yet).** Design decided:
   - Plain HTML artifact (NOT the Dashboard type — it cannot upload). Capabilities: `assets` (proposal PDF uploads), `db` (cases), `downloads` (save outputs), `user`.
   - db `cases/<id>`: {cr, year, file_no, subject, category, priority, stage, status queued|processing|done, created_at, inputs:[{asset_id,name,size}], outputs:[{name, kind, store:'asset'|'db', ref}], letter_needed, summary, essential_points[], grs[], instruction, history[]}.
   - Finding: `assets` accepts PDF/images/text but NOT .docx → store each output .docx base64 in db docs `outputs/<case>__<kind>__<n>` split into chunks < 200 KiB (db doc cap 256 KiB); the PDF output goes to `assets`. Page reassembles and calls downloads.save({filename, data: Blob}).
   - Flow: Abhi uploads in the page → tells Claude "प्रस्ताव कक्षातील नवीन प्रस्ताव तयार कर" → Claude lists `cases` where status=queued (ArtifactData), reads input assets (Artifact read with path = asset id), runs PROPOSAL_SOP, uploads outputs (PDF via Artifact publish asset:true; docx base64 chunks via ArtifactData batch), sets status done + summary.
   - UI: Marathi, navy/saffron restrained, Mukta font; KPI chips by stage; "+ नवीन प्रस्ताव" form; case cards with stage pill, three download buttons, re-run instruction box, reply upload; small inline SVG bar charts by stage/category; mobile-first.
4. **Repo is PUBLIC** and contains real case data (old zips, samples). Abhi was told to make it private — remind once if still public.

## Network notes
- Session allowlist was set to "All domains" by Abhi (gr.maharashtra.gov.in, archive.org, sci.gov.in, finance.maharashtra.gov.in reachable). If blocked again, use the GitHub Action "GR request" (push tools/gr-request.txt).
- Office network: GitHub/vercel blocked; Cloudflare (workers.dev) and Supabase work.
