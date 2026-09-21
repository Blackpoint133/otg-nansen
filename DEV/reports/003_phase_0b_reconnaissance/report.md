# Report 003 - Phase 0B reconnaissance

## OBJECTIVE

Perform bounded, read-only reconnaissance for a future public Nansen-powered
`$GUN` and Off The Grid market-reaction analytics module. No parser, database
schema, service, deployment, or frontend implementation was started.

## STARTING STATE

- Project root: `C:\VAMBAM\Projects\OTG\parsers\parser_nansen`
- Branch: `main`
- Starting HEAD: `89b59fd513855d956c3bfda0cd1e5aa1229f6528`
- Working tree: clean after the Task 002 report push
- `.env`: present, ignored, and never printed
- Phase 0A bootstrap: complete

## GITHUB BASELINE

Task 002 report commit:

`89b59fd513855d956c3bfda0cd1e5aa1229f6528`

The report was pushed before Phase 0B began. No unrelated repository was
changed.

## LOCAL ARCHITECTURE RECON

The existing OTG OpenSea reference project is a Windows/Python application
with Streamlit presentation, PostgreSQL-backed importers, prepared CSV/JSON
artifacts, and NSSM-wrapped Windows services. Relevant roles include sales
import, indexer, market-overview generation, price history, and Streamlit
presentation. Existing production tooling records service application paths,
NSSM settings, stdout/stderr log paths, and rollback metadata.

The reference host currently exposes separate OTG services for OpenSea sales,
the OpenSea indexer, market overview, listings, and other unrelated systems.
Relevant scheduled-task conventions include staging metadata, item metadata,
item class, trader profile, and derived-data refresh tasks. The expected
`system_managment` reference directory did not contain a useful file set in
this inspection; no new convention was invented.

The future Nansen module should remain separate from those production services
until its API, persistence, and restart behavior are reviewed.

## POSTGRESQL RECON

POSTGRESQL_RECON_STATUS=PASS_READ_ONLY
POSTGRES_VERSION=18.3
DATABASES=blackpoint_eve, postgres, server_otg, server_otg_staging
DATABASE_WRITES=0

The connection used environment variables from the local `.env` only, enabled
`default_transaction_read_only`, and used a short statement timeout. Only
catalog metadata, estimated row counts, sizes, and aggregate min/max timestamp
queries were used. No row-level wallet data was included.

Relevant `server_otg.public` sources:

| Table | Approximate rows/size | Time metadata | Future use |
|---|---:|---|---|
| `sales` | 9,004,370 / 3,870 MB | `timestamp`, 2025-04-25 to 2026-09-21 | Read-only OTG market reaction history |
| `opensea_sales` | 19,660 / 18 MB | `parsed_date`, 2026-03-10 to 2026-09-21 | OpenSea sales reference |
| `opensea_listings` | 3,365 / 1.1 MB | `parsed_date`, 2026-09-20 | Listing reference |
| `inventory` | 23,692 / 32 MB | UTC snapshot column | Ownership/inventory reference |
| `inventory_new` | 22,786 / 7.6 MB | UTC snapshot column | Alternate inventory snapshot |
| `item_catalog` | 4,207 / 1.0 MB | first/last observation | Item identity reference |
| `item_metadata_current` | 1,661 / 928 kB | `updated_at` through 2026-09-09 | Metadata reference; freshness is a future question |
| `token_price` | 2,716 / 352 kB | `updated_at` through 2026-09-21 | GUN price alignment |
| `opensea_listings_events_v2` | 1,657 / 4.6 MB | event timestamps through 2026-09-16 | Event-state reference |
| `opensea_listings_v2` | estimated unavailable / 176 kB | update timestamps through 2026-09-16 | Current listing-state reference |

Timestamp conventions are mixed: legacy tables use timestamp-without-timezone
columns, while newer event and snapshot tables use timezone-aware columns.
Future normalization must explicitly choose UTC and preserve source timezone
metadata rather than assuming all legacy values are UTC.

## OFFICIAL GUN IDENTITIES

The official GUNZ website lists the following cross-chain addresses:

| Chain | Address | Source | Confidence |
|---|---|---|---|
| Avalanche C-Chain | `0x26deBD39D5eD069770406FCa10A0E4f8d2c743eB` | https://www.gunbygunz.com/gun/ | HIGH; official GUNZ page |
| Solana | `3jUf2RTyXp867piSB2dt8uUcNiLDW58asjGtXkRAkBbe` | https://www.gunbygunz.com/gun/ | HIGH; official GUNZ page, corroborated by official Solana-expansion announcement |

The official documentation also describes GUN as the native coin of the GUNZ
chain, not an ERC-20 on that chain. Nansen's reviewed supported-chain list did
not include `gunz`; therefore the cross-chain identities above must not be
treated as proof that Nansen covers native GUNZ-chain activity.

## NANSEN DOCUMENTATION FINDINGS

Official documentation reviewed:

- Authentication: https://docs.nansen.ai/getting-started/authentication
- Rate limits: https://docs.nansen.ai/getting-started/rate-limits
- Credits: https://docs.nansen.ai/getting-started/credits
- Error handling: https://docs.nansen.ai/getting-started/error-handling
- Endpoint overview: https://docs.nansen.ai/api/overview
- Supported chains: https://docs.nansen.ai/reference/chains
- Data methodology: https://docs.nansen.ai/guides/data-methodology-and-technical-reference

Documented authentication uses an `apikey` header. Current documented limits
are 20 requests per second and 300 requests per minute per key. Pagination is
page/per_page with an is_last_page response flag. Date ranges are inclusive.
Documented Smart Money historical holdings provide a four-year rolling window
of daily end-of-day UTC snapshots, but that depth does not generalize to every
endpoint.

## NANSEN ENDPOINT MATRIX

| Endpoint family | Method/inputs | Documented cost | Diagnostic result |
|---|---|---:|---|
| TGM token-information | POST; chain, token address, timeframe | 1 Pro / 10 Free | 200 on both chains |
| TGM flows | POST; chain, token, date, label, pagination | 1 Pro / 10 Free | Avalanche usable; Solana empty in narrow window |
| TGM DEX trades | POST; chain, token, date, pagination, filters | 1 Pro / 10 Free | Usable on both chains |
| TGM who-bought-sold | POST; chain, token, buy/sell, date, pagination | 1 Pro / 10 Free | Usable on both chains |
| TGM transfers | POST; chain, token, pagination | 1 Pro / 10 Free | Usable on both chains |
| TGM holders | POST; chain, token, label type, pagination | 5 Pro / 50 Free | Usable on both chains |
| Smart Money historical holdings | POST; chains, date range, filters, pagination | 5 Pro / 50 Free | Documentation only; not live-probed |
| TGM token OHLCV | POST, endpoint listed | 1 Pro per overview | Request schema not sufficiently verified |

The account plan and credit balance were not queried. No historical backfill,
large pagination, or repeated request was performed.

## LIVE API REQUEST LOG

LIVE_API_CALLS_TOTAL=12

All calls used `per_page=2` where applicable and a narrow diagnostic date
window of 2026-09-19 through 2026-09-20. Headers and raw responses were never
logged.

| Call | Chain | Endpoint | HTTP | Result |
|---:|---|---|---:|---|
| 1 | Avalanche | token-information | 200 | usable |
| 2 | Avalanche | flows, smart_money | 200 | 2 records |
| 3 | Avalanche | dex-trades | 200 | 2 records |
| 4 | Avalanche | who-bought-sold | 200 | 2 records |
| 5 | Avalanche | transfers | 200 | 2 records |
| 6 | Avalanche | holders | 200 | 2 records |
| 7 | Solana | token-information | 200 | usable |
| 8 | Solana | flows, smart_money | 200 | empty |
| 9 | Solana | dex-trades | 200 | 2 records |
| 10 | Solana | who-bought-sold | 200 | 2 records |
| 11 | Solana | transfers | 200 | 2 records |
| 12 | Solana | holders | 200 | 2 records |

## AVALANCHE RESULTS

AVALANCHE_USABLE=YES

Nansen recognized the official Avalanche identity. Token information, Smart
Money-labeled flows, DEX trades, buyer/seller summaries, transfers, and holders
all returned usable diagnostic results. This is the richer initial source for
event detection and is the recommended MVP primary chain.

## SOLANA RESULTS

SOLANA_USABLE=PARTIAL

Nansen recognized the official Solana identity. DEX trades, buyer/seller
summaries, transfers, and holders returned usable results. The narrow two-day
Smart Money flows query returned HTTP 200 with an empty data array. This may be
data sparsity or a query-window/label limitation; it is not evidence that the
chain is unusable overall.

## API CREDIT OBSERVATIONS

API_CREDIT_SUMMARY=Documentation estimates 20 Pro credits for the 12 calls, or 200 Free-plan credits; actual account consumption was not queried.

The free/pro plan is unresolved. The request budget remained below 20 calls,
well below the task cap, and no credit-related error occurred.

## HISTORICAL DEPTH

HISTORICAL_DEPTH_SUMMARY=Smart Money historical holdings documents a four-year rolling window; TGM flow/trade endpoint maximum depth was not documented in the reviewed pages; the live probe proved only the narrow two-day diagnostic window.

The next task must measure endpoint-specific historical coverage with one or
two bounded ranges before designing retention or backfill behavior.

## FIXTURES CREATED

`tests/fixtures/nansen/phase0b_endpoint_shapes.json` was created. It contains
only public token identities, endpoint names, statuses, and small record-count
shape metadata. It contains no API key, header, wallet rows, or raw response.

## COMPETITION REQUIREMENTS

Official Nansen Meridian Buildathon sources reviewed:

- https://nansen.ai/campaigns/meridian-buildathon
- https://release.nansen.ai/help/articles/3540155-nansen-meridian-buildathon-sep-14-27

Verified requirements include the September 14-27, 2026 event window, a
September 27 23:59 UTC submission close, 1,000 or more API calls, a public
GitHub repository, an X demo post tagging `@nansen_ai`, a 30-60 second live
screen recording, and an entry form containing email, X post URL, and GitHub
repository. The four judging categories are Data Integration, Functionality,
Creativity & Originality, and Documentation & Submission. Prize details and
winner timing should be rechecked immediately before submission.

## CHAIN DECISION

CHAIN_DECISION=PRIMARY_AVALANCHE

Avalanche is primary because it produced usable Smart Money flows in the
diagnostic window in addition to all other tested TGM families. Solana is a
tested secondary source, not discarded: its trade, holder, transfer, and
buyer/seller results were usable, but its Smart Money flows result was empty.
The native GUNZ-chain coverage question remains unresolved.

## MINIMAL MVP ARCHITECTURE

1. A small API client reads `NANSEN_API_KEY` and a versioned chain/token
   configuration, enforces rate and credit budgets, and records HTTP status.
2. A bounded ingestion command requests only approved date windows and stores
   normalized public event/flow records with chain, token identity, source
   timestamp, retrieval timestamp, and request metadata.
3. A future isolated PostgreSQL namespace stores checkpoints and normalized
   records. It must not write to existing OTG tables.
4. An event detector produces data-driven `$GUN` activity windows with
   completeness and uncertainty fields.
5. A read-only OTG adapter aggregates existing sales, listings, and token
   price history on a documented UTC convention.
6. A comparison layer produces prepared analytical outputs, not direct
   production UI writes. A later DEV-only frontend can consume those outputs.

This is a design decision only; no component was implemented.

## RISKS

- Nansen may not cover native GUNZ-chain activity even though it covers the
  Avalanche and Solana representations.
- Endpoint historical depth and credit consumption are not uniform.
- Mixed legacy OTG timestamp types create timezone-alignment risk.
- Empty Solana flows may reflect sparsity, label semantics, or query shape.
- Public repository fixtures must remain small and avoid unnecessary wallet
  or transaction detail.
- Existing OTG tables are production-owned and must remain read-only.

## UNRESOLVED QUESTIONS

- Does Nansen expose the native GUNZ chain under a different chain identifier?
- What is the exact historical depth and credit cost for token OHLCV and TGM
  event endpoints under the account plan?
- Are Smart Money labels meaningful for this token on both chains over longer
  windows?
- Which normalized event definition best predicts or describes subsequent OTG
  market reaction without implying causality?
- What isolated PostgreSQL schema and retention policy should be reviewed?

## RESOURCE OBSERVATIONS

No heavy job, backfill, long-running process, service, or database write was
performed. Lightweight Windows samples were:

- baseline: CPU 33.1%, available RAM 6.102/15.999 GiB, committed 18.292/30.987 GiB, free commit 12.695 GiB;
- final: CPU 23.8%, available RAM 6.069/15.999 GiB, committed 18.309/30.987 GiB, free commit 12.678 GiB.

## NEXT RECOMMENDED TASK

Task 004 should implement only a reviewed, fixture-first Nansen client and
bounded endpoint contract tests, after resolving native GUNZ-chain coverage
and confirming the account's API plan/credit budget. It should not yet create
production tables, backfill history, or deploy a service.

FINAL_STATUS=PHASE_0B_RECONNAISSANCE_COMPLETE
CYRILLIC_SCAN=REQUIRED_BEFORE_COMMIT
SECRET_SCAN=REQUIRED_BEFORE_COMMIT
DATABASE_WRITES=0
PRODUCTION_CHANGED=NO
