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
export interface CollRef {
  doc(id?: string): DocRef;
  get(): Promise<QuerySnap>;
  onSnapshot(next: (s: QuerySnap) => void, err?: (e: DbErr) => void): () => void;
}
export interface Db { doc(path: string): DocRef; collection(path: string): CollRef }
export interface Assets {
  upload(blob: Blob, o?: { type?: string }): Promise<{ id: string; url: string; sizeBytes: number; contentType: string }>;
}
export interface Downloads { save(r: { filename: string; data: Blob | string | ArrayBuffer }): Promise<{ status: string }> }
export interface Mcp { callTool(server: string, tool: string, input?: unknown): Promise<{ payload?: unknown }> }
export interface User {
  me(): Promise<{ id: string | null; name: string; email: string | null; isOwner: boolean; canEdit: boolean }>;
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

/** The db namespace or an Error('db unavailable') (→ Marathi "माहिती …" text via humanError's generic path). */
export async function needDb(): Promise<Db> {
  const d = await cap('db');
  if (!d) throw new Error('db 503 unavailable');
  return d;
}

export const nowIso = () => new Date().toISOString();
export const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
