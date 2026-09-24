# Task 032: Complete canonical hourly backfill

## OBJECTIVE

Execute canonical unit 74 once and perform read-only end-to-end validation of the 12,336-hour Avalanche `smart_money` target.

## STARTING_STATE

Starting `HEAD` and `origin/main` were `e30584c483fa55e891a334a29575ce6d4018d87f`, synchronized with a clean worktree. Baseline tests passed: 219 passed, 6 skipped. No source change was made.

## TASK031_ACCEPTED_STATE

Staging began at 73 complete / 1 pending / 0 ambiguous. Unit 74 was the only pending unit. Flow totals were 12,243 (12,214 hourly and 29 daily); there were 80 ingestion runs. The high-water checkpoint timestamp was 2026-09-20T23:59:59Z. The previously retained September 20 hourly set had 23 identities.

## BASELINE_TESTS

`pytest -q`: 219 passed, 6 skipped. Default tests made zero live API calls and zero PostgreSQL connections.

## KEY_CONFIGURATION_CHECK

The normal dotenv path reported `NANSEN_API_KEY_PRESENT=YES` and `NANSEN_API_KEY_NONEMPTY=YES`; `.env` is untracked. No key material was printed or stored.

## PRE_LIVE_STAGING_STATE

Read-only connection identity was `server_otg_staging` / `gunz_user` / transaction read-only `on`. Progress was 73/1/0; first pending unit 74. Totals matched the accepted state, global natural-identity duplicates were zero, and September 20 was 23/23. The checkpoint referenced run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d` before the request.

## UNIT74_AUTHORIZATION

The dynamic runner selected unit 74, ID `a8500d314f529d3d4efc8399d833ba4ffecf3d06252a3415fdcb958cf7eb7af3`.

Coverage: 2026-09-14T23:00:00Z through 2026-09-20T23:00:00Z. Request: 2026-09-14T22:00:00Z through 2026-09-20T23:59:59Z. The request duration is 6 days, 23:59:59. The unit contains 145 desired bucket starts.

## UNIT74_PRE_LIVE_COVERAGE

Of 145 desired identities, 23 were present and 122 were missing. The unit-window daily identity digest before was the empty-set digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`. Full-range hourly identity digests before execution: expected `f521670317a3291f0b24a51578fdb0d6c16bafdfe5d6b62936d80d4a20576e09`; observed `e6a47667a4ece17041760ae39070a5749a6ab55c7a784002f2ceee35bd8bfd13`.

## RESOURCE_BASELINE

Before unit 74: CPU 38.9%; available RAM 4,891,566,080 bytes; committed memory 21,357,813,760 bytes; commit limit 33,272,041,472 bytes; free commit 11,914,227,712 bytes.

## LIVE_EXECUTION

The committed generic runner was invoked with both live gates and a one-unit/one-call ceiling. It used the existing ingestion orchestrator, a fresh client with one attempt, no retries, and the exact planner request window. Exactly one Nansen attempt occurred. Unit 74 received and normalized 145 records.

## UNIT74_AUDIT

Run `dd2d9c89-3800-44b2-a8a9-9548dc87db55`: success, Avalanche Flows `smart_money`, exact request window, one page, one API call, 145 received, 145 normalized, and non-null sanitized warning audit. The only warning category was `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`.

## UNIT74_COVERAGE

UTC-normalized validation found 145 desired / 145 observed / 0 missing / 0 duplicate hourly identities. Of these, 122 were new and 23 were reused.

## UNIT74_ROW_ACCOUNTING

Flow rows increased from 12,243 to 12,365, exactly the 122 new identities. Final canonical counts are 12,336 hourly and 29 daily rows; ingestion runs total 81. Global flow accounting passed and global natural-identity duplicates remain zero.

## FINAL_PLAN_PROGRESS

Fresh read-only inspection found 74 complete / 0 pending / 0 ambiguous. There is no next pending unit; `FULL_PLAN_COMPLETE=PASS`.

## FULL_EXPECTED_IDENTITY_SET

The planner independently generated 12,336 hourly `(date, bucket_end)` identities from 2025-04-25T00:00:00Z through 2026-09-20T23:00:00Z, inclusive.

## FULL_OBSERVED_IDENTITY_SET

The read-only staging query returned 12,336 distinct canonical hourly identities after UTC normalization.

## FULL_MISSING_UNEXPECTED_DUPLICATE_CHECK

Missing identities: 0. Unexpected identities: 0. Duplicate canonical hourly identities: 0.

## FULL_RANGE_CONTIGUITY

Observed minimum: 2025-04-25T00:00:00Z. Observed maximum: 2026-09-20T23:00:00Z. Both endpoints match the target. Non-one-hour gaps: 0. Full hourly contiguity passed.

## FULL_IDENTITY_DIGEST_PROOF

Expected digest: `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`. Observed digest: `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`. Both use sorted UTC ISO timestamp pairs. Digest match passed.

## BUCKET_DURATION_INTEGRITY

Invalid duration among canonical hourly records: 0.

## COMPLETION_FLAG_INTEGRITY

Incomplete canonical hourly records: 0.

## GLOBAL_IDENTITY_INTEGRITY

Global natural-identity duplicates: 0. Canonical hourly natural-identity duplicates: 0.

## DAILY_IDENTITY_PRESERVATION

Canonical daily count remains 29. The unit 74 date range had no daily identities before or after; its empty-set digest is unchanged. The unit 74 request window is disjoint from the retained early-history daily layer. A full-target pre-request daily digest was not captured, so the full 29-row layer is supported by unchanged count and non-overlapping write scope rather than a before/after full-set digest comparison. No daily row was intentionally changed.

## CANONICAL_AUDIT_COMPLETION

All 74 canonical units have at least one successful exact-window audit with one API call and non-null warning audit. Units without a successful audit: 0. Successful canonical units with unknown warning categories: 0.

## FAILED_AUDIT_HISTORY

Three failed audit rows remain present, including the historical unit 46 failures. No audit history was deleted or rewritten.

## CHECKPOINT_NON_REGRESSION

The checkpoint timestamp remains 2026-09-20T23:59:59Z. At the equal timestamp, the checkpoint owner changed from the prior high-water run to unit 74 run `dd2d9c89-3800-44b2-a8a9-9548dc87db55`. This is allowed by the task's equal-timestamp policy. The runner printed `BACKFILL_BATCH_STATUS=LIVE_BATCH_FAILURE` after successful persistence because its final check compares the entire checkpoint tuple for equality; independent read-only validation confirms the timestamp did not regress and the run ID is the successful final unit. No source patch was made.

## RECENT_DATA_INTEGRITY

September 20 now has 24 hourly rows / 24 identities. Its prior 23 identities (starts before 23:00 UTC) remain present; the final canonical target required and added the 2026-09-20T23:00:00Z bucket. Thus the literal expected row count of 23 did not remain unchanged, while the prior set was preserved without duplication and the canonical 12,336-hour target is complete.

## FULL_DATA_RANGE_SUMMARY

Canonical target start: 2025-04-25T00:00:00Z. End: 2026-09-20T23:00:00Z. Desired hours: 12,336. Canonical hourly rows: 12,336. Canonical daily rows: 29. Total Nansen flow rows: 12,365.

## RESOURCE_OBSERVATION

After unit 74: CPU 92.7%; available RAM 4,803,956,736 bytes; committed memory 21,616,955,392 bytes; commit limit 33,272,041,472 bytes; free commit 11,655,086,080 bytes. Before read-only full validation: CPU 57.1%; RAM 3,339,325,440 bytes; committed 22,987,173,888 bytes; limit 33,272,041,472 bytes; free commit 10,284,867,584 bytes. After validation: CPU 80.6%; RAM 4,491,198,464 bytes; committed 21,817,970,688 bytes; limit 33,272,041,472 bytes; free commit 11,454,070,784 bytes. Memory headroom remained stable.

## DEFAULT_TESTS

Post-live `pytest -q`: 219 passed, 6 skipped. Default tests made zero live API calls and zero PostgreSQL connections. No extra Nansen request was made.

## PRODUCTION_SAFETY

Production connections, DDL, and DML were zero. Production was unchanged. No deployment, service, or scheduler was started.

## SECURITY_CHECK

No key material, `.env` contents, raw warning, raw response, wallet address, transaction hash, analytical metric, or individual flow identity was recorded. `.env` is untracked.

## CYRILLIC_CHECK

English-only scan passed.

## FILES_CHANGED

- `DEV/reports/032_complete_canonical_hourly_backfill/report.md`
- `docs/architecture.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/analytics_methodology.md`
- `docs/nansen_api.md`

## RISKS

The reusable runner's strict checkpoint tuple equality reports failure when the equal-timestamp checkpoint owner changes, even though the timestamp remains unchanged and the task permits ownership replacement. The exact September 20 row count increased to 24 because the final desired bucket is on that date; the original 23 identities remain present. The full-target daily set's pre-run digest was not captured, although its count is unchanged and the final request range does not overlap it.

## NEXT_RECOMMENDED_TASK

The canonical staging backfill is complete. Review the checkpoint postcondition and the September 20 count convention before any later analytical task. Do not infer market relationships from coverage completion alone.

## TASK032R_ADDENDUM

Unit 74 persistence succeeded and canonical hourly coverage became complete. The original generic runner then emitted `BACKFILL_BATCH_STATUS=LIVE_BATCH_FAILURE` because terminal postconditions required exact checkpoint tuple equality, exact recent-day count equality, and a synthetic next index after the final unit. The API, audit, persistence, and canonical coverage checks had succeeded. Task 032R corrected these runner validation semantics and their offline tests without another Nansen call or staging write. Read-only physical verification again found the full 12,336/12,336 canonical identity set. The checkpoint timestamp remains unchanged while its valid owner is unit 74's successful run. September 20 has 24 rows: the documented prior count was 23 and the final canonical 23:00 bucket is the one authorized addition. The original report chronology and runner failure output are preserved.
