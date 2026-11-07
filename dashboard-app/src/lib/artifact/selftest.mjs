// Self-test of the artifact data layer against an in-memory fake of window.claude (db, assets, downloads, mcp, user).
// Run from dashboard-app/:  node src/lib/artifact/selftest.mjs
// It bundles a small entry with esbuild (a vite dependency) — VITE_BACKEND=artifact — and checks the call shapes the
// app uses. Exit code 0 = all passed.
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import assert from 'node:assert/strict';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(mkdtempSync(join(tmpdir(), 'artifact-selftest-')), 'bundle.mjs');
const entry = `
export { sb } from ${JSON.stringify(join(here, '../supabase.ts'))};
export { api, uploadFile, fileBytes, fileUrl, downloadFile, ApiError, humanError } from ${JSON.stringify(join(here, '../api.ts'))};
export { searchDocs } from ${JSON.stringify(join(here, 'api.ts'))};
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
const clone = v => JSON.parse(JSON.stringify(v));
const snapOf = (path, body) => ({ id: path.split('/').pop(), exists: body !== undefined, data: () => (body === undefined ? undefined : Object.freeze(clone(body))) });
const collOf = path => path.split('/').slice(0, -1).join('/');
function notify(coll) { for (const fn of listeners.get(coll) || []) fn(); }
function docRef(path) {
  return {
    id: path.split('/').pop(), path,
    get: async () => snapOf(path, store.get(path)),
    set: async d => { store.set(path, clone(d)); notify(collOf(path)); },
    update: async d => { if (!store.has(path)) throw { code: 'invalid_argument' }; store.set(path, { ...store.get(path), ...clone(d) }); notify(collOf(path)); },
    delete: async () => { store.delete(path); notify(collOf(path)); },
    acquire: async ({ holder }) => { const l = leases.get(path); if (l && l !== holder) return { acquired: false }; leases.set(path, holder); return { acquired: true }; },
    onSnapshot: () => () => {},
  };
}
function collRef(coll) {
  const docs = () => [...store.entries()].filter(([p]) => collOf(p) === coll).sort(([a], [b]) => (a < b ? -1 : 1)).map(([p, b]) => snapOf(p, b));
  return {
    doc: id => docRef(`${coll}/${id ?? Math.random().toString(36).slice(2)}`),
    get: async () => ({ docs: docs(), docChanges: () => [] }),
    onSnapshot(next) {
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
const blobs = new Map();
let assetN = 0;
const mcpCalls = [];
let saves = [];
const caps = {
  db: { doc: docRef, collection: collRef },
  assets: { upload: async (blob, o) => { const id = (++assetN).toString(16).padStart(32, '0'); blobs.set(id, { bytes: new Uint8Array(await blob.arrayBuffer()), type: o?.type || blob.type }); return { id, url: `/_blob/${id}`, sizeBytes: blob.size, contentType: o?.type }; } },
  downloads: { save: async r => { saves.push(r); return { status: 'saved' }; } },
  mcp: { callTool: async (server, tool, input) => { mcpCalls.push({ server, tool, input }); return { payload: { ok: true } }; } },
  user: { me: async () => ({ id: 'u-owner', name: 'Abhi', email: 'abhi@example.org', isOwner: true, canEdit: true }) },
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

const L = await import(out);
const { sb, api, uploadFile, fileBytes, fileUrl, downloadFile, ApiError, humanError, searchDocs } = L;
let n = 0;
const t = async (name, fn) => { await fn(); n++; console.log('ok', name); };
const rejects = async (p, status, error) => {
  try { await p; } catch (e) { assert.ok(e instanceof ApiError, `ApiError expected, got ${e}`); assert.equal(e.status, status); assert.equal(e.message, error); return e; }
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
await t('create case, ids from meta/seq_cases, duplicate C R 409', async () => {
  const c = await api('/api/cases', { body: { cr_no: '14', cr_year: 2026, subject: 'विषय', category: 'सेवा' } });
  caseId = c.id;
  assert.equal(c.id, 1);
  assert.equal(c.stage, 'प्राप्त');
  assert.equal(store.get('meta/seq_cases').next, 2);
  const e = await rejects(api('/api/cases', { body: { cr_no: '014', cr_year: 2026 } }), 409, 'duplicate_cr');
  assert.equal(e.data.existing_id, 1);
  assert.match(humanError(e), /प्रकरण क्र\. 1/);
  const c2 = await api('/api/cases', { body: { cr_no: '15', cr_year: 2026 } });
  assert.equal(c2.id, 2);
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
  const cols = await sb().from('cases').select('id,stage').in('id', [1, 2]).gte('created_at', '2000-01-01');
  assert.deepEqual(Object.keys(cols.data[0]), ['id', 'stage']);
  const nn = await sb().from('runs').select('*').eq('state', 'done').not('cost_usd', 'is', null).limit(40);
  assert.deepEqual(nn.data, []);
});

await t('stage update through sb() logs stage_changed (touch_case)', async () => {
  const { error } = await sb().from('cases').update({ stage: 'मसुदा तयार' }).eq('id', caseId);
  assert.equal(error, null);
  const a = await sb().from('activity').select('id,case_id,action,detail,at').eq('action', 'stage_changed').order('at', { ascending: false }).limit(8);
  assert.equal(a.data.length, 1);
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
  assert.deepEqual(run.outputs, ['letter', 'reminder']);
  assert.equal(run.kind, 'full');
  assert.deepEqual(run.essential_points, []);
  store.set('meta/config', { trigger_id: 'trig_test' });
  const ok = await api('/api/run', { body: { case_id: caseId } });
  assert.equal(ok.id, runId);
  assert.equal(ok.queued, false);
  assert.ok(ok.dispatched_at);
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

await t('register search over meta/register_index', async () => {
  await rejects(api('/api/search?q=वेतन'), 503, 'search_unavailable');
  const docs = [{ path: 'register/01-pay.md', title: '# वेतननिश्चिती', text: '# वेतननिश्चिती\n\nनियम 11 वेतन\nदुसरी ओळ' }, { path: 'register/02.md', title: 'x', text: 'काहीही नाही' }];
  const id = 'd'.repeat(32);
  blobs.set(id, { bytes: new Uint8Array(Buffer.from(JSON.stringify(docs))), type: 'application/json' });
  store.set('meta/register_index', { asset: id });
  const r = await api('/api/search?q=' + encodeURIComponent('नियम वेतन'));
  assert.equal(r.length, 1);
  assert.equal(r[0].path, 'register/01-pay.md');
  assert.ok(r[0].frags.length >= 1 && r[0].frags[0].includes('नियम 11'));
  assert.deepEqual(searchDocs(docs, 'repo:x'), []);
});

await t('owner-only endpoints are harmless', async () => {
  assert.deepEqual(await api('/api/settings'), {});
  assert.deepEqual(await api('/api/settings', { method: 'PUT', body: { model: 'x' } }), { ok: true });
  assert.deepEqual(await api('/api/runs/sweep', { method: 'POST', body: {} }), { ok: true, failed: [], dispatched: null });
  await rejects(api('/api/members', { body: { email: 'a@b.c', role: 'staff' } }), 409, 'members_artifact');
  await rejects(api('/api/nope'), 404, 'not found');
});

console.log(`ALL ${n} PASSED`);
