export type Role = 'owner' | 'staff' | 'senior';
export interface Me { id: string; email: string; role: Role | null }

export interface Case {
  id: number; cr_no: string | null; cr_year: number | null; file_no: string | null; subject: string | null; category: string;
  employee_name: string | null; post: string | null; office: string | null; received_from: string | null;
  received_via: string | null; inward_date: string | null; stage: string; priority: string;
  due_date: string | null; assigned_to: string | null; created_at: string; updated_at: string;
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
