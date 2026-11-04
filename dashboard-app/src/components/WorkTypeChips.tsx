// Work-category filter chips with counts (C33): "सर्व N" + one chip per WORK_TYPES id. Controlled (value '' = all);
// with `linkTo` the chips are links (Home → /cases?work=<id>) instead of toggles.
import { Link } from 'react-router-dom';
import { WORK_TYPES, workTypeOf } from '../lib/constants';
import type { Case } from '../lib/types';

const base = 'inline-flex min-h-tap items-center gap-1.5 rounded-full border-2 px-3 text-sm font-semibold transition';
const on = 'border-navy-700 bg-navy-700 text-white dark:border-navy-400 dark:bg-navy-500';
const off = 'border-slate-300 bg-white text-slate-800 hover:bg-slate-100 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-100 dark:hover:bg-navy-800';

export default function WorkTypeChips({ cases, value = '', onChange, linkTo }: {
  cases: Case[]; value?: string; onChange?: (v: string) => void; linkTo?: (id: string) => string;
}) {
  const count = (id: string) => cases.filter(c => workTypeOf(c) === id).length;
  const items = [{ id: '', label: 'सर्व', n: cases.length }, ...WORK_TYPES.map(w => ({ id: w.id as string, label: w.short, n: count(w.id) }))];
  return (
    <div className="flex flex-wrap gap-2" role={linkTo ? undefined : 'group'} aria-label="कामाचा प्रकार">
      {items.map(x => {
        const active = !linkTo && value === x.id;
        const inner = (
          <>
            <span>{x.label}</span>
            <span className={`rounded-full px-1.5 text-xs font-bold ${active ? 'bg-white/20' : 'bg-slate-100 dark:bg-navy-800'}`}>{x.n}</span>
          </>
        );
        return linkTo ? (
          <Link key={x.id} to={linkTo(x.id)} className={`${base} ${off}`}>{inner}</Link>
        ) : (
          <button key={x.id} type="button" aria-pressed={active} className={`${base} ${active ? on : off}`} onClick={() => onChange?.(x.id)}>{inner}</button>
        );
      })}
    </div>
  );
}
