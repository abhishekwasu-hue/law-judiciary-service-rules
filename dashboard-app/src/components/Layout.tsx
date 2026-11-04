import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import CommandPalette from './CommandPalette';
import { useData } from '../lib/data';
import { isStale, isWaiting } from '../lib/constants';
import { crLabel } from '../lib/format';
import { Modal, Spinner } from './ui';
import ProfileForm from './ProfileForm';
import CasePicker from './CasePicker';
import ErrorBoundary from './ErrorBoundary';

/** Global bar on every page: runs still processing, each a link to its case (Abhi 01.11.2026 — progress must not "disappear" when he leaves the page). */
function ActiveRunsBar() {
  const { cases, latestRuns } = useData();
  const active = [...latestRuns.values()].filter(r => (r.state === 'queued' || r.state === 'running') && !isStale(r));
  if (!active.length) return null;
  return (
    <div className="no-print mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-blue-900 dark:border-blue-900 dark:bg-blue-900/30 dark:text-blue-100" role="status">
      <Spinner className="h-4 w-4" />
      <span className="font-bold">{(() => {
        const w = active.filter(isWaiting).length;
        return `${active.length - w} प्रक्रिया चालू${w ? `, ${w} रांगेत` : ''} — दुसऱ्या पानावर गेलात तरी काम चालूच राहते`;
      })()}</span>
      {active.map(r => {
        const c = cases.find(x => x.id === r.case_id);
        return (
          <NavLink key={r.id} to={`/cases/${r.case_id}`} className="rounded-md bg-white px-2.5 py-1 text-sm font-semibold text-blue-800 underline-offset-2 hover:underline dark:bg-navy-800 dark:text-blue-200">
            {c ? crLabel(c) : `प्रकरण #${r.case_id}`} → पाहा
          </NavLink>
        );
      })}
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

const NAV = [
  { to: '/', label: 'मुख्य पृष्ठ', icon: '🏠', end: true },
  { to: '/nasti', label: 'नस्ती अद्ययावत स्थिती', icon: '📊' },
  { to: '/new', label: 'नवीन प्रस्ताव', icon: '➕' },
  { to: '/cases', label: 'प्रकरणे', icon: '🗂️' },
  { to: '/gr', label: 'GR ग्रंथालय', icon: '📚' },
  { to: '/search', label: 'नोंदवही शोध', icon: '🔎' },
];

export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    try {
      localStorage.setItem('theme', dark ? 'dark' : 'light');
    } catch {
      /* storage unavailable */
    }
  }, [dark]);
  return (
    <button className="btn-ghost min-w-tap px-2" onClick={() => setDark(d => !d)} aria-label={dark ? 'हलका मोड' : 'गडद मोड'} title={dark ? 'हलका मोड' : 'गडद मोड'}>
      {dark ? '☀️' : '🌙'}
    </button>
  );
}

/** In-app logout confirmation (no window.confirm). */
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
        <div id="logout-q" className="text-lg font-bold">app मधून बाहेर पडायचे का?</div>
        <p className="text-slate-600 dark:text-slate-300">चालू प्रक्रिया थांबणार नाही; पुन्हा लॉगिन करून पाहता येईल.</p>
        <div className="flex gap-2">
          <button className="btn-ghost min-h-tap flex-1" onClick={onClose} autoFocus>नाही, थांबा</button>
          <button className="btn-primary min-h-tap flex-1" onClick={() => void signOut()}>होय, बाहेर पडा</button>
        </div>
      </div>
    </div>
  );
}

function LogoutButton({ className, label }: { className: string; label: string }) {
  const [ask, setAsk] = useState(false);
  const close = useCallback(() => setAsk(false), []);
  return (
    <>
      <button className={className} onClick={() => setAsk(true)}>{label}</button>
      <LogoutConfirm open={ask} onClose={close} />
    </>
  );
}

/** Phone header: settings (owner) + logout behind one "⋯" button so the header fits 360 px. */
function MoreMenu({ isOwner, onProfile, onEdit }: { isOwner: boolean; onProfile: () => void; onEdit: () => void }) {
  const [open, setOpen] = useState(false);
  const [ask, setAsk] = useState(false);
  const closeAsk = useCallback(() => setAsk(false), []);
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
        <div ref={menu} id="more-menu" role="menu" aria-label="अधिक पर्याय" className="card absolute right-0 top-full z-40 mt-1 w-48 overflow-hidden py-1">
          <button role="menuitem" className={item} onClick={() => { setOpen(false); onEdit(); }}>
            <span aria-hidden="true">✏️</span> सुधारणा
          </button>
          <button role="menuitem" className={item} onClick={() => { setOpen(false); onProfile(); }}>
            <span aria-hidden="true">👤</span> माझी माहिती
          </button>
          {isOwner && (
            <NavLink to="/settings" role="menuitem" className={item} onClick={() => setOpen(false)}>
              <span aria-hidden="true">⚙️</span> सेटिंग्ज
            </NavLink>
          )}
          <button role="menuitem" className={item} onClick={() => { setOpen(false); setAsk(true); }}>
            <span aria-hidden="true">⎋</span> बाहेर पडा
          </button>
        </div>
      )}
      <LogoutConfirm open={ask} onClose={closeAsk} />
    </div>
  );
}

const isTyping = (t: EventTarget | null) => {
  const el = t as HTMLElement | null;
  return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
};

export default function Layout() {
  const { me } = useAuth();
  const nav = useNavigate();
  const [palette, setPalette] = useState(false);
  const [profile, setProfile] = useState(false);
  const [pick, setPick] = useState(false); // ✏️ सुधारणा: choose the case first
  const closeProfile = useCallback(() => setProfile(false), []);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPalette(p => !p);
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

  const items = me?.role === 'owner' ? [...NAV, { to: '/settings', label: 'सेटिंग्ज', icon: '⚙️' }] : NAV;
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `flex min-h-tap items-center gap-3 rounded-lg px-3 py-2 font-semibold ${
      isActive ? 'bg-navy-700 text-white dark:bg-navy-600' : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-navy-800'
    }`;

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
          <button className="btn-ghost w-full justify-between" onClick={() => setPalette(true)}>
            झटपट शोध <kbd className="rounded border px-1 text-xs">Ctrl K</kbd>
          </button>
          <button className="btn-ghost w-full justify-start" onClick={() => setPick(true)}>
            <span aria-hidden="true">✏️</span> सुधारणा (प्रकरण निवडा)
          </button>
          <button className="btn-ghost w-full justify-start" onClick={() => setProfile(true)}>
            <span aria-hidden="true">👤</span> माझी माहिती
          </button>
          {me?.profile?.display_name && <div className="font-semibold">{me.profile.display_name}{me.profile.designation ? `, ${me.profile.designation}` : ''}</div>}
          <div className="break-all text-slate-500 dark:text-slate-400">{me?.email}</div>
          <div className="flex gap-2">
            <ThemeToggle />
            <LogoutButton className="btn-ghost min-h-tap flex-1" label="बाहेर पडा" />
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="no-print sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-slate-200 bg-white/95 px-4 py-2 backdrop-blur dark:border-navy-800 dark:bg-navy-900/95 md:hidden">
          <div className="flex min-w-0 items-center gap-2">
            <img src="/icon.svg" alt="" className="h-8 w-8 shrink-0" />
            <span className="truncate font-head text-lg font-bold">प्रस्ताव कक्ष</span>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button className="btn-ghost min-h-tap min-w-tap px-2 text-sm font-semibold" onClick={() => setPalette(true)}>शोध</button>
            <ThemeToggle />
            <MoreMenu isOwner={me?.role === 'owner'} onProfile={() => setProfile(true)} onEdit={() => setPick(true)} />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 pb-28 pt-4 md:pb-10 md:pt-6">
          <ActiveRunsBar />
          <RouteBoundary />
        </main>
        <nav className="no-print fixed inset-x-0 bottom-0 z-30 grid grid-cols-6 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] dark:border-navy-800 dark:bg-navy-900 md:hidden" aria-label="मुख्य">
          {NAV.map(i => (
            <NavLink
              key={i.to}
              to={i.to}
              end={i.end}
              className={({ isActive }) =>
                `flex min-h-[56px] flex-col items-center justify-center text-xs font-semibold ${isActive ? 'text-navy-700 dark:text-saffron-400' : 'text-slate-500 dark:text-slate-400'}`
              }
            >
              <span className="text-lg" aria-hidden="true">{i.icon}</span>
              {i.label.split(' ')[0]}
            </NavLink>
          ))}
        </nav>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
      <CasePicker open={pick} onClose={() => setPick(false)} />
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
