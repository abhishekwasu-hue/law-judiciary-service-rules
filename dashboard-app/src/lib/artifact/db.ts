// Artifact build: a minimal supabase-js-compatible client over the artifact `db` capability. Covers exactly the call
// shapes the app uses (README.md in this folder = the storage contract the cloud worker writes against).
//   from(t).select(cols, {count, head}).eq/neq/gt/gte/lt/lte/is/in/not/or/match/order/limit/range/single/maybeSingle
//   from(t).insert/update/upsert/delete(...) [.select()] [.single()]
//   channel(n).on('postgres_changes', {event, table, filter}, cb).subscribe(status => …) / removeChannel(ch)
//   auth.getSession / getUser / onAuthStateChange / signOut / signInWithOtp / verifyOtp (always the signed-in owner)
// Storage: collection per table (same name), doc id = String(row.id) (members: user_id, gr_library: code). Filters,
// order and limits run client-side on the whole collection (data is small) — except `activity` reads with a limit,
// which go to the store as orderBy/limit (+ simple where filters), client-side filters kept as a safety net (A-M4).
// Every db rejection is a Marathi DbFail (runtime.ts, A-M5). No top-level side effects.
import { cap, DbFail, isDbFail, needDb, nowIso, sleep, type Db, type DocSnap, type QueryRef } from './runtime';

export type Row = Record<string, unknown>;
type Err = { message: string; code?: string; details?: string; hint?: string };
type Res = { data: unknown; error: Err | null; count: number | null; status: number; statusText: string };

/** Doc-id column per table (default `id`, numeric, allocated by allocId). */
const KEY: Record<string, string> = { members: 'user_id', gr_library: 'code' };
export const keyOf = (table: string) => KEY[table] || 'id';
const NUMERIC_ID = (table: string) => keyOf(table) === 'id';

// ---------- the viewer and its role (A-M1) ----------
/** role: 'owner' = user.isOwner() (or no `user` capability at all: old single-owner page); 'staff' = may write
 *  (can('data.write') true or null); 'senior' = read-only (can('data.write') false). canWrite = role !== 'senior'. */
export type Role = 'owner' | 'staff' | 'senior';
export interface Viewer { id: string; email: string; name: string; isOwner: boolean; role: Role; canWrite: boolean }
let viewerP: Promise<Viewer> | null = null;
/** claude.ai viewer via the `user` capability; without it a fixed owner id. Never rejects. */
export function viewer(): Promise<Viewer> {
  if (!viewerP) {
    viewerP = (async () => {
      try {
        const u = await cap('user');
        if (u) {
          const m = await u.me();
          const isOwner = typeof u.isOwner === 'function' ? (await u.isOwner()) === true : m.isOwner === true;
          const w = isOwner ? true : typeof u.can === 'function' ? await u.can('data.write').catch(() => null) : null;
          const role: Role = isOwner ? 'owner' : w === false ? 'senior' : 'staff';
          return { id: m.id || (isOwner ? 'owner' : 'guest'), email: m.email || '', name: m.name || '', isOwner, role, canWrite: role !== 'senior' };
        }
      } catch {
        /* user capability failed: treated as absent below */
      }
      return { id: 'owner', email: '', name: '', isOwner: true, role: 'owner', canWrite: true };
    })();
  }
  return viewerP;
}

// ---------- defaults (SQL column defaults + later migrations) ----------
const NULLS = (cols: string) => Object.fromEntries(cols.split(',').map(c => [c, null]));
function defaults(table: string): Row {
  const t = nowIso();
  switch (table) {
    case 'cases':
      return { ...NULLS('cr_no,cr_year,file_no,subject,employee_name,post,office,received_from,received_via,inward_date,due_date,assigned_to,desk,work_type,nasti_no'),
        category: 'इतर', stage: 'प्राप्त', priority: 'सामान्य', created_at: t, updated_at: t };
    case 'case_files':
      return { version: 1, uploaded_by: null, created_at: t };
    case 'runs':
      return { ...NULLS('step,started_at,finished_at,instructions,log_url,summary,letter_needed,created_by,cost_usd,num_turns,duration_s,last_step,outputs,dispatched_at,edit_target,edit_message,edit_attachments,edit_result,config_taken_at,step_at,dispatch_error,dispatch_unsure'),
        dispatch_tries: 0, state: 'queued', essential_points: [], grs_attached: [], grs_missing: [], warnings: [], kind: 'full', created_at: t };
    case 'letters':
      return { ...NULLS('ref_no,addressed_to,sent_date,reply_due,reply_received_date'), status: 'पाठवले', created_at: t };
    case 'activity':
      return { case_id: null, actor: null, detail: {}, at: t };
    case 'members':
      return { role: 'staff', created_at: t, display_name: null, designation: null, office: null, mine: null };
    case 'gr_library':
      return { ...NULLS('date,department,title,storage_path,source_url'), used_in_cases: [] };
    default:
      return {};
  }
}

// ---------- raw store ----------
const maxIdCache = new Map<string, number>();
const rowOf = (table: string, s: DocSnap): Row | null => {
  const d = s.data();
  if (!d) return null;
  const r: Row = { ...d };
  const k = keyOf(table);
  if (r[k] === undefined || r[k] === null) r[k] = NUMERIC_ID(table) && /^\d+$/.test(s.id) ? Number(s.id) : s.id;
  return r;
};
function noteIds(table: string, rows: Row[]) {
  if (!NUMERIC_ID(table)) return;
  let m = maxIdCache.get(table) || 0;
  for (const r of rows) { const n = Number(r.id); if (Number.isFinite(n) && n > m) m = n; }
  maxIdCache.set(table, m);
}

/** All rows of a table (gr_library: the GR index asset merged with any gr_library docs). */
export async function listRows(table: string): Promise<Row[]> {
  if (table === 'gr_library') return grLibraryRows();
  const db = await needDb();
  const snap = await db.collection(table).get();
  const rows = snap.docs.map(s => rowOf(table, s)).filter((r): r is Row => !!r);
  noteIds(table, rows);
  return rows;
}
/** Rows of a store query (ordered / limited / filtered server-side). */
export async function queryRows(table: string, q: QueryRef): Promise<Row[]> {
  const snap = await q.get();
  const rows = snap.docs.map(s => rowOf(table, s)).filter((r): r is Row => !!r);
  noteIds(table, rows);
  return rows;
}
export async function getRow(table: string, id: unknown): Promise<Row | null> {
  if (id === null || id === undefined || id === '') return null;
  const db = await needDb();
  const s = await db.doc(`${table}/${String(id)}`).get();
  return s.exists ? rowOf(table, s) : null;
}
async function putRow(db: Db, table: string, row: Row) {
  await db.doc(`${table}/${String(row[keyOf(table)])}`).set(JSON.parse(JSON.stringify(row)) as Row);
}

// ---------- ids (A-M3): the page takes EVEN ids, the worker ODD ids ----------
// Disjoint sets, so a page write and a worker write never take the same id. n = the smallest even number above
// max(highest id in the collection — fresh read orderBy('id','desc').limit(1), the highest id this tab has seen,
// legacy meta/seq_<table>.next - 1 read only), skipping (n += 2) while <table>/<n> exists, under a short lease on
// locks/seq_<table> against a second tab. No meta/ writes (meta is owner-only). Lease not granted → DbFail 'busy'.
const TAB = `tab-${Math.random().toString(36).slice(2, 10)}`;
const LEASE_TRIES = 30; // ~7 s of retries: longer than the 5 s lease of another tab
export async function allocId(table: string): Promise<number> {
  const db = await needDb();
  const lock = db.doc(`locks/seq_${table}`);
  let got = false;
  for (let i = 0; i < LEASE_TRIES && !got; i++) {
    try { got = (await lock.acquire({ holder: TAB, ttlMs: 5000 })).acquired === true; } catch (e) {
      if (isDbFail(e) && (e.dbCode === 'invalid_argument' || e.dbCode === 'not_granted' || e.dbCode === 'revoked')) throw e;
      got = false; // a throwing acquire is retried, never treated as granted
    }
    if (!got) await sleep(100 + Math.random() * 250);
  }
  if (!got) throw new DbFail('दुसऱ्या टॅबमध्ये याच वेळी नोंद होत आहे. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.', 'db_busy', 'busy');
  const top = await db.collection(table).orderBy('id', 'desc').limit(1).get();
  let max = maxIdCache.get(table) || 0;
  for (const s of top.docs) { const v = Number(s.data()?.id ?? s.id); if (Number.isFinite(v) && v > max) max = v; }
  const legacy = Number((await db.doc(`meta/seq_${table}`).get()).data()?.next);
  if (Number.isFinite(legacy) && legacy - 1 > max) max = legacy - 1;
  let n = Math.floor(max) + 1;
  if (n % 2) n++;
  if (n < 2) n = 2;
  while ((await db.doc(`${table}/${n}`).get()).exists) n += 2;
  maxIdCache.set(table, Math.max(maxIdCache.get(table) || 0, n));
  return n;
}

// ---------- writes with the DB's triggers ----------
let actorId: string | null = null;
/** The member id written as activity.actor by triggers (set from /api/me). */
export const setActor = (id: string | null) => { actorId = id; };

export async function insertRow(table: string, data: Row): Promise<Row> {
  const db = await needDb();
  const row: Row = { ...defaults(table), ...data };
  const k = keyOf(table);
  if (NUMERIC_ID(table)) row.id = await allocId(table);
  else if (row[k] === undefined || row[k] === null || row[k] === '') throw new Error(`${table}: ${k} required`);
  await putRow(db, table, row);
  return row;
}

/** Apply a patch to one existing row, with the triggers: cases touch_case (updated_at + stage_changed activity),
 *  runs runs_keep_last_step (last_step / step_at). Returns the new row. */
export async function patchRow(table: string, old: Row, patch: Row): Promise<Row> {
  const db = await needDb();
  const next: Row = { ...old, ...patch, [keyOf(table)]: old[keyOf(table)] };
  if (table === 'cases') {
    next.updated_at = nowIso();
    if (next.stage !== old.stage)
      await insertRow('activity', { case_id: old.id, actor: actorId, action: 'stage_changed', detail: { from: old.stage, to: next.stage } });
  }
  if (table === 'runs') {
    const active = next.state === 'queued' || next.state === 'running';
    if (active && next.step != null && next.step !== old.step) next.last_step = next.step;
    else if (next.state === 'failed' && (old.state === 'queued' || old.state === 'running') && next.last_step == null && old.step != null) next.last_step = old.step;
    if (active && (next.step !== old.step || (next.state === 'running' && old.state !== 'running'))) next.step_at = nowIso();
  }
  await putRow(db, table, next);
  return next;
}
export async function deleteRow(table: string, row: Row) {
  const db = await needDb();
  await db.doc(`${table}/${String(row[keyOf(table)])}`).delete();
}

// ---------- gr_library from the GR index asset (meta/gr_library {asset}) + gr_files/<key> {store, ref, name} ----------
const GR_INDEX_READ = 'GR सूची उघडता आली नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.';
interface GrIdx { key: string; path?: string; folder?: string; topic?: string; file?: string; code?: string; date?: string; title?: string; url?: string }
let grIdx: Promise<GrIdx[]> | null = null;
export async function grIndex(): Promise<GrIdx[]> {
  if (!grIdx) {
    grIdx = (async () => {
      const db = await needDb();
      const asset = (await db.doc('meta/gr_library').get()).data()?.asset;
      if (typeof asset !== 'string' || !asset) return [];
      const r = await fetch(`/_blob/${asset}`);
      if (!r.ok) throw new Error(GR_INDEX_READ);
      const j = (await r.json()) as unknown;
      return Array.isArray(j) ? (j as GrIdx[]) : [];
    })();
    grIdx.catch(() => { grIdx = null; });
  }
  return grIdx;
}
const isoOf = (d: string | undefined) => {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(d || '');
  return m ? `${m[3]}-${m[2]}-${m[1]}` : /^\d{4}-\d{2}-\d{2}$/.test(d || '') ? d! : null;
};
export interface GrFile { store?: string; ref?: unknown; name?: string }
export async function grFiles(): Promise<Map<string, GrFile>> {
  const db = await needDb();
  const snap = await db.collection('gr_files').get();
  return new Map(snap.docs.map(s => [s.id, (s.data() || {}) as GrFile]));
}
/** storage_path of a gr_files entry: "asset:<id>" or "asset-parts:<n>" (ref = [ids]); null when nothing stored. */
export const grStoragePath = (f: GrFile | undefined) =>
  !f || !f.ref ? null : Array.isArray(f.ref) ? `asset-parts:${f.ref.length}` : `asset:${String(f.ref)}`;
async function grLibraryRows(): Promise<Row[]> {
  const db = await needDb();
  const [idx, files, own] = await Promise.all([grIndex(), grFiles(), db.collection('gr_library').get()]);
  const out = new Map<string, Row>();
  for (const g of idx) {
    const code = g.code || g.key;
    out.set(code, { code, key: g.key, path: g.path ?? null, file: g.file ?? null, date: isoOf(g.date), department: g.topic || null,
      title: g.title || g.file || null, source_url: g.url || null, storage_path: grStoragePath(files.get(g.key)), used_in_cases: [] });
  }
  for (const s of own.docs) { const r = rowOf('gr_library', s); if (r) out.set(String(r.code), { ...defaults('gr_library'), ...(out.get(String(r.code)) || {}), ...r }); }
  return [...out.values()];
}

// ---------- query builder ----------
type Pred = (r: Row) => boolean;
const num = (v: unknown) => (typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v)) ? Number(v) : NaN);
function same(a: unknown, b: unknown) {
  if (a === b) return true;
  if (a == null || b == null) return false;
  return String(a) === String(b);
}
function cmp(a: unknown, b: unknown): number {
  const x = num(a), y = num(b);
  if (!Number.isNaN(x) && !Number.isNaN(y)) return x - y;
  const s = String(a), t = String(b);
  return s < t ? -1 : s > t ? 1 : 0;
}
const parseVal = (v: string): unknown => (v === 'null' ? null : v === 'true' ? true : v === 'false' ? false : v);
function opPred(col: string, op: string, val: unknown): Pred {
  switch (op) {
    case 'eq': return r => same(r[col], val);
    case 'neq': return r => !same(r[col], val);
    case 'gt': return r => r[col] != null && cmp(r[col], val) > 0;
    case 'gte': return r => r[col] != null && cmp(r[col], val) >= 0;
    case 'lt': return r => r[col] != null && cmp(r[col], val) < 0;
    case 'lte': return r => r[col] != null && cmp(r[col], val) <= 0;
    case 'is': return r => (val === null ? r[col] == null : r[col] === val);
    case 'in': {
      const list = Array.isArray(val) ? val : String(val).replace(/^\(|\)$/g, '').split(',').map(s => parseVal(s.trim().replace(/^"|"$/g, '')));
      return r => list.some(v => same(r[col], v));
    }
    case 'like': case 'ilike': {
      const re = new RegExp(`^${String(val).replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/%/g, '.*')}$`, op === 'ilike' ? 'i' : '');
      return r => re.test(String(r[col] ?? ''));
    }
    case 'match': case 'imatch': {
      const re = new RegExp(String(val), op === 'imatch' ? 'i' : '');
      return r => re.test(String(r[col] ?? ''));
    }
    default: throw new Error(`filter ${op} not supported`);
  }
}
/** PostgREST text filter "col.op.value" ("not.col.op.value" not used by the app). */
function textPred(f: string): Pred {
  const m = /^([a-z_]+)\.(not\.)?([a-z]+)\.(.*)$/.exec(f.trim());
  if (!m) throw new Error(`filter ${f} not supported`);
  const p = opPred(m[1], m[3], m[3] === 'in' ? m[4] : parseVal(m[4].replace(/^"|"$/g, '')));
  return m[2] ? r => !p(r) : p;
}
function splitTop(s: string): string[] {
  const out: string[] = [];
  let depth = 0, cur = '';
  for (const ch of s) {
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (ch === ',' && depth === 0) { out.push(cur); cur = ''; } else cur += ch;
  }
  if (cur) out.push(cur);
  return out;
}

type Mode = 'select' | 'insert' | 'update' | 'upsert' | 'delete';
interface Order { col: string; asc: boolean; nullsFirst: boolean }
/** Tables whose limited reads go to the store (orderBy + limit + simple where), A-M4. */
const SERVER_LIMITED = new Set(['activity']);
const STORE_OP: Record<string, string> = { eq: '==', neq: '!=', gt: '>', gte: '>=', lt: '<', lte: '<=' };
/** Store value of a filter: numeric id columns as numbers (case_id stored as a JSON number). */
const storeVal = (col: string, v: unknown) => (/(^|_)id$/.test(col) && typeof v === 'string' && /^\d+$/.test(v) ? Number(v) : v);

class Query implements PromiseLike<Res> {
  private preds: Pred[] = [];
  private orders: Order[] = [];
  private lim: number | null = null;
  private from0 = 0;
  private cols: string[] | null = null;
  private countOpt: string | null = null;
  private head = false;
  private one: 'single' | 'maybe' | null = null;
  private returning = false;
  /** Simple filters the store can run (where); `opaque` = a filter it cannot (or / not / in / like …). */
  private storeWhere: [string, string, unknown][] = [];
  private opaque = false;
  constructor(private table: string, private mode: Mode = 'select', private payload: Row | Row[] | null = null) {}

  select(cols = '*', opt?: { count?: string; head?: boolean }) {
    if (this.mode !== 'select') this.returning = true;
    const c = cols.split(',').map(s => s.trim()).filter(Boolean);
    this.cols = c.includes('*') ? null : c;
    if (opt?.count) this.countOpt = opt.count;
    if (opt?.head) this.head = true;
    return this;
  }
  insert(v: Row | Row[]) { this.mode = 'insert'; this.payload = v; return this; }
  update(v: Row) { this.mode = 'update'; this.payload = v; return this; }
  upsert(v: Row | Row[]) { this.mode = 'upsert'; this.payload = v; return this; }
  delete() { this.mode = 'delete'; return this; }
  private add(p: Pred, store?: [string, string, unknown]) {
    this.preds.push(p);
    if (store && store[2] !== null && store[2] !== undefined) this.storeWhere.push(store); else this.opaque = true;
    return this;
  }
  private simple(c: string, op: string, v: unknown) { return this.add(opPred(c, op, v), [c, STORE_OP[op], storeVal(c, v)]); }
  eq(c: string, v: unknown) { return this.simple(c, 'eq', v); }
  neq(c: string, v: unknown) { return this.add(opPred(c, 'neq', v)); }
  gt(c: string, v: unknown) { return this.simple(c, 'gt', v); }
  gte(c: string, v: unknown) { return this.simple(c, 'gte', v); }
  lt(c: string, v: unknown) { return this.simple(c, 'lt', v); }
  lte(c: string, v: unknown) { return this.simple(c, 'lte', v); }
  is(c: string, v: unknown) { return this.add(opPred(c, 'is', v)); }
  in(c: string, v: unknown[]) { return this.add(opPred(c, 'in', v)); }
  like(c: string, v: string) { return this.add(opPred(c, 'like', v)); }
  ilike(c: string, v: string) { return this.add(opPred(c, 'ilike', v)); }
  match(o: Row) { for (const [k, v] of Object.entries(o)) this.eq(k, v); return this; }
  /** A select the store can window: activity, a limit, at most one order column, only simple filters. */
  private serverWindow(): boolean {
    // the store's limit is 1..1000: a larger window (e.g. Home's month counts) stays a full client-side read
    return this.mode === 'select' && SERVER_LIMITED.has(this.table) && this.lim !== null && this.from0 + this.lim <= 1000
      && !this.opaque && this.orders.length <= 1 && this.storeWhere.length <= 10;
  }
  private async storeRows(): Promise<Row[]> {
    const db = await needDb();
    let q: QueryRef = db.collection(this.table);
    for (const [c, op, v] of this.storeWhere) q = q.where(c, op, v);
    if (this.orders.length) q = q.orderBy(this.orders[0].col, this.orders[0].asc ? 'asc' : 'desc');
    q = q.limit(Math.max(1, this.from0 + (this.lim || 0)));
    return queryRows(this.table, q);
  }
  not(c: string, op: string, v: unknown) {
    const p = opPred(c, op, v);
    return this.add(r => !p(r));
  }
  filter(c: string, op: string, v: unknown) { return this.add(opPred(c, op, v)); }
  or(f: string) {
    const ps = splitTop(f).map(x => {
      const and = /^and\((.*)\)$/.exec(x.trim());
      if (and) { const qs = splitTop(and[1]).map(textPred); return (r: Row) => qs.every(q => q(r)); }
      return textPred(x);
    });
    return this.add(r => ps.some(p => p(r)));
  }
  order(col: string, o?: { ascending?: boolean; nullsFirst?: boolean }) {
    const asc = o?.ascending !== false;
    this.orders.push({ col, asc, nullsFirst: o?.nullsFirst ?? !asc });
    return this;
  }
  limit(n: number) { this.lim = n; return this; }
  range(a: number, b: number) { this.from0 = a; this.lim = b - a + 1; return this; }
  single() { this.one = 'single'; return this; }
  maybeSingle() { this.one = 'maybe'; return this; }
  abortSignal() { return this; }

  private sorted(rows: Row[]): Row[] {
    if (!this.orders.length) return rows;
    return [...rows].sort((a, b) => {
      for (const o of this.orders) {
        const x = a[o.col], y = b[o.col];
        if (x == null && y == null) continue;
        if (x == null) return o.nullsFirst ? -1 : 1;
        if (y == null) return o.nullsFirst ? 1 : -1;
        const c = cmp(x, y);
        if (c) return o.asc ? c : -c;
      }
      return 0;
    });
  }
  private project(r: Row): Row {
    return this.cols ? Object.fromEntries(this.cols.map(c => [c, r[c] === undefined ? null : r[c]])) : r;
  }
  private async run(): Promise<Res> {
    let rows: Row[] = [];
    let total: number | null = null;
    if (this.mode === 'select') {
      // client-side filters stay as a safety net after a server-side (windowed) fetch
      const all = (this.serverWindow() ? await this.storeRows() : await listRows(this.table)).filter(r => this.preds.every(p => p(r)));
      total = all.length;
      rows = this.sorted(all).slice(this.from0, this.lim === null ? undefined : this.from0 + this.lim);
    } else if (this.mode === 'insert') {
      for (const v of ([] as Row[]).concat(this.payload || [])) rows.push(await insertRow(this.table, v));
    } else if (this.mode === 'upsert') {
      const k = keyOf(this.table);
      for (const v of ([] as Row[]).concat(this.payload || [])) {
        const cur = v[k] != null ? await getRow(this.table, v[k]) : null;
        rows.push(cur ? await patchRow(this.table, cur, v) : await insertRow(this.table, v));
      }
    } else {
      const hit = this.sorted((await listRows(this.table)).filter(r => this.preds.every(p => p(r))));
      for (const r of hit) {
        if (this.mode === 'update') rows.push(await patchRow(this.table, r, (this.payload || {}) as Row));
        else { await deleteRow(this.table, r); rows.push(r); }
      }
    }
    const out = rows.map(r => this.project(r));
    const count = this.countOpt ? (total ?? out.length) : null;
    if (this.mode !== 'select' && !this.returning) return ok(null, count);
    if (this.one) {
      if (out.length === 1) return ok(out[0], count);
      if (!out.length && this.one === 'maybe') return ok(null, count);
      return { data: null, error: { code: 'PGRST116', message: 'JSON object requested, multiple (or no) rows returned' }, count, status: 406, statusText: 'Not Acceptable' };
    }
    return ok(this.head ? null : out, count);
  }
  then<A = Res, B = never>(onOk?: ((v: Res) => A | PromiseLike<A>) | null, onErr?: ((e: unknown) => B | PromiseLike<B>) | null): PromiseLike<A | B> {
    return this.run()
      .catch((e: unknown): Res => isDbFail(e)
        ? { data: null, error: { message: e.message, code: e.code }, count: null, status: e.dbCode === 'invalid_argument' ? 403 : 503, statusText: 'Error' }
        : { data: null, error: { message: e instanceof Error ? e.message : String(e) }, count: null, status: 500, statusText: 'Error' })
      .then(onOk, onErr);
  }
}
const ok = (data: unknown, count: number | null): Res => ({ data, error: null, count, status: 200, statusText: 'OK' });

// ---------- realtime over onSnapshot ----------
type Payload = { schema: string; table: string; eventType: 'INSERT' | 'UPDATE' | 'DELETE'; new: Row; old: Row; commit_timestamp: string; errors: null };
interface Handler { event: string; table: string; filter?: string; cb: (p: Payload) => void }

class Channel {
  private handlers: Handler[] = [];
  private unsubs: (() => void)[] = [];
  private dead = false;
  constructor(public topic: string) {}
  on(_type: string, cfg: { event?: string; table: string; filter?: string }, cb: (p: Payload) => void) {
    this.handlers.push({ event: cfg.event || '*', table: cfg.table, filter: cfg.filter, cb });
    return this;
  }
  subscribe(status?: (s: string, err?: Error) => void) {
    const tables = [...new Set(this.handlers.map(h => h.table))];
    let pending = tables.length;
    void needDb().then(
      db => {
        for (const table of tables) {
          let first = true;
          const known = new Map<string, Row>();
          // activity: only the newest 200 rows (a window — rows leaving it are not deletions), A-M4
          const windowed = SERVER_LIMITED.has(table);
          const src: QueryRef = windowed ? db.collection(table).orderBy('at', 'desc').limit(200) : db.collection(table);
          const un = src.onSnapshot(
            snap => {
              if (this.dead) return;
              if (first) {
                first = false;
                for (const d of snap.docs) { const r = rowOf(table, d); if (r) known.set(d.id, r); }
                if (--pending === 0) status?.('SUBSCRIBED');
                return;
              }
              for (const ch of snap.docChanges()) {
                if (windowed && ch.type === 'removed') { known.delete(ch.doc.id); continue; }
                const r = rowOf(table, ch.doc) || {};
                const old = known.get(ch.doc.id) || {};
                if (ch.type === 'removed') known.delete(ch.doc.id); else known.set(ch.doc.id, r);
                const ev = ch.type === 'added' ? (old && Object.keys(old).length ? 'UPDATE' : 'INSERT') : ch.type === 'modified' ? 'UPDATE' : 'DELETE';
                const p: Payload = { schema: 'public', table, eventType: ev, new: ev === 'DELETE' ? {} : r, old: ev === 'DELETE' ? r : old, commit_timestamp: nowIso(), errors: null };
                for (const h of this.handlers) {
                  if (h.table !== table || (h.event !== '*' && h.event !== ev)) continue;
                  if (h.filter && !textPred(h.filter.replace('=', '.'))(ev === 'DELETE' ? p.old : p.new)) continue;
                  h.cb(p);
                }
              }
            },
            e => status?.('CHANNEL_ERROR', new Error(e.message)),
          );
          this.unsubs.push(un);
        }
        if (!tables.length) status?.('SUBSCRIBED');
      },
      e => status?.('CHANNEL_ERROR', e instanceof Error ? e : new Error(String(e))),
    );
    return this;
  }
  unsubscribe() {
    this.dead = true;
    for (const u of this.unsubs.splice(0)) u();
    return Promise.resolve('ok');
  }
}

// ---------- auth: always the signed-in owner ----------
async function session() {
  const v = await viewer();
  return { access_token: 'artifact', refresh_token: '', token_type: 'bearer', expires_in: 3600, expires_at: Math.floor(Date.now() / 1000) + 3600,
    user: { id: v.id, email: v.email, aud: 'authenticated', role: 'authenticated', app_metadata: {}, user_metadata: { name: v.name }, created_at: '' } };
}
const auth = {
  getSession: async () => ({ data: { session: await session() }, error: null }),
  getUser: async () => ({ data: { user: (await session()).user }, error: null }),
  onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
  signOut: async () => ({ error: null }),
  signInWithOtp: async () => ({ data: {}, error: null }),
  verifyOtp: async () => ({ data: { session: await session(), user: (await session()).user }, error: null }),
};

let client: unknown = null;
/** The client object (typed loosely; supabase.ts casts it to SupabaseClient). */
export function artifactClient(): unknown {
  if (!client) {
    client = {
      from: (table: string) => new Query(table),
      channel: (name: string) => new Channel(name),
      removeChannel: (ch: Channel) => ch.unsubscribe(),
      removeAllChannels: () => Promise.resolve([]),
      auth,
    };
  }
  return client;
}
