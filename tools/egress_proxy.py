#!/usr/bin/env python3
"""egress_proxy.py — the only way out to the internet for the unix user `engine` when KV `engine_isolation` is "on"
(S-F1 (b), audit 05.11.2026; docs/ENGINE_ISOLATION.md). Stdlib only. Runs as the RUNNER user from the root-owned tool
snapshot (/opt/engine-tools); scripts/engine/egress.sh lets `engine` reach nothing but 127.0.0.1:<this port> and the
local model gateway, so every outbound request of `engine` (curl, Python urllib, Claude Code's own HTTPS_PROXY) goes
through here and only to the allowed hosts.

  python3 -I egress_proxy.py --port 3128 --allow gr.maharashtra.gov.in --allow archive.org --allow <worker host>
          [--log <file>] [--ports 80,443] [--allow-private]

* an allowed host = the host itself or any sub-domain of it (archive.org -> ia800000.us.archive.org, the download
  mirrors); names only, never an IP literal (unless --allow-private, for tests);
* HTTPS: `CONNECT host:443` -> tunnel (the TLS stays end-to-end; nothing is decrypted); plain HTTP: absolute-URI
  requests (`GET http://host/path HTTP/1.1`) are forwarded with `Connection: close`;
* ports: only --ports (default 80, 443); a host that resolves to a loopback / private / link-local / reserved address
  is refused (no way to the runner's own services or the cloud metadata address through an allowed name);
* everything else -> `403` and one log line "DENY <host>:<port>" (host names only, never a path or a body).
"""
import argparse, ipaddress, select, socket, socketserver, sys, threading, time

IDLE = 300          # seconds without traffic on a tunnel -> closed
HEAD_MAX = 65536    # request head limit


class State:
    allow = ()
    ports = (80, 443)
    private_ok = False
    log = None
    lock = threading.Lock()


def note(line):
    if not State.log:
        return
    with State.lock:
        try:
            with open(State.log, "a", encoding="utf-8") as f:
                f.write(time.strftime("%H:%M:%S ") + line + "\n")
        except OSError:
            pass


def host_allowed(host):
    h = (host or "").strip().lower().rstrip(".")
    if not h or len(h) > 253:
        return False
    try:
        ipaddress.ip_address(h.strip("[]"))
        return State.private_ok and h in State.allow   # IP literals only in tests
    except ValueError:
        pass
    return any(h == a or h.endswith("." + a) for a in State.allow)


def resolve(host, port):
    """-> a list of (family, address) of `host` that are public, or [] (refused)."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return []
    out = []
    for fam, _, _, _, sa in infos:
        ip = ipaddress.ip_address(sa[0].split("%")[0])
        if not State.private_ok and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                                     or ip.is_multicast or ip.is_unspecified):
            return []   # one bad address = refuse the name (no mixed answers)
        out.append((fam, sa))
    return out


def connect(host, port):
    addrs = resolve(host, port)
    if not addrs:
        return None
    for fam, sa in addrs:
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.settimeout(20)
        try:
            s.connect(sa)
            s.settimeout(None)
            return s
        except OSError:
            s.close()
    return None


def pipe(a, b):
    socks = [a, b]
    last = time.time()
    while time.time() - last < IDLE:
        r, _, x = select.select(socks, [], socks, 10)
        if x:
            return
        for s in r:
            try:
                data = s.recv(65536)
            except OSError:
                return
            if not data:
                return
            (b if s is a else a).sendall(data)
            last = time.time()


def split_hostport(hp, default):
    hp = hp.strip()
    if hp.startswith("["):
        h, _, rest = hp[1:].partition("]")
        return h, int(rest[1:]) if rest.startswith(":") and rest[1:].isdigit() else default
    h, sep, p = hp.rpartition(":")
    if sep and p.isdigit():
        return h, int(p)
    return hp, default


class Handler(socketserver.BaseRequestHandler):
    def deny(self, host, port, why="DENY"):
        note(f"{why} {host}:{port}")
        try:
            self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        except OSError:
            pass

    def handle(self):
        c = self.request
        c.settimeout(30)
        head = b""
        try:
            while b"\r\n\r\n" not in head and len(head) < HEAD_MAX:
                d = c.recv(4096)
                if not d:
                    return
                head += d
        except OSError:
            return
        if b"\r\n\r\n" not in head:
            return self.deny("?", 0, "BAD")
        hdr, _, rest = head.partition(b"\r\n\r\n")
        lines = hdr.decode("latin-1").split("\r\n")
        parts = lines[0].split(" ")
        if len(parts) != 3:
            return self.deny("?", 0, "BAD")
        method, target, ver = parts
        c.settimeout(None)
        if method.upper() == "CONNECT":
            host, port = split_hostport(target, 443)
            if port not in State.ports or not host_allowed(host):
                return self.deny(host, port)
            up = connect(host, port)
            if up is None:
                return self.deny(host, port, "NORESOLVE")
            note(f"CONNECT {host}:{port}")
            try:
                c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                if rest:
                    up.sendall(rest)
                pipe(c, up)
            finally:
                up.close()
            return
        # plain HTTP proxy request: absolute URI only
        if not target.lower().startswith("http://"):
            return self.deny("?", 0, "BAD")
        hp, _, path = target[7:].partition("/")
        host, port = split_hostport(hp, 80)
        if port not in State.ports or not host_allowed(host):
            return self.deny(host, port)
        up = connect(host, port)
        if up is None:
            return self.deny(host, port, "NORESOLVE")
        note(f"HTTP {host}:{port}")
        keep = [l for l in lines[1:] if l and not l.lower().startswith(("proxy-", "connection:", "keep-alive:"))]
        out = "\r\n".join([f"{method} /{path} {ver}"] + keep + ["Connection: close", "", ""]).encode("latin-1")
        try:
            up.sendall(out + rest)
            pipe(c, up)
        finally:
            up.close()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=3128)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--ports", default="80,443")
    ap.add_argument("--log")
    ap.add_argument("--allow-private", action="store_true")
    a = ap.parse_args(argv)
    State.allow = tuple(x.strip().lower().rstrip(".") for x in a.allow if x.strip())
    State.ports = tuple(int(p) for p in a.ports.split(",") if p.strip().isdigit())
    State.private_ok = a.allow_private
    State.log = a.log
    if not State.allow:
        print("egress_proxy: no --allow host", file=sys.stderr)
        return 2
    srv = Server((a.host, a.port), Handler)
    note("START " + " ".join(State.allow))
    print(f"egress proxy on {a.host}:{srv.server_address[1]} ({len(State.allow)} allowed hosts)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
