import { lazy, Suspense, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, api, downloadFile, humanError, runStartText, uploadFile, type RunStart } from '../lib/api';
import { ACTION_LABEL, DRAFT_KEYS, EXTRA_OUTPUT_KINDS, FIELD_LABEL, FILE_KIND_LABEL, INPUT_KINDS, INPUT_KIND_LABEL, LETTER_STATUSES, RUN_STATE_LABEL, TONE_HEX, draftsText, editTargetLabel, runActive, runTone, type DraftKey, type InputKind } from '../lib/constants';
import { sameDrafts, suggestDrafts } from '../lib/drafts';
import { CompactDraftPicker } from '../components/DraftPicker';
import { useAuth } from '../lib/auth';
import EditChat from '../components/EditChat';
import { asArray, cleanReason as cleanReasonLib, daysBetween, fmtDate, fmtDateTime, isCriticalWarning, textOf, todayISO } from '../lib/format';
import { diffLines, type DiffLine } from '../lib/diff';
import type { Activity, CaseFile, Letter, Run } from '../lib/types';
import { Chip, Empty, Field, Modal, Section, Skeleton, SkeletonRows, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import RunProgress, { OwnerRunLines, RunCost } from '../components/RunProgress';
import PdfViewer from '../components/PdfViewer';
import DocxView, { docxParagraphs } from '../components/DocxView';
import type { CaseCtx } from './CaseDetail';

// Recharts loads only with this chart (not with the case page).
const StageDaysChart = lazy(() => import('../components/Charts').then(m => ({ default: m.StageDaysChart })));

// newest upload first (created_at): `version` counts per original_name, so a corrected file under a new name is v1 (A3 audit;
// the engine also takes the newest proposal by created_at)
const ofKind = (files: CaseFile[], kind: string) =>
  files.filter(f => f.kind === kind).sort((a, b) => (a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : b.version - a.version));
const latestRun = (runs: Run[] | null) => runs?.[0];
const latestDone = (runs: Run[] | null) => runs?.find(r => r.state === 'done');
/** A सुधारणा run of the case is queued / running (the Worker refuses a full run then: run_active). */
const editBusy = (ctx: CaseCtx) => (ctx.editRuns ?? []).some(r => runActive(r));

interface GrItem { code?: string; date?: string; title?: string; pages?: unknown; page?: unknown }
const grItem = (v: unknown): GrItem => (v && typeof v === 'object' ? (v as GrItem) : { title: textOf(v) });
const firstPage = (g: GrItem): number | null => {
  const p = asArray(g.page ?? g.pages)[0];
  const n = Number(typeof p === 'string' ? p.match(/\d+/)?.[0] : p);
  return Number.isFinite(n) && n > 0 ? n : null;
};

/** Failure reason for the person looking: the lib helper decides what staff may see (C13). The helper takes the owner flag
 *  when it supports it (isOwner-aware version from the wording round); the older one-argument version ignores it. */
const reasonText = (s: string | null | undefined, isOwner: boolean) =>
  (cleanReasonLib as (s: string | null | undefined, isOwner?: boolean) => string)(s, isOwner);

export function DownloadBtn({ f, label = 'डाउनलोड', className = 'btn-ghost' }: { f: CaseFile; label?: string; className?: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      title={f.original_name}
      aria-label={`${label} — ${f.original_name}`}
      onClick={async () => {
        setBusy(true);
        try {
          await downloadFile(f.id);
        } catch (e) {
          toast(humanError(e), 'err');
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? <Spinner /> : <span aria-hidden="true">⬇</span>} {label}
    </button>
  );
}

/** C1: the three files the desk sends on — first thing in the case header, latest version of each (no-print). */
export function DownloadStrip({ ctx, after }: { ctx: CaseCtx; after?: ReactNode }) {
  const items = ([['note_letter', 'टिप्पणी व पत्र'], ['study', 'अभ्यास-फाइल'], ['package_pdf', 'GR सह प्रस्ताव (PDF)']] as const)
    .map(([k, label]) => ({ f: ofKind(ctx.files, k)[0], label }))
    .filter((x): x is { f: CaseFile; label: typeof x.label } => !!x.f);
  if (!items.length && !after) return null;
  // phone: two per row (all of it on the first screen); wider: one row
  return (
    <div className="no-print grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center" aria-label="तयार फाइल डाउनलोड">
      {items.map((x, i) => (
        <DownloadBtn key={x.f.id} f={x.f} label={x.label} className={`${i === 0 ? 'btn-primary' : 'btn-ghost'} min-w-0 px-2 leading-tight sm:px-4`} />
      ))}
      {after}
    </div>
  );
}

/** Phone width (< 768 px, same limit as DocxView's zoom). */
function useNarrow() {
  const q = '(max-width: 767px)';
  const [n, setN] = useState(() => typeof window !== 'undefined' && !!window.matchMedia?.(q).matches);
  useEffect(() => {
    const m = window.matchMedia?.(q);
    if (!m) return;
    const on = () => setN(m.matches);
    m.addEventListener?.('change', on);
    return () => m.removeEventListener?.('change', on);
  }, []);
  return n;
}

/** C8: on a phone the A4 preview is too small to read — a big download first, the preview behind a toggle. */
function DocPreview({ f }: { f: CaseFile }) {
  const narrow = useNarrow();
  const [show, setShow] = useState(false);
  if (!narrow) return <DocxView fileId={f.id} />;
  return (
    <div className="space-y-2">
      <DownloadBtn f={f} label="Word डाउनलोड" className="btn-primary w-full" />
      <p className="text-sm text-slate-600 dark:text-slate-300">लहान पडद्यावर अक्षरे लहान दिसतात — कृपया फाइल डाउनलोड करून पाहावी.</p>
      <button type="button" className="btn-ghost w-full" aria-expanded={show} onClick={() => setShow(v => !v)}>
        {show ? 'पूर्वावलोकन बंद करावे ▲' : 'पूर्वावलोकन पाहावे ▼'}
      </button>
      {show && <DocxView fileId={f.id} />}
    </div>
  );
}

/** C9: "टिप्पणी व पत्र — आवृत्ती 2 (04.11.2026)" + the file name small and grey. */
function FileHead({ name, f, children }: { name: string; f: CaseFile; children?: ReactNode }) {
  return (
    <div className="no-print mb-3 flex flex-wrap items-start gap-2">
      <div className="min-w-0 flex-1">
        <h2 className="text-lg font-bold">{name} — आवृत्ती {f.version} ({fmtDate(f.created_at)})</h2>
        <div className="truncate text-xs text-slate-500 dark:text-slate-400" title={f.original_name}>{f.original_name}</div>
      </div>
      {children}
    </div>
  );
}

/** Latest run failed or timed out (stale) → the banner itself offers "पुन्हा तयार करावे". */
const latestFailed = (ctx: CaseCtx) => {
  const r = latestRun(ctx.runs);
  return !!r && r.state !== 'done' && !runActive(r);
};

function RunBanner({ ctx }: { ctx: CaseCtx }) {
  const r = latestRun(ctx.runs);
  if (!r || r.state === 'done') return null;
  const failed = latestFailed(ctx);
  const canRetry = failed && ctx.canWrite;
  return (
    <Section title={runActive(r) ? 'टिप्पणी तयार होत आहे' : 'प्रक्रियेची स्थिती'} className="mb-4">
      <RunProgress run={r} retryHint={canRetry ? 'कृपया खालील "पुन्हा तयार करावे" हे बटण वापरावे.' : failed ? 'पुन्हा तयार करण्याची परवानगी फक्त कार्यासनाला आहे.' : undefined} />
      {canRetry && <div className="no-print mt-4 border-t border-slate-200 pt-4 dark:border-navy-800"><ReRun ctx={ctx} /></div>}
    </Section>
  );
}

/** Drafts of the last full run that recorded its choice (DRAFT_KEYS order), or null. */
function lastDrafts(ctx: CaseCtx): DraftKey[] | null {
  const r = (ctx.runs ?? []).find(x => Array.isArray(x.outputs));
  return r ? DRAFT_KEYS.filter(k => (r.outputs as string[]).includes(k)) : null;
}

/** Starts a full run (POST /api/run); `running` also covers a dispatched run whose Realtime row is not here yet (H3). */
function useStartRun(ctx: CaseCtx) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<number | null>(null);
  const r = latestRun(ctx.runs);
  const running = runActive(r) || editBusy(ctx) || (pending !== null && !(ctx.runs ?? []).some(x => x.id === pending)); // a failed or stale (> 3.5 h) latest run does not block
  const waitText = editBusy(ctx) && !runActive(r) ? 'सुधारणा चालू आहे — ती पूर्ण झाल्यावर कृपया वापरावे.' : 'प्रक्रिया चालू आहे — ती पूर्ण झाल्यावर कृपया वापरावे.';
  async function start(instructions: string, outputs: DraftKey[]): Promise<boolean> {
    setBusy(true);
    try {
      const started = await api<RunStart>('/api/run', { body: { case_id: ctx.c.id, instructions: instructions.trim() || undefined, outputs } });
      setPending(started.id);
      toast(runStartText(started, 'प्रक्रिया पुन्हा सुरू झाली'));
      return true;
    } catch (x) {
      if (x instanceof ApiError && x.message === 'run_active') setPending(Number((x.data as { run_id?: number } | undefined)?.run_id) || null);
      toast(humanError(x), 'err');
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, running, waitText, start };
}

/** C11: "संपूर्ण प्रकरण पुन्हा तयार करणे" — the drafts default to those of the last full run ("मागील वेळेप्रमाणे"), so a
 *  re-run after a reply does not silently drop the letter; compact picker, optional instruction. */
export function ReRun({ ctx, preset = '', presetDrafts }: { ctx: CaseCtx; preset?: string; presetDrafts?: DraftKey[] }) {
  const [text, setText] = useState(preset);
  const last = lastDrafts(ctx);
  const suggestion = suggestDrafts(ctx.files, ctx.runs, ctx.c.work_type);
  const base = presetDrafts ?? last ?? suggestion.keys;
  const baseNote = presetDrafts ? '' : last ? 'मागील वेळेप्रमाणे' : `सुचवलेले (${suggestion.reason})`;
  const [drafts, setDraftsRaw] = useState<DraftKey[] | null>(null);
  const chosen = drafts ?? base;
  const { busy, running, waitText, start } = useStartRun(ctx);
  if (!ctx.canWrite) return null;
  async function go(e: FormEvent) {
    e.preventDefault();
    if (await start(text, chosen)) {
      setText('');
      setDraftsRaw(null);
    }
  }
  return (
    <form onSubmit={go} className="space-y-3">
      <div>
        <CompactDraftPicker value={chosen} onChange={v => setDraftsRaw(sameDrafts(v, base) ? null : v)} disabled={busy || running} />
        {drafts === null && baseNote && <p className="text-xs text-slate-500 dark:text-slate-400">{baseNote}</p>}
      </div>
      <Field label="काय बदलावे? (ऐच्छिक)">
        <textarea className="input min-h-[64px]" placeholder="उदा. पत्रात फक्त सेवापुस्तकाची प्रत मागवावी" value={text} onChange={e => setText(e.target.value)} />
      </Field>
      <button className="btn-primary" disabled={busy || running}>{busy && <Spinner />} {running ? 'प्रक्रिया चालू…' : 'पुन्हा तयार करावे'}</button>
      {running ? <p className="text-sm text-slate-500 dark:text-slate-400">{waitText}</p>
        : ctx.hasSpec && <p className="text-sm text-slate-500 dark:text-slate-400">लहान बदलासाठी 'AI सुधारणा' पुरेशी आहे.</p>}
    </form>
  );
}

// ---------------- ब्रीफिंग ----------------
function stageDays(ctx: CaseCtx) {
  const ev = ctx.activity.filter(a => a.action === 'stage_changed').sort((a, b) => (a.at < b.at ? -1 : 1));
  const acc = new Map<string, number>();
  let t = ctx.c.created_at;
  let cur = ev.length ? String(ev[0].detail?.from ?? 'प्राप्त') : ctx.c.stage;
  for (const e of ev) {
    acc.set(cur, (acc.get(cur) || 0) + Math.max(0, daysBetween(t, e.at)));
    t = e.at;
    cur = String(e.detail?.to ?? ctx.c.stage);
  }
  acc.set(cur, (acc.get(cur) || 0) + Math.max(0, daysBetween(t, new Date().toISOString())));
  return [...acc.entries()].map(([stage, days]) => ({ stage, days }));
}

export function BriefingTab({ ctx }: { ctx: CaseCtx }) {
  const run = latestDone(ctx.runs);
  const days = useMemo(() => stageDays(ctx), [ctx]);
  if (ctx.runs === null) return <SkeletonRows n={4} />;
  const points = asArray(run?.essential_points);
  const grs = asArray(run?.grs_attached).map(grItem);
  const missing = asArray(run?.grs_missing);
  return (
    <div className="print-a4">
      <RunBanner ctx={ctx} />
      {!run ? (
        <div className="card"><Empty icon="📝" title="ब्रीफिंग अजून तयार नाही" hint="प्रक्रिया पूर्ण झाल्यावर येथे दिसेल." /></div>
      ) : (
        <div className="space-y-4">
          <div className="no-print flex justify-end"><button className="btn-ghost" onClick={() => window.print()}>🖨 वरिष्ठांसाठी प्रिंट</button></div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="card p-4 md:col-span-2">
              <div className="text-sm font-semibold text-slate-500">प्रस्ताव एका ओळीत</div>
              <p className="mt-1 whitespace-pre-wrap text-lg">{run.summary || '—'}</p>
            </div>
            <div className="card p-4">
              <div className="text-sm font-semibold text-slate-500">माहिती-मागणी पत्र</div>
              <div className="mt-2">{run.letter_needed == null ? '—' : run.letter_needed ? <Chip tone="amber">आवश्यक</Chip> : <Chip tone="green">आवश्यक नाही</Chip>}</div>
              <div className="mt-3 text-sm text-slate-500">तयार: {fmtDateTime(run.finished_at)}</div>
              <RunCost run={run} />
              <div className="mt-2"><OwnerRunLines run={run} /></div>
            </div>
          </div>
          {points.length > 0 && (
            <Section title="पत्रात मागवलेले अत्यावश्यक मुद्दे">
              <ol className="list-decimal space-y-1 pl-6">{points.map((p, i) => <li key={i}>{textOf(p)}</li>)}</ol>
            </Section>
          )}
          <Section title={`जोडलेले GR (${grs.length})`}>
            {grs.length === 0 ? <div className="text-slate-500">—</div> : (
              <ul className="divide-y divide-slate-100 dark:divide-navy-800">
                {grs.map((g, i) => (
                  <li key={i} className="py-2">
                    <div className="break-words font-semibold">{textOf(g.title) || textOf(g.code) || '—'}</div>
                    <div className="text-sm text-slate-500">{[textOf(g.code), g.date && fmtDate(textOf(g.date)), g.pages != null && `पृ. ${textOf(g.pages)}`].filter(Boolean).join(' • ')}</div>
                  </li>
                ))}
              </ul>
            )}
          </Section>
          {missing.length > 0 && (
            <Section title="न मिळालेले GR (सांकेतांक हवा)">
              <ul className="list-disc space-y-1 pl-6 text-red-800 dark:text-red-300">{missing.map((m, i) => <li key={i}>{textOf(m)}</li>)}</ul>
            </Section>
          )}
          {days.length > 0 && (
            <details className="card no-print group">
              <summary className="flex min-h-tap cursor-pointer items-center justify-between px-4 py-3 font-bold">
                टप्पानिहाय दिवस (या प्रकरणाचे) <span aria-hidden="true" className="group-open:rotate-180">▼</span>
              </summary>
              <div className="border-t border-slate-200 p-4 dark:border-navy-800">
                <Suspense fallback={<Skeleton className="h-40 w-full" />}>
                  <StageDaysChart days={days} />
                </Suspense>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------- टिप्पणी व पत्र ----------------
/** C7: optional outputs (शासन निर्णय-प्रारूप, परिच्छेदनिहाय अभिप्राय, शपथपत्र, विधानमंडळ प्रश्नाचे उत्तर) as download buttons
 *  right under the noting: latest version of each kind, "पाहा" opens it. */
function ExtraOutputs({ ctx }: { ctx: CaseCtx }) {
  const items = EXTRA_OUTPUT_KINDS.map(k => ofKind(ctx.files, k)[0]).filter((f): f is CaseFile => !!f);
  // made by the latest finished run = stored after that run started; older ones are labelled (they may be stale)
  const last = latestDone(ctx.runs);
  const since = last ? last.started_at || last.created_at : null;
  const current = (f: CaseFile) => !!since && f.created_at >= since;
  const [view, setView] = useState<CaseFile | null>(null);
  if (items.length === 0) return null;
  return (
    <section className="card p-3" aria-label="इतर मसुदे">
      <h2 className="mb-2 text-base font-bold">इतर मसुदे</h2>
      <ul className="space-y-2">
        {items.map(f => (
          <li key={f.id} className="flex flex-wrap items-center gap-2">
            <DownloadBtn f={f} label={FILE_KIND_LABEL[f.kind]} className="btn-ghost min-w-0 flex-1 justify-start" />
            <button type="button" className="btn-ghost" aria-label={`${FILE_KIND_LABEL[f.kind]} — पाहा`} onClick={() => setView(f)}>पाहा</button>
            {!current(f) && <Chip tone="amber">मागील प्रक्रियेतील</Chip>}
          </li>
        ))}
      </ul>
      <Modal open={!!view} onClose={() => setView(null)} title={view ? `${FILE_KIND_LABEL[view.kind]} — आवृत्ती ${view.version}` : ''} wide>
        {view && <DocxView fileId={view.id} />}
      </Modal>
    </section>
  );
}

export function NoteTab({ ctx }: { ctx: CaseCtx }) {
  const versions = ofKind(ctx.files, 'note_letter');
  const [selId, setSelId] = useState<number | null>(null);
  const [diff, setDiff] = useState<DiffLine[] | null>(null);
  const [diffBusy, setDiffBusy] = useState(false);
  const toast = useToast();
  const sel = versions.find(v => v.id === selId) || versions[0];
  const run = latestDone(ctx.runs);
  const points = asArray(run?.essential_points);
  const prev = sel ? versions[versions.findIndex(v => v.id === sel.id) + 1] : undefined; // the one stored before (list is newest first)

  async function showDiff() {
    if (!sel || !prev) return;
    setDiffBusy(true);
    try {
      const [a, b] = await Promise.all([docxParagraphs(prev.id), docxParagraphs(sel.id)]);
      setDiff(diffLines(a, b));
    } catch (e) {
      toast(humanError(e), 'err');
    } finally {
      setDiffBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <RunBanner ctx={ctx} />
      <div className="grid gap-4 lg:grid-cols-[1fr_360px] xl:grid-cols-[1fr_400px]">
        <div className="min-w-0 space-y-4">
          <div className="card min-w-0 p-3">
            {!sel ? <Empty icon="📄" title="टिप्पणी अजून तयार नाही" hint="प्रक्रिया पूर्ण झाल्यावर येथे दिसेल." /> : (
              <>
                <FileHead name="टिप्पणी व पत्र" f={sel}>
                  <div className="flex flex-wrap gap-2">
                    {prev && <button className="btn-ghost" disabled={diffBusy} onClick={() => void showDiff()}>{diffBusy && <Spinner />} मागील आवृत्तीशी फरक</button>}
                    <span className="hidden md:inline-flex"><DownloadBtn f={sel} label="Word डाउनलोड" /></span>
                  </div>
                </FileHead>
                <DocPreview f={sel} />
              </>
            )}
          </div>
          <ExtraOutputs ctx={ctx} />
        </div>
        <div className="min-w-0 space-y-4">
          <EditChat ctx={ctx} />
          {run?.letter_needed && points.length > 0 && (
            <Section title="पत्रातील अत्यावश्यक मुद्दे">
              <ol className="list-decimal space-y-1 pl-6">{points.map((p, i) => <li key={i}>{textOf(p)}</li>)}</ol>
            </Section>
          )}
          {versions.length > 1 && (
            <details className="card group">
              <summary className="flex min-h-tap cursor-pointer items-center justify-between px-4 py-3 font-bold">
                मागील आवृत्त्या ({versions.length - 1}) <span aria-hidden="true" className="group-open:rotate-180">▼</span>
              </summary>
              <ul className="space-y-1 border-t border-slate-200 p-3 dark:border-navy-800">
                {versions.map(v => (
                  <li key={v.id}>
                    <button className={`min-h-tap w-full rounded-lg px-3 py-1 text-left ${sel?.id === v.id ? 'bg-navy-100 font-semibold dark:bg-navy-800' : 'hover:bg-slate-100 dark:hover:bg-navy-800/60'}`} aria-current={sel?.id === v.id} onClick={() => { setSelId(v.id); setDiff(null); }}>
                      आवृत्ती {v.version}{v.id === versions[0].id ? ' (नवीनतम)' : ''} <span className="text-sm text-slate-500">• {fmtDateTime(v.created_at)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {ctx.canWrite && !latestFailed(ctx) && <Section title="संपूर्ण प्रकरण पुन्हा तयार करणे"><ReRun ctx={ctx} /></Section>}
        </div>
      </div>
      <Modal open={!!diff} onClose={() => setDiff(null)} title={`फरक: आवृत्ती ${prev?.version} → ${sel?.version}`} wide>
        <div className="mb-2 flex gap-2 text-sm"><Chip tone="green">+ नवीन</Chip><Chip tone="red">− काढलेले</Chip></div>
        {diff && diff.every(d => d.t === 'same') && <div className="text-slate-500">मजकुरात फरक नाही.</div>}
        <div className="space-y-1">
          {diff?.filter(d => d.t !== 'same').map((d, i) => (
            <div key={i} className={`rounded px-2 py-1 ${d.t === 'add' ? 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-100' : 'bg-red-100 text-red-900 line-through dark:bg-red-900/40 dark:text-red-100'}`}>{d.t === 'add' ? '+ ' : '− '}{d.s}</div>
          ))}
        </div>
      </Modal>
    </div>
  );
}

// ---------------- GR सह प्रस्ताव (PDF) ----------------
export function PackageTab({ ctx }: { ctx: CaseCtx }) {
  const toast = useToast();
  const pkg = ofKind(ctx.files, 'package_pdf')[0];
  const proposal = ofKind(ctx.files, 'proposal')[0];
  const [which, setWhich] = useState<'pkg' | 'orig'>('pkg');
  const shown = which === 'orig' && proposal ? proposal : pkg || proposal;
  const isPkg = !!pkg && shown?.id === pkg.id;
  const [jump, setJump] = useState<{ page: number; at: number } | undefined>();
  const grs = asArray(latestDone(ctx.runs)?.grs_attached).map(grItem);
  const inputs = ctx.files.filter(f => (INPUT_KINDS as readonly string[]).includes(f.kind));
  const multiProposal = ctx.files.filter(f => f.kind === 'proposal').length > 1;

  async function openGr(code: string) {
    const w = window.open('', '_blank');
    try {
      const { url } = await api<{ url: string }>(`/api/gr/${code}`);
      if (w) w.location.href = url;
      else window.location.href = url;
    } catch (e) {
      w?.close();
      toast(humanError(e), 'err');
    }
  }

  return (
    <div className="space-y-4">
      <RunBanner ctx={ctx} />
      <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
        <div className="card min-w-0 p-3">
          {!shown ? <Empty icon="📄" title="PDF उपलब्ध नाही" hint="कृपया प्रस्ताव अपलोड करावा." /> : (
            <>
              {pkg && proposal && (
                <div className="no-print mb-3 grid grid-cols-2 gap-1" role="group" aria-label="कोणती PDF दाखवावी">
                  {([['pkg', 'GR सह प्रस्ताव (PDF)'], ['orig', 'मूळ प्रस्ताव']] as const).map(([k, l]) => (
                    <button key={k} type="button" aria-pressed={(k === 'pkg') === isPkg} onClick={() => setWhich(k)}
                      className={`min-h-tap rounded-lg px-2 font-semibold ${(k === 'pkg') === isPkg ? 'bg-navy-700 text-white dark:bg-navy-500' : 'bg-slate-100 text-slate-700 dark:bg-navy-800 dark:text-slate-200'}`}>{l}</button>
                  ))}
                </div>
              )}
              <div className="mb-3 flex flex-wrap items-start gap-2">
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg font-bold">{isPkg ? 'GR सह प्रस्ताव (PDF) — परत पाठवायची' : 'मूळ प्रस्ताव'}</h2>
                  <div className="truncate text-xs text-slate-500 dark:text-slate-400" title={shown.original_name}>{shown.original_name} • {fmtDate(shown.created_at)}</div>
                  {!pkg && <div className="mt-1"><Chip tone="amber">GR सह प्रस्ताव (PDF) अजून तयार नाही</Chip></div>}
                </div>
                <DownloadBtn f={shown} label="PDF डाउनलोड" />
              </div>
              <PdfViewer fileId={shown.id} jumpTo={isPkg ? jump : undefined} />
            </>
          )}
        </div>
        <div className="space-y-4">
          <Section title={`जोडलेले GR (${grs.length})`}>
            {grs.length === 0 ? <div className="text-slate-500">—</div> : (
              <ul className="space-y-2">
                {grs.map((g, i) => {
                  const p = firstPage(g);
                  const code = /^\d{16,20}$/.test(textOf(g.code)) ? textOf(g.code) : '';
                  return (
                    <li key={i} className="rounded-lg border border-slate-200 p-2 dark:border-navy-800">
                      <div className="break-words text-sm font-semibold">{textOf(g.title) || textOf(g.code) || '—'}</div>
                      <div className="text-xs text-slate-500">{[textOf(g.code), g.date && fmtDate(textOf(g.date))].filter(Boolean).join(' • ')}</div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {p && pkg && <button className="btn-ghost min-h-tap px-2 py-1 text-sm" onClick={() => { setWhich('pkg'); setJump({ page: p, at: Date.now() }); }}>पृ. {p} वर जा</button>}
                        {code && <button className="btn-ghost min-h-tap px-2 py-1 text-sm" onClick={() => void openGr(code)}>मूळ GR</button>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </Section>
          <Section title="मूळ कागदपत्रे">
            {ctx.canWrite && <AddFile ctx={ctx} />}
            <ul className="space-y-2">
              {inputs.map(f => (
                <li key={f.id} className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold" title={f.original_name}>{f.original_name}</div>
                    <div className="text-xs text-slate-500">{FILE_KIND_LABEL[f.kind]} • आवृत्ती {f.version} • {fmtDateTime(f.created_at)}{multiProposal && proposal?.id === f.id ? ' • प्रक्रियेसाठी वापरला जाणारा (नवीनतम)' : ''}</div>
                  </div>
                  <DownloadBtn f={f} label="डाउनलोड" className="btn-ghost shrink-0 px-3" />
                </li>
              ))}
            </ul>
          </Section>
        </div>
      </div>
    </div>
  );
}

/** "फाइल जोडा" on a case: type selector (प्रस्ताव / उत्तर / मान्यता / न्यायालयीन नोटीस / इतर) + file picker (C28). */
function AddFile({ ctx }: { ctx: CaseCtx }) {
  const toast = useToast();
  const [kind, setKind] = useState<InputKind>('extra_doc');
  const [pct, setPct] = useState<number | null>(null);
  const ref = useRef<HTMLInputElement>(null);
  async function up(file: File) {
    if (file.size > 50 * 1024 * 1024) return toast('फाइल 50 MB पेक्षा मोठी आहे — कृपया लहान फाइल जोडावी.', 'err');
    setPct(0);
    try {
      await uploadFile(ctx.c.id, kind, file, setPct);
      toast(`${INPUT_KIND_LABEL[kind]} अपलोड झाले. मसुदे हवे असल्यास कृपया "पुन्हा तयार करावे" वापरावे.`);
      await Promise.all([ctx.reloadFiles(), ctx.reloadLetters(), ctx.reloadActivity()]);
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setPct(null);
    }
  }
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3 dark:border-navy-800">
      <label className="flex min-w-0 flex-1 items-center gap-2 text-sm">
        <span className="shrink-0 font-semibold">प्रकार</span>
        <select className="input min-w-0 py-1" value={kind} disabled={pct !== null} onChange={e => setKind(e.target.value as InputKind)}>
          {INPUT_KINDS.map(k => <option key={k} value={k}>{INPUT_KIND_LABEL[k]}</option>)}
        </select>
      </label>
      <button type="button" className="btn-ghost" disabled={pct !== null} onClick={() => ref.current?.click()}>
        {pct !== null ? <><Spinner /> {pct}%</> : '⬆ फाइल जोडा'}
      </button>
      <input ref={ref} type="file" hidden accept={kind === 'proposal' ? 'application/pdf,.pdf' : '.pdf,.doc,.docx,.jpg,.jpeg,.png'} onChange={e => { const x = e.target.files?.[0]; e.target.value = ''; if (x) void up(x); }} />
    </div>
  );
}

// ---------------- अभ्यास-फाइल ----------------
export function StudyTab({ ctx }: { ctx: CaseCtx }) {
  const s = ofKind(ctx.files, 'study')[0];
  return (
    <div>
      <RunBanner ctx={ctx} />
      <div className="card p-3">
        {!s ? <Empty icon="📘" title="अभ्यास-फाइल अजून तयार नाही" hint="प्रक्रिया पूर्ण झाल्यावर येथे दिसेल." /> : (
          <>
            <FileHead name="अभ्यास-फाइल" f={s}>
              <span className="hidden md:inline-flex"><DownloadBtn f={s} label="Word डाउनलोड" /></span>
            </FileHead>
            <DocPreview f={s} />
          </>
        )}
      </div>
    </div>
  );
}

// ---------------- पत्रव्यवहार ----------------
function letterTone(l: Letter) {
  if (l.reply_received_date || l.status === 'उत्तर प्राप्त') return 'green' as const;
  if (l.reply_due && l.reply_due < todayISO()) return 'red' as const;
  if (l.sent_date) return 'amber' as const;
  return 'slate' as const;
}

/** स्मरणपत्र-N: 1 + the full runs asked for a reminder since this letter was recorded. */
function reminderNo(ctx: CaseCtx, l: Letter) {
  return 1 + (ctx.runs ?? []).filter(r => Array.isArray(r.outputs) && r.outputs.includes('reminder') && r.created_at >= l.created_at).length;
}

const letterLine = (l: Letter) => [
  l.ref_no ? `पत्र क्र. ${l.ref_no}` : 'पत्र',
  l.sent_date && `दि. ${fmtDate(l.sent_date)}`,
  l.addressed_to && `(${l.addressed_to})`,
].filter(Boolean).join(', ');

/** C20: one line on the letter + one primary button; other drafts / an instruction only behind a toggle. */
function ReminderForm({ ctx, l, onDone }: { ctx: CaseCtx; l: Letter; onDone: () => void }) {
  const n = reminderNo(ctx, l);
  const preset = `${letterLine(l)} याचे उत्तर अप्राप्त — स्मरणपत्र-${n} चा मसुदा तयार करावा.`;
  const [more, setMore] = useState(false);
  const { busy, running, waitText, start } = useStartRun(ctx);
  return (
    <div className="space-y-3">
      <p className="break-words [overflow-wrap:anywhere]">
        {letterLine(l)} — उत्तर अप्राप्त{l.reply_due ? ` (उत्तराची मुदत ${fmtDate(l.reply_due)})` : ''}.
      </p>
      <button type="button" className="btn-primary w-full sm:w-auto" disabled={busy || running} onClick={async () => { if (await start(preset, ['reminder'])) onDone(); }}>
        {busy && <Spinner />} होय, स्मरणपत्र-{n} चा मसुदा तयार करावा
      </button>
      {running && <p className="text-sm text-slate-500 dark:text-slate-400">{waitText}</p>}
      <button type="button" className="flex min-h-tap items-center gap-1 font-semibold text-navy-700 underline dark:text-navy-200" aria-expanded={more} onClick={() => setMore(v => !v)}>
        इतर मसुदे / सूचना {more ? '▲' : '▼'}
      </button>
      {more && <div className="border-t border-slate-200 pt-3 dark:border-navy-800"><ReRun ctx={ctx} presetDrafts={['reminder']} preset={preset} /></div>}
    </div>
  );
}

/** C18: one reply flow per letter — date (today) + the reply file (optional), then the re-run offer. */
function ReplyForm({ ctx, l, onDone }: { ctx: CaseCtx; l: Letter; onDone: (withFile: boolean) => void }) {
  const toast = useToast();
  const [date, setDate] = useState(todayISO());
  const [file, setFile] = useState<File | null>(null);
  const [pct, setPct] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  async function save(e: FormEvent) {
    e.preventDefault();
    if (file && file.size > 50 * 1024 * 1024) return toast('फाइल 50 MB पेक्षा मोठी आहे — कृपया लहान फाइल जोडावी.', 'err');
    setBusy(true);
    try {
      if (file) {
        setPct(0);
        await uploadFile(ctx.c.id, 'reply', file, setPct);
      }
      await api(`/api/letters/${l.id}`, { method: 'PATCH', body: { reply_received_date: date || todayISO(), status: 'उत्तर प्राप्त' } });
      toast('उत्तर प्राप्त झाल्याची नोंद केली');
      await Promise.all([ctx.reloadFiles(), ctx.reloadLetters(), ctx.reloadActivity()]);
      onDone(!!file);
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
      setPct(null);
    }
  }
  return (
    <form onSubmit={save} className="space-y-3">
      <p className="break-words [overflow-wrap:anywhere]">{letterLine(l)}</p>
      <Field label="उत्तर प्राप्त दिनांक"><input className="input" type="date" value={date} onChange={e => setDate(e.target.value)} /></Field>
      <div>
        <span className="label">उत्तराची फाइल (ऐच्छिक)</span>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-ghost" disabled={busy} onClick={() => ref.current?.click()}>⬆ फाइल जोडावी</button>
          {file && <span className="min-w-0 break-words text-sm [overflow-wrap:anywhere]">{file.name} <button type="button" className="ml-1 min-h-tap min-w-tap font-bold text-slate-600 dark:text-slate-300" aria-label={`${file.name} काढावी`} onClick={() => setFile(null)}>✕</button></span>}
        </div>
        <input ref={ref} type="file" hidden accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={e => { const x = e.target.files?.[0]; e.target.value = ''; if (x) setFile(x); }} />
      </div>
      <div className="flex justify-end gap-2">
        <button className="btn-primary" disabled={busy}>{busy && <Spinner />} {pct !== null ? `${pct}%` : 'जतन करा'}</button>
      </div>
    </form>
  );
}

export function LettersTab({ ctx }: { ctx: CaseCtx }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const blank = () => ({ ref_no: ctx.c.file_no || '', addressed_to: ctx.c.received_from || '', sent_date: todayISO(), reply_due: '', status: 'पाठवले' });
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [upPct, setUpPct] = useState<number | null>(null);
  const [offerRerun, setOfferRerun] = useState(false);
  const [reminderFor, setReminderFor] = useState<Letter | null>(null);
  const [replyFor, setReplyFor] = useState<Letter | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));
  const replies = ofKind(ctx.files, 'reply');
  const busyRun = runActive(latestRun(ctx.runs)) || editBusy(ctx);
  const pendingLetters = ctx.letters.some(l => !l.reply_received_date && l.status !== 'उत्तर प्राप्त');

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api('/api/letters', { body: { case_id: ctx.c.id, ...f } });
      toast('पत्राची नोंद केली');
      setOpen(false);
      await ctx.reloadLetters();
      await ctx.reloadActivity();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }
  // a reply with no recorded letter (only when no letter is waiting for one — otherwise the per-letter flow is used)
  async function uploadReply(file: File) {
    setUpPct(0);
    try {
      await uploadFile(ctx.c.id, 'reply', file, setUpPct);
      toast('उत्तराची फाइल जोडली; टप्पा "माहिती प्राप्त"');
      setOfferRerun(true);
      await Promise.all([ctx.reloadFiles(), ctx.reloadLetters(), ctx.reloadActivity()]);
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setUpPct(null);
    }
  }

  return (
    <div className="space-y-4">
      {offerRerun && ctx.canWrite && (
        <section className="card border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/40" aria-label="प्राप्त उत्तरासह पुन्हा तयार करणे">
          <h2 className="mb-2 font-bold">प्राप्त उत्तर विचारात घेऊन टिप्पणी पुन्हा तयार करावी का?</h2>
          <ReRun ctx={ctx} preset="प्राप्त उत्तर (जोडलेले उत्तराचे पत्र) विचारात घेऊन अभ्यास-फाइल व टिप्पणी पुन्हा तयार करावी." />
          <button type="button" className="btn-ghost mt-2" onClick={() => setOfferRerun(false)}>आता नाही</button>
        </section>
      )}
      <Section
        title="पाठवलेली पत्रे"
        right={ctx.canWrite && <button className="btn-primary" onClick={() => { setF(blank()); setOpen(true); }}>+ पत्र नोंदवा</button>}
      >
        {ctx.letters.length === 0 ? <Empty icon="✉️" title="पत्राची नोंद नाही" hint="माहिती-मागणी पत्र पाठवल्यावर कृपया येथे नोंद करावी." /> : (
          <ul className="divide-y divide-slate-100 dark:divide-navy-800">
            {ctx.letters.map(l => {
              const tone = letterTone(l);
              const meta = [l.sent_date && `पाठवले ${fmtDate(l.sent_date)}`, l.reply_due && `उत्तराची मुदत ${fmtDate(l.reply_due)}`, l.reply_received_date && `उत्तर ${fmtDate(l.reply_received_date)}`].filter(Boolean).join(' • ');
              const waiting = !l.reply_received_date && l.status !== 'उत्तर प्राप्त';
              return (
                <li key={l.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div className="min-w-0">
                    <div className="break-words font-semibold [overflow-wrap:anywhere]">{l.ref_no || 'पत्र'} <Chip tone={tone}>{tone === 'red' ? 'उत्तराची मुदत संपली' : l.status}</Chip></div>
                    {l.addressed_to && <div className="text-sm text-slate-600 dark:text-slate-300">{l.addressed_to}</div>}
                    {meta && <div className="text-sm text-slate-500">{meta}</div>}
                  </div>
                  {ctx.canWrite && waiting && (
                    <div className="flex flex-col items-end gap-1">
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-ghost" disabled={busyRun} title={busyRun ? 'प्रक्रिया चालू आहे — ती पूर्ण झाल्यावर कृपया वापरावे' : undefined} onClick={() => setReminderFor(l)}>स्मरणपत्र</button>
                        <button className="btn-primary" onClick={() => setReplyFor(l)}>उत्तर प्राप्त — फाइल जोडावी</button>
                      </div>
                      {busyRun && <span className="text-sm text-slate-500 dark:text-slate-400">स्मरणपत्र: प्रक्रिया चालू आहे — ती पूर्ण झाल्यावर कृपया वापरावे</span>}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Section>

      <Section title="प्राप्त उत्तरे">
        {replies.length > 0 ? (
          <ul className="mb-3 space-y-2">
            {replies.map(r => (
              <li key={r.id} className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate" title={r.original_name}>{r.original_name} <span className="text-sm text-slate-500">• {fmtDate(r.created_at)}</span></span>
                <DownloadBtn f={r} label="डाउनलोड" className="btn-ghost shrink-0 px-3" />
              </li>
            ))}
          </ul>
        ) : <p className="mb-3 text-slate-500">उत्तराची फाइल नाही.</p>}
        {ctx.canWrite && !pendingLetters && (
          <>
            <button className="btn-ghost" disabled={upPct !== null} onClick={() => fileRef.current?.click()}>
              {upPct !== null ? <><Spinner /> {upPct}%</> : '⬆ उत्तराची फाइल जोडावी'}
            </button>
            <input ref={fileRef} type="file" hidden accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={e => { const x = e.target.files?.[0]; e.target.value = ''; if (x) void uploadReply(x); }} />
          </>
        )}
      </Section>

      <Modal open={open} onClose={() => setOpen(false)} title="पाठवलेल्या पत्राची नोंद">
        <form onSubmit={create} className="space-y-3">
          <Field label="पत्र क्रमांक"><input className="input" placeholder="संकिर्ण-2026/___/प्र.क्र.___/का.6" value={f.ref_no} onChange={set('ref_no')} /></Field>
          <Field label="कोणाला"><input className="input" value={f.addressed_to} onChange={set('addressed_to')} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="पाठवल्याचा दिनांक"><input className="input" type="date" value={f.sent_date} onChange={set('sent_date')} /></Field>
            <Field label="उत्तराची मुदत"><input className="input" type="date" value={f.reply_due} onChange={set('reply_due')} /></Field>
          </div>
          <Field label="स्थिती"><select className="input" value={f.status} onChange={set('status')}>{LETTER_STATUSES.map(s => <option key={s}>{s}</option>)}</select></Field>
          <p className="text-sm text-slate-500">पाठवल्याचा दिनांक भरल्यास टप्पा "पत्र पाठवले (माहिती प्रतीक्षेत)" होतो.</p>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={() => setOpen(false)}>रद्द</button>
            <button className="btn-primary" disabled={busy}>{busy && <Spinner />} जतन करा</button>
          </div>
        </form>
      </Modal>
      <Modal open={!!reminderFor} onClose={() => setReminderFor(null)} title="स्मरणपत्राचा मसुदा">
        {reminderFor && <ReminderForm ctx={ctx} l={reminderFor} onDone={() => setReminderFor(null)} />}
      </Modal>
      <Modal open={!!replyFor} onClose={() => setReplyFor(null)} title="उत्तर प्राप्त — नोंद">
        {replyFor && <ReplyForm ctx={ctx} l={replyFor} onDone={() => { setReplyFor(null); setOfferRerun(true); }} />}
      </Modal>
    </div>
  );
}

// ---------------- इतिहास ----------------
const isDate = (v: unknown) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v);
/** Field list in Marathi ("पत्र क्र.: … • पाठवल्याचा दिनांक: 02.11.2026"); unknown / technical keys are left out. */
function fieldsText(d: Record<string, unknown> | null | undefined, skip: string[] = []): string {
  return Object.entries(d || {})
    .filter(([k, v]) => FIELD_LABEL[k] && !skip.includes(k) && v != null && v !== '')
    .map(([k, v]) => `${FIELD_LABEL[k]}: ${k === 'received_via' ? (v === 'High Court' ? 'उच्च न्यायालयामार्फत' : v === 'direct' ? 'थेट' : textOf(v)) : isDate(v) ? fmtDate(String(v)) : textOf(v)}`)
    .join(' • ');
}
/** Glossary (UI audit X2): the automatic job is always "प्रक्रिया" — these override the shared labels for run rows. */
const HISTORY_LABEL: Record<string, string> = {
  run_started: 'प्रक्रिया सुरू झाली', run_queued: 'प्रक्रिया प्रतीक्षेत', run_done: 'प्रक्रिया पूर्ण', run_failed: 'प्रक्रिया अयशस्वी',
  run_warning: 'प्रक्रियेतील सूचना', case_cr_duplicate: 'C R आधीच दुसऱ्या प्रकरणात',
};
const RUN_ACTIONS = ['run_started', 'run_queued', 'run_done', 'run_failed'];
const EDIT_ACTIONS = ['edit_requested', 'edit_done', 'edit_failed'];

/** Marathi text of one activity row (A3 audit: no raw keys such as "letter_id: 3 • date: …"). Run ids, migration numbers and
 *  raw failure text only for the owner. */
export function activityText(x: Activity, isOwner = false): string {
  const d = (x.detail || {}) as Record<string, unknown>;
  const run = isOwner && d.run_id != null ? `प्रक्रिया क्र. ${textOf(d.run_id)}` : '';
  switch (x.action) {
    case 'stage_changed': return `${textOf(d.from)} → ${textOf(d.to)}`;
    case 'file_uploaded': return `${FILE_KIND_LABEL[String(d.kind)] || textOf(d.kind)}: ${textOf(d.name)} (आवृत्ती ${textOf(d.version)})`;
    case 'run_started': return [run, d.outputs_dropped ? (isOwner ? 'मसुदे-निवड लागू झाली नाही (migration 0008 बाकी)' : 'मसुदे-निवड लागू झाली नाही') : draftsText(d.outputs) && `मसुदे: ${draftsText(d.outputs)}`, d.instructions ? `सूचना: ${textOf(d.instructions)}` : ''].filter(Boolean).join(' • ');
    case 'run_done': {
      const files = asArray(d.files).filter(f => !(f && typeof f === 'object' && (f as { kind?: unknown }).kind === 'spec'))
        .map(f => (f && typeof f === 'object' ? textOf((f as { name?: unknown }).name) : textOf(f))).filter(n => n && !/^(spec|enclosures)\.json$/.test(n));
      return [run, files.length ? `फाइल: ${files.join(', ')}` : ''].filter(Boolean).join(' • ');
    }
    case 'edit_requested': return [isOwner && d.run_id != null ? `सुधारणा क्र. ${textOf(d.run_id)}` : '', editTargetLabel(textOf(d.target)), textOf(d.message)].filter(Boolean).join(' • ');
    case 'run_failed': return [run, reasonText(textOf(d.reason), isOwner)].filter(Boolean).join(' • ');
    case 'run_warning': return [run, textOf(d.warning)].filter(Boolean).join(' • ');
    case 'case_created': return d.cr ? `C R ${textOf(d.cr)}` : '';
    case 'case_updated': {
      const f = asArray(d.fields).map(k => FIELD_LABEL[String(k)]).filter(Boolean);
      return [d.cr !== undefined ? `C R: ${textOf(d.cr) || '—'}` : '', f.length ? `बदललेले: ${f.join(', ')}` : ''].filter(Boolean).join(' • ');
    }
    case 'case_cr_duplicate': return `PDF वरील C R ${textOf(d.cr)} आधीच प्रकरण क्र. ${textOf(d.existing_id)} मध्ये आहे`;
    case 'case_filled_from_pdf': return fieldsText(d.fields as Record<string, unknown>);
    case 'case_fill_skipped': return fieldsText(d.fields as Record<string, unknown>); // technical reason not shown
    case 'letter_reply_received': return `उत्तर दि. ${fmtDate(textOf(d.date))}`;
    case 'letter_saved': return fieldsText(d, ['case_id']);
    case 'letter_updated': return fieldsText(d);
    default: return fieldsText(d);
  }
}

export function HistoryTab({ ctx }: { ctx: CaseCtx }) {
  const { me } = useAuth();
  const isOwner = me?.role === 'owner';
  const items = useMemo(() => {
    // C21: a run / edit is shown once (its own row below) — the activity rows that only repeat it are left out
    const runIds = new Set((ctx.runs || []).map(r => String(r.id)));
    const editIds = new Set((ctx.editRuns || []).map(r => String(r.id)));
    const dupRow = (x: Activity) => {
      const rid = x.detail?.run_id != null ? String(x.detail.run_id) : '';
      return (RUN_ACTIONS.includes(x.action) && runIds.has(rid)) || (EDIT_ACTIONS.includes(x.action) && editIds.has(rid));
    };
    // the drafts' source file (kind spec) is internal: its upload rows are not shown
    const a = ctx.activity.filter(x => !(x.action === 'file_uploaded' && x.detail?.kind === 'spec') && !dupRow(x)).map(x => ({
      at: x.at,
      key: `a${x.id}`,
      title: HISTORY_LABEL[x.action] || ACTION_LABEL[x.action] || 'इतर नोंद',
      text: activityText(x, isOwner),
      who: x.actor ? ctx.members.get(x.actor) || '' : 'प्रणाली',
      tone: x.action === 'stage_changed' ? ('navy' as const) : x.action === 'run_failed' ? ('red' as const)
        : x.action === 'run_warning' && isCriticalWarning(textOf(x.detail?.warning)) ? ('red' as const) : ('slate' as const),
    }));
    const r = (ctx.runs || []).map(x => ({
      at: x.finished_at || x.started_at || x.created_at,
      key: `r${x.id}`,
      title: `${isOwner ? `प्रक्रिया क्र. ${x.id}` : 'प्रक्रिया'}: ${RUN_STATE_LABEL[x.state] || x.state}`,
      text: [x.state === 'failed' ? reasonText(x.step, isOwner) : x.state === 'done' ? '' : x.step, draftsText(x.outputs) && `मसुदे: ${draftsText(x.outputs)}`, x.instructions && `सूचना: ${x.instructions}`].filter(Boolean).join(' • '),
      who: x.created_by ? ctx.members.get(x.created_by) || '' : '',
      tone: runTone(x.state),
    }));
    const e = (ctx.editRuns || []).map(x => ({
      at: x.finished_at || x.started_at || x.created_at,
      key: `e${x.id}`,
      title: `${isOwner ? `सुधारणा क्र. ${x.id}` : 'सुधारणा'}: ${x.state === 'done' ? (x.edit_result?.refused ? 'नाकारली' : 'पूर्ण') : RUN_STATE_LABEL[x.state] || x.state}`,
      text: [editTargetLabel(x.edit_target), x.edit_message, x.state === 'failed' ? reasonText(x.step, isOwner) : x.edit_result?.refused || x.edit_result?.summary || ''].filter(Boolean).join(' • '),
      who: x.created_by ? ctx.members.get(x.created_by) || '' : '',
      tone: x.state === 'done' && x.edit_result?.refused ? ('amber' as const) : runTone(x.state),
    }));
    return [...a, ...r, ...e].sort((p, q) => (p.at < q.at ? 1 : -1));
  }, [ctx.activity, ctx.runs, ctx.editRuns, ctx.members, isOwner]);

  if (!items.length) return <div className="card"><Empty icon="🕘" title="इतिहास नाही" /></div>;
  return (
    <div className="card min-w-0 overflow-hidden p-4">
      <ol className="relative ml-2 border-l-2 border-slate-200 dark:border-navy-800">
        {items.map(i => (
          <li key={i.key} className="mb-4 ml-4 min-w-0">
            <span className="absolute -left-[7px] mt-2 h-3 w-3 rounded-full" style={{ background: TONE_HEX[i.tone] }} aria-hidden="true" />
            <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
              <span className="font-semibold">{i.title}</span>
              <span className="min-w-0 break-words text-sm text-slate-500 [overflow-wrap:anywhere]">{fmtDateTime(i.at)}{i.who ? ` • ${i.who}` : ''}</span>
            </div>
            {i.text && <div className="break-words text-slate-700 [overflow-wrap:anywhere] dark:text-slate-300">{i.text}</div>}
          </li>
        ))}
      </ol>
    </div>
  );
}
