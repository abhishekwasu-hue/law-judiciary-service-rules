# Engine run — Study part 1 only (parallel helper of tools/ENGINE_PROMPT.md; started by .github/workflows/process-proposal.yml)

Given at run time (end of this prompt): PAGES (page files of the proposal), WORKDIR (case inputs), OUT (where you write).
Working directory = repo root. You do ONE thing: write Study part 1 — "भाग 1 — प्रस्तावाचे मराठी रूपांतर" — for this one
case. The main run (in parallel) does everything else; it checks your part against the main tier's own reading of
the images (`engine_supabase.py part1check`: every number, date and name per page must match) and inserts it
unchanged only when it matches — pages that do not match are redone by the main tier. So copy every number, date
and name exactly as on the image. Work in few turns: several Read calls in ONE message, no file read twice.

## Read first
1. `tools/ENGINE_BRIEF.md` (the binding rules of the engine run; its Study part 1 rules and source rules apply),
   then in `tools/PROPOSAL_PROMPT.md` only the section "कायमच्या सूचना" and the paragraph "भाग 1 — प्रस्तावाचे मराठी
   रूपांतर (जसेच्या तसे)" (Read with offset/limit). INSTRUCTIONS.md wins on any doubt.
2. The docstring of `tools/build_study.py` (the block format).
3. `PAGES/pages.json` — `pages`, `files[]` (`png`, `txt`, `ocr`), `has_text_layer[]`, `ocr_lang`.
Do not read other rule files, GRs or old cases; they are not needed for part 1.

## How to read
- LOOK at every page image `PAGES/p-NN.png` with the Read tool, in order, every page, none skipped (PROPOSAL_SOP Step 1).
  Read stamps, inward nos., handwritten remarks, dates and amounts twice.
- `p-NN.txt` (text layer) and `p-NN.ocr.txt` (OCR, if present) are a CROSS-CHECK only. Every number, date, name and amount
  is taken from the IMAGE. Where the image and the text/OCR differ, the image wins. Where the image itself cannot be read
  = "[अस्पष्ट]" — never fill it from the OCR or by guessing.
- If a PNG is missing or unreadable, render that page yourself from the proposal PDF in `WORKDIR/in/proposal/`
  (`python3 -c "import pymupdf; ..."`, 110 dpi) and look at it.

## What to write (exactly the PROPOSAL_PROMPT part-1 rules)
Each document of the proposal in order, page-wise, with the page number ("PDF पान N" and the file page "पृ. __" where it
is written on the page). English text translated into Marathi (designations / offices / Acts / GR numbers kept in the
original script in brackets); Marathi text exactly as written (जसेच्या तसे — no summary, no cut); tables as table blocks;
handwritten remarks "[हस्तलिखित शेरा: …]"; stamps / receipts "[शिक्का: …]"; unclear "[अस्पष्ट]". No comment, opinion or
gist of your own (that is part 2 of the main run).

## Output (OUT)
1. `OUT/study_part1.json` (UTF-8) = ONE `parts[]` entry of build_study.py, nothing else:
```json
{"heading": "भाग 1 — प्रस्तावाचे मराठी रूपांतर", "blocks": [
  {"subheading": "PDF पान 1 — <document, e.g. निर्देशपत्र>"},
  {"para": "..."},
  {"table": [["...", "..."], ["...", "..."]]}
]}
```
   Allowed block keys: `subheading`, `para`, `bullets`, `table` (no images). Write long text in steps (e.g. one page at a
   time into a scratch file under /tmp/part1/, then assemble) so nothing is lost.
2. Check it: `python3 -c` — the file parses as JSON, `heading` starts with "भाग 1", every proposal page 1..`pages` has its
   own subheading, every block has one allowed key.
3. Only then create the empty marker `OUT/study_part1.done`. If you cannot complete part 1, write `OUT/study_part1.failed`
   with a one-line reason instead (never both).

## Rules
- No questions (no interaction). Scratch work in /tmp only; never write in the repo, WORKDIR or any other OUTDIR.
- No git, no network, no environment values printed.
- Final reply: one line.
