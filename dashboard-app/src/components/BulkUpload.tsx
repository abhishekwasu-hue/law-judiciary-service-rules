// Bulk upload (C33, Abhi 04.11.2026: "किमान पाच प्रस्ताव एका वेळेला अपलोड … काम मात्र … वन बाय वन"): up to 10 proposal
// PDFs, one row (= one case) each: work category (bulk setter "सर्वांना"), drafts (compact, default पत्र; court → पत्र +
// परिच्छेदनिहाय उत्तर), optional instruction. "रांगेत टाका (N)": for every row in turn → POST /api/cases (work_type, desk;
// C R and subject are filled by the engine from the निर्देशपत्र) → upload → POST /api/run. The Worker runs them one by one
// ({queued: true, position}). A failed row keeps what was done (case / upload) and is retried from there.
import { useEffect, useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api, budgetReachedText, getSpend, humanError, runStartText, spendBlocked, uploadFile, type RunStart } from '../lib/api';
import { DEFAULT_DESK, DEFAULT_WORK_TYPE, DESKS, WORK_TYPES, type DraftKey, type WorkType } from '../lib/constants';
import { fmtBytes } from '../lib/format';
import { guessSubject } from '../lib/pdf';
import { useData } from '../lib/data';
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

type St = 'wait' | 'case' | 'up' | 'run' | 'queued' | 'started' | 'err';
interface Row {
  key: number; file: File; work: WorkType; drafts: DraftKey[] | null; // null = default of the category
  instr: string; showInstr: boolean; subject: string;
  st: St; pct: number; caseId: number | null; uploaded: boolean; msg: string;
}

const ST_TEXT: Record<St, string> = {
  wait: 'प्रतीक्षा', case: 'प्रकरण नोंदवत आहे…', up: 'अपलोड', run: 'प्रक्रिया पाठवत आहे…', queued: '', started: '', err: '',
};

export default function BulkUpload({ initial, overBudget }: { initial?: File[]; overBudget: boolean }) {
  const toast = useToast();
  const { latestRuns } = useData();
  const [rows, setRows] = useState<Row[]>([]);
  const [bulkWork, setBulkWork] = useState<WorkType>(DEFAULT_WORK_TYPE);
  const [desk, setDesk] = useState<string>(DEFAULT_DESK);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const keyRef = useRef(1);
  const inputRef = useRef<HTMLInputElement>(null);
  const rowsRef = useRef<Row[]>([]);
  rowsRef.current = rows;
  const patch = (key: number, p: Partial<Row>) => setRows(s => s.map(r => (r.key === key ? { ...r, ...p } : r)));

  function add(files: File[]) {
    const pdfs = files.filter(isPdf);
    if (pdfs.length < files.length) toast('फक्त PDF घेतल्या; इतर फाइल वगळल्या', 'err');
    const ok = pdfs.filter(f => f.size <= MAX_BYTES);
    if (ok.length < pdfs.length) toast('50 MB पेक्षा मोठ्या फाइल वगळल्या', 'err');
    const room = BULK_MAX - rowsRef.current.length;
    const take = ok.slice(0, Math.max(0, room));
    if (ok.length > take.length) toast(`एका वेळी कमाल ${BULK_MAX} प्रस्ताव — ${ok.length - take.length} वगळले`, 'err');
    const fresh = take.map(file => ({
      key: keyRef.current++, file, work: bulkWork, drafts: null, instr: '', showInstr: false, subject: '',
      st: 'wait' as St, pct: 0, caseId: null, uploaded: false, msg: '',
    }));
    setRows(s => [...s, ...fresh]);
    // subject from the PDF text layer (as the single upload does); empty = the engine fills it
    for (const r of fresh) void guessSubject(r.file).then(sub => sub && patch(r.key, { subject: sub }), () => undefined);
  }
  const did = useRef(false);
  useEffect(() => {
    if (!did.current && initial?.length) { did.current = true; add(initial); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      if (spendBlocked(sp)) { toast(budgetReachedText(sp.limit_usd), 'err'); setBusy(false); return; }
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
        if (!r.uploaded) {
          patch(r.key, { st: 'up', pct: 0 });
          await uploadFile(caseId, 'proposal', r.file, pct => patch(r.key, { pct }));
          patch(r.key, { uploaded: true, pct: 100 });
        }
        patch(r.key, { st: 'run' });
        const started = await api<RunStart>('/api/run', {
          body: { case_id: caseId, instructions: r.instr.trim() || undefined, outputs: r.drafts ?? draftsForWork(r.work) },
        });
        patch(r.key, { st: started.queued ? 'queued' : 'started', msg: runStartText(started) });
      } catch (x) {
        if (x instanceof ApiError && x.message === 'run_active') { patch(r.key, { st: 'queued', msg: humanError(x) }); continue; }
        const m = humanError(x);
        patch(r.key, { st: 'err', msg: m });
        // the monthly limit refuses every further run: do not send the rest (their files stay here for a later retry)
        if (x instanceof ApiError && x.message === 'monthly_budget_reached') stop = m;
      }
    }
    setBusy(false);
    const failed = rowsRef.current.filter(r => r.st === 'err').length;
    toast(failed ? `${failed} प्रस्ताव पाठवता आले नाहीत — त्या ओळी पाहा व पुन्हा दाबा` : 'सर्व प्रस्ताव रांगेत — एकामागून एक तयार होतील', failed ? 'err' : 'ok');
  }

  const drop = (e: DragEvent) => { e.preventDefault(); setOver(false); if (!busy) add(Array.from(e.dataTransfer.files)); };
  const locked = (r: Row) => busy || !(r.st === 'wait' || r.st === 'err');
  return (
    <div className="space-y-4">
      <div
        onDragOver={e => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        className={`flex min-h-[110px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-4 text-center transition ${over ? 'border-saffron-500 bg-saffron-500/10' : 'border-slate-300 dark:border-navy-700'}`}
      >
        <div className="font-semibold">प्रस्ताव PDF येथे ओढा — एकाच वेळी अनेक</div>
        <div className="text-sm text-slate-500 dark:text-slate-400">एक PDF = एक प्रस्ताव • कमाल {BULK_MAX} • प्रत्येकी कमाल 50 MB • काम एकामागून एक होईल</div>
        <button type="button" className="btn-ghost" disabled={busy || rows.length >= BULK_MAX} onClick={() => inputRef.current?.click()}>फाइल निवडा ({rows.length}/{BULK_MAX})</button>
        <input ref={inputRef} type="file" hidden multiple accept="application/pdf,.pdf" onChange={e => { add(Array.from(e.target.files || [])); e.target.value = ''; }} />
      </div>

      {rows.length > 0 && (
        <div className="card grid gap-3 p-3 sm:grid-cols-2">
          <label className="block min-w-0">
            <span className="label">कामाचा प्रकार — सर्वांना</span>
            <select className="input" value={bulkWork} disabled={busy} onChange={e => setAll(e.target.value as WorkType)}>
              {WORK_TYPES.map(w => <option key={w.id} value={w.id}>{w.label}</option>)}
            </select>
          </label>
          <label className="block min-w-0">
            <span className="label">विभाग / कार्यासन — सर्वांना</span>
            <select className="input" value={desk} disabled={busy || sent.length > 0} onChange={e => setDesk(e.target.value)}>
              {DESKS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
            </select>
          </label>
        </div>
      )}

      {rows.length > 0 && (
        <ol className="space-y-3">
          {rows.map((r, i) => {
            const run = r.caseId ? latestRuns.get(r.caseId) : undefined;
            const drafts = r.drafts ?? draftsForWork(r.work);
            return (
              <li key={r.key} className={`card min-w-0 space-y-2 p-3 ${r.st === 'err' ? 'border-red-300 dark:border-red-800' : ''}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-semibold" title={r.file.name}><span className="text-slate-500">{i + 1}.</span> 📄 {r.file.name}</div>
                    <div className="text-sm text-slate-500">{fmtBytes(r.file.size)}{r.subject ? <> • <span className="text-slate-600 dark:text-slate-300">{r.subject}</span></> : null}</div>
                  </div>
                  {!locked(r) && !r.caseId && (
                    <button type="button" className="btn-ghost min-w-tap shrink-0 px-2" aria-label="काढा" onClick={() => setRows(s => s.filter(x => x.key !== r.key))}>✕</button>
                  )}
                </div>
                <label className="flex min-w-0 items-center gap-2 text-sm">
                  <span className="shrink-0 font-semibold">प्रकार</span>
                  <select className="input min-h-tap min-w-0 py-1" disabled={locked(r) || !!r.caseId} value={r.work}
                    onChange={e => patch(r.key, { work: e.target.value as WorkType, drafts: null })}>
                    {WORK_TYPES.map(w => <option key={w.id} value={w.id}>{w.label}</option>)}
                  </select>
                </label>
                <CompactDraftPicker value={drafts} onChange={v => patch(r.key, { drafts: v })} disabled={locked(r)} />
                {r.showInstr ? (
                  <textarea className="input min-h-[64px] text-sm" placeholder="विशेष सूचना (ऐच्छिक) — उदा. पत्र नको; नस्ती वित्त विभागाकडे पाठवा" disabled={locked(r)}
                    value={r.instr} onChange={e => patch(r.key, { instr: e.target.value })} />
                ) : !locked(r) && (
                  <button type="button" className="min-h-tap text-sm font-semibold text-navy-700 underline dark:text-navy-200" onClick={() => patch(r.key, { showInstr: true })}>+ विशेष सूचना (ऐच्छिक)</button>
                )}
                {r.st !== 'wait' && (
                  <div className="space-y-1">
                    {r.st === 'up' && <Progress pct={r.pct} tone="blue" />}
                    <div className={`flex flex-wrap items-center justify-between gap-2 text-sm font-semibold ${r.st === 'err' ? 'text-red-700 dark:text-red-400' : r.st === 'queued' || r.st === 'started' ? 'text-green-800 dark:text-green-300' : 'text-blue-800 dark:text-blue-200'}`} role={r.st === 'err' ? 'alert' : 'status'}>
                      <span className="flex min-w-0 items-center gap-1.5 break-words [overflow-wrap:anywhere]">
                        {(r.st === 'case' || r.st === 'up' || r.st === 'run') && <Spinner className="h-4 w-4" />}
                        {r.st === 'up' ? `अपलोड ${r.pct}%` : r.st === 'err' ? `✕ ${r.msg}` : r.st === 'queued' || r.st === 'started' ? `✓ ${r.msg}` : ST_TEXT[r.st]}
                      </span>
                      {r.caseId && (r.st === 'queued' || r.st === 'started') && (
                        <span className="flex items-center gap-2">
                          {run && <RunStateBadge run={run} />}
                          <Link className="text-navy-700 underline dark:text-navy-200" to={`/cases/${r.caseId}`}>प्रकरण उघडा →</Link>
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

      {rows.length > 0 && (
        <div className="space-y-2">
          {(todo.length > 0 || busy) && <button type="button" className="btn-accent w-full text-lg" disabled={busy || !todo.length || overBudget} onClick={() => void go()}>
            {busy && <Spinner />}{' '}
            {busy ? 'पाठवत आहे…' : todo.some(r => r.st === 'err') ? `↻ पुन्हा पाठवा (${todo.length})` : `रांगेत टाका (${todo.length})`}
          </button>}
          {sent.length > 0 && !busy && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-900 dark:bg-green-900/30 dark:text-green-100">
              <span><b>{sent.length}</b> प्रस्ताव रांगेत — प्रत्येक तयार होताच प्रकरणात उपलब्ध</span>
              <Link className="font-semibold underline" to="/cases">प्रकरणे →</Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
