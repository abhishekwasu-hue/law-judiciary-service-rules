# Cost and time audit — engine runs #17–#21 (06.11.2026)

Owner (06.11.2026): "तुम्ही कामाचे खर्चाचे आणि लागणाऱ्या वेळेचे ऑडिट करा". Source: GitHub Actions job logs of runs #17–#21
(modelUsage of the CLI result = exact cost; वेळ-तक्ता = stage times). Chart: docs/cost-time-audit-2026-11-06.png.

| Run | Case (pages) | Cost | Opus | Sonnet | Haiku | Part 1 | Job time | Claude step | Drafter / reviewer image reads |
|---|---|---|---|---|---|---|---|---|---|
| #17 | CR 14 (63) | $6.93 | $5.12 | $0.88 | $0.36 | $0.57 | 50 min | 30.4 min | 73 / 20 |
| #18 | CR 14 (63) | $5.99 | $4.71 | $0.44 | $0.20 | $0.64 | 42 min | 21.5 min | 74 / 18 |
| #19 | CR 50 (96) | $8.50 | $7.54 | $0.24 | $0.29 | $0.43 | 62 min | 40.0 min | 83 / 32 |
| #20 | CR 50 (96) | $8.26 | $6.69 | $0.79 | $0.55 | $0.23 | 57 min | 35.5 min | 66 / 39 |
| #21 | CR 50 | failed in 2 min, $0 | — | — | — | — | 9 min | — | main AI set to Gemini 2.5 Pro in Settings; part 1 and main run both exit 1 at turn 1 |

Opus cost split (prices $4 in / $20 out / $0.20 cache read / $5 cache write per 1M; reconciles to the logged totals):
run #19 cache writes $3.29, output $2.32, cache re-reads $1.94; run #20 $2.42 / $2.38 / $1.89.

Findings
1. **OCR never worked (all four runs):** `prep_pages: … ocr none (… tesseract … timed out after 300 seconds)`. Parallel
   tesseract processes with OpenMP's default threads thrash: measured on 4 CR 50 pages in parallel, default 300 s (all
   timed out) vs `OMP_THREAD_LIMIT=1` 2 s; the whole 27-page noting part OCR'd in 23 s. With no page text, the Opus
   agents had to open the page images (66–83 + 18–39 per run) — the main source of Opus cache writes and re-reads; the
   prep stage cost 8.7–10.2 min and the runner OCR of the package 5.4–10.0 min for nothing. **Fixed:** prep_pages.OCR_ENV,
   highlight.py, workflow env `OMP_THREAD_LIMIT: '1'`; test tests/test_tools.py::test_ocr_one_thread_per_tesseract.
2. **COST RULE (commit 2635b9e)** depends on finding 1: the agents read text / OCR first and open only the cited pages.
   No run has used it yet (#21 failed on Gemini before any work).
3. Opus written output ≈ $2.3 per run (88–119k tokens) — drafter + reviewer; not changed in this round.
4. Run #21: the reason (195 chars) is stored on the case page, not in the job log; part 1 also went through the Gemini
   gateway (AUTH is shared by both runs in the workflow).

Next measurement: the first run after this commit — cost lines, image reads, prep / OCR stage times.
