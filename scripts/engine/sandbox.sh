#!/usr/bin/env bash
# H1 sandbox for the App B engine (.github/workflows/process-proposal.yml; audit A2 CRITICAL, 02.11.2026).
# The Claude step runs as the unix user `engine` (untrusted PDFs, Bash, internet). The runner user later runs code with
# the secrets file, so `engine` must never be able to change code/config the runner executes:
#   up    <workspace> <mount> <rwdir>   create `engine`; bind-mount the repo READ-ONLY at <mount>; give `engine` writable
#                                       COPIES of the only paths it may write (pdf/gr/, tools/gr-request*.txt) in <rwdir>,
#                                       bind-mounted over those paths inside <mount>. The workspace itself is never
#                                       chowned or writable for `engine`.
#   down  <workspace> <mount> <rwdir>   kill every `engine` process (SIGKILL), unmount (fails loudly when busy), then copy
#                                       back from <rwdir> only regular files that pass the checks (GR PDFs named
#                                       <16-20 digits>.pdf with a %PDF header, INDEX.tsv, the request files). Idempotent.
#   check <workspace>                   `git status`: any change outside the allowed paths is printed ("VIOLATION <path>")
#                                       and restored (git checkout HEAD + git clean, allowed paths excluded); exit 3 then.
#   scrub <dir>...                      delete symlinks, hard-linked files and special files (fifo/socket/device) that
#                                       `engine` left in its output dirs, before the runner chowns/reads them.
# Run this script only from the root-owned snapshot (/opt/engine-scripts), never from the workspace.
set -euo pipefail

ALLOWED_DIR="pdf/gr"
ALLOWED_FILES=("tools/gr-request.txt" "tools/gr-request-done.txt")
MAX_BYTES=$((60 * 1024 * 1024))
GIT=(git -c core.hooksPath=/dev/null -c core.fsmonitor= -c safe.directory='*')

die() { echo "sandbox: $*" >&2; exit 2; }

kill_engine() {
  id engine >/dev/null 2>&1 || return 0
  sudo pkill -KILL -u engine 2>/dev/null || true
  for _ in $(seq 1 40); do
    pgrep -u engine >/dev/null 2>&1 || return 0
    sudo pkill -KILL -u engine 2>/dev/null || true
    sleep 0.25
  done
  pgrep -a -u engine >&2 || true
  die "engine processes survived SIGKILL"
}

cmd_up() {
  local ws=$1 mnt=$2 rw=$3
  [ -d "$ws/.git" ] || die "no git workspace: $ws"
  id engine >/dev/null 2>&1 || sudo useradd -m -s /bin/bash engine
  if mountpoint -q "$mnt" 2>/dev/null; then die "$mnt is already mounted"; fi
  sudo mkdir -p "$mnt"
  sudo mount --bind "$ws" "$mnt"
  sudo mount -o remount,ro,bind "$mnt"
  # writable copies (engine-owned) of the allowed paths only
  sudo rm -rf "$rw"; sudo mkdir -p "$rw/pdf-gr" "$rw/files"; sudo chmod 755 "$rw"
  mkdir -p "$ws/$ALLOWED_DIR"
  sudo cp -a "$ws/$ALLOWED_DIR/." "$rw/pdf-gr/"
  local f n
  for f in "${ALLOWED_FILES[@]}"; do
    n=$(basename "$f")
    if [ ! -e "$ws/$f" ]; then
      # a bind mount needs an existing target; an empty one we created is removed again by `down` if still empty
      : > "$ws/$f"; echo "$f" | sudo tee -a "$rw/created.list" >/dev/null
    fi
    sudo cp "$ws/$f" "$rw/files/$n"
  done
  sudo chown -R engine:engine "$rw/pdf-gr" "$rw/files"
  sudo mount --bind "$rw/pdf-gr" "$mnt/$ALLOWED_DIR"
  for f in "${ALLOWED_FILES[@]}"; do
    sudo mount --bind "$rw/files/$(basename "$f")" "$mnt/$f"
  done
  # self-test: the repo is read-only for `engine`, the allowed paths are writable
  if sudo -u engine test -w "$mnt/tools" || sudo -u engine test -w "$mnt/.git" || sudo -u engine test -w "$mnt"; then
    die "repo mount is writable for engine"
  fi
  sudo -u engine test -w "$mnt/$ALLOWED_DIR" || die "$ALLOWED_DIR is not writable for engine"
  if sudo -u engine touch "$mnt/tools/.sandbox-probe" 2>/dev/null; then die "engine could write into tools/"; fi
  echo "sandbox up: $mnt (ro) + writable $ALLOWED_DIR ${ALLOWED_FILES[*]}"
}

copy_file() {  # copy_file <src> <dst>: engine-owned regular file -> runner-owned 644 (sudo: engine may chmod 600)
  sudo install -o "$(id -u)" -g "$(id -g)" -m 644 "$1" "$2"
}

cmd_down() {
  local ws=$1 mnt=$2 rw=$3
  kill_engine
  if mountpoint -q "$mnt" 2>/dev/null; then
    if ! sudo umount -R "$mnt"; then
      for p in /proc/[0-9]*; do   # processes whose cwd / root is inside the mount
        case "$(sudo readlink "$p/cwd" 2>/dev/null)$(printf '\n')$(sudo readlink "$p/root" 2>/dev/null)" in
          *"$mnt"*) echo "busy: pid ${p#/proc/} $(tr '\0' ' ' < "$p/cmdline" 2>/dev/null | head -c 120)" >&2 ;;
        esac
      done
      die "umount $mnt failed (busy)"
    fi
  fi
  [ -d "$rw" ] || { echo "sandbox down: nothing to copy back"; return 0; }
  local p n sz f
  while IFS= read -r -d '' p; do
    n=$(basename "$p")
    if [ -L "$p" ] || [ ! -f "$p" ]; then echo "sandbox: ignored (not a regular file): $ALLOWED_DIR/$n"; continue; fi
    if ! [[ "$n" =~ ^([0-9]{16,20}\.pdf|INDEX\.tsv)$ ]]; then echo "sandbox: ignored (name): $ALLOWED_DIR/$n"; continue; fi
    sz=$(sudo stat -c %s "$p")
    if [ "$sz" -gt "$MAX_BYTES" ]; then echo "sandbox: ignored (size $sz): $ALLOWED_DIR/$n"; continue; fi
    if [[ "$n" == *.pdf ]] && [ "$(sudo head -c 4 "$p")" != "%PDF" ]; then echo "sandbox: ignored (not a PDF): $ALLOWED_DIR/$n"; continue; fi
    if ! sudo cmp -s "$p" "$ws/$ALLOWED_DIR/$n"; then copy_file "$p" "$ws/$ALLOWED_DIR/$n"; echo "sandbox: copied back $ALLOWED_DIR/$n"; fi
  done < <(sudo find "$rw/pdf-gr" -mindepth 1 -maxdepth 1 -print0)
  for f in "${ALLOWED_FILES[@]}"; do
    p="$rw/files/$(basename "$f")"
    if sudo test -f "$p" && ! sudo test -L "$p" && [ "$(sudo stat -c %s "$p")" -le "$MAX_BYTES" ]; then
      sudo cmp -s "$p" "$ws/$f" || { copy_file "$p" "$ws/$f"; echo "sandbox: copied back $f"; }
    fi
    if sudo test -f "$rw/created.list" && sudo grep -qxF "$f" "$rw/created.list" && [ ! -s "$ws/$f" ]; then rm -f "$ws/$f"; fi
  done
  sudo rm -rf "$rw"
  echo "sandbox down: ok"
}

allowed() {
  local p=$1 f
  [[ "$p" == "$ALLOWED_DIR/"* ]] && return 0
  for f in "${ALLOWED_FILES[@]}"; do [ "$p" = "$f" ] && return 0; done
  return 1
}

cmd_check() {
  local ws=$1 rec p bad=()
  while IFS= read -r -d '' rec; do
    p=${rec:3}
    allowed "$p" || bad+=("$p")
  done < <("${GIT[@]}" -C "$ws" status --porcelain=v1 -z --no-renames --untracked-files=all)
  [ ${#bad[@]} -eq 0 ] && { echo "sandbox check: clean (changes only under allowed paths)"; return 0; }
  for p in "${bad[@]}"; do echo "VIOLATION $p"; done
  local ex=(":(exclude)$ALLOWED_DIR")
  for p in "${ALLOWED_FILES[@]}"; do ex+=(":(exclude)$p"); done
  "${GIT[@]}" -C "$ws" checkout -q HEAD -- . "${ex[@]}"
  "${GIT[@]}" -C "$ws" clean -q -fd -- . "${ex[@]}"
  return 3
}

cmd_scrub() {
  local d
  for d in "$@"; do
    [ -d "$d" ] || continue
    sudo find "$d" -mindepth 1 \( -type l -o -type p -o -type s -o -type b -o -type c -o \( -type f -links +1 \) \) -print -delete \
      | sed 's/^/sandbox scrub: removed /' || true
  done
}

case "${1:-}" in
  up)    [ $# -eq 4 ] || die "usage: up <workspace> <mount> <rwdir>"; cmd_up "$2" "$3" "$4" ;;
  down)  [ $# -eq 4 ] || die "usage: down <workspace> <mount> <rwdir>"; cmd_down "$2" "$3" "$4" ;;
  check) [ $# -eq 2 ] || die "usage: check <workspace>"; cmd_check "$2" ;;
  scrub) shift; cmd_scrub "$@" ;;
  *) die "usage: $0 up|down|check|scrub ..." ;;
esac
