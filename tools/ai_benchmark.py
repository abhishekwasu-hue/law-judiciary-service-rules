#!/usr/bin/env python3
"""AI-provider benchmark for the प्रस्ताव कक्ष engine (docs/AI_BENCHMARK.md). Stdlib only (matplotlib for the chart).

Test A — page reading: every provider gets the SAME per-page task as tools/part1_vision.py (same system prompt, same
JSON answer, one PNG per request) for every page of a benchmark set (tools/ai_benchmark_set.py), and the answer is
scored against the page's ground truth.

Usage:
  python3 tools/ai_benchmark.py run <set dir> <out dir> [--providers p1,p2:model,...] [--sleep 4] [--retries 2]
          [--retry-wait 20] [--cross none|ocr] [--pages id1,id2] [--base provider=URL]...
  python3 tools/ai_benchmark.py facts <facts.json> <file.docx|.txt|.json>...      (Test B: facts found in outputs)
  python3 tools/ai_benchmark.py report <out dir>                                   (rebuild results.md + chart)

Providers (a run is skipped, and listed, when its key / URL is not in the environment):
  claude      ANTHROPIC_API_KEY (Anthropic Messages API with an image; baseline; default model claude-haiku-5-5)
  gemini      GEMINI_API_KEY (native generateContent, as part1_vision.call)
  openai, openrouter, groq, mistral, cerebras   <NAME>_API_KEY (OpenAI-compatible, as part1_vision.call_compat)
  cloudflare  CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID;   ollama  OLLAMA_BASE_URL (OLLAMA_API_KEY optional)
  "provider:model" picks a model (e.g. ollama:gemma4:12b, gemini:gemini-2.5-pro); default = part1_vision's default.
  Default --providers = all of them, each with its default model.
Free limits: requests are sequential, one request per page; a 429 / 5xx / network error is retried at most --retries
times after --retry-wait x attempt seconds (every request and every 429 is counted); --sleep seconds between requests.
--cross: what goes with the image as the "cross-check" text. none (default) = the model reads the image alone;
ocr = tesseract mar+eng of the PNG (what the engine gives for a scanned proposal). The PDF text layer is never sent
(it IS the ground truth).

Scores per page (text = all para / bullet / table-cell text of the answer; headings added by part1_vision are not
part of it; Devanagari digits -> ASCII, NFC, ZWJ/ZWNJ removed):
  number_recall  share of the ground-truth number tokens (multiset; "35,400" = "35400") found in the answer
  date_recall    the same for dates (D.M.YYYY / D/M/YYYY / D-M-YYYY -> DD.MM.YYYY)
  word_recall    share of the ground-truth Devanagari words (multiset) found in the answer; on GR pages the truth is
                 ground_truth/<id>.words.txt (text-layer words that tesseract also reads — the text layers of Marathi
                 GRs carry font-mapping slips), on dummy pages the exact source text
  cer            character error rate = Levenshtein(answer, truth) / len(truth), whitespace collapsed. Reading order
                 counts here (a table read column-wise scores worse) — read it together with word_recall. Exact on
                 dummy pages; on GR pages it is against the text layer, so its font-mapping slips count as errors
                 (results.md shows CER per page kind).
  invented       number tokens in the answer that are not in the ground truth (multiset difference)
Output: <out>/results.json, results.md (table), results.png (grouped bar chart), raw/<run>/<page>.txt (answers)."""
import base64, collections, json, os, re, shutil, subprocess, sys, time, unicodedata, urllib.error, urllib.request, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import part1_vision as pv  # noqa: E402

CLAUDE_DEFAULT = "claude-haiku-5-5"
CLAUDE_URL = "https://api.anthropic.com"
ALL = ["claude", "gemini", "openai", "openrouter", "groq", "mistral", "cerebras", "cloudflare", "ollama"]

# ---------------------------------------------------------------- scoring
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
DEV_WORD = re.compile(r"[ऀ-ॣॱ-ॿ]+")
DATE = re.compile(r"(?<![\d.])(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})(?![\d])")
NUM = re.compile(r"\d+(?:[.,/:-]\d+)*")


def norm(t):
    t = unicodedata.normalize("NFC", str(t or "")).translate(DEV_DIGITS)
    t = t.replace("‍", "").replace("‌", "").replace("﻿", "").replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in t.splitlines()).strip()


def words(t):
    return DEV_WORD.findall(norm(t))


def dates(t):
    out = []
    for d, m, y in DATE.findall(norm(t)):
        if 1 <= int(d) <= 31 and 1 <= int(m) <= 12:
            out.append(f"{int(d):02d}.{int(m):02d}.{y if len(y) == 4 else '20' + y}")
    return out


def numbers(t):
    rest = DATE.sub(" ", norm(t))  # dates counted once, in DD.MM.YYYY form
    return [n.replace(",", "") for n in NUM.findall(rest)] + dates(t)


def recall(truth, got):
    tc = collections.Counter(truth)
    if not tc:
        return None
    return sum((tc & collections.Counter(got)).values()) / sum(tc.values())


def word_recall(truth_text, got_text):
    return recall(words(truth_text), words(got_text))


def levenshtein(a, b):
    """Bit-parallel edit distance (Hyyrö 2003) — exact, fast on page-sized strings with Python big ints."""
    if not a: return len(b)
    if not b: return len(a)
    m = len(a); full = (1 << m) - 1; top = 1 << (m - 1)
    peq = {}
    for i, c in enumerate(a):
        peq[c] = peq.get(c, 0) | (1 << i)
    vp, vn, score = full, 0, m
    for c in b:
        eq = peq.get(c, 0)
        xv = eq | vn
        xh = (((eq & vp) + vp) ^ vp) | eq
        hp = vn | ~(xh | vp)
        hn = vp & xh
        if hp & top: score += 1
        elif hn & top: score -= 1
        hp = (hp << 1) | 1
        hn = hn << 1
        vp = (hn | ~(xv | hp)) & full
        vn = (hp & xv) & full
    return score


def flat(t):
    return re.sub(r"\s+", " ", norm(t)).strip()


def score(truth, got, truth_words=None):
    """truth_words: the confirmed words of a GR page (ground_truth/<id>.words.txt) — word recall is scored on them."""
    tn, gn = numbers(truth), numbers(got)
    ft, fg = flat(truth), flat(got)
    tw = words(truth_words) if truth_words is not None else words(truth)
    return {"number_recall": recall(tn, gn), "date_recall": recall(dates(truth), dates(got)),
            "word_recall": recall(tw, words(got)),
            "cer": round(levenshtein(ft, fg) / len(ft), 4) if ft else None,
            "invented": sum((collections.Counter(gn) - collections.Counter(tn)).values()),
            "truth_numbers": len(tn), "truth_dates": len(dates(truth)), "truth_words": len(tw)}


def blocks_text(blocks):
    out = []
    for b in blocks:
        if "para" in b: out.append(b["para"])
        elif "bullets" in b: out.extend(b["bullets"])
        elif "table" in b: out.extend(" ".join(r) for r in b["table"])
    return "\n".join(out)


# ---------------------------------------------------------------- providers
def parse_runs(spec):
    runs = []
    for s in [x.strip() for x in (spec or ",".join(ALL)).split(",") if x.strip()]:
        prov, _, model = s.partition(":")
        if prov not in ALL:
            raise SystemExit(f"unknown provider: {prov}")
        default = CLAUDE_DEFAULT if prov == "claude" else pv.DEFAULT_MODEL if prov == "gemini" else pv.OPENAI_COMPAT[prov][2]
        model = model or (os.environ.get("CLAUDE_MODEL") if prov == "claude" else "") or default
        runs.append({"label": f"{prov}:{model}", "provider": prov, "model": model})
    return runs


def key_env(prov):
    return "ANTHROPIC_API_KEY" if prov == "claude" else "GEMINI_API_KEY" if prov == "gemini" else pv.OPENAI_COMPAT[prov][1]


def missing(prov, bases):
    """'' when the provider can run, else the reason (names of the missing env vars)."""
    if prov == "ollama":
        return "" if re.match(r"https?://", os.environ.get("OLLAMA_BASE_URL", "").strip()) or prov in bases else "OLLAMA_BASE_URL not set"
    need = [key_env(prov)] + (["CLOUDFLARE_ACCOUNT_ID"] if prov == "cloudflare" and prov not in bases else [])
    miss = [k for k in need if not os.environ.get(k, "").strip()]
    if prov == "cloudflare" and "CLOUDFLARE_ACCOUNT_ID" not in miss and prov not in bases and not re.fullmatch(r"[0-9a-f]{32}", os.environ["CLOUDFLARE_ACCOUNT_ID"].strip()):
        miss.append("CLOUDFLARE_ACCOUNT_ID (32 hex)")
    return (", ".join(miss) + " not set") if miss else ""


def call_claude(model, key, img_b64, text, base=None):
    """Anthropic Messages API, one PNG + text, one try -> Gemini-shaped dict for part1_vision.page_blocks."""
    url = (base or os.environ.get("ANTHROPIC_BASE_URL") or CLAUDE_URL).rstrip("/") + "/v1/messages"
    body = {"model": model, "max_tokens": 8192, "temperature": 0, "system": pv.SYSTEM + "\n" + pv.JSON_HINT,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                {"type": "text", "text": text}]}]}
    for attempt in (1, 2):
        req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                j = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            m = e.read()[:300].decode("utf-8", "replace")
            if e.code == 400 and "temperature" in m and "temperature" in body and attempt == 1:
                body.pop("temperature"); continue  # a model that does not take sampling parameters
            raise RuntimeError(f"HTTP {e.code}: {m}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RuntimeError(f"network: {e}")
    msg = "".join(c.get("text", "") for c in j.get("content") or [] if c.get("type") == "text")
    msg = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", msg)
    u = j.get("usage") or {}
    return {"candidates": [{"content": {"parts": [{"text": msg}]}}],
            "usageMetadata": {"promptTokenCount": int(u.get("input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0),
                              "candidatesTokenCount": int(u.get("output_tokens") or 0)}}


class _Base:
    """Points part1_vision's calls at --base URL for one request (PART1_BASE is read at call time)."""
    def __init__(self, url): self.url, self.old = url, None
    def __enter__(self):
        self.old = os.environ.pop("PART1_BASE", None), os.environ.pop("GEMINI_BASE", None)
        if self.url: os.environ["PART1_BASE"] = self.url
    def __exit__(self, *a):
        os.environ.pop("PART1_BASE", None)
        for k, v in zip(("PART1_BASE", "GEMINI_BASE"), self.old):
            if v is not None: os.environ[k] = v


def one_request(run, img_b64, text, base):
    prov, model = run["provider"], run["model"]
    key = os.environ.get(key_env(prov), "").strip()
    if prov == "claude":
        return call_claude(model, key, img_b64, text, base)
    with _Base(base):
        if prov == "gemini":
            return pv.call(model, key, [{"inlineData": {"mimeType": "image/png", "data": img_b64}}, {"text": text}], tries=1)
        return pv.call_compat(prov, model, key, img_b64, text, tries=1)


def raw_text(resp):
    cand = (resp.get("candidates") or [{}])[0]
    return "".join(p.get("text", "") for p in ((cand.get("content") or {}).get("parts") or []))


def ocr_text(png):
    exe = shutil.which("tesseract")
    if not exe:
        return ""
    r = subprocess.run([exe, png, "stdout", "-l", "mar+eng"], capture_output=True, timeout=300)
    return r.stdout.decode("utf-8", "replace").strip()[:6000]


def run_page(run, page, n, total, set_dir, opts, raw_dir):
    png = os.path.join(set_dir, "pages", page + ".png")
    truth = open(os.path.join(set_dir, "ground_truth", page + ".txt"), encoding="utf-8").read()
    wpath = os.path.join(set_dir, "ground_truth", page + ".words.txt")
    truth_words = open(wpath, encoding="utf-8").read() if os.path.exists(wpath) else None
    img = base64.b64encode(open(png, "rb").read()).decode("ascii")
    cross = ocr_text(png) if opts["cross"] == "ocr" else ""
    text = f"PDF page {n} of {total}.\n\nText layer (cross-check only):\n(none)\n\nOCR (cross-check only):\n{cross or '(none)'}"
    rec = {"page": page, "requests": 0, "rate_limited": 0, "seconds": 0.0, "in_tokens": 0, "out_tokens": 0,
           "error": "", "json_ok": False, "scores": None}
    resp = None
    for attempt in range(opts["retries"] + 1):
        if opts["_sent"][0]:
            time.sleep(opts["sleep"])
        opts["_sent"][0] += 1
        rec["requests"] += 1
        t0 = time.monotonic()
        try:
            resp = one_request(run, img, text, opts["bases"].get(run["provider"]))
            rec["seconds"] += time.monotonic() - t0
            rec["error"] = ""
            break
        except Exception as e:
            rec["seconds"] += time.monotonic() - t0
            rec["error"] = str(e)[:300]
            code = re.match(r"HTTP (\d+)", rec["error"])
            if code and code.group(1) == "429": rec["rate_limited"] += 1
            retry = (code and code.group(1) in ("429", "500", "502", "503", "504")) or rec["error"].startswith("network")
            if not retry or attempt == opts["retries"]:
                break
            time.sleep(opts["retry_wait"] * (attempt + 1))
    rec["seconds"] = round(rec["seconds"], 2)
    if resp is None:
        return rec
    u = resp.get("usageMetadata") or {}
    rec["in_tokens"] = int(u.get("promptTokenCount") or 0)
    rec["out_tokens"] = int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)
    try:
        _d, _f, blocks, _i, _o = pv.page_blocks(resp)
        got = blocks_text(blocks)
        rec["json_ok"] = True
    except Exception as e:  # not the asked JSON: still scored on the raw answer, flagged
        got = raw_text(resp)
        rec["error"] = f"answer not valid page JSON: {str(e)[:120]}"
    os.makedirs(raw_dir, exist_ok=True)
    open(os.path.join(raw_dir, page + ".txt"), "w", encoding="utf-8").write(got)
    rec["scores"] = score(truth, got, truth_words)
    return rec


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def summarise(pages):
    ok = [p for p in pages if p["scores"]]
    s = lambda k: mean([p["scores"][k] for p in ok])
    return {"pages": len(pages), "pages_answered": len(ok), "pages_json_ok": sum(p["json_ok"] for p in pages),
            "number_recall": s("number_recall"), "date_recall": s("date_recall"), "word_recall": s("word_recall"),
            "cer": s("cer"), "invented_per_page": s("invented"),
            "sec_per_page": mean([p["seconds"] for p in ok]), "seconds_total": round(sum(p["seconds"] for p in pages), 1),
            "requests": sum(p["requests"] for p in pages), "rate_limited_429": sum(p["rate_limited"] for p in pages),
            "in_tokens": sum(p["in_tokens"] for p in pages), "out_tokens": sum(p["out_tokens"] for p in pages),
            "errors": sum(1 for p in pages if p["error"])}


def cmd_run(argv):
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    if len(pos) < 2:
        print(__doc__); return 2
    set_dir, out = pos[0], pos[1]
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    bases = {}
    for i, a in enumerate(argv):
        if a == "--base":
            p, _, u = argv[i + 1].partition("="); bases[p] = u
    opts = {"sleep": float(opt("--sleep", 4)), "retries": int(opt("--retries", 2)), "retry_wait": float(opt("--retry-wait", 20)),
            "cross": opt("--cross", "none"), "bases": bases, "_sent": [0]}
    manifest = json.load(open(os.path.join(set_dir, "manifest.json"), encoding="utf-8"))
    pages = [p["id"] for p in manifest["pages"]]
    if "--pages" in argv:
        want = opt("--pages", "").split(",")
        pages = [p for p in pages if p in want]
    kinds = {p["id"]: p.get("kind", "") for p in manifest["pages"]}
    results = {"set": os.path.abspath(set_dir), "pages": pages,
               "settings": {k: v for k, v in opts.items() if not k.startswith("_") and k != "bases"} | {"base_overrides": sorted(bases)},
               "runs": [], "skipped": []}
    for run in parse_runs(opt("--providers", "")):
        why = missing(run["provider"], bases)
        if why:
            results["skipped"].append({"run": run["label"], "reason": why}); print(f"SKIP {run['label']}: {why}"); continue
        recs = []
        for n, page in enumerate(pages, 1):
            r = run_page(run, page, n, len(pages), set_dir, opts, os.path.join(out, "raw", re.sub(r"[^A-Za-z0-9._-]", "_", run["label"])))
            r["kind"] = kinds.get(page, "")
            recs.append(r)
            sc = r["scores"] or {}
            print(f"{run['label']} {page}: {r['seconds']}s req {r['requests']} 429x{r['rate_limited']} "
                  + (f"num {sc.get('number_recall')} words {sc.get('word_recall')} cer {sc.get('cer')}" if sc else "FAILED " + r["error"][:120]))
        by_kind = {k: summarise([r for r in recs if r["kind"] == k]) for k in sorted({r["kind"] for r in recs}) if k}
        results["runs"].append(dict(run, summary=summarise(recs), by_kind=by_kind, pages=recs))
    os.makedirs(out, exist_ok=True)
    json.dump(results, open(os.path.join(out, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    report(out)
    print(f"results: {out}/results.json, results.md, results.png  ({len(results['runs'])} run(s), {len(results['skipped'])} skipped)")
    return 0


# ---------------------------------------------------------------- report + chart
def f2(x, pct=False):
    if x is None: return "–"
    return f"{x * 100:.1f}%" if pct else f"{x:g}"


def report(out):
    res = json.load(open(os.path.join(out, "results.json"), encoding="utf-8"))
    L = ["# AI benchmark — Test A (page reading)", "",
         f"Pages: {len(res['pages'])} ({', '.join(res['pages'])}). Settings: {json.dumps(res['settings'], ensure_ascii=False)}", "",
         "| Run | pages answered / JSON ok | number recall | date recall | word recall | CER (lower = better) | invented numbers / page | sec / page | requests | 429s | tokens in / out | errors |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["runs"]:
        s = r["summary"]
        L.append(f"| {r['label']} | {s['pages_answered']}/{s['pages']} / {s['pages_json_ok']} | {f2(s['number_recall'], 1)} | {f2(s['date_recall'], 1)} | "
                 f"{f2(s['word_recall'], 1)} | {f2(s['cer'], 1)} | {f2(s['invented_per_page'])} | {f2(s['sec_per_page'])} | {s['requests']} | "
                 f"{s['rate_limited_429']} | {s['in_tokens']} / {s['out_tokens']} | {s['errors']} |")
    for r in res["runs"]:
        if len(r.get("by_kind") or {}) > 1:
            L += ["", f"**{r['label']}** by page kind: " + "; ".join(
                f"{k}: numbers {f2(v['number_recall'], 1)}, words {f2(v['word_recall'], 1)}, CER {f2(v['cer'], 1)}" for k, v in r["by_kind"].items())]
    if res["skipped"]:
        L += ["", "Skipped (no key / URL): " + "; ".join(f"{s['run']} — {s['reason']}" for s in res["skipped"])]
    L += ["", "Failed pages: " + ("; ".join(f"{r['label']} {p['page']}: {p['error'][:100]}" for r in res["runs"] for p in r["pages"] if p["error"]) or "none")]
    open(os.path.join(out, "results.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    if res["runs"]:
        chart(res, os.path.join(out, "results.png"))


def chart(res, path):
    try:
        import matplotlib
    except ImportError:  # chart is optional; results.json / results.md are the record (CI has no matplotlib)
        print("matplotlib not installed — results.png skipped", file=sys.stderr)
        return
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    runs = res["runs"]
    labels = [r["provider"] + "\n" + r["model"].split("/")[-1][:22] for r in runs]
    metrics = [("number_recall", "Number recall"), ("date_recall", "Date recall"), ("word_recall", "Devanagari word recall"),
               ("char_acc", "1 − CER")]
    colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # categorical slots 1-4 (fixed order)
    vals = lambda k: [((1 - r["summary"]["cer"]) if r["summary"]["cer"] is not None else 0) if k == "char_acc"
                      else (r["summary"][k] or 0) for r in runs]
    fig, axes = plt.subplots(1, 3, figsize=(max(12, 2.4 * len(runs) + 7), 5.4), gridspec_kw={"width_ratios": [3, 1.5, 1.5]})
    ax = axes[0]
    w = 0.8 / len(metrics)
    for i, (k, name) in enumerate(metrics):
        xs = [j + (i - (len(metrics) - 1) / 2) * w for j in range(len(runs))]
        ax.bar(xs, [v * 100 for v in vals(k)], width=w * 0.92, color=colors[i], label=name, edgecolor="white", linewidth=1)
    ax.set_xticks(range(len(runs))); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 105); ax.set_ylabel("% (higher = better)"); ax.set_title("Reading quality vs ground truth", fontsize=10, pad=28)
    ax.legend(fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, ncol=4)
    for a, key, title, col in ((axes[1], "sec_per_page", "Seconds per page", "#2a78d6"),
                               (axes[2], "invented_per_page", "Invented numbers per page\n(lower = better)", "#eb6834")):
        v = [r["summary"][key] or 0 for r in runs]
        a.bar(range(len(runs)), v, color=col, width=0.6)
        for j, x in enumerate(v):
            a.text(j, x, f"{x:.3g}", ha="center", va="bottom", fontsize=8, color="#333")
        a.set_xticks(range(len(runs))); a.set_xticklabels(labels, fontsize=7, rotation=35, ha="right"); a.set_title(title, fontsize=10, pad=28)
    for a in axes:
        a.spines[["top", "right"]].set_visible(False); a.grid(axis="y", color="#e6e6e6", linewidth=0.8); a.set_axisbelow(True)
    fig.suptitle(f"AI benchmark — Test A, {len(res['pages'])} pages", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- Test B helper: facts found in outputs
def doc_text(path):
    if path.lower().endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            xml = " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.startswith("word/") and n.endswith(".xml"))
        xml = re.sub(r"</w:p>|<w:tab/>|<w:br/>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    return open(path, encoding="utf-8", errors="replace").read()


def facts_check(facts, texts):
    body = flat(" ".join(texts))
    body_d = DATE.sub(lambda m: f"{int(m.group(1)):02d}.{int(m.group(2)):02d}.{m.group(3)}", body)
    rows = []
    for f in facts["facts"]:
        if f.get("check") is False:
            continue
        v = flat(f["value"])
        hit = v in body or v in body_d or v.replace(",", "") in body.replace(",", "")
        rows.append({"field": f["field"], "value": f["value"], "found": hit})
    return {"found": sum(r["found"] for r in rows), "total": len(rows), "missing": [r for r in rows if not r["found"]]}


def cmd_facts(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    r = facts_check(json.load(open(argv[0], encoding="utf-8")), [doc_text(p) for p in argv[1:]])
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r["found"] == r["total"] else 1


def main(argv):
    if argv and argv[0] == "run": return cmd_run(argv[1:])
    if argv and argv[0] == "facts": return cmd_facts(argv[1:])
    if argv and argv[0] == "report" and len(argv) > 1: report(argv[1]); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
