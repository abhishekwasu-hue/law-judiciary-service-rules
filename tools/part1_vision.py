#!/usr/bin/env python3
"""Study part 1 ("भाग 1 — प्रस्तावाचे मराठी रूपांतर") on Google Gemini — option A (Abhi, 02.11.2026;
docs/AI_PROVIDERS_RESEARCH.md). Replaces the cheap-tier Claude helper of the engine run when Settings
part1_provider = gemini and a Gemini key is set. The output is checked exactly like the Claude helper's: the workflow
validates the JSON shape, and the main run's `engine_supabase.py part1check` compares every number, date and name per
page with the drafter's own reading of the images; pages that do not match are redone by the drafter. Uses the PAID
Gemini API only: Google's terms say "Do not submit sensitive, confidential, or personal information to the Unpaid
Services" (ai.google.dev/gemini-api/terms) — a free-tier key must not be used for proposals.

Usage:  python3 tools/gemini_part1.py <pages dir> <out dir> [--model gemini-2.5-flash]
  <pages dir>  tools/prep_pages.py output (pages.json, p-NN.png, p-NN.txt, p-NN.ocr.txt)
  <out dir>    writes study_part1.json + study_part1.done (or study_part1.failed with a reason) and
               part1_result.json = a Claude-Code-like result {type, subtype, is_error, num_turns, total_cost_usd,
               modelUsage{<model>: {costUSD, inputTokens, outputTokens}}} so the engine's cost/model lines work as is.
Env: GEMINI_API_KEY (required), GEMINI_MODEL (default model), GEMINI_BASE / GEMINI_RETRY_WAIT (tests only).
Stdlib only (runs on the runner without extra packages). One request per page; 3 tries on 429/5xx/network errors."""
import base64, json, os, re, sys, time, urllib.error, urllib.request

DEFAULT_MODEL = "gemini-2.5-flash"
# USD per 1M tokens (input, output incl. thinking), paid tier, ai.google.dev/gemini-api/docs/pricing (read 02.11.2026;
# 3.x Flash prices valid to 31.12.2026). Unknown model -> cost 0 with a note (tokens still recorded).
PRICES = {"gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-flash-lite": (0.10, 0.40), "gemini-2.5-pro": (1.25, 10.00),
          "gemini-3.5-flash-lite": (0.30, 2.50), "gemini-3.1-flash-lite": (0.25, 1.50), "gemini-3-flash-preview": (0.50, 3.00),
          "gemini-3.6-flash": (0.75, 3.75), "gemini-3.8-flash": (0.75, 3.75)}

SYSTEM = """You write one page of "भाग 1 — प्रस्तावाचे मराठी रूपांतर" (Study part 1) for a Government of Maharashtra,
Law & Judiciary Department proposal file. Binding rules:
- Read the PAGE IMAGE. The text layer / OCR given with it are a cross-check only: every number, date, name and amount
  is taken from the image; where they differ, the image wins. What cannot be read on the image = "[अस्पष्ट]" — never
  fill it from the OCR or by guessing.
- Marathi text exactly as written (जसेच्या तसे — no summary, no cut, no correction). English text translated into
  Marathi, with designations / offices / Acts / GR numbers kept in the original script in brackets.
- Tables as table blocks (rows of cells). Handwritten remarks "[हस्तलिखित शेरा: …]"; stamps / receipts / inward numbers
  "[शिक्का: …]". Read stamps, inward numbers, handwritten remarks, dates and amounts twice.
- No comment, opinion, gist or heading of your own; nothing that is not on the page.
- "document": a short Marathi name of the document this page belongs to as written on it (e.g. "निर्देशपत्र",
  "जिल्हा न्यायाधीश यांचे पत्र"); "file_page": the file page number written on the page ("पृ. __"), or "" if none.
- blocks: in page order; type "para" (text), "bullets" (items), "table" (rows). Never "subheading"."""

SCHEMA = {"type": "OBJECT", "properties": {
    "document": {"type": "STRING"}, "file_page": {"type": "STRING"},
    "blocks": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "type": {"type": "STRING", "enum": ["para", "bullets", "table"]},
        "text": {"type": "STRING"},
        "items": {"type": "ARRAY", "items": {"type": "STRING"}},
        "rows": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "STRING"}}}},
        "required": ["type"]}}},
    "required": ["document", "blocks"]}


def call(model, key, parts, tries=3):
    base = os.environ.get("GEMINI_BASE", "https://generativelanguage.googleapis.com").rstrip("/")
    body = {"systemInstruction": {"parts": [{"text": SYSTEM}]}, "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": SCHEMA}}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    err = ""
    for i in range(tries):
        req = urllib.request.Request(f"{base}/v1beta/models/{model}:generateContent", data=data, method="POST",
                                     headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            err = f"HTTP {e.code}: {msg}"
            if e.code not in (429, 500, 502, 503, 504): break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            err = f"network: {e}"
        if i + 1 < tries: time.sleep(float(os.environ.get("GEMINI_RETRY_WAIT") or 5) * (i + 1))
    raise RuntimeError(err or "no response")


def page_blocks(resp):
    """Gemini response -> (document, file_page, build_study blocks, in_tokens, out_tokens)."""
    cand = (resp.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in ((cand.get("content") or {}).get("parts") or []))
    j = json.loads(txt)
    blocks = []
    for b in j.get("blocks") or []:
        t = b.get("type")
        if t == "para" and str(b.get("text") or "").strip():
            blocks.append({"para": str(b["text"]).strip()})
        elif t == "bullets" and b.get("items"):
            blocks.append({"bullets": [str(x) for x in b["items"] if str(x).strip()]})
        elif t == "table" and b.get("rows"):
            rows = [[str(c) for c in r] for r in b["rows"] if isinstance(r, list) and r]
            if rows: blocks.append({"table": rows})
    if not blocks:
        raise ValueError("empty page output")
    u = resp.get("usageMetadata") or {}
    out_t = int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)
    return str(j.get("document") or "").strip(), str(j.get("file_page") or "").strip(), blocks, int(u.get("promptTokenCount") or 0), out_t


def read_text(path, limit=6000):
    try:
        return open(path, encoding="utf-8", errors="replace").read().strip()[:limit]
    except OSError:
        return ""


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    pages_dir, out = argv[0], argv[1]
    model = (argv[argv.index("--model") + 1] if "--model" in argv else "") or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,80}", model):
        model = DEFAULT_MODEL
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    tin = tout = calls = 0
    result_path = os.path.join(out, "part1_result.json")

    def finish(ok, reason=""):
        pin, pout = PRICES.get(model, (0.0, 0.0))
        cost = round(tin / 1e6 * pin + tout / 1e6 * pout, 4)
        res = {"type": "result", "subtype": "success" if ok else "error_during_execution", "is_error": not ok,
               "num_turns": calls, "total_cost_usd": cost, "duration_ms": int((time.time() - t0) * 1000),
               "modelUsage": {model: {"costUSD": cost, "inputTokens": tin, "outputTokens": tout}},
               "result": reason or ("price unknown for " + model if model not in PRICES else "")}
        json.dump(res, open(result_path, "w", encoding="utf-8"), ensure_ascii=False)
        if not ok:
            open(os.path.join(out, "study_part1.failed"), "w", encoding="utf-8").write(reason[:300] + "\n")
        print(("PART1 GEMINI OK" if ok else "PART1 GEMINI FAILED: " + reason[:200]) + f" | {model} | calls {calls} | in {tin} out {tout} | ${cost}")
        return 0 if ok else 1

    if not key:
        return finish(False, "GEMINI_API_KEY missing")
    try:
        info = json.load(open(os.path.join(pages_dir, "pages.json"), encoding="utf-8"))
        files = info["files"]
    except Exception as e:
        return finish(False, f"pages.json: {e}")
    blocks = []
    for f in files:
        n = int(f["page"])
        png = os.path.join(pages_dir, f["png"])
        try:
            img = base64.b64encode(open(png, "rb").read()).decode("ascii")
        except OSError as e:
            return finish(False, f"page {n}: {e}")
        txt = read_text(os.path.join(pages_dir, f["txt"])) if f.get("txt") else ""
        ocr = read_text(os.path.join(pages_dir, f["ocr"])) if f.get("ocr") else ""
        cross = f"PDF page {n} of {len(files)}.\n\nText layer (cross-check only):\n{txt or '(none)'}\n\nOCR (cross-check only):\n{ocr or '(none)'}"
        try:
            calls += 1
            resp = call(model, key, [{"inlineData": {"mimeType": "image/png", "data": img}}, {"text": cross}])
            doc, fpage, pb, i_t, o_t = page_blocks(resp)
        except Exception as e:
            return finish(False, f"page {n}: {str(e)[:250]}")
        tin += i_t; tout += o_t
        head = f"PDF पान {n}" + (f" — {doc}" if doc else "") + (f" (पृ. {fpage})" if fpage and fpage not in ("__", "-") else "")
        blocks.append({"subheading": head})
        blocks.extend(pb)
    part = {"heading": "भाग 1 — प्रस्तावाचे मराठी रूपांतर", "blocks": blocks}
    json.dump(part, open(os.path.join(out, "study_part1.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(out, "study_part1.done"), "w").close()
    return finish(True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
