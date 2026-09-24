# Task 029R: Complete Interrupted Backfill Batch

`TASK_029R_STATUS=SUCCESS`

## OBJECTIVE

Complete the five pending canonical units 29–33 after Task 029 stopped on a false-positive DST-fold identity comparison. No units 14–28 were repeated.

## STARTING_STATE

Starting `main` was `3d4e68b2ef9d50a56ada250b9ccf31e59d6e0370`, clean. Default baseline tests passed: 219 passed, 6 skipped; zero test Nansen calls and zero default PostgreSQL connections.

## TASK029_INTERRUPTION

Task 029 remains recorded as `LIVE_BATCH_FAILURE`. Its runner stopped after unit 28 because PostgreSQL-returned `America/Los_Angeles` fold timestamps were compared directly with UTC planner datetimes. Task 029R reviewed the committed UTC conversion and did not rewrite that earlier outcome.

## UTC_FIX_REVIEW

`_utc_identity()` rejects naive values and converts each aware bucket endpoint to `timezone.utc`. `_target_counts()` and `_validate_unit_readonly()` use this helper before comparing structural bucket identities.

## DST_REGRESSION_TEST

The offline regression test uses `America/Los_Angeles` on 2025-11-02: local 01:00 fold 0 through local 01:00 fold 1 canonicalizes to `2025-11-02T08:00:00Z` through `2025-11-02T09:00:00Z`.

## BASELINE_TESTS

Before live work: `pytest -q` passed, 219 passed, 6 skipped. The test suite made zero Nansen calls and zero default PostgreSQL connections.

## READ_ONLY_PROGRESS

Staging identity was verified read-only as `server_otg_staging` / `gunz_user`. Canonical progress was 28 complete / 46 pending / 0 ambiguous. First pending index was 29.

## UNIT28_PHYSICAL_REVALIDATION

Using the committed validator and its UTC canonicalization, unit 28 has 167 desired / 167 observed / zero missing / zero duplicate hourly identities. Its exact-window audit is valid and its progress state is COMPLETE. `DST_FIX_PHYSICAL_REVALIDATION=PASS`.

## UNITS14_28_COMBINED_REVALIDATION

Read-only UTC-normalized validation confirms 2,505 desired / 2,505 observed / zero missing / zero duplicates across units 14–28.

## PRE_LIVE_STAGING_STATE

Counts matched the authorization: 4,728 total flow rows, 4,699 canonical target hourly rows, 29 daily rows, and 33 ingestion audits. Global natural-identity duplicates were zero. September 20 remained 23 hourly rows / 23 identities. The checkpoint remained `2026-09-20T23:59:59Z` / `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## AUTHORIZED_SELECTION

The generic progress selection chose units 29–33 in ascending order:

| Unit | Unit ID |
|---:|---|
| 29 | `44d29412ee215ec88fa6e92fcbab3f14244fbf0a16df52f0340f21e071d911b3` |
| 30 | `11e27c2c184d6fb1c5e60b4019ebe005a11d5a21fd2fa24148633259b05d0556` |
| 31 | `b2d8e3a5dd97974808f53afcd1b28f09825985b85a5828cd905b032d09728ed8` |
| 32 | `c61871d091dc06d6d08cfd614968bb461162145213682c0afcb09806524d1e90` |
| 33 | `c91f494f816dd24dae240bf2f6375d0f224f380fb78c685a9d05959a8d7304f0` |

## BOUNDARY_SANITY

| Unit | Coverage window (inclusive bucket starts) | Nansen request window |
|---:|---|---|
| 29 | `2025-11-05T20:00:00Z` to `2025-11-12T18:00:00Z` | `2025-11-05T19:00:00Z` to `2025-11-12T18:59:59Z` |
| 30 | `2025-11-12T19:00:00Z` to `2025-11-19T17:00:00Z` | `2025-11-12T18:00:00Z` to `2025-11-19T17:59:59Z` |
| 31 | `2025-11-19T18:00:00Z` to `2025-11-26T16:00:00Z` | `2025-11-19T17:00:00Z` to `2025-11-26T16:59:59Z` |
| 32 | `2025-11-26T17:00:00Z` to `2025-12-03T15:00:00Z` | `2025-11-26T16:00:00Z` to `2025-12-03T15:59:59Z` |
| 33 | `2025-12-03T16:00:00Z` to `2025-12-10T14:00:00Z` | `2025-12-03T15:00:00Z` to `2025-12-10T14:59:59Z` |

Each unit contains 167 desired starts. No task-specific bounds were added to reusable source.

## BATCH_IDENTITY_BASELINE

`BATCH_DESIRED_BUCKETS=835`; desired identities present before execution: 0.

## DAILY_IDENTITY_BASELINE

Daily natural-identity digest before: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` (empty daily set in these five windows).

## RESOURCE_BASELINE

Pre-invocation sample: CPU 19.0%; available RAM 4,626,587,648 bytes; committed memory 22,393,937,920 bytes; commit limit 33,272,041,472 bytes; free commit 10,878,103,552 bytes. The runner's immediate pre-request sample was also within normal headroom.

## LIVE_EXECUTION

The committed generic runner used `--execute`, both live gates, five units / five calls, and all expected staging snapshot assertions. Each selected unit used a fresh one-attempt client, zero retries, page size 1,000, one page maximum, and a 120-second timeout. Exactly five Nansen attempts occurred.

| Unit | Run ID | Calls | Received / normalized | Desired / observed / missing | Request-start bucket | Audit | Progress after unit | Resource snapshot (CPU; available RAM; commit used; free commit) |
|---:|---|---:|---:|---:|---|---|---|---|
| 29 | `87a2e795-0341-4ccf-9174-7336f7f5ef58` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 29 / 45 / 0 | 16.7%; 4,583,104,512; 22,255,325,184; 11,016,716,288 |
| 30 | `f2657bf2-a660-4053-a1b2-2baa5f74c8bf` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 30 / 44 / 0 | 36.1%; 4,570,509,312; 22,254,026,752; 11,018,014,720 |
| 31 | `abeef586-0644-4baf-a0e1-203912f0b970` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 31 / 43 / 0 | 77.8%; 4,592,742,400; 22,225,182,720; 11,046,858,752 |
| 32 | `073727dc-4647-4b2e-85b6-ad79a022b475` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 32 / 42 / 0 | 23.8%; 4,561,612,800; 22,254,194,688; 11,017,846,784 |
| 33 | `6e260c4c-90ec-46b3-8906-5bdc02a00631` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 28.6%; 4,558,757,888; 22,256,320,512; 11,015,720,960 |

## UNIT_29_RESULT

Successful; one API call; 167 records received and normalized.

## UNIT_29_AUDIT

Exact-window success, one page, one API call, non-null sanitized warning audit; category `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` only.

## UNIT_29_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities; request-start bucket present.

## UNIT_29_PROGRESS

29 complete / 45 pending / 0 ambiguous.

## UNIT_29_RESOURCE_STATE

CPU 16.7%; available RAM 4,583,104,512 bytes; committed 22,255,325,184 bytes; commit limit 33,272,041,472 bytes; free commit 11,016,716,288 bytes.

## UNIT_30_RESULT

Successful; one API call; 167 records received and normalized.

## UNIT_30_AUDIT

Exact-window success, one page, one API call, non-null sanitized warning audit; approved category only.

## UNIT_30_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities; request-start bucket present.

## UNIT_30_PROGRESS

30 complete / 44 pending / 0 ambiguous.

## UNIT_30_RESOURCE_STATE

CPU 36.1%; available RAM 4,570,509,312 bytes; committed 22,254,026,752 bytes; commit limit 33,272,041,472 bytes; free commit 11,018,014,720 bytes.

## UNIT_31_RESULT

Successful; one API call; 167 records received and normalized.

## UNIT_31_AUDIT

Exact-window success, one page, one API call, non-null sanitized warning audit; approved category only.

## UNIT_31_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities; request-start bucket present.

## UNIT_31_PROGRESS

31 complete / 43 pending / 0 ambiguous.

## UNIT_31_RESOURCE_STATE

CPU 77.8%; available RAM 4,592,742,400 bytes; committed 22,225,182,720 bytes; commit limit 33,272,041,472 bytes; free commit 11,046,858,752 bytes.

## UNIT_32_RESULT

Successful; one API call; 167 records received and normalized.

## UNIT_32_AUDIT

Exact-window success, one page, one API call, non-null sanitized warning audit; approved category only.

## UNIT_32_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities; request-start bucket present.

## UNIT_32_PROGRESS

32 complete / 42 pending / 0 ambiguous.

## UNIT_32_RESOURCE_STATE

CPU 23.8%; available RAM 4,561,612,800 bytes; committed 22,254,194,688 bytes; commit limit 33,272,041,472 bytes; free commit 11,017,846,784 bytes.

## UNIT_33_RESULT

Successful; one API call; 167 records received and normalized.

## UNIT_33_AUDIT

Exact-window success, one page, one API call, non-null sanitized warning audit; approved category only.

## UNIT_33_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities; request-start bucket present.

## UNIT_33_PROGRESS

33 complete / 41 pending / 0 ambiguous.

## UNIT_33_RESOURCE_STATE

CPU 28.6%; available RAM 4,558,757,888 bytes; committed 22,256,320,512 bytes; commit limit 33,272,041,472 bytes; free commit 11,015,720,960 bytes.

## BATCH_WARNING_AUDIT

Five new successful runs have non-null sanitized warning summaries, zero NULL warning audits, and zero UNKNOWN categories. Each observed warning classified only as `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`.

## BATCH_COVERAGE

835 desired / 835 observed / zero missing. Before: zero present; 835 new identities; zero reused.

## GLOBAL_ROW_ACCOUNTING

Flow rows increased from 4,728 to 5,563 (+835); canonical target hourly rows increased from 4,699 to 5,534; daily rows remained 29. `GLOBAL_FLOW_ROW_ACCOUNTING=PASS`.

## IDENTITY_INTEGRITY

Global natural-identity duplicates: zero.

## DAILY_IDENTITY_PRESERVATION

Digest before and after: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`. Unchanged.

## AUDIT_ROW_ACCOUNTING

Ingestion audits increased from 33 to 38. All five new success audits contain non-null sanitized warning evidence.

## CHECKPOINT_NON_REGRESSION

Checkpoint remains `2026-09-20T23:59:59Z` / `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## RECENT_DATA_INTEGRITY

September 20 remains 23 hourly rows / 23 identities.

## RESTART_RESUME_PROOF

Fresh canonical replan and read-only progress inspection: 33 complete / 41 pending / 0 ambiguous. First pending unit is 34.

## RESOURCE_OBSERVATION

After batch: CPU 29.7%; available RAM 4,562,882,560 bytes; committed memory 22,251,167,744 bytes; commit limit 33,272,041,472 bytes; free commit 11,020,873,728 bytes. Headroom remained stable; no retry loop or abnormal resource pressure occurred.

## DEFAULT_TESTS

After recovery: `pytest -q` passed, 219 passed and 6 skipped. Default Nansen calls: zero; default PostgreSQL connections: zero. No additional API validation call was made.

## PRODUCTION_SAFETY

Staging only. Production connections, DDL, DML, and changes: zero. No service or scheduler was added.

## SECURITY_CHECK

No raw warnings/responses, credentials, wallet addresses, transaction hashes, metric values, or individual flow keys were printed or committed. Secret scan passed; `.env` is not tracked.

## CYRILLIC_CHECK

Pass.

## FILES_CHANGED

Evidence-only changes: this report, a historical addendum to the Task 029 report, and addenda to the five requested documentation files. No source changes were made.

## RISKS

Task 029's failure status remains as originally recorded; Task 029R completes the five units left pending by that stopped invocation. Unit 34 is next and was not run.

## NEXT_RECOMMENDED_TASK

Review the combined Task 029 / 029R evidence. Any further backfill requires separate authorization; do not execute unit 34 or start Task 030 automatically.
