# Task 033E: On-Chain Sales Contract Resolution

## OBJECTIVE

Resolve the historical OTG sales timestamp, event classification, and GUN denomination contracts using the parser lineage, current official GUNZ material, and bounded read-only chain evidence. This remains contract resolution only; no analytics tables or analytical conclusions were produced.

`TASK_033E_STATUS=DATA_CONTRACT_BLOCKER`: the UTC timestamp mapping and complete paid-sale predicate remain unresolved; the official 1:1 bridge ratio was also not explicit in the reviewed official material.

## STARTING_STATE

- Repository `HEAD` and `origin/main`: `590f73950712fa68e35a9a89f63d6f57eadeb2cb`; branch `main`; worktree clean.
- Task 033D's schema and writer findings were rechecked. The production sales table has a naive timestamp, a transaction-hash primary key, no event/status column, and no currency or USD column.
- Baseline tests: 231 passed, 6 skipped.

## DATABASE_SAFETY

The only database connection was to `server_otg`. The session verified `current_database=server_otg` and `transaction_read_only=on`; the connection also set PostgreSQL's default transaction mode to read-only. Queries were SELECT-only and rolled back before closing. No staging connection was made. Production DDL=0, DML=0, changed=NO; staging DDL=0, DML=0.

## LOCAL_PARSER_LINEAGE

Rechecked `parsers/parser_sales/rpc/client.py`, `parsers/parser_sales/parsers/marketplace.py`, `parsers/parser_sales/parsers/event.py`, `parsers/parser_sales/processors/transaction_processor.py`, `parsers/parser_sales/db/save.py`, `parsers/parser_sales/db/create_database.py`, and the worker call sites.

- The source timestamp is the containing GUNZ block's Unix `timestamp` in seconds.
- The worker fetches logs filtered to the configured marketplace contract and groups them by transaction hash.
- `MarketplaceParser.EVENTS` maps two topic-0 signatures to `Trade` and the standard `Transfer` topic to `Transfer`. For `Trade`, the final 32-byte data word is parsed as an integer, converted with `Web3.from_wei(value, 'ether')`, passed through `float`, then truncated with `int`.
- A `Transfer` can supply seller, buyer, and token ID. If no Trade price was found, the parser sets the price to zero and returns a record. A Transfer data word can also be attempted as a price fallback.
- `transaction_processor.py` calls `datetime.fromtimestamp(tx['timestamp'])`, formats to second precision, and discards zone information. `db/save.py` reparses that naive string and inserts it into `timestamp TIMESTAMP`.
- `tx_hash` is the database primary key. The insert uses `ON CONFLICT (tx_hash) DO NOTHING`; no update repairs changed/reorged rows.
- The parser source's transaction processor does not establish a persisted receipt-status or event-kind field.

Relevant event signatures from parser source:

- Trade: `dc1da0bf7038060851086ae316261313bb58ae31a3c217e4ba5f5baf0c7756b8`
- Additional Trade topic accepted by parser: `ac10bdb84346971f200f2a4715fc39eedb2e41d52c712c3dccb42990cd45b8ce`
- Transfer: `ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- Marketplace contract configured in the current worker source: `0x4c9B291874fB5363E3a46cD3BF4a352ffA26A124`.

## OFFICIAL_GUNZ_TOKEN_EVIDENCE

Current official sources establish that GUN is the native GUNZ coin, uses symbol GUN with 18 decimals, and is used for OTG/GUNZ marketplace trades. The official GUN page lists the official bridge and a GUNZ/Avalanche contract pair, including Avalanche C-Chain contract `0x26deBD39D5eD069770406FCa10A0E4f8d2c743eB`. The official bridge UI identifies cross-chain bridging, but the official material reviewed does not explicitly state a 1:1 bridge ratio or specify that one GUNZ native unit is redeemable for exactly one Avalanche token unit.

Sources: [official GUN page](https://www.gunbygunz.com/gun/), [official GUNZ documentation](https://gunbygunz.com/documentation/), [official GUNZ bridge](https://bridge.gunzchain.io/), and [official GUN token whitepaper](https://storage.gunbygunz.com/GUNTokenWhitepaper.pdf). The official pages identify the marketplace use and bridge endpoints, but the whitepaper and bridge material reviewed did not explicitly establish a 1:1 ratio.

## OFFICIAL_BRIDGE_EVIDENCE

- Official native token symbol: GUN.
- Official marketplace currency: GUN; official material says GUN is used to trade and buy items and powers OTG trades.
- Official Avalanche C-Chain address listed in the bridge section: `0x26deBD39D5eD069770406FCa10A0E4f8d2c743eB`.
- Bridge relationship: official cross-chain bridge and corresponding network addresses are identified.
- Bridge ratio: `NOT_EXPLICITLY_DOCUMENTED` in the official sources reviewed. No 1:1 equivalence is claimed here.

## RPC_SAFETY

The parser's official GUNZ RPC endpoint returned HTTP 403 for read-only calls. The alternative GUNZ RPC endpoint linked by official documentation responded to `eth_chainId` with 43419, matching the official chain ID. All subsequent calls were read-only JSON-RPC receipt and block lookups. No signing or state-changing method was used. RPC method objects counted, including unsuccessful attempts and chain-ID probes: 1,814 total (610 to the parser-configured endpoint and 1,204 to the official alternate endpoint). This is within the 2,000-call cap.

## MARKETPLACE_EVENT_SIGNATURES

The signatures above are proven as the event topics explicitly recognized by the checked-in parser. Receipt logs were compared only when their emitting address matched the parser's configured marketplace contract. The event signatures establish parser-recognized event types; they do not create a stored event discriminator in `public.sales`.

## ZERO_PRICE_POPULATION

Read-only recheck: `ZERO_PRICE_ROWS=508`.

## ZERO_PRICE_ONCHAIN_CLASSIFICATION

All 508 zero-price row receipts resolved. All 508 contained a parser-mapped Trade event from the configured marketplace contract; all had a positive raw Trade data word. None was Transfer-fallback-only, both, neither, or unresolved. Thus:

```text
ZERO_PRICE_WITH_TRADE_EVENT=508
ZERO_PRICE_WITH_TRANSFER_FALLBACK_ONLY=0
ZERO_PRICE_WITH_BOTH=0
ZERO_PRICE_WITH_NEITHER=0
ZERO_PRICE_RPC_UNRESOLVED=0
ZERO_PRICE_TRADE_RAW_VALUE_POSITIVE_COUNT=508
ZERO_PRICE_TRADE_RAW_VALUE_ZERO_COUNT=0
ZERO_PRICE_NONSALE_CLASSIFICATION=DISPROVEN
```

The source conversion truncates whole-token values after converting from wei. Positive raw Trade values can therefore be stored as zero after integer conversion. The receipt aggregates establish that every zero-price row has a Trade event and at least one positive raw Trade word; they do not reveal or reproduce the parser's selected word for each transaction, so exact per-row truncation amounts are not claimed. This proves `price > 0` would omit Trade-event transactions and is not a complete paid-Trade filter. A Transfer-only zero-price interpretation is contradicted by the receipts.

## POSITIVE_PRICE_SAMPLE_DESIGN

Selected five positive rows per represented calendar month by stable `md5(tx_hash)` ordering across 18 months, plus five nearest positive rows around each of two DST-transition date anchors. After de-duplication the sample contained 100 transactions. Hashes were held in memory only and are absent from the report.

## POSITIVE_PRICE_ONCHAIN_VALIDATION

All 100 sample receipts resolved and contained a parser-mapped Trade event from the configured marketplace contract. The decoded raw event amount transformed using the parser's actual `from_wei` / float / integer-truncation sequence matched the stored integer for all 100. No sampled transaction was unresolved.

```text
POSITIVE_SAMPLE_ROWS=100
POSITIVE_SAMPLE_WITH_TRADE_EVENT=100
POSITIVE_SAMPLE_PRICE_TRANSFORM_MATCH=100
POSITIVE_SAMPLE_RPC_UNRESOLVED=0
```

This deterministic stratified sample supports the transformation but is not an exhaustive audit of every positive row.

## PRICE_TOKEN_IDENTITY_DECISION

Parser and official documentation establish that the decoded Trade amount is denominated in the native GUN coin on GUNZ and that GUN is the OTG marketplace currency. The official site also lists a bridged Avalanche representation and its contract. A 1:1 relationship is not explicit in reviewed official material, so the requested cross-chain unit equivalence is not proven. This report does not describe `public.sales.price` as an Avalanche ERC-20 transfer amount.

## COMPLETED_SALE_FILTER_DECISION

`price > 0` is disproven as a complete Trade filter by 508 zero-price rows with positive raw Trade event values. `public.sales` contains no event type, completion/finality, status, cancellation, or reorg field. Receipts in the investigated populations contained Trade logs, but the current table does not retain that event classification. A complete historical sales predicate over the table alone is therefore not established. The transaction hash primary key proves stored transaction-key uniqueness, not line-item identity or finality.

```text
SALE_COMPLETE_FILTER=NOT ESTABLISHED; price > 0 omits observed Trade events
SALE_COMPLETE_FILTER_CONFIDENCE=AMBIGUOUS
SALE_DEDUPLICATION_KEY=tx_hash (transaction-level database primary key)
```

## ONCHAIN_TIMESTAMP_COMPARISON

For each of the 608 inspected transactions (508 zero-price rows plus 100 positive sample rows), the receipt's containing block timestamp was fetched and compared in memory with the stored naive timestamp. The resulting observed offset is `stored naive wall-clock minus exact block UTC`, grouped by stored calendar month:

| Stored month | Observed offset | Inspected rows |
|---|---:|---:|
| 2025-04 | UTC+05:00 | 8 |
| 2025-05 | UTC+05:00 | 5 |
| 2025-06 | UTC+05:00 | 5 |
| 2025-07 | UTC+05:00 | 510 |
| 2025-08 | UTC+05:00 | 5 |
| 2025-09 | UTC+05:00 | 5 |
| 2025-10 | UTC+05:00 | 5 |
| 2025-11 | UTC+05:00 | 10 |
| 2025-12 | UTC+05:00 | 5 |
| 2026-01 | UTC+05:00 | 5 |
| 2026-02 | UTC+05:00 | 4 |
| 2026-02 | UTC-08:00 | 1 |
| 2026-03 | UTC-08:00 | 5 |
| 2026-03 | UTC-07:00 | 5 |
| 2026-04 | UTC-07:00 | 5 |
| 2026-05 | UTC-07:00 | 5 |
| 2026-06 | UTC-07:00 | 5 |
| 2026-07 | UTC-07:00 | 5 |
| 2026-08 | UTC-07:00 | 5 |
| 2026-09 | UTC-07:00 | 5 |

These are observed offsets, not proof of a named runtime timezone. They show materially different historical wall-clock behavior: UTC+05:00 in sampled 2025 through January 2026, mixed offsets in February/March 2026, and Pacific seasonal offsets in later sampled months. A single timezone expression cannot safely reconstruct all rows from `timestamp` alone.

## WINDOWS_RUNTIME_TIMEZONE_EVIDENCE

- Current Windows zone: `Pacific Standard Time`; dynamic daylight changes enabled.
- Parser source, worker code, orchestrator launch code, and searched parser scripts contain no explicit `TZ` / `tzset` override. No matching parser Windows service or scheduled task was found.
- Available System event log coverage begins `2026-08-25T14:15:18Z`, after most of the canonical period. No candidate timezone-change events were found in the retained queried period. Historical event-log coverage is incomplete; missing old events are not evidence that the zone did not change.
- The present host setting cannot explain the sampled 2025 UTC+05:00 offsets and does not establish which machine/timezone wrote each historical row.

```text
WINDOWS_CURRENT_TIMEZONE=Pacific Standard Time
TIMEZONE_OVERRIDE_IN_PARSER_RUNTIME=NO_EXPLICIT_OVERRIDE_FOUND
HISTORICAL_TIMEZONE_CHANGE_EVENTS=0 in retained queried logs
HISTORICAL_EVENT_LOG_COVERAGE_INCOMPLETE=YES
```

## TIMEZONE_CONTRACT_DECISION

The writer's conversion is process-local `datetime.fromtimestamp()` followed by zone removal. Direct samples establish multiple wall-clock offsets, not one stable named zone or a complete date-partitioned regime. Therefore:

```text
SALE_TIMEZONE_CONTRACT=AMBIGUOUS
SALE_SOURCE_WALLCLOCK_ZONE=NOT PROVEN
SALE_TIMESTAMP_UTC_EXPRESSION=NOT ESTABLISHED
```

No candidate interpretation was selected based on activity shape.

## DST_FOLD_AUDIT

Under a Pacific-time candidate, the canonical period has one fall-back repeated local interval, 2025-11-02 01:00 through 01:59:59. The stored naive column contains 2,126 rows in that wall-clock interval. However, sampled 2025-11 rows mapped to UTC+05:00, so treating those 2,126 records as Pacific fold records would itself be an unsupported assumption. Exact receipt/block resolution was not requested for the 2,126 rows: the remaining budget after the 1,814 bounded calls was insufficient for the required per-row audit. None of those row hashes is included here.

```text
DST_FOLD_INTERVAL_COUNT=1 candidate Pacific interval; source zone unproven
DST_FOLD_AFFECTED_ROWS=2126 candidate wall-clock rows
DST_FOLD_EARLIER_OFFSET_ROWS=NOT DETERMINED
DST_FOLD_LATER_OFFSET_ROWS=NOT DETERMINED
DST_FOLD_UNRESOLVED_ROWS=2126
DST_FOLD_RESOLUTION=INCOMPLETE
DST_FOLD_ANALYTICS_STRATEGY=No safe strategy until historical runtime regimes and every candidate fold row are resolved
```

## DST_FOLD_RESOLUTION

Because the source zone is unproven and the candidate fold population exceeds the remaining authorized per-row RPC budget, no deterministic fold assignment is claimed. A later evidence task would need a larger explicitly authorized RPC budget or an authoritative historical archive of the parser's block-to-row mapping and runtime zone.

## UTC_AGGREGATION_CONTRACT

No future UTC SQL expression is approved. A correct reconstruction must first determine which process-local zone/regime applied to each record and resolve repeated local times by exact block instant. Plain `timestamp AT TIME ZONE ...` is not sufficient for the mixed observed offsets and unresolved repeated-hour candidates.

## USD_VALUE_CONTRACT

`public.sales` has no USD field. Existing site enrichment material previously reviewed describes daily manual-price enrichment, while current display fallbacks can use a current token price. Neither is a reliable transaction-time hourly USD contract.

```text
SALE_USD_VALUE_EXPRESSION=NOT_RELIABLY_AVAILABLE
SALE_USD_VALUE_CONFIDENCE=NOT_RELIABLY_AVAILABLE
USD_REQUIRED_FOR_NEXT_ANALYTICS_PHASE=NO, provided a valid timestamp and sale-event contract is later established; sale counts and native-unit volume do not inherently require USD
```

## NEXT_ANALYTICS_METRIC_SCOPE

USD is not intrinsically required for descriptive sale counts or native GUN-denominated volume. These metrics are not authorized from the current historical table yet because the timestamp and completed-sale contracts remain unresolved, and cross-chain 1:1 token equivalence is not documented. No market-reaction or causal analysis was performed.

## CANONICAL_PERIOD_AGGREGATES

`PRODUCTION_COMPLETED_SALES=NOT_DETERMINED`; `PRODUCTION_DISTINCT_SALE_IDENTITIES=NOT_DETERMINED`; `PRODUCTION_DUPLICATE_SALE_IDENTITIES=NOT_DETERMINED`; earliest/latest completed-sale UTC timestamps and completed-sale hours are `NOT_DETERMINED`. The timestamp and completed-sale predicates required for these aggregates are unresolved. The production table's transaction hash is unique by primary key, but that is not a substitute for the requested completed-sale identity counts.

## FINAL_CONTRACT_BLOCK

```text
SALE_TIMESTAMP_COLUMN=public.sales.timestamp
SALE_TIMESTAMP_POSTGRES_TYPE=timestamp without time zone
SALE_TIMEZONE_CONTRACT=AMBIGUOUS
SALE_SOURCE_WALLCLOCK_ZONE=NOT PROVEN
SALE_TIMESTAMP_UTC_EXPRESSION=NOT ESTABLISHED
DST_FOLD_INTERVAL_COUNT=1 candidate Pacific interval
DST_FOLD_AFFECTED_ROWS=2126 candidate wall-clock rows
DST_FOLD_RESOLUTION=INCOMPLETE
DST_FOLD_ANALYTICS_STRATEGY=NOT ESTABLISHED

SALE_COMPLETE_FILTER=NOT ESTABLISHED; price > 0 omits observed Trade events
SALE_COMPLETE_FILTER_CONFIDENCE=AMBIGUOUS
SALE_DEDUPLICATION_KEY=tx_hash

SALE_GUN_VALUE_EXPRESSION=public.sales.price (native GUNZ GUN amount only)
SALE_GUN_VALUE_CONFIDENCE=AMBIGUOUS for equivalence to Avalanche GUN
SALE_GUN_TOKEN_IDENTITY_CONTRACT=NOT PROVEN; official 1:1 bridge ratio not explicit
SALE_GUN_PRECISION_LIMITATION=from_wei result converted through float and int; fractional GUN truncated

SALE_USD_VALUE_EXPRESSION=NOT RELIABLY AVAILABLE
SALE_USD_VALUE_CONFIDENCE=NOT_RELIABLY_AVAILABLE
USD_REQUIRED_FOR_NEXT_ANALYTICS_PHASE=NO, if time and sale contracts are resolved

BUYER_ID_AVAILABLE=YES
SELLER_ID_AVAILABLE=YES
ITEM_ID_AVAILABLE=YES (token_id)
```

## DEFAULT_TESTS

`pytest -q`: 231 passed, 6 skipped. No Nansen calls were made.

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK033E=0`.

## ONCHAIN_RPC_CALL_ACCOUNTING

1,814 read-only JSON-RPC method objects were attempted, within the maximum of 2,000. The 508 zero-price receipts and 100 positive sample receipts all resolved on the official alternate endpoint; 594 distinct containing blocks resolved. There were 610 attempts to the parser-configured endpoint: its first 609 method objects (chain-ID and receipt calls) were unresolved, and a separate endpoint probe returned HTTP 403. It was not used again afterward. No wallet values, transaction hashes, raw RPC responses, or individual prices are in this report.

## PRODUCTION_SAFETY

Production connection mode: READ_ONLY. Production DDL=0, DML=0, changed=NO.

## STAGING_SAFETY

No staging connection or write. Staging DDL=0, DML=0.

## SECURITY_CHECK

No keys, credentials, wallet addresses, transaction hashes, individual sale data, or raw RPC payloads are included. No application source was changed. `.env` is not tracked.

## CYRILLIC_CHECK

PASS for this English-only report.

## FILES_CHANGED

- `DEV/reports/033e_onchain_sales_contract_resolution/report.md`

## UNRESOLVED_ITEMS

- Historical rows show multiple observed process-local offsets; historical deployment/runtime evidence is unavailable for most of the data period.
- Exact UTC reconstruction and the candidate repeated-hour population remain unresolved.
- The table does not retain event kind/finality; the positive-price predicate is disproven by zero-price Trade events.
- Official materials identify GUN and the Avalanche bridge contract but do not explicitly establish a 1:1 ratio.
- No reliable transaction-time USD amount exists in the inspected production contract.

## NEXT_RECOMMENDED_TASK

Keep Task 033 analytics blocked. First recover authoritative historical runtime/timezone deployment records or a complete row-to-block timestamp mapping, and establish a durable event-kind/finality discriminator. Separately obtain official bridge documentation that explicitly specifies native-to-Avalanche token unit conversion if cross-chain GUN volume equivalence is required. Do not proceed to Task 033 analytics until timestamp and completed-sale contracts are proven.
