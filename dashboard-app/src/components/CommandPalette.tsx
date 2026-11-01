import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../lib/data';
import { useAuth } from '../lib/auth';
import { crLabel } from '../lib/format';

interface Cmd { id: string; label: string; hint?: string; go: string }

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const nav = useNavigate();
  const { cases } = useData();
  const { me } = useAuth();
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQ('');
      setSel(0);
      setTimeout(() => input.current?.focus(), 0);
    }
  }, [open]);

  const list = useMemo<Cmd[]>(() => {
    const base: Cmd[] = [
      { id: 'home', label: 'मुख्य पृष्ठ', go: '/' },
      { id: 'new', label: 'नवीन प्रस्ताव', hint: 'n', go: '/new' },
      { id: 'cases', label: 'प्रकरणे — तक्ता', hint: '/', go: '/cases' },
      { id: 'kanban', label: 'प्रकरणे — Kanban', go: '/cases?view=kanban' },
      { id: 'overdue', label: 'मुदत संपलेली प्रकरणे', go: '/cases?overdue=1' },
      { id: 'gr', label: 'GR ग्रंथालय', go: '/gr' },
      { id: 'search', label: 'नोंदवही शोध', go: '/search' },
      ...(me?.role === 'owner' ? [{ id: 'settings', label: 'सेटिंग्ज', go: '/settings' }] : []),
    ];
    const s = q.trim().toLowerCase();
    const cs: Cmd[] = cases
      .filter(c => !s || `${c.cr_no}/${c.cr_year} ${c.subject} ${c.file_no || ''} ${c.office || ''} ${c.employee_name || ''}`.toLowerCase().includes(s))
      .slice(0, 8)
      .map(c => ({ id: `c${c.id}`, label: `${crLabel(c)} — ${c.subject}`, hint: c.stage, go: `/cases/${c.id}` }));
    const bs = base.filter(b => !s || b.label.toLowerCase().includes(s));
    return [...bs, ...(s ? cs : [])];
  }, [q, cases, me?.role]);

  if (!open) return null;
  const run = (c?: Cmd) => {
    if (!c) return;
    onClose();
    nav(c.go);
  };
  return (
    <div className="fixed inset-0 z-[55] flex items-start justify-center bg-black/50 p-3 pt-[10vh]" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="card w-full max-w-xl overflow-hidden" role="dialog" aria-modal="true" aria-label="आदेश शोधा">
        <input
          ref={input}
          className="w-full border-b border-slate-200 bg-transparent px-4 py-4 text-lg outline-none dark:border-navy-800"
          placeholder="आदेश किंवा प्रकरण (C R क्र., विषय) शोधा…"
          value={q}
          onChange={e => {
            setQ(e.target.value);
            setSel(0);
          }}
          onKeyDown={e => {
            if (e.key === 'Escape') onClose();
            else if (e.key === 'ArrowDown') { e.preventDefault(); setSel(x => Math.min(x + 1, list.length - 1)); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(x => Math.max(x - 1, 0)); }
            else if (e.key === 'Enter') run(list[sel]);
          }}
        />
        <ul className="max-h-[50vh] overflow-auto py-1" role="listbox">
          {list.length === 0 && <li className="px-4 py-3 text-slate-500">काहीही सापडले नाही</li>}
          {list.map((c, i) => (
            <li key={c.id} role="option" aria-selected={i === sel}>
              <button
                className={`flex min-h-tap w-full items-center justify-between gap-3 px-4 py-2 text-left ${i === sel ? 'bg-navy-100 dark:bg-navy-800' : ''}`}
                onMouseEnter={() => setSel(i)}
                onClick={() => run(c)}
              >
                <span className="truncate">{c.label}</span>
                {c.hint && <span className="shrink-0 text-sm text-slate-500">{c.hint}</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
