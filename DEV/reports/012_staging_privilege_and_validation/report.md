# Report 012 - Staging privilege and validation recovery

## TASK_012_STATUS

BLOCKED_STAGING_PRIVILEGE

## LOCAL_STATE

Task 012 was not present locally at recovery start. The repository was clean at
Task 011 commit `f41584671476161e5052f56671d9609811995494`.

## SOURCE_FIXES

The Task 012 source hardening now requires the migration request scope to be a
JSON object with all four required string keys: `chain`, `endpoint`,
`token_address`, and `flow_label`. The complete predicate is explicitly
required to be TRUE, rejecting missing keys, JSON nulls, wrong JSON types, and
mismatched scalar values.

The opt-in integration harness uses a deterministic Task 012 trade identity,
tests separate flow checkpoints, covers invalid request scopes including
non-flow scope violations, and asserts cleanup for flows, DEX trades, token
snapshots, checkpoints, and ingestion runs.

## DATABASE_PREFLIGHT

The connection was pinned to `server_otg_staging` and reported PostgreSQL
18.3. The `nansen` schema and expected objects were absent. The role was
`gunz_user`; no password or connection secret was exposed.

NANSEN_SCHEMA_EXISTS_BEFORE=NO
CURRENT_DATABASE=server_otg_staging
CURRENT_ROLE_CREATE_BEFORE=NO
TEMP_CREATE_GRANTED=NO
TEMP_CREATE_REVOKED=NOT_APPLICABLE
MIGRATION_EXECUTED=NO
POSTGRES_INTEGRATION_TESTS_RUN=NO

## BLOCKER

No legitimate administrative path was available. The minimum required
privilege is:

`GRANT CREATE ON DATABASE server_otg_staging TO gunz_user;`

That grant was not performed by this task. No password reset, `pg_hba.conf`
change, trust authentication, superuser creation, or workaround was attempted.

## PRODUCTION_SAFETY

Production `server_otg` was checked only with a read-only connection and had
no `nansen` schema. No production DDL or DML occurred.

PRODUCTION_DDL=0
PRODUCTION_DML=0

## TESTS

`pytest -q`: 85 passed, 2 opt-in tests skipped. Default tests made zero live
Nansen calls and zero PostgreSQL connections. The real PostgreSQL integration
suite remains blocked before migration because staging CREATE privilege is
absent.

LIVE_API_CALLS_TASK012=0
DEFAULT_TESTS_POSTGRES_CONNECTIONS=0

## SECURITY

CYRILLIC_SCAN=PASS
SECRET_SCAN=PASS
ENV_TRACKED=NO

## COMMITS

The Task 012 source/report publication commit is the final commit for this
recovery and was pushed normally. No published history was amended and no
force push was used.

## NEXT_RECOMMENDED_TASK

An authorized PostgreSQL administrator should grant CREATE on
`server_otg_staging` to `gunz_user`, then rerun only the guarded migration and
opt-in integration suite. Production must remain untouched.

## TASK 012R ADDENDUM

External review found that the DEX cleanup predicate did not match the Task
012 trade identifier, the integration source did not cover all JSON null/type
and non-object request-scope cases, checkpoint advancement trusted caller-
supplied status, and a checkpoint could reference a run from another flow
scope.

Task 012R corrected these issues before any PostgreSQL migration execution.
Synthetic data uses exact Task 012 identifiers with FK-safe cleanup. The
integration harness now contains the complete request-scope invalid-case
matrix, separate matching smart-money and exchange runs/checkpoints, and
cleanup assertions for every table. The public checkpoint API and SQL now
validate actual successful run status and exact stream identity; a composite
foreign key prevents cross-stream references. The staging CREATE privilege
blocker remains unchanged.
