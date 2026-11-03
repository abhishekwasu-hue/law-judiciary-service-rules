import { lazy, Suspense, useMemo, useRef, useState, type FormEvent } from 'react';
import { ApiError, api, downloadFile, humanError, uploadFile } from '../lib/api';
import { ACTION_LABEL, EXTRA_OUTPUT_KINDS, FIELD_LABEL, FILE_KIND_LABEL, INPUT_KINDS, INPUT_KIND_LABEL, LETTER_STATUSES, RUN_STATE_LABEL, TONE_HEX, draftsText, runActive, runTone, type DraftKey, type InputKind } from '../lib/constants';
import { sameDrafts, suggestDrafts } from '../lib/drafts';
import DraftPicker from '../components/DraftPicker';
import { asArray, cleanReason, daysBetween, fmtDate, fmtDateTime, isCriticalWarning, textOf, todayISO } from '../lib/format';
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

interface GrItem { code?: string; date?: string; title?: string; pages?: unknown; page?: unknown }
const grItem = (v: unknown): GrItem => (v && typeof v === 'object' ? (v as GrItem) : { title: textOf(v) });
const firstPage = (g: GrItem): number | null => {
  const p = asArray(g.page ?? g.pages)[0];
  const n = Number(typeof p === 'string' ? p.match(/\d+/)?.[0] : p);
  return Number.isFinite(n) && n > 0 ? n : null;
};

function DownloadBtn({ f, label = 'डाउनलोड' }: { f: CaseFile; label?: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="btn-ghost"
      disabled={busy}
      title={f.original_name}
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
      {busy ? <Spinner /> : '⬇'} {label}
    </button>
  );
}

/** Latest run failed or timed out (stale) → the banner itself offers "पुन्हा तयार करा". */
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
    <Section title="प्रक्रियेची स्थिती" className="mb-4">
      <RunProgress run={r} retryHint={canRetry ? 'खालील "पुन्हा तयार करा" बटण वापरा.' : failed ? 'पुन्हा तयार करण्याची परवानगी फक्त कार्यासनाला आहे.' : undefined} />
      {canRetry && <div className="no-print mt-4 border-t border-slate-200 pt-4 dark:border-navy-800"><ReRun ctx={ctx} /></div>}
    </Section>
  );
}

export function ReRun({ ctx, title = 'सुधारणा करून पुन्हा तयार करा', preset = '', presetDrafts }: { ctx: CaseCtx; title?: string; preset?: string; presetDrafts?: DraftKey[] }) {
  const toast = useToast();
  const [text, setText] = useState(preset);
  // "कोणते मसुदे हवेत?": the suggestion from the case's files and runs until the user changes a chip
  const suggestion = suggestDrafts(ctx.files, ctx.runs);
  const [drafts, setDraftsRaw] = useState<DraftKey[] | null>(presetDrafts ?? null);
  const chosen = drafts ?? suggestion.keys;
  const setDrafts = (v: DraftKey[]) => setDraftsRaw(sameDrafts(v, suggestion.keys) ? null : v);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<number | null>(null); // dispatched run whose Realtime row is not here yet (H3)
  const r = latestRun(ctx.runs);
  const running = runActive(r) || (pending !== null && !(ctx.runs ?? []).some(x => x.id === pending)); // a failed or stale (> 3.5 h) latest run does not block
  if (!ctx.canWrite) return null;
  async function go(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const started = await api<{ id: number; outputs_dropped?: boolean }>('/api/run', { body: { case_id: ctx.c.id, instructions: text.trim() || undefined, outputs: chosen } });
      setPending(started.id);
      toast(started.outputs_dropped ? 'प्रक्रिया सुरू झाली — मसुदे-निवड लागू झाली नाही (migration 0008 बाकी)' : 'प्रक्रिया पुन्हा सुरू झाली');
      setText('');
      setDraftsRaw(null);
    } catch (x) {
      if (x instanceof ApiError && x.message === 'run_active') setPending(Number((x.data as { run_id?: number } | undefined)?.run_id) || null);
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={go} className="space-y-3">
      <DraftPicker value={chosen} onChange={setDrafts} suggestion={suggestion} disabled={busy || running} />
      <Field label={title} hint="ही सूचना पाळून संपूर्ण अभ्यास पुन्हा तयार होतो (कायमच्या नियमांच्या मर्यादेत).">
        <textarea className="input min-h-[80px]" placeholder="उदा. पत्रात फक्त सेवापुस्तकाची प्रत मागवा…" value={text} onChange={e => setText(e.target.value)} />
      </Field>
      <button className="btn-primary" disabled={busy || running}>{busy && <Spinner />} {running ? 'प्रक्रिया चालू…' : 'पुन्हा तयार करा'}</button>
      {running && <p className="text-sm text-slate-500 dark:text-slate-400">प्रक्रिया चालू — संपल्यावर वापरा.</p>}
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
        <div className="card"><Empty icon="📝" title="अजून ब्रीफिंग नाही" hint="प्रक्रिया तयार झाल्यावर येथे दिसेल." /></div>
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
              <div className="mt-3 text-sm text-slate-500">प्रक्रिया तयार: {fmtDateTime(run.finished_at)}</div>
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
            <Section title="टप्पानिहाय दिवस (या प्रकरणाचे)">
              <Suspense fallback={<Skeleton className="h-40 w-full" />}>
                <StageDaysChart days={days} />
              </Suspense>
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------- टिप्पणी व पत्र ----------------
/** Optional outputs (शासन आदेश-मसुदा, परिच्छेदनिहाय अभिप्राय): latest version of each kind, view + download. */
function ExtraOutputs({ ctx }: { ctx: CaseCtx }) {
  const items = EXTRA_OUTPUT_KINDS.map(k => ofKind(ctx.files, k)[0]).filter((f): f is CaseFile => !!f);
  // made by the latest finished run = stored after that run started; older ones are labelled (they may be stale)
  const last = latestDone(ctx.runs);
  const since = last ? last.started_at || last.created_at : null;
  const current = (f: CaseFile) => !!since && f.created_at >= since;
  const [view, setView] = useState<CaseFile | null>(null);
  if (items.length === 0) return null;
  return (
    <Section title="इतर मसुदे">
      <ul className="space-y-2">
        {items.map(f => (
          <li key={f.id} className="rounded-lg border border-slate-200 p-2 dark:border-navy-800">
            <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">{FILE_KIND_LABEL[f.kind]}{!current(f) && <Chip tone="amber">मागील प्रक्रियेतील</Chip>}</div>
            <div className="truncate text-xs text-slate-500" title={f.original_name}>{f.original_name} • आवृत्ती {f.version}</div>
            <div className="mt-1 flex flex-wrap gap-1">
              <button className="btn-ghost min-h-tap px-2 py-1 text-sm" onClick={() => setView(f)}>पाहा</button>
              <DownloadBtn f={f} />
            </div>
          </li>
        ))}
      </ul>
      <Modal open={!!view} onClose={() => setView(null)} title={view ? FILE_KIND_LABEL[view.kind] : ''} wide>
        {view && <DocxView fileId={view.id} />}
      </Modal>
    </Section>
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
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="card min-w-0 p-3">
          {!sel ? <Empty icon="📄" title="टिप्पणी अजून तयार नाही" hint="प्रक्रिया तयार झाल्यावर येथे दिसेल." /> : (
            <>
              <div className="no-print mb-3 flex flex-wrap items-center gap-2">
                <span className="truncate font-semibold" title={sel.original_name}>{sel.original_name}</span>
                <span className="text-sm text-slate-500">आवृत्ती {sel.version}</span>
                <div className="ml-auto flex gap-2">
                  {prev && <button className="btn-ghost" disabled={diffBusy} onClick={() => void showDiff()}>{diffBusy && <Spinner />} मागील आवृत्तीशी फरक</button>}
                  <DownloadBtn f={sel} />
                </div>
              </div>
              <DocxView fileId={sel.id} />
            </>
          )}
        </div>
        <div className="space-y-4">
          {run?.letter_needed && points.length > 0 && (
            <Section title="पत्रातील अत्यावश्यक मुद्दे">
              <ol className="list-decimal space-y-1 pl-6">{points.map((p, i) => <li key={i}>{textOf(p)}</li>)}</ol>
            </Section>
          )}
          <Section title="आवृत्त्या">
            {versions.length === 0 ? <div className="text-slate-500">—</div> : (
              <ul className="space-y-1">
                {versions.map(v => (
                  <li key={v.id}>
                    <button className={`min-h-tap w-full rounded-lg px-3 py-1 text-left ${sel?.id === v.id ? 'bg-navy-100 font-semibold dark:bg-navy-800' : 'hover:bg-slate-100 dark:hover:bg-navy-800/60'}`} onClick={() => { setSelId(v.id); setDiff(null); }}>
                      आवृत्ती {v.version} <span className="text-sm text-slate-500">• {fmtDateTime(v.created_at)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>
          <ExtraOutputs ctx={ctx} />
          {ctx.canWrite && !latestFailed(ctx) && <Section title="पुन्हा तयार करा"><ReRun ctx={ctx} /></Section>}
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

// ---------------- प्रस्ताव + GR ----------------
export function PackageTab({ ctx }: { ctx: CaseCtx }) {
  const toast = useToast();
  const pkg = ofKind(ctx.files, 'package_pdf')[0];
  const proposal = ofKind(ctx.files, 'proposal')[0];
  const shown = pkg || proposal;
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
          {!shown ? <Empty icon="📄" title="PDF उपलब्ध नाही" hint="प्रस्ताव अपलोड करा." /> : (
            <>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="min-w-0 truncate font-semibold" title={shown.original_name}>{shown.original_name}</span>
                {!pkg && <Chip tone="amber">GR सह PDF अजून तयार नाही — मूळ प्रस्ताव</Chip>}
                <div className="ml-auto"><DownloadBtn f={shown} /></div>
              </div>
              <PdfViewer fileId={shown.id} jumpTo={jump} />
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
                        {p && pkg && <button className="btn-ghost min-h-tap px-2 py-1 text-sm" onClick={() => setJump({ page: p, at: Date.now() })}>पृ. {p} वर जा</button>}
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
                    <div className="text-xs text-slate-500">{FILE_KIND_LABEL[f.kind]} • v{f.version} • {fmtDateTime(f.created_at)}{multiProposal && proposal?.id === f.id ? ' • प्रक्रियेसाठी वापरला जाणारा (नवीनतम)' : ''}</div>
                  </div>
                  <DownloadBtn f={f} label="" />
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
    if (file.size > 50 * 1024 * 1024) return toast('फाइल 50 MB पेक्षा मोठी', 'err');
    setPct(0);
    try {
      await uploadFile(ctx.c.id, kind, file, setPct);
      toast(`${INPUT_KIND_LABEL[kind]} अपलोड झाले — मसुदे हवे असल्यास "पुन्हा तयार करा"`);
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

// ---------------- अभ्यास ----------------
export function StudyTab({ ctx }: { ctx: CaseCtx }) {
  const s = ofKind(ctx.files, 'study')[0];
  return (
    <div>
      <RunBanner ctx={ctx} />
      <div className="card p-3">
        {!s ? <Empty icon="📘" title="अभ्यास-फाइल अजून तयार नाही" hint="प्रक्रिया तयार झाल्यावर येथे दिसेल." /> : (
          <>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="min-w-0 truncate font-semibold" title={s.original_name}>{s.original_name}</span>
              <span className="text-sm text-slate-500">आवृत्ती {s.version}</span>
              <div className="ml-auto"><DownloadBtn f={s} /></div>
            </div>
            <DocxView fileId={s.id} />
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

export function LettersTab({ ctx }: { ctx: CaseCtx }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ ref_no: '', addressed_to: '', sent_date: '', reply_due: '', status: 'पाठवले' });
  const [busy, setBusy] = useState(false);
  const [upPct, setUpPct] = useState<number | null>(null);
  const [offerRerun, setOfferRerun] = useState(false);
  const [reminderFor, setReminderFor] = useState<Letter | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF(s => ({ ...s, [k]: e.target.value }));
  const replies = ofKind(ctx.files, 'reply');
  const busyRun = runActive(latestRun(ctx.runs));

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api('/api/letters', { body: { case_id: ctx.c.id, ...f } });
      toast('पत्र नोंदवले');
      setOpen(false);
      setF({ ref_no: '', addressed_to: '', sent_date: '', reply_due: '', status: 'पाठवले' });
      await ctx.reloadLetters();
      await ctx.reloadActivity();
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setBusy(false);
    }
  }
  async function markReply(l: Letter) {
    try {
      await api(`/api/letters/${l.id}`, { method: 'PATCH', body: { reply_received_date: todayISO(), status: 'उत्तर प्राप्त' } });
      toast('उत्तर प्राप्त नोंदवले');
      await ctx.reloadLetters();
    } catch (x) {
      toast(humanError(x), 'err');
    }
  }
  async function uploadReply(file: File) {
    setUpPct(0);
    try {
      await uploadFile(ctx.c.id, 'reply', file, setUpPct);
      toast('उत्तर अपलोड; टप्पा "माहिती प्राप्त"');
      setOfferRerun(true);
      // the Worker may have marked the pending letter "उत्तर प्राप्त"
      await Promise.all([ctx.reloadFiles(), ctx.reloadLetters(), ctx.reloadActivity()]);
    } catch (x) {
      toast(humanError(x), 'err');
    } finally {
      setUpPct(null);
    }
  }

  return (
    <div className="space-y-4">
      <Section
        title="पाठवलेली पत्रे"
        right={ctx.canWrite && <button className="btn-primary" onClick={() => setOpen(true)}>+ पत्र नोंदवा</button>}
      >
        {ctx.letters.length === 0 ? <Empty icon="✉️" title="पत्र नाही" hint="माहिती-मागणी पत्र पाठवल्यावर येथे नोंदवा." /> : (
          <ul className="divide-y divide-slate-100 dark:divide-navy-800">
            {ctx.letters.map(l => (
              <li key={l.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div className="min-w-0">
                  <div className="font-semibold">{l.ref_no || '—'} <Chip tone={letterTone(l)}>{letterTone(l) === 'red' ? 'मुदत संपली' : l.status}</Chip></div>
                  <div className="text-sm text-slate-600 dark:text-slate-300">{l.addressed_to || '—'}</div>
                  <div className="text-sm text-slate-500">पाठवले {fmtDate(l.sent_date)} • उत्तराची मुदत {fmtDate(l.reply_due)}{l.reply_received_date ? ` • उत्तर ${fmtDate(l.reply_received_date)}` : ''}</div>
                </div>
                {ctx.canWrite && !l.reply_received_date && (
                  <div className="flex flex-col items-end gap-1">
                    <div className="flex flex-wrap gap-2">
                      <button className="btn-ghost" disabled={busyRun} title={busyRun ? 'प्रक्रिया चालू — संपल्यावर वापरा' : undefined} onClick={() => setReminderFor(l)}>स्मरणपत्र</button>
                      <button className="btn-ghost" onClick={() => void markReply(l)}>उत्तर प्राप्त</button>
                    </div>
                    {busyRun && <span className="text-sm text-slate-500 dark:text-slate-400">स्मरणपत्र: प्रक्रिया चालू — संपल्यावर वापरा</span>}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="प्राप्त उत्तरे">
        {replies.length > 0 && (
          <ul className="mb-3 space-y-2">
            {replies.map(r => (
              <li key={r.id} className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate" title={r.original_name}>{r.original_name} <span className="text-sm text-slate-500">• {fmtDate(r.created_at)}</span></span>
                <DownloadBtn f={r} label="" />
              </li>
            ))}
          </ul>
        )}
        {ctx.canWrite && (
          <>
            <button className="btn-ghost" disabled={upPct !== null} onClick={() => fileRef.current?.click()}>
              {upPct !== null ? <><Spinner /> {upPct}%</> : '⬆ उत्तर अपलोड करा'}
            </button>
            <input ref={fileRef} type="file" hidden accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={e => { const x = e.target.files?.[0]; e.target.value = ''; if (x) void uploadReply(x); }} />
          </>
        )}
        {offerRerun && (
          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-950/40">
            <ReRun ctx={ctx} title="प्राप्त उत्तरासह पुन्हा तयार करायचे?" preset="प्राप्त उत्तर (अपलोड केलेले उत्तराचे पत्र) विचारात घेऊन अभ्यास-फाइल व टिप्पणी पुन्हा तयार करा." />
          </div>
        )}
      </Section>

      <Modal open={open} onClose={() => setOpen(false)} title="पत्र नोंदवा">
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
        {reminderFor && (
          <ReRun
            ctx={ctx}
            title="प्रक्रियेसाठी सूचना"
            presetDrafts={['reminder']}
            preset={`पत्र क्र. ${reminderFor.ref_no || '—'}, दि. ${fmtDate(reminderFor.sent_date)} (${reminderFor.addressed_to || ''}) याचे उत्तर अप्राप्त — स्मरणपत्राचा मसुदा तयार करा.`}
          />
        )}
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
/** Marathi text of one activity row (A3 audit: no raw keys such as "letter_id: 3 • date: …"). */
export function activityText(x: Activity): string {
  const d = (x.detail || {}) as Record<string, unknown>;
  const run = d.run_id != null ? `प्रक्रिया क्र. ${textOf(d.run_id)}` : '';
  switch (x.action) {
    case 'stage_changed': return `${textOf(d.from)} → ${textOf(d.to)}`;
    case 'file_uploaded': return `${FILE_KIND_LABEL[String(d.kind)] || textOf(d.kind)}: ${textOf(d.name)} (आवृत्ती ${textOf(d.version)})`;
    case 'run_started': return [run, d.outputs_dropped ? 'मसुदे-निवड लागू झाली नाही (migration 0008 बाकी)' : draftsText(d.outputs) && `मसुदे: ${draftsText(d.outputs)}`, d.instructions ? `सूचना: ${textOf(d.instructions)}` : ''].filter(Boolean).join(' • ');
    case 'run_done': {
      const files = asArray(d.files).map(f => (f && typeof f === 'object' ? textOf((f as { name?: unknown }).name) : textOf(f))).filter(Boolean);
      return [run, files.length ? `फाइल: ${files.join(', ')}` : ''].filter(Boolean).join(' • ');
    }
    case 'run_failed': return [run, cleanReason(textOf(d.reason))].filter(Boolean).join(' • ');
    case 'run_warning': return [run, textOf(d.warning)].filter(Boolean).join(' • ');
    case 'case_created': return d.cr ? `C R ${textOf(d.cr)}` : '';
    case 'case_updated': {
      const f = asArray(d.fields).map(k => FIELD_LABEL[String(k)]).filter(Boolean);
      return [d.cr !== undefined ? `C R: ${textOf(d.cr) || '—'}` : '', f.length ? `बदललेले: ${f.join(', ')}` : ''].filter(Boolean).join(' • ');
    }
    case 'case_cr_duplicate': return `PDF वरील C R ${textOf(d.cr)} आधीच प्रकरण #${textOf(d.existing_id)} मध्ये आहे`;
    case 'case_filled_from_pdf': return fieldsText(d.fields as Record<string, unknown>);
    case 'case_fill_skipped': return fieldsText(d.fields as Record<string, unknown>); // technical reason not shown
    case 'letter_reply_received': return `उत्तर दि. ${fmtDate(textOf(d.date))}`;
    case 'letter_saved': return fieldsText(d, ['case_id']);
    case 'letter_updated': return fieldsText(d);
    default: return fieldsText(d);
  }
}

export function HistoryTab({ ctx }: { ctx: CaseCtx }) {
  const items = useMemo(() => {
    const a = ctx.activity.map(x => ({
      at: x.at,
      key: `a${x.id}`,
      title: ACTION_LABEL[x.action] || 'इतर नोंद',
      text: activityText(x),
      who: x.actor ? ctx.members.get(x.actor) || '' : 'प्रणाली',
      tone: x.action === 'stage_changed' ? ('navy' as const) : x.action === 'run_failed' ? ('red' as const)
        : x.action === 'run_warning' && isCriticalWarning(textOf(x.detail?.warning)) ? ('red' as const) : ('slate' as const),
    }));
    const r = (ctx.runs || []).map(x => ({
      at: x.finished_at || x.started_at || x.created_at,
      key: `r${x.id}`,
      title: `प्रक्रिया क्र. ${x.id}: ${x.state === 'done' ? 'तयार' : RUN_STATE_LABEL[x.state] || x.state}`,
      text: [x.state === 'failed' ? cleanReason(x.step) : x.step, draftsText(x.outputs) && `मसुदे: ${draftsText(x.outputs)}`, x.instructions && `सूचना: ${x.instructions}`].filter(Boolean).join(' • '),
      who: x.created_by ? ctx.members.get(x.created_by) || '' : '',
      tone: runTone(x.state),
    }));
    return [...a, ...r].sort((p, q) => (p.at < q.at ? 1 : -1));
  }, [ctx.activity, ctx.runs, ctx.members]);

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
