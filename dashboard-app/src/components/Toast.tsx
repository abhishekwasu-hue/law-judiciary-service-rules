import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

type Kind = 'ok' | 'err' | 'info';
/** Optional button in the toast (e.g. "↶ पूर्ववत करा"); the toast closes when it is pressed. */
export interface ToastAction { label: string; run: () => void }
interface T { id: number; kind: Kind; text: string; action?: ToastAction }
const Ctx = createContext<(text: string, kind?: Kind, action?: ToastAction) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<T[]>([]);
  const close = useCallback((id: number) => setItems(s => s.filter(t => t.id !== id)), []);
  const push = useCallback((text: string, kind: Kind = 'ok', action?: ToastAction) => {
    const id = Date.now() + Math.random();
    setItems(s => [...s, { id, kind, text, action }]);
    // a toast with a button stays longer, so there is time to press it
    setTimeout(() => close(id), action ? 8000 : kind === 'err' ? 7000 : 3500);
  }, [close]);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="toast-stack no-print pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6" aria-live="polite">
        {items.map(t => (
          <div
            key={t.id}
            className={`pointer-events-auto flex max-w-md flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-4 py-3 text-base font-semibold shadow-lg ${
              t.kind === 'err' ? 'bg-red-700 text-white' : t.kind === 'info' ? 'bg-navy-800 text-white' : 'bg-green-700 text-white'
            }`}
            role={t.kind === 'err' ? 'alert' : 'status'}
          >
            <span className="min-w-0">{t.text}</span>
            {t.action && (
              <button
                type="button"
                className="min-h-tap shrink-0 rounded-md bg-white/15 px-3 font-bold hover:bg-white/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
                onClick={() => { close(t.id); t.action!.run(); }}
              >
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
export const useToast = () => useContext(Ctx);
