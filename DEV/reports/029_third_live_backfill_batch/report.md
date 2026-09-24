# Task 029: Third Live Historical Backfill Batch

`TASK_029_STATUS=LIVE_BATCH_FAILURE`

## OBJECTIVE

Finalize the reusable bounded live runner and execute the authorized next twenty pending canonical units. The runner was generalized and pushed before the live invocation. The initial structural validator stopped at unit 28 after reporting three missing desired starts. A read-only UTC-normalized recheck established that those starts were present; the stop came from a daylight-saving-fold datetime comparison defect. The batch was not resumed, consistent with stop-on-first-validation-failure.

## STARTING_STATE

Starting main was `ebc658afd8365a48e6466b6ffcab699acf20e2ee`, clean on `main`. Baseline tests passed: 218 passed, 6 skipped; no live API calls or default PostgreSQL connections.

## TASK028_ACCEPTED_STATE

Before this task, staging held 2,223 flow rows: 2,194 canonical hourly rows and 29 daily rows. There were 18 ingestion runs; canonical progress was 13 complete / 61 pending / 0 ambiguous, with unit 14 next. September 20 remained 23 hourly rows / 23 identities. The high-water checkpoint was `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## GENERIC_RUNNER_FINALIZATION

Removed the Task 028 bounds constant and validator and all task-numbered runtime result output. The runner now reports `BACKFILL_BATCH_STATUS` with generic success, coverage-gap, or live-failure values. Its one-call-per-unit budget now requires `max_live_calls == max_units`. The absolute ceilings remain 20 units and 20 calls. Staging pinning, double opt-in, read-only progress discovery, expected-state gates, per-unit fresh one-call clients, fail-closed warnings, coverage checks, progress checks, resource stops, and restart proof remain in place.

## OFFLINE_TESTS

Before live execution: `pytest -q` passed, 218 passed and 6 skipped. Tests cover the generic batch status, equality of unit/call budgets, resumed selection 14–33, dynamic progress to 33/41/0, generic next index 34, skipped complete units, ambiguity refusal, stop-on-failure, resource stopping, and dry-run opt-in. No live requests or PostgreSQL connections were made by the default suite.

## SOURCE_FIRST_COMMIT

The generic runner and test change was committed and pushed before live work as `785d7d56cf7199b1ceede12c62f9f141489225a9`. Remote readback matched before execution. After the batch stopped, UTC canonicalization and a DST-fold regression test were committed as `1a8a25f5cb62d219cafd2b1483ff27f4effbbc6b`; this correction made no Nansen calls and did not resume execution.

## PRE_LIVE_STAGING_STATE

Read-only inspection verified staging identity and read-only mode. Counts matched authorization: 2,223 total flows, 2,194 hourly, 29 daily, 18 audits, September 20 rows/identities 23/23, and the accepted checkpoint/run. No progress ambiguity was present.

## PRE_LIVE_PLAN_PROGRESS

`PLAN_COMPLETE_BEFORE=13`; `PLAN_PENDING_BEFORE=61`; `PLAN_AMBIGUOUS_BEFORE=0`; first pending index 14.

## AUTHORIZED_SELECTION

Dynamic ascending selection was units 14 through 33, exactly 20 contiguous units. Unit IDs, in order: `fc359b3023c49591241453f5dfb0fc7f06751da0416e1be319535ba0bd66077d`, `aa64e6ccad66f600ca37f64f790553ef383120fdd05ff25317be868a51efe3c2`, `8cfb228f53a4fa009130b9a1525c69d6d73d615ec415e11edd8653e564f37921`, `2f58a4351e45578b031b94e116f9a587a28d1e0a3bd27318c9aa9cd66a86e719`, `a7cbea38d69ee870cac2926b0d8e0072c7d2ee9fa0036460acb8eb4afd7ae2ad`, `d4dc04ee37b33e35d5f6e790d6b6fc1d9726477844146d58c03102b11c6dbdaa`, `b5851ce4295e8f5348e001b1f5a38c935289990e9bcc00b9949c87b24f974b6c`, `4d3bf6fa04ba92ab8aca648fdf564a0618bcfcffd10c155b1b79ce329c8a8950`, `d26479249ec1b46f3612b333811996025144eb7a7aac2e5f1bd0448c6561db3c`, `02d4ddc0b49058d8d567b286c21447559b68c564620bef8813b0c812c0a60b3e`, `275abca4ad224519c5bebdf83ba98982db19275ceb270901e2f9092a8811bca8`, `5b426845d997d7d86bcbf3448067c60d798aa0716eb7abca39dae0844442ede7`, `c414ecc2480058656eb46aa005397ec81855480101efdba90464457d165a6cd2`, `eb8019db330a22aa1c17559e0aa6b7a44483708ddc09a17e7441e7a3acb954e8`, `c9cebc6c20e2c47e102a42bdd45aa831f62a73e690fe37cd1a35a031ea7bf695`, `44d29412ee215ec88fa6e92fcbab3f14244fbf0a16df52f0340f21e071d911b3`, `11e27c2c184d6fb1c5e60b4019ebe005a11d5a21fd2fa24148633259b05d0556`, `b2d8e3a5dd97974808f53afcd1b28f09825985b85a5828cd905b032d09728ed8`, `c61871d091dc06d6d08cfd614968bb461162145213682c0afcb09806524d1e90`, `c91f494f816dd24dae240bf2f6375d0f224f380fb78c685a9d05959a8d7304f0`.

Boundary assertions from the canonical plan matched: unit 14 coverage `2025-07-24T11:00:00Z`–`2025-07-31T09:00:00Z`, request `2025-07-24T10:00:00Z`–`2025-07-31T09:59:59Z`; unit 33 coverage `2025-12-03T16:00:00Z`–`2025-12-10T14:00:00Z`, request `2025-12-03T15:00:00Z`–`2025-12-10T14:59:59Z`.

## BATCH_IDENTITY_BASELINE

The requested twenty units represented 3,340 desired hourly identities. Before execution, zero were present. The daily identity digest was `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` (the empty daily set over these windows).

## RESOURCE_BASELINE

Before batch: CPU 47.2%; available RAM 4,848,664,576 bytes; committed memory 21,941,325,824 bytes; commit limit 33,272,041,472 bytes; free commit 11,330,715,648 bytes.

## LIVE_EXECUTION

The committed runner was invoked with the double opt-in, a 20-unit / 20-call budget, and exact pre-state assertions. It made 15 requests and stopped at unit 28. Units 14–27 passed audit and coverage checks. Unit 28's ingestion transaction and successful audit committed. Its validator compared UTC planned timestamps with database-returned `America/Los_Angeles` datetimes. During the DST fall-back hour, Python does not consider an ambiguous local-fold datetime equal to the same UTC instant, so the runtime validator reported a false coverage gap and emitted `BACKFILL_BATCH_STATUS=SOURCE_COVERAGE_GAP`. Units 29–33 were not attempted. No retry or extra Nansen request was made.

`LIVE_API_CALLS_TASK029=15`; ingestion returned success for all 15 attempted units. The runner's independent post-ingestion validator passed units 14–27 and stopped on unit 28's false-positive result. This interrupted invocation is classified `TASK_029_STATUS=LIVE_BATCH_FAILURE`; it is not a completed 20-unit batch.

| Unit | Run ID | Calls | Received / normalized | Desired / observed / missing | Request-start bucket | Audit | Progress after unit | Resource snapshot (CPU; available RAM; commit used; free commit) |
|---:|---|---:|---:|---:|---|---|---|---|
| 14 | `59666b22-9176-473b-b995-d9a116b2f5f7` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 14 / 60 / 0 | 19.4%; 4,875,628,544; 21,953,552,384; 11,318,489,088 |
| 15 | `c03066df-cf99-491f-a7a5-194b0a0332ef` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 15 / 59 / 0 | 19.0%; 4,889,325,568; 21,952,446,464; 11,319,595,008 |
| 16 | `6da844ae-d4b8-479b-960e-080f1941ef15` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 16 / 58 / 0 | 22.2%; 4,891,820,032; 21,954,191,360; 11,317,850,112 |
| 17 | `baa54ee5-f51d-4129-9764-86e380426841` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 17 / 57 / 0 | 31.0%; 4,922,859,520; 21,914,583,040; 11,357,458,432 |
| 18 | `9b884dd6-9cb3-4b91-9955-a4059e49e7c3` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 18 / 56 / 0 | 21.4%; 4,820,602,880; 22,211,411,968; 11,060,629,504 |
| 19 | `52734e61-caa4-4672-9bd9-439737338729` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 19 / 55 / 0 | 31.0%; 4,603,789,312; 22,525,911,040; 10,746,130,432 |
| 20 | `217a451c-2840-485b-a553-9ed1e87311d9` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 20 / 54 / 0 | 44.4%; 4,566,978,560; 22,570,770,432; 10,701,271,040 |
| 21 | `54d932a9-9fad-48ba-8960-4f5e277b001d` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 21 / 53 / 0 | 50.0%; 4,826,812,416; 22,219,161,600; 11,052,879,872 |
| 22 | `5011ce2d-8c48-4a7e-aa88-4419186dc492` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 22 / 52 / 0 | 50.0%; 4,590,780,416; 22,560,358,400; 10,711,683,072 |
| 23 | `0dbfe04e-7533-42e4-9913-bb8c23f3c937` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 23 / 51 / 0 | 71.4%; 4,582,809,600; 22,572,724,224; 10,699,317,248 |
| 24 | `1fc910dc-f84c-4d63-abd9-574a910c1faf` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 24 / 50 / 0 | 13.9%; 4,901,265,408; 21,974,003,712; 11,298,037,760 |
| 25 | `99c500c6-e280-4370-b072-a870effe7c56` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 25 / 49 / 0 | 2.4%; 4,907,749,376; 21,972,975,616; 11,299,065,856 |
| 26 | `1c681963-476f-44c6-94f0-f29a6be625c0` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 26 / 48 / 0 | 2.4%; 4,925,603,840; 21,953,462,272; 11,318,579,200 |
| 27 | `e463ce18-71ef-4f70-8ac9-7833d3754696` | 1 | 167 / 167 | 167 / 167 / 0 | YES | PASS | 27 / 47 / 0 | 8.3%; 4,924,772,352; 21,952,843,776; 11,319,197,696 |
| 28 | `3fb65044-0cc8-4aeb-8436-018720c66afb` | 1 | 167 / 167 | runtime check: 167 / 164 / 3 | YES | PASS | 28 / 46 / 0 | Stop after structural check |
| 29 | `44d29412ee215ec88fa6e92fcbab3f14244fbf0a16df52f0340f21e071d911b3` | 0 | Not attempted | Not attempted | N/A | Not run | N/A | Not attempted after stop |
| 30 | `11e27c2c184d6fb1c5e60b4019ebe005a11d5a21fd2fa24148633259b05d0556` | 0 | Not attempted | Not attempted | N/A | Not run | N/A | Not attempted after stop |
| 31 | `b2d8e3a5dd97974808f53afcd1b28f09825985b85a5828cd905b032d09728ed8` | 0 | Not attempted | Not attempted | N/A | Not run | N/A | Not attempted after stop |
| 32 | `c61871d091dc06d6d08cfd614968bb461162145213682c0afcb09806524d1e90` | 0 | Not attempted | Not attempted | N/A | Not run | N/A | Not attempted after stop |
| 33 | `c91f494f816dd24dae240bf2f6375d0f224f380fb78c685a9d05959a8d7304f0` | 0 | Not attempted | Not attempted | N/A | Not run | N/A | Not attempted after stop |

## UNIT_28_VALIDATOR_FALSE_POSITIVE

Unit 28 normalized 167 records and had a successful exact-window warning-audited run. A first post-stop structural query returned local timestamps around the daylight-saving transition. Converting both persisted and planned bucket endpoints to UTC before identity comparison showed 167/167 desired identities, zero missing, zero unexpected, and zero duplicates. The runner's local-time set comparison caused the false positive; this was not a Nansen source coverage gap. The audit progress inspector classifies unit 28 complete.

`POSTSTOP_UTC_NORMALIZED_UNIT28_COVERAGE=167/167`; `POSTSTOP_UTC_NORMALIZED_BATCH_COVERAGE_UNITS14_28=2505/2505`; missing and duplicate counts are both zero.

## BATCH_WARNING_AUDIT

All 15 new runs have valid successful exact-window audits and non-null sanitized warning summaries. Each contained one warning in the approved `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` category; zero UNKNOWN categories were observed. Raw warning content was not printed or stored.

## BATCH_COVERAGE

Units 14–27 have 14 × 167 = 2,338 desired identities present. Across the 15 attempted units 14–28, UTC-normalized read-only validation confirms 2,505 of 2,505 desired identities, zero missing, and zero duplicates. The original authorized twenty-unit batch target was 3,340; units 29–33 (835 desired identities) were not attempted because the runner stopped on its false-positive validation result.

## GLOBAL_ROW_ACCOUNTING

Flow rows increased from 2,223 to 4,728 (+2,505); canonical target counts are 4,699 hourly and 29 daily. The global natural identity duplicate count is zero. UTC-normalized identities account for all 2,505 persisted rows across units 14–28.

## NATURAL_IDENTITY_INTEGRITY

Global natural identity duplicates: zero. Daily and hourly duration classes remain distinct.

## DAILY_IDENTITY_PRESERVATION

The daily identity digest remained `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` before and after; daily rows across the attempted coverage remain zero. Digest unchanged.

## AUDIT_ROW_ACCOUNTING

Ingestion audit rows increased from 18 to 33 (+15). The 15 new runs are successful request audits, including unit 28, whose subsequent coverage check failed. No audit rows were removed.

## CHECKPOINT_NON_REGRESSION

The high-water checkpoint remains `2026-09-20T23:59:59Z` / `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## RECENT_DATA_INTEGRITY

September 20 remains 23 hourly rows / 23 identities.

## RESTART_RESUME_PROOF

Fresh read-only progress inspection reports 28 complete / 46 pending / 0 ambiguous; the next audit-pending unit is 29. UTC-normalized structure confirms unit 28 coverage. The invocation nevertheless stopped before units 29–33 because its first validation result failed; do not resume automatically. Further execution requires a separate authorization after the correction is reviewed.

## RESOURCE_OBSERVATION

Before batch, available RAM was 4,848,664,576 bytes and free commit was 11,330,715,648 bytes. After unit 27, CPU was 8.3%, available RAM 4,924,772,352 bytes, committed memory 21,952,843,776 bytes, commit limit 33,272,041,472 bytes, and free commit 11,319,197,696 bytes. A post-stop sample recorded CPU 0.0%, available RAM 4,916,535,296 bytes, committed memory 21,944,606,720 bytes, commit limit 33,272,041,472 bytes, and free commit 11,327,434,752 bytes.

## DEFAULT_TESTS

After the live attempt and before the UTC correction, `pytest -q` passed: 218 passed, 6 skipped. After the correction, `pytest -q` passed: 219 passed, 6 skipped. Default API calls: zero; default PostgreSQL connections: zero. No extra Nansen verification request was made.

## PRODUCTION_SAFETY

Only staging was used. Production connections, DDL, DML, and changes: zero. No service or scheduler was added.

## SECURITY_CHECK

Raw warning text, raw response data, analytical values, credentials, wallet addresses, transaction hashes, and individual flow keys were not printed or included. Secret scan passed; `.env` is not tracked.

## CYRILLIC_CHECK

Pass.

## FILES_CHANGED

Source-first commit: generic runner change in `src/otg_nansen/backfill_execute.py`, `tests/test_backfill_execute.py`. Post-stop corrective source commit: UTC-canonical timestamp identity comparisons and DST-fold regression test. Evidence commit: this report and the five Task 029 status addenda in the docs.

## RISKS

The initial validator compared timezone-aware datetimes without canonicalizing PostgreSQL's session-local timezone and therefore falsely rejected repeated-hour DST identities. UTC-normalized post-stop validation confirms unit 28's desired coverage. The invocation intentionally remained stopped after the first validator failure; units 29–33 remain unattempted.

## NEXT_RECOMMENDED_TASK

Review the UTC-canonicalization correction and separately authorize a new bounded invocation beginning at unit 29. Do not start that invocation or Task 030 automatically.
