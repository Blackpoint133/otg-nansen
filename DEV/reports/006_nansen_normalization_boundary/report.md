# Report 006 - Verified Nansen normalization boundary

## OBJECTIVE

Create the deterministic raw-response to normalized-model boundary for the
three verified Nansen endpoint families without database persistence, live
calls, backfill, services, or production changes.

## STARTING_STATE

- Repository: `C:\VAMBAM\Projects\OTG\parsers\parser_nansen`
- Starting main SHA: `fb6593bc455c8c3a0562db5804e86101fce839e4`
- Working tree was clean.

## PAGINATION_TRUNCATION_FIX

`NansenClient.paginate()` now raises `PaginationLimitReached` when the final
allowed page still reports `is_last_page=false`. The exception exposes only
endpoint, page count, and collected-record count. A final allowed page with
`is_last_page=true` still succeeds. Request-budget exhaustion remains a
separate exception.

## NORMALIZATION_ARCHITECTURE

The boundary is:

`raw Nansen mapping -> strict normalizer -> immutable project model -> future persistence`

Normalizers validate required fields and reject malformed records rather than
silently dropping them. Unknown extra fields are ignored for forward
compatibility.

## MODELS

Added immutable dataclasses for `NormalizedTokenInformation`,
`NormalizedFlowRecord`, and `NormalizedDexTrade`. Each has deterministic
`to_dict()` serialization. Decimal values serialize as strings and UTC
timestamps serialize with an explicit `Z` suffix.

## NUMERIC_POLICY

Monetary, token, supply, price, and liquidity values use `Decimal(str(value))`.
NaN, infinity, booleans, and malformed values are rejected. Contract counts
remain integers.

## TIMESTAMP_POLICY

Required ISO-8601 timestamps must include an offset or `Z`. Accepted values are
converted to timezone-aware UTC datetimes. Naive and malformed timestamps fail
with `NormalizationError`.

## IDENTITY_POLICY

Chain and requested token address come from trusted caller configuration and
are preserved in every model. Token-information and DEX-trade response
identities are compared with the requested token; mismatches fail explicitly.

## TOKEN_INFORMATION_NORMALIZATION

Validates object `data`, required name/symbol/contract identity, and mapping
`token_details`/`spot_metrics` containers. Optional numeric fields remain
`None` when absent. No pagination is assumed.

## FLOW_NORMALIZATION

Validates list `data`, required flow fields, timestamps, Decimal values, integer
counts, optional bucket/completeness fields, and empty datasets. The empty
Solana fixture normalizes to `[]`.

## DEX_TRADE_NORMALIZATION

Validates list `data`, requested-token identity, timestamps, transaction/trader
strings, source action, and all verified token/value fields. Source action is
preserved without inventing a buy/sell value.

## TESTS

`pytest -q`: 55 passed, 1 opt-in live test skipped. Tests are fixture-only and
made zero live API calls. Coverage includes valid and empty responses, Decimal
conversion, offset conversion, UTC serialization, malformed/naive timestamps,
invalid numeric values, missing fields, identity mismatch, extra-field
tolerance, batch safety, and pagination completion behavior.

## LIVE_API_CALL_COUNT

LIVE_API_CALLS_TASK006=0

## FILES_CHANGED

Added `models.py`, `normalize.py`, and normalization tests; updated pagination
and public errors; updated package exports, documentation, and this report.
No database, service, or production file was changed.

## SECURITY_CHECK

SECRET_SCAN=PASS
ENV_TRACKED=NO
No API calls, credentials, authorization headers, or `.env` values were used
or written.

## CYRILLIC_CHECK

CYRILLIC_SCAN=PASS

## RISKS

Endpoint schemas may evolve and future persistence must preserve Decimal and
UTC conventions. Identity matching assumes the current verified endpoint field
semantics.

## UNRESOLVED_QUESTIONS

- Review normalized model retention and schema mapping before persistence.
- Confirm whether future endpoints require additional identity rules.
- Define analytical event semantics separately from normalization.

## NEXT_RECOMMENDED_TASK

Task 007 should add fixture-backed persistence design or a dry-run repository
adapter, after external review, without writing PostgreSQL rows or performing
historical backfill.
