import { useEffect, useState } from 'react';
import { sb } from '../lib/supabase';
import type { Run } from '../lib/types';
import { RUN_STATE_LABEL, RUN_STEPS, STALE_REASON, isStale, runTone } from '../lib/constants';
import { asArray, fmtDateTime, textOf } from '../lib/format';
import { useAuth } from '../lib/auth';
import { Chip, Progress, Spinner } from './ui';

/** Glossary wording for a run state (प्रक्रिया रांगेत / चालू / तयार / अयशस्वी). */
const STATE_TEXT: Record<string, string> = { queued: 'प्रक्रिया रांगेत', running: 'प्रक्रिया चालू', done: 'प्रक्रिया तयार', failed: 'प्रक्रिया अयशस्वी' };
const stateText = (s: string) => STATE_TEXT[s] || RUN_STATE_LABEL[s] || s;

/** Latest runs of a case, kept live through Supabase Realtime (table `runs`). */
export function useRuns(caseId: number | null) {
  const [runs, setRuns] = useState<Run[] | null>(null);
  useEffect(() => {
    setRuns(null); // never show the previous case's runs
    if (!caseId) return;
    let alive = true;
    const load = () =>
      sb()
        .from('runs')
        .select('*')
        .eq('case_id', caseId)
        .order('created_at', { ascending: false })
        .then(({ data, error }) => {
          // a failed re-read keeps what is shown (first read: empty list, as before)
          if (alive) setRuns(s => (error ? s ?? [] : (data as Run[]) || []));
        });
    void load();
    // Realtime does not replay missed events → re-read on tab return, reconnect and (re)subscribe
    const onVisible = () => document.visibilityState === 'visible' && void load();
    const onOnline = () => void load();
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onOnline);
    const ch = sb()
      .channel(`runs-${caseId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'runs', filter: `case_id=eq.${caseId}` }, p => {
        const row = p.new as Run;
        if (!alive || !row?.id) return;
        setRuns(s => {
          const list = s || [];
          return list.some(r => r.id === row.id) ? list.map(r => (r.id === row.id ? row : r)) : [row, ...list];
        });
      })
      .subscribe(status => {
        if (status === 'SUBSCRIBED') void load();
      });
    return () => {
      alive = false;
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onOnline);
      void sb().removeChannel(ch);
    };
  }, [caseId]);
  return runs;
}

function stepIndex(r: Run): number {
  if (r.state === 'done') return RUN_STEPS.length - 1;
  if (r.state === 'queued' && !r.step) return 0;
  const s = (r.step || '').toLowerCase();
  const i = RUN_STEPS.findIndex(x => s.includes(x.key.toLowerCase()));
  return i < 0 ? (r.state === 'running' ? 1 : 0) : i;
}

const num = (v: unknown): number | null => {
  const n = typeof v === 'string' ? Number(v) : typeof v === 'number' ? v : NaN;
  return Number.isFinite(n) ? n : null;
};
export function fmtDuration(s: number): string {
  const m = Math.round(s / 60);
  return m < 60 ? `${m} मि.` : `${Math.floor(m / 60)} ता. ${m % 60} मि.`;
}

const COST_TARGET = 'प्रति प्रस्ताव लक्ष्य $0.50';
/** green ≤ $0.50 (target), amber ≤ $1, red above. */
const costTone = (c: number) =>
  c <= 0.5 ? 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-100'
    : c <= 1 ? 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100'
      : 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100';

/** Cost / turns / duration of one run (from Claude Code's JSON result, stored by the engine). */
export function RunCost({ run }: { run: Run }) {
  const { me } = useAuth();
  const cost = num(run.cost_usd), turns = num(run.num_turns), dur = num(run.duration_s);
  // owner-only, never printed (seniors' briefing)
  if (me?.role !== 'owner') return null;
  if (cost == null && turns == null && dur == null) return null;
  return (
    <div className="no-print flex flex-wrap gap-2 text-sm">
      {cost != null && (
        <span className={`rounded-md px-2 py-0.5 font-semibold ${costTone(cost)}`} title={COST_TARGET} aria-label={`खर्च $${cost.toFixed(2)} — ${COST_TARGET}`}>
          खर्च ${cost.toFixed(2)}
        </span>
      )}
      {turns != null && <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-navy-800 dark:text-slate-200">पायऱ्या {turns}</span>}
      {dur != null && <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-navy-800 dark:text-slate-200">वेळ {fmtDuration(dur)}</span>}
    </div>
  );
}

/** Provisional total when no run has finished yet (minutes). Replaced by the median of real runs. */
const DEFAULT_RUN_MIN = 15; // first live run 01.11.2026: 10 min, 79 turns (all 3 files built)

/** Median engine seconds of recent runs that did the full work: done, or failed only at the end (≥30 turns). */
export function useTypicalRunSeconds() {
  const [v, setV] = useState<{ sec: number; n: number } | null>(null);
  useEffect(() => {
    let alive = true;
    void sb()
      .from('runs')
      .select('state,created_at,finished_at,duration_s,num_turns')
      .in('state', ['done', 'failed'])
      .not('finished_at', 'is', null)
      .order('finished_at', { ascending: false })
      .limit(20)
      .then(({ data }) => {
        if (!alive) return;
        type R = { state: string; created_at: string; finished_at: string; duration_s: number | string | null; num_turns: number | null };
        const d = ((data as R[]) || [])
          .filter(r => r.state === 'done' || (r.num_turns ?? 0) >= 30)
          .slice(0, 10)
          .map(r => (Date.parse(r.finished_at) - Date.parse(r.created_at)) / 1000)
          .filter(x => x > 0)
          .sort((a, b) => a - b);
        setV(d.length ? { sec: d[Math.floor(d.length / 2)], n: d.length } : { sec: DEFAULT_RUN_MIN * 60, n: 0 });
      });
    return () => { alive = false; };
  }, []);
  return v;
}

/** Elapsed + estimated remaining time for an active run (refreshes every 30 s). */
export function RunEta({ run }: { run: Run }) {
  const typical = useTypicalRunSeconds();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(t);
  }, []);
  if (!typical) return null;
  const elapsed = Math.max(0, (now - Date.parse(run.created_at)) / 1000);
  const left = typical.sec - elapsed;
  const basis = typical.n ? `मागील ${typical.n} प्रक्रियांच्या प्रत्यक्ष वेळेवरून` : 'प्राथमिक अंदाज';
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-900 dark:bg-blue-900/30 dark:text-blue-100">
      <span>⏱ लागलेला वेळ <b>{fmtDuration(elapsed)}</b></span>
      {left > 60 ? (
        <span>अंदाजे उरलेला वेळ <b>~{fmtDuration(left)}</b> (एकूण ~{fmtDuration(typical.sec)})</span>
      ) : (
        <span>अपेक्षेपेक्षा जास्त वेळ — अजून काही मिनिटे लागू शकतात</span>
      )}
      <span className="text-xs opacity-75">{basis}</span>
    </div>
  );
}

/** Engine model-routing lines in `runs.warnings` start with this prefix (not real warnings). */
const MODEL_PREFIX = 'मॉडेल:';

export function RunWarnings({ run }: { run: Run }) {
  const { me } = useAuth();
  const all = asArray(run.warnings).map(textOf).map(x => x.trim()).filter(Boolean);
  const models = all.filter(x => x.startsWith(MODEL_PREFIX)).map(x => x.slice(MODEL_PREFIX.length).trim());
  const w = all.filter(x => !x.startsWith(MODEL_PREFIX));
  // model-routing list: owner-only, never printed
  const showModels = me?.role === 'owner' && models.length > 0;
  if (!w.length && !showModels) return null;
  return (
    <>
      {w.length > 0 && (
        <ul className="space-y-1 rounded-lg bg-amber-100 px-3 py-2 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
          {w.map((x, i) => <li key={i}>⚠ {x}</li>)}
        </ul>
      )}
      {showModels && (
        <details className="no-print rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-navy-800 dark:text-slate-200">
          <summary className="cursor-pointer font-semibold">मॉडेल-वापर ({models.length})</summary>
          <ul className="mt-1 space-y-0.5 break-words">
            {models.map((x, i) => <li key={i}>• {x}</li>)}
          </ul>
        </details>
      )}
    </>
  );
}

/** `retryHint`: shown under a failure only when the caller really renders a "पुन्हा तयार करा" control next to it. */
export default function RunProgress({ run, retryHint }: { run: Run; retryHint?: string }) {
  const idx = stepIndex(run);
  const stale = isStale(run);
  const failed = run.state === 'failed' || stale;
  const active = !failed && (run.state === 'queued' || run.state === 'running');
  // while active, the bar also fills with elapsed time vs the typical run time (capped at 95 %)
  const typical = useTypicalRunSeconds();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(t);
  }, [active]);
  const elapsed = Math.max(0, (now - Date.parse(run.created_at)) / 1000);
  const stepPct = Math.round((idx / (RUN_STEPS.length - 1)) * 100);
  const timePct = typical ? Math.min(95, Math.round((elapsed / typical.sec) * 100)) : 0;
  const pct = run.state === 'done' ? 100 : active ? Math.max(4, stepPct, timePct) : stepPct;
  // the GitHub runner is still starting / installing tools while the run row says queued
  const preparing = run.state === 'queued' && !run.step && elapsed > 20;
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {active ? (
            <span className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
              <Spinner className="h-4 w-4" /> {preparing ? 'तयारी चालू — सर्व्हर सुरू होत आहे' : 'प्रक्रिया चालू'}
            </span>
          ) : (
            <Chip tone={stale ? 'red' : runTone(run.state)}>{stale ? 'वेळ संपली' : stateText(run.state)}</Chip>
          )}
          <span className="text-sm text-slate-500 dark:text-slate-400">प्रक्रिया क्र. {run.id} • {fmtDateTime(run.created_at)}</span>
        </div>
        <RunCost run={run} />
      </div>
      <Progress pct={failed ? 100 : pct} tone={failed ? 'red' : run.state === 'done' ? 'green' : 'blue'} active={active} label={`प्रक्रिया क्र. ${run.id} — ${stale ? 'वेळ संपली' : stateText(run.state)}`} />
      <ol className="grid grid-cols-4 gap-1 text-center text-xs sm:grid-cols-7 sm:text-sm">
        {RUN_STEPS.map((s, i) => {
          const done = i < idx || run.state === 'done';
          const cur = i === idx && run.state !== 'done' && !failed;
          return (
            <li
              key={s.key}
              className={`rounded-md px-1 py-1.5 font-semibold ${
                done ? 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-200'
                  : cur ? 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-200'
                    : failed && i === idx ? 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200'
                      : 'bg-slate-100 text-slate-500 dark:bg-navy-800 dark:text-slate-400'
              }`}
            >
              {cur && <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-600" aria-hidden="true" />}
              {s.label}
            </li>
          );
        })}
      </ol>
      {run.step && !failed && <div className="text-sm text-slate-600 dark:text-slate-300">सद्य: {run.step}</div>}
      {!failed && (run.state === 'queued' || run.state === 'running') && <RunEta run={run} />}
      {failed && (
        <div className="rounded-lg bg-red-100 px-3 py-2 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">
          <div className="font-semibold">प्रक्रिया अयशस्वी</div>
          <div className="mt-1 whitespace-pre-wrap break-words">{stale ? STALE_REASON : run.step || 'कारण उपलब्ध नाही'}</div>
          {retryHint && <div className="mt-1 text-sm">{retryHint}</div>}
        </div>
      )}
      <RunWarnings run={run} />
    </div>
  );
}

/** Compact live status of a case's latest run (list rows, global bar). */
export function RunStateBadge({ run }: { run: Run | undefined }) {
  if (!run) return <span className="text-sm text-slate-500">—</span>;
  const stale = isStale(run);
  if (!stale && (run.state === 'queued' || run.state === 'running'))
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
        <Spinner className="h-3.5 w-3.5" /> प्रक्रिया चालू
      </span>
    );
  if (run.state === 'done') return <Chip tone="green">✓ तयार</Chip>;
  return <Chip tone="red">{stale ? 'वेळ संपली' : 'अयशस्वी'}</Chip>;
}
