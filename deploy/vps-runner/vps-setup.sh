#!/bin/bash
# प्रस्ताव कक्ष — self-hosted GitHub Actions runner on the VPS (docs/VPS_RUNNER.md). Run as root:
#   bash vps-setup.sh <TOKEN>   first install (TOKEN = GitHub → Settings → Actions → Runners → New self-hosted runner)
#   bash vps-setup.sh           rebuild / restart; the saved registration (Docker volume) is kept, no token needed
#   bash vps-setup.sh --remove  stop and delete the container, the image and the registration volume
# Touches nothing else on the host: installs docker.io only when Docker is missing; the runner lives only in the Docker
# container "vps-prastav" (no host paths, no Docker socket, --cpus 1.5 --memory 5g). The Dockerfile, entrypoint.sh and
# cleanup.sh below are identical copies of deploy/vps-runner/* (the repo is private, so nothing is downloaded from it;
# tests/test_vps_runner.py checks that the copies match).
set -euo pipefail
NAME=vps-prastav
IMAGE=prastav-runner:2.338.1
BASE=ghcr.io/actions/actions-runner:2.338.1
VOL=vps-prastav-state
say() { echo "== $*"; }

[ "$(id -u)" = 0 ] || { echo "हे script root म्हणून चालवा: sudo bash vps-setup.sh <TOKEN>"; exit 1; }

if [ "${1:-}" = --remove ]; then
  if command -v docker >/dev/null 2>&1; then
    if docker rm -f "$NAME" >/dev/null 2>&1; then say "container $NAME काढला"; else say "container $NAME आधीच नाही"; fi
    if docker rmi "$IMAGE" >/dev/null 2>&1; then say "image $IMAGE काढली"; fi
    docker rmi "$BASE" >/dev/null 2>&1 || true
    if docker volume rm "$VOL" >/dev/null 2>&1; then say "नोंदणी-volume $VOL काढला"; fi
  fi
  say "VPS वरील runner पूर्ण काढला. Docker स्वतः (व trading bot) यांना हात लावलेला नाही."
  say "GitHub मधूनही काढा: repo → Settings → Actions → Runners → vps-prastav → ⋯ → Remove (offline असल्यास Force remove)."
  say "Workflows पुन्हा GitHub वर: repo → Settings → Secrets and variables → Actions → Variables → RUNS_ON → Delete."
  exit 0
fi

TOKEN=${1:-}
case "$TOKEN" in -*) echo "अज्ञात पर्याय: $TOKEN (वापर: bash vps-setup.sh <TOKEN> | --remove)"; exit 1 ;; esac

if ! command -v docker >/dev/null 2>&1; then
  say "Docker नाही — docker.io install करत आहे (apt)"
  apt-get update -y && apt-get install -y docker.io
  systemctl enable --now docker
fi
systemctl is-active --quiet docker 2>/dev/null || systemctl start docker 2>/dev/null || true
docker info >/dev/null 2>&1 || { echo "Docker चालू नाही (docker info अयशस्वी) — थांबवले"; exit 1; }

if [ -z "$TOKEN" ] && ! docker volume inspect "$VOL" >/dev/null 2>&1; then
  echo "पहिल्या वेळी TOKEN हवा: bash vps-setup.sh <TOKEN> (GitHub → Settings → Actions → Runners → New self-hosted runner)"
  exit 1
fi

B=$(mktemp -d)
trap 'rm -rf "$B"' EXIT
cat > "$B/Dockerfile" <<'VPS_EOF'
# Self-hosted GitHub Actions runner for this repo (docs/VPS_RUNNER.md). Built and started by vps-setup.sh, which carries
# an identical copy of this file (heredoc) — change both together (tests/test_vps_runner.py checks they match).
# Base: official runner image 2.338.1 (ghcr.io, created 22.10.2026, Ubuntu 24.04), pinned by its index digest.
# The runner updates itself to newer releases at run time (GitHub requires current runners); the pin fixes the build.
FROM ghcr.io/actions/actions-runner:2.338.1@sha256:e275409999c37162649aa050ca573f03eab2eabcb3a1e7fcc47548de6b4f9690

USER root
# What the workflows install at run time (process-proposal.yml "Install tools" apt line, copied exactly:
# poppler-utils tesseract-ocr tesseract-ocr-mar libreoffice-writer fonts-freefont-ttf) plus the sandbox / hook tools.
# python3 brings the shared libraries (libffi, sqlite, readline) that setup-python's prebuilt Python 3.12 needs.
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends \
      poppler-utils tesseract-ocr tesseract-ocr-mar libreoffice-writer fonts-freefont-ttf \
      python3 python3-venv python3-pip acl jq curl git iptables util-linux procps unzip zip ca-certificates \
      sudo passwd diffutils findutils file xz-utils \
 && rm -rf /var/lib/apt/lists/*

# setup-python / setup-node install into the tool cache (same path as GitHub-hosted runners); kept across jobs.
# /home/runner: 750 as on GitHub-hosted runners (the base image makes it 777, which would let the sandbox user `engine`
# rename the runner's own files). /runner-state: the registration (named volume, see entrypoint.sh).
ENV RUNNER_TOOL_CACHE=/opt/hostedtoolcache \
    AGENT_TOOLSDIRECTORY=/opt/hostedtoolcache \
    ACTIONS_RUNNER_HOOK_JOB_STARTED=/opt/vps-runner/job-started.sh \
    ACTIONS_RUNNER_HOOK_JOB_COMPLETED=/opt/vps-runner/job-completed.sh
COPY entrypoint.sh cleanup.sh /opt/vps-runner/
RUN install -d -o runner -g runner -m 755 /opt/hostedtoolcache \
 && install -d -o runner -g runner -m 700 /runner-state \
 && chmod 750 /home/runner \
 && printf '#!/bin/bash\nexec /opt/vps-runner/cleanup.sh started\n' > /opt/vps-runner/job-started.sh \
 && printf '#!/bin/bash\nexec /opt/vps-runner/cleanup.sh completed\n' > /opt/vps-runner/job-completed.sh \
 && chown -R root:root /opt/vps-runner && chmod 755 /opt/vps-runner/*.sh

USER runner
WORKDIR /home/runner
ENTRYPOINT ["/opt/vps-runner/entrypoint.sh"]
VPS_EOF
cat > "$B/entrypoint.sh" <<'VPS_EOF'
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
VPS_EOF
cat > "$B/cleanup.sh" <<'VPS_EOF'
#!/bin/bash
# Wipes everything a job leaves behind on the self-hosted runner container (docs/VPS_RUNNER.md), so no proposal file,
# secret or `engine` user survives a job. Never fails (always exit 0): a cleanup problem must not fail the job.
#   started    runner hook ACTIONS_RUNNER_HOOK_JOB_STARTED (before the first step; _work is left alone)
#   completed  runner hook ACTIONS_RUNNER_HOOK_JOB_COMPLETED (after the last step)
#   boot       container start (entrypoint.sh): leftovers of a job cut off by a restart
#   pre        from a workflow step (process-proposal.yml first step): like `started`, but leaves _work alone
#              (the workspace is already checked out) and removes only the known job paths in /tmp
# Root-owned copy in the image (/opt/vps-runner); the repo copy is never executed.
MODE=${1:-completed}
if [ "$(id -u)" != 0 ]; then exec sudo -n "$0" "$MODE"; fi
set -u
log() { echo "vps-cleanup[$MODE]: $*"; }

# 1) every process of the sandbox user `engine` (scripts/engine/sandbox.sh), then the user itself
if id engine >/dev/null 2>&1; then
  for _ in $(seq 1 40); do
    pgrep -u engine >/dev/null 2>&1 || break
    pkill -KILL -u engine 2>/dev/null || true
    sleep 0.25
  done
  pgrep -a -u engine 2>/dev/null | sed 's/^/vps-cleanup: engine process survived: /' || true
fi

# 2) the sandbox mounts (/srv/engine read-only repo view + every bind mount below it)
for m in /srv/engine /srv/engine-rw; do
  if mountpoint -q "$m" 2>/dev/null || findmnt -rn -o TARGET 2>/dev/null | grep -q "^$m/"; then
    umount -R "$m" 2>/dev/null || umount -lR "$m" 2>/dev/null || log "umount $m failed"
  fi
done
findmnt -rn -o TARGET 2>/dev/null | grep -E '^/srv/engine(-rw)?(/|$)' | sort -r | while read -r m; do
  umount -l "$m" 2>/dev/null || log "umount $m failed"
done
if findmnt -rn -o TARGET 2>/dev/null | grep -qE '^/srv/engine(-rw)?(/|$)'; then
  log "a /srv/engine mount is still there: nothing below it is deleted"
else
  rm -rf /srv/engine /srv/engine-rw
fi

# 3) the job paths of the workflows (.github/workflows/*.yml) and the root-owned tool snapshots
rm -rf /tmp/case /tmp/work /tmp/out /tmp/old /tmp/precedent /tmp/runner-priv /tmp/engine-secrets /tmp/edit-work \
       /tmp/new.txt /tmp/batch_* /tmp/tmp.* \
       /opt/engine-tools /opt/engine-scripts /opt/engine-samples 2>/dev/null || true

# 4) files `engine` left anywhere else (it may write to /tmp, /var/tmp, /dev/shm), then the user and its home
if id engine >/dev/null 2>&1; then
  for fs in / /tmp /var/tmp /dev/shm; do
    X=(-not -path '/proc/*' -not -path '/srv/engine*' -not -path '/runner-state*')
    find "$fs" -xdev -user engine "${X[@]}" -delete 2>/dev/null || true
    find "$fs" -xdev -depth -user engine "${X[@]}" -exec rm -rf {} + 2>/dev/null || true
  done
  userdel -r -f engine 2>/dev/null || userdel -f engine 2>/dev/null || log "userdel engine failed"
  getent group engine >/dev/null 2>&1 && { groupdel engine 2>/dev/null || true; }
fi
rm -rf /home/engine 2>/dev/null || true

# 5) all temp dirs (not in `pre`: the job is already running); the .NET runner's own diagnostic sockets are kept
if [ "$MODE" != pre ]; then
  find /tmp -mindepth 1 -maxdepth 1 ! -name 'clr-debug-pipe-*' ! -name 'dotnet-diagnostic-*' ! -name '.dotnet*' \
       -exec rm -rf {} + 2>/dev/null || true
  find /var/tmp /dev/shm -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
fi

# 6) the runner's _work after a job (and at boot): the checkout dirs _work/<repo>/<repo> are emptied (kept as empty
#    dirs), _temp emptied; the runner's own dirs are kept (_actions, _tool, _PipelineMapping, _update). Not at `started`
#    (this job's dirs are set up already; actions/checkout cleans the workspace) and not in `pre`.
W=/home/runner/_work
if { [ "$MODE" = completed ] || [ "$MODE" = boot ]; } && [ -d "$W" ]; then
  for d in "$W"/* "$W"/.[!.]*; do
    [ -e "$d" ] || continue
    case "$(basename "$d")" in
      _actions|_tool|_PipelineMapping|_update) continue ;;
      _temp) depth=1 ;;
      *) depth=2 ;;
    esac
    if [ -d "$d" ] && [ ! -L "$d" ]; then find "$d" -mindepth "$depth" -delete 2>/dev/null || true
    else rm -f "$d"; fi
  done
fi
log "done"
exit 0
VPS_EOF
chmod 755 "$B/entrypoint.sh" "$B/cleanup.sh"

say "image तयार करत आहे ($IMAGE) — पहिल्या वेळी 5-10 मिनिटे लागू शकतात"
docker build --pull -t "$IMAGE" "$B"

if docker volume inspect "$VOL" >/dev/null 2>&1; then
  say "नोंदणी-volume $VOL आधीपासून आहे: त्यातील नोंदणी वापरली जाईल${TOKEN:+ (दिलेला TOKEN वापरला जाणार नाही)}"
else
  docker volume create "$VOL" >/dev/null
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true

ENVF="$B/runner.env"
( umask 077; if [ -n "$TOKEN" ]; then echo "RUNNER_TOKEN=$TOKEN"; fi > "$ENVF" )
docker run -d --name "$NAME" --hostname "$NAME" --restart unless-stopped --init \
  --cpus 1.5 --memory 5g --memory-swap 5g --pids-limit 4096 \
  --cap-add SYS_ADMIN --security-opt apparmor=unconfined \
  --log-opt max-size=10m --log-opt max-file=3 \
  -v "$VOL:/runner-state" --env-file "$ENVF" "$IMAGE" >/dev/null
rm -f "$ENVF"
say "container $NAME सुरू झाला; GitHub शी जोडणी तपासत आहे…"

for _ in $(seq 1 60); do
  if docker logs "$NAME" 2>&1 | grep -q "Listening for Jobs"; then
    say "यशस्वी: runner vps-prastav GitHub शी जोडला (Listening for Jobs)."
    say "GitHub → Settings → Actions → Runners येथे vps-prastav \"Idle\" दिसेल."
    say "पुढे: Variables मध्ये RUNS_ON = [\"self-hosted\",\"prastav\"] ठेवल्यावर सर्व workflows VPS वर चालतील."
    exit 0
  fi
  if ! docker ps -q -f "name=^${NAME}$" | grep -q .; then break; fi
  sleep 3
done
say "runner अजून जोडलेला दिसत नाही. शेवटच्या ओळी:"
docker logs "$NAME" --tail 30 2>&1 || true
say "TOKEN कालबाह्य (1 तास) झाला असल्यास: bash vps-setup.sh --remove ; नंतर नवीन TOKEN ने bash vps-setup.sh <TOKEN>"
exit 1
