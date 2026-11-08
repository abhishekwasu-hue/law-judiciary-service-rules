import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, useCanWrite } from '../lib/auth';
import CommandPalette, { type PaletteMode } from './CommandPalette';
import { useData, useLatestRuns } from '../lib/data';
import { isStale, isWaiting, runNeedsFire } from '../lib/constants';
import { crLabel } from '../lib/format';
import type { Run } from '../lib/types';
import { Modal, Spinner } from './ui';
import ProfileForm from './ProfileForm';
import CasePicker from './CasePicker';
import AiAssistant, { aiFabShown } from './AiAssistant';
import ErrorBoundary from './ErrorBoundary';

/** claude.ai artifact build (lib/artifact): no logout (claude.ai sign-in), no Settings, runs whose firing failed. */
const ARTIFACT = import.meta.env.VITE_BACKEND === 'artifact';

/** Runs still processing (queued or running, not stale). */
export function useActiveRuns(): Run[] {
  const latestRuns = useLatestRuns();
  return [...latestRuns.values()].filter(r => (r.state === 'queued' || r.state === 'running') && !isStale(r));
}

/** "1 प्रक्रिया चालू, 2 प्रतीक्षेत" */
export function activeRunsText(active: Run[]): string {
  if (ARTIFACT) {
    // artifact: no queue — a run left queued did not start (its case page offers "▶ पुन्हा सुरू करा")
    const nf = active.filter(x => runNeedsFire(x)).length;
    const rn = active.length - nf;
    return [rn ? `${rn} प्रक्रिया चालू` : '', nf ? `${nf} काम सुरू झाले नाही` : ''].filter(Boolean).join(', ');
  }
  const w = active.filter(isWaiting).length;
  const r = active.length - w;
  return [r ? `${r} प्रक्रिया चालू` : '', w ? `${w} प्रतीक्षेत` : ''].filter(Boolean).join(', ');
}

// U9: cases whose run the current page already shows in its own status card (नवीन प्रस्ताव: one proposal or the bulk boxes)
// are left out of the global bar, so the same run is not shown twice on that page.
let shownHere: ReadonlySet<number> = new Set();
const shownBy = new Map<symbol, number[]>(); // one entry per mounted page part that shows runs itself
const shownSubs = new Set<() => void>();
const publishShown = () => {
  shownHere = new Set([...shownBy.values()].flat());
  shownSubs.forEach(f => f());
};
const subscribeShown = (f: () => void) => {
  shownSubs.add(f);
  return () => void shownSubs.delete(f);
};
/** A page part shows these cases' runs itself (while mounted). */
export function useRunsShownHere(caseIds: (number | null | undefined)[]) {
  const key = caseIds.filter((x): x is number => typeof x === 'number').sort((a, b) => a - b).join(',');
  const me = useRef(Symbol('runs-shown'));
  useEffect(() => {
    const k = me.current;
    shownBy.set(k, key ? key.split(',').map(Number) : []);
    publishShown();
    return () => {
      shownBy.delete(k);
      publishShown();
    };
  }, [key]);
}

/** Global bar: runs still processing, each a link to its case (Abhi 01.11.2026 — progress must not "disappear" when he
 *  leaves the page). Not shown on the मुख्य पृष्ठ, whose प्रतीक्षा-यादी card lists the same runs with their times (UI audit
 *  S3: the same runs were shown twice there); the प्रकरणे page keeps this bar and has no card. On /nasti the नस्ती bar shows
 *  them (dot on the phone, a short link on desktop) — above the full-height frame this bar overlapped / pushed it. */
function ActiveRunsBar({ className = '' }: { className?: string }) {
  const { cases } = useData();
  const hidden = useSyncExternalStore(subscribeShown, () => shownHere);
  const active = useActiveRuns().filter(r => !hidden.has(r.case_id));
  if (!active.length) return null;
  return (
    <div className={`no-print mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-blue-900 dark:border-blue-900 dark:bg-blue-900/30 dark:text-blue-100 ${className}`} role="status">
      <Spinner className="h-4 w-4" />
      <span className="font-bold">{activeRunsText(active)}</span>
      {/* phone: the case links in one row that scrolls sideways (one per line took ~150 px) */}
      <span className="flex w-full gap-2 overflow-x-auto [scrollbar-width:none] sm:w-auto sm:flex-wrap sm:overflow-visible">
        {active.map(r => {
          const c = cases.find(x => x.id === r.case_id);
          return (
            <NavLink key={r.id} to={`/cases/${r.case_id}`} className="inline-flex min-h-tap shrink-0 items-center whitespace-nowrap rounded-md bg-white px-2.5 py-1 text-sm font-semibold text-blue-800 underline-offset-2 hover:underline dark:bg-navy-800 dark:text-blue-200">
              {ARTIFACT && runNeedsFire(r) ? '⚠ ' : ''}{c ? crLabel(c) : `प्रकरण क्र. ${r.case_id}`} → उघडा
            </NavLink>
          );
        })}
      </span>
    </div>
  );
}

export function Brand() {
  return (
    <div className="flex items-center gap-3">
      <img src="/icon.svg" alt="" className="h-10 w-10" />
      <div className="leading-tight">
        <div className="font-head text-xl font-bold text-navy-800 dark:text-white">प्रस्ताव कक्ष</div>
        <div className="text-sm text-slate-500 dark:text-slate-400">विधि व न्याय विभाग • कार्यासन-6</div>
      </div>
    </div>
  );
}

// `short` = the phone bottom-nav label (UI audit S13: the first word alone, "मुख्य" / "नवीन" / "नस्ती", was unclear); up to
// two lines there.
const NAV = [
  { to: '/', label: 'मुख्य पृष्ठ', short: 'मुख्य पृष्ठ', icon: '🏠', end: true },
  { to: '/nasti', label: 'नस्ती अद्ययावत स्थिती', short: 'नस्ती स्थिती', icon: '📊' },
  { to: '/new', label: 'नवीन प्रस्ताव', short: 'नवीन प्रस्ताव', icon: '➕' },
  { to: '/cases', label: 'प्रकरणे', short: 'प्रकरणे', icon: '🗂️' },
  { to: '/gr', label: 'GR ग्रंथालय', short: 'GR', icon: '📚' },
  { to: '/search', label: 'नियम-उतारे शोध', short: 'नियम-उतारे', icon: '📖' },
];

const ROLE_LABEL: Record<string, string> = { owner: 'मालक', staff: 'कार्यासन कर्मचारी', senior: 'वरिष्ठ (फक्त वाचन)' };

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    try {
      localStorage.setItem('theme', dark ? 'dark' : 'light');
    } catch {
      /* storage unavailable */
    }
  }, [dark]);
  return [dark, useCallback(() => setDark(d => !d), [])];
}

export function ThemeToggle() {
  const [dark, toggle] = useTheme();
  return (
    <button className="btn-ghost min-w-tap px-2" onClick={toggle} aria-label={dark ? 'हलका मोड' : 'गडद मोड'} title={dark ? 'हलका मोड' : 'गडद मोड'}>
      {dark ? '☀️' : '🌙'}
    </button>
  );
}

/** In-app logout confirmation (no window.confirm). Rendered at the Layout root: inside the sticky header (backdrop-blur) a
 *  `position: fixed` box was placed relative to the header and opened off-screen on phones (UI audit S1). */
function LogoutConfirm({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { signOut } = useAuth();
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="card w-full max-w-sm space-y-4 p-5" role="alertdialog" aria-modal="true" aria-labelledby="logout-q">
        <div id="logout-q" className="text-lg font-bold">बाहेर पडायचे आहे का?</div>
        <p className="text-slate-600 dark:text-slate-300">चालू प्रक्रिया थांबणार नाही; पुन्हा लॉगिन करून पाहता येईल.</p>
        <div className="flex gap-2">
          <button className="btn-ghost min-h-tap flex-1" onClick={onClose} autoFocus>नाही</button>
          <button className="btn-primary min-h-tap flex-1" onClick={() => void signOut()}>होय, बाहेर पडणे</button>
        </div>
      </div>
    </div>
  );
}

/** Phone header: सुधारणा, माझी माहिती, theme, settings (owner) and logout behind one "⋯" button so the header fits 360 px. */
function MoreMenu({ isOwner, onProfile, onEdit, onLogout }: { isOwner: boolean; onProfile?: () => void; onEdit: () => void; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const [dark, toggleTheme] = useTheme();
  const btn = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    if (!open) return;
    menu.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    const k = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        btn.current?.focus();
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const items = Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') || []);
        const i = items.indexOf(document.activeElement as HTMLElement);
        const n = items.length;
        if (!n) return;
        e.preventDefault();
        items[(i + (e.key === 'ArrowDown' ? 1 : -1) + n) % n].focus();
      }
    };
    const out = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!menu.current?.contains(t) && !btn.current?.contains(t)) setOpen(false);
    };
    window.addEventListener('keydown', k);
    window.addEventListener('mousedown', out);
    return () => {
      window.removeEventListener('keydown', k);
      window.removeEventListener('mousedown', out);
    };
  }, [open]);
  const item = 'flex min-h-tap w-full items-center gap-2 px-4 py-2 text-left font-semibold hover:bg-slate-100 focus:bg-slate-100 focus:outline-none dark:hover:bg-navy-800 dark:focus:bg-navy-800';
  return (
    <div className="relative">
      <button
        ref={btn}
        className="btn-ghost min-h-tap min-w-tap px-2 text-xl leading-none"
        aria-label="अधिक पर्याय"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls="more-menu"
        onClick={() => setOpen(o => !o)}
      >
        ⋯
      </button>
      {open && (
        <div ref={menu} id="more-menu" role="menu" aria-label="अधिक पर्याय" className="card absolute right-0 top-full z-40 mt-1 w-56 overflow-hidden py-1">
          <button role="menuitem" className={item} onClick={() => { setOpen(false); onEdit(); }}>
            <span aria-hidden="true">✏️</span> मसुद्यात सुधारणा
          </button>
          {onProfile && (
            <button role="menuitem" className={item} onClick={() => { setOpen(false); onProfile(); }}>
              <span aria-hidden="true">👤</span> माझी माहिती
            </button>
          )}
          <button role="menuitem" className={item} onClick={toggleTheme}>
            <span aria-hidden="true">{dark ? '☀️' : '🌙'}</span> {dark ? 'हलका मोड' : 'गडद मोड'}
          </button>
          {isOwner && (
            <NavLink to="/settings" role="menuitem" className={item} onClick={() => setOpen(false)}>
              <span aria-hidden="true">⚙️</span> सेटिंग्ज
            </NavLink>
          )}
          {!ARTIFACT && (
            <button role="menuitem" className={item} onClick={() => { setOpen(false); onLogout(); }}>
              <span aria-hidden="true">🚪</span> बाहेर पडा
            </button>
          )}
        </div>
      )}
    </div>
  );
}

const isTyping = (t: EventTarget | null) => {
  const el = t as HTMLElement | null;
  return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
};

export default function Layout() {
  const { me } = useAuth();
  const canWrite = useCanWrite();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const [palette, setPalette] = useState<PaletteMode | null>(null);
  const [profile, setProfile] = useState(false);
  const [pick, setPick] = useState(false); // ✏️ मसुद्यात सुधारणा: choose the case first
  const [logout, setLogout] = useState(false);
  const closeProfile = useCallback(() => setProfile(false), []);
  const closeLogout = useCallback(() => setLogout(false), []);
  // /nasti on a phone (UI audit option C): the app header and bottom nav are hidden; NastiDashboard shows its own slim bar
  const nasti = pathname === '/nasti';
  const fab = aiFabShown(pathname, canWrite);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPalette(p => (p ? null : 'all'));
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target)) return;
      if (e.key === 'n') {
        e.preventDefault();
        nav('/new');
      } else if (e.key === '/') {
        e.preventDefault();
        nav('/cases?focus=1');
      }
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [nav]);

  // artifact: a read-only viewer (role senior) gets no "नवीन प्रस्ताव" entry (A-M1)
  const nav0 = ARTIFACT && !canWrite ? NAV.filter(i => i.to !== '/new') : NAV;
  const items = me?.role === 'owner' ? [...nav0, { to: '/settings', label: 'सेटिंग्ज', short: 'सेटिंग्ज', icon: '⚙️' }] : nav0;
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `flex min-h-tap items-center gap-3 rounded-lg px-3 py-2 font-semibold ${
      isActive ? 'bg-navy-700 text-white dark:bg-navy-600' : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-navy-800'
    }`;
  // phone: room under the last content for the bottom nav (+ the AI button when shown); /nasti phone: no padding at all
  const mainPad = nasti
    ? 'max-md:p-0 md:pb-10 md:pt-6'
    : `pt-4 md:pt-6 ${fab ? 'pb-36 md:pb-28' : 'pb-28 md:pb-10'}`;

  return (
    <div className="min-h-screen md:flex">
      <aside className="no-print sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-4 border-r border-slate-200 bg-white p-4 dark:border-navy-800 dark:bg-navy-900 md:flex">
        <Brand />
        <nav className="flex flex-col gap-1" aria-label="मुख्य">
          {items.map(i => (
            <NavLink key={i.to} to={i.to} end={i.end} className={linkCls}>
              <span aria-hidden="true">{i.icon}</span>
              {i.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-2 text-sm">
          <button className="btn-ghost w-full justify-between" onClick={() => setPalette('cases')} title="Ctrl + K">
            <span><span aria-hidden="true">🔎</span> प्रकरण शोध</span>
            <span className="text-xs font-normal text-slate-500 dark:text-slate-400">Ctrl K</span>
          </button>
          <button className="btn-ghost w-full justify-start" onClick={() => setPick(true)}>
            <span aria-hidden="true">✏️</span> मसुद्यात सुधारणा
          </button>
          {(!ARTIFACT || canWrite) && (
            <button className="btn-ghost w-full justify-start" onClick={() => setProfile(true)}>
              <span aria-hidden="true">👤</span> माझी माहिती
            </button>
          )}
          <div className="pt-1">
            {me?.profile?.display_name && <div className="font-semibold">{me.profile.display_name}{me.profile.designation ? `, ${me.profile.designation}` : ''}</div>}
            {me?.role && <div className="text-slate-600 dark:text-slate-300">{ROLE_LABEL[me.role] || me.role}</div>}
            <div className="break-all text-slate-500 dark:text-slate-400">{me?.email}</div>
          </div>
          <div className="flex gap-2">
            <ThemeToggle />
            {!ARTIFACT && <button className="btn-ghost min-h-tap flex-1" onClick={() => setLogout(true)}><span aria-hidden="true">🚪</span> बाहेर पडा</button>}
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className={`no-print sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-slate-200 bg-white/95 px-3 py-2 backdrop-blur dark:border-navy-800 dark:bg-navy-900/95 md:hidden ${nasti ? 'hidden' : ''}`}>
          <div className="flex min-w-0 items-center gap-2">
            <img src="/icon.svg" alt="" className="h-8 w-8 shrink-0" />
            <span className="truncate font-head text-lg font-bold">प्रस्ताव कक्ष</span>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button className="btn-ghost min-h-tap px-2.5 text-sm font-semibold" onClick={() => setPalette('cases')}>
              <span aria-hidden="true">🔎</span> प्रकरण शोध
            </button>
            <MoreMenu isOwner={me?.role === 'owner'} onProfile={!ARTIFACT || canWrite ? () => setProfile(true) : undefined} onEdit={() => setPick(true)} onLogout={() => setLogout(true)} />
          </div>
        </header>
        <main className={`mx-auto w-full max-w-7xl px-4 ${mainPad}`}>
          {pathname !== '/' && !nasti && <ActiveRunsBar />}
          <RouteBoundary />
        </main>
        <nav className={`no-print fixed inset-x-0 bottom-0 z-30 grid ${nav0.length === 5 ? 'grid-cols-5' : 'grid-cols-6'} border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] dark:border-navy-800 dark:bg-navy-900 md:hidden ${nasti ? 'hidden' : ''}`} aria-label="मुख्य">
          {nav0.map(i => (
            <NavLink
              key={i.to}
              to={i.to}
              end={i.end}
              aria-label={i.label}
              className={({ isActive }) =>
                `flex min-h-[56px] flex-col items-center justify-center px-0.5 text-center text-[11.5px] font-semibold leading-tight ${isActive ? 'text-navy-700 dark:text-saffron-400' : 'text-slate-600 dark:text-slate-300'}`
              }
            >
              <span className="text-lg leading-none" aria-hidden="true">{i.icon}</span>
              <span className="mt-0.5">{i.short}</span>
            </NavLink>
          ))}
        </nav>
      </div>
      <CommandPalette open={palette !== null} mode={palette || 'all'} onClose={() => setPalette(null)} onEdit={() => setPick(true)} onProfile={!ARTIFACT || canWrite ? () => setProfile(true) : undefined} />
      <CasePicker open={pick} onClose={() => setPick(false)} />
      <AiAssistant />
      {!ARTIFACT && <LogoutConfirm open={logout} onClose={closeLogout} />}
      <Modal open={profile} onClose={closeProfile} title="माझी माहिती">
        <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">नस्ती अद्ययावत स्थिती पानात हीच माहिती वापरली जाते.</p>
        <ProfileForm onDone={closeProfile} onSkip={closeProfile} skipLabel="रद्द" />
      </Modal>
    </div>
  );
}

function RouteBoundary() {
  const loc = useLocation();
  return <ErrorBoundary resetKey={loc.pathname}><Outlet /></ErrorBoundary>;
}
