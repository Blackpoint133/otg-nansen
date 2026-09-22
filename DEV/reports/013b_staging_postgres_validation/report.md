# Task 013B Staging PostgreSQL Validation

## OBJECTIVE

Validate the deployed Nansen schema and PostgreSQL repository against the
isolated `server_otg_staging` database. No migration was rerun and no Nansen
API calls were made.

## STARTING_STATE

- Starting main: `cf324b0247a1dab50d8f4e936ea4a4a54aa77b26`
- The `nansen` schema was already deployed by Task 013A.
- The working tree was clean before validation.

## TARGET_VERIFICATION

The live connection reported database `server_otg_staging`, user `gunz_user`,
and `transaction_read_only=off`. The repository target guard remained pinned to
the staging database.

## OWNER_PRIVILEGE_DECISION

Database CREATE privilege was `YES`. The owner explicitly approved this as a
persistent staging-only privilege. It was not revoked and no additional
privilege was granted. This does not grant CREATE, SUPERUSER, CREATEDB, or
CREATEROLE rights on production.

## SCHEMA_PRECHECK

The `nansen` schema existed with owner `gunz_user`. The five expected tables
were present and all pre-test table counts were zero. Table ownership was
`gunz_user` for each expected table.

## DEFAULT_TESTS

`pytest -q`: 91 passed, 2 skipped. The default suite made no PostgreSQL
connections and no live Nansen API calls.

## POSTGRES_INTEGRATION_TESTS

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q`: 1 passed, 92 deselected.
The suite used deterministic synthetic records only and targeted staging.

## FLOW_TESTS

Flow idempotency, finalization, complete-record downgrade protection, and
separate smart-money/exchange scope behavior passed. Checkpoint streams used
their matching successful ingestion runs.

## DEX_TRADE_TESTS

DEX trade idempotency and mutable enrichment updates passed. The integration
harness cleanup predicate was corrected to use the exact Task 012 synthetic
namespace and parameterized wildcard.

## TOKEN_SNAPSHOT_TEST

Duplicate `(chain, token_address, retrieved_at)` snapshots were ignored and a
different retrieval timestamp produced a second snapshot. Cleanup passed.

## AUDIT_TEST

Durable running audit creation and readback passed.

## SUCCESS_ATOMICITY

Data, checkpoint, and success audit status were staged in one data transaction
and became visible together after commit.

## ROLLBACK_ATOMICITY

Rollback removed staged data and checkpoint state while preserving the durable
running audit row.

## FAILURE_AUDIT_DURABILITY

Failure status was recorded after rollback in the separate audit connection.

## CHECKPOINT_STATUS_VALIDATION

Checkpoint advancement validated the actual successful ingestion run rather
than caller-supplied status flags.

## CHECKPOINT_STREAM_VALIDATION

The deployed composite foreign key and guarded checkpoint SQL enforced matching
chain, endpoint, token, and flow scope.

## CHECKPOINT_MONOTONICITY

Newer checkpoint timestamps advanced state; an older timestamp did not move the
checkpoint backward.

## REQUEST_SCOPE_CONSTRAINT_MATRIX

The real suite exercised missing required keys, JSON nulls, wrong JSON types,
non-object roots, scalar/JSON mismatches, and endpoint-specific scope rules.
Each invalid attempt was rolled back and rejected by PostgreSQL.

## FLOW_SCOPE_CONSTRAINT

The deployed flow checks require non-empty trimmed flow scope and enforce the
explicit empty non-flow representation.

## COMPOSITE_FOREIGN_KEY

The deployed `checkpoints` table contains the composite foreign key to the
matching ingestion-run identity. The separate run-id foreign key is also
present in the deployed migration.

## TEST_DATA_CLEANUP

Independent post-test queries found zero Task 012/013 synthetic rows in
`flows`, `dex_trades`, `token_information`, `checkpoints`, and
`ingestion_runs`. The schema and tables were retained.

## SCHEMA_POSTCHECK

All five tables remained present. Expected primary keys, indexes, scope checks,
request-scope checks, and the composite checkpoint foreign key remained
present.

## PRODUCTION_SAFETY

Production `server_otg` was checked read-only with `default_transaction_read_only`
enabled. It contained no `nansen` schema. Production DDL=0 and production
DML=0.

## RESOURCE_OBSERVATIONS

A post-validation host sample reported approximately 26% total CPU, 6.16 GiB
available physical RAM, 17.95 GiB committed, a 30.99 GiB commit limit, and
13.04 GiB free commit. No heavy job or backfill was run. A separate pre-test
resource sample was not captured.

## SECURITY_CHECK

No credentials, passwords, API keys, authorization headers, or `.env` values
were included. `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

Repository-authored text scan: PASS. All authored content is English only.

## FILES_CHANGED

- `README.md`
- `docs/database.md`
- `docs/deployment.md`
- `docs/operations.md`
- `tests/test_postgres_integration.py` (focused cleanup/timezone test-harness corrections)
- this report

## RISKS

The staging CREATE privilege remains broader than a least-privilege runtime
role, but this is an explicit owner decision and is restricted to staging.
Production remains outside the migration and integration target.

## NEXT_RECOMMENDED_TASK

Review the staging evidence externally, then design the first bounded,
fixture-backed ingestion orchestration step. Do not run production ingestion.
