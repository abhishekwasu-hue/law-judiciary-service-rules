// Proposal Desk API (Cloudflare Worker). Serves the PWA (static assets) and /api/*.
// The browser talks only to this Worker and to Supabase. GitHub is used server-side only.
// Secrets: SUPABASE_SERVICE_KEY, GH_TOKEN. Vars: SUPABASE_URL, SUPABASE_ANON_KEY, GH_REPO.
// Every /api call needs a valid Supabase JWT; table access runs AS THE USER (RLS applies); the service key is used only
// for Storage signing, rate-limit counting and the GitHub dispatch bookkeeping.

const MAX_BYTES = 50 * 1024 * 1024;
const UPLOADS_PER_HOUR = 40;
const SIGN_SECONDS = 600;
const OK_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const STAGES = ['प्राप्त', 'अभ्यास चालू', 'मसुदा तयार', 'वरिष्ठांकडे सादर', 'पत्र पाठवले (माहिती प्रतीक्षेत)', 'माहिती प्राप्त',
  'वित्त/सा.प्र.वि. कडे', 'अभिप्राय प्राप्त', 'आदेश/पत्र निर्गमित', 'बंद'];

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
class HttpError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
const asciiName = (s) => (s || '').normalize('NFKD').replace(/[^A-Za-z0-9._-]+/g, '_').replace(/^_+|_+$/g, '').slice(-80) || 'file';

async function sb(env, path, { method = 'GET', body, jwt, prefer, headers = {} } = {}) {
  const h = {
    apikey: jwt ? env.SUPABASE_ANON_KEY : env.SUPABASE_SERVICE_KEY,
    Authorization: `Bearer ${jwt || env.SUPABASE_SERVICE_KEY}`,
    ...headers,
  };
  if (body !== undefined) h['Content-Type'] = 'application/json';
  if (prefer) h.Prefer = prefer;
  const r = await fetch(env.SUPABASE_URL + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
  const t = await r.text();
  let d = null;
  try { d = t ? JSON.parse(t) : null; } catch { d = t; }
  if (!r.ok) throw new HttpError(r.status >= 500 ? 502 : r.status, (d && (d.message || d.msg || d.error)) || `supabase ${r.status}`);
  return d;
}
const rest = (env, table, q, o) => sb(env, `/rest/v1/${table}${q ? '?' + q : ''}`, o);

async function auth(req, env) {
  const m = (req.headers.get('authorization') || '').match(/^Bearer (.+)$/);
  if (!m) throw new HttpError(401, 'login required');
  const jwt = m[1];
  const u = await fetch(`${env.SUPABASE_URL}/auth/v1/user`, { headers: { apikey: env.SUPABASE_ANON_KEY, Authorization: `Bearer ${jwt}` } });
  if (!u.ok) throw new HttpError(401, 'session expired');
  const user = await u.json();
  const mem = await rest(env, 'members', `user_id=eq.${user.id}&select=role,email`);
  if (!mem.length) throw new HttpError(403, 'no access — ask the owner for an invite');
  return { jwt, user, role: mem[0].role, email: mem[0].email };
}
const writer = (a) => { if (!['owner', 'desk'].includes(a.role)) throw new HttpError(403, 'read-only user'); };

async function signUpload(env, bucket, path) {
  const d = await sb(env, `/storage/v1/object/upload/sign/${bucket}/${path.split('/').map(encodeURIComponent).join('/')}`, { method: 'POST', body: {} });
  return `${env.SUPABASE_URL}/storage/v1${d.url}`;
}
async function signDownload(env, bucket, path, downloadName) {
  const d = await sb(env, `/storage/v1/object/sign/${bucket}/${path.split('/').map(encodeURIComponent).join('/')}`, { method: 'POST', body: { expiresIn: SIGN_SECONDS } });
  let url = `${env.SUPABASE_URL}/storage/v1${d.signedURL || d.signedUrl}`;
  if (downloadName) url += `&download=${encodeURIComponent(downloadName)}`;
  return url;
}

async function dispatch(env, event, payload) {
  const r = await fetch(`https://api.github.com/repos/${env.GH_REPO}/dispatches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.GH_TOKEN}`, Accept: 'application/vnd.github+json', 'User-Agent': 'proposal-desk', 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: event, client_payload: payload }),
  });
  if (r.status !== 204) throw new HttpError(502, `GitHub dispatch failed (${r.status})`);
}

// ---------- handlers ----------
async function upload(req, env, a) {
  writer(a);
  const b = await req.json();
  const files = Array.isArray(b.files) ? b.files : [];
  if (!files.length) throw new HttpError(400, 'no files');
  for (const f of files) {
    if (!['proposal', 'extra_doc', 'reply'].includes(f.kind)) throw new HttpError(400, 'bad file kind');
    if (!OK_TYPES.includes(f.type)) throw new HttpError(400, `${f.name}: only PDF/JPG/PNG`);
    if (!(f.size > 0) || f.size > MAX_BYTES) throw new HttpError(400, `${f.name}: max 50 MB`);
  }
  const since = new Date(Date.now() - 3600e3).toISOString();
  const recent = await rest(env, 'activity', `action=eq.upload&actor=eq.${a.user.id}&at=gte.${since}&select=id`);
  if (recent.length + files.length > UPLOADS_PER_HOUR) throw new HttpError(429, 'too many uploads this hour');

  let caseId = b.case_id ? Number(b.case_id) : null;
  if (!caseId) {
    if (files.filter((f) => f.kind === 'proposal').length !== 1) throw new HttpError(400, 'exactly one proposal PDF is required');
    const cr = String(b.cr_no || '').trim(), yr = Number(b.cr_year) || null;
    const row = {
      cr_no: cr || null, cr_year: yr, file_no: (b.file_no || '').trim() || null, subject: (b.subject || '').trim() || null,
      category: b.category || 'इतर', priority: b.priority || 'सामान्य', received_via: b.received_via || null,
      office: (b.office || '').trim() || null, inward_date: b.inward_date || undefined,
    };
    const [c] = await rest(env, 'cases', 'select=id', { method: 'POST', body: row, jwt: a.jwt, prefer: 'return=representation' });
    caseId = c.id;
    const base = cr && yr ? `CR${asciiName(cr)}_${yr}` : `CASE${caseId}`;
    const taken = await rest(env, 'cases', `prefix=eq.${base}&select=id`);
    await rest(env, 'cases', `id=eq.${caseId}`, { method: 'PATCH', body: { prefix: taken.length ? `${base}_${caseId}` : base }, jwt: a.jwt, prefer: 'return=minimal' });
  } else {
    const c = await rest(env, 'cases', `id=eq.${caseId}&select=id`, { jwt: a.jwt });
    if (!c.length) throw new HttpError(404, 'case not found');
  }

  const out = [];
  for (const f of files) {
    const prev = await rest(env, 'case_files', `case_id=eq.${caseId}&kind=eq.${f.kind}&select=version&order=version.desc&limit=1`, { jwt: a.jwt });
    const version = prev.length ? prev[0].version + 1 : 1;
    const path = `${caseId}/${f.kind}-v${version}-${Date.now()}-${asciiName(f.name)}`;
    const [row] = await rest(env, 'case_files', 'select=id', {
      method: 'POST', jwt: a.jwt, prefer: 'return=representation',
      body: { case_id: caseId, kind: f.kind, bucket: 'proposals', storage_path: path, original_name: f.name, version, size_bytes: f.size },
    });
    out.push({ file_id: row.id, name: f.name, upload_url: await signUpload(env, 'proposals', path) });
    await rest(env, 'activity', '', { method: 'POST', jwt: a.jwt, prefer: 'return=minimal', body: { case_id: caseId, actor_email: a.email, action: 'upload', detail: { kind: f.kind, name: f.name, size: f.size } } });
  }
  if (files.some((f) => f.kind === 'reply')) {
    await rest(env, 'cases', `id=eq.${caseId}`, { method: 'PATCH', jwt: a.jwt, prefer: 'return=minimal', body: { stage: 'माहिती प्राप्त' } });
    const open = await rest(env, 'letters', `case_id=eq.${caseId}&reply_received_date=is.null&select=id&order=id.desc&limit=1`, { jwt: a.jwt });
    if (open.length) await rest(env, 'letters', `id=eq.${open[0].id}`, { method: 'PATCH', jwt: a.jwt, prefer: 'return=minimal', body: { reply_received_date: new Date().toISOString().slice(0, 10), status: 'उत्तर प्राप्त', reply_file_id: out.find((o) => o.name === files.find((f) => f.kind === 'reply').name)?.file_id ?? null } });
  }
  return json({ case_id: caseId, uploads: out });
}

async function run(req, env, a) {
  writer(a);
  const b = await req.json();
  const caseId = Number(b.case_id);
  const mode = ['study', 'reminder', 'cabinet'].includes(b.mode) ? b.mode : 'study';
  const c = await rest(env, 'cases', `id=eq.${caseId}&select=id,prefix`, { jwt: a.jwt });
  if (!c.length) throw new HttpError(404, 'case not found');
  const prop = await rest(env, 'case_files', `case_id=eq.${caseId}&kind=eq.proposal&select=id,storage_path&order=version.desc&limit=1`, { jwt: a.jwt });
  if (!prop.length) throw new HttpError(400, 'proposal PDF missing');
  const head = await fetch(`${env.SUPABASE_URL}/storage/v1/object/info/proposals/${prop[0].storage_path.split('/').map(encodeURIComponent).join('/')}`, { headers: { apikey: env.SUPABASE_SERVICE_KEY, Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}` } });
  if (!head.ok) throw new HttpError(400, 'proposal upload not finished');
  const busy = await rest(env, 'runs', `case_id=eq.${caseId}&state=in.(queued,running)&select=id`, { jwt: a.jwt });
  if (busy.length) throw new HttpError(409, 'a run is already in progress for this case');
  const [r] = await rest(env, 'runs', 'select=*', { method: 'POST', jwt: a.jwt, prefer: 'return=representation', body: { case_id: caseId, mode, instructions: (b.instructions || '').trim() || null } });
  try {
    await dispatch(env, 'process_proposal', { case_id: caseId, run_id: r.id });
  } catch (e) {
    await rest(env, 'runs', `id=eq.${r.id}`, { method: 'PATCH', prefer: 'return=minimal', body: { state: 'failed', progress: 'failed', error: e.message, finished_at: new Date().toISOString() } });
    throw e;
  }
  await rest(env, 'activity', '', { method: 'POST', jwt: a.jwt, prefer: 'return=minimal', body: { case_id: caseId, actor_email: a.email, action: 'run', detail: { run_id: r.id, mode, instructions: r.instructions } } });
  return json({ run: r });
}

async function fileUrl(env, a, id, download) {
  const f = await rest(env, 'case_files', `id=eq.${Number(id)}&select=id,bucket,storage_path,original_name,kind,version`, { jwt: a.jwt });
  if (!f.length) throw new HttpError(404, 'file not found');
  const name = f[0].original_name || f[0].storage_path.split('/').pop();
  return { id: f[0].id, kind: f[0].kind, version: f[0].version, name, url: await signDownload(env, f[0].bucket, f[0].storage_path, download ? name : null) };
}

async function grFile(env, a, code) {
  const g = await rest(env, 'gr_library', `code=eq.${encodeURIComponent(code)}&select=code,storage_path`, { jwt: a.jwt });
  if (!g.length || !g[0].storage_path) throw new HttpError(404, 'GR file not stored');
  return { url: await signDownload(env, 'gr-library', g[0].storage_path, `${code}.pdf`) };
}

async function addGr(req, env, a) {
  writer(a);
  const { code } = await req.json();
  if (!/^[0-9]{12,20}$/.test(String(code || ''))) throw new HttpError(400, 'सांकेतांक: digits only');
  const urls = [
    `https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/${code}.pdf`,
    `https://archive.org/download/in.gov.maharashtra.gr.${code}/${code}.pdf`,
    `https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/English/${code}.pdf`,
  ];
  let pdf = null, source = null;
  for (const u of urls) {
    try {
      const r = await fetch(u, { headers: { 'User-Agent': 'Mozilla/5.0' } });
      if (r.ok) { const b = new Uint8Array(await r.arrayBuffer()); if (b[0] === 0x25 && b[1] === 0x50 && b[2] === 0x44 && b[3] === 0x46) { pdf = b; source = u; break; } }
    } catch { /* try next */ }
  }
  if (!pdf) {
    // fall back to the repo's GitHub Action (tools/gr_request.py), which then syncs the GR into Supabase
    await dispatch(env, 'fetch_gr', { code });
    return json({ status: 'queued', message: 'GR थेट मिळाला नाही; GitHub Action द्वारे मागवला आहे' }, 202);
  }
  const path = `${code}.pdf`;
  const up = await fetch(`${env.SUPABASE_URL}/storage/v1/object/gr-library/${path}`, { method: 'POST', headers: { apikey: env.SUPABASE_SERVICE_KEY, Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`, 'Content-Type': 'application/pdf', 'x-upsert': 'true' }, body: pdf });
  if (!up.ok) throw new HttpError(502, 'storage upload failed');
  let meta = {};
  try {
    const q = `https://archive.org/advancedsearch.php?q=identifier:in.gov.maharashtra.gr.${code}&fl[]=title&fl[]=date&fl[]=subject&output=json`;
    const d = await (await fetch(q)).json();
    meta = d.response.docs[0] || {};
  } catch { /* metadata optional */ }
  const subj = Array.isArray(meta.subject) ? meta.subject.join(', ') : meta.subject;
  await rest(env, 'gr_library', 'on_conflict=code', { method: 'POST', jwt: a.jwt, prefer: 'resolution=merge-duplicates,return=minimal', body: { code, storage_path: path, source_url: source, title: meta.title || null, department: subj || null, date: meta.date ? String(meta.date).slice(0, 10) : null } });
  return json({ status: 'saved', code });
}

async function letters(req, env, a, id, action) {
  writer(a);
  if (req.method === 'POST' && !id) {
    const b = await req.json();
    const [l] = await rest(env, 'letters', 'select=*', { method: 'POST', jwt: a.jwt, prefer: 'return=representation', body: { case_id: Number(b.case_id), ref_no: b.ref_no || null, addressed_to: b.addressed_to || null, sent_date: b.sent_date || null, reply_due: b.reply_due || null, status: 'पाठवले' } });
    await rest(env, 'cases', `id=eq.${l.case_id}`, { method: 'PATCH', jwt: a.jwt, prefer: 'return=minimal', body: { stage: 'पत्र पाठवले (माहिती प्रतीक्षेत)' } });
    return json({ letter: l });
  }
  if (req.method === 'POST' && action === 'remind') {
    const l = await rest(env, 'letters', `id=eq.${Number(id)}&select=id,case_id`, { jwt: a.jwt });
    if (!l.length) throw new HttpError(404, 'letter not found');
    return run(new Request(req.url, { method: 'POST', body: JSON.stringify({ case_id: l[0].case_id, mode: 'reminder' }) }), env, a);
  }
  throw new HttpError(405, 'method');
}

async function cases(req, env, a, id) {
  if (req.method === 'GET') {
    const url = new URL(req.url);
    const q = ['select=*', 'order=updated_at.desc', 'limit=500'];
    for (const k of ['stage', 'category', 'office', 'cr_year']) if (url.searchParams.get(k)) q.push(`${k}=eq.${encodeURIComponent(url.searchParams.get(k))}`);
    return json(await rest(env, 'cases', q.join('&'), { jwt: a.jwt }));
  }
  if (req.method === 'PATCH' && id) {
    writer(a);
    const b = await req.json();
    const allowed = {};
    for (const k of ['stage', 'priority', 'due_date', 'assigned_to', 'subject', 'category', 'file_no', 'office', 'post', 'employee_name', 'received_from', 'received_via']) if (k in b) allowed[k] = b[k];
    if (allowed.stage && !STAGES.includes(allowed.stage)) throw new HttpError(400, 'bad stage');
    const [c] = await rest(env, 'cases', `id=eq.${Number(id)}&select=*`, { method: 'PATCH', jwt: a.jwt, prefer: 'return=representation', body: allowed });
    return json(c);
  }
  throw new HttpError(405, 'method');
}

async function search(req, env, a) {
  const q = (new URL(req.url).searchParams.get('q') || '').trim();
  if (q.length < 2) return json([]);
  return json(await sb(env, '/rest/v1/rpc/search_register', { method: 'POST', jwt: a.jwt, body: { q, lim: 40 } }));
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(req);
    try {
      if (url.pathname === '/api/config') return json({ supabaseUrl: env.SUPABASE_URL, supabaseAnonKey: env.SUPABASE_ANON_KEY });
      const a = await auth(req, env);
      const p = url.pathname.split('/').filter(Boolean); // ['api', name, id?, action?]
      switch (p[1]) {
        case 'upload': if (req.method === 'POST') return await upload(req, env, a); break;
        case 'run': if (req.method === 'POST') return await run(req, env, a); break;
        case 'files':
          if (p[2]) return json(await fileUrl(env, a, p[2], url.searchParams.get('download') === '1'));
          if (url.searchParams.get('ids')) return json(await Promise.all(url.searchParams.get('ids').split(',').slice(0, 30).map((i) => fileUrl(env, a, i, true))));
          break;
        case 'gr':
          if (req.method === 'POST') return await addGr(req, env, a);
          if (p[2]) return json(await grFile(env, a, decodeURIComponent(p[2])));
          break;
        case 'search': return await search(req, env, a);
        case 'letters': return await letters(req, env, a, p[2], p[3]);
        case 'cases': return await cases(req, env, a, p[2]);
        case 'me': return json({ id: a.user.id, email: a.email, role: a.role });
      }
      return json({ error: 'not found' }, 404);
    } catch (e) {
      return json({ error: e.message || 'error' }, e.status || 500);
    }
  },
};
