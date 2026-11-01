import { useState, type FormEvent } from 'react';
import { api, humanError } from '../lib/api';
import { Empty, SkeletonRows, Spinner } from '../components/ui';

interface Hit { path: string; frags: string[] }

export default function RegisterSearch() {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function go(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setErr('');
    try {
      setHits(await api<Hit[]>(`/api/search?q=${encodeURIComponent(q.trim())}`));
    } catch (x) {
      setErr(humanError(x));
      setHits(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">नोंदवही शोध</h1>
      <form onSubmit={go} className="card flex gap-2 p-3">
        <input className="input" type="search" autoFocus placeholder="नियम, GR, शब्द… (register/ मधील पडताळलेले उतारे)" value={q} onChange={e => setQ(e.target.value)} aria-label="शोधा" />
        <button className="btn-primary shrink-0" disabled={busy}>{busy ? <Spinner /> : '🔎'} शोधा</button>
      </form>
      {err && <div className="card p-3 text-red-800 dark:text-red-300" role="alert">{err}</div>}
      {busy ? <div className="card"><SkeletonRows n={4} /></div> : hits === null ? (
        <div className="card"><Empty icon="🔎" title="शोध सुरू करा" hint="निकालात स्रोत-फाइल व संबंधित उतारा (पृष्ठ/परिच्छेदासह) दिसेल." /></div>
      ) : hits.length === 0 ? (
        <div className="card"><Empty icon="∅" title="काहीही सापडले नाही" hint="दुसरा शब्द वापरा." /></div>
      ) : (
        <ul className="space-y-3">
          {hits.map((h, i) => (
            <li key={i} className="card p-4">
              <div className="font-mono text-sm font-semibold text-navy-700 dark:text-navy-200">{h.path}</div>
              {h.frags.map((f, j) => (
                <pre key={j} className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-slate-100 p-3 font-sans text-base dark:bg-navy-950">{f}</pre>
              ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
