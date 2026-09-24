# Task 032R: Fix terminal backfill runner postconditions

## OBJECTIVE

Fix and test terminal validation for the generic backfill runner, then ratify the already-complete staging data using read-only checks only.

## STARTING_STATE

Starting `HEAD` and `origin/main` were `93e3fb7715900e1914861ef5b086263f5b73a670`, synchronized and clean. Baseline `pytest -q` passed with 219 passed and 6 skipped. No Nansen call or staging write was made in this task.

## TASK032_DATA_COMPLETION

Unit 74 had already persisted successfully as run `dd2d9c89-3800-44b2-a8a9-9548dc87db55`. The prior task independently proved 12,336/12,336 expected hourly identities. Task 032R did not replay that unit.

## ORIGINAL_RUNNER_FALSE_FAILURE

The original unit 74 execution persisted successfully but the runner emitted `BACKFILL_BATCH_STATUS=LIVE_BATCH_FAILURE` during terminal validation. Its strict postconditions rejected equal-timestamp checkpoint owner replacement, a legitimate selected-unit addition to the September 20 set, and a terminal plan with no next pending unit.

## ROOT_CAUSE

Checkpoint validation compared the entire `(timestamp, run_id)` tuple for equality. Recent-data validation required the exact row count to remain unchanged. Final resume validation expected `last_unit.index + 1`, including after the final canonical unit.

## CHECKPOINT_SEMANTICS_FIX

The runner now rejects a timestamp regression. A timestamp advance or changed owner requires a successful matching stream audit whose `window_end` equals the after timestamp. An unchanged timestamp and owner is accepted. An equal-timestamp successful owner replacement is accepted after validating the owner stream and window end.

## RECENT_IDENTITY_SEMANTICS_FIX

The runner captures recent hourly identities before execution. It requires every prior identity to remain, permits newly appearing identities only when selected units planned them, and rejects duplicate or unauthorized identities. Output names report preservation, authorized additions, and duplicates without claiming that the enlarged set is unchanged.

## TERMINAL_RESUME_FIX

The expected next pending index is the next canonical index for nonterminal batches and `None` when the selected unit is the final plan unit. The terminal plan can therefore complete with no pending unit.

## OFFLINE_TESTS

Added pure tests for unchanged/advanced/equal-timestamp checkpoint behavior, timestamp regression, failed/wrong-stream/wrong-window owners, unchanged/authorized/removed/unexpected/duplicate recent identities, and terminal/nonterminal resume expectations. Post-fix `pytest -q`: 231 passed, 6 skipped. No live API or PostgreSQL tests ran.

## SOURCE_FIX_COMMIT

Source and tests were committed and pushed first as `49fd9fde137bb4324e0ae23765dd283dbe078497` (`fix: handle terminal nansen backfill postconditions`). Remote readback matched before physical validation.

## READ_ONLY_STAGING_STATE

Connection identity: `server_otg_staging` / `gunz_user` / transaction read-only `on`. Progress: 74 complete / 0 pending / 0 ambiguous; first pending is `NONE`. Flows: 12,365 total; 12,336 canonical hourly; 29 canonical daily. Ingestion runs: 81. Global natural-identity duplicates: 0.

## FULL_CANONICAL_IDENTITY_PROOF

The planner generated 12,336 expected identities. The database contained 12,336 distinct UTC-normalized identities. Missing: 0; unexpected: 0; duplicates: 0.

## FULL_CONTIGUITY_PROOF

Observed minimum: 2025-04-25T00:00:00Z. Observed maximum: 2026-09-20T23:00:00Z. Non-one-hour gaps: 0. Full contiguity passed.

## IDENTITY_DIGEST_PROOF

Expected and observed sorted UTC ISO identity digests both equal `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7`.

## BUCKET_INTEGRITY

Invalid non-hourly duration among canonical target records: 0. Incomplete canonical hourly rows: 0. Canonical natural-identity duplicates: 0.

## CHECKPOINT_OWNER_VALIDATION

Checkpoint timestamp: `2026-09-20T23:59:59Z`. Owner run: `dd2d9c89-3800-44b2-a8a9-9548dc87db55`. Owner status is success; stream matches Avalanche / Flows / canonical token / `smart_money`; its window end equals the checkpoint timestamp. Relative to Task 031's timestamp, timestamp non-regression passed. The equal-timestamp owner replacement is valid.

## RECENT_SET_VALIDATION

Task 031 documented 23 September 20 hourly identities before unit 74. Current count and distinct count are 24. The count delta is one, the final 23:00 UTC canonical target bucket is present, and duplicates are zero. Task 032R does not claim to reconstruct exact old-set membership retrospectively; the prior count is taken from Task 031, and full expected-versus-observed identity proof confirms the added bucket is canonical.

## DAILY_LAYER_CURRENT_BASELINE

Canonical daily rows remain 29. The current full daily natural-identity digest is `f1e457abee20e0a794c51ebf7cba87d8716c17bf80f41c5ceb8ccf7b6102ddaa`. Task 032 did not capture a full-target pre-unit-74 daily digest. Unit 74's date/write scope is disjoint from the early daily layer; this current digest is a baseline for future checks, not a claimed before/after comparison.

## CANONICAL_AUDIT_COMPLETION

All 74 canonical units have at least one successful exact-window audit with one API call and non-null warning evidence. Units without a successful audit: 0. Successful canonical units with unknown warning categories: 0.

## FAILED_AUDIT_HISTORY

Three failed ingestion audit rows remain present. Historical failed unit 46 audits were preserved.

## NO_LIVE_CALL_PROOF

`NANSEN_API_CALLS_TASK032R=0`. All staging inspection used an explicitly read-only transaction. `STAGING_WRITES_TASK032R=0`.

## POST_FIX_TESTS

`pytest -q`: 231 passed, 6 skipped. Default tests made zero live calls and zero PostgreSQL connections.

## PRODUCTION_SAFETY

Production connections, DDL, and DML were zero. Production was unchanged.

## SECURITY_CHECK

No key, `.env` contents, database password, raw response, warning text, wallet/transaction identifier, individual flow identity, or metric value was recorded. `.env` is untracked.

## CYRILLIC_CHECK

English-only scan passed.

## FILES_CHANGED

- `src/otg_nansen/backfill_execute.py`
- `tests/test_backfill_execute.py`
- `DEV/reports/032_complete_canonical_hourly_backfill/report.md` (append-only addendum)
- `DEV/reports/032r_terminal_postcondition_fix/report.md`
- `docs/architecture.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/analytics_methodology.md`
- `docs/nansen_api.md`

## RISKS

The full-target daily identity digest was not captured before unit 74; the current full daily digest is recorded for future comparisons. The recent prior count is documented, but exact pre-run identity membership is not reconstructed from the current database.

## NEXT_RECOMMENDED_TASK

The canonical staging backfill is fully verified. Any later analytical work requires separate authorization; this task starts none.
