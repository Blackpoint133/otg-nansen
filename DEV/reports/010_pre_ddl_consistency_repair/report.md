# Report 010 - Pre-DDL consistency repair

## OBJECTIVE

Close identity, scope, and crash-consistency gaps before any PostgreSQL DDL or
write is authorized.

## STARTING_STATE

Started from main `813aff6e0c882ba6eeb01473937b671489c94de7`, with the Task 009
migration still review-only and unapplied.

## EXTERNAL_REVIEW_FINDINGS

Avalanche persistence used raw address casing, flow scope could retain
whitespace, database checks did not fully enforce scoped-flow rules, and the
success audit update occurred after data/checkpoint commit.

## EVM_PERSISTENCE_IDENTITY

`canonical_chain_address` validates Avalanche EVM shape and stores lowercase
addresses. Token snapshots, flows, flow keys, ingestion provenance,
checkpoints, and all verified Avalanche DEX address-like identity fields use
this representation. Malformed Avalanche addresses fail safely.

## SOLANA_PERSISTENCE_IDENTITY

Solana addresses preserve exact Base58 case and are never case-folded.
Unknown chains also preserve exact values.

## FLOW_SCOPE_CANONICALIZATION

One shared helper strips leading and trailing whitespace, rejects non-string or
empty results, and preserves meaningful case. The canonical value is used by
normalization, models, mappings, keys, request scope, and checkpoints.

## DATABASE_SCOPE_CONSTRAINTS

The review-only migration now requires trimmed non-empty scope for `flows` and
for `ingestion_runs` and `checkpoints` when endpoint is `flows`. Non-flow
endpoints must use the explicit empty scope. Ingestion request JSON is checked
against scalar identity fields.

## REQUEST_SCOPE_CONSISTENCY

`map_ingestion_run` canonicalizes the token address and scope once, then uses
the same values in scalar columns and `request_scope`.

## AUDIT_START_SEMANTICS

The audit run is inserted as `running` and committed before data work begins.
This preserves a durable audit record for later failure reporting.

## ATOMIC_SUCCESS_TRANSACTION

The future repository stages normalized data, checkpoint, and success audit
status in one transaction and commits them together. `complete_ingestion_run`
is explicitly a transaction-participating operation in the protocol and test
double.

## FAILURE_ROLLBACK_SEMANTICS

Failure rolls back staged data, checkpoint, and success state. The durable run
remains `running` until `fail_ingestion_run` updates it outside the rolled-back
transaction to `failed` or `partial`.

## CHECKPOINT_RUN_CONSISTENCY

`last_success_run_id` references a run whose success status is committed in the
same transaction as the checkpoint. The successful state cannot expose a new
checkpoint paired with a still-running run.

## IN_MEMORY_TRANSACTION_MODEL

Tests cover durable running state, staged data/checkpoint/success state before
commit, atomic visibility after commit, rollback invisibility, durable failure
update, and crash-safety state consistency.

## MIGRATION_REVIEW

`sql/001_create_nansen_schema.sql` was updated only as a reviewable artifact.
It was not executed and contains no environment-specific connection details.

## TESTS

The full default pytest suite passes. The opt-in live test remains skipped.

## LIVE_API_CALL_COUNT

LIVE_API_CALLS_TASK010=0

## DATABASE_CONNECTION_COUNT

DATABASE_CONNECTIONS_TASK010=0

## DATABASE_WRITE_COUNT

DATABASE_WRITES=0

## DATABASE_DDL_COUNT

DATABASE_DDL=0

## SECURITY_CHECK

SECRET_SCAN=PASS
ENV_TRACKED=NO

## CYRILLIC_CHECK

CYRILLIC_SCAN=PASS

## FILES_CHANGED

Identity and normalization helpers, persistence mappings and lifecycle double,
review-only SQL, tests, documentation, Task 009 addendum, and this report.

## RISKS

The migration remains unapplied. Address-shape assumptions should be reviewed
against future endpoint families before adding additional chains.

## NEXT_RECOMMENDED_TASK

Task 011 may perform an isolated driver-specific migration dry run against a
temporary database only. Existing OTG databases must remain untouched.
