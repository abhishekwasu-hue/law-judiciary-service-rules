import { useEffect, useRef, type ReactNode } from 'react';
import { TONE_CLASS, type Tone } from '../lib/constants';

export function Chip({ tone = 'slate', children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`chip ${TONE_CLASS[tone]}`} title={title}>
      {children}
    </span>
  );
}

export function Skeleton({ className = 'h-5 w-full' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}
export function SkeletonRows({ n = 4 }: { n?: number }) {
  return (
    <div className="space-y-3 p-4" aria-busy="true" aria-label="लोड होत आहे">
      {Array.from({ length: n }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function Empty({ icon = '📂', title, hint, children }: { icon?: string; title: string; hint?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <div className="text-4xl" aria-hidden="true">{icon}</div>
      <div className="text-lg font-semibold">{title}</div>
      {hint && <div className="text-slate-500 dark:text-slate-400">{hint}</div>}
      {children}
    </div>
  );
}

export function Spinner({ className = 'h-5 w-5' }: { className?: string }) {
  return <span className={`inline-block animate-spin rounded-full border-2 border-current border-r-transparent ${className}`} aria-hidden="true" />;
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    ref.current?.querySelector<HTMLElement>('input,textarea,select,button')?.focus();
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-3 pt-[8vh]" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title} className={`card max-h-[84vh] w-full overflow-auto p-4 ${wide ? 'max-w-3xl' : 'max-w-lg'}`}>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-lg font-bold">{title}</h2>
          <button className="btn-ghost min-w-tap px-2" onClick={onClose} aria-label="बंद करा">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">{hint}</span>}
    </label>
  );
}

export function Section({ title, right, children, className = '' }: { title: string; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3 dark:border-navy-800">
        <h2 className="text-base font-bold">{title}</h2>
        {right}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Progress({ pct, tone = 'blue', active = false }: { pct: number; tone?: 'blue' | 'green' | 'red'; active?: boolean }) {
  const c = tone === 'green' ? 'bg-green-600' : tone === 'red' ? 'bg-red-600' : 'bg-blue-600';
  return (
    <div className={`${active ? 'h-3' : 'h-2'} w-full overflow-hidden rounded-full bg-slate-200 dark:bg-navy-800`} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full ${c} transition-all duration-700 ${active ? 'progress-stripes' : ''}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
