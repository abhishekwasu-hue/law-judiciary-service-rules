// Values must match supabase/migrations/20261101000001_init.sql CHECK constraints exactly.
export const STAGES = [
  'प्राप्त',
  'अभ्यास चालू',
  'मसुदा तयार',
  'वरिष्ठांकडे सादर',
  'पत्र पाठवले (माहिती प्रतीक्षेत)',
  'माहिती प्राप्त',
  'वित्त/सा.प्र.वि. कडे',
  'अभिप्राय प्राप्त',
  'आदेश/पत्र निर्गमित',
  'बंद',
] as const;

export const CATEGORIES = [
  'वेतननिश्चिती', 'भत्ते', 'निवृत्तीवेतन', 'जुनी पेन्शन', 'विशेष वेतन',
  'विमा/GPF', 'सेवा', 'न्यायिक वेतन', 'वैद्यकीय', 'इतर',
] as const;

export const PRIORITIES = ['सामान्य', 'तातडीचे'] as const;
export const LETTER_STATUSES = ['मसुदा', 'पाठवले', 'उत्तर प्राप्त', 'स्मरणपत्र'] as const;

/** Status colours by meaning: green done, amber waiting, red overdue/failed, blue running. */
export type Tone = 'green' | 'amber' | 'red' | 'blue' | 'slate' | 'navy';
export const TONE_CLASS: Record<Tone, string> = {
  green: 'bg-green-100 text-green-900 dark:bg-green-900/50 dark:text-green-200',
  amber: 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-200',
  red: 'bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-200',
  blue: 'bg-blue-100 text-blue-900 dark:bg-blue-900/50 dark:text-blue-200',
  slate: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
  navy: 'bg-navy-100 text-navy-900 dark:bg-navy-800 dark:text-navy-100',
};
export const TONE_HEX: Record<Tone, string> = {
  green: '#15803d', amber: '#b45309', red: '#b91c1c', blue: '#1d4ed8', slate: '#64748b', navy: '#3a5892',
};

export function stageTone(s: string): Tone {
  if (s === 'बंद' || s === 'आदेश/पत्र निर्गमित') return 'green';
  if (s === 'अभ्यास चालू') return 'blue';
  if (s === 'पत्र पाठवले (माहिती प्रतीक्षेत)' || s === 'वित्त/सा.प्र.वि. कडे' || s === 'वरिष्ठांकडे सादर') return 'amber';
  if (s === 'प्राप्त') return 'navy';
  return 'slate';
}

export const RUN_STATE_LABEL: Record<string, string> = {
  queued: 'रांगेत', running: 'चालू', done: 'पूर्ण', failed: 'अयशस्वी',
};
export function runTone(s: string): Tone {
  return s === 'done' ? 'green' : s === 'failed' ? 'red' : s === 'running' ? 'blue' : 'amber';
}

/** A run queued/running longer than this is stuck (engine job timeout 180 min). Same limit as the Worker's /api/runs/sweep. */
export const STALE_MS = 3.5 * 3600 * 1000;
export const STALE_REASON = 'वेळ संपली — पुन्हा तयार करा';
export const isStale = (r: { state: string; created_at: string }) =>
  (r.state === 'queued' || r.state === 'running') && Date.now() - new Date(r.created_at).getTime() > STALE_MS;
/** Run in progress (blocks a new run). A stale run does not block. */
export const runActive = (r: { state: string; created_at: string } | null | undefined) =>
  !!r && (r.state === 'queued' || r.state === 'running') && !isStale(r);

/** Live progress steps (prompt §6.2). Keys = the exact runs.step texts written by the engine (tools/ENGINE_PROMPT.md rule 4). */
export const RUN_STEPS: { key: string; label: string }[] = [
  { key: 'queued', label: 'रांगेत' },
  { key: 'पाने वाचत आहे', label: 'पाने वाचन' },
  { key: 'GR शोधत आहे', label: 'GR शोध' },
  { key: 'मसुदा तयार करत आहे', label: 'मसुदा' },
  { key: 'PDF बनवत आहे', label: 'PDF तयार' },
  { key: 'तपासणी चालू', label: 'पडताळणी' },
  { key: 'done', label: 'पूर्ण' },
];

export const FILE_KIND_LABEL: Record<string, string> = {
  proposal: 'प्रस्ताव', extra_doc: 'इतर कागदपत्र', study: 'अभ्यास', note_letter: 'टिप्पणी व पत्र',
  package_pdf: 'GR सह प्रस्ताव', gr: 'GR', reply: 'उत्तर',
  order_draft: 'शासन आदेश-मसुदा', parawise: 'परिच्छेदनिहाय अभिप्राय (इंग्रजी)',
};

/** Optional engine outputs (02.11.2026, migration 0006): shown with the note when the engine produced them. */
export const EXTRA_OUTPUT_KINDS = ['order_draft', 'parawise'] as const;

export const ACTION_LABEL: Record<string, string> = {
  case_created: 'प्रकरण नोंदवले', file_uploaded: 'फाइल अपलोड', run_started: 'अभ्यास सुरू',
  stage_changed: 'टप्पा बदलला', letter_saved: 'पत्र नोंदवले', run_done: 'अभ्यास पूर्ण', run_failed: 'अभ्यास अयशस्वी', run_warning: 'अभ्यास-सूचना',
};
