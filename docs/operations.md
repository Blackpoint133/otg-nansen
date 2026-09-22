# Operations

The reference OTG deployment uses Windows services wrapped by NSSM, with
separate importer, indexer, overview, and Streamlit roles. Logs are kept in
the existing OTG logging layout and scheduled tasks are used for selected
staging and refresh jobs. No Nansen service or scheduled task exists.

Future Nansen work should remain a foreground, bounded, read-only validated
process until its persistence and retry behavior are reviewed. No operational
component was added in Phase 0B.

The persistence interface uses parameterized psycopg3 queries, records
ingestion status, and advances checkpoints only after complete successful
ingestion. The reviewed schema is deployed to staging only; production is not
connected for writes.

Each future ingestion run must retain token and request scope; flow ingestion
requires a non-empty flow label. The audit start and final audit update are
durable operations separate from the data transaction. Normalized rows and
their scoped checkpoint commit together, while a failed or partial run rolls
back both and records failure in the already-created audit row. Success status
is staged with data and checkpoint, removing the post-commit running-state
window. The migration was review-only until Task 013A applied it to
`server_otg_staging`; production remains NOT APPLIED. The owner intentionally
retains CREATE for `gunz_user` on staging as a persistent staging-only
privilege. PostgreSQL integration tests are opt-in with
`NANSEN_RUN_POSTGRES_TESTS=1`; the validated suite leaves no synthetic rows.
The guarded staging command is `python -m otg_nansen.migrate_staging`; it
refuses any database other than `server_otg_staging`. PostgreSQL integration
tests are opt-in with `NANSEN_RUN_POSTGRES_TESTS=1`; default pytest remains
database-free.
The checkpoint API does not accept caller-authoritative status flags. It
requires a staged successful run with matching stream identity, and rejects
zero-row eligibility. Flow scopes use separate successful runs and checkpoints
for each stream. Task 013B validated these behaviors against staging.
