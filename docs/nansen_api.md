# Nansen API reconnaissance

## Documented

Official documentation reviewed on 2026-09-21 states that API requests use
POST with JSON bodies and an `apikey` header. Current documented limits are 20
requests per second and 300 requests per minute per key. Common errors include
400, 401, 402, 403, 404, 422, 429, 500, and 504.

The documented response pagination shape uses `page`, `per_page`, and an
`is_last_page` field. Date ranges are inclusive. Smart Money historical
holdings documents a four-year rolling window, daily end-of-day UTC snapshots,
and delayed availability for the current day. This does not establish the
historical depth of every endpoint.

Documented Pro credit costs are generally 1 for TGM token-information, flows,
who-bought-sold, DEX trades, and transfers; TGM holders is 5. Free-plan costs
are documented as 10x those costs. Account plan and remaining balance were not
queried.

Official references:

- https://docs.nansen.ai/getting-started/authentication
- https://docs.nansen.ai/getting-started/rate-limits
- https://docs.nansen.ai/getting-started/credits
- https://docs.nansen.ai/getting-started/error-handling
- https://docs.nansen.ai/api/overview
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

## Not verified

The account plan, exact credit balance, endpoint-specific maximum historical
depth, token OHLCV request schema, Smart Money historical results for `$GUN`,
and Nansen coverage of the native GUNZ chain were not verified. No backfill or
large pagination was attempted.
