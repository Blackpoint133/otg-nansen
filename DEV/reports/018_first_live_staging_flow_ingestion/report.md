# Task 018: First controlled live staging flow ingestion

## OBJECTIVE

Attempt the first bounded persistence of real Avalanche `$GUN` flow data to
the isolated staging schema using the existing orchestrator.

## STARTING_STATE

Starting `main` was `9a86b850600a179ffcb554831d0399783609093e`; the repository was
clean. Prior Task 017V evidence covered the exact requested day, but no live
data had been persisted.

## AUTHORIZED_SCOPE

Only Avalanche `$GUN`, endpoint `flows`, label `smart_money`, window
2026-09-20T00:00:00Z through 2026-09-20T23:59:59Z, targeting
`server_otg_staging.nansen`. No production target, other endpoint, chain, or
window was accessed.

## PRE_INGESTION_DATABASE_STATE

The staging target was `server_otg_staging`, user `gunz_user`, with
`transaction_read_only=off`. The two total flow count columns were `numeric`
and `NOT NULL`; all five expected tables existed. Exact target-window flow
rows were 0, the matching checkpoint was absent, and no exact-window prior
run existed.

## RESOURCE_BASELINE

CPU was 56%; available physical memory was 4,785,196 KB. Windows committed
memory was 21,248,045,056 bytes of a 33,272,041,472-byte limit, leaving
12,023,996,416 bytes of commit.

## LIVE_CLIENT_BOUNDS

The client was configured with `max_calls=3`, `max_retries=0`,
`page_size=10`, `max_pages=3`, and the configured 20-second timeout. Exactly
one orchestrator call was made; no retry or further request was attempted.

## INGESTION_EXECUTION

The existing `NansenIngestionOrchestrator.ingest_flows()` path created the
durable audit run, then the first source request timed out. The source raised
`NansenTransportError` with a sanitized timeout summary. No page was returned,
so normalization and the data transaction were never reached.

## LIVE_REQUEST_ACCOUNTING

One API attempt was made. `pages_requested=0`, `api_calls=1`,
`records_received=0`, and `records_normalized=0` in the failure audit.
Current record count is not comparable with Task 017V because no page was
received.

## NORMALIZATION_RESULT

Not reached: no records were returned by the request.

## DATABASE_PERSISTENCE_RESULT

Independent read-only verification found 0 target-window flow rows and no
checkpoint after the attempt. No live data was persisted.

## FRACTIONAL_NUMERIC_EVIDENCE

There are no persisted target rows from this attempt; fractional persisted
row counts are therefore zero. This does not test the live response's numeric
content. Task 017M's synthetic PostgreSQL NUMERIC round-trip remains the
database precision evidence.

## AUDIT_RUN_VALIDATION

Run `8ab88f8b-327d-4183-b20d-b32697ec62b8` is durably recorded as `failed`.
Its scope and exact requested window match the authorized request. Request
scope JSON agrees with the scalar identity columns. Failure counters reflect
the known attempt/page/record progress.

## REQUEST_SCOPE_VALIDATION

`request_scope` matches the run's scalar chain, endpoint, token, and flow label.

## CHECKPOINT_VALIDATION

No checkpoint was created or advanced. This is the expected failure-path
result; there is no successful run to reference.

## POST_COMMIT_CONSISTENCY

Failure-path consistency passed: the durable audit is failed, while target
data and checkpoint state remain absent.

## KNOWN_AUDIT_COUNTER_LIMITATION

`records_inserted` and `records_updated_or_conflicted` remain neutral zero by
design and do not represent affected-row classification. Persistence was
assessed through independent target-row state, which remained empty.

## RESOURCE_POSTCHECK

CPU was 43%; available physical memory was 4,929,168 KB. Committed memory was
21,064,470,528 bytes of 33,272,041,472, leaving 12,207,570,944 bytes of
commit. No retry loop or abnormal resource growth was observed; stability
passed.

## DEFAULT_TESTS

Before and after the attempt, `pytest -q` passed: 140 passed, 5 skipped.
Default tests made zero live API calls and zero PostgreSQL connections.

## PRODUCTION_SAFETY

Production DDL=0 and DML=0; production was not used. No migration or DDL was
run.

## SECURITY_CHECK

No credentials, raw response, wallet identity, transaction hash, or analytical
metric values are included in this report. Secret scan: PASS. Tracked `.env`:
NO.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `docs/database.md`
- `docs/operations.md`
- `docs/nansen_api.md`
- `DEV/reports/018_first_live_staging_flow_ingestion/report.md`

No application source was changed.

## RISKS

The API request timed out before data retrieval. The first live persistence
objective therefore remains incomplete; no conclusion about current response
count or source revision is possible. The failed audit row is intentionally
retained.

## NEXT_RECOMMENDED_TASK

Review the sanitized timeout and staging audit evidence, then request a
separately bounded retry task if appropriate. Do not expand the window or
request budget without authorization.

## TASK_018R_ADDENDUM

The original Task 018 run above remains failed on its first request under the
20-second timeout. Task 018R was a separate, explicitly authorized retry; it
completed successfully with a 60-second request timeout and retained the
validated flow rows and matching checkpoint in staging. See
`DEV/reports/018r_first_live_staging_flow_retry/report.md` for the retry's
independent evidence. The original failed audit was preserved.
