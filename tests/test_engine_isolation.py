"""S-F1 / S-F2 engine isolation (docs/ENGINE_ISOLATION.md; KV engine_isolation "on"): the workflow pieces are gated by
the flag, the config steps write the same secrets file as before when it is off (run against the HEAD version of the
step when git has one), tools/egress_proxy.py lets through only the allowed hosts, and sandbox / egress scripts parse."""
import json, os, re, shutil, socket, subprocess, sys, tempfile, threading, time, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def step_of(text, prefix):
    doc = yaml.safe_load(text)
    for job in doc["jobs"].values():
        for st in job.get("steps", []):
            if str(st.get("name", "")).startswith(prefix):
                return st["run"]
    raise KeyError(prefix)


BEFORE = "1741eeb^"   # the last commit before the isolation change (history may be shallow: then only the fixed text)


def head_text(rel, rev="HEAD"):
    try:
        r = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


FAKE_CURL = """#!/usr/bin/env bash
# test double: writes $CFG_JSON to the -o file, prints the HTTP code
out=""
while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift 2 ;; *) shift ;; esac; done
[ -n "$out" ] && cp "$CFG_JSON" "$out"
printf 200
"""


@unittest.skipIf(yaml is None or not shutil.which("bash") or not shutil.which("jq"), "needs pyyaml, bash, jq")
class ConfigStep(unittest.TestCase):
    """The 'Get run config' steps run for real (fake curl): off -> the old secrets file; on -> DB token, no service key."""

    def run_step(self, script, cfg):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "bin"))
        fc = os.path.join(d, "bin", "curl")
        open(fc, "w").write(FAKE_CURL); os.chmod(fc, 0o755)
        json.dump(cfg, open(os.path.join(d, "cfg.in.json"), "w"))
        json.dump({"client_payload": {"case_id": "7", "run_id": "11", "token": "tok", "worker": "https://w.example"}},
                  open(os.path.join(d, "event.json"), "w"))
        env = dict(os.environ, PATH=os.path.join(d, "bin") + os.pathsep + os.environ["PATH"], CFG_JSON=os.path.join(d, "cfg.in.json"),
                   GITHUB_EVENT_PATH=os.path.join(d, "event.json"), GITHUB_ENV=os.path.join(d, "github_env"),
                   RP=os.path.join(d, "rp"), ENGINE_SECRETS=os.path.join(d, "sec", "secrets.env"), T=os.path.join(ROOT, "tools"))
        os.makedirs(env["RP"])
        r = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, text=True)
        rd = lambda p: open(p).read() if os.path.exists(p) else None
        out = (r.returncode, rd(env["ENGINE_SECRETS"]), rd(env["GITHUB_ENV"]))
        shutil.rmtree(d, ignore_errors=True)
        return out

    BASE = {"anthropic_api_key": "sk-ant-x", "supabase_url": "https://sb.example", "model": "claude-opus-5-5"}

    def check_wf(self, name, prefix):
        rel = f".github/workflows/{name}"
        now = step_of(open(os.path.join(ROOT, rel), encoding="utf-8").read(), prefix)
        off = dict(self.BASE, supabase_service_key="svc-key")
        rc, sec, genv = self.run_step(now, off)
        self.assertEqual(rc, 0, name)
        self.assertIn("SUPABASE_SERVICE_KEY=svc-key", sec)
        self.assertNotIn("ENGINE_DB_TOKEN", sec)
        self.assertNotIn("ENGINE_ISOLATION", genv)
        # off = byte-identical to the step before this change (verified against commit 1741eeb^ when it was written)
        self.assertEqual(sec, "ANTHROPIC_API_KEY=sk-ant-x\nSUPABASE_URL=https://sb.example\nSUPABASE_SERVICE_KEY=svc-key\n", name)
        old = head_text(rel, BEFORE)
        if old and "db_token" not in old:
            rc0, sec0, genv0 = self.run_step(step_of(old, prefix), off)
            self.assertEqual((rc0, sec0, genv0), (rc, sec, genv), f"{name}: off must equal the old step")
        on = dict(self.BASE, engine_isolation="on", db_token="d" * 48)
        rc, sec, genv = self.run_step(now, on)
        self.assertEqual(rc, 0, name)
        self.assertNotIn("SUPABASE_SERVICE_KEY", sec)
        self.assertIn("ENGINE_DB_TOKEN=" + "d" * 48, sec)
        if name == "process-proposal.yml":   # the Claude step's gateway / egress block reads it (no engine user in edits)
            self.assertIn("ENGINE_ISOLATION=on", genv)
        # on without a DB token (old Worker / broken KV) -> refused, no secrets file
        rc, sec, _ = self.run_step(now, dict(self.BASE, engine_isolation="on"))
        self.assertNotEqual(rc, 0)
        self.assertIsNone(sec)

    def test_process_proposal_config(self):
        self.check_wf("process-proposal.yml", "Get run config")

    def test_edit_drafts_config(self):
        self.check_wf("edit-drafts.yml", "Get run config")


@unittest.skipIf(yaml is None, "pyyaml not installed")
class ClaudeStepStatic(unittest.TestCase):
    def setUp(self):
        self.main = step_of(open(os.path.join(WF, "process-proposal.yml"), encoding="utf-8").read(), "Process the proposal")

    def test_gated_and_off_path_kept(self):
        m = self.main
        self.assertIn('AUTH=(ANTHROPIC_API_KEY="$AK")', m, "off: the engine still gets the key as before")
        i = m.index('if [ "${ENGINE_ISOLATION:-}" = on ] && [ -z "$SKIP_MAIN" ]; then')
        block = m[i:m.index("# ---- time for the main run")]
        for s in ("ERUN+=(", "bash \"$EG\" up", "egress_proxy.py", "--port 4001", "/anthropic", "iso_stop", "SKIP_MAIN=1"):
            self.assertIn(s, block, s)
        self.assertNotIn("ERUN+=(", m[:i] + m[m.index("# ---- time for the main run"):], "ERUN extended only when on")
        self.assertIn('HIDE=""; [ "${ENGINE_ISOLATION:-}" = on ] && HIDE=1', m)
        self.assertIn('SANDBOX_HIDE_RAW="$HIDE" "$SB" up', m)
        self.assertIn('if [ "${ENGINE_ISOLATION:-}" = on ]; then iso_stop; fi', m)
        # the gateway: own master key, bound to loopback, real key only in its own env
        self.assertRegex(block, r'litellm" --config "\$RP/agw/litellm\.yaml" --host 127\.0\.0\.1 --port 4001')
        self.assertIn('ANTHROPIC_AUTH_TOKEN="$AMK"', block)
        self.assertNotRegex(block, r"ERUN\+=\([^)]*ANTHROPIC_API_KEY")
        # allowlist = Worker host, GR site, archive.org
        self.assertRegex(block, r'--allow "\$WH" --allow gr\.maharashtra\.gov\.in --allow archive\.org')
        self.assertIn("bash \"$EG\" up 4000,4001,3128", block)

    def test_scripts_parse(self):
        for p in ("scripts/engine/egress.sh", "scripts/engine/sandbox.sh"):
            r = subprocess.run(["bash", "-n", os.path.join(ROOT, p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, p + r.stderr)
        sb = open(os.path.join(ROOT, "scripts/engine/sandbox.sh"), encoding="utf-8").read()
        self.assertIn('if [ "${SANDBOX_HIDE_RAW:-}" = 1 ]; then hide_raw "$mnt" "$rw"; fi', sb)
        eg = open(os.path.join(ROOT, "scripts/engine/egress.sh"), encoding="utf-8").read()
        self.assertIn("-m owner --uid-owner engine", eg)
        self.assertIn("-o lo -d 127.0.0.1/32 -p tcp -m multiport --dports", eg)


class Echo(BaseHTTPRequestHandler):
    def do_GET(self):
        b = b"hello " + self.path.encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a): pass


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class EgressProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import egress_proxy as EP
        cls.EP = EP
        cls.up = ThreadingHTTPServer(("127.0.0.1", 0), Echo)
        threading.Thread(target=cls.up.serve_forever, daemon=True).start()
        cls.upport = cls.up.server_address[1]
        cls.port = free_port()
        cls.log = tempfile.mktemp()
        cls.proc = subprocess.Popen([sys.executable, "-I", os.path.join(ROOT, "tools", "egress_proxy.py"), "--port", str(cls.port),
                                     "--allow", "127.0.0.1", "--allow-private", "--ports", f"{cls.upport}", "--log", cls.log],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.2).close(); break
            except OSError:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.proc.kill(); cls.proc.wait(); cls.up.shutdown()

    def raw(self, data):
        s = socket.create_connection(("127.0.0.1", self.port), 5)
        s.sendall(data)
        out = b""
        s.settimeout(5)
        try:
            while True:
                d = s.recv(4096)
                if not d: break
                out += d
                if b"hello" in out or b"403" in out[:20]: break
        except socket.timeout:
            pass
        return s, out

    def test_connect_allowed_tunnel(self):
        s, out = self.raw(f"CONNECT 127.0.0.1:{self.upport} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        self.assertTrue(out.startswith(b"HTTP/1.1 200"), out)
        s.sendall(b"GET /t HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        got = b""
        while b"hello /t" not in got:
            d = s.recv(4096)
            if not d: break
            got += d
        s.close()
        self.assertIn(b"hello /t", got)

    def test_plain_http_allowed(self):
        s, out = self.raw(f"GET http://127.0.0.1:{self.upport}/p?q=1 HTTP/1.1\r\nHost: 127.0.0.1\r\nProxy-Authorization: x\r\n\r\n".encode())
        s.close()
        self.assertIn(b"hello /p?q=1", out)

    def test_denied(self):
        for req in (f"CONNECT example.com:{self.upport} HTTP/1.1\r\n\r\n", "CONNECT 127.0.0.1:22 HTTP/1.1\r\n\r\n",
                    "GET http://example.com/ HTTP/1.1\r\n\r\n", "GET /relative HTTP/1.1\r\n\r\n"):
            s, out = self.raw(req.encode()); s.close()
            self.assertTrue(out.startswith(b"HTTP/1.1 403"), (req, out))
        self.assertIn("DENY example.com", open(self.log, encoding="utf-8").read())

    def test_host_rules(self):
        EP = self.EP
        EP.State.allow, EP.State.private_ok = ("archive.org", "gr.maharashtra.gov.in"), False
        self.assertTrue(EP.host_allowed("archive.org"))
        self.assertTrue(EP.host_allowed("ia800300.us.archive.org"))
        self.assertTrue(EP.host_allowed("GR.Maharashtra.gov.in."))
        self.assertFalse(EP.host_allowed("evilarchive.org"))
        self.assertFalse(EP.host_allowed("archive.org.evil.com"))
        self.assertFalse(EP.host_allowed("1.2.3.4"))
        self.assertFalse(EP.host_allowed(""))
        self.assertEqual(EP.resolve("127.0.0.1", 443), [], "loopback refused without --allow-private")


if __name__ == "__main__":
    unittest.main()
