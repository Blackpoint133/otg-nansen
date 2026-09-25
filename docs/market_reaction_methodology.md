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

## Task 034 preregistered relationship analysis

Task 034 is descriptive. Correlation is not causation; a lagged association is
not prediction, and within-hour ordering is unknown. Native GUN marketplace
amounts and Avalanche Nansen `$GUN` observations remain separate series and
are never numerically combined. No p-values are calculated and no causal or
predictive claims are made.

The only real input is read-only `server_otg_staging.nansen.otg_nansen_hourly`.
It must contain the 12,336 exact canonical UTC hours and match aligned digest
`9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8`; any
identity or digest mismatch stops analysis.

The two fixed `$GUN` drivers are `gun_price_return_1h` and
`flow_imbalance_share`. The latter equals
`flow_count_imbalance / flow_count_total` only when total is positive and is
NULL otherwise. The three fixed OTG outcomes are `market_trade_tx_count`,
`market_native_gun_amount_truncated`, and `market_unique_buyers`. Each
nonnegative outcome is transformed with `log1p`; there is no winsorization or
arbitrary outlier deletion. The primary form subtracts the median transformed
outcome for the same UTC hour-of-week group (weekday * 24 + hour, 0 through
167), using `statistics.median` across the full sample. The sensitivity form
is `log1p(value[t]) - log1p(value[t-1])`, with the first hour NULL.

Fixed lags are 0, 1, 6, and 24 hours. Driver at `t-k` is paired with outcome
at `t`, so positive lag means the `$GUN` observation precedes the market
observation. All 48 combinations of two drivers, three outcomes, two forms,
and four lags are retained, including undefined coefficients. Each row gives
finite-pair n, Spearman rho as the primary descriptive coefficient, and
Pearson r as secondary. Spearman uses average ranks for ties. Coefficients are
NULL below three finite pairs or when their denominator is zero. No p-values
or best-lag selection are used.

Time stability uses exactly eight contiguous chronological blocks of 1,542
canonical outcome hours. Every fixed relationship is recalculated in each
block with its same lag. A block coefficient is NULL below 20 valid pairs or
when undefined. The output reports the number of defined block coefficients,
their median, minimum, maximum, and positive, negative, and zero counts. These
are diagnostics, not significance labels.

One event analysis uses only non-NULL `gun_price_return_1h`. Negative and
positive thresholds are the empirical 5th and 95th percentiles, respectively,
using position `(n-1)*q` and linear interpolation. Thresholds are not adjusted
after observing event counts. Positive and negative candidates are handled
separately. Chronologically consecutive candidates no more than 24 hours apart
form a cluster represented by its largest absolute return; the earliest time
wins a tie. After declustering, an event is retained only when both `t-1` and
`t+24` exist. The three outcomes are summarized at horizons 0, 1, 6, and 24
hours as `log1p(value[t+h]) - log1p(value[t-1])`. Horizon zero means same-hour
association only because within-hour ordering is unknown.

All 24 direction/outcome/horizon cells are retained. Each reports count, mean,
median, q25, q75, and a deterministic non-parametric bootstrap interval for the
median. Bootstrap uses 2,000 replacement samples of the event-group size with
a local `random.Random`. Seed is `3401 + direction_index*100 +
outcome_index*10 + horizon_index`; fixed category indices are positive=0,
negative=1; the outcome order above; and horizon order 0, 1, 6, 24. Interval
limits are interpolated at 2.5% and 97.5%. They are descriptive, not binary
significance decisions. Event groups below 20 are flagged without changing
the method.

Artifacts retain every predefined cell and follow fixed category ordering,
never coefficient magnitude. Aggregate CSV and JSON contain no hourly records,
event timestamp list, or identities. Result SHA-256 digests use normalized
logical rows or canonical summary JSON, excluding filesystem metadata and
current time. No arbitrary lag search, outcome changes, threshold tuning,
outlier removal, or winsorization is permitted after preregistration. If an
implementation defect is found after reading the real snapshot, execution
stops for a separately reviewed repair.
