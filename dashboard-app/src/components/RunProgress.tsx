import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { sb } from '../lib/supabase';
import type { Run } from '../lib/types';
import { RUN_STATE_LABEL, RUN_STEPS, STALE_REASON, isEditRun, isStale, isWaiting, runTone } from '../lib/constants';
import { asArray, cleanReason, cleanStep, criticalWarnings, fmtDateTime, isOwnerOnlyLine, studyWarningTexts, textOf } from '../lib/format';
import { useAuth } from '../lib/auth';
import { Chip, Progress, Spinner } from './ui';
import { studyPointsText } from '../lib/perf';

/** Glossary wording for a run state (प्रक्रिया प्रतीक्षेत / चालू / पूर्ण / अयशस्वी). */
const STATE_TEXT: Record<string, string> = { queued: 'प्रक्रिया प्रतीक्षेत', running: 'प्रक्रिया चालू', done: 'प्रक्रिया पूर्ण', failed: 'प्रक्रिया अयशस्वी' };
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

const findStep = (text: string | null | undefined) => {
  const s = (text || '').toLowerCase();
  return s ? RUN_STEPS.findIndex(x => s.includes(x.key.toLowerCase())) : -1;
};
/** Step of the progress row. A failed run's `step` is the failure reason, so its step comes from `last_step`
 *  (migration 0007); without it: never started = "रांगेत" (e.g. GitHub dispatch failed), started = unknown (-1, no red mark). */
function stepIndex(r: Run): number {
  if (r.state === 'done') return RUN_STEPS.length - 1;
  if (r.state === 'failed') {
    if (r.last_step) { const i = findStep(r.last_step); return i < 0 ? 1 : i; }
    return r.started_at ? -1 : 0;
  }
  if (r.state === 'queued' && !r.step) return 0;
  const i = findStep(r.step);
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
      // '*' (not a column list): dispatched_at exists only after migration 0011; a missing column must not break the read
      .select('*')
      .in('state', ['done', 'failed'])
      .not('finished_at', 'is', null)
      .order('finished_at', { ascending: false })
      .limit(40)
      .then(({ data }) => {
        if (!alive) return;
        type R = { kind?: string | null; state: string; created_at: string; dispatched_at?: string | null; finished_at: string; duration_s: number | string | null; num_turns: number | null };
        const d = ((data as R[]) || [])
          .filter(r => !isEditRun(r)) // सुधारणा runs take a minute or two — not a processing run
          .filter(r => r.state === 'done' || (r.num_turns ?? 0) >= 30)
          .slice(0, 10)
          .map(r => (Date.parse(r.finished_at) - Date.parse(r.dispatched_at || r.created_at)) / 1000) // queue wait not counted
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
  if (!typical || isWaiting(run)) return null;
  const elapsed = Math.max(0, (now - Date.parse(run.dispatched_at || run.created_at)) / 1000);
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

/** Abhi 03.11.2026 ("हे इशारे नोटिंग मध्ये नको … स्टडी … फाईल … त्याच्यामध्ये द्या"): a finished run's warnings are written
 *  into the Study (end of भाग 7, tools/study_warnings.py) — the case page shows only this one neutral line.
 *  `studyHref`: link to the Study tab (case page); without it plain text. */
export function StudyWarningsLine({ run, studyHref, className = '' }: { run: Run | undefined; studyHref?: string; className?: string }) {
  const n = run && run.state === 'done' ? studyWarningTexts(run.warnings).length : 0;
  if (!n) return null;
  const text = studyPointsText(n); // U6: 1 मुद्दा … पाहावा / N मुद्दे … पाहावेत
  return (
    <div className={`text-sm text-slate-600 dark:text-slate-300 break-words [overflow-wrap:anywhere] ${className}`}>
      ⓘ {studyHref ? <Link className="font-semibold text-navy-600 underline-offset-2 hover:underline dark:text-navy-200" to={studyHref}>{text}</Link> : text}
    </div>
  );
}

/** Owner-only run lines (model routing, cost, AI provider): a collapsed list for the owner, never printed. */
export function OwnerRunLines({ run }: { run: Run }) {
  const { me } = useAuth();
  if (me?.role !== 'owner') return null;
  const lines = asArray(run.warnings).map(textOf).map(x => x.trim()).filter(x => x && isOwnerOnlyLine(x))
    .map(x => (x.startsWith(MODEL_PREFIX) ? x.slice(MODEL_PREFIX.length).trim() : x));
  if (!lines.length) return null;
  return (
    <details className="no-print rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-navy-800 dark:text-slate-200">
      <summary className="cursor-pointer font-semibold">मॉडेल-वापर ({lines.length})</summary>
      <ul className="mt-1 space-y-0.5 break-words [overflow-wrap:anywhere]">
        {lines.map((x, i) => <li key={i}>• {x}</li>)}
      </ul>
    </details>
  );
}

/** A run's warnings: finished run -> the neutral Study line (the warnings are in the Study); a run still going or failed
 *  (no Study yet) -> the plain list; plus the owner's list. */
export function RunWarnings({ run, studyHref }: { run: Run; studyHref?: string }) {
  const w = run.state === 'done' ? [] : studyWarningTexts(run.warnings);
  return (
    <>
      <StudyWarningsLine run={run} studyHref={studyHref} />
      {w.length > 0 && (
        <ul className="space-y-1 rounded-lg bg-amber-100 px-3 py-2 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
          {w.map((x, i) => <li key={i} className="break-words [overflow-wrap:anywhere]">⚠ {x}</li>)}
        </ul>
      )}
      <OwnerRunLines run={run} />
    </>
  );
}

/** `retryHint`: shown under a failure only when the caller really renders a "पुन्हा तयार करा" control next to it. */
export default function RunProgress({ run, retryHint }: { run: Run; retryHint?: string }) {
  const { me } = useAuth();
  const isOwner = me?.role === 'owner';
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
  const waiting = isWaiting(run);
  const elapsed = waiting ? 0 : Math.max(0, (now - Date.parse(run.dispatched_at || run.created_at)) / 1000);
  const stepPct = Math.round((idx / (RUN_STEPS.length - 1)) * 100);
  const timePct = typical ? Math.min(95, Math.round((elapsed / typical.sec) * 100)) : 0;
  const pct = run.state === 'done' ? 100 : active ? Math.max(4, stepPct, timePct) : stepPct;
  // the GitHub runner is still starting / installing tools while the run row says queued
  const preparing = !waiting && run.state === 'queued' && !run.step && elapsed > 20;
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {active ? (
            <span className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
              <Spinner className="h-4 w-4" /> {waiting ? 'प्रतीक्षेत — आधीची प्रक्रिया पूर्ण झाल्यावर आपोआप सुरू होईल' : preparing ? 'तयारी चालू — सर्व्हर सुरू होत आहे' : 'प्रक्रिया चालू'}
            </span>
          ) : (
            <Chip tone={stale ? 'red' : runTone(run.state)}>{stale ? 'वेळ संपली' : stateText(run.state)}</Chip>
          )}
          {/* run id: owner only (X4) */}
          <span className="text-sm text-slate-500 dark:text-slate-400">{isOwner ? `प्रक्रिया क्र. ${run.id} • ` : ''}{fmtDateTime(run.created_at)}</span>
        </div>
        <RunCost run={run} />
      </div>
      <Progress pct={failed ? 100 : pct} tone={failed ? 'red' : run.state === 'done' ? 'green' : 'blue'} active={active} label={`प्रक्रिया — ${stale ? 'वेळ संपली' : stateText(run.state)}`} />
      <ol className="grid grid-cols-4 gap-1 text-center text-xs sm:grid-cols-7 sm:text-sm">
        {RUN_STEPS.map((s, i) => {
          const done = i < idx || run.state === 'done' || (idx < 0 && i === 0);
          const cur = i === idx && run.state !== 'done' && !failed;
          return (
            <li
              key={s.key}
              className={`rounded-md px-1 py-1.5 font-semibold ${
                done ? 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-200'
                  : cur ? 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-200'
                    : failed && i === idx ? 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200'
                      : 'bg-slate-100 text-slate-600 dark:bg-navy-800 dark:text-slate-300'
              }`}
            >
              {cur && <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-600" aria-hidden="true" />}
              {s.label}
            </li>
          );
        })}
      </ol>
      {!failed && cleanStep(run.step, isOwner) && <div className="text-sm text-slate-600 dark:text-slate-300 break-words [overflow-wrap:anywhere]">सद्य: {cleanStep(run.step, isOwner)}</div>}
      {!failed && (run.state === 'queued' || run.state === 'running') && <RunEta run={run} />}
      {failed && (
        <div className="rounded-lg bg-red-100 px-3 py-2 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">
          <div className="font-semibold">प्रक्रिया अयशस्वी{!stale && idx >= 0 && run.state === 'failed' ? ` — टप्पा: ${RUN_STEPS[idx].label}` : ''}</div>
          <div className="mt-1 whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{stale ? STALE_REASON : cleanReason(run.step, isOwner) || 'कारण उपलब्ध नाही'}</div>
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
  if (!stale && isWaiting(run)) return <Chip tone="amber">⏳ प्रतीक्षेत</Chip>;
  if (!stale && (run.state === 'queued' || run.state === 'running'))
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
        <Spinner className="h-3.5 w-3.5" /> प्रक्रिया चालू
      </span>
    );
  if (run.state === 'done') return criticalWarnings(run.warnings).length ? <Chip tone="amber">⚠ तयार — तपासणी अपूर्ण</Chip> : <Chip tone="green">✓ तयार</Chip>;
  return <Chip tone="red">{stale ? 'वेळ संपली' : 'अयशस्वी'}</Chip>;
}
