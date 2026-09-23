# Task 019: Live retained-window idempotency replay

## OBJECTIVE

Replay the already-retained Avalanche `$GUN` `smart_money` flow window once
through the existing ingestion pipeline and verify deduplication, audit
history, and checkpoint restart behavior.

## STARTING_STATE

Starting `main` was `96f8ba5c5eb3e07989e2c8a057e9330589b8f25c`; the worktree
was clean. No application source was changed.

## PRE_REPLAY_STATE

Staging preflight verified database `server_otg_staging`, user `gunz_user`,
and `transaction_read_only=off`. All five Nansen tables existed; both total
flow count columns were `numeric NOT NULL`. The exact target window had 23
rows and 23 unique keys, with zero out-of-window and incomplete rows. The
original Task 018 audit was failed; the Task 018R audit was successful and
the checkpoint referenced it at the exact requested window end.

## FLOW_KEY_SET_BASELINE

Before replay, fractional inflow rows: 2; fractional outflow rows: 0. The
SHA-256 digest of sorted flow-key strings was:

`54a93e2dac54eb911af150cb0a9a107ca0f56c28de950ab4da419f3c5bb9c64d`

No individual flow keys or metric values are recorded.

## RESOURCE_BASELINE

CPU was 51%; available physical RAM was 4,957,448 KB. Windows committed
memory was 20,876,296,192 of 33,272,041,472 bytes; free commit was
12,395,745,280 bytes.

## CLIENT_BOUNDS

This one replay used `max_calls=3`, `max_retries=0`, `page_size=10`,
`max_pages=3`, and `timeout_seconds=60`. No source defaults were changed and
no fourth request was made.

## REPLAY_EXECUTION

Exactly one call to `NansenIngestionOrchestrator.ingest_flows()` completed
successfully through the existing Nansen client and staging repository.

## LIVE_REQUEST_ACCOUNTING

- Replay run: `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`
- Pages requested: 3
- API attempts: 3
- Records received: 23
- Records normalized: 23

## SOURCE_COUNT_COMPARISON

Source count remained 23, matching Task 018R: `SOURCE_RECORD_COUNT_STABLE=YES`.

## ROW_COUNT_VALIDATION

After replay the target had 23 rows and 23 unique flow keys; duplicate keys:
0. Out-of-window rows: 0. Incomplete rows: 0.

## FLOW_KEY_SET_VALIDATION

After replay the sorted flow-key-set SHA-256 digest remained
`54a93e2dac54eb911af150cb0a9a107ca0f56c28de950ab4da419f3c5bb9c64d`.
The before/after digest matched. No individual flow key is included.

## LIVE_IDEMPOTENCY_RESULT

`LIVE_IDEMPOTENCY=PASS` for this exact retained window: source count, row
count, unique-key count, and flow-key-set digest were stable, and no duplicate
row was created.

## COMPLETE_WINDOW_VALIDATION

All retained target rows remained complete and within the requested window.

## NUMERIC_STRUCTURE

Fractional inflow rows were 2 before and after replay; fractional outflow
rows were 0 before and after. Fractional structure was stable. No analytical
values were selected or reported; flow upserts may refresh mutable metrics,
so this does not assert metric-value immutability.

## AUDIT_VALIDATION

The replay run is `success` with matching stream/window scope and counters:
3 pages, 3 API attempts, 23 received, and 23 normalized. Inserted/conflicted
outcome counters remain neutral zero by design and were not used as evidence
of idempotency.

## CHECKPOINT_VALIDATION

After replay, the checkpoint references the replay run and remains at
2026-09-20T23:59:59Z. The timestamp is stable; the successful run reference
advanced as expected.

## AUDIT_HISTORY

The original Task 018 audit (`8ab88f8b-327d-4183-b20d-b32697ec62b8`) remains
failed, Task 018R (`9ceff191-d65c-448b-8f3a-f7b4e7efba01`) remains success,
and the Task 019 replay run remains success. All three coexist.

## POST_REPLAY_CONSISTENCY

PASS: retained rows are unique, complete, and in-window; replay audit is
successful; checkpoint references that run at the same end timestamp; prior
failed and successful audits remain preserved.

## RESOURCE_POSTCHECK

CPU was 41%; available physical RAM was 5,617,060 KB. Windows committed
memory was 20,304,908,288 of 33,272,041,472 bytes; free commit was
12,967,133,184 bytes. No retry loop, runaway process, abnormal connection
growth, or sustained resource increase was observed; stability passed.

## DEFAULT_TESTS

`pytest -q`: 140 passed, 5 skipped before and after replay. Default tests made
zero live Nansen calls and zero PostgreSQL connections.

## PRODUCTION_SAFETY

Production DDL=0 and DML=0. Production was not accessed. No migration or DDL
was run.

## SECURITY_CHECK

No credentials, raw Nansen data, individual flow keys, wallet identities,
transaction hashes, or metric values are present. Secret scan: PASS. Tracked
`.env`: NO.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `DEV/reports/019_live_flow_idempotency_replay/report.md`
- `docs/database.md`
- `docs/operations.md`
- `docs/nansen_api.md`

No application source was changed.

## RISKS

Evidence is limited to this exact retained date, chain, token, and flow label.
The source may revise historical metrics; this task measured identity-set
stability only and did not compare metric immutability. It does not authorize
broader backfill or define reconciliation for a future changed identity set.

## NEXT_RECOMMENDED_TASK

Review this one-window replay evidence and separately decide whether to
authorize another bounded scope. Do not start broader historical ingestion or
Task 020 automatically.
