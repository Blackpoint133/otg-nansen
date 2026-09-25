# Task 035: Meridian Submission Readiness and API-Call Audit

## OBJECTIVE

Assess submission readiness for the Nansen Meridian Buildathon without making
any Nansen request. The work reconciles the in-window request count, checks
the committed Task 034 result artifacts, and updates judge-facing preparation
documents.

## STARTING_STATE

Repository `C:/VAMBAM/Projects/OTG/parsers/parser_nansen`, branch `main`,
started clean and synchronized at `f95cfb92bc408ee497057449c62c51e8adbcb4ca`.
No production connection was made. Staging reads used the pinned read-only
connection. No RPC or Nansen request was made.

## BASELINE_TESTS

Before documentation edits, `pytest -q` passed: **281 passed, 6 skipped**.
Default tests do not connect to PostgreSQL or the network. Analytics source,
tests, and Task 034 artifacts were not changed.

## OFFICIAL_REQUIREMENT_CONFLICT

As checked on 2026-09-25, the [main campaign page](https://nansen.ai/campaigns/meridian-buildathon)
states 1,000 API calls. The [Nansen Meridian FAQ](https://release.nansen.ai/help/articles/3540155-nansen-meridian-buildathon-sep-14-27),
updated two days before this audit, states 100+ calls between Sep 14 and Sep
27 and says calls before Sep 14 do not count. Both give the deadline as Sep
27, 23:59 UTC. The official-source conflict is preserved; this report does
not infer which threshold governs.

## BUILDATHON_WINDOW

The SQL audit used the half-open UTC interval
`[2026-09-14T00:00:00Z, 2026-09-28T00:00:00Z)`. The exclusive end represents
the full Sep 27 UTC submission day.

## AUDIT_SCHEMA

Read-only inspection verified `current_database=server_otg_staging` and
`transaction_read_only=on`. The actual audit relation is
`nansen.ingestion_runs`. Relevant PostgreSQL columns and types:

| Field | Type | Interpretation |
|---|---|---|
| `run_id` | `uuid` | Persisted ingestion-run identity. |
| `started_at` | `timestamp with time zone` | Run start; used for UTC window inclusion. |
| `finished_at` | `timestamp with time zone`, nullable | Completion time when available. |
| `status` | `text` | Run success/failure status. |
| `chain` | `text` | Chain scope. |
| `endpoint` | `text` | Endpoint/stream family. |
| `flow_label` | `text` | Flow label where applicable. |
| `pages_requested` | `integer` | Response pages fetched, not HTTP attempts. |
| `api_calls` | `integer` | Count of Nansen HTTP request attempts for the run. |
| `records_received`, `records_normalized` | `integer` | Response and normalized record counts. |
| `request_scope` | `jsonb` | Sanitized request scope. |

The table also has nullable UTC request-window bounds, token scope, inserted
and conflicted counters, error class/summary, and sanitized source-warning
metadata. No key, request body, or raw payload was selected. Source review of
`src/otg_nansen/ingestion.py` and its persistence path confirms that
`api_calls` is the delta in `requests_attempted`; it includes failed attempts
and retries. This is the best persisted measure of HTTP API requests.

## AUDITED_API_CALLS

| Status | Endpoint / stream | Runs | API attempts | Pages | Records received |
|---|---|---:|---:|---:|---:|
| success | `flows` / `smart_money` | 78 | 82 | 82 | 12,578 |
| failed | `flows` / `smart_money` | 3 | 3 | 0 | 0 |
| **Total** | | **81** | **85** | **82** | **12,578** |

`SUCCESSFUL_RUN_API_ATTEMPTS=82`; `FAILED_RUN_API_ATTEMPTS=3`.
`EARLIEST_COUNTED_RUN_UTC=2026-09-23T08:17:25.889112Z`;
`LATEST_COUNTED_RUN_UTC=2026-09-24T10:04:19.555173Z`. All persisted runs were
inside the eligible window. The all-time audit table had the same 81 runs and
85 attempts, so there were no older audit rows to subtract or newer rows to
exclude.

## NON_AUDITED_CALL_RECONCILIATION

Reports document bounded direct requests made before the durable audit path
or outside ingestion orchestration. They are separate from the 85 persisted
attempts. Counts below are explicit task totals, not re-counted mentions in
later addenda. Report/task commit chronology bounds these requests to Sep
19–23 UTC, inside the window.

| Task/report | Date supported | Calls | Classification | Reason |
|---|---|---:|---|---|
| 003 Phase 0B reconnaissance | Sep 19–21, 2026 | 12 | `EXPLICIT_NON_AUDITED_CALL` | Report records 12 bounded endpoint probes; the request window was Sep 19–20 and report execution/commit was Sep 21. No ingestion audit path existed for these probes. |
| 015 Avalanche contract probe | Sep 22, 2026 | 3 | `EXPLICIT_NON_AUDITED_CALL` | Three direct endpoint attempts; no DB/audit operation. |
| 016 flow normalization diagnostic | Sep 22, 2026 | 1 | `EXPLICIT_NON_AUDITED_CALL` | One direct flow request; not persisted as an ingestion run. |
| 016V flow revalidation | Sep 22, 2026 | 1 | `EXPLICIT_NON_AUDITED_CALL` | One direct request; no ingestion audit. |
| 017 complete flow-window probe | Sep 22–23, 2026 | 3 | `EXPLICIT_NON_AUDITED_CALL` | Three direct pagination requests; no persistence. |
| 017V decimal-window revalidation | Sep 23, 2026 | 3 | `EXPLICIT_NON_AUDITED_CALL` | Three direct requests; no audit run. |
| 017R later-page diagnostic | Sep 23, 2026 | 3 | `EXPLICIT_NON_AUDITED_CALL` | Three direct diagnostic requests; no staging audit. |
| 021 granularity probe | Sep 23, 2026 | 2 | `EXPLICIT_NON_AUDITED_CALL` | Two direct narrow-window probes; report confirms staging state unchanged. |
| 023 warning boundary | Sep 23, 2026 | 1 | `EXPLICIT_NON_AUDITED_CALL` | One direct warning-semantics request; report says no database connection/audit write. |
| 023R warning inspection | Sep 23, 2026 | 1 | `EXPLICIT_NON_AUDITED_CALL` | One direct request; report explicitly says no audit write. |
| 023F fingerprint revalidation | Sep 23, 2026 | 1 | `EXPLICIT_NON_AUDITED_CALL` | One direct request before migration; staging audit history remained unchanged. |
| 018, 018R, 019, 020, 024, 027–032 | Sep 23–24, 2026 | Included in audited total | `AUDIT_RECORDED` | Orchestrated ingestion attempts have durable run records; later report mentions are not added again. |
| Task 025 boundary probe | Sep 23, 2026 | 1 | `EXPLICIT_NON_AUDITED_CALL` | One direct shifted-window request; report confirms no run was created. |

Explicit non-audited requests sum to **32**. No unresolved report-level call
count was added as an ambiguous possible call. Calls from Tasks 003 and
015–017 are included because their dated evidence places them within the
Buildathon window, even though the focused later-task review begins at Task
018.

## MINIMUM_CONFIRMED_CALL_COUNT

`AUDITED_COUNT=85`

`EXPLICIT_NON_AUDITED_ADDITIONAL_COUNT=32`

`MINIMUM_CONFIRMED_BUILDATHON_CALLS=117`

`AMBIGUOUS_POSSIBLE_ADDITIONAL_CALLS=0`

The conservative total is the audited count plus explicit, in-window calls
that are not represented by the run-audit table. It does not include
pre-Sep-14 activity, duplicate report references, page counts, or ambiguous
mentions.

## 100_CALL_THRESHOLD_STATUS

`MEETS_100_CALL_THRESHOLD=YES`; `CALLS_REMAINING_TO_100=0`.

## 1000_CALL_THRESHOLD_STATUS

`MEETS_1000_CALL_THRESHOLD=NO`; `CALLS_REMAINING_TO_1000=883`.

No request was made to increase either count. Since the official pages
conflict, eligibility should not be claimed until the requirement is
clarified.

## CALL_QUALITY

The 85 audited attempts belong to historical Avalanche `flows` /
`smart_money` ingestion: 82 attempts produced 82 pages and 12,578 received
records across successful runs; 3 failed attempts yielded no page or record.
The 32 non-audited calls cover endpoint/schema reconnaissance, pagination and
boundary behavior, flow normalization, and warning-contract validation.
Failures remain counted as attempts, not successful data integrations. No
synthetic/no-op traffic was used or recommended.

## TASK034_ARTIFACT_INTEGRITY

The committed artifacts remain at the accepted state: 48 relationship rows,
24 event-summary rows, and 12,336 source rows. The summary JSON records
snapshot digest `9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8`,
relationship digest `81004c088b886eee4289151803a18c27d8ee4a75132f178ce6a8be584b1831ef`,
event digest `5f3e89ed359275c65977acaf02ad45d14b2a8329fcc4902c8e3b590396bff772`,
and summary digest `e7a16b3b2a84c15d20b5ce019e7463357b06513b60ed7e48754113df2e844e74`.
The relationship logical-row digest was rechecked against the committed CSV;
the summary JSON digest and expected metadata match the accepted Task 034
report. The CSV/JSON files were not edited.

## README_UPDATE

Replaced the early-project README with the current ingestion, hourly dataset,
preregistered analysis, reproduction command, safety boundaries, current
descriptive result, and pending presentation-layer status. It avoids any
eligibility claim.

## SUBMISSION_CHECKLIST

The repository is public. The minimum confirmed request count meets the FAQ's
100-call threshold but does not meet the campaign page's 1,000-call
threshold. API-key validity was not tested or inspected. A working judge-
facing demo, recording, X post, and entry-form submission remain pending.
The detailed checklist is in `docs/meridian_submission.md`.

## JUDGING_CRITERIA_MAPPING

- **Data Integration:** real Nansen Smart Money history informs the aligned
  data and fixed analysis drivers; no live display exists yet.
- **Functionality & Workability:** ingestion and read-only analysis are
  implemented and tested; an integrated demo is absent.
- **Creativity & Originality:** the OTG marketplace comparison is a specific
  descriptive use case; no user-facing product surface exists.
- **Documentation & Submission:** updated README, methodology, and aggregate
  reports are present; recording and submission steps remain open.

## DEMO_SURFACE_AUDIT

Repository search found no UI framework, HTML/CSS/JS screen, chart package,
public HTTP route, or integrated demo command. Existing CLIs perform backend
ingestion or read-only analysis; they do not constitute a judge-facing demo.

`LIVE_NANSEN_DEMO_SURFACE_EXISTS=NO`

`RELATIONSHIP_VISUALIZATION_EXISTS=NO`

`EVENT_STUDY_VISUALIZATION_EXISTS=NO`

`PUBLIC_WEB_INTEGRATION_EXISTS=NO`

`ONE_COMMAND_DEMO_EXISTS=NO`

## DEMO_STORYBOARD

Created `docs/meridian_demo_script.md`, a silent 45-second storyboard. It
specifies a problem statement, visibly live Nansen card, historical OTG
comparison, price-shock response view, transparent weak/inconsistent result,
and GitHub identity. Every unbuilt screen and live-data surface is marked
`PENDING_IMPLEMENTATION`; it does not describe the storyboard as an existing
UI.

## CURRENT_GAPS

The largest submission gap is an end-to-end presentation surface. The live
Nansen data is currently ingested through backend tools but is not visible in
a running judge-facing application. Historical results are CSV/JSON and a
report, not charts. Recording, X post, entry form, and threshold clarification
also remain outstanding.

## NEXT_IMPLEMENTATION_MILESTONE

Build one local read-only demo shell that joins (1) one bounded, current Nansen
`$GUN` observation served by a backend-only request adapter and (2) the
committed Task 034 historical aggregate results. Proposed files are
`src/otg_nansen/demo_app.py` (local HTTP routes and server),
`src/otg_nansen/demo_data.py` (digest-checked historical CSV/JSON loading),
and `web/demo.html`, `web/demo.js`, `web/demo.css` (screen and charts).
Proposed read-only routes are `/api/live-gun` and `/api/history`; keep the API
key server-side, bound/label the live request, and never persist it. This is a
future task and requires separately authorized live API use. Keep the data
adapter independent so `otgostest.run.place` can consume it later. No part of
this milestone was implemented here.

## FINAL_TESTS

After documentation changes, `pytest -q` passed with the same baseline count:
**281 passed, 6 skipped**. No database, Nansen, or RPC calls came from the
suite.

## DATABASE_SAFETY

Staging reads only: `server_otg_staging`, `transaction_read_only=on`.
`STAGING_DDL=0`; `STAGING_DML=0`. Production connections=0; production
DDL/DML=0.

## NANSEN_API_PROOF

`NANSEN_API_CALLS_TASK035=0`. No API key value or request payload was read.

## RPC_PROOF

`ONCHAIN_RPC_CALLS_TASK035=0`.

## SECURITY_CHECK

No credentials, request payloads, wallet identities, or source rows were
added. The ignored local `.env` is not tracked; its values were not inspected.
Final secret scan: PASS; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS` for changed files.

## FILES_CHANGED

- `README.md`
- `docs/meridian_submission.md`
- `docs/meridian_demo_script.md`
- `DEV/reports/035_meridian_submission_readiness/report.md`

No analytics source, tests, or Task 034 artifacts changed.
