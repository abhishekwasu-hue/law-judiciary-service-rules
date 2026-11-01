// Shared case + letter store for list, Kanban, Home and the command palette. Reads go straight to Supabase (RLS).
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { sb } from './supabase';
import type { Case, Letter } from './types';
import { addDaysISO, todayISO } from './format';

interface DataState {
  cases: Case[];
  letters: Letter[];
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  setStage: (id: number, stage: string) => Promise<void>;
  patchLocal: (c: Case) => void;
}
const Ctx = createContext<DataState>(null as unknown as DataState);

export function DataProvider({ children }: { children: ReactNode }) {
  const [cases, setCases] = useState<Case[]>([]);
  const [letters, setLetters] = useState<Letter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    const [c, l] = await Promise.all([
      sb().from('cases').select('*').order('created_at', { ascending: false }),
      sb().from('letters').select('*').order('created_at', { ascending: false }),
    ]);
    if (c.error) setError(c.error.message);
    else setError('');
    setCases((c.data as Case[]) || []);
    setLetters((l.data as Letter[]) || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
    const ch = sb()
      .channel('cases-all')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'cases' }, payload => {
        if (payload.eventType === 'DELETE') {
          const id = (payload.old as { id?: number }).id;
          setCases(s => s.filter(x => x.id !== id));
        } else {
          const row = payload.new as Case;
          setCases(s => (s.some(x => x.id === row.id) ? s.map(x => (x.id === row.id ? row : x)) : [row, ...s]));
        }
      })
      .subscribe();
    return () => {
      void sb().removeChannel(ch);
    };
  }, [refresh]);

  const patchLocal = useCallback((row: Case) => setCases(s => s.map(x => (x.id === row.id ? row : x))), []);

  /** Optimistic stage change; RLS allows owner/staff; the DB trigger logs it in `activity`. */
  const setStage = useCallback(async (id: number, stage: string) => {
    let before: Case | undefined;
    setCases(s =>
      s.map(x => {
        if (x.id !== id) return x;
        before = x;
        return { ...x, stage };
      }),
    );
    const { error: e } = await sb().from('cases').update({ stage }).eq('id', id);
    if (e) {
      if (before) {
        const b = before;
        setCases(s => s.map(x => (x.id === id ? b : x)));
      }
      throw new Error(e.message);
    }
  }, []);

  return <Ctx.Provider value={{ cases, letters, loading, error, refresh, setStage, patchLocal }}>{children}</Ctx.Provider>;
}
export const useData = () => useContext(Ctx);

/** Letter awaiting reply: sent, no reply received. */
export const isPendingLetter = (l: Letter) => !!l.sent_date && !l.reply_received_date && l.status !== 'उत्तर प्राप्त';

/** Overdue: case due_date passed (not closed) or a pending letter whose reply_due passed. */
export function overdueIds(cases: Case[], letters: Letter[]): Set<number> {
  const t = todayISO();
  const s = new Set<number>();
  for (const c of cases) if (c.due_date && c.due_date < t && c.stage !== 'बंद') s.add(c.id);
  for (const l of letters) if (isPendingLetter(l) && l.reply_due && l.reply_due < t) s.add(l.case_id);
  return s;
}
export function dueSoon(letters: Letter[], days = 7): Letter[] {
  const t = todayISO();
  const lim = addDaysISO(t, days);
  return letters.filter(l => isPendingLetter(l) && l.reply_due && l.reply_due <= lim).sort((a, b) => (a.reply_due! < b.reply_due! ? -1 : 1));
}
