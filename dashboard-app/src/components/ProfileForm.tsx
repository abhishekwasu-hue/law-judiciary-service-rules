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
  const set = (k: keyof Profile) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value.slice(0, MAX) }));

  async function save(e: FormEvent) {
    e.preventDefault();
    setErr('');
    if (!f.display_name.trim()) return setErr('नाव भरा');
    setBusy(true);
    try {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v.trim()])) as unknown as Profile;
      const m = await saveProfile(body);
      setMe(m);
      toast('माहिती जतन केली');
      onDone?.();
    } catch (x) {
      setErr(humanError(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
      {!p && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100 sm:col-span-2" role="status">
          सर्व्हर अद्ययावत नाही — माहिती जतन करता येणार नाही (Worker deploy बाकी)
        </div>
      )}
      <Field label="नाव"><input className="input" maxLength={MAX} autoComplete="name" value={f.display_name} onChange={set('display_name')} /></Field>
      <Field label="पदनाम"><input className="input" maxLength={MAX} placeholder="उदा. कार्यासन अधिकारी" value={f.designation} onChange={set('designation')} /></Field>
      <Field label="कार्यालय / विभाग"><input className="input" maxLength={MAX} placeholder="उदा. विधि व न्याय विभाग" value={f.office} onChange={set('office')} /></Field>
      <Field label="आपल्याकडे असलेले स्थान (स्वल्पविराम)" hint="उदा. कार्यासन-६, माझ्याकडे">
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
