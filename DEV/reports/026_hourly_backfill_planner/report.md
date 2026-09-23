# Task 026: Resumable Hourly Backfill Planner

## OBJECTIVE

Implement and test a deterministic, overlapped, resumable planner for Avalanche `smart_money` hourly flow coverage. No live unit was executed.

## STARTING_STATE

Starting main was `554ad9e26c5c0c202a2b8baf1c0746442547aa5b`, branch `main`, clean. Baseline default tests passed: 180 passed, 6 skipped; no live API calls or default PostgreSQL connections.

## TASK025_EVIDENCE

Task 025's one shifted read-only request recovered the previously missing hourly bucket when it was internal to the request. Its own lower-bound bucket was absent; symmetric differences matched the one-hour shift. This observed behavior is limited to that tested interval and differed from the current official documentation's lower-bound description. It motivates one-hour pre-roll; no broader API behavior is inferred.

## BACKFILL_ARCHITECTURE_DECISION

Keep desired `coverage_start/coverage_end` separate from the Nansen `request_start/request_end`. Each request pre-rolls one hour; adjacent desired coverage intervals are contiguous and disjoint, while adjacent request windows include the prior unit's final hourly bucket. Progress comes from exact-window audit evidence, not flow counts or the high-water checkpoint.

## TARGET_COVERAGE

Inclusive desired hourly bucket starts: `2025-04-25T00:00:00Z` through `2026-09-20T23:00:00Z`, 12,336 starts.

## PLANNER_INVARIANTS

Inputs must be timezone-aware and are normalized to UTC. Bounds must be hour-aligned and ordered. A unit size must be a positive integer no greater than the request-duration policy permits. Coverage is inclusive at hourly bucket-start resolution. Every desired first bucket equals `request_start + 1 hour`.

## REQUEST_PRE_ROLL

`request_start=coverage_start-1 hour`; `request_end=coverage_end+59 minutes 59 seconds`. Full 167-start units span `6 days 23:59:59`. Adjacent request windows overlap by the final one-hour bucket of the prior unit (`REQUEST_BOUNDARY_OVERLAP_SECONDS=3600` as bucket duration).

## UNIT_MODEL

`HourlyFlowBackfillUnit` is immutable and records index, deterministic ID, stream identity, request bounds, coverage bounds, and desired count. `HourlyFlowBackfillPlan` records the target, units, bucket count, per-request maximum, and canonical call ceiling.

## DETERMINISTIC_UNIT_IDENTITY

The SHA-256 unit ID derives only from normalized chain, canonical token, flow label, and coverage/request bounds. It excludes time-of-run, randomness, metrics, database state, and run IDs. Replanning tests produce identical IDs/order/bounds; boundary changes produce different IDs.

## COVERAGE_VALIDATION

`validate_unit_coverage()` reads normalized timestamps and bucket durations only. It reports expected and observed desired starts, absent desired starts (`SOURCE_ABSENT_BUCKET`), unexpected starts inside/outside responsibility, hourly/non-hourly counts, and whether the request lower-bound bucket is absent (`REQUEST_BOUNDARY_GAP`). A missing source observation is reported, not treated as a planning failure. It verifies the first desired bucket is internal to the request.

## RESUME_CONTRACT

The sequential executor accepts a finite `max_units`, whole-batch `max_live_calls`, per-unit call ceiling, progress states, and an injected callback. It skips COMPLETE units, executes only PENDING units in ascending order, stops on the first callback failure, rejects AMBIGUOUS progress before execution, and checks budget before starting another unit. Calls are serial; this is a fakeable contract, not a live executor.

## AUDIT_COMPLETION_RULE

A unit is COMPLETE only if an exact matching successful audit exists for chain, flows endpoint, canonical token, `smart_money`, exact request bounds, and non-null structurally valid warning summaries (`[]` is valid). Failed exact runs remain PENDING. An exact success with NULL or malformed warning evidence is AMBIGUOUS unless a later valid warning-audited success exists. Multiple audit rows remain intact. The stream high-water checkpoint is not backfill progress state.

## EXECUTOR_SAFETY_CONTRACT

Offline fake tests prove stop-on-first-failure, skip-completed resume with `max_units=1`, call-ceiling rejection before the next callback, sequential order, and ambiguous-state refusal. The callback receives its explicit maximum call allowance and must configure any future client to that bound. No production target or concurrency is present in the planner.

## UNIT_TESTS

The focused planner suite passes 21 tests. It covers exact first, second, and final units; 167-unit maximum; UTC normalization and invalid inputs; gap/overlap and request duration; deterministic IDs; source absence versus request-boundary gap; exact audit completion; and executor resume/failure/budget behavior.

## FULL_PLAN_DRY_RUN

`python -m otg_nansen.backfill_plan` (with `PYTHONPATH=src` in an uninstalled checkout) prints only the structural plan summary. It makes zero Nansen calls and no database writes. Full plan: 12,336 desired starts, 74 units, 74-call ceiling.

## FIRST_UNIT

Coverage `2025-04-25T00:00:00Z`–`2025-05-01T22:00:00Z`; request `2025-04-24T23:00:00Z`–`2025-05-01T22:59:59Z`; 167 desired starts. Unit ID `daa4a9c3628b9aaf3a76cebf6b718f3399828c8c74fcf11bd7261f6ce25940d1`.

## SECOND_UNIT

Coverage `2025-05-01T23:00:00Z`–`2025-05-08T21:00:00Z`; request `2025-05-01T22:00:00Z`–`2025-05-08T21:59:59Z`; 167 desired starts. Unit ID `df72786d1fb923611e6f5b2db6569a4281e57b47c5945f898c98974f7f2fe91f`.

## FINAL_UNIT

Coverage `2026-09-14T23:00:00Z`–`2026-09-20T23:00:00Z`; request `2026-09-14T22:00:00Z`–`2026-09-20T23:59:59Z`; 145 desired starts. Unit ID `a8500d314f529d3d4efc8399d833ba4ffecf3d06252a3415fdcb958cf7eb7af3`.

## PLAN_MATHEMATICS

73 full units × 167 starts plus 145 final starts = 12,336. `TOTAL_PLAN_UNITS=74`; `FULL_PLAN_MAX_LIVE_CALLS=74`; coverage gaps 0; coverage overlaps 0.

## REQUEST_DURATION_VALIDATION

Maximum request duration is `6 days, 23:59:59`; all units are within that bound. `REQUEST_DURATION_POLICY=PASS`.

## READ_ONLY_STAGING_PROGRESS

After source/tests were complete, the optional progress mode connected read-only to `server_otg_staging` as `gunz_user`. Audit-based plan status: complete 0, pending 74, ambiguous 0. No DML or DDL was run.

## CURRENT_DATA_COVERAGE

Read-only structural snapshot for the canonical target: 190 hourly rows, 29 daily rows, zero other-duration rows; 219 global flow rows. Row counts were not used as unit completion evidence.

## CHECKPOINT_ROLE

Checkpoint remains `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. `HIGH_WATER_CHECKPOINT_USED_FOR_BACKFILL_PROGRESS=NO`.

## CREDIT_BUDGET_RECHECK

The current [official credits page](https://docs.nansen.ai/getting-started/credits) lists TGM Flows at 1 credit per call for Free and Pro. The account plan and balance were not queried. A 74-credit documented estimate assumes one API request per planned unit; actual call count and usage are not guaranteed by the pure planner.

## RESOURCE_OBSERVATION

Before staging inspection: CPU average 15.9% (range 5.6–25.9%), available RAM 4,949 MB, committed memory 20,603 MB, commit limit 31,730 MB, free commit 11,126 MB. After inspection and final default tests: CPU average 27.5% (range 24.8–32.6%), available RAM 4,609 MB, committed memory 20,863 MB, commit limit 31,730 MB, free commit 10,867 MB. `RESOURCE_STABILITY=PASS`.

## DEFAULT_TESTS

Final `pytest -q`: 201 passed, 6 skipped; default live API calls 0; default PostgreSQL connections 0. No live Nansen calls were made in Task 026.

## PRODUCTION_SAFETY

No production connection, DDL, or DML. Staging inspection was explicitly read-only. No API call, ingestion run, data write, checkpoint change, service, or scheduler was made.

## SECURITY_CHECK

No credential, raw warning, response, wallet address, transaction hash, metric value, or individual flow key was printed or committed. `SECRET_SCAN=PASS`; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

`src/otg_nansen/backfill.py`; `src/otg_nansen/backfill_plan.py`; `tests/test_backfill.py`; `docs/architecture.md`; `docs/operations.md`; `docs/analytics_methodology.md`; `docs/nansen_api.md`; this report. No migration or database artifact changed.

## RISKS

The one-hour pre-roll is based on one shifted diagnostic window and conflicts with current official wording for non-Hyperliquid first buckets. The plan is deterministic and tested, but no live batch has validated all units. Future execution must retain per-unit warning checks, request bounds, audit-based resumption, and the whole-batch call ceiling.

## NEXT_RECOMMENDED_TASK

Review Task 026 acceptance and separately authorize any bounded live execution. Do not execute a planned unit or start Task 027 automatically.
