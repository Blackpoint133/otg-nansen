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

Task 027 added three exact-window successful ingestion audits for canonical hourly units 1–3. Each recorded one page, one API call, 167 received and normalized rows, and a non-null sanitized warning summary containing only `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`. The combined desired coverage is 501 unique hourly identities: 167 already existed and 334 were added. Daily identities in the combined coverage remained unchanged; global flow rows increased from 219 to 553 with zero natural-identity duplicates. Exact-window audit progress is now 3 complete / 71 pending / 0 ambiguous. The historical requests did not change the existing high-water checkpoint. These rows and audits are staging data; production was untouched.

Task 028 added ten successful exact-window audit rows for canonical units 4–13. Each recorded one page and one API call, 167 received and normalized records, and a non-null sanitized warning summary containing only the approved category. The 1,670 desired hourly natural identities were absent before this batch and present afterward. Canonical target totals are now 2,194 hourly plus 29 daily rows; global flows total 2,223 with zero natural-identity duplicates. The daily identity digest and September 20 retained rows were unchanged. Audit-based progress is 13 complete / 61 pending / 0 ambiguous; the September high-water checkpoint did not move. Production was untouched.

Task 029 added 15 successful exact-window ingestion audit rows for units 14–28. An initial Python identity comparison falsely reported three missing starts for unit 28 because database timestamps were returned in the local daylight-saving fold and were compared directly with UTC values. A read-only UTC-normalized identity check confirmed all 167 unit 28 starts, and all 2,505 desired identities across units 14–28, with zero missing and zero duplicates. Staging has 4,699 canonical hourly rows, 29 daily rows, 4,728 total flow rows, and 33 ingestion runs. Audit-only progress reports 28 complete / 46 pending / 0 ambiguous. The checkpoint and September retained state remained unchanged. The runner stopped before unit 29; staging only.

Task 029R added five warning-audited success runs for units 29–33. Each retained 167/167 desired hourly identities. The combined Task 029 and 029R range (units 14–33) now has 3,340 desired identities complete. Staging totals are 5,534 canonical hourly rows, 29 daily rows, 5,563 total flow rows, and 38 ingestion runs, with zero natural-identity duplicates. The checkpoint remains unchanged; production was untouched.

Task 030R reconciled staging after the partial Task 030 run. Units 34–45 have valid successful audits and 167/167 desired hourly identities. Unit 46 has two failed one-attempt audits with no page evidence; units 47–53 have no audit. Current totals are 7,567 flows (7,538 hourly, 29 daily) and 52 ingestion runs, with zero natural-identity duplicates. Progress is 45 complete / 29 pending / 0 ambiguous. The failed attempts added no flow rows.

Task 030D diagnosed the two unit 46 failures as HTTP 403 `NansenHTTPError` responses. Their safe summaries indicate an insufficient-credit condition. Current official Nansen guidance marks the credit condition and forbidden access non-retryable; 403 is also excluded from the committed client's retryable status set. No third call was authorized or made. Unit 46 remains blocked pending account/credit resolution; units 47–53 remain pending.

Task 030K validated the operator-replaced local key with one authorized unit 46 request. The exact-window run succeeded and all 167 desired hourly identities are present. Progress is 46 complete / 28 pending / 0 ambiguous; unit 47 is next and was not executed. Production remains untouched.

Task 030F completed units 47–53 after Task 030K's successful unit 46 recovery. The replacement key resolved the unit 46 access/credit blocker for that request. The full original Task 030 range, units 34–53, now has 3,340/3,340 desired hourly identities and 20 successful exact-window unit runs; earlier failed unit 46 audits remain in history. Progress is 53 complete / 21 pending / 0 ambiguous, unit 54 is next, and the checkpoint remains unchanged. Production was untouched.

Task 031 added 3,340 hourly flow identities for canonical units 54-73. Staging now contains 12,214 canonical hourly rows, 29 daily rows, 12,243 total flow rows, and 80 ingestion runs, with zero natural-identity duplicates. The 20 new successful exact-window runs have non-null sanitized warning audits and no unknown categories. Progress is 73 complete / 1 pending / 0 ambiguous; unit 74 remains pending. The daily identity digest, September 20 rows, and high-water checkpoint were unchanged. Production was untouched.
