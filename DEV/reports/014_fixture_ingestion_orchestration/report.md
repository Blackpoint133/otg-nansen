# Task 014 Fixture Ingestion Orchestration

## OBJECTIVE

Implement and validate a bounded orchestration boundary from Nansen-compatible
source pages through normalization, audit, PostgreSQL persistence, and
checkpoint advancement without live Nansen traffic.

## STARTING_STATE

- Starting main: `f9103639e439eb38c73833a56fd0245d9dceb6bc`
- The staging `nansen` schema and repository were already validated.
- No schema migration or production operation was authorized.

## ORCHESTRATION_ARCHITECTURE

`NansenIngestionOrchestrator` accepts an injectable source, repository, clock,
and run-id factory. It exposes token-information, flows, and DEX-trades methods
and uses the existing normalization and repository boundaries.

## INGESTION_WINDOW

`IngestionWindow` is immutable, converts timezone-aware inputs to UTC, rejects
naive or reversed bounds, rejects future ends against the injected clock, and
emits deterministic UTC `from`/`to` strings.

## PAGINATION_METADATA

`PaginationResult` and `paginate_with_metadata()` expose logical pages fetched.
The existing `paginate()` API remains compatible. Page limits and malformed
pagination continue to raise instead of returning partial success.

## REQUEST_ACCOUNTING

Each run records the delta of source `requests_attempted`, so retries count as
API attempts while `pages_requested` counts successful logical pages. Inserted
and conflicted counts remain neutral zero because the current repository does
not expose reliable per-row outcome counts.

## FLOW_REQUEST

Flows use `/api/v1/tgm/flows`, the explicit canonical flow scope, the bounded
UTC date window, and deterministic ascending date ordering fields.

## DEX_REQUEST

DEX trades use `/api/v1/tgm/dex-trades`, the bounded UTC date window, and
deterministic ascending block-timestamp ordering fields.

## TOKEN_INFORMATION_REQUEST

Token-information uses the existing endpoint helper and persists a snapshot
with the injected UTC retrieval time. It is audited but does not advance a
checkpoint.

## DURABLE_AUDIT_START

The running ingestion row is committed before source fetching begins and
contains run, stream, scope, and historical window provenance.

## FETCH_BEFORE_TRANSACTION

All source pages are fetched, pagination completion is established, all
records are normalized, and window/completeness validation succeeds before the
data transaction opens.

## FLOW_COMPLETENESS_POLICY

Every non-empty normalized flow record must have `is_complete is True`. False
or null completeness fails the run and prevents data or checkpoint commit.

## EMPTY_WINDOW_POLICY

A valid empty final page is a complete empty window. It succeeds and advances
the historical checkpoint to the requested window end.

## WINDOW_VALIDATION

Flow dates and DEX block timestamps are checked inclusively against the
requested UTC window. Out-of-window records fail explicitly and are not
dropped.

## SUCCESS_TRANSACTION

Normalized rows, success audit status, and the historical checkpoint are staged
in one transaction. The checkpoint uses the requested window end, including for
empty windows, and commits atomically.

## FAILURE_LIFECYCLE

Fetch, pagination, normalization, completeness, and window failures occur
before a data transaction and update the durable audit row as failed. Failures
after transaction start roll back data/checkpoint state and then update the
audit row through the separate audit path.

## CHECKPOINT_POLICY

Only complete successful historical flows and DEX windows advance checkpoints.
The requested end is stored rather than the latest returned record timestamp.
Future overlapping windows rely on idempotent persistence; no scheduler was
added.

## AUDIT_COUNTER_POLICY

Pages, API attempts, records received, and records normalized are recorded.
Inserted versus conflicted counts remain documented neutral values because the
repository does not distinguish those outcomes reliably.

## SAFE_ERROR_POLICY

Failure summaries contain a bounded exception class and sanitized message, are
limited to 500 characters, and redact API-key/header-style material.

## FIXTURE_UNIT_TESTS

Offline tests cover UTC windows, token snapshots, one- and multi-page flows,
DEX trades, empty complete windows, completeness failures, out-of-window
records, normalization failures, pagination/budget failures, safe errors, and
rerun idempotency.

## RETRY_ACCOUNTING_TEST

The client metadata test verifies logical page count separately from request
attempt count. Orchestration tests verify per-run request deltas, with no sleep
or live HTTP.

## IDEMPOTENCY_TEST

Repeating the same complete fixture window leaves one logical flow row while
retaining two distinct successful audit runs and the deterministic checkpoint.

## STAGING_FIXTURE_INTEGRATION

The opt-in PostgreSQL orchestration test used a fake source and valid synthetic
Avalanche identity, exercised the real orchestrator and repository, verified
flow/audit/checkpoint persistence and rerun idempotency, and made no network
requests.

## TEST_DATA_CLEANUP

The integration test removed only its deterministic Task 014 identifiers and
verified zero matching flows, trades, token snapshots, checkpoints, and audit
runs. The schema remained deployed.

## DEFAULT_TESTS

`pytest -q`: 104 passed, 4 skipped. Default tests made zero PostgreSQL
connections and zero live Nansen calls.

## POSTGRES_TESTS

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q`: 3 passed, 105 deselected.
The opt-in suite made zero Nansen API calls.

## LIVE_API_CALL_COUNT

`LIVE_API_CALLS_TASK014=0`. Live Nansen tests were not enabled. Real `$GUN`
ingestion was not performed.

## DATABASE_DDL_COUNT

`DATABASE_DDL=0`; migration was not executed.

## PRODUCTION_SAFETY

No production database or service was used. Production DDL=0 and DML=0.

## SECURITY_CHECK

No API keys, passwords, credential-bearing DSNs, authorization headers, or
`.env` values were committed. `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

Repository-authored text scan: PASS. All authored content is English only.

## FILES_CHANGED

- `src/otg_nansen/client.py`
- `src/otg_nansen/errors.py`
- `src/otg_nansen/ingestion.py`
- `src/otg_nansen/persistence.py`
- `src/otg_nansen/postgres.py`
- `tests/test_client.py`
- `tests/test_ingestion.py`
- `tests/test_ingestion_postgres_integration.py`
- `README.md`
- `docs/architecture.md`
- `docs/nansen_api.md`
- `docs/database.md`
- `docs/operations.md`
- this report

## RISKS

The orchestration is intentionally fixture-tested and staging-tested only.
Source endpoint ordering fields and historical depth require separate review
before real `$GUN` ingestion. No scheduler or production path exists.

## NEXT_RECOMMENDED_TASK

Review the orchestration contract, then authorize a narrowly bounded real
Avalanche `$GUN` ingestion window with explicit live-call and staging-data
limits.

## TASK 014R ADDENDUM

External review found three pre-live issues: historical sorting used an
undocumented string `order_by` plus standalone `order`; successful PostgreSQL
audit updates did not persist `pages_requested` or `api_calls`; and
`PaginationLimitReached` could lose its known page and record progress in the
failure audit. Task 014R corrected these issues before any real Nansen
ingestion.
