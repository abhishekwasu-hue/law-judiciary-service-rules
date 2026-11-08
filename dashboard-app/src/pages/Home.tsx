import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { fmtUsd, getSpend, humanError, type Spend } from '../lib/api';
import { useAuth, useCanWrite } from '../lib/auth';
import { dueSoon, isPendingLetter, useData } from '../lib/data';
import { ACTION_LABEL, CATEGORIES, STAGES, stageTone, type Tone } from '../lib/constants';
import { crLabel, daysBetween, fmtDateTime, monthLabel, textOf, todayISO } from '../lib/format';
import type { Activity } from '../lib/types';
import { ACTIVITY_COLUMNS, TODO_TOP } from '../lib/perf';
import { Empty, Section, Skeleton, Spinner } from '../components/ui';
import QueueCard from '../components/QueueCard';
import WorkTypeChips from '../components/WorkTypeChips';

// Recharts is loaded only when the आलेख section is opened.
/** claude.ai artifact build: no monthly limit on the page (the $ line is the Worker's) — E-F4. */
const ARTIFACT = import.meta.env.VITE_BACKEND === 'artifact';
const HomeCharts = lazy(() => import('../components/Charts').then(m => ({ default: m.HomeCharts })));

// Number colours with a dark-mode variant (UI audit S17: the fixed TONE_HEX colours were 2.4–3.3:1 on the dark cards).
const TONE_TEXT: Record<Tone, string> = {
  green: 'text-green-700 dark:text-green-400', amber: 'text-amber-700 dark:text-amber-300', red: 'text-red-700 dark:text-red-300',
  blue: 'text-blue-700 dark:text-blue-300', slate: 'text-slate-600 dark:text-slate-300', navy: 'text-navy-700 dark:text-slate-200',
};

// value: null = still loading (skeleton); 'na' = could not be read (shown as "—", never as a false 0 — UI audit S8)
function Kpi({ label, value, tone, to }: { label: string; value: number | null | 'na'; tone: Tone; to: string }) {
  return (
    <Link to={to} className="card block p-3 transition hover:-translate-y-0.5 hover:shadow-md sm:p-4">
      <div className="text-sm font-semibold leading-tight text-slate-600 dark:text-slate-300">{label}</div>
      <div className={`mt-1 font-head text-2xl font-bold sm:text-3xl ${TONE_TEXT[tone]}`}>
        {value === null ? <Skeleton className="h-8 w-10" /> : value === 'na' ? '—' : value}
      </div>
    </Link>
  );
}

/** Short time for the activity list: today "17:03", yesterday "काल", else "25.09" (the full date-time stays in the tooltip). */
function shortWhen(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const day = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(now) - day(d)) / 864e5);
  if (diff === 0) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  if (diff === 1) return 'काल';
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}${d.getFullYear() !== now.getFullYear() ? `.${d.getFullYear()}` : ''}`;
}
// one word for the automatic job (glossary: प्रक्रिया), whatever lib/constants still says
const RUN_ACTION: Record<string, string> = {
  run_started: 'प्रक्रिया सुरू झाली', run_queued: 'प्रक्रिया प्रतीक्षेत', run_done: 'प्रक्रिया पूर्ण', run_failed: 'प्रक्रिया अयशस्वी', run_warning: 'प्रक्रियेची सूचना',
};

// Owner only: this month's AI spend against the monthly limit (green < 80% ≤ amber < 100% ≤ red). A small line under the
// work counts, not a tile among them (UI audit S22).
function SpendLine({ spend }: { spend: Spend | null | 'err' }) {
  const ok = spend && spend !== 'err';
  const pct = ok && spend.limit_usd > 0 ? (spend.spent_usd / spend.limit_usd) * 100 : 0;
  const tone: Tone = !ok ? 'slate' : pct >= 100 ? 'red' : pct >= 80 ? 'amber' : 'green';
  return (
    <Link to="/settings" className="col-span-full inline-flex min-h-tap flex-wrap items-center gap-x-2 text-sm text-slate-600 hover:underline dark:text-slate-300" title={ok ? `${spend.runs} प्रक्रिया • ${Math.round(pct)}%` : undefined}>
      <span className="font-semibold">या महिन्याचा खर्च (फक्त मालकांना दिसतो):</span>
      {spend === null ? <Skeleton className="inline-block h-4 w-16" /> : (
        <b className={TONE_TEXT[tone]}>{ok ? `${fmtUsd(spend.spent_usd)} / ${fmtUsd(spend.limit_usd)}${pct >= 100 ? ' • मर्यादा संपली' : ''}` : '—'}</b>
      )}
    </Link>
  );
}

export default function Home() {
  const { cases, letters, loading, error, refresh } = useData();
  const [actErr, setActErr] = useState('');
  const [reloading, setReloading] = useState(false);
  const [actTry, setActTry] = useState(0);
  const nav = useNavigate();
  // P4: two small reads instead of 12 months of every action (read twice before): the last 8 events (हालचाल) and this month's
  // stage changes (या महिन्यात बंद). The 12-month stage changes for the आलेख are read only when the charts are opened.
  const [acts, setActs] = useState<Activity[] | null>(null);
  const [monthActs, setMonthActs] = useState<Activity[] | null>(null);
  const [chartActs, setChartActs] = useState<Activity[] | null>(null);
  const isOwner = useAuth().me?.role === 'owner';
  const canWrite = useCanWrite();
  const [spend, setSpend] = useState<Spend | null | 'err'>(null);
  useEffect(() => {
    if (isOwner && !ARTIFACT) void getSpend().then(setSpend, () => setSpend('err'));
  }, [isOwner, actTry]);
  // charts folded by default on every width (UI audit S23: open, they took ~60 % of the desktop page); one tap opens them
  const [chartsOpen, setChartsOpen] = useState(false);
  const [allTodo, setAllTodo] = useState(false); // U2: "आज करायचे" shows TODO_TOP rows until "सर्व N पाहा"

  const monthStart = useMemo(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1).toISOString();
  }, []);
  // read on open, on "पुन्हा प्रयत्न" and when the tab comes back (not on every case-count change any more)
  const [visTick, setVisTick] = useState(0);
  useEffect(() => {
    const on = () => document.visibilityState === 'visible' && setVisTick(n => n + 1);
    document.addEventListener('visibilitychange', on);
    return () => document.removeEventListener('visibilitychange', on);
  }, []);
  useEffect(() => {
    let alive = true;
    const fail = (e: unknown) => {
      if (!alive) return;
      setActErr(e instanceof Error ? e.message : String(e));
      setActs(a => a ?? []);
      setMonthActs(a => a ?? []);
    };
    void Promise.all([
      sb().from('activity').select(ACTIVITY_COLUMNS).order('at', { ascending: false }).limit(8),
      sb().from('activity').select(ACTIVITY_COLUMNS).eq('action', 'stage_changed').gte('at', monthStart).order('at', { ascending: false }).limit(2000),
    ]).then(([r, m]) => {
      if (!alive) return;
      const e = r.error || m.error;
      setActErr(e ? e.message : '');
      if (!r.error) setActs((r.data as unknown as Activity[]) || []);
      else setActs(a => a ?? []);
      if (!m.error) setMonthActs((m.data as unknown as Activity[]) || []);
      else setMonthActs(a => a ?? []);
    }, fail);
    return () => { alive = false; };
  }, [actTry, visTick, monthStart]);
  useEffect(() => {
    if (!chartsOpen || chartActs) return;
    const since = new Date();
    since.setMonth(since.getMonth() - 12);
    void sb().from('activity').select(ACTIVITY_COLUMNS).eq('action', 'stage_changed').gte('at', since.toISOString()).order('at', { ascending: false }).limit(5000).then(
      ({ data, error: e }) => setChartActs(e ? [] : ((data as unknown as Activity[]) || [])),
      () => setChartActs([]),
    );
  }, [chartsOpen, chartActs, actTry]);
  const anyErr = [error, actErr].filter(Boolean).join(' • ');
  async function reloadAll() {
    setReloading(true);
    setActTry(n => n + 1);
    setChartActs(null);
    await refresh();
    setReloading(false);
  }
  // A failed read must not look like "no cases" / "nothing pending".
  const errCard = anyErr ? (
    <div className="card flex flex-wrap items-center justify-between gap-3 border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">
      <div className="min-w-0">
        <div className="font-bold">⚠️ माहिती आणता आली नाही.{ARTIFACT ? '' : ' कृपया पुन्हा प्रयत्न करावा.'}</div>
        {/* artifact (E-F9): the data layer's Marathi reason (store not available in this view / temporary) for everyone */}
        <div className="mt-1 break-words text-sm">{isOwner || ARTIFACT ? humanError(anyErr) : 'अडचण कायम राहिल्यास कृपया मालकांना कळवावे.'}</div>
      </div>
      <button className="btn-primary" disabled={reloading} onClick={() => void reloadAll()}>{reloading && <Spinner />} ↻ पुन्हा प्रयत्न</button>
    </div>
  ) : null;

  const byId = useMemo(() => new Map(cases.map(c => [c.id, c])), [cases]);
  const isClose = (a: Activity) => a.action === 'stage_changed' && a.detail?.to === 'बंद';
  const closedEvents = useMemo(() => (chartActs || []).filter(isClose), [chartActs]);

  const kpi = useMemo(() => {
    const n = (s: string) => cases.filter(c => c.stage === s).length;
    return {
      new: n('प्राप्त'),
      study: n('अभ्यास चालू'),
      waiting: n('पत्र पाठवले (माहिती प्रतीक्षेत)'),
      finance: n('वित्त/सा.प्र.वि. कडे'),
      closed: actErr ? ('na' as const) : monthActs ? new Set(monthActs.filter(a => isClose(a) && a.at >= monthStart).map(a => a.case_id)).size : null,
    };
  }, [cases, monthActs, actErr, monthStart]);

  const today = todayISO();
  const todo = useMemo(() => dueSoon(letters, 7), [letters]);
  const overdueCases = useMemo(() => cases.filter(c => c.due_date && c.due_date < today && c.stage !== 'बंद'), [cases, today]);
  // "आज करायचे": one row per case with its most urgent reason (UI audit S15: a case was listed twice)
  const todoRows = useMemo(() => {
    const m = new Map<number, { caseId: number; due: string; reason: string; href: string }>();
    const put = (caseId: number, due: string, reason: string, href: string) => {
      const o = m.get(caseId);
      if (!o || due < o.due) m.set(caseId, { caseId, due, reason, href });
    };
    for (const l of todo) put(l.case_id, l.reply_due!, `पत्राचे उत्तर: ${l.addressed_to || l.ref_no || 'पत्र'}`, `/cases/${l.case_id}?tab=letters`);
    for (const c of overdueCases) put(c.id, c.due_date!, 'प्रकरणाची मुदत', `/cases/${c.id}`);
    return [...m.values()].sort((a, b) => (a.due < b.due ? -1 : 1));
  }, [todo, overdueCases]);

  const catData = useMemo(() => CATEGORIES.map(k => ({ name: k, value: cases.filter(c => c.category === k).length })).filter(d => d.value > 0), [cases]);
  const stageData = useMemo(() => STAGES.map(s => ({ name: s, value: cases.filter(c => c.stage === s).length, tone: stageTone(s) })), [cases]);
  const monthly = useMemo(() => {
    const now = new Date();
    const rows = Array.from({ length: 12 }, (_, i) => {
      const d = new Date(now.getFullYear(), now.getMonth() - 11 + i, 1);
      return { y: d.getFullYear(), m: d.getMonth(), name: monthLabel(d.getFullYear(), d.getMonth()), प्राप्त: 0, बंद: 0 };
    });
    const idx = (iso: string) => {
      const d = new Date(iso);
      return rows.findIndex(r => r.y === d.getFullYear() && r.m === d.getMonth());
    };
    for (const c of cases) {
      const i = idx(c.inward_date || c.created_at);
      if (i >= 0) rows[i].प्राप्त++;
    }
    for (const a of closedEvents) {
      const i = idx(a.at);
      if (i >= 0) rows[i].बंद++;
    }
    return rows;
  }, [cases, closedEvents]);
  const avgDays = useMemo(() => {
    // From stage_changed events: time spent in `from` stage = this change − previous change (or case creation).
    const per = new Map<string, number[]>();
    const evByCase = new Map<number, Activity[]>();
    for (const a of chartActs || []) if (a.action === 'stage_changed' && a.case_id) (evByCase.get(a.case_id) || evByCase.set(a.case_id, []).get(a.case_id)!).push(a);
    for (const [cid, evs] of evByCase) {
      const c = byId.get(cid);
      if (!c) continue;
      evs.sort((x, y) => (x.at < y.at ? -1 : 1));
      let t = c.created_at;
      for (const e of evs) {
        const from = textOf(e.detail?.from);
        (per.get(from) || per.set(from, []).get(from)!).push(Math.max(0, daysBetween(t, e.at)));
        t = e.at;
      }
    }
    return STAGES.filter(s => per.has(s)).map(s => {
      const v = per.get(s)!;
      return { name: s, value: Math.round((v.reduce((p, q) => p + q, 0) / v.length) * 10) / 10 };
    });
  }, [chartActs, byId]);
  const byOffice = useMemo(() => {
    const m = new Map<string, number>();
    for (const l of letters) if (isPendingLetter(l)) {
      const o = byId.get(l.case_id)?.office || 'नमूद नाही';
      m.set(o, (m.get(o) || 0) + 1);
    }
    return [...m.entries()].map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 10);
  }, [letters, byId]);

  if (!loading && cases.length === 0 && error) return errCard;
  if (!loading && cases.length === 0)
    return (
      <div className="card">
        <Empty icon="🗂️" title="अजून एकही प्रकरण नाही" hint="पहिला प्रस्ताव अपलोड करण्यासाठी कृपया खालील बटण वापरावे.">
          <ol className="my-2 max-w-md space-y-1.5 text-left text-slate-700 dark:text-slate-200">
            <li><b>1.</b> प्रस्तावाची PDF अपलोड करावी.</li>
            <li><b>2.</b> प्रक्रिया पूर्ण झाल्यावर टिप्पणी, पत्राचा मसुदा, अभ्यास-फाइल व GR सह प्रस्ताव (PDF) तयार होतात.</li>
            <li><b>3.</b> प्रकरणाच्या पानावर त्या तपासून डाउनलोड करता येतात.</li>
          </ol>
          {(!ARTIFACT || canWrite) && <Link className="btn-accent" to="/new">+ नवीन प्रस्ताव</Link>}
        </Empty>
      </div>
    );

  const readErr = <div className="font-semibold text-red-800 dark:text-red-300" role="alert">माहिती आणता आली नाही. कृपया वरील “↻ पुन्हा प्रयत्न” बटण वापरावे.</div>;
  // Phone order (UI audit S2): आज करायचे, the counts, प्रतीक्षा-यादी, work types, हालचाल, आलेख. Wide screen (lg): work types and
  // प्रतीक्षा-यादी first, the counts, then आज करायचे | हालचाल side by side, आलेख.
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="order-first flex flex-wrap items-center justify-between gap-2 lg:col-span-2">
        <h1 className="text-2xl font-bold">मुख्य पृष्ठ</h1>
        {(!ARTIFACT || canWrite) && <Link to="/new" className="btn-accent">+ नवीन प्रस्ताव</Link>}
      </div>
      {errCard && <div className="order-first lg:col-span-2">{errCard}</div>}

      <div className="order-1 min-w-0 lg:order-4">
        <Section title="आज करायचे" right={<Link to="/cases?overdue=1" className="inline-flex min-h-tap items-center text-sm font-semibold text-navy-700 hover:underline dark:text-slate-200">सर्व मुदत संपलेली →</Link>}>
          {error && todoRows.length === 0 ? readErr : todoRows.length === 0 ? (
            <Empty icon="✅" title="आज काही प्रलंबित नाही" hint="मुदत संपलेली किंवा 7 दिवसांत येणारी उत्तरे व प्रकरणे येथे दिसतील." />
          ) : (
            <>
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">
              {(allTodo ? todoRows : todoRows.slice(0, TODO_TOP)).map(r => {
                const c = byId.get(r.caseId);
                const late = r.due < today;
                const n = Math.abs(daysBetween(r.due, today));
                return (
                  <li key={r.caseId}>
                    <Link to={r.href} className="block min-h-tap py-2">
                      <span className="flex items-center justify-between gap-2">
                        <span className="min-w-0 truncate font-semibold">{c ? crLabel(c) : `प्रकरण क्र. ${r.caseId}`}</span>
                        <span className={`chip shrink-0 ${late ? 'bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-100' : 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100'}`}>
                          {late ? `${n} दिवस उशीर` : n === 0 ? 'आज मुदत' : `${n} दिवसांत मुदत`}
                        </span>
                      </span>
                      <span className="block truncate text-sm text-slate-600 dark:text-slate-300">{r.reason}{c?.subject ? ` • ${c.subject}` : ''}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
            {todoRows.length > TODO_TOP && (
              <button type="button" className="btn-ghost mt-2 w-full" aria-expanded={allTodo} onClick={() => setAllTodo(o => !o)}>
                {allTodo ? 'कमी दाखवा ▲' : `सर्व ${todoRows.length} पाहा ▼`}
              </button>
            )}
            </>
          )}
        </Section>
      </div>

      <div className="order-2 grid grid-cols-3 gap-2 sm:grid-cols-5 sm:gap-3 lg:order-3 lg:col-span-2">
        <Kpi label="प्राप्त" value={loading ? null : kpi.new} tone="navy" to="/cases?stage=प्राप्त" />
        <Kpi label="अभ्यास चालू" value={loading ? null : kpi.study} tone="blue" to="/cases?stage=अभ्यास चालू" />
        <Kpi label="उत्तर प्रतीक्षेत" value={loading ? null : kpi.waiting} tone="amber" to={`/cases?stage=${encodeURIComponent('पत्र पाठवले (माहिती प्रतीक्षेत)')}`} />
        <Kpi label="वित्त/सा.प्र.वि. कडे" value={loading ? null : kpi.finance} tone="amber" to={`/cases?stage=${encodeURIComponent('वित्त/सा.प्र.वि. कडे')}`} />
        <Kpi label="या महिन्यात बंद" value={loading ? null : kpi.closed} tone="green" to="/cases?stage=बंद" />
        {isOwner && !ARTIFACT && <SpendLine spend={spend} />}
      </div>

      <QueueCard className="order-3 lg:order-2 lg:col-span-2" />
      <div className="order-4 min-w-0 lg:order-1 lg:col-span-2"><WorkTypeChips cases={cases} linkTo={id => (id ? `/cases?work=${id}` : '/cases')} /></div>

      <div className="order-5 min-w-0">
        <Section title="अलीकडील हालचाल">
          {!acts ? <div className="space-y-2">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full" />)}</div> : actErr && acts.length === 0 ? readErr : acts.length === 0 ? (
            <Empty icon="🕘" title="हालचाल नाही" />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">
              {acts.slice(0, 8).map(a => {
                const c = a.case_id ? byId.get(a.case_id) : undefined;
                return (
                  <li key={a.id}>
                    <Link to={a.case_id ? `/cases/${a.case_id}?tab=history` : '/'} className="block min-h-tap py-2">
                      <span className="flex items-center justify-between gap-2">
                        <span className="min-w-0 truncate font-semibold">{c ? crLabel(c) : a.case_id ? `प्रकरण क्र. ${a.case_id}` : ''}</span>
                        <span className="shrink-0 text-sm text-slate-500 dark:text-slate-400" title={fmtDateTime(a.at)}>{shortWhen(a.at)}</span>
                      </span>
                      <span className="block truncate text-sm text-slate-700 dark:text-slate-300">
                        {RUN_ACTION[a.action] || ACTION_LABEL[a.action] || a.action}
                        {a.action === 'stage_changed' && <span className="text-slate-500 dark:text-slate-400"> → {textOf(a.detail?.to)}</span>}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>
      </div>

      <details className="order-6 min-w-0 lg:col-span-2" open={chartsOpen} onToggle={e => setChartsOpen((e.currentTarget as HTMLDetailsElement).open)}>
        <summary className="card flex list-none [&::-webkit-details-marker]:hidden min-h-tap cursor-pointer select-none items-center justify-between px-4 py-3 text-base font-bold">
          <span>आलेख</span>
          <span className="text-sm font-normal text-slate-500 dark:text-slate-400">{chartsOpen ? 'लपवा ▲' : 'दाखवा ▼'}</span>
        </summary>
      {chartsOpen && !chartActs && <div className="mt-4 grid gap-4 lg:grid-cols-2">{[0, 1].map(i => <Skeleton key={i} className="h-72 w-full" />)}</div>}
      {chartsOpen && chartActs && (
        <Suspense fallback={<div className="mt-4 grid gap-4 lg:grid-cols-2">{[0, 1].map(i => <Skeleton key={i} className="h-72 w-full" />)}</div>}>
          <HomeCharts
            catData={catData}
            stageData={stageData}
            monthly={monthly}
            byOffice={byOffice}
            avgDays={avgDays}
            onCategory={n => nav(`/cases?category=${encodeURIComponent(n)}`)}
            onStage={n => nav(`/cases?stage=${encodeURIComponent(n)}`)}
            onOffice={n => nav(`/cases?office=${encodeURIComponent(n)}`)}
          />
        </Suspense>
      )}
      </details>
    </div>
  );
}
