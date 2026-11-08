// claude.ai artifact runtime access (artifact build only, VITE_BACKEND === 'artifact').
// Minimal local types of the capability namespaces the data layer uses (artifact-capabilities 0.2.96 contract:
// db.d.ts, assets.d.ts, downloads.d.ts, mcp.d.ts, user.d.ts). No top-level side effects: the module is tree-shaken
// out of the normal build.

export interface DocSnap { id: string; exists: boolean; data(): Record<string, unknown> | undefined }
export interface DocChange { type: 'added' | 'modified' | 'removed'; doc: DocSnap }
export interface QuerySnap { docs: DocSnap[]; docChanges(): DocChange[]; metadata?: { fromCache: boolean } }
export interface DbErr { code: string; message: string }
export interface DocRef {
  id: string;
  get(): Promise<DocSnap>;
  set(data: Record<string, unknown>): Promise<void>;
  update(data: Record<string, unknown>): Promise<void>;
  delete(): Promise<void>;
  acquire(o: { holder: string; ttlMs?: number }): Promise<{ acquired: boolean; expiresAt?: string }>;
  onSnapshot(next: (s: DocSnap) => void, err?: (e: DbErr) => void): () => void;
}
export interface QueryRef {
  where(field: string, op: string, value: unknown): QueryRef;
  orderBy(field: string, dir?: 'asc' | 'desc'): QueryRef;
  limit(n: number): QueryRef;
  get(): Promise<QuerySnap>;
  onSnapshot(next: (s: QuerySnap) => void, err?: (e: DbErr) => void): () => void;
}
export interface CollRef extends QueryRef { doc(id?: string): DocRef }
export interface Db { doc(path: string): DocRef; collection(path: string): CollRef }
export interface Assets {
  upload(blob: Blob, o?: { type?: string }): Promise<{ id: string; url: string; sizeBytes: number; contentType: string }>;
}
export interface Downloads { save(r: { filename: string; data: Blob | string | ArrayBuffer }): Promise<{ status: string }> }
export interface McpErr { code?: string; message?: string; retryable?: boolean }
export interface Mcp { callTool(server: string, tool: string, input?: unknown): Promise<{ payload?: unknown }> }
export interface User {
  me(): Promise<{ id: string | null; name: string; email: string | null; isOwner: boolean; canEdit: boolean }>;
  isOwner?(): Promise<boolean>;
  can?(capability: string): Promise<boolean | null>;
}
interface CapMap { db: Db; assets: Assets; downloads: Downloads; mcp: Mcp; user: User }

const caps = new Map<string, Promise<unknown>>();
/** window.claude.use(name) once per name; null when the view cannot run it (or no window.claude at all). */
export function cap<K extends keyof CapMap>(name: K): Promise<CapMap[K] | null> {
  let p = caps.get(name);
  if (!p) {
    const w = typeof window !== 'undefined' ? (window as unknown as { claude?: { use?: (n: string) => Promise<unknown> } }).claude : undefined;
    p = w && typeof w.use === 'function' ? w.use(name).catch(() => null) : Promise.resolve(null);
    caps.set(name, p);
  }
  return p as Promise<CapMap[K] | null>;
}

// ---------- db errors → Marathi (A-M5, E-F9) ----------
/** The data store cannot run in this view at all (page not opened from its own link / capability not granted). */
export const NO_DB_TEXT = 'या दृश्यात माहिती-साठा उपलब्ध नाही. कृपया हे पान त्याच्या मूळ दुव्यावरून (शेअर केलेल्या लिंकवरून) उघडावे, ही विनंती.';
const DB_TEXT: Record<string, string> = {
  invalid_argument: 'या पानावरील माहिती बदलण्याची आपल्याला परवानगी नाही; आपल्याला फक्त पाहण्याची परवानगी आहे. आवश्यक असल्यास कृपया मालकांना कळवावे, ही विनंती.',
  quota_exceeded: 'या पानाच्या माहिती-साठ्याची मर्यादा पूर्ण झाली आहे; नवी नोंद जतन झाली नाही. कृपया मालकांना कळवावे, ही विनंती.',
  resource_exhausted: 'एकाच वेळी खूप विनंत्या झाल्या. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.',
  unavailable: 'माहिती-साठा सध्या उपलब्ध नाही (तात्पुरती अडचण). कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.',
  revoked: 'या पानाची परवानगी बदलली आहे. कृपया पान पुन्हा उघडावे, ही विनंती.',
  not_granted: NO_DB_TEXT,
  capability_disabled: NO_DB_TEXT,
  capability_removed: NO_DB_TEXT,
  busy: 'दुसऱ्या टॅबमध्ये याच वेळी नोंद होत आहे. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.',
};
const DB_READ_BAD = 'माहिती वाचता आली नाही (तांत्रिक अडचण). कृपया पुन्हा प्रयत्न करावा; अडचण राहिल्यास मालकांना कळवावे, ही विनंती.';
/** Normalised store code: transform_error → invalid_argument, unknown → unavailable (db.d.ts rules). */
export function dbCodeOf(code: unknown): string {
  const c = typeof code === 'string' ? code : '';
  if (c === 'transform_error') return 'invalid_argument';
  return c in DB_TEXT ? c : 'unavailable';
}
/** Marathi text of a db error code; invalid_argument on a read is a page bug, not "read-only". */
export function dbText(code: unknown, write = true): string {
  const c = dbCodeOf(code);
  return c === 'invalid_argument' && !write ? DB_READ_BAD : DB_TEXT[c];
}
/** A db rejection as an Error: `message` Marathi, `code` "db_<code>", `dbCode` the store code. */
export class DbFail extends Error {
  constructor(message: string, public code: string, public dbCode: string) {
    super(message);
  }
}
export function dbFail(e: unknown, write: boolean): unknown {
  if (e instanceof DbFail) return e;
  const code = (e as { code?: unknown } | null)?.code;
  if (e instanceof TypeError || (typeof code !== 'string' && e instanceof Error)) return e; // our own bug, not the store
  const c = dbCodeOf(code);
  return new DbFail(dbText(c, write), `db_${c}`, c);
}
export const isDbFail = (e: unknown): e is DbFail => e instanceof DbFail;

const wrapP = <T>(p: Promise<T>, write: boolean): Promise<T> => p.catch((e: unknown) => { throw dbFail(e, write); });
const wrapErr = (err: ((e: DbErr) => void) | undefined) => (e: DbErr) => {
  const c = dbCodeOf(e?.code);
  err?.({ code: `db_${c}`, message: dbText(c, false) });
};
function wrapDoc(d: DocRef): DocRef {
  return {
    id: d.id,
    get: () => wrapP(d.get(), false),
    set: x => wrapP(d.set(x), true),
    update: x => wrapP(d.update(x), true),
    delete: () => wrapP(d.delete(), true),
    acquire: o => wrapP(d.acquire(o), true),
    onSnapshot: (next, err) => d.onSnapshot(next, wrapErr(err)),
  };
}
function wrapQuery(q: QueryRef): QueryRef {
  return {
    where: (f, op, v) => wrapQuery(q.where(f, op, v)),
    orderBy: (f, dir) => wrapQuery(q.orderBy(f, dir)),
    limit: n => wrapQuery(q.limit(n)),
    get: () => wrapP(q.get(), false),
    onSnapshot: (next, err) => q.onSnapshot(next, wrapErr(err)),
  };
}
function wrapDb(db: Db): Db {
  return {
    doc: p => wrapDoc(db.doc(p)),
    collection: p => {
      const c = db.collection(p);
      return { ...wrapQuery(c), doc: (id?: string) => wrapDoc(c.doc(id)) };
    },
  };
}
let wrapped: { raw: Db; db: Db } | null = null;
/** The db namespace with every rejection mapped to a Marathi DbFail; no db in this view → DbFail NO_DB_TEXT. */
export async function needDb(): Promise<Db> {
  const d = await cap('db');
  if (!d) throw new DbFail(NO_DB_TEXT, 'db_not_granted', 'not_granted');
  if (!wrapped || wrapped.raw !== d) wrapped = { raw: d, db: wrapDb(d) };
  return wrapped.db;
}

export const nowIso = () => new Date().toISOString();
export const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
