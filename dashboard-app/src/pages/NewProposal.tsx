import { useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, humanError, uploadFile } from '../lib/api';
import { useCanWrite } from '../lib/auth';
import { CATEGORIES, PRIORITIES } from '../lib/constants';
import { fmtBytes } from '../lib/format';
import { guessSubject } from '../lib/pdf';
import type { Case, Run } from '../lib/types';
import { Field, Progress, Section, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import RunProgress, { useRuns } from '../components/RunProgress';

const MAX = 50 * 1024 * 1024;
interface Up { file: File; kind: 'proposal' | 'extra_doc'; pct: number; state: 'wait' | 'up' | 'ok' | 'err'; err?: string }

function DropZone({ label, hint, accept, multiple, onFiles }: { label: string; hint: string; accept: string; multiple?: boolean; onFiles: (f: File[]) => void }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const drop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    onFiles(Array.from(e.dataTransfer.files));
  };
  return (
    <div
      onDragOver={e => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
      className={`flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-4 text-center transition ${
        over ? 'border-saffron-500 bg-saffron-500/10' : 'border-slate-300 dark:border-navy-700'
      }`}
    >
      <div className="font-semibold">{label}</div>
      <div className="text-sm text-slate-500 dark:text-slate-400">{hint}</div>
      <button type="button" className="btn-ghost" onClick={() => ref.current?.click()}>फाइल निवडा</button>
      <input ref={ref} type="file" hidden accept={accept} multiple={multiple} onChange={e => { onFiles(Array.from(e.target.files || [])); e.target.value = ''; }} />
    </div>
  );
}

export default function NewProposal() {
  const canWrite = useCanWrite();
  const toast = useToast();
  const [proposal, setProposal] = useState<File | null>(null);
  const [extras, setExtras] = useState<File[]>([]);
  const [f, setF] = useState({ cr_no: '', cr_year: String(new Date().getFullYear()), file_no: '', subject: '', category: 'इतर', priority: 'सामान्य', instructions: '' });
  const [busy, setBusy] = useState(false);
  const [ups, setUps] = useState<Up[]>([]);
  const [created, setCreated] = useState<Case | null>(null);
  const [runErr, setRunErr] = useState('');
  const runs = useRuns(created?.id ?? null);
  const run: Run | undefined = runs?.[0];
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));

  if (!canWrite) return <div className="card p-6 text-center">आपल्याला फक्त वाचण्याची परवानगी आहे.</div>;

  async function pickProposal(files: File[]) {
    const p = files.find(x => x.type === 'application/pdf' || /\.pdf$/i.test(x.name));
    if (!p) return toast('प्रस्ताव PDF असावा', 'err');
    if (p.size > MAX) return toast('फाइल 50 MB पेक्षा मोठी', 'err');
    setProposal(p);
    if (!f.subject) {
      const s = await guessSubject(p);
      if (s) {
        setF(x => (x.subject ? x : { ...x, subject: s }));
        toast('विषय PDF मधून भरला — तपासा', 'info');
      }
    }
  }
  function addExtras(files: File[]) {
    const ok = files.filter(x => x.size <= MAX);
    if (ok.length < files.length) toast('50 MB पेक्षा मोठ्या फाइल वगळल्या', 'err');
    setExtras(s => [...s, ...ok]);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!proposal) return toast('प्रस्ताव PDF निवडा', 'err');
    setBusy(true);
    setRunErr('');
    try {
      let c = created;
      if (!c) {
        c = await api<Case>('/api/cases', {
          body: { cr_no: f.cr_no.trim(), cr_year: Number(f.cr_year), file_no: f.file_no.trim(), subject: f.subject.trim(), category: f.category, priority: f.priority },
        });
        setCreated(c);
      }
      const list: Up[] = [{ file: proposal, kind: 'proposal', pct: 0, state: 'wait' }, ...extras.map(x => ({ file: x, kind: 'extra_doc' as const, pct: 0, state: 'wait' as const }))];
      const prev = ups;
      setUps(list.map((u, i) => (prev[i]?.state === 'ok' && prev[i].file === u.file ? prev[i] : u)));
      for (let i = 0; i < list.length; i++) {
        if (prev[i]?.state === 'ok' && prev[i].file === list[i].file) continue; // retry skips finished files
        setUps(s => s.map((u, j) => (j === i ? { ...u, state: 'up' } : u)));
        try {
          await uploadFile(c.id, list[i].kind, list[i].file, pct => setUps(s => s.map((u, j) => (j === i ? { ...u, pct } : u))));
          setUps(s => s.map((u, j) => (j === i ? { ...u, pct: 100, state: 'ok' } : u)));
        } catch (x) {
          setUps(s => s.map((u, j) => (j === i ? { ...u, state: 'err', err: humanError(x) } : u)));
          throw x;
        }
      }
      try {
        await api('/api/run', { body: { case_id: c.id, instructions: f.instructions.trim() || undefined } });
        toast('अभ्यास सुरू झाला');
      } catch (x) {
        setRunErr(humanError(x));
      }
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }

  const locked = !!created;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">नवीन प्रस्ताव</h1>
      <form onSubmit={submit} className="grid gap-5 lg:grid-cols-2">
        <Section title="फाइल">
          <div className="space-y-4">
            {proposal ? (
              <div className="flex items-center justify-between gap-2 rounded-lg bg-navy-50 px-3 py-2 dark:bg-navy-800">
                <div className="min-w-0">
                  <div className="truncate font-semibold" title={proposal.name}>📄 {proposal.name}</div>
                  <div className="text-sm text-slate-500">{fmtBytes(proposal.size)}</div>
                </div>
                {!locked && <button type="button" className="btn-ghost min-w-tap px-2" onClick={() => setProposal(null)} aria-label="काढा">✕</button>}
              </div>
            ) : (
              <DropZone label="प्रस्ताव PDF येथे ओढा" hint="एकच PDF • कमाल 50 MB • फाइलनाव जसेच्या तसे राहील" accept="application/pdf,.pdf" onFiles={pickProposal} />
            )}
            <DropZone label="इतर कागदपत्रे (ऐच्छिक)" hint="PDF / Word / प्रतिमा" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" multiple onFiles={addExtras} />
            {extras.length > 0 && (
              <ul className="space-y-1">
                {extras.map((x, i) => (
                  <li key={i} className="flex items-center justify-between gap-2 rounded-lg bg-slate-100 px-3 py-1 dark:bg-navy-800">
                    <span className="truncate" title={x.name}>{x.name} <span className="text-sm text-slate-500">({fmtBytes(x.size)})</span></span>
                    {!busy && <button type="button" className="btn-ghost min-w-tap px-2" onClick={() => setExtras(s => s.filter((_, j) => j !== i))} aria-label="काढा">✕</button>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Section>

        <Section title="तपशील">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field label="C R क्र. *"><input className="input" inputMode="numeric" pattern="\d+" required disabled={locked} value={f.cr_no} onChange={set('cr_no')} /></Field>
              <Field label="वर्ष *"><input className="input" inputMode="numeric" pattern="\d{4}" required disabled={locked} value={f.cr_year} onChange={set('cr_year')} /></Field>
            </div>
            <Field label="नस्ती क्र. (निर्देशपत्र)"><input className="input" placeholder="संकीर्ण-2026/___/प्र.क्र.___/का.6" disabled={locked} value={f.file_no} onChange={set('file_no')} /></Field>
            <Field label="विषय *"><textarea className="input min-h-[88px]" required disabled={locked} value={f.subject} onChange={set('subject')} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="प्रवर्ग">
                <select className="input" disabled={locked} value={f.category} onChange={set('category')}>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
              </Field>
              <Field label="प्राधान्य">
                <select className="input" disabled={locked} value={f.priority} onChange={set('priority')}>{PRIORITIES.map(c => <option key={c}>{c}</option>)}</select>
              </Field>
            </div>
            <Field label="विशेष सूचना (ऐच्छिक)"><textarea className="input min-h-[72px]" value={f.instructions} onChange={set('instructions')} /></Field>
            <button className="btn-accent w-full text-lg" disabled={busy || !proposal || (!!run && run.state !== 'failed')}>
              {busy && <Spinner />} {created ? 'पुन्हा प्रयत्न करा' : 'अभ्यास सुरू करा'}
            </button>
          </div>
        </Section>
      </form>

      {ups.length > 0 && (
        <Section title="अपलोड">
          <ul className="space-y-3">
            {ups.map((u, i) => (
              <li key={i} className="space-y-1">
                <div className="flex justify-between gap-2 text-sm">
                  <span className="truncate">{u.file.name}</span>
                  <span className={u.state === 'err' ? 'text-red-700' : u.state === 'ok' ? 'text-green-700 dark:text-green-400' : ''}>
                    {u.state === 'ok' ? '✓ पूर्ण' : u.state === 'err' ? u.err : u.state === 'up' ? `${u.pct}%` : 'प्रतीक्षा'}
                  </span>
                </div>
                <Progress pct={u.pct} tone={u.state === 'err' ? 'red' : u.state === 'ok' ? 'green' : 'blue'} />
              </li>
            ))}
          </ul>
        </Section>
      )}

      {created && (
        <Section title={`प्रगती — C R ${created.cr_no}/${created.cr_year}`} right={<Link className="btn-ghost" to={`/cases/${created.id}`}>प्रकरण उघडा →</Link>}>
          {runErr && <div className="mb-3 rounded-lg bg-red-100 px-3 py-2 text-red-900 dark:bg-red-900/40 dark:text-red-100" role="alert">अभ्यास सुरू झाला नाही: {runErr}</div>}
          {run ? <RunProgress run={run} /> : !runErr && <div className="text-slate-500">{busy ? 'अपलोड चालू…' : 'प्रतीक्षा…'}</div>}
        </Section>
      )}
    </div>
  );
}
