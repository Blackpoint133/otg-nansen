# Task 015 Live Avalanche Contract Probe

## OBJECTIVE

Perform exactly one live request attempt for each of the three authorized
Avalanche `$GUN` endpoint families, validate only sanitized structure, and make
no database connection or persistence operation.

## STARTING_STATE

- Starting main: `b1094f697710481ee20ca747421859e821c2de9b`
- Working tree was clean.
- No PostgreSQL repository was instantiated.

## OFFICIAL_TOKEN_IDENTITY

The current official GUNZ website lists the Avalanche C-Chain contract as
`0x26deBD39D5eD069770406FCa10A0E4f8d2c743eB`, matching
`TOKEN_IDENTITIES["avalanche"]`.

Source: https://gunbygunz.com/gun/

## OFFICIAL_REQUEST_CONTRACT_RECHECK

Current official Nansen documentation confirms the array sorting form:

- flows: `[{'field': 'date', 'direction': 'ASC'}]`;
- DEX trades: `[{'field': 'block_timestamp', 'direction': 'ASC'}]`.

Sources:

- https://docs.nansen.ai/api/token-god-mode/flows
- https://docs.nansen.ai/api/token-god-mode/dex-trades

No standalone `order` field was used.

## LIVE_CALL_BUDGET

The client was configured with `max_calls=3`, `max_retries=0`, `page_size=2`,
and `max_pages=1`. Exactly three request attempts were observed.

## PROBE_WINDOW

Historical UTC window: `2026-09-20T00:00:00Z` through
`2026-09-20T23:59:59Z`.

## TOKEN_INFORMATION_PROBE

- HTTP: 2xx
- data type: object
- top-level keys: `data`
- data keys: `contract_address`, `logo`, `name`, `spot_metrics`, `symbol`,
  `token_details`
- normalization: PASS

No raw response values or headers were retained.

## FLOWS_PROBE

- HTTP: 2xx
- first-page record count: 2
- `pagination.is_last_page`: false
- record keys: `bucket_end`, `date`, `holders_count`, `is_complete`,
  `price_usd`, `token_amount`, `total_inflows_cex`,
  `total_inflows_count`, `total_inflows_dex`, `total_outflows_cex`,
  `total_outflows_count`, `total_outflows_dex`, `value_usd`
- `is_complete` present: yes
- `bucket_end` present: yes
- observed completeness values: `[true, true]`
- normalization: FAIL (`NormalizationError`)

The page was structurally accepted but was not accepted as a normalized
ingestion page. No retry or second request was made.

## FLOW_COMPLETENESS_OBSERVATION

The observed first page contained `is_complete=true` for both rows. This is
only a structural observation for this page; complete historical-window
behavior is not live-verified.

## DEX_TRADES_PROBE

- HTTP: 2xx
- first-page record count: 2
- `pagination.is_last_page`: false
- record keys: `action`, `block_timestamp`, `estimated_swap_price_usd`,
  `estimated_value_usd`, `token_address`, `token_amount`, `token_name`,
  `traded_token_address`, `traded_token_amount`, `traded_token_name`,
  `trader_address`, `trader_address_label`, `transaction_hash`
- normalization: PASS

No wallet addresses, transaction hashes, amounts, prices, or raw rows were
recorded in this report.

## SORTING_REQUEST_VERIFICATION

- flows order_by sent: `[{'field': 'date', 'direction': 'ASC'}]`
- DEX trades order_by sent: `[{'field': 'block_timestamp', 'direction': 'ASC'}]`
- legacy standalone order field sent: no

## NORMALIZATION_RESULTS

Token-information and DEX trades normalized successfully. The live flows page
failed the current strict normalization boundary. This is recorded as an
endpoint-level contract/normalization mismatch, not worked around with an
additional request.

## LIVE_RESULT_CLASSIFICATION

- token-information: PASS
- flows: FAIL (structural response accepted; normalization failed)
- DEX trades: PASS
- complete historical ingestion: NOT VERIFIED

## DATABASE_ISOLATION

No PostgreSQL connection was opened. No live data, audit run, checkpoint, or
other database state was persisted.

## DEFAULT_TESTS

`pytest -q`: 106 passed, 4 skipped. Default live calls and PostgreSQL
connections were zero.

## LIVE_API_CALL_COUNT

`LIVE_API_CALLS_TASK015=3`. No retries were enabled.

## SECURITY_CHECK

The API key and headers were never printed or persisted. No database secrets,
raw response bodies, wallet addresses, transaction hashes, or `.env` values
were committed. `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

Repository-authored text scan: PASS. All authored content is English only.

## FILES_CHANGED

- `docs/nansen_api.md`
- this report

## RISKS

The flows endpoint returned a structurally valid non-final page but did not
pass the current strict normalizer. No ingestion should use flows until the
normalization mismatch is reviewed. No complete historical behavior was
established because pagination was intentionally limited to one page.

## NEXT_RECOMMENDED_TASK

Review the sanitized live flows mismatch and correct the normalization contract
only with evidence from the observed official response shape. Do not start
real ingestion or broaden the live request budget.

## TASK 016 ADDENDUM

Task 016 used one additional bounded Avalanche flows request because the Task
015 report retained only the exception class, not its field-level message. The
safe diagnostic identified `total_inflows_count` as a finite, mathematically
integral JSON float while the normalizer required an integer. The companion
`total_outflows_count` field had the same observed wire type. Optional CEX/DEX
count fields were null.

The normalizer was repaired narrowly with a dedicated exact integer-like
conversion for these two count fields. It accepts finite integral numeric
values and rejects fractional, non-finite, boolean, negative, and malformed
values. The sanitized fixture and regression tests reproduce the observed type
shape. The diagnostic response object was not retained after the original
probe process, so post-repair normalization was proven against the sanitized
observed shape rather than by issuing another live request. No live data was
persisted.
