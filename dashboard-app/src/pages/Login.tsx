import { useState, type FormEvent } from 'react';
import { sb } from '../lib/supabase';
import { humanError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Field, Spinner } from '../components/ui';
import { Brand } from '../components/Layout';

export default function Login() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function send(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setErr('');
    const { error } = await sb().auth.signInWithOtp({ email: email.trim(), options: { emailRedirectTo: window.location.origin } });
    setBusy(false);
    if (error) setErr(humanError(error));
    else setSent(true);
  }
  async function verify(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr('');
    const { error } = await sb().auth.verifyOtp({ email: email.trim(), token: code.trim(), type: 'email' });
    setBusy(false);
    if (error) setErr('कोड चुकीचा किंवा मुदत संपली');
  }

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <Brand />
      <div className="card mt-6 p-5">
        <h1 className="mb-4 text-2xl font-bold">लॉगिन</h1>
        {!sent ? (
          <form onSubmit={send} className="space-y-4">
            <Field label="ई-मेल">
              <input className="input" type="email" required autoFocus value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" />
            </Field>
            <button className="btn-primary w-full" disabled={busy || !email}>
              {busy && <Spinner />} कोड पाठवा
            </button>
          </form>
        ) : (
          <form onSubmit={verify} className="space-y-4">
            <p className="text-slate-600 dark:text-slate-300">{email} वर कोड पाठवला. ई-मेलमधील कोड टाका (किंवा ई-मेलमधील लिंक उघडा).</p>
            <Field label="OTP कोड">
              <input className="input text-center font-mono text-2xl tracking-[0.4em]" inputMode="numeric" autoComplete="one-time-code" required autoFocus value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} maxLength={10} />
            </Field>
            <button className="btn-primary w-full" disabled={busy || code.length < 6}>
              {busy && <Spinner />} लॉगिन करा
            </button>
            <div className="flex justify-between">
              <button type="button" className="btn-ghost" onClick={() => { setSent(false); setCode(''); }}>ई-मेल बदला</button>
              <button type="button" className="btn-ghost" disabled={busy} onClick={() => send()}>पुन्हा पाठवा</button>
            </div>
          </form>
        )}
        {err && <div className="mt-4 rounded-lg bg-red-100 px-3 py-2 font-semibold text-red-900 dark:bg-red-900/50 dark:text-red-100" role="alert">{err}</div>}
      </div>
    </div>
  );
}

export function NotMember() {
  const { signOut, session } = useAuth();
  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <Brand />
      <div className="card mt-6 space-y-4 p-5 text-center">
        <div className="text-4xl" aria-hidden="true">🔒</div>
        <h1 className="text-xl font-bold">आपण या कक्षाचे सदस्य नाही</h1>
        <p className="text-slate-600 dark:text-slate-300">{session?.user.email} — मालकाने "सेटिंग्ज" मधून आमंत्रण द्यावे.</p>
        <button className="btn-ghost w-full" onClick={() => void signOut()}>बाहेर पडा</button>
      </div>
    </div>
  );
}
