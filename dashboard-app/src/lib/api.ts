// Calls to the Cloudflare Worker (/api/*, same origin). Auth: Bearer <supabase access_token>.
import { hasSupabase, sb } from './supabase';
import type { InputKind } from './constants';
import type { Me, Profile } from './types';

export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message);
  }
}

async function token(): Promise<string | null> {
  if (!hasSupabase()) return null;
  const { data } = await sb().auth.getSession();
  return data.session?.access_token ?? null;
}

// Order matters: specific messages first, generic (status codes, network) last.
export const MARATHI: [RegExp, string][] = [
  [/login required|JWT expired|invalid JWT|\b401\b/i, 'कृपया पुन्हा लॉगिन करा'],
  [/not a member/i, 'आपण या कक्षाचे सदस्य नाही'],
  [/owner only/i, 'हे काम फक्त मालक (owner) करू शकतात'],
  [/read-only/i, 'आपल्याला फक्त पाहण्याची परवानगी आहे — बदल करता येणार नाही'],
  [/setup code wrong/i, 'सेटअप कोड चुकीचा'],
  [/already configured/i, 'सेटअप आधीच झाला आहे'],
  [/not configured/i, 'app ची सेटिंग्ज अजून पूर्ण नाहीत — मालकाने सेटिंग्ज भरावीत'],
  [/bad token/i, 'प्रक्रियेची परवानगी संपली — पुन्हा तयार करा'],
  [/file over 50 MB|\b413\b/i, 'फाइल 50 MB पेक्षा मोठी आहे — लहान फाइल निवडा'],
  [/upload the proposal PDF first/i, 'आधी प्रस्ताव PDF अपलोड करा'],
  [/^Settings: GitHub repo\/token/i, 'सेटिंग्जमध्ये GitHub repo/token व AI key (Anthropic किंवा निवडलेल्या AI ची) भरा'],
  [/^invite_failed$/, 'आमंत्रण पाठवता आले नाही — ई-मेल तपासून पुन्हा प्रयत्न करा'],
  [/^nothing to change$/, 'काहीही बदल नाही'],
  [/duplicate key|23505/i, 'हा C R क्रमांक/वर्ष आधीच नोंदवलेला आहे'],
  [/cr_no: digits only/i, 'C R क्रमांकात फक्त अंक लिहा'],
  [/cr_year/i, 'वर्ष 4 अंकी लिहा (उदा. 2026)'],
  [/case not found/i, 'हे प्रकरण सापडले नाही (कदाचित काढून टाकले असेल)'],
  [/not found|\b404\b/i, 'माहिती सापडली नाही'],
  [/^storage \d+/i, 'फाइल साठवताना त्रुटी आली — पुन्हा प्रयत्न करा'],
  [/^dispatch \d+/i, 'प्रक्रिया सुरू करता आली नाही — सेटिंग्जमधील GitHub token तपासा व पुन्हा तयार करा'],
  [/^db \d+/i, 'माहिती जतन करताना त्रुटी आली — पुन्हा प्रयत्न करा'],
  [/^sign \d+/i, 'फाइल उघडता आली नाही — पुन्हा प्रयत्न करा'],
  [/HTTP 5\d\d|\b50[0-4]\b/i, 'सर्व्हरमध्ये तात्पुरती त्रुटी — थोड्या वेळाने पुन्हा प्रयत्न करा'],
  [/Failed to fetch|NetworkError|Load failed|network|नेटवर्क त्रुटी/i, 'इंटरनेट/नेटवर्क संपर्क तुटला — जोडणी तपासून पुन्हा प्रयत्न करा'],
];
const GENERIC = 'तांत्रिक त्रुटी — पुन्हा प्रयत्न करा';
export const DISPATCH_REASON = 'GitHub जोडणी अयशस्वी (token तपासा — सेटिंग्ज) — पुन्हा तयार करा';

/** Settings keys → Marathi field names (Worker validation errors "<key>: <rule>" / "<key> required"). */
export const SETTING_LABEL: Record<string, string> = {
  owner_email: 'मालकाचा ई-मेल', supabase_url: 'Supabase URL', supabase_anon_key: 'Supabase anon key', supabase_service_key: 'Supabase service_role key',
  github_repo: 'GitHub repo', github_branch: 'GitHub branch', github_token: 'GitHub token', anthropic_api_key: 'Anthropic API key',
  model: 'मुख्य मॉडेल', model_light: 'स्वस्त मॉडेल', model_review: 'अंतिम पडताळणी मॉडेल', model_strong: 'उच्च-स्तर मॉडेल', effort: 'विचार-पातळी',
  budget_usd: 'कमाल खर्च ($)', monthly_budget_usd: 'मासिक कमाल खर्च ($)',
  engine_provider: 'मुख्य अभ्यास कोणाकडून', engine_model: 'मुख्य — मॉडेल', engine_model_light: 'मुख्य — स्वस्त मॉडेल',
  fallback_provider: 'राखीव AI', fallback_model: 'राखीव — मॉडेल', fallback_model_light: 'राखीव — स्वस्त मॉडेल',
  part1_provider: 'Study भाग 1 कोणाकडून', part1_model: 'भाग 1 — मॉडेल', gemini_model: 'Gemini मॉडेल',
  cloudflare_account_id: 'Cloudflare account id', ollama_base_url: 'Ollama पत्ता',
  gemini_api_key: 'Google Gemini API key', openai_api_key: 'OpenAI API key', openrouter_api_key: 'OpenRouter API key', groq_api_key: 'Groq API key',
  mistral_api_key: 'Mistral API key', cerebras_api_key: 'Cerebras API key', cloudflare_api_token: 'Cloudflare API token', ollama_api_key: 'Ollama key',
};
/** Worker rule text → what to type (same rules as the Settings page's own checks). */
export const SETTING_RULE: [RegExp, string][] = [
  [/^positive number <= 20$/, '0 पेक्षा जास्त व 20 पर्यंतची संख्या लिहा'],
  [/^positive number <= 1000$/, '0 पेक्षा जास्त व 1000 पर्यंतची संख्या लिहा (रिकामे = $20)'],
  [/^one of .* or empty$/, 'यादीतील पर्याय निवडा किंवा रिकामे ठेवा'],
  [/^32 hex characters$/, 'नेमकी 32 अक्षरे (0-9, a-f) लिहा'],
  [/^http\(s\)/, 'http:// किंवा https:// ने सुरू होणारा पत्ता लिहा (उदा. https://host:11434)'],
  [/^model name or none$/, 'योग्य मॉडेल-नाव (अक्षरे, अंक, . _ : @ / - ; जागा नाही) किंवा none लिहा'],
  [/^model name$/, 'योग्य मॉडेल-नाव लिहा (अक्षरे, अंक, . _ : @ / - ; जागा नाही)'],
  [/^cannot clear$/, 'ही की काढता येत नाही'],
];
function settingError(msg: string): string | null {
  const req = /^([a-z0-9_]+) required$/.exec(msg);
  if (req && SETTING_LABEL[req[1]]) return `${SETTING_LABEL[req[1]]}: रिकामे ठेवता येत नाही`;
  const m = /^([a-z0-9_]+): (.+)$/.exec(msg);
  if (!m || !SETTING_LABEL[m[1]]) return null;
  const rule = SETTING_RULE.find(([re]) => re.test(m[2]));
  return `${SETTING_LABEL[m[1]]}: ${rule ? rule[1] : 'मूल्य योग्य नाही'}`;
}

// ---------- POST /api/run (C33: may answer {queued: true, position} when another case's run is active) ----------
export interface RunStart { id: number; outputs_dropped?: boolean; queued?: boolean; position?: number }
/** Short Marathi text of a /api/run answer: started now, or waiting in the sequential queue at position N. */
export function runStartText(r: RunStart, startedText = 'अभ्यास सुरू झाला'): string {
  const base = r.queued ? `रांगेत — क्रमांक ${Number(r.position) || '?'} (आधीची प्रक्रिया संपल्यावर आपोआप सुरू होईल)` : startedText;
  return r.outputs_dropped ? `${base} — मसुदे-निवड लागू झाली नाही (migration 0008 बाकी)` : base;
}

// ---------- monthly spend limit (Worker GET /api/spend; POST /api/run → 402 monthly_budget_reached) ----------
export interface Spend { month: string; spent_usd: number; limit_usd: number; runs: number; reserved_usd?: number; active_runs?: number }
/** Same test as the Worker's /api/run (402): this month's spend + active runs at their estimate reach the limit. */
export const spendBlocked = (s: Spend) => s.spent_usd + (Number(s.reserved_usd) || 0) >= s.limit_usd;
export const getSpend = () => api<Spend>('/api/spend');
export const fmtUsd = (n: number) => `$${(Math.round(n * 100) / 100).toFixed(2)}`;
export const budgetReachedText = (limit: number | null) =>
  `या महिन्याची खर्च-मर्यादा${limit !== null ? ` (${fmtUsd(limit)})` : ''} संपली — सेटिंग्जमध्ये मर्यादा वाढवा`;
/** Message already meant for the user (Devanagari, no English sentence / JSON / code). */
const looksMarathi = (m: string) => /[ऀ-ॿ]/.test(m) && !/[{}[\]]|\b[a-z]+ [a-z]+ [a-z]+\b/i.test(m);

/** Any error → short Marathi text for a non-technical user. Unknown technical text → generic message. */
export function humanError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e ?? '');
  if (msg === 'monthly_budget_reached') {
    const lim = e instanceof ApiError ? Number((e.data as { limit_usd?: unknown } | undefined)?.limit_usd) : NaN;
    return budgetReachedText(Number.isFinite(lim) ? lim : null);
  }
  if (msg === 'migration_missing') {
    const r = e instanceof ApiError ? (e.data as { reason?: unknown } | undefined)?.reason : undefined;
    return typeof r === 'string' && r ? r : 'सर्व्हरचा डेटाबेस अद्ययावत नाही (migration बाकी) — मालकाने migration लागू करावे';
  }
  if (msg === 'profile_unsupported') return 'सर्व्हर अद्ययावत नाही — माहिती जतन झाली नाही (Worker deploy बाकी)';
  if (msg === 'run_active') return 'या प्रकरणाची प्रक्रिया आधीच चालू आहे — ती संपेपर्यंत थांबा';
  if (msg === 'dispatch_failed') return DISPATCH_REASON;
  if (msg === 'duplicate_cr') {
    const id = e instanceof ApiError ? Number((e.data as { existing_id?: unknown } | undefined)?.existing_id) : NaN;
    return `हा C R क्र. / वर्ष आधीच प्रकरण #${Number.isFinite(id) ? id : '?'} मध्ये आहे`;
  }
  const se = settingError(msg);
  if (se) return se;
  for (const [re, mr] of MARATHI) if (re.test(msg)) return mr;
  if (looksMarathi(msg)) return msg;
  return GENERIC;
}

/** PATCH /api/me — the user's own profile. An old Worker answers PATCH like GET (no `profile`) → treated as not saved. */
export async function saveProfile(p: Partial<Profile>): Promise<Me> {
  const m = await api<Me>('/api/me', { method: 'PATCH', body: p });
  if (!m || !m.profile) throw new ApiError(501, 'profile_unsupported');
  return m;
}

export async function api<T = unknown>(path: string, opt: { method?: string; body?: unknown } = {}): Promise<T> {
  const t = await token();
  const headers: Record<string, string> = {};
  if (t) headers.Authorization = `Bearer ${t}`;
  if (opt.body !== undefined) headers['content-type'] = 'application/json';
  const r = await fetch(path, {
    method: opt.method || (opt.body !== undefined ? 'POST' : 'GET'),
    headers,
    body: opt.body !== undefined ? JSON.stringify(opt.body) : undefined,
  });
  const text = await r.text();
  let j: unknown = null;
  try {
    j = text ? JSON.parse(text) : null;
  } catch {
    j = null;
  }
  if (!r.ok) {
    const m = j && typeof j === 'object' && 'error' in j ? String((j as { error: unknown }).error) : `HTTP ${r.status}`;
    throw new ApiError(r.status, m, j);
  }
  return j as T;
}

/** Raw-body upload with progress (XHR so upload.onprogress works). */
export async function uploadFile(caseId: number, kind: InputKind, file: File, onProgress?: (pct: number) => void): Promise<{ id: number }> {
  const t = await token();
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open('POST', `/api/upload?case_id=${caseId}&kind=${kind}`);
    if (t) x.setRequestHeader('Authorization', `Bearer ${t}`);
    x.setRequestHeader('x-file-name', encodeURIComponent(file.name));
    x.setRequestHeader('content-type', file.type || 'application/octet-stream');
    x.upload.onprogress = e => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    x.onload = () => {
      let j: { error?: string; id?: number } = {};
      try {
        j = JSON.parse(x.responseText || '{}');
      } catch {
        /* ignore */
      }
      if (x.status >= 200 && x.status < 300) resolve(j as { id: number });
      else reject(new ApiError(x.status, j.error || `HTTP ${x.status}`));
    };
    x.onerror = () => reject(new ApiError(0, 'नेटवर्क त्रुटी'));
    x.send(file);
  });
}

export const fileUrl = (id: number, download = false) =>
  api<{ url: string; name: string }>(`/api/files/${id}${download ? '?download=1' : ''}`);

export async function fileBytes(id: number): Promise<{ data: ArrayBuffer; name: string }> {
  const { url, name } = await fileUrl(id);
  const r = await fetch(url);
  if (!r.ok) throw new Error(`फाइल मिळाली नाही (${r.status})`);
  return { data: await r.arrayBuffer(), name };
}

/** Download with the original file name (the Worker adds &download=<original name> to the signed URL). */
export async function downloadFile(id: number): Promise<void> {
  const { url, name } = await fileUrl(id, true);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}
