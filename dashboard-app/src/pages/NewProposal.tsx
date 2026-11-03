import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api, budgetReachedText, fmtUsd, getSpend, humanError, spendBlocked, uploadFile, type Spend } from '../lib/api';
import { useAuth, useCanWrite } from '../lib/auth';
import { CATEGORIES, DEFAULT_DESK, DESKS, INPUT_KINDS, INPUT_KIND_LABEL, PRIORITIES, isStale, type DraftKey, type InputKind } from '../lib/constants';
import { sameDrafts, suggestDrafts } from '../lib/drafts';
import { crLabel, fmtBytes } from '../lib/format';
import { guessSubject } from '../lib/pdf';
import type { Case, Run } from '../lib/types';
import { Field, Progress, Section, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import RunProgress, { useRuns } from '../components/RunProgress';
import DraftPicker from '../components/DraftPicker';

const MAX = 50 * 1024 * 1024;
/** Types for the other files (the proposal has its own drop zone). */
const EXTRA_KINDS = INPUT_KINDS.filter(k => k !== 'proposal');
interface Extra { file: File; kind: InputKind }
interface Up { file: File; kind: InputKind; pct: number; state: 'wait' | 'up' | 'ok' | 'err'; err?: string }

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
      className={`flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-4 text-center transition ${
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
  const [extras, setExtras] = useState<Extra[]>([]);
  const [f, setF] = useState({ cr_no: '', cr_year: '', file_no: '', subject: '', category: '', priority: 'सामान्य', desk: DEFAULT_DESK as string, instructions: '' });
  // "कोणते मसुदे हवेत?": follows the suggestion (from the file types) until the user changes a chip
  const suggestion = suggestDrafts(extras.map(x => ({ kind: x.kind })), []);
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
  const statusRef = useRef<HTMLDivElement>(null);
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

  // scroll to the status panel after it has rendered (created / ups set), not before
  const wantScroll = useRef(false);
  useEffect(() => {
    if (!wantScroll.current || !statusRef.current) return;
    wantScroll.current = false;
    statusRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [created, ups.length]);

  if (!canWrite) return <div className="card p-6 text-center">आपल्याला फक्त वाचण्याची परवानगी आहे.</div>;

  async function pickProposal(files: File[]) {
    const p = files.find(x => x.type === 'application/pdf' || /\.pdf$/i.test(x.name));
    if (!p) {
      const photo = files.some(x => /^image\//.test(x.type) || /\.(jpe?g|png|heic|webp)$/i.test(x.name));
      return toast(photo ? 'फोटो असल्यास आधी PDF करा (फोनवर: Scan / Print → PDF म्हणून जतन) व तो PDF निवडा' : 'प्रस्ताव PDF असावा', 'err');
    }
    if (p.size > MAX) return toast('फाइल 50 MB पेक्षा मोठी', 'err');
    setProposal(p);
    if (!f.subject) {
      const s = await guessSubject(p);
      if (s) {
        setF(x => (x.subject ? x : { ...x, subject: s }));
        toast('विषय PDF मधून भरला — तपासा', 'info');
      }
    }
  }
  function addExtras(files: File[]) {
    const ok = files.filter(x => x.size <= MAX);
    if (ok.length < files.length) toast('50 MB पेक्षा मोठ्या फाइल वगळल्या', 'err');
    setExtras(s => [...s, ...ok.map(file => ({ file, kind: 'extra_doc' as InputKind }))]);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!proposal) return toast('प्रस्ताव PDF निवडा', 'err');
    setBusy(true);
    setRunErr('');
    try {
      const sp = await getSpend();
      setSpend(sp);
      if (spendBlocked(sp)) {
        toast(budgetReachedText(sp.limit_usd), 'err');
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
          body: Object.fromEntries(Object.entries({ cr_no: f.cr_no.trim(), cr_year: f.cr_year.trim() ? Number(f.cr_year) : '', file_no: f.file_no.trim(), subject: f.subject.trim(), category: f.category, priority: f.priority, desk: f.desk }).filter(([, v]) => v !== '')),
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
          setUps(s => s.map((u, j) => (j === i ? { ...u, state: 'err', err: humanError(x) } : u)));
          throw x;
        }
      }
      try {
        const started = await api<{ id: number; outputs_dropped?: boolean }>('/api/run', { body: { case_id: c.id, instructions: f.instructions.trim() || undefined, outputs: chosen } });
        setPendingRun(started.id);
        toast(started.outputs_dropped ? 'अभ्यास सुरू झाला — मसुदे-निवड लागू झाली नाही (migration 0008 बाकी)' : 'अभ्यास सुरू झाला');
      } catch (x) {
        if (x instanceof ApiError && x.message === 'run_active') {
          setPendingRun(Number((x.data as { run_id?: number } | undefined)?.run_id) || null);
          toast(humanError(x));
        } else setRunErr(humanError(x));
      }
    } catch (x) {
      if (x instanceof ApiError && x.message === 'duplicate_cr') {
        const id = Number((x.data as { existing_id?: number } | undefined)?.existing_id) || null;
        setDupId(id);
        toast(`हा C R आधीच प्रकरण #${id ?? '?'} मध्ये आहे`, 'err');
        return;
      }
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }

  const locked = !!created;
  // start a fresh proposal: clears this page only; the earlier case stays in प्रकरणे (Abhi, 01.11.2026)
  function reset() {
    setProposal(null);
    setExtras([]);
    setDraftsRaw(null);
    setF({ cr_no: '', cr_year: '', file_no: '', subject: '', category: '', priority: 'सामान्य', desk: DEFAULT_DESK as string, instructions: '' });
    setUps([]);
    setCreated(null);
    setRunErr('');
    setPendingRun(null);
    setDupId(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">नवीन प्रस्ताव</h1>
        {(proposal || created || ups.length > 0) && (
          <button type="button" className="btn-ghost" onClick={reset} disabled={busy} title="हे पान रिकामे करा; आधीचे प्रकरण प्रकरणे मध्ये राहील">
            ↺ रीसेट — नवीन प्रस्ताव
          </button>
        )}
      </div>
      {overBudget && spend && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">
          <div className="font-bold">{isOwner ? budgetReachedText(spend.limit_usd) : `या महिन्याची खर्च-मर्यादा (${fmtUsd(spend.limit_usd)}) संपली — मालकाने सेटिंग्जमध्ये मर्यादा वाढवावी`}</div>
          <div className="mt-1 text-sm">या महिन्याचा खर्च {fmtUsd(spend.spent_usd)}{spend.reserved_usd ? ` + चालू प्रक्रिया (अंदाजे) ${fmtUsd(spend.reserved_usd)}` : ''} / {fmtUsd(spend.limit_usd)} • नवीन प्रक्रिया सुरू होणार नाही; चालू प्रक्रिया पूर्ण होतील.</div>
          {isOwner && <Link className="btn-primary mt-2 inline-flex" to="/settings">सेटिंग्ज उघडा →</Link>}
        </div>
      )}
      {(ups.length > 0 || created) && (
        <div ref={statusRef} className="scroll-mt-4">
          <Section title={created ? `स्थिती — ${crLabel(created)}` : 'स्थिती'} right={created ? <Link className="btn-ghost" to={`/cases/${created.id}`}>प्रकरण उघडा →</Link> : undefined}>
            <div className="space-y-4">
              {runErr && <div className="rounded-lg bg-red-100 px-3 py-2 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">अभ्यास सुरू झाला नाही: {runErr}</div>}
              {run ? <RunProgress run={run} /> : !runErr && <div className="text-slate-500">{busy ? 'फाइल अपलोड होत आहे…' : 'प्रतीक्षा…'}</div>}
              {ups.length > 0 && (
                <ul className="space-y-3">
                  {ups.map((u, i) => (
                    <li key={i} className="space-y-1">
                      <div className="flex justify-between gap-2 text-sm">
                        <span className="truncate">{u.file.name}</span>
                        <span className={u.state === 'err' ? 'text-red-700' : u.state === 'ok' ? 'text-green-700 dark:text-green-400' : ''}>
                          {u.state === 'ok' ? '✓ अपलोड पूर्ण' : u.state === 'err' ? u.err : u.state === 'up' ? `${u.pct}%` : 'प्रतीक्षा'}
                        </span>
                      </div>
                      <Progress pct={u.pct} tone={u.state === 'err' ? 'red' : u.state === 'ok' ? 'green' : 'blue'} />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Section>
        </div>
      )}
      <form onSubmit={submit} className="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
        <Section title="फाइल">
          <div className="space-y-4">
            {proposal ? (
              <div className="flex items-center justify-between gap-2 rounded-lg bg-navy-50 px-3 py-2 dark:bg-navy-800">
                <div className="min-w-0">
                  <div className="truncate font-semibold" title={proposal.name}>📄 {proposal.name}</div>
                  <div className="text-sm text-slate-500">{fmtBytes(proposal.size)}</div>
                </div>
                {!locked && <button type="button" className="btn-ghost min-w-tap px-2" onClick={() => setProposal(null)} aria-label="काढा">✕</button>}
              </div>
            ) : (
              <DropZone label="प्रस्ताव PDF येथे ओढा" hint="एकच PDF • कमाल 50 MB • फाइलनाव जसेच्या तसे राहील • फोटो असल्यास आधी PDF करा" accept="application/pdf,.pdf" onFiles={pickProposal} />
            )}
            <DropZone label="इतर फाइल (ऐच्छिक)" hint="उत्तर / मान्यता / न्यायालयीन नोटीस / इतर • PDF / Word / प्रतिमा • प्रकार खाली निवडा" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" multiple onFiles={addExtras} />
            {extras.length > 0 && (
              <ul className="space-y-1">
                {extras.map((x, i) => (
                  <li key={i} className="space-y-1 rounded-lg bg-slate-100 px-3 py-2 dark:bg-navy-800">
                    <div className="flex items-center justify-between gap-2">
                      <span className="min-w-0 truncate" title={x.file.name}>{x.file.name} <span className="text-sm text-slate-500">({fmtBytes(x.file.size)})</span></span>
                      {!busy && !locked && <button type="button" className="btn-ghost min-w-tap px-2" onClick={() => setExtras(s => s.filter((_, j) => j !== i))} aria-label="काढा">✕</button>}
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                      <span className="shrink-0 font-semibold">प्रकार</span>
                      <select className="input min-h-tap py-1" disabled={busy || locked} value={x.kind}
                        onChange={e => { const kind = e.target.value as InputKind; setExtras(s => s.map((y, j) => (j === i ? { ...y, kind } : y))); }}>
                        {EXTRA_KINDS.map(k => <option key={k} value={k}>{INPUT_KIND_LABEL[k]}</option>)}
                      </select>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Section>

        {dupId != null && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100 lg:col-span-2" role="alert">
            <div className="font-bold">हा C R क्र. / वर्ष आधीच प्रकरण #{dupId} मध्ये नोंदलेला आहे.</div>
            <div className="mt-1 text-sm">तेच प्रकरण पुढे न्यायचे असल्यास ते उघडा (तिथे “पुन्हा तयार करा” वापरा). नवीन प्रकरण हवेच असल्यास C R व वर्ष रिकामे ठेवून पुन्हा जमा करा.</div>
            <Link className="btn-primary mt-2 inline-flex" to={`/cases/${dupId}`}>प्रकरण #{dupId} उघडा →</Link>
          </div>
        )}
        <Section title="तपशील">
          <div className="space-y-4">
            <Field label="विभाग / कार्यासन" hint="नोंद व पत्राची रचना (शीर्ष, सही-साखळी, पत्राचा क्रमांक) या कार्यासनाप्रमाणे.">
              <select className="input" disabled={locked} value={f.desk} onChange={set('desk')}>{DESKS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}</select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="C R क्र."><input className="input" inputMode="numeric" placeholder="उदा. 128" disabled={locked} value={f.cr_no} onChange={setCr} /></Field>
              <Field label="वर्ष"><input ref={yearRef} className="input" inputMode="numeric" maxLength={4} placeholder="PDF वरून" disabled={locked} value={f.cr_year} onChange={setYear} /></Field>
            </div>
            <Field label="नस्ती क्र. (निर्देशपत्र)"><input className="input" placeholder={DESKS.find(d => d.id === f.desk)?.fileNo} disabled={locked} value={f.file_no} onChange={set('file_no')} /></Field>
            <Field label="विषय"><textarea className="input min-h-[88px]" placeholder="रिकामे ठेवल्यास PDF वरून भरले जाईल" disabled={locked} value={f.subject} onChange={set('subject')} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="प्रवर्ग">
                <select className="input" disabled={locked} value={f.category} onChange={set('category')}><option value="">PDF वरून ठरवा</option>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
              </Field>
              <Field label="प्राधान्य">
                <select className="input" disabled={locked} value={f.priority} onChange={set('priority')}>{PRIORITIES.map(c => <option key={c}>{c}</option>)}</select>
              </Field>
            </div>
            <Field label="विशेष सूचना (ऐच्छिक)" hint="इथे लिहिलेली सूचना अभ्यास करताना पाळली जाते (कायमच्या नियमांच्या मर्यादेत). रिकामे ठेवल्यास नेहमीप्रमाणे.">
              <textarea className="input min-h-[72px]" value={f.instructions} onChange={set('instructions')}
                placeholder={'उदा. • पत्रात फक्त सेवापुस्तकाची प्रत मागवा\n• पत्र नको; नस्ती वित्त विभागाकडे पाठवा\n• पान 7 वरील हस्तलिखित शेरा नीट वाचा'} />
            </Field>
            <DraftPicker value={chosen} onChange={setDrafts} suggestion={suggestion} disabled={busy || running || done} />
            {done && created ? (
              <Link className="btn-accent flex w-full items-center justify-center py-3 text-xl" to={`/cases/${created.id}?tab=note`}>
                तयार फाइल पाहा →
              </Link>
            ) : running ? (
              <div className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-100 px-3 py-3 text-lg font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100" role="status">
                <Spinner /> प्रक्रिया चालू — पूर्ण झाल्यावर येथे बटण येईल
              </div>
            ) : (
              <button className="btn-accent w-full text-lg" disabled={busy || !proposal || overBudget}>
                {busy && <Spinner />}{' '}
                {busy
                  ? 'फाइल अपलोड होत आहे…'
                  : failed || (created && (runErr || ups.some(u => u.state === 'err')))
                    ? '↻ पुन्हा तयार करा'
                    : created
                      ? 'प्रक्रिया सुरू करा'
                      : 'अभ्यास सुरू करा'}
              </button>
            )}
            {failed && !busy && <div className="text-center text-sm font-semibold text-red-700 dark:text-red-400">प्रक्रिया अयशस्वी — वरील "↻ पुन्हा तयार करा" दाबा</div>}
          </div>
        </Section>
      </form>

    </div>
  );
}
