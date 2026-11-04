// सुधारणा-चॅट (docs/DRAFT_EDIT_DESIGN.md §6 + Addendum A): a chat box on the case page. One message = one edit run
// (POST /api/edit); only the asked change is made to the chosen draft and a new file version is stored. Files can be
// attached (📎 / drag-drop): uploaded first with /api/upload (kind gr / extra_doc), their ids go with the edit.
import { useEffect, useMemo, useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError, api, downloadFile, humanError, uploadFile } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  EDIT_ATTACH_ACCEPT, EDIT_ATTACH_DEFAULT, EDIT_ATTACH_KINDS, EDIT_MAX_CHARS, EDIT_MAX_FILES, EDIT_TARGETS, FILE_KIND_LABEL,
  editTargetLabel, isStale, runActive, type EditAttachKind, type EditTarget,
} from '../lib/constants';
import { cleanReason as cleanReasonLib, fmtBytes, fmtDateTime, textOf } from '../lib/format';
import type { CaseFile, EditChange, Run } from '../lib/types';
import type { CaseCtx } from '../pages/CaseDetail';
import { Chip, Modal, Spinner } from './ui';
import CasePicker from './CasePicker';
import { useToast } from './Toast';
import DocxView from './DocxView';

const MAX_BYTES = 50 * 1024 * 1024;
/** Failure reason via the lib helper (C13): the owner flag is passed for the isOwner-aware version; the older one-argument
 *  version ignores it. */
const reasonText = (s: string | null | undefined, isOwner: boolean) =>
  (cleanReasonLib as (s: string | null | undefined, isOwner?: boolean) => string)(s, isOwner);
const okExt = (name: string) => EDIT_ATTACH_ACCEPT.split(',').includes((name.match(/\.[A-Za-z0-9]+$/) || [''])[0].toLowerCase());
/** A GR-looking file name (सांकेतांक digits or "GR") → pre-select GR; else इतर कागदपत्र. */
const guessKind = (name: string): EditAttachKind => (/\d{16,20}|(^|[^a-z])gr([^a-z]|$)|शासन निर्णय/i.test(name) ? 'gr' : 'extra_doc');

interface Att { key: string; file: File; kind: EditAttachKind; pct: number | null; id?: number }

const num = (v: unknown) => {
  const n = typeof v === 'string' ? Number(v) : typeof v === 'number' ? v : NaN;
  return Number.isFinite(n) ? n : null;
};

/** The file a finished edit stored for `kind`: the first version stored after the edit was asked (latest as fallback). */
function fileOf(files: CaseFile[], kind: string, r: Run): CaseFile | undefined {
  const all = files.filter(f => f.kind === kind).sort((a, b) => (a.created_at < b.created_at ? -1 : 1));
  return all.find(f => f.created_at >= r.created_at) || all[all.length - 1];
}

function DlBtn({ f, label }: { f: CaseFile; label: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <button type="button" className="btn-ghost min-h-tap px-2 py-1 text-sm" disabled={busy} title={f.original_name}
      onClick={async () => { setBusy(true); try { await downloadFile(f.id); } catch (e) { toast(humanError(e), 'err'); } finally { setBusy(false); } }}>
      {busy ? <Spinner className="h-4 w-4" /> : '⬇'} {label}
    </button>
  );
}

function FileChip({ name, size, extra }: { name: string; size?: number; extra?: ReactNode }) {
  return (
    <span className="inline-flex min-w-0 max-w-full items-center gap-1 rounded-md bg-white/90 px-2 py-0.5 text-xs font-semibold text-slate-800 dark:bg-navy-900 dark:text-slate-100">
      <span aria-hidden="true">📎</span>
      <span className="min-w-0 truncate" title={name}>{name}</span>
      {size != null && <span className="shrink-0 font-normal text-slate-500">{fmtBytes(size)}</span>}
      {extra}
    </span>
  );
}

function Change({ c }: { c: EditChange }) {
  return (
    <li className="rounded-lg border border-slate-200 p-2 dark:border-navy-800">
      {c.where && <div className="mb-1 text-xs font-bold text-slate-600 dark:text-slate-300">{textOf(c.where)}</div>}
      {c.before ? <div className="whitespace-pre-wrap break-words rounded bg-red-100 px-2 py-1 text-sm text-red-900 line-through [overflow-wrap:anywhere] dark:bg-red-900/40 dark:text-red-100">{textOf(c.before)}</div> : null}
      {c.after ? <div className={`${c.before ? 'mt-1 ' : ''}whitespace-pre-wrap break-words rounded bg-green-100 px-2 py-1 text-sm text-green-900 [overflow-wrap:anywhere] dark:bg-green-900/40 dark:text-green-100`}>{textOf(c.after)}</div> : null}
      {!c.before && !c.after && <div className="text-sm text-slate-500">—</div>}
    </li>
  );
}

/** One edit run = the user's bubble + the answer bubble. */
function Turn({ r, ctx, names, onOpen }: { r: Run; ctx: CaseCtx; names: string[]; onOpen: (f: CaseFile) => void }) {
  const { me } = useAuth();
  const res = r.edit_result || {};
  const stale = isStale(r);
  const refused = r.state === 'done' && !!res.refused;
  const active = !stale && (r.state === 'queued' || r.state === 'running');
  const changes = Array.isArray(res.changes) ? res.changes : [];
  const attached = Array.isArray(res.attached) ? res.attached : [];
  const kinds = r.state === 'done' && !refused && Array.isArray(res.files) ? res.files.filter(k => k !== 'spec') : [];
  const cost = num(res.cost_usd ?? r.cost_usd);
  const attNames = names.length ? names : (r.edit_attachments || []).map(id => ctx.files.find(f => f.id === id)?.original_name).filter((x): x is string => !!x);
  return (
    <li className="space-y-2">
      <div className="flex justify-end">
        <div className="min-w-0 max-w-[92%] rounded-2xl rounded-br-sm bg-navy-700 px-3 py-2 text-white dark:bg-navy-600">
          <div className="mb-0.5 flex flex-wrap items-center gap-x-2 text-xs opacity-80">
            <span className="font-bold">{editTargetLabel(r.edit_target) || '—'}</span>
            <span>{fmtDateTime(r.created_at)}</span>
          </div>
          <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{r.edit_message || r.instructions || '—'}</div>
          {attNames.length > 0 && <div className="mt-1.5 flex flex-wrap gap-1">{attNames.map((n, i) => <FileChip key={i} name={n} />)}</div>}
        </div>
      </div>
      <div className="min-w-0 max-w-[96%] space-y-2 rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2 dark:bg-navy-800/70">
        <div className="flex flex-wrap items-center gap-2">
          {active ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-bold text-blue-900 dark:bg-blue-900/40 dark:text-blue-100">
              <Spinner className="h-3.5 w-3.5" /> {r.state === 'queued' ? 'प्रतीक्षेत' : 'चालू'}
            </span>
          ) : stale ? <Chip tone="red">वेळ संपली</Chip>
            : refused ? <Chip tone="amber">नाकारले</Chip>
              : r.state === 'done' ? <Chip tone="green">✓ तयार</Chip> : <Chip tone="red">अयशस्वी</Chip>}
          {active && r.step && <span className="min-w-0 break-words text-sm text-slate-600 dark:text-slate-300">{r.step}</span>}
          {me?.role === 'owner' && cost != null && <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">खर्च ${cost.toFixed(2)}</span>}
        </div>
        {refused && <div className="break-words text-sm text-amber-900 [overflow-wrap:anywhere] dark:text-amber-100">{textOf(res.refused)}</div>}
        {(r.state === 'failed' || stale) && (
          <div className="break-words text-sm text-red-900 [overflow-wrap:anywhere] dark:text-red-200">{stale ? 'वेळ संपली — कृपया सुधारणा पुन्हा पाठवावी, ही विनंती.' : reasonText(r.step, me?.role === 'owner') || 'कारण उपलब्ध नाही'}</div>
        )}
        {r.state === 'done' && !refused && (res.summary || r.summary) && <div className="break-words font-semibold [overflow-wrap:anywhere]">{res.summary || r.summary}</div>}
        {r.state === 'done' && !refused && Array.isArray(res.notes) && res.notes.map((n, i) => <div key={i} className="break-words rounded-lg bg-amber-50 px-2 py-1 text-sm text-amber-900 [overflow-wrap:anywhere] dark:bg-amber-900/30 dark:text-amber-100">ℹ️ {textOf(n)}</div>)}
        {r.state === 'done' && !refused && changes.length > 0 && (
          <ol className="space-y-1.5" aria-label={`बदल (${changes.length})`}>{changes.map((c, i) => <Change key={i} c={c} />)}</ol>
        )}
        {attached.length > 0 && (
          <ul className="space-y-0.5 text-sm">
            {attached.map((a, i) => <li key={i} className="break-words [overflow-wrap:anywhere]">📎 {textOf(a.title) || '—'}{a.pages != null && a.pages !== '' ? ` — पृ.${textOf(a.pages)}` : ''}</li>)}
          </ul>
        )}
        {kinds.length > 0 && (
          <div className="space-y-1 border-t border-slate-200 pt-2 dark:border-navy-700">
            {kinds.map(k => {
              const f = fileOf(ctx.files, k, r);
              if (!f) return null;
              return (
                <div key={k} className="flex flex-wrap items-center gap-1">
                  <span className="min-w-0 text-sm font-semibold">{FILE_KIND_LABEL[k] || k} • आवृत्ती {f.version}</span>
                  <span className="ml-auto flex gap-1">
                    {k === 'package_pdf'
                      ? <Link className="btn-ghost min-h-tap px-2 py-1 text-sm" to="?tab=pdf">नवीन आवृत्ती उघडा</Link>
                      : <button type="button" className="btn-ghost min-h-tap px-2 py-1 text-sm" onClick={() => onOpen(f)}>नवीन आवृत्ती उघडा</button>}
                    <DlBtn f={f} label="डाउनलोड" />
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </li>
  );
}

export default function EditChat({ ctx }: { ctx: CaseCtx }) {
  const toast = useToast();
  const targets = EDIT_TARGETS.filter(t => ctx.files.some(f => f.kind === t.kind));
  const [target, setTarget] = useState<EditTarget | ''>('');
  const tgt = targets.find(t => t.id === target)?.id ?? targets[0]?.id ?? '';
  const [text, setText] = useState('');
  const [atts, setAtts] = useState<Att[]>([]);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [sent, setSent] = useState<Run[]>([]); // rows returned by POST /api/edit, until Realtime brings them
  const [names, setNames] = useState<Map<number, string[]>>(new Map()); // run id → attached file names (this session)
  const [view, setView] = useState<CaseFile | null>(null);
  // Abhi 04.11.2026: the case is chosen by the user and confirmed before every message (no tokens spent on a wrong case)
  const [pick, setPick] = useState(false);
  // glow + "AI" badge until the user first uses the chat (this browser only)
  const [seen, setSeen] = useState(() => { try { return localStorage.getItem('edit_chat_seen') === '1'; } catch { return false; } });
  const markSeen = () => { if (seen) return; setSeen(true); try { localStorage.setItem('edit_chat_seen', '1'); } catch { /* storage blocked */ } };
  const [confirm, setConfirm] = useState(false);
  const [sp] = useSearchParams();
  const boxRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (sp.get('edit') === '1') boxRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [sp]);
  const fileRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const fine = useMemo(() => typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: fine)').matches, []);

  const turns = useMemo(() => {
    const m = new Map<number, Run>();
    for (const r of sent) m.set(r.id, r);
    for (const r of ctx.editRuns || []) m.set(r.id, r);
    return [...m.values()].sort((a, b) => a.id - b.id);
  }, [sent, ctx.editRuns]);
  const active = runActive(ctx.runs?.[0]) || turns.some(r => runActive(r));
  // this visit: the turns sent from this page + any still running; the rest are "मागील सुधारणा"
  const sentIds = useMemo(() => new Set(sent.map(r => r.id)), [sent]);
  const recent = turns.filter(r => sentIds.has(r.id) || runActive(r));
  const older = turns.filter(r => !(sentIds.has(r.id) || runActive(r)));

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns.length, turns[turns.length - 1]?.state]);

  // nothing produced yet (first run still going) → no panel
  if (!targets.length && !turns.length) return null;

  function addFiles(list: FileList | File[]) {
    const add: Att[] = [];
    for (const f of Array.from(list)) {
      if (!okExt(f.name)) { toast(`${f.name}: फक्त PDF / JPG / PNG / Word फाइल जोडता येते.`, 'err'); continue; }
      if (f.size > MAX_BYTES) { toast(`${f.name}: फाइल 50 MB पेक्षा मोठी आहे — कृपया लहान फाइल जोडावी.`, 'err'); continue; }
      add.push({ key: `${f.name}-${f.size}-${Math.random()}`, file: f, kind: guessKind(f.name), pct: null });
    }
    setAtts(s => {
      const n = [...s, ...add];
      if (n.length > EDIT_MAX_FILES) toast(`एका संदेशात जास्तीत जास्त ${EDIT_MAX_FILES} फाइल जोडता येतात.`, 'err');
      return n.slice(0, EDIT_MAX_FILES);
    });
    if (add.length) setText(t => (t.trim() ? t : EDIT_ATTACH_DEFAULT));
    if (add.length && targets.some(t => t.id === 'package') && !target) setTarget('package');
  }

  function ask(e?: FormEvent) {
    e?.preventDefault();
    if (!tgt || !text.trim() || busy || active) return;
    setConfirm(true);
  }
  async function send() {
    setConfirm(false);
    const message = text.trim();
    if (!tgt || !message || busy || active) return;
    if (message.length > EDIT_MAX_CHARS) return toast(`कृपया संदेश ${EDIT_MAX_CHARS} अक्षरांपेक्षा लहान लिहावा.`, 'err');
    setBusy(true);
    try {
      const ids: number[] = [];
      for (const a of atts) {
        if (a.id) { ids.push(a.id); continue; }
        setAtts(s => s.map(x => (x.key === a.key ? { ...x, pct: 0 } : x)));
        const r = await uploadFile(ctx.c.id, a.kind, a.file, p => setAtts(s => s.map(x => (x.key === a.key ? { ...x, pct: p } : x))));
        ids.push(r.id);
        // uploaded once: a retry after a refused edit does not upload it again
        setAtts(s => s.map(x => (x.key === a.key ? { ...x, id: r.id, pct: null } : x)));
      }
      const run = await api<Run>('/api/edit', { body: { case_id: ctx.c.id, target: tgt, message, ...(ids.length ? { attachments: ids } : {}) } });
      if (run && run.id) {
        setSent(s => [...s, { ...run, kind: 'edit' }]);
        if (atts.length) setNames(m => new Map(m).set(run.id, atts.map(a => a.file.name)));
      }
      setText('');
      setAtts([]);
      if (ids.length) void ctx.reloadFiles();
    } catch (x) {
      setAtts(s => s.map(a => ({ ...a, pct: null })));
      toast(humanError(x), 'err');
      if (x instanceof ApiError && x.message === 'no_spec') void ctx.reloadFiles();
    } finally {
      setBusy(false);
    }
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    // desktop: Enter sends, Shift+Enter new line; phone: Enter = new line (send button)
    if (fine && e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      ask();
    }
  }
  const dragProps = ctx.canWrite && ctx.hasSpec ? {
    onDragOver: (e: DragEvent) => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); setDrag(true); } },
    onDragLeave: (e: DragEvent) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDrag(false); },
    onDrop: (e: DragEvent) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files); },
  } : {};

  const canSend = !!tgt && !!text.trim() && !busy && !active;
  return (
    <section id="edit-chat" ref={boxRef} className={`card edit-panel relative min-w-0 scroll-mt-20 overflow-hidden ${seen ? 'seen' : ''} ${drag ? 'ring-4 ring-saffron-500' : ''}`} aria-label="सुधारणा" {...dragProps}>
      <div className="edit-head flex items-center justify-between gap-2 px-4 py-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-lg font-bold">✏️ सुधारणा-चॅट <span className={`${seen ? '' : 'blink-badge '}rounded-full bg-white px-3 py-1 text-base font-black text-orange-600 shadow`}>AI</span></h2>
          <p className="text-sm text-white/90">टिप्पणी किंवा मसुद्यात (पत्र, शासन निर्णय इ.) बदल हवा असल्यास कृपया येथे नमूद करावे</p>
        </div>
      </div>
      <div className="flex min-w-0 items-center justify-between gap-2 border-b border-slate-200 bg-navy-50 px-4 py-2 text-sm dark:border-navy-800 dark:bg-navy-800/60">
        <div className="min-w-0">
          <span className="font-semibold">प्रकरण:</span> <b>{ctx.title}</b>
          {ctx.c.subject && <div className="truncate text-slate-600 dark:text-slate-300" title={ctx.c.subject}>{ctx.c.subject}</div>}
        </div>
        <button type="button" className="btn-ghost shrink-0 px-2 text-sm" onClick={() => setPick(true)}>कृपया प्रकरण बदलावे</button>
      </div>
      <CasePicker open={pick} onClose={() => setPick(false)} />
      {drag && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-amber-50/90 text-lg font-bold text-navy-800 dark:bg-navy-900/90 dark:text-white">📎 कृपया फाइल येथे सोडावी</div>
      )}
      <div className="space-y-3 p-3">
        {/* owner 05.11.2026: earlier edits confused the chat — only this visit's messages (and a running one) are shown;
            the earlier ones stay behind "मागील सुधारणा (N)" */}
        {older.length > 0 && (
          <details className="rounded-lg border border-slate-200 dark:border-navy-800">
            <summary className="min-h-tap cursor-pointer px-3 py-2 text-sm font-semibold text-slate-600 dark:text-slate-300">मागील सुधारणा ({older.length})</summary>
            <ol className="space-y-4 p-2">
              {older.map(r => <Turn key={r.id} r={r} ctx={ctx} names={names.get(r.id) || []} onOpen={setView} />)}
            </ol>
          </details>
        )}
        {recent.length > 0 && (
          <div ref={listRef}>
            <ol className="space-y-4">
              {recent.map(r => <Turn key={r.id} r={r} ctx={ctx} names={names.get(r.id) || []} onOpen={setView} />)}
            </ol>
          </div>
        )}
        {!ctx.hasSpec ? (
          <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-navy-800 dark:text-slate-200">हे प्रकरण या सुविधेपूर्वीचे आहे. बदलासाठी कृपया 'संपूर्ण प्रकरण पुन्हा तयार करणे' हा पर्याय वापरावा, ही विनंती.</p>
        ) : !ctx.canWrite ? null : (
          <form onSubmit={ask} className="space-y-2">
            <label className="flex min-w-0 items-center gap-2 text-sm">
              <span className="shrink-0 font-semibold">कशात</span>
              <select className="input min-w-0 py-1" value={tgt} disabled={busy} onChange={e => setTarget(e.target.value as EditTarget)} aria-label="सुधारणा कशात">
                {targets.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </label>
            <label htmlFor="edit-msg" className="block text-base font-bold text-orange-700 dark:text-orange-300">✍️ कृपया येथे आपला बदल लिहावा</label>
            <div className="rounded-xl border-2 border-orange-400 bg-white shadow-sm focus-within:border-navy-500 focus-within:ring-2 focus-within:ring-navy-200 dark:border-navy-700 dark:bg-navy-900 dark:focus-within:ring-navy-700">
              {atts.length > 0 && (
                <ul className="flex flex-wrap gap-1.5 border-b border-slate-200 p-2 dark:border-navy-800">
                  {atts.map(a => (
                    <li key={a.key} className="flex min-w-0 max-w-full flex-wrap items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-xs dark:bg-navy-800">
                      <span aria-hidden="true">📎</span>
                      <span className="min-w-0 max-w-[8.5rem] truncate font-semibold sm:max-w-[11rem]" title={a.file.name}>{a.file.name}</span>
                      <span className="text-slate-500">{fmtBytes(a.file.size)}</span>
                      {a.pct !== null ? <span className="inline-flex items-center gap-1 font-semibold text-blue-800 dark:text-blue-200"><Spinner className="h-3 w-3" /> {a.pct}%</span>
                        : a.id ? <span className="font-semibold text-green-800 dark:text-green-300">✓</span> : null}
                      <select className="min-h-tap rounded border border-slate-300 bg-white px-1 py-0.5 text-xs dark:border-navy-700 dark:bg-navy-900" value={a.kind} disabled={busy || !!a.id}
                        aria-label={`${a.file.name}: प्रकार`} onChange={e => setAtts(s => s.map(x => (x.key === a.key ? { ...x, kind: e.target.value as EditAttachKind } : x)))}>
                        {EDIT_ATTACH_KINDS.map(k => <option key={k.id} value={k.id}>{k.label}</option>)}
                      </select>
                      <button type="button" className="min-h-tap min-w-tap rounded font-bold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-navy-700" disabled={busy}
                        aria-label={`${a.file.name} काढावी`} onClick={() => setAtts(s => s.filter(x => x.key !== a.key))}>✕</button>
                    </li>
                  ))}
                </ul>
              )}
              <textarea
                className="block min-h-[160px] w-full resize-y rounded-xl bg-transparent px-3 py-3 text-lg outline-none"
                placeholder="उदा. टिप्पणीच्या परि. 5 मधील शेवटची दोन वाक्ये वगळावीत; पत्रातील दिनांक 12.10.2026 असा करावा"
                value={text}
                maxLength={EDIT_MAX_CHARS}
                disabled={busy}
                onChange={e => setText(e.target.value)}
                onFocus={markSeen}
                onKeyDown={onKey}
                id="edit-msg"
                aria-label="सुधारणेचा संदेश"
              />
              <div className="flex items-center gap-2 px-2 pb-2">
                <button type="button" className="btn-ghost min-h-tap min-w-tap px-2" disabled={busy || atts.length >= EDIT_MAX_FILES} title="फाइल जोडावी (PDF / JPG / PNG / Word)" aria-label="फाइल जोडावी" onClick={() => fileRef.current?.click()}>📎</button>
                <input ref={fileRef} type="file" hidden multiple accept={EDIT_ATTACH_ACCEPT} onChange={e => { const l = e.target.files; if (l?.length) addFiles(l); e.target.value = ''; }} />
                <span className="min-w-0 truncate text-xs text-slate-500 dark:text-slate-400">{text.length > EDIT_MAX_CHARS - 200 ? `${text.length}/${EDIT_MAX_CHARS}` : fine ? 'Enter = कृपया पाठवावे • Shift+Enter = नवी ओळ' : ''}</span>
                <button className="btn-primary ml-auto" disabled={!canSend}>{busy && <Spinner />} {busy && atts.some(a => !a.id) ? 'अपलोड…' : 'कृपया पाठवावे'}</button>
              </div>
            </div>
            {confirm && (
              <div className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100" role="alertdialog" aria-label="पुष्टी">
                <div>हा बदल <b>{ctx.title}</b>{ctx.c.subject ? <> ({ctx.c.subject.length > 60 ? `${ctx.c.subject.slice(0, 60)}…` : ctx.c.subject})</> : null} च्या <b>{editTargetLabel(tgt)}</b> मध्ये करावयाचा आहे{atts.length ? ` • ${atts.length} फाइल जोडणार` : ''} — कृपया खात्री करावी.</div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-primary" onClick={() => void send()}>✓ होय, कृपया पाठवावे</button>
                  <button type="button" className="btn-ghost" onClick={() => setConfirm(false)}>✕ नाही, थांबावे</button>
                  <button type="button" className="btn-ghost" onClick={() => { setConfirm(false); setPick(true); }}>कृपया प्रकरण बदलावे</button>
                </div>
              </div>
            )}
            <p className="text-xs text-slate-500 dark:text-slate-400">आपण एका संदेशात अनेक सुधारणा नमूद करू शकता • आपण सांगितलेलाच बदल करण्यात येईल{active ? ' • प्रक्रिया चालू आहे — ती पूर्ण झाल्यावर कृपया संदेश पाठवावा' : ''}</p>
          </form>
        )}
      </div>
      <Modal open={!!view} onClose={() => setView(null)} title={view ? `${FILE_KIND_LABEL[view.kind] || ''} • आवृत्ती ${view.version}` : ''} wide>
        {view && <DocxView fileId={view.id} />}
      </Modal>
    </section>
  );
}
