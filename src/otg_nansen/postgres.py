"""PostgreSQL repository adapter for the isolated staging Nansen schema."""

from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Iterator, Optional

import psycopg
from psycopg.types.json import Jsonb

from .persistence import (
    CHECKPOINT_READ_SQL,
    CHECKPOINT_UPSERT_SQL,
    DEX_TRADE_UPSERT_SQL,
    FLOW_UPSERT_SQL,
    INGESTION_RUN_FAILURE_SQL,
    INGESTION_RUN_INSERT_SQL,
    INGESTION_RUN_SUCCESS_SQL,
    TOKEN_INFORMATION_INSERT_SQL,
    PersistenceDesignError,
    map_dex_trade,
    map_flow,
    map_token_information,
)
from .models import NormalizedDexTrade, NormalizedFlowRecord, NormalizedTokenInformation


ALLOWED_STAGING_DATABASE = "server_otg_staging"


def _load_dotenv_if_present(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name and name not in os.environ:
            os.environ[name] = value.strip().strip('"').strip("'")


def staging_connection_kwargs() -> dict[str, Any]:
    """Return connection settings with the database forcibly pinned to staging."""
    _load_dotenv_if_present()
    return {
        "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER", ""),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "dbname": ALLOWED_STAGING_DATABASE,
    }


def verify_staging_target(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    """Verify target identity before any staging DDL or DML."""
    database = connection.execute("SELECT current_database()").fetchone()[0]
    user = connection.execute("SELECT current_user").fetchone()[0]
    read_only = connection.execute("SHOW transaction_read_only").fetchone()[0]
    if database != ALLOWED_STAGING_DATABASE:
        raise RuntimeError("refusing non-staging database target")
    return {"database": database, "user": user, "transaction_read_only": read_only}


class PostgresRepository:
    """Small psycopg3 adapter with separate durable-audit and data ownership."""

    def __init__(self, audit_connection: psycopg.Connection[Any], data_connection: psycopg.Connection[Any]) -> None:
        self.audit_connection = audit_connection
        self.data_connection = data_connection
        self._data_transaction_active = False
        verify_staging_target(audit_connection)
        verify_staging_target(data_connection)
        data_connection.rollback()

    @classmethod
    def from_env(cls) -> "PostgresRepository":
        kwargs = staging_connection_kwargs()
        audit = psycopg.connect(**kwargs, autocommit=True)
        data = psycopg.connect(**kwargs, autocommit=False)
        return cls(audit, data)

    def close(self) -> None:
        self.audit_connection.close()
        self.data_connection.close()

    def begin_ingestion_run(self, run: dict[str, Any]) -> None:
        values = (
            run["run_id"], run["started_at"], run["status"], run["chain"], run["endpoint"],
            run["token_address"], run["flow_label"], Jsonb(run["request_scope"]), run["window_start"],
            run["window_end"], run["pages_requested"], run["api_calls"], run["records_received"],
            run["records_normalized"], run["records_inserted"], run["records_updated_or_conflicted"],
            run["error_type"], run["error_summary"],
        )
        self.audit_connection.execute(INGESTION_RUN_INSERT_SQL, values)

    def begin_data_transaction(self) -> None:
        if self._data_transaction_active:
            raise RuntimeError("data transaction already active")
        self.data_connection.execute("BEGIN")
        self._data_transaction_active = True

    def _data_cursor(self) -> psycopg.Connection[Any]:
        if not self._data_transaction_active:
            raise RuntimeError("data transaction is not active")
        return self.data_connection

    def store_token_information(self, model: NormalizedTokenInformation, retrieved_at: datetime) -> None:
        payload = map_token_information(model, retrieved_at)
        values = tuple(payload[field] for field in (
            "chain", "token_address", "retrieved_at", "name", "symbol", "market_cap_usd",
            "fdv_usd", "circulating_supply", "total_supply", "volume_total_usd", "buy_volume_usd",
            "sell_volume_usd", "total_buys", "total_sells", "unique_buyers", "unique_sellers",
            "liquidity_usd", "total_holders",
        ))
        self._data_cursor().execute(TOKEN_INFORMATION_INSERT_SQL, values)

    def store_flows(self, models: list[NormalizedFlowRecord]) -> None:
        fields = ("flow_key", "chain", "token_address", "date", "price_usd", "token_amount", "value_usd",
                  "holders_count", "total_inflows_count", "total_outflows_count", "flow_label", "bucket_end",
                  "is_complete", "total_inflows_cex", "total_inflows_dex", "total_outflows_cex", "total_outflows_dex")
        for model in models:
            payload = map_flow(model)
            self._data_cursor().execute(FLOW_UPSERT_SQL, tuple(payload[field] for field in fields))

    def store_dex_trades(self, models: list[NormalizedDexTrade]) -> None:
        fields = ("trade_key", "chain", "requested_token_address", "block_timestamp", "transaction_hash",
                  "trader_address", "trader_address_label", "action", "token_address", "token_name",
                  "token_amount", "traded_token_address", "traded_token_name", "traded_token_amount",
                  "estimated_swap_price_usd", "estimated_value_usd")
        for model in models:
            payload = map_dex_trade(model)
            self._data_cursor().execute(DEX_TRADE_UPSERT_SQL, tuple(payload[field] for field in fields))

    def read_checkpoint(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> Optional[dict[str, Any]]:
        row = self.audit_connection.execute(
            CHECKPOINT_READ_SQL,
            (chain, endpoint, self._canonical_token(chain, token_address), self._scope(endpoint, flow_label)),
        ).fetchone()
        if row is None:
            return None
        columns = ("chain", "endpoint", "token_address", "flow_label", "last_complete_timestamp", "last_success_run_id", "updated_at", "metadata")
        return dict(zip(columns, row))

    @staticmethod
    def _canonical_token(chain: str, token_address: str) -> str:
        from .persistence import _canonical_address
        return _canonical_address(chain, token_address)

    @staticmethod
    def _scope(endpoint: str, flow_label: Optional[str]) -> str:
        from .persistence import canonical_request_scope
        return canonical_request_scope(endpoint, flow_label)

    def advance_checkpoint(self, chain: str, endpoint: str, token_address: str, last_complete_timestamp: datetime,
                           run_id: str, flow_label: Optional[str] = None) -> None:
        canonical_token = self._canonical_token(chain, token_address)
        scope = self._scope(endpoint, flow_label)
        eligible = self._data_cursor().execute(
            """SELECT 1 FROM nansen.ingestion_runs
               WHERE run_id = %s AND status = 'success' AND chain = %s
                 AND endpoint = %s AND token_address = %s AND flow_label = %s""",
            (run_id, chain, endpoint, canonical_token, scope),
        ).fetchone()
        if eligible is None:
            raise PersistenceDesignError("checkpoint run is not a matching successful ingestion run")
        values = (chain, endpoint, canonical_token, scope, last_complete_timestamp, run_id,
                  datetime.now(last_complete_timestamp.tzinfo), Jsonb({}), run_id, chain, endpoint,
                  canonical_token, scope)
        cursor = self._data_cursor().execute(CHECKPOINT_UPSERT_SQL, values)
        if cursor.rowcount not in (0, 1):
            raise PersistenceDesignError("unexpected checkpoint upsert result")

    def complete_ingestion_run(self, run_id: str, counts: dict[str, int]) -> None:
        values = (datetime.now().astimezone(), counts.get("pages_requested", 0), counts.get("api_calls", 0),
                  counts.get("records_received", 0), counts.get("records_normalized", 0),
                  counts.get("records_inserted", 0), counts.get("records_updated_or_conflicted", 0), run_id)
        self._data_cursor().execute(INGESTION_RUN_SUCCESS_SQL, values)

    def commit_data_transaction(self) -> None:
        self._data_cursor()
        self.data_connection.commit()
        self._data_transaction_active = False

    def rollback_data_transaction(self) -> None:
        if self._data_transaction_active:
            self.data_connection.rollback()
        self._data_transaction_active = False

    def fail_ingestion_run(self, run_id: str, error_type: str, error_summary: str, partial: bool = False, counts: Optional[dict[str, int]] = None) -> None:
        counts = counts or {}
        self.audit_connection.execute(
            INGESTION_RUN_FAILURE_SQL,
            ("partial" if partial else "failed", datetime.now().astimezone(), counts.get("pages_requested", 0),
             counts.get("api_calls", 0), counts.get("records_received", 0), counts.get("records_normalized", 0),
             error_type, error_summary, run_id),
        )


@contextmanager
def staging_repository() -> Iterator[PostgresRepository]:
    repository = PostgresRepository.from_env()
    try:
        yield repository
    finally:
        repository.close()
