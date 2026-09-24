# Operations

The reference OTG deployment uses Windows services wrapped by NSSM, with
separate importer, indexer, overview, and Streamlit roles. Logs are kept in
the existing OTG logging layout and scheduled tasks are used for selected
staging and refresh jobs. No Nansen service or scheduled task exists.

Future Nansen work should remain a foreground, bounded, read-only validated
process until its persistence and retry behavior are reviewed. No operational
component was added in Phase 0B.

The persistence interface uses parameterized psycopg3 queries, records
ingestion status, and advances checkpoints only after complete successful
ingestion. The reviewed schema is deployed to staging only; production is not
connected for writes.

Each future ingestion run must retain token and request scope; flow ingestion
requires a non-empty flow label. The audit start and final audit update are
durable operations separate from the data transaction. Normalized rows and
their scoped checkpoint commit together, while a failed or partial run rolls
back both and records failure in the already-created audit row. Success status
is staged with data and checkpoint, removing the post-commit running-state
window. The migration was review-only until Task 013A applied it to
`server_otg_staging`; production remains NOT APPLIED. The owner intentionally
retains CREATE for `gunz_user` on staging as a persistent staging-only
privilege. PostgreSQL integration tests are opt-in with
`NANSEN_RUN_POSTGRES_TESTS=1`; the validated suite leaves no synthetic rows.
The guarded staging command is `python -m otg_nansen.migrate_staging`; it
refuses any database other than `server_otg_staging`. PostgreSQL integration
tests are opt-in with `NANSEN_RUN_POSTGRES_TESTS=1`; default pytest remains
database-free.

Task 017M applied `sql/002_flow_counts_numeric.sql` to `server_otg_staging`
only. The migration changed only the two total flow count columns from BIGINT
to NUMERIC, using explicit casts. The source commit was pushed before DDL;
post-migration checks confirmed both columns are still NOT NULL, staging table
ownership is unchanged, and all five Nansen tables remain. No live Nansen data
was used. Production was not connected or modified.
The checkpoint API does not accept caller-authoritative status flags. It
requires a staged successful run with matching stream identity, and rejects
zero-row eligibility. Flow scopes use separate successful runs and checkpoints
for each stream. Task 013B validated these behaviors against staging.

Task 014 adds no service or scheduler. Its foreground orchestrator starts a
durable audit row, fetches all bounded pages outside the data transaction,
normalizes and validates the complete window, then atomically persists data,
success status, and the checkpoint. Empty complete windows advance to the
requested end; incomplete, malformed, or out-of-window source data records a
bounded failure. All Task 014 tests used fixtures or fakes, with zero live
Nansen calls.

Task 014R uses the documented array sorting form for historical requests and
does not send a standalone `order` field. Successful runs persist logical page
and API-attempt counters. If bounded pagination reaches its limit, the failure
audit retains the known fetched page and record counts while data and
checkpoints remain unchanged.

Task 018 attempted exactly one live Avalanche `$GUN` flow request with retries
disabled and the configured three-call maximum. The request timed out on that
first attempt. The durable run was marked failed, and independent staging
verification found no flow rows or checkpoint for the target window. No retry
or persistence followed. The failed audit is intentionally retained; another
live attempt requires separate authorization.

Task 018R was subsequently authorized as a separate single-run retry. With a
60-second timeout, zero retries, and a three-call cap, the existing
orchestrator completed the exact same window using three requests. Staging
validation found 23 unique complete in-window flow rows, a successful audit,
and the checkpoint referencing that run and window end. The first failed
Task 018 audit remains preserved. This does not authorize another window,
endpoint, chain, or historical backfill.

Task 019 replayed the same retained Avalanche `$GUN` `smart_money` day once.
The flow-key set digest and row count were stable (23 unique rows, no
duplicates), while a new successful audit became the checkpoint's referenced
run at the same window end. Earlier failed/successful audit history was
preserved. This narrow replay is not evidence for broader historical replay
or source-revision reconciliation.

Task 020 ran one bounded early-history pilot for 2025-04-25 through
2025-05-24 UTC, with a two-call maximum, zero retries, and a 120-second
timeout. The response completed in one page and persisted 29 normalized rows.
The checkpoint remained at its later September 20 timestamp and still
references the Task 019 success run. This is exact-window availability
evidence only; do not infer maximum Nansen history, daily completeness, or
authorization for a broad loop.

Nansen Flows resolution is range-dependent, so persistence identity includes
both `date` and exclusive `bucket_end`. The model may retain a null bucket end
for diagnosis, but orchestration rejects null or non-positive intervals before
opening the data transaction. Task 022 published its migration before applying
it to staging; all retained flow rows were re-keyed without row loss. Production
remains untouched.

Task 023 makes pagination retain warnings per source page in memory. Only
sanitized categories, page numbers, and warning counts are stored in the run
audit. Warning-free paginated runs store `[]`; legacy and pre-response runs
remain NULL. Unknown warnings stop before the data transaction, and a
pagination-limit failure preserves the warning evidence already fetched.
The verified non-exchange breakdown warning is allowed only for flows labeled
`smart_money`. Task 023's live revalidation was `UNKNOWN`, so migration 004
remains unapplied, production is unchanged, and broader ingestion remains
blocked.

Task 023F accepts one exact warning fingerprint only for TGM Flows `smart_money`, and only after normalized records confirm all four CEX/DEX breakdown fields are null. Different wording and mixed unknown warnings fail closed before the data transaction. Migration 004 is applied to staging only; production remains untouched. The raw warning is never stored or logged.

Task 024 used one foreground orchestrator run with one API call, one page, zero retries, and a one-page bound for 2025-04-25 through 2025-05-01 UTC. It retained 167 hourly buckets beside six pre-existing daily buckets. The exact warning policy passed and the audit stored only the sanitized warning category. The September high-water checkpoint did not regress. No service or scheduler was added, and production remains untouched.

Task 025 performed one shifted, read-only Flows request. It recovered the previously missing first hourly bucket from Task 024, while the shifted request omitted its own lower-bound bucket. This observation conflicts with the current official description of non-Hyperliquid first-bucket behavior. Do not use naive non-overlapping weekly windows for systematic hourly ingestion until a boundary-aware request plan is separately reviewed and authorized. No database mutation, ingestion audit, or checkpoint update was made.

Task 026 provides `python -m otg_nansen.backfill_plan` as a plan-only dry run. The optional `--staging-progress` mode forces a read-only connection to `server_otg_staging` and classifies each unit from exact-window audit evidence. Unit execution is exposed only as a sequential injected callback contract with finite unit and live-call ceilings, completion skipping, and stop-on-first-failure behavior; it was exercised with fakes only. Each unit's Nansen request starts one hour before its desired coverage, covers at most 167 desired hourly starts, and must remain within the hourly-resolution request-duration limit. No API call, ingestion, audit write, checkpoint change, service, or scheduler was made for Task 026. Do not use the stream high-water checkpoint as historical backfill progress.

Task 027 adds `python -m otg_nansen.backfill_execute`. It refuses live work unless both `--execute` and `NANSEN_RUN_LIVE_BACKFILL=1` are supplied; it has no database-target override and verifies `server_otg_staging` / `gunz_user` before opening a writer. Read-only audit progress selects the first three pending canonical units. Each receives a fresh Nansen client configured for one call, zero retries, one page, and a 120-second timeout. The batch stops at its first failure and enforces three units and three calls maximum. The first three units succeeded; exact-window warning-audited progress now selects unit 4 after restart. The remaining plan was not run. Production remains untouched.

Task 028 generalizes this runner to resume from read-only exact-window audit progress. Live invocation requires explicit `--max-units`, `--max-live-calls`, `--expected-complete-before`, and `--expected-first-pending-index`, plus the double opt-in. Code-level caps reject more than 20 units or calls before a writer opens; batch calls must cover at least one attempt per unit. Each selected unit uses a fresh one-call, zero-retry client. Units 4–13 completed sequentially and exact-window progress now selects unit 14. Resource checks run after every successful unit and stop before the next selected unit if pressure is detected. No later unit, service, or scheduler was started; production remains untouched.

Task 029 removed Task 028-specific bounds and task-numbered status output; the runner now requires equal unit and call budgets, each capped at 20. It stopped after unit 28 when Python reported a false coverage gap across a daylight-saving fold. A read-only UTC-normalized check confirmed 167/167 desired unit 28 identities and 2,505/2,505 across attempted units 14–28. The runner now canonicalizes aware bucket timestamps to UTC before set comparison, with a DST-fold regression test. Only 15 requests were made; units 29–33 were not requested. Review the fix and separately authorize resumption; do not resume automatically. Production remains untouched.

Task 029R revalidated the committed UTC identity fix and then used the generic runner for exactly units 29–33, with five requests total. All five audits and coverage checks passed; progress is now 33 complete / 41 pending, with unit 34 next. Task 029's historical failure status remains recorded. No further units, service, scheduler, or production target were used.

Task 030R stopped after one new attempt for pending unit 46 returned an API error. Units 34–45 are complete; units 46–53 remain pending. Failed audit history is retained, no retry loop ran, and no unit 47 or later was requested. Review the Task 030 report and staging progress before any separately authorized continuation.

Task 030D diagnosed the two unit 46 failures as HTTP 403 `NansenHTTPError` responses. Their safe summaries indicate an insufficient-credit condition. Current official Nansen guidance marks the credit condition and forbidden access non-retryable; 403 is also excluded from the committed client's retryable status set. No third call was authorized or made. Unit 46 remains blocked pending account/credit resolution; units 47–53 remain pending.

Task 030K validated the operator-replaced local key with one authorized unit 46 request. The exact-window run succeeded and all 167 desired hourly identities are present. Progress is 46 complete / 28 pending / 0 ambiguous; unit 47 is next and was not executed. Production remains untouched.

Task 030F completed units 47–53 after Task 030K's successful unit 46 recovery. The replacement key resolved the unit 46 access/credit blocker for that request. The full original Task 030 range, units 34–53, now has 3,340/3,340 desired hourly identities and 20 successful exact-window unit runs; earlier failed unit 46 audits remain in history. Progress is 53 complete / 21 pending / 0 ambiguous, unit 54 is next, and the checkpoint remains unchanged. Production was untouched.

Task 031 used the committed staging-only runner for units 54-73, with one API attempt per unit and no retries. Each unit passed its exact-window audit, sanitized warning policy, and UTC-normalized 167/167 coverage check. The runner finished at 73 complete / 1 pending / 0 ambiguous; unit 74 is next and was not run. Warning-audited exact-window runs remain the historical resume authority, not the high-water checkpoint. The checkpoint remained unchanged and production was untouched.

Task 032 used the committed staging runner for the single pending unit 74 with a one-call budget and no retry. The successful run is warning-audited and all 145 desired identities are present. Fresh read-only validation reports 74 complete / 0 pending / 0 ambiguous and confirms full contiguous 12,336-hour coverage. The runner's final tuple-equality checkpoint check printed a failure because equal-timestamp ownership moved to the new run; the checkpoint timestamp itself did not regress, consistent with the accepted equal-timestamp policy. No source change was made. Unit 74 was the final canonical request; production was untouched.

Task 032R fixed and tested runner terminal checks without live calls or staging writes. Checkpoint timestamp regression is rejected; when an owner changes or the timestamp advances, the owner must be a successful matching stream run whose window ends at the checkpoint. Recent identities must be preserved, duplicate-free, and any new identity must be desired by the selected units. The final unit may leave no next pending index. The completed plan verifies as 74/0/0; no analytical task was started.
# Task 033's operational path is source-first: review and push code, migration,
# tests, and runbook before applying any staging migration or data replacement.
# `python -m otg_nansen.analytics_build --execute` pins source reads to
# `server_otg` (transaction read-only) and analytics writes to
# `server_otg_staging`. It verifies the canonical Nansen identity digest,
# resolves the 5,632-row timestamp overlap through read-only GUNZ RPC, requires
# the accepted overlap digest, aggregates and aligns all 12,336 UTC hours, then
# atomically replaces only the two analytics snapshots. The same in-memory
# snapshot is written and read back twice to verify persistence idempotency;
# the second pass makes no RPC call. No Nansen request is part of this build.
# The real SELECT-only staging-writer/cursor capability preflight must pass
# before any overlap RPC. Snapshot bulk inserts use psycopg3 cursor.executemany;
# a failed preflight stops the run with zero RPC calls.
#
# The first Task 033 execution applied migration 005 but stopped before staging
# data writes because the pinned staging writer could not open its connection.
# A source fix is now pushed; both analytics tables were confirmed empty after
# that attempt. Completing the build requires a separately authorized fresh
# overlap-resolution pass because the in-memory RPC mapping was not persisted.
