import { useState, type FormEvent } from 'react';
import { useAuth } from '../lib/auth';
import { humanError, saveProfile } from '../lib/api';
import type { Profile } from '../lib/types';
import { Field, Spinner } from './ui';
import { useToast } from './Toast';

const MAX = 120;

/** "माझी माहिती": name / designation / office / own places — entered once here (PATCH /api/me); the नस्ती page reads it
 *  from the app (lib/nasti.ts prefillNasti) and does not ask again. */
export default function ProfileForm({ onDone, onSkip, skipLabel = 'नंतर' }: { onDone?: () => void; onSkip?: () => void; skipLabel?: string }) {
  const { me, setMe } = useAuth();
  const toast = useToast();
  const p = me?.profile;
  const [f, setF] = useState<Profile>({
    display_name: p?.display_name || '', designation: p?.designation || '', office: p?.office || '', mine: p?.mine || '',
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [nameErr, setNameErr] = useState('');
  const set = (k: keyof Profile) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value.slice(0, MAX) }));

  async function save(e: FormEvent) {
    e.preventDefault();
    setErr('');
    setNameErr('');
    if (!f.display_name.trim()) return setNameErr('कृपया नाव नमूद करावे.');
    setBusy(true);
    try {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v.trim()])) as unknown as Profile;
      const m = await saveProfile(body);
      setMe(m);
      toast('माहिती जतन केली आहे.');
      onDone?.();
    } catch (x) {
      setErr(humanError(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} noValidate className="grid gap-3 sm:grid-cols-2">
      {!p && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100 sm:col-span-2" role="status">
          ही सुविधा अजून सुरू झालेली नाही.
          {me?.role === 'owner' && <span className="mt-0.5 block text-xs">सर्व्हर अद्ययावत नाही (Worker deploy बाकी).</span>}
        </div>
      )}
      <Field label="नाव *">
        <input className="input" maxLength={MAX} autoComplete="name" required aria-invalid={!!nameErr} value={f.display_name} onChange={e => { set('display_name')(e); setNameErr(''); }} />
        {nameErr && <span className="mt-1 block font-semibold text-red-700 dark:text-red-400" role="alert">{nameErr}</span>}
      </Field>
      <Field label="पदनाम"><input className="input" maxLength={MAX} placeholder="उदा. कार्यासन अधिकारी" value={f.designation} onChange={set('designation')} /></Field>
      <Field label="कार्यालय / विभाग"><input className="input" maxLength={MAX} placeholder="उदा. विधि व न्याय विभाग" value={f.office} onChange={set('office')} /></Field>
      <Field label="नस्ती आपल्याकडे असल्याचे दाखवणारी नावे (स्वल्पविरामाने वेगळी)" hint="उदा. कार्यासन-६, माझ्याकडे">
        <input className="input" maxLength={MAX} value={f.mine} onChange={set('mine')} />
      </Field>
      {err && <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 font-semibold text-red-900 dark:border-red-800 dark:bg-red-900/30 dark:text-red-100 sm:col-span-2" role="alert">{err}</div>}
      <div className="flex justify-end gap-2 sm:col-span-2">
        {onSkip && <button type="button" className="btn-ghost min-h-tap" onClick={onSkip}>{skipLabel}</button>}
        <button className="btn-primary min-h-tap" disabled={busy || !p}>{busy && <Spinner />} जतन करा</button>
      </div>
    </form>
  );
}
