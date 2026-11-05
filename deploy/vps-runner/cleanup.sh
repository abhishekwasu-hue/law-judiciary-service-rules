#!/bin/bash
# Wipes everything a job leaves behind on the self-hosted runner container (docs/VPS_RUNNER.md), so no proposal file,
# secret or `engine` user survives a job. Never fails (always exit 0): a cleanup problem must not fail the job.
#   started    runner hook ACTIONS_RUNNER_HOOK_JOB_STARTED (before the first step; this job's _work/_temp is kept)
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

# 6) the runner's _work: workspace checkouts (and, after a job, _temp) emptied; the runner's own dirs are kept
#    (_actions = downloaded actions of this job, _tool = tool cache fallback, _PipelineMapping, _update)
W=/home/runner/_work
if [ "$MODE" != pre ] && [ -d "$W" ]; then
  for d in "$W"/* "$W"/.[!.]*; do
    [ -e "$d" ] || continue
    case "$(basename "$d")" in
      _actions|_tool|_PipelineMapping|_update) continue ;;
      _temp) [ "$MODE" = started ] && continue ;;
    esac
    if [ -d "$d" ] && [ ! -L "$d" ]; then find "$d" -mindepth 1 -delete 2>/dev/null || rm -rf "${d:?}"/* "${d:?}"/.[!.]* 2>/dev/null
    else rm -f "$d"; fi
  done
fi
log "done"
exit 0
