## OBJECTIVE

Diagnose and repair the Avalanche `$GUN` flows normalization mismatch found by
Task 015 without database access or additional endpoint calls beyond the one
authorized flows diagnostic.

## STARTING_STATE

The repository started at the Task 015 baseline. Token-information and DEX
trades had normalized successfully. Flows had returned a structurally valid
two-record first page but normalization had failed.

## TASK015_MISMATCH

Task 015 retained the failure class but not the field-level message. Local
evidence was therefore insufficient to identify the exact field before a new
request.

## DIAGNOSTIC_SOURCE

One direct, non-retried Avalanche flows request using the already validated
Task 015 payload and historical window was used. The response was inspected
in memory only. No raw row, value, wallet identity, transaction hash, header,
or credential was saved.

## LIVE_CALL_BUDGET

The Task 016 limit was one attempt. Exactly one attempt was used, with zero
retries and one page requested.

## SANITIZED_FIELD_TYPES

The two observed records had these relevant shapes:

- `date`: timezone-bearing ISO-8601 string;
- `price_usd`, `token_amount`, `value_usd`: finite JSON floats;
- `holders_count`: JSON integer;
- `total_inflows_count`, `total_outflows_count`: finite mathematically
  integral JSON floats;
- `bucket_end`: timezone-bearing ISO-8601 string;
- `is_complete`: boolean;
- optional CEX/DEX count fields: null.

No numeric values were recorded.

## NORMALIZATION_ERROR

The safe error was:

`NormalizationError: flows.data[N].total_inflows_count: expected integer`

`N` denotes a record index. The error contained no live value.

## OFFICIAL_FIELD_SEMANTICS

The current official flows documentation defines the relevant fields as flow
metrics, including inflow and outflow counts. It does not establish that the
JSON wire encoding must always be an integer token. The live observation is
therefore authoritative for the narrow wire-type compatibility repair.

## ROOT_CAUSE

The normalizer's general integer helper accepted Python integers only. JSON
decoding of the observed count fields produced floats even though their values
were mathematically integral. The second count field would have failed at the
same boundary after the first was corrected.

## NORMALIZATION_REPAIR

A dedicated field-specific helper now accepts finite, non-negative,
mathematically integral `int` or `float` values and converts them exactly to
`int`. It is used only for `total_inflows_count` and `total_outflows_count`.
The general integer policy was not loosened.

## STRICTNESS_PRESERVED

Booleans, fractional floats, negative counts, NaN, infinity, malformed values,
missing required values, malformed timestamps, and naive timestamps remain
rejected. Optional null fields remain `None`; they are not converted to zero.

## FIXTURE_UPDATE

The Avalanche flow fixture now uses invented deterministic values with the
observed integral-float count shape and nullable optional count fields.

## REGRESSION_TESTS

Tests cover successful exact integral floats and rejection of fractional,
negative, non-finite, and boolean count values. The full default suite passed.

## LIVE_RENORMALIZATION

The original live response object was not retained after the diagnostic
process, so it could not be rerun in memory after the source edit without a
second prohibited live request. The repaired normalizer passes the sanitized
fixture that reproduces the observed live type/null contract. A same-object
post-edit live rerun is therefore UNPROVEN.

## FLOW_COMPLETENESS_OBSERVATION

Both observed records had `is_complete=true` and included `bucket_end`. The
page was not final (`is_last_page=false`), so complete historical-window
behavior remains NOT VERIFIED.

## DATABASE_ISOLATION

No PostgreSQL connection, repository, write, checkpoint update, or DDL was
performed.

## DEFAULT_TESTS

`pytest -q`: 114 passed, 4 skipped. Default live calls and PostgreSQL
connections were zero.

## LIVE_API_CALL_COUNT

`LIVE_API_CALLS_TASK016=1`.

## SECURITY_CHECK

No API key, authorization header, password, credential-bearing URL, raw live
response, wallet address, or transaction hash was saved. `SECRET_SCAN=PASS`.

## CYRILLIC_CHECK

All repository-authored content is English only. `CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

- `src/otg_nansen/normalize.py`
- `tests/fixtures/nansen/flows_avalanche.json`
- `tests/test_normalize.py`
- `docs/nansen_api.md`
- `DEV/reports/015_live_avalanche_contract_probe/report.md`
- this report

## RISKS

The exact live page was not retained for a post-edit same-object rerun. The
repair is narrowly supported by the one sanitized live type diagnostic and
fixture regression coverage. Complete multi-page flow ingestion remains
unverified.

## NEXT_RECOMMENDED_TASK

Obtain separate authorization for a small live recheck or proceed only after
review of this repair. Do not begin real ingestion or Task 017 from this
report alone.
