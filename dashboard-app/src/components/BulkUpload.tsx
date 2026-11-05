// Bulk upload (C33, Abhi 04.11.2026: "किमान पाच प्रस्ताव एका वेळेला अपलोड … काम मात्र … वन बाय वन"): up to 10 proposals,
// one box (= one case) each. 04.11.2026 (Abhi: "एकाच प्रस्तावाच्या अनेक पीडीएफ वर्ड फाईल असू शकतात … जेवढंही अपलोड होईल ते
// त्या एका प्रस्तावाशी संबंधित"): a box holds its main proposal PDF plus any other files of THAT proposal (PDF / Word /
// image, each with its type); several PDFs are never split into several proposals automatically. Per box: work category (bulk setter "सर्वांना"), drafts (compact, default पत्र; court → पत्र +
// परिच्छेदनिहाय उत्तर), optional instruction. "रांगेत टाका (N)": for every row in turn → POST /api/cases (work_type, desk;
// C R and subject are filled by the engine from the निर्देशपत्र) → upload → POST /api/run. The Worker runs them in FIFO order (up to max_parallel_runs at once)
// ({queued: true, position}). A failed row keeps what was done (case / upload) and is retried from there.
import { useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api, budgetReachedText, getSpend, humanError, spendBlocked, uploadFile, type RunStart } from '../lib/api';
import { useAuth } from '../lib/auth';
import { DEFAULT_DESK, DEFAULT_WORK_TYPE, DESKS, INPUT_KINDS, INPUT_KIND_LABEL, WORK_TYPES, type DraftKey, type InputKind, type WorkType } from '../lib/constants';
import { suggestDrafts } from '../lib/drafts';
import { fmtBytes } from '../lib/format';
import { guessSubject } from '../lib/pdf';
import { useLatestRuns } from '../lib/data';
import { useRunsShownHere } from './Layout';
import type { Case } from '../lib/types';
import { CompactDraftPicker } from './DraftPicker';
import { RunStateBadge } from './RunProgress';
import { Progress, Spinner } from './ui';
import { useToast } from './Toast';

export const BULK_MAX = 10;
const MAX_BYTES = 50 * 1024 * 1024;
const isPdf = (f: File) => f.type === 'application/pdf' || /\.pdf$/i.test(f.name);
/** Default drafts of a category (same rule as suggestDrafts for a new court case). */
export const draftsForWork = (w: string): DraftKey[] => (w === 'court' ? ['letter', 'parawise'] : ['letter']);
const EXTRA_KINDS = INPUT_KINDS.filter(k => k !== 'proposal');
const EXTRA_ACCEPT = '.pdf,.doc,.docx,.jpg,.jpeg,.png';
interface Extra { file: File; kind: InputKind }
/** Default drafts of a box: from its other files' types (reply / approval / court notice), as the single upload does. */
const defaultDrafts = (r: { work: WorkType; extras: Extra[] }): DraftKey[] =>
  r.extras.length ? suggestDrafts(r.extras.map(x => ({ kind: x.kind })), [], r.work).keys : draftsForWork(r.work);

/** Words the staff should not see (owner-only: GitHub / token / Supabase / Worker / migration …, BRIEF OWNER-ONLY). */
const TECH = /GitHub|token|Supabase|Worker|migration|deploy|API|JSON|सर्व्हर|सेटिंग्ज/i;
export const STAFF_TECH = 'तांत्रिक अडचण — कृपया मालकांना कळवावे.';
/** Error text for this user: the owner sees the technical text, staff a respectful Marathi line (N5). */
export function userError(x: unknown, isOwner: boolean): string {
  if (x instanceof ApiError && x.message === 'monthly_budget_reached' && !isOwner) return 'या महिन्याची खर्च-मर्यादा संपली आहे. कृपया मालकांना कळवावे.';
  if (x instanceof ApiError && x.message === 'run_active') return 'या प्रकरणाची प्रक्रिया आधीच चालू आहे. ती पूर्ण होईपर्यंत कृपया प्रतीक्षा करावी.';
  const m = humanError(x);
  if (isOwner) return m;
  if ((x instanceof ApiError && x.message === 'dispatch_failed') || TECH.test(m) || /[A-Za-z]{5,}/.test(m.replace(/\b(PDF|Word|MB)\b/g, ''))) return STAFF_TECH;
  return m;
}
/** Text after /api/run (glossary: प्रक्रिया, प्रतीक्षेत). The migration note is owner-only. */
export function startText(r: RunStart, isOwner: boolean): string {
  const base = r.queued
    ? `प्रतीक्षेत — क्रमांक ${Number(r.position) || '?'}. आधीच्या प्रक्रियांपैकी एक पूर्ण झाल्यावर ही प्रक्रिया क्रमाने आपोआप सुरू होईल.`
    : 'प्रक्रिया सुरू झाली.';
  return r.outputs_dropped && isOwner ? `${base} मसुदे-निवड लागू झाली नाही (migration 0008 बाकी).` : base;
}

type St = 'wait' | 'case' | 'up' | 'run' | 'queued' | 'started' | 'err';
interface Row {
  key: number; file: File; extras: Extra[]; work: WorkType; drafts: DraftKey[] | null; // null = default of the category
  instr: string; showInstr: boolean; showWork: boolean; subject: string;
  st: St; pct: number; caseId: number | null; uploaded: number; msg: string; // uploaded = files done (main first)
}

const ST_TEXT: Record<St, string> = {
  wait: 'प्रतीक्षा', case: 'प्रकरण नोंदवत आहे…', up: 'अपलोड', run: 'प्रक्रिया सुरू करत आहे…', queued: '', started: '', err: '',
};

export default function BulkUpload({ overBudget }: { overBudget: boolean }) {
  const toast = useToast();
  const isOwner = useAuth().me?.role === 'owner';
  const latestRuns = useLatestRuns();
  const [rows, setRows] = useState<Row[]>([]);
  useRunsShownHere(rows.map(r => r.caseId)); // U9: each box shows its run — not again in the global bar
  const [bulkWork, setBulkWork] = useState<WorkType>(DEFAULT_WORK_TYPE);
  const [desk, setDesk] = useState<string>(DEFAULT_DESK);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const keyRef = useRef(1);
  const inputRef = useRef<HTMLInputElement>(null);
  const rowsRef = useRef<Row[]>([]);
  rowsRef.current = rows;
  const patch = (key: number, p: Partial<Row>) => setRows(s => s.map(r => (r.key === key ? { ...r, ...p } : r)));

  // "+ नवीन प्रस्ताव": the chosen files form ONE proposal — the first PDF is the main proposal, every other file is an
  // other file of the same proposal (type "इतर", changeable)
  function addProposal(files: File[]) {
    const ok = files.filter(f => f.size <= MAX_BYTES);
    if (ok.length < files.length) toast('50 MB पेक्षा मोठ्या फाइल वगळल्या आहेत.', 'err');
    const main = ok.find(isPdf);
    if (!main) return ok.length ? toast('मुख्य प्रस्ताव PDF स्वरूपात असावा. कृपया प्रस्तावाचा PDF निवडावा (फोटो / Word असल्यास आधी PDF करावा).', 'err') : undefined;
    if (rowsRef.current.length >= BULK_MAX) return toast(`एका वेळी कमाल ${BULK_MAX} प्रस्ताव पाठविता येतात.`, 'err');
    const extras = ok.filter(f => f !== main && /\.(pdf|docx?|jpe?g|png)$/i.test(f.name)).map(file => ({ file, kind: 'extra_doc' as InputKind }));
    if (extras.length) toast(`“${main.name}” हा मुख्य प्रस्ताव; उरलेल्या ${extras.length} फाइल याच प्रस्तावाच्या इतर फाइल म्हणून जोडल्या. कृपया त्यांचा प्रकार तपासावा.`, 'info');
    const fresh: Row = {
      key: keyRef.current++, file: main, extras, work: bulkWork, drafts: null, instr: '', showInstr: false, showWork: false, subject: '',
      st: 'wait', pct: 0, caseId: null, uploaded: 0, msg: '',
    };
    setRows(s => [...s, fresh]);
    void guessSubject(main).then(sub => sub && patch(fresh.key, { subject: sub }), () => undefined);
  }
  function addExtras(key: number, files: File[]) {
    const ok = files.filter(f => f.size <= MAX_BYTES && /\.(pdf|docx?|jpe?g|png)$/i.test(f.name));
    if (ok.length < files.length) toast('50 MB पेक्षा मोठ्या / वेगळ्या प्रकारच्या फाइल वगळल्या आहेत.', 'err');
    setRows(s => s.map(r => (r.key === key ? { ...r, extras: [...r.extras, ...ok.map(file => ({ file, kind: 'extra_doc' as InputKind }))] } : r)));
  }
  const setAll = (w: WorkType) => {
    setBulkWork(w);
    setRows(s => s.map(r => (r.st === 'wait' || r.st === 'err' ? { ...r, work: w } : r)));
  };
  const todo = rows.filter(r => r.st === 'wait' || r.st === 'err');
  const sent = rows.filter(r => r.st === 'queued' || r.st === 'started');

  async function go() {
    if (!todo.length) return;
    setBusy(true);
    try {
      const sp = await getSpend();
      if (spendBlocked(sp)) { toast(isOwner ? budgetReachedText(sp.limit_usd) : 'या महिन्याची खर्च-मर्यादा संपली आहे. कृपया मालकांना कळवावे.', 'err'); setBusy(false); return; }
    } catch { /* the Worker still enforces the limit on /api/run */ }
    let stop = '';
    for (const r0 of todo.map(r => r.key)) {
      const r = rowsRef.current.find(x => x.key === r0);
      if (!r) continue;
      if (stop) { patch(r.key, { st: 'err', msg: stop }); continue; }
      let caseId = r.caseId;
      try {
        if (!caseId) {
          patch(r.key, { st: 'case', msg: '' });
          const body: Record<string, unknown> = { work_type: r.work, desk, priority: 'सामान्य' };
          if (r.subject) body.subject = r.subject;
          const c = await api<Case>('/api/cases', { body });
          caseId = c.id;
          patch(r.key, { caseId });
        }
        // main PDF first, then this proposal's other files; a retry continues after the last file that was uploaded
        const files: Extra[] = [{ file: r.file, kind: 'proposal' }, ...r.extras];
        for (let i = r.uploaded; i < files.length; i++) {
          patch(r.key, { st: 'up', pct: 0, msg: files.length > 1 ? `${i + 1}/${files.length}` : '' });
          await uploadFile(caseId, files[i].kind, files[i].file, pct => patch(r.key, { pct }));
          patch(r.key, { uploaded: i + 1, pct: 100 });
        }
        patch(r.key, { st: 'run' });
        const started = await api<RunStart>('/api/run', {
          body: { case_id: caseId, instructions: r.instr.trim() || undefined, outputs: r.drafts ?? defaultDrafts(r) },
        });
        patch(r.key, { st: started.queued ? 'queued' : 'started', msg: startText(started, isOwner) });
      } catch (x) {
        if (x instanceof ApiError && x.message === 'run_active') { patch(r.key, { st: 'queued', msg: userError(x, isOwner) }); continue; }
        const m = userError(x, isOwner);
        patch(r.key, { st: 'err', msg: m });
        // the monthly limit refuses every further run: do not send the rest (their files stay here for a later retry)
        if (x instanceof ApiError && x.message === 'monthly_budget_reached') stop = m;
      }
    }
    setBusy(false);
    const failed = rowsRef.current.filter(r => r.st === 'err').length;
    const nSent = rowsRef.current.filter(r => r.st === 'queued' || r.st === 'started').length;
    toast(failed ? `${failed} प्रस्ताव पाठविता आले नाहीत. कृपया लाल ओळी पाहून बटण पुन्हा दाबावे.` : `${nSent} प्रस्ताव पाठवले — क्रमाने तयार होतील`, failed ? 'err' : 'ok');
  }

  const drop = (e: DragEvent) => { e.preventDefault(); setOver(false); if (!busy) addProposal(Array.from(e.dataTransfer.files)); };
  const locked = (r: Row) => busy || !(r.st === 'wait' || r.st === 'err');
  // the "add a proposal" zone: on top while empty, below the proposals afterwards (next proposal after the last one)
  const addZone = (
      <div
        onDragOver={e => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        className={`flex min-h-[110px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-4 text-center transition ${over ? 'border-saffron-500 bg-saffron-500/10' : 'border-slate-300 dark:border-navy-700'}`}
      >
        <div className="font-semibold">{rows.length ? `प्रस्ताव ${rows.length + 1} जोडा` : 'प्रस्ताव 1 जोडा'}</div>
        <div className="text-sm text-slate-500 dark:text-slate-400">कृपया एका वेळी एकाच प्रस्तावाच्या फाइल निवडाव्यात: मुख्य PDF (व हवे असल्यास त्याच प्रस्तावाच्या इतर PDF / Word / प्रतिमा) • कमाल {BULK_MAX} प्रस्ताव • प्रक्रिया क्रमाने होईल</div>
        <button type="button" className="btn-ghost" disabled={busy || rows.length >= BULK_MAX} onClick={() => inputRef.current?.click()}>＋ नवीन प्रस्ताव ({rows.length}/{BULK_MAX})</button>
        <input ref={inputRef} type="file" hidden multiple accept={EXTRA_ACCEPT} onChange={e => { addProposal(Array.from(e.target.files || [])); e.target.value = ''; }} />
      </div>
  );
  return (
    <div className="space-y-4">
      {rows.length === 0 && addZone}

      {rows.length > 0 && (
        <div className={`card grid gap-3 p-3 ${isOwner ? 'sm:grid-cols-2' : ''}`}>
          <label className="block min-w-0">
            <span className="label">कामाचा प्रकार — सर्व प्रस्तावांसाठी</span>
            <select className="input" value={bulkWork} disabled={busy} onChange={e => setAll(e.target.value as WorkType)}>
              {WORK_TYPES.map(w => <option key={w.id} value={w.id}>{w.label}</option>)}
            </select>
          </label>
          {isOwner && (
            <label className="block min-w-0">
              <span className="label">विभाग / कार्यासन — सर्व प्रस्तावांसाठी</span>
              <select className="input" value={desk} disabled={busy || sent.length > 0} onChange={e => setDesk(e.target.value)}>
                {DESKS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
              </select>
            </label>
          )}
        </div>
      )}

      {rows.length > 0 && (
        <ol className="space-y-3">
          {rows.map((r, i) => {
            const run = r.caseId ? latestRuns.get(r.caseId) : undefined;
            const drafts = r.drafts ?? defaultDrafts(r);
            return (
              <li key={r.key} className={`card min-w-0 space-y-2 p-3 ${r.st === 'err' ? 'border-red-300 dark:border-red-800' : ''}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-navy-700 dark:text-navy-200">प्रस्ताव {i + 1}</div>
                    <div className="truncate font-semibold" title={r.file.name}>📄 {r.file.name}</div>
                    <div className="text-sm text-slate-500">{fmtBytes(r.file.size)}{r.subject ? <> • <span className="text-slate-600 dark:text-slate-300">{r.subject}</span></> : null}</div>
                  </div>
                  {!locked(r) && !r.caseId && (
                    <button type="button" className="btn-ghost min-w-tap shrink-0 px-2" aria-label="काढा" onClick={() => setRows(s => s.filter(x => x.key !== r.key))}>✕</button>
                  )}
                </div>
                <ExtraFiles extras={r.extras} disabled={locked(r) || r.uploaded > 0}
                  onAdd={f => addExtras(r.key, f)}
                  onKind={(j, kind) => patch(r.key, { extras: r.extras.map((x, k) => (k === j ? { ...x, kind } : x)) })}
                  onRemove={j => patch(r.key, { extras: r.extras.filter((_, k) => k !== j) })} />
                {r.showWork || r.work !== bulkWork ? (
                  <label className="flex min-w-0 items-center gap-2 text-sm">
                    <span className="shrink-0 font-semibold">कामाचा प्रकार</span>
                    <select className="input min-h-tap min-w-0 py-1" disabled={locked(r) || !!r.caseId} value={r.work}
                      onChange={e => patch(r.key, { work: e.target.value as WorkType, drafts: null })}>
                      {WORK_TYPES.map(w => <option key={w.id} value={w.id}>{w.label}</option>)}
                    </select>
                  </label>
                ) : !locked(r) && !r.caseId && (
                  <button type="button" className="min-h-tap text-sm font-semibold text-navy-700 underline dark:text-navy-200" aria-expanded={false} onClick={() => patch(r.key, { showWork: true })}>हा प्रस्ताव वेगळ्या प्रकाराचा ▼</button>
                )}
                <CompactDraftPicker value={drafts} onChange={v => patch(r.key, { drafts: v })} disabled={locked(r)} />
                {r.showInstr ? (
                  <textarea className="input min-h-[96px] text-sm" placeholder="विशेष सूचना (ऐच्छिक) — उदा. पत्र नको; नस्ती वित्त विभागाकडे पाठवावी" disabled={locked(r)}
                    value={r.instr} onChange={e => patch(r.key, { instr: e.target.value })} />
                ) : !locked(r) && (
                  <button type="button" className="min-h-tap text-sm font-semibold text-navy-700 underline dark:text-navy-200" aria-expanded={false} onClick={() => patch(r.key, { showInstr: true })}>+ विशेष सूचना (ऐच्छिक)</button>
                )}
                {r.st !== 'wait' && (
                  <div className="space-y-1">
                    {r.st === 'up' && <Progress pct={r.pct} tone="blue" />}
                    <div className={`flex flex-wrap items-center justify-between gap-2 text-sm font-semibold ${r.st === 'err' ? 'text-red-700 dark:text-red-400' : r.st === 'queued' || r.st === 'started' ? 'text-green-800 dark:text-green-300' : 'text-blue-800 dark:text-blue-200'}`} role={r.st === 'err' ? 'alert' : 'status'}>
                      <span className="flex min-w-0 items-center gap-1.5 break-words [overflow-wrap:anywhere]">
                        {(r.st === 'case' || r.st === 'up' || r.st === 'run') && <Spinner className="h-4 w-4" />}
                        {r.st === 'up' ? `अपलोड${r.msg ? ` ${r.msg}` : ''} ${r.pct}%` : r.st === 'err' ? `✕ ${r.msg}` : r.st === 'queued' || r.st === 'started' ? `✓ ${r.msg}` : ST_TEXT[r.st]}
                      </span>
                      {r.caseId && (r.st === 'queued' || r.st === 'started') && (
                        <span className="flex items-center gap-2">
                          {run && <RunStateBadge run={run} />}
                          <Link className="inline-flex min-h-tap items-center text-navy-700 underline dark:text-navy-200" to={`/cases/${r.caseId}`}>प्रकरण उघडा →</Link>
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}

      {rows.length > 0 && rows.length < BULK_MAX && !busy && addZone}

      {rows.length > 0 && (
        <div className="space-y-2">
          {(todo.length > 0 || busy) && <button type="button" className="btn-accent w-full text-lg" disabled={busy || !todo.length || overBudget} onClick={() => void go()}>
            {busy && <Spinner />}{' '}
            {busy ? 'पाठवत आहे…' : todo.some(r => r.st === 'err') ? `↻ पुन्हा पाठवा (${todo.length})` : `टिप्पणी व मसुदे तयार करा — ${todo.length} प्रस्ताव`}
          </button>}
          {sent.length > 0 && !busy && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-900 dark:bg-green-900/30 dark:text-green-100">
              <span><b>{sent.length}</b> प्रस्ताव पाठवले — क्रमाने तयार होतील. प्रत्येक प्रस्ताव तयार होताच तो ‘प्रकरणे’ मध्ये त्या प्रकरणात मिळेल. हे पान बंद केले तरी काम चालू राहील.</span>
              <Link className="inline-flex min-h-tap items-center font-semibold underline" to="/cases">प्रकरणे →</Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** The other files of ONE proposal: list with type + remove, and a picker that adds to this proposal only. */
function ExtraFiles({ extras, disabled, onAdd, onKind, onRemove }: {
  extras: Extra[]; disabled: boolean; onAdd: (f: File[]) => void; onKind: (i: number, k: InputKind) => void; onRemove: (i: number) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div className="space-y-1">
      {extras.length > 0 && (
        <ul className="space-y-1">
          {extras.map((x, i) => (
            <li key={i} className="flex min-w-0 flex-wrap items-center gap-2 rounded-lg bg-slate-100 px-2 py-1 text-sm dark:bg-navy-800">
              <span className="min-w-0 basis-full break-words [overflow-wrap:anywhere] sm:basis-auto sm:flex-1" title={x.file.name}>📎 {x.file.name} <span className="text-slate-500">({fmtBytes(x.file.size)})</span></span>
              <select className="input min-h-tap min-w-0 flex-1 py-1 sm:w-auto sm:flex-none" disabled={disabled} value={x.kind} aria-label="फाइलचा प्रकार" onChange={e => onKind(i, e.target.value as InputKind)}>
                {EXTRA_KINDS.map(k => <option key={k} value={k}>{INPUT_KIND_LABEL[k]}</option>)}
              </select>
              {!disabled && <button type="button" className="btn-ghost min-w-tap px-2" aria-label="काढा" onClick={() => onRemove(i)}>✕</button>}
            </li>
          ))}
        </ul>
      )}
      {!disabled && (
        <>
          <button type="button" className="min-h-tap text-sm font-semibold text-navy-700 underline dark:text-navy-200" onClick={() => ref.current?.click()}>＋ याच प्रस्तावाची इतर फाइल (PDF / Word / प्रतिमा)</button>
          <input ref={ref} type="file" hidden multiple accept={EXTRA_ACCEPT} onChange={e => { onAdd(Array.from(e.target.files || [])); e.target.value = ''; }} />
        </>
      )}
    </div>
  );
}
