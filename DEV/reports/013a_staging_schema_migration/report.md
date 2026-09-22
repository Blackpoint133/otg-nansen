# Report 013A - Nansen staging schema migration

## OBJECTIVE

Apply the reviewed Nansen schema to `server_otg_staging` only. No integration
rows or application data were written.

## STARTING_STATE

Started from main `99ba82a60e2d3026e9c24e08be5d9ea501383966` with a clean
working tree and the reviewed migration source.

## TARGET_VERIFICATION

The guarded connection reported:

TARGET_DATABASE=server_otg_staging
CURRENT_USER=gunz_user
TRANSACTION_READ_ONLY=off

The production database was not used for migration.

## CREATE_PRIVILEGE_VERIFICATION

`has_database_privilege(current_user, current_database(), 'CREATE')` returned
true before migration.

CREATE_PRIVILEGE_BEFORE=YES
CREATE_PRIVILEGE_AFTER_MIGRATION=YES

The privilege was not revoked by this task. The operator must revoke it
manually immediately after this task.

## PRE_MIGRATION_STATE

The `nansen` schema did not exist and no `nansen.*` objects were present.

NANSEN_SCHEMA_EXISTS_BEFORE=NO
NANSEN_OBJECTS_BEFORE=NONE

## UNIT_TESTS

`pytest -q`: 91 passed, 2 opt-in tests skipped. No live Nansen calls and no
PostgreSQL integration tests were run.

## MIGRATION_EXECUTION

`python -m otg_nansen.migrate_staging` completed successfully. The command
verified the database target, used the transactional migration, applied a
five-second lock timeout and thirty-second statement timeout, and rejected
DROP statements. No ad hoc SQL was used.

## SCHEMA_VERIFICATION

NANSEN_SCHEMA_EXISTS_AFTER=YES
EXPECTED_TABLES_PRESENT=YES

The five tables present are:

- `nansen.token_information`
- `nansen.flows`
- `nansen.dex_trades`
- `nansen.ingestion_runs`
- `nansen.checkpoints`

All five tables are owned by `gunz_user`, as is the `nansen` schema.

## OWNERSHIP_VERIFICATION

NANSEN_SCHEMA_OWNER=gunz_user
TABLE_OWNER_CHECK=PASS

## CONSTRAINT_VERIFICATION

CHECKPOINT_COMPOSITE_FK=PASS
REQUEST_SCOPE_CHECK=PASS
FLOW_SCOPE_CHECKS=PASS

The composite checkpoint foreign key covers run ID and stream identity. The
strict request-scope JSON checks and endpoint-aware flow-scope checks are
present. Primary keys, the ingestion-run stream uniqueness constraint, and
expected NOT NULL constraints are present.

## INDEX_VERIFICATION

Expected primary-key indexes and lookup indexes were present, including
`nansen_flows_lookup`, `nansen_dex_trades_lookup`, and
`nansen_ingestion_runs_lookup`.

## PRODUCTION_SAFETY

The production database was checked only read-only with
`default_transaction_read_only=on`; it had no `nansen` schema.

PRODUCTION_DDL=0
PRODUCTION_DML=0
STAGING_DML=0

All staging table row counts were zero after migration. No integration data was
inserted.

## CREATE_PRIVILEGE_AFTER_MIGRATION

The temporary CREATE privilege remains present:

CREATE_PRIVILEGE_AFTER_MIGRATION=YES

## NEXT_OPERATOR_ACTION

REVOKE CREATE ON DATABASE server_otg_staging FROM gunz_user;

After revocation, a later task may run the opt-in PostgreSQL integration suite.

## SECURITY_CHECK

SECRET_SCAN=PASS
ENV_TRACKED=NO

No credentials, passwords, API keys, or connection strings were committed.

## CYRILLIC_CHECK

CYRILLIC_SCAN=PASS

## FILES_CHANGED

Only documentation and this migration evidence report were changed after the
staging migration. No application source was modified.

## NEXT_RECOMMENDED_TASK

Revoke the temporary database CREATE privilege, then run the explicit opt-in
PostgreSQL integration tests against `server_otg_staging` only. Do not touch
production.
