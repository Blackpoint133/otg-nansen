# Task 033F2R: Transition Digest Ratification

## OBJECTIVE

Repeat the read-only resolution of the 5,632 conservative transition-overlap rows and record a deterministic digest for the exact UTC mapping. No analytics tables were built, no database was written, and no Nansen request was made.

`TASK_033F2R_STATUS=SUCCESS`. The complete aggregate evidence reproduced, the canonical digest was generated and independently rechecked, and the timestamp transition contract is ratified.

## STARTING_STATE

- Local and remote `main` were `3622ae450c4567171b8b3d82b826b23a8eb18268`; ahead/behind 0/0; worktree clean.
- Task 033F and 033F2 reports were read in full.
- Accepted interval: `[2026-02-27 22:08:18, 2026-02-28 11:09:10)`.

## SAFETY

Production was verified read-only as `server_otg` / `gunz_user`, with `transaction_read_only=on` and the session default read-only guard enabled. Only `tx_hash` and naive `timestamp` were loaded for overlap rows. No staging connection was made. Production DDL=0, DML=0, changed=NO; staging DDL=0, DML=0. Nansen API calls=0. Source unchanged.

## OVERLAP_POPULATION

```text
OVERLAP_ROWS_CURRENT=5632
```

The population exactly matched the accepted count. Identifiers and row data remained in memory only.

## DIGEST_SERIALIZER_SELFTEST

Before any RPC request, the serializer was tested with synthetic tuples in different input orders. It produced the same valid lowercase SHA-256 both times.

```text
DIGEST_SERIALIZER_SELFTEST=PASS
```

## RPC_ENDPOINT

The official Avalanche-hosted GUNZ read-only RPC mirror was used. The official GUNZ site lists chain ID 43419 and links GUNZ network information: [official GUNZ chain information](https://gunbygunz.com/gun/), [official GUNZ developer documentation](https://gunbygunz.com/documentation/).

```text
RPC_CHAIN_ID=43419
```

Only `eth_chainId`, `eth_getTransactionReceipt`, and `eth_getBlockByNumber` were used. No state-changing RPC methods or signing operations occurred.

## RPC_BUDGET

```text
ONCHAIN_RPC_CALLS_TASK033F2R=10519
```

Counted JSON-RPC method objects: one chain check, 5,632 receipt calls, and one block request per 4,886 distinct block numbers. No retries occurred; no block was fetched more than once.

## RECEIPT_RESOLUTION

```text
OVERLAP_RECEIPTS_REQUESTED=5632
OVERLAP_RECEIPTS_RESOLVED=5632
OVERLAP_RECEIPTS_UNRESOLVED=0
```

Only transaction-to-block-number associations were retained from receipts.

## BLOCK_RESOLUTION

```text
OVERLAP_DISTINCT_BLOCKS=4886
OVERLAP_BLOCKS_RESOLVED=4886
OVERLAP_BLOCKS_UNRESOLVED=0
```

Only block-number-to-UTC-timestamp mappings were retained from block responses.

## OFFSET_REPRODUCTION

```text
OVERLAP_OFFSET_PLUS_05_ROWS=3459
OVERLAP_OFFSET_MINUS_08_ROWS=2173
OVERLAP_OTHER_OFFSET_ROWS=0
```

The counts sum to 5,632 and exactly reproduce Task 033F2.

## REGIME_ORDERING_REPRODUCTION

```text
EXACT_LAST_OLD_REGIME_BLOCK_UTC=2026-02-28T06:08:18Z
EXACT_FIRST_NEW_REGIME_BLOCK_UTC=2026-02-28T06:09:10Z
EXACT_TRANSITION_OBSERVED_GAP_SECONDS=52
REGIME_ORDERING_NON_INTERLEAVED=PASS
```

These are observed chain bounds, not an assertion of the exact host runtime transition instant.

## UTC_COVERAGE_REPRODUCTION

```text
OVERLAP_EXACT_UTC_MIN=2026-02-27T17:09:13Z
OVERLAP_EXACT_UTC_MAX=2026-02-28T19:09:04Z
OVERLAP_DISTINCT_UTC_SECONDS=4886
```

All 5,632 production rows were mapped to exact containing-block UTC timestamps in memory.

## CANONICAL_DIGEST_SPECIFICATION

For each overlap row, the digest input tuple was `(stored_naive_iso, exact_utc_iso, offset_class)`, with `YYYY-MM-DDTHH:MM:SS`, `YYYY-MM-DDTHH:MM:SSZ`, and offset class `UTC+05:00` or `UTC-08:00`. Tuples were lexicographically sorted, serialized as compact UTF-8 JSON using `separators=(',', ':')` and `ensure_ascii=True`, then hashed with SHA-256. No transaction hash, block number, address, price, or other row field was included.

## RESOLUTION_DIGEST

```text
OVERLAP_RESOLUTION_DIGEST_TUPLE_COUNT=5632
OVERLAP_TIME_RESOLUTION_DIGEST=08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6
OVERLAP_TIME_RESOLUTION_DIGEST_VALID=PASS
```

## DETERMINISM_CHECK

The same in-memory evidence tuples were independently copied, sorted, serialized, and hashed a second time without additional RPC calls.

```text
OVERLAP_TIME_RESOLUTION_DIGEST_SECOND_PASS=08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6
OVERLAP_TIME_RESOLUTION_DIGEST_DETERMINISTIC=PASS
```

## TIMESTAMP_CONTRACT_RATIFICATION

```text
TIMESTAMP_TRANSITION_CONTRACT=RATIFIED
SALE_TIMEZONE_CONTRACT=PROVEN_PIECEWISE_REGIMES
UTC_RECONSTRUCTION_ALGORITHM=PASS
```

Future UTC reconstruction remains:

1. Stored timestamps before `2026-02-27 22:08:18` use fixed UTC+05:00 conversion.
2. Stored timestamps at or after `2026-02-28 11:09:10` use Pacific local-time rules.
3. Every row inside the conservative overlap resolves to exact containing-block UTC. Do not replace this step with a guessed cutoff.

## MEMORY_CLEANUP

Receipt payloads were reduced to transaction-to-block-number mappings; block payloads were reduced to UTC timestamps. After aggregate checks and digest generation, transaction hashes, receipt/block mappings, and tuple lists were deleted from process memory. No caches or raw identifiers were written to disk.

```text
RAW_IDENTIFIER_FILES_CREATED=0
```

## DEFAULT_TESTS

`pytest -q`: 231 passed, 6 skipped. No Nansen calls or database writes.

## RESOURCE_OBSERVATION

CPU is a point sample; memory values are bytes.

| Stage | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before RPC | 19.0 | 4,494,028,800 | 4,829,929,472 | 16,092,729,344 | 11,262,799,872 |
| After receipts | 25.0 | 4,416,176,128 | 4,829,929,472 | 16,092,729,344 | 11,262,799,872 |
| After blocks | 100.0 | 4,383,363,072 | 4,829,929,472 | 16,092,729,344 | 11,262,799,872 |
| After digest | 100.0 | 4,364,931,072 | 4,829,929,472 | 16,092,729,344 | 11,262,799,872 |
| After cleanup | 100.0 | 4,388,352,000 | 4,829,929,472 | 16,092,729,344 | 11,262,799,872 |

```text
RESOURCE_STABILITY=PASS
```

Available RAM remained above 4.3 GB and free commit remained above 11.2 GB. The CPU sample reached 100% during local digest work; no resource stop or request failure occurred.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033F2R=0`.

## PRODUCTION_SAFETY

Production connection mode: READ_ONLY. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

No staging connection or writes. Staging DDL=0, DML=0.

## SECURITY_CHECK

No transaction hashes, wallet addresses, individual timestamps, individual prices, RPC payloads, or credentials are present. `.env` is not tracked. Raw identifier files created: 0.

## CYRILLIC_CHECK

PASS. Report is English-only.

## FILES_CHANGED

- `DEV/reports/033f2_transition_overlap_resolution/report.md` (chronology-preserving addendum)
- `DEV/reports/033f2r_transition_digest_ratification/report.md`

## RISKS

The writer's exact runtime transition instant remains unknown. The observed 52-second chain bracket and conservative overlap algorithm avoid asserting an unsupported exact host transition time.

## NEXT_RECOMMENDED_TASK

Proceed to a separately authorized, source-first implementation of the OTG–Nansen hourly analytics foundation, retaining the exact on-chain overlap resolution algorithm and keeping native GUN marketplace activity separate from Avalanche Nansen values.
