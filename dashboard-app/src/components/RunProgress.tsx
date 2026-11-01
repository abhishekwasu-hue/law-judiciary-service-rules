import { useEffect, useState } from 'react';
import { sb } from '../lib/supabase';
import type { Run } from '../lib/types';
import { RUN_STATE_LABEL, RUN_STEPS, STALE_REASON, isStale, runTone } from '../lib/constants';
import { asArray, fmtDateTime, textOf } from '../lib/format';
import { Chip, Progress } from './ui';

/** Latest runs of a case, kept live through Supabase Realtime (table `runs`). */
export function useRuns(caseId: number | null) {
  const [runs, setRuns] = useState<Run[] | null>(null);
  useEffect(() => {
    if (!caseId) return;
    let alive = true;
    const load = () =>
      sb()
        .from('runs')
        .select('*')
        .eq('case_id', caseId)
        .order('created_at', { ascending: false })
        .then(({ data }) => alive && setRuns((data as Run[]) || []));
    void load();
    const ch = sb()
      .channel(`runs-${caseId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'runs', filter: `case_id=eq.${caseId}` }, p => {
        const row = p.new as Run;
        if (!row?.id) return;
        setRuns(s => {
          const list = s || [];
          return list.some(r => r.id === row.id) ? list.map(r => (r.id === row.id ? row : r)) : [row, ...list];
        });
      })
      .subscribe();
    return () => {
      alive = false;
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

/** Cost / turns / duration of one run (from Claude Code's JSON result, stored by the engine). */
export function RunCost({ run }: { run: Run }) {
  const cost = num(run.cost_usd), turns = num(run.num_turns), dur = num(run.duration_s);
  if (cost == null && turns == null && dur == null) return null;
  return (
    <div className="flex flex-wrap gap-2 text-sm">
      {cost != null && <span className="rounded-md bg-amber-100 px-2 py-0.5 font-semibold text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">खर्च ${cost.toFixed(2)}</span>}
      {turns != null && <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-navy-800 dark:text-slate-200">पायऱ्या {turns}</span>}
      {dur != null && <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-navy-800 dark:text-slate-200">वेळ {fmtDuration(dur)}</span>}
    </div>
  );
}

/** Provisional total when no run has finished yet (minutes). Replaced by the median of real runs. */
const DEFAULT_RUN_MIN = 30;

/** Median wall-clock seconds (created → finished) of the last finished runs, all cases. */
export function useTypicalRunSeconds() {
  const [v, setV] = useState<{ sec: number; n: number } | null>(null);
  useEffect(() => {
    let alive = true;
    void sb()
      .from('runs')
      .select('created_at,finished_at')
      .eq('state', 'done')
      .not('finished_at', 'is', null)
      .order('finished_at', { ascending: false })
      .limit(10)
      .then(({ data }) => {
        if (!alive) return;
        const d = ((data as { created_at: string; finished_at: string }[]) || [])
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
  const basis = typical.n ? `मागील ${typical.n} पूर्ण अभ्यासांवरून` : 'प्राथमिक अंदाज';
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

export function RunWarnings({ run }: { run: Run }) {
  const w = asArray(run.warnings).map(textOf).filter(Boolean);
  if (!w.length) return null;
  return (
    <ul className="space-y-1 rounded-lg bg-amber-100 px-3 py-2 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
      {w.map((x, i) => <li key={i}>⚠ {x}</li>)}
    </ul>
  );
}

export default function RunProgress({ run }: { run: Run }) {
  const idx = stepIndex(run);
  const stale = isStale(run);
  const failed = run.state === 'failed' || stale;
  const pct = run.state === 'done' ? 100 : Math.round((idx / (RUN_STEPS.length - 1)) * 100);
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Chip tone={stale ? 'red' : runTone(run.state)}>{stale ? 'वेळ संपली' : RUN_STATE_LABEL[run.state] || run.state}</Chip>
          <span className="text-sm text-slate-500 dark:text-slate-400">अभ्यास #{run.id} • {fmtDateTime(run.created_at)}</span>
        </div>
        <RunCost run={run} />
      </div>
      <Progress pct={failed ? 100 : pct} tone={failed ? 'red' : run.state === 'done' ? 'green' : 'blue'} />
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
          <div className="font-semibold">अभ्यास अयशस्वी</div>
          <div className="mt-1 whitespace-pre-wrap break-words">{stale ? STALE_REASON : run.step || 'कारण उपलब्ध नाही — पुन्हा तयार करा'}</div>
          <div className="mt-1 text-sm">खालील "पुन्हा तयार करा" वापरा.</div>
        </div>
      )}
      <RunWarnings run={run} />
    </div>
  );
}
