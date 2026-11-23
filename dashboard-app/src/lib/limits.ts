/** Upload size limit. The page (claude.ai artifact build) stores a file over 19 MiB as base64 parts of 14.4 MB, so it
 *  takes up to 100 MB (Abhi, 23.11.2026: "file upload capacity 100 mb kra"); the Supabase build keeps 50 MB (bucket
 *  file_size_limit, supabase/migrations init.sql, and cloudflare/worker.js MAX_UPLOAD). */
export const UPLOAD_MAX_MB = import.meta.env.VITE_BACKEND === 'artifact' ? 100 : 50;
export const UPLOAD_MAX_BYTES = UPLOAD_MAX_MB * 1024 * 1024;
