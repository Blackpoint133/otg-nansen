# Architecture

## Confirmed objective

The project will use Nansen token/wallet intelligence to study historical
`$GUN` activity and subsequent Off The Grid NFT/item-market reactions.

Phase 0B established that the smallest future architecture is a controlled
Nansen client, normalized event/flow persistence, historical `$GUN` event
detection, read-only comparison against existing OTG market history, and
prepared analytical output. The client, normalization boundary, staging
schema, repository, and bounded fixture-backed orchestration now exist; event
detection and market comparison do not.

The current technical recommendation is primary Avalanche ingestion with a
separately checkpointed Solana adapter. Both chains returned usable token,
trade, holder, transfer, and buyer/seller responses, while the narrow Solana
Smart Money flows window was empty. The native GUNZ chain remains a separate
identity question because the reviewed Nansen chain list did not include
`gunz`.

The first code foundation is a bounded HTTP client with no service runtime.

The raw API response boundary feeds immutable normalized models for token
information, flows, and DEX trades. Normalization validates required fields,
preserves caller-trusted chain/token identity, and uses UTC-aware timestamps.
Financial and token quantities use Decimal. The two Nansen flow total count
metrics also use Decimal because the live endpoint returned a finite
fractional JSON number; `holders_count` and the optional CEX/DEX counts remain
integer typed. PostgreSQL staging persistence is implemented and validated;
the live historical window still requires a post-change normalization check.

Task 007 defined an isolated `nansen` PostgreSQL schema
with snapshot, flow, trade, ingestion-run, and checkpoint tables. A future
driver-backed repository must use parameter binding and preserve the raw-to-
normalized boundary.

Persistence identity is scope-aware: flow labels are part of request and
checkpoint provenance. A flow key identifies one exact bucket by chain,
canonical token, label, UTC `date`, and exclusive UTC `bucket_end`; mutable
measurements are excluded. DEX trade
keys exclude mutable labels and USD estimates while retaining transaction and
swap identity. Repository lifecycle methods are designed around one
transaction per ingestion run.
The final proposed lifecycle instead uses a durable audit start, one atomic
data/checkpoint transaction, and a durable audit success or failure update.
Migration status is applied to staging only and NOT APPLIED to production.
Flow scope and positive bucket interval are mandatory for persistence, and
flow identity includes both bucket bounds; DEX trade identity excludes mutable enrichment.
Persistence identity canonicalizes Avalanche EVM addresses to lowercase while
preserving exact Solana and unknown-chain values. Flow scope is trimmed once
at normalization and reused by all persistence mappings.
Task 011 adds a psycopg3 repository adapter with separate durable-audit and
atomic data/checkpoint/success connections. The staging migration command is
database-pinned and was applied to `server_otg_staging` only in Task 013A.
Production remains unapplied.

Task 014R aligns historical request sorting with the official Nansen contract:
flows use `order_by=[{'field': 'date', 'direction': 'ASC'}]` and DEX trades use
`order_by=[{'field': 'block_timestamp', 'direction': 'ASC'}]`. Success audit
updates persist page and API-attempt counters, and pagination-limit failures
retain known page/record progress. These repairs are fixture-verified only.

Task 023 retains top-level warnings with each fetched page in memory and
classifies them before normalization or persistence. Only sanitized page,
count, and category summaries enter ingestion audit rows; legacy runs remain
NULL and an observed warning-free paginated run stores `[]`. Unknown warnings
fail closed. The documented non-exchange breakdown warning is eligible only
for `flows` with `smart_money`, but the authorized live revalidation remained
`UNKNOWN`; broader backfill is blocked and migration 004 remains unapplied.

Task 023F adds an exact SHA-256 fingerprint policy for the previously observed warning, restricted to `flows` / `smart_money`. After normalization, every returned record must have all four optional CEX/DEX breakdown fields null before the warning is accepted. The raw wording is never stored, and any wording change becomes `UNKNOWN`. The exact fingerprint and evidence are in the Task 023F report. Migration 004 is applied to staging only; production remains unchanged. Legacy warning audit values remain NULL, while inspected warning-free runs use `[]`.

Task 026 provides deterministic plan-only tooling after the observed Task 025 lower-bound bucket omission. The canonical range contains 12,336 inclusive desired hourly bucket starts and 74 request units, each covering at most 167 starts. `coverage_start/coverage_end` define desired responsibility; `request_start/request_end` define the Nansen range and include a one-hour pre-roll. Consecutive desired coverage is gap-free and non-overlapping, while request ranges overlap by one hourly bucket. Resume requires an exact matching successful flow audit with non-null sanitized warning metadata. The current high-water checkpoint is not historical progress state. The planner and fake executor shell do not perform live requests; Task 026 did not run backfill.

Task 027 adds a staging-pinned live runner with double opt-in (`--execute` and `NANSEN_RUN_LIVE_BACKFILL=1`), a three-unit ceiling, and one fresh one-attempt client per unit. It executed canonical units 1–3 sequentially through the existing ingestion orchestrator. Each exact-window audit was successful and warning-audited; all 501 desired hourly starts across the three coverage windows are present, with 167 identities reused and 334 added. The request pre-roll overlap coexists with bucket-aware identity. Audit progress is the resume authority; the September high-water checkpoint remains unchanged. Unit 4 is next. The remaining 71 units were not executed, and production remains untouched.

Task 028 generalizes the same staging-pinned runner to select a bounded batch from freshly inspected exact-window audit progress. Absolute per-invocation limits are 20 units and 20 live calls; each unit still has one call. The authorized ten-unit batch resumed at unit 4 and completed through unit 13, advancing progress from 3/71 to 13/61. All 1,670 desired hourly identities were present, daily identities remained unchanged, and the high-water checkpoint stayed separate. Unit 14 is next; the remaining 61 units were not executed. Production remains untouched.

Task 029 removes the prior task-specific bound assertion and result naming from the reusable runner. Live unit and call budgets must now be equal and are each capped at 20. Its 20-unit authorization attempted units 14–28, then stopped at unit 28 after a false coverage-gap result: database timestamps in the daylight-saving fold were compared to UTC timestamps without normalization. A read-only UTC-normalized check confirmed 167/167 desired identities for unit 28. Progress is 28 complete / 46 pending; units 29–33 were not requested. UTC identity normalization was added with a regression test after the stop. Production remains untouched.

Task 029R preserved Task 029's original failure status, physically revalidated the DST fix, and completed units 29–33 with five requests. The full intended Task 029 unit range, 14–33, now has complete desired coverage. Progress is 33 complete / 41 pending / 0 ambiguous; unit 34 is next. The high-water checkpoint remained unchanged and production remains untouched.

Task 030/030R did not complete its authorized 34–53 range. The first invocation completed units 34–45 and stopped on an API error at unit 46. Reconciliation confirmed those 12 units valid; one new attempt for pending unit 46 also failed, and the runner stopped before unit 47. Current progress is 45 complete / 29 pending / 0 ambiguous; unit 46 remains next. The partial state is documented in the Task 030 report. Production remains untouched.
