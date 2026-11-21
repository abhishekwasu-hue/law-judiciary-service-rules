// कार्यालयीन काम (Abhi 20.11.2026): everyday office work that is not a proposal — "these 2-3 documents, put the information
// into this format", calculations on figures, neat tables, a PPT. Decisions: a separate tab (office tasks never appear with
// the proposals); outputs Excel (formulas) / Word / PPT / PDF; English text Times New Roman, Marathi DVOT-SurekhMR.
// An office task = a `cases` doc with work_type 'office' (subject = title); inputs = case_files extra_doc / template; a run
// = runs kind 'full' with instructions + outputs ⊆ OFFICE_OUTPUT_KEYS; results = case_files kind office_output
// (docs/DESK_WORKER.md §3b). A later run on the same task = a correction that starts from the newest results; it is asked
// in the task's AI सुधारणा-चॅट (components/OfficeChat.tsx, 21.11.2026).
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, downloadFile, humanError } from '../lib/api';
import { newestByName, uploadAndRun } from '../lib/office';
import { sb } from '../lib/supabase';
import { useData, useLatestRuns } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import {
  OFFICE_ACCEPT, OFFICE_OUTPUT_KEYS, OFFICE_OUTPUT_LABEL, OFFICE_STEPS, OFFICE_WORK_TYPE, RUN_STATE_LABEL,
  runActive, runNeedsFire, runTone, type OfficeOutputKey,
} from '../lib/constants';
import { fmtBytes, fmtDateTime, runWarningTexts } from '../lib/format';
import type { Case, CaseFile, Run } from '../lib/types';
import { useToast } from '../components/Toast';
import { useRuns, RunNotStarted } from '../components/RunProgress';
import { Chip, Empty, Field, Progress, Section, Spinner } from '../components/ui';
import OfficeChat from '../components/OfficeChat';

const ARTIFACT = import.meta.env.VITE_BACKEND === 'artifact';
const TITLE_MAX = 200;
const INSTR_MAX = 4000;
const MAX_FILES = 10;

/** Office runs write their own step texts (OFFICE_STEPS); index of the progress row. */
function officeStep(r: Run): number {
  const last = OFFICE_STEPS.length - 1;
  if (r.state === 'done') return last;
  const t = (r.state === 'failed' ? r.last_step : r.step) || '';
  const i = OFFICE_STEPS.findIndex(s => t.includes(s.key));
  if (i >= 0) return i;
  return r.state === 'running' ? 1 : 0;
}

function OutputPicker({ value, onChange }: { value: OfficeOutputKey[]; onChange: (v: OfficeOutputKey[]) => void }) {
  return (
    <fieldset>
      <legend className="label">कोणती फाइल तयार करावी?</legend>
      <div className="flex flex-wrap gap-2">
        {OFFICE_OUTPUT_KEYS.map(k => {
          const on = value.includes(k);
          return (
            <label key={k} className={`flex min-h-tap cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm ${on ? 'border-navy-600 bg-navy-50 font-semibold dark:bg-navy-800' : 'border-slate-300 dark:border-navy-700'}`}>
              <input type="checkbox" checked={on} onChange={() => onChange(on ? value.filter(x => x !== k) : OFFICE_OUTPUT_KEYS.filter(x => x === k || value.includes(x)))} />
              {OFFICE_OUTPUT_LABEL[k]}
            </label>
          );
        })}
      </div>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">काहीही निवडले नाही तर उत्तर फक्त येथे मजकुरात मिळेल.</p>
    </fieldset>
  );
}

function FilePick({ label, hint, files, onChange, multiple = true }: { label: string; hint: string; files: File[]; onChange: (f: File[]) => void; multiple?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div>
      <span className="label">{label}</span>
      <button type="button" className="btn-ghost" onClick={() => ref.current?.click()}>
        <span aria-hidden="true">📎</span> {multiple ? 'फाइल्स निवडा' : 'फाइल निवडा'}
      </button>
      <input
        ref={ref}
        type="file"
        multiple={multiple}
        accept={OFFICE_ACCEPT}
        className="sr-only"
        aria-label={label}
        onChange={e => {
          const add = Array.from(e.target.files || []);
          onChange(multiple ? [...files, ...add].slice(0, MAX_FILES) : add.slice(0, 1));
          if (ref.current) ref.current.value = '';
        }}
      />
      <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">{hint}</span>
      {files.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center justify-between gap-2 rounded bg-slate-50 px-2 py-1 dark:bg-navy-800">
              <span className="min-w-0 break-all">{f.name} <span className="text-slate-500">({fmtBytes(f.size)})</span></span>
              <button type="button" className="text-red-700 dark:text-red-300" aria-label={`${f.name} काढा`} onClick={() => onChange(files.filter((_, j) => j !== i))}>✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NewTask() {
  const { refresh } = useData();
  const toast = useToast();
  const nav = useNavigate();
  const [title, setTitle] = useState('');
  const [instr, setInstr] = useState('');
  const [docs, setDocs] = useState<File[]>([]);
  const [tpl, setTpl] = useState<File[]>([]);
  const [outs, setOuts] = useState<OfficeOutputKey[]>(['xlsx']);
  const [busy, setBusy] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !instr.trim()) {
      toast('कृपया कामाचे शीर्षक व सूचना नमूद करावी, ही विनंती.', 'err');
      return;
    }
    setBusy('कामाची नोंद करत आहे…');
    let caseId: number | null = null;
    try {
      const c = await api<Case>('/api/cases', { method: 'POST', body: { subject: title.trim(), work_type: OFFICE_WORK_TYPE } });
      caseId = c.id;
      await uploadAndRun(c.id, docs, tpl, instr.trim(), outs, setBusy);
      toast('काम सुरू झाले. तयार फाइल याच पानावर मिळतील.');
      await refresh();
      nav(`/office/${c.id}`);
    } catch (err) {
      toast(humanError(err), 'err');
      if (caseId) {
        await refresh();
        nav(`/office/${caseId}`);
      }
    } finally {
      setBusy('');
    }
  }
  return (
    <Section title="➕ नवीन काम">
      <form className="space-y-4" onSubmit={e => void submit(e)}>
        <Field label="कामाचे शीर्षक">
          <input className="input" maxLength={TITLE_MAX} value={title} onChange={e => setTitle(e.target.value)} placeholder="उदा. जिल्हानिहाय रिक्त पदांचे विवरणपत्र" />
        </Field>
        <Field label="सूचना (काय करायचे)" hint={`${instr.length}/${INSTR_MAX} अक्षरे`}>
          <textarea
            className="input min-h-[8rem]"
            maxLength={INSTR_MAX}
            value={instr}
            onChange={e => setInstr(e.target.value)}
            placeholder="उदा. जोडलेल्या तीन फाइल्समधील माहिती साच्याप्रमाणे उतरवून द्यावी; जिल्हानिहाय बेरीज व एकूण काढावे; 5 स्लाइडचे सादरीकरण करावे."
          />
        </Field>
        <FilePick label="माहितीच्या फाइल्स" hint="PDF, Word, Excel, CSV, PPT, TXT किंवा प्रतिमा — जास्तीत जास्त 10." files={docs} onChange={setDocs} />
        <FilePick label="साचा / नमुना फाइल (असल्यास)" hint="याच फॉरमॅटमध्ये माहिती भरली जाईल." files={tpl} onChange={setTpl} multiple={false} />
        <OutputPicker value={outs} onChange={setOuts} />
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="btn-primary" disabled={!!busy}>
            {busy ? <Spinner className="h-4 w-4" /> : <span aria-hidden="true">▶</span>} काम सुरू करा
          </button>
          {busy && <span className="text-sm text-slate-600 dark:text-slate-300" role="status">{busy}</span>}
        </div>
      </form>
    </Section>
  );
}

function stateChip(r: Run | undefined) {
  if (!r) return <Chip tone="slate">सुरू नाही</Chip>;
  if (ARTIFACT && runNeedsFire(r)) return <Chip tone="amber">सुरू झाले नाही</Chip>;
  return <Chip tone={runTone(r.state)}>{RUN_STATE_LABEL[r.state] || r.state}</Chip>;
}

function TaskList() {
  const { officeCases, loading } = useData();
  const latest = useLatestRuns();
  const rows = useMemo(() => [...officeCases].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)), [officeCases]);
  return (
    <Section title={`कामांची यादी (${rows.length})`}>
      {loading && !rows.length ? (
        <Spinner />
      ) : !rows.length ? (
        <Empty icon="🗂️" title="अजून कोणतेही काम नाही" hint="वर सूचना व फाइल्स देऊन नवीन काम सुरू करा." />
      ) : (
        <ul className="divide-y divide-slate-200 dark:divide-navy-800">
          {rows.map(c => {
            const r = latest.get(c.id);
            return (
              <li key={c.id}>
                <Link to={`/office/${c.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-slate-50 dark:hover:bg-navy-800">
                  <span className="min-w-0 flex-1">
                    <span className="block break-words font-semibold">{c.subject || `काम क्र. ${c.id}`}</span>
                    <span className="block text-sm text-slate-500 dark:text-slate-400">{fmtDateTime(c.created_at)}</span>
                  </span>
                  {stateChip(r)}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

function FileRow({ f, label }: { f: CaseFile; label?: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2">
      <span className="min-w-0 flex-1 break-all text-sm">
        {f.original_name}
        {f.version > 1 && <span className="ml-1 text-slate-500">(आवृत्ती {f.version})</span>}
        {label && <span className="ml-2"><Chip tone="slate">{label}</Chip></span>}
      </span>
      <button
        type="button"
        className="btn-ghost"
        disabled={busy}
        aria-label={`डाउनलोड — ${f.original_name}`}
        onClick={async () => {
          setBusy(true);
          try {
            await downloadFile(f.id);
          } catch (e) {
            toast(humanError(e), 'err');
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? <Spinner /> : <span aria-hidden="true">⬇</span>} डाउनलोड
      </button>
    </li>
  );
}

function RunBox({ run }: { run: Run }) {
  const i = officeStep(run);
  const failed = run.state === 'failed';
  const active = runActive(run) && !(ARTIFACT && runNeedsFire(run));
  const pct = (i / (OFFICE_STEPS.length - 1)) * 100;
  const warns = runWarningTexts(run.warnings);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {stateChip(run)}
        <span className="text-sm text-slate-500 dark:text-slate-400">{fmtDateTime(run.created_at)}</span>
      </div>
      {ARTIFACT && runNeedsFire(run) ? (
        <RunNotStarted run={run} />
      ) : (
        <>
          <Progress pct={failed ? 100 : pct} tone={failed ? 'red' : run.state === 'done' ? 'green' : 'blue'} active={active} label="कामाची प्रगती" />
          <ol className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
            {OFFICE_STEPS.map((s, k) => (
              <li key={s.key} className={k < i || run.state === 'done' ? 'text-green-700 dark:text-green-300' : k === i ? (failed ? 'font-bold text-red-700 dark:text-red-300' : 'font-bold text-blue-700 dark:text-blue-300') : 'text-slate-400'}>
                {k < i || run.state === 'done' ? '✓' : k === i ? '●' : '○'} {s.label}
              </li>
            ))}
          </ol>
        </>
      )}
      {failed && run.step && <p className="break-words text-sm text-red-800 dark:text-red-200">{run.step}</p>}
      {run.summary && (
        <div className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm dark:bg-navy-800">{run.summary}</div>
      )}
      {warns.length > 0 && (
        <details className="rounded-lg border border-amber-300 bg-amber-50 p-2 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100">
          <summary className="cursor-pointer font-semibold">⚠ तपासण्याचे मुद्दे ({warns.length})</summary>
          <ul className="mt-1 list-disc space-y-1 pl-5">{warns.map((w, k) => <li key={k} className="break-words">{w}</li>)}</ul>
        </details>
      )}
    </div>
  );
}

function TaskDetail({ id }: { id: number }) {
  const { officeCases, loading, refresh } = useData();
  const c = officeCases.find(x => x.id === id);
  const runs = useRuns(id);
  const [files, setFiles] = useState<CaseFile[] | null>(null);
  const loadFiles = useCallback(async () => {
    const { data } = await sb().from('case_files').select('*').eq('case_id', id).order('created_at', { ascending: false });
    setFiles(((data as CaseFile[]) || []).filter(f => f.kind !== 'spec'));
  }, [id]);
  const latest = runs?.[0];
  // re-read the files when a run of this task finishes (new results)
  const doneKey = (runs || []).filter(r => r.state === 'done' || r.state === 'failed').map(r => r.id).join(',');
  useEffect(() => {
    void loadFiles();
  }, [loadFiles, doneKey]);
  if (!c) {
    return loading ? <Spinner /> : <Empty icon="🔍" title="हे काम सापडले नाही"><Link to="/office" className="btn-ghost">कामांची यादी</Link></Empty>;
  }
  const outputs = files ? newestByName(files, ['office_output']) : [];
  const inputs = files ? newestByName(files, ['extra_doc', 'template']) : [];
  return (
    <div className="space-y-4">
      <div>
        <Link to="/office" className="text-sm text-navy-700 underline dark:text-navy-200">← कार्यालयीन काम</Link>
        <h1 className="mt-1 break-words text-xl font-bold">{c.subject || `काम क्र. ${c.id}`}</h1>
      </div>
      <Section title="स्थिती व उत्तर">
        {!runs ? <Spinner /> : latest ? <RunBox run={latest} /> : <p className="text-sm">अजून काम सुरू झालेले नाही.</p>}
      </Section>
      <Section title={`तयार फाइल्स (${outputs.length})`}>
        {!files ? <Spinner /> : outputs.length ? (
          <ul className="divide-y divide-slate-200 dark:divide-navy-800">{outputs.map(f => <FileRow key={f.id} f={f} />)}</ul>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">अजून तयार फाइल नाही.</p>
        )}
      </Section>
      <OfficeChat caseId={id} onChanged={() => { void refresh(); void loadFiles(); }} />
      <Section title={`दिलेल्या फाइल्स (${inputs.length})`}>
        {!files ? <Spinner /> : inputs.length ? (
          <ul className="divide-y divide-slate-200 dark:divide-navy-800">{inputs.map(f => <FileRow key={f.id} f={f} label={f.kind === 'template' ? 'साचा' : undefined} />)}</ul>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">फाइल दिलेली नाही.</p>
        )}
      </Section>
    </div>
  );
}

export default function OfficeWork() {
  const { id } = useParams();
  const canWrite = useCanWrite();
  const n = Number(id);
  if (id && Number.isInteger(n) && n > 0) return <TaskDetail id={n} />;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold">कार्यालयीन काम</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">माहिती साच्यात उतरवणे, आकडेमोड, तक्ते, सादरीकरण — प्रस्तावाव्यतिरिक्त दैनंदिन कामे.</p>
      </div>
      {canWrite && <NewTask />}
      <TaskList />
    </div>
  );
}
