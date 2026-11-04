"""Static checks of the GitHub workflows (audit A2, 02.11.2026): YAML parses, every `run:` block passes `bash -n`, and
the H1 / time-budget / commit-safety rules of process-proposal.yml stay in place."""
import os, re, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load(name):
    with open(os.path.join(WF, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def steps(doc):
    for job in doc["jobs"].values():
        for st in job.get("steps", []):
            yield st


def step(doc, prefix):
    return next(s for s in steps(doc) if str(s.get("name", "")).startswith(prefix))


@unittest.skipIf(yaml is None, "pyyaml not installed")
class WorkflowStatic(unittest.TestCase):
    names = sorted(n for n in os.listdir(WF) if n.endswith((".yml", ".yaml")))

    def test_yaml_and_bash_syntax(self):
        bash = shutil.which("bash")
        for n in self.names:
            doc = load(n)
            self.assertIn("jobs", doc, n)
            for st in steps(doc):
                if "run" not in st or not bash:
                    continue
                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8") as f:
                    f.write(st["run"])
                try:
                    r = subprocess.run([bash, "-n", f.name], capture_output=True, text=True)
                finally:
                    os.unlink(f.name)
                self.assertEqual(r.returncode, 0, f"{n} / {st.get('name')}: {r.stderr}")

    def test_checkout_pinned_without_credentials(self):
        for n in ("process-proposal.yml", "gr-request.yml", "retry-failed.yml", "tests.yml"):
            co = [s for s in steps(load(n)) if str(s.get("uses", "")).startswith("actions/checkout")]
            self.assertTrue(co, n)
            for s in co:
                self.assertRegex(s["uses"], r"@[0-9a-f]{40}$", n)
                self.assertIs(s.get("with", {}).get("persist-credentials"), False, n)

    def test_timeouts(self):
        for n in ("process-proposal.yml", "gr-request.yml", "retry-failed.yml", "tests.yml"):
            for job in load(n)["jobs"].values():
                self.assertIn("timeout-minutes", job, n)
        d = load("process-proposal.yml")
        job_min = d["jobs"]["run"]["timeout-minutes"]
        self.assertEqual(str(job_min), str(d["env"]["JOB_MINUTES"]))
        for s in steps(d):
            self.assertIn("timeout-minutes", s, s.get("name") or s.get("uses"))
        main = step(d, "Process the proposal")
        self.assertLess(main["timeout-minutes"], job_min)
        run = main["run"]
        self.assertIn("DEADLINE=$(( JOB_T0 + JOB_MINUTES * 60 - POST_RESERVE_MIN * 60 ))", run)
        self.assertIn('timeout -k 60 "${MAIN_S}s"', run)
        self.assertIn('timeout -k 60 "${FB_S}s"', run)
        self.assertRegex(run, r'\[ "\$FB_S" -lt 1800 \]')     # fallback skipped below 30 min
        self.assertNotRegex(run, r"timeout -k \d+ 150m")       # no fixed 150-min runs any more

    def test_h1_sandbox(self):
        d = load("process-proposal.yml")
        main = step(d, "Process the proposal")["run"]
        self.assertNotIn('chown -R engine:engine "$GITHUB_WORKSPACE"', main)
        self.assertNotRegex(main, r"OWNED=\([^)]*GITHUB_WORKSPACE")
        self.assertIn('"$SB" up "$GITHUB_WORKSPACE" /srv/engine /srv/engine-rw', main)
        self.assertIn('"$SB" down "$GITHUB_WORKSPACE" /srv/engine /srv/engine-rw', main)
        self.assertIn('"$SB" check "$GITHUB_WORKSPACE"', main)
        self.assertIn('"$SB" scrub /tmp/out /tmp/work /tmp/case', main)
        # every runner-side tool after the Claude step comes from the root-owned snapshot
        after = main[main.index('"$SB" down'):]
        self.assertNotRegex(after, r"python3 tools/")
        for name in ("Runner OCR", "Verify outputs", "Check extracts", "Upload outputs", "Record failure", "Commit new GRs"):
            r = step(d, name)["run"]
            self.assertNotRegex(r.replace("ESP=tools/engine_supabase.py", ""), r"python3 tools/", name)
        snap = step(d, "Snapshot runner tools")["run"]
        self.assertIn('sudo chown -R root:root "$T"', snap)
        self.assertEqual(d["env"]["T"], "/opt/engine-tools")
        sb = open(os.path.join(ROOT, "scripts", "engine", "sandbox.sh"), encoding="utf-8").read()
        self.assertIn("mount -o remount,ro,bind", sb)
        self.assertIn("pkill -KILL -u engine", sb)
        self.assertIn('die "umount $mnt failed (busy)"', sb)

    def test_commit_blocks_safe(self):
        for n, name in (("process-proposal.yml", "Commit new GRs"), ("gr-request.yml", "Commit fetched GRs"),
                        ("retry-failed.yml", "Commit")):
            r = step(load(n), name)["run"]
            self.assertIn("core.hooksPath=/dev/null", r, n)
            self.assertIn("core.fsmonitor=", r, n)
            self.assertIn("credential.helper=!f()", r, n)
            self.assertNotIn("extraheader", r, n)          # the token never goes into argv
            self.assertNotRegex(r, r"\$\{?GH_TOKEN\}?\"? *\|", n)
            self.assertIn("rebase -q --autostash --onto FETCH_HEAD HEAD~1", r, n)
        for n in ("process-proposal.yml", "gr-request.yml"):
            r = [s for s in steps(load(n)) if "merge=union" in s.get("run", "")][0]["run"]
            for p in ("pdf/gr/INDEX.tsv", "tools/gr-request.txt", "tools/gr-request-done.txt"):
                self.assertIn(p, r, n)

    def test_cost_flags(self):
        d = load("process-proposal.yml")
        main = step(d, "Process the proposal")["run"]
        self.assertIn('FIRST_ARGS=(--first "$RP/claude.first.json")', main)
        self.assertIn("124|137|143) KILLED=(--killed)", main)
        self.assertIn('P1_ARGS=(--part1 "$P1F")', main)
        self.assertIn("--part1-no-cost", main)
        rf = step(d, "Record failure")["run"]
        self.assertIn("claude_result", rf)
        self.assertIn("--killed", rf)
        v = step(d, "Verify outputs")["run"]
        self.assertIn("--case-meta", v)
        x = step(d, "Check extracts")["run"]
        self.assertIn('"$RP/pkgpages"', x)
        self.assertNotIn("/tmp/work/pkgpages", x)
        names = [s.get("name", "") for s in steps(d)]
        order = [next(i for i, x in enumerate(names) if x.startswith(p)) for p in
                 ("Fetch case files", "Process the proposal", "Runner OCR", "Verify outputs", "Check extracts", "Upload outputs")]
        self.assertEqual(order, sorted(order))

    def test_litellm_hash_locked(self):
        d = load("process-proposal.yml")
        main = step(d, "Process the proposal")["run"]
        self.assertIn('--require-hashes --no-deps --only-binary=:all: -r "$T/requirements-litellm.txt"', main)
        req = open(os.path.join(ROOT, "tools", "requirements-litellm.txt"), encoding="utf-8").read()
        self.assertRegex(req, r"(?m)^litellm==1\.105\.1 ")
        pins = re.findall(r"(?m)^([A-Za-z0-9_.-]+)==\S+", req)
        self.assertGreater(len(pins), 10)
        for block in re.split(r"(?m)^(?=[A-Za-z0-9_.-]+==)", req):
            if re.match(r"[A-Za-z0-9_.-]+==", block):
                self.assertIn("--hash=sha256:", block, block.split()[0])

    def test_c33_queue_next_and_work_type(self):
        """C33: the LAST step always calls /api/engine/next with the run token and never fails the job; the prompt gets the
        work-type block from the root-owned snapshot, with a fallback that cannot fail the Claude step."""
        d = load("process-proposal.yml")
        last = d["jobs"]["run"]["steps"][-1]
        self.assertTrue(str(last.get("name", "")).startswith("Dispatch the next queued run"))
        self.assertEqual(last.get("if"), "always()")
        self.assertIn("timeout-minutes", last)
        run = last["run"]
        self.assertIn('"$WORKER/api/engine/next"', run)
        self.assertIn('Authorization: Bearer $RUN_TOKEN', run)
        self.assertIn("|| echo", run)
        self.assertTrue(run.rstrip().endswith("exit 0"))
        self.assertNotIn("set -e", run)
        main = step(d, "Process the proposal")["run"]
        self.assertIn('WT_BLOCK=$(timeout 30 python3 -I "$T/work_type.py" prompt "$WT" 2>/dev/null) || WT_BLOCK=""', main)
        self.assertIn('"$RP/runner-case.json" 2>/dev/null) || WT=service', main)
        self.assertLess(main.index("$(cat tools/ENGINE_BRIEF.md)"), main.index("$WT_BLOCK"))


if __name__ == "__main__":
    unittest.main()
