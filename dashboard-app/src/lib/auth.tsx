import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { api, ApiError, humanError } from './api';
import { initSupabase, sb } from './supabase';
import type { Me } from './types';

export type Phase = 'loading' | 'error' | 'setup' | 'login' | 'not_member' | 'ready';
interface AuthState {
  phase: Phase;
  error: string;
  me: Me | null;
  session: Session | null;
  reload: () => void;
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthState>({ phase: 'loading', error: '', me: null, session: null, reload: () => {}, signOut: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>('loading');
  const [error, setError] = useState('');
  const [me, setMe] = useState<Me | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(t => t + 1), []);

  useEffect(() => {
    let unsub: (() => void) | undefined;
    let alive = true;
    (async () => {
      setPhase('loading');
      try {
        const cfg = await api<{ configured: boolean; supabase_url: string; supabase_anon_key: string }>('/api/public-config');
        if (!alive) return;
        if (!cfg.configured) {
          setPhase('setup');
          return;
        }
        const client = initSupabase(cfg.supabase_url, cfg.supabase_anon_key);
        const resolve = async (s: Session | null) => {
          setSession(s);
          if (!s) {
            setMe(null);
            setPhase('login');
            return;
          }
          try {
            // /api/me also makes the owner email a member on its first sign-in (worker currentUser()).
            const m = await api<Me>('/api/me');
            if (!alive) return;
            setMe(m);
            setPhase('ready');
          } catch (e) {
            if (e instanceof ApiError && e.status === 403) setPhase('not_member');
            else if (e instanceof ApiError && e.status === 401) setPhase('login');
            else {
              setError(humanError(e));
              setPhase('error');
            }
          }
        };
        const { data } = await client.auth.getSession();
        await resolve(data.session);
        const sub = client.auth.onAuthStateChange((ev, s) => {
          if (ev === 'SIGNED_IN' || ev === 'SIGNED_OUT') void resolve(s);
          else if (ev === 'TOKEN_REFRESHED') setSession(s);
        });
        unsub = () => sub.data.subscription.unsubscribe();
      } catch (e) {
        if (!alive) return;
        setError(humanError(e));
        setPhase('error');
      }
    })();
    return () => {
      alive = false;
      unsub?.();
    };
  }, [tick]);

  const signOut = useCallback(async () => {
    await sb().auth.signOut();
  }, []);

  return <Ctx.Provider value={{ phase, error, me, session, reload, signOut }}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
export const useCanWrite = () => {
  const { me } = useAuth();
  return me?.role === 'owner' || me?.role === 'staff';
};
