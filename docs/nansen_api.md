# Nansen API reconnaissance

## Documented

Official documentation reviewed on 2026-09-23 states that API requests use
POST with JSON bodies and an `apikey` header. The current rate-limit reference
states 20 requests per second and 300 requests per minute per API key. These
are not embedded as universal client limits. The account plan was not queried.
Common errors include
400, 401, 402, 403, 404, 422, 429, 500, and 504.

The documented response pagination shape uses `page`, `per_page`, and an
`is_last_page` field. Date ranges are inclusive. Smart Money historical
holdings documents a four-year rolling window, daily end-of-day UTC snapshots,
and delayed availability for the current day. This does not establish the
historical depth of every endpoint.

Documented Pro credit costs are generally 1 for TGM token-information, flows,
who-bought-sold, DEX trades, and transfers; TGM holders is 5. The current
endpoint overview is the source of per-endpoint credit values; account plan and
remaining balance were not queried.

Official references:

- https://docs.nansen.ai/getting-started/authentication
- https://docs.nansen.ai/getting-started/rate-limits
- https://docs.nansen.ai/getting-started/credits
- https://docs.nansen.ai/getting-started/error-handling
- https://docs.nansen.ai/api/overview
- https://docs.nansen.ai/api/token-god-mode/flows
- https://docs.nansen.ai/guides/data-methodology-and-technical-reference

## Endpoint matrix

| Endpoint | Method | Documented request | Historical/depth note | Live result |
|---|---|---|---|---|
| `/api/v1/tgm/token-information` | POST | chain, token_address, timeframe | 5m/1h/6h/12h/1d/7d timeframe; no long-range depth claim | 200 on Avalanche and Solana |
| `/api/v1/tgm/flows` | POST | chain, token_address, date, label, pagination, filters | Hourly flow snapshots; endpoint-specific maximum not stated | 200 with 2 records on Avalanche; 200 empty on Solana probe |
| `/api/v1/tgm/dex-trades` | POST | chain, token_address, date, pagination, filters | Date-range trade records; maximum not stated | 200 on both chains |
| `/api/v1/tgm/who-bought-sold` | POST | chain, token_address, buy_or_sell, date, pagination, filters | Date-range aggregate address results; maximum not stated | 200 on both chains |
| `/api/v1/tgm/transfers` | POST | chain, token_address, pagination and filters | Transfer coverage documented; exact historical limit not stated | 200 on both chains |
| `/api/v1/tgm/holders` | POST | chain, token_address, label_type, pagination, filters | Exact historical request/depth contract needs verification | 200 on both chains |
| `/api/v1/smart-money/historical-holdings` | POST | chains, date_range, filters, pagination | Four-year rolling window; daily UTC snapshots | Not live-probed |
| `/api/v1/smart-money/dex-trades` | POST | Smart Money trade query | Documentation describes last 24 hours | Not live-probed |
| `/api/v1/tgm/token-ohlcv` | POST | Listed in endpoint overview | Request schema/depth not sufficiently verified | Not live-probed |

## Live verified

Exactly 12 small diagnostic requests were made, six per chain, with
`per_page=2` or the smallest documented timeframe. No raw response, header, or
credential was saved. A sanitized shape fixture is at
`tests/fixtures/nansen/phase0b_endpoint_shapes.json`.

The live probe verified that the API key authenticates and that Nansen accepts
both configured token identities for token-information. It also verified
usable trade, holder, transfer, and buyer/seller responses on both chains.

## Client foundation

The client uses the documented base URL, configurable timeout, finite retries,
a hard per-run request budget, and finite pagination. Default unit tests use
mocks and fixtures only. Live tests are explicitly opt-in with
`NANSEN_RUN_LIVE_TESTS=1`.

The client implements `token_information`, `flows`, and `dex_trades`. The
Task 014 orchestration layer uses these endpoint families through bounded
pagination, but no live calls were made in that task. Persistence, backfill,
and business-specific event analysis remain separate concerns.

The normalization boundary is separate from the raw client. It produces
immutable token-information, flow, and DEX-trade models. Required malformed
fields fail explicitly; unknown extra fields are tolerated; empty flow data is
valid. Timestamps become timezone-aware UTC values and numeric analytical
values become Decimal values. Pagination now raises if its page limit is
reached while `is_last_page` is false, so incomplete data cannot look complete.

The corrected fixture representation is: token-information has an object in
`data` with token details and spot metrics; flows and DEX trades have list
`data` plus `pagination`. Live verification confirmed these shapes for the
current Avalanche diagnostic calls. The fixtures are sanitized contract
representations, not raw response archives.

Task 014 uses date payloads with UTC `from` and `to` values, deterministic
ascending ordering fields, finite pagination, and per-run API-attempt counts.
This orchestration behavior is fixture-verified only; real `$GUN` request
behavior remains unverified in Task 014.

Task 014R rechecked the current official endpoint documentation. The official
historical request form is an `order_by` array, represented in the client as:

- flows: `[{'field': 'date', 'direction': 'ASC'}]`;
- DEX trades: `[{'field': 'block_timestamp', 'direction': 'ASC'}]`.

These request shapes are OFFICIAL-DOC VERIFIED and FIXTURE VERIFIED, but not
LIVE VERIFIED by Task 014R. No standalone `order` field is sent.

Task 015 live-verified the Avalanche request transport and sanitized response
structures with exactly one attempt per endpoint. Token-information returned
an object and normalized successfully. Flows returned a non-empty paginated
first page with `is_complete` and `bucket_end` fields, but the current flow
normalizer initially rejected the observed page because the inflow and outflow
count fields were delivered as finite, mathematically integral JSON floats.
Task 016 added a field-specific exact conversion for those count fields while
keeping fractional, non-finite, boolean, negative, and malformed values
invalid. The observed records also contained boolean `is_complete`, timestamp
`bucket_end`, and nullable CEX/DEX count fields. The sanitized fixture mirrors
those types without retaining live values. Completeness is therefore not
accepted as an ingestion contract. DEX trades returned a non-empty paginated
first page and normalized successfully. No live response body was retained,
and these observations do not establish complete historical ingestion
behavior.

Task 016 evidence classification:

- OFFICIAL-DOC VERIFIED: flow count field names and their analytical count
  semantics are documented at
  https://docs.nansen.ai/api/token-god-mode/flows.
- LIVE VERIFIED: the diagnostic page used finite integral JSON floats for
  `total_inflows_count` and `total_outflows_count`, integer `holders_count`,
  boolean `is_complete`, timezone-bearing timestamps, and nullable optional
  CEX/DEX count fields.
- FIXTURE VERIFIED: the sanitized flow fixture reproduces those field types
  and the repaired normalizer converts only exact integral count values.

Task 017 attempted the first bounded multi-page validation for the same
historical day. The paginator reached a final page after three no-retry
requests, but normalization of the complete collected set failed on a later
record at `total_inflows_count`. Task 017R diagnosed the later field as a
finite fractional JSON float. The normalizer does not round or truncate it,
so complete-window ingestion remains NOT VERIFIED and no live data was
persisted.

Task 017M changes only `total_inflows_count` and `total_outflows_count` to
required Decimal model values sourced from JSON numbers. Finite integer and
fractional numeric values are preserved through `Decimal(str(value))`; strings,
booleans, null, and non-finite values remain invalid. `holders_count` remains
an integer. Optional CEX/DEX count fields remain optional integers and have
only been live-observed as null for the tested Smart Money label. Task 017M
made no live API calls, so complete-window normalization still requires a
separately authorized live revalidation.

Task 017V completed that revalidation for exactly the 2026-09-20 Avalanche
`smart_money` window. Three pages reached the final page, all collected rows
normalized with Decimal total count metrics, all observed buckets were marked
complete, and dates were non-decreasing and within the requested bounds. A
fractional inflow count was observed and preserved as Decimal; outflow count
values in this window were integral. Optional CEX/DEX breakdowns were null.
No live data was persisted. This proves behavior only for this one window; it
does not establish broader history, other dates or labels, Solana complete
windows, production ingestion, or backfill behavior.

Task 018 subsequently attempted the first live persistence run for that same
bounded stream/window. Its only API request timed out before a page was
returned. The audit records failure, and no rows or checkpoint were committed.
This was not a successful live ingestion and adds no new source-data evidence.

Task 018R separately completed ingestion of the exact bounded
2026-09-20 Avalanche `$GUN` `smart_money` flow window into staging. Three
pages were fetched and 23 records normalized and persisted; two stored inflow
count values remain fractional NUMERIC values. The successful audit and
checkpoint were verified together, while the original Task 018 failed audit
was retained. This is evidence for this single window only, not a general
historical-coverage claim.

Task 019 replayed the same exact bounded window once. It again returned 23
records; persisted row count and sorted flow-key-set digest stayed stable,
with no duplicate keys. This demonstrates live idempotency for this one
retained window only. It does not establish broad historical idempotency or
revision reconciliation behavior.

Task 020 verified non-empty Nansen flow history for the exact bounded window
2025-04-25T00:00:00Z through 2025-05-24T23:59:59Z: 29 normalized records
were returned on one final page and persisted. They span 29 distinct dates;
this does not claim a record for every day or establish maximum historical
depth. The later September checkpoint was not regressed. No broader backfill
was performed.

## Not verified

The account plan, exact credit balance, endpoint-specific maximum historical
depth, token OHLCV request schema, Smart Money historical results for `$GUN`,
and Nansen coverage of the native GUNZ chain were not verified. No backfill or
large pagination was attempted.

Task 021 rechecked the current official Flows contract and made two direct,
read-only live probes. Nansen documents hourly snapshots for requested ranges
of seven days or less and daily snapshots for longer ranges. It defines `date`
as an inclusive bucket start, `bucket_end` as exclusive, and `is_complete` as
request-window coverage rather than finality. The same represented calendar
day returned 23 one-hour observations in its one-day probe versus one daily
bucket in the retained 30-day result; their timestamp sets differed. A
calendar date absent from the wider result returned 23 hourly observations
when queried alone. Both responses included one warning; its text was not
retained, and no range/truncation classification was inferred from it. See
the [official Flows documentation](https://docs.nansen.ai/api/token-god-mode/flows).

The observed granularity is range-dependent. A same-date/different-bucket-end
collision was not observed in the represented-day comparison, but identity
collision risk remains inconclusive because the tested narrow page had no
midnight record. Broader backfill remains unsafe until bucket identity is
resolved. A read-only check confirmed Task 020's 29 rows, the recent 23 rows,
and the September checkpoint were unchanged by these probes.

Because the official contract changes resolution with request-range width,
persisted flow identity includes both `date` (bucket start) and `bucket_end`
(exclusive end), in addition to chain, canonical token, and flow label. Null
or non-positive bucket intervals may be normalized for diagnosis but are
rejected before persistence. Migration 003 and re-key verification completed
on staging; production was not changed. This design change does not authorize
a broader backfill.

## Task 023 warning boundary

The current official Flows contract defines optional top-level `warnings` as
an array of strings. It documents a warning entry when non-exchange labels
have null CEX/DEX breakdown fields. It does not define null as a supported
warnings container, warning wording, truncation warnings, partial-result
warnings, aggregation warnings, or request-range warning semantics. The same
contract documents hourly snapshots for ranges of seven days or less, daily
snapshots for longer ranges, and `is_complete=false` for upper-cutoff bucket
truncation or a live bucket (plus lower-cutoff truncation on Hyperliquid).

The client retains warning values with each fetched page in memory. Historical
ingestion stores only page number, warning count, and sanitized categories in
`nansen.ingestion_runs.source_warnings`. Unknown warnings fail before data
persistence. Task 023's single authorized live validation returned one warning
that the strict classifier did not recognize. Its sanitized category was
`UNKNOWN`; no raw warning text was retained. Broader backfill remains blocked
pending warning-contract clarification.

Task 023F resolves the warning policy using the exact SHA-256 fingerprint recorded in its report. Recognition is limited to TGM Flows with the `smart_money` label, and normalization must show all four optional CEX/DEX breakdown counts as null on every returned record. The raw warning text is never retained. Any wording change or additional unrecognized warning is `UNKNOWN` and fails closed. The one post-change validation request matched the fingerprint and the documented breakdown structure.

Task 024 completed one Avalanche `smart_money` Flows request for 2025-04-25T00:00:00Z through 2025-05-01T23:59:59Z. The seven-day request returned and retained 167 hourly buckets on one final page. Its single source warning passed the exact fingerprint and normalized null-breakdown guard; the successful run audit stores only the sanitized category summary. The six existing daily buckets remained present with unchanged identities. The high-water checkpoint remained at 2026-09-20T23:59:59Z. This is one bounded pilot and does not establish complete historical coverage.

Task 025 rechecked the current [official Flows documentation](https://docs.nansen.ai/api/token-god-mode/flows) on 2026-09-23. It defines bucket `date` as an inclusive start, `bucket_end` as exclusive, and request `date.to` as an inclusive cutoff. It says ranges of seven days or less use hourly snapshots. For non-Hyperliquid chains it says the lower cutoff is aligned to the bucket start and the full first bucket is returned; it does not describe lower-bound omission. In one shifted Avalanche `smart_money` request, the previously absent 2025-04-25T00:00Z bucket appeared while the new request's 2025-04-24T23:00Z lower-bound bucket was absent. The evidence conflicts with the documented first-bucket behavior for this tested response. Treat naive non-overlapping weekly requests as unsafe pending a boundary-aware plan and further review; this probe does not establish behavior for other windows, chains, or labels.
