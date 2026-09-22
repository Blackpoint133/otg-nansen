# Database

PostgreSQL reconnaissance was read-only against the existing OTG instance.
The server reported PostgreSQL 18.3 and databases including `server_otg` and
`server_otg_staging`. No DDL, DML, schema, or migration was performed.

Relevant production-owned metadata observed in `server_otg.public`:

- `sales`: estimated 9,004,370 rows, about 3,870 MB; timestamp range 2025-04-25 through 2026-09-21.
- `opensea_sales`: estimated 19,660 rows; parsed-date range 2026-03-10 through 2026-09-21.
- `opensea_listings`: estimated 3,365 rows; parsed-date range 2026-09-20 through 2026-09-20.
- `inventory` and `inventory_new`: about 23,692 and 22,786 estimated rows respectively, with UTC timestamp columns.
- `item_catalog`: estimated 4,207 rows with first/last observation columns.
- `item_metadata_current`: estimated 1,661 rows; `updated_at` last observed 2026-09-09.
- `token_price`: estimated 2,716 rows; `updated_at` last observed 2026-09-21.
- `opensea_listings_events_v2` and `opensea_listings_v2`: event/state tables with timezone-aware event and update columns.

The existing application treats these as read-only analytical sources. A
future Nansen schema should be isolated and designed only after endpoint and
retention decisions are approved; this task created no tables.

## Proposed Nansen persistence design

The following is PROPOSED / NOT YET APPLIED. The review-only artifact is
`sql/001_create_nansen_schema.sql`; it has not been executed.

The proposed isolated `nansen` schema contains:

- `token_information`: immutable token-information snapshots keyed by chain,
  token address, and UTC retrieval time;
- `flows`: normalized flow records keyed by a deterministic source fingerprint;
- `dex_trades`: normalized trade records keyed by a deterministic fingerprint
  containing transaction, trader, action, token, and traded-token context;
- `ingestion_runs`: bounded execution audit with running, success, failed, and
  partial statuses;
- `checkpoints`: chain/endpoint/token restart state referencing only a
  successful ingestion run.

All Decimal model values map to PostgreSQL `NUMERIC`, not floating-point
types. All accepted datetimes map to `TIMESTAMPTZ`. Complete-window reruns are
idempotent through deterministic flow/trade keys. Partial or failed runs
cannot advance a checkpoint. No schema or row exists from this task.

Task 008 adds `flow_label` and request-scope provenance to flow/run records.
Checkpoint identity is `(chain, endpoint, token_address, flow_label)` so
separate flow-label streams cannot overwrite one another. Flow keys use only
stable scope/time identity fields and DEX trade keys use transaction/trader/
swap identity; mutable labels, names, and USD estimates are excluded.

The repository lifecycle is intended to run in one database transaction:
begin a run, upsert normalized rows, mark the run success or failure, and
advance a checkpoint only after complete success. Rollback preserves the prior
checkpoint and prevents partial data from being marked complete.
