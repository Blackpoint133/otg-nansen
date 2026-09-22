# Report 009 - Final persistence semantics repair

## OBJECTIVE

Finalize the review-only Nansen persistence semantics before any PostgreSQL
migration, write, or DDL operation.

## STARTING_STATE

Started from main `13c86faf8bd7a39b9d3a0588bbd7aa868b67702c`, with the Task 008
design published but not accepted for migration execution.

## EXTERNAL_REVIEW_FINDINGS

Review identified optional flow scope, non-canonical Decimal identity,
unproven `bucket_end` identity, redundant primary-key-inclusive UNIQUE
constraints, missing concrete UPSERT SQL, missing complete-flow downgrade
protection, and an inconsistent audit/data transaction lifecycle.

## FLOW_SCOPE_POLICY

Flow normalization, ingestion provenance, and flow checkpoints require a
non-empty caller-provided `flow_label`. Non-flow endpoints use an explicit
empty scope. Invalid flow scope cannot silently share a checkpoint.

## DECIMAL_CANONICALIZATION

Finite Decimal identity values use normalized fixed-point strings. Equivalent
values such as 1, 1.0, and 1.00, including normalized zero, produce identical
identity material. Non-finite values are rejected and analytical precision is
not changed.

## FLOW_IDENTITY

The flow key is the SHA-256 fingerprint of chain, trusted token address,
non-empty flow label, and UTC date. `bucket_end`, metrics, counts, and
completeness are observations rather than proven identity fields.

## TRADE_IDENTITY

The trade key retains stable chain, requested-token, timestamp, transaction,
trader, action, token, amount, and traded-token dimensions. Labels, names, and
USD estimates are excluded. Decimal identity fields use canonical encoding.

## SQL_CONSTRAINT_FIX

Flow and trade primary keys are the sole identity constraints; redundant UNIQUE
constraints containing those primary keys were removed. Lookup indexes remain
in the review-only migration artifact.

## TOKEN_SNAPSHOT_POLICY

Token information is historical snapshot data keyed by chain, token address,
and retrieval timestamp. Duplicate snapshots use `ON CONFLICT DO NOTHING`.

## FLOW_UPSERT_POLICY

`FLOW_UPSERT_SQL` is parameterized and updates observations on conflict. Its
database conflict predicate allows incomplete-to-incomplete and
incomplete-to-complete updates, allows complete-to-complete refreshes, and
prevents complete-to-incomplete downgrades. NULL completeness is explicit:
NULL cannot downgrade an existing TRUE value.

## TRADE_UPSERT_POLICY

`DEX_TRADE_UPSERT_SQL` updates only mutable labels, names, and USD estimates;
immutable identity fields are not rewritten.

## AUDIT_LIFECYCLE

An ingestion run is inserted as `running` in a durable audit operation. After
fetch and normalization, the data transaction upserts rows and advances the
checkpoint. Only a committed complete data transaction is followed by a
durable success update. Failures update the existing audit row to failed or
partial after data rollback, preserving failure history.

## DATA_TRANSACTION_SEMANTICS

Normalized data and checkpoint advancement are atomic in one transaction.
Audit lifecycle state is intentionally separate so a data rollback cannot
erase the failure record.

## CHECKPOINT_ATOMICITY

Checkpoint advancement requires successful complete status and occurs inside
the data transaction. Failed and partial runs leave the prior checkpoint
unchanged.

## REPOSITORY_INTERFACE

The protocol now expresses audit start/completion/failure, scoped checkpoint
operations, normalized stores, and begin/commit/rollback data transaction
boundaries. Parameterized SQL is exposed as reviewable constants and is never
constructed from runtime values.

## IN_MEMORY_TRANSACTION_TEST

The deterministic repository double proves both success and failure paths:
committed data and checkpoints become visible only after commit, while
rollback removes staged changes and leaves a durable failed audit row.

## SQL_STATIC_TESTS

Tests verify required parameter placeholders, flow and trade conflict clauses,
complete-flow protection, token snapshot behavior, scoped checkpoint SQL, and
absence of redundant UNIQUE constraints. SQL was not executed.

## FULL_TESTS

The default pytest suite passes. The opt-in live test remains skipped and no
live Nansen calls were made.

## LIVE_API_CALL_COUNT

LIVE_API_CALLS_TASK009=0

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

Source persistence semantics, normalization scope validation, migration SQL,
tests, documentation, the Task 008 addendum, and this report.

## RISKS

The migration remains unapplied and requires separate driver-specific review.
Natural-key collision assumptions should be validated against bounded live
responses before production ingestion.

## NEXT_RECOMMENDED_TASK

Task 010 may implement a driver-specific review-only SQL adapter against an
isolated temporary database. Existing OTG databases must remain untouched.

## TASK 010 ADDENDUM

External review found that EVM persistence identity was not canonicalized,
flow scope whitespace could create distinct streams, SQL did not fully enforce
flow scope, and updating audit success after data commit left a crash-
consistency window.

Task 010 corrected these issues before migration execution. Avalanche EVM
addresses now use lowercase persistence identity, Solana remains exact,
canonical trimmed flow scope is shared across normalization and persistence,
SQL adds endpoint-aware scope checks, and success status is staged with data
and checkpoint in the atomic transaction. Failure audit updates remain
durable after rollback.
