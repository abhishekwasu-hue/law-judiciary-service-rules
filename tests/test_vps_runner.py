"""Static checks of the self-hosted VPS runner (deploy/vps-runner, docs/VPS_RUNNER.md, 05.11.2026): the setup script
carries identical copies of the Dockerfile / entrypoint / cleanup, the container stays limited (no host paths, no Docker
socket, no --privileged, no NET_ADMIN), and the cleanup hook removes every job path the workflows use."""
import os, re, shutil, subprocess, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "deploy", "vps-runner")
WF = os.path.join(ROOT, ".github", "workflows")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class VpsRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.setup = read(D, "vps-setup.sh")
        cls.docker = read(D, "Dockerfile")
        cls.cleanup = read(D, "cleanup.sh")
        cls.entry = read(D, "entrypoint.sh")

    def test_heredoc_copies_identical(self):
        for name in ("Dockerfile", "entrypoint.sh", "cleanup.sh"):
            m = re.search(r"cat > \"\$B/%s\" <<'VPS_EOF'\n(.*?)\nVPS_EOF\n" % re.escape(name), self.setup, re.S)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1) + "\n", read(D, name), f"vps-setup.sh copy of {name} differs")

    def test_bash_syntax(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("no bash")
        for name in ("vps-setup.sh", "entrypoint.sh", "cleanup.sh"):
            r = subprocess.run([bash, "-n", os.path.join(D, name)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{name}: {r.stderr}")

    def test_base_image_pinned(self):
        m = re.search(r"^FROM ghcr\.io/actions/actions-runner:(\d+\.\d+\.\d+)@sha256:[0-9a-f]{64}$", self.docker, re.M)
        self.assertIsNotNone(m)
        self.assertIn(f"IMAGE=prastav-runner:{m.group(1)}", self.setup)

    def test_workflow_apt_line_in_image(self):
        wf = read(WF, "process-proposal.yml")
        apt = re.search(r"sudo apt-get install -y ([^;}\n]+);", wf).group(1).split()
        for pkg in apt:
            self.assertRegex(self.docker, r"\b%s\b" % re.escape(pkg), pkg)
        for pkg in ("sudo", "acl", "iptables", "util-linux", "procps", "python3-venv", "jq", "git"):
            self.assertRegex(self.docker, r"\b%s\b" % re.escape(pkg), pkg)
        self.assertIn("RUNNER_TOOL_CACHE=/opt/hostedtoolcache", self.docker)
        self.assertIn("chmod 750 /home/runner", self.docker)
        self.assertIn("ACTIONS_RUNNER_HOOK_JOB_STARTED=/opt/vps-runner/job-started.sh", self.docker)
        self.assertIn("ACTIONS_RUNNER_HOOK_JOB_COMPLETED=/opt/vps-runner/job-completed.sh", self.docker)

    def test_container_limits(self):
        run = self.setup[self.setup.index("docker run -d"):]
        run = run[:run.index('"$IMAGE"') + 8]
        for flag in ("--cpus 1.5", "--memory 5g", "--memory-swap 5g", "--restart unless-stopped", "--init",
                     "--cap-add SYS_ADMIN", "--security-opt apparmor=unconfined", '-v "$VOL:/runner-state"'):
            self.assertIn(flag, run, flag)
        self.assertEqual(run.count(" -v "), 1)          # only the named registration volume
        for bad in ("--privileged", "docker.sock", "NET_ADMIN", "--network host", "--pid host", "-v /"):
            self.assertNotIn(bad, self.setup, bad)
        self.assertIn("--remove", self.setup)
        self.assertNotIn("raw.githubusercontent", self.setup)

    def test_entrypoint_registration(self):
        self.assertIn('--url "$REPO_URL" --token "$RUNNER_TOKEN" --name "$NAME" --labels "$LABELS"', self.entry)
        self.assertIn("--work _work --replace", self.entry)
        self.assertIn("unset RUNNER_TOKEN", self.entry)
        self.assertLess(self.entry.index("unset RUNNER_TOKEN"), self.entry.index("exec ./run.sh"))
        self.assertIn("sudo /opt/vps-runner/cleanup.sh boot", self.entry)

    def test_cleanup_covers_every_job_path(self):
        used = set()
        for n in os.listdir(WF):
            used |= set(re.findall(r"(/tmp/[A-Za-z0-9-]+|/srv/engine(?:-rw)?|/opt/engine-[a-z]+)", read(WF, n)))
        used |= set(re.findall(r"(/opt/engine-[a-z]+)", read(WF, "process-proposal.yml")))
        for p in sorted(used):
            self.assertIn(p, self.cleanup, p)
        for s in ("pkill -KILL -u engine", "umount -R", "userdel -r -f engine", "exit 0"):
            self.assertIn(s, self.cleanup, s)
        self.assertTrue(self.cleanup.rstrip().endswith("exit 0"))

    def test_owner_block_in_doc(self):
        """docs/VPS_RUNNER.md (b): ONE block (OWNER_RULES B.3) that writes vps-setup.sh unchanged and runs it in the
        background with the token."""
        doc = read(ROOT, "docs", "VPS_RUNNER.md")
        m = re.search(r"cat > /root/vps-setup.sh <<'PRASTAV_SETUP_EOF'\n(.*?)PRASTAV_SETUP_EOF\n", doc, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), self.setup)
        self.assertIn('nohup bash /root/vps-setup.sh "$TOKEN" > /root/vps-setup.log 2>&1 &', doc)
        self.assertEqual(doc.count("```bash"), 1)


if __name__ == "__main__":
    unittest.main()
