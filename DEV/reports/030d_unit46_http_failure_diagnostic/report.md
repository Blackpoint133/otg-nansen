# Task 030D: Unit 46 HTTP failure diagnostic

## OBJECTIVE

Diagnose the two durable unit 46 failures and apply the conditional retry gate. No new API request was authorized by the evidence.

## STARTING_STATE

HEAD and `origin/main` were `29801eed8e818363111e47d830d117f8e7e1f2f5`; worktree clean. Baseline tests: 219 passed, 6 skipped. Read-only staging identity was `server_otg_staging`, `gunz_user`, read-only `on`; progress 45/29/0, first pending 46. Staging had 7,567 flows (7,538 hourly, 29 daily), 52 ingestion audits, zero natural-identity duplicates. Checkpoint and September 20 retained rows were unchanged.

## UNIT46_REQUEST

Canonical coverage: 2026-03-04T03:00:00Z through 2026-03-11T01:00:00Z. Request window: 2026-03-04T02:00:00Z through 2026-03-11T01:59:59Z. Desired bucket count: 167.

## EXISTING_FAILED_AUDITS

Exactly two failed exact-window audits were present. Both were `NansenHTTPError`; each had `api_calls=1`, `pages_requested=0`, zero received and normalized records, and NULL `source_warnings`.

## SAFE_HTTP_FAILURE_EVIDENCE

Failure 1: run `b72a1df3-fdaa-48a3-b18a-4e45050dd928`; HTTP 403; `NansenHTTPError`; exact durable `error_summary` SHA-256 `1375e3664571bd18299a2c17d9db6aef70840882ae850c1f7e37379eb0ead1b5`.

Failure 2: run `c67d3c7b-97f8-4e81-add0-82c0884a3684`; HTTP 403; `NansenHTTPError`; exact durable `error_summary` SHA-256 `12eff75e2dfedbac2848aae9062cd6fd40bfc39097907c77db44764c3fa2825a`.

The summaries were inspected in memory. Their safe text flags were identical: rate-limit false; server-failure false; gateway false; timeout false; authentication false; forbidden wording false; credit-related / insufficient-credit wording true; validation false; date-range false; bad-request false. These text flags do not override the HTTP status classification. Raw summaries and response bodies are not included here.

## FAILURE_TIMING

Failure 1 started 2026-09-24T04:37:58.820455Z; failure 2 started 2026-09-24T05:18:40.875114Z. Separation: 2,442 seconds. Timing alone does not establish cause.

## OFFICIAL_NANSEN_RESEARCH

Official Error Handling identifies HTTP 403 as Forbidden (authenticated but no permission) and advises checking account access. Its detailed error-code table marks `forbidden` and `insufficient_credits` non-retryable; insufficient credits require adding credits or upgrading. HTTP 402 is Payment Required. For 429, official guidance is to slow down and honor `Retry-After`; 500 and 504 have retry guidance. The rate-limit page says rate limiting yields 429 and `Retry-After` should be honored. The current Flows schema lists response classes including 402, 403, 429, 500, 502, 503, and 504. The changelog contained no relevant unit-46 or Flows retry change. Account plan/balance was not queried.

Official sources:
- https://docs.nansen.ai/getting-started/error-handling
- https://docs.nansen.ai/getting-started/rate-limits
- https://docs.nansen.ai/api/token-god-mode/flows
- https://docs.nansen.ai/getting-started/credits
- https://docs.nansen.ai/api/changelog

## CLIENT_RETRY_POLICY

The committed `RETRYABLE_STATUSES` set is `{429, 500, 502, 503, 504}`. HTTP 403 is excluded.

## PAYLOAD_STRUCTURAL_COMPARISON

Units 45, 46, and 47 share endpoint `/api/v1/tgm/flows`, Avalanche chain, token present, `smart_money` label, page 1 / 1,000 per page, and ascending date ordering. Only their canonical dates differ. Each request duration is 604,799 seconds (6 days, 23:59:59). Unit 46 payload structure matches both neighbors.

## FAILURE_CLASSIFICATION

`AUTH_OR_CREDIT_BLOCK`. Both statuses are 403. Their safe durable summaries contain credit-related text, but do not contain a retryable status. Current official guidance distinguishes 403 Forbidden from 402 Payment Required and marks insufficient-credit / forbidden conditions non-retryable.

## RETRY_DECISION

`RETRY_AUTHORIZED=NO`. Gate condition B fails because 403 is not in the committed retryable set; official guidance also provides no retry permission for 403 or insufficient credits. The matching payload shape does not change this result.

## RETRY_WAIT

`NOT_APPLICABLE`; no retry was authorized.

## PRE_RETRY_STATE

Not applicable. No pre-retry live gate was entered and no additional request was made. The staging state remained 45 complete / 29 pending / 0 ambiguous, first pending 46.

## CONDITIONAL_LIVE_ATTEMPT

None. `NEW_LIVE_API_CALLS_TASK030D=0`.

## UNIT46_RECOVERY_RESULT

`NOT_RETRIED`.

## POST_ATTEMPT_AUDIT

No new audit was created. Existing unit 46 failed audit count remains two.

## POST_ATTEMPT_COVERAGE

Unit 46: 167 desired starts, 0 observed, 167 missing, 0 duplicates. No data was written.

## PLAN_PROGRESS

45 complete / 29 pending / 0 ambiguous; first pending 46. No unit 47 or later was executed.

## CHECKPOINT_NON_REGRESSION

Checkpoint remains 2026-09-20T23:59:59Z, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## RECENT_DATA_INTEGRITY

September 20 remains 23 hourly rows and 23 distinct identities.

## RESOURCE_OBSERVATION

Diagnostic snapshot: CPU 21.9%, available RAM 4,706 MB, committed memory 20,889 MB, commit limit 31,731 MB, free commit 10,841 MB. No retry occurred.

## DEFAULT_TESTS

Post-diagnostic `pytest -q`: 219 passed, 6 skipped; zero live API calls and zero PostgreSQL connections.

## PRODUCTION_SAFETY

Production connections: 0; DDL: 0; DML: 0; changed: no.

## SECURITY_CHECK

Only status, type, exact summary hashes, timestamps, and Boolean semantic flags are durable. No raw summary, response body, API key, database password, wallet address, transaction hash, or metric value is included. `.env` is not tracked.

## CYRILLIC_CHECK

English-only report; Cyrillic and secret scans passed.

## FILES_CHANGED

- `DEV/reports/030d_unit46_http_failure_diagnostic/report.md`
- `DEV/reports/030_fourth_live_backfill_batch/report.md` (historical addendum)
- `docs/architecture.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/analytics_methodology.md`
- `docs/nansen_api.md`

## RISKS

The two failures classify as non-retryable under current official guidance and the committed client policy. Unit 46 remains pending; progress must not be advanced based on row counts.

## NEXT_RECOMMENDED_TASK

Check account access and credit status through the Nansen account/support channels without calling Flows. After resolving the access/payment condition, separately authorize one bounded unit 46 attempt. Do not execute unit 47.
