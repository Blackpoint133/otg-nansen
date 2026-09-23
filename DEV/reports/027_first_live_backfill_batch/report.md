# Task 027: First Live Historical Backfill Batch

`TASK_027_STATUS=SUCCESS`

## OBJECTIVE

Wire the deterministic Task 026 planner to the existing ingestion stack and execute exactly the first three pending canonical hourly units on staging.

## STARTING_STATE

Starting remote main was `9339bbe7315c72014d2052b9d05b2871d9ab1a3b`, branch `main`, clean. Baseline tests: 201 passed, 6 skipped; default live API calls and PostgreSQL connections were zero. Staging had 219 flows, 190 canonical-target hourly rows, 29 daily rows, five audits, and checkpoint `2026-09-20T23:59:59Z` / `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## TASK026_PLAN

The canonical plan covers 12,336 hourly starts with 74 units. Each unit contains at most 167 desired starts and uses a one-hour request pre-roll. Progress comes from successful exact-window warning-audited runs, not the high-water checkpoint.

## EXECUTOR_HARDENING

`execute_pending_units()` now rejects callback call counts below one, negative counts, and counts above the assigned ceiling. A callback reporting one call with a one-call ceiling succeeds. COMPLETE units remain skipped without consuming calls.

## LIVE_RUNNER_DESIGN

`src/otg_nansen/backfill_execute.py` uses the canonical planner, read-only audit progress inspector, bounded executor, `NansenClient`, `PostgresRepository`, and `NansenIngestionOrchestrator`. It does not duplicate planner arithmetic or perform manual inserts.

## DOUBLE_OPT_IN

Live execution requires both `--execute` and `NANSEN_RUN_LIVE_BACKFILL=1`. Default invocation prints a structural dry-run/refusal, makes zero Nansen calls, and performs zero database writes.

## STAGING_GUARD

The runner pins connections to `server_otg_staging`, verifies `gunz_user`, checks read-only mode for discovery and writable mode for the repository, and offers no database override. No production connection was made.

## PRE_LIVE_PLAN_PROGRESS

Read-only staging progress was 0 complete, 74 pending, 0 ambiguous. The staging preflight matched 219 total flows, 190 hourly and 29 daily canonical-target rows, five ingestion audits, and the accepted checkpoint. There was no state drift.

## AUTHORIZED_UNIT_SELECTION

Units 1, 2, and 3 were selected in ascending pending order. Unit IDs: `daa4a9c3628b9aaf3a76cebf6b718f3399828c8c74fcf11bd7261f6ce25940d1`, `df72786d1fb923611e6f5b2db6569a4281e57b47c5945f898c98974f7f2fe91f`, and `2b1a7b615303300ba64c148c548472e8f0f0c27783041a725ae9d3a15949aca2`.

## PRE_LIVE_DATA_STATE

Global flows before: 219. Combined desired hourly identities already present: 167. Legacy ingestion runs before: five total, including the four prior warning-capture legacy rows. No run or data row was created by the dry-run refusal.

## DAILY_IDENTITY_BASELINE

The runner hashed the sorted daily natural identities in the combined selected coverage before execution. The post-run digest matched exactly: `DAILY_IDENTITY_DIGEST_UNCHANGED=PASS`. Individual identities and flow keys were not printed.

## RESOURCE_BASELINE

Before execution: CPU 35.1%; available RAM 4,780,516,384 bytes; Windows committed memory 22,098,489,344 bytes; commit limit 33,272,041,472 bytes; free commit 11,173,552,128 bytes.

## SOURCE_FIRST_COMMIT

Runner and executor hardening were pushed before live work. Initial source commit: `65509c2aab20a196cb2b3b88ed392b027395a83f`. A pre-request repository initialization correction was also pushed before live work. `PRE_LIVE_SOURCE_SHA=60d999ca396bf6b462cce0638bf885d9ee642e71`; remote readback matched. The first gated invocation stopped before any unit audit or Nansen attempt; read-only staging still showed five audits and 219 rows. The correction was pushed before the authorized execution.

## LIVE_BATCH_EXECUTION

The committed runner was invoked with both opt-ins, `max_units=3`, `max_live_calls=3`, and `max_calls_per_unit=1`. Each unit used a fresh client configured for one call, zero retries, page size 1000, one page, and a 120-second timeout. Exactly three Nansen attempts were used. No fourth request was made.

## UNIT_1_RESULT

Success, run `73290965-ae4a-4ffa-8cd1-f9316e4372a2`; coverage `2025-04-25T00:00:00Z`–`2025-05-01T22:00:00Z`; request `2025-04-24T23:00:00Z`–`2025-05-01T22:59:59Z`. One API call; 167 received and 167 normalized; final page reached. Request lower-bound bucket absent. Audit valid.

## UNIT_1_COVERAGE

167 desired; 167 observed; zero missing; six daily rows coexist in the coverage interval; zero duplicate hourly identities.

## UNIT_1_AUDIT

Successful exact-window Flows / Avalanche / `smart_money` run, one page, one API call, non-null sanitized warning audit containing one `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` warning summary. No UNKNOWN category.

## UNIT_1_PROGRESS

After unit 1: 1 complete, 73 pending, 0 ambiguous.

## UNIT_2_RESULT

Success, run `115f7de2-4584-4afd-8dc2-09844a73781b`; coverage `2025-05-01T23:00:00Z`–`2025-05-08T21:00:00Z`; request `2025-05-01T22:00:00Z`–`2025-05-08T21:59:59Z`. One API call; 167 received and 167 normalized; final page reached. Request lower-bound bucket present. Audit valid.

## UNIT_2_COVERAGE

167 desired; 167 observed; zero missing; seven daily rows coexist in the coverage interval; zero duplicate hourly identities.

## UNIT_2_AUDIT

Successful exact-window Flows / Avalanche / `smart_money` run, one page, one API call, non-null sanitized warning audit containing one `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` warning summary. No UNKNOWN category.

## UNIT_2_PROGRESS

After unit 2: 2 complete, 72 pending, 0 ambiguous.

## UNIT_3_RESULT

Success, run `da3cea0c-75ee-4f5d-ad09-047109a5e612`; coverage `2025-05-08T22:00:00Z`–`2025-05-15T20:00:00Z`; request `2025-05-08T21:00:00Z`–`2025-05-15T20:59:59Z`. One API call; 167 received and 167 normalized; final page reached. Request lower-bound bucket present. Audit valid.

## UNIT_3_COVERAGE

167 desired; 167 observed; zero missing; seven daily rows coexist in the coverage interval; zero duplicate hourly identities.

## UNIT_3_AUDIT

Successful exact-window Flows / Avalanche / `smart_money` run, one page, one API call, non-null sanitized warning audit containing one `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` warning summary. No UNKNOWN category.

## UNIT_3_PROGRESS

After unit 3: 3 complete, 71 pending, 0 ambiguous.

## WARNING_AUDIT_ACCOUNTING

Three new runs have non-null sanitized warning summaries; zero have NULL warning audits; zero contain UNKNOWN. Each source warning was retained only as the approved category/count/page summary. Raw warning text and response data were not printed or stored.

## BATCH_COVERAGE_ACCOUNTING

Unique desired hourly identities increased from 167 to 501. Newly added desired identities: 334. Existing desired identities reused: 167. Every unit had zero missing desired starts.

## DAILY_IDENTITY_PRESERVATION

The combined-coverage daily natural-identity digest is unchanged. Daily and hourly bucket identities coexist.

## GLOBAL_ROW_ACCOUNTING

Flow rows increased from 219 to 553. The canonical target now contains 524 hourly rows and 29 daily rows; the 334 additions were the only new hourly identities. Global natural-identity duplicates: zero. The retained September 20 day remains 23 rows with 23 natural identities. Ingestion audit rows increased from five to eight.

## RESTART_RESUME_PROOF

A fresh read-only plan inspection classified 3 complete, 71 pending, 0 ambiguous. Selecting one pending unit returns index 4. `RESTART_RESUME_PROOF=PASS`.

## CHECKPOINT_NON_REGRESSION

Checkpoint remains `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. Read-only post-run verification confirmed the checkpoint and the September 20 retained set of 23 rows / 23 natural identities. `CHECKPOINT_NON_REGRESSION=PASS`.

## RESOURCE_OBSERVATION

After units 1 / 2 / 3, CPU was 27.8% / 22.2% / 29.7%; available RAM was 4,758,196,224 / 4,762,480,640 / 4,762,603,520 bytes; committed memory was 22,111,469,568 / 22,107,181,056 / 22,105,063,424 bytes; free commit was 11,160,571,904 / 11,164,860,416 / 11,166,978,048 bytes. After batch: CPU 19.0%, available RAM 4,773,539,840 bytes, committed memory 22,097,494,016 bytes, commit limit 33,272,041,472 bytes, free commit 11,174,547,456 bytes. No pressure stop, retry loop, or abnormal connection growth was observed. `RESOURCE_STABILITY=PASS`.

## DEFAULT_TESTS

After execution, `pytest -q`: 206 passed, 6 skipped. Default live calls: zero; default PostgreSQL connections: zero.

## PRODUCTION_SAFETY

Staging only. `PRODUCTION_CONNECTIONS=0`; `PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`. No service or scheduler was added.

## SECURITY_CHECK

No API key, database password, GitHub credential, raw warning, raw response, wallet address, transaction hash, analytical metric, or individual flow key was printed or committed. `SECRET_SCAN=PASS`; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

Source-first commits changed `src/otg_nansen/backfill.py`, `src/otg_nansen/backfill_execute.py`, `tests/test_backfill.py`, and `tests/test_backfill_execute.py`. The evidence commit changes this report and `docs/architecture.md`, `docs/database.md`, `docs/operations.md`, `docs/analytics_methodology.md`, and `docs/nansen_api.md`.

## RISKS

This batch validates only three planned units. Task 025's request-boundary observation is based on a single shifted diagnostic request; future source behavior may change. Exact warning fingerprints deliberately fail closed on wording changes. No coverage claim is made for units 4 to 74.

## NEXT_RECOMMENDED_TASK

Review Task 027 evidence and separately authorize a bounded next batch beginning with unit 4. Do not execute unit 4 or start Task 028 automatically.
