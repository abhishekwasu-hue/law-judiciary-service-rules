# PROPOSAL_DESK.md — "प्रस्ताव कक्ष" claude.ai page (Option A)

- Page: https://claude.ai/artifact/RYzwfiGwJpbVxyD5C2rCy2 (private to Abhi). Source: `desk/proposal-desk.html`.
  Republish from this file with the Artifact tool and `url` = the page link (read it first in a new session).
- Capabilities: `db` (cases + output chunks), `assets` (proposal/reply PDF uploads, output PDF), `downloads`, `user`.

## Data
- `cases/<id>` (id `CR<no>-<year>`): {cr, year, file_no, subject, category, priority normal|urgent,
  stage received|info_sought|reply_received|sent_fin_gad|closed, status queued|processing|done, created_at,
  inputs:[{asset_id, name, size, kind proposal|reply}], outputs:[{name, kind study|note_letter|package, store asset|db, ref, chunks?, mime?}],
  letter_needed, summary, essential_points[], grs[], instruction, history:[{at, by user|claude, text}]}.
- Output PDF (`kind: package`): upload with Artifact publish `url` + `asset: true` + `file_path`; record `{store:"asset", ref:<asset id>}`.
- Output .docx (assets refuse .docx): `python tools/desk_chunks.py <file.docx> <case_id> <study|note_letter> <scratch dir>`
  → chunk files `outputs/<case>__<kind>__<i>` (< 200 KiB each); write them with ArtifactData batch (`file_path` per entry);
  put the printed record in `outputs[]`.

## Flow when Abhi says "प्रस्ताव कक्षातील नवीन प्रस्ताव तयार कर"
1. ArtifactData query `cases` where status == "queued".
2. For each case: set status "processing"; read each input with Artifact read (`url`, `path` = asset_id) → local PDF.
   kind "reply" = office's reply to our letter → next note per PROPOSAL_SOP (approval stage).
   Follow `instruction` if set.
3. Run PROPOSAL_SOP.md Steps 1–7 (three outputs, verify_outputs ALL OK).
4. Upload outputs (above); update the case: outputs, letter_needed, summary (1–2 lines Marathi), essential_points, grs,
   status "done", history + {by:"claude", text}. Pin every write with `if_version`.
5. Report to Abhi in Marathi per SOP Step 8; commit specs/GRs as usual.
