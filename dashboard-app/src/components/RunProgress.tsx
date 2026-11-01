import { useEffect, useState } from 'react';
import { sb } from '../lib/supabase';
import type { Run } from '../lib/types';
import { RUN_STATE_LABEL, RUN_STEPS, runTone } from '../lib/constants';
import { fmtDateTime } from '../lib/format';
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

export default function RunProgress({ run }: { run: Run }) {
  const idx = stepIndex(run);
  const failed = run.state === 'failed';
  const pct = run.state === 'done' ? 100 : Math.round((idx / (RUN_STEPS.length - 1)) * 100);
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Chip tone={runTone(run.state)}>{RUN_STATE_LABEL[run.state] || run.state}</Chip>
          <span className="text-sm text-slate-500 dark:text-slate-400">अभ्यास #{run.id} • {fmtDateTime(run.created_at)}</span>
        </div>
        {run.log_url && (
          <span className="text-sm text-slate-500" title={run.log_url}>log उपलब्ध</span>
        )}
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
      {run.step && <div className="text-sm text-slate-600 dark:text-slate-300">सद्य: {run.step}</div>}
      {failed && <div className="rounded-lg bg-red-100 px-3 py-2 text-red-900 dark:bg-red-900/40 dark:text-red-100">अभ्यास अयशस्वी. {run.step || ''}</div>}
    </div>
  );
}
