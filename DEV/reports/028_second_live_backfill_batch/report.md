# Task 028: Second Live Historical Backfill Batch

`TASK_028_STATUS=SUCCESS`

## OBJECTIVE

Generalize the Task 027 staging-only runner to resume from persisted exact-window progress and execute exactly the next ten pending canonical Avalanche `smart_money` flow units.

## STARTING_STATE

Starting remote main was `50f24268f52e681fe1e93f9fd2a19a12c4d846c5`, branch `main`, clean. Baseline default tests passed: 206 passed, 6 skipped; baseline live API calls and PostgreSQL connections were zero.

## TASK027_ACCEPTED_STATE

Canonical plan: 74 units. Staging before this task: 553 flows, 524 canonical-target hourly rows, 29 daily rows, eight ingestion audits, and progress 3 complete / 71 pending / 0 ambiguous. The first pending unit was 4. The checkpoint was `2026-09-20T23:59:59Z` with run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. The retained September day had 23 hourly rows and 23 natural identities.

## RUNNER_GENERALIZATION

The runner now derives pending selection, progress expectations, resource-stop decisions, and restart-next-unit from the canonical plan and persisted progress. The canonical target remains fixed in `build_canonical_plan()`; the live CLI cannot select arbitrary target dates.

## REMOVED_TASK027_ASSUMPTIONS

Removed runtime checks for Task 027's 219/190/5 pre-state, 0 complete units, units 1–3, 3/71 final progress, next unit 4, and fixed batch size 3. Task 028 state is supplied through explicit expected-progress and staging-snapshot CLI assertions.

## LIVE_AUTHORIZATION_GUARDS

Execution requires `--execute`, `NANSEN_RUN_LIVE_BACKFILL=1`, `--max-units`, `--max-live-calls`, `--expected-complete-before`, and `--expected-first-pending-index`. For this run the values were 10, 10, 3, and 4. The invocation also asserted expected staging counts, recent retained count, and checkpoint identity. The explicit process environment opt-in is captured before dotenv loading, so `.env` cannot satisfy the live gate.

## ABSOLUTE_BATCH_CAP

Code-level ceilings are 20 units and 20 live API attempts per invocation. `max_live_calls` must be at least `max_units`; per-unit allowance is one call. Requests above either absolute ceiling are rejected before a writable repository is opened.

## GENERALIZED_PROGRESS_MATH

After K successful units, expected state is computed as `complete_before + K`, `pending_before - K`, and zero ambiguous. Persisted progress was re-read after every success. The batch advanced 3/71/0 through 4/70/0, 5/69/0, 6/68/0, 7/67/0, 8/66/0, 9/65/0, 10/64/0, 11/63/0, 12/62/0, and 13/61/0.

## RESOURCE_STOP_GENERALIZATION

The runner records a resource sample after each unit and checks whether another selected unit remains. It has no absolute-unit-number resource condition. If pressure is detected while selected units remain, it raises before starting the next request.

## OFFLINE_TESTS

Baseline `pytest -q`: 206 passed, 6 skipped. After generalization and before live work: 218 passed, 6 skipped. Tests cover both opt-ins, the 20-unit / 20-call caps, expected-progress refusals, Task 028 bounds, resumed pending selection, progress deltas, invocation-relative resource stopping, generic next-pending selection, one-call enforcement, ambiguity, COMPLETE skipping, and stop-on-first-failure. No live API calls or default PostgreSQL connections were made by tests.

## SOURCE_FIRST_COMMIT

The generalized runner and tests were pushed before live execution as `2bf2d7dfff72f30df1d56dfd952d509a7d0c46b8`. A read-only checkpoint representation mismatch (local timezone versus UTC wire form) refused a gated attempt before opening a writer or making a request. The correction was tested and pushed before live work. `PRE_LIVE_SOURCE_SHA=62bd0bfbf534fb401fcad44f54a8dd37dac24197`; remote readback matched.

## PRE_LIVE_STAGING_STATE

Read-only preflight verified `server_otg_staging`, `gunz_user`, and read-only mode. Total flows 553; canonical target hourly 524; daily 29; ingestion runs 8; September 20 hourly rows and identities 23/23. Checkpoint matched `2026-09-20T23:59:59Z` / `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. No state drift was found.

## PRE_LIVE_PLAN_PROGRESS

`PLAN_COMPLETE_BEFORE=3`; `PLAN_PENDING_BEFORE=71`; `PLAN_AMBIGUOUS_BEFORE=0`; `FIRST_PENDING_INDEX_BEFORE=4`.

## AUTHORIZED_UNIT_SELECTION

Dynamic audit progress selected canonical units 4 through 13 in contiguous ascending order. Unit IDs: `0595d69613819e4da189d97fdb2813b395de565aaae289e9df489165580df683`, `87eb9c95f7fa0c19ea3ba21a57bb9d6970ae8b032a079ba0a6d336192c726108`, `1db65c43d61eaa7d525070a5bb064bcddb99b554476d41d4a702d565d8054329`, `44f6b8ba8e53f7071eb8b0f33ea3210a09182c60d8322d9cfbe4b823de125ddc`, `400a517406210f33b81391aebf46397ef18f129fd9532540d829580682738982`, `8a8bdef4b32ab23b4707a03d17408a790246dc23d3d17e7345a683371dbaf34c`, `8fd05610a453cce52d313a4bcb8f34c4213ab9fda8dc7adfa0dca2ee2b7e520e`, `f0f208c9659ede370262cf67f1faa65ab3f10592c865b02910d3f612ea776017`, `e85d91129fbb907544de312e7e33a174ddcaa1e25da08a37b8ef0c198b218228`, and `59dcedcc5d8f65327a36a8b729729ac9a36569eeb637e9c57a803d8529322f67`. Coverage/request bounds are recorded per unit below and match the Task 028 assertions.

## BATCH_IDENTITY_BASELINE

`BATCH_DESIRED_BUCKETS=1670`; `BATCH_DESIRED_IDENTITIES_PRESENT_BEFORE=0`. After the batch all 1,670 were present and none were missing.

## DAILY_IDENTITY_BASELINE

Sorted daily natural-identity digest before execution: `8b27db34cbc6ae330f8a4467ab09ffdf563cd6c6a1249f4e3d9f1ad5098d172a`. Individual identities were not printed.

## RESOURCE_BASELINE

CPU 33.3%; available RAM 5,240,541,184 bytes; Windows committed memory 21,572,886,528 bytes; commit limit 33,272,041,472 bytes; free commit 11,699,154,944 bytes.

## LIVE_BATCH_EXECUTION

The committed runner used both explicit live gates and the 10-unit / 10-call budget. Each unit created a fresh `NansenClient` with `max_calls=1`, `max_retries=0`, `page_size=1000`, `max_pages=1`, and `timeout_seconds=120`, then called the existing `NansenIngestionOrchestrator.ingest_flows()` with request bounds. Exactly ten requests were attempted. No eleventh request occurred.

## UNIT_4_RESULT

Run `e2aabf9b-b968-4bc5-ae2c-b7f98db787fe`; coverage `2025-05-15T21:00:00Z`–`2025-05-22T19:00:00Z`; request `2025-05-15T20:00:00Z`–`2025-05-22T19:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_4_AUDIT

Exact-window status success; one page; one API call; `source_warnings` non-null with one sanitized `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` warning. Audit valid; no UNKNOWN.

## UNIT_4_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Seven daily rows coexist in the coverage interval.

## UNIT_4_PROGRESS

4 complete / 70 pending / 0 ambiguous.

## UNIT_4_RESOURCE_STATE

CPU 19.4%; available RAM 5,222,494,208 bytes; committed 21,578,444,800 bytes; commit limit 33,272,041,472 bytes; free commit 11,693,596,672 bytes.

## UNIT_5_RESULT

Run `d6db2d5f-323e-4ee9-854f-c6ce2b26f8ca`; coverage `2025-05-22T20:00:00Z`–`2025-05-29T18:00:00Z`; request `2025-05-22T19:00:00Z`–`2025-05-29T18:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_5_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_5_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Two daily rows coexist in the coverage interval.

## UNIT_5_PROGRESS

5 complete / 69 pending / 0 ambiguous.

## UNIT_5_RESOURCE_STATE

CPU 31.0%; available RAM 5,194,715,136 bytes; committed 21,579,046,912 bytes; commit limit 33,272,041,472 bytes; free commit 11,692,994,560 bytes.

## UNIT_6_RESULT

Run `6d1bb6d0-a512-42a9-8749-eb3294eb6cba`; coverage `2025-05-29T19:00:00Z`–`2025-06-05T17:00:00Z`; request `2025-05-29T18:00:00Z`–`2025-06-05T17:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_6_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_6_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_6_PROGRESS

6 complete / 68 pending / 0 ambiguous.

## UNIT_6_RESOURCE_STATE

CPU 40.5%; available RAM 5,187,481,600 bytes; committed 21,587,775,488 bytes; commit limit 33,272,041,472 bytes; free commit 11,684,265,984 bytes.

## UNIT_7_RESULT

Run `d027ca9f-900f-413b-8c2a-ae55b67ca6f8`; coverage `2025-06-05T18:00:00Z`–`2025-06-12T16:00:00Z`; request `2025-06-05T17:00:00Z`–`2025-06-12T16:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_7_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_7_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_7_PROGRESS

7 complete / 67 pending / 0 ambiguous.

## UNIT_7_RESOURCE_STATE

CPU 26.2%; available RAM 5,190,713,344 bytes; committed 21,580,804,096 bytes; commit limit 33,272,041,472 bytes; free commit 11,691,237,376 bytes.

## UNIT_8_RESULT

Run `184fabb7-c722-4398-8939-4b7433dae229`; coverage `2025-06-12T17:00:00Z`–`2025-06-19T15:00:00Z`; request `2025-06-12T16:00:00Z`–`2025-06-19T15:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_8_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_8_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_8_PROGRESS

8 complete / 66 pending / 0 ambiguous.

## UNIT_8_RESOURCE_STATE

CPU 47.2%; available RAM 5,196,349,440 bytes; committed 21,580,959,744 bytes; commit limit 33,272,041,472 bytes; free commit 11,690,817,728 bytes.

## UNIT_9_RESULT

Run `952713cd-33cc-4261-9671-e9a246c5259d`; coverage `2025-06-19T16:00:00Z`–`2025-06-26T14:00:00Z`; request `2025-06-19T15:00:00Z`–`2025-06-26T14:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_9_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_9_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_9_PROGRESS

9 complete / 65 pending / 0 ambiguous.

## UNIT_9_RESOURCE_STATE

CPU 21.4%; available RAM 5,188,440,064 bytes; committed 21,576,237,056 bytes; commit limit 33,272,041,472 bytes; free commit 11,695,804,416 bytes.

## UNIT_10_RESULT

Run `cce36242-25df-42a0-8225-bf49507d3120`; coverage `2025-06-26T15:00:00Z`–`2025-07-03T13:00:00Z`; request `2025-06-26T14:00:00Z`–`2025-07-03T13:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_10_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_10_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_10_PROGRESS

10 complete / 64 pending / 0 ambiguous.

## UNIT_10_RESOURCE_STATE

CPU 19.0%; available RAM 5,180,764,160 bytes; committed 21,589,315,584 bytes; commit limit 33,272,041,472 bytes; free commit 11,682,725,888 bytes.

## UNIT_11_RESULT

Run `30401cea-4f4f-4fa5-a677-86edd59fb5f3`; coverage `2025-07-03T14:00:00Z`–`2025-07-10T12:00:00Z`; request `2025-07-03T13:00:00Z`–`2025-07-10T12:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_11_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_11_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_11_PROGRESS

11 complete / 63 pending / 0 ambiguous.

## UNIT_11_RESOURCE_STATE

CPU 23.8%; available RAM 5,184,126,976 bytes; committed 21,575,364,608 bytes; commit limit 33,272,041,472 bytes; free commit 11,696,676,864 bytes.

## UNIT_12_RESULT

Run `ec425988-c3d3-4262-9050-8f2326ef117d`; coverage `2025-07-10T13:00:00Z`–`2025-07-17T11:00:00Z`; request `2025-07-10T12:00:00Z`–`2025-07-17T11:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_12_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_12_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_12_PROGRESS

12 complete / 62 pending / 0 ambiguous.

## UNIT_12_RESOURCE_STATE

CPU 27.0%; available RAM 5,181,079,552 bytes; committed 21,576,380,416 bytes; commit limit 33,272,041,472 bytes; free commit 11,695,661,056 bytes.

## UNIT_13_RESULT

Run `6221baf2-02c4-4dab-8d96-e5c039c75450`; coverage `2025-07-17T12:00:00Z`–`2025-07-24T10:00:00Z`; request `2025-07-17T11:00:00Z`–`2025-07-24T10:59:59Z`. One call; 167 received / 167 normalized; request-start bucket present.

## UNIT_13_AUDIT

Exact-window status success; one page; one API call; non-null sanitized warning summary with one approved category. Audit valid; no UNKNOWN.

## UNIT_13_COVERAGE

167 desired / 167 observed / zero missing / zero duplicate hourly identities. Zero daily rows in the coverage interval.

## UNIT_13_PROGRESS

13 complete / 61 pending / 0 ambiguous.

## UNIT_13_RESOURCE_STATE

CPU 21.4%; available RAM 5,171,863,552 bytes; committed 21,579,907,072 bytes; commit limit 33,272,041,472 bytes; free commit 11,692,134,400 bytes.

## BATCH_WARNING_AUDIT

Ten new runs have non-null sanitized warning summaries; zero NULL warning audits; zero UNKNOWN categories. Each warning summary used only the approved `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE` category. Raw warning text and responses were not printed or stored.

## BATCH_COVERAGE_ACCOUNTING

All 1,670 desired natural hourly identities were present afterward; missing count zero. Present before: zero; newly added: 1,670; reused: zero.

## GLOBAL_ROW_ACCOUNTING

Global flow rows increased from 553 to 2,223, exactly 1,670 new natural identities. Canonical target rows are 2,194 hourly and 29 daily. `GLOBAL_FLOW_ROW_ACCOUNTING=PASS`.

## NATURAL_IDENTITY_INTEGRITY

Global natural-identity duplicates: zero. Hourly and daily resolutions coexist without collision.

## DAILY_IDENTITY_PRESERVATION

Digest before and after: `8b27db34cbc6ae330f8a4467ab09ffdf563cd6c6a1249f4e3d9f1ad5098d172a`. `DAILY_IDENTITY_DIGEST_UNCHANGED=PASS`.

## AUDIT_ROW_ACCOUNTING

Ingestion runs increased from 8 to 18. Ten new successful exact-window rows were added; no prior audit rows were deleted.

## CHECKPOINT_NON_REGRESSION

Checkpoint after execution remains `2026-09-20T23:59:59Z` / `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. `CHECKPOINT_NON_REGRESSION=PASS`.

## RECENT_DATA_INTEGRITY

September 20 remains 23 hourly rows / 23 natural identities. `RECENT_RETAINED_STATE_UNCHANGED=PASS`.

## RESTART_RESUME_PROOF

Fresh canonical replan and read-only progress inspection: 13 complete / 61 pending / 0 ambiguous. First pending unit is 14. `RESTART_RESUME_PROOF=PASS`.

## RESOURCE_OBSERVATION

After batch: CPU 31.0%; available RAM 5,179,310,080 bytes; committed memory 21,574,553,600 bytes; commit limit 33,272,041,472 bytes; free commit 11,697,487,872 bytes. Unit snapshots are recorded above. Headroom remained stable; no retry loop or abnormal connection growth occurred. `RESOURCE_STABILITY=PASS`.

## DEFAULT_TESTS

After the batch, `pytest -q`: 218 passed, 6 skipped. Default live API calls: zero; default PostgreSQL connections: zero. No extra live validation request was made.

## PRODUCTION_SAFETY

All connections were pinned to staging. `PRODUCTION_CONNECTIONS=0`; `PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`. No service or scheduler was added.

## SECURITY_CHECK

No API key, database password, GitHub credential, raw warning, raw response, wallet address, transaction hash, metric value, or individual flow key was printed or committed. `SECRET_SCAN=PASS`; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

Source commits changed `src/otg_nansen/backfill_execute.py` and `tests/test_backfill_execute.py`. The evidence commit changes this report and `docs/architecture.md`, `docs/database.md`, `docs/operations.md`, `docs/analytics_methodology.md`, and `docs/nansen_api.md`.

## RISKS

The request-boundary pre-roll is supported by the bounded Task 025 observation and the live units completed so far. Warning acceptance remains exact-fingerprint and structural-guard based. This task validates only units 4–13; it does not establish full historical coverage.

## NEXT_RECOMMENDED_TASK

Review Task 028 evidence and separately authorize a bounded batch beginning at unit 14. Do not execute unit 14 or start Task 029 automatically.
