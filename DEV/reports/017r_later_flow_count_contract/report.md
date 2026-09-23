## OBJECTIVE

Diagnose the later-page Avalanche `$GUN` flow count mismatch and repair only
if the source value can be preserved exactly under the current model contract.

## STARTING_STATE

The repository started at the published Task 017 baseline. Task 017 had
reached the final page but failed normalization at a later inflow count field.

## TASK017_RESULT

Task 017 used three requests, reached the final page, collected a complete
response, and failed normalization at `flows.data[2].total_inflows_count`.
No database connection or persistence occurred.

## OFFICIAL_SEMANTICS_RECHECK

Current official Nansen flows documentation describes the inflow and outflow
fields as numeric flow metrics. The response schema exposes them as `number`,
while the related filter schema describes integer ranges. Exact response
wire encoding, nullability, and a non-negative sign constraint are not all
explicitly documented. The official documentation does not authorize
rounding or truncation of a fractional response value.

## LIVE_CALL_BUDGET

The hard limit was three attempts with zero retries. Exactly three attempts
were used.

## PAGINATION_RESULT

The paginator reached the actual final page after three requests. The complete
in-memory response contained 23 records.

## SANITIZED_COUNT_DIAGNOSTIC

`total_inflows_count`:

- wire types: `float`;
- finite: `yes`;
- integral: `yes`, `no`;
- signs: `positive`, `zero`.

`total_outflows_count`:

- wire types: `float`;
- finite: `yes`;
- integral: `yes`;
- signs: `zero`.

The failing field was `total_inflows_count`; its wire type was `float`, it was
finite, non-integral, positive, and not null. No magnitude was recorded.

## OPTIONAL_COUNT_DIAGNOSTIC

All four CEX/DEX breakdown fields were observed only as `null`. No numeric
values were recorded.

## PRE_REPAIR_NORMALIZATION

The same complete in-memory response was tested with the current normalizer
before any source change:

`PRE_REPAIR_NORMALIZATION_RESULT=FAIL`

`PRE_REPAIR_ERROR_FIELD=flows.data[2].total_inflows_count`

`PRE_REPAIR_ERROR_REASON=expected finite non-negative integer`

## ROOT_CAUSE

The later response contains a finite fractional float in a field represented
by the project as an integer count. This is materially different from the
previous accepted integral-float shape. Rounding or truncating the source
would lose information and would not preserve the source value exactly.

## REPAIR_DECISION

`TASK_017R_STATUS=DIAGNOSED_MODEL_DECISION_REQUIRED`.

The specified safe repair matrix prohibits changing this fractional value into
an integer. No source repair was applied.

## NORMALIZATION_REPAIR

None. The current strict integer boundary remains unchanged.

## STRICTNESS_PRESERVED

No fractional, non-finite, boolean, string, null, or other value was accepted
through a speculative conversion. No rounding or truncation was introduced.

## FIXTURE_UPDATE

None. No live value was copied into a fixture, and no fixture change was
justified without a model decision for fractional count semantics.

## REGRESSION_TESTS

No source change was made. The default suite passed unchanged.

## POST_REPAIR_VALIDATION_LIMIT

No repair was made, so no post-repair live validation was attempted. The
complete response remained in memory only during diagnosis and was not written
to disk.

## COMPLETE_WINDOW_STATUS

`COMPLETE_WINDOW_ACCEPTED=NO`. Final-page pagination was proven, but complete
window normalization was not.

## DATABASE_ISOLATION

No PostgreSQL connection, repository, write, checkpoint, audit row, migration,
or DDL operation occurred.

## DEFAULT_TESTS

`pytest -q`: 122 passed, 4 skipped. Default live calls and PostgreSQL
connections were zero.

## LIVE_API_CALL_COUNT

`LIVE_API_CALLS_TASK017R=3`.

## SECURITY_CHECK

No API key, authorization header, password, raw response, wallet address,
transaction hash, or live metric value was saved. `SECRET_SCAN=PASS`.

## CYRILLIC_CHECK

All repository-authored content is English only. `CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

- `docs/nansen_api.md`
- `DEV/reports/017_complete_live_flow_window/report.md`
- this report

## RISKS

The current normalized model and PostgreSQL design represent these count
fields as integers, but the live response can contain a finite fractional
number. The correct model/schema policy must be reviewed before ingestion.

## NEXT_RECOMMENDED_TASK

Decide whether flow count fields should become exact Decimal values or whether
the endpoint contract provides a safe separate interpretation. Do not start
Task 018 or persist live flows before that decision.
