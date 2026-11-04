// "कोणते मसुदे हवेत?" (C28) — deterministic pre-ticks from the case's files and runs (no AI). The user can change them.
// Priority (contract): approval > reply > court_notice > reminder > previous selection > letter.
import { DRAFT_KEYS, DRAFT_LABEL, type DraftKey } from './constants';

export interface FileLike { kind: string; created_at?: string | null }
export interface RunLike { state: string; created_at: string; outputs?: string[] | null; letter_needed?: boolean | null }
export interface Suggestion { keys: DraftKey[]; reason: string }

const ordered = (v: readonly string[]): DraftKey[] => DRAFT_KEYS.filter(k => v.includes(k));

/** runs: newest first (as useRuns gives them). Files without created_at (not uploaded yet) count as new. */
/** workType (C33): a court case (न्यायालयीन प्रकरणे) without an earlier run pre-ticks parawise + letter, like a court notice. */
export function suggestDrafts(files: FileLike[], runs: RunLike[] | null | undefined, workType?: string | null): Suggestion {
  const list = runs ?? [];
  const last = list[0];
  const since = (f: FileLike) => !last || !f.created_at || f.created_at > last.created_at;
  const newOf = (kind: string) => files.some(f => f.kind === kind && since(f));
  if (newOf('approval')) return { keys: ['gr'], reason: 'मान्यता प्राप्त' };
  if (newOf('reply')) return { keys: [], reason: 'उत्तर प्राप्त — नस्ती वित्त/सा.प्र.वि. कडे' };
  if (!list.length && files.some(f => f.kind === 'court_notice')) return { keys: ['letter', 'parawise'], reason: 'न्यायालयीन नोटीस' };
  if (!list.length && workType === 'court') return { keys: ['letter', 'parawise'], reason: 'न्यायालयीन प्रकरण' };
  if (last && last.state === 'done') {
    const madeLetter = Array.isArray(last.outputs) ? last.outputs.includes('letter') : last.letter_needed === true;
    if (madeLetter) return { keys: ['reminder'], reason: 'मागील प्रक्रियेत पत्र; उत्तर अप्राप्त' };
  }
  const prev = list.find(r => Array.isArray(r.outputs));
  if (last && prev && Array.isArray(prev.outputs)) return { keys: ordered(prev.outputs), reason: 'मागील निवड' };
  return { keys: ['letter'], reason: list.length ? 'नेहमीप्रमाणे' : 'पहिली प्रक्रिया' };
}

export const draftLabels = (keys: readonly DraftKey[]) => (keys.length ? keys.map(k => DRAFT_LABEL[k]).join(', ') : 'फक्त नोंद');
export const sameDrafts = (a: readonly DraftKey[], b: readonly DraftKey[]) => a.length === b.length && a.every((k, i) => k === b[i]);

/** Estimate: base = typical run (time/cost of earlier runs, which made the note + one letter); each further draft adds a
 *  fixed small amount. Numbers are estimates only. */
export const EXTRA_DRAFT_MIN = 2;
export const EXTRA_DRAFT_USD = 0.15;
export function draftEstimate(keys: readonly DraftKey[], baseSec: number, baseUsd: number) {
  const extra = Math.max(0, keys.length - 1);
  return { min: Math.max(1, Math.round(baseSec / 60 + extra * EXTRA_DRAFT_MIN)), usd: baseUsd + extra * EXTRA_DRAFT_USD };
}
