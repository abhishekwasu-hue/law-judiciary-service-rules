"""tools/ai_benchmark.py against local mocks (OpenAI-compatible, Gemini-shaped, Anthropic-shaped). No network, no key."""
import importlib.util
import json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ai_benchmark as ab  # noqa: E402

TOOL = os.path.join(ROOT, "tools", "ai_benchmark.py")
KEYS = ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
        "CEREBRAS_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
        "PART1_BASE", "GEMINI_BASE", "ANTHROPIC_BASE_URL", "CLAUDE_MODEL"]
TRUTH = {"p1": "महाराष्ट्र शासन वित्त विभाग\nशासन निर्णय क्र. 108, दि. 17.09.2026\nमूळ वेतन रु. 35,400/- दिनांक 01.06.2014\n",
         "p2": "अ.क्र. पद दिनांक\n1 लिपिक 01.01.2020\n2 शिपाई 15.07.2015\n"}


def page_json(text):
    return json.dumps({"document": "पत्र", "file_page": "", "blocks": [{"type": "para", "text": l} for l in text.splitlines() if l]},
                      ensure_ascii=False)


def serve(answer):
    """answer(kind, n, body) -> (code, text). kind = gemini / compat / claude by URL; replies in that provider's shape."""
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            kind = "gemini" if ":generateContent" in self.path else "claude" if self.path.endswith("/v1/messages") else "compat"
            seen.append({"kind": kind, "path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
            code, txt = answer(kind, len(seen), body)
            if code != 200:
                obj = {"error": txt}
            elif kind == "gemini":
                obj = {"candidates": [{"content": {"parts": [{"text": txt}]}}], "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 200}}
            elif kind == "claude":
                obj = {"content": [{"type": "text", "text": txt}], "usage": {"input_tokens": 1500, "output_tokens": 300}}
            else:
                obj = {"choices": [{"message": {"content": txt}}], "usage": {"prompt_tokens": 900, "completion_tokens": 250}}
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen, f"http://127.0.0.1:{srv.server_address[1]}"


def make_set(tmp):
    d = tmp / "set"
    (d / "pages").mkdir(parents=True); (d / "ground_truth").mkdir()
    for pid, t in TRUTH.items():
        (d / "pages" / f"{pid}.png").write_bytes(b"\x89PNG fake")
        (d / "ground_truth" / f"{pid}.txt").write_text(t, encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({"pages": [{"id": "p1", "kind": "gr"}, {"id": "p2", "kind": "dummy"}]}), encoding="utf-8")
    return d


def clean_env(**kw):
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env.update(PYTHONIOENCODING="utf-8", **kw)
    return env


# ---------------------------------------------------------------- scoring
def test_score_exact_and_normalisation():
    s = ab.score(TRUTH["p1"], TRUTH["p1"].replace("17.09.2026", "१७.०९.२०२६").replace("35,400", "35400"))
    assert s["number_recall"] == 1 and s["date_recall"] == 1 and s["word_recall"] == 1 and s["invented"] == 0
    assert s["truth_dates"] == 2 and s["truth_numbers"] == 4  # 108, 35400 + two dates
    assert ab.score("दि. 1/6/2014", "दि. 01.06.2014")["date_recall"] == 1


def test_score_errors_counted():
    got = TRUTH["p1"].replace("108", "180").replace("01.06.2014", "01.06.2015") + "क्र. 999"
    s = ab.score(TRUTH["p1"], got)
    assert s["number_recall"] == 0.5 and s["date_recall"] == 0.5 and s["invented"] == 3
    assert 0 < s["cer"] < 0.2 and s["word_recall"] == 1
    assert ab.score("महाराष्ट्र शासन", "")["word_recall"] == 0 and ab.score("abc", "")["cer"] == 1


def test_levenshtein_matches_dp():
    import random
    def dp(a, b):
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]
    rnd = random.Random(7)
    for _ in range(300):
        a = "".join(rnd.choice("अकि् 1.") for _ in range(rnd.randint(0, 30)))
        b = "".join(rnd.choice("अकि् 1.") for _ in range(rnd.randint(0, 30)))
        assert ab.levenshtein(a, b) == dp(a, b)


# ---------------------------------------------------------------- skipping
def test_missing_keys_listed(monkeypatch):
    for k in KEYS: monkeypatch.delenv(k, raising=False)
    assert ab.missing("gemini", {}) == "GEMINI_API_KEY not set"
    assert ab.missing("ollama", {}) == "OLLAMA_BASE_URL not set"
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
    assert "CLOUDFLARE_ACCOUNT_ID" in ab.missing("cloudflare", {})
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "0" * 32)
    assert ab.missing("cloudflare", {}) == ""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://10.0.0.5:11434")
    assert ab.missing("ollama", {}) == ""
    runs = ab.parse_runs("ollama:gemma4:12b,claude,gemini:gemini-2.5-pro")
    assert [r["label"] for r in runs] == ["ollama:gemma4:12b", "claude:claude-haiku-5-5", "gemini:gemini-2.5-pro"]


def test_no_keys_all_skipped(tmp_path):
    d = make_set(tmp_path)
    r = subprocess.run([sys.executable, TOOL, "run", str(d), str(tmp_path / "out")], env=clean_env(),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    res = json.loads((tmp_path / "out" / "results.json").read_text(encoding="utf-8"))
    assert res["runs"] == [] and len(res["skipped"]) == len(ab.ALL)
    assert "Skipped" in (tmp_path / "out" / "results.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- end to end against the mocks
def test_run_four_providers(tmp_path):
    def answer(kind, n, body):
        user = body["messages"][-1]["content"] if kind != "gemini" else body["contents"][0]["parts"]
        text = json.dumps(user, ensure_ascii=False)
        pid = "p1" if "PDF page 1 of 2" in text else "p2"
        model = body.get("model", "")
        if kind == "gemini":
            return 200, page_json(TRUTH[pid])
        if kind == "claude":
            return (429, "rate limit") if n == 3 else (200, page_json(TRUTH[pid]))  # first claude request = 429
        if model == "gemma4:12b":
            return 200, "not json " + TRUTH[pid]
        return 200, page_json(TRUTH[pid].replace("108", "180") + "क्र. 777")

    srv, seen, url = serve(answer)
    d = make_set(tmp_path)
    out = tmp_path / "out"
    env = clean_env(GEMINI_API_KEY="AIza-test", GROQ_API_KEY="gsk-test", ANTHROPIC_API_KEY="sk-ant-test", OLLAMA_BASE_URL=url)
    r = subprocess.run([sys.executable, TOOL, "run", str(d), str(out), "--providers", "gemini,claude,groq,ollama:gemma4:12b,mistral",
                        "--sleep", "0", "--retry-wait", "0", "--base", f"gemini={url}", "--base", f"groq={url}/openai/v1",
                        "--base", f"claude={url}"], env=env, capture_output=True, text=True, encoding="utf-8")
    srv.shutdown()
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads((out / "results.json").read_text(encoding="utf-8"))
    runs = {x["label"]: x for x in res["runs"]}
    assert set(runs) == {"gemini:gemini-2.5-flash", "claude:claude-haiku-5-5", "groq:qwen3.8-27b", "ollama:gemma4:12b"}
    assert res["skipped"] == [{"run": "mistral:mistral-small-latest", "reason": "MISTRAL_API_KEY not set"}]
    g = runs["gemini:gemini-2.5-flash"]["summary"]
    assert g["number_recall"] == 1 and g["word_recall"] == 1 and g["cer"] == 0 and g["invented_per_page"] == 0
    assert g["requests"] == 2 and g["in_tokens"] == 2000 and g["pages_json_ok"] == 2
    c = runs["claude:claude-haiku-5-5"]["summary"]
    assert c["rate_limited_429"] == 1 and c["requests"] == 3 and c["pages_answered"] == 2 and c["errors"] == 0
    q = runs["groq:qwen3.8-27b"]
    assert q["pages"][0]["scores"]["number_recall"] == 0.75 and q["pages"][0]["scores"]["invented"] == 2
    assert q["summary"]["invented_per_page"] == 1.5
    o = runs["ollama:gemma4:12b"]["summary"]
    assert o["pages_json_ok"] == 0 and o["pages_answered"] == 2 and o["errors"] == 2 and o["word_recall"] == 1
    # same task as part1_vision: its system prompt, the image, temperature 0, no text layer sent
    cl = next(s for s in seen if s["kind"] == "claude")
    assert cl["headers"]["x-api-key"] == "sk-ant-test" and cl["body"]["system"].startswith(ab.pv.SYSTEM[:40])
    assert cl["body"]["messages"][0]["content"][0]["source"]["media_type"] == "image/png"
    gm = next(s for s in seen if s["kind"] == "gemini")
    assert gm["path"] == "/v1beta/models/gemini-2.5-flash:generateContent" and gm["body"]["generationConfig"]["temperature"] == 0
    cp = [s for s in seen if s["kind"] == "compat"]
    assert {s["path"] for s in cp} == {"/openai/v1/chat/completions", "/v1/chat/completions"}
    assert "Text layer (cross-check only):\n(none)" in cp[0]["body"]["messages"][1]["content"][1]["text"]
    assert len(seen) == 9  # 2 pages x 4 runs + one retried 429
    md = (out / "results.md").read_text(encoding="utf-8")
    assert "| gemini:gemini-2.5-flash | 2/2 / 2 | 100.0% |" in md and "mistral" in md
    if importlib.util.find_spec("matplotlib"):  # optional: CI has no matplotlib, the tool then skips the chart
        assert (out / "results.png").stat().st_size > 10000
    assert (out / "raw" / "groq_qwen3.8-27b" / "p1.txt").read_text(encoding="utf-8").endswith("क्र. 777")


def test_non_retry_error_recorded(tmp_path):
    srv, seen, url = serve(lambda kind, n, body: (401, "bad key"))
    d = make_set(tmp_path)
    r = subprocess.run([sys.executable, TOOL, "run", str(d), str(tmp_path / "out"), "--providers", "openrouter", "--sleep", "0",
                        "--retry-wait", "0", "--base", f"openrouter={url}"], env=clean_env(OPENROUTER_API_KEY="k"),
                       capture_output=True, text=True, encoding="utf-8")
    srv.shutdown()
    s = json.loads((tmp_path / "out" / "results.json").read_text(encoding="utf-8"))["runs"][0]["summary"]
    assert r.returncode == 0 and s["pages_answered"] == 0 and s["errors"] == 2 and s["requests"] == 2 and len(seen) == 2


# ---------------------------------------------------------------- Test B helper
def test_facts_check(tmp_path):
    facts = {"facts": [{"field": "date", "value": "01.06.2014"}, {"field": "pay", "value": "35,400"},
                       {"field": "name", "value": "अ. ब. चाचणी"}, {"field": "route", "value": "x", "check": False}]}
    r = ab.facts_check(facts, ["श्री. अ. ब. चाचणी यांची नियुक्ती दि. 1/6/2014", "मूळ वेतन रु. 35400"])
    assert r == {"found": 3, "total": 3, "missing": []}
    r = ab.facts_check(facts, ["श्री. अ.ब. चाचणी"])
    assert r["found"] == 0 and r["total"] == 3


def test_confirmed_words_used_for_word_recall():
    truth = "शासन धवभाग दि. 01.06.2014"            # text layer with a font-mapping slip
    got = "शासन विभाग दि. 01.06.2014"              # a correct reading of the image
    assert abs(ab.score(truth, got)["word_recall"] - 2 / 3) < 1e-9
    s = ab.score(truth, got, truth_words="शासन दि")  # confirmed words (text layer ∩ OCR)
    assert s["word_recall"] == 1 and s["truth_words"] == 2 and s["date_recall"] == 1
