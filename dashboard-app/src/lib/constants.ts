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

/** Desk profiles (C30): ids mirror tools/desks/<id>.json and the Worker's DESK_IDS (cloudflare/worker.js) — add a desk in
 *  all three. cases.desk null (or migration 0009 not applied) = DEFAULT_DESK. */
export const DESKS = [
  { id: 'law-desk6', label: 'विधि व न्याय विभाग — कार्यासन-6', fileNo: 'संकीर्ण-2026/___/प्र.क्र.___/का.6' },
  { id: 'hte-mashi5', label: 'उच्च व तंत्र शिक्षण विभाग — मशि-5', fileNo: '___-2026/प्र.क्र.___/मशि-5' },
] as const;
export const DEFAULT_DESK = 'law-desk6';
export const deskLabel = (id: string | null | undefined) =>
  (DESKS.find(d => d.id === (id || DEFAULT_DESK)) ?? { label: id || '' }).label;

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
  approval: 'मान्यता (वित्त/सा.प्र.वि.)', court_notice: 'न्यायालयीन नोटीस',
  order_draft: 'शासन आदेश-मसुदा', parawise: 'परिच्छेदनिहाय अभिप्राय (इंग्रजी)',
  affidavit: 'शपथपत्र (इंग्रजी)', lq_answer: 'विधानमंडळ प्रश्नाचे उत्तर',
};

/** Files the user uploads, with the type selector's short labels (C28; migration 0008 adds approval / court_notice). */
export const INPUT_KINDS = ['proposal', 'reply', 'approval', 'court_notice', 'extra_doc'] as const;
export type InputKind = (typeof INPUT_KINDS)[number];
export const INPUT_KIND_LABEL: Record<InputKind, string> = {
  proposal: 'प्रस्ताव', reply: 'उत्तर', approval: 'मान्यता', court_notice: 'न्यायालयीन नोटीस', extra_doc: 'इतर',
};

/** "कोणते मसुदे हवेत?" (C28) — keys in the Worker's fixed order (DRAFT_KEYS); stored in runs.outputs.
 *  04.11.2026: do_letter … lq appended (same order in cloudflare/worker.js and tools/engine_supabase.py). */
export const DRAFT_KEYS = [
  'letter', 'reminder', 'gr', 'corrigendum', 'circular', 'memo', 'notification', 'parawise',
  'do_letter', 'uo_note', 'endorsement', 'office_order', 'press_note', 'addendum', 'affidavit', 'lq',
] as const;
export type DraftKey = (typeof DRAFT_KEYS)[number];
export const DRAFT_LABEL: Record<DraftKey, string> = {
  letter: 'पत्र', reminder: 'स्मरणपत्र', gr: 'शासन निर्णय', corrigendum: 'शुद्धिपत्रक', circular: 'परिपत्रक', memo: 'ज्ञापन',
  notification: 'अधिसूचना', parawise: 'परिच्छेदनिहाय उत्तर',
  do_letter: 'अर्धशासकीय पत्र', uo_note: 'अनौपचारिक संदर्भ नोंद', endorsement: 'पृष्ठांकन', office_order: 'कार्यालयीन आदेश',
  press_note: 'प्रसिद्धीपत्रक', addendum: 'पूरकपत्र', affidavit: 'शपथपत्र', lq: 'विधानमंडळ प्रश्नाचे उत्तर',
};
/** Picker groups (phone layout: a short heading per group). Every DRAFT_KEYS key is in exactly one group. */
export const DRAFT_GROUPS: { label: string; keys: readonly DraftKey[] }[] = [
  { label: 'पत्रे', keys: ['letter', 'reminder', 'do_letter', 'uo_note'] },
  { label: 'आदेश', keys: ['gr', 'corrigendum', 'circular', 'memo', 'notification', 'endorsement', 'office_order', 'press_note', 'addendum'] },
  { label: 'न्यायालय / विधिमंडळ', keys: ['parawise', 'affidavit', 'lq'] },
];
/** Labels of a runs.outputs value: null = legacy run (nothing shown), [] = note only. */
export function draftsText(v: unknown): string {
  if (!Array.isArray(v)) return '';
  const l = DRAFT_KEYS.filter(k => v.includes(k)).map(k => DRAFT_LABEL[k]);
  return l.length ? l.join(', ') : 'फक्त नोंद';
}

/** Optional engine outputs (02.11.2026, migration 0006; affidavit / lq_answer 04.11.2026, migration 0010): shown with the
 *  note when the engine produced them. */
export const EXTRA_OUTPUT_KINDS = ['order_draft', 'parawise', 'affidavit', 'lq_answer'] as const;

export const ACTION_LABEL: Record<string, string> = {
  case_created: 'प्रकरण नोंदवले', case_updated: 'तपशील बदलला', file_uploaded: 'फाइल अपलोड', run_started: 'अभ्यास सुरू',
  stage_changed: 'टप्पा बदलला', letter_saved: 'पत्र नोंदवले', letter_updated: 'पत्राची नोंद बदलली', letter_reply_received: 'पत्राचे उत्तर प्राप्त',
  run_done: 'अभ्यास पूर्ण', run_failed: 'अभ्यास अयशस्वी', run_warning: 'अभ्यास-सूचना',
  case_cr_duplicate: 'C R आधीच दुसऱ्या प्रकरणात', case_filled_from_pdf: 'तपशील PDF वरून भरला', case_fill_skipped: 'PDF वरून तपशील भरता आला नाही',
};

/** Marathi names of case / letter fields (History details, Settings errors). */
export const FIELD_LABEL: Record<string, string> = {
  cr_no: 'C R क्र.', cr_year: 'वर्ष', cr: 'C R', file_no: 'नस्ती क्र.', subject: 'विषय', category: 'प्रवर्ग', priority: 'प्राधान्य',
  employee_name: 'कर्मचारी', post: 'पद', office: 'कार्यालय', received_from: 'कोणाकडून प्राप्त', received_via: 'मार्ग',
  inward_date: 'आवक दिनांक', due_date: 'मुदत', ref_no: 'पत्र क्र.', addressed_to: 'कोणाला', sent_date: 'पाठवल्याचा दिनांक',
  reply_due: 'उत्तराची मुदत', reply_received_date: 'उत्तर प्राप्त दिनांक', status: 'स्थिती', stage: 'टप्पा',
};
