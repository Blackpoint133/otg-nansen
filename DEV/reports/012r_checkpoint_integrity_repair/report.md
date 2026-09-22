# Report 012R - Checkpoint integrity repair

## OBJECTIVE

Repair checkpoint run validation and the staging integration harness before
any CREATE privilege grant or migration execution.

## STARTING_STATE

Started from published main `63736eab5513ea9e0ed2172f7b61e9a67182c2e2`.
Task 012 remained blocked on staging CREATE privilege; no Nansen schema or
integration data existed.

## EXTERNAL_REVIEW_FINDINGS

The DEX cleanup predicate used the wrong namespace, request-scope integration
coverage was incomplete, checkpoint status was caller-authoritative, and
checkpoint stream identity was not tied to the referenced ingestion run.

## DEX_CLEANUP_FIX

The harness now inserts the exact deterministic `task012_trade_identity` and
deletes that exact value. Flow labels, token name, run UUIDs, checkpoints, and
ingestion runs use exact Task 012 identifiers. Final assertions cover flows,
DEX trades, token snapshots, checkpoints, and ingestion runs.

## REQUEST_SCOPE_TEST_MATRIX

The opt-in PostgreSQL source now tests missing required keys, JSON nulls,
wrong JSON primitive/object/array types, non-object roots, scalar/JSON
mismatches for every identity field, empty flow scope, and non-flow scope
violations. Every case uses a rollback-safe transaction.

## CHECKPOINT_API_FIX

`advance_checkpoint` no longer accepts caller-supplied status or completeness
flags. It accepts the stream identity and run ID only. The adapter validates
the actual staged database row and raises a project persistence error when no
matching successful run exists.

## ACTUAL_RUN_STATUS_VALIDATION

Eligibility requires an existing run with status `success`, matching chain,
endpoint, canonical token, and canonical flow scope. The in-memory double uses
the same rule against staged audit state.

## STREAM_IDENTITY_VALIDATION

Smart-money and exchange streams require distinct successful runs. A run from
one scope cannot advance another scope's checkpoint; wrong token, endpoint,
chain, or status is rejected.

## COMPOSITE_FOREIGN_KEY

The migration adds a semantically independent unique constraint on the run
identity tuple and a composite checkpoint foreign key covering run ID and all
stream identity columns.

## SUCCESS_TRANSACTION_ORDER

The required order is data upserts, staged success audit update, guarded
checkpoint advance, then commit. This makes data, success status, and
checkpoint atomically visible.

## ROLLBACK_SEMANTICS

Rollback removes staged data, success state, and checkpoint together. The
durable running audit remains and can be marked failed separately.

## FLOW_SCOPE_CHECKPOINT_TEST

The source harness creates separate smart-money and exchange runs and checks
that each checkpoint references its own run ID.

## TEST_CLEANUP_POLICY

Cleanup is exact and foreign-key-safe: checkpoints first, then flows/trades/
snapshots, then ingestion runs. No broad wildcard cleanup is used.

## DEFAULT_TESTS

`pytest -q`: 86 passed, 2 opt-in PostgreSQL tests skipped. Default tests use
zero PostgreSQL connections and zero live Nansen calls.

## DATABASE_ACTIONS

DATABASE_CONNECTIONS_WRITE=0
DATABASE_WRITES=0
DATABASE_DDL=0
MIGRATION_EXECUTED=NO
TEMP_CREATE_GRANTED=NO

## SECURITY_CHECK

SECRET_SCAN=PASS
ENV_TRACKED=NO

## CYRILLIC_CHECK

CYRILLIC_SCAN=PASS

## FILES_CHANGED

Checkpoint SQL/API and in-memory validation, composite migration foreign key,
integration harness cleanup and matrix coverage, documentation, Task 012
addendum, and this report.

## REMAINING_BLOCKER

An authorized administrator must grant `CREATE` on `server_otg_staging` to
`gunz_user` before migration and opt-in tests can run. No privilege escalation
was attempted.

## NEXT_RECOMMENDED_TASK

After the approved temporary grant, run the guarded staging migration and the
opt-in PostgreSQL suite, then revoke the grant. Do not touch production.
