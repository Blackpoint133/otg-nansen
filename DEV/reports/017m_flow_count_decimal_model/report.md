## OBJECTIVE

Preserve Nansen flow `total_inflows_count` and `total_outflows_count` as exact
decimal numbers in the model and staging database.

## STARTING_STATE

Starting main was `49653964a47b7ca80425b38a95e7cac593497a7e`. Task 017R had
reached the final page in three requests and observed a finite fractional JSON
number in a required total count metric. No live value was retained.

## EVIDENCE_REVIEW

Current official Nansen flow response schema types both total count fields as
`number`; the integer range schema applies to request filters, not the response
wire type. The response documentation does not explicitly specify nullable or
signed restrictions for these two fields. The live fractional observation
contradicts the previous integer-only model. No live API call was made in this
task.

## MODEL_DECISION

Both total count fields now use Python `Decimal`. `holders_count` remains
integer. The optional CEX/DEX count fields remain `Optional[int]` because only
null values have been observed for the tested Smart Money label.

## NORMALIZATION_CONTRACT

The two required total fields accept JSON numeric Python values (`int` or
`float`, excluding booleans) and convert through `Decimal(str(value))`. Finite
positive, zero, negative, integral, and fractional values are preserved
without rounding or quantization. Null, strings, booleans, objects, arrays,
NaN, and infinities fail explicitly.

## SERIALIZATION_CONTRACT

Normalized model serialization emits Decimal values as deterministic decimal
strings. Synthetic precision tests verify serialization of a fractional value
without float conversion.

## PERSISTENCE_MAPPING

`map_flow()` passes both Decimal objects through unchanged. Flow identity
remains based on chain, canonical token address, scope, and date; metric values
do not participate in the key.

## FRESH_SCHEMA_CHANGE

Only `nansen.flows.total_inflows_count` and
`nansen.flows.total_outflows_count` changed in the fresh-schema definition,
from `BIGINT NOT NULL` to `NUMERIC NOT NULL`.

## STAGING_PRECHECK

Before migration, target was `server_otg_staging`, current user was
`gunz_user`, and `transaction_read_only` was off. The `nansen` schema and all
five expected tables existed, both target columns were `bigint NOT NULL`,
`nansen.flows` was owned by `gunz_user`, and the flow row count was zero.

## MIGRATION_002

The pre-DDL source commit was `5e59c21b27e8b97698ab2f45b75fcaca61eeb02d`
and was pushed before applying DDL. Migration 002 was applied through the
existing staging-pinned transactional migration guard. Migration 001 was not
rerun. The migration explicitly casts only the two columns to NUMERIC and
contains no DROP.

## STAGING_POSTCHECK

After migration, both target columns were `numeric NOT NULL`. All five Nansen
tables remained; table ownership remained `gunz_user`; flow constraints and
the schema indexes remained present. The staging flow row count remained zero
after integration cleanup.

## NUMERIC_ROUNDTRIP

The opt-in staging integration test stored synthetic positive and negative
fractional Decimal counts, read them through psycopg as Decimal, and verified
exact equality. `POSTGRES_NUMERIC_ROUNDTRIP=PASS`.

## REGRESSION_TESTS

Unit coverage verifies JSON integer and float inputs, positive and negative
fractional values, zero, exact Decimal serialization, direct persistence
mapping, and rejection of booleans, null, strings, non-finite values, objects,
and arrays. It also verifies that metric changes do not affect the flow key.

## DEFAULT_TESTS

`pytest -q`: 140 passed, 5 skipped. Default tests made zero live Nansen calls
and zero PostgreSQL connections.

## POSTGRES_TESTS

`NANSEN_RUN_POSTGRES_TESTS=1 pytest -m postgres -q`: 4 passed, 141
deselected. No Nansen request was made.

## SYNTHETIC_CLEANUP

The Task 017M numeric round-trip row was deleted by its exact flow key and
independently verified absent. Staging retained all five schema tables.

## PRODUCTION_SAFETY

Only `server_otg_staging` was used for DDL/DML. Production `server_otg` was
not connected or modified. No live data was persisted.

## RESOURCE_OBSERVATION

Baseline sample before staging migration: CPU load 57%; available RAM
4,857,220 KB. A baseline Windows commit counter was unavailable from the
initial sample. Final sample: CPU load 54%; available RAM 4,902,616 KB;
committed memory 21,088,337,920 bytes; commit limit 33,272,041,472 bytes;
free commit 12,183,703,552 bytes.

## SECURITY_CHECK

No API key, database password, credential-bearing URL, or raw Nansen response
was committed. `SECRET_SCAN=PASS`; `.env` is untracked and ignored.

## CYRILLIC_CHECK

All repository-authored content is English only. `CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

- `src/otg_nansen/models.py`
- `src/otg_nansen/normalize.py`
- `sql/001_create_nansen_schema.sql`
- `sql/002_flow_counts_numeric.sql`
- `tests/fixtures/nansen/flows_avalanche.json`
- `tests/test_normalize.py`
- `tests/test_persistence.py`
- `tests/test_postgres_integration.py`
- `docs/nansen_api.md`
- `docs/database.md`
- `docs/architecture.md`
- `docs/operations.md`
- `DEV/reports/017r_later_flow_count_contract/report.md`
- this report

## RISKS

Complete-window live normalization has not yet been repeated after the model
change. No broader historical depth or production ingestion behavior is
claimed.

## NEXT_RECOMMENDED_TASK

Authorize a bounded live revalidation of the same complete window using the
Decimal model. Do not start Task 018 before that validation and review.
