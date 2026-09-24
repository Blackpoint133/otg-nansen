# Task 033: OTG–Nansen Hourly Analytics Foundation

## OBJECTIVE

Implement and begin the source-first build of the analysis-ready hourly data foundation. The code, migration, and offline tests were committed and pushed before staging DDL. The live builder passed the read-only source checks, overlap digest gate, aggregation, alignment, and in-memory digest construction. It then stopped before inserting any data because the staging writer opened with an incorrect psycopg call signature.

```text
TASK_033_STATUS=BUILDER_CONNECTION_FAILURE
```

The source bug was fixed and pushed. This task did not rerun the builder because it had already used 10,519 of its 11,265 authorized on-chain RPC method objects; the in-memory overlap mapping was not persisted, so rerunning would require a new complete resolution pass.

## STARTING_STATE

- Starting `HEAD` / `origin/main`: `894e8b59cd047bac92f775dd2245889fe82ddb87`, synchronized and clean.
- Initial tests: 231 passed, 6 skipped.
- Accepted canonical Nansen state: 12,336 hourly identities, 29 retained daily rows, digest `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.
- Accepted overlap contract: 5,632 rows; 3,459 UTC+05:00; 2,173 UTC−08:00; 4,886 distinct blocks; digest `08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6`.

## ACCEPTED_DATA_CONTRACTS

Market rows retain the `marketplace_trade_event_transaction` meaning. Market values are parser-recorded native GUN Trade amounts after integer truncation. No USD sale volume or 1:1 bridge conversion is used. Native GUN marketplace values and Avalanche Nansen values remain separate. The timestamp contract uses fixed UTC+05:00 before the overlap, Pacific local-time rules afterward, and exact containing-block UTC within the overlap.

## BASELINE_TESTS

Before implementation: `pytest -q` reported 231 passed, 6 skipped. After implementation and the staging-writer fix: 253 passed, 6 skipped. The added tests use synthetic values/fakes; default tests make no Nansen call and no PostgreSQL connection.

## NANSEN_SOURCE_SCHEMA

Read-only schema inspection verified `nansen.flows` provides `date` and `bucket_end` as `timestamp with time zone`; `price_usd`, `token_amount`, `value_usd`, `total_inflows_count`, and `total_outflows_count` as `numeric`; `holders_count` as `bigint`; and optional CEX/DEX breakdown columns as nullable `bigint`. The build omits those breakdown fields because they are unavailable under the accepted source warning. Canonical source checks found 12,336 hourly, 29 daily, 12,365 total rows; the hourly identity digest matched the accepted value.

## ANALYTICS_DATA_MODEL

Migration 005 creates `nansen.otg_market_hourly` with seven columns and `nansen.otg_nansen_hourly` with 24 columns. Both use UTC `hour_start` primary keys and one-hour boundary checks. The market table includes transaction counts, truncated native GUN amounts, and distinct buyer/seller/item counts; it has no raw sale identity, wallet, transaction hash, or market USD column. The aligned table adds the verified Nansen fields and mechanical returns/deltas.

## TIMESTAMP_IMPLEMENTATION

The production reader is pinned to `server_otg`, starts with `default_transaction_read_only=on`, sets the transaction read-only, and verifies the live database/mode. Production aggregation is SQL-side over reconstructed UTC time. It combines normal-regime and parameterized overlap rows in one logical stream before computing hourly and full-range distinct counts.

## OVERLAP_RESOLUTION

The builder confirmed `server_otg` / `gunz_user` / read-only `on` and overlap population 5,632. The official Avalanche-hosted GUNZ RPC returned chain ID 43419. One receipt was fetched per row; the 4,886 distinct blocks were fetched once each.

```text
ONCHAIN_RPC_CALLS_TASK033=10519
OVERLAP_RECEIPTS_RESOLVED=5632
OVERLAP_RECEIPTS_UNRESOLVED=0
OVERLAP_DISTINCT_BLOCKS=4886
OVERLAP_BLOCKS_UNRESOLVED=0
OVERLAP_OFFSET_PLUS_05_ROWS=3459
OVERLAP_OFFSET_MINUS_08_ROWS=2173
OVERLAP_OFFSET_OTHER_ROWS=0
OVERLAP_TIME_RESOLUTION_DIGEST=08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6
OVERLAP_DIGEST_GATE=PASS
```

The transition bounds reproduced as `2026-02-28T06:08:18Z` and `2026-02-28T06:09:10Z`; non-interleaved ordering passed. No transaction hashes or row-level mappings were persisted.

## OVERLAP_DIGEST_GATE

The exact accepted digest gate passed before production aggregation and before staging migration/write. The in-memory mapping was released when the builder process ended after its writer connection error. No second RPC pass was attempted under this task’s remaining 746-object budget.

## PRODUCTION_READ_ONLY_PROOF

The builder and final read-only check connected to `server_otg` as `gunz_user` with transaction read-only `on`. Production `public.sales` was only queried. Production DDL=0, DML=0, changed=NO.

## MARKET_AGGREGATION

The production-side SQL aggregation completed in read-only mode over a broad stored-time filter and applied canonical UTC inclusion after timestamp reconstruction. It computed hourly counts/sums/distincts and full-range distinct totals in PostgreSQL, avoiding a Python load of raw sales. The builder formed the canonical 12,336-hour zero-filled spine and aligned Nansen data in memory. Market source totals were computed but were not emitted before the process stopped; this report does not claim their physical validation.

## CANONICAL_HOURLY_SPINE

The in-memory spine contained 12,336 UTC hours from `2025-04-25T00:00:00Z` through `2026-09-20T23:00:00Z`. Zero-activity hours were represented with zero counts and zero native amount.

## NANSEN_ALIGNMENT

The 12,336 canonical Nansen rows aligned by exact UTC `hour_start`. No Nansen API call was made. The aligned rows existed only in process memory because the subsequent writer connection failed.

## DERIVED_FEATURES

The implementation computes 1/6/24-hour Nansen price returns with NULL for missing/zero lag denominators; flow count difference/sum; and absolute transaction/native-GUN deltas. No statistical comparison, correlation, event effect, causal claim, or prediction was run.

## OFFLINE_TESTS

Coverage includes fixed UTC+05:00 and Pacific standard/daylight conversion, spring-forward nonexistent-hour rejection, overlap bounds/digest/budget, RPC block caching and failure cases, connection guards, zero-hour preservation, distinct counts across partitions, exact alignment, lag arithmetic, NULL denominator behavior, deterministic content digests, and atomic snapshot replacement with fakes. Final test run: 253 passed, 6 skipped.

## SOURCE_FIRST_COMMIT

The complete implementation/migration/tests/docs commit was pushed before staging DDL:

```text
PRE_WRITE_SOURCE_SHA=ed1c6687ccc30154e65fe4b677e6085efa1380f6
```

The live builder reached migration 005 only after the overlap gate and complete in-memory analytical dataset/digests had passed. The staging writer bug was then fixed and pushed before any staging DML:

```text
WRITER_FIX_SHA=f516328b21150046c5c4d0216b0c438a2ec644f5
```

## STAGING_MIGRATION

Migration 005 applied successfully to `server_otg_staging` after the source-first commit. Read-only inspection confirms both analytics tables exist with the intended column counts and zero rows. Staging DDL=authorized migration only; staging DML=0.

## LIVE_BUILD

The builder completed Nansen source validation, overlap resolution/digest validation, production SQL aggregation, 12,336-hour spine/alignment construction, and in-memory content digests. It applied the staging migration, then failed while opening the staging writer because the connection kwargs dictionary had been passed positionally to `psycopg.connect`. The error occurred before a writer connection existed and before any INSERT or DELETE. The corrected writer call was pushed as `f516328b21150046c5c4d0216b0c438a2ec644f5`.

## MARKET_TABLE_VALIDATION

Read-only post-check: `nansen.otg_market_hourly` exists and contains 0 rows. The build’s in-memory market digest was `0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e`; physical row validation was not reached.

## ALIGNED_TABLE_VALIDATION

Read-only post-check: `nansen.otg_nansen_hourly` exists and contains 0 rows. The build’s in-memory aligned digest was `9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8`; physical row validation was not reached.

## CONTENT_DIGESTS

```text
MARKET_HOURLY_CONTENT_DIGEST=0319bc770ff05422d60a77f51ccb39c4835a749c6e3a5f562492062a0609155e
ALIGNED_HOURLY_CONTENT_DIGEST=9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8
```

These are in-memory content digests from the interrupted build, not physical staging readbacks.

## LAG_FEATURE_QA

The builder had formed aligned rows, but lag/null aggregate diagnostics were not emitted before the writer failure. Physical lag QA remains pending.

## SOURCE_NON_REGRESSION

Read-only checks before and after the attempt found 12,336 canonical Nansen hourly rows, 29 daily rows, 12,365 total flow rows, and the accepted hourly identity digest. The analytics attempt did not write `nansen.flows`.

## IDEMPOTENCY_PROOF

Not run. No staging data snapshot was written, so there is no physical first/second persistence readback comparison.

## STRUCTURAL_QA

No physical analytical rows exist yet. Structural checks of table counts, zero-hour retention, and aligned coverage cannot be claimed from empty tables.

## RESOURCE_OBSERVATION

Memory values are bytes; CPU is a point sample.

| Stage | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before overlap RPC | 77.8 | 4,070,400,000 | 4,837,736,448 | 16,092,729,344 | 11,254,992,896 |
| After overlap RPC | 57.1 | 4,051,140,608 | 4,837,691,392 | 16,092,729,344 | 11,255,037,952 |
| After production aggregation | 28.6 | 4,296,945,664 | 4,837,605,376 | 16,092,729,344 | 11,255,123,968 |
| After analytical construction | 35.7 | 4,295,020,544 | 4,837,605,376 | 16,092,729,344 | 11,255,123,968 |
| Final read-only check | 2.8 | 4,416,696,320 | 4,837,548,032 | 16,092,729,344 | 11,255,181,312 |

`RESOURCE_STABILITY=PASS`; available RAM remained above 4 GB and free commit above 11 GB. No first/second staging-write resource samples exist because no data write occurred.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033=0`.

## ONCHAIN_RPC_CALL_ACCOUNTING

10,519 allowed read-only GUNZ JSON-RPC method objects were used: one chain check, 5,632 receipts, and 4,886 unique blocks. No retries or state-changing methods were used. Remaining budget in this task at stop: 746 objects; this was insufficient to repeat the full mapping, and no second pass was attempted.

## PRODUCTION_SAFETY

Production connection mode: READ_ONLY. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

Staging migration 005 created the two intended tables after source push and full read-only/data-construction gates. Both tables remain empty. Staging DML=0.

## SECURITY_CHECK

No raw production rows, transaction hashes, wallet addresses, token identifiers, raw RPC payloads, or credentials were committed. `.env` is not tracked.

## CYRILLIC_CHECK

PASS. English-only files.

## FILES_CHANGED

Source-first commit `ed1c6687ccc30154e65fe4b677e6085efa1380f6`:

- `src/otg_nansen/market_analytics.py`
- `src/otg_nansen/analytics_build.py`
- `src/otg_nansen/migrate_analytics.py`
- `sql/005_otg_nansen_hourly_analytics.sql`
- `tests/test_market_analytics.py`
- `docs/architecture.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/analytics_methodology.md`
- `docs/market_reaction_methodology.md`

Writer fix commit `f516328b21150046c5c4d0216b0c438a2ec644f5`:

- `src/otg_nansen/market_analytics.py`
- `tests/test_market_analytics.py`

This evidence commit:

- `DEV/reports/033_otg_nansen_hourly_analytics_foundation/report.md`
- `docs/operations.md` (records the interrupted attempt and recovery requirement)

## RISKS

The authorized RPC cap was reached near its maximum before the writer defect was exposed. The overlap mapping is intentionally not persisted, so completing the data write requires a new explicitly authorized overlap-resolution pass. Analytics tables exist but are empty. No task completion or physical analytics validation is claimed.

## NEXT_RECOMMENDED_TASK

Authorize a fresh bounded build pass of up to 10,519 read-only GUNZ RPC method objects. The source writer fix and migration are already pushed/applied; the next run should use `PYTHONPATH=src` (or an installed package), recreate and validate the overlap mapping, then populate/read back both staging snapshots and prove same-memory idempotency.
