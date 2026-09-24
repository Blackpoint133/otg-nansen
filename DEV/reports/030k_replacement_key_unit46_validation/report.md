# Task 030K: Replacement key validation for unit 46

## OBJECTIVE

Validate the operator-replaced local Nansen key using exactly one authorized canonical unit 46 ingestion attempt, with no unit 47 request.

## STARTING_STATE

Local `HEAD` and `origin/main` were `7f89502ae73a55339462d7515b3e8a02adf34123`, with a clean worktree. The accepted starting staging state was 45 complete / 29 pending / 0 ambiguous; first pending unit 46. Flows were 7,567 total (7,538 hourly, 29 daily), with 52 ingestion runs. Unit 46 had two failed audits, no success, and no desired hourly rows.

## KEY_CONFIGURATION_CHECK

The project dotenv loader was used after removing any inherited process key. It reported `NANSEN_API_KEY_PRESENT=YES` and `NANSEN_API_KEY_NONEMPTY=YES`. The key, its fragments, length, and hash were not read into output or persisted. `.env` is not tracked.

## BASELINE_TESTS

`pytest -q`: 219 passed, 6 skipped. The default suite made no live Nansen calls and no PostgreSQL connections.

## PRE_LIVE_STAGING_STATE

Read-only identity was `server_otg_staging`, `gunz_user`, transaction read-only `on`. Progress was 45 / 29 / 0, first pending 46. Structural totals were 7,567 flows, 7,538 canonical hourly, 29 daily, and 52 ingestion audits. Unit 46 had two failed audits, zero successful audits, and 0/167 desired identities. The checkpoint was `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`; September 20 retained 23 hourly rows / 23 identities.

## UNIT46_PRE_STATE

Coverage: 2026-03-04T03:00:00Z through 2026-03-11T01:00:00Z. Request: 2026-03-04T02:00:00Z through 2026-03-11T01:59:59Z. Desired hourly starts: 167.

## LIVE_AUTHORIZATION

One new live API attempt was authorized, limited to unit 46 through the committed staging-only runner with one call, no retries, one page maximum, and the existing double opt-in. Unit 47 was not authorized.

## LIVE_ATTEMPT

The runner selected only canonical unit 46 and used the exact planned request bounds. Exactly one API attempt was made.

## UNIT46_AUDIT_RESULT

New run `bf10d1fc-5ce1-47b2-b29f-2484cf1286b4` is successful with one page, one API call, 167 records received and normalized, and non-null sanitized warning evidence. The only category is `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`. The two earlier failed audits remain intact.

## UNIT46_COVERAGE_RESULT

UTC-normalized structural validation: 167 desired, 167 observed, zero missing, zero duplicate hourly identities. The request-start bucket is present. Unit 47 has no audit.

## REPLACEMENT_KEY_VALIDATION

`PASS`: the one authorized request succeeded after loading the replacement key through the normal project dotenv configuration path. No key material was displayed, hashed, or committed.

## PLAN_PROGRESS

Fresh read-only progress: 46 complete / 28 pending / 0 ambiguous; first pending unit 47. No additional canonical unit was executed.

## GLOBAL_ROW_ACCOUNTING

Flow rows increased from 7,567 to 7,734, exactly 167 new hourly identities. Final counts: 7,705 hourly, 29 daily, 53 ingestion audits, and zero global natural-identity duplicates. Daily identity digest remained unchanged.

## CHECKPOINT_NON_REGRESSION

Checkpoint remains `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## RECENT_DATA_INTEGRITY

September 20 remains 23 hourly rows and 23 distinct identities.

## DEFAULT_TESTS

Post-live `pytest -q`: 219 passed, 6 skipped. Default tests made zero live calls and zero PostgreSQL connections.

## PRODUCTION_SAFETY

Production connections: 0; DDL: 0; DML: 0; production changed: no.

## SECURITY_CHECK

No API key, key fragment, key length/hash, `.env` content, raw response, raw warning, credential, wallet address, transaction hash, or analytical metric was included. `.env` is not tracked.

## CYRILLIC_CHECK

English-only report; secret and Cyrillic scans passed.

## FILES_CHANGED

- `DEV/reports/030k_replacement_key_unit46_validation/report.md`
- `DEV/reports/030_fourth_live_backfill_batch/report.md` (historical addendum)
- `DEV/reports/030d_unit46_http_failure_diagnostic/report.md` (historical addendum)
- `docs/architecture.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/analytics_methodology.md`
- `docs/nansen_api.md`

## RISKS

This validates one specific canonical window with one call. It does not establish the key's broader access scope or account balance, and it does not validate later units.

## NEXT_RECOMMENDED_TASK

Unit 47 is the next pending canonical unit. Execute it only under separate authorization.
