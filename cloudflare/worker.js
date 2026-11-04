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
  'model_strong', 'effort',
  // draft edit (docs/DRAFT_EDIT_DESIGN.md): model of tools/edit_drafts.py (one Messages API call); empty = DEFAULT_MODEL_EDIT
  'model_edit'];
const PROVIDERS = { part1_provider: ['', 'claude', ...AI_PROVIDERS], fallback_provider: ['', ...AI_PROVIDERS], engine_provider: ['', 'claude', ...AI_PROVIDERS] };
const MODEL_KEYS = ['gemini_model', 'part1_model', 'fallback_model', 'fallback_model_light', 'engine_model', 'engine_model_light', 'model_edit'];
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
// upload kinds (C28, migration 0008: approval = वित्त/सा.प्र.वि. मान्यता, court_notice = न्यायालयीन नोटीस;
// gr = a GR / rule PDF attached in the draft-edit chat, docs/DRAFT_EDIT_DESIGN.md Addendum A — enum value since 0001)
const FILE_KINDS = ['proposal', 'extra_doc', 'reply', 'approval', 'court_notice', 'gr'];
// drafts the user can tick for a run (C28 "कोणते मसुदे हवेत?"), in this fixed order; stored in runs.outputs
const DRAFT_KEYS = ['letter', 'reminder', 'gr', 'corrigendum', 'circular', 'memo', 'notification', 'parawise',
  'do_letter', 'uo_note', 'endorsement', 'office_order', 'press_note', 'addendum', 'affidavit', 'lq'];   // 04.11.2026: last 8
const KIND_NOT_READY = 'हा फाइल-प्रकार अजून सुरू नाही (मालकाने migration 0008 लागू करावे) — "इतर" निवडा';
const BAD_OUTPUTS = 'मसुद्यांची निवड चुकीची — पान पुन्हा उघडा';
const MAX_UPLOAD = 50 * 1024 * 1024;
// ---------- draft edit (सुधारणा-चॅट; docs/DRAFT_EDIT_DESIGN.md points 3 + Addendum A, migration 0013) ----------
// POST /api/edit targets: टिप्पणी, पत्र, आदेश-प्रारूप, परिच्छेदनिहाय उत्तर, शपथपत्र, विधानमंडळ उत्तर, GR सह प्रस्ताव PDF
export const EDIT_TARGETS = ['note', 'letter', 'order', 'parawise', 'affidavit', 'lq', 'package'];
const EDIT_MSG_MAX = 2000;
const EDIT_ATTACH_MAX = 5;
const EDIT_ATTACH_KINDS = ['gr', 'extra_doc', 'reply', 'approval', 'court_notice'];   // case_files kinds that may be attached
const DEFAULT_MODEL_EDIT = 'claude-sonnet-5-5';
const EDIT_STALE_MS = 30 * 60 * 1000;           // edit job timeout 20 min (edit-drafts.yml) + dispatch time
const EDIT_STALE_REASON = 'वेळ संपली — कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.';
const NO_SPEC = "हे प्रकरण या सुविधेपूर्वीचे असल्याने सुधारणा-फाइल उपलब्ध नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.";
const EDIT_MIGRATION = 'Supabase मध्ये migration 0013 लागू करणे आवश्यक आहे.';
const BAD_EDIT_TARGET = 'सुधारणा कोठे करावयाची हे यादीतील पर्यायांतून कृपया निवडावे, ही विनंती.';
const EDIT_MSG_EMPTY = 'कृपया सुधारणा-संदेश नमूद करावा, ही विनंती.';
const EDIT_MSG_LONG = `कृपया सुधारणा-संदेश ${EDIT_MSG_MAX} अक्षरांच्या मर्यादेत नमूद करावा, ही विनंती.`;
const BAD_ATTACH = `जोडलेल्या फाइल चुकीच्या — या प्रकरणाच्या जास्तीत जास्त ${EDIT_ATTACH_MAX} फाइल (GR / इतर कागदपत्र / उत्तर / मान्यता / नोटीस) कृपया जोडाव्यात, ही विनंती.`;
const SIGN_BUCKETS = ['proposals', 'outputs', 'gr-library'];
// Run token (D4): created at dispatch, sent to GitHub in the payload. Single use for /api/engine/config (the secrets);
// after that it is only good for /api/engine/fail and /api/engine/step (THIS run only, return nothing secret) until it expires.
const RUN_TOKEN_TTL = 4 * 3600;                 // > job timeout (180 min) + queue time
const STALE_MS = 3.5 * 3600 * 1000;             // queued/running longer than this = stuck (job timeout 180 min)
const STALE_REASON = 'वेळ संपली — पुन्हा तयार करा';
// dispatch to GitHub failed (A3 audit): the run row and the user see only this; the raw GitHub text stays in activity
const DISPATCH_REASON = 'GitHub जोडणी अयशस्वी (token तपासा — सेटिंग्ज) — पुन्हा तयार करा';
// Settings PUT: this value deletes a secret key (Settings "key काढा"); the Supabase service key can never be cleared
const CLEAR = '__clear__';
const UNCLEARABLE = ['supabase_service_key'];
// case fields the app may set (POST create, PATCH edit)
const CASE_FIELDS = ['cr_no', 'cr_year', 'file_no', 'subject', 'category', 'priority', 'employee_name', 'post', 'office', 'received_from', 'received_via', 'inward_date', 'due_date', 'desk', 'work_type', 'nasti_no'];
// desk profiles (C30, tools/desks/<id>.json; app list dashboard-app/src/lib/constants.ts DESKS). Add an id here when a
// profile json is added. cases.desk null = law-desk6 (migration 0009).
export const DESK_IDS = ['law-desk6', 'hte-mashi5'];
const BAD_DESK = 'विभाग / कार्यासन चुकीचे — यादीतील पर्याय निवडा';
// work categories (C33, migration 0011; app list dashboard-app): service = सेवाविषयक प्रकरणे (default; cases.work_type
// null = service), court = न्यायालयीन प्रकरणे, legislature = विधिमंडळ कामकाज, procurement = खरेदी विषयक बाबी
export const WORK_TYPES = ['service', 'court', 'legislature', 'procurement'];
const BAD_WORK_TYPE = 'कामाची श्रेणी चुकीची — यादीतील पर्याय निवडा';
// cases.nasti_no (migration 0012) = the eOffice नस्ती file / receipt no. as shown on the नस्ती page (/nasti/), to link
// the two; free text, at most NASTI_NO_MAX characters after trim; '' / null clears
const NASTI_NO_MAX = 100;
const BAD_NASTI_NO = `नस्ती क्रमांक चुकीचा — जास्तीत जास्त ${NASTI_NO_MAX} अक्षरे`;
// case columns added by later migrations: the case is saved without them until the migration is applied
const OPTIONAL_CASE_COLS = { desk: '0009', work_type: '0011', nasti_no: '0012' };
// member profile (migration 0012: members.display_name / designation / office / mine): stored once per member so the
// नस्ती page need not ask again. mine = the नस्ती page's "आपल्याकडे असलेले स्थान" list (e.g. "कार्यासन-६, माझ्याकडे").
const PROFILE_KEYS = ['display_name', 'designation', 'office', 'mine'];
const PROFILE_MAX = 120;
const PROFILE_LABELS = { display_name: 'नाव', designation: 'पदनाम', office: 'कार्यालय', mine: 'आपल्याकडे असलेले स्थान' };
const PROFILE_MIGRATION = 'माहिती साठवता आली नाही — Supabase मध्ये migration 0012 लागू करा';
const profileOf = r => Object.fromEntries(PROFILE_KEYS.map(k => [k, r && r[k] != null ? String(r[k]) : '']));

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
      if (!r.ok) {
        const t = (await r.text()).slice(0, 200);
        // bucket file_size_limit (50 MB, migration 0001): Supabase answers 413, or 400 with statusCode "413" in the body
        if (r.status === 413 || /"statusCode"\s*:\s*"?413|exceeded the maximum allowed size|Payload too large/i.test(t)) throw new Error('file over 50 MB');
        throw new Error(`storage ${r.status}: ${t}`);
      }
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
  // role + profile; profile columns missing (migration 0012 not applied) → role only, empty profile
  const memberRow = async () => {
    const q = `members?user_id=eq.${encodeURIComponent(u.id)}&select=role`;
    let rows;
    try {
      rows = await db.rest(`${q},${PROFILE_KEYS.join(',')}`);
    } catch (e) {
      if (!PROFILE_KEYS.some(k => missingColumn(e, k))) throw e;
      rows = await db.rest(q);
    }
    return rows && rows.length ? rows[0] : null;
  };
  const row = await memberRow();
  if (row && row.role) return { id: u.id, email: u.email, role: row.role, profile: profileOf(row) };
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
    if (ins && ins.length) return { id: u.id, email: u.email, role: 'owner', profile: profileOf(null) };
    const again = await memberRow();
    return { id: u.id, email: u.email, role: again ? again.role : null, profile: profileOf(again) };
  }
  return { id: u.id, email: u.email, role: null, profile: profileOf(null) };
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
    // draft edit (migration 0013): an edit run starts tools/edit_drafts.py (edit-drafts.yml), same payload/token scheme
    body: JSON.stringify({ event_type: run.kind === 'edit' ? 'edit_drafts' : 'process_proposal', client_payload: { case_id: run.case_id, run_id: run.id, token, worker: origin } }),
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
      body: JSON.stringify(rows.map(r => ({ case_id: r.case_id, actor, action: r.kind === 'edit' ? 'edit_failed' : 'run_failed', detail: { run_id: r.id, reason } }))) });   // edit runs: migration 0013
  return rows || [];
}

// ---------- sequential queue (C33, migration 0011: runs.dispatched_at) ----------
// One engine run at a time across ALL cases (Abhi 04.11.2026: "काम मात्र सिक्वेन्सनेस … वन बाय वन"). A run waits with
// state 'queued' and dispatched_at null; dispatchNext hands the oldest one (FIFO: created_at, id) to GitHub when no run
// is active. Active = running/queued and dispatched less than STALE_MS ago (a legacy running row without dispatched_at:
// created less than STALE_MS ago). Column missing (migration not applied) → null: every run is dispatched at once.
const ENGINE_END_REASON = 'इंजिन अयशस्वी — पुन्हा तयार करा';
const pgTime = ms => `"${new Date(ms).toISOString()}"`;
// draft edit (migration 0013): edit runs (runs.kind 'edit') are dispatched at once and never take part in the queue —
// neither as its active run nor as a waiting one. Column runs.kind missing (0013 not applied) → no edit runs exist:
// the same query without the filter.
const namesColumn = (e, col) => e instanceof DbError && (e.code === '42703' || e.code === 'PGRST204') && new RegExp(`\\b${col}\\b`).test(e.detail);
async function withoutEditRuns(db, path) {
  try {
    return await db.rest(`${path}&kind=neq.edit`);
  } catch (e) {
    if (!namesColumn(e, 'kind')) throw e;
    return db.rest(path);
  }
}
async function activeRuns(db) {
  const since = pgTime(Date.now() - STALE_MS);
  try {
    return (await withoutEditRuns(db, `runs?state=in.(queued,running)&or=${encodeURIComponent(`(dispatched_at.gt.${since},and(dispatched_at.is.null,state.eq.running,created_at.gt.${since}))`)}&select=id,case_id,state,dispatched_at&order=id.asc`)) || [];
  } catch (e) {
    if (missingColumn(e, 'dispatched_at')) { console.log('runs.dispatched_at column missing (apply migration 0011); runs dispatched at once'); return null; }
    throw e;
  }
}
const BUDGET_WAIT = 'मासिक खर्च-मर्यादा गाठली — Settings मध्ये मर्यादा वाढवल्यावर आपोआप सुरू होईल';
const waitingRuns = db => withoutEditRuns(db, 'runs?state=eq.queued&dispatched_at=is.null&select=id,case_id,created_at,step&order=created_at.asc,id.asc&limit=200').then(r => r || []);
// stuck runs (queued/running too long since dispatch) → failed; runs waiting in the queue are never swept here.
// Edit runs: a shorter limit (EDIT_STALE_MS since creation = dispatch); the 3.5 h sweep covers them too.
async function sweepStale(cfg, actor) {
  const before = Date.now() - STALE_MS;
  let rows;
  try {
    rows = await failRuns(cfg, `or=${encodeURIComponent(`(dispatched_at.lt.${pgTime(before)},and(dispatched_at.is.null,state.eq.running,created_at.lt.${pgTime(before)}))`)}`, STALE_REASON, actor);
  } catch (e) {
    if (!missingColumn(e, 'dispatched_at')) throw e;
    rows = await failRuns(cfg, `created_at=lt.${encodeURIComponent(new Date(before).toISOString())}`, STALE_REASON, actor);
  }
  let edits = [];
  try {
    edits = await failRuns(cfg, `kind=eq.edit&created_at=lt.${encodeURIComponent(new Date(Date.now() - EDIT_STALE_MS).toISOString())}`, EDIT_STALE_REASON, actor);
  } catch (e) {
    if (!namesColumn(e, 'kind')) throw e;   // migration 0013 not applied: no edit runs
  }
  return rows.concat(edits);
}
// Dispatch the oldest waiting run when no run is active. Race-safe: (1) claim with a conditional PATCH (only one
// request gets the row back); (2) after the claim, if any OTHER run is active the claim is given back (two claimers
// that see each other both give back; the cron / next call dispatches later — never two at once). A failed GitHub
// dispatch marks that run failed (DISPATCH_REASON) and the next one is tried.
// → { legacy } (column missing) | { active } | { blocked } (monthly limit: the run stays queued) | { dispatched, failed: [ids] }
async function dispatchNext(env, cfg, origin, actor = null, ownRunId = null) {
  const db = sb(cfg);
  const failed = [];
  if (!cfg.github_repo || !cfg.github_token || !engineReady(cfg) || !origin) return { dispatched: null, failed, not_ready: true };
  for (let i = 0; i < 20; i++) {
    const act = await activeRuns(db);
    if (act === null) return { legacy: true, dispatched: null, failed };
    if (act.length) return { active: act[0].id, dispatched: null, failed };
    const [next] = await waitingRuns(db);
    if (!next) return { dispatched: null, failed };
    // the existing monthly-limit check (as /api/run), at the moment of dispatch: reached → the run stays queued with
    // BUDGET_WAIT as its step and nothing more is dispatched; the cron retries every 5 min
    const sp = await monthSpend(cfg);
    if (sp.spent_usd + sp.reserved_usd >= sp.limit_usd) {
      if (next.step !== BUDGET_WAIT) await db.rest(`runs?id=eq.${Number(next.id)}&state=eq.queued&dispatched_at=is.null`, { method: 'PATCH', body: JSON.stringify({ step: BUDGET_WAIT }) });
      return { blocked: 'monthly_budget_reached', run: next.id, dispatched: null, failed };
    }
    const claimed = (await db.rest(`runs?id=eq.${Number(next.id)}&state=eq.queued&dispatched_at=is.null`, {
      method: 'PATCH', body: JSON.stringify({ dispatched_at: new Date().toISOString() }) })) || [];
    if (!claimed.length) return { lost: next.id, dispatched: null, failed };
    const run = claimed[0];
    const again = (await activeRuns(db)) || [];
    if (again.some(r => Number(r.id) !== Number(run.id))) {
      await db.rest(`runs?id=eq.${Number(run.id)}&state=eq.queued`, { method: 'PATCH', body: JSON.stringify({ dispatched_at: null }) });
      return { yielded: run.id, dispatched: null, failed };
    }
    try {
      await env.SETTINGS.put('worker_origin', origin);
      await dispatchRun(env, cfg, run, origin);
    } catch (e) {
      await db.rest(`runs?id=eq.${Number(run.id)}`, { method: 'PATCH', body: JSON.stringify({ state: 'failed', step: DISPATCH_REASON, finished_at: new Date().toISOString() }) });
      await log(cfg, run.case_id, actor, 'run_failed', { run_id: run.id, reason: DISPATCH_REASON, error: String(e.message || e).slice(0, 300) });
      failed.push(run.id);
      continue;
    }
    await db.rest(`cases?id=eq.${Number(run.case_id)}`, { method: 'PATCH', body: JSON.stringify({ stage: 'अभ्यास चालू' }) });
    // the caller's own run is logged by /api/run (with its instructions); a run taken from the queue is logged here
    if (Number(run.id) !== Number(ownRunId)) await log(cfg, run.case_id, actor, 'run_started', { run_id: run.id, from_queue: true });
    return { dispatched: run, failed };
  }
  return { dispatched: null, failed };
}
// cron (wrangler.toml [triggers]) safety net: sweep stuck runs, then dispatch the next waiting run
async function cronTick(env) {
  const cfg = await settings(env);
  if (!(cfg.supabase_url && cfg.supabase_service_key)) return { skipped: 'not configured' };
  const swept = await sweepStale(cfg, null);
  const origin = (await env.SETTINGS.get('worker_origin')) || '';
  const r = await dispatchNext(env, cfg, origin, null);
  return { swept: swept.map(x => x.id), dispatched: r.dispatched ? r.dispatched.id : null, failed: r.failed };
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

// One run per case (H3): the case's queued/running run (full or edit), not stuck. legacy = runs.dispatched_at missing.
function caseActivePath(caseId, legacy) {
  const sinceIso = new Date(Date.now() - STALE_MS).toISOString();
  return legacy
    ? `runs?case_id=eq.${Number(caseId)}&state=in.(queued,running)&created_at=gt.${encodeURIComponent(sinceIso)}&select=id&order=created_at.desc&limit=1`
    : `runs?case_id=eq.${Number(caseId)}&state=in.(queued,running)&or=${encodeURIComponent(`(dispatched_at.is.null,dispatched_at.gt."${sinceIso}",created_at.gt."${sinceIso}")`)}&select=id&order=created_at.desc&limit=1`;
}
async function caseActiveRun(db, caseId) {
  try {
    return (await db.rest(caseActivePath(caseId, false))) || [];
  } catch (e) {
    if (!missingColumn(e, 'dispatched_at')) throw e;
    return (await db.rest(caseActivePath(caseId, true))) || [];
  }
}

// Duplicate C R: same year and same number ignoring leading zeros ("021" = "21"); cr_no is stored as given.
// exceptId: the case being edited (PATCH) is not its own duplicate.
// POST /api/run `outputs`: undefined/null = legacy run (engine decides) → null; otherwise an array of DRAFT_KEYS,
// deduplicated and put in the fixed order ([] = note only). Anything else → { error }.
export function normOutputs(v) {
  if (v === undefined || v === null) return { value: null };
  if (!Array.isArray(v) || v.length > 32 || v.some(k => typeof k !== 'string' || !DRAFT_KEYS.includes(k))) return { error: BAD_OUTPUTS };
  return { value: DRAFT_KEYS.filter(k => v.includes(k)) };
}
const missingColumn = (e, col) => e instanceof DbError && (e.code === '42703' || e.code === 'PGRST204' || (new RegExp(col).test(e.detail) && /does not exist|could not find/i.test(e.detail)));

// cases.desk (migration 0009) / cases.work_type (migration 0011) / cases.nasti_no (migration 0012) missing: write the case without that column and log;
// never fail the request
async function writeCase(db, path, method, row, what) {
  let cur = row;
  for (;;) {
    try {
      if (cur !== row && !Object.keys(cur).length) return (await db.rest(`${path}${path.includes('?') ? '&' : '?'}select=*`)) || [];
      return (await db.rest(path, { method, body: JSON.stringify(cur) })) || [];
    } catch (e) {
      // the column named in the error; a bare "missing column" code without a name only when one optional column is sent
      const sent = Object.keys(OPTIONAL_CASE_COLS).filter(k => k in cur && missingColumn(e, k));
      const col = sent.find(k => new RegExp(`\\b${k}\\b`).test(e.detail)) || (sent.length === 1 ? sent[0] : null);
      if (!col) throw e;
      const { [col]: v, ...rest } = cur;
      console.log(`cases.${col} column missing (apply migration ${OPTIONAL_CASE_COLS[col]}); ${what} without ${col}=${v}`);
      cur = rest;
    }
  }
}

// row.nasti_no: string → trimmed ('' → null), null stays null; false = not a string or longer than NASTI_NO_MAX
function cleanNastiNo(row) {
  const v = row.nasti_no;
  if (v === null) return true;
  if (typeof v !== 'string') return false;
  const t = v.trim();
  if (t.length > NASTI_NO_MAX) return false;
  row.nasti_no = t || null;
  return true;
}

async function findCrDup(db, crNo, crYear, exceptId = null) {
  if (crNo == null || crNo === '' || crYear == null || crYear === '') return null;
  const n = String(crNo).trim().replace(/^0+(?=\d)/, '');
  const dup = await db.rest(`cases?cr_no=match.${encodeURIComponent(`^0*${n}$`)}&cr_year=eq.${encodeURIComponent(crYear)}${exceptId !== null ? `&id=neq.${Number(exceptId)}` : ''}&select=id&order=id.asc&limit=1`);
  return dup && dup.length ? dup[0].id : null;
}

// Auth user id for an e-mail (admin API, service role). GoTrue's list has a `filter` (e-mail search); the exact,
// case-insensitive match is taken. Falls back to scanning a few pages when the filter is not supported.
async function findAuthUser(base, headers, email) {
  const want = String(email).trim().toLowerCase();
  const pick = j => ((j && (j.users || (Array.isArray(j) ? j : []))) || []).find(u => String(u.email || '').toLowerCase() === want);
  const r = await fetch(`${base}/auth/v1/admin/users?filter=${encodeURIComponent(want)}&per_page=50`, { headers });
  if (r.ok) { const u = pick(await r.json().catch(() => null)); if (u) return u.id; }
  for (let page = 1; page <= 5; page++) {
    const rr = await fetch(`${base}/auth/v1/admin/users?page=${page}&per_page=200`, { headers });
    if (!rr.ok) return null;
    const j = await rr.json().catch(() => null);
    const u = pick(j);
    if (u) return u.id;
    if (!j || !(j.users || []).length || (j.users || []).length < 200) return null;
  }
  return null;
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
  const q = `runs?created_at=gte.${encodeURIComponent(start)}&created_at=lt.${encodeURIComponent(end)}&select=cost_usd,created_at,state`;
  let rows;
  try {
    rows = (await sb(cfg).rest(`${q},dispatched_at`)) || [];
  } catch (e) {
    if (!missingColumn(e, 'dispatched_at')) throw e;
    rows = (await sb(cfg).rest(q)) || [];   // migration 0011 not applied: every queued run was dispatched at once
  }
  const inMonth = rows.filter(r => r.created_at && istMonth(new Date(r.created_at).getTime()).month === month);
  const spent = inMonth.reduce((t, r) => t + (Number(r.cost_usd) || 0), 0);
  // queued/running runs (not stale) have no cost yet: each is reserved at the estimate, so runs started together
  // cannot jointly pass the limit
  const since = Date.now() - STALE_MS;
  // C33: a run still waiting in the queue (queued, dispatched_at null) is not reserved — the limit is checked when it
  // is dispatched
  const waiting = r => r.state === 'queued' && 'dispatched_at' in r && r.dispatched_at === null;
  const isActive = r => (r.state === 'queued' || r.state === 'running') && !waiting(r) && new Date(r.dispatched_at || r.created_at).getTime() > since;   // queue: age from dispatch
  const active = inMonth.filter(isActive);
  const est = active.length ? runEstimate(cfg, inMonth.filter(r => r.state === 'done' || r.state === 'failed')) : 0;
  const reserved = active.reduce((t, r) => t + Math.max(0, est - (Number(r.cost_usd) || 0)), 0);
  return { month, spent_usd: Math.round(spent * 10000) / 10000, limit_usd: monthlyLimit(cfg), runs: inMonth.length,
    reserved_usd: Math.round(reserved * 10000) / 10000, active_runs: active.length };
}

// ---------- security headers on HTML (A3 audit: clickjacking) ----------
// Needs wrangler.toml run_worker_first = true (otherwise static assets bypass the Worker).
// App pages: inline scripts allowed by their sha256 (computed from the served HTML), Supabase REST/Realtime/Storage
// in connect-src. The नस्ती page (/nasti/, the owner's own APK page: large inline scripts, eval in its Excel library)
// gets a looser script policy; same origin as the app, framed only by the app (frame-ancestors 'self'). Its connect-src
// has no 'self' (only data: blob:): the page makes no fetch/XHR (only its own navigation GET and a blob: PDF.js worker),
// so even injected HTML could not call /api with the session.
const sha256b64 = async text => btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))));
export async function cspFor(html, pathname, supabaseUrl) {
  const common = ["base-uri 'self'", "object-src 'none'", "frame-ancestors 'self'", "form-action 'self'"];
  if (pathname.startsWith('/nasti/') || pathname === '/nasti')
    return ["default-src 'self' data: blob:", "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:", "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:", "font-src 'self' data:", "worker-src 'self' blob:", "connect-src data: blob:", ...common].join('; ');
  const hashes = [];
  for (const m of html.matchAll(/<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi)) {
    if (/\ssrc\s*=/i.test(m[1] || '') || !m[2]) continue;
    hashes.push(`'sha256-${await sha256b64(m[2])}'`);
  }
  let sbOrigin = '';
  try { if (supabaseUrl) sbOrigin = new URL(supabaseUrl).origin; } catch { /* bad URL in settings */ }
  // *.supabase.co too: a page loaded before Setup / a Supabase URL change still reaches the new project
  const sbConn = `${sbOrigin ? ` ${sbOrigin} ${sbOrigin.replace(/^http/, 'ws')}` : ''} https://*.supabase.co wss://*.supabase.co`;
  return ["default-src 'self'", `script-src 'self' ${hashes.join(' ')}`.trim(), "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: blob: https://fonts.gstatic.com", `img-src 'self' data: blob:${sbOrigin ? ' ' + sbOrigin : ''} https://*.supabase.co`,
    `connect-src 'self'${sbConn}`, "worker-src 'self' blob:", "frame-src 'self'", "manifest-src 'self'", ...common].join('; ');
}
async function withSecurityHeaders(res, url, env) {
  const type = res.headers.get('content-type') || '';
  if (!/text\/html/i.test(type)) return res;
  const html = await res.text();
  let supabaseUrl = '';
  try { supabaseUrl = (await env.SETTINGS.get('supabase_url')) || ''; } catch { /* KV unavailable: CSP without Supabase */ }
  const h = new Headers(res.headers);
  h.set('content-security-policy', await cspFor(html, url.pathname, supabaseUrl));
  h.set('x-frame-options', 'SAMEORIGIN');
  h.set('x-content-type-options', 'nosniff');
  h.set('referrer-policy', 'same-origin');
  h.delete('content-length');
  return new Response(html, { status: res.status, statusText: res.statusText, headers: h });
}

// ---------- routes ----------
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!url.pathname.startsWith('/api/')) return withSecurityHeaders(await env.ASSETS.fetch(req), url, env);
    try {
      return await route(req, env, url);
    } catch (e) {
      return bad(String(e.message || e), 500);
    }
  },
  // cron every 5 min (wrangler.toml [triggers]): stuck-run sweep + dispatch of the next queued run (C33 safety net)
  async scheduled(event, env, ctx) {
    const job = cronTick(env).then(r => console.log('cron', JSON.stringify(r))).catch(e => console.log('cron error', String(e.message || e)));
    if (ctx && ctx.waitUntil) ctx.waitUntil(job); else await job;
  },
};
export { cronTick };

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
    const out = { anthropic_api_key: cfg.anthropic_api_key, model: cfg.model, model_light: cfg.model_light || '', model_review: cfg.model_review || '', budget_usd: cfg.budget_usd || '', model_strong: cfg.model_strong || '', effort: cfg.effort || '', model_edit: cfg.model_edit || DEFAULT_MODEL_EDIT, supabase_url: cfg.supabase_url, supabase_service_key: cfg.supabase_service_key };
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
    const nx = await dispatchNext(env, cfg, url.origin, null);   // C33: the queue moves on
    return json({ ok: true, changed: rows.length, dispatched: nx.dispatched ? nx.dispatched.id : null });
  }

  // engine: the workflow's last step (if: always()) — the job of THIS run has ended. Run token, used or not. A run still
  // queued/running then can never finish → failed (ENGINE_END_REASON); then the next queued run is dispatched (C33).
  // → { ok, changed, dispatched: run id | null }
  if (p === '/api/engine/next' && M === 'POST') {
    const tok = await runToken(env, req);
    const b = await req.json().catch(() => ({}));
    if (!tok || tok.run_id !== String(b.run_id || '')) return bad('bad token', 403);
    if (!cfg.supabase_url || !cfg.supabase_service_key) return bad('not configured', 503);
    const rows = await failRuns(cfg, `id=eq.${Number(tok.run_id)}`, ENGINE_END_REASON);
    const nx = await dispatchNext(env, cfg, url.origin, null);
    return json({ ok: true, changed: rows.length, dispatched: nx.dispatched ? nx.dispatched.id : null });
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

  // PATCH /api/me {any of display_name, designation, office, mine} → the user object as GET /api/me. Own row only
  // (service role, user_id from the session); trimmed, each <= PROFILE_MAX chars, '' / null clears; unknown keys ignored.
  // Profile columns missing (migration 0012) → 409 {error: 'migration_missing', reason}.
  if (p === '/api/me' && M === 'PATCH') {
    const b = await req.json().catch(() => null);
    if (!b || typeof b !== 'object' || Array.isArray(b)) return bad('माहिती पाठवली नाही');
    const row = {};
    for (const k of PROFILE_KEYS) {
      if (!(k in b)) continue;
      const v = b[k];
      if (v !== null && typeof v !== 'string') return bad(`${PROFILE_LABELS[k]}: मजकूर असावा`);
      const t = (v || '').trim();
      if (t.length > PROFILE_MAX) return bad(`${PROFILE_LABELS[k]}: जास्तीत जास्त ${PROFILE_MAX} अक्षरे`);
      row[k] = t || null;
    }
    if (!Object.keys(row).length) return bad('बदलण्यासाठी माहिती नाही');
    let rows;
    try {
      rows = await db.rest(`members?user_id=eq.${encodeURIComponent(user.id)}&select=role,${PROFILE_KEYS.join(',')}`, { method: 'PATCH', body: JSON.stringify(row) });
    } catch (e) {
      if (PROFILE_KEYS.some(k => missingColumn(e, k))) return json({ error: 'migration_missing', reason: PROFILE_MIGRATION }, 409);
      throw e;
    }
    const r = rows && rows[0];
    return json({ id: user.id, email: user.email, role: (r && r.role) || user.role, profile: profileOf(r || { ...user.profile, ...row }) });
  }
  if (p === '/api/me') return json(user);

  // GET /api/spend (members) → {month, spent_usd, limit_usd (empty setting = 20), runs, reserved_usd (active runs at their estimate), active_runs}: runs.cost_usd this IST calendar month
  if (p === '/api/spend' && M === 'GET') {
    const { month, spent_usd, limit_usd, runs, reserved_usd, active_runs } = await monthSpend(cfg);
    return json({ month, spent_usd, limit_usd, runs, reserved_usd, active_runs });
  }

  // POST /api/runs/sweep → runs queued/running for more than 3.5 h since dispatch are marked failed (called by the app
  // on load); runs waiting in the queue are not swept. Then the next queued run is dispatched (C33).
  // → { ok, failed: [run ids], dispatched: run id | null }
  if (p === '/api/runs/sweep' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const rows = await sweepStale(cfg, user.id);
    const nx = await dispatchNext(env, cfg, url.origin, user.id);
    return json({ ok: true, failed: rows.map(r => r.id), dispatched: nx.dispatched ? nx.dispatched.id : null });
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
    for (const k of ALL_KEYS) if (k in b && String(b[k] ?? '').trim() === CLEAR && (!SECRET_KEYS.includes(k) || UNCLEARABLE.includes(k))) return bad(`${k}: cannot clear`);
    for (const k of ALL_KEYS) {
      if (!(k in b) || b[k] === null) continue;
      const v = String(b[k]).trim();
      if (SECRET_KEYS.includes(k) && v === CLEAR) { await env.SETTINGS.delete(k); continue; } // "key काढा"
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
    const ah = { apikey: cfg.supabase_service_key, Authorization: `Bearer ${cfg.supabase_service_key}`, 'content-type': 'application/json' };
    const r = await fetch(`${base}/auth/v1/invite`, { method: 'POST', headers: ah, body: JSON.stringify({ email }) });
    const j = await r.json().catch(() => ({}));
    let userId = r.ok ? j.id : null, existing = false;
    // A3 audit: the e-mail already has an auth account (e.g. tried the OTP login before being invited) → Supabase
    // refuses the invite (422). Find that account with the admin API (service role) and add it as a member.
    if (!r.ok && (r.status === 422 || /already|registered|exists/i.test(`${j.msg || ''} ${j.message || ''} ${j.error_code || ''}`))) {
      userId = await findAuthUser(base, ah, email);
      existing = !!userId;
    }
    if (!userId) return json({ error: 'invite_failed', status: r.status }, 502);
    await db.rest('members', { method: 'POST', body: JSON.stringify({ user_id: userId, email, role }), headers: { Prefer: 'resolution=merge-duplicates' } });
    return json({ ok: true, existing });
  }

  // POST /api/cases {cr_no, cr_year, file_no, subject, category, priority, ...} → case row
  if (p === '/api/cases' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const b = await req.json();
    // all identity fields optional (owner rule 01.11.2026): the engine fills empty ones from the निर्देशपत्र
    if (b.cr_no && !/^\d+$/.test(String(b.cr_no))) return bad('cr_no: digits only');
    if (b.cr_year && !/^\d{4}$/.test(String(b.cr_year))) return bad('cr_year: 4 digits');
    const row = Object.fromEntries(CASE_FIELDS.filter(k => b[k] !== undefined && b[k] !== '').map(k => [k, b[k]]));
    if (row.desk != null && !DESK_IDS.includes(row.desk)) return bad(BAD_DESK);
    if (row.work_type != null && !WORK_TYPES.includes(row.work_type)) return bad(BAD_WORK_TYPE);
    if ('nasti_no' in row && !cleanNastiNo(row)) return bad(BAD_NASTI_NO);
    if (row.nasti_no === null) delete row.nasti_no;
    const findDup = () => findCrDup(db, row.cr_no, row.cr_year);
    const dupId = await findDup();
    if (dupId !== null) return json({ error: 'duplicate_cr', existing_id: dupId }, 409);
    let c;
    try {
      [c] = await writeCase(db, 'cases', 'POST', row, 'case created');
    } catch (e) {
      // a parallel request inserted the same C R between the check and the insert (unique cr_no, cr_year)
      if (e instanceof DbError && (e.status === 409 || e.code === '23505')) return json({ error: 'duplicate_cr', existing_id: await findDup() }, 409);
      throw e;
    }
    await log(cfg, c.id, user.id, 'case_created', { cr: c.cr_no ? `${c.cr_no}/${c.cr_year || ''}` : '' });
    return json(c);
  }

  // PATCH /api/cases/:id {any of CASE_FIELDS; '' / null = empty} → case row. C R / वर्ष: same rules and duplicate
  // check as create (digits, leading zeros ignored, 409 duplicate_cr with the other case's id) — A3 audit (EditCase).
  let m = p.match(/^\/api\/cases\/(\d+)$/);
  if (m && M === 'PATCH') {
    if (!canWrite(user)) return bad('read-only', 403);
    const id = Number(m[1]);
    const b = await req.json().catch(() => null);
    if (!b || typeof b !== 'object') return bad('body required');
    const row = Object.fromEntries(CASE_FIELDS.filter(k => k in b).map(k => [k, b[k] === '' || b[k] === undefined ? null : b[k]]));
    if (!Object.keys(row).length) return bad('nothing to change');
    if ('subject' in row && row.subject === null) row.subject = ''; // subject column: empty text, not null (as the app saved it before)
    if (row.cr_no != null && !/^\d+$/.test(String(row.cr_no).trim())) return bad('cr_no: digits only');
    if (row.cr_year != null && !/^\d{4}$/.test(String(row.cr_year).trim())) return bad('cr_year: 4 digits');
    if (row.desk != null && !DESK_IDS.includes(row.desk)) return bad(BAD_DESK);
    if (row.work_type != null && !WORK_TYPES.includes(row.work_type)) return bad(BAD_WORK_TYPE);
    if ('nasti_no' in row && !cleanNastiNo(row)) return bad(BAD_NASTI_NO);
    if (row.cr_no != null) row.cr_no = String(row.cr_no).trim();
    if (row.cr_year != null) row.cr_year = Number(String(row.cr_year).trim());
    const [cur] = (await db.rest(`cases?id=eq.${id}&select=id,cr_no,cr_year`)) || [];
    if (!cur) return bad('case not found', 404);
    const crNo = 'cr_no' in row ? row.cr_no : cur.cr_no, crYear = 'cr_year' in row ? row.cr_year : cur.cr_year;
    const crChanged = ('cr_no' in row || 'cr_year' in row) && (String(crNo ?? '') !== String(cur.cr_no ?? '') || String(crYear ?? '') !== String(cur.cr_year ?? ''));
    if (crChanged) {
      const dupId = await findCrDup(db, crNo, crYear, id);
      if (dupId !== null) return json({ error: 'duplicate_cr', existing_id: dupId }, 409);
    }
    let c;
    try {
      [c] = await writeCase(db, `cases?id=eq.${id}`, 'PATCH', row, `case ${id} updated`);
    } catch (e) {
      if (e instanceof DbError && (e.status === 409 || e.code === '23505')) return json({ error: 'duplicate_cr', existing_id: await findCrDup(db, crNo, crYear, id) }, 409);
      throw e;
    }
    if (!c) return bad('case not found', 404);
    await log(cfg, id, user.id, 'case_updated', { fields: Object.keys(row), ...(crChanged ? { cr: crNo ? `${crNo}/${crYear || ''}` : '' } : {}) });
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
    try {
      await db.upload('proposals', path, req.body, req.headers.get('content-type'));
    } catch (e) {
      if (String(e.message) === 'file over 50 MB') return bad('file over 50 MB', 413);
      throw e;
    }
    let f;
    try {
      [f] = await db.rest('case_files', { method: 'POST', body: JSON.stringify({ case_id: caseId, kind, storage_path: `proposals/${path}`, original_name: name, version, uploaded_by: user.id }) });
    } catch (e) {
      // approval / court_notice before migration 0008: enum value missing (22P02 invalid input value for enum file_kind)
      if (e instanceof DbError && ['approval', 'court_notice'].includes(kind) && (e.code === '22P02' || /enum/i.test(e.detail))) {
        console.log(`file_kind ${kind} missing (apply migration 0008)`);
        return bad(KIND_NOT_READY, 409);
      }
      throw e;
    }
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

  // POST /api/run {case_id, instructions, outputs?} → runs row + dispatch. outputs (C28): ticked drafts, DRAFT_KEYS only
  // C33 queue (migration 0011): → {...run, queued: false} dispatched now | {...run, queued: true, position} waiting
  // (position 1 = next after the active run) | without the migration: the run row as before (dispatched at once)
  if (p === '/api/run' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    if (!cfg.github_repo || !cfg.github_token || !engineReady(cfg)) return bad('Settings: GitHub repo/token and the AI key (Anthropic or the chosen engine provider) needed', 412);
    const { case_id, instructions, outputs: outputsRaw } = await req.json();
    if (!isId(case_id)) return bad('case_id required');
    const outs = normOutputs(outputsRaw);
    if (outs.error) return bad(outs.error);
    const has = await db.rest(`case_files?case_id=eq.${case_id}&kind=eq.proposal&select=id&limit=1`);
    if (!has.length) return bad('upload the proposal PDF first');
    // monthly limit: once this month's spend reached it, no new run is dispatched (runs already going finish)
    const sp = await monthSpend(cfg);
    // queued/running runs count at their estimate (reserved_usd), so several runs started together cannot pass it
    if (sp.spent_usd + sp.reserved_usd >= sp.limit_usd) return json({ error: 'monthly_budget_reached', spent_usd: sp.spent_usd, limit_usd: sp.limit_usd, reserved_usd: sp.reserved_usd }, 402);
    // one run at a time per case (H3, QUALITY_AUDIT §7): a double tap / second tab / second user would start a second,
    // paid run. Runs older than STALE_MS (since dispatch) are stuck (swept), so they do not block; a run waiting in
    // the queue (C33) always blocks.
    // (full or edit: an active edit run of the case blocks a full run too — draft edit, migration 0013)
    const act = await activeRuns(db);   // null = migration 0011 not applied → immediate dispatch as before
    const active = await db.rest(caseActivePath(case_id, act === null));
    if (active && active.length) return json({ error: 'run_active', run_id: active[0].id }, 409);
    const runRow = { case_id, instructions: instructions || null, created_by: user.id };
    let run;
    try {
      [run] = await db.rest('runs', { method: 'POST', body: JSON.stringify(outs.value === null ? runRow : { ...runRow, outputs: outs.value }) });
    } catch (e) {
      // migration 0008 not applied: the run is never refused for that — insert without the column (legacy behaviour)
      if (outs.value === null || !missingColumn(e, 'outputs')) throw e;
      console.log(`runs.outputs column missing (apply migration 0008); run for case ${case_id} inserted without outputs`);
      [run] = await db.rest('runs', { method: 'POST', body: JSON.stringify(runRow) });
      run = { ...run, outputs_dropped: true };
    }
    const started = { run_id: run.id, instructions: instructions || '', outputs: outs.value, ...(run.outputs_dropped ? { outputs_dropped: true } : {}) };
    const dispatchFailed = async e => {
      // A3 audit: the run row (red box, History) gets only the Marathi reason; the raw GitHub text goes to activity
      if (e) {
        await db.rest(`runs?id=eq.${run.id}`, { method: 'PATCH', body: JSON.stringify({ state: 'failed', step: DISPATCH_REASON, finished_at: new Date().toISOString() }) });
        await log(cfg, case_id, user.id, 'run_failed', { run_id: run.id, reason: DISPATCH_REASON, error: String(e.message || e).slice(0, 300) });
      }
      return json({ error: 'dispatch_failed', reason: DISPATCH_REASON, run_id: run.id }, 502);
    };
    if (act === null) {
      try {
        await dispatchRun(env, cfg, run, url.origin);
      } catch (e) {
        return dispatchFailed(e);
      }
    } else {
      // C33 queue: the new run waits (dispatched_at null); dispatchNext takes the oldest waiting run if none is active
      await env.SETTINGS.put('worker_origin', url.origin);
      const nx = await dispatchNext(env, cfg, url.origin, user.id, run.id);
      if (nx.failed.map(Number).includes(Number(run.id))) return dispatchFailed(null);   // marked failed + logged there
      if (!nx.dispatched || Number(nx.dispatched.id) !== Number(run.id)) {
        const waiting = await waitingRuns(db);
        const i = waiting.findIndex(r => Number(r.id) === Number(run.id));
        const position = i >= 0 ? i + 1 : waiting.length + 1;
        await log(cfg, case_id, user.id, 'run_queued', { ...started, position });
        return json({ ...run, queued: true, position, ...(nx.blocked ? { blocked: nx.blocked, step: BUDGET_WAIT } : {}) });
      }
      run = { ...run, dispatched_at: nx.dispatched.dispatched_at };
    }
    await db.rest(`cases?id=eq.${case_id}`, { method: 'PATCH', body: JSON.stringify({ stage: 'अभ्यास चालू' }) });
    await log(cfg, case_id, user.id, 'run_started', started);
    return json(act === null ? run : { ...run, queued: false });
  }

  // POST /api/edit {case_id, target, message, attachments?} → the edit run row ({id, case_id, kind: 'edit', edit_target,
  // edit_message, edit_attachments, dispatched_at, state 'queued', …}), dispatched at once as repository_dispatch
  // `edit_drafts` (docs/DRAFT_EDIT_DESIGN.md point 3 + Addendum A; migration 0013). Never waits in the C33 queue; one
  // run per case (full or edit). target ∈ EDIT_TARGETS; message trimmed 1..EDIT_MSG_MAX; attachments = ≤ EDIT_ATTACH_MAX
  // case_files ids of THIS case, kinds EDIT_ATTACH_KINDS (uploaded first with /api/upload). Errors: 403 read-only;
  // 412 settings; 400 {error} Marathi; 409 {error: 'migration_missing' | 'no_spec', reason} | {error: 'run_active', run_id};
  // 402 monthly_budget_reached (as /api/run); 502 dispatch_failed (as /api/run).
  if (p === '/api/edit' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    if (!cfg.github_repo || !cfg.github_token || !cfg.anthropic_api_key) return bad('Settings: GitHub repo/token and the Anthropic key needed', 412);
    const b = await req.json().catch(() => null);
    if (!b || typeof b !== 'object' || Array.isArray(b)) return bad('माहिती पाठवली नाही');
    if (!isId(b.case_id)) return bad('case_id required');
    const caseId = Number(b.case_id);
    if (!EDIT_TARGETS.includes(b.target)) return bad(BAD_EDIT_TARGET);
    if (typeof b.message !== 'string' || !b.message.trim()) return bad(EDIT_MSG_EMPTY);
    const message = b.message.trim();
    if (message.length > EDIT_MSG_MAX) return bad(EDIT_MSG_LONG);
    let attachments = [];
    if (b.attachments !== undefined && b.attachments !== null) {
      const a = b.attachments;
      if (!Array.isArray(a) || a.length > EDIT_ATTACH_MAX || a.some(x => (typeof x !== 'number' && typeof x !== 'string') || !isId(x))) return bad(BAD_ATTACH);
      attachments = [...new Set(a.map(Number))];
      if (attachments.length) {
        const rows = (await db.rest(`case_files?id=in.(${attachments.join(',')})&case_id=eq.${caseId}&select=id,kind`)) || [];
        if (rows.length !== attachments.length || rows.some(r => !EDIT_ATTACH_KINDS.includes(r.kind))) return bad(BAD_ATTACH);
      }
    }
    // the spec of the last full run (tools/engine_supabase.py finish); also for target 'package' (enclosures.json may
    // be missing for older runs — the edit job handles that)
    let spec;
    try {
      spec = await db.rest(`case_files?case_id=eq.${caseId}&kind=eq.spec&original_name=eq.spec.json&select=id&limit=1`);
    } catch (e) {
      // enum value 'spec' missing (22P02 invalid input value for enum file_kind): migration 0013 not applied
      if (e instanceof DbError && (e.code === '22P02' || /enum/i.test(e.detail))) return json({ error: 'migration_missing', reason: EDIT_MIGRATION }, 409);
      throw e;
    }
    if (!spec || !spec.length) return json({ error: 'no_spec', reason: NO_SPEC }, 409);
    const sp = await monthSpend(cfg);
    if (sp.spent_usd + sp.reserved_usd >= sp.limit_usd) return json({ error: 'monthly_budget_reached', spent_usd: sp.spent_usd, limit_usd: sp.limit_usd, reserved_usd: sp.reserved_usd }, 402);
    const active = await caseActiveRun(db, caseId);
    if (active.length) return json({ error: 'run_active', run_id: active[0].id }, 409);
    let cur = { case_id: caseId, kind: 'edit', edit_target: b.target, edit_message: message, edit_attachments: attachments,
      created_by: user.id, dispatched_at: new Date().toISOString() };
    let run;
    for (;;) {
      try {
        [run] = await db.rest('runs', { method: 'POST', body: JSON.stringify(cur) });
        break;
      } catch (e) {
        if (['kind', 'edit_target', 'edit_message', 'edit_attachments'].some(c => namesColumn(e, c))) return json({ error: 'migration_missing', reason: EDIT_MIGRATION }, 409);
        // runs.dispatched_at missing (migration 0011): the row without it (the edit run is dispatched at once anyway)
        if (!('dispatched_at' in cur) || !missingColumn(e, 'dispatched_at')) throw e;
        const { dispatched_at, ...rest } = cur;
        cur = rest;
      }
    }
    run = { ...run, kind: 'edit' };
    try {
      await dispatchRun(env, cfg, run, url.origin);
    } catch (e) {
      await db.rest(`runs?id=eq.${Number(run.id)}`, { method: 'PATCH', body: JSON.stringify({ state: 'failed', step: DISPATCH_REASON, finished_at: new Date().toISOString() }) });
      await log(cfg, caseId, user.id, 'edit_failed', { run_id: run.id, reason: DISPATCH_REASON, error: String(e.message || e).slice(0, 300) });
      return json({ error: 'dispatch_failed', reason: DISPATCH_REASON, run_id: run.id }, 502);
    }
    await log(cfg, caseId, user.id, 'edit_requested', { run_id: run.id, target: b.target, message, attachments });
    return json(run);
  }

  // GET /api/files/:id → signed URL (10 min); ?download=1 keeps the original name
  m = p.match(/^\/api\/files\/(\d+)$/);
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
