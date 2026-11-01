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
  const ec = await body(await cfg(payload.token));
  assert.equal(ec.anthropic_api_key, 'sk-ant-secret-wxyz'); assert.equal(ec.supabase_service_key, 'service-secret-1234');
  assert.equal((await call(`/api/engine/config?run_id=56`, { headers: { authorization: `Bearer ${payload.token}` } })).status, 403, 'token bound to its run');
});
