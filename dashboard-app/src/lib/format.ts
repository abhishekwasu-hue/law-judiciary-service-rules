import { STALE_REASON } from './constants';

// ---------- who is viewing (owner-only technical text, BRIEF / UI audit X2) ----------
// DataProvider (lib/data.tsx) sets this from useAuth().me on every render, so helpers called without an explicit
// `isOwner` (humanError, cleanReason, budgetReachedText …) already know the viewer. Before login: not the owner.
let viewerIsOwner = false;
export function setViewerIsOwner(v: boolean) {
  viewerIsOwner = !!v;
}
export const viewerOwner = () => viewerIsOwner;

/** Text already meant for the user (Devanagari, no English sentence / JSON / code). */
export const looksMarathi = (m: string) => /[ऀ-ॿ]/.test(m) && !/[{}[\]]|\b[a-z]+ [a-z]+ [a-z]+\b/i.test(m);
/** Developer words that staff must not see (migration numbers, services, tokens, deploy …). */
export const DEV_WORDS = /migration|supabase|github|token|worker|deploy|cloudflare|anthropic|claude|\bapp\b|इंजिन|रीलोड|screenshot|\bSettings\b|\bverify\b|\blint\b|\bstep\b/i;
/** Staff text for any failure whose real reason is technical (the owner sees the raw reason as well). */
export const RUN_FAIL_TEXT = "प्रक्रिया पूर्ण होऊ शकली नाही (तांत्रिक कारण). कृपया 'पुन्हा तयार करा' वापरावे; अडचण राहिल्यास मालकांना कळवावे.";
export const RUN_START_FAIL_TEXT = "प्रक्रिया सुरू होऊ शकली नाही (तांत्रिक कारण). कृपया 'पुन्हा तयार करा' वापरावे; अडचण राहिल्यास मालकांना कळवावे.";
export const OWNER_DISPATCH_TEXT = "GitHub जोडणी अयशस्वी. कृपया सेटिंग्जमधील GitHub token तपासून 'पुन्हा तयार करा' वापरावे.";
export const TECH_TROUBLE_TEXT = 'तांत्रिक अडचण — कृपया मालकांना कळवावे, ही विनंती.';
/** Owner-only suffix with the raw technical text (empty for staff or when there is nothing extra to say). */
export const ownerDetail = (raw: string | null | undefined, isOwner = viewerIsOwner) => {
  const t = String(raw ?? '').trim();
  return isOwner && t ? ` (तांत्रिक कारण: ${t.slice(0, 300)})` : '';
};

const MONTHS = ['जाने', 'फेब्रु', 'मार्च', 'एप्रि', 'मे', 'जून', 'जुलै', 'ऑग', 'सप्टें', 'ऑक्टो', 'नोव्हें', 'डिसें'];
const pad = (n: number) => String(n).padStart(2, '0');

/** dd.mm.yyyy */
export function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v.length === 10 ? v + 'T00:00:00' : v);
  if (isNaN(d.getTime())) return v;
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}
export function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (isNaN(d.getTime())) return v;
  return `${fmtDate(v)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
export const monthLabel = (y: number, m: number) => `${MONTHS[m]} ${String(y).slice(2)}`;

export function isoOf(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
export const todayISO = () => isoOf(new Date());
export function addDaysISO(iso: string, n: number): string {
  const d = new Date(iso + 'T00:00:00');
  d.setDate(d.getDate() + n);
  return isoOf(d);
}
export function daysBetween(a: string, b: string): number {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 86400000);
}
export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
export const crLabel = (c: { id?: number; cr_no: string | null; cr_year: number | null }) =>
  c.cr_no ? `C R ${c.cr_no}/${c.cr_year ?? '—'}` : c.id ? `प्रकरण क्र. ${c.id}` : 'नवीन प्रकरण';

/** Readable text for unknown jsonb (string | object | array). Never HTML. */
export function textOf(v: unknown): string {
  if (v == null) return '';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  if (Array.isArray(v)) return v.map(textOf).join(', ');
  if (typeof v === 'object')
    return Object.entries(v as Record<string, unknown>)
      .filter(([, x]) => x != null && x !== '')
      .map(([k, x]) => `${k}: ${textOf(x)}`)
      .join(' • ');
  return String(v);
}
export const asArray = (v: unknown): unknown[] => (Array.isArray(v) ? v : v == null ? [] : [v]);

/** Failure reason of a run (runs.step of a failed run) for display (UI audit X2).
 *  Old rows start with "status.json state = 'failed': " (engine before 02.11.2026); old dispatch failures hold raw GitHub
 *  text. Marathi reasons without developer words are shown as they are; anything technical (English engine text such as
 *  "Claude step exited 1", "verify FAIL …", GitHub / token / migration words) → staff see RUN_FAIL_TEXT, the owner sees it
 *  plus the raw reason. `isOwner` defaults to the current viewer (setViewerIsOwner). */
export function cleanReason(s: string | null | undefined, isOwner = viewerIsOwner): string {
  const t = String(s ?? '').replace(/^status\.json state = '?\w+'?:\s*/, '').trim();
  if (!t) return '';
  if (/^dispatch \d+/.test(t) || /^GitHub जोडणी अयशस्वी/.test(t) || t === RUN_START_FAIL_TEXT)
    return isOwner ? OWNER_DISPATCH_TEXT + (/^dispatch \d+/.test(t) ? ownerDetail(t, true) : '') : RUN_START_FAIL_TEXT;
  if (/^वेळ संपली — पुन्हा तयार करा$/.test(t)) return STALE_REASON; // Worker text before 04.11.2026
  if (/^इंजिन अयशस्वी — पुन्हा तयार करा$/.test(t)) return RUN_FAIL_TEXT; // Worker text before 04.11.2026
  if (looksMarathi(t) && !DEV_WORDS.test(t)) return t;
  if (t === RUN_FAIL_TEXT) return t;
  return RUN_FAIL_TEXT + ownerDetail(t, isOwner);
}
/** Live step text of a run still waiting / running: Marathi engine steps as they are; the Worker's old monthly-limit text
 *  in the new wording; technical text hidden from staff (the owner sees it). */
export function cleanStep(s: string | null | undefined, isOwner = viewerIsOwner): string {
  const t = String(s ?? '').trim();
  if (!t) return '';
  if (/^मासिक खर्च-मर्यादा गाठली/.test(t)) return MONTHLY_LIMIT_WAIT_TEXT;
  if (looksMarathi(t) && !DEV_WORDS.test(t)) return t;
  return isOwner ? t : '';
}
/** = cloudflare/worker.js BUDGET_WAIT (the step of a queued run held by the monthly limit). */
export const MONTHLY_LIMIT_WAIT_TEXT = 'मासिक खर्च-मर्यादा पूर्ण झाली आहे. मालकांनी सेटिंग्जमध्ये मर्यादा वाढवल्यावर प्रक्रिया आपोआप सुरू होईल.';

/** Run warnings that mean the outputs were NOT fully checked (engine contract 02.11.2026) — shown in a red card. */
export const CRITICAL_WARNING_PREFIXES = ['पडताळणी अपूर्ण — ', 'अंतिम पडताळणी (Opus) मान्यता नाही — '];
export const isCriticalWarning = (w: string) => CRITICAL_WARNING_PREFIXES.some(p => w.trim().startsWith(p.trim()));
/** Warning texts of a run (model-routing lines "मॉडेल:" excluded). */
export function runWarningTexts(warnings: unknown): string[] {
  return asArray(warnings).map(textOf).map(x => x.trim()).filter(x => x && !x.startsWith('मॉडेल:'));
}
export const criticalWarnings = (warnings: unknown) => runWarningTexts(warnings).filter(isCriticalWarning);
/** Owner-only run lines (model routing, cost, AI provider) — same rule as tools/study_warnings.py OWNER_ONLY_PREFIXES. */
export const OWNER_ONLY_PREFIXES = ['मॉडेल:', 'खर्च', 'मुख्य AI', 'राखीव AI'];
export const isOwnerOnlyLine = (w: string) => OWNER_ONLY_PREFIXES.some(p => w.trim().startsWith(p));
/** The warnings the engine writes into the Study (end of भाग 7) at finish (Abhi 03.11.2026: "हे इशारे नोटिंग मध्ये नको"):
 *  every run warning except the owner-only lines, whitespace-normalised, duplicates once (tools/study_warnings.study_lines). */
export function studyWarningTexts(warnings: unknown): string[] {
  const out: string[] = [];
  for (const w of asArray(warnings).map(textOf)) {
    const t = w.replace(/\s+/g, ' ').trim();
    if (t && !isOwnerOnlyLine(t) && !out.includes(t)) out.push(t);
  }
  return out;
}

/** "CR131_2026_Note_and_Letter.docx" → "C R 131/2026" (engine output names carry the C R). */
export function crFromFileName(name: string | null | undefined): string | null {
  const m = /^CR(\d+)_(\d{4})_/.exec(name || '');
  return m ? `C R ${m[1]}/${m[2]}` : null;
}
/** Case title for headings and lists: C R → C R from output file → प्रकरण क्र. id. */
export function caseTitle(c: { id: number; cr_no: string | null; cr_year: number | null }, fileName?: string | null): string {
  return c.cr_no ? crLabel(c) : crFromFileName(fileName) || `प्रकरण क्र. ${c.id}`;
}
/** Subject line: subject from the PDF → summary of the latest finished run → hint. */
export function caseSubject(c: { subject: string | null }, runSummary?: string | null): string {
  return c.subject || runSummary || 'विषय PDF वरून येईल';
}
