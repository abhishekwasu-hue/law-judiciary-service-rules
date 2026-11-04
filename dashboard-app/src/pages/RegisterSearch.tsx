import { useState, type FormEvent } from 'react';
import { api, humanError } from '../lib/api';
import { Empty, SkeletonRows, Spinner } from '../components/ui';

/** `title` = the file's first Markdown heading, when the Worker sends it; otherwise found in the fragments or made from the file name. */
interface Hit { path: string; frags: string[]; title?: string }
/** The Worker may answer with a Marathi reason instead of a list (e.g. search not configured). */
type SearchAnswer = Hit[] | { reason?: string; hits?: Hit[] };

/** Markdown → plain text: no #, *, `, >, table pipes or link syntax shown to the reader (R2). */
function mdPlain(s: string): string {
  return s
    .split('\n')
    .filter(l => !/^\s*\|?\s*:?-{3,}/.test(l)) // table separator rows
    .map(l => l
      .replace(/^\s{0,3}#{1,6}\s*/, '')
      .replace(/^\s*>\s?/, '')
      .replace(/^\s*[-*+]\s+/, '• ')
      .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/(\*\*|__)(.*?)\1/g, '$2')
      .replace(/(^|[^*\w])[*_]([^*_\n]+)[*_](?=[^*\w]|$)/g, '$1$2')
      .replace(/`+/g, '')
      .replace(/^\s*\|\s*|\s*\|\s*$/g, '')
      .replace(/\s*\|\s*/g, ' • '))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function hitTitle(h: Hit): string {
  if (h.title?.trim()) return mdPlain(h.title);
  for (const f of h.frags) {
    const m = /^\s{0,3}#{1,6}\s+(.+)$/m.exec(f);
    if (m) return mdPlain(m[1]);
  }
  const stem = (h.path.split('/').pop() || h.path).replace(/\.md$/i, '');
  return stem.replace(/[-_]+/g, ' ');
}

export default function RegisterSearch() {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function go(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setErr('');
    try {
      const r = await api<SearchAnswer>(`/api/search?q=${encodeURIComponent(q.trim())}`);
      if (Array.isArray(r)) setHits(r);
      else if (r?.reason) {
        setErr(humanError(new Error(r.reason)));
        setHits(null);
      } else setHits(r?.hits || []);
    } catch (x) {
      // humanError shows the Worker's Marathi `reason` when it sends one (R3)
      setErr(humanError(x));
      setHits(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">नियम-उतारे शोध</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-300">पडताळलेल्या GR / नियमांच्या उताऱ्यांत शोध</p>
      </div>
      <form onSubmit={go} className="card flex gap-2 p-3">
        <input className="input min-w-0" type="search" autoFocus placeholder="उदा. वेतननिश्चिती" value={q} onChange={e => setQ(e.target.value)} aria-label="शोध-शब्द" />
        <button className="btn-primary shrink-0" disabled={busy}>{busy ? <Spinner /> : '🔎'} शोधा</button>
      </form>
      {err && <div className="card p-3 font-semibold text-red-800 dark:text-red-300" role="alert">{err}</div>}
      {busy ? <div className="card"><SkeletonRows n={4} /></div> : hits === null ? (
        err ? null : <div className="card"><Empty icon="🔎" title="कृपया शोध-शब्द नमूद करावा" hint="निकालात नियम / GR चे नाव व संबंधित उतारा (पृष्ठ / परिच्छेदासह) दिसेल." /></div>
      ) : hits.length === 0 ? (
        <div className="card"><Empty icon="∅" title="या शब्दासाठी उतारा सापडला नाही" hint="कृपया दुसरा शब्द वापरून पाहावा." /></div>
      ) : (
        <ul className="space-y-3">
          {hits.map((h, i) => (
            <li key={i} className="card p-4">
              <div className="font-semibold text-navy-700 dark:text-navy-200">{hitTitle(h)}</div>
              <div className="break-all font-mono text-xs text-slate-400 dark:text-slate-500">{h.path}</div>
              {h.frags.map((f, j) => (
                <p key={j} className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-slate-100 p-3 text-base dark:bg-navy-950">{mdPlain(f)}</p>
              ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
