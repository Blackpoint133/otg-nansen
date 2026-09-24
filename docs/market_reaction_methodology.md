# OTG and Nansen Hourly Data Foundation

This document describes the Task 033 descriptive data foundation. It does not
define correlation or event-study methods and makes no causal or predictive
claim.

## Source lineage and row meaning

The market source is `server_otg.public.sales`, read through a connection
verified as `server_otg` and `transaction_read_only=on`. Its transaction-hash
key identifies parser-backed `marketplace_trade_event_transaction` rows. The
count is transactions containing a recognized marketplace Trade event, not
item line items or independently verified settlement. `price` is the parser-
recorded native GUN Trade amount after `Web3.from_wei(..., 'ether')`, float
conversion, and integer conversion; fractional native GUN is truncated.
Buyer, seller, and token identifiers are used only in the production-side
aggregation and are not copied to staging. No raw sale row, wallet, or
transaction hash is persisted in staging.

The Nansen source is the previously verified Avalanche `$GUN` `smart_money`
hourly data in `server_otg_staging.nansen.flows`. No Nansen API request is made
by this builder. Native GUN marketplace amounts and Avalanche Nansen values
remain separate numeric series; no cross-chain conversion or bridge ratio is
assumed. A reliable transaction-time market USD value is unavailable, so the
market tables have no USD volume field.

## Timestamp reconstruction

`public.sales.timestamp` is naive wall-clock time. Before
`2026-02-27 22:08:18`, it is interpreted with fixed UTC+05:00. At or after
`2026-02-28 11:09:10`, it is interpreted under `America/Los_Angeles` local-time
rules. Rows in the conservative interval
`[2026-02-27 22:08:18, 2026-02-28 11:09:10)` are assigned the exact UTC
timestamp of their containing GUNZ block. The builder checks the 5,632-row
population, 4,886 distinct blocks, offset totals, transition ordering, and
accepted overlap mapping digest before writing analytical rows.

The normal-regime production rows are converted and aggregated in SQL. Exact
overlap timestamps are parameterized into a read-only CTE. Overlap identifiers
remain in memory only. The query groups the combined logical row stream by
explicit UTC hour and calculates distinct buyer/seller/item counts over the
whole hour so counts are not incorrectly summed across timestamp regimes.

## Hourly spine and market aggregates

The canonical spine contains all 12,336 UTC hour starts from
`2025-04-25T00:00:00Z` through `2026-09-20T23:00:00Z`, inclusive. A no-activity
hour remains present with zero transaction count, native amount, and distinct
entity counts. `nansen.otg_market_hourly` stores one row per UTC hour with the
hour end, transaction count, truncated native GUN sum, and distinct buyer,
seller, and item counts.

## Nansen fields and derived features

The aligned table includes source `price_usd`, `token_amount`, `value_usd`,
`holders_count`, `total_inflows_count`, and `total_outflows_count`, prefixed
with `nansen_`. The unavailable CEX/DEX breakdown fields are omitted.

Price returns at 1, 6, and 24 hours are `current / lagged - 1`; they are NULL
when either input is NULL or the lagged price is zero. Flow count imbalance is
inflows minus outflows; total is inflows plus outflows. Market features are
absolute 1, 6, and 24-hour deltas for transaction count and native GUN amount.
No value is forward-filled and undefined ratios are NULL.

## Storage, safety, and reproducibility

Migration 005 creates `nansen.otg_market_hourly` and
`nansen.otg_nansen_hourly` on `server_otg_staging` only. The production reader
is pinned to `server_otg`, sets the session default read-only, and verifies
read-only mode. The staging writer is pinned to `server_otg_staging` and
refuses other databases. The builder atomically replaces only the two
analytical snapshots.

Content digests serialize rows in ascending UTC `hour_start` order with
canonical UTC timestamps, canonical integer and decimal strings, explicit
NULLs, compact UTF-8 JSON, and SHA-256. Volatile timestamps are not included.
The same already-validated in-memory rows are persisted twice and compared by
readback to check idempotency without another RPC pass.

The outputs are structural descriptive data only. Correlations, event studies,
causal interpretation, prediction, and deployment require separate review and
authorization.
