import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { useData } from '../lib/data';
import { crLabel } from '../lib/format';
import { NASTI_KEY, findRow, prefillNasti, readNasti, type NastiStore } from '../lib/nasti';
import ProfileForm from '../components/ProfileForm';
import NastiFacts from '../components/NastiFacts';

/** "नस्ती अद्ययावत स्थिती" tab: Abhi's नस्ती-स्थिती डॅशबोर्ड (from Nasti-Dashboard.apk, assets/public/index.html), served
 *  unchanged at /nasti/index.html and shown here in a full-height frame. Its data stays in this browser's storage
 *  (same origin as the app); Android-only features fall back to the browser's own (download, share, copy).
 *  Before the frame loads, the user's profile (/api/me) fills only the EMPTY name / designation / office / places of the
 *  page's store (lib/nasti.ts), so the page's welcome form does not ask again. */
const SKIP_KEY = 'nasti_profile_skip';
const OPEN_KEY = 'nasti_linked_open';
const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } };

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
      <div className="card mx-auto max-w-2xl space-y-3 p-4">
        <h1 className="text-lg font-bold">नस्ती पानासाठी आपली माहिती एकदाच भरा</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">नस्ती अद्ययावत स्थिती पान ही माहिती पुन्हा विचारणार नाही.</p>
        <ProfileForm onSkip={() => { lsSet(SKIP_KEY, '1'); setSkipped(true); }} />
      </div>
    );
  }
  return (
    <div className="-mx-4 -mt-4 md:-mt-6">
      <LinkedCases />
      {mounted !== null && (
        <iframe
          key={mounted}
          src="/nasti/index.html"
          title="नस्ती अद्ययावत स्थिती"
          className="block h-[calc(100dvh-10.25rem)] w-full border-0 md:h-[calc(100dvh-2.8125rem)]"
          allow="microphone; clipboard-write; web-share"
        />
      )}
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
  const toggle = () => {
    setOpen(o => { lsSet(OPEN_KEY, o ? '0' : '1'); return !o; });
    setStore(readNasti());
  };
  return (
    <div className="no-print border-b border-slate-200 bg-white dark:border-navy-800 dark:bg-navy-900">
      <button className="flex min-h-[2.75rem] w-full items-center justify-between gap-2 px-4 text-left font-semibold" aria-expanded={open} aria-controls="linked-cases" onClick={toggle}>
        <span>🔗 जोडलेले प्रस्ताव ({linked.length})</span>
        <span aria-hidden="true" className="text-slate-500">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div id="linked-cases" className="max-h-[40dvh] overflow-auto px-4 pb-3">
          {!linked.length ? (
            <p className="py-2 text-sm text-slate-600 dark:text-slate-300">एकाही प्रकरणाला नस्ती क्र. जोडलेला नाही — प्रकरणाच्या पानावर “नस्ती क्र. (eOffice)” भरा.</p>
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
