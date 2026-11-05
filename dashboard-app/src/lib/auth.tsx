import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { api, ApiError, humanError } from './api';
import { initSupabase, sb } from './supabase';
import { parseInlineConfig, type PublicConfig } from './perf';
import { prefetchData } from './data';
import type { Me } from './types';

/** P2: the Worker inlines GET /api/public-config into index.html (#pk-config) → no round trip before login; without it
 *  (dev server, older Worker) the endpoint is called as before. Used once: "पुन्हा प्रयत्न करा" asks the server again. */
let inlineUsed = false;
async function publicConfig(): Promise<PublicConfig> {
  if (!inlineUsed) {
    inlineUsed = true;
    const c = parseInlineConfig(typeof document !== 'undefined' ? document.getElementById('pk-config')?.textContent : null);
    if (c) return c;
  }
  return api<PublicConfig>('/api/public-config');
}

export type Phase = 'loading' | 'error' | 'setup' | 'login' | 'not_member' | 'ready';
interface AuthState {
  phase: Phase;
  error: string;
  me: Me | null;
  session: Session | null;
  reload: () => void;
  /** Replace `me` after PATCH /api/me (profile saved). */
  setMe: (m: Me) => void;
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthState>({ phase: 'loading', error: '', me: null, session: null, reload: () => {}, setMe: () => {}, signOut: async () => {} });

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
        const cfg = await publicConfig();
        if (!alive) return;
        if (!cfg.configured) {
          setPhase('setup');
          return;
        }
        const client = initSupabase(cfg.supabase_url, cfg.supabase_anon_key);
        let resolvedUid: string | null = null; // user whose /api/me already succeeded
        const resolve = async (s: Session | null) => {
          if (!alive) return;
          setSession(s);
          if (!s) {
            resolvedUid = null;
            setMe(null);
            setPhase('login');
            return;
          }
          try {
            // P2: the first data reads start now, alongside /api/me (they used to wait for it)
            prefetchData();
            // /api/me also makes the owner email a member on its first sign-in (worker currentUser()).
            const m = await api<Me>('/api/me');
            if (!alive) return;
            setMe(m);
            resolvedUid = s.user.id;
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
        if (!alive) return; // effect already cleaned up: do not register a listener nobody unsubscribes
        const sub = client.auth.onAuthStateChange((ev, s) => {
          if (!alive) return;
          // supabase-js repeats SIGNED_IN on tab focus: same user → keep the session fresh, no extra /api/me
          if (ev === 'SIGNED_IN' && s && s.user.id === resolvedUid) setSession(s);
          else if (ev === 'SIGNED_IN' || ev === 'SIGNED_OUT') void resolve(s);
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

  return <Ctx.Provider value={{ phase, error, me, session, reload, setMe, signOut }}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
export const useCanWrite = () => {
  const { me } = useAuth();
  return me?.role === 'owner' || me?.role === 'staff';
};
