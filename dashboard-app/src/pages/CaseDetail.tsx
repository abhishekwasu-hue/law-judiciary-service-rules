import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { useData, overdueIds } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import { CATEGORIES, PRIORITIES, STAGES, stageTone } from '../lib/constants';
import { crLabel, fmtDate } from '../lib/format';
import { humanError } from '../lib/api';
import type { Activity, Case, CaseFile, Letter, Member } from '../lib/types';
import { Chip, Empty, Field, Modal, Skeleton, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import { useRuns } from '../components/RunProgress';
import { BriefingTab, HistoryTab, LettersTab, NoteTab, PackageTab, StudyTab } from './CaseTabs';

const TABS = [
  { k: 'brief', label: 'ब्रीफिंग' },
  { k: 'note', label: 'टिप्पणी व पत्र' },
  { k: 'pdf', label: 'प्रस्ताव + GR' },
  { k: 'study', label: 'अभ्यास' },
  { k: 'letters', label: 'पत्रव्यवहार' },
  { k: 'history', label: 'इतिहास' },
] as const;

export interface CaseCtx {
  c: Case;
  files: CaseFile[];
  letters: Letter[];
  activity: Activity[];
  members: Map<string, string>;
  runs: ReturnType<typeof useRuns>;
  reloadFiles: () => Promise<void>;
  reloadLetters: () => Promise<void>;
  reloadActivity: () => Promise<void>;
  canWrite: boolean;
}

export default function CaseDetail() {
  const id = Number(useParams().id);
  const { cases, letters: allLetters, setStage, patchLocal, refresh } = useData();
  const canWrite = useCanWrite();
  const toast = useToast();
  const [sp, setSp] = useSearchParams();
  const tab = (TABS.find(t => t.k === sp.get('tab')) || TABS[0]).k;
  const [single, setSingle] = useState<Case | null | undefined>(undefined);
  const [files, setFiles] = useState<CaseFile[]>([]);
  const [letters, setLetters] = useState<Letter[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [members, setMembers] = useState<Map<string, string>>(new Map());
  const [editOpen, setEditOpen] = useState(false);
  const runs = useRuns(id || null);

  const c = cases.find(x => x.id === id) ?? single ?? null;

  useEffect(() => {
    if (!cases.find(x => x.id === id))
      void sb().from('cases').select('*').eq('id', id).maybeSingle().then(({ data }) => setSingle((data as Case) || null));
  }, [id, cases]);

  const reloadFiles = useCallback(async () => {
    const { data } = await sb().from('case_files').select('*').eq('case_id', id).order('version', { ascending: false }).order('created_at', { ascending: false });
    setFiles((data as CaseFile[]) || []);
  }, [id]);
  const reloadLetters = useCallback(async () => {
    const { data } = await sb().from('letters').select('*').eq('case_id', id).order('created_at', { ascending: false });
    setLetters((data as Letter[]) || []);
    void refresh();
  }, [id, refresh]);
  const reloadActivity = useCallback(async () => {
    const { data } = await sb().from('activity').select('*').eq('case_id', id).order('at', { ascending: false }).limit(300);
    setActivity((data as Activity[]) || []);
  }, [id]);

  useEffect(() => {
    void reloadFiles();
    void reloadLetters();
    void reloadActivity();
    void sb().from('members').select('user_id,email').then(({ data }) => setMembers(new Map(((data as Member[]) || []).map(m => [m.user_id, m.email]))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // When the latest run finishes, its outputs appear in case_files (not in the Realtime publication) → reload.
  const latestState = runs?.[0]?.state;
  useEffect(() => {
    if (latestState === 'done' || latestState === 'failed') {
      void reloadFiles();
      void reloadActivity();
    }
  }, [latestState, reloadFiles, reloadActivity]);
  useEffect(() => {
    void reloadActivity();
  }, [c?.stage, reloadActivity]);

  const overdue = useMemo(() => overdueIds(c ? [c] : [], allLetters), [c, allLetters]);

  if (single === undefined && !c) return <div className="space-y-3"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-40 w-full" /></div>;
  if (!c) return <div className="card"><Empty icon="❓" title="प्रकरण सापडले नाही" hint="यादीतून पुन्हा निवडा."><Link className="btn-ghost" to="/cases">प्रकरणे</Link></Empty></div>;

  async function changeStage(s: string) {
    try {
      if (cases.find(x => x.id === id)) await setStage(id, s);
      else {
        const { error } = await sb().from('cases').update({ stage: s }).eq('id', id);
        if (error) throw new Error(error.message);
        setSingle(x => (x ? { ...x, stage: s } : x));
      }
      toast(`टप्पा: ${s}`);
    } catch (e) {
      toast(humanError(e), 'err');
    }
  }

  const ctx: CaseCtx = { c, files, letters, activity, members, runs, reloadFiles, reloadLetters, reloadActivity, canWrite };
  return (
    <div className="space-y-4">
      <div className="no-print">
        <Link to="/cases" className="text-sm font-semibold text-navy-600 hover:underline dark:text-navy-200">← प्रकरणे</Link>
      </div>
      <header className="card space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold">{crLabel(c)}</h1>
              <Chip tone={stageTone(c.stage)}>{c.stage}</Chip>
              {c.priority === 'तातडीचे' && <Chip tone="amber">तातडीचे</Chip>}
              {overdue.has(c.id) && <Chip tone="red">मुदत संपली</Chip>}
            </div>
            <p className="mt-1 text-lg">{c.subject}</p>
          </div>
          {canWrite && (
            <div className="no-print flex flex-wrap gap-2">
              <select className="input w-auto" value={c.stage} onChange={e => void changeStage(e.target.value)} aria-label="टप्पा बदला">
                {STAGES.map(s => <option key={s}>{s}</option>)}
              </select>
              <button className="btn-ghost" onClick={() => setEditOpen(true)}>✎ तपशील</button>
            </div>
          )}
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
          {[
            ['नस्ती क्र.', c.file_no], ['प्रवर्ग', c.category], ['कार्यालय', c.office], ['कर्मचारी / पद', [c.employee_name, c.post].filter(Boolean).join(' / ')],
            ['प्राप्त', c.received_from], ['मार्ग', c.received_via === 'High Court' ? 'उच्च न्यायालयामार्फत' : c.received_via === 'direct' ? 'थेट' : null],
            ['आवक दिनांक', c.inward_date && fmtDate(c.inward_date)], ['मुदत', c.due_date && fmtDate(c.due_date)],
          ].map(([k, v]) => (
            <div key={k as string} className="min-w-0">
              <dt className="text-slate-500 dark:text-slate-400">{k}</dt>
              <dd className="truncate font-semibold" title={(v as string) || ''}>{v || '—'}</dd>
            </div>
          ))}
        </dl>
      </header>

      <div className="no-print -mx-4 overflow-x-auto px-4">
        <div className="inline-flex min-w-full gap-1 border-b border-slate-200 dark:border-navy-800" role="tablist">
          {TABS.map(t => (
            <button
              key={t.k}
              role="tab"
              aria-selected={tab === t.k}
              className={`min-h-tap whitespace-nowrap border-b-4 px-3 font-semibold ${tab === t.k ? 'border-saffron-500 text-navy-800 dark:text-white' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
              onClick={() => setSp(t.k === 'brief' ? {} : { tab: t.k }, { replace: true })}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div role="tabpanel">
        {tab === 'brief' && <BriefingTab ctx={ctx} />}
        {tab === 'note' && <NoteTab ctx={ctx} />}
        {tab === 'pdf' && <PackageTab ctx={ctx} />}
        {tab === 'study' && <StudyTab ctx={ctx} />}
        {tab === 'letters' && <LettersTab ctx={ctx} />}
        {tab === 'history' && <HistoryTab ctx={ctx} />}
      </div>

      <EditCase open={editOpen} onClose={() => setEditOpen(false)} c={c} onSaved={row => { patchLocal(row); setSingle(row); }} />
    </div>
  );
}

function EditCase({ open, onClose, c, onSaved }: { open: boolean; onClose: () => void; c: Case; onSaved: (c: Case) => void }) {
  const toast = useToast();
  const pick = (x: Case) => ({
    file_no: x.file_no || '', subject: x.subject, category: x.category, priority: x.priority, employee_name: x.employee_name || '', post: x.post || '',
    office: x.office || '', received_from: x.received_from || '', received_via: x.received_via || '', inward_date: x.inward_date || '', due_date: x.due_date || '',
  });
  const [f, setF] = useState(pick(c));
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) setF(pick(c));
  }, [open, c]);
  const set = (k: keyof ReturnType<typeof pick>) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const row = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === '' && k !== 'subject' ? null : v]));
    const { data, error } = await sb().from('cases').update(row).eq('id', c.id).select().single();
    setBusy(false);
    if (error) return toast(humanError(error.message), 'err');
    onSaved(data as Case);
    toast('जतन केले');
    onClose();
  }
  return (
    <Modal open={open} onClose={onClose} title="प्रकरणाचा तपशील" wide>
      <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2"><Field label="विषय"><textarea className="input" value={f.subject ?? ''} onChange={set('subject')} /></Field></div>
        <Field label="नस्ती क्र."><input className="input" value={f.file_no} onChange={set('file_no')} /></Field>
        <Field label="प्रवर्ग"><select className="input" value={f.category} onChange={set('category')}>{CATEGORIES.map(x => <option key={x}>{x}</option>)}</select></Field>
        <Field label="प्राधान्य"><select className="input" value={f.priority} onChange={set('priority')}>{PRIORITIES.map(x => <option key={x}>{x}</option>)}</select></Field>
        <Field label="कार्यालय"><input className="input" value={f.office} onChange={set('office')} /></Field>
        <Field label="कर्मचारी"><input className="input" value={f.employee_name} onChange={set('employee_name')} /></Field>
        <Field label="पद"><input className="input" value={f.post} onChange={set('post')} /></Field>
        <Field label="कोणाकडून प्राप्त"><input className="input" value={f.received_from} onChange={set('received_from')} /></Field>
        <Field label="मार्ग">
          <select className="input" value={f.received_via} onChange={set('received_via')}>
            <option value="">—</option><option value="High Court">उच्च न्यायालयामार्फत</option><option value="direct">थेट</option>
          </select>
        </Field>
        <Field label="आवक दिनांक"><input className="input" type="date" value={f.inward_date} onChange={set('inward_date')} /></Field>
        <Field label="मुदत"><input className="input" type="date" value={f.due_date} onChange={set('due_date')} /></Field>
        <div className="flex justify-end gap-2 sm:col-span-2">
          <button type="button" className="btn-ghost" onClick={onClose}>रद्द</button>
          <button className="btn-primary" disabled={busy}>{busy && <Spinner />} जतन करा</button>
        </div>
      </form>
    </Modal>
  );
}
