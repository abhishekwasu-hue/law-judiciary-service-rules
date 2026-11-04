import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

type Kind = 'ok' | 'err' | 'info';
interface T { id: number; kind: Kind; text: string }
const Ctx = createContext<(text: string, kind?: Kind) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<T[]>([]);
  const push = useCallback((text: string, kind: Kind = 'ok') => {
    const id = Date.now() + Math.random();
    setItems(s => [...s, { id, kind, text }]);
    setTimeout(() => setItems(s => s.filter(t => t.id !== id)), kind === 'err' ? 7000 : 3500);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="toast-stack no-print pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6" aria-live="polite">
        {items.map(t => (
          <div
            key={t.id}
            className={`pointer-events-auto max-w-md rounded-lg px-4 py-3 text-base font-semibold shadow-lg ${
              t.kind === 'err' ? 'bg-red-700 text-white' : t.kind === 'info' ? 'bg-navy-800 text-white' : 'bg-green-700 text-white'
            }`}
            role={t.kind === 'err' ? 'alert' : 'status'}
          >
            {t.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
export const useToast = () => useContext(Ctx);
