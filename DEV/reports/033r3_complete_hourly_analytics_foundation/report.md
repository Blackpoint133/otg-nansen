# Task 033R3: OTG–Nansen Hourly Analytics Foundation Attempt

## OBJECTIVE

Complete the interrupted Task 033 build from the verified empty analytics-table state. The source defect encountered during persistence prevented physical completion; this report records the actual outcome.

```text
TASK_033R3_STATUS=SOURCE_REPAIR_REQUIRED
TASK_033_RATIFIED_STATUS=NOT_COMPLETE
NEXT_PHASE_READY=NO
```

## STARTING_STATE

- Starting main: `13c8e05046b6f4a4e0a1ef8a12508548e517a23a`, synchronized and clean.
- Source implementation: `ed1c6687ccc30154e65fe4b677e6085efa1380f6`.
- Pinned writer connection fix: `f516328b21150046c5c4d0216b0c438a2ec644f5`.
- Both analytics tables started empty; Task 033R2 had independently verified that state.
- Nansen source baseline: 12,336 canonical hourly rows, 29 daily rows, accepted identity digest `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.

## BASELINE_TESTS

Before the build, `pytest -q` reported 253 passed, 6 skipped. Tests are offline and use fakes; no Nansen, GUNZ RPC, or PostgreSQL calls were made by the test suite.

## SOURCE_VERIFICATION

The committed `staging_writer_connection()` uses keyword expansion into `psycopg.connect`, pins the database to `server_otg_staging`, and verifies the database identity. No source changes were made in this task. The connection opened successfully during the build and passed the writer identity/read-write checks, but the later persistence method call exposed a separate untested defect.

## PRODUCTION_PREFLIGHT

The builder connected to `server_otg` through the committed production read-only connection path. It queried production sales; no production DDL or DML was performed. Production was not modified.

## STAGING_READONLY_PREFLIGHT

The starting source check used `server_otg_staging` read-only. Both analytical tables existed and contained zero rows. Canonical source validation found 12,336 hourly rows and 29 daily rows with the accepted digest.

## STAGING_WRITER_PREFLIGHT

The separate writer preflight requested by the later detailed run procedure was not completed before RPC; the builder's committed order performs source resolution first and opens the writer afterward. After the RPC campaign, the writer did open and verified `current_database=server_otg_staging` and `transaction_read_only=off`. It was used for the snapshot path, then closed after the exception rollback.

## ANALYTICS_SCHEMA_PREFLIGHT

Migration 005 was applied idempotently to staging by the builder. The schema is the already committed seven-column market table and 24-column aligned table, keyed by `hour_start`. The writer call progressed past database identity and read-only checks. No schema mismatch caused the failure.

## NANSEN_SOURCE_PREFLIGHT

Before the build: canonical hourly rows=12,336; daily rows=29; identity digest=`73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.

## LIVE_OVERLAP_RESOLUTION

Exactly one fresh read-only GUNZ resolution campaign ran. It used 10,519 JSON-RPC method objects: one chain check, 5,632 transaction receipts, and 4,886 distinct block reads. Chain ID was 43419. Receipts resolved=5,632, unresolved=0; blocks resolved=4,886, unresolved=0. Nansen API calls=0.

## OVERLAP_DIGEST_GATE

The accepted overlap contract reproduced exactly:

```text
OVERLAP_ROWS=5632
OVERLAP_OFFSET_PLUS_05_ROWS=3459
OVERLAP_OFFSET_MINUS_08_ROWS=2173
OVERLAP_OFFSET_OTHER_ROWS=0
OVERLAP_TIME_RESOLUTION_DIGEST=08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6
OVERLAP_DIGEST_MATCH=PASS
```

The accepted transition ordering and bounds passed in the committed resolver. No row identifiers or RPC payloads were persisted.

## IN_MEMORY_ANALYTICS

The builder formed 12,336 market rows and 12,336 aligned rows over the canonical UTC range. It passed the in-memory size checks before attempting staging persistence.

## PRIOR_DIGEST_COMPARISON

```text
MARKET_IN_MEMORY_CONTENT_DIGEST=0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e
ALIGNED_IN_MEMORY_CONTENT_DIGEST=9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8
MARKET_DIGEST_REPRODUCES_INTERRUPTED_RUN=YES
ALIGNED_DIGEST_REPRODUCES_INTERRUPTED_RUN=YES
```

These are in-memory digests only, not physical readback evidence.

## FIRST_STAGING_WRITE

The builder called the committed `replace_analytics_snapshot()` once. Inside its transaction, it issued deletes for the two staging snapshots, then failed at the first `connection.executemany(...)` call with `AttributeError: 'Connection' object has no attribute 'executemany'`. The exception handler called rollback. No insert completed.

## FIRST_PHYSICAL_READBACK

A fresh staging read-only connection after the failure found market rows=0 and aligned rows=0; both min/max hour values were NULL. Thus the transaction rollback preserved the empty starting state. No digest readback occurred.

## SECOND_IDEMPOTENCY_WRITE

Not run. No second snapshot write was attempted. `ANALYTICS_PERSISTENCE_IDEMPOTENCY=NOT_PROVEN`.

## FINAL_MARKET_VALIDATION

Physical market rows=0. Canonical hour coverage, activity counts, duplicate counts, and aggregate totals are not validated because the snapshot did not persist.

## FINAL_ALIGNED_VALIDATION

Physical aligned rows=0. Physical match counts, coverage, and duplicate counts are not validated.

## CONTENT_DIGESTS

The two in-memory digests above match the prior interrupted build. Final physical staging digests are NOT_AVAILABLE because both tables are empty.

## LAG_FEATURE_QA

No physical lag QA was completed. No correlation, event study, predictive metric, or market conclusion was calculated.

## STRUCTURAL_QA

No physical analytical snapshot exists. Physical NULL and zero-hour counts are not available.

## NANSEN_SOURCE_NON_REGRESSION

Fresh read-only staging verification after rollback found 12,336 canonical Nansen hourly rows, 29 daily rows, and digest `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`. `NANSEN_SOURCE_NON_REGRESSION=PASS`.

## RESOURCE_OBSERVATION

| Stage | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before overlap RPC | 50.0 | 4,048,887,808 | 4,873,158,656 | 16,092,729,344 | 11,219,570,688 |
| After overlap RPC | 100.0 | 3,999,805,440 | 4,873,158,656 | 16,092,729,344 | 11,219,570,688 |
| After production aggregation | 41.7 | 3,896,991,744 | 4,880,166,912 | 16,092,729,344 | 11,212,562,432 |
| After analytical construction | 33.3 | 3,896,209,408 | 4,880,166,912 | 16,092,729,344 | 11,212,562,432 |

RAM remained above 3.8 GB and free commit above 11.2 GB through analytical construction. No post-write resource sample was emitted because persistence failed. Overall resource pressure did not trigger the stop.

## DEFAULT_TESTS

Baseline: 253 passed, 6 skipped. No post-run tests were started after discovering the source defect, consistent with the stop-on-source-defect instruction.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033R3=0`.

## ONCHAIN_RPC_CALL_ACCOUNTING

`ONCHAIN_RPC_CALLS_TASK033R3=10519`, within the 11,265 method-object maximum. No retry campaign or state-changing method was used.

## PRODUCTION_SAFETY

`PRODUCTION_CONNECTION_MODE=READ_ONLY`; production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

The authorized idempotent migration ran against staging. One snapshot replacement transaction began and rolled back on the psycopg API error. Post-run read-only inspection confirmed both snapshot tables remained empty. No successful staging data mutation persisted.

## SECURITY_CHECK

No transaction hashes, wallets, buyer/seller identifiers, token IDs, individual market rows/prices, RPC payloads, or credentials were included. `.env` is not tracked.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `DEV/reports/033_otg_nansen_hourly_analytics_foundation/report.md` (chronological addendum)
- `DEV/reports/033r3_complete_hourly_analytics_foundation/report.md`

No source, test, or migration file changed in Task 033R3.

## RISKS

The committed replacement path uses `Connection.executemany`, which is unsupported by the active psycopg connection API. It must be repaired and covered by an offline fake/adapter test before another build. The one authorized overlap campaign has been consumed; a repaired builder requires separate authorization for a fresh overlap-resolution campaign because its exact row-to-block map is intentionally not persisted.

## TASK_033_RATIFICATION

`TASK_033_RATIFIED_STATUS=NOT_COMPLETE`. Physical market/aligned snapshots are still empty; no final physical coverage, digest readback, lag QA, or idempotency proof exists.

## NEXT_RECOMMENDED_TASK

Authorize a source repair for psycopg bulk insertion (for example, using a cursor's `executemany` or an equivalent supported API) with offline coverage. After source-first review/push, authorize one new bounded build run. Do not reuse the in-memory digests as proof of persisted analytics.
