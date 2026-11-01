// Shared case + letter store for list, फलक (Kanban), Home and the command palette. Reads go straight to Supabase (RLS).
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { sb } from './supabase';
import { api } from './api';
import { useCanWrite } from './auth';
import type { Case, Letter, Run } from './types';
import { addDaysISO, crLabel, todayISO } from './format';
import { useToast } from '../components/Toast';

interface DataState {
  latestRuns: Map<number, Run>;
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
  // latest run of every case (for list status + the global 'अभ्यास चालू' bar), kept live via Realtime
  const [latestRuns, setLatestRuns] = useState<Map<number, Run>>(new Map());
  // Toast when a run finishes (queued/running → done/failed) so a user on another page learns of it.
  const toast = useToast();
  const runState = useRef<Map<number, Run['state']>>(new Map()); // run id → last known state
  const casesRef = useRef<Case[]>([]);
  useEffect(() => {
    casesRef.current = cases;
  }, [cases]);

  const refresh = useCallback(async () => {
    const [c, l] = await Promise.all([
      sb().from('cases').select('*').order('created_at', { ascending: false }),
      sb().from('letters').select('*').order('created_at', { ascending: false }),
    ]);
    if (c.error) setError(c.error.message);
    else setError('');
    setCases((c.data as Case[]) || []);
    setLetters((l.data as Letter[]) || []);
    const r = await sb().from('runs').select('*').order('created_at', { ascending: false }).limit(500);
    const m = new Map<number, Run>();
    for (const x of (r.data as Run[]) || []) {
      if (!m.has(x.case_id)) m.set(x.case_id, x);
      runState.current.set(x.id, x.state);
    }
    setLatestRuns(m);
    setLoading(false);
  }, []);

  // Stuck runs (queued/running > 3.5 h) → failed "वेळ संपली — पुन्हा तयार करा" (Worker, service role). Once per app load.
  const canWrite = useCanWrite();
  useEffect(() => {
    if (canWrite) void api('/api/runs/sweep', { method: 'POST', body: {} }).catch(() => undefined);
  }, [canWrite]);

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
    const chr = sb()
      .channel('runs-all')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'runs' }, payload => {
        const row = payload.new as Run;
        if (!row?.id) return;
        const prev = runState.current.get(row.id);
        runState.current.set(row.id, row.state);
        if ((prev === 'queued' || prev === 'running') && (row.state === 'done' || row.state === 'failed')) {
          const c = casesRef.current.find(x => x.id === row.case_id);
          const label = c ? crLabel(c) : `प्रकरण #${row.case_id}`;
          if (row.state === 'done') toast(`${label}: प्रक्रिया तयार — प्रकरणे मध्ये पाहा`, 'ok');
          else toast(`${label}: प्रक्रिया अयशस्वी — प्रकरण उघडून "पुन्हा तयार करा" दाबा`, 'err');
        }
        setLatestRuns(s => {
          const cur = s.get(row.case_id);
          if (cur && cur.id > row.id) return s;
          const n = new Map(s);
          n.set(row.case_id, row);
          return n;
        });
      })
      .subscribe();
    return () => {
      void sb().removeChannel(ch);
      void sb().removeChannel(chr);
    };
  }, [refresh, toast]);

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

  return <Ctx.Provider value={{ cases, letters, latestRuns, loading, error, refresh, setStage, patchLocal }}>{children}</Ctx.Provider>;
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
