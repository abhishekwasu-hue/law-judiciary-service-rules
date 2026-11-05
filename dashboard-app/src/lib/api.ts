// Calls to the Cloudflare Worker (/api/*, same origin). Auth: Bearer <supabase access_token>.
import { hasSupabase, sb } from './supabase';
import type { InputKind } from './constants';
import type { Me, Profile } from './types';
import { OWNER_DISPATCH_TEXT, RUN_START_FAIL_TEXT, TECH_TROUBLE_TEXT, DEV_WORDS, looksMarathi, ownerDetail, viewerOwner } from './format';

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
// [pattern, text for everyone, owner text?, tech?]: owner text replaces the first one for the owner; tech = the raw
// message is added for the owner (" (तांत्रिक कारण: …)"). Staff never see developer words (UI audit X2).
export const MARATHI: [RegExp, string, string?, boolean?][] = [
  [/login required|JWT expired|invalid JWT|\b401\b/i, 'कृपया पुन्हा लॉगिन करावे, ही विनंती.'],
  [/not a member/i, 'आपण या कक्षाचे सदस्य नाही.'],
  // S-F6: OTP sign-in with shouldCreateUser:false for an e-mail without an account (GoTrue otp_disabled)
  [/Signups not allowed|otp_disabled|signup.*disabled/i, 'हा ई-मेल कक्षात आमंत्रित नाही. कृपया आमंत्रित ई-मेल नमूद करावा किंवा मालकांना कळवावे, ही विनंती.'],
  [/owner only/i, 'हे काम फक्त मालक करू शकतात.'],
  [/read-only/i, 'आपल्याला फक्त पाहण्याची परवानगी आहे; बदल करता येणार नाहीत.'],
  [/setup code wrong/i, 'सेटअप कोड चुकीचा आहे. कृपया योग्य कोड नमूद करावा, ही विनंती.'],
  [/already configured/i, 'सेटअप आधीच पूर्ण झाला आहे.'],
  [/not configured/i, 'कक्षाची सेटिंग्ज अजून पूर्ण नाहीत. कृपया मालकांना कळवावे, ही विनंती.', 'कक्षाची सेटिंग्ज अजून पूर्ण नाहीत. कृपया सेटिंग्ज भरावीत, ही विनंती.'],
  [/bad token/i, "प्रक्रियेची परवानगी संपली. कृपया 'पुन्हा तयार करा' वापरावे, ही विनंती."],
  [/file over 50 MB|\b413\b/i, 'फाइल 50 MB पेक्षा मोठी आहे. कृपया लहान फाइल निवडावी, ही विनंती.'],
  [/upload the proposal PDF first/i, 'कृपया आधी प्रस्ताव PDF अपलोड करावा, ही विनंती.'],
  [/^Settings: GitHub repo\/token/i, 'प्रक्रिया सुरू होऊ शकली नाही — सेटिंग्ज अपूर्ण आहेत. कृपया मालकांना कळवावे, ही विनंती.',
    'कृपया सेटिंग्जमध्ये GitHub repo/token व AI key (Anthropic किंवा निवडलेल्या AI ची) भरावी, ही विनंती.'],
  [/^invite_failed$/, 'आमंत्रण पाठवता आले नाही. कृपया ई-मेल तपासून पुन्हा प्रयत्न करावा, ही विनंती.'],
  [/^nothing to change$/, 'काहीही बदल नाही.'],
  [/duplicate key|23505/i, 'हा C R क्रमांक / वर्ष आधीच नोंदवलेला आहे.'],
  [/cr_no: digits only/i, 'कृपया C R क्रमांकात फक्त अंक लिहावेत, ही विनंती.'],
  [/cr_year/i, 'कृपया वर्ष 4 अंकी लिहावे (उदा. 2026), ही विनंती.'],
  [/case not found/i, 'हे प्रकरण सापडले नाही; ते काढून टाकलेले असू शकते.'],
  [/not found|\b404\b/i, 'माहिती सापडली नाही.'],
  [/^storage \d+/i, 'फाइल साठवताना त्रुटी आली. कृपया पुन्हा प्रयत्न करावा, ही विनंती.', undefined, true],
  [/^dispatch \d+/i, RUN_START_FAIL_TEXT, OWNER_DISPATCH_TEXT, true],
  [/^db \d+/i, 'माहिती जतन करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करावा, ही विनंती.', undefined, true],
  [/^sign \d+/i, 'फाइल उघडता आली नाही. कृपया पुन्हा प्रयत्न करावा, ही विनंती.', undefined, true],
  [/^search \d+/i, 'नियम-उतारे शोध सध्या होऊ शकला नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.', undefined, true],
  [/HTTP 5\d\d|\b50[0-4]\b/i, 'सर्व्हरमध्ये तात्पुरती त्रुटी आली. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.', undefined, true],
  [/Failed to fetch|NetworkError|Load failed|network|नेटवर्क त्रुटी/i, 'इंटरनेट संपर्क तुटला. कृपया जोडणी तपासून पुन्हा प्रयत्न करावा, ही विनंती.'],
];
const GENERIC = 'तांत्रिक अडचण आली. कृपया पुन्हा प्रयत्न करावा; अडचण राहिल्यास मालकांना कळवावे, ही विनंती.';
/** Staff text of a failed dispatch (the owner gets OWNER_DISPATCH_TEXT through humanError / cleanReason). */
export const DISPATCH_REASON = RUN_START_FAIL_TEXT;

/** Settings keys → Marathi field names (Worker validation errors "<key>: <rule>" / "<key> required"). */
export const SETTING_LABEL: Record<string, string> = {
  owner_email: 'मालकाचा ई-मेल', supabase_url: 'डेटाबेस (Supabase) पत्ता', supabase_anon_key: 'डेटाबेस सार्वजनिक की (anon)', supabase_service_key: 'डेटाबेस सेवा-की (service_role)',
  github_repo: 'प्रक्रिया-भांडार (GitHub repo)', github_branch: 'प्रक्रिया-शाखा (GitHub branch)', github_token: 'प्रक्रिया-परवानगी की (GitHub token)', anthropic_api_key: 'Anthropic AI की',
  model: 'मुख्य मॉडेल', model_light: 'स्वस्त मॉडेल', model_review: 'अंतिम पडताळणी मॉडेल', model_strong: 'उच्च-स्तर मॉडेल', model_edit: 'सुधारणा-चॅटचे मॉडेल', effort: 'विचार-पातळी',
  budget_usd: 'प्रति प्रक्रिया कमाल खर्च ($)', monthly_budget_usd: 'मासिक कमाल खर्च ($)', max_parallel_runs: 'एकाच वेळी चालणारे run (1–3)',
  engine_provider: 'मुख्य प्रक्रिया कोणाकडून', engine_model: 'मुख्य — मॉडेल', engine_model_light: 'मुख्य — स्वस्त मॉडेल',
  fallback_provider: 'राखीव AI', fallback_model: 'राखीव — मॉडेल', fallback_model_light: 'राखीव — स्वस्त मॉडेल',
  part1_provider: 'अभ्यास-फाइल भाग 1 कोणाकडून', part1_model: 'भाग 1 — मॉडेल', gemini_model: 'Gemini मॉडेल',
  cloudflare_account_id: 'Cloudflare खाते क्रमांक', ollama_base_url: 'Ollama पत्ता',
  gemini_api_key: 'Google Gemini की', openai_api_key: 'OpenAI की', openrouter_api_key: 'OpenRouter की', groq_api_key: 'Groq की',
  mistral_api_key: 'Mistral की', cerebras_api_key: 'Cerebras की', cloudflare_api_token: 'Cloudflare की', ollama_api_key: 'Ollama की',
};
/** Worker rule text → what to type (same rules as the Settings page's own checks). */
export const SETTING_RULE: [RegExp, string][] = [
  [/^positive number <= 20$/, 'कृपया 0 पेक्षा जास्त व 20 पर्यंतची संख्या लिहावी, ही विनंती.'],
  [/^positive number <= 1000$/, 'कृपया 0 पेक्षा जास्त व 1000 पर्यंतची संख्या लिहावी (रिकामे = $20), ही विनंती.'],
  [/^one of .* or empty$/, 'कृपया यादीतील पर्याय निवडावा किंवा रिकामे ठेवावे, ही विनंती.'],
  [/^32 hex characters$/, 'कृपया नेमकी 32 अक्षरे (0-9, a-f) लिहावीत, ही विनंती.'],
  [/^http\(s\)/, 'कृपया http:// किंवा https:// ने सुरू होणारा पत्ता लिहावा (उदा. https://host:11434), ही विनंती.'],
  [/^model name or none$/, 'कृपया योग्य मॉडेल-नाव (अक्षरे, अंक, . _ : @ / - ; जागा नाही) किंवा none लिहावे, ही विनंती.'],
  [/^claude model name$/, 'कृपया claude- ने सुरू होणारे मॉडेल-नाव लिहावे (उदा. claude-sonnet-5-5), ही विनंती.'],
  [/^model name$/, 'कृपया योग्य मॉडेल-नाव लिहावे (अक्षरे, अंक, . _ : @ / - ; जागा नाही), ही विनंती.'],
  [/^whole number 1 to 3$/, 'कृपया 1, 2 किंवा 3 निवडावे (रिकामे = 2), ही विनंती.'],
  [/^cannot clear$/, 'ही की काढता येत नाही.'],
];
function settingError(msg: string): string | null {
  const req = /^([a-z0-9_]+) required$/.exec(msg);
  if (req && SETTING_LABEL[req[1]]) return `${SETTING_LABEL[req[1]]}: रिकामे ठेवता येत नाही.`;
  const m = /^([a-z0-9_]+): (.+)$/.exec(msg);
  if (!m || !SETTING_LABEL[m[1]]) return null;
  const rule = SETTING_RULE.find(([re]) => re.test(m[2]));
  return `${SETTING_LABEL[m[1]]}: ${rule ? rule[1] : 'मूल्य योग्य नाही.'}`;
}

// ---------- POST /api/run (C33: may answer {queued: true, position} when every engine slot is busy) ----------
export interface RunStart { id: number; outputs_dropped?: boolean; queued?: boolean; position?: number }
/** Short Marathi text of a /api/run answer: started now, or waiting in the queue at position N.
 *  `isOwner` (optional, default = current viewer): the migration hint only for the owner. */
export function runStartText(r: RunStart, startedText = 'प्रक्रिया सुरू झाली', isOwner = viewerOwner()): string {
  const base = r.queued
    ? `प्रतीक्षा-यादीत क्रमांक ${Number(r.position) || '?'} — आधीच्या प्रक्रियांपैकी एक पूर्ण झाल्यावर ही प्रक्रिया क्रमाने आपोआप सुरू होईल.`
    : startedText;
  if (!r.outputs_dropped) return base;
  return isOwner
    ? `${base} — मसुदे-निवड लागू झाली नाही (migration 0008 बाकी).`
    : `${base} — निवडलेले मसुदे या वेळी लागू झाले नाहीत (तांत्रिक अडचण; कृपया मालकांना कळवावे).`;
}

// ---------- monthly spend limit (Worker GET /api/spend; POST /api/run → 402 monthly_budget_reached) ----------
/** max_parallel: full runs the Worker runs at the same time (KV max_parallel_runs, 1..3; default 2). */
export interface Spend { month: string; spent_usd: number; limit_usd: number; runs: number; reserved_usd?: number; active_runs?: number; max_parallel?: number }
/** Same test as the Worker's /api/run (402): this month's spend + active runs at their estimate reach the limit. */
export const spendBlocked = (s: Spend) => s.spent_usd + (Number(s.reserved_usd) || 0) >= s.limit_usd;
export const getSpend = () => api<Spend>('/api/spend');
export const fmtUsd = (n: number) => `$${(Math.round(n * 100) / 100).toFixed(2)}`;
/** Monthly limit reached. The amount ($) and the Settings hint only for the owner (UI audit X5). */
export const budgetReachedText = (limit: number | null, isOwner = viewerOwner()) =>
  isOwner
    ? `या महिन्याची खर्च-मर्यादा${limit !== null ? ` (${fmtUsd(limit)})` : ''} पूर्ण झाली आहे. कृपया सेटिंग्जमध्ये मर्यादा वाढवावी.`
    : 'या महिन्याची प्रक्रिया-मर्यादा पूर्ण झाली आहे. कृपया मालकांना कळवावे, ही विनंती.';

/** Any error → short Marathi text for a non-technical user. Unknown technical text → generic message.
 *  `isOwner` (optional; default = current viewer, set by DataProvider): the owner also gets the technical part
 *  (Worker `detail`, raw message) — staff never see developer words (UI audit X2). */
export function humanError(e: unknown, isOwner = viewerOwner()): string {
  const msg = e instanceof Error ? e.message : String(e ?? '');
  const data = e instanceof ApiError ? (e.data as { reason?: unknown; detail?: unknown; limit_usd?: unknown } | undefined) : undefined;
  const reason = typeof data?.reason === 'string' ? data.reason : '';
  const detail = typeof data?.detail === 'string' ? data.detail : '';
  const tech = (raw: string) => ownerDetail(raw, isOwner);
  /** A Worker reason meant for the user: as it is; with developer words (old Worker texts) → staff get the generic line. */
  const fromReason = (r: string) => (DEV_WORDS.test(r) ? (isOwner ? r : TECH_TROUBLE_TEXT) : r + tech(detail));
  if (msg === 'monthly_budget_reached') {
    const lim = Number(data?.limit_usd);
    return budgetReachedText(Number.isFinite(lim) ? lim : null, isOwner);
  }
  if (msg === 'migration_missing') {
    if (reason) return fromReason(reason);
    return isOwner ? 'सर्व्हरचा डेटाबेस अद्ययावत नाही (migration बाकी). कृपया migration लागू करावे.' : TECH_TROUBLE_TEXT;
  }
  if (msg === 'profile_unsupported')
    return isOwner ? 'माहिती जतन झाली नाही — सर्व्हर अद्ययावत नाही (Worker deploy बाकी).' : 'माहिती जतन झाली नाही (तांत्रिक अडचण). कृपया मालकांना कळवावे, ही विनंती.';
  if (msg === 'no_spec')
    return reason ? fromReason(reason) : "हे प्रकरण या सुविधेपूर्वीचे असल्याने सुधारणा-फाइल उपलब्ध नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.";
  if (msg === 'run_active') return 'या प्रकरणाची प्रक्रिया आधीच चालू आहे. कृपया ती पूर्ण होईपर्यंत थांबावे, ही विनंती.';
  if (msg === 'dispatch_failed') return isOwner ? OWNER_DISPATCH_TEXT + tech(detail) : RUN_START_FAIL_TEXT;
  if (msg === 'duplicate_cr') {
    const id = e instanceof ApiError ? Number((e.data as { existing_id?: unknown } | undefined)?.existing_id) : NaN;
    return `हा C R क्र. / वर्ष आधीच प्रकरण क्र. ${Number.isFinite(id) ? id : '?'} मध्ये नोंदवलेला आहे.`;
  }
  // any refusal that carries a Marathi `reason` (Worker 409s: no_spec, migration_missing, bad attachment, search …)
  if (reason && looksMarathi(reason)) return fromReason(reason);
  const se = settingError(msg);
  if (se) return se;
  for (const [re, mr, owner, isTech] of MARATHI) if (re.test(msg)) return (isOwner && owner ? owner : mr) + (isTech ? tech(msg) : '');
  if (looksMarathi(msg)) return DEV_WORDS.test(msg) && !isOwner ? TECH_TROUBLE_TEXT : msg + tech(detail);
  return GENERIC + tech(msg);
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
export async function uploadFile(caseId: number, kind: InputKind | 'gr', file: File, onProgress?: (pct: number) => void): Promise<{ id: number }> {
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
  if (!r.ok) throw new ApiError(r.status, `sign ${r.status}`); // → 'फाइल उघडता आली नाही …' (+ code for the owner)
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
