// कार्यालयीन कामाचा AI सुधारणा-चॅट (Abhi 21.11.2026: "तिथे ए आय चाट बॉक्स मधून सुधारणा सुचविण्याची सुद्धा तरतूद करा";
// choice "दोन्ही" — on the office task page in place of the old "बदल हवा आहे?" form, and in the floating AI सहाय्यक).
// One message = one office run (POST /api/run, the same as the old form, docs/DESK_WORKER.md §3b): the worker starts from
// the newest result files. The files to change are picked as chips; their names go on the first line of the instruction
// ("बदल करायच्या फाइल्स: …", lib/office.ts) — nothing new on the server or in the data model.
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { downloadFile, humanError } from '../lib/api';
import { sb } from '../lib/supabase';
import { useCanWrite } from '../lib/auth';
import {
  OFFICE_ACCEPT, OFFICE_OUTPUT_KEYS, OFFICE_OUTPUT_LABEL, RUNS_RELOAD_EVENT, runActive, runNeedsFire, type OfficeOutputKey,
} from '../lib/constants';
import { fmtBytes, fmtDateTime, runWarningTexts } from '../lib/format';
import { newestByName, splitTargets, uploadAndRun, withTargets } from '../lib/office';
import type { CaseFile, Run } from '../lib/types';
import { useToast } from './Toast';
import { RunNotStarted, useRuns } from './RunProgress';
import { Chip, Spinner } from './ui';

const ARTIFACT = import.meta.env.VITE_BACKEND === 'artifact';
const MAX_CHARS = 4000;
const MAX_FILES = 10;

function DlBtn({ f }: { f: CaseFile }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <button type="button" className="inline-flex min-h-tap min-w-0 max-w-full items-center gap-1 rounded-lg bg-white px-2 py-1 text-left text-sm font-semibold text-navy-800 shadow-sm hover:bg-slate-50 dark:bg-navy-900 dark:text-slate-100"
      disabled={busy} title={f.original_name} aria-label={`डाउनलोड — ${f.original_name}`}
      onClick={async () => { setBusy(true); try { await downloadFile(f.id); } catch (e) { toast(humanError(e), 'err'); } finally { setBusy(false); } }}>
      {busy ? <Spinner className="h-4 w-4" /> : <span aria-hidden="true">⬇</span>}
      <span className="min-w-0 break-all">{f.original_name}{f.version > 1 ? ` (आवृत्ती ${f.version})` : ''}</span>
    </button>
  );
}

/** One instruction (right bubble) and its answer (left bubble). `made` = result files stored by this run. */
function Turn({ r, made }: { r: Run; made: CaseFile[] }) {
  const { targets, text } = splitTargets(r.instructions);
  const needFire = ARTIFACT && runNeedsFire(r);
  const active = !needFire && runActive(r);
  const warns = runWarningTexts(r.warnings);
  const outs = Array.isArray(r.outputs) ? r.outputs : [];
  return (
    <li className="space-y-2">
      <div className="flex justify-end">
        <div className="min-w-0 max-w-[92%] rounded-2xl rounded-br-sm bg-navy-700 px-3 py-2 text-white dark:bg-navy-600">
          <div className="mb-0.5 text-xs opacity-80">{fmtDateTime(r.created_at)}</div>
          {targets.length > 0 && <div className="mb-1 text-xs font-bold opacity-90">बदल: {targets.join(', ')}</div>}
          <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{text || '—'}</div>
          {outs.length > 0 && <div className="mt-1 text-xs opacity-80">फाइल: {outs.map(k => OFFICE_OUTPUT_LABEL[k as OfficeOutputKey] || k).join(', ')}</div>}
        </div>
      </div>
      <div className="min-w-0 max-w-[96%] space-y-2 rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2 dark:bg-navy-800/70">
        <div className="flex flex-wrap items-center gap-2">
          {active ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
              <Spinner className="h-3.5 w-3.5" /> {r.state === 'queued' ? 'प्रतीक्षेत' : 'चालू'}
            </span>
          ) : needFire ? <Chip tone="amber">⚠ सुरू झाले नाही</Chip>
            : r.state === 'done' ? <Chip tone="green">✓ तयार</Chip> : <Chip tone="red">अयशस्वी</Chip>}
          {active && r.step && <span className="min-w-0 break-words text-sm text-slate-600 dark:text-slate-300">{r.step}</span>}
        </div>
        {needFire && <RunNotStarted run={r} />}
        {r.state === 'failed' && <div className="break-words text-sm text-red-900 [overflow-wrap:anywhere] dark:text-red-200">{r.step || 'कारण उपलब्ध नाही'}</div>}
        {r.state === 'done' && r.summary && <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{r.summary}</div>}
        {r.state === 'done' && made.length > 0 && <div className="flex flex-wrap gap-1.5">{made.map(f => <DlBtn key={f.id} f={f} />)}</div>}
        {warns.length > 0 && (
          <details className="rounded-lg border border-amber-300 bg-amber-50 p-2 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100">
            <summary className="cursor-pointer font-semibold">⚠ तपासण्याचे मुद्दे ({warns.length})</summary>
            <ul className="mt-1 list-disc space-y-1 pl-5">{warns.map((w, k) => <li key={k} className="break-words">{w}</li>)}</ul>
          </details>
        )}
      </div>
    </li>
  );
}

export default function OfficeChat({ caseId, onChanged }: { caseId: number; onChanged?: () => void }) {
  const toast = useToast();
  const canWrite = useCanWrite();
  const runs = useRuns(caseId);
  const [files, setFiles] = useState<CaseFile[] | null>(null);
  const [text, setText] = useState('');
  const [docs, setDocs] = useState<File[]>([]);
  const [targets, setTargets] = useState<string[]>([]);
  const [outs, setOuts] = useState<OfficeOutputKey[] | null>(null);
  const [busy, setBusy] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const loadFiles = useCallback(async () => {
    const { data } = await sb().from('case_files').select('*').eq('case_id', caseId).order('created_at', { ascending: true });
    setFiles(((data as CaseFile[]) || []).filter(f => f.kind !== 'spec'));
  }, [caseId]);
  const doneKey = (runs || []).filter(r => r.state === 'done' || r.state === 'failed').map(r => r.id).join(',');
  useEffect(() => { void loadFiles(); }, [loadFiles, doneKey]);
  // oldest first, like a chat
  const turns = useMemo(() => [...(runs || [])].sort((a, b) => (a.created_at < b.created_at ? -1 : 1)), [runs]);
  const latest = turns[turns.length - 1];
  const results = useMemo(() => (files ? newestByName(files, ['office_output']) : []), [files]);
  // the files asked last time stay ticked (a correction usually wants the same files back)
  const outKeys = outs ?? OFFICE_OUTPUT_KEYS.filter(k => (latest?.outputs ?? ['xlsx']).includes(k));
  /** Result files stored by run i: office_output rows created after it was asked and before the next instruction. */
  const madeBy = (i: number) => {
    const from = turns[i].created_at;
    const to = turns[i + 1]?.created_at;
    return (files || []).filter(f => f.kind === 'office_output' && f.created_at >= from && (!to || f.created_at < to));
  };
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'nearest' }); }, [turns.length]);
  const working = !!latest && runActive(latest) && !(ARTIFACT && runNeedsFire(latest));
  const canSend = canWrite && !busy && !working && text.trim().length > 0;
  async function send(e?: FormEvent) {
    e?.preventDefault();
    if (!canSend) {
      if (!text.trim()) toast('कृपया बदल / पुढील सूचना नमूद करावी, ही विनंती.', 'err');
      return;
    }
    try {
      await uploadAndRun(caseId, docs, [], withTargets(text.trim(), targets), outKeys, setBusy);
      toast('संदेश पाठवला — काम सुरू झाले.');
      setText('');
      setDocs([]);
      setTargets([]);
    } catch (err) {
      toast(humanError(err), 'err');
    } finally {
      setBusy('');
      void loadFiles();
      window.dispatchEvent(new Event(RUNS_RELOAD_EVENT));
      onChanged?.();
    }
  }
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); }
  };
  return (
    <section className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-navy-800 dark:bg-navy-900" aria-label="AI सुधारणा-चॅट">
      <div className="edit-head flex items-center gap-3 px-4 py-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-sm font-black text-orange-700">AI</span>
        <div className="min-w-0">
          <div className="text-lg font-bold">AI सुधारणा-चॅट</div>
          <div className="text-sm text-white/90">तयार फाइलमध्ये बदल हवा असल्यास येथे लिहावे</div>
        </div>
      </div>
      <div className="space-y-4 p-3">
        {!runs ? <div className="flex justify-center p-4"><Spinner /></div> : turns.length === 0 ? (
          <p className="rounded-2xl rounded-tl-sm bg-slate-100 p-3 text-sm dark:bg-navy-800">अजून कोणताही संदेश नाही.</p>
        ) : (
          <ol className="space-y-4">{turns.map((r, i) => <Turn key={r.id} r={r} made={madeBy(i)} />)}</ol>
        )}
        <div ref={endRef} />
        {canWrite && (
          <form onSubmit={e => void send(e)} className="space-y-2">
            {results.length > 0 && (
              <fieldset>
                <legend className="mb-1 text-sm font-semibold">कोणत्या फाइलमध्ये बदल? <span className="font-normal text-slate-500 dark:text-slate-400">(निवडले नाही तर सूचनेप्रमाणे)</span></legend>
                <div className="flex flex-wrap gap-1.5">
                  {results.map(f => {
                    const on = targets.includes(f.original_name);
                    return (
                      <button key={f.id} type="button" aria-pressed={on} disabled={!!busy}
                        className={`min-h-tap min-w-0 max-w-full break-all rounded-full border px-3 py-1 text-left text-sm ${on ? 'border-orange-500 bg-orange-50 font-semibold text-orange-900 dark:bg-orange-900/30 dark:text-orange-100' : 'border-slate-300 dark:border-navy-700'}`}
                        onClick={() => setTargets(s => (on ? s.filter(x => x !== f.original_name) : [...s, f.original_name]))}>
                        {on ? '✓ ' : ''}{f.original_name}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
            )}
            <label htmlFor={`office-msg-${caseId}`} className="block text-base font-bold text-orange-700 dark:text-orange-300">✍️ कृपया येथे आपला बदल लिहावा</label>
            <div className="rounded-xl border-2 border-orange-400 bg-white shadow-sm focus-within:border-navy-500 focus-within:ring-2 focus-within:ring-navy-200 dark:border-navy-700 dark:bg-navy-900 dark:focus-within:ring-navy-700">
              {docs.length > 0 && (
                <ul className="flex flex-wrap gap-1.5 border-b border-slate-200 p-2 dark:border-navy-800">
                  {docs.map((f, i) => (
                    <li key={`${f.name}-${i}`} className="flex min-w-0 max-w-full items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-xs dark:bg-navy-800">
                      <span aria-hidden="true">📎</span>
                      <span className="min-w-0 max-w-[10rem] truncate font-semibold" title={f.name}>{f.name}</span>
                      <span className="text-slate-500">{fmtBytes(f.size)}</span>
                      <button type="button" className="min-h-tap min-w-tap rounded font-bold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-navy-700" disabled={!!busy}
                        aria-label={`${f.name} काढावी`} onClick={() => setDocs(s => s.filter((_, j) => j !== i))}>✕</button>
                    </li>
                  ))}
                </ul>
              )}
              <textarea
                id={`office-msg-${caseId}`}
                className="block min-h-[130px] w-full resize-y rounded-xl bg-transparent px-3 py-3 text-lg outline-none"
                placeholder="उदा. परिच्छेद 4 मध्ये घटनाक्रम जोडावा; PPT मधील स्लाइड 8 वगळावी"
                value={text}
                maxLength={MAX_CHARS}
                disabled={!!busy}
                onChange={e => setText(e.target.value)}
                onKeyDown={onKey}
                aria-label="बदलाचा संदेश"
              />
              <div className="flex flex-wrap items-center gap-2 px-2 pb-2">
                <button type="button" className="btn-ghost min-h-tap min-w-tap px-2" disabled={!!busy || docs.length >= MAX_FILES} title="फाइल जोडावी" aria-label="फाइल जोडावी" onClick={() => fileRef.current?.click()}>📎</button>
                <input ref={fileRef} type="file" hidden multiple accept={OFFICE_ACCEPT}
                  onChange={e => { const add = Array.from(e.target.files || []); setDocs(s => [...s, ...add].slice(0, MAX_FILES)); e.target.value = ''; }} />
                <span className="hidden min-w-0 truncate text-xs text-slate-500 dark:text-slate-400 sm:inline">Enter = पाठवावे • Shift+Enter = नवी ओळ</span>
                <button className="btn-primary ml-auto" disabled={!canSend}>{busy && <Spinner />} {busy ? 'पाठवत आहे…' : 'कृपया पाठवावे'}</button>
              </div>
            </div>
            <fieldset>
              <legend className="mb-1 text-sm font-semibold">परत कोणती फाइल हवी?</legend>
              <div className="flex flex-wrap gap-1.5">
                {OFFICE_OUTPUT_KEYS.map(k => {
                  const on = outKeys.includes(k);
                  return (
                    <label key={k} className={`flex min-h-tap cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1 text-sm ${on ? 'border-navy-600 bg-navy-50 font-semibold dark:bg-navy-800' : 'border-slate-300 dark:border-navy-700'}`}>
                      <input type="checkbox" checked={on} disabled={!!busy}
                        onChange={() => setOuts(on ? outKeys.filter(x => x !== k) : OFFICE_OUTPUT_KEYS.filter(x => x === k || outKeys.includes(x)))} />
                      {OFFICE_OUTPUT_LABEL[k]}
                    </label>
                  );
                })}
              </div>
            </fieldset>
            {busy && <p className="text-sm text-slate-600 dark:text-slate-300" role="status">{busy}</p>}
            <p className="text-xs text-slate-500 dark:text-slate-400">
              मागील तयार फाइलवरूनच बदल केले जातील • आपण सांगितलेलाच बदल करण्यात येईल{working ? ' • काम चालू आहे — ते पूर्ण झाल्यावर कृपया संदेश पाठवावा' : ''}
            </p>
          </form>
        )}
      </div>
    </section>
  );
}
