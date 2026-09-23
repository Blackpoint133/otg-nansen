## OBJECTIVE

Revalidate the complete bounded Avalanche `$GUN` flow window after converting
the two total flow count metrics to Decimal/NUMERIC.

## STARTING_STATE

Starting main was `195e53a8c4de0681fe49dd23c66417a646f521a1`. Task 017M had
published the Decimal model and applied the two-column NUMERIC migration to
staging. This task did not connect to PostgreSQL.

## IDENTITY_RECHECK

The current official GUNZ public source listed the Avalanche contract as
`0x26deBD39D5eD069770406FCa10A0E4f8d2c743eB`; project configuration matched.
Source: https://gunbygunz.com/gun/.

## REQUEST_CONTRACT_RECHECK

Current official Nansen flows documentation supports the POST date-range,
label, pagination, and `order_by` array request. The request used
`[{"field":"date","direction":"ASC"}]` and no standalone `order` field.
The official pagination schema permits page sizes from 1 to 1000; page size
10 is within that documented range. Source:
https://docs.nansen.ai/api/token-god-mode/flows.

## WINDOW

Exactly 2026-09-20T00:00:00Z through 2026-09-20T23:59:59Z, Avalanche,
`smart_money`.

## LIVE_CALL_BUDGET

Configuration: `page_size=10`, `max_pages=3`, `max_calls=3`, and
`max_retries=0`. Exactly three request attempts were used.

## PAGINATION_RESULT

- pages fetched: 3;
- records collected: 23;
- final page reached: yes.

## WIRE_TYPE_OBSERVATION

- `total_inflows_count`: finite JSON floats; both integral and fractional
  categories observed; sign categories zero and positive;
- `total_outflows_count`: finite JSON floats; integral category; zero sign
  category;
- all four optional CEX/DEX count fields: null only.

No magnitudes were recorded.

## NORMALIZATION_RESULT

All 23 collected records normalized successfully with the same in-memory page
collection. No record was dropped.

## DECIMAL_MODEL_VALIDATION

Every normalized total inflow and outflow count was a Python `Decimal`. A
fractional inflow was observed and preserved as a non-integral Decimal. No
fractional outflow was observed in this window. Optional count model types
were `NoneType` only.

## WINDOW_BOUND_VALIDATION

All record dates were within the requested inclusive bounds. Out-of-window
count: zero.

## COMPLETENESS_RESULT

All 23 records had `is_complete=true`; false count zero; null count zero.

## ORDERING_RESULT

Dates were non-decreasing. Duplicate timestamp count: zero.

## BUCKET_STRUCTURE

All 23 records had a non-null bucket end. All bucket-end datetimes were
timezone-aware and normalized to UTC.

## OPTIONAL_COUNT_FIELDS

Each optional CEX/DEX wire field was null only and normalized to `NoneType`.

## DATABASE_ISOLATION

Zero PostgreSQL connections, writes, DDL, migrations, ingestion audit rows,
and checkpoints. Live data was not persisted.

## DEFAULT_TESTS

`pytest -q`: 140 passed, 5 skipped. Default live API calls and PostgreSQL
connections were zero.

## LIVE_API_CALL_COUNT

`LIVE_API_CALLS_TASK017V=3`.

## LIVE_DATA_POLICY

The complete response remained in memory only. No raw response, row, metric
magnitude, wallet identity, or transaction hash was written or committed.

## SECURITY_CHECK

No API key, authorization header, database credential, or `.env` value was
recorded. `SECRET_SCAN=PASS`; `.env` is untracked and ignored.

## CYRILLIC_CHECK

All repository-authored content is English only. `CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

- `docs/nansen_api.md`
- `DEV/reports/017_complete_live_flow_window/report.md`
- `DEV/reports/017m_flow_count_decimal_model/report.md`
- this report

## RISKS

Evidence covers one chain, label, and UTC day. It does not establish other
windows, wider historical depth, Solana completeness, production ingestion,
or large backfills.

## NEXT_RECOMMENDED_TASK

Review the bounded one-day validation and separately authorize any broader
coverage or ingestion work. Do not start Task 018.
