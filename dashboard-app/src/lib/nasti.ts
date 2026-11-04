// Read / prefill the नस्ती अद्ययावत स्थिती page's own browser storage (public/nasti/index.html, same origin).
// Only key used by that page: `nasti_dash_v1`. We never touch `rows` or any key other than user / office / mine / seen,
// and we fill only EMPTY fields (the owner may have edited them inside the page). Nothing here goes to the server.
import type { Profile } from './types';

export const NASTI_KEY = 'nasti_dash_v1';

export interface NastiRow {
  compNo?: string; fileNo?: string; kind?: string; subject?: string; where?: string; holder?: string;
  since?: string; status?: string; due?: string; hearing?: string;
  [k: string]: unknown;
}
export interface NastiStore {
  rows?: NastiRow[];
  office?: string;
  mine?: string;
  user?: { n?: string; d?: string };
  seen?: boolean;
  [k: string]: unknown;
}

/** Parsed store, or null when absent / invalid / storage blocked. */
export function readNasti(): NastiStore | null {
  try {
    const raw = localStorage.getItem(NASTI_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    return o && typeof o === 'object' && !Array.isArray(o) ? (o as NastiStore) : null;
  } catch {
    return null;
  }
}

const str = (v: unknown) => (typeof v === 'string' ? v : '');
const empty = (v: unknown) => !str(v).trim();

/** Pure merge: user.n / user.d follow the profile (when set); office / mine only when empty; seen = true when user.n is set.
 *  `changed` false → nothing to write. A missing store becomes {rows: []} + the profile fields (as the page itself accepts). */
export function mergeProfile(store: NastiStore | null, p: Partial<Profile> | null | undefined): { next: NastiStore; changed: boolean } {
  const next: NastiStore = store ? { ...store } : { rows: [] };
  let changed = false;
  if (!p) return { next, changed };
  const user = { ...(next.user && typeof next.user === 'object' ? next.user : {}) };
  const put = (cur: unknown, val: unknown, set: (v: string) => void, always = false) => {
    const v = str(val).trim();
    if (v && (empty(cur) || (always && str(cur).trim() !== v))) { set(v); changed = true; }
  };
  // name / designation: the main app's profile is the one source (Abhi 04.11.2026: "ज्या गोष्टी आवश्यक आहे त्या करा" —
  // one name everywhere), so a changed profile updates the page; office / mine may also come from the page's own report
  // upload, so they are filled only when empty
  put(user.n, p.display_name, v => (user.n = v), true);
  put(user.d, p.designation, v => (user.d = v), true);
  put(next.office, p.office, v => (next.office = v));
  put(next.mine, p.mine, v => (next.mine = v));
  if (changed) next.user = user;
  if (!empty(user.n) && next.seen !== true) { next.seen = true; changed = true; }
  return { next, changed };
}

/** Write the profile into the नस्ती store (name / designation follow the profile; office / mine only when empty). Returns true when something was written. */
export function prefillNasti(p: Partial<Profile> | null | undefined): boolean {
  const cur = readNasti();
  // invalid JSON present → leave the page's data alone
  try {
    if (!cur && localStorage.getItem(NASTI_KEY)) return false;
  } catch {
    return false;
  }
  const { next, changed } = mergeProfile(cur, p);
  if (!changed) return false;
  try {
    localStorage.setItem(NASTI_KEY, JSON.stringify(next));
    return true;
  } catch {
    return false;
  }
}

/** नस्ती no. as compared: trimmed, inner spaces collapsed, case-insensitive. */
export const normNo = (s: string | null | undefined) => (s || '').trim().replace(/\s+/g, ' ').toLowerCase();

/** Row whose fileNo equals `no` (trimmed, case-insensitive). */
export function findRow(no: string | null | undefined, store: NastiStore | null = readNasti()): NastiRow | null {
  const k = normNo(no);
  if (!k || !store || !Array.isArray(store.rows)) return null;
  return store.rows.find(r => r && normNo(str(r.fileNo)) === k) || null;
}

/** Rows that have a fileNo (for the case page's datalist). */
export function nastiRows(store: NastiStore | null = readNasti()): NastiRow[] {
  return store && Array.isArray(store.rows) ? store.rows.filter(r => r && !empty(r.fileNo)) : [];
}

/** Whole days from `since` to now; null when not a date. */
export function daysSince(since: string | null | undefined, now = Date.now()): number | null {
  if (!since) return null;
  const t = Date.parse(since.length === 10 ? since + 'T00:00:00' : since);
  if (isNaN(t)) return null;
  return Math.max(0, Math.floor((now - t) / 86400000));
}
