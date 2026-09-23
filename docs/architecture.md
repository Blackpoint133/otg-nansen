# Architecture

## Confirmed objective

The project will use Nansen token/wallet intelligence to study historical
`$GUN` activity and subsequent Off The Grid NFT/item-market reactions.

Phase 0B established that the smallest future architecture is a controlled
Nansen client, normalized event/flow persistence, historical `$GUN` event
detection, read-only comparison against existing OTG market history, and
prepared analytical output. The client, normalization boundary, staging
schema, repository, and bounded fixture-backed orchestration now exist; event
detection and market comparison do not.

The current technical recommendation is primary Avalanche ingestion with a
separately checkpointed Solana adapter. Both chains returned usable token,
trade, holder, transfer, and buyer/seller responses, while the narrow Solana
Smart Money flows window was empty. The native GUNZ chain remains a separate
identity question because the reviewed Nansen chain list did not include
`gunz`.

The first code foundation is a bounded HTTP client with no service runtime.

The raw API response boundary feeds immutable normalized models for token
information, flows, and DEX trades. Normalization validates required fields,
preserves caller-trusted chain/token identity, and uses UTC-aware timestamps.
Financial and token quantities use Decimal. The two Nansen flow total count
metrics also use Decimal because the live endpoint returned a finite
fractional JSON number; `holders_count` and the optional CEX/DEX counts remain
integer typed. PostgreSQL staging persistence is implemented and validated;
the live historical window still requires a post-change normalization check.

Task 007 defined an isolated `nansen` PostgreSQL schema
with snapshot, flow, trade, ingestion-run, and checkpoint tables. A future
driver-backed repository must use parameter binding and preserve the raw-to-
normalized boundary.

Persistence identity is scope-aware: flow labels are part of request and
checkpoint provenance. A flow key identifies one exact bucket by chain,
canonical token, label, UTC `date`, and exclusive UTC `bucket_end`; mutable
measurements are excluded. DEX trade
keys exclude mutable labels and USD estimates while retaining transaction and
swap identity. Repository lifecycle methods are designed around one
transaction per ingestion run.
The final proposed lifecycle instead uses a durable audit start, one atomic
data/checkpoint transaction, and a durable audit success or failure update.
Migration status is applied to staging only and NOT APPLIED to production.
Flow scope and positive bucket interval are mandatory for persistence, and
flow identity includes both bucket bounds; DEX trade identity excludes mutable enrichment.
Persistence identity canonicalizes Avalanche EVM addresses to lowercase while
preserving exact Solana and unknown-chain values. Flow scope is trimmed once
at normalization and reused by all persistence mappings.
Task 011 adds a psycopg3 repository adapter with separate durable-audit and
atomic data/checkpoint/success connections. The staging migration command is
database-pinned and was applied to `server_otg_staging` only in Task 013A.
Production remains unapplied.

Task 014R aligns historical request sorting with the official Nansen contract:
flows use `order_by=[{'field': 'date', 'direction': 'ASC'}]` and DEX trades use
`order_by=[{'field': 'block_timestamp', 'direction': 'ASC'}]`. Success audit
updates persist page and API-attempt counters, and pagination-limit failures
retain known page/record progress. These repairs are fixture-verified only.

Task 023 retains top-level warnings with each fetched page in memory and
classifies them before normalization or persistence. Only sanitized page,
count, and category summaries enter ingestion audit rows; legacy runs remain
NULL and an observed warning-free paginated run stores `[]`. Unknown warnings
fail closed. The documented non-exchange breakdown warning is eligible only
for `flows` with `smart_money`, but the authorized live revalidation remained
`UNKNOWN`; broader backfill is blocked and migration 004 remains unapplied.

Task 023F adds an exact SHA-256 fingerprint policy for the previously observed warning, restricted to `flows` / `smart_money`. After normalization, every returned record must have all four optional CEX/DEX breakdown fields null before the warning is accepted. The raw wording is never stored, and any wording change becomes `UNKNOWN`. The exact fingerprint and evidence are in the Task 023F report. Migration 004 is applied to staging only; production remains unchanged. Legacy warning audit values remain NULL, while inspected warning-free runs use `[]`.
