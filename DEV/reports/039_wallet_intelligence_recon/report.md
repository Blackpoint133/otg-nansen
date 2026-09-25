# Task 039: Read-Only Wallet Intelligence Reconnaissance

## Objective

Inventory existing OTG wallet-level sales data and Nansen/on-chain capabilities to produce a practical, evidence-based plan for wallet intelligence. This was reconnaissance only. No schema, source data, analytics result, or UI was changed. Task 034 remains intact as historical context: hourly $GUN price-return relationships with marketplace activity were weak and inconsistent.

## Git States Inspected

All remotes were fetched before inspection.

| Project | Local branch and HEAD | Remote comparison | Worktree |
|---|---|---|---|
| `Blackpoint133/otg-nansen` | `main`, `324a8b868e0be845e1b24934b43711b1d8588694` | `origin/main` same SHA; 0 ahead / 0 behind | Clean before this report |
| OTG Analytics staging checkout, `C:\VAMBAM\Projects\OTG\staging\opensea_sales` | `develop`, `cd5a9ac242f4d1053597ec7ac453d4baa0c951c9` | `origin/develop` same SHA; 0 ahead / 0 behind; 84 commits ahead of `origin/main` | One pre-existing untracked `img/gunz_scope/logo_2.png`; left untouched |
| OTG Analytics production checkout, `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales` | `main`, `9edb927dc25432effda8fe8ae353993d55297f4d` | `origin/main` same SHA; 0 ahead / 0 behind | Clean |

The local staging checkout is synchronized with its `develop` remote and differs from `main` by the recorded 84-commit development line. The live `?mode=nansen` work belongs to that staging checkout. The production checkout is at its remote main. The Nansen repository remains separately synchronized at its own main. No checkout, reset, stash, or cleanup was performed.

## Database Read-Only Scope

Production was inspected through the committed pinned reader. Identity was `server_otg`, `transaction_read_only=on`. Staging was inspected through the pinned staging reader; identity was `server_otg_staging`, `transaction_read_only=on`. The staging schema includes Nansen ingestion tables and the two ratified hourly analytics tables, but no sales or wallet-event source table. No database writes or schema changes occurred.

## OTG Wallet-Level Sources

### Primary parser-backed source

The authoritative parser-backed source is `server_otg.public.sales`. Its live columns are:

| Column | Type | Observed meaning / limitation |
|---|---|---|
| `tx_hash` | `character varying`, primary key | Transaction identity and parser conflict key |
| `buyer`, `seller` | `character varying`, not null | Participant wallet identifiers |
| `timestamp` | `timestamp without time zone`, not null | Stored wall-clock event time; requires the ratified reconstruction contract |
| `token_id` | `integer`, not null | Item identity field |
| `item_name`, `rarity` | `character varying`, nullable | Item descriptors; not a stable category taxonomy by themselves |
| `price` | `numeric`, not null | Parser-recorded native amount after `from_wei`, float conversion, and integer truncation; no currency identity or USD column |
| `serial_number` | `character varying`, nullable | Optional metadata |

The only index observed on `public.sales` is the unique primary-key B-tree on `tx_hash`; there is no buyer, seller, or timestamp index. `tx_hash` uniqueness prevents duplicate stored transaction keys but does not establish one item-line per row, finality, or completed-sale status. The parser has a Transfer fallback that can store zero-price records. The table has no event-type, cancelled/failed, receipt-status, reorg, currency, or source-zone field. Treat rows as parser-backed marketplace transaction events, not settled paid item sales. These limitations are documented in Task 033D and the ratified Task 033 report.

The timestamp must follow the accepted piecewise contract already used for Task 033, including exact block resolution inside the historical transition overlap. A future wallet profile store should retain normalized UTC event time and its source-resolution class so profile recency is reproducible.

### Other inspected sources

- `server_otg.public.opensea_sales` exists as an OpenSea-derived table. It has `sale_date`, `parsed_date`, `buyer`, `seller`, `token_id`, `price_gun`, `type_token`, `rarity`, `transaction_hash`, and item URL/name fields. Its provenance and coverage differ from `public.sales`; it is not interchangeable without a transaction-level reconciliation and duplicate policy.
- `server_otg.public.inventory` and `inventory_new` contain wallet, contract, token, and a `timestamp_utc` snapshot field. These are snapshots, not a complete transfer history. Their refresh coverage, ownership semantics, and freshness must be verified before using them as current holder state.
- `item_catalog` stores names/rarity and first/last observed timestamps. `item_metadata_current` contains item class/type fields, but its live catalog freshness and mapping coverage require validation. These can support a versioned item-category mapping, not an assumption that sales already have authoritative category labels.
- `token_price` contains date/time and price columns, but its observed legacy time naming and daily granularity do not provide a complete, validated transaction-time USD price for every sale.
- The OTG staging app's `streamlit_opensea_sales/trader_analytics.py` already normalizes prepared sales events and derives buyer/seller counts, native amount volumes, first/last activity, active days, unique items/assets/counterparties, and a conservative observable FIFO P&L when asset identity is available. `scripts/build_trader_analytics.py` builds an offline snapshot from prepared `sales_enriched` files. This is reusable implementation evidence, but not a complete database-backed production wallet index.

## Buyer Universe and Quantification Limits

The ratified Task 033 canonical interval already has an aggregate-only query result: 9,562,201 parser-backed rows, stored native amount sum 356,791,669, 79,548 distinct buyers, 78,681 distinct sellers, and 6,934,161 distinct item IDs. This is canonical-range evidence, not a current lifetime count. It contains no raw identities.

A local generated Top Traders snapshot in the staging checkout covers only 22,337 prepared events and 1,347 wallet profiles from 2025-07-15 through 2026-09-24. It is not tracked, is not complete production history, and must not be used as the production buyer universe. Within this limited snapshot only, buyer counts are: at least 2 purchases 643; at least 5, 447; at least 10, 232; at least 25, 137; at least 50, 73. Snapshot buy-count quantiles (min, p25, p50, p75, p90, p95, p99, max) are 0, 1, 1, 7, 25, 54, 253, 2,035. These figures demonstrate the existing profile code and the skew of the partial extract; they do not estimate full-population counts or define tiers.

A new full-table buyer distribution aggregation was attempted using a read-only session and a bounded 120-second statement timeout. It exceeded that limit. The table has no buyer index, so repeated exact grouping queries would scan/group a large source and are not justified in this reconnaissance. No exact full-population >=2/5/10/25/50 counts, spend quantiles, purchase-size distribution, or current recency distribution were established here. Task 033R6 provides the exact canonical aggregate totals above. A future planned read-only batch job should compute the complete distributions under an approved resource window, preferably after a wallet-event store is initialized from a stable source snapshot.

## Buyer Profile Feature Availability

| Feature | Classification | Evidence and caveat |
|---|---|---|
| Previous purchase count | DERIVABLE WITH EXISTING DATA | Count parser-backed rows grouped by buyer; first define zero/fallback handling and event semantics. |
| Historical native amount spend | DERIVABLE WITH EXISTING DATA | Sum `price`; preserve parser truncation and label as stored native marketplace amount, not Avalanche $GUN or USD. |
| Historical USD spend | UNRELIABLE / NOT RECOMMENDED | No production USD field; daily/manual enrichment and current-price display fallbacks do not prove transaction-time USD value. |
| First and last purchase time | DERIVABLE WITH EXISTING DATA | Requires exact UTC reconstruction, including overlap mapping; store normalized UTC for future events. |
| Median / typical purchase size | DERIVABLE WITH EXISTING DATA | Compute per-wallet quantiles from correctly classified rows; zero/fallback records must be handled by a documented rule. |
| Preferred price band | DERIVABLE WITH EXISTING DATA | Derive from native amounts; cannot call it USD purchasing power without reliable historical valuation. |
| Item/category preference | DERIVABLE WITH EXISTING DATA | Name/rarity plus a versioned metadata mapping can support approximate preferences; category completeness and drift need QA. |
| Buying frequency | DERIVABLE WITH EXISTING DATA | Requires reliable UTC event ordering and declared observation window. |
| Active/inactive recency | DERIVABLE WITH EXISTING DATA | Requires UTC-normalized last-buy time and current parser refresh watermark. |
| Maximum individual purchase | DERIVABLE WITH EXISTING DATA | Maximum stored `price` per buyer; describe parser-recorded amount and transaction-row semantics. |
| Recent 7d / 30d activity | DERIVABLE WITH EXISTING DATA | Requires incremental freshness, exact UTC conversion, and duplicate/reorg policy. |
| Current holdings of item | REQUIRES NEW DATA | Sales alone cannot show subsequent transfers, burns, gifts, or current owner. Inventory snapshots may help after their provenance/freshness is verified. |
| Reliable per-sale USD valuation | REQUIRES NEW DATA | Need a documented historical price source and exact timestamp/market conversion policy. |

## Nansen and Chain Wallet-Event Capabilities

### A. Current implemented Flows endpoint

`NansenClient.flows()` calls `/api/v1/tgm/flows`; normalization returns time-bucketed token-level values such as price, token amount/value, holders, and aggregate inflow/outflow counts. It does not return arbitrary wallet addresses, transfer identities, or per-wallet received value. The current Smart Money label is a cohort aggregation, not an address feed. Task 034's flow-imbalance series therefore remains aggregate historical context and cannot power a `KNOWN BUYER FUNDED` event.

### B. Other documented Nansen endpoints

Official Nansen Profiler Address Transactions documentation describes per-address recent transactions, token transfers, native movements, contract interactions, direction, token amounts, USD value, block timestamp, and pagination capped at 100 records per page. This is a candidate for known-buyer monitoring but means at least one request per wallet per polling interval/page. The current Nansen client does not implement it. [Profiler Address Transactions](https://docs.nansen.ai/api/profiler/address-transactions)

Profiler Current Balances is a current point-in-time holding snapshot, not an event stream or historical change detector. Historical Balances offers dated snapshots but not exact transfer event identity; it can miss short-lived incoming-and-outgoing movement between snapshots. [Current Balances](https://docs.nansen.ai/api/profiler/address-current-balances), [Historical Balances](https://docs.nansen.ai/api/profiler/address-historical-balances)

TGM Transfers is token-centric: a request is for one chain and token, with transfer and exchange-flow filters and optional from/to address filters. It can help monitor a chosen token (such as Avalanche $GUN) across known OTG buyers; it cannot discover every asset that funded a wallet. The earlier Task 003 probe established a small diagnostic response for TGM transfers, but did not establish full coverage, historical depth, or a known-wallet monitoring contract. [TGM Token Transfers](https://docs.nansen.ai/api/token-god-mode/token-transfers)

Current Nansen documentation lists one credit for Profiler address transactions, address current/historical balances, and TGM transfers. Historical address transactions and historical token balances are listed at higher cost. Costs and plan availability can change; confirm in account usage before a production design. No Nansen request was made during this reconnaissance. [Nansen Credits](https://docs.nansen.ai/getting-started/credits)

### C. Direct Avalanche data

An Avalanche archive/indexing source can identify ERC-20 `Transfer` events for an allowlisted token set and native AVAX value movements from transaction traces/receipts. For known buyer addresses, a local indexer can poll recent blocks, deduplicate by chain/tx/log index, and derive incoming gross/net token amounts. USD valuation still needs reliable historical prices. A standard RPC node is not a convenient all-address discovery API; archive/log access, indexed provider capacity, reorg handling, and token registry are required. This avoids per-wallet Nansen credit costs after setup but has material ingestion, storage, index coverage, and operational costs.

### D. Not currently available

There is no implemented per-wallet Nansen adapter, address event store, general all-token known-wallet funding feed, validated historical USD valuation for all candidate assets, or complete transfer-based current ownership index in the Nansen repo. No live endpoint capability probe was justified after reading documentation; none was made.

## Defining “Liquidity Received”

| Candidate observable | Source and valuation | Reliability / false positives | OTG use and cost |
|---|---|---|---|
| Received Avalanche $GUN | Nansen TGM token transfers or direct ERC-20 logs; token units exact, USD requires dated $GUN price | Clear token flow, but receipt may be exchange, bridge, contract, self-transfer, or immediate onward transfer; gross receipt is not spendable new capital | Relevant context for a $GUN/OTG audience; Nansen token-transfer monitoring is 1 credit per request in current docs, while direct indexing has setup/ops cost. |
| Received AVAX | Nansen address transaction data or direct native transaction/trace source; USD using dated AVAX price | Native transfer is observable, but transaction value can be gas/contract routing; incoming value may be offset by outgoing flow | Useful funding context, but not necessarily OTG purchase intent. Per-wallet API scan cost grows with known-wallet count. |
| Received stablecoin | Address transaction/transfer data for an explicit allowlist of verified Avalanche stablecoin contracts; dated price source | Stronger USD approximation for supported redeemable assets, but depegs, bridged variants, mint/burn, spam, and contract interactions create false positives | Useful liquidity context if token allowlist and price provenance are explicit; cost scales by wallets/assets or by indexing. |
| Any tracked liquid token with USD value | Profiler transaction feed or direct indexed ERC-20 transfers plus price registry | Coverage depends on token universe and price availability; unsolicited dust/spam and illiquid tokens inflate gross value | Broadest view but highest data cleaning/false-positive risk. Not suitable for V1 without an allowlist. |
| Net inflow over a window | Sum eligible incoming less outgoing transfers for an allowlist | More informative than gross receipts but requires complete transfer coverage for the entire window, self-transfer/bridge/entity rules, and reorg-safe deduplication | Useful as neutral “observed net token inflow”; not available from the current aggregate flow endpoint per wallet. |

Recommended event name for a first truthful prototype: `observed_allowlisted_asset_inflow`, with explicit asset, amount, valuation source/time, gross-versus-net definition, and source coverage. Use `KNOWN OTG BUYER RECEIVED [ASSET]` only if an address is linked to prior parser-backed purchases. Avoid the generic term “funded” until the tracked asset set and event completeness are clear.

## Known Buyer Funded Feasibility

Technically feasible as a **bounded observation** over a selected cohort of historical OTG buyers, not as a comprehensive market-wide alert today. The following are supportable:

- prior OTG purchase count, stored native-amount spend, last observed purchase time, and a typical native amount range: derivable from parser-backed `sales` after UTC and row-semantic rules are applied;
- received token/native amount: potentially supported by Nansen Profiler Address Transactions for selected wallets or direct indexed events;
- received USD value: only when an eligible asset and dated valuation exist; otherwise show token units or omit USD;
- activity tier: defer until full buyer distributions are measured and a non-arbitrary rule is approved;
- “watch for renewed market activity”: descriptive context only. Never say the wallet is likely to buy or will buy.

The documented endpoint’s 100-row page cap means a large cohort can incur many requests and may not be polled frequently within modest credits. Current credits docs list 1 credit per address transaction request, but actual plan limits and historical/current variant availability must be checked. Direct chain indexing is better at cohort scale after setup, while Nansen is the quickest low-infrastructure capability to validate on a small, opt-in cohort. It does not make a full-population real-time feed cheap.

## Returning Buyer Liquidity and Market Divergence

A rolling 24-hour aggregate is feasible after selected-wallet transfer data exists. Define raw measures first: number of distinct known OTG buyers with eligible incoming events; gross and net token units by asset; valued subtotal and coverage share; count of subsequent OTG buyer events; current marketplace transaction count, native amount, and unique buyers from the existing source. Keep per-asset values separate unless price conversions are validated.

“Buyer liquidity increased while marketplace activity remained flat” requires a predeclared comparison window and baseline. It should report both observed inflow and marketplace activity measures, their coverage/freshness, and change against a stated prior period. Do not label that “buying pressure”: funding does not establish intent, and historical amount/count alone does not observe current holdings or purchasing action.

## Funding-to-Purchase and Recurring Behavior

The sales source provides purchase timestamps, but there is no historical per-wallet funding-event archive. Nansen address transactions may provide recent wallet transactions, and direct chain logs can be backfilled for selected wallets/token contracts; historical depth, page coverage, plan access, and cost need a bounded measured pilot. Task 003 documents only narrow endpoint probes, not complete historical transfer coverage.

To avoid look-ahead bias, construct each funding episode using only events available at its event time; define eligible assets and event window before joining to later sales; exclude sales before or at the funding event; keep wallet-specific chronological splits for validation; and handle repeated inflows within a predeclared declustering window. Display only observed frequencies such as “x of y observed episodes had a purchase within 2–6 hours,” include denominators and coverage, and never translate this into a probability of a future purchase. Do not display an individual recurring pattern until there are at least 20 independent eligible episodes across the analyzed population and repeated evidence for that wallet (recommended minimum 3 episodes); label this as a conservative display gate, not a statistical significance test. A V1 should not attempt this feature because no historical funding-event baseline exists.

## New-to-OTG, Seller, and Holder Interpretation

- **New to OTG:** an address with no observed prior buyer event in the covered OTG sales history, then a new observed purchase or an eligible incoming funding event. It means “new in our covered OTG history,” not a new blockchain wallet. Coverage start, parser gaps, and old wallet aliases can create false novelty.
- **New on-chain wallet:** wallet age or first-ever transaction requires chain-wide transaction history and is not implied by first OTG appearance. Do not conflate these labels.
- **Seller history:** seller appearances, sell counts, proceeds proxy, item mix, and recency can be derived from `sales`, subject to event semantics and native amount caveats.
- **Current holder:** cannot be inferred from seller history. Inventory snapshots exist, but must be validated for full collection coverage, refresh time, transfer ownership rules, and failure rows. A current holder feature needs a reconciled ownership index or a validated current inventory feed.
- **Prior buyer who still holds:** requires joining purchase item identity to all subsequent transfers/burns and current ownership; current sales rows alone are insufficient.

For any public UI, show a shortened address with a chain explorer link only where the source network is established. Never invent a person, social identity, or reputation label. Explain whether the wallet is merely an address observed in public data.

## Proposed Parallel Wallet-Intelligence Model

These entities are a planning proposal only; no migration was created. They coexist with, and do not replace, `nansen.otg_market_hourly` or `nansen.otg_nansen_hourly`.

| Entity | Purpose and grain | Key/source fields | Cadence, retention, dedupe, indexing |
|---|---|---|---|
| `otg_wallet_profile` | One current derived profile per chain/address | PK `(chain_id, wallet_address_normalized)`; first/last OTG buy/sell UTC; counts; native amount sums/quantiles; unique item/category summaries; source watermark; mapping version | Incremental refresh after source ingest; retain versioned snapshots or recomputable aggregates; never store inferred identity labels; index last activity and cohort membership as needed. |
| `otg_market_wallet_event` | One normalized parser-backed marketplace transaction event | PK `(source, tx_hash)` consistent with current transaction grain; buyer/seller, item/token ID, stored amount, event/source timestamp, normalized UTC, timestamp resolution class, parser version, event classification/quality flags | Incremental from sales; source-key idempotency; preserve parser semantics and correction/reorg policy; indexes on normalized event UTC, buyer+UTC, seller+UTC, and item+UTC after workload proof. Avoid copying raw chain payloads. |
| `wallet_funding_event` | One observed incoming/outgoing asset transfer at chain log/transaction grain | PK `(chain_id, tx_hash, log_index)` or a provider event identity; wallet, counterparty, asset contract, direction, amount, event UTC/block, source, receipt/finality, valuation amount/source/time/coverage | Poll or bounded address scan; retain raw identity only in access-controlled operational store, with reorg reconciliation; indexes `(wallet, event_utc)`, `(asset, event_utc)`, unique chain event key. |
| `wallet_behavior_episode` | One derived funding episode or funding→purchase episode per wallet and definition version | PK episode ID derived from versioned event IDs; wallet key, funding window, later marketplace event key, delay, episode rule/version, coverage flags | Recompute when source watermark changes; retain rule version and observed evidence; dedupe event IDs and predeclared episode window; indexes wallet+episode time and rule/version. |
| `market_wallet_intelligence_hourly` | One UTC hour or rolling window aggregate for monitored cohort | PK `(window_start_utc, cohort_id, definition_version)`; known buyers funded, distinct wallet count, asset-specific inflow units/value, returning-buyer purchases, marketplace activity, coverage/freshness | Hourly/daily refresh; retain aggregate history per reporting need; dedupe by source watermark/version; indexes on window and cohort. No addresses in public aggregate. |

Storage of raw wallet-level activity should be minimized and access-controlled. Public output should be aggregated by default; a wallet-level drilldown needs an explicit product/privacy review.

## Product Model and Prioritization

Scores are relative qualitative judgments for a short deadline; high false-positive risk and unavailable source data are explicit blockers.

| Candidate | Trader usefulness | Availability / reliability | Time, API and ops cost | False positives / deadline risk | Priority |
|---|---|---|---|---|---|
| A. Known Buyer Funded event feed | High if sourced and qualified | Medium for a small cohort; not implemented | Medium-high; per-wallet calls or indexer | High unless asset/transfer filters and coverage are explicit | 2, after bounded feasibility pilot |
| B. Returning Buyer Liquidity 24h aggregate | High, actionable context | Medium after event source and baseline | Medium; cohort polling/indexing and aggregation | Medium-high; gross flow can mislead | 1, smallest useful V1 only for a declared monitored cohort |
| C. Funding vs OTG Market divergence | Medium-high | Depends on A/B plus trustworthy current marketplace metrics | Medium | High unless “flat/increased” baseline and coverage are fixed | 3 |
| D. Funded buyer → subsequent OTG purchase tracking | High as a retrospective behavior measure | Sales side available; historical funding history absent | High initial backfill, moderate thereafter | Medium; attribution/timing confounds | 5 |
| E. Recurring wallet funding/purchase patterns | Medium | No historical funding archive | High backfill and validation | High, small samples/selection bias | 7 |
| F. New-to-OTG capital | High | OTG history available, funding universe absent | High | High due incomplete history and wallet migration | 6 |
| G. Seller activity | Medium | Derivable from current sales history | Low-medium once profiles computed | Medium due transaction semantics | 4 |
| H. Holder activity | High | Current inventory snapshots exist but are unvalidated; sales are insufficient | Medium-high ownership reconciliation | High if seller is mistaken for holder | 8 |
| I. Existing historical Market Reaction | Medium as context | Complete, ratified, reproducible | Low; already built | Low methodological risk, but weak/inconsistent association | Existing fallback / historical context |

The smallest useful V1 is a read-only, allowlisted **Returning Buyer Liquidity 24h** aggregate for a measured cohort, paired with existing current OTG marketplace activity and explicit data coverage. It gives a trader the observation: “selected wallets with prior OTG purchases had these asset inflows, while marketplace transactions/buyers/amount changed by these measured amounts.” Start with one tracked asset family, preferably stablecoins only if contract allowlist and valuation are verified; otherwise show asset units separately. Do not launch a whole-market “Known Buyer Funded” feed until completeness and event semantics are measured.

Given the short competition deadline, a truthful wallet-level V1 is **not yet safe to claim ready**: the full buyer universe has not been profiled, the event source is not implemented, and all-token valuation and feed coverage are unresolved. Keep the working Nansen historical demo as fallback and present the new direction as a next-stage plan.

## V1 / V2 / V3 Roadmap

- **V1 — bounded read-only monitored cohort:** one allowlisted asset definition; start from a capped set of historical OTG buyers; build profile aggregates from correctly normalized sales history; ingest or query funding events with source/freshness/coverage fields; show a 24-hour aggregate beside current OTG activity. No prediction and no tier until population distributions are computed.
- **V2 — broader buyer intelligence:** validate more asset contracts and dated USD valuations; track returning buyers and new-to-OTG addresses; compare funding and subsequent purchases; add monitored seller history. Establish coverage and resource controls before expanding cohort.
- **V3 — behavior episodes and holder state:** backfill funding events for a justified period; evaluate repeated funding→purchase episodes with temporal holdout and minimum-denominator rules; build current ownership reconciliation from transfers/inventory. Keep all outputs descriptive.

## Recommended Next Implementation Task

Run a separate **wallet-source feasibility pilot** before schema design: (1) profile the exact full buyer distribution in an approved resource window using a read-only, query-planned batch; (2) select a small capped cohort by a documented, non-arbitrary sampling procedure; (3) make one explicitly authorized Nansen Profiler Address Transactions probe for a sanitized cohort address, or use a local direct-chain test if API authorization is unavailable; (4) validate pagination, eligible transfer fields, latency, credit cost, and USD coverage; (5) compare a limited interval against direct public chain logs; (6) return only aggregate evidence and a go/no-go recommendation. Do not add schema until this establishes event semantics, freshness, cost, and a safe cohort size.

## Safety and Limitations

- No Nansen API request, RPC request, public sales row readout, production write, staging write, DDL, or DML occurred in this task.
- Read-only source inspection used catalog metadata and aggregate evidence only. One broad historical distribution query exceeded its 120-second read-only timeout; no exact current full-table buyer frequency/spend distribution is claimed.
- The locally available Top Traders snapshot is a partial, ignored generated artifact and was used only for sanitized illustrative counts. It was not copied into this repository or report with wallet rows.
- Task 034 artifacts and methodology were not modified. Existing hourly results remain valid historical context, not a wallet-level funding signal.
- No holder state, universal liquidity measure, complete new-wallet state, or causal/predictive behavior is claimed.

## Sources Reviewed

- Existing OTG source contract: `DEV/reports/033d_sales_data_contract_resolution/report.md`, `DEV/reports/033f_timestamp_regime_resolution/report.md`, `DEV/reports/033f2r_transition_digest_ratification/report.md`, and `DEV/reports/033r6_ratify_existing_hourly_snapshot/report.md`.
- Existing Nansen endpoint reconnaissance: `DEV/reports/003_phase_0b_reconnaissance/report.md` and `DEV/reports/015_live_avalanche_contract_probe/report.md`.
- Current official Nansen documentation: [Address Transactions](https://docs.nansen.ai/api/profiler/address-transactions), [Current Balances](https://docs.nansen.ai/api/profiler/address-current-balances), [Historical Balances](https://docs.nansen.ai/api/profiler/address-historical-balances), [TGM Token Transfers](https://docs.nansen.ai/api/token-god-mode/token-transfers), and [Credits](https://docs.nansen.ai/getting-started/credits).
