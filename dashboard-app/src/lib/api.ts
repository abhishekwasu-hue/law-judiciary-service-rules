// Calls to the Cloudflare Worker (/api/*, same origin). Auth: Bearer <supabase access_token>.
import { hasSupabase, sb } from './supabase';

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
  [/Settings: GitHub repo\/token and Anthropic key needed/i, 'सेटिंग्जमध्ये GitHub repo/token व Anthropic key भरा'],
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

// ---------- monthly spend limit (Worker GET /api/spend; POST /api/run → 402 monthly_budget_reached) ----------
export interface Spend { month: string; spent_usd: number; limit_usd: number; runs: number }
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
  if (msg === 'run_active') return 'या प्रकरणाची प्रक्रिया आधीच चालू आहे — ती संपेपर्यंत थांबा';
  for (const [re, mr] of MARATHI) if (re.test(msg)) return mr;
  if (looksMarathi(msg)) return msg;
  return GENERIC;
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
export async function uploadFile(caseId: number, kind: 'proposal' | 'extra_doc' | 'reply', file: File, onProgress?: (pct: number) => void): Promise<{ id: number }> {
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
