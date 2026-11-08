// Self-test of the artifact data layer against an in-memory fake of window.claude (db, assets, downloads, mcp, user).
// Run from dashboard-app/:  node src/lib/artifact/selftest.mjs
// It bundles a small entry with esbuild (a vite dependency) — VITE_BACKEND=artifact — and checks the call shapes the
// app uses. Exit code 0 = all passed.
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import assert from 'node:assert/strict';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(mkdtempSync(join(tmpdir(), 'artifact-selftest-')), 'bundle.mjs');
const entry = `
export { sb } from ${JSON.stringify(join(here, '../supabase.ts'))};
export { api, uploadFile, fileBytes, fileUrl, downloadFile, ApiError, humanError } from ${JSON.stringify(join(here, '../api.ts'))};
export { searchDocs, fireFailText, artifactSaveFile } from ${JSON.stringify(join(here, 'api.ts'))};
`;
await build({
  stdin: { contents: entry, resolveDir: here, loader: 'ts' },
  bundle: true, format: 'esm', platform: 'node', outfile: out, logLevel: 'error',
  define: { 'import.meta.env.VITE_BACKEND': '"artifact"', 'import.meta.env.PROD': 'false', 'import.meta.env.DEV': 'true' },
});

// ---------- fake runtime ----------
const store = new Map();             // path -> body
const listeners = new Map();         // collection -> Set<fn>
const leases = new Map();
const writes = [];                   // paths written through the db capability (set / update / delete)
const acquires = [];                 // paths leased
const queries = [];                  // {coll, wheres, order, lim, how: 'get' | 'snap'}
let dbFail = null;                   // (op, path) => rejection object | null
let acquireThrows = 0;
const clone = v => JSON.parse(JSON.stringify(v));
const snapOf = (path, body) => ({ id: path.split('/').pop(), exists: body !== undefined, data: () => (body === undefined ? undefined : Object.freeze(clone(body))) });
const collOf = path => path.split('/').slice(0, -1).join('/');
function notify(coll) { for (const fn of listeners.get(coll) || []) fn(); }
const failIf = async (op, path) => { const f = dbFail && dbFail(op, path); if (f) throw f; };
function docRef(path) {
  return {
    id: path.split('/').pop(), path,
    get: async () => { await failIf('get', path); return snapOf(path, store.get(path)); },
    set: async d => { await failIf('set', path); writes.push(path); store.set(path, clone(d)); notify(collOf(path)); },
    update: async d => { await failIf('update', path); if (!store.has(path)) throw { code: 'invalid_argument' }; writes.push(path); store.set(path, { ...store.get(path), ...clone(d) }); notify(collOf(path)); },
    delete: async () => { await failIf('delete', path); writes.push(path); store.delete(path); notify(collOf(path)); },
    acquire: async ({ holder, ttlMs = 30000 }) => {
      acquires.push(path);
      if (acquireThrows > 0) { acquireThrows--; throw { code: 'unavailable', message: 'x' }; }
      const l = leases.get(path), now = Date.now();
      if (l && l.holder !== holder && l.until > now) return { acquired: false };
      leases.set(path, { holder, until: now + ttlMs }); return { acquired: true };
    },
    onSnapshot: () => () => {},
  };
}
const cmpV = (a, b) => (typeof a === 'number' && typeof b === 'number' ? a - b : String(a) < String(b) ? -1 : String(a) > String(b) ? 1 : 0);
const OPS = { '==': (a, b) => a === b, '!=': (a, b) => a !== b, '<': (a, b) => a != null && cmpV(a, b) < 0, '<=': (a, b) => a != null && cmpV(a, b) <= 0,
  '>': (a, b) => a != null && cmpV(a, b) > 0, '>=': (a, b) => a != null && cmpV(a, b) >= 0 };
function queryRef(coll, q) {
  const docs = () => {
    let all = [...store.entries()].filter(([p]) => collOf(p) === coll).sort(([a], [b]) => (a < b ? -1 : 1)).map(([p, b]) => snapOf(p, b));
    for (const [f, op, v] of q.wheres) all = all.filter(d => OPS[op](d.data()[f], v));
    if (q.order) {
      const [f, dir] = q.order;
      all.sort((x, y) => { const a = x.data()[f], b = y.data()[f]; if (a == null && b == null) return 0; if (a == null) return 1; if (b == null) return -1; return dir === 'desc' ? -cmpV(a, b) : cmpV(a, b); });
    }
    return q.lim ? all.slice(0, q.lim) : all;
  };
  const rec = how => queries.push({ coll, wheres: q.wheres, order: q.order, lim: q.lim, how });
  return {
    where: (f, op, v) => queryRef(coll, { ...q, wheres: [...q.wheres, [f, op, v]] }),
    orderBy: (f, dir = 'asc') => queryRef(coll, { ...q, order: [f, dir] }),
    limit: n => queryRef(coll, { ...q, lim: n }),
    get: async () => { rec('get'); await failIf('query', coll); return { docs: docs(), docChanges: () => [] }; },
    onSnapshot(next) {
      rec('snap');
      let prev = new Map();
      const emit = () => {
        const now = docs();
        const cur = new Map(now.map(d => [d.id, JSON.stringify(d.data())]));
        const changes = [];
        for (const d of now) if (!prev.has(d.id)) changes.push({ type: 'added', doc: d }); else if (prev.get(d.id) !== cur.get(d.id)) changes.push({ type: 'modified', doc: d });
        for (const [id, body] of prev) if (!cur.has(id)) changes.push({ type: 'removed', doc: snapOf(`${coll}/${id}`, JSON.parse(body)) });
        prev = cur;
        next({ docs: now, docChanges: () => changes, metadata: { fromCache: false } });
      };
      const fn = () => setTimeout(emit, 0);
      if (!listeners.has(coll)) listeners.set(coll, new Set());
      listeners.get(coll).add(fn);
      setTimeout(emit, 0);
      return () => listeners.get(coll).delete(fn);
    },
  };
}
function collRef(coll) {
  return { ...queryRef(coll, { wheres: [], order: null, lim: null }), path: coll, doc: id => docRef(`${coll}/${id ?? Math.random().toString(36).slice(2)}`) };
}
const blobs = new Map();
let assetN = 0;
const mcpCalls = [];
let mcpReject = null;                // rejection object for the next fire_trigger calls (null = success)
let saves = [];
let saveReject = null;
// the viewer: mutable so a fresh bundle (fresh module state) sees another person
const who = { id: 'u-owner', name: 'Abhi', email: 'abhi@example.org', isOwner: true, canWrite: true };
const caps = {
  db: { doc: docRef, collection: collRef },
  assets: { upload: async (blob, o) => { const id = (++assetN).toString(16).padStart(32, '0'); blobs.set(id, { bytes: new Uint8Array(await blob.arrayBuffer()), type: o?.type || blob.type }); return { id, url: `/_blob/${id}`, sizeBytes: blob.size, contentType: o?.type }; } },
  downloads: { save: async r => { if (saveReject) throw saveReject; saves.push(r); return { status: 'saved' }; } },
  mcp: { callTool: async (server, tool, input) => { mcpCalls.push({ server, tool, input }); if (mcpReject) throw mcpReject; return { payload: { ok: true } }; } },
  user: {
    me: async () => ({ id: who.id, name: who.name, email: who.email, isOwner: who.isOwner, canEdit: who.isOwner }),
    isOwner: async () => who.isOwner,
    can: async c => (c === 'data.write' ? who.canWrite : false),
  },
};
globalThis.window = { claude: { use: async n => caps[n] ?? null } };
globalThis.document = { getElementById: () => null, createElement: () => ({ click() {}, remove() {} }), body: { appendChild() {} } };
const realFetch = globalThis.fetch;
globalThis.fetch = async (u, o) => {
  const m = /^\/_blob\/([0-9a-f]{32})$/.exec(String(u));
  if (m) { const b = blobs.get(m[1]); return b ? new Response(b.bytes, { status: 200 }) : new Response('', { status: 404 }); }
  if (String(u).startsWith('blob:')) return realFetch(u, o);
  throw new Error(`unexpected fetch ${u}`);
};
globalThis.FileReader = class {
  readAsDataURL(blob) { blob.arrayBuffer().then(b => { this.result = `data:${blob.type};base64,${Buffer.from(b).toString('base64')}`; this.onload(); }, e => { this.error = e; this.onerror(); }); }
};
/** A fresh copy of the bundle (own module state: viewer, caches) for another viewer. */
let copyN = 0;
const freshLayer = async () => { const p = out.replace(/bundle\.mjs$/, `bundle${++copyN}.mjs`); copyFileSync(out, p); return import(p); };

const L = await import(out);
const { sb, api, uploadFile, fileBytes, fileUrl, downloadFile, ApiError, humanError, searchDocs, fireFailText, artifactSaveFile } = L;
let n = 0;
const t = async (name, fn) => { await fn(); n++; console.log('ok', name); };
const rejects = async (p, status, error) => {
  try { await p; } catch (e) { assert.ok(e?.constructor?.name === ApiError.name && 'status' in e, `ApiError expected, got ${e}`); assert.equal(e.status, status); assert.equal(e.message, error); return e; }
  assert.fail(`expected ${status} ${error}`);
};

await t('auth session + /api/me owner', async () => {
  const { data } = await sb().auth.getSession();
  assert.equal(data.session.user.id, 'u-owner');
  const me = await api('/api/me');
  assert.equal(me.role, 'owner');
  assert.deepEqual(Object.keys(me.profile), ['display_name', 'designation', 'office', 'mine']);
  assert.equal(store.get('members/u-owner').role, 'owner');
  const m2 = await api('/api/me', { method: 'PATCH', body: { designation: 'कार्यासन अधिकारी' } });
  assert.equal(m2.profile.designation, 'कार्यासन अधिकारी');
  assert.equal((await api('/api/public-config')).configured, true);
});

let caseId;
await t('create case, even page ids under locks/seq_cases, no meta/ writes, duplicate C R 409', async () => {
  const c = await api('/api/cases', { body: { cr_no: '14', cr_year: 2026, subject: 'विषय', category: 'सेवा' } });
  caseId = c.id;
  assert.equal(c.id, 2);
  assert.equal(c.stage, 'प्राप्त');
  assert.ok(acquires.includes('locks/seq_cases'));
  assert.equal(store.has('meta/seq_cases'), false);
  const e = await rejects(api('/api/cases', { body: { cr_no: '014', cr_year: 2026 } }), 409, 'duplicate_cr');
  assert.equal(e.data.existing_id, 2);
  assert.match(humanError(e), /प्रकरण क्र\. 2/);
  const c2 = await api('/api/cases', { body: { cr_no: '15', cr_year: 2026 } });
  assert.equal(c2.id, 4);
  await rejects(api('/api/cases', { body: { cr_no: '1a' } }), 400, 'cr_no: digits only');
  const p = await api(`/api/cases/${c2.id}`, { method: 'PATCH', body: { nasti_no: ' 12/34 ' } });
  assert.equal(p.nasti_no, '12/34');
});

await t('select shapes: order / eq / maybeSingle / not is null / in / gte', async () => {
  const { data, error } = await sb().from('cases').select('*').order('created_at', { ascending: false });
  assert.equal(error, null);
  assert.equal(data.length, 2);
  const one = await sb().from('cases').select('*').eq('id', caseId).maybeSingle();
  assert.equal(one.data.cr_no, '14');
  const none = await sb().from('cases').select('*').eq('id', 99).maybeSingle();
  assert.equal(none.data, null);
  assert.equal(none.error, null);
  const cols = await sb().from('cases').select('id,stage').in('id', [2, 4]).gte('created_at', '2000-01-01');
  assert.deepEqual(Object.keys(cols.data[0]), ['id', 'stage']);
  const nn = await sb().from('runs').select('*').eq('state', 'done').not('cost_usd', 'is', null).limit(40);
  assert.deepEqual(nn.data, []);
});

await t('stage update through sb() logs stage_changed (touch_case)', async () => {
  const { error } = await sb().from('cases').update({ stage: 'मसुदा तयार' }).eq('id', caseId);
  assert.equal(error, null);
  queries.length = 0;
  const a = await sb().from('activity').select('id,case_id,action,detail,at').eq('action', 'stage_changed').order('at', { ascending: false }).limit(8);
  assert.equal(a.data.length, 1);
  // A-M4: the limited activity read went to the store as where + orderBy + limit
  assert.deepEqual(queries.map(q => [q.coll, q.wheres, q.order, q.lim]), [['activity', [['action', '==', 'stage_changed']], ['at', 'desc'], 8]]);
  const byCase = await sb().from('activity').select('*').eq('case_id', String(caseId)).order('at', { ascending: false }).limit(300);
  assert.ok(byCase.data.length >= 1 && byCase.data.every(r => r.case_id === caseId));
  assert.deepEqual(queries.at(-1).wheres, [['case_id', '==', caseId]]);
  assert.deepEqual(a.data[0].detail, { from: 'प्राप्त', to: 'मसुदा तयार' });
});

await t('upload: pdf as one asset; docx and >19 MiB as base64 parts; bytes round-trip', async () => {
  const pdf = new Uint8Array([...Buffer.from('%PDF-1.7\n'), ...new Uint8Array(500).fill(7)]);
  const f = await uploadFile(caseId, 'proposal', new File([pdf], 'प्रस्ताव.pdf', { type: 'application/pdf' }));
  const row = store.get(`case_files/${f.id}`);
  assert.match(row.storage_path, /^asset:[0-9a-f]{32}$/);
  assert.equal(row.asset_id, row.storage_path.slice(6));
  assert.equal(row.version, 1);
  assert.deepEqual(new Uint8Array((await fileBytes(f.id)).data), pdf);
  assert.equal((await fileUrl(f.id)).url, `/_blob/${row.asset_id}`);
  const f2 = await uploadFile(caseId, 'proposal', new File([pdf], 'प्रस्ताव.pdf'));
  assert.equal(store.get(`case_files/${f2.id}`).version, 2);
  const big = new Uint8Array(15_000_000); big.set([0x50, 0x4B, 0x03, 0x04]); for (let i = 4; i < big.length; i += 9973) big[i] = i & 255;
  const d = await uploadFile(caseId, 'extra_doc', new File([big], 'a.docx'));
  const drow = store.get(`case_files/${d.id}`);
  assert.equal(drow.asset_parts.length, 2);
  assert.equal(drow.storage_path, 'asset-parts:2');
  const back = new Uint8Array((await fileBytes(d.id)).data);
  assert.equal(back.length, big.length);
  assert.ok(Buffer.from(back).equals(Buffer.from(big)));
  await downloadFile(d.id);
  assert.equal(saves.at(-1).filename, 'a.docx');
  await rejects(uploadFile(caseId, 'proposal', new File([new Uint8Array([1, 2, 3])], 'x.pdf')), 400, 'हा फाइल-प्रकार स्वीकारता येत नाही. कृपया PDF, Word (DOC / DOCX) किंवा प्रतिमा (JPG / PNG / TIF) फाइल जोडावी, ही विनंती.');
});

await t('letters + reply upload marks the single pending letter', async () => {
  const l = await api('/api/letters', { body: { case_id: caseId, ref_no: 'संकिर्ण-2026/1/प्र.क्र.14/का.6', sent_date: '2026-11-01' } });
  assert.equal(store.get(`cases/${caseId}`).stage, 'पत्र पाठवले (माहिती प्रतीक्षेत)');
  const pdf = new Uint8Array([...Buffer.from('%PDF-1.4\n')]);
  const r = await uploadFile(caseId, 'reply', new File([pdf], 'उत्तर.pdf'));
  assert.equal(r.letter_updated, l.id);
  assert.equal(store.get(`letters/${l.id}`).status, 'उत्तर प्राप्त');
  assert.equal(store.get(`cases/${caseId}`).stage, 'माहिती प्राप्त');
});

await t('realtime: runs channel with case filter + /api/run queued, fire failure keeps it queued, retry fires', async () => {
  const events = [];
  let subscribed = false;
  const ch = sb().channel('runs-1').on('postgres_changes', { event: '*', schema: 'public', table: 'runs', filter: `case_id=eq.${caseId}` }, p => events.push(p)).subscribe(s => { if (s === 'SUBSCRIBED') subscribed = true; });
  await new Promise(r => setTimeout(r, 20));
  assert.ok(subscribed);
  const e = await rejects(api('/api/run', { body: { case_id: caseId, outputs: ['reminder', 'letter'] } }), 502, 'trigger_failed');
  assert.match(humanError(e, false), /प्रतीक्षा-यादीत नोंदवली/);
  const runId = e.data.run_id;
  let run = store.get(`runs/${runId}`);
  assert.equal(run.state, 'queued');
  assert.equal(run.dispatched_at, null);
  assert.equal(run.dispatch_error, 'error');
  assert.equal(run.dispatch_tries, 1);
  assert.equal(e.data.code, 'error');
  assert.deepEqual(run.outputs, ['letter', 'reminder']);
  assert.equal(run.kind, 'full');
  assert.deepEqual(run.essential_points, []);
  store.set('meta/config', { trigger_id: 'trig_test' });
  const ok = await api('/api/run', { body: { case_id: caseId } });
  assert.equal(ok.id, runId);
  assert.equal(ok.queued, false);
  assert.ok(ok.dispatched_at);
  assert.equal(ok.dispatch_error, null);
  assert.equal(ok.dispatch_tries, 2);
  assert.deepEqual(mcpCalls.at(-1), { server: 'Claude Code Remote', tool: 'fire_trigger', input: { trigger_id: 'trig_test' } });
  assert.equal(store.get(`cases/${caseId}`).stage, 'अभ्यास चालू');
  await rejects(api('/api/run', { body: { case_id: caseId } }), 409, 'run_active');
  await new Promise(r => setTimeout(r, 20));
  assert.ok(events.some(p => p.eventType === 'INSERT' && p.new.id === runId && p.new.state === 'queued'));
  // the worker finishes the run (its write reaches the page as an UPDATE)
  store.set(`runs/${runId}`, { ...store.get(`runs/${runId}`), state: 'done', step: 'पूर्ण', cost_usd: 1.25, finished_at: new Date().toISOString() });
  notify('runs');
  await new Promise(r => setTimeout(r, 20));
  assert.ok(events.some(p => p.eventType === 'UPDATE' && p.new.state === 'done' && p.old.state === 'queued'));
  await sb().removeChannel(ch);
  const sp = await api('/api/spend');
  assert.equal(sp.spent_usd, 1.25);
  assert.equal(sp.limit_usd, 1000);
  await rejects(api('/api/edit', { body: { case_id: caseId, target: 'note', message: 'बदल' } }), 409, 'no_spec');
});

await t('gr_library from the index asset, open → request, file present → url', async () => {
  const idx = [
    { key: 'k1', path: 'pdf/gr/a.pdf', folder: 'gr', topic: 'finance', file: 'a.pdf', code: '202204191549468012', date: '19.04.2022', title: 'GR A', url: 'https://x/a.pdf' },
    { key: 'k2', path: 'pdf/b/b.pdf', folder: 'b', topic: 'pay', file: 'b.pdf', code: '', date: '', title: '', url: '' },
  ];
  const id = 'f'.repeat(32);
  blobs.set(id, { bytes: new Uint8Array(Buffer.from(JSON.stringify(idx))), type: 'application/json' });
  store.set('meta/gr_library', { asset: id });
  const { data } = await sb().from('gr_library').select('*').order('date', { ascending: false, nullsFirst: false });
  assert.equal(data.length, 2);
  assert.equal(data[0].code, '202204191549468012');
  assert.equal(data[0].date, '2022-04-19');
  assert.equal(data[0].department, 'finance');
  assert.equal(data[1].code, 'k2');
  assert.equal(data[1].title, 'b.pdf');
  assert.equal(data[1].storage_path, null);
  const e = await rejects(api('/api/gr/k2'), 409, 'gr_requested');
  assert.match(humanError(e), /मागविण्याची नोंद/);
  assert.equal(store.get('gr_requests/k2').status, 'pending');
  assert.equal(store.get('gr_requests/k2').path, 'pdf/b/b.pdf');
  const pdfId = 'e'.repeat(32);
  blobs.set(pdfId, { bytes: new Uint8Array(Buffer.from('%PDF-1.4')), type: 'application/pdf' });
  store.set('gr_files/k1', { store: 'asset', ref: pdfId, name: 'a.pdf' });
  assert.equal((await api('/api/gr/202204191549468012')).url, `/_blob/${pdfId}`);
  assert.equal((await sb().from('gr_library').select('*').eq('code', '202204191549468012').single()).data.storage_path, `asset:${pdfId}`);
  assert.equal((await api('/api/gr', { body: { code: '202204191549468012' } })).ok, true);
  await rejects(api('/api/gr', { body: { code: '123' } }), 400, 'सांकेतांक 16 ते 20 अंकी असावा. कृपया योग्य सांकेतांक नमूद करावा, ही विनंती.');
});

await t('register search over meta/register_index (empty query [], no header in snippets)', async () => {
  assert.deepEqual(await api('/api/search?q='), []);
  await rejects(api('/api/search?q=वेतन'), 503, 'search_unavailable');
  const docs = [{ path: 'register/01-pay.md', title: '# वेतननिश्चिती', text: '---\ntitle: वेतन नियम\n---\n# वेतननिश्चिती\n\nनियम 11 वेतन\nदुसरी ओळ' }, { path: 'register/02.md', title: 'x', text: 'काहीही नाही' }];
  const id = 'd'.repeat(32);
  blobs.set(id, { bytes: new Uint8Array(Buffer.from(JSON.stringify(docs))), type: 'application/json' });
  store.set('meta/register_index', { asset: id });
  const r = await api('/api/search?q=' + encodeURIComponent('नियम वेतन'));
  assert.equal(r.length, 1);
  assert.equal(r[0].path, 'register/01-pay.md');
  assert.ok(r[0].frags.length >= 1 && r[0].frags[0].includes('नियम 11'));
  assert.ok(r[0].frags.every(f => !f.includes('---') && !f.includes('# वेतननिश्चिती') && !f.includes('title:')), JSON.stringify(r[0].frags));
  assert.deepEqual(searchDocs(docs, 'repo:x'), []);
});

await t('owner-only endpoints are harmless', async () => {
  assert.deepEqual(await api('/api/settings'), {});
  assert.deepEqual(await api('/api/settings', { method: 'PUT', body: { model: 'x' } }), { ok: true });
  assert.deepEqual(await api('/api/runs/sweep', { method: 'POST', body: {} }), { ok: true, failed: [], dispatched: null });
  await rejects(api('/api/members', { body: { email: 'a@b.c', role: 'staff' } }), 409, 'members_artifact');
  await rejects(api('/api/nope'), 404, 'not found');
});

const pdfFile = name => new File([new Uint8Array([...Buffer.from('%PDF-1.4\n')])], name, { type: 'application/pdf' });
const finish = id => { store.set(`runs/${id}`, { ...store.get(`runs/${id}`), state: 'done', finished_at: new Date().toISOString() }); };

await t('(a) approval_required: full run stays queued with dispatch_error; /api/run/<id>/fire succeeds later', async () => {
  await uploadFile(4, 'proposal', pdfFile('p4.pdf'));
  mcpReject = { code: 'approval_required', message: 'needs approval' };
  const e = await rejects(api('/api/run', { body: { case_id: 4 } }), 502, 'trigger_failed');
  assert.equal(e.data.code, 'approval_required');
  assert.equal(e.data.reason, fireFailText('approval_required'));
  assert.match(humanError(e, false), /परवानगी/);
  const id = e.data.run_id;
  let r = store.get(`runs/${id}`);
  assert.deepEqual([r.state, r.dispatched_at, r.dispatch_error, r.dispatch_tries], ['queued', null, 'approval_required', 1]);
  assert.notEqual(store.get('cases/4').stage, 'अभ्यास चालू');
  mcpReject = null;
  const ok = await api(`/api/run/${id}/fire`, { method: 'POST', body: {} });
  assert.equal(ok.id, id);
  assert.ok(ok.dispatched_at);
  assert.equal(ok.dispatch_error, null);
  assert.equal(ok.dispatch_unsure, null);
  assert.equal(ok.dispatch_tries, 2);
  assert.equal(store.get('cases/4').stage, 'अभ्यास चालू');
  const started = [...store.values()].filter(v => v.action === 'run_started' && v.detail?.run_id === id);
  assert.equal(started.length, 1);
  finish(id);
  const nw = await rejects(api(`/api/run/${id}/fire`, { method: 'POST', body: {} }), 409, 'run_not_waiting');
  assert.match(nw.data.reason, /आधीच/);
});

await t('(a) approval_required: edit run stays queued; new edit refused run_waiting; /fire succeeds', async () => {
  store.set('case_files/1001', { id: 1001, case_id: 4, kind: 'spec', original_name: 'spec.json', version: 1 });
  mcpReject = { code: 'approval_required', message: 'x' };
  const e = await rejects(api('/api/edit', { body: { case_id: 4, target: 'note', message: 'परि. 2 बदला' } }), 502, 'trigger_failed');
  const id = e.data.run_id;
  let r = store.get(`runs/${id}`);
  assert.deepEqual([r.kind, r.state, r.dispatched_at, r.dispatch_error], ['edit', 'queued', null, 'approval_required']);
  const w = await rejects(api('/api/edit', { body: { case_id: 4, target: 'note', message: 'आणखी' } }), 409, 'run_waiting');
  assert.equal(w.data.run_id, id);
  assert.match(w.data.reason, /पूर्वीची प्रक्रिया सुरू झालेली नाही/);
  mcpReject = null;
  const ok = await api(`/api/run/${id}/fire`, { method: 'POST', body: {} });
  assert.ok(ok.dispatched_at);
  assert.equal(ok.dispatch_error, null);
  assert.equal([...store.values()].filter(v => v.action === 'run_started' && v.detail?.run_id === id).length, 0);
  finish(id);
});

await t('(b) ambiguous mcp answers -> dispatch_unsure + dispatched_at; retryable upstream_error is definite', async () => {
  for (const rej of [{ code: 'upstream_error', message: 'no reply' }, { code: 'cancelled', message: 'x' }, { code: 'server_unavailable', message: 't', retryable: true }, { code: 'brand_new_code', message: 'x' }]) {
    mcpReject = rej;
    const r = await api('/api/run', { body: { case_id: 4 } });
    assert.ok(r.dispatched_at, rej.code);
    assert.equal(store.get(`runs/${r.id}`).dispatch_unsure, true, rej.code);
    assert.equal(store.get(`runs/${r.id}`).dispatch_error, null);
    finish(r.id);
  }
  mcpReject = { code: 'upstream_error', message: 'consent prompt busy', retryable: true };
  const e = await rejects(api('/api/run', { body: { case_id: 4 } }), 502, 'trigger_failed');
  assert.equal(store.get(`runs/${e.data.run_id}`).dispatch_unsure, null);
  assert.equal(store.get(`runs/${e.data.run_id}`).dispatch_error, 'error');
  mcpReject = { code: 'not_in_manifest', message: 'x' };
  const e2 = await rejects(api(`/api/run/${e.data.run_id}/fire`, { method: 'POST', body: {} }), 502, 'trigger_failed');
  assert.equal(e2.data.reason, fireFailText('server_not_connected'));
  assert.equal(store.get(`runs/${e.data.run_id}`).dispatch_tries, 2);
  mcpReject = null;
  finish(e.data.run_id);
});

let staff;
await t('(c) non-owner without own trigger -> no_trigger, owner trigger never called; own trigger fires', async () => {
  Object.assign(who, { id: 'u-staff', name: 'S', email: 's@example.org', isOwner: false, canWrite: true });
  staff = await freshLayer();
  const before = mcpCalls.length;
  leases.clear(); // the owner tab's leases (fake: 5 s) would make the second tab wait
  const e = await rejects(staff.api('/api/run', { body: { case_id: 4 } }), 502, 'trigger_failed');
  assert.equal(e.data.code, 'no_trigger');
  assert.equal(e.data.reason, fireFailText('no_trigger'));
  assert.equal(mcpCalls.length, before);
  assert.equal(store.get(`runs/${e.data.run_id}`).dispatch_error, 'no_trigger');
  store.set('meta/config', { trigger_id: 'trig_test', triggers: { 'u-staff': 'trig_staff' } });
  const ok = await staff.api(`/api/run/${e.data.run_id}/fire`, { method: 'POST', body: {} });
  assert.ok(ok.dispatched_at);
  assert.deepEqual(mcpCalls.at(-1).input, { trigger_id: 'trig_staff' });
  finish(e.data.run_id);
});

await t('(d) roles: owner / staff (can data.write) / senior (read-only); no owner row for a non-owner', async () => {
  assert.equal((await api('/api/me')).role, 'owner');
  store.set('members/u-staff', { user_id: 'u-staff', role: 'owner', email: 's@example.org' }); // old bug
  const m = await staff.api('/api/me');
  assert.equal(m.role, 'staff');
  assert.equal(store.get('members/u-staff').role, 'staff');
  Object.assign(who, { id: 'u-senior', name: 'V', email: 'v@example.org', isOwner: false, canWrite: false });
  const senior = await freshLayer();
  const n0 = writes.length;
  const ms = await senior.api('/api/me');
  assert.equal(ms.role, 'senior');
  assert.equal(store.has('members/u-senior'), false);
  const e = await senior.api('/api/me', { method: 'PATCH', body: { designation: 'x' } }).catch(x => x);
  assert.equal(e.status, 403);
  assert.match(e.data.reason, /फक्त पाहण्याची परवानगी/);
  assert.equal(writes.length, n0);
  assert.ok(![...store.entries()].some(([p, v]) => p.startsWith('members/') && p !== 'members/u-owner' && v.role === 'owner'));
  const saved = caps.user; delete caps.user;
  const old = await freshLayer();
  assert.equal((await old.api('/api/me')).role, 'owner');
  caps.user = saved;
  Object.assign(who, { id: 'u-owner', name: 'Abhi', email: 'abhi@example.org', isOwner: true, canWrite: true });
});

await t('(e) ids: even ids, skip odd worker row and existing even row, legacy meta/seq read-only, lease on locks/', async () => {
  const cases = [...store.keys()].filter(p => p.startsWith('cases/')).map(p => Number(p.slice(6)));
  const top = Math.max(...cases);
  store.set(`cases/${top + 3}`, { id: top + 3, subject: 'worker row (odd)', stage: 'प्राप्त', created_at: new Date().toISOString() });
  store.set(`cases/${top + 4}`, { subject: 'even row without id field', stage: 'प्राप्त', created_at: new Date().toISOString() });
  leases.clear();
  const L2 = await freshLayer(); // fresh cache: only the store read decides
  const c = await L2.api('/api/cases', { body: { cr_no: '901', cr_year: 2026 } });
  assert.equal(c.id, top + 6);
  store.set('meta/seq_letters', { next: 51, table: 'letters' });
  leases.clear();
  const l = await api('/api/letters', { body: { case_id: caseId, ref_no: 'x' } });
  assert.equal(l.id, 52);
  assert.equal(store.get('meta/seq_letters').next, 51);
  acquireThrows = 2;
  const c2 = await api('/api/cases', { body: { cr_no: '902', cr_year: 2026 } });
  assert.equal(c2.id % 2, 0);
  leases.set('locks/seq_cases', { holder: 'another-tab', until: Date.now() + 60_000 });
  const e = await api('/api/cases', { body: { cr_no: '903', cr_year: 2026 } }).catch(x => x);
  assert.equal(e.status, 503);
  assert.match(e.data.reason, /दुसऱ्या टॅबमध्ये/);
  leases.delete('locks/seq_cases');
  assert.deepEqual(writes.filter(p => p.startsWith('meta/')), []);
  assert.ok([...store.keys()].filter(p => /^(cases|letters|runs|activity|case_files)\/\d+$/.test(p) && !store.get(p).subject?.startsWith('worker') && p !== 'case_files/1001')
    .every(p => Number(p.split('/')[1]) % 2 === 0));
});

await t('(f) POST /api/gr/request writes pending + fires; processing > 30 min re-opened; GET /api/gr/requests', async () => {
  const n0 = mcpCalls.length;
  const r = await api('/api/gr/request', { body: { key: 'k2' } });
  assert.deepEqual([r.status, r.fired], ['pending', true]);
  assert.equal(mcpCalls.length, n0 + 1);
  const old = new Date(Date.now() - 40 * 60 * 1000).toISOString();
  store.set('gr_requests/k2', { ...store.get('gr_requests/k2'), status: 'processing', processing_at: old });
  assert.equal((await api('/api/gr/request', { body: { key: 'k2' } })).status, 'pending');
  assert.equal(store.get('gr_requests/k2').status, 'pending');
  const fresh = new Date(Date.now() - 5 * 60 * 1000).toISOString();
  store.set('gr_requests/k2', { ...store.get('gr_requests/k2'), status: 'processing', processing_at: fresh });
  assert.equal((await api('/api/gr/request', { body: { key: 'k2' } })).status, 'processing');
  assert.equal(store.get('gr_requests/k2').processing_at, fresh);
  store.set('gr_requests/k2', { ...store.get('gr_requests/k2'), status: 'failed', reply: 'मिळाला नाही' });
  assert.equal((await api('/api/gr/request', { body: { key: 'k2' } })).status, 'pending');
  const c = await api('/api/gr/request', { body: { code: '201901011234567812' } });
  assert.equal(store.get('gr_requests/201901011234567812').code, '201901011234567812');
  assert.equal(c.status, 'pending');
  assert.equal((await api('/api/gr/request', { body: { code: '202204191549468012' } })).status, 'done');
  await rejects(api('/api/gr/request', { body: { code: '12' } }), 400, 'सांकेतांक 16 ते 20 अंकी असावा. कृपया योग्य सांकेतांक नमूद करावा, ही विनंती.');
  mcpReject = { code: 'approval_required', message: 'x' };
  const nf = await api('/api/gr/request', { body: { key: 'k2' } });
  assert.equal(nf.fired, false);
  assert.equal(nf.reason, fireFailText('approval_required'));
  mcpReject = null;
  const list = await api('/api/gr/requests');
  assert.ok(list.some(x => x.key === 'k2' && x.status === 'pending'));
  assert.deepEqual(Object.keys(list[0]), ['key', 'code', 'status', 'at', 'reply']);
});

await t('(g) db error codes -> Marathi + db_<code> (sb() and api)', async () => {
  dbFail = (op, path) => (op === 'set' && path.startsWith('cases/') ? { code: 'invalid_argument', message: 'rule' } : null);
  const u = await sb().from('cases').update({ subject: 'x' }).eq('id', caseId);
  assert.equal(u.error.code, 'db_invalid_argument');
  assert.match(u.error.message, /फक्त पाहण्याची परवानगी/);
  const e = await api('/api/cases', { body: { cr_no: '904', cr_year: 2026 } }).catch(x => x);
  assert.ok(e instanceof ApiError);
  assert.equal(e.message, 'db_invalid_argument');
  assert.match(humanError(e, false), /फक्त पाहण्याची परवानगी/);
  dbFail = (op, path) => (op === 'query' && path === 'runs' ? { code: 'weird_new', message: 'x' } : null);
  const q = await sb().from('runs').select('*');
  assert.equal(q.error.code, 'db_unavailable');
  assert.match(q.error.message, /तात्पुरती अडचण/);
  dbFail = (op, path) => (op === 'set' && path.startsWith('activity/') ? { code: 'quota_exceeded', message: 'x' } : null);
  const qe = await api(`/api/cases/${caseId}`, { method: 'PATCH', body: { subject: 'नवा' } }).catch(x => x);
  assert.equal(qe.message, 'db_quota_exceeded');
  assert.match(qe.data.reason, /मर्यादा पूर्ण/);
  dbFail = null;
  const saved = caps.db; delete caps.db;
  const nodb = await freshLayer();
  const nd = await nodb.sb().from('cases').select('*');
  assert.equal(nd.error.code, 'db_not_granted');
  assert.match(nd.error.message, /मूळ दुव्यावरून/);
  caps.db = saved;
});

await t('(h) activity channel subscribes to the limited query; downloads rate_limited -> Marathi error', async () => {
  queries.length = 0;
  const got = [];
  const ch = sb().channel('act').on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'activity' }, p => got.push(p)).subscribe();
  await new Promise(r => setTimeout(r, 20));
  assert.deepEqual(queries.filter(q => q.how === 'snap').map(q => [q.coll, q.order, q.lim]), [['activity', ['at', 'desc'], 200]]);
  await api(`/api/cases/${caseId}`, { method: 'PATCH', body: { subject: 'आणखी नवा' } });
  await new Promise(r => setTimeout(r, 20));
  assert.ok(got.some(p => p.new.action === 'case_updated'));
  await sb().removeChannel(ch);
  saveReject = { code: 'rate_limited', message: 'x' };
  const e = await artifactSaveFile('a.csv', new Blob(['a,b'])).catch(x => x);
  assert.equal(e.status, 429);
  assert.match(e.data.reason, /थोड्या वेळाने/);
  saveReject = { code: 'declined', message: 'x' };
  await artifactSaveFile('a.csv', new Blob(['a,b']));
  saveReject = null;
  await artifactSaveFile('a.csv', new Blob(['a,b']));
  assert.equal(saves.at(-1).filename, 'a.csv');
});

console.log(`ALL ${n} PASSED`);
