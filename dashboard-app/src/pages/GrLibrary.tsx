import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { api, humanError } from '../lib/api';
import { useCanWrite } from '../lib/auth';
import { useData } from '../lib/data';
import { crLabel, fmtDate } from '../lib/format';
import type { GrRow } from '../lib/types';
import { Empty, Field, Modal, SkeletonRows, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import PdfViewer from '../components/PdfViewer';

export default function GrLibrary() {
  const canWrite = useCanWrite();
  const toast = useToast();
  const { cases } = useData();
  const [rows, setRows] = useState<GrRow[] | null>(null);
  const [q, setQ] = useState('');
  const [dept, setDept] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [code, setCode] = useState('');
  const [adding, setAdding] = useState(false);
  const [view, setView] = useState<{ code: string; url: string; title: string } | null>(null);
  const [opening, setOpening] = useState('');

  const load = () => sb().from('gr_library').select('*').order('date', { ascending: false, nullsFirst: false }).then(({ data, error }) => {
    if (error) toast(humanError(error.message), 'err');
    setRows((data as GrRow[]) || []);
  });
  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const depts = useMemo(() => [...new Set((rows || []).map(r => r.department).filter(Boolean) as string[])].sort(), [rows]);
  const caseById = useMemo(() => new Map(cases.map(c => [c.id, c])), [cases]);
  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return (rows || []).filter(r => {
      if (dept && r.department !== dept) return false;
      if (from && (!r.date || r.date < from)) return false;
      if (to && (!r.date || r.date > to)) return false;
      if (s && !`${r.code} ${r.title || ''} ${r.department || ''} ${fmtDate(r.date)}`.toLowerCase().includes(s)) return false;
      return true;
    });
  }, [rows, q, dept, from, to]);

  async function add(e: FormEvent) {
    e.preventDefault();
    if (!/^\d{16,20}$/.test(code)) return toast('सांकेतांक 16 ते 20 अंकी असावा (उदा. 202204191549468012)', 'err');
    setAdding(true);
    try {
      const r = await api<{ code: string }>('/api/gr', { body: { code: code.trim() } });
      toast(`GR ${r.code} जोडला`);
      setCode('');
      await load();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setAdding(false);
    }
  }
  async function open(r: GrRow) {
    setOpening(r.code);
    try {
      const { url } = await api<{ url: string }>(`/api/gr/${r.code}`);
      setView({ code: r.code, url, title: r.title || r.code });
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setOpening('');
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">GR ग्रंथालय <span className="text-base font-normal text-slate-500">({list.length})</span></h1>
      <div className="card grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-5">
        <input className="input lg:col-span-2" type="search" placeholder="सांकेतांक, शीर्षक, विभाग…" value={q} onChange={e => setQ(e.target.value)} aria-label="शोधा" />
        <select className="input" value={dept} onChange={e => setDept(e.target.value)} aria-label="विभाग">
          <option value="">सर्व विभाग</option>
          {depts.map(d => <option key={d}>{d}</option>)}
        </select>
        <input className="input" type="date" value={from} onChange={e => setFrom(e.target.value)} aria-label="दिनांकापासून" title="दिनांकापासून" />
        <input className="input" type="date" value={to} onChange={e => setTo(e.target.value)} aria-label="दिनांकापर्यंत" title="दिनांकापर्यंत" />
      </div>

      {canWrite && (
        <form onSubmit={add} className="card flex flex-col gap-2 p-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Field label="GR जोडा — सांकेतांक" hint="सांकेतांक टाकल्यावर अधिकृत संकेतस्थळावरून (gr.maharashtra.gov.in) PDF आणली जाते.">
              <input className="input font-mono" inputMode="numeric" placeholder="उदा. 202204191549468012" value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} />
            </Field>
          </div>
          <button className="btn-primary sm:mb-6" disabled={adding}>{adding && <Spinner />} GR जोडा</button>
        </form>
      )}

      <div className="card">
        {!rows ? <SkeletonRows n={6} /> : list.length === 0 ? <Empty icon="📚" title="GR सापडला नाही" hint="शोध बदला किंवा सांकेतांकाने GR जोडा." /> : (
          <ul className="divide-y divide-slate-100 dark:divide-navy-800">
            {list.map(r => (
              <li key={r.code} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="font-semibold">{r.title || '—'}</div>
                  <div className="text-sm text-slate-500">
                    <span className="font-mono">{r.code}</span> • {fmtDate(r.date)}{r.department ? ` • ${r.department}` : ''}
                  </div>
                  {(r.used_in_cases || []).length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1 text-sm">
                      वापर:
                      {(r.used_in_cases || []).map(id => {
                        const c = caseById.get(Number(id));
                        return <Link key={id} to={`/cases/${id}`} className="chip bg-navy-100 text-navy-900 dark:bg-navy-800 dark:text-navy-100">{c ? crLabel(c) : `#${id}`}</Link>;
                      })}
                    </div>
                  )}
                </div>
                <button className="btn-ghost shrink-0" disabled={!r.storage_path || opening === r.code} onClick={() => void open(r)} title={r.storage_path ? '' : 'या GR ची PDF अजून आणलेली नाही'}>
                  {opening === r.code ? <Spinner /> : '📄'} उघडा
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Modal open={!!view} onClose={() => setView(null)} title={view?.title || ''} wide>
        {view && (
          <div className="space-y-2">
            <a className="btn-ghost" href={view.url} target="_blank" rel="noopener noreferrer">नवीन टॅबमध्ये उघडा</a>
            <PdfViewer url={view.url} />
          </div>
        )}
      </Modal>
    </div>
  );
}
