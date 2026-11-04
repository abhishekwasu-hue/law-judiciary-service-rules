// प्रकरण निवड (Abhi 04.11.2026: "चॅट बॉक्समध्ये प्रस्ताव निवडण्याची व्यवस्था पाहिजे … प्रकरण क्रमांक निवडण्याची व्यवस्था"): the
// सुधारणा chat always works on ONE case the user picked here; the model never chooses or guesses the case.
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../lib/data';
import { crLabel } from '../lib/format';
import { Modal } from './ui';

/** Link to a case's सुधारणा chat (टिप्पणी व पत्र tab; the chat scrolls into view). */
export const editHref = (id: number) => `/cases/${id}?tab=note&edit=1`;

export default function CasePicker({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { cases } = useData();
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const list = useMemo(() => {
    const t = q.trim().toLowerCase();
    return cases.filter(c => !t || `${crLabel(c)} ${c.cr_no ?? ''} ${c.subject ?? ''} ${c.file_no ?? ''}`.toLowerCase().includes(t)).slice(0, 50);
  }, [cases, q]);
  return (
    <Modal open={open} onClose={onClose} title="✏️ मसुद्यात सुधारणा — कृपया प्रकरण निवडावे">
      <input className="input mb-3" autoFocus placeholder="C R क्र., विषय किंवा नस्ती क्र." value={q} onChange={e => setQ(e.target.value)} aria-label="प्रकरण शोधा" />
      {list.length === 0 ? <p className="text-sm text-slate-500">या शोधानुसार प्रकरण आढळले नाही.</p> : (
        <ul className="max-h-[60vh] space-y-1 overflow-y-auto">
          {list.map(c => (
            <li key={c.id}>
              <button type="button" className="w-full rounded-lg px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-navy-800"
                onClick={() => { onClose(); setQ(''); nav(editHref(c.id)); }}>
                <div className="font-bold">{crLabel(c)}</div>
                {c.subject && <div className="line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{c.subject}</div>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
