import { fmtDate } from '../lib/format';
import { daysSince, type NastiRow } from '../lib/nasti';

/** where / holder / days / status / due of one नस्ती row — numbers first, compact chips. */
export default function NastiFacts({ r }: { r: NastiRow }) {
  const days = daysSince(r.since);
  const tone = days === null ? 'bg-slate-100 text-slate-700 dark:bg-navy-800 dark:text-slate-200' : days > 15 ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200' : days > 7 ? 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100' : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200';
  return (
    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-sm">
      {days !== null && <span className={`rounded px-1.5 py-0.5 font-bold ${tone}`}>{days} दिवस</span>}
      <span className="min-w-0 break-words"><span className="text-slate-500 dark:text-slate-400">कुठे:</span> <b>{r.where || '—'}</b>{r.holder ? ` (${r.holder})` : ''}</span>
      {r.status && <span className="rounded bg-blue-100 px-1.5 py-0.5 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">{r.status}</span>}
      {r.due && <span><span className="text-slate-500 dark:text-slate-400">मुदत:</span> <b>{fmtDate(r.due)}</b></span>}
    </div>
  );
}
