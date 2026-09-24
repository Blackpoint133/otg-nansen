"""Apply the reviewed analytics migration to server_otg_staging only."""

from pathlib import Path

import psycopg

from .market_analytics import verify_staging_writer_identity
from .postgres import staging_connection_kwargs


def apply_analytics_migration() -> None:
    migration = Path(__file__).parents[2] / "sql" / "005_otg_nansen_hourly_analytics.sql"
    sql = migration.read_text(encoding="utf-8")
    if "DROP " in sql.upper() or "TRUNCATE " in sql.upper():
        raise RuntimeError("analytics migration safety guard rejected destructive DDL")
    kwargs = staging_connection_kwargs()
    kwargs["dbname"] = "server_otg_staging"
    with psycopg.connect(**kwargs, autocommit=True) as connection:
        database = connection.execute("SELECT current_database()").fetchone()[0]
        verify_staging_writer_identity(database)
        connection.execute("SET lock_timeout = '5s'")
        connection.execute("SET statement_timeout = '30s'")
        with connection.transaction():
            connection.execute(sql)


if __name__ == "__main__":
    apply_analytics_migration()
