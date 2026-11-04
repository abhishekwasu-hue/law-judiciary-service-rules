import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, humanError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { findRow, nastiRows, readNasti } from '../lib/nasti';
import type { Case } from '../lib/types';
import NastiFacts from './NastiFacts';
import { Spinner } from './ui';
import { useToast } from './Toast';

const OUTDATED = 'server_outdated';

/** Case page: "नस्ती क्र. (eOffice)" — links the case to a row of the नस्ती अद्ययावत स्थिती page (this browser's data only)
 *  and shows that row's where / holder / days / status / due. Saved as cases.nasti_no (PATCH /api/cases/:id). */
export default function NastiLink({ c, canWrite, onSaved }: { c: Case; canWrite: boolean; onSaved: (c: Case) => void }) {
  const toast = useToast();
  const { me } = useAuth();
  const isOwner = me?.role === 'owner';
  // C16: no empty box on every case — a link opens the input; shown open once a number is saved
  const [open, setOpen] = useState(false);
  const store = useMemo(() => readNasti(), []);
  const rows = useMemo(() => nastiRows(store), [store]);
  const [v, setV] = useState(c.nasti_no || '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  useEffect(() => setV(c.nasti_no || ''), [c.nasti_no]);
  const saved = (c.nasti_no || '').trim();
  const row = saved ? findRow(saved, store) : null;
  const dirty = v.trim() !== saved;

  async function save(e: FormEvent) {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      const out = await api<Case>(`/api/cases/${c.id}`, { method: 'PATCH', body: { nasti_no: v.trim().slice(0, 100) } });
      // an old Worker / DB drops the field: the answer then does not carry the value just sent
      if (((out && out.nasti_no) || '') !== v.trim().slice(0, 100)) throw new Error(OUTDATED);
      onSaved(out);
      toast('नस्ती क्र. जतन केला');
    } catch (x) {
      // old Worker: nasti_no is not one of its case fields → "nothing to change"
      const outdated = x instanceof Error && (x.message === 'nothing to change' || x.message === OUTDATED);
      // technical cause (migration / Worker deploy) only for the owner
      setErr(outdated ? (isOwner ? 'सर्व्हर अद्ययावत नाही — नस्ती क्र. जतन झाला नाही (migration 0012 / Worker deploy बाकी)' : 'तांत्रिक अडचण — नस्ती क्र. जतन झाला नाही. कृपया मालकांना कळवावे.') : humanError(x));
    } finally {
      setBusy(false);
    }
  }

  if (!canWrite && !saved) return null;
  return (
    <div className="no-print space-y-2 border-t border-slate-200 pt-3 dark:border-navy-800">
      {canWrite && !saved && !open ? (
        <button type="button" className="inline-flex min-h-tap items-center font-semibold text-navy-700 underline-offset-2 hover:underline dark:text-navy-200" onClick={() => setOpen(true)}>
          + eOffice नस्ती क्र. जोडावा
        </button>
      ) : canWrite ? (
        <form onSubmit={save} className="flex flex-wrap items-end gap-2">
          <label className="min-w-0 flex-1 basis-56">
            <span className="label">नस्ती क्र. (eOffice)</span>
            <input className="input" autoFocus={open && !saved} list={rows.length ? `nasti-rows-${c.id}` : undefined} maxLength={100} value={v} onChange={e => setV(e.target.value)} placeholder={rows.length ? 'यादीतून निवडावा किंवा लिहावा' : ''} />
          </label>
          {rows.length > 0 && (
            <datalist id={`nasti-rows-${c.id}`}>
              {rows.map((r, i) => <option key={`${r.fileNo}-${i}`} value={String(r.fileNo)} label={`${r.fileNo} — ${r.subject || ''}`.slice(0, 120)} />)}
            </datalist>
          )}
          <button className="btn-primary min-h-tap" disabled={busy || !dirty}>{busy && <Spinner />} जतन करा</button>
          {!saved && <button type="button" className="btn-ghost" disabled={busy} onClick={() => { setOpen(false); setV(''); setErr(''); }}>रद्द</button>}
        </form>
      ) : saved ? (
        <div className="text-sm"><span className="text-slate-500 dark:text-slate-400">नस्ती क्र. (eOffice): </span><b>{saved}</b></div>
      ) : null}
      {err && <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm font-semibold text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100" role="alert">{err}</div>}
      {saved && store && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-navy-800 dark:bg-navy-800/50">
          {row ? <NastiFacts r={row} /> : <div className="text-sm font-semibold text-amber-700 dark:text-amber-300">नस्ती पानात सापडली नाही</div>}
          <Link to="/nasti" className="mt-1 inline-block text-sm font-semibold text-navy-600 hover:underline dark:text-navy-200">नस्ती अद्ययावत स्थिती उघडा →</Link>
        </div>
      )}
    </div>
  );
}
