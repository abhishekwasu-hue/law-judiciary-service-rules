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

    RUNS_ON = "${{ fromJSON(vars.RUNS_ON || '\"ubuntu-latest\"') }}"

    def test_runs_on_switchable(self):
        """docs/VPS_RUNNER.md (05.11.2026): EVERY job takes its runner from the repository variable RUNS_ON
        (["self-hosted","prastav"] = the VPS runner); without the variable it is GitHub's ubuntu-latest."""
        for n in self.names:
            doc = load(n)
            for jid, job in doc["jobs"].items():
                self.assertEqual(job.get("runs-on"), self.RUNS_ON, f"{n} / {jid}")
            self.assertNotIn("runs-on: ubuntu-latest", open(os.path.join(WF, n), encoding="utf-8").read(), n)

    def test_self_hosted_leftover_guard(self):
        snap = step(load("process-proposal.yml"), "Snapshot runner tools")["run"]
        g = snap.index('if [ "${RUNNER_ENVIRONMENT:-}" = self-hosted ]')
        self.assertLess(g, snap.index('mkdir -m 700 "$RP"'))
        self.assertIn("sudo /opt/vps-runner/cleanup.sh pre || true", snap)
        self.assertIn("if id engine >/dev/null 2>&1 || mountpoint -q /srv/engine", snap)
        ed = step(load("edit-drafts.yml"), "Get run config")["run"]
        self.assertLess(ed.index("sudo /opt/vps-runner/cleanup.sh pre"), ed.index('mkdir -m 700 -p "$RP"'))

    def test_checkout_pinned_without_credentials(self):
        # S-F14 (audit 05.11.2026): EVERY workflow — SHA-pinned checkout, no persisted credentials
        for n in self.names:
            co = [s for s in steps(load(n)) if str(s.get("uses", "")).startswith("actions/checkout")]
            self.assertTrue(co, n)
            for s in co:
                self.assertRegex(s["uses"], r"@[0-9a-f]{40}$", n)
                self.assertIs(s.get("with", {}).get("persist-credentials"), False, n)

    def test_push_steps_use_env_credential_helper(self):
        """S-F14: a workflow that pushes with persist-credentials false gets the token only in its commit step's env,
        through a credential helper that reads $GH_TOKEN (never the token itself in .git/config or argv)."""
        for n in ("download-extra.yml", "download-pdfs.yml", "fetch-case-docs.yml"):
            push = [s for s in steps(load(n)) if "git push" in s.get("run", "")]
            self.assertEqual(len(push), 1, n)
            st = push[0]
            self.assertEqual(st.get("env", {}).get("GH_TOKEN"), "${{ secrets.GITHUB_TOKEN }}", n)
            self.assertIn("credential.helper '!f()", st["run"], n)
            self.assertIn('echo "password=$GH_TOKEN"', st["run"], n)
            self.assertNotIn("extraheader", st["run"], n)

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
        for name in ("Runner OCR", "Verify outputs", "Check extracts", "Check consistency", "Upload outputs", "Record failure",
                     "Commit new GRs"):
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
                 ("Fetch case files", "Process the proposal", "Runner OCR", "Verify outputs", "Check extracts",
                  "Check consistency", "Upload outputs")]
        self.assertEqual(order, sorted(order))
        c = step(d, "Check consistency")["run"]   # Q-F15: soft, never fails the job
        self.assertIn('consistency /tmp/work/spec.json /tmp/work/study.json || echo', c)

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

    def test_engine_requirements_hash_locked(self):
        """S-F14: tools/requirements-engine.txt = the whole tree with sha256; every install of it requires the hashes."""
        req = open(os.path.join(ROOT, "tools", "requirements-engine.txt"), encoding="utf-8").read()
        for pin in ("pymupdf==2.0 ", "python-docx==1.2.0 ", "docxcompose==2.2.0 ", "lxml=="):
            self.assertIn(pin, req)
        for block in re.split(r"(?m)^(?=[A-Za-z0-9_.-]+==)", req):
            if re.match(r"[A-Za-z0-9_.-]+==", block):
                self.assertIn("--hash=sha256:", block, block.split()[0])
        for n in ("process-proposal.yml", "edit-drafts.yml", "tests.yml"):
            t = open(os.path.join(WF, n), encoding="utf-8").read()
            lines = [l for l in t.splitlines() if "pip install" in l and "requirements-engine.txt" in l]
            self.assertTrue(lines, n)
            for l in lines:
                self.assertIn("--require-hashes --only-binary=:all: -r", l, n)

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


class PromptViaStdin(unittest.TestCase):
    """04.11.2026 run #12: "/usr/bin/timeout: Argument list too long" — the main prompt (prompt + brief + tool docstrings,
    ~164 KB) exceeded Linux's 128 KiB limit for ONE argv string. The main and fallback runs read it from stdin."""

    def test_main_prompt_on_stdin(self):
        y = open(os.path.join(ROOT, ".github/workflows/process-proposal.yml"), encoding="utf-8").read()
        self.assertNotIn('-p "$PROMPT"', y)
        self.assertIn('printf \'%s\' "$PROMPT" > "$RP/prompt.txt"', y)
        self.assertEqual(y.count('claude "${ARGS[@]}" < "$RP/prompt.txt"'), 2)

    def test_part1_prompt_small(self):
        n = len(open(os.path.join(ROOT, "tools/ENGINE_PART1_PROMPT.md"), encoding="utf-8").read().encode())
        self.assertLess(n, 100_000)


class Audit0511TimeCost(unittest.TestCase):
    """audit 05.11.2026 Part 1/2/9 fixes: parallel set-up (T-H), OCR once (T-C), brief in the agent definitions (C-D),
    `fixer` model plumbing (C-B), no wait loops / foreground writers / reviewer parallel to Study repairs (T-A, T-D),
    download workflows never delete an existing PDF (R-F13)."""

    @classmethod
    def setUpClass(cls):
        cls.y = open(os.path.join(WF, "process-proposal.yml"), encoding="utf-8").read()
        cls.p = open(os.path.join(ROOT, "tools", "ENGINE_PROMPT.md"), encoding="utf-8").read()

    @unittest.skipIf(yaml is None, "pyyaml not installed")
    def test_parallel_setup(self):
        d = load("process-proposal.yml")
        inst = step(d, "Install tools")["run"]
        self.assertIn('& PIP_PID=$!', inst)
        self.assertIn('& NPM_PID=$!', inst)
        self.assertIn('wait "$PIP_PID" || PIP_RC=$?', inst)
        self.assertIn('[ "$APT_RC" = 0 ] && [ "$PIP_RC" = 0 ] && [ "$NPM_RC" = 0 ] ||', inst)
        prep = step(d, "Prepare page images + precedent sources")["run"]
        self.assertIn('wait "$PREP" "$OLD" "$PREC"', prep)
        self.assertIn('"$RP/prop_ocr"', prep)
        self.assertIn('mkdir -m 700 "$RP/prop_ocr"', prep)
        names = [s.get("name", "") for s in steps(d)]
        self.assertLess(names.index("Prepare page images + precedent sources (parallel)"),
                        next(i for i, n in enumerate(names) if n.startswith("Process the proposal")))

    @unittest.skipIf(yaml is None, "pyyaml not installed")
    def test_runner_ocr_reuses_only_its_own_files(self):
        r = step(load("process-proposal.yml"), "Runner OCR")["run"]
        self.assertIn('"$T/pkg_ocr.py" "$PKG" "$RP/pkgpages"', r)
        self.assertIn('--reuse "$RP/prop_ocr"', r)
        self.assertNotIn("--reuse /tmp", r)
        self.assertNotRegex(r, r"cp[^\n]*/tmp/work/pkgpages")
        self.assertNotIn("prep_pages.py", r)

    def test_brief_into_agent_definitions_and_fixer_model(self):
        self.assertIn('python3 -I - "$T/ENGINE_BRIEF.md" /tmp/work/agents.json', self.y)
        self.assertLess(self.y.index("ES agents /tmp/work/agents.json"), self.y.index('"$T/ENGINE_BRIEF.md" /tmp/work/agents.json'))
        self.assertIn("|MODEL_FIXER|", self.y)
        self.assertIn('MODEL_FIXER="$MODEL_FIXER"', self.y)
        self.assertIn("MODEL_FIXER=$MODEL_FIXER", self.y)
        self.assertIn("export MODEL MODEL_LIGHT MODEL_REVIEW MODEL_STRONG MODEL_FIXER", self.y)

    def test_engine_prompt_no_waits_and_parallel_review(self):
        p = self.p
        self.assertIn("never `run_in_background`", p)
        self.assertIn("The single exception is the part-1 wait command", p)
        self.assertEqual(p.count("until [ -e /tmp/work/study_part1.done ]"), 1)
        self.assertNotIn("ONE Bash loop", p)
        self.assertIn("tools/pkg_ocr.py", p)
        self.assertNotIn('prep_pages.py "OUTDIR/<package>"', p)
        self.assertIn("the `reviewer` call below\n   AND, only when there is Study work left, ONE `fixer` call", p)
        self.assertNotIn("Read the brief", p)
        self.assertIn("under 100K tokens", p)
        self.assertIn("No `fixer` in\n/tmp/work/agents.json", p)

    def test_download_workflows_keep_existing_files(self):
        for n in ("download-extra.yml", "download-pdfs.yml"):
            t = open(os.path.join(WF, n), encoding="utf-8").read()
            self.assertIn('-o "$t"', t, n)
            self.assertIn('mv -f "$t" "pdf/$folder/$name"', t, n)
            self.assertNotIn('rm -f "pdf/$folder/$name"', t, n)
            self.assertNotRegex(t, r'-o "pdf/\$folder/\$name"', n)
