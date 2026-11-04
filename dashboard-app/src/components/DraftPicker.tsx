// "कोणते मसुदे हवेत?" (C28). UI audit 04.11.2026 (N6, N8, N18): the suggestion line first, the four common drafts as
// chips with a one-line help each, the other twelve behind "इतर मसुदे (12) ▼" (grouped पत्रे / आदेश / न्यायालय-विधिमंडळ),
// then the estimate line (time for everyone, cost for the owner only). The compact form (bulk rows) opens the same chips.
import { useEffect, useState } from 'react';
import { sb } from '../lib/supabase';
import { useAuth } from '../lib/auth';
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
      // '*': runs.kind exists only after migration 0013 (a missing column must not break the read); edit runs left out
      .select('*')
      .eq('state', 'done')
      .not('cost_usd', 'is', null)
      .order('created_at', { ascending: false })
      .limit(40)
      .then(({ data }) => {
        if (!alive) return;
        const c = ((data as { kind?: string | null; cost_usd: number | string | null }[]) || []).filter(r => r.kind !== 'edit').slice(0, 20).map(r => Number(r.cost_usd)).filter(Number.isFinite).sort((a, b) => a - b);
        setV(c.length ? (c.length % 2 ? c[(c.length - 1) / 2] : (c[c.length / 2 - 1] + c[c.length / 2]) / 2) : DEFAULT_RUN_USD);
      });
    return () => { alive = false; };
  }, []);
  return v;
}

/** The four drafts most proposals need (N6); the rest are folded. */
const COMMON: readonly DraftKey[] = ['letter', 'reminder', 'gr', 'parawise'];
const OTHER_GROUPS = DRAFT_GROUPS.map(g => ({ label: g.label, keys: g.keys.filter(k => !COMMON.includes(k)) })).filter(g => g.keys.length);
const OTHER_N = OTHER_GROUPS.reduce((n, g) => n + g.keys.length, 0);
/** One line per draft: when it is used (INSTRUCTIONS §4.28 / §4.33). */
export const DRAFT_HELP: Record<DraftKey, string> = {
  letter: 'माहिती मागविणे, उत्तर देणे किंवा कळविणे',
  reminder: 'पाठविलेल्या पत्रास उत्तर अप्राप्त असल्यास',
  gr: 'मान्यता प्राप्त झाल्यावर शासन निर्णय-प्रारूप',
  parawise: 'न्यायालयीन याचिकेवर अभिप्राय (इंग्रजी)',
  corrigendum: 'शासन निर्णयातील दुरुस्ती',
  circular: 'कार्यालयांना सर्वसाधारण सूचना',
  memo: 'संबंधित कर्मचारी / कार्यालयास निर्णय कळविणे',
  notification: 'राजपत्रात प्रसिद्ध करावयाचा आदेश',
  do_letter: 'स्मरणपत्रांनंतरही उत्तर अप्राप्त असल्यास वैयक्तिक पत्र',
  uo_note: 'इतर विभागाचा अभिप्राय / सहमती घेण्यासाठी',
  endorsement: 'प्राप्त पत्राची प्रत इतर अधिकाऱ्यांना पाठविणे',
  office_order: 'कार्यालयांतर्गत निर्णय (नेमणूक, कामवाटप)',
  press_note: 'महत्त्वाचा निर्णय वृत्तपत्रांसाठी',
  addendum: 'शासन निर्णयात भर घालणे',
  affidavit: 'याचिकेत शासनाचे शपथपत्र (इंग्रजी)',
  lq: 'तारांकित / अतारांकित प्रश्नाचे उत्तर',
};
const DEFAULT_REASONS = ['पहिली प्रक्रिया', 'नेहमीप्रमाणे'];
/** "सुचवलेले: पत्र — बहुतेक प्रस्तावांसाठी हेच पुरेसे." / "सुचवलेले: शासन निर्णय — मान्यता प्राप्त." */
function suggestionWhy(s: Suggestion) {
  return sameDrafts(s.keys, ['letter']) && DEFAULT_REASONS.includes(s.reason) ? 'बहुतेक प्रस्तावांसाठी हेच पुरेसे' : s.reason;
}

/** Chips: the common four (with their help line), then "इतर मसुदे (12) ▼" — opens by itself when one of those is chosen. */
function Chips({ value, onChange, small }: { value: DraftKey[]; onChange: (v: DraftKey[]) => void; small?: boolean }) {
  const toggle = (k: DraftKey) => onChange(DRAFT_KEYS.filter(x => (x === k ? !value.includes(x) : value.includes(x))));
  const otherOn = OTHER_GROUPS.reduce((n, g) => n + g.keys.filter(k => value.includes(k)).length, 0);
  const [open, setOpen] = useState(otherOn > 0);
  useEffect(() => { if (otherOn > 0) setOpen(true); }, [otherOn]);
  const chip = (k: DraftKey, help: boolean) => {
    const on = value.includes(k);
    return (
      <button key={k} type="button" aria-pressed={on} onClick={() => toggle(k)} title={DRAFT_HELP[k]}
        aria-label={`${DRAFT_LABEL[k]} — ${DRAFT_HELP[k]}`}
        className={`flex min-h-[44px] min-w-0 flex-col items-center justify-center break-words rounded-lg border-2 px-2 py-1 text-center leading-tight transition disabled:opacity-50 ${
          on ? 'border-navy-700 bg-navy-700 text-white dark:border-navy-400 dark:bg-navy-500'
            : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-100 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-100 dark:hover:bg-navy-800'
        }`}>
        <span className={`font-semibold ${small ? 'text-sm' : 'text-base'}`}>{on && <span aria-hidden="true">✓ </span>}{DRAFT_LABEL[k]}</span>
        {help && <span aria-hidden="true" className={`mt-0.5 text-xs font-normal ${on ? 'text-navy-100' : 'text-slate-500 dark:text-slate-400'}`}>{DRAFT_HELP[k]}</span>}
      </button>
    );
  };
  return (
    <div className="min-w-0 space-y-2">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="group" aria-label="नेहमीचे मसुदे">{COMMON.map(k => chip(k, true))}</div>
      <button type="button" aria-expanded={open} onClick={() => setOpen(o => !o)}
        className="min-h-tap rounded-md px-1 text-sm font-semibold text-navy-700 underline dark:text-navy-200">
        इतर मसुदे ({OTHER_N}){otherOn > 0 ? ` — ${otherOn} निवडले` : ''} {open ? '▲' : '▼'}
      </button>
      {open && OTHER_GROUPS.map(g => (
        <div key={g.label} role="group" aria-label={g.label} className="min-w-0 space-y-1">
          <div className="text-sm font-semibold text-slate-600 dark:text-slate-300">{g.label}</div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{g.keys.map(k => chip(k, !small))}</div>
        </div>
      ))}
    </div>
  );
}

/** Compact form (bulk upload rows, C33; props unchanged for other callers): one line "मसुदे: …" with a "बदला" button that
 *  opens the same chips as the full picker (common four + fold). */
export function CompactDraftPicker({ value, onChange, disabled }: { value: DraftKey[]; onChange: (v: DraftKey[]) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <fieldset className="min-w-0 space-y-2" disabled={disabled}>
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1 text-sm">
        <span className="min-w-0"><span className="font-semibold">मसुदे:</span> <b className={value.length ? 'text-navy-700 dark:text-navy-100' : 'text-amber-800 dark:text-amber-200'}>{draftLabels(value)}</b></span>
        <button type="button" className="min-h-tap rounded-md px-2 font-semibold text-navy-700 underline dark:text-navy-200" aria-expanded={open} onClick={() => setOpen(o => !o)}>
          {open ? 'बंद ▲' : 'बदला ▼'}
        </button>
      </div>
      {open && <Chips value={value} onChange={onChange} small />}
    </fieldset>
  );
}

export default function DraftPicker({ value, onChange, suggestion, disabled }: {
  value: DraftKey[]; onChange: (v: DraftKey[]) => void; suggestion: Suggestion; disabled?: boolean;
}) {
  const isOwner = useAuth().me?.role === 'owner';
  const sec = useTypicalRunSeconds();
  const usd = useTypicalRunUsd();
  const est = sec && usd !== null ? draftEstimate(value, sec.sec, usd) : null;
  const differs = !sameDrafts(value, suggestion.keys);
  return (
    <fieldset className="min-w-0 space-y-2" disabled={disabled}>
      <legend className="label mb-0">कोणते मसुदे हवेत?</legend>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-navy-50 px-3 py-1.5 text-sm dark:bg-navy-800">
        <span className="min-w-0 text-slate-800 dark:text-slate-100">सुचवलेले: <b>{draftLabels(suggestion.keys)}</b> — {suggestionWhy(suggestion)}.</span>
        {differs && !disabled && (
          <button type="button" className="min-h-tap rounded-md px-2 font-semibold text-navy-700 underline dark:text-navy-200" onClick={() => onChange(suggestion.keys)}>
            सुचवलेले घ्या
          </button>
        )}
      </div>
      <Chips value={value} onChange={onChange} />
      {value.length === 0 && <div className="rounded-lg bg-amber-100 px-3 py-1.5 text-sm font-semibold text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">फक्त टिप्पणी तयार होईल</div>}
      <p className="text-sm text-slate-500 dark:text-slate-400">टिप्पणी, अभ्यास-फाइल व GR सह प्रस्ताव (PDF) नेहमी मिळतील.</p>
      {est && (
        <div className="text-sm text-slate-500 dark:text-slate-400"
          title={`मागील प्रक्रियांवरून; प्रत्येक जादा मसुदा +${EXTRA_DRAFT_MIN} मि.${isOwner ? `, +$${EXTRA_DRAFT_USD.toFixed(2)}` : ''} (अंदाज)`}>
          अंदाजे वेळ ~{est.min} मि.{isOwner && <> · खर्च ~${est.usd.toFixed(2)}</>}
        </div>
      )}
    </fieldset>
  );
}
