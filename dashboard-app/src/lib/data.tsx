// Shared case + letter store for list, फलक (Kanban), Home and the command palette. Reads go straight to Supabase (RLS).
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { sb } from './supabase';
import { api, humanError } from './api';
import { useAuth, useCanWrite } from './auth';
import type { Case, Letter, Run } from './types';
import { isEditRun } from './constants';
import { addDaysISO, crLabel, ownerDetail, setViewerIsOwner, todayISO } from './format';
import { isMissingColumn, latestRunPerCase, RUN_LIST_COLUMNS } from './perf';
import { useToast } from '../components/Toast';

type Res<T> = { data: T[] | null; error: { message: string; code?: string } | null };
type Reads = [Res<Case>, Res<Letter>, Res<Run>];

// P4: the runs list reads only the columns the shared store uses. An old DB without one of them (migrations 0007 / 0011 /
// 0013 not applied) answers "column does not exist" → that read is repeated with '*' and '*' is kept for this app load.
let runCols = RUN_LIST_COLUMNS;
async function readRuns(): Promise<Res<Run>> {
  const q = (cols: string) => sb().from('runs').select(cols).order('created_at', { ascending: false }).limit(500);
  let r = (await q(runCols)) as unknown as Res<Run>;
  if (r.error && runCols !== '*' && isMissingColumn(r.error)) {
    runCols = '*';
    r = (await q('*')) as unknown as Res<Run>;
  }
  return r;
}
const readAll = (): Promise<Reads> =>
  Promise.all([
    sb().from('cases').select('*').order('created_at', { ascending: false }) as unknown as Promise<Res<Case>>,
    sb().from('letters').select('*').order('created_at', { ascending: false }) as unknown as Promise<Res<Letter>>,
    readRuns(),
  ]);

// P2: started by AuthProvider as soon as a stored session exists, in parallel with GET /api/me (before: me → page → data).
// The first DataProvider read takes it once; RLS decides what a non-member gets (nothing), and that result is then unused.
let early: Promise<Reads> | null = null;
export function prefetchData() {
  const p = readAll();
  early = p;
  p.catch(() => { if (early === p) early = null; });
}

interface DataState {
  cases: Case[];
  letters: Letter[];
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  setStage: (id: number, stage: string) => Promise<void>;
  patchLocal: (c: Case) => void;
  /** Replace the letters of one case in the shared store (after a local re-read of that case's letters). */
  setCaseLetters: (caseId: number, rows: Letter[]) => void;
}
const Ctx = createContext<DataState>(null as unknown as DataState);
// P6: the latest runs live in their own context, so a Realtime run update (progress step) re-renders only the run views
// (list badges, प्रतीक्षा-यादी, global bar), not every page that reads the cases.
const RunsCtx = createContext<Map<number, Run>>(new Map());

export function DataProvider({ children }: { children: ReactNode }) {
  // the viewer's role for helpers called without `isOwner` (humanError, cleanReason …): set during render, before children
  const { me } = useAuth();
  setViewerIsOwner(me?.role === 'owner');
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

  const fetchAll = useCallback(async () => {
    // A failed read keeps the previous data and reports the error (never shown as "no cases").
    try {
      const pre = early;
      early = null;
      const [c, l, r] = await (pre ? pre.catch(() => readAll()) : readAll());
      // staff: which lists could not be read + the Marathi reason; the owner also gets the raw Supabase text (X2)
      const failed = ([['प्रकरणे', c.error], ['पत्रे', l.error], ['प्रक्रिया', r.error]] as const).filter(([, e]) => e);
      setError(
        failed.length
          ? `${failed.map(([n]) => n).join(', ')} यांची माहिती वाचता आली नाही. ${humanError(new Error(failed[0][1]!.message), false)}`
            + ownerDetail(failed.map(([n, e]) => `${n}: ${e!.message}`).join(' • '))
          : '',
      );
      if (!c.error) setCases((c.data as Case[]) || []);
      if (!l.error) setLetters((l.data as Letter[]) || []);
      if (!r.error) {
        const rows = (r.data as Run[]) || [];
        for (const x of rows) runState.current.set(x.id, x.state);
        // सुधारणा-चॅट runs never stand for the case's processing state (list badges, queue, global bar)
        setLatestRuns(latestRunPerCase(rows));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setLoading(false);
  }, []);

  // Coalesced refresh: tab focus, `online` and Realtime (re)subscribe can fire together → at most one fetch in flight + one queued.
  const inFlight = useRef<Promise<void> | null>(null);
  const again = useRef(false);
  const refresh = useCallback(async () => {
    if (inFlight.current) {
      again.current = true;
      return inFlight.current;
    }
    const run = (async () => {
      do {
        again.current = false;
        await fetchAll();
      } while (again.current);
    })();
    inFlight.current = run;
    try {
      await run;
    } finally {
      inFlight.current = null;
    }
  }, [fetchAll]);

  // Stuck runs (queued/running > 3.5 h) → failed "वेळ संपली — पुन्हा तयार करा" (Worker, service role). Once per app load.
  const canWrite = useCanWrite();
  useEffect(() => {
    if (canWrite) void api('/api/runs/sweep', { method: 'POST', body: {} }).catch(() => undefined);
  }, [canWrite]);

  useEffect(() => {
    void refresh();
    // Realtime does not replay events missed while the tab slept or the network dropped → re-read on return.
    const onVisible = () => document.visibilityState === 'visible' && void refresh();
    const onOnline = () => void refresh();
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onOnline);
    // (re)subscribed: events between the last read and now were not delivered → re-read (coalesced with the first read)
    const onStatus = (status: string) => status === 'SUBSCRIBED' && void refresh();
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
      .subscribe(onStatus);
    const chr = sb()
      .channel('runs-all')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'runs' }, payload => {
        const row = payload.new as Run;
        if (!row?.id) return;
        const prev = runState.current.get(row.id);
        runState.current.set(row.id, row.state);
        if ((prev === 'queued' || prev === 'running') && (row.state === 'done' || row.state === 'failed')) {
          const c = casesRef.current.find(x => x.id === row.case_id);
          const label = c ? crLabel(c) : `प्रकरण क्र. ${row.case_id}`;
          if (isEditRun(row)) {
            if (row.state === 'done') toast(`${label}: ${row.edit_result?.refused ? 'सुधारणा नाकारली. कृपया कारण प्रकरणात पाहावे, ही विनंती.' : 'सुधारणा तयार — नवीन आवृत्ती उपलब्ध आहे.'}`, row.edit_result?.refused ? 'err' : 'ok');
            else toast(`${label}: सुधारणा अयशस्वी. कृपया कारण प्रकरणात पाहावे, ही विनंती.`, 'err');
          } else if (row.state === 'done') toast(`${label}: प्रक्रिया पूर्ण — फाइल प्रकरणात उपलब्ध आहेत.`, 'ok');
          else toast(`${label}: प्रक्रिया अयशस्वी. कृपया प्रकरण उघडून 'पुन्हा तयार करा' वापरावे, ही विनंती.`, 'err');
        }
        if (isEditRun(row)) return;
        setLatestRuns(s => {
          const cur = s.get(row.case_id);
          if (cur && cur.id > row.id) return s;
          const n = new Map(s);
          n.set(row.case_id, row);
          return n;
        });
      })
      .subscribe(onStatus);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onOnline);
      void sb().removeChannel(ch);
      void sb().removeChannel(chr);
    };
  }, [refresh, toast]);

  const patchLocal = useCallback((row: Case) => setCases(s => s.map(x => (x.id === row.id ? row : x))), []);
  const setCaseLetters = useCallback(
    (caseId: number, rows: Letter[]) =>
      setLetters(s => [...rows, ...s.filter(x => x.case_id !== caseId)].sort((a, b) => (a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : 0))),
    [],
  );

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

  const value = useMemo(
    () => ({ cases, letters, loading, error, refresh, setStage, patchLocal, setCaseLetters }),
    [cases, letters, loading, error, refresh, setStage, patchLocal, setCaseLetters],
  );
  return (
    <Ctx.Provider value={value}>
      <RunsCtx.Provider value={latestRuns}>{children}</RunsCtx.Provider>
    </Ctx.Provider>
  );
}
export const useData = () => useContext(Ctx);
/** Latest (non-edit) run of every case, live via Realtime. */
export const useLatestRuns = () => useContext(RunsCtx);

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
