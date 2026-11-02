"""tools/gemini_part1.py against a local mock of the Gemini generateContent API (no network, no key)."""
import json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "gemini_part1.py")


def serve(handler_fn):
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"path": self.path, "key": self.headers.get("x-goog-api-key"), "body": body})
            code, obj = handler_fn(len(seen), body)
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


def pages(tmp, n):
    d = tmp / "pages"; d.mkdir()
    files = []
    for i in range(1, n + 1):
        (d / f"p-{i:02d}.png").write_bytes(b"\x89PNG fake")
        (d / f"p-{i:02d}.txt").write_text(f"दि. 0{i}.08.2026", encoding="utf-8")
        files.append({"page": i, "png": f"p-{i:02d}.png", "png_small": None, "txt": f"p-{i:02d}.txt", "ocr": None})
    (d / "pages.json").write_text(json.dumps({"pages": n, "files": files}), encoding="utf-8")
    return d


def ok_resp(i):
    page = {"document": "निर्देशपत्र" if i == 1 else "पत्र", "file_page": str(i + 10),
            "blocks": [{"type": "para", "text": f"दि. 0{i}.08.2026 रोजीचे पत्र"}, {"type": "table", "rows": [["पद", "दिनांक"], ["लिपिक", "01.01.2020"]]},
                       {"type": "para", "text": " "}]}
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(page, ensure_ascii=False)}]}}],
            "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 400, "thoughtsTokenCount": 100}}


def run(tmp, base, key="AIza-test", extra=()):
    env = dict(os.environ, GEMINI_API_KEY=key, GEMINI_BASE=base, GEMINI_RETRY_WAIT="0", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, TOOL, str(tmp / "pages"), str(tmp / "out"), *extra], env=env, capture_output=True, text=True, encoding="utf-8")


def test_two_pages_ok(tmp_path):
    srv, seen = serve(lambda n, b: (200, ok_resp(n)))
    pages(tmp_path, 2)
    r = run(tmp_path, f"http://127.0.0.1:{srv.server_address[1]}")
    srv.shutdown()
    assert r.returncode == 0, r.stdout + r.stderr
    out = tmp_path / "out"
    p1 = json.loads((out / "study_part1.json").read_text(encoding="utf-8"))
    assert p1["heading"].startswith("भाग 1") and (out / "study_part1.done").exists() and not (out / "study_part1.failed").exists()
    heads = [b["subheading"] for b in p1["blocks"] if "subheading" in b]
    assert heads == ["PDF पान 1 — निर्देशपत्र (पृ. 11)", "PDF पान 2 — पत्र (पृ. 12)"]
    assert {"para": "दि. 02.08.2026 रोजीचे पत्र"} in p1["blocks"] and all(len(b) == 1 for b in p1["blocks"])
    assert not any(b.get("para") == "" for b in p1["blocks"]), "empty paragraphs dropped"
    assert seen[0]["path"] == "/v1beta/models/gemini-2.5-flash:generateContent" and seen[0]["key"] == "AIza-test"
    parts = seen[0]["body"]["contents"][0]["parts"]
    assert parts[0]["inlineData"]["mimeType"] == "image/png" and "cross-check" in parts[1]["text"]
    assert seen[0]["body"]["generationConfig"]["temperature"] == 0
    res = json.loads((out / "part1_result.json").read_text(encoding="utf-8"))
    # 2 pages x (1000 in, 500 out) at 0.30 / 2.50 per 1M = 0.0006 + 0.0025
    assert res["subtype"] == "success" and res["num_turns"] == 2 and abs(res["total_cost_usd"] - 0.0031) < 1e-9
    assert res["modelUsage"]["gemini-2.5-flash"]["inputTokens"] == 2000


def test_retry_then_fail_marks_failed(tmp_path):
    srv, seen = serve(lambda n, b: (200, ok_resp(n)) if n == 1 else (503, {"error": "busy"}))
    pages(tmp_path, 2)
    r = run(tmp_path, f"http://127.0.0.1:{srv.server_address[1]}", extra=("--model", "gemini-2.5-pro"))
    srv.shutdown()
    out = tmp_path / "out"
    assert r.returncode == 1 and len(seen) == 4, "page 2 tried 3 times"
    assert (out / "study_part1.failed").exists() and not (out / "study_part1.done").exists() and not (out / "study_part1.json").exists()
    assert "page 2" in (out / "study_part1.failed").read_text(encoding="utf-8")
    res = json.loads((out / "part1_result.json").read_text(encoding="utf-8"))
    assert res["is_error"] and "gemini-2.5-pro" in res["modelUsage"]


def test_no_key_and_bad_model_name(tmp_path):
    pages(tmp_path, 1)
    r = run(tmp_path, "http://127.0.0.1:9", key="")
    assert r.returncode == 1 and "GEMINI_API_KEY missing" in (tmp_path / "out" / "study_part1.failed").read_text(encoding="utf-8")
    srv, seen = serve(lambda n, b: (200, ok_resp(n)))
    (tmp_path / "out" / "study_part1.failed").unlink()
    r = run(tmp_path, f"http://127.0.0.1:{srv.server_address[1]}", extra=("--model", "../../x"))
    srv.shutdown()
    assert r.returncode == 0 and seen[0]["path"].endswith("/gemini-2.5-flash:generateContent"), "unsafe model name -> default"
