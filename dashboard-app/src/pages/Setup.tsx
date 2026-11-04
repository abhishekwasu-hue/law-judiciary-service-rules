import { useEffect, useState, type FormEvent } from 'react';
import { api, humanError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Field, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import { Brand } from '../components/Layout';

const EMPTY = {
  setup_code: '', owner_email: '', supabase_url: '', supabase_anon_key: '', supabase_service_key: '',
  github_repo: '', github_branch: '', github_token: '', anthropic_api_key: '', model: '',
};

export default function Setup() {
  const { reload } = useAuth();
  const toast = useToast();
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));

  // GET /api/setup creates the one-time setup_code in KV (read it in the Cloudflare dashboard).
  useEffect(() => {
    api('/api/setup').catch(() => {});
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr('');
    try {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
      await api('/api/setup', { body });
      toast('सेटअप पूर्ण झाला. कृपया लॉगिन करावे.');
      reload();
    } catch (x) {
      setErr(humanError(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <Brand />
      <form onSubmit={submit} className="card mt-4 space-y-5 p-5">
        <div>
          <h1 className="text-2xl font-bold">प्रारंभिक सेटअप</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">हा सेटअप एकदाच करावयाचा आहे. नंतरचे सर्व बदल "सेटिंग्ज" मधून (फक्त मालक) करता येतात.</p>
        </div>

        <fieldset className="space-y-4">
          <legend className="mb-2 font-bold text-navy-700 dark:text-navy-200">1. सेटअप कोड</legend>
          <Field
            label="सेटअप कोड *"
            hint={
              <details>
                <summary className="flex min-h-tap cursor-pointer items-center">कोड कुठे मिळेल?</summary>
                Cloudflare dashboard → Workers &amp; Pages → Workers KV (Storage &amp; Databases) → namespace <b>SETTINGS</b> → key <b>setup_code</b> ची value. हा कोड एकदाच लागतो; सेटअपनंतर तो नष्ट होतो.
              </details>
            }
          >
            <input className="input font-mono" required value={f.setup_code} onChange={set('setup_code')} autoComplete="off" />
          </Field>
          <Field label="मालकाचा ई-मेल *" hint="या ई-मेलने पहिले लॉगिन करणारा वापरकर्ता = मालक.">
            <input className="input" type="email" required value={f.owner_email} onChange={set('owner_email')} autoComplete="email" />
          </Field>
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="mb-2 font-bold text-navy-700 dark:text-navy-200">2. Supabase (आवश्यक)</legend>
          <p className="text-sm text-slate-500 dark:text-slate-400">Supabase → Project Settings → API.</p>
          <Field label="Supabase URL *">
            <input className="input font-mono" type="url" required placeholder="https://xxxx.supabase.co" value={f.supabase_url} onChange={set('supabase_url')} />
          </Field>
          <Field label="anon (public) key *">
            <input className="input font-mono" required value={f.supabase_anon_key} onChange={set('supabase_anon_key')} autoComplete="off" />
          </Field>
          <Field label="service_role key *" hint="गोपनीय — Worker मध्येच राहते; ब्राउझरला परत दिली जात नाही.">
            <input className="input font-mono" type="password" required value={f.supabase_service_key} onChange={set('supabase_service_key')} autoComplete="off" />
          </Field>
        </fieldset>

        <details className="rounded-lg border border-slate-200 p-3 dark:border-navy-800">
          <summary className="flex min-h-tap cursor-pointer items-center py-2 font-bold text-navy-700 dark:text-navy-200">3. प्रस्ताव तयार करणारी सेवा (ऐच्छिक)</summary>
          <div className="mt-3 space-y-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">हे तपशील नंतर "सेटिंग्ज" मधूनही भरता येतात.</p>
            <Field label="GitHub repo" hint="उदा. owner/repo">
              <input className="input font-mono" value={f.github_repo} onChange={set('github_repo')} />
            </Field>
            <Field label="GitHub branch">
              <input className="input font-mono" placeholder="main" value={f.github_branch} onChange={set('github_branch')} />
            </Field>
            <Field label="GitHub token">
              <input className="input font-mono" type="password" value={f.github_token} onChange={set('github_token')} autoComplete="off" />
            </Field>
            <Field label="Anthropic API key">
              <input className="input font-mono" type="password" value={f.anthropic_api_key} onChange={set('anthropic_api_key')} autoComplete="off" />
            </Field>
            <Field label="Model">
              <input className="input font-mono" value={f.model} onChange={set('model')} />
            </Field>
          </div>
        </details>

        {err && <div className="rounded-lg bg-red-100 px-3 py-2 font-semibold text-red-900 dark:bg-red-900/50 dark:text-red-100" role="alert">{err}</div>}
        <button className="btn-primary w-full" disabled={busy}>
          {busy && <Spinner />} सेटअप जतन करा
        </button>
      </form>
    </div>
  );
}
