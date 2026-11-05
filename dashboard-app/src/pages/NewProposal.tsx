// नवीन प्रस्ताव. UI audit 04.11.2026 §3 (N1–N25): the form shows only what is required — 1. प्रस्ताव PDF (+ इतर फाइल),
// 2. कामाचा प्रकार व मसुदे, 3. the button; the optional identity fields sit in a closed "अधिक तपशील". After the start the form
// collapses into the status card (one summary line, the action button, "↺ दुसरा प्रस्ताव"); files are added to a created
// case only on the case page (N2: extra files picked here after the start were never uploaded).
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError, api, budgetReachedText, fmtUsd, getSpend, spendBlocked, uploadFile, type RunStart, type Spend } from '../lib/api';
import { useAuth, useCanWrite } from '../lib/auth';
import { CATEGORIES, DEFAULT_DESK, DEFAULT_WORK_TYPE, DESKS, INPUT_KINDS, INPUT_KIND_LABEL, PRIORITIES, WORK_TYPES, isStale, isWaiting, type DraftKey, type InputKind } from '../lib/constants';
import { draftLabels, sameDrafts, suggestDrafts } from '../lib/drafts';
import { fmtBytes } from '../lib/format';
import { guessSubject } from '../lib/pdf';
import type { Case, Run } from '../lib/types';
import { Field, Progress, Section, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import RunProgress, { useRuns } from '../components/RunProgress';
import { useRunsShownHere } from '../components/Layout';
import DraftPicker, { CompactDraftPicker } from '../components/DraftPicker';
import BulkUpload, { BULK_MAX, startText, userError } from '../components/BulkUpload';

const MAX = 50 * 1024 * 1024;
/** Types for the other files (the proposal has its own drop zone). */
const EXTRA_KINDS = INPUT_KINDS.filter(k => k !== 'proposal');
interface Extra { file: File; kind: InputKind }
interface Up { file: File; kind: InputKind; pct: number; state: 'wait' | 'up' | 'ok' | 'err'; err?: string }
const EMPTY_FORM = { cr_no: '', cr_year: '', file_no: '', subject: '', category: '', priority: 'सामान्य', desk: DEFAULT_DESK as string, work_type: DEFAULT_WORK_TYPE as string, instructions: '' };
const STAFF_BUDGET = 'या महिन्याची खर्च-मर्यादा संपली आहे. त्यामुळे नवीन प्रस्ताव सध्या पाठविता येणार नाही. कृपया मालकांना कळवावे.';
const isPdf = (x: File) => x.type === 'application/pdf' || /\.pdf$/i.test(x.name);

function DropZone({ label, hint, accept, multiple, onFiles }: { label: string; hint: string; accept: string; multiple?: boolean; onFiles: (f: File[]) => void }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const drop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    onFiles(Array.from(e.dataTransfer.files));
  };
  return (
    <div
      onDragOver={e => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
      className={`flex min-h-[110px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-4 text-center transition ${
        over ? 'border-saffron-500 bg-saffron-500/10' : 'border-slate-300 dark:border-navy-700'
      }`}
    >
      <div className="font-semibold">{label}</div>
      <div className="text-sm text-slate-500 dark:text-slate-400">{hint}</div>
      <button type="button" className="btn-ghost" onClick={() => ref.current?.click()}>फाइल निवडा</button>
      <input ref={ref} type="file" hidden accept={accept} multiple={multiple} onChange={e => { onFiles(Array.from(e.target.files || [])); e.target.value = ''; }} />
    </div>
  );
}

/** N17: why a picked main file is not taken. */
function notPdfText(files: File[]): string {
  if (files.some(x => /\.docx?$/i.test(x.name)))
    return 'Word फाइल मुख्य प्रस्ताव म्हणून घेता येत नाही. कृपया प्रस्तावाचा PDF निवडावा; Word फाइल खालील “इतर फाइल” मध्ये जोडता येईल.';
  if (files.some(x => /^image\//.test(x.type) || /\.(jpe?g|png|heic|webp)$/i.test(x.name)))
    return 'फोटो मुख्य प्रस्ताव म्हणून घेता येत नाही. कृपया आधी त्याचा PDF करावा (फोनवर: Scan / Print → PDF म्हणून जतन) व तो PDF निवडावा.';
  return 'मुख्य प्रस्ताव PDF स्वरूपात असावा. कृपया PDF फाइल निवडावी.';
}

export default function NewProposal() {
  const canWrite = useCanWrite();
  const isOwner = useAuth().me?.role === 'owner';
  const toast = useToast();
  // monthly spend limit: checked on open and again before upload (Worker also refuses /api/run with 402)
  const [spend, setSpend] = useState<Spend | null>(null);
  useEffect(() => {
    if (canWrite) void getSpend().then(setSpend, () => setSpend(null));
  }, [canWrite]);
  // same test as the Worker: spend + active runs at their estimate (reserved_usd)
  const overBudget = !!spend && spendBlocked(spend);
  const [proposal, setProposal] = useState<File | null>(null);
  const [mainErr, setMainErr] = useState('');
  const [extras, setExtras] = useState<Extra[]>([]);
  const [f, setF] = useState(EMPTY_FORM);
  const [moreOpen, setMoreOpen] = useState(false); // "अधिक तपशील" (N1)
  // C33: एक प्रस्ताव / अनेक प्रस्ताव (bulk) — kept in the URL (?bulk=1); several files picked in एक प्रस्ताव stay with that one proposal
  const [sp, setSp] = useSearchParams();
  const bulk = sp.get('bulk') === '1';
  const [queuedPos, setQueuedPos] = useState<number | null>(null);
  // "कोणते मसुदे हवेत?": follows the suggestion (from the file types) until the user changes a chip
  const suggestion = suggestDrafts(extras.map(x => ({ kind: x.kind })), [], f.work_type);
  const [drafts, setDraftsRaw] = useState<DraftKey[] | null>(null); // null = untouched → the suggestion
  const chosen = drafts ?? suggestion.keys;
  const setDrafts = (v: DraftKey[]) => setDraftsRaw(sameDrafts(v, suggestion.keys) ? null : v);
  const [busy, setBusy] = useState(false);
  const [ups, setUps] = useState<Up[]>([]);
  const [created, setCreated] = useState<Case | null>(null);
  const [runErr, setRunErr] = useState('');
  const [dupId, setDupId] = useState<number | null>(null); // C R/year already in another case
  const [pendingRun, setPendingRun] = useState<number | null>(null); // run dispatched; its Realtime row may not be here yet
  const runs = useRuns(created?.id ?? null);
  const run: Run | undefined = created ? runs?.[0] : undefined; // ignore the previous case after reset
  useRunsShownHere([created?.id]); // U9: the status card shows this run — not again in the global bar
  const statusRef = useRef<HTMLDivElement>(null);
  const dupRef = useRef<HTMLDivElement>(null);
  const yearRef = useRef<HTMLInputElement>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));
  // C R / वर्ष: digits only; "128/2026" typed or pasted in C R is split into C R and वर्ष
  const setCr = (e: { target: { value: string } }) => {
    const m = e.target.value.match(/^\D*(\d*)\s*[/\\-]\s*(\d*)/);
    if (m) {
      setF(s => ({ ...s, cr_no: m[1], cr_year: m[2].slice(0, 4) || s.cr_year }));
      if (!m[2]) yearRef.current?.focus(); // "128/" typed by hand → continue in वर्ष
    }
    else setF(s => ({ ...s, cr_no: e.target.value.replace(/\D/g, '') }));
  };
  const setYear = (e: { target: { value: string } }) => setF(s => ({ ...s, cr_year: e.target.value.replace(/\D/g, '').slice(0, 4) }));
  const done = run?.state === 'done';
  // locked from the moment /api/run answers (H3): a second tap cannot start a second paid run before Realtime delivers the row
  const running = (pendingRun !== null && run?.id !== pendingRun) || (!!run && (run.state === 'queued' || run.state === 'running') && !isStale(run));
  const failed = !!run && !done && !running;
  const upErr = ups.some(u => u.state === 'err');
  const canRetry = !!created && !busy && !running && !done && (failed || !!runErr || upErr || !run);

  // scroll to the status panel after it has rendered (created / ups set), not before
  const wantScroll = useRef(false);
  useEffect(() => {
    if (!wantScroll.current || !statusRef.current) return;
    wantScroll.current = false;
    statusRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [created, ups.length]);
  // N4: the duplicate notice sits above the button; bring it into view
  useEffect(() => {
    if (dupId != null) dupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [dupId]);

  if (!canWrite)
    return (
      <div className="card space-y-3 p-6 text-center">
        <div className="font-semibold">आपल्याला फक्त वाचण्याची परवानगी आहे.</div>
        <div className="text-slate-600 dark:text-slate-300">नवीन प्रस्ताव पाठविण्यासाठी लेखनाची परवानगी आवश्यक आहे. कृपया मालकांना तशी विनंती करावी.</div>
        <Link className="btn-ghost inline-flex" to="/cases">प्रकरणे पाहा →</Link>
      </div>
    );

  async function pickProposal(files: File[]) {
    const pdfs = files.filter(isPdf);
    // several files picked: they belong to THIS proposal (Abhi 04.11.2026) — the first PDF is the proposal, the rest
    // become its other files (type "इतर", changeable); never split into several proposals
    if (files.length > 1 && pdfs.length && !created) {
      const rest = files.filter(x => x !== pdfs[0] && /\.(pdf|docx?|jpe?g|png)$/i.test(x.name));
      if (rest.length) {
        addExtras(rest);
        toast(`“${pdfs[0].name}” हा प्रस्ताव; उरलेल्या ${rest.length} फाइल याच प्रस्तावाच्या इतर फाइल म्हणून जोडल्या. कृपया त्यांचा प्रकार तपासावा.`, 'info');
      }
    }
    const p = pdfs[0];
    if (!p) {
      const m = notPdfText(files);
      setMainErr(m);
      return toast(m, 'err');
    }
    if (p.size > MAX) {
      setMainErr('फाइल 50 MB पेक्षा मोठी आहे. कृपया लहान PDF निवडावा.');
      return toast('फाइल 50 MB पेक्षा मोठी आहे.', 'err');
    }
    setMainErr('');
    setProposal(p);
    if (!f.subject) {
      const s = await guessSubject(p);
      if (s) {
        setF(x => (x.subject ? x : { ...x, subject: s }));
        toast('विषय PDF वरून भरला आहे (अधिक तपशील). कृपया तपासावा.', 'info');
      }
    }
  }
  function addExtras(files: File[]) {
    const ok = files.filter(x => x.size <= MAX);
    if (ok.length < files.length) toast('50 MB पेक्षा मोठ्या फाइल वगळल्या आहेत.', 'err');
    setExtras(s => [...s, ...ok.map(file => ({ file, kind: 'extra_doc' as InputKind }))]);
  }

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!proposal) return toast('कृपया आधी प्रस्ताव PDF निवडावा.', 'err');
    setBusy(true);
    setRunErr('');
    try {
      const sp = await getSpend();
      setSpend(sp);
      if (spendBlocked(sp)) {
        toast(isOwner ? budgetReachedText(sp.limit_usd) : STAFF_BUDGET, 'err');
        setBusy(false);
        return; // nothing uploaded
      }
    } catch {
      /* spend check unavailable: the Worker still enforces the limit on /api/run */
    }
    // show the status panel (top of the page) once it is rendered — Abhi's request 01.11.2026 (effect below)
    wantScroll.current = true;
    try {
      let c = created;
      if (!c) {
        c = await api<Case>('/api/cases', {
          // every identity field is optional; empty ones are filled by the engine from the निर्देशपत्र
          body: Object.fromEntries(Object.entries({ cr_no: f.cr_no.trim(), cr_year: f.cr_year.trim() ? Number(f.cr_year) : '', file_no: f.file_no.trim(), subject: f.subject.trim(), category: f.category, priority: f.priority, desk: f.desk, work_type: f.work_type }).filter(([, v]) => v !== '')),
        });
        setCreated(c);
        setDupId(null);
      }
      const list: Up[] = [{ file: proposal, kind: 'proposal', pct: 0, state: 'wait' }, ...extras.map(x => ({ file: x.file, kind: x.kind, pct: 0, state: 'wait' as const }))];
      // a retry skips files already uploaded — matched by the File object itself, not by list position
      const prevOk = (u: Up) => ups.find(p => p.state === 'ok' && p.file === u.file && p.kind === u.kind);
      setUps(list.map(u => prevOk(u) ?? u));
      for (let i = 0; i < list.length; i++) {
        if (prevOk(list[i])) continue;
        setUps(s => s.map((u, j) => (j === i ? { ...u, state: 'up' } : u)));
        try {
          await uploadFile(c.id, list[i].kind, list[i].file, pct => setUps(s => s.map((u, j) => (j === i ? { ...u, pct } : u))));
          setUps(s => s.map((u, j) => (j === i ? { ...u, pct: 100, state: 'ok' } : u)));
        } catch (x) {
          setUps(s => s.map((u, j) => (j === i ? { ...u, state: 'err', err: userError(x, isOwner) } : u)));
          throw x;
        }
      }
      try {
        const started = await api<RunStart>('/api/run', { body: { case_id: c.id, instructions: f.instructions.trim() || undefined, outputs: chosen } });
        setPendingRun(started.id);
        setQueuedPos(started.queued ? Number(started.position) || null : null);
        toast(startText(started, isOwner));
      } catch (x) {
        if (x instanceof ApiError && x.message === 'run_active') {
          setPendingRun(Number((x.data as { run_id?: number } | undefined)?.run_id) || null);
          toast(userError(x, isOwner));
        } else setRunErr(userError(x, isOwner));
      }
    } catch (x) {
      if (x instanceof ApiError && x.message === 'duplicate_cr') {
        const id = Number((x.data as { existing_id?: number } | undefined)?.existing_id) || null;
        setDupId(id);
        setMoreOpen(true); // the C R / वर्ष fields are in "अधिक तपशील"
        toast(`हा C R आधीच प्रकरण क्र. ${id ?? '?'} मध्ये नोंदवलेला आहे.`, 'err');
        return;
      }
      toast(userError(x, isOwner), 'err');
    } finally {
      setBusy(false);
    }
  }

  // start a fresh proposal: clears this page only; the earlier case stays in प्रकरणे (Abhi, 01.11.2026)
  function reset() {
    setProposal(null);
    setMainErr('');
    setExtras([]);
    setDraftsRaw(null);
    setF(EMPTY_FORM);
    setMoreOpen(false);
    setQueuedPos(null);
    setUps([]);
    setCreated(null);
    setRunErr('');
    setPendingRun(null);
    setDupId(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  const modeToggle = (
    <div className="inline-flex rounded-lg border border-slate-300 p-0.5 dark:border-navy-700" role="group" aria-label="अपलोड पद्धत">
      {([['', 'एक प्रस्ताव'], ['1', `अनेक प्रस्ताव (कमाल ${BULK_MAX})`]] as const).map(([v, l]) => (
        <button key={v} type="button" aria-pressed={(v === '1') === bulk} disabled={busy || (!!v && !!created)}
          className={`min-h-tap rounded-md px-3 font-semibold ${(v === '1') === bulk ? 'bg-navy-700 text-white' : ''}`}
          onClick={() => setSp(v ? { bulk: '1' } : {}, { replace: true })}>{l}</button>
      ))}
    </div>
  );
  // N21: staff cannot start anything over the limit → the message replaces the form; the owner keeps the form + Settings link
  const budgetBox = overBudget && spend && (isOwner ? (
    <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">
      <div className="font-bold">{budgetReachedText(spend.limit_usd)}</div>
      <div className="mt-1 text-sm">या महिन्याचा खर्च {fmtUsd(spend.spent_usd)}{spend.reserved_usd ? ` + चालू प्रक्रिया (अंदाजे) ${fmtUsd(spend.reserved_usd)}` : ''} / {fmtUsd(spend.limit_usd)} • नवीन प्रक्रिया सुरू होणार नाही; चालू प्रक्रिया पूर्ण होतील.</div>
      <Link className="btn-primary mt-2 inline-flex" to="/settings">सेटिंग्ज उघडा →</Link>
    </div>
  ) : (
    <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">
      <div className="font-bold">{STAFF_BUDGET}</div>
      <div className="mt-1 text-sm">चालू प्रक्रिया पूर्ण होतील. तयार फाइल ‘प्रकरणे’ मध्ये मिळतील.</div>
    </div>
  ));
  const staffBlocked = overBudget && !isOwner;
  if (bulk)
    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold">नवीन प्रस्ताव</h1>
          {modeToggle}
        </div>
        {budgetBox}
        {!staffBlocked && <BulkUpload overBudget={overBudget} />}
      </div>
    );

  const caseTitle = created ? (created.cr_no ? `C R ${created.cr_no}/${created.cr_year ?? '____'}` : `प्रकरण क्र. ${created.id}`) : '';
  const waiting = !!run && isWaiting(run);
  const openCase = created && (
    <Link className="inline-flex min-h-tap items-center font-semibold text-navy-700 underline dark:text-navy-200" to={`/cases/${created.id}`}>प्रकरण उघडा →</Link>
  );
  const retryBtn = (
    <button type="button" className="btn-accent w-full text-lg" disabled={busy || overBudget} onClick={() => void submit()}>
      {busy && <Spinner />} {busy ? 'फाइल अपलोड होत आहे…' : '↻ पुन्हा तयार करा'}
    </button>
  );
  const disabledWhy = !proposal ? 'कृपया आधी प्रस्ताव PDF निवडावा.' : overBudget ? 'या महिन्याची खर्च-मर्यादा संपली आहे.' : '';

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">नवीन प्रस्ताव</h1>
        {modeToggle}
        {!created && (proposal || extras.length > 0) && (
          <button type="button" className="btn-ghost" onClick={reset} disabled={busy}>✕ निवड रद्द करा</button>
        )}
      </div>
      {budgetBox}

      {created && (
        <div ref={statusRef} className="scroll-mt-20">
          <Section title={`स्थिती — ${caseTitle}`}
            right={!busy && (done || running || canRetry) ? <button type="button" className="btn-ghost" onClick={reset}>↺ दुसरा प्रस्ताव</button> : undefined}>
            <div className="space-y-4">
              {/* N3: the collapsed form — one line */}
              <div className="min-w-0 rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-navy-800">
                <div className="break-words [overflow-wrap:anywhere]">
                  <span className="font-semibold">प्रस्ताव:</span> {proposal?.name}
                  {extras.length > 0 && <> • <span className="font-semibold">इतर फाइल:</span> {extras.length}</>}
                  {!canRetry && <> • <span className="font-semibold">मसुदे:</span> {draftLabels(chosen)}</>}
                </div>
                {canRetry && <div className="mt-1"><CompactDraftPicker value={chosen} onChange={setDrafts} disabled={busy} /></div>}
              </div>

              {runErr && (
                <div className="space-y-2 rounded-lg bg-red-100 px-3 py-2 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">
                  <div><span className="font-semibold">प्रक्रिया सुरू होऊ शकली नाही.</span> {runErr}</div>
                  {canRetry && retryBtn}
                </div>
              )}
              {/* N14: one amber line while the run waits for its turn */}
              {run && waiting ? (
                <div className="rounded-lg bg-amber-100 px-3 py-2 font-bold text-amber-900 dark:bg-amber-900/40 dark:text-amber-100" role="status">
                  ⏳ प्रतीक्षेत{queuedPos ? ` — क्रमांक ${queuedPos}` : ''}. आधीच्या प्रक्रियांपैकी एक पूर्ण झाल्यावर ही प्रक्रिया क्रमाने आपोआप सुरू होईल.
                </div>
              ) : run ? (
                <RunProgress run={run} retryHint={failed && canRetry ? 'कृपया खालील “↻ पुन्हा तयार करा” बटण दाबावे.' : undefined} />
              ) : !runErr && (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">{(busy || pendingRun !== null) && <Spinner className="h-4 w-4" />}{busy ? 'फाइल अपलोड होत आहे…' : pendingRun !== null ? 'प्रक्रिया सुरू होत आहे…' : 'प्रतीक्षा…'}</div>
              )}

              {ups.length > 0 && (
                <ul className="space-y-3">
                  {ups.map((u, i) => (
                    <li key={i} className="space-y-1">
                      <div className="flex justify-between gap-2 text-sm">
                        <span className="min-w-0 truncate">{u.file.name}</span>
                        <span className={`shrink-0 ${u.state === 'err' ? 'text-red-700 dark:text-red-400' : u.state === 'ok' ? 'text-green-700 dark:text-green-400' : ''}`}>
                          {u.state === 'ok' ? '✓ अपलोड पूर्ण' : u.state === 'err' ? '✕ अपलोड अयशस्वी' : u.state === 'up' ? `${u.pct}%` : 'प्रतीक्षा'}
                        </span>
                      </div>
                      {u.state === 'err' && u.err && <div className="break-words text-sm text-red-700 dark:text-red-400">{u.err}</div>}
                      <Progress pct={u.pct} tone={u.state === 'err' ? 'red' : u.state === 'ok' ? 'green' : 'blue'} />
                    </li>
                  ))}
                </ul>
              )}

              {/* the main button lives here after the start (N3) */}
              {done ? (
                <Link className="btn-accent flex w-full items-center justify-center py-3 text-xl" to={`/cases/${created.id}?tab=note`}>तयार फाइल पाहा →</Link>
              ) : canRetry && !runErr ? retryBtn : null}
              {(running || waiting) && (
                <p className="text-sm text-slate-600 dark:text-slate-300">हे पान बंद केले तरी काम चालू राहील. तयार झाल्यावर फाइल ‘प्रकरणे’ मध्ये या प्रकरणात मिळतील.</p>
              )}
              {/* N2: other files go to the created case on its own page */}
              <p className="flex flex-wrap items-center gap-x-2 text-sm text-slate-600 dark:text-slate-300">
                <span>या प्रकरणासाठी नवीन फाइल जोडायची असल्यास कृपया प्रकरण उघडून तेथे जोडावी.</span>
                {openCase}
              </p>
            </div>
          </Section>
        </div>
      )}

      {!created && !staffBlocked && (
        <form onSubmit={submit} className="space-y-5 [&>*]:min-w-0">
          <Section title="1. प्रस्ताव PDF (आवश्यक) व इतर फाइल">
            <div className="space-y-4">
              {proposal ? (
                <div className="flex items-center justify-between gap-2 rounded-lg bg-navy-50 px-3 py-2 dark:bg-navy-800">
                  <div className="min-w-0">
                    <div className="truncate font-semibold" title={proposal.name}>📄 {proposal.name}</div>
                    <div className="text-sm text-slate-500">{fmtBytes(proposal.size)}</div>
                  </div>
                  <button type="button" className="btn-ghost min-w-tap px-2" onClick={() => setProposal(null)} aria-label="प्रस्ताव PDF काढा" disabled={busy}>✕</button>
                </div>
              ) : (
                <>
                  <DropZone label="प्रस्ताव PDF येथे ओढा किंवा निवडा" hint="मुख्य PDF (हवे असल्यास त्याच प्रस्तावाच्या इतर फाइलसह) • कमाल 50 MB • फाइलनाव तेच राहील" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" multiple onFiles={pickProposal} />
                  {mainErr && <div className="rounded-lg bg-amber-100 px-3 py-2 text-sm font-semibold text-amber-900 dark:bg-amber-900/40 dark:text-amber-100" role="alert">{mainErr}</div>}
                </>
              )}
              <DropZone label="इतर फाइल (ऐच्छिक)" hint="उत्तर / मान्यता / न्यायालयीन नोटीस / इतर • PDF / Word / प्रतिमा • प्रकार खाली निवडावा" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" multiple onFiles={addExtras} />
              {extras.length > 0 && (
                <ul className="space-y-1">
                  {extras.map((x, i) => {
                    const other = x.kind === 'extra_doc';
                    const sg = suggestDrafts([{ kind: x.kind }], [], f.work_type);
                    return (
                      <li key={i} className="space-y-1 rounded-lg bg-slate-100 px-3 py-2 dark:bg-navy-800">
                        <div className="flex items-center justify-between gap-2">
                          <span className="min-w-0 truncate" title={x.file.name}>{x.file.name} <span className="text-sm text-slate-500">({fmtBytes(x.file.size)})</span></span>
                          {!busy && <button type="button" className="btn-ghost min-w-tap px-2" onClick={() => setExtras(s => s.filter((_, j) => j !== i))} aria-label="फाइल काढा">✕</button>}
                        </div>
                        <label className="flex items-center gap-2 text-sm">
                          <span className="shrink-0 font-semibold">प्रकार</span>
                          <select className="input min-h-tap min-w-0 py-1" disabled={busy} value={x.kind}
                            onChange={e => { const kind = e.target.value as InputKind; setExtras(s => s.map((y, j) => (j === i ? { ...y, kind } : y))); }}>
                            {EXTRA_KINDS.map(k => <option key={k} value={k}>{INPUT_KIND_LABEL[k]}</option>)}
                          </select>
                        </label>
                        {/* N7: how the type changes the suggestion */}
                        <div className={`rounded-md px-2 py-1 text-sm ${other ? 'bg-amber-100 font-semibold text-amber-900 dark:bg-amber-900/40 dark:text-amber-100' : 'text-slate-600 dark:text-slate-300'}`}>
                          {other
                            ? 'प्रकार “इतर”: सुचवलेले मसुदे बदलत नाहीत. ही फाइल उत्तर / मान्यता / न्यायालयीन नोटीस असल्यास कृपया तो प्रकार निवडावा.'
                            : `या प्रकारामुळे सुचवलेले मसुदे: ${draftLabels(sg.keys)} (${sg.reason}).`}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </Section>

          <Section title="2. कामाचा प्रकार व मसुदे">
            <div className="space-y-4">
              <Field label="कामाचा प्रकार">
                <select className="input" disabled={busy} value={f.work_type} onChange={set('work_type')}>{WORK_TYPES.map(w => <option key={w.id} value={w.id}>{w.label}</option>)}</select>
              </Field>
              <DraftPicker value={chosen} onChange={setDrafts} suggestion={suggestion} disabled={busy} />
            </div>
          </Section>

          <details className="card group" open={moreOpen} onToggle={e => setMoreOpen((e.currentTarget as HTMLDetailsElement).open)}>
            <summary className="flex min-h-tap cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 font-bold">
              <span>अधिक तपशील <span className="font-normal text-slate-500 dark:text-slate-400">(ऐच्छिक — रिकामे ठेवल्यास PDF वरून आपोआप भरले जाईल)</span></span>
              <span aria-hidden="true" className="shrink-0">{moreOpen ? '▲' : '▼'}</span>
            </summary>
            <div className="space-y-4 border-t border-slate-200 p-4 dark:border-navy-800">
              <div className="grid grid-cols-2 gap-3">
                <Field label="C R क्र."><input className="input" inputMode="numeric" placeholder="उदा. 128" disabled={busy} value={f.cr_no} onChange={setCr} /></Field>
                <Field label="वर्ष"><input ref={yearRef} className="input" inputMode="numeric" maxLength={4} placeholder="PDF वरून" disabled={busy} value={f.cr_year} onChange={setYear} /></Field>
              </div>
              <Field label="नस्ती क्र. (निर्देशपत्र)"><input className="input" placeholder={DESKS.find(d => d.id === f.desk)?.fileNo} disabled={busy} value={f.file_no} onChange={set('file_no')} /></Field>
              <Field label="विषय"><textarea className="input min-h-[96px]" placeholder="रिकामे ठेवल्यास PDF वरून भरला जाईल" disabled={busy} value={f.subject} onChange={set('subject')} /></Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="प्रवर्ग">
                  <select className="input" disabled={busy} value={f.category} onChange={set('category')}><option value="">PDF वरून ठरेल</option>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
                </Field>
                <Field label="प्राधान्य">
                  <select className="input" disabled={busy} value={f.priority} onChange={set('priority')}>{PRIORITIES.map(c => <option key={c}>{c}</option>)}</select>
                </Field>
              </div>
              <Field label="विभाग / कार्यासन" hint="टिप्पणी व पत्राची रचना (शीर्ष, सही-साखळी, पत्राचा क्रमांक) या कार्यासनाप्रमाणे होते.">
                <select className="input" disabled={busy} value={f.desk} onChange={set('desk')}>{DESKS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}</select>
              </Field>
              <Field label="विशेष सूचना (ऐच्छिक)" hint="येथे लिहिलेली सूचना प्रक्रियेत पाळली जाते (कायमच्या नियमांच्या मर्यादेत). रिकामे ठेवल्यास नेहमीप्रमाणे.">
                <textarea className="input min-h-[96px]" value={f.instructions} onChange={set('instructions')} disabled={busy}
                  placeholder={'उदा. • पत्रात फक्त सेवापुस्तकाची प्रत मागवावी\n• पत्र नको; नस्ती वित्त विभागाकडे पाठवावी\n• पान 7 वरील हस्तलिखित शेरा नीट वाचावा'} />
              </Field>
            </div>
          </details>

          <section className="card space-y-3 p-4">
            {dupId != null && (
              <div ref={dupRef} className="scroll-mt-20 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100" role="alert">
                <div className="font-bold">हा C R क्र. / वर्ष आधीच प्रकरण क्र. {dupId} मध्ये नोंदवलेला आहे.</div>
                <div className="mt-1 text-sm">तेच प्रकरण पुढे न्यायचे असल्यास कृपया ते उघडून तेथे “पुन्हा तयार करा” वापरावे. नवीन प्रकरण हवे असल्यास C R व वर्ष रिकामे ठेवून बटण पुन्हा दाबावे.</div>
                <Link className="btn-primary mt-2 inline-flex" to={`/cases/${dupId}`}>प्रकरण क्र. {dupId} उघडा →</Link>
              </div>
            )}
            <h2 className="text-base font-bold">3. प्रक्रिया सुरू करा</h2>
            <button className="btn-accent w-full text-lg" disabled={busy || !proposal || overBudget} aria-describedby={disabledWhy ? 'np-why' : undefined}>
              {busy && <Spinner />} {busy ? 'फाइल अपलोड होत आहे…' : 'टिप्पणी व मसुदे तयार करा'}
            </button>
            {disabledWhy && !busy && <p id="np-why" className="text-center text-sm font-semibold text-slate-600 dark:text-slate-300">{disabledWhy}</p>}
            <p className="text-sm text-slate-500 dark:text-slate-400">हे पान बंद केले तरी काम चालू राहील. तयार झाल्यावर फाइल ‘प्रकरणे’ मध्ये या प्रकरणात मिळतील.</p>
          </section>
        </form>
      )}
      {!created && staffBlocked && (
        <Link className="btn-ghost inline-flex" to="/cases">प्रकरणे पाहा →</Link>
      )}
    </div>
  );
}
