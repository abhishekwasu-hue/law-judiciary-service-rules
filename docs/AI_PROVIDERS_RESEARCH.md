# AI_PROVIDERS_RESEARCH.md — other AI providers / free models for the प्रस्ताव कक्ष engine (research 02.11.2026; discussion only, nothing built)

Abhi (02.11.2026): "AI api key sarv paid models aahet, option thewa, google gemini, chatgpt aani other free model aslyas web research karun sanga" + "kase fit krta yeil charcha kra".

## 1. Facts found (official pages unless marked)
| Provider | Free? | Confidential data on free tier | Paid price $/1M tok (in / out) | Source |
|---|---|---|---|---|
| Anthropic (now) | No | API data not used for training | Opus 5.5 4/20, Sonnet 5.5 2/10, Haiku 5.5 0.10/0.50 (QUALITY_AUDIT §6, models table 2026-10-06) | — |
| Google Gemini API | Yes (free tier; limits shown only in AI Studio) | **Free tier: content used to improve Google products; human reviewers may read it; terms: "Do not submit sensitive, confidential, or personal information to the Unpaid Services."** Paid: not used | 3.8 Flash 0.75/3.75 (to 31.12.2026; 1.50/7.50 from 2027); 3.5 Flash-Lite 0.30/2.50; 2.5 Pro 1.25/10; 2.5 Flash-Lite 0.10/0.40 | ai.google.dev/gemini-api/terms, /docs/pricing |
| Gemini CLI (Google login) | 1,000 req/day | free = unpaid terms above | — | geminicli.com quota page: for unpaid users "Gemini CLI was replaced by Antigravity CLI on June 18th, 2026" |
| OpenAI (ChatGPT) API | **No free tier** for text models | API data not trained on by default (secondary source: conductatlas.com; primary page not read) | gpt-6.1-sol 2/10, gpt-6.1-terra 1/5, gpt-5.4-mini 0.75/4.50, gpt-5.4-nano 0.20/1.25 | developers.openai.com/api/docs/pricing |
| OpenRouter ":free" models | 50 req/day (1,000 with $10 credit) | depends on host; secondary article: 9 of 19 free models on hosts that may train on prompts | — | openrouter.ai/pricing; blog |
| Cloudflare Workers AI | 10,000 Neurons/day (already have Cloudflare) | data policy not verified | $0.011 / 1,000 Neurons | developers.cloudflare.com (via search) |
| Sarvam AI (India) | ₹100 credit for new users | not verified | Document AI Digitise ₹0.5/page, Extract ₹1/page (docs); Marathi supported | docs.sarvam.ai pricing, changelog |

## 2. How it can fit the engine
- Engine = Claude Code headless (tools, subagents, prompts). Claude Code can call other models only through a gateway (LiteLLM proxy, `ANTHROPIC_BASE_URL`). Translation can lose features (prompt caching, tool fidelity); LiteLLM had a PyPI compromise on 24.03.2026 → pin version. Quality of Marathi verbatim text and scanned-page reading by Gemini/OpenAI for this work: NOT tested.
- Fit A (low risk): extra provider only for machine-checked helper work — page OCR first pass / Study part 1 (part1check), Sarvam or Gemini paid as an OCR cross-check. Drafter + Opus review unchanged.
- Fit B: provider choice per tier in Settings (`provider_<tier>` + key), engine starts LiteLLM when a non-Anthropic provider is chosen. Needs a side-by-side test on an approved case (e.g. CR131) before use.
- Fit C: fallback only — if Anthropic key fails (credit/outage), run on the second provider with a warning on the case.
- Free tiers: not suitable for proposals (Gemini free terms forbid confidential data; OpenRouter limits 50 req/day vs ~80–150 turns per run; hosts may train).

## 3. Open questions (Abhi)
Q1 Which fit (A / B / C)? Default: A, then C.  Q2 May proposal contents go to Google / OpenAI paid APIs (office policy)? Default: ask before use.  Q3 Test case for side-by-side? Default: CR131.

## 4. Decision and build (Abhi 02.11.2026: "AI साठी A व C")
Built: A (Study part 1 on Gemini, `tools/part1_vision.py`) and C (fallback provider through LiteLLM) — APP_B_DESIGN D15.
Defaults: part 1 on Claude; Gemini model gemini-2.5-flash; fallback off; fallback models Gemini 2.5 Pro / 2.5 Flash or
OpenAI gpt-6.1-sol / gpt-5.4-mini. Tested: mock Gemini API (3 tests), LiteLLM gateway reached Google with Claude Code's
requests (fake key → Google's own "API key not valid"), workflow step locally (overload → fallback → proxy → second run).
NOT yet tested: output quality with real Gemini/OpenAI keys — first real use should be on an approved case (e.g. CR131)
and compared with the approved note before relying on it. Q2 (office policy on sending proposals to Google/OpenAI paid
APIs) stays Abhi's: nothing is sent unless he enters a key and chooses the provider.

## 5. Free models (research 02.11.2026, official pages first; Abhi: "फ्री मॉडेल पण युज करता आले पाहिजे")
Run size: 80–200 requests of 40–100k tokens with page images; part 1 alone ~15 image requests.
| Provider (free) | Free limits | Data use on free tier | Verdict |
|---|---|---|---|
| Gemini API unpaid | numbers only in AI Studio | "human reviewers may read…"; "Do not submit sensitive, confidential, or personal information to the Unpaid Services" | not for proposals |
| OpenRouter :free | 20 RPM; 50 RPD (1,000 after $10 credit) | depends on host; NVIDIA free endpoint: "do not upload any confidential information"; account setting excludes training providers | enough requests (with credit), not confidential-safe |
| Groq | Developer table: 30 RPM, 1K RPD, 8K TPM, 200K TPD | "does not retain customer data" by default | too small (8K TPM < one prompt) |
| Cerebras trial | 5 RPM, 30K/90K TPM, 1M TPD | terms not found | too small for engine; trial |
| Mistral free | not officially stated | "we may use your data … to train" (opt-out) | not without opt-out |
| GitHub Models | "fully retired" 30.07.2026 | — | gone |
| Cloudflare Workers AI | 10,000 Neurons/day | "does not use Customer Content … to train" | best terms; maybe part 1 (Neurons per page not measured) |
| Hugging Face / Together / DeepInfra | no free credits | — | not free |
| NVIDIA build (NIM) free | prototyping only | logged; "do not upload any confidential information" | no |
| Sarvam (India) | ₹100 credit; Vision ₹1.50/page [S] | API terms not found | short OCR trial only after written terms |
| Own Ollama (e.g. gemma4:12b/26b/31b) | no API cost; GPU machine needed | data stays in office | only free + confidential route; test quality first |
Sources: ai.google.dev (rate-limits, pricing, terms); openrouter.ai/docs (limits, privacy-and-logging), openrouter.ai/api/v1/models;
console.groq.com/docs (rate-limits, your-data); inference-docs.cerebras.ai/support/rate-limits; help.mistral.ai (training article);
docs.github.com (GitHub Models); developers.cloudflare.com/workers-ai (pricing, privacy, models); huggingface.co/docs/inference-providers/pricing;
docs.api.nvidia.com/nim; docs.sarvam.ai/api/ratelimits, sarvam.ai/api-pricing; docs.together.ai/docs/billing; ollama.com/library/gemma4.
Built (D16): all of these except Sarvam/HF/Together/NVIDIA are selectable in Settings (engine / fallback / part 1), with this table shown.
