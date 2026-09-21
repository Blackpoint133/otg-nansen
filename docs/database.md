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
