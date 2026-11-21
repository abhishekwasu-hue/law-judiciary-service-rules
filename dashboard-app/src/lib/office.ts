// कार्यालयीन काम: helpers shared by the task page (pages/OfficeWork.tsx) and its AI चॅट (components/OfficeChat.tsx).
import { api, uploadFile } from './api';
import type { OfficeOutputKey } from './constants';
import type { CaseFile, Run } from './types';

/** Uploads the source files (extra_doc) and the template, then starts the run. Returns the started run. */
export async function uploadAndRun(caseId: number, docs: File[], tpl: File[], instructions: string, outputs: OfficeOutputKey[], onStatus: (s: string) => void) {
  const all: [File, 'extra_doc' | 'template'][] = [...docs.map(f => [f, 'extra_doc'] as [File, 'extra_doc']), ...tpl.map(f => [f, 'template'] as [File, 'template'])];
  for (let i = 0; i < all.length; i++) {
    const [f, kind] = all[i];
    onStatus(`फाइल अपलोड (${i + 1}/${all.length}): ${f.name}`);
    await uploadFile(caseId, kind, f, pct => onStatus(`फाइल अपलोड (${i + 1}/${all.length}): ${f.name} — ${pct}%`));
  }
  onStatus('काम सुरू करत आहे…');
  return api<Run>('/api/run', { method: 'POST', body: { case_id: caseId, instructions, outputs } });
}

/** Newest version of each file name of the given kinds. */
export function newestByName(files: CaseFile[], kinds: string[]): CaseFile[] {
  const m = new Map<string, CaseFile>();
  for (const f of files) {
    if (!kinds.includes(f.kind)) continue;
    const k = `${f.kind}|${f.original_name}`;
    const cur = m.get(k);
    if (!cur || f.version > cur.version || (f.version === cur.version && f.id > cur.id)) m.set(k, f);
  }
  return [...m.values()].sort((a, b) => b.id - a.id);
}

/** First line of a chat instruction that names the files to change (read by the worker, tools/work_rules/office.md). */
export const OFFICE_TARGET_PREFIX = 'बदल करायच्या फाइल्स:';
export const withTargets = (text: string, targets: string[]) =>
  targets.length ? `${OFFICE_TARGET_PREFIX} ${targets.join(', ')}\n${text}` : text;
/** Splits a stored instruction back into its target files and the message (for the chat bubbles). */
export function splitTargets(instr: string | null | undefined): { targets: string[]; text: string } {
  const s = instr || '';
  if (!s.startsWith(OFFICE_TARGET_PREFIX)) return { targets: [], text: s };
  const nl = s.indexOf('\n');
  const head = nl < 0 ? s : s.slice(0, nl);
  return { targets: head.slice(OFFICE_TARGET_PREFIX.length).split(',').map(x => x.trim()).filter(Boolean), text: nl < 0 ? '' : s.slice(nl + 1) };
}
