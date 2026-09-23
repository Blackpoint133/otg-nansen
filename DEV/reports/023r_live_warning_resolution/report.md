# Task 023R: Live warning semantic resolution

## OBJECTIVE

Inspect one live Flows warning without retaining or printing its text, and
resolve the Task 023 classifier mismatch only if its exact semantics can be
confirmed safely.

## STARTING_STATE

Repository `parsers/parser_nansen`, branch `main`, started at
`1cf2035e0e162274550288a888cf98abf3e25f6e` with a clean worktree. Baseline
`pytest -q` passed: 164 passed, 6 skipped. Baseline live API calls and
PostgreSQL connections were both zero.

## TASK023_BLOCKER

Task 023 had one live warning classified as `UNKNOWN`. Its original outcome
remains `LIVE_WARNING_CONTRACT_MISMATCH`; this report records Task 023R as a
separate continuation and does not rewrite the earlier result.

## AUTHORITATIVE_SOURCE_RESEARCH

The current official Flows page and its OpenAPI response schema were checked.
They document an optional warning array of strings, and state that a warning
entry is included when the four CEX/DEX breakdown fields are null for a
non-exchange label. The schema names those fields and says they are populated
only for `exchange`; its warning schema example is a placeholder, not
canonical wording. The current API changelog contains no canonical warning
representation. Searches of the official Nansen CLI repository and changelog
found no canonical Flows warning string or API response contract. The Nansen
CLI is not installed locally; no Nansen Python distribution or local API
OpenAPI artifact was found.

`AUTHORITATIVE_CANONICAL_WARNING_FOUND=NO`

References: <https://docs.nansen.ai/api/token-god-mode/flows>,
<https://docs.nansen.ai/api/changelog>, and
<https://github.com/nansen-ai/nansen-cli>.

## CLASSIFIER_DECISION

The current speculative regex matcher was not broadened or replaced. The
source tree was restored to the clean starting commit after offline design
experiments. No production fingerprint was pinned because the one-time
semantic gate below remained unresolved.

## RAW_WARNING_HANDLING_POLICY

The warning was held only in the request process memory. It was not printed,
written to disk, added to a fixture, placed in an exception, or sent to
PostgreSQL. Only the authorized SHA-256, UTF-8 byte length, booleans, and
public schema field names are recorded here.

## LIVE_REQUEST_SCOPE

One bounded read-only `POST /api/v1/tgm/flows` request used the specified
Avalanche `smart_money` historical day, page 1, `per_page=1000`, ascending
date order, `max_calls=1`, `max_retries=0`, `max_pages=1`, and 120-second
timeout. No records were persisted. No second request was made.

## LIVE_SAFE_WARNING_EVIDENCE

```text
LIVE_API_CALLS_TASK023R=1
LIVE_WARNING_COUNT=1
LIVE_WARNING_SHA256=50a9e595fb2d539dbf5aade57b0dfba8b440f00841933c87a3335644dca23912
LIVE_WARNING_UTF8_LENGTH=245
WARNING_REFERENCES_CEX=YES
WARNING_REFERENCES_DEX=YES
WARNING_REFERENCES_EXCHANGE_LABEL=YES
WARNING_REFERENCES_NON_EXCHANGE_CONDITION=NO
WARNING_REFERENCES_NULL_OR_UNAVAILABLE_BREAKDOWN=YES
WARNING_REFERENCED_PUBLIC_FIELDS=total_inflows_cex,total_inflows_dex,total_outflows_cex,total_outflows_dex
```

No raw wording or surrounding text was retained. No truncation, partial,
error, range-limit, aggregation-loss, or downsampling semantics were detected
by the one-time safe inspection.

## LIVE_SEMANTIC_INSPECTION

The warning referenced CEX and DEX, the exchange label, unavailable/null
breakdowns, and all four documented public field names. However, the bounded
inspection did not confirm an explicit non-exchange condition in the warning.
The docs and requested label alone are insufficient to prove that the warning
itself refers only to the documented benign condition.

`LIVE_WARNING_SEMANTIC_MATCH=NO`
`TASK_023R_STATUS=WARNING_SEMANTICS_UNRESOLVED`

## BREAKDOWN_FIELD_STRUCTURE

All four optional breakdown fields were present and null across every returned
flow record. No field values or record metrics were recorded.

`LIVE_BREAKDOWN_FIELDS_ALL_NULL=YES`

## WARNING_FINGERPRINT

The exact SHA-256 above is retained as safe diagnostic evidence only. It was
not added to the production allowlist because semantic acceptance failed.

`WARNING_FINGERPRINT_PINNED=NO`

## SAME_LIVE_OBJECT_CLASSIFICATION

The original in-memory warning was not reclassified as benign; the exact
fingerprint was not approved. No second request was made.

`SAME_LIVE_OBJECT_REVALIDATION=NOT_AVAILABLE`
`SAME_LIVE_WARNING_CLASSIFICATION=UNKNOWN`

## OFFLINE_TESTS

The required baseline suite passed before any edits: 164 passed, 6 skipped.
The production matcher and test files were restored to the clean baseline
after classifier testability experiments. No post-request source change was
made. Default tests made zero live calls and zero PostgreSQL connections.

## WARNING_CLASSIFIER_SOURCE_COMMIT

None. The unresolved semantic gate prohibited classifier changes and source
publication. HEAD remains `1cf2035e0e162274550288a888cf98abf3e25f6e`.

## STAGING_PREFLIGHT

Not run. No PostgreSQL connection was opened.

## MIGRATION_004_EXECUTION

`MIGRATION_004_EXECUTED=NO`.

## POST_MIGRATION_SCHEMA

Not applicable. Migration 004 was not applied.

## LEGACY_WARNING_STATE

No database connection or write occurred. Legacy rows were not changed or
queried; `source_warnings` remains unapplied on staging.

## POSTGRES_WARNING_AUDIT

Not run. The explicit semantic stop condition requires stopping before
migration and physical PostgreSQL tests.

## RETAINED_DATA_INTEGRITY

No database connection or DML occurred. The accepted retained flow state was
not changed by this task; it was not requeried.

## CHECKPOINT_INTEGRITY

No database connection or checkpoint write occurred. The accepted checkpoint
was not requeried.

## AUDIT_HISTORY

No database connection or audit write occurred. Existing audit history was
not changed or requeried.

## RESOURCE_OBSERVATION

CPU, physical RAM, and Windows commit metrics were not collected.
`RESOURCE_STABILITY=NOT_ASSESSED`.

## PRODUCTION_SAFETY

`PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`. Staging DDL
and DML were also zero.

## SECURITY_CHECK

The report contains no raw warning text, API response, credential, `.env`
content, wallet address, transaction hash, or analytical metric value.
`ENV_TRACKED=NO`.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

Only the Task 023R report and the Task 023 report addendum are intended to be
committed. Application source, schema, classifier, tests, and documentation
remain at the starting baseline.

## RISKS

The safe semantic inspection did not confirm the non-exchange relation in the
warning itself. The fingerprint is not approved, so the warning remains
unknown and fail-closed ingestion would still reject it. Migration 004,
staging validation, physical warning tests, and retained-state rechecks remain
pending.

## NEXT_RECOMMENDED_TASK

Ask Nansen support to confirm what the recorded fingerprint represents, using
the fingerprint and public schema field names only. Do not send or publish the
raw warning. After authoritative semantic confirmation, continue with a
separately authorized fingerprint pin and staging migration. Do not start
historical backfill or Task 024.
