# Task 025: Flows Lower-Bound Bucket Probe

## OBJECTIVE

Test whether the Task 024 missing hourly bucket appears when it is moved one hour inside a shifted seven-day Flows request.

## STARTING_STATE

Starting main was `55aab222fbb2ab78bf5522f272ec08ec2413e49f`, clean. Baseline tests: 180 passed, 6 skipped; default live API calls and PostgreSQL connections were zero. No application source change was made.

## TASK024_EVIDENCE

Task 024 retained 167 hourly rows from its seven-day request, earliest `2025-04-25T01:00:00Z`, latest `2025-05-01T23:00:00Z`, with 167 distinct timestamps and no missing calendar dates. The theoretical hourly start grid has 168 timestamps; `2025-04-25T00:00:00Z` is the missing grid timestamp.

## OFFICIAL_DOCUMENTATION_RECHECK

Current official [TGM Flows documentation](https://docs.nansen.ai/api/token-god-mode/flows) was reviewed on 2026-09-23. `date` is an inclusive aggregation-bucket start; `bucket_end` is exclusive; request `date.to` is an inclusive cutoff. The page states ranges of seven days or less return hourly snapshots. It says that on non-Hyperliquid chains the lower cutoff is aligned to the bucket start so the full first bucket is returned. It separately says Hyperliquid `is_complete` is false when `date.from` truncates the first bucket. It does not document omission of a partial first bucket for Avalanche. The live observation below conflicts with the documented non-Hyperliquid full-first-bucket behavior for this tested request; no attempt was made to reconcile the mismatch.

## READ_ONLY_STAGING_BASELINE

The connection was forced read-only and verified `server_otg_staging` / `gunz_user`. Task 024 structure matched: 167 hourly rows, earliest `2025-04-25T01:00:00Z`, latest `2025-05-01T23:00:00Z`; total flows 219; six daily rows also retained; checkpoint remained `2026-09-20T23:59:59Z` with run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## MISSING_GRID_TIMESTAMP

`EXPECTED_GRID_TIMESTAMPS=168`; `MISSING_GRID_TIMESTAMP_COUNT=1`; `MISSING_GRID_TIMESTAMPS=2025-04-25T00:00:00Z`.

## HOURLY_IDENTITY_BASELINE

SHA-256 over sorted natural hourly identities (chain, canonical token, flow label, UTC date, UTC bucket_end): `7721e2735690d243d661b0e661401c339b0de6e7e23bddc78f2e34d51a34d7ea`. Individual identities and flow keys were not printed or persisted.

## LIVE_CALL_BUDGET

The client was configured for one call, zero retries, page size 1000, one page, and 120 seconds. No second request was made.

## SHIFTED_REQUEST

One metadata-capable request was made to TGM Flows for Avalanche `smart_money`, from `2025-04-24T23:00:00Z` through `2025-05-01T22:59:59Z`, page 1, ascending date order. No database writes or ingestion orchestration occurred.

## WARNING_POLICY

One warning was observed and classified as `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`; warning policy passed. Raw warning content was neither printed nor persisted.

## NORMALIZATION

The same in-memory response normalized successfully. The structural warning guard passed.

## SHIFTED_RESPONSE_STRUCTURE

167 records; 167 distinct timestamps; earliest `2025-04-25T00:00:00Z`; latest `2025-05-01T22:00:00Z`; 167 hourly buckets; zero other-duration buckets; zero incomplete records. The response was final on page 1.

## LOWER_BOUND_TEST

`PREVIOUSLY_MISSING_BUCKET_PRESENT=YES` for the hourly bucket starting `2025-04-25T00:00:00Z` and ending one hour later. `SHIFTED_REQUEST_LOWER_BOUND_BUCKET_PRESENT=NO` for `2025-04-24T23:00:00Z`.

## OVERLAP_SET_COMPARISON

Intersection: 166 identities. Task 024 only: 1 identity at `2025-05-01T23:00:00Z`. Shifted response only: 1 identity at `2025-04-25T00:00:00Z`. The sets differ only at the expected endpoints for a one-hour shift.

## LOWER_BOUND_CLASSIFICATION

`LOWER_BOUND_CLASSIFICATION=LOWER_BOUND_BUCKET_OMITTED` for this tested request: the previously missing bucket appeared when internal, the shifted request's own lower-bound bucket was absent, and identity differences otherwise matched the one-hour shift. This observation conflicts with current official documentation for non-Hyperliquid first-bucket behavior. It does not establish a universal API rule or the cause of the original absence.

## BACKFILL_SAFETY_DECISION

`NAIVE_NONOVERLAPPING_WEEKLY_BACKFILL_SAFE=NO` for complete coverage under the observed behavior. Any future request strategy should use boundary overlap or shifted windows so each desired first bucket falls inside a request, while keeping every Nansen request duration at or below seven days. No planner was implemented.

## PERSISTED_STATE_VERIFICATION

Database connections used `default_transaction_read_only=on`. Flow rows remained 219, including 167 Task 024 hourly and 6 daily rows. Hourly natural-identity digest remained unchanged. Five ingestion runs remained; no run was created. The checkpoint remained at `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. `DATABASE_READS_ONLY=YES`; writes 0; DDL 0; `CHECKPOINT_CHANGED=NO`; `PERSISTED_STATE_UNCHANGED=PASS`.

## RESOURCE_OBSERVATION

Before: CPU average 39.6% (range 30.0–47.2%), available RAM 4,636 MB, committed memory 20,748 MB. After: CPU average 62.0% (range 26.9–85.4%), available RAM 4,718 MB, committed memory 20,707 MB. Commit limit remained 31,730 MB; free commit increased from 10,982 MB to 11,023 MB. CPU was variable; memory/commit headroom remained stable. `RESOURCE_STABILITY=PASS`.

## DEFAULT_TESTS

After the probe: `pytest -q` => 180 passed, 6 skipped; live API calls 0; PostgreSQL connections 0.

## PRODUCTION_SAFETY

No production connection or mutation was made. `PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`.

## SECURITY_CHECK

No raw warning, raw response, metric value, credential, wallet address, transaction hash, or individual flow key was printed or committed. `SECRET_SCAN=PASS`; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

`DEV/reports/025_flow_lower_boundary_probe/report.md`; `docs/nansen_api.md`; `docs/analytics_methodology.md`; `docs/operations.md`. No application source or schema changes.

## RISKS

This single shifted request suggests a lower-bound omission for the tested Avalanche `smart_money` interval, contrary to current official wording for other chains. Do not generalize to other windows, labels, or chains. Naive non-overlapping weekly requests are unsafe for full hourly coverage until boundary behavior and a request planner are reviewed.

## NEXT_RECOMMENDED_TASK

Review the documented/live boundary discrepancy and design a separately authorized, read-only validation or boundary-overlap planner. Do not start systematic historical backfill or Task 026.
