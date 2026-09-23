# Task 018R: First live staging flow retry

## OBJECTIVE

Execute one separately authorized retry of the exact Avalanche `$GUN`
`smart_money` flow window into `server_otg_staging.nansen`.

## STARTING_STATE

Starting `main` was `0a08044cba95c1617e0667a52686e634496b9a5e`; the worktree
was clean. No source change was made.

## RECOVERY_STATE

Task 018R recovery classified the retry as not executed. The original Task 018
audit remained failed, target rows were absent, and no checkpoint existed.

## ORIGINAL_FAILED_RUN

Run `8ab88f8b-327d-4183-b20d-b32697ec62b8` remained `failed` before and after
the retry.

## AUTHORIZED_SCOPE

Only Avalanche `$GUN`, `flows`, `smart_money`, for
2026-09-20T00:00:00Z through 2026-09-20T23:59:59Z. The only writable target
was `server_otg_staging.nansen`. No other chain, endpoint, or window was
requested.

## PRE_RETRY_DATABASE_STATE

Verified target was `server_otg_staging`, user `gunz_user`,
`transaction_read_only=off`. Both total flow count columns were `numeric NOT
NULL`; all five expected Nansen tables existed. The exact target flow row
count was 0, checkpoint was absent, and the only exact-window run was the
original failed Task 018 run.

## CLIENT_TIMEOUT_POLICY

The one orchestrator execution used `max_calls=3`, `max_retries=0`,
`page_size=10`, `max_pages=3`, and `timeout_seconds=60`. No fourth request or
second ingestion run was made.

## RESOURCE_BASELINE

CPU was 69%; available physical RAM was 4,816,172 KB. Windows committed
memory was 21,215,789,056 of 33,272,041,472 bytes; free commit was
12,056,252,416 bytes.

## INGESTION_EXECUTION

The existing `NansenClient`, `PostgresRepository`, and
`NansenIngestionOrchestrator.ingest_flows()` path completed successfully. The
orchestrator fetched and normalized the bounded response, then persisted the
flows, successful run audit, and checkpoint atomically.

## LIVE_REQUEST_ACCOUNTING

- Run ID: `9ceff191-d65c-448b-8f3a-f7b4e7efba01`
- Pages requested: 3
- API attempts: 3
- Records received: 23
- Records normalized: 23
- Record count matches Task 017V: YES

No raw response or analytical metric magnitude is retained here.

## NORMALIZATION_RESULT

All 23 records normalized. Independent database checks found all rows
canonicalized to the expected Avalanche stream, inside the requested window,
and complete. No duplicate flow keys were present.

## DATABASE_PERSISTENCE_RESULT

The target window contains 23 rows and 23 distinct flow keys after commit.
Identity mismatches: 0; out-of-window rows: 0; incomplete rows: 0. Live rows
remain intentionally retained in staging.

## NUMERIC_PRESERVATION

The persisted columns remain PostgreSQL `numeric NOT NULL`. Two inflow rows
have a fractional component; no outflow rows have a fractional component.
Values were not selected or reported. This verifies fractional NUMERIC
storage structurally without disclosing metric magnitudes.

## AUDIT_RUN_VALIDATION

The new run has status `success`, the authorized scalar stream/window, and
counters matching the orchestrator result: 3 pages, 3 API attempts, 23
received, and 23 normalized. Inserted/conflicted counters remain neutral zero
by design and are not interpreted as row-write evidence.

## REQUEST_SCOPE_VALIDATION

The persisted request-scope JSON matches scalar chain, endpoint, canonical
token, and flow label.

## CHECKPOINT_VALIDATION

The stream checkpoint exists, its completion time equals the exact requested
window end, and its `last_success_run_id` is this successful retry run.

## AUDIT_HISTORY

The original Task 018 run remains failed and the separate Task 018R run is
success. Both audit rows coexist; the original was not removed or rewritten.

## POST_COMMIT_CONSISTENCY

PASS: retained flow rows, successful audit, and checkpoint are mutually
consistent; checkpoint references the successful retry, and the earlier
failed audit remains intact.

## RESOURCE_POSTCHECK

CPU was 47%; available physical RAM was 5,101,648 KB. Windows committed
memory was 21,185,277,952 of 33,272,041,472 bytes; free commit was
12,086,763,520 bytes. No retry loop or abnormal sustained resource increase
was observed; stability passed.

## DEFAULT_TESTS

`pytest -q`: 140 passed, 5 skipped after execution. The same suite passed
before execution. Default tests made zero live API calls and zero PostgreSQL
connections.

## PRODUCTION_SAFETY

Production DDL=0 and DML=0; production was not accessed. No migration or DDL
was run.

## SECURITY_CHECK

No credentials, raw response data, wallet identities, transaction hashes, or
analytical metric magnitudes are recorded. Secret scan: PASS. Tracked `.env`:
NO.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `DEV/reports/018_first_live_staging_flow_ingestion/report.md`
- `DEV/reports/018r_first_live_staging_flow_retry/report.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/nansen_api.md`

No application source was changed.

## RISKS

Evidence covers only the requested historical day and stream. It does not
establish broader historical depth, another date/label, other endpoints,
Solana behavior, or production ingestion. Audit outcome counters still do not
classify per-row inserts versus conflicts.

## NEXT_RECOMMENDED_TASK

Review this single-window staging evidence and decide whether to authorize a
separate next scope. Do not infer approval for broader ingestion or Task 019.
