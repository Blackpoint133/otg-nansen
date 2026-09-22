# Report 008 - Persistence semantics hardening

## OBJECTIVE

Complete the missing Task 008 persistence semantics hardening and publish the
result without database access, live API calls, or migration execution.

## LOCAL_STATE_CLASSIFICATION

TASK008_NOT_IMPLEMENTED at recovery start. Local HEAD was the Task 007 commit
`935136679e7de96a7de074f4747d9869cc49d5ce`; no Task 008 report or uncommitted
Task 008 implementation existed.

## FLOW_LABEL_AND_REQUEST_SCOPE

`NormalizedFlowRecord` now carries the caller-provided optional flow label.
Flow mappings retain it, and ingestion-run mappings retain chain, endpoint,
token address, flow label, and a request-scope object. No label is inferred
from response rows.

## STABLE_FLOW_KEY

The flow key uses canonical chain, token address, flow label, date, and bucket
end fields. Mutable measurements, counts, and completeness flags are excluded.
The same scoped time bucket therefore remains idempotent when measurements are
refreshed.

## STABLE_DEX_TRADE_KEY

The trade key uses canonical chain, requested/token addresses, block timestamp,
transaction hash, trader, action, token amount, traded-token address, and
traded-token amount. Mutable trader labels, token names, and USD estimates are
excluded. Transaction hash alone is not treated as globally unique.

## CANONICAL_KEY_ENCODING

Key inputs are normalized to deterministic JSON with sorted keys, compact
separators, UTC `Z` timestamps, and string Decimal values before SHA-256
fingerprinting.

## CHECKPOINT_STREAM_IDENTITY

Checkpoint identity is `(chain, endpoint, token_address, flow_label)`, with an
empty scope value for non-flow endpoints. Different flow labels cannot
overwrite one another.

## REPOSITORY_INTERFACE

The driver-neutral protocol now covers storing normalized models, beginning an
ingestion run, completing or failing it, reading a scoped checkpoint, and
advancing a checkpoint. A small in-memory checkpoint double verifies the
completion invariant without a database.

## TRANSACTION_SEMANTICS

The future driver-backed implementation should perform each bounded ingestion
run in one transaction: record run start, upsert normalized rows, mark success
or failure, and advance the checkpoint only after complete success. Rollback
must leave the prior checkpoint unchanged. Partial or failed runs remain
auditable and cannot be treated as complete.

## MIGRATION

`sql/001_create_nansen_schema.sql` was updated with flow scope and ingestion
provenance fields and a scoped checkpoint primary key. It remains a review-only
artifact and was not executed.

## TESTS

`pytest -q`: 68 passed, 1 opt-in live test skipped. Default tests made zero
live API calls. Tests cover scope retention, mutable-field key exclusion,
canonical mapping, provenance, separate checkpoint streams, lifecycle protocol,
and static migration expectations.

## SAFETY

LIVE_API_CALLS_TASK008=0
DATABASE_WRITES=0
DATABASE_DDL=0
MIGRATION_EXECUTED=NO
CYRILLIC_SCAN=PASS
SECRET_SCAN=PASS
ENV_TRACKED=NO

## NEXT_RECOMMENDED_TASK

Task 009 should perform an isolated driver-specific dry-run against a temporary
database or SQL harness only after review. Existing OTG databases must remain
untouched.
