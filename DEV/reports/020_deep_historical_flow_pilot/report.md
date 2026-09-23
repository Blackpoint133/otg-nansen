# Task 020: Deep-historical Avalanche flow pilot

## OBJECTIVE

Ingest one bounded 30-day Avalanche `$GUN` `smart_money` flow window near the
beginning of the known OTG market-history overlap and validate source
availability, pagination, persistence, and checkpoint non-regression.

## STARTING_STATE

Starting `main` was `cbc2552bec79f4b0d234690907e96c037fbfbbea`; the worktree was
clean. Default tests passed before any live request or data write. No
application source was changed.

## CURRENT_HIGH_WATER_STATE

Before the pilot, the stream checkpoint was at
2026-09-20T23:59:59Z and referenced successful Task 019 run
`1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. The retained recent window still had
23 rows and 23 distinct keys, with no out-of-window or incomplete rows.

## AUTHORIZED_HISTORICAL_SCOPE

Only Avalanche `$GUN`, `flows`, `smart_money`, from
2025-04-25T00:00:00Z through 2025-05-24T23:59:59Z was requested. No other
window, endpoint, chain, service, migration, or production target was used.

## PRE_INGESTION_HISTORICAL_STATE

The verified database was `server_otg_staging`, user `gunz_user`, with
`transaction_read_only=off`. All five Nansen tables existed. Both total flow
count columns were `numeric NOT NULL`. Exact target-window row count was 0;
no exact-window ingestion run existed.

## RESOURCE_BASELINE

Available RAM was 5,289,340 KB. Windows committed memory was
20,836,003,840 of 33,272,041,472 bytes; free commit was 12,436,037,632 bytes.
The first CPU sample was 100%, so a short follow-up sample was taken before
any live request: five samples over approximately ten seconds ranged from
18% to 41%. This appeared transient rather than sustained pressure, and
memory/commit headroom remained substantial.

## CLIENT_BOUNDS

This execution used `max_calls=2`, `max_retries=0`, `page_size=1000`,
`max_pages=2`, and `timeout_seconds=120`. Source defaults were not changed; no
third request was possible or made.

## INGESTION_EXECUTION

Exactly one `NansenIngestionOrchestrator.ingest_flows()` execution completed
successfully. The bounded paginator reached the final page. The command
process wall time was approximately 1.8 seconds including process setup and
teardown; an isolated orchestrator-only timer was not retained.

## LIVE_REQUEST_ACCOUNTING

- Run ID: `284e3652-93fb-4d8b-b6fc-dc2811bd4a83`
- Pages requested: 1
- API attempts: 1
- Records received: 29
- Records normalized: 29
- Final page reached: YES

## HISTORICAL_AVAILABILITY

`HISTORICAL_AVAILABILITY=LIVE_VERIFIED_FOR_EXACT_WINDOW`. The response was
non-empty and completed within the explicit request/page bound. This proves
availability only for the requested interval, not maximum history or broad
coverage.

## NORMALIZATION_RESULT

All 29 received records normalized. The orchestration validation and
independent persisted-row checks found no incomplete or out-of-window rows.

## HISTORICAL_PERSISTENCE_RESULT

The exact historical window contains 29 rows, 29 unique flow keys, zero
duplicates, zero out-of-window rows, zero incomplete rows, and zero identity
mismatches. All rows use the canonical Avalanche token and `smart_money`
scope.

## TEMPORAL_COVERAGE_STRUCTURE

- Earliest persisted date: 2025-04-25T00:00:00Z
- Latest persisted date: 2025-05-24T00:00:00Z
- Distinct dates: 29
- Duplicate timestamps: 0

No one-row-per-day guarantee is inferred; the observed set contains 29
distinct dates within this 30-day requested interval.

## NUMERIC_STRUCTURE

Fractional inflow rows: 0. Fractional outflow rows: 0. Both persisted columns
remain PostgreSQL NUMERIC. No metric values were selected or reported.

## AUDIT_VALIDATION

The new run is `success` for the exact stream and window. Audit counters match
the execution result: 1 page, 1 API attempt, 29 received, 29 normalized.
`records_inserted` and `records_updated_or_conflicted` remain neutral zero by
design and are not treated as write evidence.

## CHECKPOINT_NON_REGRESSION

The historical run did not replace or move the newer high-water checkpoint.
After the pilot the checkpoint remains at 2026-09-20T23:59:59Z and still
references Task 019 run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.
`CHECKPOINT_NON_REGRESSION=PASS`.

## RECENT_DATA_INTEGRITY

The recent September window remains at 23 rows, 23 unique keys, and zero
incomplete rows. No existing recent data was removed or damaged.

## AUDIT_HISTORY

The original Task 018 audit remains failed; Task 018R and Task 019 remain
successful; the Task 020 historical run is successful. All four records
coexist.

## RESOURCE_POSTCHECK

CPU was 30%; available RAM was 5,010,804 KB. Windows committed memory was
21,089,062,912 of 33,272,041,472 bytes; free commit was 12,182,978,560 bytes.
No retry loop or runaway process was observed. The modest resource variation
was not sustained; stability passed.

## DEFAULT_TESTS

`pytest -q` passed before and after the pilot: 140 passed, 5 skipped. Default
tests made zero live Nansen calls and zero PostgreSQL connections.

## PRODUCTION_SAFETY

Production DDL=0 and DML=0. Production was not used. No migration or DDL was
run.

## SECURITY_CHECK

No credentials, raw response rows, wallet identities, transaction hashes, or
metric values are included. Secret scan: PASS. Tracked `.env`: NO.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `DEV/reports/020_deep_historical_flow_pilot/report.md`
- `docs/database.md`
- `docs/nansen_api.md`
- `docs/operations.md`

No application source was changed.

## RISKS

The result proves a non-empty response only for this exact historical window.
It does not establish maximum Nansen historical depth, complete activity
coverage, one data point for each day, other labels/chains/endpoints, or
backfill safety. The pre-request CPU sample was transiently high and should be
monitored if future work becomes larger.

## NEXT_RECOMMENDED_TASK

Review this bounded pilot and its checkpoint behavior before authorizing any
additional finite window. Do not start a broad historical loop or Task 021
automatically.

## TASK_021_TIMESTAMP_RECONCILIATION_ADDENDUM

A later read-only inspection found that the earlier `EARLIEST_PERSISTED_DATE`
entry above incorrectly interpreted a PostgreSQL session-local timestamp as
UTC. Converting the stored `2025-04-25 17:00:00-07:00` instant correctly
gives `2025-04-26T00:00:00Z`. The 29 persisted UTC dates are therefore
2025-04-26 through 2025-05-24, and 2025-04-25 is absent from the 30-day
calendar set. Task 021 directly queried 2025-04-25 and received normalized
hourly records. The Task 020 execution and retained rows were not changed.
