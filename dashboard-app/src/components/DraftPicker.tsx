// "कोणते मसुदे हवेत?" (C28): toggle chips in three groups (पत्रे / आदेश / न्यायालय-विधिमंडळ; two per row on a phone),
// the suggestion line and the estimate line.
import { useEffect, useState } from 'react';
import { sb } from '../lib/supabase';
import { DRAFT_GROUPS, DRAFT_KEYS, DRAFT_LABEL, type DraftKey } from '../lib/constants';
import { EXTRA_DRAFT_MIN, EXTRA_DRAFT_USD, draftEstimate, draftLabels, sameDrafts, type Suggestion } from '../lib/drafts';
import { useTypicalRunSeconds } from './RunProgress';

/** Same fallback as the Worker's runEstimate (DEFAULT_RUN_USD) when no finished run has a cost. */
const DEFAULT_RUN_USD = 0.75;

/** Median cost_usd of the last 20 done runs (null while loading). */
function useTypicalRunUsd() {
  const [v, setV] = useState<number | null>(null);
  useEffect(() => {
    let alive = true;
    void sb()
      .from('runs')
      .select('cost_usd')
      .eq('state', 'done')
      .not('cost_usd', 'is', null)
      .order('created_at', { ascending: false })
      .limit(20)
      .then(({ data }) => {
        if (!alive) return;
        const c = ((data as { cost_usd: number | string | null }[]) || []).map(r => Number(r.cost_usd)).filter(Number.isFinite).sort((a, b) => a - b);
        setV(c.length ? (c.length % 2 ? c[(c.length - 1) / 2] : (c[c.length / 2 - 1] + c[c.length / 2]) / 2) : DEFAULT_RUN_USD);
      });
    return () => { alive = false; };
  }, []);
  return v;
}

export default function DraftPicker({ value, onChange, suggestion, disabled }: {
  value: DraftKey[]; onChange: (v: DraftKey[]) => void; suggestion: Suggestion; disabled?: boolean;
}) {
  const sec = useTypicalRunSeconds();
  const usd = useTypicalRunUsd();
  const toggle = (k: DraftKey) => onChange(DRAFT_KEYS.filter(x => (x === k ? !value.includes(x) : value.includes(x))));
  const est = sec && usd !== null ? draftEstimate(value, sec.sec, usd) : null;
  const differs = !sameDrafts(value, suggestion.keys);
  return (
    <fieldset className="min-w-0 space-y-2" disabled={disabled}>
      <legend className="label mb-0">कोणते मसुदे हवेत?</legend>
      <p className="text-sm text-slate-500 dark:text-slate-400">नोंद, अभ्यास-फाइल व GR सह PDF नेहमी मिळतील</p>
      {DRAFT_GROUPS.map(g => {
        const n = g.keys.filter(k => value.includes(k)).length;
        return (
          <div key={g.label} role="group" aria-label={g.label} className="min-w-0 space-y-1">
            <div className="text-sm font-semibold text-slate-600 dark:text-slate-300">
              {g.label}
              {n > 0 && <span className="ml-1 rounded-full bg-navy-100 px-1.5 text-xs text-navy-900 dark:bg-navy-800 dark:text-navy-100">{n}</span>}
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {g.keys.map(k => {
                const on = value.includes(k);
                return (
                  <button
                    key={k}
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggle(k)}
                    className={`flex min-h-[44px] min-w-0 items-center justify-center gap-1 break-words rounded-lg border-2 px-2 py-1 text-center text-base font-semibold leading-tight transition disabled:opacity-50 ${
                      on
                        ? 'border-navy-700 bg-navy-700 text-white dark:border-navy-400 dark:bg-navy-500'
                        : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-100 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-100 dark:hover:bg-navy-800'
                    }`}
                  >
                    {on && <span aria-hidden="true">✓</span>}
                    {DRAFT_LABEL[k]}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
      {value.length === 0 && <div className="rounded-lg bg-amber-100 px-3 py-1.5 text-sm font-semibold text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">फक्त नोंद तयार होईल</div>}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        <span className="text-slate-700 dark:text-slate-200">सुचवलेले: <b>{draftLabels(suggestion.keys)}</b> <span className="text-slate-500 dark:text-slate-400">({suggestion.reason})</span></span>
        {differs && !disabled && (
          <button type="button" className="min-h-tap rounded-md px-2 font-semibold text-navy-700 underline dark:text-navy-200" onClick={() => onChange(suggestion.keys)}>
            सुचवलेले घ्या
          </button>
        )}
      </div>
      {est && (
        <div className="text-sm text-slate-500 dark:text-slate-400" title={`मागील प्रक्रियांवरून; प्रत्येक जादा मसुदा +${EXTRA_DRAFT_MIN} मि., +$${EXTRA_DRAFT_USD.toFixed(2)} (अंदाज)`}>
          अंदाजे वेळ ~{est.min} मि. · खर्च ~${est.usd.toFixed(2)}
        </div>
      )}
    </fieldset>
  );
}
