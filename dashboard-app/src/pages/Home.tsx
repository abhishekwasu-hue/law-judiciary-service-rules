import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { fmtUsd, getSpend, humanError, type Spend } from '../lib/api';
import { useAuth } from '../lib/auth';
import { dueSoon, isPendingLetter, useData } from '../lib/data';
import { ACTION_LABEL, CATEGORIES, STAGES, TONE_HEX, stageTone, type Tone } from '../lib/constants';
import { crLabel, daysBetween, fmtDate, fmtDateTime, monthLabel, textOf, todayISO } from '../lib/format';
import type { Activity } from '../lib/types';
import { Empty, Section, Skeleton, Spinner } from '../components/ui';
import QueueCard from '../components/QueueCard';
import WorkTypeChips from '../components/WorkTypeChips';

// Recharts is loaded only when the आलेख section is opened.
const HomeCharts = lazy(() => import('../components/Charts').then(m => ({ default: m.HomeCharts })));

function Kpi({ label, value, tone, to }: { label: string; value: number | null; tone: Tone; to: string }) {
  return (
    <Link to={to} className="card block p-3 transition hover:-translate-y-0.5 hover:shadow-md sm:p-4">
      <div className="text-sm font-semibold leading-tight text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 font-head text-2xl font-bold sm:text-3xl" style={{ color: TONE_HEX[tone] }}>
        {value === null ? <Skeleton className="h-8 w-10" /> : value}
      </div>
    </Link>
  );
}

// Owner only: this month's AI spend against the monthly limit (green < 80% ≤ amber < 100% ≤ red).
function SpendKpi({ spend }: { spend: Spend | null | 'err' }) {
  const ok = spend && spend !== 'err';
  const pct = ok && spend.limit_usd > 0 ? (spend.spent_usd / spend.limit_usd) * 100 : 0;
  const tone: Tone = !ok ? 'slate' : pct >= 100 ? 'red' : pct >= 80 ? 'amber' : 'green';
  return (
    <Link to="/settings" className="card block p-3 transition hover:-translate-y-0.5 hover:shadow-md sm:p-4" title={ok ? `${spend.runs} प्रक्रिया • ${Math.round(pct)}%` : undefined}>
      <div className="text-sm font-semibold leading-tight text-slate-500 dark:text-slate-400">या महिन्याचा खर्च</div>
      <div className="mt-1 font-head text-2xl font-bold sm:text-3xl" style={{ color: TONE_HEX[tone] }}>
        {spend === null ? <Skeleton className="h-8 w-16" /> : ok ? fmtUsd(spend.spent_usd) : '—'}
      </div>
      {ok && <div className="text-sm font-semibold text-slate-500 dark:text-slate-400">/ {fmtUsd(spend.limit_usd)}{pct >= 100 ? ' • मर्यादा संपली' : ''}</div>}
    </Link>
  );
}

export default function Home() {
  const { cases, letters, loading, error, refresh } = useData();
  const [actErr, setActErr] = useState('');
  const [reloading, setReloading] = useState(false);
  const [actTry, setActTry] = useState(0);
  const nav = useNavigate();
  const [acts, setActs] = useState<Activity[] | null>(null);
  const isOwner = useAuth().me?.role === 'owner';
  const [spend, setSpend] = useState<Spend | null | 'err'>(null);
  useEffect(() => {
    if (isOwner) void getSpend().then(setSpend, () => setSpend('err'));
  }, [isOwner, cases.length]);
  // charts: open by default on a wide screen, folded on phones (आज करायचे comes first there)
  const [chartsOpen, setChartsOpen] = useState(() => typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches);

  useEffect(() => {
    const since = new Date();
    since.setMonth(since.getMonth() - 12);
    void sb().from('activity').select('*').gte('at', since.toISOString()).order('at', { ascending: false }).limit(2000).then(
      ({ data, error: e }) => {
        setActErr(e ? e.message : '');
        if (!e) setActs((data as Activity[]) || []);
        else setActs(a => a ?? []);
      },
      (e: unknown) => {
        setActErr(String(e));
        setActs(a => a ?? []);
      },
    );
  }, [cases.length, actTry]);
  const anyErr = [error, actErr].filter(Boolean).join(' • ');
  async function reloadAll() {
    setReloading(true);
    setActTry(n => n + 1);
    await refresh();
    setReloading(false);
  }
  // A failed read must not look like "no cases" / "nothing pending".
  const errCard = anyErr ? (
    <div className="card flex flex-wrap items-center justify-between gap-3 border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">
      <div className="min-w-0">
        <div className="font-bold">⚠️ माहिती आणता आली नाही — पुन्हा लोड करा</div>
        <div className="mt-1 break-words text-sm">{humanError(anyErr)}</div>
      </div>
      <button className="btn-primary" disabled={reloading} onClick={() => void reloadAll()}>{reloading && <Spinner />} ↻ पुन्हा लोड करा</button>
    </div>
  ) : null;

  const byId = useMemo(() => new Map(cases.map(c => [c.id, c])), [cases]);
  const monthStart = useMemo(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1).toISOString();
  }, []);
  const closedEvents = useMemo(() => (acts || []).filter(a => a.action === 'stage_changed' && a.detail?.to === 'बंद'), [acts]);

  const kpi = useMemo(() => {
    const n = (s: string) => cases.filter(c => c.stage === s).length;
    return {
      new: n('प्राप्त'),
      study: n('अभ्यास चालू'),
      waiting: n('पत्र पाठवले (माहिती प्रतीक्षेत)'),
      finance: n('वित्त/सा.प्र.वि. कडे'),
      closed: acts ? new Set(closedEvents.filter(a => a.at >= monthStart).map(a => a.case_id)).size : null,
    };
  }, [cases, acts, closedEvents, monthStart]);

  const today = todayISO();
  const todo = useMemo(() => dueSoon(letters, 7), [letters]);
  const overdueCases = useMemo(() => cases.filter(c => c.due_date && c.due_date < today && c.stage !== 'बंद'), [cases, today]);

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
    for (const a of acts || []) if (a.action === 'stage_changed' && a.case_id) (evByCase.get(a.case_id) || evByCase.set(a.case_id, []).get(a.case_id)!).push(a);
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
  }, [acts, byId]);
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
        <Empty icon="🗂️" title="अजून एकही प्रकरण नाही" hint="पहिला प्रस्ताव अपलोड करा (n).">
          <Link className="btn-accent" to="/new">नवीन प्रस्ताव</Link>
        </Empty>
      </div>
    );

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="order-first flex flex-wrap items-center justify-between gap-2 lg:col-span-2">
        <h1 className="text-2xl font-bold">मुख्य पृष्ठ</h1>
        <Link to="/new" className="btn-accent">+ नवीन प्रस्ताव</Link>
      </div>
      {errCard && <div className="order-first lg:col-span-2">{errCard}</div>}
      <div className="order-first min-w-0 lg:col-span-2"><WorkTypeChips cases={cases} linkTo={id => (id ? `/cases?work=${id}` : '/cases')} /></div>
      <QueueCard className="order-first lg:col-span-2" />

      <div className={`order-2 grid grid-cols-3 gap-2 sm:gap-3 lg:order-1 lg:col-span-2 ${isOwner ? 'lg:grid-cols-6' : 'sm:grid-cols-5'}`}>
        <Kpi label="नवीन" value={loading ? null : kpi.new} tone="navy" to="/cases?stage=प्राप्त" />
        <Kpi label="अभ्यास चालू" value={loading ? null : kpi.study} tone="blue" to="/cases?stage=अभ्यास चालू" />
        <Kpi label="उत्तर प्रतीक्षेत" value={loading ? null : kpi.waiting} tone="amber" to={`/cases?stage=${encodeURIComponent('पत्र पाठवले (माहिती प्रतीक्षेत)')}`} />
        <Kpi label="वित्त विभागाकडे" value={loading ? null : kpi.finance} tone="amber" to={`/cases?stage=${encodeURIComponent('वित्त/सा.प्र.वि. कडे')}`} />
        <Kpi label="या महिन्यात बंद" value={loading ? null : kpi.closed} tone="green" to="/cases?stage=बंद" />
        {isOwner && <SpendKpi spend={spend} />}
      </div>

      <div className="order-1 min-w-0 lg:order-2">
        <Section title="आज करायचे" right={<Link to="/cases?overdue=1" className="text-sm font-semibold text-red-700 hover:underline dark:text-red-300">मुदत संपलेली →</Link>}>
          {error && todo.length === 0 && overdueCases.length === 0 ? (
            <div className="font-semibold text-red-800 dark:text-red-300" role="alert">माहिती आणता आली नाही — वरील “पुन्हा लोड करा” दाबा.</div>
          ) : todo.length === 0 && overdueCases.length === 0 ? (
            <Empty icon="✅" title="आज काही प्रलंबित नाही" hint="मुदत संपलेली किंवा 7 दिवसांत येणारी उत्तरे येथे दिसतील." />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">
              {todo.map(l => {
                const c = byId.get(l.case_id);
                const late = l.reply_due! < today;
                return (
                  <li key={`l${l.id}`}>
                    <Link to={`/cases/${l.case_id}?tab=letters`} className="flex min-h-tap items-center justify-between gap-2 py-2">
                      <span className="min-w-0">
                        <span className="font-semibold">{c ? crLabel(c) : `#${l.case_id}`}</span> — उत्तर: {l.addressed_to || l.ref_no || 'पत्र'}
                      </span>
                      <span className={`chip shrink-0 ${late ? 'bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-100' : 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100'}`}>
                        {late ? `${daysBetween(l.reply_due!, today)} दिवस उशीर` : fmtDate(l.reply_due)}
                      </span>
                    </Link>
                  </li>
                );
              })}
              {overdueCases.map(c => (
                <li key={`c${c.id}`}>
                  <Link to={`/cases/${c.id}`} className="flex min-h-tap items-center justify-between gap-2 py-2">
                    <span className="min-w-0 truncate"><span className="font-semibold">{crLabel(c)}</span> — {c.subject}</span>
                    <span className="chip shrink-0 bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-100">मुदत {fmtDate(c.due_date)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <div className="order-3 min-w-0">
        <Section title="अलीकडील हालचाल">
          {!acts ? <div className="space-y-2">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full" />)}</div> : actErr && acts.length === 0 ? (
            <div className="font-semibold text-red-800 dark:text-red-300" role="alert">माहिती आणता आली नाही — वरील “पुन्हा लोड करा” दाबा.</div>
          ) : acts.length === 0 ? (
            <Empty icon="🕘" title="हालचाल नाही" />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">
              {acts.slice(0, 8).map(a => {
                const c = a.case_id ? byId.get(a.case_id) : undefined;
                return (
                  <li key={a.id}>
                    <Link to={a.case_id ? `/cases/${a.case_id}?tab=history` : '/'} className="flex min-h-tap items-center justify-between gap-2 py-2">
                      <span className="min-w-0 truncate">
                        <span className="font-semibold">{c ? crLabel(c) : ''}</span> {ACTION_LABEL[a.action] || a.action}
                        {a.action === 'stage_changed' && <span className="text-slate-500"> → {textOf(a.detail?.to)}</span>}
                      </span>
                      <span className="shrink-0 text-sm text-slate-500">{fmtDateTime(a.at)}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Section>
      </div>

      <details className="order-4 min-w-0 lg:col-span-2" open={chartsOpen} onToggle={e => setChartsOpen((e.currentTarget as HTMLDetailsElement).open)}>
        <summary className="card flex list-none [&::-webkit-details-marker]:hidden min-h-tap cursor-pointer select-none items-center justify-between px-4 py-3 text-base font-bold">
          <span>आलेख</span>
          <span className="text-sm font-normal text-slate-500">{chartsOpen ? 'लपवा ▲' : 'दाखवा ▼'}</span>
        </summary>
      {chartsOpen && (
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
