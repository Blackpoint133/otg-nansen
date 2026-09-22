# Operations

The reference OTG deployment uses Windows services wrapped by NSSM, with
separate importer, indexer, overview, and Streamlit roles. Logs are kept in
the existing OTG logging layout and scheduled tasks are used for selected
staging and refresh jobs. No Nansen service or scheduled task exists.

Future Nansen work should remain a foreground, bounded, read-only validated
process until its persistence and retry behavior are reviewed. No operational
component was added in Phase 0B.

The proposed persistence interface is driver-neutral and tested with an
in-memory checkpoint double. A later implementation must use parameterized
queries, record ingestion status, and advance checkpoints only after complete
successful ingestion. No PostgreSQL connection or migration is part of the
current project.

Each future ingestion run must retain token and request scope; flow ingestion
requires a non-empty flow label. The audit start and final audit update are
durable operations separate from the data transaction. Normalized rows and
their scoped checkpoint commit together, while a failed or partial run rolls
back both and records failure in the already-created audit row. Success status
is staged with data and checkpoint, removing the post-commit running-state
window. The migration remains review-only and NOT APPLIED.
The guarded staging command is `python -m otg_nansen.migrate_staging`; it
refuses any database other than `server_otg_staging`. PostgreSQL integration
tests are opt-in with `NANSEN_RUN_POSTGRES_TESTS=1`; default pytest remains
database-free.
