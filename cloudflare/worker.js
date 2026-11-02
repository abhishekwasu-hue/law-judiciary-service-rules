// प्रस्ताव कक्ष — Cloudflare Worker (app B). Design: docs/APP_B_DESIGN.md (D1–D7).
// The browser talks only to this Worker and to Supabase (anon key + user JWT, RLS). No key is hard-coded:
// every key/URL lives in KV namespace SETTINGS, entered on the app's Settings screen (owner only).

// Other AI providers (Abhi 02.11.2026: keys for various models, free models too; research docs/AI_PROVIDERS_RESEARCH.md).
// Reached by the engine through a LiteLLM gateway; `ollama` = the office's own self-hosted model server.
const AI_PROVIDERS = ['gemini', 'openai', 'openrouter', 'groq', 'mistral', 'cerebras', 'cloudflare', 'ollama'];
const PROVIDER_KEY = { gemini: 'gemini_api_key', openai: 'openai_api_key', openrouter: 'openrouter_api_key', groq: 'groq_api_key',
  mistral: 'mistral_api_key', cerebras: 'cerebras_api_key', cloudflare: 'cloudflare_api_token', ollama: 'ollama_api_key' };
const SECRET_KEYS = ['supabase_service_key', 'github_token', 'anthropic_api_key', ...Object.values(PROVIDER_KEY)];
const PLAIN_KEYS = ['supabase_url', 'supabase_anon_key', 'github_repo', 'github_branch', 'model', 'model_light', 'model_review', 'budget_usd', 'monthly_budget_usd', 'owner_email',
  // other AI providers (Abhi 02.11.2026, docs/AI_PROVIDERS_RESEARCH.md: A = Study part 1 on Gemini, C = fallback when Claude fails)
  'part1_provider', 'gemini_model', 'part1_model', 'fallback_provider', 'fallback_model', 'fallback_model_light',
  'engine_provider', 'engine_model', 'engine_model_light', 'cloudflare_account_id', 'ollama_base_url',
  // engine tiers read by tools/engine_supabase.py engine_config (QUALITY_AUDIT §7): escalation model, reasoning effort
  'model_strong', 'effort'];
const PROVIDERS = { part1_provider: ['', 'claude', ...AI_PROVIDERS], fallback_provider: ['', ...AI_PROVIDERS], engine_provider: ['', 'claude', ...AI_PROVIDERS] };
const MODEL_KEYS = ['gemini_model', 'part1_model', 'fallback_model', 'fallback_model_light', 'engine_model', 'engine_model_light'];
// providers this configuration uses (engine / fallback / part 1); 'claude' and '' are Anthropic
const usedProviders = cfg => [...new Set([cfg.engine_provider, cfg.fallback_provider, cfg.part1_provider].filter(p => AI_PROVIDERS.includes(p)))];
const providerReady = (cfg, p) => !!cfg[PROVIDER_KEY[p]] || (p === 'ollama' && !!cfg.ollama_base_url);
// the main run needs the Anthropic key unless another provider (with its key) runs the engine
const engineReady = cfg => (AI_PROVIDERS.includes(cfg.engine_provider) ? providerReady(cfg, cfg.engine_provider) : !!cfg.anthropic_api_key);
const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:@\/-]{1,99}$/;
const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max'];
const REQUIRED_KEYS = ['supabase_url', 'supabase_anon_key', 'owner_email']; // never saved empty (Settings PUT)
const LETTER_STATUS = ['मसुदा', 'पाठवले', 'उत्तर प्राप्त', 'स्मरणपत्र']; // = letters.status CHECK (migration 0001)
const DEFAULT_RUN_USD = 0.75;                   // estimate for a running run when nothing better is known
const isId = v => /^\d+$/.test(String(v ?? ''));
const ALL_KEYS = [...SECRET_KEYS, ...PLAIN_KEYS];
const FILE_KINDS = ['proposal', 'extra_doc', 'reply'];
const MAX_UPLOAD = 50 * 1024 * 1024;
const SIGN_BUCKETS = ['proposals', 'outputs', 'gr-library'];
// Run token (D4): created at dispatch, sent to GitHub in the payload. Single use for /api/engine/config (the secrets);
// after that it is only good for /api/engine/fail and /api/engine/step (THIS run only, return nothing secret) until it expires.
const RUN_TOKEN_TTL = 4 * 3600;                 // > job timeout (180 min) + queue time
const STALE_MS = 3.5 * 3600 * 1000;             // queued/running longer than this = stuck (job timeout 180 min)
const STALE_REASON = 'वेळ संपली — पुन्हा तयार करा';

// PostgREST error: the browser gets only "db <status>" (no table/column text); code/detail stay for the Worker's own checks.
class DbError extends Error {
  constructor(status, body) {
    super(`db ${status}`);
    this.status = status;
    let j = null;
    try { j = JSON.parse(body); } catch { /* not JSON */ }
    this.code = (j && j.code) || '';
    this.detail = j ? [j.message, j.details, j.hint].filter(Boolean).join(' ') : String(body || '');
  }
}

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json; charset=utf-8' } });
const bad = (msg, s = 400) => json({ error: msg }, s);

async function settings(env) {
  const out = {};
  await Promise.all(ALL_KEYS.map(async k => { out[k] = (await env.SETTINGS.get(k)) || ''; }));
  return out;
}
const mask = v => (v ? '••••' + v.slice(-4) : '');
const randomToken = () => [...crypto.getRandomValues(new Uint8Array(24))].map(b => b.toString(16).padStart(2, '0')).join('');

// ---------- Supabase (service role) ----------
function sb(cfg) {
  const h = { apikey: cfg.supabase_service_key, Authorization: `Bearer ${cfg.supabase_service_key}` };
  const base = cfg.supabase_url.replace(/\/$/, '');
  return {
    async rest(path, opt = {}) {
      const r = await fetch(`${base}/rest/v1/${path}`, { ...opt, headers: { ...h, 'content-type': 'application/json', Prefer: 'return=representation', ...(opt.headers || {}) } });
      const t = await r.text();
      if (!r.ok) throw new DbError(r.status, t.slice(0, 500));
      return t ? JSON.parse(t) : null;
    },
    async upload(bucket, path, body, type) {
      const r = await fetch(`${base}/storage/v1/object/${bucket}/${encodePath(path)}`, { method: 'POST', headers: { ...h, 'content-type': type || 'application/octet-stream', 'x-upsert': 'true' }, body });
      if (!r.ok) throw new Error(`storage ${r.status}: ${(await r.text()).slice(0, 200)}`);
    },
    async sign(bucket, path, download) {
      const r = await fetch(`${base}/storage/v1/object/sign/${bucket}/${encodePath(path)}`, { method: 'POST', headers: { ...h, 'content-type': 'application/json' }, body: JSON.stringify({ expiresIn: 600 }) });
      if (!r.ok) throw new Error(`sign ${r.status}`);
      const { signedURL } = await r.json();
      const u = `${base}/storage/v1${signedURL}`;
      return download ? `${u}&download=${encodeURIComponent(download)}` : u;
    },
  };
}
const encodePath = p => p.split('/').map(encodeURIComponent).join('/');

// ---------- auth ----------
async function currentUser(req, cfg) {
  const m = (req.headers.get('authorization') || '').match(/^Bearer (.+)$/);
  if (!m || !cfg.supabase_url || !cfg.supabase_anon_key) return null;
  const r = await fetch(`${cfg.supabase_url.replace(/\/$/, '')}/auth/v1/user`, { headers: { apikey: cfg.supabase_anon_key, Authorization: `Bearer ${m[1]}` } });
  if (!r.ok) return null;
  const u = await r.json();
  const db = sb(cfg);
  const memberRole = async () => {
    const rows = await db.rest(`members?user_id=eq.${encodeURIComponent(u.id)}&select=role`);
    return rows && rows.length ? rows[0].role : null;
  };
  const role = await memberRole();
  if (role) return { id: u.id, email: u.email, role };
  // first sign-in of the owner email given at setup → becomes owner, only with a confirmed e-mail address
  const confirmed = !!(u.email_confirmed_at || u.confirmed_at);
  if (confirmed && cfg.owner_email && u.email && u.email.toLowerCase() === cfg.owner_email.toLowerCase()) {
    // two first requests in parallel: the second insert is ignored (or 409) → read the row the first one wrote
    let ins = null;
    try {
      ins = await db.rest('members', { method: 'POST', body: JSON.stringify({ user_id: u.id, email: u.email, role: 'owner' }), headers: { Prefer: 'resolution=ignore-duplicates,return=representation' } });
    } catch (e) {
      if (!(e instanceof DbError && (e.status === 409 || e.code === '23505'))) throw e;
    }
    if (ins && ins.length) return { id: u.id, email: u.email, role: 'owner' };
    return { id: u.id, email: u.email, role: await memberRole() };
  }
  return { id: u.id, email: u.email, role: null };
}
const canWrite = u => u && (u.role === 'owner' || u.role === 'staff');

async function log(cfg, case_id, actor, action, detail = {}) {
  await sb(cfg).rest('activity', { method: 'POST', body: JSON.stringify({ case_id, actor, action, detail }), headers: { Prefer: 'return=minimal' } });
}

// ---------- engine dispatch (GitHub Actions, server-side only) ----------
async function dispatchRun(env, cfg, run, origin) {
  const token = randomToken();
  const exp = Math.floor(Date.now() / 1000) + RUN_TOKEN_TTL;
  await env.SETTINGS.put(`run_token:${token}`, JSON.stringify({ run_id: String(run.id), used: false, exp }), { expiration: exp });
  const r = await fetch(`https://api.github.com/repos/${cfg.github_repo}/dispatches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${cfg.github_token}`, Accept: 'application/vnd.github+json', 'User-Agent': 'prastav-kaksha' },
    body: JSON.stringify({ event_type: 'process_proposal', client_payload: { case_id: run.case_id, run_id: run.id, token, worker: origin } }),
  });
  if (!r.ok) throw new Error(`dispatch ${r.status}: ${(await r.text()).slice(0, 200)}`);
}

// Token record: JSON {run_id, used, exp}; a plain run id (tokens issued before this change) counts as unused.
async function runToken(env, req) {
  const t = (req.headers.get('authorization') || '').replace(/^Bearer /, '').trim();
  if (!t) return null;
  const v = await env.SETTINGS.get(`run_token:${t}`);
  if (!v) return null;
  let rec;
  try { rec = JSON.parse(v); } catch { rec = null; }
  if (!rec || typeof rec !== 'object') rec = { run_id: String(v), used: false, exp: 0 };
  return { key: `run_token:${t}`, ...rec, run_id: String(rec.run_id) };
}

// Mark runs failed (engine fail without Supabase env, stale-run sweep). Only queued/running rows change.
async function failRuns(cfg, filter, reason, actor = null) {
  const db = sb(cfg);
  const rows = await db.rest(`runs?${filter}&state=in.(queued,running)`, {
    method: 'PATCH', body: JSON.stringify({ state: 'failed', step: reason, finished_at: new Date().toISOString() }),
  });
  if (rows && rows.length)
    await db.rest('activity', { method: 'POST', headers: { Prefer: 'return=minimal' },
      body: JSON.stringify(rows.map(r => ({ case_id: r.case_id, actor, action: 'run_failed', detail: { run_id: r.id, reason } }))) });
  return rows || [];
}

// Single use of the config token, atomic in Postgres (M, QUALITY_AUDIT §7): only the request whose conditional PATCH
// sets runs.config_taken_at gets a row back. true = taken now, false = taken before / no such run,
// null = column not there yet (migration 0005 not applied) → the caller relies on the KV flag alone.
async function takeConfig(cfg, runId) {
  try {
    const rows = await sb(cfg).rest(`runs?id=eq.${Number(runId)}&config_taken_at=is.null`, {
      method: 'PATCH', body: JSON.stringify({ config_taken_at: new Date().toISOString() }), headers: { Prefer: 'return=representation' },
    });
    return !!(rows && rows.length);
  } catch (e) {
    if (e instanceof DbError && (e.code === '42703' || e.code === 'PGRST204' || (/config_taken_at/.test(e.detail) && /does not exist|could not find/i.test(e.detail)))) return null;
    throw e;
  }
}

// ---------- monthly spend (calendar month in India time: IST = UTC+5:30, no DST) ----------
const IST_MS = 5.5 * 3600 * 1000;
function istMonth(nowMs = Date.now()) {
  const d = new Date(nowMs + IST_MS);
  const y = d.getUTCFullYear(), mo = d.getUTCMonth();
  return {
    month: `${y}-${String(mo + 1).padStart(2, '0')}`,
    start: new Date(Date.UTC(y, mo, 1) - IST_MS).toISOString(),
    end: new Date(Date.UTC(y, mo + 1, 1) - IST_MS).toISOString(),
  };
}
// empty (or an invalid stored value) = default $20 (Abhi, 01.11.2026)
const DEFAULT_MONTHLY_USD = 20;
function monthlyLimit(cfg) {
  const v = String(cfg.monthly_budget_usd || '').trim();
  const n = Number(v);
  return v && Number.isFinite(n) && n > 0 ? n : DEFAULT_MONTHLY_USD;
}
// Estimated cost of one run: median cost_usd of this month's finished runs, else the per-run budget, else $0.75.
function runEstimate(cfg, finished) {
  const c = finished.map(r => r.cost_usd).filter(v => v !== null && v !== undefined && v !== '').map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  if (c.length) return c.length % 2 ? c[(c.length - 1) / 2] : (c[c.length / 2 - 1] + c[c.length / 2]) / 2;
  const b = Number(String(cfg.budget_usd || '').trim());
  return String(cfg.budget_usd || '').trim() && Number.isFinite(b) && b > 0 ? b : DEFAULT_RUN_USD;
}
async function monthSpend(cfg) {
  const { month, start, end } = istMonth();
  const rows = (await sb(cfg).rest(`runs?created_at=gte.${encodeURIComponent(start)}&created_at=lt.${encodeURIComponent(end)}&select=cost_usd,created_at,state`)) || [];
  const inMonth = rows.filter(r => r.created_at && istMonth(new Date(r.created_at).getTime()).month === month);
  const spent = inMonth.reduce((t, r) => t + (Number(r.cost_usd) || 0), 0);
  // queued/running runs (not stale) have no cost yet: each is reserved at the estimate, so runs started together
  // cannot jointly pass the limit
  const since = Date.now() - STALE_MS;
  const isActive = r => (r.state === 'queued' || r.state === 'running') && new Date(r.created_at).getTime() > since;
  const active = inMonth.filter(isActive);
  const est = active.length ? runEstimate(cfg, inMonth.filter(r => r.state === 'done' || r.state === 'failed')) : 0;
  const reserved = active.reduce((t, r) => t + Math.max(0, est - (Number(r.cost_usd) || 0)), 0);
  return { month, spent_usd: Math.round(spent * 10000) / 10000, limit_usd: monthlyLimit(cfg), runs: inMonth.length,
    reserved_usd: Math.round(reserved * 10000) / 10000, active_runs: active.length };
}

// ---------- routes ----------
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(req);
    try {
      return await route(req, env, url);
    } catch (e) {
      return bad(String(e.message || e), 500);
    }
  },
};

async function route(req, env, url) {
  const p = url.pathname, M = req.method;
  const cfg = await settings(env);
  const configured = !!(cfg.owner_email && cfg.supabase_url && cfg.supabase_anon_key && cfg.supabase_service_key);

  // public: what the browser needs to start (anon key is public by Supabase design)
  if (p === '/api/public-config' && M === 'GET') {
    return json({ configured, supabase_url: cfg.supabase_url, supabase_anon_key: cfg.supabase_anon_key });
  }

  // first-run setup (D2): setup_code is created in KV; owner reads it in the Cloudflare dashboard
  if (p === '/api/setup' && M === 'GET') {
    if (configured) return json({ configured: true });
    if (!(await env.SETTINGS.get('setup_code'))) await env.SETTINGS.put('setup_code', randomToken().slice(0, 12));
    return json({ configured: false });
  }
  if (p === '/api/setup' && M === 'POST') {
    if (configured) return bad('already configured', 409);
    const b = await req.json();
    const code = await env.SETTINGS.get('setup_code');
    if (!code || b.setup_code !== code) return bad('setup code wrong', 403);
    for (const k of ['owner_email', 'supabase_url', 'supabase_anon_key', 'supabase_service_key']) if (!b[k]) return bad(`${k} required`);
    for (const k of ALL_KEYS) if (b[k]) await env.SETTINGS.put(k, String(b[k]).trim());
    await env.SETTINGS.delete('setup_code');
    return json({ ok: true });
  }

  // engine: config for one run, by the run token (D4) — single use
  if (p === '/api/engine/config' && M === 'GET') {
    const tok = await runToken(env, req);
    if (!tok || tok.used || tok.run_id !== url.searchParams.get('run_id')) return bad('bad token', 403);
    if (!engineReady(cfg) || !cfg.supabase_url || !cfg.supabase_service_key) return bad('config incomplete (Settings)', 412); // token stays unused
    if ((await takeConfig(cfg, tok.run_id)) === false) return bad('bad token', 403);
    const exp = tok.exp || Math.floor(Date.now() / 1000) + RUN_TOKEN_TTL;
    await env.SETTINGS.put(tok.key, JSON.stringify({ run_id: tok.run_id, used: true, exp }), { expiration: exp });
    const out = { anthropic_api_key: cfg.anthropic_api_key, model: cfg.model, model_light: cfg.model_light || '', model_review: cfg.model_review || '', budget_usd: cfg.budget_usd || '', model_strong: cfg.model_strong || '', effort: cfg.effort || '', supabase_url: cfg.supabase_url, supabase_service_key: cfg.supabase_service_key };
    // other providers: a key is sent only when its provider is chosen (A: part 1 on Gemini; C: fallback provider)
    // a provider key leaves the Worker only when that provider is chosen (engine / fallback / part 1)
    for (const pv of usedProviders(cfg)) if (cfg[PROVIDER_KEY[pv]]) out[PROVIDER_KEY[pv]] = cfg[PROVIDER_KEY[pv]];
    for (const k of ['part1_provider', 'gemini_model', 'part1_model', 'fallback_provider', 'fallback_model', 'fallback_model_light',
      'engine_provider', 'engine_model', 'engine_model_light', 'cloudflare_account_id', 'ollama_base_url']) out[k] = cfg[k] || '';
    return json(out);
  }

  // engine: record a failure when the workflow has no Supabase env (e.g. the config step failed). Run token, used or not.
  if (p === '/api/engine/fail' && M === 'POST') {
    const tok = await runToken(env, req);
    const b = await req.json().catch(() => ({}));
    if (!tok || tok.run_id !== String(b.run_id || '')) return bad('bad token', 403);
    if (!cfg.supabase_url || !cfg.supabase_service_key) return bad('not configured', 503);
    const reason = String(b.reason || 'इंजिन अयशस्वी — पुन्हा तयार करा').trim().slice(0, 300);
    const rows = await failRuns(cfg, `id=eq.${Number(tok.run_id)}`, reason);
    return json({ ok: true, changed: rows.length });
  }

  // engine: live progress text from the Claude step, which has no Supabase key (H1, QUALITY_AUDIT §7). Run token,
  // used or not; THIS run only, only while it is queued/running; returns nothing secret.
  if (p === '/api/engine/step' && M === 'POST') {
    const tok = await runToken(env, req);
    const b = await req.json().catch(() => ({}));
    if (!tok || tok.run_id !== String(b.run_id || '')) return bad('bad token', 403);
    if (tok.exp && tok.exp < Math.floor(Date.now() / 1000)) return bad('bad token', 403);
    if (!cfg.supabase_url || !cfg.supabase_service_key) return bad('not configured', 503);
    const step = String(b.step || '').trim().slice(0, 200);
    if (!step) return bad('step required');
    const rows = await sb(cfg).rest(`runs?id=eq.${Number(tok.run_id)}&state=in.(queued,running)`, { method: 'PATCH', body: JSON.stringify({ step }) });
    return json({ ok: true, changed: (rows || []).length });
  }

  if (!configured) return bad('not configured', 503);
  const user = await currentUser(req, cfg);
  if (!user) return bad('login required', 401);
  if (!user.role) return bad('not a member', 403);
  const db = sb(cfg);

  if (p === '/api/me') return json(user);

  // GET /api/spend (members) → {month, spent_usd, limit_usd (empty setting = 20), runs}: runs.cost_usd this IST calendar month
  if (p === '/api/spend' && M === 'GET') {
    const { month, spent_usd, limit_usd, runs } = await monthSpend(cfg);
    return json({ month, spent_usd, limit_usd, runs });
  }

  // POST /api/runs/sweep → runs queued/running for more than 3.5 h are marked failed (called by the app on load)
  if (p === '/api/runs/sweep' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const before = new Date(Date.now() - STALE_MS).toISOString();
    const rows = await failRuns(cfg, `created_at=lt.${encodeURIComponent(before)}`, STALE_REASON, user.id);
    return json({ ok: true, failed: rows.map(r => r.id) });
  }

  if (p === '/api/settings' && M === 'GET') {
    if (user.role !== 'owner') return bad('owner only', 403);
    const out = {};
    for (const k of PLAIN_KEYS) out[k] = cfg[k];
    for (const k of SECRET_KEYS) out[k] = mask(cfg[k]);
    return json(out);
  }
  if (p === '/api/settings' && M === 'PUT') {
    if (user.role !== 'owner') return bad('owner only', 403);
    const b = await req.json();
    // budget_usd: empty = engine default; otherwise a positive number <= 20 (validated before anything is saved)
    if ('budget_usd' in b && b.budget_usd !== null && String(b.budget_usd).trim() !== '') {
      const n = Number(String(b.budget_usd).trim());
      if (!Number.isFinite(n) || n <= 0 || n > 20) return bad('budget_usd: positive number <= 20');
    }
    // monthly_budget_usd: empty = default $20; otherwise a positive number <= 1000
    if ('monthly_budget_usd' in b && b.monthly_budget_usd !== null && String(b.monthly_budget_usd).trim() !== '') {
      const n = Number(String(b.monthly_budget_usd).trim());
      if (!Number.isFinite(n) || n <= 0 || n > 1000) return bad('monthly_budget_usd: positive number <= 1000');
    }
    for (const [k, ok] of Object.entries(PROVIDERS))
      if (k in b && b[k] !== null && !ok.includes(String(b[k]).trim())) return bad(`${k}: one of ${ok.filter(Boolean).join(', ')} or empty`);
    if ('cloudflare_account_id' in b && b.cloudflare_account_id !== null && String(b.cloudflare_account_id).trim() !== '' && !/^[0-9a-f]{32}$/.test(String(b.cloudflare_account_id).trim()))
      return bad('cloudflare_account_id: 32 hex characters');
    if ('ollama_base_url' in b && b.ollama_base_url !== null && String(b.ollama_base_url).trim() !== '' && !/^https?:\/\/[A-Za-z0-9.-]+(:\d+)?(\/[A-Za-z0-9._~\/-]*)?$/.test(String(b.ollama_base_url).trim()))
      return bad('ollama_base_url: http(s)://host[:port][/path]');
    for (const k of MODEL_KEYS)
      if (k in b && b[k] !== null && String(b[k]).trim() !== '' && !MODEL_NAME.test(String(b[k]).trim())) return bad(`${k}: model name`);
    // model_strong: empty / none = off; effort: one of EFFORTS or empty (= engine default)
    if ('model_strong' in b && b.model_strong !== null) {
      const v = String(b.model_strong).trim();
      if (v !== '' && v.toLowerCase() !== 'none' && !MODEL_NAME.test(v)) return bad('model_strong: model name or none');
    }
    if ('effort' in b && b.effort !== null && String(b.effort).trim() !== '' && !EFFORTS.includes(String(b.effort).trim()))
      return bad(`effort: one of ${EFFORTS.join(', ')} or empty`);
    for (const k of REQUIRED_KEYS) if (k in b && b[k] !== null && String(b[k]).trim() === '') return bad(`${k} required`);
    for (const k of ALL_KEYS) {
      if (!(k in b) || b[k] === null) continue;
      const v = String(b[k]).trim();
      if (SECRET_KEYS.includes(k) && (v === '' || v.startsWith('••••'))) continue; // unchanged secret
      await env.SETTINGS.put(k, v);
    }
    return json({ ok: true });
  }

  if (p === '/api/members' && M === 'POST') {
    if (user.role !== 'owner') return bad('owner only', 403);
    const { email, role } = await req.json();
    if (!email || !['staff', 'senior'].includes(role)) return bad('email + role (staff|senior) required');
    const base = cfg.supabase_url.replace(/\/$/, '');
    const r = await fetch(`${base}/auth/v1/invite`, { method: 'POST', headers: { apikey: cfg.supabase_service_key, Authorization: `Bearer ${cfg.supabase_service_key}`, 'content-type': 'application/json' }, body: JSON.stringify({ email }) });
    const j = await r.json();
    if (!r.ok) return bad(`invite ${r.status}: ${j.msg || j.message || ''}`, 502);
    await db.rest('members', { method: 'POST', body: JSON.stringify({ user_id: j.id, email, role }), headers: { Prefer: 'resolution=merge-duplicates' } });
    return json({ ok: true });
  }

  // POST /api/cases {cr_no, cr_year, file_no, subject, category, priority, ...} → case row
  if (p === '/api/cases' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const b = await req.json();
    // all identity fields optional (owner rule 01.11.2026): the engine fills empty ones from the निर्देशपत्र
    if (b.cr_no && !/^\d+$/.test(String(b.cr_no))) return bad('cr_no: digits only');
    if (b.cr_year && !/^\d{4}$/.test(String(b.cr_year))) return bad('cr_year: 4 digits');
    const allowed = ['cr_no', 'cr_year', 'file_no', 'subject', 'category', 'priority', 'employee_name', 'post', 'office', 'received_from', 'received_via', 'inward_date', 'due_date'];
    const row = Object.fromEntries(allowed.filter(k => b[k] !== undefined && b[k] !== '').map(k => [k, b[k]]));
    // duplicate: same year and same number ignoring leading zeros ("021" = "21"); cr_no is stored as given
    const findDup = async () => {
      if (!row.cr_no || !row.cr_year) return null;
      const n = String(row.cr_no).replace(/^0+(?=\d)/, '');
      const dup = await db.rest(`cases?cr_no=match.${encodeURIComponent(`^0*${n}$`)}&cr_year=eq.${encodeURIComponent(row.cr_year)}&select=id&order=id.asc&limit=1`);
      return dup && dup.length ? dup[0].id : null;
    };
    const dupId = await findDup();
    if (dupId !== null) return json({ error: 'duplicate_cr', existing_id: dupId }, 409);
    let c;
    try {
      [c] = await db.rest('cases', { method: 'POST', body: JSON.stringify(row) });
    } catch (e) {
      // a parallel request inserted the same C R between the check and the insert (unique cr_no, cr_year)
      if (e instanceof DbError && (e.status === 409 || e.code === '23505')) return json({ error: 'duplicate_cr', existing_id: await findDup() }, 409);
      throw e;
    }
    await log(cfg, c.id, user.id, 'case_created', { cr: c.cr_no ? `${c.cr_no}/${c.cr_year || ''}` : '' });
    return json(c);
  }

  // POST /api/upload?case_id=&kind=  body = file bytes, header x-file-name (original name, URI-encoded)
  if (p === '/api/upload' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const caseIdRaw = url.searchParams.get('case_id'), kind = url.searchParams.get('kind');
    let name;
    try { name = decodeURIComponent(req.headers.get('x-file-name') || ''); } catch { return bad('x-file-name: bad encoding'); }
    if (!isId(caseIdRaw)) return bad('case_id, kind, x-file-name required');
    const caseId = Number(caseIdRaw);
    if (!caseId || !FILE_KINDS.includes(kind) || !name || /[\\/]/.test(name)) return bad('case_id, kind, x-file-name required');
    const len = Number(req.headers.get('content-length') || 0);
    if (len > MAX_UPLOAD) return bad('file over 50 MB', 413);
    const exists = await db.rest(`cases?id=eq.${caseId}&select=id`);
    if (!exists.length) return bad('case not found', 404); // no orphan object in Storage
    const prev = await db.rest(`case_files?case_id=eq.${caseId}&kind=eq.${kind}&original_name=eq.${encodeURIComponent(name)}&select=version&order=version.desc&limit=1`);
    const version = prev.length ? prev[0].version + 1 : 1;
    // Supabase Storage keys must be ASCII (live 400 InvalidKey on a Devanagari name): store as file<ext>;
    // the real name stays only in case_files.original_name (downloads use it — §4.16).
    const ext = (name.match(/\.[A-Za-z0-9]{1,8}$/) || [''])[0].toLowerCase();
    const path = `${caseId}/${kind}/v${version}-${crypto.randomUUID().slice(0, 8)}/file${ext}`; // unique per upload
    await db.upload('proposals', path, req.body, req.headers.get('content-type'));
    const [f] = await db.rest('case_files', { method: 'POST', body: JSON.stringify({ case_id: caseId, kind, storage_path: `proposals/${path}`, original_name: name, version, uploaded_by: user.id }) });
    await log(cfg, caseId, user.id, 'file_uploaded', { kind, name, version });
    let letter_updated = null, pending_letters = 0;
    if (kind === 'reply') {
      await db.rest(`cases?id=eq.${caseId}`, { method: 'PATCH', body: JSON.stringify({ stage: 'माहिती प्राप्त' }) });
      // The reply answers the pending letter: exactly one sent letter without a reply -> mark it answered.
      // Several pending -> leave them (the UI asks which one).
      const pend = (await db.rest(`letters?case_id=eq.${caseId}&sent_date=not.is.null&reply_received_date=is.null&select=id`)) || [];
      pending_letters = pend.length;
      if (pend.length === 1) {
        const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' }); // YYYY-MM-DD
        await db.rest(`letters?id=eq.${pend[0].id}`, { method: 'PATCH', body: JSON.stringify({ reply_received_date: today, status: 'उत्तर प्राप्त' }) });
        letter_updated = pend[0].id;
        await log(cfg, caseId, user.id, 'letter_reply_received', { letter_id: letter_updated, date: today });
      }
    }
    return json({ ...f, letter_updated, pending_letters });
  }

  // POST /api/run {case_id, instructions} → runs row + dispatch
  if (p === '/api/run' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    if (!cfg.github_repo || !cfg.github_token || !engineReady(cfg)) return bad('Settings: GitHub repo/token and the AI key (Anthropic or the chosen engine provider) needed', 412);
    const { case_id, instructions } = await req.json();
    if (!isId(case_id)) return bad('case_id required');
    const has = await db.rest(`case_files?case_id=eq.${case_id}&kind=eq.proposal&select=id&limit=1`);
    if (!has.length) return bad('upload the proposal PDF first');
    // monthly limit: once this month's spend reached it, no new run is dispatched (runs already going finish)
    const sp = await monthSpend(cfg);
    // queued/running runs count at their estimate (reserved_usd), so several runs started together cannot pass it
    if (sp.spent_usd + sp.reserved_usd >= sp.limit_usd) return json({ error: 'monthly_budget_reached', spent_usd: sp.spent_usd, limit_usd: sp.limit_usd, reserved_usd: sp.reserved_usd }, 402);
    // one run at a time per case (H3, QUALITY_AUDIT §7): a double tap / second tab / second user would start a second,
    // paid run. Runs older than STALE_MS are stuck (swept), so they do not block.
    const since = new Date(Date.now() - STALE_MS).toISOString();
    const active = await db.rest(`runs?case_id=eq.${case_id}&state=in.(queued,running)&created_at=gt.${encodeURIComponent(since)}&select=id&order=created_at.desc&limit=1`);
    if (active && active.length) return json({ error: 'run_active', run_id: active[0].id }, 409);
    const [run] = await db.rest('runs', { method: 'POST', body: JSON.stringify({ case_id, instructions: instructions || null, created_by: user.id }) });
    try {
      await dispatchRun(env, cfg, run, url.origin);
    } catch (e) {
      await db.rest(`runs?id=eq.${run.id}`, { method: 'PATCH', body: JSON.stringify({ state: 'failed', step: String(e.message).slice(0, 200) }) });
      throw e;
    }
    await db.rest(`cases?id=eq.${case_id}`, { method: 'PATCH', body: JSON.stringify({ stage: 'अभ्यास चालू' }) });
    await log(cfg, case_id, user.id, 'run_started', { run_id: run.id, instructions: instructions || '' });
    return json(run);
  }

  // GET /api/files/:id → signed URL (10 min); ?download=1 keeps the original name
  let m = p.match(/^\/api\/files\/(\d+)$/);
  if (m && M === 'GET') {
    const [f] = await db.rest(`case_files?id=eq.${m[1]}&select=storage_path,original_name`);
    if (!f) return bad('not found', 404);
    const [bucket, ...rest] = f.storage_path.split('/');
    if (!SIGN_BUCKETS.includes(bucket) || !rest.length) return bad('bad storage path', 403);
    return json({ url: await db.sign(bucket, rest.join('/'), url.searchParams.get('download') ? f.original_name : null), name: f.original_name });
  }

  // POST /api/gr {code} → fetch official PDF (gr.maharashtra.gov.in, else archive.org mirror) into gr-library
  if (p === '/api/gr' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const { code } = await req.json();
    if (!/^\d{16,20}$/.test(String(code || ''))) return bad('सांकेतांक: 16–20 digits');
    const srcs = [`https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/${code}.pdf`, `https://archive.org/download/in.gov.maharashtra.gr.${code}/${code}.pdf`];
    let pdf = null, src = '';
    for (const s of srcs) {
      const r = await fetch(s, { redirect: 'follow' });
      if (r.ok) { const b = await r.arrayBuffer(); if (new TextDecoder().decode(b.slice(0, 5)) === '%PDF-') { pdf = b; src = s; break; } }
    }
    if (!pdf) return bad('GR मिळाला नाही', 404);
    await db.upload('gr-library', `${code}.pdf`, pdf, 'application/pdf');
    const d = String(code);
    await db.rest('gr_library', { method: 'POST', body: JSON.stringify({ code: d, date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`, storage_path: `gr-library/${d}.pdf`, source_url: src }), headers: { Prefer: 'resolution=merge-duplicates,return=representation' } });
    return json({ ok: true, code: d, source_url: src });
  }
  m = p.match(/^\/api\/gr\/(\d{16,20})$/);
  if (m && M === 'GET') return json({ url: await db.sign('gr-library', `${m[1]}.pdf`) });

  // GET /api/search?q= → register/*.md full-text search (GitHub code search, server-side)
  if (p === '/api/search' && M === 'GET') {
    // GitHub qualifiers (repo:, org:, user:, path:, in:, language:, … — any `word:` token) are removed from q:
    // the search stays inside register/ of github_repo
    const q = (url.searchParams.get('q') || '').slice(0, 100).split(/\s+/).filter(t => t && !/[A-Za-z_]+:/.test(t)).join(' ');
    if (!q || !cfg.github_repo || !cfg.github_token) return json([]);
    const r = await fetch(`https://api.github.com/search/code?q=${encodeURIComponent(`${q} repo:${cfg.github_repo} path:register`)}&per_page=15`, {
      headers: { Authorization: `Bearer ${cfg.github_token}`, Accept: 'application/vnd.github.text-match+json', 'User-Agent': 'prastav-kaksha' },
    });
    if (!r.ok) return bad(`search ${r.status}`, 502);
    const j = await r.json();
    const repo = cfg.github_repo.toLowerCase();
    return json((j.items || []).filter(i => String((i.repository && i.repository.full_name) || '').toLowerCase() === repo).map(i => ({ path: i.path, frags: (i.text_matches || []).slice(0, 2).map(x => x.fragment) })));
  }

  // letters: POST create, PATCH /api/letters/:id update
  if (p === '/api/letters' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const b = await req.json();
    const row = Object.fromEntries(['case_id', 'ref_no', 'addressed_to', 'sent_date', 'reply_due', 'status'].filter(k => b[k]).map(k => [k, b[k]]));
    if (!isId(row.case_id)) return bad('case_id required');
    const [l] = await db.rest('letters', { method: 'POST', body: JSON.stringify(row) });
    if (row.sent_date) await db.rest(`cases?id=eq.${row.case_id}`, { method: 'PATCH', body: JSON.stringify({ stage: 'पत्र पाठवले (माहिती प्रतीक्षेत)' }) });
    await log(cfg, row.case_id, user.id, 'letter_saved', row);
    return json(l);
  }
  m = p.match(/^\/api\/letters\/(\d+)$/);
  if (m && M === 'PATCH') {
    if (!canWrite(user)) return bad('read-only', 403);
    const b = await req.json();
    const row = Object.fromEntries(['ref_no', 'addressed_to', 'sent_date', 'reply_due', 'reply_received_date', 'status'].filter(k => k in b).map(k => [k, b[k] || null]));
    if ('status' in row && !LETTER_STATUS.includes(row.status)) return bad(`status: one of ${LETTER_STATUS.join(', ')}`);
    const [l] = (await db.rest(`letters?id=eq.${m[1]}`, { method: 'PATCH', body: JSON.stringify(row) })) || [];
    if (!l) return bad('not found', 404);
    // same as POST: a sent date moves the case to "letter sent"
    if (row.sent_date) await db.rest(`cases?id=eq.${Number(l.case_id)}`, { method: 'PATCH', body: JSON.stringify({ stage: 'पत्र पाठवले (माहिती प्रतीक्षेत)' }) });
    await log(cfg, l.case_id, user.id, 'letter_updated', { letter_id: l.id, ...row });
    return json(l);
  }

  return bad('not found', 404);
}
