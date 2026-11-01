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

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const k = (e: KeyboardEvent) => {
      if (e.key === 'Escape') return closeRef.current();
      if (e.key !== 'Tab' || !ref.current) return;
      // keep keyboard focus inside the dialog while it is open
      const els = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(x => x.offsetParent !== null);
      if (!els.length) return e.preventDefault();
      const first = els[0], last = els[els.length - 1];
      const inside = ref.current.contains(document.activeElement);
      if (e.shiftKey && (document.activeElement === first || !inside)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (document.activeElement === last || !inside)) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener('keydown', k);
    const body = ref.current?.querySelector<HTMLElement>('[data-modal-body] input,[data-modal-body] textarea,[data-modal-body] select,[data-modal-body] button');
    (body || ref.current?.querySelector<HTMLElement>(FOCUSABLE))?.focus();
    return () => {
      window.removeEventListener('keydown', k);
      // return focus to the control that opened the dialog
      if (opener && document.contains(opener)) opener.focus();
    };
  }, [open]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-3 pt-[8vh]" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title} className={`card max-h-[84vh] w-full overflow-auto p-4 ${wide ? 'max-w-3xl' : 'max-w-lg'}`}>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-lg font-bold">{title}</h2>
          <button className="btn-ghost min-h-tap min-w-tap px-2" onClick={onClose} aria-label="बंद करा">✕</button>
        </div>
        <div data-modal-body>{children}</div>
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

export function Progress({ pct, tone = 'blue', active = false, label = 'प्रगती' }: { pct: number; tone?: 'blue' | 'green' | 'red'; active?: boolean; label?: string }) {
  const c = tone === 'green' ? 'bg-green-600' : tone === 'red' ? 'bg-red-600' : 'bg-blue-600';
  return (
    <div className={`${active ? 'h-3' : 'h-2'} w-full overflow-hidden rounded-full bg-slate-200 dark:bg-navy-800`} role="progressbar" aria-label={label} aria-valuetext={`${label}: ${Math.round(pct)}%`} aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full ${c} transition-all duration-700 ${active ? 'progress-stripes' : ''}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
