// Calls to the Cloudflare Worker (/api/*, same origin). Auth: Bearer <supabase access_token>.
import { hasSupabase, sb } from './supabase';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function token(): Promise<string | null> {
  if (!hasSupabase()) return null;
  const { data } = await sb().auth.getSession();
  return data.session?.access_token ?? null;
}

const MARATHI: [RegExp, string][] = [
  [/login required/, 'कृपया पुन्हा लॉगिन करा'],
  [/not a member/, 'आपण या कक्षाचे सदस्य नाही'],
  [/owner only/, 'फक्त मालकासाठी'],
  [/read-only/, 'आपल्याला फक्त वाचण्याची परवानगी आहे'],
  [/setup code wrong/, 'सेटअप कोड चुकीचा'],
  [/already configured/, 'सेटअप आधीच झाला आहे'],
  [/file over 50 MB/, 'फाइल 50 MB पेक्षा मोठी'],
  [/upload the proposal PDF first/, 'आधी प्रस्ताव PDF अपलोड करा'],
  [/Settings: GitHub repo\/token and Anthropic key needed/, 'सेटिंग्जमध्ये GitHub repo/token व Anthropic key भरा'],
  [/duplicate key|23505/, 'हा C R क्रमांक/वर्ष आधीच नोंदवलेला आहे'],
];
export function humanError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  for (const [re, mr] of MARATHI) if (re.test(msg)) return mr;
  return msg;
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
    throw new ApiError(r.status, m);
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
