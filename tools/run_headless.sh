#!/usr/bin/env bash
# usage: tools/run_headless.sh <PREFIX>   (run from repo root; needs ANTHROPIC_API_KEY)
set -u
P="$1"; OUT="cases/$P"; mkdir -p "$OUT"
FILE_NO=""
[ -f "inbox/$P.json" ] && FILE_NO=$(python3 -c "import json;print(json.load(open('inbox/$P.json')).get('file_no',''))")
PROMPT="$(cat tools/HEADLESS_PROMPT.md)

PREFIX=$P
PROPOSAL_PDF=inbox/$P.pdf
OUTDIR=$OUT
FILE_NO=$FILE_NO"
now(){ date -u +%FT%TZ; }
echo "{\"state\":\"running\",\"started\":\"$(now)\"}" > "$OUT/status.json"
if claude -p "$PROMPT" --dangerously-skip-permissions --max-turns 400; then
  grep -q '"done"' "$OUT/status.json" || echo "{\"state\":\"done\",\"finished\":\"$(now)\"}" > "$OUT/status.json"
else
  echo "{\"state\":\"failed\",\"finished\":\"$(now)\"}" > "$OUT/status.json"
fi
