// node --test cloudflare/test/worker.test.mjs — Worker flows with an in-memory KV and a mocked Supabase/GitHub.
import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { cronTick } from '../worker.js';

function kv() {
  const m = new Map();
  return { m, get: async k => (m.has(k) ? m.get(k) : null), put: async (k, v) => void m.set(k, v), delete: async k => void m.delete(k) };
}
const SB = 'https://sb.example';
const calls = [];
const members = [];
const patches = [], acts = [], uploads = [];
const run55 = { state: 'queued' };
const letterPatches = [];
let pendingLetters = [];
let monthRuns = [];
let activeRuns = [];
const spendQueries = [];
const configTaken = new Set();
let configColumn = true;
let outputsColumn = true;         // false = migration 0008 not applied (runs.outputs missing)
const runInserts = [];
let deskColumn = true;            // false = migration 0009 not applied (cases.desk missing)
const caseInserts = [];
let kindEnum08 = true;            // false = migration 0008 not applied (file_kind lacks approval / court_notice)          // false = migration 0005 not applied (PostgREST 42703)
let profileColumns = true;       // false = migration 0012 not applied (members profile columns missing)
const memberPatches = [];
let membersInsert = 'ok';         // 'conflict' = a parallel first request already inserted (409 23505)
const cases = [{ id: 40, cr_no: '21', cr_year: 2026 }];
let caseInsertRace = false;       // true = unique violation on insert although the pre-check found nothing
let searchItems = [];
let dispatchFail = false;         // true = GitHub answers 401 Bad credentials
let storageTooBig = false;        // true = Storage refuses the object (bucket file_size_limit)
const authUsers = [{ id: 'au-old', email: 'Staff.Old@example.com' }]; // accounts that exist before any invite
const caseRows = { 40: { id: 40, cr_no: '21', cr_year: 2026, subject: 's' }, 43: { id: 43, cr_no: null, cr_year: null, subject: 's' } };
const searchUrls = [];
const letterRows = { 31: { id: 31, case_id: 7 }, 32: { id: 32, case_id: 7 }, 33: { id: 33, case_id: 7 } };
// draft edit (migration 0013): editColumns false = runs.kind / edit_* and file_kind 'spec' missing; specCases = case ids
// with a spec.json row; fileRows = case_files rows for the attachments check; editStale = edit rows the non-queue sweep hits
let editColumns = true;
const specCases = new Set();
const fileRows = [];
let editStale = [];
// C33 queue: in-memory runs table (Q = { rows, nextId, hook }) for the queue queries; null = column missing (legacy)
let Q = null;
const STALE = 3.5 * 3600 * 1000;
const isoNow = () => new Date().toISOString();
async function queueDb(u, opt, res) {
  const d = decodeURIComponent(u);
  const M = opt.method || 'GET';
  const rows = Q.rows;
  const since = Date.now() - STALE;
  const isActive = r => ['queued', 'running'].includes(r.state) &&
    (r.dispatched_at ? new Date(r.dispatched_at).getTime() > since : r.state === 'running' && new Date(r.created_at).getTime() > since);
  const byId = id => rows.find(r => r.id === Number(id));
  if (Q.hook) await Q.hook(d, M);
  const noEdit = d.includes('&kind=neq.edit');   // draft edit: the queue ignores kind 'edit'
  const queueRow = r => !noEdit || r.kind !== 'edit';
  if (/\/rest\/v1\/case_files\?case_id=eq\.\d+&kind=eq\.proposal/.test(d)) return res([{ id: 1 }]);
  if (d === `${SB}/rest/v1/runs` && M === 'POST') {
    const row = { id: Q.nextId++, state: 'queued', dispatched_at: null, created_at: new Date(Date.now() + Q.nextId).toISOString(), ...JSON.parse(opt.body) };
    rows.push(row); return res([{ ...row }], 201);
  }
  if (M === 'GET' && d.startsWith(`${SB}/rest/v1/runs?state=in.(queued,running)&or=`)) return res(rows.filter(isActive).filter(queueRow).sort((a, b) => a.id - b.id).map(r => ({ ...r })));
  if (M === 'GET' && d.startsWith(`${SB}/rest/v1/runs?state=eq.queued&dispatched_at=is.null`))
    return res(rows.filter(r => r.state === 'queued' && !r.dispatched_at).filter(queueRow).sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id).map(r => ({ ...r })));
  if (M === 'GET' && d.startsWith(`${SB}/rest/v1/runs?case_id=eq.`) && d.includes('&or=')) {
    const cid = Number(d.match(/case_id=eq\.(\d+)/)[1]);
    return res(rows.filter(r => r.case_id === cid && ['queued', 'running'].includes(r.state) && (!r.dispatched_at || isActive(r))).map(r => ({ id: r.id })));
  }
  if (M === 'GET' && d.startsWith(`${SB}/rest/v1/runs?created_at=gte.`)) return res(rows.map(r => ({ cost_usd: r.cost_usd ?? null, created_at: r.created_at, state: r.state, dispatched_at: r.dispatched_at ?? null })).concat(monthRuns.map(r => ({ dispatched_at: r.created_at, ...r }))));
  let m;
  if (M === 'PATCH' && (m = d.match(/\/runs\?id=eq\.(\d+)&state=eq\.queued&dispatched_at=is\.null$/))) {
    const r = byId(m[1]);
    if (!r || r.state !== 'queued' || r.dispatched_at) return res([]);
    Object.assign(r, JSON.parse(opt.body)); return res([{ ...r }]);
  }
  if (M === 'PATCH' && (m = d.match(/\/runs\?id=eq\.(\d+)&state=eq\.queued$/))) {
    const r = byId(m[1]); if (!r || r.state !== 'queued') return res([]);
    Object.assign(r, JSON.parse(opt.body)); Q.yields = (Q.yields || 0) + 1; return res([{ ...r }]);
  }
  if (M === 'PATCH' && (m = d.match(/\/runs\?id=eq\.(\d+)&state=in\.\(queued,running\)$/))) {
    const r = byId(m[1]); if (!r || !['queued', 'running'].includes(r.state)) return res([]);
    Object.assign(r, JSON.parse(opt.body)); return res([{ id: r.id, case_id: r.case_id }]);
  }
  if (M === 'PATCH' && (m = d.match(/\/runs\?id=eq\.(\d+)$/))) {
    const r = byId(m[1]); if (!r) return res([]);
    Object.assign(r, JSON.parse(opt.body)); return res([{ ...r }]);
  }
  if (M === 'PATCH' && (m = d.match(/\/runs\?kind=eq\.edit&created_at=lt\.([^&]+)&state=in\.\(queued,running\)$/))) {
    const lim = new Date(m[1]).getTime();
    const out = rows.filter(r => r.kind === 'edit' && ['queued', 'running'].includes(r.state) && new Date(r.created_at).getTime() < lim);
    out.forEach(r => Object.assign(r, JSON.parse(opt.body)));
    return res(out.map(r => ({ id: r.id, case_id: r.case_id, kind: r.kind })));
  }
  if (M === 'PATCH' && d.startsWith(`${SB}/rest/v1/runs?or=`)) {
    const out = rows.filter(r => ['queued', 'running'].includes(r.state) &&
      (r.dispatched_at ? new Date(r.dispatched_at).getTime() < since : r.state === 'running' && new Date(r.created_at).getTime() < since));
    out.forEach(r => Object.assign(r, JSON.parse(opt.body)));
    return res(out.map(r => ({ id: r.id, case_id: r.case_id })));
  }
  return null;
}
globalThis.fetch = async (u, opt = {}) => {
  u = String(u); calls.push({ u, opt });
  const res = (o, s = 200) => new Response(JSON.stringify(o), { status: s });
  // C33: without a queue table (Q null) the runs.dispatched_at column is "missing" (migration 0011 not applied) →
  // the Worker dispatches at once, as the older tests expect
  if (u.startsWith(`${SB}/rest/v1/runs`) && /dispatched_at/.test(decodeURIComponent(u) + (opt.body || ''))) {
    if (!Q) return res({ code: '42703', message: 'column runs.dispatched_at does not exist' }, 400);
  }
  if (u.startsWith(`${SB}/rest/v1/runs`) && !editColumns) {
    let b = {}; try { b = JSON.parse(opt.body || '{}') || {}; } catch { /* not JSON */ }
    if (/[?&]kind=/.test(decodeURIComponent(u)) || 'kind' in b) return res({ code: '42703', message: 'column runs.kind does not exist' }, 400);
  }
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.`) && u.includes('kind=eq.spec')) {
    if (!editColumns) return res({ code: '22P02', message: 'invalid input value for enum file_kind: "spec"' }, 400);
    return res(specCases.has(Number(u.match(/case_id=eq\.(\d+)/)[1])) ? [{ id: 900 }] : []);
  }
  if (u.startsWith(`${SB}/rest/v1/case_files?id=in.(`)) {
    const ids = decodeURIComponent(u).match(/id=in\.\(([^)]*)\)/)[1].split(',').map(Number);
    const cid = Number(u.match(/case_id=eq\.(\d+)/)[1]);
    return res(fileRows.filter(f => ids.includes(f.id) && f.case_id === cid).map(f => ({ id: f.id, kind: f.kind })));
  }
  if (!Q && u.startsWith(`${SB}/rest/v1/runs?kind=eq.edit&created_at=lt.`) && opt.method === 'PATCH') return res(editStale);
  if (Q) { const q = await queueDb(u, opt, res); if (q) return q; }
  if (u === `${SB}/auth/v1/user`) {
    const t = opt.headers.Authorization;
    if (t === 'Bearer owner-jwt') return res({ id: 'u1', email: 'abhi@example.com', email_confirmed_at: '2026-11-01T10:00:00Z' });
    if (t === 'Bearer unconfirmed-jwt') return res({ id: 'u2', email: 'Abhi@example.com' });
    if (t === 'Bearer owner2-jwt') return res({ id: 'u3', email: 'abhi@example.com', confirmed_at: '2026-11-01T10:00:00Z' });
    if (t === 'Bearer stranger-jwt') return res({ id: 'u9', email: 'x@example.com' });
    return res({}, 401);
  }
  if (u.startsWith(`${SB}/rest/v1/members?user_id=eq.`)) {
    // migration 0012 (members.display_name/designation/office/mine) applied unless profileColumns = false
    const sel = (new URL(u).searchParams.get('select') || 'role').split(',');
    if (!profileColumns && (sel.length > 1 || opt.method === 'PATCH')) return res({ code: '42703', message: 'column members.display_name does not exist' }, 400);
    const hit = members.filter(x => u.includes(x.user_id));
    if (opt.method === 'PATCH') { const b = JSON.parse(opt.body); memberPatches.push({ u, body: b }); hit.forEach(x => Object.assign(x, b)); }
    return res(hit.map(x => Object.fromEntries(sel.map(k => [k, x[k] ?? null]))));
  }
  if (u === `${SB}/rest/v1/members`) {
    const row = JSON.parse(opt.body);
    if (membersInsert === 'conflict') { members.push(row); return res({ code: '23505', message: 'duplicate key value violates unique constraint "members_pkey"' }, 409); }
    if (members.some(x => x.user_id === row.user_id) && /ignore-duplicates/.test(opt.headers.Prefer)) return res([], 201);
    members.push(row); return res([row], 201);
  }
  if (u === `${SB}/auth/v1/invite`) {
    const { email } = JSON.parse(opt.body);
    if (authUsers.some(x => x.email.toLowerCase() === email.toLowerCase())) return res({ code: 422, error_code: 'email_exists', msg: 'A user with this email address has already been registered' }, 422);
    const nu = { id: `au-${authUsers.length + 1}`, email }; authUsers.push(nu); return res(nu);
  }
  if (u.startsWith(`${SB}/auth/v1/admin/users?`)) {
    assert.equal(opt.headers.Authorization, 'Bearer service-secret-1234', 'admin API with the service role');
    const f = new URL(u).searchParams.get('filter');
    return res({ users: f ? authUsers.filter(x => x.email.toLowerCase().includes(f)) : authUsers });
  }
  if (!deskColumn && u.startsWith(`${SB}/rest/v1/cases`) && ['POST', 'PATCH'].includes(opt.method) && 'desk' in JSON.parse(opt.body)) return res({ code: 'PGRST204', message: "Could not find the 'desk' column of 'cases' in the schema cache" }, 400);
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.`) && u.endsWith('&select=*') && !opt.method) {
    const r = caseRows[u.match(/id=eq\.(\d+)/)[1]]; return res(r ? [r] : []);
  }
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.`) && u.includes('&select=id,cr_no,cr_year')) {
    const r = caseRows[u.match(/id=eq\.(\d+)/)[1]]; return res(r ? [r] : []);
  }
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.`) && opt.method === 'PATCH' && caseRows[u.match(/id=eq\.(\d+)/)[1]]) {
    const id = u.match(/id=eq\.(\d+)/)[1];
    caseRows[id] = { ...caseRows[id], ...JSON.parse(opt.body) }; return res([caseRows[id]]);
  }
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.proposal`)) return res([{ id: 1 }]);
  if (u === `${SB}/rest/v1/runs`) {
    const row = JSON.parse(opt.body); runInserts.push(row);
    if ('outputs' in row && !outputsColumn) return res({ code: 'PGRST204', message: "Could not find the 'outputs' column of 'runs' in the schema cache" }, 400);
    return res([{ id: 55, ...row }], 201);
  }
  if (u.startsWith(`${SB}/rest/v1/runs?created_at=gte.`) && !opt.method) { spendQueries.push(u); return res(monthRuns); }
  if (u.startsWith(`${SB}/rest/v1/runs?case_id=eq.`) && u.includes('state=in.(queued,running)') && !opt.method) return res(activeRuns.filter(r => u.includes(`case_id=eq.${r.case_id}&`)));
  if (u.startsWith(`${SB}/rest/v1/runs?id=eq.`) && u.endsWith('&config_taken_at=is.null') && opt.method === 'PATCH') {
    if (!configColumn) return res({ code: '42703', message: 'column runs.config_taken_at does not exist' }, 400);
    const id = u.match(/id=eq\.(\d+)&/)[1];
    if (id === '999' || configTaken.has(id)) return res([]);
    configTaken.add(id); return res([{ id: Number(id), config_taken_at: JSON.parse(opt.body).config_taken_at }]);
  }
  if (u.startsWith(`${SB}/rest/v1/runs?`) && opt.method === 'PATCH') {
    patches.push({ u, body: JSON.parse(opt.body) });
    if (u.includes('id=eq.80&state=in.(queued,running)')) return res([{ id: 80, case_id: 7 }]);
    if (u.includes('id=eq.55&state=in.(queued,running)')) return res(run55.state === 'failed' ? [] : (run55.state = 'failed', [{ id: 55, case_id: 7 }]));
    if (u.includes('created_at=lt.') && u.includes('state=in.(queued,running)')) return res([{ id: 60, case_id: 7 }, { id: 61, case_id: 8 }]);
    return res([]);
  }
  if (u === `${SB}/rest/v1/activity` && opt.method === 'POST') { acts.push(JSON.parse(opt.body)); return new Response(null, { status: 201 }); }
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.7&select=id`)) return res([{ id: 7 }]);
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.8&select=id`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.extra_doc`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.reply`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.approval`)) return res([{ version: 1 }]);
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.court_notice`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.gr&`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?id=eq.1&`)) return res([{ storage_path: 'outputs/7/study/v1/a.docx', original_name: 'a.docx' }]);
  if (u.startsWith(`${SB}/rest/v1/case_files?id=eq.2&`)) return res([{ storage_path: 'backups/7/x', original_name: 'x' }]);
  if (u === `${SB}/rest/v1/case_files` && opt.method === 'POST') {
    const row = JSON.parse(opt.body);
    if (!kindEnum08 && ['approval', 'court_notice'].includes(row.kind)) return res({ code: '22P02', message: `invalid input value for enum file_kind: "${row.kind}"` }, 400);
    return res([{ id: 9, ...row }], 201);
  }
  if (u.startsWith(`${SB}/storage/v1/object/sign/`)) return res({ signedURL: '/object/sign/x?token=t' });
  if (u.startsWith(`${SB}/storage/v1/object/`)) {
    if (storageTooBig) return res({ statusCode: '413', error: 'Payload too large', message: 'The object exceeded the maximum allowed size' }, 400);
    uploads.push(u); return res({ Key: 'k' });
  }
  if (u.startsWith(`${SB}/rest/v1/letters?case_id=eq.7&sent_date=not.is.null&reply_received_date=is.null`)) return res(pendingLetters);
  if (u.startsWith(`${SB}/rest/v1/letters?id=eq.`) && opt.method === 'PATCH') {
    letterPatches.push({ u, body: JSON.parse(opt.body) });
    const l = letterRows[u.match(/id=eq\.(\d+)/)[1]];
    return res(l ? [{ ...l, ...JSON.parse(opt.body) }] : []);
  }
  if (u === `${SB}/rest/v1/letters` && opt.method === 'POST') return res([{ id: 50, ...JSON.parse(opt.body) }], 201);
  if (u.startsWith(`${SB}/rest/v1/cases?cr_no=match.`)) {
    const re = new RegExp(decodeURIComponent(u.match(/cr_no=match\.([^&]+)/)[1]));
    const y = Number(u.match(/cr_year=eq\.(\d+)/)[1]);
    const neq = (u.match(/id=neq\.(\d+)/) || [])[1];
    return res(cases.filter(c => re.test(c.cr_no) && c.cr_year === y && String(c.id) !== neq).map(c => ({ id: c.id })));
  }
  if (u === `${SB}/rest/v1/cases` && opt.method === 'POST') {
    const row = JSON.parse(opt.body); caseInserts.push(row);
    if (caseInsertRace) { cases.push({ id: 41, cr_no: row.cr_no, cr_year: Number(row.cr_year) }); return res({ code: '23505', message: 'duplicate key value violates unique constraint "cases_cr_no_cr_year_key"' }, 409); }
    return res([{ id: 42, ...row }], 201);
  }
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.999`) && opt.method === 'PATCH') return res({ code: '22P02', message: 'invalid input syntax for type bigint: "secret detail"' }, 400);
  if (u.startsWith('https://api.github.com/search/code?')) { searchUrls.push(u); return res({ items: searchItems }); }
  if (u.startsWith(`${SB}/rest/v1/`)) return new Response(null, { status: 204 });
  if (u.endsWith('/dispatches')) return dispatchFail ? res({ message: 'Bad credentials', documentation_url: 'https://docs.github.com/rest' }, 401) : new Response(null, { status: 204 });
  throw new Error('unexpected fetch ' + u);
};
const HTML = '<!doctype html><html><head><script>var t = 1;</script></head><body><script type="module" src="/assets/a.js"></script></body></html>';
const env = { SETTINGS: kv(), ASSETS: { fetch: async req => {
  const p = new URL(req.url).pathname;
  if (p.startsWith('/assets/')) return new Response('js', { headers: { 'content-type': 'text/javascript' } });
  return new Response(p.startsWith('/nasti/') ? '<html><script>eval("1")</script></html>' : HTML, { headers: { 'content-type': 'text/html; charset=utf-8' } });
} } };
const call = (path, opt = {}) => worker.fetch(new Request('https://desk.example' + path, opt), env);
const body = r => r.json();

test('setup → settings masking → auth → run dispatch → engine config', async () => {
  assert.equal((await body(await call('/api/public-config'))).configured, false);
  assert.equal((await call('/api/cases', { method: 'POST', body: '{}' })).status, 503);

  await call('/api/setup');
  const code = env.SETTINGS.m.get('setup_code');
  assert.match(code, /^[0-9a-f]{12}$/);
  const setup = b => call('/api/setup', { method: 'POST', body: JSON.stringify(b) });
  const base = { owner_email: 'abhi@example.com', supabase_url: SB, supabase_anon_key: 'anon', supabase_service_key: 'service-secret-1234' };
  assert.equal((await setup({ ...base, setup_code: 'wrong' })).status, 403);
  assert.equal((await setup({ ...base, setup_code: code })).status, 200);
  assert.equal(env.SETTINGS.m.has('setup_code'), false);
  assert.equal((await setup({ ...base, setup_code: code })).status, 409, 'setup locked after first save');

  const pub = await body(await call('/api/public-config'));
  assert.deepEqual(pub, { configured: true, supabase_url: SB, supabase_anon_key: 'anon' }, 'no secret in public config');

  assert.equal((await call('/api/me')).status, 401);
  const stranger = { headers: { authorization: 'Bearer stranger-jwt' } };
  assert.equal((await call('/api/me', stranger)).status, 403);
  const owner = { authorization: 'Bearer owner-jwt' };
  assert.equal((await body(await call('/api/me', { headers: owner }))).role, 'owner', 'owner email becomes owner on first login');

  const put = b => call('/api/settings', { method: 'PUT', headers: owner, body: JSON.stringify(b) });
  await put({ github_repo: 'o/r', github_token: 'ghp_secret_abcd', anthropic_api_key: 'sk-ant-secret-wxyz', model: 'claude-opus-5-5' });
  let s = await body(await call('/api/settings', { headers: owner }));
  assert.equal(s.github_token, '••••abcd'); assert.equal(s.anthropic_api_key, '••••wxyz'); assert.equal(s.supabase_service_key, '••••1234');
  await put({ anthropic_api_key: '••••wxyz', github_token: '' });
  assert.equal(env.SETTINGS.m.get('anthropic_api_key'), 'sk-ant-secret-wxyz', 'masked value does not overwrite the secret');
  assert.equal(env.SETTINGS.m.get('github_token'), 'ghp_secret_abcd');
  // model_light + budget_usd: plain settings, round-trip, budget validated (positive, <= 20)
  for (const v of ['0', '-1', '20.5', 'abc']) assert.equal((await put({ budget_usd: v, model_light: 'x' })).status, 400, `budget ${v} refused`);
  assert.equal(env.SETTINGS.m.has('model_light'), false, 'nothing saved on a refused PUT');
  assert.equal((await put({ model_light: 'claude-haiku-4-5', model_review: 'claude-opus-5-5', budget_usd: '0.75' })).status, 200);
  s = await body(await call('/api/settings', { headers: owner }));
  assert.equal(s.model_light, 'claude-haiku-4-5'); assert.equal(s.model_review, 'claude-opus-5-5'); assert.equal(s.budget_usd, '0.75');
  assert.equal((await put({ budget_usd: '20' })).status, 200);
  assert.equal((await put({ budget_usd: '1.5' })).status, 200);
  // monthly_budget_usd: plain setting, positive <= 1000, empty = no limit
  for (const v of ['0', '-5', '1000.01', 'abc']) assert.equal((await put({ monthly_budget_usd: v })).status, 400, `monthly ${v} refused`);
  assert.equal(env.SETTINGS.m.has('monthly_budget_usd'), false, 'nothing saved on a refused PUT');
  assert.equal((await put({ monthly_budget_usd: '1000' })).status, 200);
  assert.equal((await body(await call('/api/settings', { headers: owner }))).monthly_budget_usd, '1000');
  assert.equal((await put({ monthly_budget_usd: '' })).status, 200);
  assert.equal(env.SETTINGS.m.get('monthly_budget_usd'), '', 'empty clears the limit');

  const run = await call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7, instructions: 'पत्र नको' }) });
  assert.equal(run.status, 200, await run.clone().text());
  const d = calls.find(c => c.u.endsWith('/dispatches'));
  assert.equal(d.u, 'https://api.github.com/repos/o/r/dispatches');
  const payload = JSON.parse(d.opt.body).client_payload;
  assert.equal(payload.run_id, 55); assert.equal(payload.worker, 'https://desk.example');
  assert.ok(!d.opt.body.includes('sk-ant'), 'API key never sent to GitHub');

  const cfg = t => call(`/api/engine/config?run_id=55`, { headers: { authorization: `Bearer ${t}` } });
  assert.equal((await cfg('nope')).status, 403);
  assert.equal((await call(`/api/engine/config?run_id=56`, { headers: { authorization: `Bearer ${payload.token}` } })).status, 403, 'token bound to its run');
  const ec = await body(await cfg(payload.token));
  assert.equal(ec.anthropic_api_key, 'sk-ant-secret-wxyz'); assert.equal(ec.supabase_service_key, 'service-secret-1234');
  assert.equal(ec.model, 'claude-opus-5-5'); assert.equal(ec.model_light, 'claude-haiku-4-5'); assert.equal(ec.model_review, 'claude-opus-5-5'); assert.equal(ec.budget_usd, '1.5');
  assert.equal((await cfg(payload.token)).status, 403, 'config token is single use');

  // engine fail with the (used) run token: only its own run, only while queued/running
  const fail = (t, b) => call('/api/engine/fail', { method: 'POST', headers: { authorization: `Bearer ${t}` }, body: JSON.stringify(b) });
  assert.equal((await fail('nope', { run_id: 55, reason: 'x' })).status, 403);
  assert.equal((await fail(payload.token, { run_id: 56, reason: 'x' })).status, 403, 'fail bound to its run');
  const f1 = await body(await fail(payload.token, { run_id: 55, reason: 'सेटिंग्ज अपूर्ण' }));
  assert.equal(f1.changed, 1);
  const pf = patches.find(x => x.u.includes('id=eq.55&state=in.(queued,running)'));
  assert.equal(pf.body.state, 'failed'); assert.equal(pf.body.step, 'सेटिंग्ज अपूर्ण'); assert.ok(pf.body.finished_at);
  assert.equal(acts.at(-1)[0].action, 'run_failed');
  assert.equal((await body(await fail(payload.token, { run_id: 55, reason: 'y' }))).changed, 0, 'already failed run unchanged');
  assert.ok(!JSON.stringify(f1).includes('secret'), 'fail returns no secret');
});

test('config incomplete → 412, token not consumed', async () => {
  const exp = Math.floor(Date.now() / 1000) + 3600;
  env.SETTINGS.m.set('run_token:tok2', JSON.stringify({ run_id: '70', used: false, exp }));
  const key = env.SETTINGS.m.get('anthropic_api_key');
  env.SETTINGS.m.delete('anthropic_api_key');
  const r = await call('/api/engine/config?run_id=70', { headers: { authorization: 'Bearer tok2' } });
  assert.equal(r.status, 412);
  assert.equal(JSON.parse(env.SETTINGS.m.get('run_token:tok2')).used, false);
  env.SETTINGS.m.set('anthropic_api_key', key);
  env.SETTINGS.m.set('run_token:old', '71'); // token issued before the change (plain run id) still works once
  assert.equal((await call('/api/engine/config?run_id=71', { headers: { authorization: 'Bearer old' } })).status, 200);
  assert.equal((await call('/api/engine/config?run_id=71', { headers: { authorization: 'Bearer old' } })).status, 403);
});

test('sweep, upload case check, signed-URL bucket whitelist', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  patches.length = 0; acts.length = 0;
  const sw = await body(await call('/api/runs/sweep', { method: 'POST', headers: owner }));
  assert.deepEqual(sw.failed, [60, 61]);
  const p = patches[0];
  const before = decodeURIComponent(p.u.match(/created_at=lt\.([^&]+)/)[1]);
  const age = Date.now() - new Date(before).getTime();
  assert.ok(Math.abs(age - 3.5 * 3600 * 1000) < 60000, 'cut-off = 3.5 h');
  assert.equal(p.body.step, "वेळ संपली. कृपया 'पुन्हा तयार करा' वापरावे, ही विनंती.");
  assert.equal(acts[0].length, 2);

  const up = (cid, kind = 'extra_doc') => call(`/api/upload?case_id=${cid}&kind=${kind}`, { method: 'POST', headers: { ...owner, 'x-file-name': encodeURIComponent('पत्र.pdf'), 'content-type': 'application/pdf' }, body: 'x' });
  uploads.length = 0;
  assert.equal((await up(8)).status, 404, 'unknown case refused');
  assert.equal(uploads.length, 0, 'nothing stored for unknown case');
  const ok = await up(7);
  assert.equal(ok.status, 200, await ok.clone().text());
  assert.equal(uploads.length, 1);

  assert.equal((await call('/api/files/1', { headers: owner })).status, 200);
  assert.equal((await call('/api/files/2', { headers: owner })).status, 403, 'bucket outside proposals|outputs|gr-library refused');
});

test('reply upload marks the single pending letter answered; several pending left alone', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const up = () => call('/api/upload?case_id=7&kind=reply', { method: 'POST', headers: { ...owner, 'x-file-name': encodeURIComponent('उत्तर.pdf'), 'content-type': 'application/pdf' }, body: 'x' });
  letterPatches.length = 0;
  pendingLetters = [{ id: 31 }];
  const r1 = await up(); const one = await body(r1); assert.equal(r1.status, 200, JSON.stringify(one));
  assert.equal(one.letter_updated, 31); assert.equal(one.pending_letters, 1);
  assert.equal(letterPatches.length, 1);
  assert.ok(letterPatches[0].u.includes('letters?id=eq.31'));
  assert.equal(letterPatches[0].body.status, 'उत्तर प्राप्त');
  assert.match(letterPatches[0].body.reply_received_date, /^\d{4}-\d{2}-\d{2}$/);

  pendingLetters = [{ id: 31 }, { id: 32 }];
  const many = await body(await up());
  assert.equal(many.letter_updated, null); assert.equal(many.pending_letters, 2);
  assert.equal(letterPatches.length, 1, 'several pending: none patched');

  pendingLetters = [];
  const ex = await body(await call('/api/upload?case_id=7&kind=extra_doc', { method: 'POST', headers: { ...owner, 'x-file-name': encodeURIComponent('a.pdf') }, body: 'x' }));
  assert.equal(ex.letter_updated, null);
});

test('monthly spend: IST month sum, boundary, 402 block on /api/run', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const realNow = Date.now;
  // 2026-10-31 19:00 UTC = 2026-11-01 00:30 IST → month 2026-11 (IST month starts 2026-10-31 18:30 UTC)
  Date.now = () => Date.parse('2026-10-31T19:00:00Z');
  try {
    monthRuns = [
      { cost_usd: '9.99', created_at: '2026-10-31T18:29:59Z' }, // 31.10 23:59:59 IST → previous month
      { cost_usd: '0.5', created_at: '2026-10-31T18:30:00Z' },  // 01.11 00:00 IST → counted
      { cost_usd: 1.25, created_at: '2026-11-15T10:00:00+00:00' },
      { cost_usd: null, created_at: '2026-11-20T10:00:00Z' },   // run without cost → counts as a run, $0
      { cost_usd: '7', created_at: '2026-11-30T18:30:00Z' },    // 01.12 00:00 IST → next month
    ];
    spendQueries.length = 0;
    env.SETTINGS.m.set('monthly_budget_usd', '');
    const s = await body(await call('/api/spend', { headers: owner }));
    assert.deepEqual(s, { month: '2026-11', spent_usd: 1.75, limit_usd: 20, runs: 3, reserved_usd: 0, active_runs: 0 }, 'empty setting = default $20');
    const q = decodeURIComponent(spendQueries[0]);
    assert.ok(q.includes('created_at=gte.2026-10-31T18:30:00.000Z'), q);
    assert.ok(q.includes('created_at=lt.2026-11-30T18:30:00.000Z'), q);
    assert.ok(q.includes('select=cost_usd,created_at'));

    // one minute before the IST month boundary: 31.10 18:29 UTC = 31.10 23:59 IST → still October
    Date.now = () => Date.parse('2026-10-31T18:29:00Z');
    assert.equal((await body(await call('/api/spend', { headers: owner }))).month, '2026-10');
    Date.now = () => Date.parse('2026-10-31T19:00:00Z');

    const dispatches = () => calls.filter(c => c.u.endsWith('/dispatches')).length;
    const run = () => call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7 }) });
    env.SETTINGS.m.set('monthly_budget_usd', '1.75');
    const n0 = dispatches();
    const r = await run();
    assert.equal(r.status, 402);
    assert.deepEqual(await r.json(), { error: 'monthly_budget_reached', spent_usd: 1.75, limit_usd: 1.75, reserved_usd: 0 });
    assert.equal(dispatches(), n0, 'no dispatch when the limit is reached');
    assert.equal((await body(await call('/api/spend', { headers: owner }))).limit_usd, 1.75);

    env.SETTINGS.m.set('monthly_budget_usd', '2');
    assert.equal((await run()).status, 200, 'under the limit → runs');
    assert.equal(dispatches(), n0 + 1);
    // default $20: 19.99 runs, 20 (= limit) blocks
    env.SETTINGS.m.set('monthly_budget_usd', '');
    monthRuns = [{ cost_usd: '19.99', created_at: '2026-11-02T10:00:00Z' }];
    assert.equal((await run()).status, 200, 'below default $20 → runs');
    monthRuns = [{ cost_usd: '12', created_at: '2026-11-02T10:00:00Z' }, { cost_usd: '8', created_at: '2026-11-03T10:00:00Z' }];
    const rd = await run();
    assert.equal(rd.status, 402, 'default $20 reached → blocked');
    assert.deepEqual(await rd.json(), { error: 'monthly_budget_reached', spent_usd: 20, limit_usd: 20, reserved_usd: 0 });
    assert.equal(dispatches(), n0 + 2);
  } finally {
    Date.now = realNow;
    env.SETTINGS.m.set('monthly_budget_usd', '');
    monthRuns = [];
  }
});

test('one run at a time per case (409), engine step via run token, provider settings (A/C)', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  monthRuns = [];
  // H3: an active (queued/running, not stale) run blocks a second dispatch
  activeRuns = [{ id: 77, case_id: 7 }];
  const before = calls.filter(c => c.u.endsWith('/dispatches')).length;
  const r = await call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7 }) });
  assert.equal(r.status, 409);
  assert.deepEqual(await r.json(), { error: 'run_active', run_id: 77 });
  assert.equal(calls.filter(c => c.u.endsWith('/dispatches')).length, before, 'no second dispatch');
  const q = calls.filter(c => c.u.includes('runs?case_id=eq.7&state=in.(queued,running)&created_at=gt.')).at(-1);
  assert.ok(q, 'active-run query has the stale cut-off');
  activeRuns = [];
  assert.equal((await call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7 }) })).status, 200);
  assert.equal((await call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: '7&x=1' }) })).status, 400, 'case_id must be an integer');

  // H1: progress text through the Worker (the Claude step has no Supabase key)
  const exp = Math.floor(Date.now() / 1000) + 3600;
  env.SETTINGS.m.set('run_token:tok80', JSON.stringify({ run_id: '80', used: true, exp }));
  const step = (t, b) => call('/api/engine/step', { method: 'POST', headers: { authorization: `Bearer ${t}` }, body: JSON.stringify(b) });
  assert.equal((await step('nope', { run_id: 80, step: 'x' })).status, 403);
  assert.equal((await step('tok80', { run_id: 81, step: 'x' })).status, 403, 'step bound to its run');
  assert.equal((await step('tok80', { run_id: 80, step: ' ' })).status, 400);
  const st = await step('tok80', { run_id: 80, step: 'पाने वाचत आहे' });
  assert.equal(st.status, 200); assert.equal((await st.json()).changed, 1);
  const pp = patches.at(-1);
  assert.ok(pp.u.includes('id=eq.80&state=in.(queued,running)')); assert.deepEqual(pp.body, { step: 'पाने वाचत आहे' });
  env.SETTINGS.m.set('run_token:tokold', JSON.stringify({ run_id: '80', used: true, exp: 1000 }));
  assert.equal((await step('tokold', { run_id: 80, step: 'x' })).status, 403, 'expired token refused');

  // A/C settings: provider enums, model names, keys masked, keys sent to the engine only for a chosen provider
  const put = b => call('/api/settings', { method: 'PUT', headers: owner, body: JSON.stringify(b) });
  assert.equal((await put({ part1_provider: 'anthropic-x' })).status, 400);
  assert.equal((await put({ engine_provider: 'github' })).status, 400, 'GitHub Models retired (30.07.2026) — not a provider');
  assert.equal((await put({ cloudflare_account_id: 'xyz' })).status, 400);
  assert.equal((await put({ ollama_base_url: 'ftp://x' })).status, 400);
  assert.equal((await put({ fallback_provider: 'grok' })).status, 400);
  assert.equal((await put({ gemini_model: '$(id)' })).status, 400);
  assert.equal((await put({ gemini_api_key: 'AIza-gem-secret-1111', openai_api_key: 'sk-openai-secret-2222', gemini_model: 'gemini-2.5-flash' })).status, 200);
  const s1 = await (await call('/api/settings', { headers: owner })).json();
  assert.equal(s1.gemini_api_key, '••••1111'); assert.equal(s1.openai_api_key, '••••2222'); assert.equal(s1.gemini_model, 'gemini-2.5-flash');
  let cfgRun = 90;
  const cfgOf = async () => {
    const t = 'tokcfg' + Math.random().toString(16).slice(2);
    const id = String(cfgRun++); // one config read per run (single use is per run in Postgres too)
    env.SETTINGS.m.set(`run_token:${t}`, JSON.stringify({ run_id: id, used: false, exp }));
    return (await call(`/api/engine/config?run_id=${id}`, { headers: { authorization: `Bearer ${t}` } })).json();
  };
  let c = await cfgOf();
  assert.ok(!('gemini_api_key' in c) && !('openai_api_key' in c), 'no provider chosen -> no extra key leaves the Worker');
  assert.equal((await put({ part1_provider: 'gemini' })).status, 200);
  c = await cfgOf();
  assert.equal(c.gemini_api_key, 'AIza-gem-secret-1111'); assert.ok(!('openai_api_key' in c)); assert.equal(c.part1_provider, 'gemini');
  assert.equal((await put({ part1_provider: '', fallback_provider: 'openai', fallback_model: 'gpt-6.1-terra', fallback_model_light: 'gpt-5.4-mini' })).status, 200);
  c = await cfgOf();
  assert.equal(c.openai_api_key, 'sk-openai-secret-2222'); assert.ok(!('gemini_api_key' in c));
  assert.equal(c.fallback_provider, 'openai'); assert.equal(c.fallback_model, 'gpt-6.1-terra'); assert.equal(c.fallback_model_light, 'gpt-5.4-mini');
  assert.equal((await put({ fallback_provider: '' })).status, 200);

  // engine on another provider (free / other models): its key is sent, the Anthropic key is then not required
  assert.equal((await put({ openrouter_api_key: 'sk-or-secret-3333', engine_provider: 'openrouter', engine_model: 'nvidia/nemotron-3.5-super-vl:free', engine_model_light: 'google/gemma-4-31b:free' })).status, 200);
  c = await cfgOf();
  assert.equal(c.openrouter_api_key, 'sk-or-secret-3333'); assert.ok(!('openai_api_key' in c) && !('gemini_api_key' in c));
  assert.equal(c.engine_provider, 'openrouter'); assert.equal(c.engine_model, 'nvidia/nemotron-3.5-super-vl:free');
  const ak = env.SETTINGS.m.get('anthropic_api_key');
  env.SETTINGS.m.delete('anthropic_api_key');
  c = await cfgOf();
  assert.equal(c.openrouter_api_key, 'sk-or-secret-3333', 'no Anthropic key needed when another provider runs the engine');
  assert.equal((await put({ engine_provider: 'groq' })).status, 200);
  const t412 = 'tok412';
  env.SETTINGS.m.set(`run_token:${t412}`, JSON.stringify({ run_id: '91', used: false, exp }));
  assert.equal((await call('/api/engine/config?run_id=91', { headers: { authorization: `Bearer ${t412}` } })).status, 412, 'engine provider without its key -> incomplete');
  // self-hosted Ollama needs only its URL
  assert.equal((await put({ engine_provider: 'ollama', ollama_base_url: 'https://ollama.office.example:11434', engine_model: 'gemma4:31b' })).status, 200);
  c = await cfgOf();
  assert.equal(c.ollama_base_url, 'https://ollama.office.example:11434'); assert.equal(c.engine_model, 'gemma4:31b');
  env.SETTINGS.m.set('anthropic_api_key', ak);
  assert.equal((await put({ engine_provider: '' })).status, 200);
});

test('engine config: atomic single use in Postgres, KV fallback without migration 0005, model_strong/effort', async () => {
  const exp = Math.floor(Date.now() / 1000) + 3600;
  const get = (t, id) => call(`/api/engine/config?run_id=${id}`, { headers: { authorization: `Bearer ${t}` } });
  // two tokens for one run (or a KV read that has not seen the "used" write yet): only the first conditional PATCH wins
  env.SETTINGS.m.set('run_token:ta', JSON.stringify({ run_id: '100', used: false, exp }));
  env.SETTINGS.m.set('run_token:tb', JSON.stringify({ run_id: '100', used: false, exp }));
  const [a, b] = await Promise.all([get('ta', 100), get('tb', 100)]);
  assert.deepEqual([a.status, b.status].sort(), [200, 403], 'exactly one config read per run');
  const pq = calls.filter(c => c.u.includes('runs?id=eq.100&config_taken_at=is.null'));
  assert.equal(pq.length, 2); assert.equal(pq[0].opt.method, 'PATCH'); assert.ok(JSON.parse(pq[0].opt.body).config_taken_at);
  assert.match(pq[0].opt.headers.Prefer, /return=representation/);
  env.SETTINGS.m.set('run_token:tc', JSON.stringify({ run_id: '999', used: false, exp }));
  assert.equal((await get('tc', 999)).status, 403, 'no runs row → refused');
  // 412 leaves the token unused in KV and in Postgres
  const key = env.SETTINGS.m.get('anthropic_api_key');
  env.SETTINGS.m.delete('anthropic_api_key');
  env.SETTINGS.m.set('run_token:td', JSON.stringify({ run_id: '101', used: false, exp }));
  assert.equal((await get('td', 101)).status, 412);
  assert.equal(configTaken.has('101'), false);
  env.SETTINGS.m.set('anthropic_api_key', key);
  assert.equal((await get('td', 101)).status, 200);
  assert.equal(JSON.parse(env.SETTINGS.m.get('run_token:td')).used, true, 'KV flag kept');
  assert.equal((await get('td', 101)).status, 403);
  // column missing (migration 0005 not applied yet): KV flag alone, still single use
  configColumn = false;
  try {
    env.SETTINGS.m.set('run_token:te', JSON.stringify({ run_id: '102', used: false, exp }));
    const r = await get('te', 102);
    assert.equal(r.status, 200, await r.clone().text());
    assert.equal((await get('te', 102)).status, 403);
  } finally { configColumn = true; }

  // model_strong + effort: validated, saved, sent to the engine
  const owner = { authorization: 'Bearer owner-jwt' };
  const put = x => call('/api/settings', { method: 'PUT', headers: owner, body: JSON.stringify(x) });
  for (const x of [{ model_strong: '$(id)' }, { effort: 'huge' }, { effort: 'High' }]) assert.equal((await put(x)).status, 400, JSON.stringify(x));
  assert.equal((await put({ model_strong: 'claude-opus-5-5', effort: 'xhigh' })).status, 200);
  const s = await body(await call('/api/settings', { headers: owner }));
  assert.equal(s.model_strong, 'claude-opus-5-5'); assert.equal(s.effort, 'xhigh');
  env.SETTINGS.m.set('run_token:tf', JSON.stringify({ run_id: '103', used: false, exp }));
  const ec = await body(await get('tf', 103));
  assert.equal(ec.model_strong, 'claude-opus-5-5'); assert.equal(ec.effort, 'xhigh');
  for (const v of ['none', '']) assert.equal((await put({ model_strong: v })).status, 200, `model_strong ${v} allowed`);
  assert.equal((await put({ effort: '' })).status, 200, 'empty effort = engine default');
});

test('settings: required keys never saved empty', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const put = x => call('/api/settings', { method: 'PUT', headers: owner, body: JSON.stringify(x) });
  for (const k of ['supabase_url', 'supabase_anon_key', 'owner_email']) {
    const before = env.SETTINGS.m.get(k);
    assert.equal((await put({ [k]: '  ', model_light: 'claude-x-1' })).status, 400, `${k} empty refused`);
    assert.equal(env.SETTINGS.m.get(k), before);
  }
  assert.notEqual(env.SETTINGS.m.get('model_light'), 'claude-x-1', 'nothing saved on a refused PUT');
  assert.equal((await put({ supabase_service_key: '' })).status, 200, 'empty service key = unchanged');
  assert.equal(env.SETTINGS.m.get('supabase_service_key'), 'service-secret-1234');
});

test('owner by email: confirmed e-mail only; parallel first sign-in does not fail', async () => {
  assert.equal((await call('/api/me', { headers: { authorization: 'Bearer unconfirmed-jwt' } })).status, 403, 'unconfirmed owner e-mail is not owner');
  assert.ok(!members.some(x => x.user_id === 'u2'));
  // u3 (confirmed_at): a parallel first request already wrote the row → 409 on our insert → re-read
  membersInsert = 'conflict';
  try {
    const r = await call('/api/me', { headers: { authorization: 'Bearer owner2-jwt' } });
    assert.equal(r.status, 200, await r.clone().text());
    assert.equal((await r.json()).role, 'owner');
  } finally { membersInsert = 'ok'; }
  const ins = calls.filter(c => c.u === `${SB}/rest/v1/members` && c.opt.method === 'POST').at(-1);
  assert.match(ins.opt.headers.Prefer, /resolution=ignore-duplicates/);
});

test('cases: duplicate C R ignoring leading zeros, insert race → duplicate_cr; generic DB error text', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const mk = b => call('/api/cases', { method: 'POST', headers: owner, body: JSON.stringify({ subject: 'x', ...b }) });
  let r = await mk({ cr_no: '021', cr_year: 2026 });
  assert.equal(r.status, 409); assert.deepEqual(await r.json(), { error: 'duplicate_cr', existing_id: 40 });
  r = await mk({ cr_no: '210', cr_year: 2026 });
  assert.equal(r.status, 200, 'different number not a duplicate');
  assert.equal((await r.json()).cr_no, '210', 'stored as given');
  caseInsertRace = true;
  try {
    r = await mk({ cr_no: '0055', cr_year: 2026 });
    assert.equal(r.status, 409);
    assert.deepEqual(await r.json(), { error: 'duplicate_cr', existing_id: 41 });
  } finally { caseInsertRace = false; }
  // DB error body never reaches the browser
  r = await call('/api/letters', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 999, sent_date: '2026-11-02' }) });
  assert.equal(r.status, 500);
  const t = await r.text();
  assert.ok(!t.includes('secret detail') && !t.includes('bigint'), t);
  assert.deepEqual(JSON.parse(t), { error: 'db 400' });
});

test('ids validated; upload name decoding; letters PATCH 404/whitelist/log/stage', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const n0 = calls.length;
  for (const id of ['7&x=1', '7.5', '-1', '']) {
    assert.equal((await call(`/api/upload?case_id=${encodeURIComponent(id)}&kind=extra_doc`, { method: 'POST', headers: { ...owner, 'x-file-name': 'a.pdf' }, body: 'x' })).status, 400, `upload case_id ${id}`);
    assert.equal((await call('/api/letters', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: id }) })).status, 400, `letters case_id ${id}`);
  }
  assert.ok(!calls.slice(n0).some(c => c.u.includes('/rest/v1/cases?') || c.u.includes('/rest/v1/letters')), 'no DB call for a bad id');
  assert.equal((await call('/api/upload?case_id=7&kind=extra_doc', { method: 'POST', headers: { ...owner, 'x-file-name': '%E0%A4' }, body: 'x' })).status, 400, 'bad URI encoding → 400');
  const lp = await call('/api/letters', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: '7', ref_no: 'r' }) });
  assert.equal(lp.status, 200);

  const patch = (id, b) => call(`/api/letters/${id}`, { method: 'PATCH', headers: owner, body: JSON.stringify(b) });
  assert.equal((await patch(77, { ref_no: 'x' })).status, 404, 'no such letter');
  for (const st of ['बंद', '', 'sent']) assert.equal((await patch(31, { status: st })).status, 400, `status ${st}`);
  acts.length = 0; patches.length = 0;
  const casePatches = () => calls.filter(c => c.u.startsWith(`${SB}/rest/v1/cases?id=eq.7`) && c.opt.method === 'PATCH');
  const c0 = casePatches().length;
  let r = await patch(32, { status: 'स्मरणपत्र' });
  assert.equal(r.status, 200); assert.equal((await r.json()).id, 32);
  assert.equal(casePatches().length, c0, 'no stage change without sent_date');
  assert.equal(acts.at(-1).action, 'letter_updated'); assert.equal(acts.at(-1).detail.letter_id, 32); assert.equal(acts.at(-1).case_id, 7);
  r = await patch(33, { sent_date: '2026-11-02' });
  assert.equal(r.status, 200);
  const cp = casePatches().at(-1);
  assert.equal(casePatches().length, c0 + 1);
  assert.deepEqual(JSON.parse(cp.opt.body), { stage: 'पत्र पाठवले (माहिती प्रतीक्षेत)' });
});

test('search: qualifiers stripped, hits outside github_repo dropped', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  searchItems = [
    { path: 'register/a.md', repository: { full_name: 'o/r' }, text_matches: [{ fragment: 'f1' }] },
    { path: 'secret.md', repository: { full_name: 'other/private' }, text_matches: [{ fragment: 'leak' }] },
  ];
  const r = await body(await call(`/api/search?q=${encodeURIComponent('वेतन repo:other/private OR org:x -path:y language:md ACP')}`, { headers: owner }));
  assert.deepEqual(r, [{ path: 'register/a.md', frags: ['f1'] }]);
  const q = new URL(searchUrls.at(-1)).searchParams.get('q');
  assert.equal(q, 'वेतन OR ACP repo:o/r path:register');
  const n = searchUrls.length;
  assert.deepEqual(await body(await call(`/api/search?q=${encodeURIComponent('repo:x/y')}`, { headers: owner })), [], 'only qualifiers → no search');
  assert.equal(searchUrls.length, n);
  // R3 (UI audit 04.11.2026): GitHub not set → 503 with a Marathi reason (not an empty list that reads as "nothing found")
  const tok = env.SETTINGS.m.get('github_token');
  env.SETTINGS.m.delete('github_token');
  try {
    const r2 = await call(`/api/search?q=${encodeURIComponent('वेतन')}`, { headers: owner });
    assert.equal(r2.status, 503);
    assert.deepEqual(await r2.json(), { error: 'search_unavailable', reason: 'नियम-उतारे शोध-सेवा जोडलेली नाही — कृपया मालकांनी सेटिंग्ज भरावीत.' });
    assert.equal(searchUrls.length, n, 'no GitHub call');
  } finally {
    env.SETTINGS.m.set('github_token', tok);
  }
});

test('monthly limit counts queued/running runs at an estimate', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const now = new Date().toISOString();
  const old = new Date(Date.now() - 4 * 3600 * 1000).toISOString();
  const run = () => call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7 }) });
  try {
    env.SETTINGS.m.set('monthly_budget_usd', '3');
    // spent 1.0 + 1.6 (done) = 2.6; median finished = (1.0+1.6)/2 = 1.3; one running run reserves 1.3 → 3.9 >= 3
    monthRuns = [{ cost_usd: '1.0', created_at: now, state: 'done' }, { cost_usd: '1.6', created_at: now, state: 'done' }, { cost_usd: null, created_at: now, state: 'running' }];
    let r = await run();
    assert.equal(r.status, 402);
    assert.deepEqual(await r.json(), { error: 'monthly_budget_reached', spent_usd: 2.6, limit_usd: 3, reserved_usd: 1.3 });
    // a stale running run does not reserve
    monthRuns[2].created_at = old;
    assert.equal((await run()).status, 200);
    // no finished run with a cost → per-run budget_usd (1.5 here); two queued = 3 → blocked
    monthRuns = [{ cost_usd: null, created_at: now, state: 'queued' }, { cost_usd: null, created_at: now, state: 'queued' }];
    r = await run();
    assert.equal(r.status, 402); assert.equal((await r.json()).reserved_usd, 3);
    // budget_usd empty → $0.75 each: 1.5 < 3 → runs
    const bud = env.SETTINGS.m.get('budget_usd');
    env.SETTINGS.m.set('budget_usd', '');
    try { assert.equal((await run()).status, 200); } finally { env.SETTINGS.m.set('budget_usd', bud); }
    // /api/spend: reserved_usd / active_runs added (A3 audit: the app checks spent + reserved like the Worker)
    monthRuns = [{ cost_usd: '1.0', created_at: now, state: 'done' }, { cost_usd: null, created_at: now, state: 'running' }];
    const sp = await body(await call('/api/spend', { headers: owner }));
    assert.deepEqual(Object.keys(sp), ['month', 'spent_usd', 'limit_usd', 'runs', 'reserved_usd', 'active_runs']);
    assert.equal(sp.reserved_usd, 1); assert.equal(sp.active_runs, 1);
  } finally {
    env.SETTINGS.m.set('monthly_budget_usd', '');
    monthRuns = [];
  }
});

test('dispatch failure: Marathi reason + finished_at on the run, raw GitHub text only in activity', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  patches.length = 0; acts.length = 0; activeRuns = [];
  dispatchFail = true;
  try {
    const r = await call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7 }) });
    assert.equal(r.status, 502);
    const j = await r.json();
    assert.equal(j.error, 'dispatch_failed'); assert.match(j.reason, /प्रक्रिया सुरू होऊ शकली नाही/); assert.match(j.detail, /GitHub token/);
    assert.ok(!JSON.stringify(j).includes('Bad credentials'), 'raw text not sent to the browser');
    const pt = patches.find(x => x.u.includes('runs?id=eq.55') && x.body.state === 'failed');
    assert.ok(pt, 'run marked failed');
    assert.equal(pt.body.step, "प्रक्रिया सुरू होऊ शकली नाही (तांत्रिक कारण). कृपया 'पुन्हा तयार करा' वापरावे; अडचण राहिल्यास मालकांना कळवावे.");
    assert.ok(pt.body.finished_at, 'finished_at set');
    const a = acts.find(x => x.action === 'run_failed');
    assert.equal(a.detail.reason, pt.body.step); assert.match(a.detail.error, /dispatch 401: .*Bad credentials/);
  } finally { dispatchFail = false; }
});

test('PATCH /api/cases/:id: C R / वर्ष editable with the create rules and duplicate check', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const edit = (id, b, h = owner) => call(`/api/cases/${id}`, { method: 'PATCH', headers: h, body: JSON.stringify(b) });
  assert.equal((await edit(43, { cr_no: '12a', cr_year: 2026 })).status, 400);
  assert.deepEqual(await (await edit(43, { cr_no: '12', cr_year: 26 })).json(), { error: 'cr_year: 4 digits' });
  let r = await edit(43, { cr_no: '0021', cr_year: '2026' });
  assert.equal(r.status, 409, 'leading zeros ignored');
  assert.deepEqual(await r.json(), { error: 'duplicate_cr', existing_id: 40 });
  assert.equal(caseRows[43].cr_no, null, 'nothing saved on a duplicate');
  acts.length = 0;
  r = await edit(43, { cr_no: '131', cr_year: '2026', subject: 'नवीन', office: '' });
  assert.equal(r.status, 200, await r.clone().text());
  const c = await r.json();
  assert.equal(c.cr_no, '131'); assert.equal(c.cr_year, 2026); assert.equal(c.office, null, "'' stored as null");
  assert.equal(acts.at(-1).action, 'case_updated'); assert.equal(acts.at(-1).detail.cr, '131/2026');
  // the case is not its own duplicate (case 40 = 21/2026 re-saved with another field)
  cases.push({ id: 43, cr_no: '131', cr_year: 2026 });
  assert.equal((await edit(40, { cr_no: '21', cr_year: 2026, post: 'लिपिक' })).status, 200);
  assert.equal((await edit(43, { cr_no: '131', cr_year: 2026, file_no: 'x' })).status, 200);
  assert.equal((await edit(99, { file_no: 'x' })).status, 404);
  assert.equal((await edit(43, { file_no: 'x' }, { authorization: 'Bearer stranger-jwt' })).status, 403);
  assert.equal((await edit(43, {})).status, 400);
});

test('members: invite, and an e-mail that already has an auth account (422) is added via the admin API', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const inv = b => call('/api/members', { method: 'POST', headers: owner, body: JSON.stringify(b) });
  let r = await inv({ email: 'new@example.com', role: 'staff' });
  assert.equal(r.status, 200); assert.deepEqual(await r.json(), { ok: true, existing: false });
  assert.ok(members.some(x => x.email === 'new@example.com' && x.role === 'staff'));
  r = await inv({ email: 'staff.old@example.com', role: 'senior' });
  assert.equal(r.status, 200, await r.clone().text());
  assert.deepEqual(await r.json(), { ok: true, existing: true });
  const m = members.find(x => x.email === 'staff.old@example.com');
  assert.equal(m.user_id, 'au-old'); assert.equal(m.role, 'senior');
  assert.equal((await inv({ email: 'x', role: 'admin' })).status, 400);
});

test('settings: "__clear__" deletes a secret key; Supabase service key and plain keys cannot be cleared that way', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const put = b => call('/api/settings', { method: 'PUT', headers: owner, body: JSON.stringify(b) });
  env.SETTINGS.m.set('gemini_api_key', 'AIza-old-key');
  assert.equal((await put({ gemini_api_key: '__clear__' })).status, 200);
  assert.equal(env.SETTINGS.m.has('gemini_api_key'), false);
  assert.equal((await body(await call('/api/settings', { headers: owner }))).gemini_api_key, '');
  let r = await put({ supabase_service_key: '__clear__' });
  assert.equal(r.status, 400); assert.deepEqual(await r.json(), { error: 'supabase_service_key: cannot clear' });
  assert.equal(env.SETTINGS.m.get('supabase_service_key'), 'service-secret-1234');
  assert.equal((await put({ model: '__clear__' })).status, 400);
});

test('upload: Storage size limit → 413 "file over 50 MB"', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  storageTooBig = true;
  try {
    const r = await call('/api/upload?case_id=7&kind=extra_doc', { method: 'POST', headers: { ...owner, 'x-file-name': 'a.pdf' }, body: 'x' });
    assert.equal(r.status, 413); assert.deepEqual(await r.json(), { error: 'file over 50 MB' });
  } finally { storageTooBig = false; }
});

test('HTML responses carry CSP with frame-ancestors self; नस्ती page keeps its inline/eval scripts; non-HTML untouched', async () => {
  const r = await call('/cases/7');
  assert.equal(await r.text(), HTML, 'body unchanged');
  const csp = r.headers.get('content-security-policy');
  assert.match(csp, /frame-ancestors 'self'/); assert.equal(r.headers.get('x-frame-options'), 'SAMEORIGIN');
  const { createHash } = await import('node:crypto');
  const h = createHash('sha256').update('var t = 1;').digest('base64');
  assert.ok(csp.includes(`script-src 'self' 'sha256-${h}'`), csp);
  assert.ok(!/script-src[^;]*unsafe/.test(csp), 'no unsafe-inline / eval for the app');
  assert.ok(csp.includes(`connect-src 'self' ${SB} wss://sb.example`), csp);
  assert.match(csp, /frame-src 'self'/);
  const n = await call('/nasti/');
  const ncsp = n.headers.get('content-security-policy');
  assert.match(ncsp, /script-src 'self' 'unsafe-inline' 'unsafe-eval'/); assert.match(ncsp, /frame-ancestors 'self'/);
  assert.equal((await call('/assets/a.js')).headers.get('content-security-policy'), null);
});

test('C28: /api/run outputs — validated, deduped, fixed order; 400 Marathi; missing column → insert without it', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  monthRuns = []; activeRuns = [];
  const run = b => call('/api/run', { method: 'POST', headers: owner, body: JSON.stringify({ case_id: 7, ...b }) });
  runInserts.length = 0;
  let r = await run({ outputs: ['parawise', 'gr', 'letter', 'gr'] });
  assert.equal(r.status, 200, await r.clone().text());
  assert.deepEqual(runInserts.at(-1).outputs, ['letter', 'gr', 'parawise'], 'dedupe + fixed order');
  assert.deepEqual((await r.json()).outputs, ['letter', 'gr', 'parawise']);
  // 04.11.2026: eight more keys, appended after the old ones in the fixed order
  r = await run({ outputs: ['lq', 'affidavit', 'addendum', 'press_note', 'office_order', 'endorsement', 'uo_note', 'do_letter', 'letter'] });
  assert.equal(r.status, 200, await r.clone().text());
  assert.deepEqual(runInserts.at(-1).outputs,
    ['letter', 'do_letter', 'uo_note', 'endorsement', 'office_order', 'press_note', 'addendum', 'affidavit', 'lq'], 'new keys accepted, fixed order');
  r = await run({ outputs: [] });
  assert.deepEqual(runInserts.at(-1).outputs, [], 'empty = note only');
  await run({});
  assert.ok(!('outputs' in runInserts.at(-1)), 'missing field → legacy run (no outputs column written)');
  await run({ outputs: null });
  assert.ok(!('outputs' in runInserts.at(-1)), 'null → legacy');
  const n = runInserts.length;
  for (const bad of [['letter', 'x'], 'letter', [1], { a: 1 }, ['LETTER']]) {
    r = await run({ outputs: bad });
    assert.equal(r.status, 400, JSON.stringify(bad));
    assert.deepEqual(await r.json(), { error: 'मसुद्यांची निवड योग्य नाही. कृपया पान पुन्हा उघडून निवड करावी, ही विनंती.' });
  }
  assert.equal(runInserts.length, n, 'nothing inserted for a bad selection');
  // migration 0008 not applied: the run still starts, without outputs, and the activity log says so
  outputsColumn = false; acts.length = 0;
  try {
    const before = calls.filter(c => c.u.endsWith('/dispatches')).length;
    r = await run({ outputs: ['letter'] });
    assert.equal(r.status, 200, await r.clone().text());
    assert.equal(runInserts.length, n + 2, 'first insert refused, second without the column');
    assert.ok(!('outputs' in runInserts.at(-1)));
    assert.equal(calls.filter(c => c.u.endsWith('/dispatches')).length, before + 1, 'dispatched');
    const a = acts.find(x => x.action === 'run_started');
    assert.equal(a.detail.outputs_dropped, true);
  } finally { outputsColumn = true; }
});

test('C28: upload accepts the kinds approval and court_notice; unknown kind refused', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const up = kind => call(`/api/upload?case_id=7&kind=${kind}`, { method: 'POST', headers: { ...owner, 'x-file-name': encodeURIComponent('मान्यता.pdf'), 'content-type': 'application/pdf' }, body: 'x' });
  for (const k of ['approval', 'court_notice']) {
    const r = await up(k); const j = await r.json();
    assert.equal(r.status, 200, JSON.stringify(j)); assert.equal(j.kind, k);
    assert.equal(j.version, k === 'approval' ? 2 : 1, 'version counted per kind');
    assert.match(j.storage_path, new RegExp(`^proposals/7/${k}/v`));
    assert.equal(j.letter_updated, null, 'only a reply touches letters');
  }
  assert.equal((await up('study')).status, 400, 'output kinds cannot be uploaded');
  kindEnum08 = false;
  try {
    const r = await up('court_notice');
    assert.equal(r.status, 409);
    { const j = await r.json(); assert.match(j.error, /"इतर" हा प्रकार निवडावा/); assert.match(j.detail, /migration 0008/); }
    assert.equal((await up('extra_doc')).status, 200, 'old kinds unaffected');
  } finally { kindEnum08 = true; }
  assert.equal((await up('foo')).status, 400);
});

test('C30: case desk — create/PATCH accept the profile ids only (400 Marathi); missing column → saved without it', async () => {
  const owner = { authorization: 'Bearer owner-jwt' };
  const create = b => call('/api/cases', { method: 'POST', headers: owner, body: JSON.stringify(b) });
  const edit = (id, b) => call(`/api/cases/${id}`, { method: 'PATCH', headers: owner, body: JSON.stringify(b) });
  let r = await create({ subject: 'उ.व तं.शि.वि. प्रस्ताव', desk: 'hte-mashi5' });
  assert.equal(r.status, 200, await r.clone().text());
  assert.equal((await r.json()).desk, 'hte-mashi5');
  r = await create({ subject: 'x', desk: '' });
  assert.ok(!('desk' in caseInserts.at(-1)), "'' = not sent (null = law-desk6)");
  const n = caseInserts.length;
  for (const d of ['law-desk7', 'LAW-DESK6', 5, ['law-desk6']]) {
    r = await create({ subject: 'x', desk: d });
    assert.equal(r.status, 400, JSON.stringify(d));
    assert.deepEqual(await r.json(), { error: 'विभाग / कार्यासन योग्य नाही. कृपया यादीतील पर्याय निवडावा, ही विनंती.' });
    r = await edit(43, { desk: d });
    assert.equal(r.status, 400, JSON.stringify(d));
  }
  assert.equal(caseInserts.length, n, 'nothing inserted for a bad desk');
  r = await edit(43, { desk: 'hte-mashi5' });
  assert.equal(r.status, 200); assert.equal(caseRows[43].desk, 'hte-mashi5');
  r = await edit(43, { desk: '' });
  assert.equal(r.status, 200); assert.equal(caseRows[43].desk, null, "'' clears to the default desk");
  // migration 0009 not applied: never fail — the case is saved without desk
  deskColumn = false;
  try {
    r = await create({ subject: 'y', desk: 'law-desk6' });
    assert.equal(r.status, 200, await r.clone().text());
    assert.ok(!('desk' in caseInserts.at(-1)), 'retried without desk');
    assert.equal(caseInserts.at(-1).subject, 'y');
    r = await edit(43, { post: 'लिपिक', desk: 'hte-mashi5' });
    assert.equal(r.status, 200, await r.clone().text());
    assert.equal(caseRows[43].post, 'लिपिक'); assert.equal(caseRows[43].desk, null);
    r = await edit(43, { desk: 'hte-mashi5' });
    assert.equal(r.status, 200, 'desk-only edit: the case row comes back unchanged');
    assert.equal((await r.json()).id, 43);
  } finally { deskColumn = true; }
});

// ---------- C33: work_type + sequential queue ----------
const owner33 = { authorization: 'Bearer owner-jwt' };
const dispatchBodies = () => calls.filter(c => c.u.endsWith('/dispatches')).map(c => JSON.parse(c.opt.body).client_payload);
const runCase = cid => call('/api/run', { method: 'POST', headers: owner33, body: JSON.stringify({ case_id: cid }) });
const tokenOf = runId => [...env.SETTINGS.m.entries()].filter(([k, v]) => k.startsWith('run_token:') && JSON.parse(v).run_id === String(runId)).map(([k]) => k.slice(10)).pop();

test('C33: case work_type — 4 ids only (400 Marathi); missing column → saved without it', async () => {
  const create = b => call('/api/cases', { method: 'POST', headers: owner33, body: JSON.stringify(b) });
  caseInserts.length = 0;
  for (const w of ['service', 'court', 'legislature', 'procurement']) assert.equal((await create({ subject: 'x', work_type: w })).status, 200, w);
  const r = await create({ subject: 'x', work_type: 'medical' });
  assert.equal(r.status, 400);
  assert.match((await r.json()).error, /कामाची श्रेणी/);
  const pr = await call('/api/cases/40', { method: 'PATCH', headers: owner33, body: JSON.stringify({ work_type: 'x' }) });
  assert.equal(pr.status, 400);
  assert.equal((await call('/api/cases/40', { method: 'PATCH', headers: owner33, body: JSON.stringify({ work_type: 'court' }) })).status, 200);
  assert.equal(caseRows[40].work_type, 'court');
  // column missing (migration 0011 not applied): the case is still saved, without work_type
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (u, opt = {}) => (String(u).startsWith(`${SB}/rest/v1/cases`) && ['POST', 'PATCH'].includes(opt.method) && 'work_type' in JSON.parse(opt.body)
    ? new Response(JSON.stringify({ code: 'PGRST204', message: "Could not find the 'work_type' column of 'cases' in the schema cache" }), { status: 400 })
    : realFetch(u, opt));
  try {
    caseInserts.length = 0;
    const ok = await create({ subject: 'y', work_type: 'court', desk: 'law-desk6' });
    assert.equal(ok.status, 200);
    assert.deepEqual(caseInserts.map(x => 'work_type' in x), [false], JSON.stringify(caseInserts));
    assert.equal(caseInserts[0].desk, 'law-desk6', 'other fields kept');
    assert.equal((await call('/api/cases/40', { method: 'PATCH', headers: owner33, body: JSON.stringify({ work_type: 'service' }) })).status, 200, 'PATCH of only work_type → row returned');
  } finally { globalThis.fetch = realFetch; }
});

test('C33: one run at a time across cases — immediate when idle, else queued with FIFO position', async () => {
  Q = { rows: [], nextId: 100 }; monthRuns = []; dispatchFail = false;
  try {
    const n0 = dispatchBodies().length;
    const a = await body(await runCase(101));
    assert.equal(a.queued, false); assert.ok(a.dispatched_at, 'dispatched_at set');
    assert.equal(dispatchBodies().length, n0 + 1);
    const b = await body(await runCase(102)), c = await body(await runCase(103));
    assert.deepEqual([b.queued, b.position, c.queued, c.position], [true, 1, true, 2]);
    assert.equal(dispatchBodies().length, n0 + 1, 'nothing more dispatched while one is active');
    assert.equal(Q.rows.find(r => r.id === b.id).dispatched_at, null);
    // one run per case stays: a queued run blocks its case
    const dup = await runCase(102);
    assert.equal(dup.status, 409); assert.equal((await dup.json()).run_id, b.id);
    assert.ok(acts.some(x => x.action === 'run_queued' && x.detail.position === 2));

    // engine/next with a wrong token → 403; with the run's token: the finished run → next in FIFO order
    assert.equal((await call('/api/engine/next', { method: 'POST', headers: { authorization: 'Bearer nope' }, body: JSON.stringify({ run_id: a.id }) })).status, 403);
    Q.rows.find(r => r.id === a.id).state = 'done';
    let nx = await body(await call('/api/engine/next', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(a.id)}` }, body: JSON.stringify({ run_id: a.id }) }));
    assert.deepEqual(nx, { ok: true, changed: 0, dispatched: b.id });
    assert.equal(dispatchBodies().at(-1).run_id, b.id);
    assert.ok(acts.some(x => x.action === 'run_started' && x.detail.run_id === b.id && x.detail.from_queue));
    // calling it again changes nothing (b is active)
    nx = await body(await call('/api/engine/next', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(a.id)}` }, body: JSON.stringify({ run_id: a.id }) }));
    assert.equal(nx.dispatched, null);
    // b's job ends while its run is still "running" (no finish, no fail): marked failed, then c goes
    Q.rows.find(r => r.id === b.id).state = 'running';
    nx = await body(await call('/api/engine/next', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(b.id)}` }, body: JSON.stringify({ run_id: b.id }) }));
    assert.deepEqual(nx, { ok: true, changed: 1, dispatched: c.id });
    assert.equal(Q.rows.find(r => r.id === b.id).state, 'failed');
    // engine/fail also moves the queue
    const d = await body(await runCase(104));
    assert.equal(d.position, 1);
    const f = await body(await call('/api/engine/fail', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(c.id)}` }, body: JSON.stringify({ run_id: c.id, reason: 'x' }) }));
    assert.deepEqual(f, { ok: true, changed: 1, dispatched: d.id });
  } finally { Q = null; }
});

test('C33: race-safe — parallel /api/run calls dispatch exactly one; claim race never dispatches two', async () => {
  Q = { rows: [], nextId: 200 }; monthRuns = []; dispatchFail = false;
  try {
    const n0 = dispatchBodies().length;
    const rs = await Promise.all([201, 202, 203, 204, 205].map(cid => runCase(cid).then(body)));
    assert.equal(dispatchBodies().length, n0 + 1, 'exactly one dispatch');
    assert.equal(rs.filter(r => r.queued === false).length, 1);
    const active = Q.rows.filter(r => r.dispatched_at);
    assert.equal(active.length, 1);
    assert.equal(active[0].id, 200, 'the oldest run goes first');
    // concurrent dispatchNext callers (sweep + engine/next + cron) after the active one ended → still one dispatch
    active[0].state = 'done';
    await Promise.all([
      call('/api/runs/sweep', { method: 'POST', headers: owner33 }),
      call('/api/engine/next', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(200)}` }, body: JSON.stringify({ run_id: 200 }) }),
      worker.scheduled({}, env, null),
    ]);
    assert.equal(dispatchBodies().length, n0 + 2, 'exactly one more dispatch');
    assert.equal(dispatchBodies().at(-1).run_id, 201, 'FIFO');
    // forced interleaving: two claimers both pass the first check, both claim → both see each other → both give
    // back; nothing dispatched twice, the cron dispatches later
    Q.rows.find(r => r.id === 201).state = 'done';
    let gate = 0, release;
    const both = new Promise(r => { release = r; });
    Q.hook = async (d, M) => { if (M === 'GET' && d.includes('runs?state=eq.queued&dispatched_at=is.null')) { gate++; if (gate === 2) release(); await both; } };
    const n1 = dispatchBodies().length;
    // both callers hold at the waiting-list read until the other has reached it too
    await Promise.all([call('/api/runs/sweep', { method: 'POST', headers: owner33 }), worker.scheduled({}, env, null)]);
    Q.hook = null;
    const dispatchedNow = dispatchBodies().length - n1;
    assert.ok(dispatchedNow <= 1, 'never two at once');
    assert.ok(Q.rows.filter(r => ['queued', 'running'].includes(r.state) && r.dispatched_at).length <= 1);
    if (dispatchedNow === 0) {
      await worker.scheduled({}, env, null);
      assert.equal(dispatchBodies().length, n1 + 1, 'cron dispatches after a give-back');
    }
    assert.equal(dispatchBodies().at(-1).run_id, 202);
  } finally { Q = null; }
});

test('C33: both claimers see each other → both give back, cron dispatches one', async () => {
  Q = { rows: [], nextId: 300 }; monthRuns = []; dispatchFail = false;
  try {
    const t0 = Date.now() - 1000;
    Q.rows.push({ id: 301, case_id: 31, state: 'queued', dispatched_at: null, created_at: new Date(t0).toISOString() },
                { id: 302, case_id: 32, state: 'queued', dispatched_at: null, created_at: new Date(t0 + 1).toISOString() });
    // simulate a second Worker that claimed 302 between our check and our verify
    Q.hook = async (d, M) => {
      if (M === 'PATCH' && d.endsWith('id=eq.301&state=eq.queued&dispatched_at=is.null')) Q.rows[1].dispatched_at = isoNow();
    };
    const n0 = dispatchBodies().length;
    await worker.scheduled({}, env, null);
    Q.hook = null;
    assert.equal(dispatchBodies().length, n0, 'no dispatch when another claim is seen');
    assert.equal(Q.rows[0].dispatched_at, null, 'claim given back');
    Q.rows[1].dispatched_at = null;   // the other one gave back too
    await worker.scheduled({}, env, null);
    assert.equal(dispatchBodies().length, n0 + 1);
    assert.equal(dispatchBodies().at(-1).run_id, 301);
  } finally { Q = null; }
});

test('C33: GitHub dispatch failure → that run failed (Marathi), the next one is tried; own run → 502', async () => {
  Q = { rows: [], nextId: 400 }; monthRuns = []; acts.length = 0;
  try {
    dispatchFail = true;
    const r = await runCase(401);
    assert.equal(r.status, 502);
    assert.equal((await r.json()).reason, "प्रक्रिया सुरू होऊ शकली नाही (तांत्रिक कारण). कृपया 'पुन्हा तयार करा' वापरावे; अडचण राहिल्यास मालकांना कळवावे.");
    assert.equal(Q.rows[0].state, 'failed');
    assert.ok(acts.some(x => x.action === 'run_failed' && x.detail.run_id === 400 && /Bad credentials/.test(x.detail.error)));
    // two waiting runs, GitHub down: both failed, nothing left hanging
    const t0 = Date.now() - 1000;
    Q.rows.push({ id: 402, case_id: 42, state: 'queued', dispatched_at: null, created_at: new Date(t0).toISOString() },
                { id: 403, case_id: 43, state: 'queued', dispatched_at: null, created_at: new Date(t0 + 1).toISOString() });
    let calls402 = 0;
    const realFetch = globalThis.fetch;
    globalThis.fetch = async (u, opt = {}) => {
      if (String(u).endsWith('/dispatches') && calls402++ === 0) return new Response('{"message":"Bad credentials"}', { status: 401 });
      return realFetch(u, opt);
    };
    dispatchFail = false;
    try {
      const out = await cronTick(env);
      assert.deepEqual(out.failed, [402]);
      assert.equal(out.dispatched, 403);
    } finally { globalThis.fetch = realFetch; }
    assert.equal(Q.rows.find(x => x.id === 402).step, "प्रक्रिया सुरू होऊ शकली नाही (तांत्रिक कारण). कृपया 'पुन्हा तयार करा' वापरावे; अडचण राहिल्यास मालकांना कळवावे.");
  } finally { Q = null; dispatchFail = false; }
});

test('C33: sweep uses dispatch time; a long-waiting queued run is not swept; monthly limit keeps it queued', async () => {
  Q = { rows: [], nextId: 500 }; monthRuns = [];
  try {
    const old = new Date(Date.now() - 5 * 3600 * 1000).toISOString();
    Q.rows.push({ id: 501, case_id: 51, state: 'running', dispatched_at: old, created_at: old },
                { id: 502, case_id: 52, state: 'queued', dispatched_at: null, created_at: old });
    // limit reached at the moment of dispatch: 502 stays queued (not failed) with the Marathi wait text
    monthRuns = [{ cost_usd: 25, created_at: new Date().toISOString(), state: 'done' }];
    const n0 = dispatchBodies().length;
    const sw = await body(await call('/api/runs/sweep', { method: 'POST', headers: owner33 }));
    assert.deepEqual(sw, { ok: true, failed: [501], dispatched: null });
    assert.equal(Q.rows[1].state, 'queued');
    assert.equal(Q.rows[1].dispatched_at, null);
    assert.equal(Q.rows[1].step, 'मासिक खर्च-मर्यादा पूर्ण झाली आहे. मालकांनी सेटिंग्जमध्ये मर्यादा वाढवल्यावर प्रक्रिया आपोआप सुरू होईल.');
    await worker.scheduled({}, env, null);
    assert.equal(dispatchBodies().length, n0, 'cron retries, still blocked');
    // the owner raised the limit (here: the spend is gone) → the cron dispatches it
    monthRuns = [];
    await worker.scheduled({}, env, null);
    assert.equal(dispatchBodies().length, n0 + 1);
    assert.equal(dispatchBodies().at(-1).run_id, 502);
    // queue the run back to test the sweep path too
    Object.assign(Q.rows[1], { state: 'queued', dispatched_at: null });
    const sw2 = await body(await call('/api/runs/sweep', { method: 'POST', headers: owner33 }));
    assert.deepEqual(sw2, { ok: true, failed: [], dispatched: 502 });
  } finally { Q = null; monthRuns = []; }
});

test('C33: monthly limit — waiting runs are not reserved; the check runs at dispatch (immediate path too)', async () => {
  Q = { rows: [], nextId: 600 }; dispatchFail = false;
  try {
    const now = new Date().toISOString();
    // 5 runs waiting: none of them is reserved
    for (let i = 0; i < 5; i++) Q.rows.push({ id: 601 + i, case_id: 61 + i, state: 'queued', dispatched_at: null, created_at: now });
    monthRuns = [{ cost_usd: 2, created_at: now, state: 'done' }];
    let sp = await body(await call('/api/spend', { headers: owner33 }));
    assert.deepEqual([sp.active_runs, sp.reserved_usd], [0, 0]);
    // one dispatched: reserved at the estimate (median of finished = 2)
    Q.rows[0].dispatched_at = now;
    sp = await body(await call('/api/spend', { headers: owner33 }));
    assert.deepEqual([sp.active_runs, sp.reserved_usd], [1, 2]);
    Q.rows.length = 0;
    // immediate path: no active run, but spent + reserved reaches the limit only at dispatch time → stays queued
    monthRuns = [{ cost_usd: 19.5, created_at: now, state: 'done' }];
    const n0 = dispatchBodies().length;
    const r = await body(await runCase(670));   // 19.5 < 20 → accepted at /api/run
    assert.equal(dispatchBodies().length, n0 + 1, 'below the limit: dispatched at once');
    assert.equal(r.queued, false);
    Q.rows[0].state = 'done'; Q.rows[0].cost_usd = 1;   // spend now 20.5 ≥ 20
    const blockedRun = { id: 699, case_id: 69, state: 'queued', dispatched_at: null, created_at: now };
    Q.rows.push(blockedRun);
    const out = await cronTick(env);
    assert.equal(out.dispatched, null);
    assert.equal(blockedRun.state, 'queued');
    assert.match(blockedRun.step, /मासिक खर्च-मर्यादा पूर्ण झाली/);
    assert.equal(dispatchBodies().length, n0 + 1, 'nothing dispatched past the limit');
  } finally { Q = null; monthRuns = []; }
});

// ---------- migration 0012: member profile (PATCH /api/me), cases.nasti_no, नस्ती page CSP ----------
const ownerM = { authorization: 'Bearer owner-jwt' };
const patchMe = (b, h = ownerM) => call('/api/me', { method: 'PATCH', headers: h, body: JSON.stringify(b) });
const EMPTY_PROFILE = { display_name: '', designation: '', office: '', mine: '' };

test('0012: GET /api/me returns the profile; without the columns → role only, empty profile', async () => {
  const me = members.find(x => x.user_id === 'u1');
  Object.assign(me, { display_name: 'अभि', designation: null, office: null, mine: null });
  let u = await body(await call('/api/me', { headers: ownerM }));
  assert.deepEqual(u, { id: 'u1', email: 'abhi@example.com', role: 'owner', profile: { ...EMPTY_PROFILE, display_name: 'अभि' } });
  profileColumns = false;
  try {
    const r = await call('/api/me', { headers: ownerM });
    assert.equal(r.status, 200);
    u = await r.json();
    assert.deepEqual(u, { id: 'u1', email: 'abhi@example.com', role: 'owner', profile: EMPTY_PROFILE });
  } finally { profileColumns = true; me.display_name = null; }
});

test('0012: PATCH /api/me — trimmed own row, unknown keys ignored, too long 400, migration missing 409, non-member 403', async () => {
  memberPatches.length = 0;
  let r = await patchMe({ display_name: '  अभिषेक  ', designation: 'कार्यासन अधिकारी', office: 'विधि व न्याय विभाग', mine: 'कार्यासन-६, माझ्याकडे', role: 'staff', user_id: 'u9' });
  assert.equal(r.status, 200, await r.clone().text());
  assert.deepEqual(await r.json(), { id: 'u1', email: 'abhi@example.com', role: 'owner',
    profile: { display_name: 'अभिषेक', designation: 'कार्यासन अधिकारी', office: 'विधि व न्याय विभाग', mine: 'कार्यासन-६, माझ्याकडे' } });
  assert.equal(memberPatches.length, 1);
  assert.match(memberPatches[0].u, /members\?user_id=eq\.u1&/, 'own row only');
  assert.deepEqual(Object.keys(memberPatches[0].body).sort(), ['designation', 'display_name', 'mine', 'office'], 'role / user_id never written');
  assert.equal(members.find(x => x.user_id === 'u1').role, 'owner');
  // GET reflects it
  assert.equal((await body(await call('/api/me', { headers: ownerM }))).profile.display_name, 'अभिषेक');
  // '' / null clears
  r = await patchMe({ office: '', mine: null });
  assert.deepEqual((await r.json()).profile, { display_name: 'अभिषेक', designation: 'कार्यासन अधिकारी', office: '', mine: '' });
  assert.deepEqual(memberPatches.at(-1).body, { office: null, mine: null });
  // too long / wrong type / nothing → 400 Marathi, nothing written
  const n = memberPatches.length;
  r = await patchMe({ designation: 'प'.repeat(121) });
  assert.equal(r.status, 400); assert.match((await r.json()).error, /पदनाम: जास्तीत जास्त 120 अक्षरे/);
  assert.equal((await patchMe({ designation: '  ' + 'प'.repeat(120) + '  ' })).status, 200, '120 after trim is fine');
  r = await patchMe({ office: 5 });
  assert.equal(r.status, 400); assert.match((await r.json()).error, /कार्यालय/);
  r = await patchMe({ foo: 'x' });
  assert.equal(r.status, 400); assert.match((await r.json()).error, /बदलण्यासाठी माहिती नाही/);
  assert.equal(memberPatches.length, n + 1);
  // migration 0012 not applied
  profileColumns = false;
  try {
    r = await patchMe({ display_name: 'x' });
    assert.equal(r.status, 409);
    assert.deepEqual(await r.json(), { error: 'migration_missing', reason: 'माहिती जतन होऊ शकली नाही (तांत्रिक अडचण). कृपया मालकांना कळवावे, ही विनंती.', detail: 'Supabase मध्ये migration 0012 लागू करणे आवश्यक आहे.' });
  } finally { profileColumns = true; }
  // not a member / not signed in
  assert.equal((await patchMe({ display_name: 'x' }, { authorization: 'Bearer stranger-jwt' })).status, 403);
  assert.equal((await call('/api/me', { method: 'PATCH', body: '{}' })).status, 401);
  Object.assign(members.find(x => x.user_id === 'u1'), { display_name: null, designation: null, office: null, mine: null });
});

test('0012: case nasti_no — create / PATCH trimmed, cleared, too long 400 Marathi; missing column → saved without it', async () => {
  const create = b => call('/api/cases', { method: 'POST', headers: ownerM, body: JSON.stringify(b) });
  const edit = (id, b) => call(`/api/cases/${id}`, { method: 'PATCH', headers: ownerM, body: JSON.stringify(b) });
  caseInserts.length = 0;
  let r = await create({ subject: 'x', nasti_no: '  LNJD-DESK6/12/2026-E  ' });
  assert.equal(r.status, 200, await r.clone().text());
  assert.equal(caseInserts.at(-1).nasti_no, 'LNJD-DESK6/12/2026-E');
  r = await create({ subject: 'x', nasti_no: '   ' });
  assert.equal(r.status, 200); assert.ok(!('nasti_no' in caseInserts.at(-1)), 'blank = not sent');
  const n = caseInserts.length;
  for (const v of ['न'.repeat(101), 12, ['a']]) {
    r = await create({ subject: 'x', nasti_no: v });
    assert.equal(r.status, 400, JSON.stringify(v));
    assert.deepEqual(await r.json(), { error: 'नस्ती क्रमांक योग्य नाही. कृपया तो जास्तीत जास्त 100 अक्षरांत नमूद करावा, ही विनंती.' });
    assert.equal((await edit(43, { nasti_no: v })).status, 400);
  }
  assert.equal(caseInserts.length, n, 'nothing inserted for a bad nasti_no');
  assert.equal((await create({ subject: 'x', nasti_no: 'न'.repeat(100) })).status, 200, '100 is fine');
  r = await edit(43, { nasti_no: ' 1234567 ' });
  assert.equal(r.status, 200); assert.equal(caseRows[43].nasti_no, '1234567');
  r = await edit(43, { nasti_no: '' });
  assert.equal(r.status, 200); assert.equal(caseRows[43].nasti_no, null, "'' clears");
  r = await edit(43, { nasti_no: 'abc' });
  r = await edit(43, { nasti_no: null });
  assert.equal(r.status, 200); assert.equal(caseRows[43].nasti_no, null, 'null clears');
  // migration 0012 not applied: the case is still saved, without nasti_no
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (u, opt = {}) => (String(u).startsWith(`${SB}/rest/v1/cases`) && ['POST', 'PATCH'].includes(opt.method) && 'nasti_no' in JSON.parse(opt.body)
    ? new Response(JSON.stringify({ code: 'PGRST204', message: "Could not find the 'nasti_no' column of 'cases' in the schema cache" }), { status: 400 })
    : realFetch(u, opt));
  try {
    caseInserts.length = 0;
    r = await create({ subject: 'y', nasti_no: '42', desk: 'law-desk6' });
    assert.equal(r.status, 200);
    assert.deepEqual(caseInserts.map(x => 'nasti_no' in x), [false]);
    assert.equal(caseInserts[0].desk, 'law-desk6', 'other fields kept');
    r = await edit(43, { post: 'लिपिक', nasti_no: '42' });
    assert.equal(r.status, 200); assert.equal(caseRows[43].post, 'लिपिक'); assert.equal(caseRows[43].nasti_no, null);
    assert.equal((await edit(43, { nasti_no: '42' })).status, 200, 'PATCH of only nasti_no → row returned');
  } finally { globalThis.fetch = realFetch; }
});

test('0012: नस्ती page CSP — connect-src without self (data: blob: only); app CSP unchanged', async () => {
  for (const path of ['/nasti/', '/nasti/index.html']) {
    const ncsp = (await call(path)).headers.get('content-security-policy');
    const conn = ncsp.split('; ').find(d => d.startsWith('connect-src'));
    assert.equal(conn, 'connect-src data: blob:', ncsp);
    assert.match(ncsp, /script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:/);
    assert.match(ncsp, /worker-src 'self' blob:/); assert.match(ncsp, /frame-ancestors 'self'/);
    assert.match(ncsp, /default-src 'self' data: blob:/);
  }
  const csp = (await call('/cases/7')).headers.get('content-security-policy');
  assert.ok(csp.includes(`connect-src 'self' ${SB}`), csp);
});

// ---------- draft edit (docs/DRAFT_EDIT_DESIGN.md point 3 + Addendum A, migration 0013): POST /api/edit ----------
const editCall = (b, h = owner33) => call('/api/edit', { method: 'POST', headers: h, body: JSON.stringify(b) });
const dispatchEvents = () => calls.filter(c => c.u.endsWith('/dispatches')).map(c => JSON.parse(c.opt.body));
const NO_SPEC_TXT = "हे प्रकरण या सुविधेपूर्वीचे असल्याने सुधारणा-फाइल उपलब्ध नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.";

test('draft edit: /api/edit dispatches edit_drafts at once (dispatched_at), queue ignores edit runs, one run per case both ways', async () => {
  Q = { rows: [], nextId: 700 }; monthRuns = []; dispatchFail = false; acts.length = 0;
  [701, 702, 703].forEach(c => specCases.add(c));
  try {
    const n0 = dispatchEvents().length;
    let r = await editCall({ case_id: 701, target: 'note', message: '  परि. 3 मधील दुसरी ओळ काढा  ' });
    assert.equal(r.status, 200, await r.clone().text());
    const e = await r.json();
    assert.deepEqual([e.kind, e.edit_target, e.edit_message, e.state], ['edit', 'note', 'परि. 3 मधील दुसरी ओळ काढा', 'queued']);
    assert.deepEqual(e.edit_attachments, []);
    assert.ok(e.dispatched_at, 'dispatched_at set (never waits in the queue)');
    const ev = dispatchEvents();
    assert.equal(ev.length, n0 + 1);
    assert.equal(ev.at(-1).event_type, 'edit_drafts');
    assert.deepEqual(Object.keys(ev.at(-1).client_payload).sort(), ['case_id', 'run_id', 'token', 'worker'], 'same payload as process_proposal');
    assert.equal(ev.at(-1).client_payload.run_id, e.id);
    assert.ok(tokenOf(e.id), 'run token stored');
    assert.ok(acts.some(x => x.action === 'edit_requested' && x.detail.run_id === e.id && x.detail.target === 'note'));
    // the queue ignores the active edit run: a full run of another case is dispatched at once (process_proposal)
    const f = await body(await runCase(702));
    assert.equal(f.queued, false, 'edit run is not the queue\'s active run');
    assert.equal(dispatchEvents().at(-1).event_type, 'process_proposal');
    // a second full run waits behind the full one only (position 1)
    const g = await body(await runCase(705));
    assert.deepEqual([g.queued, g.position], [true, 1]);
    // one run per case, both ways
    r = await runCase(701);
    assert.equal(r.status, 409); assert.deepEqual(await r.json(), { error: 'run_active', run_id: e.id });
    r = await editCall({ case_id: 701, target: 'letter', message: 'x' });
    assert.equal(r.status, 409); assert.deepEqual(await r.json(), { error: 'run_active', run_id: e.id });
    r = await editCall({ case_id: 702, target: 'note', message: 'x' });
    assert.equal(r.status, 409); assert.deepEqual(await r.json(), { error: 'run_active', run_id: f.id });
    // a waiting (not yet dispatched) full run blocks an edit of its case too
    specCases.add(705);
    r = await editCall({ case_id: 705, target: 'note', message: 'x' });
    assert.equal(r.status, 409); assert.equal((await r.json()).run_id, g.id);
    // the edit run ends → nothing moves in the queue (the full run 702 is still active)
    const nx = await body(await call('/api/engine/next', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(e.id)}` }, body: JSON.stringify({ run_id: e.id }) }));
    assert.deepEqual(nx, { ok: true, changed: 1, dispatched: null });
    // /api/engine/step works for edit runs unchanged
    const e2 = await body(await editCall({ case_id: 703, target: 'package', message: 'हा GR जोडा' }));
    const st = await body(await call('/api/engine/step', { method: 'POST', headers: { authorization: `Bearer ${tokenOf(e2.id)}` }, body: JSON.stringify({ run_id: e2.id, step: 'सुधारणा करत आहे' }) }));
    assert.equal(st.changed, 1); assert.equal(Q.rows.find(x => x.id === e2.id).step, 'सुधारणा करत आहे');
    // engine config of an edit run: model_edit default, then the KV setting
    let ec = await body(await call(`/api/engine/config?run_id=${e2.id}`, { headers: { authorization: `Bearer ${tokenOf(e2.id)}` } }));
    assert.equal(ec.model_edit, 'claude-sonnet-5-5');
    assert.ok(ec.supabase_url && ec.supabase_service_key && ec.anthropic_api_key, 'edit job gets Supabase + Anthropic');
    assert.equal((await call('/api/settings', { method: 'PUT', headers: owner33, body: JSON.stringify({ model_edit: 'bad name!' }) })).status, 400);
    assert.equal((await call('/api/settings', { method: 'PUT', headers: owner33, body: JSON.stringify({ model_edit: 'claude-haiku-4-5' }) })).status, 200);
    assert.equal((await body(await call('/api/settings', { headers: owner33 }))).model_edit, 'claude-haiku-4-5');
    Q.rows.find(x => x.id === e2.id).state = 'done';
    const e3 = await body(await editCall({ case_id: 703, target: 'order', message: 'y' }));
    ec = await body(await call(`/api/engine/config?run_id=${e3.id}`, { headers: { authorization: `Bearer ${tokenOf(e3.id)}` } }));
    assert.equal(ec.model_edit, 'claude-haiku-4-5');
    env.SETTINGS.m.delete('model_edit');
  } finally { Q = null; }
});

test('draft edit: validation — target, message, attachments (this case, kinds, ≤ 5), no_spec, read-only, budget, dispatch failure', async () => {
  Q = { rows: [], nextId: 750 }; monthRuns = []; dispatchFail = false;
  specCases.add(751); specCases.add(752);
  fileRows.push({ id: 81, case_id: 751, kind: 'gr' }, { id: 82, case_id: 751, kind: 'study' }, { id: 83, case_id: 777, kind: 'gr' },
    { id: 84, case_id: 752, kind: 'extra_doc' }, { id: 85, case_id: 752, kind: 'gr' });
  const err = async (b, status, re) => { const r = await editCall(b); assert.equal(r.status, status, JSON.stringify(b)); const j = await r.json(); if (re) assert.match(j.error, re); return j; };
  try {
    await err({ case_id: 751, target: 'study', message: 'x' }, 400, /सुधारणा कोठे करावयाची/);
    await err({ case_id: 751, message: 'x' }, 400, /सुधारणा कोठे करावयाची/);
    await err({ case_id: 751, target: 'note', message: '   ' }, 400, /सुधारणा-संदेश नमूद करावा/);
    await err({ case_id: 751, target: 'note' }, 400, /सुधारणा-संदेश नमूद करावा/);
    await err({ case_id: 751, target: 'note', message: 'क'.repeat(2001) }, 400, /2000 अक्षरांच्या मर्यादेत/);
    await err({ case_id: 'x', target: 'note', message: 'x' }, 400);
    await err({ case_id: 751, target: 'note', message: 'x', attachments: [83] }, 400, /जोडलेल्या फाइल चुकीच्या/);   // other case
    await err({ case_id: 751, target: 'note', message: 'x', attachments: [82] }, 400, /जोडलेल्या फाइल चुकीच्या/);   // kind study
    await err({ case_id: 751, target: 'note', message: 'x', attachments: [81, 1, 2, 3, 4, 5] }, 400, /जास्तीत जास्त 5/);
    await err({ case_id: 751, target: 'note', message: 'x', attachments: ['x'] }, 400, /जोडलेल्या फाइल/);
    await err({ case_id: 751, target: 'note', message: 'x', attachments: 81 }, 400, /जोडलेल्या फाइल/);
    // no spec (old case) — also for the package target
    assert.deepEqual(await err({ case_id: 799, target: 'package', message: 'x' }, 409), { error: 'no_spec', reason: NO_SPEC_TXT });
    // read-only role
    const me = members.find(x => x.user_id === 'u1');
    me.role = 'senior';
    try { assert.equal((await editCall({ case_id: 751, target: 'note', message: 'x' })).status, 403); } finally { me.role = 'owner'; }
    // monthly limit → as /api/run
    monthRuns = [{ cost_usd: 25, created_at: new Date().toISOString(), state: 'done' }];
    assert.equal((await err({ case_id: 751, target: 'note', message: 'x' }, 402)).error, 'monthly_budget_reached');
    monthRuns = [];
    // ok: 2000 characters after trim, attachments deduplicated in order
    const r = await editCall({ case_id: 752, target: 'package', message: '  ' + 'क'.repeat(2000) + ' ', attachments: [84, '85', 84] });
    assert.equal(r.status, 200, await r.clone().text());
    const e = await r.json();
    assert.deepEqual(e.edit_attachments, [84, 85]); assert.equal(e.edit_message.length, 2000); assert.equal(e.edit_target, 'package');
    // GitHub dispatch failure → the edit run failed (Marathi), 502
    Q.rows.find(x => x.id === e.id).state = 'done';
    dispatchFail = true;
    const f = await editCall({ case_id: 751, target: 'note', message: 'x', attachments: [81] });
    assert.equal(f.status, 502);
    const fj = await f.json();
    assert.equal(fj.error, 'dispatch_failed');
    assert.equal(Q.rows.find(x => x.id === fj.run_id).state, 'failed');
    assert.ok(acts.some(x => x.action === 'edit_failed' && x.detail.run_id === fj.run_id));
  } finally { Q = null; dispatchFail = false; monthRuns = []; }
});

test('draft edit: migration 0013 missing → 409 migration_missing; the queue still works without runs.kind; edit sweep at 30 min', async () => {
  Q = { rows: [], nextId: 800 }; monthRuns = []; dispatchFail = false;
  specCases.add(801);
  try {
    editColumns = false;
    let r = await editCall({ case_id: 801, target: 'note', message: 'x' });
    assert.equal(r.status, 409);
    assert.deepEqual(await r.json(), { error: 'migration_missing', reason: 'सुधारणा-सुविधा सध्या उपलब्ध नाही (तांत्रिक अडचण). कृपया मालकांना कळवावे, ही विनंती.', detail: 'Supabase मध्ये migration 0013 लागू करणे आवश्यक आहे.' });
    const a = await body(await runCase(802));
    assert.equal(a.queued, false, 'queue without runs.kind: filter dropped');
    const b = await body(await runCase(803));
    assert.deepEqual([b.queued, b.position], [true, 1]);
    const sw = await body(await call('/api/runs/sweep', { method: 'POST', headers: owner33 }));
    assert.deepEqual(sw.failed, [], 'sweep without runs.kind');
    editColumns = true;
    Q.rows.length = 0;
    // stale edit run (31 min) → failed with its own reason; a 31-min full run and a 10-min edit run are not swept
    const t31 = new Date(Date.now() - 31 * 60 * 1000).toISOString(), t10 = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    Q.rows.push({ id: 811, case_id: 81, kind: 'edit', state: 'running', dispatched_at: t31, created_at: t31 },
                { id: 812, case_id: 82, kind: 'full', state: 'running', dispatched_at: t31, created_at: t31 },
                { id: 813, case_id: 83, kind: 'edit', state: 'running', dispatched_at: t10, created_at: t10 });
    const sw2 = await body(await call('/api/runs/sweep', { method: 'POST', headers: owner33 }));
    assert.deepEqual(sw2.failed, [811]);
    assert.equal(Q.rows[0].state, 'failed'); assert.equal(Q.rows[0].step, 'वेळ संपली — कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.');
    assert.deepEqual([Q.rows[1].state, Q.rows[2].state], ['running', 'running']);
    assert.ok(acts.some(x => Array.isArray(x) && x.some(y => y.action === 'edit_failed' && y.detail.run_id === 811)), 'activity edit_failed');
    // without the queue column (migration 0011): the edit row is inserted without dispatched_at, dispatched at once
    Q = null;
    specCases.add(7);
    r = await editCall({ case_id: 7, target: 'letter', message: 'x' });
    assert.equal(r.status, 200, await r.clone().text());
    assert.equal(dispatchEvents().at(-1).event_type, 'edit_drafts');
    assert.ok(!('dispatched_at' in runInserts.at(-1)), 'row without dispatched_at');
    assert.equal(runInserts.at(-1).kind, 'edit');
  } finally { Q = null; editColumns = true; }
});

test('draft edit: upload accepts kind gr (chat attachment)', async () => {
  const r = await call('/api/upload?case_id=7&kind=gr', { method: 'POST', headers: { ...owner33, 'x-file-name': encodeURIComponent('202605051234567812.pdf'), 'content-type': 'application/pdf' }, body: '%PDF-1' });
  assert.equal(r.status, 200, await r.clone().text());
  assert.equal((await r.json()).kind, 'gr');
});
