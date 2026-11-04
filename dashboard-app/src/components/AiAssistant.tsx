// AI सहाय्यक (Abhi 04.11.2026: "मुख्यपृष्ठावर सुद्धा हे बटन पाहिजे … पूर्वीच्या प्रस्तावामध्ये बदल हवे असल्यास येथे क्लिक करा …
// आस्क दिशा … सारखा चॅटबोट … अनावश्यक माहिती हाईड"): a floating AI button on every page; it opens a chat panel that first
// asks which case (the model never chooses the case), then shows that case's सुधारणा-चॅट (EditChat). Nothing new on the
// server: the same /api/edit.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { sb } from '../lib/supabase';
import { useData } from '../lib/data';
import { useCanWrite } from '../lib/auth';
import { isEditRun, isHiddenFile } from '../lib/constants';
import { caseSubject, crFromFileName, crLabel } from '../lib/format';
import type { CaseFile } from '../lib/types';
import type { CaseCtx } from '../pages/CaseDetail';
import { useRuns } from './RunProgress';
import EditChat from './EditChat';
import { Spinner } from './ui';

function CaseChat({ id, onBack }: { id: number; onBack: () => void }) {
  const { cases } = useData();
  const canWrite = useCanWrite();
  const c = cases.find(x => x.id === id) || null;
  const [files, setFiles] = useState<CaseFile[] | null>(null);
  const [hasSpec, setHasSpec] = useState(false);
  const allRuns = useRuns(id);
  const runs = useMemo(() => (allRuns ? allRuns.filter(r => !isEditRun(r)) : null), [allRuns]);
  const editRuns = useMemo(() => (allRuns ? allRuns.filter(isEditRun) : null), [allRuns]);
  const reloadFiles = useCallback(async () => {
    const { data } = await sb().from('case_files').select('*').eq('case_id', id).order('version', { ascending: false }).order('created_at', { ascending: false });
    const rows = (data as CaseFile[]) || [];
    setHasSpec(rows.some(f => f.kind === 'spec'));
    setFiles(rows.filter(f => !isHiddenFile(f)));
  }, [id]);
  useEffect(() => { void reloadFiles(); }, [reloadFiles]);
  if (!c || files === null) return <div className="flex justify-center p-8"><Spinner /></div>;
  const fileCr = !c.cr_no ? crFromFileName(files.find(f => /^CR\d+_\d{4}_/.test(f.original_name))?.original_name) : null;
  const ctx: CaseCtx = {
    c, files, letters: [], activity: [], members: new Map(), runs, editRuns, hasSpec, reloadFiles,
    reloadLetters: async () => {}, reloadActivity: async () => {}, canWrite, title: c.cr_no ? crLabel(c) : fileCr || `प्रकरण #${c.id}`,
  };
  const ready = files.some(f => f.kind === 'note_letter' || f.kind === 'package_pdf');
  return (
    <div className="space-y-3">
      <button type="button" className="btn-ghost text-sm" onClick={onBack}>← कृपया दुसरे प्रकरण निवडावे</button>
      {ready ? <EditChat ctx={ctx} /> : (
        <p className="rounded-lg bg-slate-100 p-3 text-sm dark:bg-navy-800">या प्रकरणाची टिप्पणी अजून तयार झालेली नाही. ती तयार झाल्यावर येथे बदल नमूद करता येतील.</p>
      )}
    </div>
  );
}

export default function AiAssistant() {
  const canWrite = useCanWrite();
  const { cases } = useData();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [caseId, setCaseId] = useState<number | null>(null);
  const [q, setQ] = useState('');
  // on a case page the assistant starts with that case
  const pageCase = Number((loc.pathname.match(/^\/cases\/(\d+)/) || [])[1]) || null;
  useEffect(() => { if (open && caseId === null && pageCase) setCaseId(pageCase); }, [open, pageCase, caseId]);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open]);
  const list = useMemo(() => {
    const t = q.trim().toLowerCase();
    return cases.filter(c => !t || `${crLabel(c)} ${c.cr_no ?? ''} ${c.subject ?? ''} ${c.file_no ?? ''}`.toLowerCase().includes(t)).slice(0, 40);
  }, [cases, q]);
  if (!canWrite || loc.pathname.startsWith('/nasti')) return null;
  return (
    <>
      {!open && (
        <button type="button" onClick={() => setOpen(true)} aria-label="AI सहाय्यक — प्रस्तावात बदल"
          className="ai-fab no-print fixed bottom-[calc(4.5rem+env(safe-area-inset-bottom))] right-3 z-40 flex items-center gap-2 rounded-full py-2 pl-2 pr-4 text-white md:bottom-6 md:right-6">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-lg font-black text-orange-600 shadow">AI</span>
          <span className="text-left leading-tight"><b className="block text-base">AI सहाय्यक</b><span className="text-xs text-white/90">प्रस्तावात बदल हवा?</span></span>
        </button>
      )}
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/30 md:items-end md:p-6" role="dialog" aria-modal="true" aria-label="AI सहाय्यक" onClick={() => setOpen(false)}>
          <div className="flex h-full w-full flex-col overflow-hidden bg-slate-50 shadow-2xl dark:bg-navy-950 md:h-[min(85vh,760px)] md:w-[440px] md:rounded-2xl" onClick={e => e.stopPropagation()}>
            <div className="edit-head flex items-center gap-3 px-4 py-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white text-base font-black text-orange-600">AI</span>
              <div className="min-w-0 flex-1">
                <div className="text-lg font-bold">AI सहाय्यक</div>
                <div className="text-sm text-white/90">टिप्पणी किंवा मसुद्यातील बदलासाठी</div>
              </div>
              <button type="button" className="min-h-tap min-w-tap rounded-full text-2xl font-bold text-white hover:bg-white/20" aria-label="बंद करावे" onClick={() => setOpen(false)}>✕</button>
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              {caseId ? <CaseChat id={caseId} onBack={() => setCaseId(null)} /> : (
                <div className="space-y-3">
                  <div className="rounded-2xl rounded-tl-sm bg-white p-3 shadow-sm dark:bg-navy-900">
                    नमस्कार! पूर्वीच्या प्रस्तावामध्ये बदल हवा असल्यास कृपया आधी प्रकरण निवडावे.
                  </div>
                  <input className="input" autoFocus placeholder="C R क्र. / विषय / नस्ती क्र. शोधावा" value={q} onChange={e => setQ(e.target.value)} aria-label="प्रकरण शोधा" />
                  {list.length === 0 ? <p className="text-sm text-slate-500">या शोधानुसार प्रकरण आढळले नाही.</p> : (
                    <ul className="space-y-1.5">
                      {list.map(c => (
                        <li key={c.id}>
                          <button type="button" className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left hover:border-orange-400 dark:border-navy-800 dark:bg-navy-900" onClick={() => setCaseId(c.id)}>
                            <div className="font-bold">{crLabel(c)}</div>
                            <div className="line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{caseSubject(c)}</div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
