import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { useData, overdueIds } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import { CATEGORIES, DEFAULT_DESK, DESKS, PRIORITIES, STAGES, WORK_TYPES, WORK_TYPE_TONE, deskLabel, isEditRun, isHiddenFile, stageTone, workTypeLabel, workTypeOf } from '../lib/constants';
import { caseSubject, crFromFileName, crLabel, fmtDate } from '../lib/format';
import { ApiError, api, humanError } from '../lib/api';
import type { Activity, Case, CaseFile, Letter, Member, Run } from '../lib/types';
import { Chip, Empty, Field, Modal, Skeleton, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import { StudyWarningsLine, useRuns } from '../components/RunProgress';
import NastiLink from '../components/NastiLink';
import { BriefingTab, HistoryTab, LettersTab, NoteTab, PackageTab, StudyTab } from './CaseTabs';

const TABS = [
  { k: 'brief', label: 'ब्रीफिंग' },
  { k: 'note', label: 'टिप्पणी व पत्र' },
  { k: 'pdf', label: 'प्रस्ताव + GR' },
  { k: 'study', label: 'अभ्यास-फाइल' },
  { k: 'letters', label: 'पत्रव्यवहार' },
  { k: 'history', label: 'इतिहास' },
] as const;

export interface CaseCtx {
  c: Case;
  files: CaseFile[];
  letters: Letter[];
  activity: Activity[];
  members: Map<string, string>;
  /** full processing runs only, newest first (edit runs left out — docs/DRAFT_EDIT_DESIGN.md §6) */
  runs: ReturnType<typeof useRuns>;
  /** सुधारणा-चॅट runs (runs.kind = 'edit'), newest first */
  editRuns: Run[] | null;
  /** the case has a drafts' source file (kind 'spec') → the सुधारणा chat can be used */
  hasSpec: boolean;
  reloadFiles: () => Promise<void>;
  reloadLetters: () => Promise<void>;
  reloadActivity: () => Promise<void>;
  canWrite: boolean;
  /** the case's display title (C R, or C R from the file name, or प्रकरण #id) — same as the page header */
  title: string;
}

export default function CaseDetail() {
  const id = Number(useParams().id);
  const { cases, letters: allLetters, setStage, patchLocal, setCaseLetters } = useData();
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
  const allRuns = useRuns(id || null);
  const runs = useMemo(() => (allRuns ? allRuns.filter(r => !isEditRun(r)) : null), [allRuns]);
  const editRuns = useMemo(() => (allRuns ? allRuns.filter(isEditRun) : null), [allRuns]);
  const [hasSpec, setHasSpec] = useState(false);

  const c = cases.find(x => x.id === id) ?? single ?? null;
  // the case currently shown: responses that arrive for an earlier id are dropped
  const curId = useRef(id);
  curId.current = id;

  // A failed fetch must not look like "अजून तयार नाही": keep the old data and show a reload message.
  const [loadErr, setLoadErr] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [caseTry, setCaseTry] = useState(0);

  // another case opened (same component instance): clear everything of the previous one
  const [shownId, setShownId] = useState(id);
  if (shownId !== id) {
    setShownId(id);
    setSingle(undefined);
    setFiles([]);
    setHasSpec(false);
    setLetters([]);
    setActivity([]);
    setLoadErr(false);
    setEditOpen(false);
  }

  useEffect(() => {
    if (!cases.find(x => x.id === id))
      void sb().from('cases').select('*').eq('id', id).maybeSingle().then(
        ({ data, error }) => {
          if (curId.current !== id) return;
          if (error) setLoadErr(true);
          setSingle((data as Case) || null);
        },
        () => {
          if (curId.current !== id) return;
          setLoadErr(true);
          setSingle(null);
        },
      );
  }, [id, cases, caseTry]);

  const reloadFiles = useCallback(async () => {
    try {
      const { data, error } = await sb().from('case_files').select('*').eq('case_id', id).order('version', { ascending: false }).order('created_at', { ascending: false });
      if (curId.current !== id) return;
      if (error) return setLoadErr(true);
      const rows = (data as CaseFile[]) || [];
      // internal kinds (spec) are never listed / downloaded anywhere in the app
      setHasSpec(rows.some(f => f.kind === 'spec'));
      setFiles(rows.filter(f => !isHiddenFile(f)));
    } catch {
      if (curId.current === id) setLoadErr(true);
    }
  }, [id]);
  const reloadLetters = useCallback(async () => {
    try {
      const { data, error } = await sb().from('letters').select('*').eq('case_id', id).order('created_at', { ascending: false });
      if (curId.current !== id) return;
      if (error) return setLoadErr(true);
      const rows = (data as Letter[]) || [];
      setLetters(rows);
      setCaseLetters(id, rows); // only this case's letters in the shared store (no full refetch)
    } catch {
      if (curId.current === id) setLoadErr(true);
    }
  }, [id, setCaseLetters]);
  const reloadActivity = useCallback(async () => {
    try {
      const { data, error } = await sb().from('activity').select('*').eq('case_id', id).order('at', { ascending: false }).limit(300);
      if (curId.current !== id) return;
      if (error) return setLoadErr(true);
      setActivity((data as Activity[]) || []);
    } catch {
      if (curId.current === id) setLoadErr(true);
    }
  }, [id]);
  const reloadMembers = useCallback(async () => {
    try {
      const { data, error } = await sb().from('members').select('user_id,email');
      if (error) return setLoadErr(true);
      setMembers(new Map(((data as Member[]) || []).map(m => [m.user_id, m.email])));
    } catch {
      setLoadErr(true);
    }
  }, []);

  const reloadAll = useCallback(async () => {
    setLoadErr(false);
    setReloading(true);
    setCaseTry(n => n + 1);
    await Promise.all([reloadFiles(), reloadLetters(), reloadActivity(), reloadMembers()]);
    if (curId.current === id) setReloading(false);
  }, [id, reloadFiles, reloadLetters, reloadActivity, reloadMembers]);

  useEffect(() => {
    void reloadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // When the latest run finishes, its outputs appear in case_files (not in the Realtime publication) → reload.
  // An edit run (सुधारणा) also stores new file versions when it ends.
  const latestState = runs?.[0]?.state;
  const latestEdit = editRuns?.[0] ? `${editRuns[0].id}:${editRuns[0].state}` : '';
  useEffect(() => {
    if (latestState === 'done' || latestState === 'failed' || /:(done|failed)$/.test(latestEdit)) {
      void reloadFiles();
      void reloadActivity();
    }
  }, [latestState, latestEdit, reloadFiles, reloadActivity]);
  useEffect(() => {
    void reloadActivity();
  }, [c?.stage, reloadActivity]);

  const overdue = useMemo(() => overdueIds(c ? [c] : [], allLetters), [c, allLetters]);
  const reloadBtn = (
    <button className="btn-primary" disabled={reloading} onClick={() => void reloadAll()}>{reloading && <Spinner />} ↻ पुन्हा लोड करा</button>
  );

  function onTabKey(e: KeyboardEvent<HTMLButtonElement>, i: number) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft' && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    const n = TABS.length;
    const j = e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : (i + (e.key === 'ArrowRight' ? 1 : -1) + n) % n;
    const k = TABS[j].k;
    setSp(k === 'brief' ? {} : { tab: k }, { replace: true });
    document.getElementById(`tab-${k}`)?.focus();
  }

  if (single === undefined && !c) return <div className="space-y-3"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-40 w-full" /></div>;
  if (!c)
    return loadErr ? (
      <div className="card" role="alert"><Empty icon="⚠️" title="माहिती आणता आली नाही — पुन्हा लोड करा" hint="इंटरनेट जोडणी तपासा.">{reloadBtn}</Empty></div>
    ) : (
      <div className="card"><Empty icon="❓" title="प्रकरण सापडले नाही" hint="यादीतून पुन्हा निवडा."><Link className="btn-ghost" to="/cases">प्रकरणे</Link></Empty></div>
    );

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

  // Title: C R of the case; else the C R in an output file name, marked as such — but not when the engine reported
  // that C R as a duplicate of another case (two cases would show the same heading, A3 audit)
  const hasDupNotice = activity.some(a => a.action === 'case_cr_duplicate');
  const fileCr = !c.cr_no && !hasDupNotice ? crFromFileName(files.find(f => /^CR\d+_\d{4}_/.test(f.original_name))?.original_name) : null;
  const title = c.cr_no ? crLabel(c) : fileCr || `प्रकरण #${c.id}`;
  const ctx: CaseCtx = { c, files, letters, activity, members, runs, editRuns, hasSpec, reloadFiles, reloadLetters, reloadActivity, canWrite, title };
  return (
    <div className="space-y-4">
      <div className="no-print">
        <Link to="/cases" className="text-sm font-semibold text-navy-600 hover:underline dark:text-navy-200">← प्रकरणे</Link>
      </div>
      {!c.cr_no && (() => {
        // engine found this C R/year on the निर्देशपत्र but it already belongs to another case
        const d = activity.find(a => a.action === 'case_cr_duplicate');
        const det = (d?.detail || {}) as { cr?: string; existing_id?: number };
        if (!d) return null;
        return (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100" role="alert">
            <div className="font-bold">PDF वरून C R {det.cr} सापडला, पण तो आधीच प्रकरण #{det.existing_id} मध्ये आहे.</div>
            <div className="mt-1 text-sm">एकच प्रकरण ठेवायचे असल्यास दुसऱ्याचा टप्पा “बंद” करा. योग्य C R माहीत असल्यास “✎ तपशील” मध्ये भरा.</div>
            {det.existing_id && <Link className="btn-ghost mt-2 inline-flex" to={`/cases/${det.existing_id}`}>प्रकरण #{det.existing_id} उघडा →</Link>}
          </div>
        );
      })()}
      <header className="card space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold">{title}{fileCr && <span className="ml-2 align-middle text-sm font-normal text-slate-500 dark:text-slate-400">(फाइलनावावरून)</span>}</h1>
              <Chip tone={WORK_TYPE_TONE[workTypeOf(c)]}>{workTypeLabel(c.work_type)}</Chip>
              <Chip tone={stageTone(c.stage)}>{c.stage}</Chip>
              {c.priority === 'तातडीचे' && <Chip tone="amber">तातडीचे</Chip>}
              {overdue.has(c.id) && <Chip tone="red">मुदत संपली</Chip>}
            </div>
            <p className={`mt-1 text-lg ${c.subject ? "" : "text-slate-600 dark:text-slate-300"}`}>{caseSubject(c, runs?.find(r => r.state === "done")?.summary)}</p>
          </div>
          {canWrite && (
            <div className="no-print flex flex-wrap gap-2">
              <select className="input w-auto" value={c.stage} onChange={e => void changeStage(e.target.value)} aria-label="टप्पा बदला">
                {STAGES.map(s => <option key={s}>{s}</option>)}
              </select>
              {hasSpec && (
                <Link to="?tab=note&edit=1" className="edit-cta inline-flex min-h-tap items-center gap-1.5 rounded-lg px-3 font-bold">
                  <span className="rounded-full bg-white px-1.5 text-sm font-black text-orange-600">AI</span> सुधारणा <span className="blink-dot" aria-hidden="true" />
                </Link>
              )}
              <button className="btn-ghost" onClick={() => setEditOpen(true)}>✎ तपशील</button>
            </div>
          )}
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
          {[
            ['विभाग / कार्यासन', deskLabel(c.desk)], ['नस्ती क्र.', c.file_no], ['प्रवर्ग', c.category], ['कार्यालय', c.office], ['कर्मचारी / पद', [c.employee_name, c.post].filter(Boolean).join(' / ')],
            ['प्राप्त', c.received_from], ['मार्ग', c.received_via === 'High Court' ? 'उच्च न्यायालयामार्फत' : c.received_via === 'direct' ? 'थेट' : null],
            ['आवक दिनांक', c.inward_date && fmtDate(c.inward_date)], ['मुदत', c.due_date && fmtDate(c.due_date)],
          ].map(([k, v]) => (
            <div key={k as string} className="min-w-0">
              <dt className="text-slate-500 dark:text-slate-400">{k}</dt>
              <dd className="break-words font-semibold sm:truncate" title={(v as string) || ''}>{v || '—'}</dd>
            </div>
          ))}
        </dl>
        <NastiLink c={c} canWrite={canWrite} onSaved={row => { patchLocal(row); setSingle(row); }} />
        <StudyWarningsLine run={runs?.find(r => r.state === 'done')} studyHref="?tab=study" className="no-print" />
      </header>

      {loadErr && (
        <div className="no-print flex flex-wrap items-center justify-between gap-3 rounded-lg bg-red-100 p-3 font-semibold text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">
          <span>माहिती आणता आली नाही — पुन्हा लोड करा</span>
          {reloadBtn}
        </div>
      )}

      <div className="no-print -mx-4 overflow-x-auto px-4">
        <div className="inline-flex min-w-full gap-1 border-b border-slate-200 dark:border-navy-800" role="tablist" aria-label="प्रकरणाचे भाग">
          {TABS.map((t, i) => (
            <button
              key={t.k}
              id={`tab-${t.k}`}
              role="tab"
              aria-selected={tab === t.k}
              aria-controls={`panel-${t.k}`}
              tabIndex={tab === t.k ? 0 : -1}
              onKeyDown={e => onTabKey(e, i)}
              className={`min-h-tap whitespace-nowrap border-b-4 px-3 font-semibold ${tab === t.k ? 'border-saffron-500 text-navy-800 dark:text-white' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
              onClick={() => setSp(t.k === 'brief' ? {} : { tab: t.k }, { replace: true })}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
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
    cr_no: x.cr_no || '', cr_year: x.cr_year ? String(x.cr_year) : '',
    file_no: x.file_no || '', subject: x.subject, category: x.category, priority: x.priority, employee_name: x.employee_name || '', post: x.post || '',
    office: x.office || '', received_from: x.received_from || '', received_via: x.received_via || '', inward_date: x.inward_date || '', due_date: x.due_date || '',
    desk: x.desk || DEFAULT_DESK, work_type: workTypeOf(x) as string,
  });
  const [f, setF] = useState(pick(c));
  const [busy, setBusy] = useState(false);
  const [dupId, setDupId] = useState<number | null>(null);
  const [err, setErr] = useState('');
  // reset from `c` only when the modal opens (false → true); a Realtime update must not wipe what is being typed
  const wasOpen = useRef(false);
  useEffect(() => {
    if (open && !wasOpen.current) { setF(pick(c)); setDupId(null); setErr(''); }
    wasOpen.current = open;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  const set = (k: keyof ReturnType<typeof pick>) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));

  const setDigits = (k: 'cr_no' | 'cr_year', max: number) => (e: { target: { value: string } }) =>
    setF(s => ({ ...s, [k]: e.target.value.replace(/\D/g, '').slice(0, max) }));

  // through the Worker (PATCH /api/cases/:id): C R / वर्ष get the same checks as a new case (digits, duplicate ignoring
  // leading zeros → link to the other case)
  async function save(e: FormEvent) {
    e.preventDefault();
    setDupId(null);
    setErr('');
    if (f.cr_year && !/^\d{4}$/.test(f.cr_year)) return setErr('वर्ष 4 अंकी लिहा (उदा. 2026)');
    if (!!f.cr_no !== !!f.cr_year) return setErr('C R क्र. व वर्ष दोन्ही भरा (किंवा दोन्ही रिकामे ठेवा)');
    setBusy(true);
    try {
      const row = await api<Case>(`/api/cases/${c.id}`, { method: 'PATCH', body: f });
      onSaved(row);
      toast('जतन केले');
      onClose();
    } catch (x) {
      if (x instanceof ApiError && x.message === 'duplicate_cr') setDupId(Number((x.data as { existing_id?: number } | undefined)?.existing_id) || null);
      setErr(humanError(x));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} onClose={onClose} title="प्रकरणाचा तपशील" wide>
      <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
        <div className="grid grid-cols-2 gap-3 sm:col-span-2">
          <Field label="C R क्र."><input className="input" inputMode="numeric" placeholder="उदा. 128" value={f.cr_no} onChange={setDigits('cr_no', 6)} /></Field>
          <Field label="वर्ष"><input className="input" inputMode="numeric" maxLength={4} placeholder="उदा. 2026" value={f.cr_year} onChange={setDigits('cr_year', 4)} /></Field>
        </div>
        <div className="sm:col-span-2"><Field label="विषय"><textarea className="input" value={f.subject ?? ''} onChange={set('subject')} /></Field></div>
        <div className="sm:col-span-2"><Field label="विभाग / कार्यासन"><select className="input" value={f.desk} onChange={set('desk')}>{DESKS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}</select></Field></div>
        <Field label="कामाचा प्रकार"><select className="input" value={f.work_type} onChange={set('work_type')}>{WORK_TYPES.map(w => <option key={w.id} value={w.id}>{w.label}</option>)}</select></Field>
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
        {err && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100 sm:col-span-2" role="alert">
            <div className="font-semibold">{err}</div>
            {dupId && <Link className="btn-ghost mt-2 inline-flex" to={`/cases/${dupId}`} onClick={onClose}>प्रकरण #{dupId} उघडा →</Link>}
          </div>
        )}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <button type="button" className="btn-ghost" onClick={onClose}>रद्द</button>
          <button className="btn-primary" disabled={busy}>{busy && <Spinner />} जतन करा</button>
        </div>
      </form>
    </Modal>
  );
}
