// प्रस्ताव कक्ष — Cloudflare Worker (app B). Design: docs/APP_B_DESIGN.md (D1–D7).
// The browser talks only to this Worker and to Supabase (anon key + user JWT, RLS). No key is hard-coded:
// every key/URL lives in KV namespace SETTINGS, entered on the app's Settings screen (owner only).

const SECRET_KEYS = ['supabase_service_key', 'github_token', 'anthropic_api_key'];
const PLAIN_KEYS = ['supabase_url', 'supabase_anon_key', 'github_repo', 'github_branch', 'model', 'owner_email'];
const ALL_KEYS = [...SECRET_KEYS, ...PLAIN_KEYS];
const FILE_KINDS = ['proposal', 'extra_doc', 'reply'];
const MAX_UPLOAD = 50 * 1024 * 1024;
const SIGN_BUCKETS = ['proposals', 'outputs', 'gr-library'];
// Run token (D4): created at dispatch, sent to GitHub in the payload. Single use for /api/engine/config (the secrets);
// after that it is only good for /api/engine/fail (marks THIS run failed, returns nothing secret) until it expires.
const RUN_TOKEN_TTL = 4 * 3600;                 // > job timeout (180 min) + queue time
const STALE_MS = 3.5 * 3600 * 1000;             // queued/running longer than this = stuck (job timeout 180 min)
const STALE_REASON = 'वेळ संपली — पुन्हा तयार करा';

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
      if (!r.ok) throw new Error(`db ${r.status}: ${t.slice(0, 200)}`);
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
  const rows = await sb(cfg).rest(`members?user_id=eq.${u.id}&select=role`);
  if (rows.length) return { id: u.id, email: u.email, role: rows[0].role };
  // first sign-in of the owner email given at setup → becomes owner
  if (cfg.owner_email && u.email && u.email.toLowerCase() === cfg.owner_email.toLowerCase()) {
    await sb(cfg).rest('members', { method: 'POST', body: JSON.stringify({ user_id: u.id, email: u.email, role: 'owner' }) });
    return { id: u.id, email: u.email, role: 'owner' };
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
    if (!cfg.anthropic_api_key || !cfg.supabase_url || !cfg.supabase_service_key) return bad('config incomplete (Settings)', 412); // token stays unused
    const exp = tok.exp || Math.floor(Date.now() / 1000) + RUN_TOKEN_TTL;
    await env.SETTINGS.put(tok.key, JSON.stringify({ run_id: tok.run_id, used: true, exp }), { expiration: exp });
    return json({ anthropic_api_key: cfg.anthropic_api_key, model: cfg.model, supabase_url: cfg.supabase_url, supabase_service_key: cfg.supabase_service_key });
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

  if (!configured) return bad('not configured', 503);
  const user = await currentUser(req, cfg);
  if (!user) return bad('login required', 401);
  if (!user.role) return bad('not a member', 403);
  const db = sb(cfg);

  if (p === '/api/me') return json(user);

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
    for (const k of ALL_KEYS) {
      if (!(k in b) || b[k] === null) continue;
      const v = String(b[k]).trim();
      if (SECRET_KEYS.includes(k) && (v === '' || v.startsWith('••••'))) continue; // unchanged secret
      if (k === 'owner_email' && !v) continue;
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
    if (row.cr_no && row.cr_year) {
      const dup = await db.rest(`cases?cr_no=eq.${encodeURIComponent(row.cr_no)}&cr_year=eq.${encodeURIComponent(row.cr_year)}&select=id&limit=1`);
      if (dup.length) return json({ error: 'duplicate_cr', existing_id: dup[0].id }, 409);
    }
    const [c] = await db.rest('cases', { method: 'POST', body: JSON.stringify(row) });
    await log(cfg, c.id, user.id, 'case_created', { cr: c.cr_no ? `${c.cr_no}/${c.cr_year || ''}` : '' });
    return json(c);
  }

  // POST /api/upload?case_id=&kind=  body = file bytes, header x-file-name (original name, URI-encoded)
  if (p === '/api/upload' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const caseId = Number(url.searchParams.get('case_id')), kind = url.searchParams.get('kind');
    const name = decodeURIComponent(req.headers.get('x-file-name') || '');
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
    if (!cfg.github_repo || !cfg.github_token || !cfg.anthropic_api_key) return bad('Settings: GitHub repo/token and Anthropic key needed', 412);
    const { case_id, instructions } = await req.json();
    if (!case_id) return bad('case_id required');
    const has = await db.rest(`case_files?case_id=eq.${case_id}&kind=eq.proposal&select=id&limit=1`);
    if (!has.length) return bad('upload the proposal PDF first');
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
    const q = (url.searchParams.get('q') || '').slice(0, 100);
    if (!q || !cfg.github_repo || !cfg.github_token) return json([]);
    const r = await fetch(`https://api.github.com/search/code?q=${encodeURIComponent(`${q} repo:${cfg.github_repo} path:register`)}&per_page=15`, {
      headers: { Authorization: `Bearer ${cfg.github_token}`, Accept: 'application/vnd.github.text-match+json', 'User-Agent': 'prastav-kaksha' },
    });
    if (!r.ok) return bad(`search ${r.status}`, 502);
    const j = await r.json();
    return json(j.items.map(i => ({ path: i.path, frags: (i.text_matches || []).slice(0, 2).map(x => x.fragment) })));
  }

  // letters: POST create, PATCH /api/letters/:id update
  if (p === '/api/letters' && M === 'POST') {
    if (!canWrite(user)) return bad('read-only', 403);
    const b = await req.json();
    const row = Object.fromEntries(['case_id', 'ref_no', 'addressed_to', 'sent_date', 'reply_due', 'status'].filter(k => b[k]).map(k => [k, b[k]]));
    if (!row.case_id) return bad('case_id required');
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
    const [l] = await db.rest(`letters?id=eq.${m[1]}`, { method: 'PATCH', body: JSON.stringify(row) });
    return json(l);
  }

  return bad('not found', 404);
}
