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
globalThis.fetch = async (u, opt = {}) => {
  u = String(u); calls.push({ u, opt });
  const res = (o, s = 200) => new Response(JSON.stringify(o), { status: s });
  if (u === `${SB}/auth/v1/user`) {
    const t = opt.headers.Authorization;
    if (t === 'Bearer owner-jwt') return res({ id: 'u1', email: 'abhi@example.com' });
    if (t === 'Bearer stranger-jwt') return res({ id: 'u9', email: 'x@example.com' });
    return res({}, 401);
  }
  if (u.startsWith(`${SB}/rest/v1/members?user_id=eq.`)) return res(members.filter(x => u.includes(x.user_id)).map(x => ({ role: x.role })));
  if (u === `${SB}/rest/v1/members`) { members.push(JSON.parse(opt.body)); return res([JSON.parse(opt.body)], 201); }
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.proposal`)) return res([{ id: 1 }]);
  if (u === `${SB}/rest/v1/runs`) return res([{ id: 55, case_id: 7 }], 201);
  if (u.startsWith(`${SB}/rest/v1/runs?`) && opt.method === 'PATCH') {
    patches.push({ u, body: JSON.parse(opt.body) });
    if (u.includes('id=eq.55&state=in.(queued,running)')) return res(run55.state === 'failed' ? [] : (run55.state = 'failed', [{ id: 55, case_id: 7 }]));
    if (u.includes('created_at=lt.') && u.includes('state=in.(queued,running)')) return res([{ id: 60, case_id: 7 }, { id: 61, case_id: 8 }]);
    return res([]);
  }
  if (u === `${SB}/rest/v1/activity` && opt.method === 'POST') { acts.push(JSON.parse(opt.body)); return new Response(null, { status: 201 }); }
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.7&select=id`)) return res([{ id: 7 }]);
  if (u.startsWith(`${SB}/rest/v1/cases?id=eq.8&select=id`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?case_id=eq.7&kind=eq.extra_doc`)) return res([]);
  if (u.startsWith(`${SB}/rest/v1/case_files?id=eq.1&`)) return res([{ storage_path: 'outputs/7/study/v1/a.docx', original_name: 'a.docx' }]);
  if (u.startsWith(`${SB}/rest/v1/case_files?id=eq.2&`)) return res([{ storage_path: 'backups/7/x', original_name: 'x' }]);
  if (u === `${SB}/rest/v1/case_files` && opt.method === 'POST') return res([{ id: 9, ...JSON.parse(opt.body) }], 201);
  if (u.startsWith(`${SB}/storage/v1/object/sign/`)) return res({ signedURL: '/object/sign/x?token=t' });
  if (u.startsWith(`${SB}/storage/v1/object/`)) { uploads.push(u); return res({ Key: 'k' }); }
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
