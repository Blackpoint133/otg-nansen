"""Apply the reviewed Nansen migration only to server_otg_staging."""

from pathlib import Path

import psycopg

from .postgres import ALLOWED_STAGING_DATABASE, staging_connection_kwargs, verify_staging_target


def apply_staging_migration(sql_path: Path | None = None) -> None:
    path = sql_path or Path(__file__).parents[2] / "sql" / "001_create_nansen_schema.sql"
    sql = path.read_text(encoding="utf-8")
    if "DROP " in sql.upper():
        raise RuntimeError("migration safety guard rejected DROP")
    kwargs = staging_connection_kwargs()
    if kwargs["dbname"] != ALLOWED_STAGING_DATABASE:
        raise RuntimeError("migration target is not the allowed staging database")
    with psycopg.connect(**kwargs, autocommit=False) as connection:
        identity = verify_staging_target(connection)
        if identity["database"] != ALLOWED_STAGING_DATABASE:
            raise RuntimeError("refusing non-staging database target")
        connection.execute("SET LOCAL lock_timeout = '5s'")
        connection.execute("SET LOCAL statement_timeout = '30s'")
        connection.execute(sql)
        connection.commit()


if __name__ == "__main__":
    apply_staging_migration()
