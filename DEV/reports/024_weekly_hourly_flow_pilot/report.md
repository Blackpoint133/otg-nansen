# Task 024: Weekly Hourly Flow Pilot

## OBJECTIVE

Validate one seven-day hourly Avalanche `$GUN` `smart_money` flow ingestion using bucket-aware identity and the exact warning policy.

## STARTING_STATE

Starting main was `bca84c3f061cdab95e2649224810075253cdc632`, branch `main`, clean. Baseline tests passed: 180 passed, 6 skipped; default live API calls and PostgreSQL connections were zero.

## AUTHORIZED_WINDOW

Only 2025-04-25T00:00:00Z through 2025-05-01T23:59:59Z was requested.

## STAGING_PREFLIGHT

Verified `current_database=server_otg_staging`, `current_user=gunz_user`, `transaction_read_only=off`. All five Nansen tables exist. `source_warnings` is nullable `jsonb`.

## GLOBAL_RETAINED_STATE

Before the pilot there were 52 flow rows. The September window held 23 rows and 23 natural identities. The high-water checkpoint was 2026-09-20T23:59:59Z, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## LEGACY_WARNING_AUDIT_STATE

Four ingestion runs existed and all four had `source_warnings=NULL`. No successful exact-week run existed.

## TARGET_WINDOW_PRECHECK

Six target-window rows were present: six daily buckets, zero hourly buckets, zero other durations. Each was complete and matched the Avalanche `smart_money` stream.

## DAILY_IDENTITY_BASELINE

Sorted existing daily `flow_key` set SHA-256: `d90c3c05401be9c5dd1946128d0c105a2f9ab158aa6215a552faf83de2cef251`. Individual keys were not printed or stored in this report.

## RESOURCE_BASELINE

Available RAM: 4,658 MB. Windows committed memory: 20,742 MB; commit limit: 31,730 MB; free commit: 10,988 MB. CPU samples across two short 5-second observations averaged about 55.1%, ranging from 23.7% to 94%; this was variable rather than sustained saturation. No resource condition blocked the pilot.

## CLIENT_BOUNDS

`MAX_CALLS=1`; `MAX_RETRIES=0`; `PAGE_SIZE=1000`; `MAX_PAGES=1`; `TIMEOUT_SECONDS=120`.

## INGESTION_EXECUTION

Exactly one existing `NansenIngestionOrchestrator.ingest_flows()` run completed successfully. No manual fetch or insert was used.

## LIVE_REQUEST_ACCOUNTING

`RUN_ID=8b4b9a66-1e3b-4151-b6ab-f243af67f882`; `PAGES_REQUESTED=1`; `LIVE_API_CALLS_TASK024=1`; `RECORDS_RECEIVED=167`; `RECORDS_NORMALIZED=167`; `FINAL_PAGE_REACHED=YES`.

## WARNING_POLICY_RESULT

The response had one warning. It matched the exact approved fingerprint and classified only as `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`. Normalized records passed the all-null structural guard. The successful audit has non-null sanitized warning metadata; raw warning text and response data were not persisted.

## RESOLUTION_VALIDATION

After ingestion, 167 retained buckets had exactly one-hour duration; six daily buckets remained; no other duration was present. All received records were normalized and retained as hourly buckets.

## MULTI_RESOLUTION_COEXISTENCE

The target window now contains 173 rows: six daily plus 167 hourly. This equals six pre-existing rows plus 167 normalized records. `MULTI_RESOLUTION_COEXISTENCE=PASS`.

## DAILY_IDENTITY_PRESERVATION

After digest: `d90c3c05401be9c5dd1946128d0c105a2f9ab158aa6215a552faf83de2cef251`. It matches the pre-pilot digest. `DAILY_BUCKETS_UNCHANGED=PASS`.

## HOURLY_IDENTITY_VALIDATION

167 unique hourly flow keys and 167 unique natural bucket identities; duplicate keys: 0.

## HOURLY_TEMPORAL_STRUCTURE

Earliest hourly date: `2025-04-25T01:00:00Z`. Latest: `2025-05-01T23:00:00Z`. Distinct timestamps: 167. Distinct UTC calendar dates: 7. Missing UTC calendar dates: 0 (`NONE`). An absent individual hourly bucket does not imply no activity.

## COMPLETENESS_VALIDATION

Incomplete hourly rows: 0. Out-of-window hourly rows: 0. Non-positive hourly intervals: 0.

## WARNING_AUDIT_VALIDATION

`SOURCE_WARNINGS_IS_NULL=NO`; page count 1; warning count 1; category set `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`; sanitized shape passed. The stored summary contains only `page`, `warning_count`, and `categories`; no raw text fields.

## AUDIT_COUNTERS

Run status is success for the exact stream and window. Pages 1, API calls 1, records received 167, normalized 167. `AUDIT_COUNTERS_MATCH=PASS`.

## CHECKPOINT_NON_REGRESSION

Checkpoint remains 2026-09-20T23:59:59Z with run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. `CHECKPOINT_NON_REGRESSION=PASS`.

## AUDIT_HISTORY

Five ingestion runs now exist. The four legacy rows remain unchanged and `source_warnings=NULL`; the new successful run has non-null sanitized warning data. Legacy audit digest remains `14ee45136704faedc3c30b0f5672ba04125426ae3b8d992e3666015cfb960034`. `AUDIT_HISTORY_PRESERVED=PASS`.

## GLOBAL_FLOW_ACCOUNTING

Global flow rows increased from 52 to 219, exactly 52 + 167. The recent September window remains 23 rows and 23 natural identities.

## NUMERIC_STRUCTURE

Both flow count columns remain PostgreSQL `NUMERIC`. Hourly rows with fractional inflow count: 0; fractional outflow count: 0. No metric values were exposed. `NUMERIC_PRESERVATION=PASS`.

## RESOURCE_POSTCHECK

CPU samples averaged 25.8%, ranging from 20.7% to 34.3%. Available RAM: 4,663 MB. Windows committed memory: 20,736 MB; commit limit: 31,730 MB; free commit: 10,994 MB. No retry loop or abnormal connection growth was observed. `RESOURCE_STABILITY=PASS`.

## DEFAULT_TESTS

After ingestion: `pytest -q` => 180 passed, 6 skipped; live API calls 0; PostgreSQL connections 0. Tests did not remove retained pilot rows.

## PRODUCTION_SAFETY

`PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`. No migration was run.

## SECURITY_CHECK

No raw warning, API response, credential, wallet address, transaction hash, analytical metric value, or individual flow key was printed or added to the report. `SECRET_SCAN=PASS`; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

`DEV/reports/024_weekly_hourly_flow_pilot/report.md`; `docs/database.md`; `docs/nansen_api.md`; `docs/operations.md`; `docs/analytics_methodology.md`. No source code or schema changed.

## RISKS

The pilot validates one seven-day window only. A 167-record result has one fewer hourly timestamp than a complete 168-hour grid; absent timestamps are not interpreted as inactivity. It does not establish coverage for any other window or authorize systematic backfill.

## NEXT_RECOMMENDED_TASK

Review this bounded pilot before separately authorizing any next historical ingestion unit. Do not start systematic historical backfill or Task 025 automatically.
