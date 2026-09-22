# Report 004 - Nansen client foundation

## OBJECTIVE

Implement a small bounded Nansen HTTP client, conservative configuration,
fixture-first contract tests, and a maximum-four-call live validation. No
persistence, backfill, service, frontend, or production deployment was done.

## STARTING_STATE

- Repository: `C:\VAMBAM\Projects\OTG\parsers\parser_nansen`
- Starting main SHA: `2b7f56db0727921e27432d9a5c2064b42abe2946`
- Working tree was clean.
- Task 003 Phase 0B findings were retained.

## TASK003_REPORT_CORRECTION

Repository-wide checks were run before editing. The stale Task 003 markers
were changed to `CYRILLIC_SCAN=PASS` and `SECRET_SCAN=PASS`.

## CURRENT_NANSEN_CONTRACT_RECHECK

Current official documentation continues to use `https://api.nansen.ai`, JSON
POST requests, the `apikey` authentication header, bounded pagination, and
documented transient HTTP statuses including 429 and 5xx. The current rate
reference lists plan-specific Free and Pro windows; the supported-chain
reference lists Avalanche and Solana and does not list `gunz`.

## ACCOUNT_PLAN_STATUS

ACCOUNT_PLAN=UNVERIFIED

Plan-specific limits and credits are not hardcoded. Client defaults are
conservative and configurable without exposing secret values.

## NATIVE_GUNZ_SUPPORT_STATUS

NATIVE_GUNZ_NANSEN_SUPPORT=NOT_LISTED_IN_CURRENT_SUPPORTED_CHAIN_REFERENCE

## FILES_CREATED

- `pyproject.toml`
- `src/otg_nansen/__init__.py`
- `src/otg_nansen/config.py`
- `src/otg_nansen/errors.py`
- `src/otg_nansen/client.py`
- `tests/test_client.py`
- `tests/test_live_contract.py`
- four sanitized JSON fixtures under `tests/fixtures/nansen/`
- this report

## FILES_CHANGED

- `README.md`
- `docs/architecture.md`
- `docs/nansen_api.md`
- `DEV/reports/003_phase_0b_reconnaissance/report.md`

## CLIENT_ARCHITECTURE

`NansenClient` reads `NANSEN_API_KEY` through configuration, sends JSON POST
requests, exposes request metadata, and never places the key in exception
messages. Helpers cover token information, flows, and DEX trades. The HTTP
session is injectable for deterministic tests.

## REQUEST_BUDGET

Every attempted HTTP request, including retry attempts and pagination, counts
against `max_calls`. The default hard limit is 20 and a dedicated budget error
is raised before an over-budget request is sent.

## RETRY_POLICY

Retries are finite and apply to 429, 500, 502, 503, 504, and timeouts. The
client honors numeric `Retry-After` values when present and otherwise uses a
bounded exponential delay. Normal 4xx client errors are not retried.

## PAGINATION

The primitive sends finite `page` and `per_page` values, stops on
`is_last_page`, and stops at configured `max_pages`.

## FIXTURES

Created small sanitized representative fixtures for Avalanche token
information, Avalanche flows, Avalanche DEX trades, and empty Solana flows.
Placeholder token identifiers were used in response examples; no headers,
keys, raw wallet data, or large responses were saved.

## UNIT_TESTS

`pytest -q`: 20 passed, 1 opt-in live test skipped. Default tests made zero
live API calls. Coverage includes configuration, headers, response decoding,
4xx handling, transient retries, Retry-After, timeout, budget exhaustion,
pagination, empty data, and secret redaction.

## LIVE_CONTRACT_TESTS

The opt-in live test remains disabled by default. A bounded manual validation
used four calls: Avalanche token-information, Avalanche flows, Avalanche DEX
trades, and Solana flows. Each request used a small page size and narrow
diagnostic window; no pagination or backfill was performed.

LIVE_CALLS_TASK004=4
TOKEN_INFORMATION_CONTRACT=PASS
FLOWS_CONTRACT=PASS
DEX_TRADES_CONTRACT=PASS
SOLANA_EMPTY_FLOW_CONTRACT=PASS

## RESOURCE_OBSERVATIONS

No long-running process, background watcher, database write, service change,
or production change was performed. Resource sampling remained lightweight.

## SECURITY_CHECK

CYRILLIC_SCAN=PASS
SECRET_SCAN=PASS
ENV_TRACKED=NO
The local `.env` remained ignored and no credential value or authorization
header was written to the repository.

## RISKS

The account plan and credit balance remain unknown. Endpoint-specific schemas
may evolve, and request limits may vary by plan. Persistence and broad
endpoint coverage are intentionally not implemented yet.

## UNRESOLVED_QUESTIONS

- Confirm the account plan and credit budget through a safe account review.
- Resolve whether Nansen exposes native GUNZ-chain data under another name.
- Add contract coverage for remaining approved endpoint families only after
  their current request schemas are reviewed.

## NEXT_RECOMMENDED_TASK

Task 005 should add a small fixture-backed normalization boundary for the
approved Avalanche MVP endpoints, without PostgreSQL writes or historical
backfill, after external review of this client foundation.

## TASK005_CORRECTION_ADDENDUM

External review found that the original Task 004 fixtures incorrectly modeled
token-information as a paginated list and used simplified field sets for
flows and DEX trades. Task 005 corrected those fixtures and added shape tests
against the current documented and live response contracts. The HTTP client
foundation remained largely valid; the corrected fixtures are now the contract
baseline for future normalization.
