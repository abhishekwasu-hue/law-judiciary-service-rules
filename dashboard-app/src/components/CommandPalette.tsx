import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../lib/data';
import { useAuth } from '../lib/auth';
import { crLabel } from '../lib/format';

/** 'cases' = opened from the "प्रकरण शोध" button: with an empty query the latest cases come first, then the pages.
 *  'all' = Ctrl K: pages first. */
export type PaletteMode = 'cases' | 'all';

interface Cmd { id: string; label: string; sub?: string | null; hint?: string; key?: string; go: string | (() => void) }

export default function CommandPalette({ open, onClose, mode = 'all', onEdit, onProfile }: {
  open: boolean; onClose: () => void; mode?: PaletteMode; onEdit?: () => void; onProfile?: () => void;
}) {
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
      { id: 'new', label: 'नवीन प्रस्ताव', key: 'n', go: '/new' },
      { id: 'cases', label: 'प्रकरणे — तक्ता', key: '/', go: '/cases' },
      { id: 'kanban', label: 'प्रकरणे — टप्पेनिहाय', go: '/cases?view=kanban' },
      { id: 'overdue', label: 'मुदत संपलेली प्रकरणे', go: '/cases?overdue=1' },
      { id: 'nasti', label: 'नस्ती अद्ययावत स्थिती', go: '/nasti' },
      { id: 'gr', label: 'GR ग्रंथालय', go: '/gr' },
      { id: 'search', label: 'नियम-उतारे शोध', go: '/search' },
      ...(onEdit ? [{ id: 'edit', label: 'मसुद्यात सुधारणा (प्रकरण निवडून)', go: onEdit }] : []),
      ...(onProfile ? [{ id: 'profile', label: 'माझी माहिती', go: onProfile }] : []),
      ...(me?.role === 'owner' ? [{ id: 'settings', label: 'सेटिंग्ज', go: '/settings' }] : []),
    ];
    const s = q.trim().toLowerCase();
    const toCmd = (c: (typeof cases)[number]): Cmd => ({ id: `c${c.id}`, label: crLabel(c), sub: c.subject, hint: c.stage, go: `/cases/${c.id}` });
    const cs: Cmd[] = cases
      .filter(c => !s || `${c.cr_no ?? ''}/${c.cr_year ?? ''} ${c.subject ?? ''} ${c.file_no || ''} ${c.office || ''} ${c.employee_name || ''}`.toLowerCase().includes(s))
      .slice(0, 8)
      .map(toCmd);
    const bs = base.filter(b => !s || b.label.toLowerCase().includes(s));
    if (!s && mode === 'cases') {
      const recent = [...cases].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)).slice(0, 5).map(toCmd);
      return [...recent, ...bs];
    }
    return s ? [...cs, ...bs] : bs;
  }, [q, cases, me?.role, mode, onEdit, onProfile]);

  if (!open) return null;
  const run = (c?: Cmd) => {
    if (!c) return;
    onClose();
    if (typeof c.go === 'string') nav(c.go);
    else c.go();
  };
  return (
    <div className="fixed inset-0 z-[55] flex items-start justify-center bg-black/50 p-3 pt-[8vh]" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="card w-full max-w-xl overflow-hidden" role="dialog" aria-modal="true" aria-label="प्रकरण शोध">
        <input
          ref={input}
          role="combobox"
          type="search"
          aria-expanded={list.length > 0}
          aria-controls="cmdk-list"
          aria-autocomplete="list"
          aria-activedescendant={list[sel] ? `cmdk-${list[sel].id}` : undefined}
          aria-label="प्रकरण शोध — C R क्र. किंवा विषय"
          className="w-full border-b border-slate-200 bg-transparent px-4 py-4 text-lg outline-none dark:border-navy-800"
          placeholder="C R क्र. किंवा विषय"
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
        {list.length === 0 && <div className="px-4 py-3 text-slate-600 dark:text-slate-300" role="status">या शोधानुसार प्रकरण किंवा पान आढळले नाही.</div>}
        {/* focus stays in the input (combobox); options are chosen with ↑ ↓ Enter or a tap */}
        <ul id="cmdk-list" className="max-h-[60vh] overflow-auto py-1" role="listbox" aria-label="निकाल">
          {list.map((c, i) => (
            <li
              key={c.id}
              id={`cmdk-${c.id}`}
              role="option"
              aria-selected={i === sel}
              className={`flex min-h-tap w-full cursor-pointer items-center justify-between gap-3 px-4 py-2 text-left ${i === sel ? 'bg-navy-100 dark:bg-navy-800' : ''}`}
              onMouseEnter={() => setSel(i)}
              onMouseDown={e => e.preventDefault()}
              onClick={() => run(c)}
            >
              {/* a case: C R + stage on line 1, subject on line 2 (UI audit S11: one line left no room for the subject) */}
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <span className={c.sub !== undefined ? 'font-semibold' : ''}>{c.label}</span>
                  {c.hint && <span className="rounded-full bg-slate-100 px-2 text-xs font-semibold text-slate-700 dark:bg-navy-700 dark:text-slate-200">{c.hint}</span>}
                </span>
                {c.sub && <span className="block truncate text-sm text-slate-600 dark:text-slate-300">{c.sub}</span>}
              </span>
              {c.key && <kbd className="hidden shrink-0 rounded border px-1 text-xs text-slate-500 md:inline">{c.key}</kbd>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
