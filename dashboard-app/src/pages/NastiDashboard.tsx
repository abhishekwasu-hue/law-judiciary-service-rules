import { useCallback, useEffect, useMemo, useState, type SyntheticEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { useData } from '../lib/data';
import { crLabel } from '../lib/format';
import { NASTI_KEY, findRow, prefillNasti, readNasti, type NastiStore } from '../lib/nasti';
import ProfileForm from '../components/ProfileForm';
import NastiFacts from '../components/NastiFacts';
import { activeRunsText, useActiveRuns } from '../components/Layout';

/** "नस्ती अद्ययावत स्थिती" tab: Abhi's नस्ती-स्थिती डॅशबोर्ड (from Nasti-Dashboard.apk, assets/public/index.html), served
 *  unchanged at /nasti/index.html and shown here in a full-height frame. Its data stays in this browser's storage
 *  (same origin as the app); Android-only features fall back to the browser's own (download, share, copy).
 *  Before the frame loads, the user's profile (/api/me) fills only the EMPTY name / designation / office / places of the
 *  page's store (lib/nasti.ts), so the page's welcome form does not ask again. */
const SKIP_KEY = 'nasti_profile_skip';
const OPEN_KEY = 'nasti_linked_open';
const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } };

/** Phone only (< 768 px, the frame is full width there): compact the नस्ती page's dark header (UI audit option C). CSS only,
 *  injected into the same-origin frame on every load; public/nasti/index.html itself is never edited. If the page's class
 *  names change, a rule simply misses and the header looks as before. */
const NASTI_COMPACT_CSS = `@media (max-width: 767px) {
  .top{padding:6px 10px!important;gap:6px!important;flex-wrap:nowrap!important;flex-direction:column;align-items:stretch!important}
  .top #title{display:none!important}
  .top .off{font-size:17px!important;margin:0!important}
  .top small{display:inline!important;margin:0 8px 0 0!important}
  .top .acts{flex-wrap:nowrap!important;overflow-x:auto;scrollbar-width:none;gap:6px!important}
  .top .acts .btn{flex:none;padding:6px 10px!important;white-space:nowrap}
}
/* dark mode: the selected bottom tab ("🏠 सारांश" etc.) was 3.3:1 on the dark bar — lighter blue (owner 05.11.2026) */
@media (prefers-color-scheme: dark) { :root:not([data-theme=light]) .tabs button.on{color:#9cc2ff!important;border-top-color:#9cc2ff!important} }
:root[data-theme=dark] .tabs button.on{color:#9cc2ff!important;border-top-color:#9cc2ff!important}`;
function injectCompact(e: SyntheticEvent<HTMLIFrameElement>) {
  try {
    const d = e.currentTarget.contentDocument;
    if (!d?.head || d.getElementById('pk-compact')) return;
    const st = d.createElement('style');
    st.id = 'pk-compact';
    st.textContent = NASTI_COMPACT_CSS;
    d.head.appendChild(st);
  } catch {
    /* frame not readable: the header stays as it is */
  }
}

export default function NastiDashboard() {
  const { me } = useAuth();
  const profile = me?.profile;
  const [skipped, setSkipped] = useState(() => lsGet(SKIP_KEY) === '1');
  const showForm = !!profile && !profile.display_name.trim() && !skipped;
  const pkey = profile ? [profile.display_name, profile.designation, profile.office, profile.mine].join('\u0001') : '-';
  // key of the mounted frame; null = not mounted. On a profile change: unmount the old frame first (so it cannot save its
  // old state over ours), then prefill, then mount again.
  const [mounted, setMounted] = useState<string | null>(null);
  useEffect(() => {
    if (showForm || mounted === pkey) return;
    if (mounted !== null) return setMounted(null);
    prefillNasti(profile);
    setMounted(pkey);
  }, [pkey, showForm, mounted, profile]);

  if (showForm) {
    return (
      <div className="max-md:p-4">
      <Link to="/" className="mb-3 inline-flex min-h-tap items-center font-bold text-navy-800 dark:text-white md:hidden"><span aria-hidden="true" className="mr-1">←</span> प्रस्ताव कक्ष</Link>
      <div className="card mx-auto max-w-2xl space-y-3 p-4">
        <h1 className="text-lg font-bold">नस्ती पानासाठी कृपया आपली माहिती एकदाच भरावी</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">नस्ती अद्ययावत स्थिती पान ही माहिती पुन्हा विचारणार नाही.</p>
        <ProfileForm onSkip={() => { lsSet(SKIP_KEY, '1'); setSkipped(true); }} />
      </div>
      </div>
    );
  }
  // phone (option C): Layout hides the app header and bottom nav on /nasti; this page shows one 44 px bar (back to the app,
  // linked cases, a dot while a process runs) and the frame fills the rest; the नस्ती page's own tab bar is the one bottom bar
  return (
    <div className="md:-mx-4 md:-mt-6">
      <LinkedCases />
      {mounted !== null && (
        <iframe
          key={mounted}
          src={import.meta.env.VITE_BACKEND === 'artifact' ? 'nasti/index.html' : '/nasti/index.html'}
          title="नस्ती अद्ययावत स्थिती"
          className="block h-[calc(100dvh-2.8125rem)] w-full border-0"
          allow="microphone; clipboard-write; web-share"
          onLoad={injectCompact}
        />
      )}
    </div>
  );
}

/** While a process runs: dot + "1 प्रक्रिया चालू" (desktop) or dot + count (phone); a link to that case (several: मुख्य पृष्ठ). */
function RunsLink({ className = '', compact = false }: { className?: string; compact?: boolean }) {
  const active = useActiveRuns();
  if (!active.length) return null;
  const runText = activeRunsText(active);
  const one = active.length === 1 ? active[0] : null;
  return (
    <Link to={one ? `/cases/${one.case_id}` : '/'} className={`flex min-h-[2.5rem] shrink-0 items-center gap-1.5 rounded-lg px-2 text-sm font-bold text-blue-800 hover:underline dark:text-blue-200 ${className}`} title={runText} aria-label={`${runText} — उघडा`}>
      <span className="run-dot" aria-hidden="true" /> {compact ? active.length : `${runText} → उघडा`}
    </Link>
  );
}

/** Phone slim bar: "← प्रस्ताव कक्ष" (back to the मुख्य पृष्ठ), a dot while a process runs (the app's run bar is hidden here),
 *  "🔗 जोडलेले n" (opens the linked list over the frame). */
function SlimBar({ n, open, onToggle }: { n: number; open: boolean; onToggle: () => void }) {
  return (
    <div id="nasti-bar" className="flex h-11 items-center justify-between gap-1 px-1.5 md:hidden">
      <Link to="/" className="flex min-h-[2.5rem] items-center rounded-lg px-2.5 font-bold text-navy-800 hover:bg-slate-100 dark:text-white dark:hover:bg-navy-800">
        <span aria-hidden="true" className="mr-1">←</span> प्रस्ताव कक्ष
      </Link>
      <div className="flex shrink-0 items-center gap-1">
        <RunsLink compact />
        <button type="button" className="min-h-[2.5rem] rounded-lg bg-slate-100 px-3 text-sm font-bold text-navy-800 dark:bg-navy-800 dark:text-white" aria-expanded={open} aria-controls="linked-cases" onClick={onToggle}>
          🔗 जोडलेले {n} <span aria-hidden="true" className="text-xs">{open ? '▲' : '▼'}</span>
        </button>
      </div>
    </div>
  );
}

/** Collapsible bar: cases with a नस्ती क्र. and the matching row of the नस्ती page (read from this browser only). */
function LinkedCases() {
  const { cases } = useData();
  const [open, setOpen] = useState(() => lsGet(OPEN_KEY) === '1');
  const [store, setStore] = useState<NastiStore | null>(() => readNasti());
  useEffect(() => {
    // the frame writes its store as the user works → the parent document gets a `storage` event
    const s = (e: StorageEvent) => { if (e.key === NASTI_KEY || e.key === null) setStore(readNasti()); };
    window.addEventListener('storage', s);
    return () => window.removeEventListener('storage', s);
  }, []);
  const linked = useMemo(() => cases.filter(c => (c.nasti_no || '').trim()), [cases]);
  const toggle = useCallback(() => {
    setOpen(o => { lsSet(OPEN_KEY, o ? '0' : '1'); return !o; });
    setStore(readNasti());
  }, []);
  return (
    <div className="no-print relative z-20 border-b border-slate-200 bg-white dark:border-navy-800 dark:bg-navy-900">
      <SlimBar n={linked.length} open={open} onToggle={toggle} />
      <div className="hidden min-h-[2.75rem] items-center md:flex">
        <button className="flex min-h-[2.75rem] flex-1 items-center justify-between gap-2 px-4 text-left font-semibold" aria-expanded={open} aria-controls="linked-cases" onClick={toggle}>
          <span>🔗 जोडलेले प्रस्ताव ({linked.length})</span>
          <span aria-hidden="true" className="text-slate-500">{open ? '▲' : '▼'}</span>
        </button>
        <RunsLink className="mr-4" />
      </div>
      {open && (
        // phone: a panel over the frame (the frame keeps its full height); desktop: in the flow as before
        <div id="linked-cases" className="max-h-[60dvh] overflow-auto bg-white px-4 pb-3 shadow-lg dark:bg-navy-900 max-md:absolute max-md:inset-x-0 max-md:top-full max-md:border-b max-md:border-slate-200 max-md:dark:border-navy-800 md:max-h-[40dvh] md:shadow-none">
          {!linked.length ? (
            <p className="py-2 text-sm text-slate-600 dark:text-slate-300">एकाही प्रकरणाला नस्ती क्र. जोडलेला नाही. नस्ती क्र. जोडण्यासाठी कृपया प्रकरणाच्या पानावर “नस्ती क्र. (eOffice)” भरावा.</p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-navy-800">
              {linked.map(c => {
                const r = findRow(c.nasti_no, store);
                return (
                  <li key={c.id}>
                    <Link to={`/cases/${c.id}`} className="block py-2 hover:bg-slate-50 dark:hover:bg-navy-800">
                      <div className="flex min-w-0 items-baseline gap-2">
                        <span className="shrink-0 font-bold text-navy-700 dark:text-saffron-400">{crLabel(c)}</span>
                        <span className="truncate text-sm">{c.subject || '—'}</span>
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">{c.nasti_no}</div>
                      {r ? <NastiFacts r={r} /> : <div className="text-sm font-semibold text-amber-700 dark:text-amber-300">नस्ती पानात सापडली नाही</div>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
