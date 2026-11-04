// "रांग" card (C33): runs are processed one by one by the Worker's sequential queue. Shows तयार (today) / चालू / रांगेत
// with each waiting case's position and an estimated time, from the latest run of every case (useData, live via Realtime)
// and the typical run time of recent runs (useTypicalRunSeconds — same basis as the run page's ETA).
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useData } from '../lib/data';
import { TONE_HEX, isStale, isWaiting, type Tone } from '../lib/constants';
import { crLabel } from '../lib/format';
import type { Run } from '../lib/types';
import { Chip, Spinner } from './ui';
import { fmtDuration, useTypicalRunSeconds } from './RunProgress';

const sameDay = (iso: string | null | undefined, d: Date) => {
  if (!iso) return false;
  const x = new Date(iso);
  return x.getFullYear() === d.getFullYear() && x.getMonth() === d.getMonth() && x.getDate() === d.getDate();
};

function Num({ label, value, tone }: { label: string; value: number; tone: Tone }) {
  return (
    <div className="rounded-lg bg-slate-50 px-2 py-2 text-center dark:bg-navy-800/60">
      <div className="font-head text-2xl font-bold leading-none sm:text-3xl" style={{ color: TONE_HEX[tone] }}>{value}</div>
      <div className="mt-1 text-sm font-semibold leading-tight text-slate-600 dark:text-slate-300">{label}</div>
    </div>
  );
}

export interface QueueRow { run: Run; kind: 'running' | 'waiting'; position: number; leftSec: number | null }

/** Pure: order and estimate. running first (by start), then waiting FIFO by created_at; leftSec = estimated time until that
 *  run is ready (running: typical − elapsed, at least 1 min; waiting k: rest of the running ones + k × typical). */
export function queueRows(runs: Run[], typicalSec: number | null, now: number): QueueRow[] {
  const active = runs.filter(r => (r.state === 'queued' || r.state === 'running') && !isStale(r));
  const running = active.filter(r => !isWaiting(r)).sort((a, b) => (a.created_at < b.created_at ? -1 : 1));
  const waiting = active.filter(r => isWaiting(r)).sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : a.id - b.id));
  const runLeft = (r: Run) => (typicalSec == null ? null : Math.max(60, typicalSec - (now - Date.parse(r.dispatched_at || r.created_at)) / 1000));
  const rows: QueueRow[] = running.map(r => ({ run: r, kind: 'running', position: 0, leftSec: runLeft(r) }));
  // the queue moves when the (last) running run ends
  const base = rows.reduce((m, x) => Math.max(m, x.leftSec ?? 0), 0);
  waiting.forEach((r, i) => rows.push({ run: r, kind: 'waiting', position: i + 1, leftSec: typicalSec == null ? null : base + (i + 1) * typicalSec }));
  return rows;
}

export default function QueueCard({ className = '' }: { className?: string }) {
  const { cases, latestRuns } = useData();
  const typical = useTypicalRunSeconds();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(t);
  }, []);
  const runs = useMemo(() => [...latestRuns.values()], [latestRuns]);
  const rows = useMemo(() => queueRows(runs, typical?.sec ?? null, now), [runs, typical, now]);
  const today = new Date(now);
  const ready = runs.filter(r => r.state === 'done' && sameDay(r.finished_at, today)).length;
  const nRun = rows.filter(r => r.kind === 'running').length;
  const nWait = rows.length - nRun;
  if (!rows.length && !ready) return null;
  const allLeft = rows.length ? Math.max(...rows.map(r => r.leftSec ?? 0)) : 0;
  const label = (r: Run) => {
    const c = cases.find(x => x.id === r.case_id);
    return c ? crLabel(c) : `प्रकरण #${r.case_id}`;
  };
  return (
    <section className={`card min-w-0 p-3 sm:p-4 ${className}`} aria-label="प्रक्रियेची रांग">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-lg font-bold">रांग</h2>
        {rows.length > 0 && typical && (
          <span className="text-sm text-slate-600 dark:text-slate-300">सर्व पूर्ण: अंदाजे <b>~{fmtDuration(allLeft)}</b></span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Num label="तयार (आज)" value={ready} tone="green" />
        <Num label="चालू" value={nRun} tone="blue" />
        <Num label="रांगेत" value={nWait} tone="amber" />
      </div>
      {rows.length > 0 && (
        <ol className="mt-3 divide-y divide-slate-100 dark:divide-navy-800">
          {rows.map(x => (
            <li key={x.run.id}>
              <Link to={`/cases/${x.run.case_id}`} className="flex min-h-tap items-center justify-between gap-2 py-1.5">
                <span className="flex min-w-0 items-center gap-2">
                  {x.kind === 'running' ? (
                    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100"><Spinner className="h-3.5 w-3.5" /> चालू</span>
                  ) : (
                    <span className="shrink-0 whitespace-nowrap"><Chip tone="amber">क्रमांक {x.position}</Chip></span>
                  )}
                  <span className="truncate font-semibold">{label(x.run)}</span>
                </span>
                <span className="shrink-0 text-sm text-slate-600 dark:text-slate-300">{x.leftSec != null ? `~${fmtDuration(x.leftSec)}` : '—'}</span>
              </Link>
            </li>
          ))}
        </ol>
      )}
      {rows.length > 0 && (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          एका वेळी एक प्रस्ताव • प्रत्येक प्रस्ताव तयार होताच प्रकरणात उपलब्ध • वेळ {typical?.n ? `मागील ${typical.n} प्रक्रियांवरून` : 'प्राथमिक'} अंदाज
        </p>
      )}
    </section>
  );
}
