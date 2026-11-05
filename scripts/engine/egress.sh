#!/usr/bin/env bash
# S-F1 (b) (audit 05.11.2026; docs/ENGINE_ISOLATION.md): outbound network of the unix user `engine` — ONLY when KV
# engine_isolation = "on" (.github/workflows/process-proposal.yml). iptables owner match: every packet a process of
# `engine` sends is dropped (REJECT) unless it goes to 127.0.0.1 on one of the given TCP ports (the local model gateway
# and tools/egress_proxy.py, both run by the runner user). No DNS either (the proxy resolves names), so nothing leaves
# through DNS queries. IPv6: everything of `engine` is rejected.
#   up    <port>[,<port>...]   install the rules (idempotent: old rules of this script are removed first)
#   test  <proxy port> <allowed https url>   self-test as `engine`: direct internet must fail and a host outside the
#                              allowlist must get 403 from the proxy (exit 4 on such a hole); DNS that still resolves
#                              (systemd-resolved over its local socket, not IP) prints "WARN DNS" (not fatal); the
#                              allowed URL is only reported (the site may be down)
# DNS: `up` also denies `engine` the systemd-resolved / D-Bus system sockets by ACL when they exist (best effort;
# `down` removes the ACL entries).
#   down                       remove the rules
# Run this script only from the root-owned snapshot (/opt/engine-scripts), never from the workspace.
set -euo pipefail

C4=ENGINE_OUT
C6=ENGINE_OUT6
SOCKETS=(/run/systemd/resolve/io.systemd.Resolve /run/systemd/resolve/io.systemd.Resolve.Monitor /run/dbus/system_bus_socket)
die() { echo "egress: $*" >&2; exit 2; }

cmd_down() {
  while sudo iptables -D OUTPUT -m owner --uid-owner engine -j "$C4" 2>/dev/null; do :; done
  while sudo ip6tables -D OUTPUT -m owner --uid-owner engine -j "$C6" 2>/dev/null; do :; done
  sudo iptables -F "$C4" 2>/dev/null && sudo iptables -X "$C4" 2>/dev/null || true
  sudo ip6tables -F "$C6" 2>/dev/null && sudo ip6tables -X "$C6" 2>/dev/null || true
  local s
  for s in "${SOCKETS[@]}"; do [ -e "$s" ] && sudo setfacl -x u:engine "$s" 2>/dev/null || true; done
  echo "egress down"
}

cmd_up() {
  local ports=$1
  [[ "$ports" =~ ^[0-9]{2,5}(,[0-9]{2,5}){0,7}$ ]] || die "bad port list: $ports"
  id engine >/dev/null 2>&1 || die "no user engine"
  cmd_down >/dev/null
  sudo iptables -N "$C4"
  sudo iptables -A "$C4" -o lo -d 127.0.0.1/32 -p tcp -m multiport --dports "$ports" -j ACCEPT
  sudo iptables -A "$C4" -p tcp -j REJECT --reject-with tcp-reset
  sudo iptables -A "$C4" -j REJECT
  sudo iptables -I OUTPUT 1 -m owner --uid-owner engine -j "$C4"
  if command -v ip6tables >/dev/null 2>&1; then
    sudo ip6tables -N "$C6"
    sudo ip6tables -A "$C6" -j REJECT
    sudo ip6tables -I OUTPUT 1 -m owner --uid-owner engine -j "$C6"
  fi
  local s
  for s in "${SOCKETS[@]}"; do
    if [ -e "$s" ] && command -v setfacl >/dev/null 2>&1; then sudo setfacl -m u:engine:--- "$s" 2>/dev/null || true; fi
  done
  echo "egress up: engine -> 127.0.0.1:{$ports} only"
}

cmd_test() {
  local pp=$1 url=$2 hole=0
  # 1) direct connection to a public address (no proxy): must fail
  if sudo -u engine env -i PATH="$PATH" curl -s -o /dev/null --noproxy '*' --max-time 8 https://1.1.1.1/ 2>/dev/null; then
    echo "egress test: HOLE direct internet reachable"; hole=1
  else echo "egress test: ok direct internet blocked"; fi
  # 2) DNS from `engine`: should fail (no resolver reachable); a local-socket resolver is reported, not fatal
  if sudo -u engine env -i PATH="$PATH" timeout 10 getent hosts example.com >/dev/null 2>&1; then
    echo "egress test: WARN DNS still resolves for engine"
  else echo "egress test: ok DNS blocked"; fi
  # 3) a host outside the allowlist through the proxy: 403
  local code
  code=$(sudo -u engine env -i PATH="$PATH" curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
         -x "http://127.0.0.1:$pp" https://example.com/ 2>/dev/null || true)
  if [ "$code" = "200" ]; then echo "egress test: HOLE proxy let example.com through"; hole=1
  else echo "egress test: ok proxy refused example.com (${code:-none})"; fi
  # 4) an allowed host through the proxy (information only)
  code=$(sudo -u engine env -i PATH="$PATH" curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
         -x "http://127.0.0.1:$pp" "$url" 2>/dev/null || true)
  echo "egress test: allowed host answered HTTP ${code:-none}"
  [ "$hole" = 0 ] || return 4
}

case "${1:-}" in
  up)   [ $# -eq 2 ] || die "usage: up <ports>"; cmd_up "$2" ;;
  test) [ $# -eq 3 ] || die "usage: test <proxy port> <url>"; cmd_test "$2" "$3" ;;
  down) cmd_down ;;
  *) die "usage: $0 up|test|down ..." ;;
esac
