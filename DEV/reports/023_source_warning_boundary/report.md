# Task 023: Preserve, classify, and audit Nansen source warnings

## OBJECTIVE

Close the TGM Flows warning-discard blind spot before historical ingestion.
The implementation captures warning evidence by page, classifies it before
data persistence, and stores only sanitized audit summaries.

## STARTING_STATE

Repository: `parsers/parser_nansen`; branch: `main`; starting HEAD:
`42a6a0b23c74ec71530782c04c6763c29d377323`. The worktree was clean. Baseline
`pytest -q`: 148 passed, 6 skipped. Baseline live API calls: 0. Baseline
PostgreSQL connections: 0.

## WARNING_BLIND_SPOT

Before this task, `PaginationResult` held only records and a page count. The
client discarded top-level source warnings, so ingestion could not inspect or
audit them. Task 021 had observed warnings in the bounded Avalanche
`smart_money` probes.

## OFFICIAL_DOCUMENTATION_RECHECK

The current official Flows documentation was reviewed on 2026-09-23 at
<https://docs.nansen.ai/api/token-god-mode/flows>.

- Top-level `warnings`: optional response property, array of strings.
- Non-exchange warning: the documentation says an entry is included when the
  CEX/DEX breakdown fields are null for non-exchange labels.
- Truncation: no warning meaning is documented. The contract instead states
  that `is_complete` is false when the upper cutoff truncates a bucket or the
  bucket is live; Hyperliquid can also have a lower-cutoff truncated bucket.
- Partial-result warnings: `NOT_EXPLICITLY_DOCUMENTED`.
- Aggregation warnings: `NOT_EXPLICITLY_DOCUMENTED`. Aggregation itself is
  documented as hourly for ranges up to seven days and daily for longer ranges.
- Request-range warning semantics: `NOT_EXPLICITLY_DOCUMENTED`.

The official schema does not permit a null warnings container. Missing
`warnings` is treated as an empty list; null, a non-array, or non-string array
items fail the response contract safely. Current official rate-limit
documentation was also rechecked at
<https://docs.nansen.ai/getting-started/rate-limits>: 20 requests per second
and 300 requests per minute per API key. No account plan was inferred.

## WARNING_WIRE_CONTRACT

`warnings` is absent or an array of strings. Explicit null is unsupported by
the current schema. Malformed containers and entries raise a safe
`ResponseContractError`, with only sanitized unknown evidence attached for the
failed audit path.

## ARCHITECTURE_DECISION

Page warning values remain transient in memory. Ingestion classifies all
returned pages before normalization and before `begin_data_transaction()`.
Audit rows receive only page number, warning count, and category names. Raw
warning strings and source response records are not included in exceptions or
audit summaries.

## PAGE_WARNING_METADATA

Added `PaginationPageMetadata(page, warnings)` and extended
`PaginationResult` with ordered page metadata. Offline coverage verifies
different warnings on pages 1 and 2 remain associated with their pages and an
unwarned page remains represented. `paginate()` raises a safe error when any
page has warnings and directs callers to `paginate_with_metadata()`.

## PAGINATION_LIMIT_BEHAVIOR

`PaginationLimitReached` now carries the metadata for every fetched page. Its
message remains limited to endpoint and existing progress counters. The
orchestrator classifies available warning evidence and retains a sanitized
failed audit while leaving staged rows and checkpoint changes uncommitted.

## WARNING_CLASSIFICATION_POLICY

Categories are `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` and `UNKNOWN`. The
classifier uses full-string, constrained semantic forms; unrecognized strings,
objects, or unsupported endpoint contexts are unknown. No warning substring
heuristic is used. The live validation did not match the implemented benign
forms, so the classifier was not loosened.

## BENIGN_WARNING_POLICY

Only a verified non-exchange CEX/DEX breakdown warning for `flows` labeled
`smart_money` may be accepted. The official documentation confirms that a
warning entry is associated with this null breakdown condition, but does not
publish canonical warning wording. The current live warning could not be
matched safely by the constrained classifier; acceptance therefore remains
unvalidated.

## UNKNOWN_WARNING_POLICY

Any unknown warning fails closed before normalization/persistence. The error
contains only endpoint, page, warning count, and category. A failed audit gets
sanitized `UNKNOWN` summaries; no flow rows or checkpoint are committed.
Unverified paginated endpoints reject all non-empty warning sets.

## AUDIT_SCHEMA_DESIGN

Fresh schema and migration artifact add nullable `source_warnings JSONB` with
an array-or-null check. New running audits use NULL. Successful paginated
audits pass `[]` when inspected warning-free or sanitized non-empty summaries
when warnings were accepted. Legacy runs and failures before page evidence
remain NULL. Raw warning text is never mapped to JSONB.

## MIGRATION_004_DESIGN

`sql/004_ingestion_source_warnings.sql` adds the nullable JSONB column and
array-or-null constraint. It contains no DROP, DELETE, or TRUNCATE and does
not rewrite legacy NULL values. The artifact was not applied because the live
validation gate classified the warning as unknown.

## OFFLINE_TESTS

Added fake-response coverage for absent/malformed warning containers, multiple
warnings on a page, warning preservation across pages, record-only refusal,
pagination-limit metadata, sanitized unknown classification, accepted
documented semantics, and ingestion atomicity. `pytest -q`: 164 passed,
6 skipped. Default tests made 0 live Nansen calls and 0 PostgreSQL connections.

## LIVE_WARNING_VALIDATION

Exactly one read-only Nansen request was made, using the specified historical
day, chain, token, label, page size, call/retry/page bounds, and timeout.
Output was restricted to sanitized metadata:

```text
LIVE_API_CALLS_TASK023=1
LIVE_PAGE_COUNT=1
LIVE_WARNING_PRESENT=True
LIVE_WARNING_COUNT=1
LIVE_WARNING_CATEGORIES=UNKNOWN
LIVE_WARNING_CLASSIFICATION_RESULT=UNKNOWN
LIVE_IS_LAST_PAGE=True
TASK_023_STATUS=LIVE_WARNING_CONTRACT_MISMATCH
```

No raw warning, record, response, or metric value was printed or retained.
No second Nansen request was made.

## PRE_MIGRATION_SOURCE_COMMIT

Source implementation, fresh schema, migration artifact, and offline tests
were published in source commit
`f83f01181da47737ce2b34ae346f726d84185b48` (`fix: preserve and classify
nansen source warnings`). `origin/main` was fetched after push and read back
as the same SHA. The migration artifact was published but not applied.

## STAGING_PRECHECK

Not run. The live classification gate requires stopping before DDL; no
PostgreSQL connection was opened for this task.

## MIGRATION_004_EXECUTION

`MIGRATION_004_EXECUTED=NO`. No staging DDL or DML was issued.

## POST_MIGRATION_SCHEMA

Not applicable; migration 004 was not applied.

## POSTGRES_WARNING_AUDIT_TESTS

The opt-in integration test was extended to cover NULL, `[]`, sanitized
benign and unknown summaries, and CHECK rejection of non-array JSON. It was
not run because staging migration 004 was not applied and the live gate
requires stopping before database access.

## UNKNOWN_WARNING_ATOMICITY

Offline fake-source test passed: a complete flow fixture plus an unknown
warning creates a failed audit with only a sanitized UNKNOWN summary, zero
committed flow rows, and no checkpoint.

## PAGINATION_LIMIT_AUDIT

Offline regression test passed: warning evidence from already fetched pages
is retained on the exception, summarized in the failed audit, and the data
and checkpoint remain unchanged.

## RETAINED_DATA_INTEGRITY

No database connection, DDL, or DML was used, so this task made no changes to
the 52 retained staging flow rows. The row totals were not independently
requeried after the live gate stopped database work.

## CHECKPOINT_INTEGRITY

No database connection or persistence operation occurred. The accepted
checkpoint was not independently requeried; no checkpoint update was issued.

## AUDIT_HISTORY

No database connection or audit write occurred. Existing audit history was
not changed; its row counts were not independently requeried.

## RESOURCE_OBSERVATION

Before/after CPU, available RAM, and Windows commit measurements were not
collected. `RESOURCE_STABILITY=NOT_ASSESSED`.

## DEFAULT_TESTS

`pytest -q`: 164 passed, 6 skipped. `DEFAULT_TESTS_LIVE_CALLS=0` and
`DEFAULT_TESTS_POSTGRES_CONNECTIONS=0`.

## POSTGRES_TESTS

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q` was not run because the
live mismatch blocks staging DDL and physical tests that require the new
column.

## PRODUCTION_SAFETY

`PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`. Staging DDL
and DML were also zero.

## SECURITY_CHECK

The changed-file secret scan passed. No credentials, raw warnings, raw source
records, or response bodies were committed or printed. `.env` is not tracked.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS` for changed files.

## FILES_CHANGED

Source and tests: `client.py`, `errors.py`, `ingestion.py`, `persistence.py`,
`postgres.py`, `source_warnings.py`, `test_client.py`, `test_ingestion.py`,
`test_postgres_integration.py`, and `test_source_warnings.py`. Schema and
documentation: SQL migrations 001 and 004; API, architecture, database,
operations, analytics-methodology documentation; Task 021 addendum; this
report.

## RISKS

The live warning remains unknown. The current documentation identifies the
warning condition but does not define its canonical string form. No DDL was
applied, no data was written, and broader historical ingestion remains
blocked. Physical PostgreSQL warning tests and retained-state readback remain
pending the live contract issue and a later authorized continuation.

## NEXT_RECOMMENDED_TASK

Obtain an authoritative canonical warning representation from current Nansen
documentation or support, then review it against the captured warning in a
controlled, non-persistent validation. Do not relax the matcher by heuristic,
apply migration 004, start historical backfill, or begin Task 024 until the
warning is safely classified and Task 023 acceptance checks are complete.
