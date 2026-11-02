-- Single-use run token for /api/engine/config, made atomic in Postgres (docs/QUALITY_AUDIT.md §7, M).
-- The Worker sets config_taken_at with a conditional PATCH (… &config_taken_at=is.null); only one request gets the row.
-- Until this migration is applied, the Worker falls back to its KV flag alone.
alter table runs add column if not exists config_taken_at timestamptz;
