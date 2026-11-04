import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { useData, isPendingLetter } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import { CATEGORIES, DEFAULT_DESK, DESKS, PRIORITIES, STAGES, WORK_TYPES, WORK_TYPE_TONE, deskLabel, isEditRun, isHiddenFile, stageTone, workTypeLabel, workTypeOf } from '../lib/constants';
import { caseSubject, crFromFileName, crLabel, fmtDate, studyWarningTexts, todayISO } from '../lib/format';
import { ApiError, api, humanError } from '../lib/api';
import type { Activity, Case, CaseFile, Letter, Member, Run } from '../lib/types';
import { Chip, Empty, Field, Modal, Skeleton, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import { useRuns } from '../components/RunProgress';
import NastiLink from '../components/NastiLink';
import { BriefingTab, DownloadStrip, HistoryTab, LettersTab, NoteTab, PackageTab, StudyTab } from './CaseTabs';

// `short`: phone labels (3 x 2 grid, all six visible — UI audit C3)
const TABS = [
  { k: 'brief', label: 'ब्रीफिंग', short: 'ब्रीफिंग' },
  { k: 'note', label: 'टिप्पणी व पत्र', short: 'टिप्पणी' },
  { k: 'pdf', label: 'GR सह प्रस्ताव (PDF)', short: 'PDF' },
  { k: 'study', label: 'अभ्यास-फाइल', short: 'अभ्यास' },
  { k: 'letters', label: 'पत्रव्यवहार', short: 'पत्रे' },
  { k: 'history', label: 'इतिहास', short: 'इतिहास' },
] as const;

/** "AI सुधारणा" pulses only until the सुधारणा-चॅट is first used in this browser (same key as EditChat). */
const EDIT_SEEN_KEY = 'edit_chat_seen';
const readSeen = () => { try { return localStorage.getItem(EDIT_SEEN_KEY) === '1'; } catch { return false; } };

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
  /** the case's display title (C R, or C R from the file name, or प्रकरण क्र. id) — same as the page header */
  title: string;
}

export default function CaseDetail() {
  const id = Number(useParams().id);
  const { cases, letters: allLetters, setStage, patchLocal, setCaseLetters } = useData();
  const canWrite = useCanWrite();
  const [detailsOpen, setDetailsOpen] = useState(false); // phone only: "प्रकरणाचा तपशील ▼" (always open from sm up)
  const [editSeen, setEditSeen] = useState(readSeen);
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
    setDetailsOpen(false);
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
      // '*': members.display_name exists only after migration 0012 (a missing column must not break the read)
      const { data, error } = await sb().from('members').select('*');
      if (error) return setLoadErr(true);
      setMembers(new Map(((data as (Member & { display_name?: string | null })[]) || []).map(m => [m.user_id, (m.display_name || '').trim() || m.email])));
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

  // C15: a passed case due date and a passed letter reply date are told apart (the letter one links to the letters tab)
  const today = todayISO();
  const caseOverdue = !!c && !!c.due_date && c.due_date < today && c.stage !== 'बंद';
  const letterOverdue = useMemo(
    () => !!c && [...letters, ...allLetters.filter(l => l.case_id === c.id)].some(l => isPendingLetter(l) && !!l.reply_due && l.reply_due < today),
    [c, letters, allLetters, today],
  );
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
      <div className="card" role="alert"><Empty icon="⚠️" title="माहिती आणता आली नाही" hint="कृपया इंटरनेट जोडणी तपासून पुन्हा लोड करावे.">{reloadBtn}</Empty></div>
    ) : (
      <div className="card"><Empty icon="❓" title="प्रकरण सापडले नाही" hint="कृपया प्रकरणांच्या यादीतून पुन्हा निवडावे."><Link className="btn-ghost" to="/cases">प्रकरणे</Link></Empty></div>
    );

  async function changeStage(s: string) {
    try {
      if (cases.find(x => x.id === id)) await setStage(id, s);
      else {
        const { error } = await sb().from('cases').update({ stage: s }).eq('id', id);
        if (error) throw new Error(error.message);
        setSingle(x => (x ? { ...x, stage: s } : x));
      }
      toast(`टप्पा बदलला: ${s}`);
    } catch (e) {
      toast(humanError(e), 'err');
    }
  }

  // Title: C R of the case; else the C R in an output file name, marked as such — but not when the engine reported
  // that C R as a duplicate of another case (two cases would show the same heading, A3 audit)
  const hasDupNotice = activity.some(a => a.action === 'case_cr_duplicate');
  const fileCr = !c.cr_no && !hasDupNotice ? crFromFileName(files.find(f => /^CR\d+_\d{4}_/.test(f.original_name))?.original_name) : null;
  const title = c.cr_no ? crLabel(c) : fileCr || `प्रकरण क्र. ${c.id}`;
  const ctx: CaseCtx = { c, files, letters, activity, members, runs, editRuns, hasSpec, reloadFiles, reloadLetters, reloadActivity, canWrite, title };
  const lastDone = runs?.find(r => r.state === 'done');
  const nWarn = lastDone ? studyWarningTexts(lastDone.warnings).length : 0;
  // C2: empty fields are not shown ("—" rows only took space)
  const facts = ([
    ['विभाग / कार्यासन', deskLabel(c.desk)], ['नस्ती क्र.', c.file_no], ['प्रवर्ग', c.category], ['कार्यालय', c.office], ['कर्मचारी / पद', [c.employee_name, c.post].filter(Boolean).join(' / ')],
    ['प्राप्त', c.received_from], ['मार्ग', c.received_via === 'High Court' ? 'उच्च न्यायालयामार्फत' : c.received_via === 'direct' ? 'थेट' : null],
    ['आवक दिनांक', c.inward_date && fmtDate(c.inward_date)], ['मुदत', c.due_date && fmtDate(c.due_date)],
  ] as [string, string | null | undefined][]).filter(([, v]) => !!v && v !== '—');
  const dup = !c.cr_no ? activity.find(a => a.action === 'case_cr_duplicate') : undefined;
  const dupDet = (dup?.detail || {}) as { cr?: string; existing_id?: number };
  const dupCr = dupDet.cr ? `C R ${String(dupDet.cr)}` : '';
  const dupOther = dupDet.existing_id ? cases.find(x => x.id === Number(dupDet.existing_id)) : undefined;
  const dupOtherLabel = dupOther?.cr_no ? crLabel(dupOther) : dupCr || (dupDet.existing_id ? `प्रकरण क्र. ${dupDet.existing_id}` : '');
  const openEdit = () => {
    if (!editSeen) { setEditSeen(true); try { localStorage.setItem(EDIT_SEEN_KEY, '1'); } catch { /* storage blocked */ } }
  };
  return (
    <div className="space-y-4">
      <div className="no-print">
        <Link to="/cases" className="inline-flex min-h-tap items-center text-sm font-semibold text-navy-600 hover:underline dark:text-navy-200">← प्रकरणे</Link>
      </div>
      {dup && (
        // C6: the engine found this C R/year on the निर्देशपत्र, but it already belongs to another case
        <div className="no-print rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100" role="alert">
          <div className="font-bold">{dupCr ? `हा प्रस्ताव ${dupCr} चा आहे — हे प्रकरण आधीच नोंदवलेले आहे` : 'हा प्रस्ताव आधीच नोंदवलेल्या प्रकरणाचा आहे'}</div>
          <div className="mt-1 text-sm">एकाच प्रस्तावाची दोन प्रकरणे झाली आहेत. कृपया जुने प्रकरण उघडून पाहावे; हे नवीन प्रकरण आवश्यक नसल्यास त्याचा टप्पा “बंद” ठेवावा.</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {dupDet.existing_id && <Link className="btn-ghost" to={`/cases/${dupDet.existing_id}`}>{dupOtherLabel} उघडा →</Link>}
            {canWrite && c.stage !== 'बंद' && <button className="btn-ghost" onClick={() => void changeStage('बंद')}>हे प्रकरण बंद करावे</button>}
          </div>
        </div>
      )}
      <header className="card space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold">{title}{fileCr && <span className="ml-2 align-middle text-sm font-normal text-slate-500 dark:text-slate-400">(फाइलनावावरून)</span>}</h1>
              <span className="hidden sm:inline-flex"><Chip tone={WORK_TYPE_TONE[workTypeOf(c)]}>{workTypeLabel(c.work_type)}</Chip></span>
              <Chip tone={stageTone(c.stage)}>{c.stage}</Chip>
              {c.priority === 'तातडीचे' && <Chip tone="amber">तातडीचे</Chip>}
              {caseOverdue && <Chip tone="red">मुदत संपली</Chip>}
              {letterOverdue && (
                <Link to="?tab=letters" className="no-print inline-flex min-h-tap items-center underline-offset-2 hover:underline"><span className="chip bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100">उत्तराची मुदत संपली (पत्र)</span></Link>
              )}
            </div>
            <p className={`mt-1 text-lg ${c.subject ? '' : 'text-slate-600 dark:text-slate-300'}`}>{caseSubject(c, lastDone?.summary)}</p>
            {nWarn > 0 && (
              <Link to="?tab=study" className="no-print mt-1 inline-flex min-h-tap max-w-full items-center underline-offset-2 hover:underline">
                <span className="chip bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">⚠ वापरण्यापूर्वी {nWarn} मुद्दे तपासावेत (अभ्यास-फाइल, भाग 7)</span>
              </Link>
            )}
          </div>
        </div>
        <DownloadStrip
          ctx={ctx}
          after={canWrite && hasSpec && (
            // C4: the one edit entry on the case page; pulses only until the सुधारणा-चॅट is first used
            <Link to="?tab=note&edit=1" onClick={openEdit} className="edit-cta inline-flex min-h-tap min-w-0 items-center justify-center gap-1.5 rounded-lg px-3 font-bold" style={editSeen ? { animation: 'none' } : undefined}>
              <span className="rounded-full bg-white px-1.5 text-sm font-black text-orange-600">AI</span> सुधारणा {!editSeen && <span className="blink-dot" aria-hidden="true" />}
            </Link>
          )}
        />
        <button type="button" className="no-print flex min-h-tap w-full items-center justify-between rounded-lg border border-slate-200 px-3 font-semibold text-navy-700 dark:border-navy-800 dark:text-navy-100 sm:hidden"
          aria-expanded={detailsOpen} aria-controls="case-details" onClick={() => setDetailsOpen(o => !o)}>
          प्रकरणाचा तपशील <span aria-hidden="true">{detailsOpen ? '▲' : '▼'}</span>
        </button>
        <div id="case-details" className={`space-y-3 ${detailsOpen ? '' : 'hidden'} sm:block`}>
          {canWrite && (
            <div className="no-print flex flex-wrap items-center gap-2">
              <label className="flex min-w-0 items-center gap-2 text-sm">
                <span className="shrink-0 font-semibold text-slate-600 dark:text-slate-300">टप्पा</span>
                <select className="input w-auto min-w-0" value={c.stage} onChange={e => void changeStage(e.target.value)} aria-label="टप्पा बदलावा">
                  {STAGES.map(s => <option key={s}>{s}</option>)}
                </select>
              </label>
              <button className="btn-ghost" onClick={() => setEditOpen(true)}>✎ तपशील बदलावा</button>
            </div>
          )}
          <div className="sm:hidden"><Chip tone={WORK_TYPE_TONE[workTypeOf(c)]}>{workTypeLabel(c.work_type)}</Chip></div>
          {facts.length > 0 && (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
              {facts.map(([k, v]) => (
                <div key={k} className="min-w-0">
                  <dt className="text-slate-500 dark:text-slate-400">{k}</dt>
                  <dd className="break-words font-semibold sm:truncate" title={v || ''}>{v}</dd>
                </div>
              ))}
            </dl>
          )}
          <NastiLink c={c} canWrite={canWrite} onSaved={row => { patchLocal(row); setSingle(row); }} />
        </div>
      </header>

      {loadErr && (
        <div className="no-print flex flex-wrap items-center justify-between gap-3 rounded-lg bg-red-100 p-3 font-semibold text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">
          <span>माहिती आणता आली नाही — पुन्हा लोड करा</span>
          {reloadBtn}
        </div>
      )}

      <div className="no-print">
        <div className="grid grid-cols-3 gap-1 sm:flex sm:gap-1 sm:border-b sm:border-slate-200 dark:sm:border-navy-800" role="tablist" aria-label="प्रकरणाचे भाग">
          {TABS.map((t, i) => (
            <button
              key={t.k}
              id={`tab-${t.k}`}
              role="tab"
              aria-selected={tab === t.k}
              aria-controls={`panel-${t.k}`}
              aria-label={t.label}
              tabIndex={tab === t.k ? 0 : -1}
              onKeyDown={e => onTabKey(e, i)}
              className={`min-h-tap rounded-lg px-2 font-semibold sm:whitespace-nowrap sm:rounded-none sm:border-b-4 sm:px-3 ${tab === t.k
                ? 'bg-navy-700 text-white sm:border-saffron-500 sm:bg-transparent sm:text-navy-800 dark:sm:text-white'
                : 'bg-slate-100 text-slate-700 hover:text-slate-900 dark:bg-navy-800 dark:text-slate-200 sm:border-transparent sm:bg-transparent sm:text-slate-500 dark:sm:bg-transparent dark:hover:text-slate-200'}`}
              onClick={() => setSp(t.k === 'brief' ? {} : { tab: t.k }, { replace: true })}
            >
              <span className="sm:hidden">{t.short}</span><span className="hidden sm:inline">{t.label}</span>
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
    if (f.cr_year && !/^\d{4}$/.test(f.cr_year)) return setErr('कृपया वर्ष 4 अंकी लिहावे (उदा. 2026).');
    if (!!f.cr_no !== !!f.cr_year) return setErr('कृपया C R क्र. व वर्ष दोन्ही भरावेत (किंवा दोन्ही रिकामे ठेवावेत).');
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
            {dupId && <Link className="btn-ghost mt-2 inline-flex" to={`/cases/${dupId}`} onClick={onClose}>प्रकरण क्र. {dupId} उघडा →</Link>}
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
