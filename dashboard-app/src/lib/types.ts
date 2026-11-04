export type Role = 'owner' | 'staff' | 'senior';
/** Per-user profile (Worker GET/PATCH /api/me; '' when empty). Absent on a Worker without the profile migration. */
export interface Profile { display_name: string; designation: string; office: string; mine: string }
export interface Me { id: string; email: string; role: Role | null; profile?: Profile }

export interface Case {
  id: number; cr_no: string | null; cr_year: number | null; file_no: string | null; subject: string | null; category: string;
  employee_name: string | null; post: string | null; office: string | null; received_from: string | null;
  received_via: string | null; inward_date: string | null; stage: string; priority: string;
  due_date: string | null; assigned_to: string | null; created_at: string; updated_at: string;
  // migration 20261103000009_case_desk.sql: desk profile id (DESKS); null / absent = law-desk6
  desk?: string | null;
  // migration 20261104000011_work_type_queue.sql: work category (WORK_TYPES); null / absent = service
  work_type?: string | null;
  // eOffice नस्ती no. linking the case to a row of the नस्ती अद्ययावत स्थिती page (nasti_dash_v1.rows[].fileNo); absent on old DB
  nasti_no?: string | null;
}
export interface CaseFile {
  id: number; case_id: number; kind: string; storage_path: string; original_name: string;
  version: number; uploaded_by: string | null; created_at: string;
}
export interface Run {
  id: number; case_id: number; state: 'queued' | 'running' | 'done' | 'failed'; step: string | null;
  started_at: string | null; finished_at: string | null; instructions: string | null; log_url: string | null;
  summary: string | null; letter_needed: boolean | null; essential_points: unknown; grs_attached: unknown;
  grs_missing: unknown; created_by: string | null; created_at: string;
  // migration 20261101000004_reliability.sql (numeric may arrive as string)
  cost_usd?: number | string | null; num_turns?: number | null; duration_s?: number | string | null; warnings?: unknown;
  // migration 20261102000007_run_last_step.sql: last progress text before the run ended (red marker of a failed run)
  last_step?: string | null;
  // migration 20261103000008_run_outputs.sql: drafts ticked for this run (DraftKey[]); null = legacy (engine decided)
  outputs?: string[] | null;
  // migration 20261104000011_work_type_queue.sql: when the Worker sent this run to the engine; null = waiting in the queue
  dispatched_at?: string | null;
  // migration 20261104000013_draft_edits.sql (docs/DRAFT_EDIT_DESIGN.md): 'edit' = a सुधारणा-चॅट run; absent / null = 'full'
  kind?: 'full' | 'edit' | null;
  edit_target?: string | null;
  edit_message?: string | null;
  edit_result?: EditResult | null;
  /** Addendum A: case_files ids attached to the edit message (if the Worker stores them) */
  edit_attachments?: number[] | null;
}
/** runs.edit_result of an edit run (tools/edit_drafts.py). `files` = output kinds rebuilt (case_files.kind). */
export interface EditChange { where?: string | null; before?: string | null; after?: string | null }
export interface EditResult {
  summary?: string | null; changes?: EditChange[] | null; files?: string[] | null; cost_usd?: number | string | null; refused?: string | null;
  /** Addendum A: items appended to the returned PDF */
  attached?: { title?: string | null; pages?: string | number | null }[] | null;
  /** parts of the message that could not be done in this edit (the rest was done) */
  notes?: string[] | null;
}
export interface Letter {
  id: number; case_id: number; ref_no: string | null; addressed_to: string | null; sent_date: string | null;
  reply_due: string | null; reply_received_date: string | null; status: string; created_at: string;
}
export interface GrRow {
  code: string; date: string | null; department: string | null; title: string | null;
  storage_path: string | null; source_url: string | null; used_in_cases: number[] | null;
}
export interface Activity {
  id: number; case_id: number | null; actor: string | null; action: string;
  detail: Record<string, unknown> | null; at: string;
}
export interface Member { user_id: string; email: string; role: Role; created_at: string }
