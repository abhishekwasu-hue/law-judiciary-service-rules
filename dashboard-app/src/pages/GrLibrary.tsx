import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { ApiError, api, humanError } from '../lib/api';
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
  const [addErr, setAddErr] = useState('');

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
    setAddErr('');
    if (!/^\d{16,20}$/.test(code)) return setAddErr('सांकेतांक 16 ते 20 अंकी असावा (उदा. 202204191549468012). कृपया सांकेतांक तपासावा.');
    setAdding(true);
    try {
      const r = await api<{ code: string }>('/api/gr', { body: { code: code.trim() } });
      toast(`GR ${r.code} जोडला आहे.`);
      setCode('');
      await load();
    } catch (x) {
      // 404 = the code is not on the official site (Worker: "GR not found …")
      setAddErr(x instanceof ApiError && x.status === 404 ? 'हा सांकेतांक gr.maharashtra.gov.in वर मिळाला नाही. कृपया सांकेतांक तपासावा.' : humanError(x));
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
      <div>
        <h1 className="text-2xl font-bold">GR ग्रंथालय <span className="text-base font-normal text-slate-500">({list.length})</span></h1>
        <p className="mt-1 text-slate-600 dark:text-slate-300">प्रकरणांसाठी आणलेले शासन निर्णय (GR) येथे पाहता येतात. प्रत्येक GR कोणत्या प्रकरणात वापरला, तेही दिसते.</p>
      </div>
      <div className="card grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
        <div className="min-w-0 sm:col-span-2">
          <Field label="शोध">
            <input className="input" type="search" placeholder="सांकेतांक, शीर्षक, विभाग…" value={q} onChange={e => setQ(e.target.value)} />
          </Field>
        </div>
        <div className="min-w-0">
          <Field label="विभाग">
            <select className="input" value={dept} onChange={e => setDept(e.target.value)}>
              <option value="">सर्व विभाग</option>
              {depts.map(d => <option key={d}>{d}</option>)}
            </select>
          </Field>
        </div>
        <div className="min-w-0">
          <Field label="दिनांकापासून">
            <input className="input" type="date" value={from} onChange={e => setFrom(e.target.value)} />
          </Field>
        </div>
        <div className="min-w-0">
          <Field label="दिनांकापर्यंत">
            <input className="input" type="date" value={to} onChange={e => setTo(e.target.value)} />
          </Field>
        </div>
      </div>

      {canWrite && (
        <form onSubmit={add} className="card flex flex-col gap-2 p-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1">
            <Field label="GR जोडा — सांकेतांक" hint="सांकेतांक नमूद केल्यावर अधिकृत संकेतस्थळावरून (gr.maharashtra.gov.in) PDF आणली जाते.">
              <input className="input font-mono" inputMode="numeric" placeholder="उदा. 202204191549468012" value={code} aria-invalid={!!addErr} onChange={e => { setCode(e.target.value.replace(/\D/g, '')); setAddErr(''); }} />
              {addErr && <span className="mt-1 block font-semibold text-red-700 dark:text-red-400" role="alert">{addErr}</span>}
            </Field>
          </div>
          <button className="btn-primary sm:mb-6" disabled={adding}>{adding && <Spinner />} GR जोडा</button>
        </form>
      )}

      <div className="card">
        {!rows ? <SkeletonRows n={6} /> : rows.length === 0 ? (
          <Empty icon="📚" title="ग्रंथालयात अजून एकही GR नाही" hint={canWrite ? 'कृपया वरील चौकटीत सांकेतांक नमूद करून GR जोडावा.' : 'प्रकरणांची प्रक्रिया झाल्यावर लागू GR येथे दिसतील.'} />
        ) : list.length === 0 ? (
          <Empty icon="🔎" title="या शोधाशी जुळणारा GR नाही" hint="कृपया शोध-शब्द, विभाग किंवा दिनांक बदलावा.">
            <button type="button" className="btn-ghost mt-2" onClick={() => { setQ(''); setDept(''); setFrom(''); setTo(''); }}>शोध रिकामा करावा</button>
          </Empty>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-navy-800">
            {list.map(r => (
              <li key={r.code} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  {r.title ? <div className="font-semibold [overflow-wrap:anywhere]">{r.title}</div> : <div className="font-semibold text-slate-500 dark:text-slate-400">शीर्षक उपलब्ध नाही</div>}
                  <div className="text-sm text-slate-500">
                    <span className="break-all font-mono">{r.code}</span> • {fmtDate(r.date)}{r.department ? ` • ${r.department}` : ''}
                  </div>
                  {(r.used_in_cases || []).length > 0 && (
                    <div className="mt-1 flex flex-wrap items-center gap-1 text-sm">
                      वापर:
                      {(r.used_in_cases || []).map(id => {
                        const c = caseById.get(Number(id));
                        return <Link key={id} to={`/cases/${id}`} className="chip min-h-tap bg-navy-100 px-3 text-navy-900 dark:bg-navy-800 dark:text-navy-100">{c?.cr_no ? crLabel(c) : `प्रकरण क्र. ${id}`}</Link>;
                      })}
                    </div>
                  )}
                </div>
                <div className="flex shrink-0 flex-col items-start gap-1 sm:items-end">
                  <button className="btn-ghost" disabled={!r.storage_path || opening === r.code} onClick={() => void open(r)}>
                    {opening === r.code ? <Spinner /> : '📄'} उघडा
                  </button>
                  {!r.storage_path && <span className="text-sm text-slate-500 dark:text-slate-400">PDF अजून आणलेली नाही</span>}
                </div>
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
