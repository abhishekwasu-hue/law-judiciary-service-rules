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
  const errBox = err && <span className="mt-1 block font-semibold text-red-700 dark:text-red-400" role="alert">{err}</span>;

  async function send(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setErr('');
    const { error } = await sb().auth.signInWithOtp({ email: email.trim(), options: { emailRedirectTo: window.location.origin, shouldCreateUser: false } }); // S-F6: no account for an e-mail that was not invited
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
    if (error) setErr('कोड चुकीचा आहे किंवा त्याची मुदत संपली आहे. कृपया कोड तपासावा किंवा पुन्हा पाठवावा.');
  }

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <Brand />
      <div className="card mt-6 p-5">
        <h1 className="text-2xl font-bold">लॉगिन</h1>
        <p className="mb-4 mt-1 text-slate-600 dark:text-slate-300">कार्यासनाने आमंत्रित केलेला ई-मेल नमूद करावा. त्यावर 6 अंकी कोड येईल.</p>
        {!sent ? (
          <form onSubmit={send} className="space-y-4">
            <Field label="ई-मेल">
              <input className="input" type="email" required autoFocus value={email} aria-invalid={!!err} onChange={e => { setEmail(e.target.value); setErr(''); }} autoComplete="email" />
              {errBox}
            </Field>
            <button className="btn-primary w-full" disabled={busy || !email}>
              {busy && <Spinner />} कोड पाठवा
            </button>
          </form>
        ) : (
          <form onSubmit={verify} className="space-y-4">
            <p className="break-words text-slate-600 dark:text-slate-300"><span className="break-all font-semibold">{email}</span> वर कोड पाठविला आहे. कृपया ई-मेलमधील कोड येथे नमूद करावा (किंवा ई-मेलमधील लिंक उघडावी).</p>
            <Field label="ई-मेलवर आलेला कोड">
              <input className="input text-center font-mono text-2xl tracking-[0.4em]" inputMode="numeric" autoComplete="one-time-code" required autoFocus value={code} aria-invalid={!!err} onChange={e => { setCode(e.target.value.replace(/\D/g, '')); setErr(''); }} maxLength={10} />
              {errBox}
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
        <p className="break-words text-slate-600 dark:text-slate-300"><span className="break-all font-semibold">{session?.user.email}</span> हा ई-मेल या कक्षाचा सदस्य म्हणून नोंदलेला नाही. कृपया कार्यासनाच्या प्रमुखांकडून (मालक) आमंत्रण घ्यावे.</p>
        {/* claude.ai artifact build: sign-in is claude.ai's — no logout (E-F12) */}
        {import.meta.env.VITE_BACKEND !== 'artifact' && <button className="btn-ghost w-full" onClick={() => void signOut()}>बाहेर पडा</button>}
      </div>
    </div>
  );
}
