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

Each future ingestion run must retain token and request scope, including the
flow label when applicable. A failed or partial transaction must not advance
the corresponding scoped checkpoint. The migration remains review-only.
