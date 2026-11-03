"""tools/run_timeline.py (Abhi 03.11.2026 "हो जोडा"): the stamp filter keeps the result JSON exactly as
`--output-format json` gave it, and the report shows per-subagent / per-tool time from a synthetic stream-json run."""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "run_timeline.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import run_timeline as RT  # noqa: E402

RESULT = {"type": "result", "subtype": "success", "is_error": False, "duration_ms": 600000, "duration_api_ms": 420000,
          "num_turns": 3, "result": "done", "session_id": "s", "total_cost_usd": 2.51,
          "modelUsage": {"claude-haiku-5-5": {"inputTokens": 10, "outputTokens": 20, "cacheReadInputTokens": 30,
                                              "cacheCreationInputTokens": 40, "costUSD": 0.31},
                         "claude-opus-5-5": {"inputTokens": 1, "outputTokens": 2, "cacheReadInputTokens": 3,
                                             "cacheCreationInputTokens": 4, "costUSD": 2.2}},
          "subagent_stats": {"spawned": 2, "completed": 2, "by_type": {"drafter": 1, "reviewer": 1}}}


def asst(mid, model, content, parent=None):
    return {"type": "assistant", "message": {"id": mid, "model": model, "role": "assistant", "content": content},
            "parent_tool_use_id": parent, "session_id": "s"}


def user(results, parent=None, tur=None):
    o = {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": t, "content": "x"} for t in results]},
         "parent_tool_use_id": parent, "session_id": "s"}
    if tur is not None:
        o["tool_use_result"] = tur
    return o


def tu(i, name, inp):
    return {"type": "tool_use", "id": i, "name": name, "input": inp}


H, O = "claude-haiku-5-5", "claude-opus-5-5"
STREAM = [
    (0, {"type": "system", "subtype": "init", "model": H, "claude_code_version": "2.1.300"}),
    (5, asst("m1", H, [tu("b1", "Bash", {"command": "pdftoppm -r 110 -png /tmp/case/in/proposal/x.pdf /tmp/work/pg/p"})])),
    (65, user(["b1"])),
    (66, asst("m2", H, [tu("r1", "Read", {"file_path": "/tmp/case/pages/p-01.png"})])),
    (67, user(["r1"])),
    # drafter: foreground, completed in its tool_result
    (70, asst("m3", H, [tu("a1", "Agent", {"subagent_type": "drafter", "description": "facts + note + letter", "prompt": "p"})])),
    (72, asst("d1", O, [tu("d1b", "Bash", {"command": "python3 tools/build_note_letter.py /tmp/work/spec.json /tmp/out CR1"})], parent="a1")),
    (372, user(["d1b"], parent="a1")),
    (373, asst("d2", O, [tu("d2r", "Read", {"file_path": "/tmp/case/pages/p-02.PNG"})], parent="a1")),
    (374, user(["d2r"], parent="a1")),
    (380, asst("d3", O, [{"type": "text", "text": "ok"}], parent="a1")),
    (970, user(["a1"], tur={"status": "completed", "agentType": "drafter", "totalDurationMs": 899000, "resolvedModel": O,
                           "totalToolUseCount": 2, "totalTokens": 5})),
    # reviewer: background — tool_result says async_launched, the end is the task_notification
    (971, asst("m4", H, [tu("a2", "Agent", {"subagent_type": "reviewer", "description": "final review", "prompt": "p",
                                            "run_in_background": True})])),
    (971.5, {"type": "system", "subtype": "task_started", "task_id": "t2", "tool_use_id": "a2", "description": "final review",
             "subagent_type": "reviewer", "is_backgrounded": True}),
    (972, user(["a2"], tur={"status": "async_launched", "agentId": "x", "description": "final review", "prompt": "p",
                           "outputFile": "/tmp/o"})),
    (980, asst("v1", O, [{"type": "text", "text": "checking"}], parent="a2")),
    (1200, {"type": "system", "subtype": "task_notification", "task_id": "t2", "status": "completed", "summary": "s",
            "usage": {"total_tokens": 9, "tool_uses": 0, "duration_ms": 228000}}),
    (1201, asst("m5", H, [{"type": "text", "text": "done"}])),
    (1202, RESULT),
]


def write_tsv(path, base=1000.0, garbage=True):
    with open(path, "w", encoding="utf-8") as f:
        for i, (t, o) in enumerate(STREAM):
            f.write(f"{base + t:.3f}\t{json.dumps(o, ensure_ascii=False)}\n")
            if garbage and i == 3:
                f.write("not a timestamp line\n")
                f.write(f"{base + t:.3f}\t{{broken json\n")


class Stamp(unittest.TestCase):
    def test_result_unchanged_and_tsv(self):
        with tempfile.TemporaryDirectory() as d:
            tsv, rj = os.path.join(d, "c.stream.tsv"), os.path.join(d, "claude.json")
            big = "A" * 5000
            res_line = json.dumps(dict(RESULT, result="x" * 9000), separators=(",", ":"))
            lines = [json.dumps({"type": "system", "subtype": "init"}, separators=(",", ":")),
                     json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "r",
                                 "content": [{"type": "image", "source": {"type": "base64", "data": big}}]}]}}, separators=(",", ":")),
                     "garbage line",
                     json.dumps(dict(RESULT, num_turns=1), separators=(",", ":")),
                     res_line]
            p = subprocess.run([sys.executable, "-I", TOOL, "stamp", tsv, rj], input="\n".join(lines) + "\n",
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(open(rj, encoding="utf-8").read(), res_line + "\n")      # the LAST result line, unchanged
            self.assertEqual(json.load(open(rj, encoding="utf-8"))["num_turns"], 3)
            self.assertTrue(os.path.exists(tsv + ".eof"))
            rows = open(tsv, encoding="utf-8").read().splitlines()
            self.assertEqual(len(rows), 5)
            for r in rows:
                ts, _, body = r.partition("\t")
                self.assertRegex(ts, r"^\d{10}\.\d{3}$")
            self.assertIn('"data":"<b64 5000>"', rows[1])
            self.assertNotIn(big, rows[1])
            self.assertEqual(rows[2].split("\t", 1)[1], "garbage line")
            self.assertEqual(rows[4].split("\t", 1)[1], res_line)                   # the result keeps its text in the .tsv

    def test_no_result_leaves_file_alone(self):
        with tempfile.TemporaryDirectory() as d:
            tsv, rj = os.path.join(d, "c.tsv"), os.path.join(d, "claude.json")
            open(rj, "w").close()
            subprocess.run([sys.executable, "-I", TOOL, "stamp", tsv, rj], input="{}\n", text=True, timeout=60, check=True)
            self.assertEqual(os.path.getsize(rj), 0)    # killed run: empty, as with --output-format json

    def test_unwritable_tsv_still_drains(self):
        with tempfile.TemporaryDirectory() as d:
            rj = os.path.join(d, "claude.json")
            p = subprocess.run([sys.executable, "-I", TOOL, "stamp", os.path.join(d, "no", "dir.tsv"), rj],
                               input="x\n" * 10000 + json.dumps(RESULT) + "\n", capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(json.load(open(rj, encoding="utf-8"))["total_cost_usd"], 2.51)


class Report(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.tsv = os.path.join(self.d.name, "claude.stream.tsv")
        write_tsv(self.tsv)

    def tearDown(self):
        self.d.cleanup()

    def test_analyse(self):
        a = RT.analyse(RT.read_events(self.tsv))
        self.assertEqual(a["lines"], len(STREAM))                 # garbled lines skipped
        self.assertEqual(a["total_s"], 1202.0)
        ag = {x["type"]: x for x in a["agents"]}
        self.assertEqual(set(ag), {"drafter", "reviewer"})
        dr, rv = ag["drafter"], ag["reviewer"]
        self.assertEqual((dr["start_s"], dr["end_s"], dr["dur_s"], dr["end_by"]), (70.0, 970.0, 900.0, "result"))
        self.assertEqual(dr["model"], "opus-5-5")
        self.assertEqual((dr["turns"], dr["tool_uses"], dr["image_reads"], dr["cli_s"]), (3, 2, 1, 899.0))
        self.assertEqual(dr["description"], "facts + note + letter")
        self.assertTrue(rv["background"])
        self.assertEqual((rv["end_s"], rv["dur_s"], rv["end_by"], rv["cli_s"], rv["status"]), (1200.0, 229.0, "notification", 228.0, "completed"))
        self.assertEqual(rv["model"], "opus-5-5")                 # from its own messages
        slow = a["slow_tools"]
        self.assertEqual([(x["name"], x["owner"], x["dur_s"]) for x in slow[:2]], [("Bash", "drafter", 300.0), ("Bash", "main", 60.0)])
        self.assertTrue(slow[0]["detail"].startswith("python3 tools/build_note_letter.py"))
        self.assertLessEqual(len(slow[0]["detail"]), 80)
        self.assertEqual(a["image_reads"], {"main": 1, "drafter": 1})
        turns = {(x["owner"], x["model"]): x["turns"] for x in a["turns"]}
        self.assertEqual(turns, {("main", H): 5, ("sub", O): 4})
        self.assertEqual(a["result"]["num_turns"], 3)
        self.assertEqual(a["model_usage"][O]["costUSD"], 2.2)
        self.assertEqual(a["subagent_stats"]["by_type"], {"drafter": 1, "reviewer": 1})

    def test_report_cli(self):
        js, line = os.path.join(self.d.name, "timeline.json"), os.path.join(self.d.name, "timeline.line")
        p = subprocess.run([sys.executable, "-I", TOOL, "report", js, f"main={self.tsv}", "part1=/nonexistent.tsv",
                            "--line", line], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("drafter", p.stdout)
        self.assertIn("reviewer", p.stdout)
        self.assertIn("15:00", p.stdout)                          # drafter 900 s
        self.assertIn("duration_api_ms 7:00", p.stdout)
        self.assertIn("modelUsage", p.stdout)
        d = json.load(open(js, encoding="utf-8"))
        self.assertEqual(list(d), ["main"])
        ln = open(line, encoding="utf-8").read().strip()
        self.assertTrue(ln.startswith("मॉडेल: वेळ — Claude एकूण 20.0 मि"), ln)
        self.assertIn("drafter 15.0", ln)
        self.assertLessEqual(len(ln), 300)

    def test_never_fails(self):
        bad = os.path.join(self.d.name, "bad.tsv")
        open(bad, "wb").write(b"\xff\xfe\x00garbage\n1.0\t[1,2]\n2.0\t{\"type\":\"assistant\",\"message\":\"x\"}\n"
                              b"3.0\t{\"type\":\"user\",\"message\":{\"content\":\"text\"}}\n")
        for args in (["report", os.path.join(self.d.name, "t.json"), f"main={bad}"], ["report"], ["stages", "/nonexistent", "x"],
                     ["stages", "/nonexistent"], []):
            p = subprocess.run([sys.executable, "-I", TOOL] + args, capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, (args, p.stderr))

    def test_stages(self):
        st = os.path.join(self.d.name, "stages.tsv")
        with open(st, "w", encoding="utf-8") as f:
            f.write("prep_pages\t1000\t1120\nClaude (Process the proposal)\t1200\t3390\nbroken line\n")
        js = os.path.join(self.d.name, "timeline.json")
        subprocess.run([sys.executable, "-I", TOOL, "report", js, f"main={self.tsv}"], capture_output=True, timeout=60, check=True)
        p = subprocess.run([sys.executable, "-I", TOOL, "stages", st, "900", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0)
        self.assertIn("वेळ-तक्ता", p.stdout)
        self.assertIn("2:00", p.stdout)                           # prep_pages 120 s
        self.assertIn("36:30", p.stdout)                          # Claude step 2190 s
        self.assertIn("drafter 15:00", p.stdout)


class Workflow(unittest.TestCase):
    def test_workflow_uses_stream(self):
        wf = open(os.path.join(ROOT, ".github", "workflows", "process-proposal.yml"), encoding="utf-8").read()
        self.assertNotIn("--output-format json", wf)
        self.assertEqual(wf.count("--output-format stream-json --verbose"), 2)      # main/fallback ARGS + part-1 helper
        self.assertIn('> >(STAMP "$RP/claude.stream.tsv" "$RP/claude.json") 2> "$RP/claude.err" || rc=$?', wf)
        self.assertEqual(wf.count('> >(STAMP "$RP/claude.stream.tsv" "$RP/claude.json")'), 2)   # main + fallback
        self.assertIn('> >(STAMP "$RP/part1.stream.tsv" "$RP/part1_result.json")', wf)
        self.assertIn('STAMP() { python3 -I "$T/run_timeline.py" stamp "$@"; }', wf)
        self.assertIn('"$T/run_timeline.py" report "$RP/timeline.json"', wf)
        self.assertIn('ES note "$(head -n 1 "$RP/timeline.line")" || true', wf)
        self.assertIn("name: Stage times (वेळ-तक्ता)", wf)
        self.assertEqual(wf.count('>> "$RP/stages.tsv"; } 2>/dev/null || true\' EXIT'), 9)   # 9 timed steps; trap never changes rc


if __name__ == "__main__":
    unittest.main()
