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

Task 017M updated the fresh-install definition so
`flows.total_inflows_count` and `flows.total_outflows_count` use PostgreSQL
`NUMERIC NOT NULL`. Migration `sql/002_flow_counts_numeric.sql` was applied to
`server_otg_staging` only, converting those two existing BIGINT columns using
explicit lossless casts. The staging columns are `numeric NOT NULL`; the five
Nansen tables and their ownership remain intact. Production `server_otg` was
not changed and migration 002 has NOT been applied there.

The matching normalized fields are Python `Decimal`. Psycopg receives Decimal
parameters directly, and its NUMERIC results are verified to round-trip exact
synthetic fractional values. Flow keys remain based only on chain, canonical
token identity, scope, and date; changing metric precision does not alter row
identity.

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

Task 018 made the first authorized live flow-ingestion attempt for the exact
Avalanche `$GUN` `smart_money` window 2026-09-20. The single request timed out
before returning a page. Its durable ingestion audit is `failed`; the exact
target window has zero flow rows and no checkpoint. No live flow data was
persisted. This attempt provides no new NUMERIC round-trip evidence; prior
synthetic NUMERIC validation remains the database precision evidence.
Production remains untouched.

Task 018R separately succeeded for that same single-day stream: 23 complete
flow rows are retained in staging, and the successful audit run's checkpoint
references the exact requested window end. Two inflow rows retain fractional
NUMERIC values; no outflow rows were fractional. This is one bounded window,
not broader historical coverage. The original failed Task 018 audit remains
alongside the successful retry audit. Production remains untouched.

Task 019 replayed this same retained window once through the orchestrator.
The target remained 23 rows with 23 distinct flow keys, and the sorted flow
key set digest was unchanged. No duplicates were created. The checkpoint
timestamp stayed at the requested window end and now references the successful
replay audit; the earlier failed and successful run audits remain intact.
This validates idempotency only for this retained window.

Task 020 validated a separate 30-day early-history pilot
(2025-04-25T00:00:00Z through 2025-05-24T23:59:59Z). Nansen returned 29
complete flow records on one final page; staging contains 29 unique rows on
29 distinct dates, all within the requested interval. The September 20
high-water checkpoint did not regress and remains associated with the Task
019 replay run. The existing September rows and prior audit history remain
intact. This proves non-empty availability only for the exact pilot window;
it is not a full backfill or a claim of one record for every day.

Task 022 changes logical flow identity to include both bucket boundaries.
Fresh schema SQL requires non-null `bucket_end`, a positive interval, and a
natural unique constraint over chain/token/label/date/bucket_end. Migration
003 and re-keying were applied transactionally to staging after the source
commit was published. All 52 existing rows were retained and matched the new
key model; production remains out of scope.

Task 023 adds nullable `nansen.ingestion_runs.source_warnings` in fresh schema
SQL and migration 004. NULL means warning capture was unavailable or the run
predates warning capture; `[]` means paginated responses were inspected and
were warning-free. Non-empty arrays contain only page number, warning count,
and sanitized category names. The CHECK permits only an array or NULL. The
migration was published as an artifact but was not applied because the one
authorized live warning classified as `UNKNOWN`. Existing staging rows and
data remain unchanged.

Task 023F applies migration 004 to staging only. The exact previously observed warning is represented in source code only by its SHA-256 fingerprint, and accepted audit data contains only sanitized page/count/category summaries. Existing pre-capture audit rows remain NULL; new inspected warning-free runs use `[]`. Raw source warning text is never durable.

Task 024 retained 167 one-hour Flows buckets for the single seven-day Avalanche `smart_money` window 2025-04-25 through 2025-05-01 UTC. Six existing daily buckets coexist with the hourly buckets under bucket-aware identity and kept the same key-set digest. The warning audit stored a sanitized summary, and the historical run did not move the later high-water checkpoint. Production was untouched. No broader backfill was performed.
