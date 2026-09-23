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

Task 017M applied `sql/002_flow_counts_numeric.sql` to `server_otg_staging`
only. The migration changed only the two total flow count columns from BIGINT
to NUMERIC, using explicit casts. The source commit was pushed before DDL;
post-migration checks confirmed both columns are still NOT NULL, staging table
ownership is unchanged, and all five Nansen tables remain. No live Nansen data
was used. Production was not connected or modified.
The checkpoint API does not accept caller-authoritative status flags. It
requires a staged successful run with matching stream identity, and rejects
zero-row eligibility. Flow scopes use separate successful runs and checkpoints
for each stream. Task 013B validated these behaviors against staging.

Task 014 adds no service or scheduler. Its foreground orchestrator starts a
durable audit row, fetches all bounded pages outside the data transaction,
normalizes and validates the complete window, then atomically persists data,
success status, and the checkpoint. Empty complete windows advance to the
requested end; incomplete, malformed, or out-of-window source data records a
bounded failure. All Task 014 tests used fixtures or fakes, with zero live
Nansen calls.

Task 014R uses the documented array sorting form for historical requests and
does not send a standalone `order` field. Successful runs persist logical page
and API-attempt counters. If bounded pagination reaches its limit, the failure
audit retains the known fetched page and record counts while data and
checkpoints remain unchanged.

Task 018 attempted exactly one live Avalanche `$GUN` flow request with retries
disabled and the configured three-call maximum. The request timed out on that
first attempt. The durable run was marked failed, and independent staging
verification found no flow rows or checkpoint for the target window. No retry
or persistence followed. The failed audit is intentionally retained; another
live attempt requires separate authorization.

Task 018R was subsequently authorized as a separate single-run retry. With a
60-second timeout, zero retries, and a three-call cap, the existing
orchestrator completed the exact same window using three requests. Staging
validation found 23 unique complete in-window flow rows, a successful audit,
and the checkpoint referencing that run and window end. The first failed
Task 018 audit remains preserved. This does not authorize another window,
endpoint, chain, or historical backfill.

Task 019 replayed the same retained Avalanche `$GUN` `smart_money` day once.
The flow-key set digest and row count were stable (23 unique rows, no
duplicates), while a new successful audit became the checkpoint's referenced
run at the same window end. Earlier failed/successful audit history was
preserved. This narrow replay is not evidence for broader historical replay
or source-revision reconciliation.

Task 020 ran one bounded early-history pilot for 2025-04-25 through
2025-05-24 UTC, with a two-call maximum, zero retries, and a 120-second
timeout. The response completed in one page and persisted 29 normalized rows.
The checkpoint remained at its later September 20 timestamp and still
references the Task 019 success run. This is exact-window availability
evidence only; do not infer maximum Nansen history, daily completeness, or
authorization for a broad loop.

Nansen Flows resolution is range-dependent, so persistence identity includes
both `date` and exclusive `bucket_end`. The model may retain a null bucket end
for diagnosis, but orchestration rejects null or non-positive intervals before
opening the data transaction. Task 022 published its migration before applying
it to staging; all retained flow rows were re-keyed without row loss. Production
remains untouched.

Task 023 makes pagination retain warnings per source page in memory. Only
sanitized categories, page numbers, and warning counts are stored in the run
audit. Warning-free paginated runs store `[]`; legacy and pre-response runs
remain NULL. Unknown warnings stop before the data transaction, and a
pagination-limit failure preserves the warning evidence already fetched.
The verified non-exchange breakdown warning is allowed only for flows labeled
`smart_money`. Task 023's live revalidation was `UNKNOWN`, so migration 004
remains unapplied, production is unchanged, and broader ingestion remains
blocked.

Task 023F accepts one exact warning fingerprint only for TGM Flows `smart_money`, and only after normalized records confirm all four CEX/DEX breakdown fields are null. Different wording and mixed unknown warnings fail closed before the data transaction. Migration 004 is applied to staging only; production remains untouched. The raw warning is never stored or logged.

Task 024 used one foreground orchestrator run with one API call, one page, zero retries, and a one-page bound for 2025-04-25 through 2025-05-01 UTC. It retained 167 hourly buckets beside six pre-existing daily buckets. The exact warning policy passed and the audit stored only the sanitized warning category. The September high-water checkpoint did not regress. No service or scheduler was added, and production remains untouched.

Task 025 performed one shifted, read-only Flows request. It recovered the previously missing first hourly bucket from Task 024, while the shifted request omitted its own lower-bound bucket. This observation conflicts with the current official description of non-Hyperliquid first-bucket behavior. Do not use naive non-overlapping weekly windows for systematic hourly ingestion until a boundary-aware request plan is separately reviewed and authorized. No database mutation, ingestion audit, or checkpoint update was made.

Task 026 provides `python -m otg_nansen.backfill_plan` as a plan-only dry run. The optional `--staging-progress` mode forces a read-only connection to `server_otg_staging` and classifies each unit from exact-window audit evidence. Unit execution is exposed only as a sequential injected callback contract with finite unit and live-call ceilings, completion skipping, and stop-on-first-failure behavior; it was exercised with fakes only. Each unit's Nansen request starts one hour before its desired coverage, covers at most 167 desired hourly starts, and must remain within the hourly-resolution request-duration limit. No API call, ingestion, audit write, checkpoint change, service, or scheduler was made for Task 026. Do not use the stream high-water checkpoint as historical backfill progress.
