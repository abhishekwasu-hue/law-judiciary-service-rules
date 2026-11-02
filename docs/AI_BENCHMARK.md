# AI_BENCHMARK.md — AI providers compared on the प्रस्ताव कक्ष engine's work (02.11.2026)

Status: harness built and proven offline against local mock servers (`tests/test_ai_benchmark.py`). **No real provider
has been measured yet** — every number for a real model comes only after Abhi gives keys and the run is done.

Test input = public documents only: Marathi GR pages from `pdf/` (text layer checked against tesseract) and a synthetic
dummy proposal with fake names / numbers ("श्री. अ. ब. चाचणी", "चाचणीनगर"; every page says "चाचणी नमुना — खरी नस्ती नाही").
No proposal, old case, medical bill or precedent text is ever sent.

## 1. Keys / किल्ल्या (Settings किंवा environment मध्ये)
| Provider | Env | Where (मोफत?) |
|---|---|---|
| Gemini | `GEMINI_API_KEY` | aistudio.google.com → Get API key (free tier — public test pages only) |
| OpenRouter | `OPENROUTER_API_KEY` | openrouter.ai → Keys (":free" models, 50 req/day) |
| Groq | `GROQ_API_KEY` | console.groq.com → API Keys (free) |
| Cloudflare Workers AI | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | dash.cloudflare.com → My Profile → API Tokens → Create token with permission **Workers AI** (Read/Edit); account id = 32 hex on the dashboard (free 10,000 Neurons/day) |
| Mistral / Cerebras / OpenAI | `MISTRAL_API_KEY` / `CEREBRAS_API_KEY` / `OPENAI_API_KEY` | their consoles (OpenAI: paid only) |
| Own Ollama | `OLLAMA_BASE_URL` (e.g. `http://<pc>:11434`) | office machine, no key |
| Claude baseline | `ANTHROPIC_API_KEY` | the key the engine already uses |
A provider without its key is skipped and listed in `results.md` ("Skipped").

## 2. Test A — page reading (पान वाचन)
```
python3 tools/ai_benchmark_set.py                 # already built in the repo; rebuild only if pdf/ changes (needs tesseract mar; ~20 min)
export GEMINI_API_KEY=... GROQ_API_KEY=... ANTHROPIC_API_KEY=...
python3 tools/ai_benchmark.py run tests/benchmark_set /tmp/bench_out \
    --providers claude,gemini,groq,openrouter,cloudflare,ollama:gemma4:12b --sleep 4
```
- Same task as `tools/part1_vision.py` (Study part 1): same system prompt, same JSON answer, one 110 dpi PNG per request.
  `provider:model` picks a model; default = the engine's default for that provider (Claude: `claude-haiku-5-5`).
- Free limits: sequential, one request per page, `--sleep` s between requests; 429 / 5xx retried at most `--retries`
  (default 2) after `--retry-wait` (20 s × try). Every request and every 429 is counted.
- `--cross none` (default): the model reads the image alone. `--cross ocr`: tesseract text goes with it, as the engine
  does for a scan. The PDF text layer is never sent (it is the ground truth).
- Output in the out dir: `results.json` (per page), `results.md` (table), `results.png` (grouped bars: number / date /
  word recall, 1−CER; seconds per page; invented numbers per page), `raw/<run>/<page>.txt` (each answer, for a look).
- Scores: number recall, date recall, Devanagari word recall (multisets), character error rate (order-sensitive: a
  table read column-wise scores worse — read it with word recall), invented numbers (numbers not on the page).
- `python3 tools/ai_benchmark.py report <out>` rebuilds the table + chart from results.json.

## 3. Test B — full engine run on the dummy proposal (पूर्ण engine)
Input: `tests/benchmark_set/dummy_proposal/dummy_proposal.pdf` (3 image-only pages: निर्देशपत्र-like cover, District
Judge letter asking the first benefit of the revised assured-progress scheme, a table); truth: `.../facts.json` (21 facts, 20 checked by the `facts` command).
Per provider, one run:
1. Settings → इतर AI: engine provider = the provider, its key (Cloudflare: + account id; Ollama: URL). The workflow
   then runs the whole engine through the pinned LiteLLM gateway (`engine_supabase.py litellm_config`).
2. Upload `dummy_proposal.pdf` as a new case (C R 999/2026) and run it.
3. Record: completed within the free limits? (run status; 429s in the log); lint / verify / review gate pass?; time
   (run duration); requests used (lines of the run's LiteLLM cost file = answers) and cost line.
4. Facts accuracy: `python3 tools/ai_benchmark.py facts tests/benchmark_set/dummy_proposal/facts.json
   <PREFIX>_Study.docx <PREFIX>_Note_and_Letter.docx` → found / total + the missing facts.
5. Delete the dummy case afterwards (it is test data).
Same steps with Claude (engine provider empty) give the baseline.

## 4. Honest limits / मर्यादा
- Ground truth of GR pages = their text layer. Marathi GR text layers carry font-mapping slips (seen while building the
  set: "धवभाग" for "विभाग", "पुरववठा", "महाराष्टट्र"). So: pages with impossible sign sequences are rejected; a page is
  kept only when tesseract reads >= 65 % of its text-layer words; word recall on GR pages is scored only on the
  "confirmed" words (`ground_truth/<id>.words.txt` = text layer ∩ OCR); numbers / dates (ASCII digits) come from the
  text layer. CER on GR pages is against the raw text layer (its slips count as errors) and order-sensitive — the
  exact CER is the dummy-page CER (results.md, by page kind).
- 8 + 3 pages is a small sample; a difference of a few % between two models is not proof. Typed GR pages are easier than
  real scans with stamps and handwriting; the dummy pages are clean renders — none of this measures handwriting.
- Free tiers change their limits; a 429 count shows only what happened on that day with that key.
- Test B needs a real engine run per provider (GitHub Actions minutes; paid Claude review if the gate stays on Opus).
  The research note (AI_PROVIDERS_RESEARCH §5) already found Groq / Cerebras free limits smaller than one engine prompt;
  Test B will show it in numbers.
- Free tiers are still not for real proposals (Gemini terms: no confidential data). A good score here is about ability,
  not permission.

## R5 — local Ollama (Gemma 4) vs tesseract, Study part 1 (02.11.2026)
Machine: 4 CPU, no GPU, Ollama 0.40.13. Set: tests/benchmark_set (8 public GR pages + 3 dummy pages, 11 pages). Chart: docs/ai-benchmark/ollama_gemma4_vs_tesseract.png.

| Engine | Number recall | Date recall | Word recall | CER | Invented numbers/page | s/page |
|---|---|---|---|---|---|---|
| gemma4:e2b (thinking off) | 33.2% | 50.0% | 33.5% | 66.1% | 1.36 | 94 |
| gemma4:e4b (thinking off) | 32.4% | 21.4% | 38.8% | 61.1% | 2.0 | 201 |
| tesseract -l mar | 76.1% | 85.7% | 98.7% | 16.0% | 4.45 | 1.1 |
| tesseract -l mar+eng | 74.3% | 85.7% | 98.3% | 14.9% | 0.45 | 1.9 |

- e2b with thinking on (app default; 3 pages only): numbers 64.0%, words 68.4%, CER 31.7%, ~611 s/page (one page 1372 s > the app's 300 s limit).
- The GR-page word key favours tesseract (it counts words tesseract also reads); on the 3 dummy pages (exact key) e2b: words 76.1% / CER 13.2% vs tesseract 98.7% / 7.4%.
- Not tested: gemma4 12b/26b/31b, GPU machines. CPU was shared with other jobs at times.
- Result on this hardware: Ollama (Gemma 4 small) is not usable for Study part 1.
