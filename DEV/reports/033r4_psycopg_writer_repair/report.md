# Task 033R4: Psycopg Writer Repair and Pre-RPC Preflight

## OBJECTIVE

Repair the analytics snapshot bulk-insert API usage and move a real, SELECT-only staging writer capability check ahead of the costly overlap resolver. No build was run in this task.

## STARTING_STATE

- Starting main: `540c8ea698d83ce93f0c656c6134293304f3783d`, clean and synchronized.
- Task 033R3 had reproduced the overlap evidence and in-memory data but rolled back the snapshot transaction after a psycopg API error. Both analytics tables were empty.
- Writer connection fix `f516328b21150046c5c4d0216b0c438a2ec644f5` was already present.

## CONFIRMED_DEFECT

The old replacement path called `connection.executemany(...)`. Psycopg 3 connections do not expose this method. The Task 033R3 runtime traceback confirmed the `AttributeError`.

## WHY_OFFLINE_TEST_MISSED_IT

The old `FakeWriter` implemented `executemany` directly on the fake connection, reproducing the invalid API and therefore masking the production mismatch.

## WRITER_API_REPAIR

Both bulk inserts now run through `with connection.cursor() as cursor:` and `cursor.executemany(...)`. The existing transaction still contains both deletes and both bulk inserts; exceptions trigger rollback and propagate. The database identity, read/write mode, and complete-row-count gates remain in place. No per-row insert loop or COPY path was added.

## TEST_DOUBLE_REPAIR

`FakeWriter` now exposes `cursor()` and does not expose connection-level `executemany`. `FakeCursor` models context management, SELECT execution, and `executemany`. The idempotency test still verifies two replacements and 24,672 inserted rows per table. Added assertions cover lack of the invalid connection API, read-only writer rejection, and rollback/exception propagation.

## WRITER_PREFLIGHT_IMPLEMENTATION

`staging_writer_capability_preflight()` opens the pinned staging writer, verifies `server_otg_staging` and `transaction_read_only=off`, opens a real cursor, verifies callable `executemany`, executes only SELECT operations (including a harmless cursor executemany SELECT), checks both analytics tables with `to_regclass`, then closes cursor and connection. It fails closed for an unsuitable target, read-only writer, missing cursor capability, failed SELECT, or missing table. No DML or DDL is issued.

## BUILDER_ORDERING_CHANGE

The builder now invokes and reports the capability preflight after read-only source connection validation but before loading the overlap population or calling `resolve_overlap_rows()`. A failed preflight raises immediately, so tests verify resolver invocation count remains zero. `WRITER_PREFLIGHT_BEFORE_RPC=YES`.

## BASELINE_TESTS

Before edits: `pytest -q` reported 253 passed, 6 skipped.

## POST_REPAIR_TESTS

After edits: `pytest -q` reported **257 passed, 6 skipped**. `compileall` completed successfully. Tests use fake connections/RPC sessions and made no PostgreSQL, GUNZ RPC, or Nansen calls.

## SOURCE_REPAIR_COMMIT

Source/docs commit: `1536f175a087637a02e3126cce4e80857e427726` (`fix: use psycopg cursor for analytics snapshot writes`). It was pushed before the real staging writer preflight and verified by remote readback.

## REAL_STAGING_WRITER_PREFLIGHT

The committed function passed after the source push:

```text
STAGING_WRITER_PREFLIGHT=PASS
STAGING_WRITER_DATABASE=server_otg_staging
STAGING_WRITER_TRANSACTION_READ_ONLY=off
STAGING_CURSOR_EXECUTEMANY_AVAILABLE=YES
MARKET_TABLE_EXISTS=YES
ALIGNED_TABLE_EXISTS=YES
```

The cursor SELECT and SELECT executemany checks succeeded. The preflight connection was closed. No staging DML or DDL occurred.

## ANALYTICS_TABLE_STATE

Fresh staging read-only verification confirmed both tables remain empty: market rows=0 and aligned rows=0; min/max hour values are NULL. Read-only schema inspection found 7 market columns and 24 aligned columns, each with one primary key and hour-end/check constraints.

## NANSEN_SOURCE_NON_REGRESSION

Fresh read-only source verification: canonical hourly=12,336; daily=29; identity digest=`73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.

## RPC_SAFETY

`NANSEN_API_CALLS_TASK033R4=0`; `ONCHAIN_RPC_CALLS_TASK033R4=0`. The live analytics builder and overlap resolver were not run.

## DATABASE_SAFETY

Production connections=0; production DDL=0; production DML=0. Staging was accessed only by the read-only source/schema checks and the SELECT-only writer preflight. Staging DDL=0; staging DML=0.

## SECURITY_CHECK

No credential values were printed or committed. `.env` is not tracked. `SECRET_SCAN=PASS`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

- `src/otg_nansen/market_analytics.py`
- `src/otg_nansen/analytics_build.py`
- `tests/test_market_analytics.py`
- `docs/operations.md`
- `DEV/reports/033r4_psycopg_writer_repair/report.md`

## NEXT_RECOMMENDED_TASK

The writer path now has an offline API-shape regression test and a real SELECT-only preflight that executes before overlap RPC. The analytics tables remain empty. A separate authorization is required to run the live analytics builder and perform staging persistence/idempotency validation.
