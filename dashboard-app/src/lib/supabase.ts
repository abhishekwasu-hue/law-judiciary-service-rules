import { createClient, type SupabaseClient } from '@supabase/supabase-js';

// The client is created at run time from GET /api/public-config — no URL or key is compiled into the app.
let client: SupabaseClient | null = null;

export function initSupabase(url: string, anonKey: string): SupabaseClient {
  if (!client) {
    client = createClient(url, anonKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: 'prastav-kaksha-auth' },
    });
  }
  return client;
}

export function sb(): SupabaseClient {
  if (!client) throw new Error('Supabase not initialised');
  return client;
}
export const hasSupabase = () => client !== null;
