"""Guarded, staging-only migration to bucket-aware Nansen flow identities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg

from .flow_identity_migration import plan_flow_key_migration
from .postgres import ALLOWED_STAGING_DATABASE, staging_connection_kwargs, verify_staging_target


EXPECTED_USER = "gunz_user"
MIGRATION_PATH = Path(__file__).parents[2] / "sql" / "003_flow_bucket_identity.sql"


def _check_preconditions(connection: psycopg.Connection[Any]) -> tuple[list[dict[str, Any]], int]:
    identity = verify_staging_target(connection)
    if identity["database"] != ALLOWED_STAGING_DATABASE or identity["user"] != EXPECTED_USER:
        raise RuntimeError("refusing unexpected staging database identity")
    if identity["transaction_read_only"] != "off":
        raise RuntimeError("staging migration requires a writable transaction")

    total = connection.execute("SELECT count(*) FROM nansen.flows").fetchone()[0]
    null_end = connection.execute("SELECT count(*) FROM nansen.flows WHERE bucket_end IS NULL").fetchone()[0]
    invalid_interval = connection.execute(
        "SELECT count(*) FROM nansen.flows WHERE bucket_end <= date"
    ).fetchone()[0]
    duplicates = connection.execute(
        """SELECT count(*) FROM (
             SELECT chain, token_address, flow_label, date, bucket_end
             FROM nansen.flows GROUP BY chain, token_address, flow_label, date, bucket_end
             HAVING count(*) > 1
           ) duplicate_groups"""
    ).fetchone()[0]
    if null_end or invalid_interval or duplicates:
        raise RuntimeError("flow identity migration preconditions failed")
    rows = connection.execute(
        "SELECT flow_key, chain, token_address, flow_label, date, bucket_end FROM nansen.flows"
    ).fetchall()
    names = ("flow_key", "chain", "token_address", "flow_label", "date", "bucket_end")
    return [dict(zip(names, row)) for row in rows], total


def apply_flow_identity_migration() -> dict[str, Any]:
    """Apply migration 003 and full key remap atomically to staging only."""
    kwargs = staging_connection_kwargs()
    if kwargs["dbname"] != ALLOWED_STAGING_DATABASE:
        raise RuntimeError("migration target is not the allowed staging database")
    with psycopg.connect(**kwargs, autocommit=False) as connection:
        try:
            connection.execute("SET LOCAL lock_timeout = '5s'")
            connection.execute("SET LOCAL statement_timeout = '60s'")
            connection.execute("LOCK TABLE nansen.flows IN ACCESS EXCLUSIVE MODE")
            rows, count_before = _check_preconditions(connection)
            plan = plan_flow_key_migration(rows)

            migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
            upper = migration_sql.upper()
            if any(word in upper for word in ("DROP TABLE", "DELETE", "TRUNCATE")):
                raise RuntimeError("migration safety guard rejected destructive SQL")
            for statement in migration_sql.split(";"):
                if statement.strip():
                    connection.execute(statement)

            for (old_key, _), temporary_key in zip(plan.old_to_new, plan.temporary_keys):
                connection.execute("UPDATE nansen.flows SET flow_key = %s WHERE flow_key = %s", (temporary_key, old_key))
            for temporary_key, (_, new_key) in zip(plan.temporary_keys, plan.old_to_new):
                connection.execute("UPDATE nansen.flows SET flow_key = %s WHERE flow_key = %s", (new_key, temporary_key))

            count_after = connection.execute("SELECT count(*) FROM nansen.flows").fetchone()[0]
            if count_after != count_before:
                raise RuntimeError("flow row count changed during identity migration")
            keys_after = connection.execute(
                "SELECT flow_key, chain, token_address, flow_label, date, bucket_end FROM nansen.flows"
            ).fetchall()
            after_names = ("flow_key", "chain", "token_address", "flow_label", "date", "bucket_end")
            after_rows = [dict(zip(after_names, row)) for row in keys_after]
            after_plan = plan_flow_key_migration(after_rows)
            if any(old != new for old, new in after_plan.old_to_new):
                raise RuntimeError("flow key uniqueness verification failed")
            if connection.execute("SELECT count(*) FROM nansen.flows WHERE bucket_end IS NULL OR bucket_end <= date").fetchone()[0]:
                raise RuntimeError("flow bucket interval verification failed")
            if connection.execute(
                """SELECT count(*) FROM (
                     SELECT chain, token_address, flow_label, date, bucket_end
                     FROM nansen.flows GROUP BY chain, token_address, flow_label, date, bucket_end
                     HAVING count(*) > 1
                   ) duplicate_groups"""
            ).fetchone()[0]:
                raise RuntimeError("natural flow identity uniqueness verification failed")
            connection.commit()
            return {
                "flow_rows": count_after,
                "old_flow_key_set_digest": plan.old_key_digest,
                "new_flow_key_set_digest": plan.new_key_digest,
                "new_flow_keys_unique": True,
                "old_new_key_cross_collisions": plan.cross_collisions,
            }
        except BaseException:
            connection.rollback()
            raise


if __name__ == "__main__":
    print(apply_flow_identity_migration())
