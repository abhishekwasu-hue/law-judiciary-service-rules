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
  c.cr_no ? `C R ${c.cr_no}/${c.cr_year ?? '—'}` : c.id ? `प्रकरण #${c.id} (C R PDF वरून येईल)` : 'नवीन प्रकरण';

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

/** "CR131_2026_Note_and_Letter.docx" → "C R 131/2026" (engine output names carry the C R). */
export function crFromFileName(name: string | null | undefined): string | null {
  const m = /^CR(\d+)_(\d{4})_/.exec(name || '');
  return m ? `C R ${m[1]}/${m[2]}` : null;
}
/** Case title for headings and lists: C R → C R from output file → प्रकरण #id. */
export function caseTitle(c: { id: number; cr_no: string | null; cr_year: number | null }, fileName?: string | null): string {
  return c.cr_no ? crLabel(c) : crFromFileName(fileName) || `प्रकरण #${c.id}`;
}
/** Subject line: subject from the PDF → summary of the latest finished run → hint. */
export function caseSubject(c: { subject: string | null }, runSummary?: string | null): string {
  return c.subject || runSummary || 'विषय PDF वरून येईल';
}
