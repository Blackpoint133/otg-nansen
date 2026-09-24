# Task 033F: Historical Timestamp Regime Resolution

## OBJECTIVE

Resolve the sales timestamp wall-clock regimes and define a safe activity contract before analytics. No analytics tables were built, no database was written, and no market-reaction analysis was performed.

`TASK_033F_STATUS=SUCCESS` for a deterministic piecewise reconstruction contract with a bounded on-chain override. The overlap rows remain unresolved in this task because the remaining RPC allowance was smaller than the receipt lookups alone; the specified next-step reconciliation is bounded and deterministic.

## STARTING_STATE

- Local and remote `main` were both `32ec578954d7f494a88c17dea700770f35c5e554`; ahead/behind 0/0; worktree clean.
- Task 033D and 033E reports were read in full.
- Production table timestamp is naive. Its writer uses process-local `datetime.fromtimestamp()` and drops timezone metadata.
- Task 033E's zero-price population (508) and positive-price sample (100) had all matched parser Trade events and the sample's stored price matched the parser transform.

## SAFETY

The only database connections were to `server_otg`, each verified as `current_database=server_otg` and `transaction_read_only=on`, with `default_transaction_read_only=on`. Every query was read-only and rolled back. No staging connection was opened. Production DDL=0, DML=0, changed=NO; staging DDL=0, DML=0. Nansen API calls=0. No source files changed.

## MARKET_ACTIVITY_TERMINOLOGY

Use `marketplace_trade_event_transaction`: one `public.sales` row keyed by transaction hash, backed by a parser-recognized marketplace Trade event. It describes a transaction containing a Trade event, not a count of item line-items or an independently reconciled economic settlement. Do not label the entire table as completed sales or treat it as Avalanche ERC-20 transfer volume.

## POSITIVE_PRICE_SOURCE_PATH

Re-read `parsers/parser_sales/parsers/event.py` and `parsers/parser_sales/parsers/marketplace.py`.

- A Trade event sets `trade_price` from its data word after `from_wei(..., 'ether')`, float conversion, and integer truncation.
- A recognized standard Transfer event is also parsed. For ERC-721 shape, the token ID is indexed and the data field is empty, so the fallback amount is zero. For ERC-20 shape, the amount is in data but there is no third indexed topic from which this parser gets its required `token_id`; the final guard rejects the row. A standard Transfer-only event therefore cannot produce a strictly positive persisted price through this code path.
- The code can attempt to parse Transfer data as a price, but the same Transfer branch must also supply a truthy token ID to emit a row. Under the recognized standard Transfer signature shapes, that joint condition does not produce a positive Transfer-only row.

Combining that source proof with Task 033E's exhaustive on-chain result for all 508 zero-price rows (all 508 contain the configured contract's Trade event), and the production nonnegative-price aggregate, supports:

```text
POSITIVE_PRICE_WITHOUT_TRADE_POSSIBLE_BY_CODE=NO
ALL_CURRENT_PRODUCTION_ROWS_HAVE_TRADE_EVIDENCE=PROVEN
```

The zero-price Trade rows demonstrate why `price > 0` is not a complete Trade filter. The stored amount remains integer-truncated.

## HISTORICAL_RUNTIME_SEARCH

Read-only search covered the parser source, worker/orchestrator launch code and backup, parser scripts, service/task metadata on this host, the parser log directory, and available Windows System event records.

- `parser_sales/logs/blockchain.log` has only 12 records, all dated 2026-02-28 09:34:49–09:34:50; it has no timezone or restart record.
- The OTG orchestrators launch the parser but do not set `TZ` or configure a Python timezone override. No matching service or scheduled task, NSSM configuration, or timezone override was found in the inspected local material.
- Retained System log coverage begins 2026-08-25, after the transition. It contained no candidate timezone-change events. Historical event coverage is incomplete.
- No authoritative historical runtime move/restart record or exact transition instant was found. The offset transition below is established by deterministic production samples matched to exact block timestamps, not by a host deployment log.

```text
HISTORICAL_RUNTIME_TRANSITION_EVIDENCE=No authoritative host/runtime record; on-chain matched wall-clock offsets narrow the observed transition
AUTHORITATIVE_TRANSITION_TIMESTAMP=NOT FOUND
```

## RPC_SAFETY

Used the official alternate GUNZ RPC endpoint previously validated against official chain documentation. `eth_chainId` returned 43419. Calls were limited to `eth_chainId`, `eth_getTransactionReceipt`, and `eth_getBlockByNumber`; no signing or state-changing method was called. Hashes were held in memory only.

## DAILY_OFFSET_REGIME_MAP

Selected 10 rows per stored calendar day from 2026-02-01 through 2026-03-20 using stable `md5(tx_hash)` ordering, without selecting by price. Receipt and containing-block timestamps were compared in memory. All 480 rows resolved.

| Stored day range | UTC+05:00 | UTC-08:00 | UTC-07:00 |
|---|---:|---:|---:|
| 2026-02-01 through 2026-02-26 | 10 each day | 0 | 0 |
| 2026-02-27 | 8 | 2 | 0 |
| 2026-02-28 | 2 | 8 | 0 |
| 2026-03-01 through 2026-03-07 | 0 | 10 each day | 0 |
| 2026-03-08 through 2026-03-20 | 0 | 0 | 10 each day |

Additional 20-row-per-stored-hour samples on February 27–28 show the mixed-offset wall-clock overlap. The transition hours are not treated as a clean date-only cutover.

## REGIME_TRANSITION_NARROWING

All production rows in the boundary wall-clock hours 2026-02-27 22:00–23:00 and 2026-02-28 11:00–12:00 were inspected: 828 receipts and 749 unique containing blocks, all resolved. In these cohorts, the last observed UTC+05:00 block was `2026-02-28T06:08:18Z`; the first observed UTC-08:00 block was `2026-02-28T06:09:10Z`. The observed change is therefore bracketed at second precision by those instants, a 52-second interval. This is an evidence bracket, not an exact runtime-change instant.

```text
LAST_DAY_WITH_ONLY_UTC_PLUS_05=2026-02-26 (10-row daily sample)
FIRST_DAY_WITH_ANY_PACIFIC_OFFSET=2026-02-27 (10-row daily sample)
REGIME_TRANSITION_LOWER_BOUND_UTC=2026-02-28T06:08:18Z (last observed UTC+05:00 block)
REGIME_TRANSITION_UPPER_BOUND_UTC=2026-02-28T06:09:10Z (first observed UTC-08:00 block)
REGIME_TRANSITION_EXACT_UTC=NOT DETERMINED
```

## PACIFIC_DST_VALIDATION

The February/March daily samples validate Pacific standard offset UTC-08:00 before the spring change and UTC-07:00 afterward. Around the expected 2026 spring transition, a deterministic sample of 40 rows at stored 01:55–01:59 mapped to UTC-08:00 (block range `09:55:04Z`–`09:58:47Z`); all 9 production rows at stored 03:00–03:05 mapped to UTC-07:00 (block range `10:04:44Z`–`10:04:46Z`). There were zero production rows in the nonexistent local interval 02:00–03:00.

```text
PACIFIC_STANDARD_OFFSET_VALIDATED=YES (UTC-08:00)
PACIFIC_DAYLIGHT_OFFSET_VALIDATED=YES (UTC-07:00)
PACIFIC_DST_TRANSITION_MATCH=YES; sampled UTC blocks straddle the expected 2026-03-08 10:00Z transition and local 02:00 hour has zero rows
SPRING_FORWARD_NONEXISTENT_INTERVAL_ROWS=0
```

## HISTORICAL_TIME_REGIMES

Two regimes are supported by the deterministic samples and the exact boundary-hour cohort:

| Regime | Supported period/bound | Offset/rule | Evidence |
|---|---|---|---|
| 1 | Canonical history through the observed final old-regime block at 2026-02-28T06:08:18Z | Fixed UTC+05:00 | Task 033E monthly samples from 2025-04 onward plus 10 rows/day for 2026-02-01 through 2026-02-26; full boundary-hour cohorts end at this final observed old-regime block. |
| 2 | Begins no later than the first observed new-regime block at 2026-02-28T06:09:10Z and continues through sampled canonical history | Pacific local rules: UTC-08:00 standard, UTC-07:00 daylight | Boundary-hour receipt/block comparison, daily samples, current Pacific host configuration, and direct spring-transition samples. |

The historic geographic zone for Regime 1 is not named; its fixed offset is sufficient for conversion. The exact machine/runtime event between the two block instants remains unknown.

```text
TIME_REGIME_COUNT=2
```

## BACKWARD_CLOCK_OVERLAP

A switch from UTC+05:00 to UTC-08:00 creates a 13-hour repeated naive-wall-clock interval. With the 52-second transition bracket, the conservative interval requiring resolution is `[2026-02-27 22:08:18, 2026-02-28 11:09:10)` (end exclusive). A read-only production count found 5,632 rows in this conservative interval.

```text
AMBIGUOUS_LOCAL_INTERVAL_START=2026-02-27T22:08:18 (inclusive, conservative)
AMBIGUOUS_LOCAL_INTERVAL_END=2026-02-28T11:09:10 (exclusive, conservative)
AMBIGUOUS_INTERVAL_ROWS=5632
AMBIGUOUS_ROWS_REQUIRING_ONCHAIN_RESOLUTION=5632
```

## AMBIGUOUS_ROW_RESOLUTION

This task's actual read-only RPC count is 7,539 of the 10,000 maximum, leaving 2,461 calls. The 5,632 ambiguous-row receipt lookups alone exceed the remaining allowance, so none were attempted under this task's remaining budget.

```text
AMBIGUOUS_ROWS_RESOLVED=0
AMBIGUOUS_ROWS_UNRESOLVED=5632
```

For the next authorized data build, query one receipt per ambiguous `tx_hash`, collect its block number, fetch each distinct block timestamp once, and convert the row from that exact UTC instant. Worst-case method-object budget is 5,632 receipts + 5,632 blocks + one chain check = 11,265; block reuse makes the actual count lower. Fail closed on any missing receipt/block. Keep hashes only in memory and write only final hourly aggregates. This is deterministic and bounded, but needs a separately authorized allowance of up to 11,265 read-only RPC method objects.

## DST_FOLD_REASSESSMENT

The earlier 2,126 rows in the 2025-11-02 01:00 wall-clock interval were counted under an unproven Pacific interpretation. Task 033E's November samples mapped to UTC+05:00, and the newly supported Pacific regime begins in February 2026. Under the piecewise regime map, those 2025 rows are not Pacific DST-fold rows.

```text
PREVIOUS_2126_ROW_DST_FOLD_ASSUMPTION_REVISED=YES; those were candidate wall-clock rows under the wrong Pacific assumption
DST_FOLD_AFFECTED_ROWS=0 under the supported 2025 UTC+05:00 regime
```

## SPRING_FORWARD_VALIDATION

The Pacific nonexistent 2026-03-08 local 02:00–03:00 interval contains zero production rows. The directly compared samples before and after it map to standard and daylight offsets respectively.

## UTC_RECONSTRUCTION_CONTRACT

```text
SALE_TIMEZONE_CONTRACT=PROVEN_PIECEWISE_REGIMES
SALE_TIMESTAMP_UTC_STRATEGY=For stored wall times before the conservative overlap, subtract fixed UTC+05:00. For times after it, interpret under Pacific local-time rules. For every row inside the conservative overlap, resolve exact UTC from its receipt's containing block. Reject analytics output if any overlap row cannot be resolved.
```

No single SQL expression is sufficient. The transition bracket and overlap override make the UTC mapping deterministic without inventing an exact host-change time.

## TRANSITION_OVERRIDE_STRATEGY

```text
TRANSITION_OVERRIDE_REQUIRED=YES
TRANSITION_OVERRIDE_CAN_REMAIN_AGGREGATE_ONLY=YES
```

The on-chain mapping can be held in memory during the build; only the final hourly aggregates need to be persisted. No transaction hashes need to be placed in staging.

## NATIVE_GUN_MARKET_VALUE_CONTRACT

For Trade-event rows, `public.sales.price` is the parser-recorded native GUNZ GUN amount after `from_wei` and integer truncation. A sub-GUN fraction is discarded. The parser's positive-value Transfer fallback cannot persist a standard ERC-20 Transfer because that event shape has no token ID for its final insertion guard; a standard ERC-721 Transfer has indexed token ID but no data amount. This supports the stored Trade amount semantics without claiming any Avalanche ERC-20 transfer amount.

```text
MARKET_NATIVE_GUN_VALUE_EXPRESSION=public.sales.price
MARKET_NATIVE_GUN_VALUE_CONFIDENCE=PROVEN for parser-recorded Trade amount; integer-truncated
CROSS_CHAIN_NUMERIC_EQUIVALENCE_REQUIRED=NO
NATIVE_GUN_VOLUME_CAN_BE_ANALYZED_SEPARATELY=YES, as a native GUN series distinct from Avalanche Nansen values
```

No bridge ratio is applied. Keep native GUN marketplace values and Avalanche `$GUN` Nansen observations as separate series and do not numerically combine them.

## CROSS_CHAIN_SEPARATION

The official GUN materials identify native GUN marketplace use and an Avalanche bridge representation, but Task 033F does not require an explicit 1:1 assertion. No economic or numerical equivalence between the two chain-specific series is claimed.

## USD_CONTRACT

```text
SALE_USD_VALUE_EXPRESSION=NOT RELIABLY AVAILABLE
USD_REQUIRED_FOR_NEXT_ANALYTICS_PHASE=NO
```

Native GUN activity can be examined separately without USD. The missing hourly USD contract does not block a descriptive foundation.

## ANALYTICS_READINESS

The row semantic is a parser-backed marketplace Trade-event transaction, not a line-item sale count or settlement claim. Piecewise timestamp conversion is deterministic; 5,632 transition-overlap rows require the explicitly bounded receipt/block resolution step before hourly aggregation. Native GUN and Avalanche Nansen values remain separate. No correlation, event study, causal statement, or prediction was produced.

`NEXT_PHASE_READY=YES, after the explicitly bounded transition reconciliation (up to 11,265 RPC objects) is authorized and passes with zero unresolved rows.`

## DEFAULT_TESTS

`pytest -q`: 231 passed, 6 skipped. No Nansen calls and no database writes.

## RPC_CALL_ACCOUNTING

```text
DAILY_REGIME_SAMPLE_RPC_OBJECTS=3601
TRANSITION_HOUR_SAMPLE_RPC_OBJECTS=1870
TRANSITION_NARROW_COHORT_RPC_OBJECTS=412
PACIFIC_DST_EDGE_SAMPLE_RPC_OBJECTS=78
FULL_TRANSITION_BOUNDARY_HOURS_RPC_OBJECTS=1578
ONCHAIN_RPC_CALLS_TASK033F=7539
```

Counts include chain-ID checks, every receipt/block method object, and repeated block reads. All methods were read-only. The total is below the 10,000 cap.

## PRODUCTION_SAFETY

Production connection mode: READ_ONLY. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

No staging connection or write. Staging DDL=0, DML=0.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033F=0`.

## SECURITY_CHECK

Transaction hashes, wallet addresses, individual sale records, prices, credentials, and raw RPC responses are absent. Hashes were held in memory only. No source changes were made; `.env` is not tracked.

## CYRILLIC_CHECK

PASS for this English-only report.

## FILES_CHANGED

- `DEV/reports/033f_timestamp_regime_resolution/report.md`

## UNRESOLVED_ITEMS

- No authoritative OS/deployment record establishes the exact runtime-change instant; chain evidence brackets it to a 52-second interval.
- The 5,632 conservative overlap rows were not resolved in this task because receipt lookups alone exceeded the remaining RPC allowance. They require a separately authorized, bounded resolution step before the analytical build.
- Stored native GUN values are integer-truncated and omit fractional portions below one GUN.
- USD-at-sale remains unavailable at a reliable hourly resolution.

## NEXT_RECOMMENDED_TASK

Authorize a read-only transition-overlap reconciliation capped at 11,265 RPC method objects, verify all 5,632 rows resolve to unique exact UTC instants, then proceed with the source-first analytics foundation using parser-backed Trade-event transaction counts and a separate native GUN series. Keep Avalanche Nansen observations separate and do not make causal or predictive claims.
