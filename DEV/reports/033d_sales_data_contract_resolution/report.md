# Task 033D: OTG Sales Data Contract Resolution

## OBJECTIVE

Resolve production OTG sales timestamp, completed-sale, identity, and value semantics before analytics implementation. Evidence gathering found material unresolved semantics, so this task ends at the data-contract gate.

## STARTING_STATE

- Local `HEAD` and `origin/main`: `a3eb7b3a39f50764e670d1b994eb9879d9a36e22`.
- Branch: `main`; worktree was clean before this report.
- Baseline: 231 passed, 6 skipped.
- No application source changes were made.

## DATABASE_SAFETY

Production connection identity was `server_otg`; `transaction_read_only=on`. The session `TimeZone` was `America/Los_Angeles`. No production or staging DDL/DML was performed. No staging connection was opened. Nansen API calls: 0.

## PRODUCTION_SALES_SCHEMA

Live `public.sales` metadata:

| Column | PostgreSQL type | Nullable | Default | Contract relevance |
|---|---|---:|---|---|
| `tx_hash` | `character varying` | No | None | Primary key and writer conflict key |
| `seller` | `character varying` | No | None | Seller identifier |
| `buyer` | `character varying` | No | None | Buyer identifier |
| `price` | `numeric` | No | None | Parsed event amount; no currency metadata |
| `token_id` | `integer` | No | None | Item identifier |
| `serial_number` | `character varying` | Yes | None | Optional item metadata |
| `item_name` | `character varying` | Yes | None | Optional item metadata |
| `rarity` | `character varying` | Yes | None | Optional item metadata |
| `timestamp` | `timestamp without time zone` | No | None | Event-time candidate |

The only index is the unique primary-key B-tree on `tx_hash`. Constraints are primary key and not-null constraints; there is no status, currency, sale-finality, or timestamp-zone constraint. There are no `created_at`, `updated_at`, currency/token, or USD-value columns.

## SALES_WRITER_DISCOVERY

The production row writer found in the current OTG source tree is `parsers/parser_sales/db/save.py`. The source path is `parsers/parser_sales/parsers/marketplace.py` → `parsers/parser_sales/processors/transaction_processor.py` → `parsers/parser_sales/db/save.py`; block timestamps originate in `parsers/parser_sales/rpc/client.py`. `parsers/parser_sales/db/create_database.py` defines the legacy table shape. `scripts/old_new_rarity/migrate_sales_rarity.py` is a separate rarity migration, not a timestamp or price writer. The other `sales` insert search hit was a prepared sales-average analytics migration and does not write `public.sales` rows.

The row writer inserts `tx_hash`, seller, buyer, numeric price, token ID, optional item metadata, and timestamp. It uses `ON CONFLICT (tx_hash) DO NOTHING`. No writer-side `UPDATE` or delete repairs reorged/replaced sale rows.

## TIMESTAMP_LINEAGE

- Upstream source: GunzChain RPC block `timestamp`, supplied as Unix epoch seconds in block data.
- `transaction_processor.py` calls `datetime.fromtimestamp(tx['timestamp'])`, formats to second precision, and drops timezone information.
- `db/save.py` parses that string back to a naive Python datetime and inserts it into the naive PostgreSQL `timestamp` column.
- No `.astimezone(UTC)`, explicit UTC assignment, or source offset is used in this path.
- The current Windows host reports Pacific time, and the production database session reports `America/Los_Angeles`; neither proves the timezone active in historical writer processes.
- Repeated local wall-clock times during a DST fold cannot be mapped back to a unique source instant from this stored value alone.

## DATABASE_TIMEZONE

`PRODUCTION_DB_TIMEZONE=America/Los_Angeles` for the inspected production session. The sales writer calls `psycopg2.connect()` without a timezone option or a `SET TIME ZONE`; therefore `SALES_WRITER_SESSION_TIMEZONE=NOT_EXPLICITLY_SET` in application code. A session timezone does not restore information already discarded before insertion into a `timestamp without time zone` column.

## TIMESTAMP_STORAGE_SEMANTICS

`SALE_TIMESTAMP_COLUMN=public.sales.timestamp`; PostgreSQL type is `timestamp without time zone`. The source value is Unix seconds, but the writer converts it using process-local time and persists a naive wall-clock value. The historical process timezone is not recorded. The supported contract is therefore ambiguous.

## HISTORICAL_TIMEZONE_EVIDENCE

Read-only aggregate checks compared two candidate interpretations; they are diagnostic only and do not select a timezone. For raw stored timestamp bounds `2025-04-25 14:01:38` to `2026-09-24 04:50:50`:

| Candidate interpretation | Rows within canonical UTC period | UTC hours containing stored rows | Candidate earliest UTC | Candidate latest UTC |
|---|---:|---:|---|---|
| Treat naive values as UTC | 9,563,855 | 11,905 | 2025-04-25T14:01:38Z | 2026-09-20T23:59:40Z |
| Interpret naive values as `America/Los_Angeles` | 9,562,201 | 11,898 | 2025-04-25T21:01:38Z | 2026-09-20T23:59:30Z |

The different results show why an assumption changes coverage. Activity distribution is not proof of the historical process timezone. No authoritative historic runtime timezone or stored source offset was found.

## SALE_TIMEZONE_CONTRACT

`SALE_TIMEZONE_CONTRACT=AMBIGUOUS`

`SALE_TIMESTAMP_UTC_EXPRESSION=NOT ESTABLISHED`

Neither `timestamp AT TIME ZONE 'UTC'` nor `timestamp AT TIME ZONE 'America/Los_Angeles'` is authorized for canonical aggregation without historic writer-timezone evidence. `PRODUCTION_COMPLETED_SALES`, UTC min/max, and completed-sale hours are not determinable under the required contract gate.

## PRICE_COLUMN_LINEAGE

| Column | Upstream source | Transformation | Stored meaning / limitation |
|---|---|---|---|
| `price` | Parsed marketplace event data (`Trade` event, with a `Transfer` fallback) | Parsed integer event value is passed through `Web3.from_wei(..., 'ether')`, then converted to `int`, truncating any fractional part | Writer logs this as GUNZ, but production has no currency/token identity field and the event parser does not persist a currency identifier. It is not proven equivalent to the Nansen Avalanche `$GUN` token. |
| USD sale value | None in `public.sales` | None | No production USD field or expression exists. |

The parser source and market UI label source are `GUNZ` / `GUNZ`-named fields, but that naming does not establish token identity with the Avalanche `$GUN` contract. No transaction-level conversion to USD exists in the production row writer.

## PRICE_CONVERSION_CODE

The existing site data model can read `price_gun`, `gun_usd_price_at_sale`, and `price_usd_at_sale` from enriched market files. The September 19 export report describes `price_usd_at_sale = price_gun * gun_usd_price_at_sale`, with manual CoinMarketCap CSV sourcing and daily price resolution. The export/enrichment implementation was not present alongside that report for independent code-lineage verification. Daily resolution is not a reliable hourly sale-time USD value. Some UI formatting paths also fall back to `price_gun * current_gun_price`, which is current-price display logic, not historical sale-time USD.

## PRICE_CONSISTENCY_CHECKS

Read-only aggregate scan of `public.sales` found 9,585,283 rows; `price` was non-null for all rows, 508 rows had zero price, 9,584,775 were positive, and none were negative. `tx_hash` distinct count equals row count by the unique primary key. These aggregate checks do not determine which zero-price rows represent sales or identify the currency of positive values.

## SALE_GUN_VALUE_CONTRACT

`SALE_GUN_VALUE_EXPRESSION=NOT_AVAILABLE` for the specific Avalanche `$GUN` measure. The stored `price` is application-labeled GUNZ after whole-unit truncation, but no verified bridge/token identity maps that denomination to the Nansen token. It must not be used as Avalanche `$GUN` volume.

## SALE_USD_VALUE_CONTRACT

`SALE_USD_VALUE_EXPRESSION=NOT_RELIABLY_AVAILABLE` for hourly historical analysis. Production has no USD column. The site enrichment report describes daily manual-price joins, and UI fallbacks can use the current GUN price; neither supplies a verified hourly historical USD amount for every sale.

## COMPLETED_SALE_FILTER

No exact production completed-sale predicate is available. The parser recognizes both `Trade` and generic `Transfer` logs. When a transfer record has no parsed trade price, it sets price to zero and can continue through validation and insertion. The table stores no event type, status, receipt finality, or cancellation/reorg state. Therefore stored rows cannot be filtered unambiguously into completed paid sales. Failed/pending/cancelled/replaced/reorged status is not represented; insert-only behavior does not reconcile a prior row after a chain reorg.

## SALE_IDENTITY_CONTRACT

`tx_hash` is the proven database uniqueness and writer deduplication key (`PRIMARY KEY`; `ON CONFLICT (tx_hash) DO NOTHING`). This proves unique stored transaction keys, not necessarily one line-item sale identity per row: the parser groups logs by transaction and extracts one trade-info structure. Stored transaction count is 9,585,283; duplicate `tx_hash` count is zero by constraint. Completed-sale identity count is not determinable because the completed-sale predicate is unresolved.

## CANONICAL_PERIOD_COVERAGE

Exact completed-sale count and UTC coverage are not reported because no timestamp expression or completed-sale filter is established. Candidate row/hour aggregates in `HISTORICAL_TIMEZONE_EVIDENCE` include all stored rows, including the zero-price transfer fallback, and must not be treated as completed sales.

## EXISTING_SITE_SEMANTICS

- `EXISTING_SITE_GUN_LABEL_SOURCE=price_gun` in the market-file data contract; the overview sums this field and labels it GUN. Its lineage to production `price` is not proven in the current live table contract, and the production parser calls its amount GUNZ.
- `EXISTING_SITE_USD_LABEL_SOURCE=price_usd_at_sale` when historical enriched values are present; the export report documents daily manual CoinMarketCap-derived values. Some display paths fall back to `price_gun` times current token price. This is not a uniform hourly historical USD contract.

## EVIDENCE_HIERARCHY

1. Live schema proves the naive timestamp type, transaction primary key, available columns, and absence of currency/status/USD metadata.
2. Current parser code proves epoch-to-local conversion, event parsing, price conversion, insert behavior, and lack of explicit timezone initialization.
3. Local export documentation describes daily manual USD enrichment; the original enrichment implementation was not found for validation.
4. Current site code proves display labels and current-price fallback behavior.
5. Aggregate checks describe row counts and price sign/zero distribution only; they do not prove timezone, completed-sale status, or denomination.

## RESOLVED_DATA_CONTRACT

```text
SALE_TIMESTAMP_COLUMN=public.sales.timestamp
SALE_TIMESTAMP_POSTGRES_TYPE=timestamp without time zone
SALE_TIMEZONE_CONTRACT=AMBIGUOUS
SALE_TIMESTAMP_UTC_EXPRESSION=NOT ESTABLISHED

SALE_COMPLETE_FILTER=NOT ESTABLISHED; Trade and Transfer-derived rows are both insertable
SALE_DEDUPLICATION_KEY=tx_hash (stored transaction key; line-item completeness not proven)

SALE_GUN_VALUE_EXPRESSION=NOT_AVAILABLE for Avalanche $GUN
SALE_GUN_VALUE_CONFIDENCE=NOT_AVAILABLE

SALE_USD_VALUE_EXPRESSION=NOT_RELIABLY_AVAILABLE for hourly historical analysis
SALE_USD_VALUE_CONFIDENCE=NOT_RELIABLY_AVAILABLE

BUYER_ID_AVAILABLE=YES
SELLER_ID_AVAILABLE=YES
ITEM_ID_AVAILABLE=YES (token_id)
```

## UNRESOLVED_ITEMS

`TASK_033D_STATUS=DATA_CONTRACT_BLOCKER`. Historical writer timezone cannot be proven from current code, schema, or database session settings. The current schema also cannot distinguish generic transfer records from completed market sales. Production `price` is application-labeled GUNZ but lacks persisted currency identity; it is not equivalent by evidence to the Avalanche Nansen `$GUN` measure. No trustworthy hourly USD expression exists.

## DEFAULT_TESTS

`pytest -q`: 231 passed, 6 skipped. No Nansen API calls were made.

## PRODUCTION_SAFETY

Connection was explicitly read-only and verified as `server_otg` / `transaction_read_only=on`. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

No staging connection was opened. Staging DDL=0, DML=0.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033D=0`.

## SECURITY_CHECK

The report contains no credentials, addresses, transaction hashes, individual sale data, raw database rows, or source patches. `.env` is not tracked by the Nansen repository.

## CYRILLIC_CHECK

PASS for this English-only report.

## FILES_CHANGED

- `DEV/reports/033d_sales_data_contract_resolution/report.md`

## NEXT_RECOMMENDED_TASK

Establish the historical process timezone from authoritative deployment/runtime records and preserve event timestamps with an explicit zone in any future source. Separately persist an event discriminator/finality contract and token/currency identity for sales. If the site enrichment remains the intended market source, locate and review its actual generation code and source files before defining hourly USD semantics. Reauthorize analytics implementation only after those contracts are explicit.
