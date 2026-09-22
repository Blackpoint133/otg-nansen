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

The following schema is applied to `server_otg_staging` only. It remains NOT
APPLIED to production. The migration artifact is
`sql/001_create_nansen_schema.sql`.

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

Task 009 makes `flow_label` a required non-empty scope for flow normalization
and request provenance. Checkpoint identity is `(chain, endpoint,
token_address, flow_label)` so separate flow-label streams cannot overwrite
one another. Flow keys use only stable chain/token/scope/date identity; the
unproven `bucket_end` and all mutable observations are excluded. DEX trade
keys use stable swap dimensions with canonical Decimal encoding and exclude
mutable enrichment. Normalized models preserve caller identity for application
use, while persistence mappings canonicalize Avalanche EVM addresses to
lowercase; Solana and unknown-chain address values remain exact.
Checkpoint identity is `(chain, endpoint, token_address, flow_label)` so
separate flow-label streams cannot overwrite one another. Flow keys use only
stable scope/time identity fields and DEX trade keys use transaction/trader/
swap identity; mutable labels, names, and USD estimates are excluded.

Token snapshots use `(chain, token_address, retrieved_at)` and duplicate
snapshots are ignored. Parameterized flow and trade upserts are reviewable in
the persistence module. A complete flow cannot be downgraded by a later
incomplete observation. The audit lifecycle is separate: a committed running
row is created first; data and checkpoint changes commit atomically; then the
run is marked success inside that same transaction, or the data transaction
rolls back and the existing run is marked failed/partial in a separate audit
operation. SQL checks require canonical non-empty flow scope and enforce the
empty non-flow scope representation. A successful checkpoint always references
a run that becomes success in the same commit. Migration status is applied to
staging only and NOT APPLIED to production.
Task 011 provides the selected psycopg3 adapter and a guarded migration
command. The command forces `server_otg_staging`, verifies `current_database`,
and uses bounded lock and statement timeouts. Task 013A applied the schema to
`server_otg_staging` only; production remains NOT APPLIED.
Checkpoint advancement now validates the actual successful ingestion run,
canonical token, endpoint, chain, and flow scope. The checkpoint SQL uses an
`INSERT ... SELECT` eligibility guard, and the schema composite foreign key
prevents cross-stream run references. Success status is updated before the
checkpoint in the same transaction. Task 013B validated the deployed schema
with the opt-in PostgreSQL suite and removed all synthetic test rows. The
owner-approved `gunz_user` CREATE privilege remains intentionally persistent
on `server_otg_staging` only; no production privileges were granted.

Task 014 orchestration fetches and normalizes the complete bounded source
window before opening the data transaction. Successful flow and DEX windows
advance their checkpoint to the requested window end; valid empty windows are
also checkpointed. Incomplete or out-of-window records fail the run without
persisting data. Task 014 used fixture sources only.
