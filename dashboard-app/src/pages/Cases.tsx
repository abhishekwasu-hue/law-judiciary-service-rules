import { memo, useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useData, useLatestRuns, overdueIds } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import { CATEGORIES, STAGES, WORK_TYPES, stageTone, workTypeLabel, workTypeOf } from '../lib/constants';
import WorkTypeChips from '../components/WorkTypeChips';
import { crLabel, fmtDate } from '../lib/format';
import { RunStateBadge } from '../components/RunProgress';
import { humanError } from '../lib/api';
import type { Case, Run } from '../lib/types';
import { Chip, Empty, SkeletonRows } from '../components/ui';
import { useToast } from '../components/Toast';
import { PAGE_STEP, pageRows } from '../lib/perf';

// short stage words for the table chips (UI audit S20: long chips wrapped into round blobs); the full stage is the tooltip
const STAGE_SHORT: Record<string, string> = { 'पत्र पाठवले (माहिती प्रतीक्षेत)': 'माहिती प्रतीक्षेत', 'वित्त/सा.प्र.वि. कडे': 'वित्त/सा.प्र.वि.' };
function StageChip({ stage }: { stage: string }) {
  return <span className="whitespace-nowrap"><Chip tone={stageTone(stage)} title={stage}>{STAGE_SHORT[stage] || stage}</Chip></span>;
}
const Urgent = () => <span className="chip ml-1.5 bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">तातडीचे</span>;

const workShort = (c: Case) => WORK_TYPES.find(w => w.id === workTypeOf(c))?.short;
const subjectOf = (c: Case, run: Run | undefined) => c.subject || <span className="text-slate-500 dark:text-slate-400">{run?.summary || 'विषय PDF वरून येईल'}</span>;

/** P5/P6: one list row; memo → a Realtime update of one case / run re-renders that row only. */
const TableRow = memo(function TableRow({ c, run, late, open }: { c: Case; run: Run | undefined; late: boolean; open: (id: number) => void }) {
  return (
    <tr className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-navy-800/60 dark:hover:bg-navy-800/50" onClick={() => open(c.id)}>
      <td className="td whitespace-nowrap font-semibold"><Link to={`/cases/${c.id}`} onClick={e => e.stopPropagation()} className="inline-flex min-h-tap items-center underline-offset-2 hover:underline">{crLabel(c)}</Link>{c.priority === 'तातडीचे' && <div><Urgent /></div>}</td>
      <td className="td whitespace-nowrap"><RunStateBadge run={run} /></td>
      <td className="td min-w-[18rem]"><div className="line-clamp-2">{subjectOf(c, run)}</div></td>
      <td className="td whitespace-nowrap">{c.category}<div className="text-xs text-slate-500 dark:text-slate-400">{workShort(c)}</div></td>
      <td className="td max-w-[14rem]"><div className="line-clamp-2 text-sm" title={c.office || undefined}>{c.office || '—'}</div></td>
      <td className="td"><StageChip stage={c.stage} /></td>
      <td className="td whitespace-nowrap">{late ? <Chip tone="red">मुदत संपली</Chip> : fmtDate(c.due_date)}</td>
    </tr>
  );
});
const CardRow = memo(function CardRow({ c, run, late }: { c: Case; run: Run | undefined; late: boolean }) {
  return (
    <li>
      <Link to={`/cases/${c.id}`} className="card block p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="font-bold">{crLabel(c)}{c.priority === 'तातडीचे' && <Urgent />}</span>
          {late ? <Chip tone="red">मुदत संपली</Chip> : <span className="truncate text-sm text-slate-500 dark:text-slate-400">{workShort(c)} • {c.category}</span>}
        </div>
        <div className="mt-1 line-clamp-2">{subjectOf(c, run)}</div>
        <dl className="mt-2 grid grid-cols-[auto_1fr] items-center gap-x-2 gap-y-1 text-sm">
          <dt className="text-slate-500 dark:text-slate-400">नस्तीचा टप्पा</dt><dd><StageChip stage={c.stage} /></dd>
          {run && <><dt className="text-slate-500 dark:text-slate-400">मसुदे</dt><dd><RunStateBadge run={run} /></dd></>}
        </dl>
      </Link>
    </li>
  );
});

/** md and up: the table; phone: the cards. Only one of the two is rendered (both were in the page, one hidden by CSS). */
function useWide(): boolean {
  const q = '(min-width: 768px)';
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const on = () => setWide(m.matches);
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  return wide;
}

/** Stage changed from the टप्पेनिहाय board: shown 8 s with "पूर्ववत" (UI audit S18: the change was immediate, no undo). */
interface Undo { id: number; label: string; from: string; to: string }

const FILTER_KEYS = ['q', 'work', 'category', 'stage', 'office', 'year', 'overdue'] as const;

function exportCsv(rows: Case[], overdue: Set<number>) {
  const head = ['C R क्र.', 'वर्ष', 'नस्ती क्र.', 'विषय', 'कामाचा प्रकार', 'प्रवर्ग', 'टप्पा', 'प्राधान्य', 'कर्मचारी', 'पद', 'कार्यालय', 'आवक दिनांक', 'मुदत', 'मुदत संपली', 'नोंद दिनांक'];
  const esc = (v: unknown) => {
    const s = v == null ? '' : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [head, ...rows.map(c => [c.cr_no, c.cr_year, c.file_no, c.subject, workTypeLabel(c.work_type), c.category, c.stage, c.priority, c.employee_name, c.post, c.office, fmtDate(c.inward_date), fmtDate(c.due_date), overdue.has(c.id) ? 'होय' : '', fmtDate(c.created_at)])];
  // UTF-8 BOM so Excel opens Devanagari correctly.
  const blob = new Blob(['﻿' + lines.map(r => r.map(esc).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `prakarane-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

export default function Cases() {
  const { cases, letters, loading, error, setStage } = useData();
  const latestRuns = useLatestRuns();
  const canWrite = useCanWrite();
  const toast = useToast();
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const view = sp.get('view') === 'kanban' ? 'kanban' : 'table';
  const searchRef = useRef<HTMLInputElement>(null);
  const overdue = useMemo(() => overdueIds(cases, letters), [cases, letters]);
  const [filtersOpen, setFiltersOpen] = useState(false); // phone only: the selects fold behind "फिल्टर (n)" (UI audit S4)
  const [undo, setUndo] = useState<Undo | null>(null);
  const undoTimer = useRef<number>();
  const wide = useWide();
  const open = useCallback((id: number) => nav(`/cases/${id}`), [nav]);
  // P5: the list shows PAGE_STEP rows, "अधिक दाखवा (N)" adds the next; search / filters still run over every case
  const [shown, setShown] = useState(PAGE_STEP);

  useEffect(() => {
    if (sp.get('focus')) {
      searchRef.current?.focus();
      sp.delete('focus');
      setSp(sp, { replace: true });
    }
  }, [sp, setSp]);
  useEffect(() => () => window.clearTimeout(undoTimer.current), []);

  const setParam = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v);
    else n.delete(k);
    setSp(n, { replace: true });
  };
  const offices = useMemo(() => [...new Set(cases.map(c => c.office).filter(Boolean) as string[])].sort(), [cases]);
  const years = useMemo(() => [...new Set(cases.map(c => c.cr_year).filter((y): y is number => y != null))].sort((a, b) => b - a), [cases]);

  const rows = useMemo(() => {
    const q = (sp.get('q') || '').trim().toLowerCase();
    return cases.filter(c => {
      if (sp.get('work') && workTypeOf(c) !== sp.get('work')) return false;
      if (sp.get('category') && c.category !== sp.get('category')) return false;
      if (sp.get('stage') && c.stage !== sp.get('stage')) return false;
      if (sp.get('office') && c.office !== sp.get('office')) return false;
      if (sp.get('year') && String(c.cr_year) !== sp.get('year')) return false;
      if (sp.get('overdue') && !overdue.has(c.id)) return false;
      if (q && !`${c.cr_no ?? ''}/${c.cr_year ?? ''} ${c.subject ?? ''} ${c.file_no || ''} ${c.employee_name || ''} ${c.post || ''} ${c.office || ''}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [cases, sp, overdue]);
  const filterKey = FILTER_KEYS.map(k => sp.get(k) || '').join('|');
  useEffect(() => setShown(PAGE_STEP), [filterKey]);
  const page = useMemo(() => pageRows(rows, shown), [rows, shown]);
  const moreBtn = page.more > 0 && (
    <button type="button" className="btn-ghost w-full" onClick={() => setShown(n => n + PAGE_STEP)}>
      अधिक दाखवा ({page.more})
    </button>
  );

  // every filter incl. the search text (UI audit S19: a text-only search had no one-tap way back)
  const active = FILTER_KEYS.filter(k => sp.get(k));
  const panelActive = (['category', 'stage', 'office', 'year', 'overdue'] as const).filter(k => sp.get(k)).length;
  const clearAll = () => setSp(view === 'kanban' ? { view: 'kanban' } : {}, { replace: true });

  const move = useCallback(async (id: number, stage: string, isUndo = false) => {
    const c = cases.find(x => x.id === id);
    const from = c?.stage || '';
    try {
      await setStage(id, stage);
      window.clearTimeout(undoTimer.current);
      if (isUndo || !c) {
        setUndo(null);
        toast(`टप्पा पूर्ववत: ${stage}`, 'info');
      } else {
        setUndo({ id, label: crLabel(c), from, to: stage });
        undoTimer.current = window.setTimeout(() => setUndo(null), 8000);
      }
    } catch (e) {
      toast(humanError(e), 'err');
    }
  }, [cases, setStage, toast]);

  const overdueOn = !!sp.get('overdue');
  const csvBtn = (cls: string) => (
    <button className={`btn-ghost ${cls}`} onClick={() => exportCsv(rows, overdue)} disabled={!rows.length}>⬇ Excel (CSV)</button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">प्रकरणे <span className="text-base font-normal text-slate-500 dark:text-slate-400">({loading ? '—' : rows.length})</span></h1>
        <div className="flex gap-2">
          <div className="inline-flex rounded-lg border border-slate-300 p-0.5 dark:border-navy-700" role="group" aria-label="दृश्य">
            {(['table', 'kanban'] as const).map(v => (
              <button key={v} type="button" aria-pressed={view === v} className={`min-h-tap rounded-md px-3 font-semibold ${view === v ? 'bg-navy-700 text-white dark:bg-navy-500' : ''}`} onClick={() => setParam('view', v === 'table' ? '' : v)}>
                {v === 'table' ? 'तक्ता' : 'टप्पेनिहाय'}
              </button>
            ))}
          </div>
          {csvBtn('hidden md:inline-flex')}
        </div>
      </div>

      <WorkTypeChips cases={cases} value={sp.get('work') || ''} onChange={v => setParam('work', v)} />

      <div className="card space-y-2 p-3">
        <div className="flex gap-2">
          <input ref={searchRef} className="input" type="search" placeholder="C R क्र., विषय, कार्यालय" value={sp.get('q') || ''} onChange={e => setParam('q', e.target.value)} aria-label="प्रकरण शोध" />
          <button type="button" className="btn-ghost shrink-0 px-3 md:hidden" aria-expanded={filtersOpen} aria-controls="case-filters" onClick={() => setFiltersOpen(o => !o)}>
            फिल्टर{panelActive ? ` (${panelActive})` : ''} <span aria-hidden="true">{filtersOpen ? '▲' : '▼'}</span>
          </button>
        </div>
        <div id="case-filters" className={`${filtersOpen ? 'grid' : 'hidden'} gap-2 sm:grid-cols-2 md:grid md:grid-cols-3 lg:grid-cols-5`}>
          <select className="input" value={sp.get('category') || ''} onChange={e => setParam('category', e.target.value)} aria-label="प्रवर्ग">
            <option value="">सर्व प्रवर्ग</option>
            {CATEGORIES.map(c => <option key={c}>{c}</option>)}
          </select>
          <select className="input" value={sp.get('stage') || ''} onChange={e => setParam('stage', e.target.value)} aria-label="नस्तीचा टप्पा">
            <option value="">सर्व टप्पे</option>
            {STAGES.map(c => <option key={c}>{c}</option>)}
          </select>
          <select className="input" value={sp.get('office') || ''} onChange={e => setParam('office', e.target.value)} aria-label="कार्यालय">
            <option value="">सर्व कार्यालये</option>
            {offices.map(c => <option key={c}>{c}</option>)}
          </select>
          <select className="input" value={sp.get('year') || ''} onChange={e => setParam('year', e.target.value)} aria-label="वर्ष">
            <option value="">सर्व वर्षे</option>
            {years.map(y => <option key={y}>{y}</option>)}
          </select>
          {/* a toggle button, not a status-like chip (UI audit S19) */}
          <button type="button" aria-pressed={overdueOn} onClick={() => setParam('overdue', overdueOn ? '' : '1')}
            className={`btn min-h-tap justify-start border-2 text-base ${overdueOn ? 'border-red-700 bg-red-700 text-white hover:bg-red-800' : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-100 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-100 dark:hover:bg-navy-800'}`}>
            <span aria-hidden="true">{overdueOn ? '☑' : '☐'}</span> फक्त मुदत संपलेली
          </button>
          {csvBtn('md:hidden')}
        </div>
        {active.length > 0 && (
          <button className="btn-ghost w-full" onClick={clearAll}>फिल्टर काढा ({active.length})</button>
        )}
      </div>

      {error && <div className="card border-red-300 p-3 text-red-800 dark:border-red-800 dark:text-red-200" role="alert">{humanError(error)}</div>}
      {loading ? (
        <div className="card"><SkeletonRows n={6} /></div>
      ) : cases.length === 0 ? (
        <div className="card"><Empty title="अजून प्रकरण नाही" hint="पहिला प्रस्ताव अपलोड करण्यासाठी कृपया खालील बटण वापरावे."><Link to="/new" className="btn-accent">+ नवीन प्रस्ताव</Link></Empty></div>
      ) : rows.length === 0 ? (
        <div className="card"><Empty icon="🔍" title="जुळणारे प्रकरण नाही" hint="कृपया शोध किंवा फिल्टर बदलावा."><button className="btn-primary" onClick={clearAll}>सर्व फिल्टर काढा</button></Empty></div>
      ) : view === 'table' ? (
        <>
          {wide ? (
            <div className="card overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-navy-800">
                    <th className="th">C R</th><th className="th">मसुदे</th><th className="th">विषय</th><th className="th">प्रवर्ग</th><th className="th">कार्यालय</th><th className="th">नस्तीचा टप्पा</th><th className="th">मुदत</th>
                  </tr>
                </thead>
                <tbody>
                  {page.visible.map(c => <TableRow key={c.id} c={c} run={latestRuns.get(c.id)} late={overdue.has(c.id)} open={open} />)}
                </tbody>
              </table>
            </div>
          ) : (
            <ul className="space-y-2">
              {page.visible.map(c => <CardRow key={c.id} c={c} run={latestRuns.get(c.id)} late={overdue.has(c.id)} />)}
            </ul>
          )}
          {moreBtn}
        </>
      ) : (
        <Kanban rows={rows} overdue={overdue} canWrite={canWrite} onMove={(id, st) => void move(id, st)} runs={latestRuns} />
      )}

      {undo && (
        <div className="no-print fixed inset-x-0 bottom-[calc(8.5rem+env(safe-area-inset-bottom))] z-[61] flex justify-center px-4 md:bottom-[6.5rem]" role="status">
          <div className="flex max-w-md flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-navy-800 px-4 py-2.5 text-white shadow-lg">
            <span className="min-w-0 font-semibold">{undo.label}: टप्पा “{undo.to}”</span>
            <button type="button" className="min-h-tap rounded-md bg-white/15 px-3 font-bold hover:bg-white/25" onClick={() => void move(undo.id, undo.from, true)}>↶ पूर्ववत</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Kanban({ rows, overdue, canWrite, onMove, runs }: { rows: Case[]; overdue: Set<number>; canWrite: boolean; onMove: (id: number, stage: string) => void; runs: Map<number, Run> }) {
  const [over, setOver] = useState<string | null>(null);
  const drop = (stage: string) => (e: DragEvent) => {
    e.preventDefault();
    setOver(null);
    const id = Number(e.dataTransfer.getData('text/plain'));
    const c = rows.find(r => r.id === id);
    if (c && c.stage !== stage) onMove(id, stage);
  };
  return (
    <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-3">
      {STAGES.map(s => {
        const col = rows.filter(r => r.stage === s);
        return (
          <section
            key={s}
            aria-label={s}
            onDragOver={e => { if (canWrite) { e.preventDefault(); setOver(s); } }}
            onDragLeave={() => setOver(o => (o === s ? null : o))}
            onDrop={drop(s)}
            className={`flex w-[78vw] max-w-[300px] shrink-0 snap-start flex-col rounded-xl border p-2 sm:w-72 ${over === s ? 'border-saffron-500 bg-saffron-500/10' : 'border-slate-200 bg-slate-100/60 dark:border-navy-800 dark:bg-navy-900/60'}`}
          >
            <header className="mb-2 flex items-center justify-between gap-2 px-1">
              <Chip tone={stageTone(s)}>{s}</Chip>
              <span className="text-sm font-semibold text-slate-500">{col.length}</span>
            </header>
            <div className="flex min-h-[80px] flex-col gap-2">
              {col.map(c => (
                <article
                  key={c.id}
                  draggable={canWrite}
                  onDragStart={e => { e.dataTransfer.setData('text/plain', String(c.id)); e.dataTransfer.effectAllowed = 'move'; }}
                  className={`card p-3 ${canWrite ? 'cursor-grab active:cursor-grabbing' : ''} ${overdue.has(c.id) ? 'border-l-4 border-l-red-600' : ''}`}
                >
                  <Link to={`/cases/${c.id}`} className="block">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-bold">{crLabel(c)}</span>
                      {c.priority === 'तातडीचे' && <Urgent />}
                    </div>
                    <div className="mt-1 line-clamp-3 text-sm">{c.subject || <span className="text-slate-500">{runs.get(c.id)?.summary || 'विषय PDF वरून येईल'}</span>}</div>
                    <div className="mt-1 text-xs text-slate-500">{c.category}{c.office ? ` • ${c.office}` : ''}</div>
                    {runs.get(c.id) && <div className="mt-2"><RunStateBadge run={runs.get(c.id)} /></div>}
                  </Link>
                  {canWrite && (
                    <label className="mt-2 block">
                      <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">टप्पा बदला</span>
                      <select className="input mt-0.5 text-sm" value={c.stage} onChange={e => onMove(c.id, e.target.value)} aria-label="टप्पा बदला">
                        {STAGES.map(x => <option key={x}>{x}</option>)}
                      </select>
                    </label>
                  )}
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
