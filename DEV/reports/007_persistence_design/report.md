# Report 007 - PostgreSQL persistence design

## OBJECTIVE

Fix chain-aware token identity comparison and design, but do not apply, an
isolated PostgreSQL persistence layer for the verified normalized models.

## STARTING_STATE

- Repository: `C:\VAMBAM\Projects\OTG\parsers\parser_nansen`
- Starting main SHA: `738bd9c04e2c8dd6723a306c106c50ae0af09e11`
- Working tree was clean.

## TASK006_EXTERNAL_REVIEW

Task 006 compared all identities with casefolding. This was unsafe for
case-sensitive Solana Base58 addresses, although it was appropriate for
Avalanche EVM hexadecimal addresses.

## CHAIN_IDENTITY_FIX

Added `token_identity_matches()`. Avalanche requires reasonable `0x` plus 40
hexadecimal address shape and compares hex letters case-insensitively. Solana
and unknown chains compare exact strings. Caller-provided chain and token
identity remains authoritative; response identity is validation evidence only.

## POSTGRESQL_DESIGN

The proposed isolated namespace is `nansen`. No connection, schema creation,
DDL, or row write was performed. The review artifact is
`sql/001_create_nansen_schema.sql`.

## PROPOSED_SCHEMA

The migration proposes `token_information`, `flows`, `dex_trades`,
`ingestion_runs`, and `checkpoints` under `nansen`, with UTC `TIMESTAMPTZ`,
financial/token `NUMERIC`, indexes for date lookups, and explicit ingestion
status checks.

## TABLE_DESIGNS

- Token snapshots use `(chain, token_address, retrieved_at)` as the primary
  key, preserving historical snapshots.
- Flow rows use a SHA-256 fingerprint over stable normalized fields as
  `flow_key`. This avoids duplicate rows on complete-window reruns; identical
  source records intentionally collide.
- DEX trades use a SHA-256 fingerprint over chain, timestamp, transaction,
  trader, action, token, traded token, amounts, and values as `trade_key`.
  Transaction hash alone is not treated as globally unique.
- Ingestion runs record bounded execution counts and sanitized error summaries.
- Checkpoints are keyed by chain, endpoint, and token address and reference a
  successful run.

## IDEMPOTENCY_POLICY

Repeated complete windows use deterministic flow/trade keys and must not add
duplicates. A retry after a failed run may replay rows safely. A partial page
run raises before it is considered complete and cannot advance a checkpoint.
Process restart resumes from the last complete checkpoint, not from a partial
run marker.

## CHECKPOINT_POLICY

Checkpoint advancement requires `status=success` and `complete=true`. Failed
or partial ingestion leaves the prior checkpoint unchanged.

## NUMERIC_POLICY

Python `Decimal` maps to PostgreSQL `NUMERIC`; no float conversion is used.
Unbounded `NUMERIC` is proposed because source precision and token scales vary.

## TIMESTAMP_POLICY

UTC-aware Python datetimes map to PostgreSQL `TIMESTAMPTZ`. The persistence
mapping rejects naive values and does not depend on server local timezone.

## MIGRATION_ARTIFACT

`sql/001_create_nansen_schema.sql` is reviewable source only. It was not
executed. No `CREATE`, `ALTER`, or other DDL was sent to PostgreSQL.

## PERSISTENCE_INTERFACE

`persistence.py` provides deterministic model-to-parameter mappings, static
design rules, a driver-neutral repository protocol, and a small in-memory
checkpoint test double. Future SQL must use parameterized driver placeholders;
no dynamic untrusted identifiers are supported.

## DRIVER_DECISION

No new driver dependency was added. The repository boundary remains
driver-neutral until a later persistence task confirms the existing OTG
PostgreSQL driver convention and performs a separately authorized connection.

## TESTS

`pytest -q`: 64 passed, 1 opt-in live test skipped. Tests cover identity
semantics, deterministic mappings, Decimal/timezone preservation, checkpoint
invariants, and static migration expectations. No live API calls or database
connections were made.

## LIVE_API_CALL_COUNT

LIVE_API_CALLS_TASK007=0
DATABASE_WRITES=0
DATABASE_DDL=0

## SECURITY_CHECK

SECRET_SCAN=PASS
ENV_TRACKED=NO

## CYRILLIC_CHECK

CYRILLIC_SCAN=PASS

## FILES_CHANGED

Added chain identity, persistence mapping, review-only SQL, and tests; updated
package exports, documentation, and Task 006 with an honest addendum.

## RISKS

The schema remains unreviewed and unapplied. Source endpoint identity and
duplicate semantics should be confirmed before production-scale ingestion.

## NEXT_RECOMMENDED_TASK

Task 008 should perform a driver-specific dry-run repository test using a
temporary isolated database or SQL inspection harness, only after review and
without touching existing OTG databases.
