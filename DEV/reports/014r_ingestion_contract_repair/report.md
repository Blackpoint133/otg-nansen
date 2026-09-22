# Task 014R Ingestion Contract Repair

## OBJECTIVE

Repair the Task 014 historical request shape and audit accounting before any
real Nansen ingestion.

## STARTING_STATE

- Starting main: `79815c0c672f3cef6d4e3c04a8f9a06b5dd7b6d9`
- Task 014 orchestration was preserved and repaired in place.
- No live Nansen call, migration, DDL, or production operation was performed.

## EXTERNAL_REVIEW_FINDINGS

The prior orchestration sent an undocumented string sorting form and standalone
`order`, successful SQL omitted page/API counters, and pagination-limit failures
did not preserve known fetched progress.

## OFFICIAL_FLOWS_REQUEST_CONTRACT

Current official documentation for
`/api/v1/tgm/flows` documents `order_by` as a sort-order array. Its relevant
shape is `[{'field': 'date', 'direction': 'ASC'}]`. Reference:
https://docs.nansen.ai/api/token-god-mode/flows

## OFFICIAL_DEX_REQUEST_CONTRACT

Current official documentation for
`/api/v1/tgm/dex-trades` documents `order_by` as a sort-order array. Its
relevant shape is
`[{'field': 'block_timestamp', 'direction': 'ASC'}]`. Reference:
https://docs.nansen.ai/api/token-god-mode/dex-trades

## FLOWS_ORDER_BY_FIX

The orchestrator now sends the documented array and does not send a standalone
`order` field. Chain, token, date, label, and bounded pagination remain
unchanged.

## DEX_ORDER_BY_FIX

The DEX-trades request now sends the documented block-timestamp array and no
standalone `order` field. No undocumented tie-breaker was added.

## SUCCESS_AUDIT_ACCOUNTING_FIX

Success SQL and the psycopg adapter now persist pages requested, API calls,
records received, records normalized, and neutral inserted/conflicted counters.
The staging fixture test verified stored values `(1, 1, 1, 1)` for a one-page,
one-record run.

## PAGINATION_FAILURE_ACCOUNTING

When `PaginationLimitReached` is raised, failure audit uses its
`pages_fetched` and `records_collected` metadata. No source rows or checkpoint
are persisted. Normalized count remains zero because the incomplete window is
rejected.

## REQUEST_BUDGET_FAILURE_POLICY

Request-budget failures preserve the actual request-attempt delta and retain
zero page/record counts when the source provides no reliable progress metadata.
They cannot produce success or advance a checkpoint.

## FLOW_COMPLETENESS_POLICY

The fail-closed policy remains: every non-empty flow result must have
`is_complete is True`. Empty final windows retain the existing complete-empty
semantics, pending confirmation during a future small live probe.

## FIXTURE_TESTS

Offline tests assert the complete flow and DEX payload shapes, absence of the
legacy `order` field, success counter SQL, pagination-limit progress, request
budget behavior, and unchanged failure persistence semantics.

## STAGING_FIXTURE_TEST

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q` passed with 3 tests. The
fixture-backed orchestration test queried `nansen.ingestion_runs` and verified
the persisted success counters. It made no network requests.

## DEFAULT_TESTS

`pytest -q`: 106 passed, 4 skipped.

## LIVE_API_CALL_COUNT

`LIVE_API_CALLS_TASK014R=0`. Live tests were not enabled.

## DATABASE_DDL_COUNT

`DATABASE_DDL=0`; migration was not executed.

## TEST_DATA_CLEANUP

The staging fixture test removed its exact Task 014 synthetic rows and retained
the schema. No unrelated rows were deleted.

## PRODUCTION_SAFETY

Production was not used. Production DDL=0 and DML=0.

## SECURITY_CHECK

No API keys, passwords, credential-bearing URLs, authorization headers, or
`.env` values were committed. `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

Repository-authored text scan: PASS. All authored content is English only.

## FILES_CHANGED

- `src/otg_nansen/ingestion.py`
- `src/otg_nansen/persistence.py`
- `src/otg_nansen/postgres.py`
- `tests/test_ingestion.py`
- `tests/test_ingestion_postgres_integration.py`
- `tests/test_persistence.py`
- `docs/nansen_api.md`
- `docs/architecture.md`
- `docs/operations.md`
- `DEV/reports/014_fixture_ingestion_orchestration/report.md` addendum
- this report

## RISKS

The corrected request form is official-documentation and fixture verified but
not live verified in this task. Empty-window and completeness behavior should
be checked in a tiny separately authorized live probe before broad ingestion.

## NEXT_RECOMMENDED_TASK

Perform a small, explicitly authorized live Avalanche contract probe using the
corrected payloads. Do not start historical ingestion.
