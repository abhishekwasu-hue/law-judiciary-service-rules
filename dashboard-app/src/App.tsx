import { lazy, Suspense, useEffect, type ComponentType } from 'react';
import { BrowserRouter, HashRouter, Navigate, Route, Routes } from 'react-router-dom';
// artifact build (claude.ai page): the page URL is fixed, so routes live in the hash
const Router = import.meta.env.VITE_BACKEND === 'artifact' ? HashRouter : BrowserRouter;
import { AuthProvider, useAuth } from './lib/auth';
import { DataProvider } from './lib/data';
import { humanError } from './lib/api';
import { ToastProvider } from './components/Toast';
import Layout, { Brand } from './components/Layout';
import { Skeleton, Spinner } from './components/ui';
import Setup from './pages/Setup';
import Login, { NotMember } from './pages/Login';
import { isChunkError, reloadOnceForNewBuild } from './components/ErrorBoundary';
import { routeChunk } from './lib/perf';

/** lazy() that survives a redeploy: a failed page-file load reloads the page once (guarded per build, no loop). */
function lazyRetry<T extends ComponentType<object>>(load: () => Promise<{ default: T }>) {
  return lazy(() =>
    load().catch((e: unknown) => {
      if (isChunkError(e) && reloadOnceForNewBuild()) return new Promise<{ default: T }>(() => undefined); // page is reloading
      throw e;
    }),
  );
}

// P2: the three most-used pages. The one the address needs starts loading with the app (in parallel with config, login and
// /api/me — it used to wait for them); the other two are fetched when the browser is idle after the first page is shown.
const loadHome = () => import('./pages/Home');
const loadCases = () => import('./pages/Cases');
const loadCaseDetail = () => import('./pages/CaseDetail');
const PAGE_LOADERS = { home: loadHome, cases: loadCases, case: loadCaseDetail } as const;
const first = typeof location !== 'undefined' ? routeChunk(location.pathname) : null;
if (first) void PAGE_LOADERS[first]().catch(() => undefined); // a failure is retried (and reported) by lazyRetry
let warmed = false;
/** After the first page has painted: fetch the other main page files into the cache (no execution cost until opened). */
function warmPages() {
  if (warmed) return;
  warmed = true;
  const go = () => {
    for (const [k, load] of Object.entries(PAGE_LOADERS)) if (k !== first) void load().catch(() => undefined);
  };
  const w = window as Window & { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number };
  if (w.requestIdleCallback) w.requestIdleCallback(go, { timeout: 4000 });
  else setTimeout(go, 1500);
}

const Home = lazyRetry(loadHome);
const NewProposal = lazyRetry(() => import('./pages/NewProposal'));
const Cases = lazyRetry(loadCases);
const CaseDetail = lazyRetry(loadCaseDetail);
const GrLibrary = lazyRetry(() => import('./pages/GrLibrary'));
const RegisterSearch = lazyRetry(() => import('./pages/RegisterSearch'));
const Settings = lazyRetry(() => import('./pages/Settings'));
const NastiDashboard = lazyRetry(() => import('./pages/NastiDashboard'));

function PageFallback() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

function Gate() {
  const { phase, error, reload } = useAuth();
  if (phase === 'loading')
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <Brand />
        <Spinner className="h-8 w-8 text-navy-600" />
      </div>
    );
  if (phase === 'error')
    return (
      <div className="mx-auto max-w-md px-4 py-10">
        <Brand />
        <div className="card mt-6 space-y-3 p-5">
          <h1 className="text-xl font-bold">सर्व्हरशी संपर्क झाला नाही</h1>
          <p className="break-words text-slate-600 dark:text-slate-300">{humanError(error)}</p>
          <button className="btn-primary w-full" onClick={reload}>पुन्हा प्रयत्न करा</button>
        </div>
      </div>
    );
  if (phase === 'setup') return <Setup />;
  if (phase === 'login') return <Login />;
  if (phase === 'not_member') return <NotMember />;
  return <Ready />;
}

function Ready() {
  useEffect(() => {
    // two frames after the first app paint: the page is on screen, the network is free for the other page files
    const id = requestAnimationFrame(() => requestAnimationFrame(warmPages));
    return () => cancelAnimationFrame(id);
  }, []);
  return (
    <DataProvider>
      <Router>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Suspense fallback={<PageFallback />}><Home /></Suspense>} />
            <Route path="new" element={<Suspense fallback={<PageFallback />}><NewProposal /></Suspense>} />
            <Route path="cases" element={<Suspense fallback={<PageFallback />}><Cases /></Suspense>} />
            <Route path="cases/:id" element={<Suspense fallback={<PageFallback />}><CaseDetail /></Suspense>} />
            <Route path="gr" element={<Suspense fallback={<PageFallback />}><GrLibrary /></Suspense>} />
            <Route path="search" element={<Suspense fallback={<PageFallback />}><RegisterSearch /></Suspense>} />
            <Route path="nasti" element={<Suspense fallback={<PageFallback />}><NastiDashboard /></Suspense>} />
            <Route path="settings" element={<Suspense fallback={<PageFallback />}><Settings /></Suspense>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Router>
    </DataProvider>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </ToastProvider>
  );
}
