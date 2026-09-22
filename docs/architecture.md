# Architecture

## Confirmed objective

The project will use Nansen token/wallet intelligence to study historical
`$GUN` activity and subsequent Off The Grid NFT/item-market reactions.

Phase 0B established that the smallest future architecture is a controlled
Nansen client, normalized event/flow persistence, historical `$GUN` event
detection, read-only comparison against existing OTG market history, and
prepared analytical output. No implementation or schema has been created.

The current technical recommendation is primary Avalanche ingestion with a
separately checkpointed Solana adapter. Both chains returned usable token,
trade, holder, transfer, and buyer/seller responses, while the narrow Solana
Smart Money flows window was empty. The native GUNZ chain remains a separate
identity question because the reviewed Nansen chain list did not include
`gunz`.

The first code foundation is a bounded HTTP client with no persistence or
service runtime.

The raw API response boundary now feeds immutable normalized models for token
information, flows, and DEX trades. Normalization validates required fields,
preserves caller-trusted chain/token identity, uses UTC-aware timestamps, and
uses Decimal values for token and financial numbers. No persistence exists yet.

Task 007 defines, but does not apply, an isolated `nansen` PostgreSQL schema
with snapshot, flow, trade, ingestion-run, and checkpoint tables. A future
driver-backed repository must use parameter binding and preserve the raw-to-
normalized boundary.

Persistence identity is scope-aware: flow labels are part of request and
checkpoint provenance, while flow keys exclude mutable measurements. DEX trade
keys exclude mutable labels and USD estimates while retaining transaction and
swap identity. Repository lifecycle methods are designed around one
transaction per ingestion run.
The final proposed lifecycle instead uses a durable audit start, one atomic
data/checkpoint transaction, and a durable audit success or failure update.
Migration status is NOT APPLIED. Flow scope is mandatory and flow identity is
chain, token, scope, and date; DEX trade identity excludes mutable enrichment.
Persistence identity canonicalizes Avalanche EVM addresses to lowercase while
preserving exact Solana and unknown-chain values. Flow scope is trimmed once
at normalization and reused by all persistence mappings.
Task 011 adds a psycopg3 repository adapter with separate durable-audit and
atomic data/checkpoint/success connections. The staging migration command is
database-pinned and has not been applied while permissions are pending.
