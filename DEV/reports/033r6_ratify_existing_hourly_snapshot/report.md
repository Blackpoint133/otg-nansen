# Task 033R6: Ratify Existing Hourly Snapshot

## OBJECTIVE

Repair UTC readback identity validation and prove persistence idempotency using the existing staged snapshot, without rebuilding from production or resolving overlap on chain.

## STARTING_STATE

- Starting main: `62fe647dc18150eb2887b1ca44fe2068ea2f521a`, clean and synchronized.
- Existing physical snapshots: 12,336 market rows and 12,336 aligned rows.
- Accepted physical digests: market `0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e`; aligned `9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8`.

## CONFIRMED_DST_FOLD_DEFECT

The old helper compared `len(set(starts))` using local `ZoneInfo` datetimes returned for `timestamptz`. The Pacific fall-back hour can represent two distinct UTC instants with the same local wall-clock and ZoneInfo, causing Python equality to collapse them. Task 033R5 physical evidence showed SQL distinct and UTC-normalized distinct counts were 12,336 while the raw local-zone set count was 12,335.

## UTC_READBACK_REPAIR

`_validate_canonical_hour_identities()` converts all actual values to `datetime.timezone.utc`, then compares the complete ordered sequence with the canonical UTC hour spine. `_assert_readback()` uses this helper before retaining min/max diagnostics. This proves exact sequence, range, uniqueness, no gaps, and order without raw local-time equality.

## DST_FOLD_REGRESSION_TEST

Offline coverage constructs both real Pacific local representations of the repeated fall-back hour from distinct UTC instants, demonstrates raw equality/set collapse, and verifies UTC normalization retains both. A small ordered sequence spanning the fold also passes. `DST_FOLD_READBACK_REGRESSION=PASS`.

## BASELINE_TESTS

Before repair: 257 passed, 6 skipped.

## POST_REPAIR_TESTS

After repair: 265 passed, 6 skipped. Tests cover the full 12,336-hour spine, missing/duplicate/unexpected/out-of-order sequences, DST fold normalization, and digest mismatch. Tests use no database, RPC, or Nansen connections.

## SOURCE_FIRST_COMMIT

The UTC validation source/test commit was pushed before staging DML:

```text
UTC_READBACK_FIX_SHA=1991405e1e392c9b5888f8a0a75ba528222a5e33
```

## PRE_RATIFICATION_PHYSICAL_STATE

Read-only staging identity: `server_otg_staging`, transaction read-only on. Before ratification, market=12,336 and aligned=12,336. Both canonical identity validations passed.

## PRE_RATIFICATION_DIGESTS

```text
MARKET_PRE_RATIFICATION_DIGEST=0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e
ALIGNED_PRE_RATIFICATION_DIGEST=9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8
MARKET_PRE_RATIFICATION_DIGEST_MATCH=PASS
ALIGNED_PRE_RATIFICATION_DIGEST_MATCH=PASS
```

## STAGING_WRITER_PREFLIGHT

The committed SELECT-only writer preflight passed: database=`server_otg_staging`; transaction read-only=`off`; cursor `executemany` available; both target tables exist. No RPC was made.

## IDEMPOTENCY_WRITE_1

The two existing snapshots were read through `read_analytics_rows()` into memory. Their same row objects were passed to `replace_analytics_snapshot()`. Write 1 left market/aligned counts at 12,336 each, passed both canonical identity checks, and read back the accepted digests.

## IDEMPOTENCY_WRITE_2

The exact same in-memory row objects were passed through the same replacement function again. Write 2 again left 12,336 rows per table, passed both identity checks, and preserved both digests. `ANALYTICS_PERSISTENCE_IDEMPOTENCY=PASS`.

## FINAL_MARKET_VALIDATION

Market rows=12,336; UTC min=`2025-04-25T00:00:00Z`; max=`2026-09-20T23:00:00Z`; missing=0; unexpected=0; duplicates=0. Activity hours=11,911; zero-activity hours=425. Transaction count sum=9,562,201; truncated native GUN amount sum=356,791,669.

## FULL_RANGE_DISTINCT_EVIDENCE

One parameterized production aggregate over the accepted stored-time bounds was run READ ONLY. It matched the physical hourly transaction count and amount total. Result: distinct buyers=79,548; distinct sellers=78,681; distinct items=6,934,161. The first command session completed without returning its output, so the identical aggregate SELECT was executed once more to capture the result; both executions were read-only, aggregate-only, and loaded no raw rows. Validation=PASS.

## FINAL_ALIGNED_VALIDATION

Aligned rows=12,336; UTC min/max match the canonical endpoints; Nansen matched=12,336; market matched=12,336; missing Nansen=0; missing market=0; unexpected=0; duplicates=0.

## CONTENT_DIGESTS

Final read-only physical digests remained:

```text
MARKET_HOURLY_CONTENT_DIGEST=0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e
ALIGNED_HOURLY_CONTENT_DIGEST=9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8
```

## LAG_FEATURE_QA

Physical non-null rows: price return 1h/6h/24h = 12,335/12,330/12,312; transaction delta = 12,335/12,330/12,312; native GUN delta = 12,335/12,330/12,312.

## STRUCTURAL_QA

Aligned NULL counts: price returns 1h=1, 6h=6, 24h=24; transaction deltas 1h=1, 6h=6, 24h=24; native GUN deltas 1h=1, 6h=6, 24h=24; all other aligned fields=0. Market zero counts: transaction count=425; native amount=426; unique buyers=425; unique sellers=425; unique items=425.

## NANSEN_SOURCE_NON_REGRESSION

Fresh read-only staging validation after both writes found hourly=12,336; daily=29; missing canonical identities=0; digest=`73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`. `NANSEN_SOURCE_NON_REGRESSION=PASS`.

## RESOURCE_OBSERVATION

| Stage | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before write 1 | 36.1 | 3,599,253,504 | 4,904,255,488 | 16,092,729,344 | 11,188,473,856 |
| After write 1 | 71.4 | 3,608,977,408 | 4,904,255,488 | 16,092,729,344 | 11,188,473,856 |
| After write 2 | 50.0 | 3,570,827,264 | 4,904,255,488 | 16,092,729,344 | 11,188,473,856 |
| After final validation | 75.0 | 3,527,180,288 | 4,904,255,488 | 16,092,729,344 | 11,188,473,856 |

Memory remained above 3.5 GB and free commit above 11.1 GB. `RESOURCE_STABILITY=PASS`.

## RPC_SAFETY

`NANSEN_API_CALLS_TASK033R6=0`; `ONCHAIN_RPC_CALLS_TASK033R6=0`. The full builder and overlap resolver were not run.

## PRODUCTION_SAFETY

Production aggregate access was READ ONLY. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

Only the two authorized same-snapshot replacement transactions wrote staging analytics tables. No schema change occurred. Nansen source rows were read-only and unchanged.

## SECURITY_CHECK

No wallet identities, transaction hashes, token IDs, individual sales/prices, or credentials were recorded. `.env` is not tracked.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `src/otg_nansen/analytics_build.py`
- `tests/test_market_analytics.py`
- `DEV/reports/033_otg_nansen_hourly_analytics_foundation/report.md`
- `DEV/reports/033r6_ratify_existing_hourly_snapshot/report.md`

## TASK_033_RATIFICATION

All 12,336 canonical hourly market and aligned identities are physically present, ordered, gap-free, and duplicate-free after UTC normalization. Physical digests are stable across two same-memory replacements. Market aggregate count/sum agree with the read-only source aggregate. Nansen source remains unchanged. `TASK_033_RATIFIED_STATUS=SUCCESS`; this is a descriptive data foundation only.

## NEXT_RECOMMENDED_TASK

Any later correlation/event-study work requires a separately scoped review. This task produced no correlation, causal, predictive, or event-study result and performed no deployment.
