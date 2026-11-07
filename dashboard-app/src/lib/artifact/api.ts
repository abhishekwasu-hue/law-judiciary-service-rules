// Artifact build: in-page replacements for the Cloudflare Worker's /api/* endpoints (cloudflare/worker.js), over the
// `db`, `assets`, `downloads` and `mcp` capabilities. Responses and error shapes follow worker.js closely enough for the
// UI (ApiError(status, error, body) exactly as lib/api.ts builds it from a Worker answer).
//
// Hidden / harmless in this build (owner / infra only — nothing to configure inside a claude.ai page):
//   GET/PUT /api/settings (API keys, models, budgets, GitHub, Supabase) → {} / {ok:true}, nothing stored;
//   POST /api/members → Marathi refusal (people are added through the page's share menu);
//   /api/setup → already configured; /api/runs/sweep → no-op; /api/spend → this month's runs.cost_usd, limit $1000,
//   nothing reserved, max_parallel 1; /api/engine/* → not served (the cloud worker writes the db directly);
//   monthly budget gate (402) and the GitHub/AI-key "Settings" gate (412) → never refused.
import { ApiError } from '../api';
import { DESKS, WORK_TYPES } from '../constants';
import { cap, needDb, nowIso } from './runtime';
import { getRow, grFiles, grStoragePath, insertRow, listRows, patchRow, setActor, viewer, type GrFile, type Row } from './db';

// ---------- texts (same as worker.js) ----------
const CASE_FIELDS = ['cr_no', 'cr_year', 'file_no', 'subject', 'category', 'priority', 'employee_name', 'post', 'office', 'received_from', 'received_via', 'inward_date', 'due_date', 'desk', 'work_type', 'nasti_no'];
const DESK_IDS: readonly string[] = DESKS.map(d => d.id);
const WORK_IDS: readonly string[] = WORK_TYPES.map(w => w.id);
const BAD_DESK = 'विभाग / कार्यासन योग्य नाही. कृपया यादीतील पर्याय निवडावा, ही विनंती.';
const BAD_WORK_TYPE = 'कामाची श्रेणी योग्य नाही. कृपया यादीतील पर्याय निवडावा, ही विनंती.';
const NASTI_NO_MAX = 100;
const BAD_NASTI_NO = `नस्ती क्रमांक योग्य नाही. कृपया तो जास्तीत जास्त ${NASTI_NO_MAX} अक्षरांत नमूद करावा, ही विनंती.`;
const PROFILE_KEYS = ['display_name', 'designation', 'office', 'mine'] as const;
const PROFILE_MAX = 120;
const PROFILE_LABELS: Record<string, string> = { display_name: 'नाव', designation: 'पदनाम', office: 'कार्यालय', mine: 'आपल्याकडे असलेले स्थान' };
const FILE_KINDS = ['proposal', 'extra_doc', 'reply', 'approval', 'court_notice', 'gr'];
const DRAFT_KEYS = ['letter', 'reminder', 'gr', 'corrigendum', 'circular', 'memo', 'notification', 'parawise',
  'do_letter', 'uo_note', 'endorsement', 'office_order', 'press_note', 'addendum', 'affidavit', 'lq'];
const BAD_OUTPUTS = 'मसुद्यांची निवड योग्य नाही. कृपया पान पुन्हा उघडून निवड करावी, ही विनंती.';
const LETTER_STATUS = ['मसुदा', 'पाठवले', 'उत्तर प्राप्त', 'स्मरणपत्र'];
const MAX_UPLOAD = 50 * 1024 * 1024;
const UPLOAD_TYPES: Record<string, string> = { '.pdf': 'application/pdf', '.doc': 'application/msword',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.tif': 'image/tiff', '.tiff': 'image/tiff' };
const BAD_FILE_TYPE = 'हा फाइल-प्रकार स्वीकारता येत नाही. कृपया PDF, Word (DOC / DOCX) किंवा प्रतिमा (JPG / PNG / TIF) फाइल जोडावी, ही विनंती.';
const CLOSED_STAGE = 'बंद';
const CASE_CLOSED = 'हे प्रकरण बंद आहे. प्रक्रिया सुरू करण्यापूर्वी कृपया प्रकरणाचा टप्पा बदलावा, ही विनंती.';
const EDIT_TARGETS = ['note', 'letter', 'order', 'parawise', 'affidavit', 'lq', 'package'];
const EDIT_MSG_MAX = 2000;
const EDIT_ATTACH_MAX = 5;
const EDIT_ATTACH_KINDS = ['gr', 'extra_doc', 'reply', 'approval', 'court_notice'];
const NO_SPEC = "हे प्रकरण या सुविधेपूर्वीचे असल्याने सुधारणा-फाइल उपलब्ध नाही. कृपया 'पुन्हा तयार करा' हा पर्याय वापरावा, ही विनंती.";
const BAD_EDIT_TARGET = 'सुधारणा कोठे करावयाची हे यादीतील पर्यायांतून कृपया निवडावे, ही विनंती.';
const EDIT_MSG_EMPTY = 'कृपया सुधारणा-संदेश नमूद करावा, ही विनंती.';
const EDIT_MSG_LONG = `कृपया सुधारणा-संदेश ${EDIT_MSG_MAX} अक्षरांच्या मर्यादेत नमूद करावा, ही विनंती.`;
const BAD_ATTACH = `जोडलेल्या फाइल चुकीच्या — या प्रकरणाच्या जास्तीत जास्त ${EDIT_ATTACH_MAX} फाइल (GR / इतर कागदपत्र / उत्तर / मान्यता / नोटीस) कृपया जोडाव्यात, ही विनंती.`;
const STALE_MS = 3.5 * 3600 * 1000;
// artifact-only texts
const FIRE_FAILED = 'प्रक्रिया प्रतीक्षा-यादीत नोंदवली आहे; मात्र काम सुरू करणारी सेवा आत्ता सुरू करता आली नाही. ती सुरू झाल्यावर ही प्रक्रिया क्रमाने होईल. कृपया थोड्या वेळाने पुन्हा प्रयत्न करावा, ही विनंती.';
const GR_REQUESTED = 'हा GR या पानावर अजून उपलब्ध नाही. तो मागविण्याची नोंद केली आहे; थोड्या वेळाने पुन्हा उघडावा, ही विनंती.';
const GR_BAD_CODE = 'सांकेतांक 16 ते 20 अंकी असावा. कृपया योग्य सांकेतांक नमूद करावा, ही विनंती.';
const SEARCH_MISSING = 'नियम-उतारे शोधाची सूची या पानावर अजून जोडलेली नाही. कृपया मालकांना कळवावे, ही विनंती.';
const MEMBERS_HERE = 'या पानावर सदस्य पानाच्या "शेअर" पर्यायातून जोडावेत, ही विनंती.';

const fail = (status: number, error: string, extra: Row = {}): never => { throw new ApiError(status, error, { error, ...extra }); };
const bad = (msg: string, s = 400): never => fail(s, msg);
const isId = (v: unknown) => /^\d+$/.test(String(v ?? ''));
const istToday = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });

async function me(): Promise<string> {
  const v = await viewer();
  setActor(v.id);
  return v.id;
}
async function log(case_id: unknown, action: string, detail: Row = {}) {
  await insertRow('activity', { case_id: case_id ?? null, actor: await me(), action, detail });
}
async function caseRow(id: unknown): Promise<Row | null> {
  return isId(id) ? getRow('cases', Number(id)) : null;
}
async function setStage(c: Row, stage: string) {
  if (c.stage !== stage) await patchRow('cases', c, { stage });
}

// ---------- worker trigger (cloud worker processes queued runs / GR requests) ----------
/** mcp fire_trigger with meta/config.trigger_id. Resolves null on success, else a short technical reason. */
async function fireWorker(): Promise<string | null> {
  try {
    const db = await needDb();
    const id = (await db.doc('meta/config').get()).data()?.trigger_id;
    if (typeof id !== 'string' || !id) return 'meta/config.trigger_id missing';
    const mcp = await cap('mcp');
    if (!mcp) return 'mcp capability unavailable';
    await mcp.callTool('Claude Code Remote', 'fire_trigger', { trigger_id: id });
    return null;
  } catch (e) {
    const x = e as { code?: string; message?: string };
    return `${x?.code || 'error'}: ${String(x?.message || e).slice(0, 200)}`;
  }
}

// ---------- /api/me ----------
const profileOf = (r: Row | null) => Object.fromEntries(PROFILE_KEYS.map(k => [k, r && r[k] != null ? String(r[k]) : ''])) as Record<(typeof PROFILE_KEYS)[number], string>;
async function ownerRow(): Promise<Row> {
  const v = await viewer();
  setActor(v.id);
  let m = await getRow('members', v.id);
  if (!m) m = await insertRow('members', { user_id: v.id, email: v.email || 'owner', role: 'owner', display_name: v.name || null });
  else if (m.role !== 'owner') m = await patchRow('members', m, { role: 'owner' });
  return m;
}
async function getMe() {
  const v = await viewer();
  let m: Row | null = null;
  try { m = await ownerRow(); } catch { /* db unavailable: the page still opens as the owner */ }
  return { id: v.id, email: v.email, role: 'owner' as const, profile: profileOf(m) };
}
async function patchMe(b: unknown) {
  if (!b || typeof b !== 'object' || Array.isArray(b)) bad('माहिती पाठवली नाही');
  const body = b as Row, row: Row = {};
  for (const k of PROFILE_KEYS) {
    if (!(k in body)) continue;
    const v = body[k];
    if (v !== null && typeof v !== 'string') bad(`${PROFILE_LABELS[k]}: मजकूर असावा`);
    const t = String(v || '').trim();
    if (t.length > PROFILE_MAX) bad(`${PROFILE_LABELS[k]}: जास्तीत जास्त ${PROFILE_MAX} अक्षरे`);
    row[k] = t || null;
  }
  if (!Object.keys(row).length) bad('बदलण्यासाठी माहिती नाही');
  const m = await patchRow('members', await ownerRow(), row);
  const v = await viewer();
  return { id: v.id, email: v.email, role: 'owner', profile: profileOf(m) };
}

// ---------- cases ----------
function cleanNastiNo(row: Row): boolean {
  const v = row.nasti_no;
  if (v === null) return true;
  if (typeof v !== 'string') return false;
  const t = v.trim();
  if (t.length > NASTI_NO_MAX) return false;
  row.nasti_no = t || null;
  return true;
}
async function findCrDup(crNo: unknown, crYear: unknown, exceptId: number | null = null): Promise<number | null> {
  if (crNo == null || crNo === '' || crYear == null || crYear === '') return null;
  const n = String(crNo).trim().replace(/^0+(?=\d)/, '');
  const re = new RegExp(`^0*${n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`);
  const hit = (await listRows('cases'))
    .filter(c => re.test(String(c.cr_no ?? '')) && String(c.cr_year ?? '') === String(crYear).trim() && Number(c.id) !== exceptId)
    .sort((a, b) => Number(a.id) - Number(b.id));
  return hit.length ? Number(hit[0].id) : null;
}
function checkCaseRow(row: Row) {
  if (row.desk != null && !DESK_IDS.includes(String(row.desk))) bad(BAD_DESK);
  if (row.work_type != null && !WORK_IDS.includes(String(row.work_type))) bad(BAD_WORK_TYPE);
  if ('nasti_no' in row && !cleanNastiNo(row)) bad(BAD_NASTI_NO);
}
async function createCase(b: Row) {
  if (b.cr_no && !/^\d+$/.test(String(b.cr_no))) bad('cr_no: digits only');
  if (b.cr_year && !/^\d{4}$/.test(String(b.cr_year))) bad('cr_year: 4 digits');
  const row: Row = Object.fromEntries(CASE_FIELDS.filter(k => b[k] !== undefined && b[k] !== '').map(k => [k, b[k]]));
  checkCaseRow(row);
  if (row.nasti_no === null) delete row.nasti_no;
  if (row.cr_year != null) row.cr_year = Number(row.cr_year);
  const dup = await findCrDup(row.cr_no, row.cr_year);
  if (dup !== null) fail(409, 'duplicate_cr', { existing_id: dup });
  const c = await insertRow('cases', row);
  await log(c.id, 'case_created', { cr: c.cr_no ? `${c.cr_no}/${c.cr_year || ''}` : '' });
  return c;
}
async function updateCase(id: number, b: unknown) {
  if (!b || typeof b !== 'object') bad('body required');
  const body = b as Row;
  const row: Row = Object.fromEntries(CASE_FIELDS.filter(k => k in body).map(k => [k, body[k] === '' || body[k] === undefined ? null : body[k]]));
  if (!Object.keys(row).length) bad('nothing to change');
  if ('subject' in row && row.subject === null) row.subject = '';
  if (row.cr_no != null && !/^\d+$/.test(String(row.cr_no).trim())) bad('cr_no: digits only');
  if (row.cr_year != null && !/^\d{4}$/.test(String(row.cr_year).trim())) bad('cr_year: 4 digits');
  checkCaseRow(row);
  if (row.cr_no != null) row.cr_no = String(row.cr_no).trim();
  if (row.cr_year != null) row.cr_year = Number(String(row.cr_year).trim());
  const cur = await caseRow(id);
  if (!cur) return bad('case not found', 404);
  const crNo = 'cr_no' in row ? row.cr_no : cur.cr_no, crYear = 'cr_year' in row ? row.cr_year : cur.cr_year;
  const crChanged = ('cr_no' in row || 'cr_year' in row) && (String(crNo ?? '') !== String(cur.cr_no ?? '') || String(crYear ?? '') !== String(cur.cr_year ?? ''));
  if (crChanged) {
    const dup = await findCrDup(crNo, crYear, id);
    if (dup !== null) fail(409, 'duplicate_cr', { existing_id: dup });
  }
  const c = await patchRow('cases', cur, row);
  await log(id, 'case_updated', { fields: Object.keys(row), ...(crChanged ? { cr: crNo ? `${crNo}/${crYear || ''}` : '' } : {}) });
  return c;
}

// ---------- runs ----------
const isActive = (r: Row) => (r.state === 'queued' || r.state === 'running')
  && (r.dispatched_at == null || Date.now() - Date.parse(String(r.dispatched_at)) < STALE_MS || Date.now() - Date.parse(String(r.created_at)) < STALE_MS);
async function activeRun(caseId: number): Promise<Row | null> {
  const act = (await listRows('runs')).filter(r => Number(r.case_id) === caseId && isActive(r)).sort((a, b) => Number(b.id) - Number(a.id));
  return act[0] || null;
}
/** Fire the worker for a queued run: success → dispatched_at set (+ full run: case stage, run_started), else the row
 *  stays queued (dispatched_at null; the worker takes it on its next firing) and a Marathi error is thrown. */
async function dispatch(run: Row, c: Row, started: Row | null): Promise<Row> {
  const why = await fireWorker();
  if (why) {
    await log(run.case_id, 'run_dispatch_failed', { run_id: run.id, error: why });
    fail(502, 'trigger_failed', { reason: FIRE_FAILED, detail: why, run_id: run.id });
  }
  const fresh = (await getRow('runs', run.id)) || run;
  const next = await patchRow('runs', fresh, { dispatched_at: nowIso() });
  if (started) {
    await setStage(c, 'अभ्यास चालू');
    await log(run.case_id, 'run_started', started);
  }
  return next;
}
async function startRun(b: Row) {
  const { case_id, instructions, outputs } = b;
  if (!isId(case_id)) bad('case_id required');
  const caseId = Number(case_id);
  let outs: string[] | null = null;
  if (outputs !== undefined && outputs !== null) {
    if (!Array.isArray(outputs) || outputs.length > 32 || outputs.some(k => typeof k !== 'string' || !DRAFT_KEYS.includes(k))) bad(BAD_OUTPUTS);
    outs = DRAFT_KEYS.filter(k => (outputs as string[]).includes(k));
  }
  const c = await caseRow(caseId);
  if (c && c.stage === CLOSED_STAGE) fail(409, 'case_closed', { reason: CASE_CLOSED });
  const files = await listRows('case_files');
  if (!files.some(f => Number(f.case_id) === caseId && f.kind === 'proposal')) bad('upload the proposal PDF first');
  if (!c) return bad('case not found', 404);
  const active = await activeRun(caseId);
  if (active) {
    // a run left waiting by a failed firing: fire again instead of refusing (the user's retry)
    if (active.state === 'queued' && active.dispatched_at == null && active.kind !== 'edit') {
      const r = await dispatch(active, c, { run_id: active.id, instructions: active.instructions || '', outputs: active.outputs ?? null });
      return { ...r, queued: false };
    }
    fail(409, 'run_active', { run_id: active.id });
  }
  const run = await insertRow('runs', { case_id: caseId, instructions: instructions || null, created_by: await me(), outputs: outs, kind: 'full' });
  const r = await dispatch(run, c, { run_id: run.id, instructions: instructions || '', outputs: outs });
  return { ...r, queued: false };
}
async function startEdit(b: unknown) {
  if (!b || typeof b !== 'object' || Array.isArray(b)) bad('माहिती पाठवली नाही');
  const body = b as Row;
  if (!isId(body.case_id)) bad('case_id required');
  const caseId = Number(body.case_id);
  if (!EDIT_TARGETS.includes(String(body.target))) bad(BAD_EDIT_TARGET);
  const c = await caseRow(caseId);
  if (c && c.stage === CLOSED_STAGE) fail(409, 'case_closed', { reason: CASE_CLOSED });
  if (typeof body.message !== 'string' || !body.message.trim()) bad(EDIT_MSG_EMPTY);
  const message = String(body.message).trim();
  if (message.length > EDIT_MSG_MAX) bad(EDIT_MSG_LONG);
  const files = (await listRows('case_files')).filter(f => Number(f.case_id) === caseId);
  let attachments: number[] = [];
  if (body.attachments !== undefined && body.attachments !== null) {
    const a = body.attachments;
    if (!Array.isArray(a) || a.length > EDIT_ATTACH_MAX || a.some(x => (typeof x !== 'number' && typeof x !== 'string') || !isId(x))) bad(BAD_ATTACH);
    attachments = [...new Set((a as unknown[]).map(Number))];
    const rows = files.filter(f => attachments.includes(Number(f.id)));
    if (rows.length !== attachments.length || rows.some(r => !EDIT_ATTACH_KINDS.includes(String(r.kind)))) bad(BAD_ATTACH);
  }
  if (!files.some(f => f.kind === 'spec' && f.original_name === 'spec.json')) fail(409, 'no_spec', { reason: NO_SPEC });
  if (!c) return bad('case not found', 404);
  const active = await activeRun(caseId);
  if (active) fail(409, 'run_active', { run_id: active.id });
  const run = await insertRow('runs', { case_id: caseId, kind: 'edit', edit_target: body.target, edit_message: message, edit_attachments: attachments, created_by: await me() });
  const r = await dispatch(run, c, null);
  await log(caseId, 'edit_requested', { run_id: run.id, target: body.target, message, attachments });
  return { ...r, kind: 'edit' };
}
async function spend() {
  const month = new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 7);
  const monthOf = (iso: unknown) => new Date(Date.parse(String(iso)) + 5.5 * 3600 * 1000).toISOString().slice(0, 7);
  let runs: Row[] = [];
  try { runs = await listRows('runs'); } catch { /* db unavailable */ }
  const mine = runs.filter(r => r.created_at && monthOf(r.created_at) === month);
  const spent = mine.reduce((s, r) => s + (Number(r.cost_usd) || 0), 0);
  return { month, spent_usd: Math.round(spent * 100) / 100, limit_usd: 1000, runs: mine.filter(r => r.kind !== 'edit').length,
    reserved_usd: 0, active_runs: runs.filter(r => r.state === 'queued' || r.state === 'running').length, max_parallel: 1 };
}

// ---------- letters ----------
async function createLetter(b: Row) {
  const row: Row = Object.fromEntries(['case_id', 'ref_no', 'addressed_to', 'sent_date', 'reply_due', 'status'].filter(k => b[k]).map(k => [k, b[k]]));
  if (!isId(row.case_id)) bad('case_id required');
  row.case_id = Number(row.case_id);
  if (row.status && !LETTER_STATUS.includes(String(row.status))) bad(`status: one of ${LETTER_STATUS.join(', ')}`);
  const c = await caseRow(row.case_id);
  if (!c) return bad('case not found', 404);
  const l = await insertRow('letters', row);
  if (row.sent_date) await setStage(c, 'पत्र पाठवले (माहिती प्रतीक्षेत)');
  await log(row.case_id, 'letter_saved', row);
  return l;
}
async function updateLetter(id: number, b: Row) {
  const row: Row = Object.fromEntries(['ref_no', 'addressed_to', 'sent_date', 'reply_due', 'reply_received_date', 'status'].filter(k => k in b).map(k => [k, b[k] || null]));
  if ('status' in row && !LETTER_STATUS.includes(String(row.status))) bad(`status: one of ${LETTER_STATUS.join(', ')}`);
  const cur = await getRow('letters', id);
  if (!cur) return bad('not found', 404);
  const l = await patchRow('letters', cur, row);
  if (row.sent_date) { const c = await caseRow(l.case_id); if (c) await setStage(c, 'पत्र पाठवले (माहिती प्रतीक्षेत)'); }
  await log(l.case_id, 'letter_updated', { letter_id: l.id, ...row });
  return l;
}

// ---------- files: assets, or base64 text parts ----------
const ASSET_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const DIRECT_MAX = 19 * 1024 * 1024;
const PART_RAW = 3 * 4_800_000;   // 14.4 MB raw → 19.2 MB of base64 text per part (asset limit 20 MiB)
function magicOk(ext: string, b: Uint8Array): boolean {
  const sw = (sig: number[], at = 0) => sig.every((x, i) => b[at + i] === x);
  const asc = (s: string) => [...s].map(c => c.charCodeAt(0));
  if (ext === '.pdf') { const p = asc('%PDF-'); for (let i = 0; i + p.length <= b.length; i++) if (sw(p, i)) return true; return false; }
  if (ext === '.doc') return sw([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1]) || sw(asc('{\\rtf'));
  if (ext === '.docx') return sw([0x50, 0x4B, 0x03, 0x04]);
  if (ext === '.jpg' || ext === '.jpeg') return sw([0xFF, 0xD8, 0xFF]);
  if (ext === '.png') return sw([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
  if (ext === '.tif' || ext === '.tiff') return sw([0x49, 0x49, 0x2A, 0x00]) || sw([0x4D, 0x4D, 0x00, 0x2A]);
  return false;
}
const b64Of = (blob: Blob) => new Promise<string>((res, rej) => {
  const fr = new FileReader();
  fr.onload = () => res(String(fr.result).replace(/^data:[^,]*,/, ''));
  fr.onerror = () => rej(fr.error || new Error('read failed'));
  fr.readAsDataURL(blob);
});
function bytesOfB64(s: string): Uint8Array {
  const bin = atob(s.trim());
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
/** Stores a blob: {asset_id} for an accepted type ≤ 19 MiB, else {asset_parts: [ids]} (base64 text/plain parts). */
export async function storeBlob(blob: Blob, ctype: string, onProgress?: (pct: number) => void): Promise<{ asset_id: string | null; asset_parts: string[] | null; storage_path: string }> {
  const assets = await cap('assets');
  if (!assets) throw new Error('storage 503 assets unavailable');
  onProgress?.(1);
  if (ASSET_TYPES.includes(ctype) && blob.size <= DIRECT_MAX) {
    const r = await assets.upload(blob, { type: ctype }).catch((e: { code?: string; message?: string }) => { throw new Error(`storage 500 ${e?.code || ''} ${e?.message || ''}`); });
    onProgress?.(100);
    return { asset_id: r.id, asset_parts: null, storage_path: `asset:${r.id}` };
  }
  const parts: string[] = [];
  const n = Math.max(1, Math.ceil(blob.size / PART_RAW));
  for (let i = 0; i < n; i++) {
    const text = await b64Of(blob.slice(i * PART_RAW, (i + 1) * PART_RAW));
    const r = await assets.upload(new Blob([text], { type: 'text/plain' }), { type: 'text/plain' }).catch((e: { code?: string; message?: string }) => { throw new Error(`storage 500 ${e?.code || ''} ${e?.message || ''}`); });
    parts.push(r.id);
    onProgress?.(Math.round(((i + 1) / n) * 100));
  }
  return { asset_id: null, asset_parts: parts, storage_path: `asset-parts:${parts.length}` };
}
async function partsBytes(ids: string[]): Promise<Uint8Array> {
  const chunks: Uint8Array[] = [];
  for (const id of ids) {
    const r = await fetch(`/_blob/${id}`);
    if (!r.ok) throw new ApiError(r.status, `sign ${r.status}`);
    chunks.push(bytesOfB64(await r.text()));
  }
  const out = new Uint8Array(chunks.reduce((s, c) => s + c.length, 0));
  let at = 0;
  for (const c of chunks) { out.set(c, at); at += c.length; }
  return out;
}
/** Pointer of a stored file: one asset id, or the list of base64 parts. storage_path "asset:<id>" is enough on its own. */
function pointer(r: Row): { id?: string; parts?: string[] } | null {
  if (Array.isArray(r.asset_parts) && r.asset_parts.length) return { parts: r.asset_parts.map(String) };
  if (typeof r.asset_id === 'string' && r.asset_id) return { id: r.asset_id };
  const m = /^asset:([A-Za-z0-9]+)$/.exec(String(r.storage_path || ''));
  return m ? { id: m[1] } : null;
}
const ctypeOfName = (name: string) => UPLOAD_TYPES[(/\.[A-Za-z0-9]{1,8}$/.exec(name) || [''])[0].toLowerCase()] || 'application/octet-stream';
const objectUrls = new Map<string, string>();

export async function artifactUpload(caseId: number, kind: string, file: File, onProgress?: (pct: number) => void): Promise<{ id: number }> {
  const name = file.name;
  if (!caseId || !FILE_KINDS.includes(kind) || !name || /[\\/]/.test(name)) bad('case_id, kind, x-file-name required');
  if (file.size > MAX_UPLOAD) bad('file over 50 MB', 413);
  const ext = (/\.[A-Za-z0-9]{1,8}$/.exec(name) || [''])[0].toLowerCase();
  const ctype = UPLOAD_TYPES[ext];
  if (!ctype) bad(BAD_FILE_TYPE);
  const c = await caseRow(caseId);
  if (!c) return bad('case not found', 404);
  if (!magicOk(ext, new Uint8Array(await file.slice(0, 1024).arrayBuffer()))) bad(BAD_FILE_TYPE);
  const stored = await storeBlob(file, ctype, onProgress);
  const prev = (await listRows('case_files')).filter(f => Number(f.case_id) === caseId && f.kind === kind && f.original_name === name);
  const version = prev.length ? Math.max(...prev.map(f => Number(f.version) || 0)) + 1 : 1;
  const f = await insertRow('case_files', { case_id: caseId, kind, original_name: name, version, uploaded_by: await me(),
    ...stored, content_type: ctype, size_bytes: file.size });
  await log(caseId, 'file_uploaded', { kind, name, version });
  let letter_updated: unknown = null, pending_letters = 0;
  if (kind === 'reply') {
    if (c.stage === CLOSED_STAGE) await log(caseId, 'reply_on_closed_case', { name, version });
    else await setStage(c, 'माहिती प्राप्त');
    const pend = (await listRows('letters')).filter(l => Number(l.case_id) === caseId && l.sent_date != null && l.reply_received_date == null);
    pending_letters = pend.length;
    if (pend.length === 1) {
      const today = istToday();
      await patchRow('letters', pend[0], { reply_received_date: today, status: 'उत्तर प्राप्त' });
      letter_updated = pend[0].id;
      await log(caseId, 'letter_reply_received', { letter_id: letter_updated, date: today });
    }
  }
  onProgress?.(100);
  return { ...f, letter_updated, pending_letters } as unknown as { id: number };
}

/** {url, name} of a case file: "/_blob/<id>" for one asset; an object URL of the joined parts otherwise. */
export async function artifactFileUrl(id: number): Promise<{ url: string; name: string }> {
  const f = await getRow('case_files', id);
  if (!f) return bad('not found', 404);
  const name = String(f.original_name || `file-${id}`);
  const p = pointer(f);
  if (!p) throw new ApiError(404, 'sign 404');
  if (p.id) return { url: `/_blob/${p.id}`, name };
  const key = `f${id}`;
  if (!objectUrls.has(key)) {
    const bytes = await partsBytes(p.parts!);
    objectUrls.set(key, URL.createObjectURL(new Blob([bytes], { type: String(f.content_type || ctypeOfName(name)) })));
  }
  return { url: objectUrls.get(key)!, name };
}
export async function artifactFileBytes(id: number): Promise<{ data: ArrayBuffer; name: string }> {
  const f = await getRow('case_files', id);
  if (!f) return bad('not found', 404);
  const name = String(f.original_name || `file-${id}`);
  const p = pointer(f);
  if (!p) throw new ApiError(404, 'sign 404');
  if (p.parts) { const b = await partsBytes(p.parts); return { data: b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer, name }; }
  const r = await fetch(`/_blob/${p.id}`);
  if (!r.ok) throw new ApiError(r.status, `sign ${r.status}`);
  return { data: await r.arrayBuffer(), name };
}
/** Save with the original name through the `downloads` capability (viewer confirms); a plain link when it is absent
 *  or refuses the extension (e.g. .tif). Declined = nothing. */
export async function artifactDownload(id: number): Promise<void> {
  const { data, name } = await artifactFileBytes(id);
  const blob = new Blob([data], { type: ctypeOfName(name) });
  const dl = await cap('downloads');
  if (dl) {
    try {
      await dl.save({ filename: name, data: blob });
      return;
    } catch (e) {
      const code = (e as { code?: string })?.code;
      if (code === 'declined' || code === 'rate_limited') return;
    }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

// ---------- GR library ----------
async function grRequest(key: string, path: unknown, file: unknown, code: string | null) {
  const db = await needDb();
  const ref = db.doc(`gr_requests/${key}`);
  const cur = (await ref.get()).data();
  if (!cur || (cur.status !== 'pending' && cur.status !== 'processing'))
    await ref.set({ key, code, path: path ?? null, file: file ?? null, status: 'pending', at: nowIso(), by: await me() });
  return fireWorker();
}
function fileOfGr(f: GrFile | undefined): { id?: string; parts?: string[] } | null {
  if (!f || !f.ref) return null;
  return Array.isArray(f.ref) ? { parts: f.ref.map(String) } : { id: String(f.ref) };
}
async function grUrl(code: string) {
  const [rows, files] = await Promise.all([listRows('gr_library'), grFiles()]);
  const row = rows.find(r => String(r.code) === code) || rows.find(r => String(r.key) === code) || null;
  const key = String(row?.key || code);
  const p = fileOfGr(files.get(key)) || (row ? pointer(row) : null);
  if (p?.id) return { url: `/_blob/${p.id}` };
  if (p?.parts) {
    const k = `g${key}`;
    if (!objectUrls.has(k)) objectUrls.set(k, URL.createObjectURL(new Blob([await partsBytes(p.parts)], { type: 'application/pdf' })));
    return { url: objectUrls.get(k)! };
  }
  const why = await grRequest(key, row?.path, row?.file, /^\d{16,20}$/.test(code) ? code : null);
  return fail(409, 'gr_requested', { reason: GR_REQUESTED, ...(why ? { detail: why } : {}) });
}
async function addGr(b: Row) {
  const code = String(b.code ?? '');
  if (!/^\d{16,20}$/.test(code)) bad(GR_BAD_CODE);
  const [rows, files] = await Promise.all([listRows('gr_library'), grFiles()]);
  const row = rows.find(r => String(r.code) === code);
  if (row && (grStoragePath(files.get(String(row.key || code))) || pointer(row))) return { ok: true, code, source_url: row.source_url ?? null };
  const why = await grRequest(String(row?.key || code), row?.path, row?.file, code);
  return fail(409, 'gr_requested', { reason: GR_REQUESTED, ...(why ? { detail: why } : {}) });
}

// ---------- register search over meta/register_index {asset} → [{path, title, text}] ----------
interface RegDoc { path: string; title?: string; text: string }
let regIdx: Promise<RegDoc[] | null> | null = null;
function registerIndex(): Promise<RegDoc[] | null> {
  if (!regIdx) {
    regIdx = (async () => {
      const db = await needDb();
      const asset = (await db.doc('meta/register_index').get()).data()?.asset;
      if (typeof asset !== 'string' || !asset) return null;
      const r = await fetch(`/_blob/${asset}`);
      if (!r.ok) throw new Error(`search ${r.status}`);
      const j = (await r.json()) as unknown;
      return Array.isArray(j) ? (j as RegDoc[]).filter(d => d && typeof d.text === 'string') : [];
    })();
    regIdx.then(v => { if (v === null) regIdx = null; }, () => { regIdx = null; });
  }
  return regIdx;
}
/** Every term must occur (case-insensitive); score = occurrences; ≤ 2 fragments (the lines around a hit); ≤ 15 hits. */
export function searchDocs(docs: RegDoc[], q: string) {
  const terms = q.slice(0, 100).split(/\s+/).filter(t => t && !/[A-Za-z_]+:/.test(t)).map(t => t.toLowerCase());
  if (!terms.length) return [];
  const hits: { path: string; title?: string; frags: string[]; score: number }[] = [];
  for (const d of docs) {
    const low = d.text.toLowerCase();
    if (!terms.every(t => low.includes(t))) continue;
    let score = 0;
    for (const t of terms) for (let i = low.indexOf(t); i >= 0; i = low.indexOf(t, i + t.length)) score++;
    const frags: string[] = [];
    let from = 0;
    while (frags.length < 2) {
      let at = -1;
      for (const t of terms) { const i = low.indexOf(t, from); if (i >= 0 && (at < 0 || i < at)) at = i; }
      if (at < 0) break;
      const s = Math.max(0, d.text.lastIndexOf('\n', Math.max(0, at - 120)) + 1);
      let e = d.text.indexOf('\n', Math.min(d.text.length, at + 200));
      if (e < 0) e = d.text.length;
      frags.push(d.text.slice(s, Math.min(e, s + 600)));
      from = e + 1;
    }
    hits.push({ path: d.path, title: d.title, frags, score });
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 15).map(({ score: _s, ...h }) => h);
}
async function search(q: string) {
  const docs = await registerIndex();
  if (!docs) fail(503, 'search_unavailable', { reason: SEARCH_MISSING });
  return searchDocs(docs!, q);
}

// ---------- router ----------
export async function artifactApi<T>(path: string, opt: { method?: string; body?: unknown } = {}): Promise<T> {
  const M = (opt.method || (opt.body !== undefined ? 'POST' : 'GET')).toUpperCase();
  const u = new URL(path, 'https://artifact.local');
  const p = u.pathname;
  const b = (opt.body ?? {}) as Row;
  let m: RegExpExecArray | null;
  const out = await (async (): Promise<unknown> => {
    if (p === '/api/public-config') return { configured: true, supabase_url: 'artifact:', supabase_anon_key: 'artifact' };
    if (p === '/api/setup') return M === 'GET' ? { configured: true } : bad('already configured', 409);
    if (p === '/api/me') return M === 'PATCH' ? patchMe(opt.body) : getMe();
    if (p === '/api/spend' && M === 'GET') return spend();
    if (p === '/api/runs/sweep' && M === 'POST') return { ok: true, failed: [], dispatched: null };
    if (p === '/api/settings') return M === 'GET' ? {} : { ok: true };
    if (p === '/api/members' && M === 'POST') return fail(409, 'members_artifact', { reason: MEMBERS_HERE });
    if (p === '/api/cases' && M === 'POST') return createCase(b);
    if ((m = /^\/api\/cases\/(\d+)$/.exec(p)) && M === 'PATCH') return updateCase(Number(m[1]), opt.body);
    if (p === '/api/run' && M === 'POST') return startRun(b);
    if (p === '/api/edit' && M === 'POST') return startEdit(opt.body);
    if ((m = /^\/api\/files\/(\d+)$/.exec(p)) && M === 'GET') return artifactFileUrl(Number(m[1]));
    if (p === '/api/gr' && M === 'POST') return addGr(b);
    if ((m = /^\/api\/gr\/([A-Za-z0-9_-]{1,64})$/.exec(p)) && M === 'GET') return grUrl(m[1]);
    if (p === '/api/search' && M === 'GET') return search(u.searchParams.get('q') || '');
    if (p === '/api/letters' && M === 'POST') return createLetter(b);
    if ((m = /^\/api\/letters\/(\d+)$/.exec(p)) && M === 'PATCH') return updateLetter(Number(m[1]), b);
    return bad('not found', 404);
  })();
  return out as T;
}
