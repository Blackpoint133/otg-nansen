# Task 022: Bucket-aware flow identity

## OBJECTIVE

Make persisted Nansen flow identity include the exact aggregation interval,
then safely migrate retained staging keys without changing rows, audits, or
checkpoint state.

## STARTING_STATE

Starting main was `0c0d4e5fc71c152e22a75eabb055bb92f66fc79e`; the worktree was
clean. Baseline offline tests passed: 140 passed, 5 opt-in skipped. Task 021
reported range-dependent hourly/daily Flows resolution and an inconclusive
same-start/different-end collision observation.

## TASK021_EVIDENCE

The official contract and Task 021 observations establish that query widths
can return distinct hourly or daily bucket intervals. `date` is bucket start
and `bucket_end` is exclusive. Existing flow keys did not include `bucket_end`,
so same-start resolutions could not safely coexist under the old identity.

## ARCHITECTURE_DECISION

Persisted identity is chain, canonical token address, canonical flow label,
UTC `date`, and UTC `bucket_end`. The normalized API model still permits a null
`bucket_end` for diagnosis; mapping and ingestion reject absent or non-positive
intervals. No bucket duration is assumed. Metrics and completeness remain
outside identity.

## IDENTITY_CONTRACT

The reusable `flow_identity_key()` fingerprints exactly the five identity
fields using the existing canonical JSON/SHA-256 machinery. Avalanche address
lowercasing and UTC canonicalization are preserved. Same interval is stable;
different bucket end, date, or label changes the key; metric changes do not.
The table also enforces a natural unique constraint on those same fields.

## PERSISTENCE_GUARDS

`map_flow()` raises `PersistenceDesignError` for null `bucket_end` or
`bucket_end <= date`. The orchestrator rejects the same invalid interval before
opening the data transaction, alongside its existing complete-record and
requested-window checks. It does not infer an end or duration.

## FRESH_SCHEMA_CHANGE

Fresh schema 001 now requires `bucket_end TIMESTAMPTZ NOT NULL`, checks
`bucket_end > date`, and declares the named natural bucket-identity unique
constraint. The `flow_key` text primary key remains.

## MIGRATION_003_DESIGN

`sql/003_flow_bucket_identity.sql` only sets `bucket_end` NOT NULL and adds the
positive-interval check and natural unique constraint. It has no DROP, DELETE,
or TRUNCATE. The staging-only Python utility pins the database name and
expected user, verifies writable staging, locks only `nansen.flows`, reads
identity columns only, checks null/invalid/duplicate preconditions, plans every
new key, and applies DDL plus key changes in one transaction. Existing keys
are first moved to unique temporary namespace keys disjoint from old and final
sets, then assigned final keys; any error rolls back the whole transaction.

## STAGING_PRECHECK

Read-only preflight confirmed `server_otg_staging`, `gunz_user`, and writable
mode for the migration account. There were 52 flow rows, zero null bucket ends,
zero non-positive intervals, and zero natural-identity duplicate groups.
Proposed keys were unique and old/new cross-collisions were zero. Recent scope
was 23 rows / 23 natural identities; early scope was 29 / 29.

## KEY_REMAP_PLAN

Old key-set SHA-256:
`2b63aabd2e126954847097695f19992fbdccd54b0b8a30c53efa6a9c471aa818`.
Planned new key-set SHA-256:
`71875ae7c8609b91f9d404021598304061ea7faeeb10c4797245b9801e4a80e6`.
All 52 planned final keys were unique; cross-collisions: 0.

## PRE_MIGRATION_SOURCE_COMMIT

The source, schema artifact, tests, and design documentation were committed
and pushed before database mutation. `PRE_MIGRATION_SOURCE_SHA=a964e613904a1538c8b7002913c2c1828cb02e9f`; remote readback matched.

## MIGRATION_EXECUTION

Migration 003 and all key remaps committed in one staging transaction. It
reported 52 rows, unique final keys, and zero old/new cross-collisions. No
Nansen API call was made.

## POST_MIGRATION_SCHEMA

Independent read-only inspection confirmed `bucket_end` is timestamp with
time zone and NOT NULL; both total count columns remain numeric NOT NULL. The
named bucket interval CHECK and natural unique constraint are present. All five
Nansen tables remain owned by `gunz_user`.

## FLOW_KEY_VERIFICATION

All 52 stored keys recompute from current application identity (mismatch rows:
0); keys and natural identities are unique; no temporary keys remain. Final
sorted flow-key-set SHA-256:
`71875ae7c8609b91f9d404021598304061ea7faeeb10c4797245b9801e4a80e6`.

## RETAINED_DATA_INTEGRITY

Total rows remain 52. The recent September window remains 23 rows / 23 natural
identities; the early Task 020 window remains 29 / 29. No retained analytical
values were selected for migration verification.

## CHECKPOINT_INTEGRITY

The checkpoint remains at the instant `2026-09-20T23:59:59Z` and still
references `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. Its database display used
the local `-07:00` offset, representing that same UTC instant.

## AUDIT_HISTORY

The original Task 018 audit remains failed; the Task 018R and Task 019 audits
remain successful. The Task 020 exact-window run remains present and
successful. Migration touched no audit or checkpoint table.

## UNIT_TESTS

Offline tests cover bucket-end/date/label identity variation, unchanged keys
for metric changes, null/zero/negative intervals, exact dual-resolution
coexistence and replay in memory, static SQL safety, complete migration
planning, and rejection of an old/new cross-collision. Default suite: 148
passed, 6 opt-in skipped. It made zero Nansen calls and zero PostgreSQL
connections.

## POSTGRES_TESTS

Opt-in staging suite: 5 passed. The Task 022 synthetic test persisted two
same-start buckets with distinct ends, replayed both without duplication, and
cleaned its exact synthetic scope. A read-only post-test query found zero
Task 022 synthetic rows; all 52 retained real rows remained.

## SYNTHETIC_CLEANUP

`task022_resolution_fixture` synthetic rows remaining: 0. No retained live
rows, audits, or checkpoints were deleted.

## RESOURCE_OBSERVATION

Before: CPU 59.3%, available RAM 4707 MB, committed memory 20503 MB, commit
limit 31731 MB. After: CPU 57.3%, available RAM 4799 MB, committed memory
20108 MB, commit limit 31731 MB. No sustained resource pressure observed.

## PRODUCTION_SAFETY

Migration target was staging only. Production DDL: 0; production DML: 0;
production changed: no.

## SECURITY_CHECK

Credential-pattern scan passed; `.env` is not tracked. Reports contain no
credentials or analytical flow values.

## CYRILLIC_CHECK

PASS; changed project files are English-only.

## FILES_CHANGED

- `src/otg_nansen/persistence.py`
- `src/otg_nansen/ingestion.py`
- `src/otg_nansen/flow_identity_migration.py`
- `src/otg_nansen/migrate_flow_identity.py`
- `sql/001_create_nansen_schema.sql`
- `sql/003_flow_bucket_identity.sql`
- `tests/test_persistence.py`
- `tests/test_ingestion.py`
- `tests/test_postgres_integration.py`
- `docs/architecture.md`
- `docs/database.md`
- `docs/analytics_methodology.md`
- `docs/operations.md`
- `docs/nansen_api.md`
- `DEV/reports/021_historical_flow_granularity_probe/report.md`
- `DEV/reports/022_bucket_aware_flow_identity/report.md`

## RISKS

Bucket-aware keys prevent different bucket ends at the same start from
colliding. Historical source revision/reconciliation behavior remains
unverified. This work does not establish a broad backfill policy.

## NEXT_RECOMMENDED_TASK

Review a separately bounded historical ingestion plan that selects request
window widths intentionally and validates bucket-aware overlap behavior. Do
not begin a broad backfill or Task 023 automatically.
