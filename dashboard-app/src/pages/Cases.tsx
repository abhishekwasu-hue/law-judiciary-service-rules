import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useData, overdueIds } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import { CATEGORIES, STAGES, stageTone } from '../lib/constants';
import { crLabel, fmtDate } from '../lib/format';
import { humanError } from '../lib/api';
import type { Case } from '../lib/types';
import { Chip, Empty, SkeletonRows } from '../components/ui';
import { useToast } from '../components/Toast';

const FILTER_KEYS = ['q', 'category', 'stage', 'office', 'year', 'overdue'] as const;

function exportCsv(rows: Case[], overdue: Set<number>) {
  const head = ['C R क्र.', 'वर्ष', 'नस्ती क्र.', 'विषय', 'प्रवर्ग', 'टप्पा', 'प्राधान्य', 'कर्मचारी', 'पद', 'कार्यालय', 'आवक दिनांक', 'मुदत', 'मुदत संपली', 'नोंद दिनांक'];
  const esc = (v: unknown) => {
    const s = v == null ? '' : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [head, ...rows.map(c => [c.cr_no, c.cr_year, c.file_no, c.subject, c.category, c.stage, c.priority, c.employee_name, c.post, c.office, fmtDate(c.inward_date), fmtDate(c.due_date), overdue.has(c.id) ? 'होय' : '', fmtDate(c.created_at)])];
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
  const canWrite = useCanWrite();
  const toast = useToast();
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const view = sp.get('view') === 'kanban' ? 'kanban' : 'table';
  const searchRef = useRef<HTMLInputElement>(null);
  const overdue = useMemo(() => overdueIds(cases, letters), [cases, letters]);

  useEffect(() => {
    if (sp.get('focus')) {
      searchRef.current?.focus();
      sp.delete('focus');
      setSp(sp, { replace: true });
    }
  }, [sp, setSp]);

  const setParam = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v);
    else n.delete(k);
    setSp(n, { replace: true });
  };
  const offices = useMemo(() => [...new Set(cases.map(c => c.office).filter(Boolean) as string[])].sort(), [cases]);
  const years = useMemo(() => [...new Set(cases.map(c => c.cr_year))].sort((a, b) => b - a), [cases]);

  const rows = useMemo(() => {
    const q = (sp.get('q') || '').trim().toLowerCase();
    return cases.filter(c => {
      if (sp.get('category') && c.category !== sp.get('category')) return false;
      if (sp.get('stage') && c.stage !== sp.get('stage')) return false;
      if (sp.get('office') && c.office !== sp.get('office')) return false;
      if (sp.get('year') && String(c.cr_year) !== sp.get('year')) return false;
      if (sp.get('overdue') && !overdue.has(c.id)) return false;
      if (q && !`${c.cr_no}/${c.cr_year} ${c.subject} ${c.file_no || ''} ${c.employee_name || ''} ${c.post || ''} ${c.office || ''}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [cases, sp, overdue]);

  const active = FILTER_KEYS.filter(k => k !== 'q' && sp.get(k));

  async function move(id: number, stage: string) {
    try {
      await setStage(id, stage);
      toast(`टप्पा: ${stage}`);
    } catch (e) {
      toast(humanError(e), 'err');
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">प्रकरणे <span className="text-base font-normal text-slate-500">({rows.length})</span></h1>
        <div className="flex gap-2">
          <div className="inline-flex rounded-lg border border-slate-300 p-0.5 dark:border-navy-700" role="tablist">
            {(['table', 'kanban'] as const).map(v => (
              <button key={v} role="tab" aria-selected={view === v} className={`min-h-tap rounded-md px-3 font-semibold ${view === v ? 'bg-navy-700 text-white' : ''}`} onClick={() => setParam('view', v === 'table' ? '' : v)}>
                {v === 'table' ? 'तक्ता' : 'Kanban'}
              </button>
            ))}
          </div>
          <button className="btn-ghost" onClick={() => exportCsv(rows, overdue)} disabled={!rows.length}>⬇ Excel (CSV)</button>
        </div>
      </div>

      <div className="card grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-6">
        <input ref={searchRef} className="input lg:col-span-2" type="search" placeholder="शोधा: C R क्र., विषय, कर्मचारी…  ( / )" value={sp.get('q') || ''} onChange={e => setParam('q', e.target.value)} aria-label="शोधा" />
        <select className="input" value={sp.get('category') || ''} onChange={e => setParam('category', e.target.value)} aria-label="प्रवर्ग">
          <option value="">सर्व प्रवर्ग</option>
          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
        </select>
        <select className="input" value={sp.get('stage') || ''} onChange={e => setParam('stage', e.target.value)} aria-label="टप्पा">
          <option value="">सर्व टप्पे</option>
          {STAGES.map(c => <option key={c}>{c}</option>)}
        </select>
        <select className="input" value={sp.get('office') || ''} onChange={e => setParam('office', e.target.value)} aria-label="कार्यालय">
          <option value="">सर्व कार्यालये</option>
          {offices.map(c => <option key={c}>{c}</option>)}
        </select>
        <div className="flex gap-2">
          <select className="input" value={sp.get('year') || ''} onChange={e => setParam('year', e.target.value)} aria-label="वर्ष">
            <option value="">वर्ष</option>
            {years.map(y => <option key={y}>{y}</option>)}
          </select>
          <label className={`chip min-h-tap shrink-0 cursor-pointer px-3 ${sp.get('overdue') ? 'bg-red-700 text-white' : 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100'}`}>
            <input type="checkbox" className="sr-only" checked={!!sp.get('overdue')} onChange={e => setParam('overdue', e.target.checked ? '1' : '')} />
            मुदत संपली
          </label>
        </div>
        {active.length > 0 && (
          <button className="btn-ghost sm:col-span-2 lg:col-span-6" onClick={() => setSp(view === 'kanban' ? { view: 'kanban' } : {}, { replace: true })}>फिल्टर काढा ({active.length})</button>
        )}
      </div>

      {error && <div className="card border-red-300 p-3 text-red-800">{error}</div>}
      {loading ? (
        <div className="card"><SkeletonRows n={6} /></div>
      ) : cases.length === 0 ? (
        <div className="card"><Empty title="अजून प्रकरण नाही" hint="नवीन प्रस्ताव अपलोड करा (n)."><Link to="/new" className="btn-accent">नवीन प्रस्ताव</Link></Empty></div>
      ) : rows.length === 0 ? (
        <div className="card"><Empty icon="🔍" title="जुळणारे प्रकरण नाही" hint="फिल्टर बदला." /></div>
      ) : view === 'table' ? (
        <>
          <div className="card hidden overflow-x-auto md:block">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-navy-800">
                  <th className="th">C R</th><th className="th">विषय</th><th className="th">प्रवर्ग</th><th className="th">कार्यालय</th><th className="th">टप्पा</th><th className="th">मुदत</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(c => (
                  <tr key={c.id} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-navy-800/60 dark:hover:bg-navy-800/50" onClick={() => nav(`/cases/${c.id}`)}>
                    <td className="td whitespace-nowrap font-semibold"><Link to={`/cases/${c.id}`} onClick={e => e.stopPropagation()} className="underline-offset-2 hover:underline">{crLabel(c)}</Link>{c.priority === 'तातडीचे' && <span className="ml-1 text-saffron-600" title="तातडीचे">●</span>}</td>
                    <td className="td max-w-md"><div className="line-clamp-2">{c.subject}</div></td>
                    <td className="td whitespace-nowrap">{c.category}</td>
                    <td className="td">{c.office || '—'}</td>
                    <td className="td"><Chip tone={stageTone(c.stage)}>{c.stage}</Chip></td>
                    <td className="td whitespace-nowrap">{overdue.has(c.id) ? <Chip tone="red">मुदत संपली</Chip> : fmtDate(c.due_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="space-y-2 md:hidden">
            {rows.map(c => (
              <li key={c.id}>
                <Link to={`/cases/${c.id}`} className="card block p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold">{crLabel(c)}{c.priority === 'तातडीचे' && <span className="ml-1 text-saffron-600">●</span>}</span>
                    {overdue.has(c.id) ? <Chip tone="red">मुदत संपली</Chip> : <span className="text-sm text-slate-500">{c.category}</span>}
                  </div>
                  <div className="mt-1 line-clamp-2">{c.subject}</div>
                  <div className="mt-2"><Chip tone={stageTone(c.stage)}>{c.stage}</Chip></div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <Kanban rows={rows} overdue={overdue} canWrite={canWrite} onMove={move} />
      )}
    </div>
  );
}

function Kanban({ rows, overdue, canWrite, onMove }: { rows: Case[]; overdue: Set<number>; canWrite: boolean; onMove: (id: number, stage: string) => void }) {
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
                      {c.priority === 'तातडीचे' && <span className="text-sm font-semibold text-saffron-600">तातडीचे</span>}
                    </div>
                    <div className="mt-1 line-clamp-3 text-sm">{c.subject}</div>
                    <div className="mt-1 text-xs text-slate-500">{c.category}{c.office ? ` • ${c.office}` : ''}</div>
                  </Link>
                  {canWrite && (
                    <select className="input mt-2 text-sm" value={c.stage} onChange={e => onMove(c.id, e.target.value)} aria-label="टप्पा बदला">
                      {STAGES.map(x => <option key={x}>{x}</option>)}
                    </select>
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
