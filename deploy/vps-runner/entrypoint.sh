#!/bin/bash
# Container entrypoint of the self-hosted runner (docs/VPS_RUNNER.md). Runs as `runner`.
# First start: registers the runner with RUNNER_TOKEN (GitHub → Settings → Actions → Runners → New self-hosted runner)
# and saves the registration in /runner-state (named Docker volume), so later restarts need no new token.
set -euo pipefail
REPO_URL=https://github.com/abhishekwasu-hue/law-judiciary-service-rules
NAME=vps-prastav
LABELS=prastav
STATE=/runner-state
FILES=(.runner .credentials .credentials_rsaparams .env .path)
cd /home/runner

# leftovers of a job that was cut off (container restart / VPS reboot) go before anything else
sudo /opt/vps-runner/cleanup.sh boot || true

if [ -s "$STATE/.runner" ] && [ -s "$STATE/.credentials" ]; then
  for f in "${FILES[@]}"; do [ -e "$STATE/$f" ] && cp -p "$STATE/$f" "./$f"; done
  echo "runner: saved registration found ($NAME)"
else
  if [ -z "${RUNNER_TOKEN:-}" ]; then
    echo "runner: no registration yet and no RUNNER_TOKEN — run vps-setup.sh <TOKEN> (docs/VPS_RUNNER.md)" >&2
    sleep 60; exit 1
  fi
  ./config.sh --unattended --url "$REPO_URL" --token "$RUNNER_TOKEN" --name "$NAME" --labels "$LABELS" \
    --work _work --replace
  for f in "${FILES[@]}"; do [ -e "./$f" ] && cp -p "./$f" "$STATE/$f"; done
  chmod 600 "$STATE"/.credentials* 2>/dev/null || true
  echo "runner: registered as $NAME (labels: self-hosted, $LABELS)"
fi
chmod 600 .credentials .credentials_rsaparams 2>/dev/null || true
# the registration token is single use; jobs never see it
unset RUNNER_TOKEN
exec ./run.sh
