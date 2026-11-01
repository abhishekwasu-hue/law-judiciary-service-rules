import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';
import { DataProvider } from './lib/data';
import { ToastProvider } from './components/Toast';
import Layout, { Brand } from './components/Layout';
import { Skeleton, Spinner } from './components/ui';
import Setup from './pages/Setup';
import Login, { NotMember } from './pages/Login';

const Home = lazy(() => import('./pages/Home'));
const NewProposal = lazy(() => import('./pages/NewProposal'));
const Cases = lazy(() => import('./pages/Cases'));
const CaseDetail = lazy(() => import('./pages/CaseDetail'));
const GrLibrary = lazy(() => import('./pages/GrLibrary'));
const RegisterSearch = lazy(() => import('./pages/RegisterSearch'));
const Settings = lazy(() => import('./pages/Settings'));

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
          <p className="break-words text-slate-600 dark:text-slate-300">{error}</p>
          <button className="btn-primary w-full" onClick={reload}>पुन्हा प्रयत्न करा</button>
        </div>
      </div>
    );
  if (phase === 'setup') return <Setup />;
  if (phase === 'login') return <Login />;
  if (phase === 'not_member') return <NotMember />;
  return (
    <DataProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Suspense fallback={<PageFallback />}><Home /></Suspense>} />
            <Route path="new" element={<Suspense fallback={<PageFallback />}><NewProposal /></Suspense>} />
            <Route path="cases" element={<Suspense fallback={<PageFallback />}><Cases /></Suspense>} />
            <Route path="cases/:id" element={<Suspense fallback={<PageFallback />}><CaseDetail /></Suspense>} />
            <Route path="gr" element={<Suspense fallback={<PageFallback />}><GrLibrary /></Suspense>} />
            <Route path="search" element={<Suspense fallback={<PageFallback />}><RegisterSearch /></Suspense>} />
            <Route path="settings" element={<Suspense fallback={<PageFallback />}><Settings /></Suspense>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
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
