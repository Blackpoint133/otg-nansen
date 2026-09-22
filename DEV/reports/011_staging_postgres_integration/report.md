# Report 011 - Staging PostgreSQL integration

## OBJECTIVE

Implement the real PostgreSQL adapter and apply the isolated Nansen schema to
`server_otg_staging`, followed by bounded synthetic integration tests.

## STARTING_STATE

Started from `a17eea2f5455f25f58ea85a2de7c3a6badbf11a8`. The pre-DDL source
commit was pushed as `cc91806afb242ac7d51cf246fef479362626239f`.

## REQUEST_SCOPE_CHECK_FIX

The migration now requires JSON request-scope keys `chain`, `endpoint`,
`token_address`, and `flow_label` before strict scalar comparisons. This
closes PostgreSQL CHECK three-valued-logic loopholes. Endpoint-aware checks
also require non-empty trimmed flow scope only for the `flows` endpoint.

## DRIVER_SELECTION

POSTGRES_DRIVER=psycopg
POSTGRES_DRIVER_VERSION=3.2.9

psycopg3 was already installed and is the selected modern local convention.
The project declares `psycopg[binary]>=3.2,<4` without exposing credentials.

## DATABASE_TARGET_GUARD

All writable adapter and migration connections force `dbname` to
`server_otg_staging` and verify `SELECT current_database()`, current user, and
transaction read-only state before work. The migration refuses DROP and sets
five-second lock and thirty-second statement timeouts.

## STAGING_PREFLIGHT

The connection resolved to `server_otg_staging` as user `gunz_user` with
transaction read-only off. PostgreSQL version was 18.3. The `nansen` schema
and all `nansen.*` objects were absent. The role had no database CREATE
privilege and no public-schema CREATE privilege, so migration execution was
blocked before any DDL.

NANSEN_SCHEMA_EXISTS_BEFORE=NO
STAGING_CREATE_PERMISSION=NO

## PRE_DDL_COMMIT

The complete adapter, guarded migration command, SQL repair, unit/static tests,
and opt-in integration harness were committed and pushed before any DDL:
`cc91806afb242ac7d51cf246fef479362626239f`.

## MIGRATION_EXECUTION

STAGING_DDL=NOT EXECUTED
MIGRATION_EXECUTED=NO

No migration statement was sent because the preflight role lacked CREATE
privilege. There was no partial schema and no retry or destructive workaround.

## SCHEMA_VERIFICATION

NANSEN_SCHEMA_EXISTS_AFTER=NO
EXPECTED_TABLES_PRESENT=NOT APPLICABLE
UNEXPECTED_NANSEN_OBJECTS=NONE

## INTEGRATION_TESTS

The opt-in PostgreSQL integration harness covers audit start, flow upsert and
finalization, complete-flow downgrade protection, Avalanche case identity,
flow scope separation, DEX trade enrichment upsert, token snapshots, atomic
success, rollback and failure audit durability, request-scope constraints,
and checkpoint monotonicity. It was not run because the authorized staging
database role cannot create the schema required by the test.

AUDIT_START_TEST=NOT RUN
FLOW_UPSERT_TEST=NOT RUN
FLOW_FINALIZATION_TEST=NOT RUN
FLOW_DOWNGRADE_TEST=NOT RUN
EVM_CASE_TEST=NOT RUN
FLOW_SCOPE_TEST=NOT RUN
DEX_TRADE_TEST=NOT RUN
TOKEN_SNAPSHOT_TEST=NOT RUN
SUCCESS_ATOMICITY_TEST=NOT RUN
ROLLBACK_TEST=NOT RUN
FAILURE_AUDIT_TEST=NOT RUN
REQUEST_SCOPE_CONSTRAINT_TEST=NOT RUN
CHECKPOINT_MONOTONICITY_TEST=NOT RUN

## TEST_DATA_CLEANUP

No synthetic PostgreSQL rows were created. No cleanup was required.

## PRODUCTION_SAFETY

Production was checked only through a separate read-only connection pinned to
`server_otg` with `default_transaction_read_only=on`. It had no `nansen` schema.

PRODUCTION_DDL=0
PRODUCTION_DML=0
STAGING_DML=0

## UNIT_TESTS

`pytest -q`: 85 passed, 2 opt-in tests skipped. Default tests made zero live
Nansen calls and zero PostgreSQL connections.

## POSTGRES_INTEGRATION_TESTS

Blocked before execution by missing staging CREATE privilege.

## RESOURCE_OBSERVATIONS

Only lightweight metadata checks and the offline test suite were run. No
backfill, large scan, service, or long-running process was started.

## SECURITY_CHECK

SECRET_SCAN=PASS
ENV_TRACKED=NO
No password, API key, connection string, or authorization value is included.

## CYRILLIC_CHECK

CYRILLIC_SCAN=PASS

## FILES_CHANGED

The pre-DDL commit contains the psycopg3 adapter, guarded migration command,
request-scope SQL repair, dependency declaration, opt-in integration harness,
offline safety tests, and documentation. This report records the blocked
staging validation.

## RISKS

The staging schema is not deployed. An operator with reviewed CREATE privilege
on `server_otg_staging` must rerun the guarded migration and opt-in integration
suite. Production remains outside scope.

## NEXT_RECOMMENDED_TASK

Grant or use an explicitly approved staging role with CREATE privilege, then
rerun only `python -m otg_nansen.migrate_staging` and
`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres`. Do not use `server_otg`.
