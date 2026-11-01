# HANDOVER — state as of 01.11.2026 (updated: CR128 GRs, प्रस्ताव कक्ष) (read after CLAUDE.md files)

## Done (all in this repo)
- Procedure: INSTRUCTIONS.md §4 items 1–17, PROPOSAL_SOP.md (step-by-step), PROPOSAL_WORKFLOW.md, samples/specs/ (approved notes), tools/ (mkdocs, build_note_letter, build_study, pkg3, highlight, verify_outputs, gr_request, oldcases_text).
- Proposals delivered: C R 66, 122, 128, 130, 131, 133 /2026 (three files each, sent to Abhi). GRs used are in pdf/gr/ (+INDEX.tsv), SC order in pdf/sc/, MCS (Pay) Rules 1981 full in pdf/01-mcs-pay-rules-1981/.
- Dashboard build prompt for a real app: docs/DASHBOARD_BUILD_PROMPT.md (option B, to be given by Abhi to a Claude Code session).
- 01.11.2026: CR 128 — found on archive.org (identifier prefix search) and downloaded: pdf/gr/202608051759229212.pdf (05.08.2026, retirement age 62) and pdf/gr/202204191851066912.pdf (19.04.2022, संकीर्ण-2021/98/प्र.क्र.32). Not on archive.org under their date prefix: 12.03.2014, 31.03.2018, 14.05.2021, 02.12.2022. Also checked ±2–3 day prefixes (incl. 31.01.2018, the date the spec notes for the 31.03.2018 GR): no L&J pay-scale GR — only court-building/post/fund GRs.
- 01.11.2026: Option A built — "प्रस्ताव कक्ष" page https://claude.ai/artifact/RYzwfiGwJpbVxyD5C2rCy2 (source desk/proposal-desk.html, flow docs/PROPOSAL_DESK.md, chunk tool tools/desk_chunks.py). Seeded cases CR 122/128/130/131/133 (metadata only, no outputs). CR 131 and 133 category set to "इतर" (library mapping not certain) — Abhi to confirm.
- Repo is now private (anonymous git ls-remote refused, 01.11.2026).

## Pending
1. **C R 128/2026** — still need सांकेतांक for 4 GRs: 12.03.2014, 31.03.2018, 14.05.2021, 02.12.2022 (05.08.2026 and 19.04.2022 now in pdf/gr/), and Abhi's CR 128 proposal PDF (not in repo; upload it in प्रस्ताव कक्ष or attach). Then: download (gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/<code>.pdf), add to the package after the existing enclosures (the package's spec/enclosures were in the old session's scratch — rebuild: proposal = Abhi's CR 128 PDF; enclosures: SC order pdf/sc/... pages 1,2,20,34,35 (para 14 a–c highlighted, p.34), pdf/gr/202204191549468012.pdf p1-2, pdf/gr/202301111807499612.pdf p1-2, MJS Rules 2008 pdf/71-district-court-staff-recruitment-rules/... pages 1,2,18,19,20, MCS Pension Rules 1982 pdf/80-retirement-age-group-d-reemployment/... pages 11,12,22), highlight the posts, update पृ./प.वि. in samples/specs/CR128_*.json and rebuild with tools/build_note_letter.py. Ask Abhi to re-attach the CR 128 proposal PDF if needed.
2. **Study part 0 (briefing for seniors, §4.17)** — not yet in the Study files of C R 130, 131, 133 (made before the rule). Add only if Abhi asks.
3. **प्रस्ताव कक्ष** — built (see Done). Open: stage list (प्राप्त / माहिती मागवली / उत्तर प्राप्त / वित्त-सा.प्र.वि. कडे / निकाली) is provisional — Abhi to confirm; first real end-to-end run when Abhi uploads a proposal.
4. Repo private — done.

## Network notes
- Session allowlist was set to "All domains" by Abhi (gr.maharashtra.gov.in, archive.org, sci.gov.in, finance.maharashtra.gov.in reachable). If blocked again, use the GitHub Action "GR request" (push tools/gr-request.txt).
- Office network: GitHub/vercel blocked; Cloudflare (workers.dev) and Supabase work.
