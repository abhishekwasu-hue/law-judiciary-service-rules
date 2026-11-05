// Pure helpers of the speed fixes (audit 05.11.2026 P2/P4/P5, U2/U6). No imports: unit-tested with
// `node --test --experimental-strip-types dashboard-app/test/perf.test.mjs`.

/** What GET /api/public-config answers (also inlined by the Worker as <script type="application/json" id="pk-config">). */
export interface PublicConfig { configured: boolean; supabase_url: string; supabase_anon_key: string }

/** P2: the config the Worker inlined into index.html, or null (dev server, old Worker, bad JSON) → fetch /api/public-config. */
export function parseInlineConfig(text: string | null | undefined): PublicConfig | null {
  if (!text || !text.trim()) return null;
  try {
    const j = JSON.parse(text) as Partial<PublicConfig> | null;
    if (!j || typeof j !== 'object' || typeof j.configured !== 'boolean') return null;
    if (!j.configured) return { configured: false, supabase_url: '', supabase_anon_key: '' };
    if (typeof j.supabase_url !== 'string' || !/^https?:\/\//.test(j.supabase_url) || typeof j.supabase_anon_key !== 'string' || !j.supabase_anon_key) return null;
    return { configured: true, supabase_url: j.supabase_url, supabase_anon_key: j.supabase_anon_key };
  } catch {
    return null;
  }
}

/** P4: the runs columns the shared store needs (list badges, प्रतीक्षा-यादी, global bar, toasts). Not: instructions, log_url,
 *  grs_*, essential_points, edit_message / edit_result (read by the case page itself, useRuns). */
export const RUN_LIST_COLUMNS = 'id,case_id,state,step,kind,created_at,started_at,finished_at,dispatched_at,summary,warnings,last_step';
/** P4: activity columns Home needs. */
export const ACTIVITY_COLUMNS = 'id,case_id,action,detail,at';

/** A select that names a column the DB does not have yet (migration not applied) → retry with '*'. PostgREST: 42703 /
 *  PGRST204 / "column … does not exist". */
export function isMissingColumn(e: { code?: string | null; message?: string | null } | null | undefined): boolean {
  if (!e) return false;
  return e.code === '42703' || e.code === 'PGRST204' || /column .* does not exist|could not find the .* column/i.test(e.message || '');
}

/** Latest non-edit run of every case, from rows ordered newest first (logic unchanged from data.tsx). */
export function latestRunPerCase<R extends { case_id: number; kind?: string | null }>(rows: R[]): Map<number, R> {
  const m = new Map<number, R>();
  for (const x of rows) if (x.kind !== 'edit' && !m.has(x.case_id)) m.set(x.case_id, x);
  return m;
}

/** P5: rows shown in the प्रकरणे list — the first `shown`, plus how many more are behind "अधिक दाखवा (N)". */
export const PAGE_STEP = 50;
export function pageRows<T>(rows: T[], shown: number): { visible: T[]; more: number } {
  const n = Math.max(0, Math.min(rows.length, shown));
  return { visible: n === rows.length ? rows : rows.slice(0, n), more: rows.length - n };
}

/** U2: "आज करायचे" shows the first 5 rows; "सर्व N पाहा" opens the rest. */
export const TODO_TOP = 5;

/** U6: "1 मुद्दा तपासावा" / "N मुद्दे तपासावेत". */
export const pointsToCheck = (n: number) => (n === 1 ? '1 मुद्दा तपासावा' : `${n} मुद्दे तपासावेत`);
/** U6, run line: "तपासणीचा 1 मुद्दा … आहे … पाहावा" / "तपासणीचे N मुद्दे … आहेत … पाहावेत". */
export const studyPointsText = (n: number) =>
  n === 1
    ? 'तपासणीचा 1 मुद्दा अभ्यास-फाइलमध्ये (भाग 7 शेवटी) आहे — कृपया वापरण्यापूर्वी पाहावा.'
    : `तपासणीचे ${n} मुद्दे अभ्यास-फाइलमध्ये (भाग 7 शेवटी) आहेत — कृपया वापरण्यापूर्वी पाहावेत.`;

/** P2: which page chunk the current address needs first (started before config / login finish). */
export function routeChunk(pathname: string): 'home' | 'cases' | 'case' | null {
  if (pathname === '/' || pathname === '') return 'home';
  if (/^\/cases\/?$/.test(pathname)) return 'cases';
  if (/^\/cases\/\d+\/?$/.test(pathname)) return 'case';
  return null;
}

/** P3: bar widths (%) of the टप्पानिहाय दिवस bars; the longest = 100, any non-zero value at least 2 so it stays visible. */
export function barPercents(values: number[]): number[] {
  const max = Math.max(0, ...values);
  return values.map(v => (max > 0 && v > 0 ? Math.max(2, Math.round((v / max) * 100)) : 0));
}
