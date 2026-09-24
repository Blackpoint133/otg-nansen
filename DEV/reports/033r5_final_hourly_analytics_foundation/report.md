# Task 033R5: Final OTG–Nansen Hourly Foundation Attempt

## OBJECTIVE

Run one bounded overlap resolution and physically populate the staging hourly analytics snapshots. Data persistence completed, but the builder's non-UTC-aware Python duplicate assertion stopped the run before idempotency validation.

```text
TASK_033R5_STATUS=SOURCE_REPAIR_REQUIRED
TASK_033_RATIFIED_STATUS=NOT_COMPLETE
NEXT_PHASE_READY=NO
```

## STARTING_STATE

- Starting main: `f03849377dc50879d6c1f138f968065932bee280`, clean and synchronized.
- Source repair `1536f175a087637a02e3126cce4e80857e427726` was present.
- Analytics tables began empty.

## BASELINE_TESTS

`pytest -q`: 257 passed, 6 skipped. Default tests make no Nansen API, live RPC, or PostgreSQL connections.

## PRODUCTION_PREFLIGHT

Committed `production_readonly_connection()` verified `current_database=server_otg` and `transaction_read_only=on`. Production was queried only; DDL=0, DML=0, unchanged.

## STAGING_READONLY_PREFLIGHT

Committed staging read-only connection verified `server_otg_staging`, read-only on. Before execution, market/aligned rows were 0/0. Nansen source was 12,336 canonical hourly rows and 29 daily rows with digest `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.

## WRITER_CAPABILITY_PREFLIGHT

Before RPC, the committed SELECT-only capability preflight passed: database `server_otg_staging`, transaction read-only `off`, cursor `executemany` available, both target tables present. The connection was closed after SELECT-only checks.

## INSERT_SQL_EXPLAIN_PREFLIGHT

Before RPC, the exact two INSERT statements were extracted from the committed `replace_analytics_snapshot()` AST and passed to PostgreSQL as `EXPLAIN` with synthetic typed values. No INSERT was executed.

```text
MARKET_INSERT_EXPLAIN_PREFLIGHT=PASS
ALIGNED_INSERT_EXPLAIN_PREFLIGHT=PASS
MARKET_ROWS_AFTER_INSERT_EXPLAIN=0
ALIGNED_ROWS_AFTER_INSERT_EXPLAIN=0
```

## ANALYTICS_SCHEMA_PREFLIGHT

Read-only schema check found 7 market columns and 24 aligned columns. Each has one primary key and hour-end/check constraints. `ANALYTICS_SCHEMA_PREFLIGHT=PASS`.

## NANSEN_SOURCE_PREFLIGHT

Before build: hourly=12,336; daily=29; digest=`73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.

## LIVE_OVERLAP_RESOLUTION

One fresh bounded read-only campaign ran: 10,519 method objects (chain ID 43419, 5,632 receipts, 4,886 distinct block reads). Nansen API calls=0.

## OVERLAP_DIGEST_GATE

All accepted values reproduced: rows=5,632; receipts resolved=5,632/unresolved=0; distinct blocks=4,886/resolved=4,886/unresolved=0; offsets UTC+05=3,459, UTC−08=2,173, other=0; accepted digest `08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6`. Gate=PASS.

## IN_MEMORY_ANALYTICS

Market rows=12,336 and aligned rows=12,336 over `2025-04-25T00:00:00Z` through `2026-09-20T23:00:00Z`.

## PRIOR_DIGEST_REPRODUCTION

```text
MARKET_IN_MEMORY_CONTENT_DIGEST=0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e
ALIGNED_IN_MEMORY_CONTENT_DIGEST=9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8
MARKET_DIGEST_REPRODUCES_PRIOR_BUILDS=YES
ALIGNED_DIGEST_REPRODUCES_PRIOR_BUILDS=YES
```

## FIRST_PHYSICAL_PERSISTENCE

The committed replacement function used cursor `executemany` and committed both 12,336-row snapshots. The builder's market first-readback count and digest checks passed, then its raw Python `set(starts)` check raised. It did not reach the aligned first-readback helper or the second replacement.

## FIRST_READBACK

Post-failure read-only validation established for both tables: SQL rows=12,336; SQL distinct hours=12,336; UTC-normalized Python distinct starts=12,336; expected canonical identity set equal; missing=0; unexpected=0; adjacent UTC starts have no gaps. UTC min/max are the canonical endpoints.

Raw unnormalized Python `set(datetime)` size was 12,335 for each table because PostgreSQL returned local `ZoneInfo` timestamps and Python equality collapses the two repeated fall-back wall-clock representations. The UTC-normalized identity proof and SQL primary-key/distinct evidence show no persisted duplicate. This exposes a defect in `_assert_readback()`; no source fix was made after RPC.

## SECOND_IDEMPOTENCY_PERSISTENCE

Not run. No second same-memory replacement occurred. `ANALYTICS_PERSISTENCE_IDEMPOTENCY=NOT_PROVEN`.

## FINAL_MARKET_VALIDATION

Read-only physical state: 12,336 rows; min `2025-04-25T00:00:00Z`; max `2026-09-20T23:00:00Z`; missing=0; SQL duplicate hours=0. Activity hours=11,911; zero-activity hours=425. Aggregate trade transaction count=9,562,201; sum of truncated native GUN hourly amounts=356,791,669. Full-range distinct buyer/seller/item values were not captured and are not inferred by summing per-hour distinct counts.

## FINAL_ALIGNED_VALIDATION

Read-only physical state: 12,336 rows; min/max match the canonical endpoints; Nansen matched=12,336; market matched=12,336; missing source/spine hours=0; SQL duplicate hours=0.

## CONTENT_DIGESTS

Physical canonical digests, calculated from read-only staging readback:

```text
MARKET_HOURLY_CONTENT_DIGEST=0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e
ALIGNED_HOURLY_CONTENT_DIGEST=9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8
```

Both equal current in-memory digests and prior interrupted-build digests.

## LAG_FEATURE_QA

Physical non-null counts: GUN price return 1h=12,335, 6h=12,330, 24h=12,312; transaction-count delta 1h=12,335, 6h=12,330, 24h=12,312; native-GUN delta has the same respective counts.

## STRUCTURAL_QA

Across the 24 aligned columns, NULL counts are: `gun_price_return_1h`=1, `gun_price_return_6h`=6, `gun_price_return_24h`=24, `trade_tx_delta_1h`=1, `trade_tx_delta_6h`=6, `trade_tx_delta_24h`=24, `native_gun_delta_1h`=1, `native_gun_delta_6h`=6, `native_gun_delta_24h`=24; all other columns=0. Market field zero counts are: transaction count=425, native GUN amount=426, unique buyers=425, unique sellers=425, unique items=425. No correlation or event analysis was run.

## NANSEN_SOURCE_NON_REGRESSION

After the first persistence, a fresh staging read-only connection confirmed 12,336 hourly and 29 daily Nansen rows with the accepted identity digest. `NANSEN_SOURCE_NON_REGRESSION=PASS`.

## RESOURCE_OBSERVATION

| Stage | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before RPC | 36.1 | 4,352,393,216 | 4,877,148,160 | 16,092,729,344 | 11,215,581,184 |
| After RPC | 35.7 | 4,336,771,072 | 4,877,148,160 | 16,092,729,344 | 11,215,581,184 |
| After production aggregation | 52.8 | 4,638,048,256 | 4,877,053,952 | 16,092,729,344 | 11,215,675,392 |
| After analytical construction | 35.7 | 4,641,140,736 | 4,877,053,952 | 16,092,729,344 | 11,215,675,392 |
| After first staging write | 16.7 | 4,724,543,488 | 4,877,053,952 | 16,092,729,344 | 11,215,675,392 |

No second-write or final-validation resource sample exists. Resource pressure did not cause the stop.

## DEFAULT_TESTS

Baseline suite passed: 257 passed, 6 skipped. Final tests were not run after the builder's source-validation defect; no source code changed during or after the live run.

## NANSEN_API_PROOF

`NANSEN_API_CALLS_TASK033R5=0`.

## ONCHAIN_RPC_ACCOUNTING

`ONCHAIN_RPC_CALLS_TASK033R5=10519`, within the 11,265 cap. One campaign only; no retry campaign.

## PRODUCTION_SAFETY

Production connection mode was READ_ONLY; production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

The schema migration check ran against staging after source gates. The single snapshot replacement committed 12,336 rows into each analytics table. No later staging write was made. Further operations after the validation defect were read-only.

## SECURITY_CHECK

No row-level identities, wallets, transaction hashes, prices, RPC payloads, or credentials were reported. `.env` is not tracked.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `DEV/reports/033_otg_nansen_hourly_analytics_foundation/report.md` (chronological addendum)
- `DEV/reports/033r5_final_hourly_analytics_foundation/report.md`

No source, test, or migration files changed in Task 033R5.

## TASK_033_RATIFICATION

The physical hourly datasets are present and match all 12,336 canonical identities with matching deterministic digests. Full Task 033 acceptance remains incomplete because the builder's raw-local-time duplicate assertion is defective and its second same-memory idempotency write was not reached. Repair/test UTC normalization in the readback assertion, then separately authorize any required further write validation. Do not rerun the overlap campaign merely to recheck these persisted rows.

## RISKS

The readback helper's `len(set(starts))` uses local `ZoneInfo` datetimes directly; during the repeated fall-back hour, two distinct instants compare as equal. Any fresh builder run would reproduce the false duplicate failure unless the helper canonicalizes each value to UTC. No code was changed after RPC, consistent with the task stop rule.

## NEXT_RECOMMENDED_TASK

Make a source-only repair to normalize readback hour identities to UTC before set/continuity checks and add an offline DST-fold regression test. Then decide how to prove idempotency without repeating RPC or rebuilding from production; the persisted snapshot already has verified canonical counts/digests. No correlation analysis or deployment is authorized by this report.
