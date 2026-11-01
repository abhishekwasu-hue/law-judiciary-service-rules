#!/usr/bin/env bash
# usage: tools/run_headless.sh <PREFIX>   (run from repo root; needs ANTHROPIC_API_KEY)
set -u
P="$1"; OUT="cases/$P"; mkdir -p "$OUT"
FILE_NO=""; ORIG="$P.pdf"; MODE="study"; EXTRA=""; INSTR=""; PREV=""
if [ -f "inbox/$P.json" ]; then
  J(){ python3 -c "import json,sys;v=json.load(open('inbox/$P.json')).get('$1','');print('\n'.join(v) if isinstance(v,list) else (v or ''))"; }
  FILE_NO=$(J file_no); ORIG=$(J original_name); MODE=$(J mode); EXTRA=$(J extras); INSTR=$(J instructions); PREV=$(J previous)
  [ -z "$MODE" ] && MODE=study
fi
PROMPT="$(cat tools/HEADLESS_PROMPT.md)

PREFIX=$P
PROPOSAL_PDF=inbox/$P.pdf
OUTDIR=$OUT
FILE_NO=$FILE_NO
ORIGINAL_NAME=$ORIG
MODE=$MODE
EXTRA_DOCS:
$EXTRA
USER_INSTRUCTIONS:
$INSTR
PREVIOUS_OUTPUTS:
$PREV"
now(){ date -u +%FT%TZ; }
echo "{\"state\":\"running\",\"started\":\"$(now)\"}" > "$OUT/status.json"
if claude -p "$PROMPT" --dangerously-skip-permissions --max-turns 400; then
  grep -q '"done"' "$OUT/status.json" || echo "{\"state\":\"done\",\"finished\":\"$(now)\"}" > "$OUT/status.json"
else
  echo "{\"state\":\"failed\",\"finished\":\"$(now)\"}" > "$OUT/status.json"
fi
