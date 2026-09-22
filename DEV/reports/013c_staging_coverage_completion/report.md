# Task 013C Staging Coverage Completion

## OBJECTIVE

Complete the real PostgreSQL evidence for checkpoint integrity, flow-scope
separation, Avalanche persistence identity, and transaction visibility using
only `server_otg_staging`.

## STARTING_STATE

- Starting main: `bb8afa26ecc88e851cff2e64ac19382173bebded`
- The deployed `nansen` schema was retained without migration or DDL.
- The working tree was clean before the test-harness change.

## EXTERNAL_REVIEW_FINDINGS

Task 013B had passed, but its single integration test did not independently
exercise every negative checkpoint status and stream-mismatch case claimed in
the summary. Task 013C added a dedicated real PostgreSQL test with deterministic
`task013c_` identifiers.

## SCHEMA_PRECHECK

The target reported `server_otg_staging`, user `gunz_user`, and
`transaction_read_only=off`. The schema and five expected tables existed before
testing. No migration was run.

## CHECKPOINT_RUNNING_REJECTION

An actual persisted `running` ingestion run was rejected by the repository
checkpoint guard. No checkpoint row was created.

## CHECKPOINT_FAILED_REJECTION

An actual persisted `failed` ingestion run was rejected. No checkpoint row was
created.

## CHECKPOINT_PARTIAL_REJECTION

An actual persisted `partial` ingestion run was rejected. No checkpoint row was
created.

## CHECKPOINT_WRONG_CHAIN_REJECTION

A successful run was rejected when used with a different chain identity.

## CHECKPOINT_WRONG_ENDPOINT_REJECTION

A successful flows run was rejected when used with a different endpoint.

## CHECKPOINT_WRONG_TOKEN_REJECTION

A successful run was rejected when used with a different canonical token.

## CHECKPOINT_WRONG_SCOPE_REJECTION

A successful run was rejected when used with the other flow scope. The existing
checkpoint for that other scope remained bound to its own successful run.

## FLOW_SCOPE_CHECKPOINT_SEPARATION

Separate real `task013c_smart_money` and `task013c_exchange` runs each produced
one flow row and one checkpoint. Each checkpoint referenced its matching run.
Both reciprocal cross-use attempts were rejected.

## AVALANCHE_CASE_IDEMPOTENCY

The mixed-case EVM address
`0x00000000000000000000000000000000000000Aa` and its lowercase equivalent
produced one persisted flow key and one row. The persisted token address was
lowercase, and both address forms read the same checkpoint stream.

## SUCCESS_EXTERNAL_VISIBILITY_ATOMICITY

Using a separate observer connection, the pre-commit view showed the durable
run as `running`, with no new flow and no new checkpoint. After commit, the
observer saw the flow, `success` run status, and checkpoint together.

## REQUEST_SCOPE_MATRIX

The existing real PostgreSQL matrix remained enabled and passed for missing
keys, JSON null values, wrong JSON types, non-object roots, scalar mismatches,
and endpoint-specific flow-scope rules.

## DEFAULT_TESTS

`pytest -q`: 91 passed, 3 skipped. Default tests made zero PostgreSQL
connections and zero live Nansen calls.

## POSTGRES_INTEGRATION_TESTS

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q`: 2 passed, 92 deselected.
No Nansen API calls were made.

## TEST_DATA_CLEANUP

Independent post-test queries found zero `task013c_` rows in flows,
checkpoints, and ingestion runs, and zero Task 013C trade or token rows. No
Task 012 rows were targeted by the Task 013C cleanup.

## SCHEMA_POSTCHECK

The `nansen` schema and all five tables remained present. Owners remained
`gunz_user`; primary keys, indexes, scope checks, and both deployed checkpoint
foreign keys remained present.

## OWNER_PRIVILEGE_POLICY

CREATE remained `YES` for `gunz_user` on `server_otg_staging`, consistent with
the owner-approved persistent staging-only policy. No additional privilege was
granted and no privilege was revoked.

## PRODUCTION_SAFETY

Production `server_otg` was checked read-only and still had no `nansen` schema.
Production DDL=0 and production DML=0.

## SECURITY_CHECK

No secrets, credentials, API keys, authorization headers, or `.env` values were
committed. `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

Repository-authored text scan: PASS. All authored content is English only.

## FILES_CHANGED

- `tests/test_postgres_integration.py`
- `DEV/reports/013b_staging_postgres_validation/report.md` addendum
- this report

## RISKS

The staging CREATE privilege remains intentionally persistent by owner
decision. The integration harness is opt-in and must remain pointed only at
staging.

## NEXT_RECOMMENDED_TASK

Review this evidence, then implement a bounded fixture-backed ingestion
orchestration layer. Do not begin production ingestion or historical backfill.
