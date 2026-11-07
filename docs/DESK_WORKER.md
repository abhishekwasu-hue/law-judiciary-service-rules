# DESK_WORKER.md — work queued on the प्रस्ताव कक्ष page (run by the scheduled task "प्रस्ताव कक्ष — काम")

Abhi presses "▶ काम सुरू करा" on the page (https://claude.ai/artifact/8cJP8wz6j5tYM5kRHK1rVx); that fires this task in a fresh
cloud session. Everything below is binding together with CLAUDE.md (OWNER_RULES, INSTRUCTIONS, PROPOSAL_SOP, PROPOSAL_WORKFLOW).
Page data model: docs/PROPOSAL_DESK.md. All page reads/writes: ArtifactData / Artifact with that url. Abhi is not watching:
never ask, never stop for a question — log open points in the case history and in `missing_grs` / study part 7.

## 0. Start
1. Repo: `/home/claude/law-judiciary-service-rules` (pre-cloned) — `git pull -q`. If absent, clone abhishekwasu-hue/law-judiciary-service-rules.
2. Read `meta/worker`. If `state` = "running" and `at` is less than 3 h old, another run is active: stop at once (write nothing).
3. `meta/worker` ← `{state:"running", at:<now ISO>, step:"सुरुवात", note:""}`. Update `step` (one short Marathi line) at each item.

## 1. Collect
- `gr_requests` where status == "pending"; `cases` where status == "queued"; `edits` where status == "pending".
- Order: GR requests → edits (short) → queued cases (long). One case at a time; finish, sync, then the next.

## 2. GR request (`gr_requests/<key>` = {key, path, file})
- File = `<repo>/<path>`. ≤ 19 MiB: Artifact publish `asset: true` → `gr_files/<key>` = `{store:"asset", ref:<id>, name:<file>}`.
  Bigger: `tools/desk_sync.split_b64` parts, one upload each → `{store:"asset_parts", ref:[ids], name}`.
- Request ← `{status:"done", done_at}` (missing file: `status:"failed", reply:"फाइल रेपोमध्ये नाही"`).

## 3. Queued case (`cases/<id>`, status "queued": new intake, a reply added, or "पुन्हा तयार करा")
- `cases/<id>` ← `{status:"processing", stage:"अभ्यास चालू" (only if stage was "प्राप्त"), history += {at, stage, note:"Claude काम सुरू"}}`.
- Inputs: each `inputs[]` asset — Artifact `read` with `path` = asset_id (saved to a local file; keep `name`).
- Work type from the file content (service / court / legislature / procurement) → load the matching skill
  (`lj-seva`, `lj-nyayalayin`, `lj-vidhimandal`, `lj-kharedi`) and follow it and PROPOSAL_SOP fully (same rules as a chat
  proposal). `instruction` (if any) = Abhi's instruction for this run. A case with a `reply` input = next round with the
  office's reply (PROPOSAL_SOP).
- After the drafts pass lint + verify: `tools/case_state.py save <id> …`, `rebuild <id> <out> --package`, then
  `tools/desk_sync.py <id> <out> <sync>` → upload every path in `assets.txt` → ArtifactData batch: `outputs` chunks (set) and
  `cases/<id>` update: `outputs` (asset ids in place of `__ASSET__…`), `paras`, `summary` (2–3 lines), `letter_needed`,
  `essential_points`, `grs [{code,date,title,pages}]`, `missing_grs`, `status:"done"`, `stage:"मसुदा तयार"` (if it was
  "अभ्यास चालू"), `instruction:""`, `updated_at`, history += {note:"मसुदे तयार"}.
- Assets replaced by a new sync: delete the old asset ids (Artifact delete, `path` = id) after the case doc points at the new ones.
- Failure: `status:"failed"`, history note = one Marathi line why; continue with the next item.

## 4. Pending edits (`edits/<id>` = {case, target, para, message, attachments})
- Group by case. `tools/case_state.py load <case> <work>` (state from `cases/<case>/`); attachments: Artifact read `path` = asset_id.
- Apply only the asked change (INSTRUCTIONS §4.41 (इ)): `para` ids per tools/desk_sync.py docstring (position in spec.json);
  target package / attachments = enclosure or GR change → rebuild with `--package`.
- `save --note "सुधारणा: …"` → rebuild → LINT OK + verify ALL OK → desk_sync → upload → case update (outputs, paras,
  updated_at, history += {note:"सुधारणा केली"}).
- Each edit ← `{status:"done", reply:<one Marathi line: what changed, where>, done_at}`; not possible → `status:"failed"`,
  reply = why (one line).

## 5. End
- `git add cases/ && git commit -m "desk worker: <ids>" && git push` (only cases/ state; nothing else).
- `meta/worker` ← `{state:"idle", at:<now>, step:"", note:<one Marathi line: what was done>}`.
- If a usage limit stops the run, items keep their status; the next press continues. Set `meta/worker.state` "idle" first when possible.
