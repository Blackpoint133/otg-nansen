-- Task 023: retain sanitized warning summaries for newly observed source pages.
ALTER TABLE nansen.ingestion_runs
    ADD COLUMN source_warnings JSONB;

ALTER TABLE nansen.ingestion_runs
    ADD CONSTRAINT ingestion_runs_source_warnings_array_check
    CHECK (source_warnings IS NULL OR jsonb_typeof(source_warnings) = 'array');
