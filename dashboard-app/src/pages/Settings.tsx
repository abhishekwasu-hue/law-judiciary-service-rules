import { useEffect, useState, type FormEvent } from 'react';
import { api, humanError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { sb } from '../lib/supabase';
import type { Member } from '../lib/types';
import { fmtDate } from '../lib/format';
import { Chip, Field, Section, SkeletonRows, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';

const PLAIN: { k: string; label: string; hint?: string }[] = [
  { k: 'owner_email', label: 'मालकाचा ई-मेल' },
  { k: 'supabase_url', label: 'Supabase URL' },
  { k: 'supabase_anon_key', label: 'Supabase anon key' },
  { k: 'github_repo', label: 'GitHub repo', hint: 'owner/repo' },
  { k: 'github_branch', label: 'GitHub branch' },
  { k: 'model', label: 'Model' },
];
const SECRET: { k: string; label: string }[] = [
  { k: 'supabase_service_key', label: 'Supabase service_role key' },
  { k: 'github_token', label: 'GitHub token' },
  { k: 'anthropic_api_key', label: 'Anthropic API key' },
];
const ROLE_LABEL: Record<string, string> = { owner: 'मालक', staff: 'कार्यासन कर्मचारी', senior: 'वरिष्ठ (फक्त वाचन)' };

export default function Settings() {
  const { me } = useAuth();
  const toast = useToast();
  const [cur, setCur] = useState<Record<string, string> | null>(null);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [inv, setInv] = useState({ email: '', role: 'staff' });
  const [invBusy, setInvBusy] = useState(false);

  const load = async () => {
    try {
      const s = await api<Record<string, string>>('/api/settings');
      setCur(s);
      setEdit(Object.fromEntries(PLAIN.map(p => [p.k, s[p.k] || ''])));
    } catch (e) {
      toast(humanError(e), 'err');
    }
    const m = await sb().from('members').select('*').order('created_at');
    setMembers((m.data as Member[]) || []);
  };
  useEffect(() => {
    if (me?.role === 'owner') void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  if (me?.role !== 'owner') return <div className="card p-6 text-center">सेटिंग्ज फक्त मालकासाठी.</div>;

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      // Plain values are sent as typed; a secret is sent only if a new value was typed (empty = unchanged).
      const body: Record<string, string> = {};
      for (const p of PLAIN) if (cur && edit[p.k] !== (cur[p.k] || '')) body[p.k] = edit[p.k] ?? '';
      for (const s of SECRET) if (edit[s.k]) body[s.k] = edit[s.k];
      if (!Object.keys(body).length) {
        toast('काहीही बदल नाही', 'info');
        return;
      }
      await api('/api/settings', { method: 'PUT', body });
      toast('सेटिंग्ज जतन');
      await load();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }

  async function invite(e: FormEvent) {
    e.preventDefault();
    setInvBusy(true);
    try {
      await api('/api/members', { body: { email: inv.email.trim(), role: inv.role } });
      toast('आमंत्रण पाठवले');
      setInv({ email: '', role: inv.role });
      await load();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setInvBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">सेटिंग्ज</h1>

      <Section title="की व जोडण्या">
        {!cur ? (
          <SkeletonRows n={5} />
        ) : (
          <form onSubmit={save} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {PLAIN.map(p => (
                <Field key={p.k} label={p.label} hint={p.hint}>
                  <input className="input font-mono" value={edit[p.k] ?? ''} onChange={e => setEdit(s => ({ ...s, [p.k]: e.target.value }))} />
                </Field>
              ))}
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {SECRET.map(s => (
                <Field
                  key={s.k}
                  label={s.label}
                  hint={cur[s.k] ? <>सध्या: <span className="font-mono">{cur[s.k]}</span> — बदलायची असल्यासच टाइप करा</> : <Chip tone="amber">भरलेली नाही</Chip>}
                >
                  <input className="input font-mono" type="password" autoComplete="off" placeholder={cur[s.k] || ''} value={edit[s.k] ?? ''} onChange={e => setEdit(x => ({ ...x, [s.k]: e.target.value }))} />
                </Field>
              ))}
            </div>
            <button className="btn-primary" disabled={busy}>{busy && <Spinner />} जतन करा</button>
          </form>
        )}
      </Section>

      <Section title="सदस्य">
        {!members ? (
          <SkeletonRows n={2} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px]">
              <thead>
                <tr className="border-b border-slate-200 dark:border-navy-800"><th className="th">ई-मेल</th><th className="th">भूमिका</th><th className="th">दिनांक</th></tr>
              </thead>
              <tbody>
                {members.map(m => (
                  <tr key={m.user_id} className="border-b border-slate-100 dark:border-navy-800/60">
                    <td className="td break-all">{m.email}</td>
                    <td className="td"><Chip tone={m.role === 'owner' ? 'navy' : m.role === 'staff' ? 'blue' : 'slate'}>{ROLE_LABEL[m.role] || m.role}</Chip></td>
                    <td className="td">{fmtDate(m.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <form onSubmit={invite} className="mt-4 grid gap-3 md:grid-cols-[1fr_220px_auto] md:items-end">
          <Field label="नवीन सदस्याचा ई-मेल">
            <input className="input" type="email" required value={inv.email} onChange={e => setInv(s => ({ ...s, email: e.target.value }))} />
          </Field>
          <Field label="भूमिका">
            <select className="input" value={inv.role} onChange={e => setInv(s => ({ ...s, role: e.target.value }))}>
              <option value="staff">{ROLE_LABEL.staff}</option>
              <option value="senior">{ROLE_LABEL.senior}</option>
            </select>
          </Field>
          <button className="btn-primary" disabled={invBusy}>{invBusy && <Spinner />} आमंत्रण पाठवा</button>
        </form>
      </Section>

      <Section title="टिप्पणीतील सही-साखळी, पत्राचे पत्ते, सूचना">
        <p className="text-slate-600 dark:text-slate-300">या सेटिंग्ज अजून उपलब्ध नाहीत. सध्या सही-साखळी व पत्राचा मजकूर रेपोतील नियमांनुसार (INSTRUCTIONS.md §4) back-end ठरवते.</p>
      </Section>
    </div>
  );
}
