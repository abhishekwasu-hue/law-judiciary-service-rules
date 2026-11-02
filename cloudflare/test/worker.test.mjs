// node --test cloudflare/test/worker.test.mjs — Worker flows with an in-memory KV and a mocked Supabase/GitHub.
import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker.js';

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
let configColumn = true;          // false = migration 0005 not applied (PostgREST 42703)
let membersInsert = 'ok';         // 'conflict' = a parallel first request already inserted (409 23505)
const cases = [{ id: 40, cr_no: '21', cr_year: 2026 }];
let caseInsertRace = false;       // true = unique violation on insert although the pre-check found nothing
let searchItems = [];
const searchUrls = [];
const letterRows = { 31: { id: 31, case_id: 7 }, 32: { id: 32, case_id: 7 }, 33: { id: 33, case_id: 7 } };
globalThis.fetch = async (u, opt = {}) => {
  u = String(u); calls.push({ u, opt });
  const res = (o, s = 200) => new Response(JSON.stringify(o), { status: s });
  if (u === `${SB}/auth/v1/user`) {
    const t = opt.headers.Authorization;
    if (t === 'Bearer owner-jwt') return res({ id: 'u1', email: 'abhi@example.com', email_confirmed_at: '2026-11-01T10:00:00Z' });
    if (t === 'Bearer unconfirmed-jwt') return res({ id: 'u2', email: 'Abhi@example.com' });
    if (t === 'Bearer owner2-jwt') return res({ id: 'u3', email: 'abhi@example.com', confirmed_at: '2026-11-01T10:00:00Z' });
    if (t === 'Bearer stranger-jwt') return res({ id: 'u9', email: 'x@example.com' });
    return res({}, 401);
  }
  if (u.startsWith(`${SB}/rest/v1/members?user_id=eq.`)) return res(members.filter(x => u.includes(x.user_id)).map(x => ({ role: x.role })));
  if (u === `${SB}/rest/v1/members`) {
    const row = JSON.parse(opt.body);
    if (membersInsert === 'conflict') { members.push(row); return res({ code: '23505', message: 'duplicate key value violates unique constraint "members_pkey"' }, 409); }
    if (members.some(x => x.user_id === row.user_id) && /ignore-duplicates/.test(opt.headers.Prefer)) return res([], 201);
    members.push(row); return res([row], 201);
  }
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.proposal`)) return res([{ id: 1 }]);
  if (u === `${SB}/rest/v1/runs`) return res([{ id: 55, case_id: 7 }], 201);
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
  if (u.startsWith(`${SB}/rest/v1/case_files?id=eq.1&`)) return res([{ storage_path: 'outputs/7/study/v1/a.docx', original_name: 'a.docx' }]);
  if (u.startsWith(`${SB}/rest/v1/case_files?id=eq.2&`)) return res([{ storage_path: 'backups/7/x', original_name: 'x' }]);
  if (u === `${SB}/rest/v1/case_files` && opt.method === 'POST') return res([{ id: 9, ...JSON.parse(opt.body) }], 201);
  if (u.startsWith(`${SB}/storage/v1/object/sign/`)) return res({ signedURL: '/object/sign/x?token=t' });
  if (u.startsWith(`${SB}/storage/v1/object/`)) { uploads.push(u); return res({ Key: 'k' }); }
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
    return res(cases.filter(c => re.test(c.cr_no) && c.cr_year === y).map(c => ({ id: c.id })));
  }
  if (u === `${SB}/rest/v1/cases` && opt.method === 'POST') {
    const row = JSON.parse(opt.body);
    if (caseInsertRace) { cases.push({ id: 41, cr_no: row.cr_no, cr_year: Number(row.cr_year) }); return res({ code: '23505', message: 'duplicate key value violates unique constraint "cases_cr_no_cr_year_key"' }, 409); }
    return res([{ id: 42, ...row }], 201);
  }
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.999`) && opt.method === 'PATCH') return res({ code: '22P02', message: 'invalid input syntax for type bigint: "secret detail"' }, 400);
  if (u.startsWith('https://api.github.com/search/code?')) { searchUrls.push(u); return res({ items: searchItems }); }
  if (u.startsWith(`${SB}/rest/v1/`)) return new Response(null, { status: 204 });
  if (u.endsWith('/dispatches')) return new Response(null, { status: 204 });
  throw new Error('unexpected fetch ' + u);
};
const env = { SETTINGS: kv(), ASSETS: { fetch: async () => new Response('app') } };
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
  assert.equal(p.body.step, 'वेळ संपली — पुन्हा तयार करा');
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
    assert.deepEqual(s, { month: '2026-11', spent_usd: 1.75, limit_usd: 20, runs: 3 }, 'empty setting = default $20');
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
    // /api/spend keeps its shape
    assert.deepEqual(Object.keys(await body(await call('/api/spend', { headers: owner }))), ['month', 'spent_usd', 'limit_usd', 'runs']);
  } finally {
    env.SETTINGS.m.set('monthly_budget_usd', '');
    monthRuns = [];
  }
});
