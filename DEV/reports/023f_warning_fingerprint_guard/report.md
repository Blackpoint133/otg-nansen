# Task 023F: Warning Fingerprint and Structural Guard

## OBJECTIVE

Replace text-pattern warning acceptance with the exact observed SHA-256 fingerprint, enforce the documented normalized null-breakdown structure, and complete migration 004 on staging.

## STARTING_STATE

Starting main was `95436306fcd095ec2ac125c09bf762300a123ed1`, clean. Default baseline tests passed: 164 passed, 6 skipped. Migration 004 was absent from staging.

## TASK023_AND_023R_EVIDENCE

Task 023 failed closed on an unknown live warning. Task 023R recorded safe semantic evidence and fingerprint but remained unresolved under its stricter textual gate. The exact fingerprint used here is `50a9e595fb2d539dbf5aade57b0dfba8b440f00841933c87a3335644dca23912`; no raw warning text or object is retained.

## ARCHITECTURE_DECISION

Use exact decoded-string SHA-256 matching, restricted to TGM Flows `smart_money`. Require all four normalized CEX/DEX breakdown fields to be null across every returned record before persistence. Any changed wording, wrong context, structural mismatch, or extra unknown warning fails closed.

## EXACT_FINGERPRINT_POLICY

The production allowlist contains only the accepted fingerprint mapped to `NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`. Matching uses `sha256(raw_warning.encode("utf-8")).hexdigest()` without text normalization. The code comment records endpoint/scope/date provenance and that wording is intentionally not retained.

## CONTEXT_RESTRICTION

The category is a candidate only for endpoint `flows` and label `smart_money`. Wrong endpoint or label is `UNKNOWN`.

## STRUCTURAL_GUARD

After normalization and before `begin_data_transaction()`, every record is checked for null `total_inflows_cex`, `total_inflows_dex`, `total_outflows_cex`, and `total_outflows_dex`. A benign warning with no returned records fails closed because there is no structural evidence.

## MULTIPLE_WARNING_POLICY

Warnings are classified individually across every page. Duplicate exact warnings retain their warning count. Any unknown warning rejects the entire run and the audit retains sanitized `UNKNOWN` evidence.

## UNKNOWN_WARNING_POLICY

Unknown or structurally mismatched warnings fail before flow persistence and checkpoint advancement. Error and audit content includes only safe endpoint/page/count/category data.

## OFFLINE_TESTS

Fingerprint edits in case, whitespace, punctuation, or characters classify as unknown. Synthetic tests cover injected allowlist behavior, wrong context, unlisted values, duplicate warnings, mixed warnings, every individual non-null breakdown field, unknown-warning atomicity, and audit sanitization. Before live validation: `pytest -q` => 180 passed, 6 skipped; live API calls 0; PostgreSQL connections 0.

## LIVE_REVALIDATION

Exactly one read-only request was made to the authorized Flows endpoint scope and represented historical day using page 1, 1000 records, zero retries, one call, one page, and a 120-second timeout. No response was persisted.

## LIVE_STRUCTURAL_EVIDENCE

`LIVE_API_CALLS=1`; `LIVE_WARNING_COUNT=1`; `LIVE_WARNING_SHA256_MATCH=YES`; `LIVE_WARNING_CATEGORIES=NON_EXCHANGE_BREAKDOWN_UNAVAILABLE`; `LIVE_BREAKDOWN_FIELDS_ALL_NULL=YES`; `LIVE_STRUCTURAL_GUARD=PASS`; `LIVE_WARNING_POLICY_RESULT=PASS`; `LIVE_IS_LAST_PAGE=YES`; `LIVE_RECORD_COUNT=23`. Only sanitized evidence is recorded.

## SOURCE_COMMIT

`PRE_MIGRATION_SOURCE_SHA=24c9eda20145e47a753a1e174327f5e8115ce623`, commit `fix: pin verified nansen flow warning`, pushed and read back from origin before DDL.

## STAGING_PREFLIGHT

Verified `current_database=server_otg_staging`, `current_user=gunz_user`, `transaction_read_only=off`. Before DDL, `source_warnings` was absent; 4 ingestion audit rows existed, all predating warning capture. Retained flow state was 52 total, 23 recent, and 29 early. Checkpoint UTC timestamp was `2026-09-20T23:59:59Z`, run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## MIGRATION_004_EXECUTION

`sql/004_ingestion_source_warnings.sql` was applied with the staging-pinned migration guard. No other migration was run.

## POST_MIGRATION_SCHEMA

`source_warnings` is nullable `jsonb`; the array-or-null CHECK exists.

## LEGACY_WARNING_STATE

All 4 existing ingestion runs remain `source_warnings IS NULL`. Warning-free inspected runs store `[]`.

## POSTGRES_WARNING_AUDIT

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q` => 5 passed, 181 deselected. Physical integration coverage round-tripped `[]`, benign and unknown summaries, allowed NULL, rejected non-array JSON, and checked rollback/checkpoint behavior. Synthetic cleanup assertions passed; no live API calls came from tests.

## RETAINED_DATA_INTEGRITY

After migration and tests, flow rows remained 52 total, 23 recent, and 29 early. `RETAINED_FLOW_STATE_UNCHANGED=PASS`.

## CHECKPOINT_INTEGRITY

The checkpoint remained `2026-09-20T23:59:59Z` with run `1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. `CHECKPOINT_UNCHANGED=PASS`.

## AUDIT_HISTORY

All 4 pre-existing runs retained the same run IDs, statuses, windows, counters, and error fields, and remained NULL for `source_warnings`. The safe before/after audit-history digest was identical: `14ee45136704faedc3c30b0f5672ba04125426ae3b8d992e3666015cfb960034`.

## RESOURCE_OBSERVATION

Before: CPU sample 5.4%; available RAM 4,433 MB; committed memory 21,046 MB; commit limit 31,730 MB; free commit 10,684 MB. After: CPU sample 31.8%; available RAM 4,594 MB; committed memory 20,835 MB; commit limit 31,730 MB; free commit 10,895 MB. Resource state remained stable.

## DEFAULT_TESTS

After migration: `pytest -q` => 180 passed, 6 skipped; live API calls 0; PostgreSQL connections 0.

## PRODUCTION_SAFETY

`PRODUCTION_DDL=0`; `PRODUCTION_DML=0`; `PRODUCTION_CHANGED=NO`. Migration 004 was staging-only. No backfill or service was started.

## SECURITY_CHECK

`SECRET_SCAN=PASS`; `ENV_TRACKED=NO`. No raw warning text/object, raw response, credential, wallet, transaction hash, or analytical metric was written into source, test fixtures, report, or audit.

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

Source commit: `src/otg_nansen/source_warnings.py`, `src/otg_nansen/ingestion.py`, `tests/test_source_warnings.py`, `tests/test_ingestion.py`, and the five requested documentation files. Evidence commit: Task 023 and 023R report addenda and this report. Migration 004 was already present from Task 023 and was applied without modification.

## RISKS

The fingerprint accepts only the exact observed wording and the tightly scoped documented structure. Any wording change or non-null breakdown value fails closed. Evidence covers one request/window only and does not establish broader history or other labels.

## NEXT_RECOMMENDED_TASK

Review Task 023F acceptance and consider a separately scoped historical-ingestion readiness task. Do not start historical backfill or Task 024 automatically.
