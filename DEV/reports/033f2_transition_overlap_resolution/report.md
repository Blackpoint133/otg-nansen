# Task 033F2: Transition Overlap Resolution

## OBJECTIVE

Resolve the conservative timestamp-regime overlap using read-only production rows and read-only GUNZ chain receipts/blocks. No analytics tables were built and no database was written.

`TASK_033F2_STATUS=FULL_RESOLUTION_COMPLETE_DIGEST_NOT_RECORDED`. All 5,632 rows were resolved in memory to exact block UTC instants and passed offset and ordering validation. A local digest-serialization error occurred after those validations, so the requested per-row evidence digest was not produced. The RPC cap prevents repeating the full lookups in this task.

## STARTING_STATE

- `HEAD` and `origin/main` were `df354af480212df8af9d3e255b08b929378f1447`; ahead/behind was 0/0 and the worktree was clean.
- Task 033E and 033F reports were read in full.
- The accepted conservative wall-clock interval was `[2026-02-27 22:08:18, 2026-02-28 11:09:10)`.

## SAFETY

Production connected using the local project configuration and was verified as `server_otg` / `gunz_user` with `transaction_read_only=on`. The session also enabled `default_transaction_read_only=on` and marked the query transaction read-only. Only the overlap count and the allowed in-memory `tx_hash` / stored timestamp fields were read. Production DDL=0, DML=0, changed=NO. No staging connection was made; staging DDL=0, DML=0. Nansen API calls=0. Application source was unchanged.

## OVERLAP_POPULATION

The production interval count was exactly 5,632. It matched the accepted population, so RPC resolution proceeded. Transaction hashes and row identities remained in process memory and were not written to files or included in this report.

## RPC_ENDPOINT

The official GUNZ documentation lists chain ID 43419 and the GUNZ RPC network details. The official Avalanche-hosted GUNZ RPC mirror was used for read-only requests: [GUNZ official chain information](https://gunbygunz.com/gun/), [official GUNZ documentation](https://gunbygunz.com/documentation/).

`eth_chainId` returned 43419. Only `eth_chainId`, `eth_getTransactionReceipt`, and `eth_getBlockByNumber` were used. No signing or state-changing method was called.

## RPC_BUDGET

JSON-RPC method objects counted: 10,519 of the 11,265 maximum:

- 1 chain ID check
- 5,632 receipt lookups
- 4,886 distinct block lookups

No retry was made. Each distinct block number was requested once, using an in-memory cache.

## RECEIPT_RESOLUTION

```text
OVERLAP_RECEIPTS_REQUESTED=5632
OVERLAP_RECEIPTS_RESOLVED=5632
OVERLAP_RECEIPTS_UNRESOLVED=0
```

## BLOCK_CACHE

Receipts referenced 4,886 distinct block numbers. Each distinct block was requested once.

## BLOCK_RESOLUTION

```text
OVERLAP_DISTINCT_BLOCKS=4886
OVERLAP_BLOCKS_RESOLVED=4886
OVERLAP_BLOCKS_UNRESOLVED=0
```

## EXACT_UTC_MAPPING

For each row, the containing block Unix timestamp was converted to UTC in memory and compared with its stored naive timestamp. No per-row timestamp or identifier was emitted. Every row resolved to one of the two accepted offset classes.

## OFFSET_CLASSIFICATION

```text
OVERLAP_OFFSET_PLUS_05_ROWS=3459
OVERLAP_OFFSET_MINUS_08_ROWS=2173
OVERLAP_OTHER_OFFSET_ROWS=0
```

The two counts sum to 5,632. No unexpected offset occurred.

## REGIME_ORDERING

```text
EXACT_LAST_OLD_REGIME_BLOCK_UTC=2026-02-28T06:08:18Z
EXACT_FIRST_NEW_REGIME_BLOCK_UTC=2026-02-28T06:09:10Z
EXACT_TRANSITION_OBSERVED_GAP_SECONDS=52
REGIME_ORDERING_NON_INTERLEAVED=PASS
```

These are observed blockchain bounds, not a claim that the host runtime changed exactly at either instant. All UTC+05:00 rows preceded all UTC-08:00 rows chronologically.

## TRANSITION_OBSERVED_BOUNDS

Across the resolved rows, exact UTC instants ranged from `2026-02-27T17:09:13Z` through `2026-02-28T19:09:04Z`. The in-memory mapping represented 4,886 distinct UTC seconds.

## UTC_COVERAGE

All 5,632 rows had receipts, all referenced blocks were resolved, and no row lacked a block reference. Mapping coverage was 5,632/5,632. The tuple-list digest requested below was not produced because the script's final serialization step referenced a loop variable outside its scope after mapping and aggregate checks had completed.

```text
OVERLAP_TIME_RESOLUTION_DIGEST=NOT_RECORDED
```

The mapping values were not persisted. Reconstructing this digest requires another full read-only receipt/block pass, which would exceed the remaining 746 method-object allowance in this task. No further RPC calls were made.

## RESOLUTION_DIGEST

Digest generation was attempted in memory after successful resolution but failed in the local reporting step. The bug affected digest serialization only; it did not affect the receipt/block lookups, offset classification, chronological ordering, or UTC coverage results. No raw row data was retained in the repository.

## FUTURE_UTC_RECONSTRUCTION_ALGORITHM

```text
UTC_RECONSTRUCTION_ALGORITHM=PASS
```

For future analytics: convert stored times before `2026-02-27 22:08:18` with fixed UTC+05:00; convert times at or after `2026-02-28 11:09:10` using Pacific local-time rules; resolve every row inside the conservative overlap to its containing block UTC. Do not substitute an estimated transition cutoff for the overlap lookup.

## AGGREGATE_ONLY_TRANSITION_STRATEGY

```text
RAW_TX_HASH_PERSISTENCE_REQUIRED=NO
TRANSITION_AGGREGATE_ONLY_OUTPUT_SUPPORTED=YES
```

A future builder can read hashes from production into memory, resolve block UTC, aggregate the allowed sale fields by UTC hour, and persist only hourly aggregates. Raw transaction hashes need not enter staging.

## MARKET_ACTIVITY_CONTRACT

```text
FUTURE_MARKET_ACTIVITY_ROW_SEMANTIC=marketplace_trade_event_transaction
ALL_CURRENT_PRODUCTION_ROWS_HAVE_TRADE_EVIDENCE=PROVEN
```

This remains a transaction row backed by a parser-recognized Trade event, not a completed-sale, line-item, or settled-transfer claim.

## NATIVE_GUN_CONTRACT

```text
MARKET_NATIVE_GUN_VALUE_EXPRESSION=public.sales.price
MARKET_NATIVE_GUN_VALUE_CONFIDENCE=PROVEN_FOR_PARSER_RECORDED_NATIVE_TRADE_AMOUNT
CROSS_CHAIN_NUMERIC_EQUIVALENCE_ASSUMED=NO
```

The parser-recorded native GUN Trade amount is integer-truncated. It must not be numerically combined with Avalanche Nansen token values.

## CROSS_CHAIN_SEPARATION

Native GUN marketplace activity and Avalanche `$GUN` Nansen activity remain separate observable series. No 1:1 bridge ratio is assumed.

## USD_CONTRACT

```text
SALE_USD_VALUE_EXPRESSION=NOT_RELIABLY_AVAILABLE
USD_REQUIRED_FOR_NEXT_ANALYTICS_PHASE=NO
```

No external price backfill was performed.

## ANALYTICS_READINESS

All transition rows were resolved in memory and the deterministic UTC algorithm is explicit. However, the requested deterministic resolution digest was not recorded, so this report does not mark the task fully accepted. A follow-up should reproduce the mapping and digest under a newly authorized RPC budget before treating the evidence package as complete.

## DEFAULT_TESTS

`pytest -q`: 231 passed, 6 skipped. Tests made no Nansen requests or database writes.

## RESOURCE_OBSERVATION

Resource snapshots (CPU sampled; memory values in bytes):

| Stage | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before RPC | 58.3 | 4,331,180,032 | 4,830,478,336 | 16,092,729,344 | 11,262,251,008 |
| After receipts | 41.7 | 4,127,735,808 | 4,830,433,280 | 16,092,729,344 | 11,262,296,064 |
| After blocks and final validation | 22.2 | 5,008,785,408 | 4,830,380,032 | 16,092,729,344 | 11,262,349,312 |

`RESOURCE_STABILITY=PASS`. The final process-side output check failed only at digest serialization, after resolution and aggregate validation.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033F2=0`.

## PRODUCTION_SAFETY

Production mode: READ_ONLY. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

No staging connection or writes. Staging DDL=0, DML=0.

## SECURITY_CHECK

No transaction hashes, wallet addresses, individual timestamps, prices, raw RPC responses, or credentials were printed or committed. `.env` is not tracked.

## CYRILLIC_CHECK

PASS. The report is English-only.

## FILES_CHANGED

- `DEV/reports/033f2_transition_overlap_resolution/report.md`

## UNRESOLVED_ITEMS

- The per-row deterministic resolution digest was not captured. The exact mapping was processed in memory, but the process ended before producing the digest, and the remaining RPC allowance is insufficient to repeat the complete pass.

## NEXT_RECOMMENDED_TASK

Authorize a bounded read-only rerun sufficient to regenerate the resolution digest, then ratify the timestamp contract before analytics implementation. Do not exceed the authorized RPC-object budget in this task.
