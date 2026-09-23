"""Review-only persistence mappings and checkpoint rules."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from decimal import Decimal
from typing import Any, Optional, Protocol

from .errors import NansenError
from .identity import canonical_chain_address, canonical_flow_scope
from .models import NormalizedDexTrade, NormalizedFlowRecord, NormalizedTokenInformation


TOKEN_INFORMATION_INSERT_SQL = """INSERT INTO nansen.token_information (
    chain, token_address, retrieved_at, name, symbol, market_cap_usd,
    fdv_usd, circulating_supply, total_supply, volume_total_usd,
    buy_volume_usd, sell_volume_usd, total_buys, total_sells,
    unique_buyers, unique_sellers, liquidity_usd, total_holders
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (chain, token_address, retrieved_at) DO NOTHING;"""

FLOW_UPSERT_SQL = """INSERT INTO nansen.flows (
    flow_key, chain, token_address, date, price_usd, token_amount, value_usd,
    holders_count, total_inflows_count, total_outflows_count, flow_label,
    bucket_end, is_complete, total_inflows_cex, total_inflows_dex,
    total_outflows_cex, total_outflows_dex
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (flow_key) DO UPDATE SET
    date = EXCLUDED.date,
    price_usd = EXCLUDED.price_usd,
    token_amount = EXCLUDED.token_amount,
    value_usd = EXCLUDED.value_usd,
    holders_count = EXCLUDED.holders_count,
    total_inflows_count = EXCLUDED.total_inflows_count,
    total_outflows_count = EXCLUDED.total_outflows_count,
    bucket_end = EXCLUDED.bucket_end,
    is_complete = CASE
        WHEN nansen.flows.is_complete IS TRUE OR EXCLUDED.is_complete IS TRUE THEN TRUE
        ELSE EXCLUDED.is_complete
    END,
    total_inflows_cex = EXCLUDED.total_inflows_cex,
    total_inflows_dex = EXCLUDED.total_inflows_dex,
    total_outflows_cex = EXCLUDED.total_outflows_cex,
    total_outflows_dex = EXCLUDED.total_outflows_dex
WHERE nansen.flows.is_complete IS NOT TRUE OR EXCLUDED.is_complete IS TRUE;"""

DEX_TRADE_UPSERT_SQL = """INSERT INTO nansen.dex_trades (
    trade_key, chain, requested_token_address, block_timestamp,
    transaction_hash, trader_address, trader_address_label, action,
    token_address, token_name, token_amount, traded_token_address,
    traded_token_name, traded_token_amount, estimated_swap_price_usd,
    estimated_value_usd
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (trade_key) DO UPDATE SET
    trader_address_label = EXCLUDED.trader_address_label,
    token_name = EXCLUDED.token_name,
    traded_token_name = EXCLUDED.traded_token_name,
    estimated_swap_price_usd = EXCLUDED.estimated_swap_price_usd,
    estimated_value_usd = EXCLUDED.estimated_value_usd;"""

INGESTION_RUN_INSERT_SQL = """INSERT INTO nansen.ingestion_runs (
    run_id, started_at, status, chain, endpoint, token_address, flow_label,
    request_scope, window_start, window_end, pages_requested, api_calls,
    records_received, records_normalized, records_inserted,
    records_updated_or_conflicted, error_type, error_summary, source_warnings
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""

INGESTION_RUN_SUCCESS_SQL = """UPDATE nansen.ingestion_runs
SET status = 'success', finished_at = %s, pages_requested = %s,
    api_calls = %s, records_received = %s, records_normalized = %s,
    records_inserted = %s, records_updated_or_conflicted = %s,
    error_type = NULL, error_summary = NULL, source_warnings = %s
WHERE run_id = %s;"""

INGESTION_RUN_FAILURE_SQL = """UPDATE nansen.ingestion_runs
SET status = %s, finished_at = %s, pages_requested = %s, api_calls = %s,
    records_received = %s, records_normalized = %s,
    error_type = %s, error_summary = %s, source_warnings = %s
WHERE run_id = %s;"""

CHECKPOINT_READ_SQL = """SELECT chain, endpoint, token_address, flow_label,
    last_complete_timestamp, last_success_run_id, updated_at, metadata
FROM nansen.checkpoints
WHERE chain = %s AND endpoint = %s AND token_address = %s AND flow_label = %s;"""

CHECKPOINT_UPSERT_SQL = """INSERT INTO nansen.checkpoints (
    chain, endpoint, token_address, flow_label, last_complete_timestamp,
    last_success_run_id, updated_at, metadata
) SELECT %s, %s, %s, %s, %s, %s, %s, %s
FROM nansen.ingestion_runs r
WHERE r.run_id = %s
  AND r.status = 'success'
  AND r.chain = %s
  AND r.endpoint = %s
  AND r.token_address = %s
  AND r.flow_label = %s
ON CONFLICT (chain, endpoint, token_address, flow_label) DO UPDATE SET
    last_complete_timestamp = EXCLUDED.last_complete_timestamp,
    last_success_run_id = EXCLUDED.last_success_run_id,
    updated_at = EXCLUDED.updated_at,
    metadata = EXCLUDED.metadata
WHERE EXCLUDED.last_complete_timestamp >= nansen.checkpoints.last_complete_timestamp;"""


class PersistenceDesignError(NansenError):
    """Raised when a persistence payload or checkpoint rule is invalid."""


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PersistenceDesignError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _utc(value, "timestamp").isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise PersistenceDesignError("identity Decimal must be finite")
        if value.is_zero():
            return "0"
        text = format(value.normalize(), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, dict):
        return {key: _canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _fingerprint(values: dict[str, Any]) -> str:
    encoded = json.dumps(_canonical_value(values), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def canonical_request_scope(endpoint: str, flow_label: Optional[str] = None) -> str:
    if endpoint == "flows":
        try:
            return canonical_flow_scope(flow_label)
        except ValueError as exc:
            raise PersistenceDesignError("flows requires a non-empty flow_label scope") from exc
    return ""


def flow_identity_key(
    chain: str,
    token_address: str,
    flow_label: str,
    date: datetime,
    bucket_end: datetime,
) -> str:
    """Build stable identity for one exact Nansen aggregation bucket."""
    start = _utc(date, "date")
    end = _utc(bucket_end, "bucket_end")
    if end <= start:
        raise PersistenceDesignError("bucket_end must be after date")
    try:
        scope = canonical_flow_scope(flow_label)
    except ValueError as exc:
        raise PersistenceDesignError("flows requires a non-empty flow_label scope") from exc
    return _fingerprint({
        "chain": chain,
        "token_address": _canonical_address(chain, token_address),
        "flow_label": scope,
        "date": start,
        "bucket_end": end,
    })


def _canonical_address(chain: str, address: str) -> str:
    try:
        return canonical_chain_address(chain, address)
    except ValueError as exc:
        raise PersistenceDesignError(str(exc)) from exc


def checkpoint_stream_key(chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> tuple[str, str, str, str]:
    """Return a checkpoint identity that separates flow request scopes."""
    return chain, endpoint, _canonical_address(chain, token_address), canonical_request_scope(endpoint, flow_label)


def map_token_information(model: NormalizedTokenInformation, retrieved_at: datetime) -> dict[str, Any]:
    return {
        "chain": model.chain,
        "token_address": _canonical_address(model.chain, model.token_address),
        "retrieved_at": _utc(retrieved_at, "retrieved_at"),
        "name": model.name,
        "symbol": model.symbol,
        "market_cap_usd": model.market_cap_usd,
        "fdv_usd": model.fdv_usd,
        "circulating_supply": model.circulating_supply,
        "total_supply": model.total_supply,
        "volume_total_usd": model.volume_total_usd,
        "buy_volume_usd": model.buy_volume_usd,
        "sell_volume_usd": model.sell_volume_usd,
        "total_buys": model.total_buys,
        "total_sells": model.total_sells,
        "unique_buyers": model.unique_buyers,
        "unique_sellers": model.unique_sellers,
        "liquidity_usd": model.liquidity_usd,
        "total_holders": model.total_holders,
    }


def map_flow(model: NormalizedFlowRecord) -> dict[str, Any]:
    date = _utc(model.date, "date")
    if model.bucket_end is None:
        raise PersistenceDesignError("flow bucket_end is required for persistence")
    bucket_end = _utc(model.bucket_end, "bucket_end")
    if bucket_end <= date:
        raise PersistenceDesignError("bucket_end must be after date")
    payload = {
        "chain": model.chain,
        "token_address": _canonical_address(model.chain, model.token_address),
        "date": date,
        "price_usd": model.price_usd,
        "token_amount": model.token_amount,
        "value_usd": model.value_usd,
        "holders_count": model.holders_count,
        "total_inflows_count": model.total_inflows_count,
        "total_outflows_count": model.total_outflows_count,
        "bucket_end": bucket_end,
        "is_complete": model.is_complete,
        "total_inflows_cex": model.total_inflows_cex,
        "total_inflows_dex": model.total_inflows_dex,
        "total_outflows_cex": model.total_outflows_cex,
        "total_outflows_dex": model.total_outflows_dex,
        "flow_label": canonical_flow_scope(model.flow_label),
    }
    payload["flow_key"] = flow_identity_key(
        model.chain, model.token_address, model.flow_label, date, bucket_end,
    )
    return payload


def map_dex_trade(model: NormalizedDexTrade) -> dict[str, Any]:
    payload = {
        "chain": model.chain,
        "requested_token_address": _canonical_address(model.chain, model.requested_token_address),
        "block_timestamp": _utc(model.block_timestamp, "block_timestamp"),
        "transaction_hash": model.transaction_hash,
        "trader_address": _canonical_address(model.chain, model.trader_address),
        "trader_address_label": model.trader_address_label,
        "action": model.action,
        "token_address": _canonical_address(model.chain, model.token_address),
        "token_name": model.token_name,
        "token_amount": model.token_amount,
        "traded_token_address": _canonical_address(model.chain, model.traded_token_address),
        "traded_token_name": model.traded_token_name,
        "traded_token_amount": model.traded_token_amount,
        "estimated_swap_price_usd": model.estimated_swap_price_usd,
        "estimated_value_usd": model.estimated_value_usd,
    }
    payload["trade_key"] = _fingerprint({
        "chain": model.chain,
        "requested_token_address": _canonical_address(model.chain, model.requested_token_address),
        "block_timestamp": model.block_timestamp,
        "transaction_hash": model.transaction_hash,
        "trader_address": _canonical_address(model.chain, model.trader_address),
        "action": model.action,
        "token_address": _canonical_address(model.chain, model.token_address),
        "token_amount": model.token_amount,
        "traded_token_address": _canonical_address(model.chain, model.traded_token_address),
        "traded_token_amount": model.traded_token_amount,
    })
    return payload


def map_ingestion_run(
    *,
    run_id: str,
    started_at: datetime,
    status: str,
    chain: str,
    endpoint: str,
    token_address: str,
    flow_label: Optional[str] = None,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
    pages_requested: int = 0,
    api_calls: int = 0,
    records_received: int = 0,
    records_normalized: int = 0,
    records_inserted: int = 0,
    records_updated_or_conflicted: int = 0,
    error_type: Optional[str] = None,
    error_summary: Optional[str] = None,
    source_warnings: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    if status not in {"running", "success", "failed", "partial"}:
        raise PersistenceDesignError("invalid ingestion run status")
    scope = canonical_request_scope(endpoint, flow_label)
    persisted_token_address = _canonical_address(chain, token_address)
    return {
        "run_id": run_id,
        "started_at": _utc(started_at, "started_at"),
        "status": status,
        "chain": chain,
        "endpoint": endpoint,
        "token_address": persisted_token_address,
        "flow_label": scope,
        "request_scope": {"chain": chain, "endpoint": endpoint, "token_address": persisted_token_address, "flow_label": scope},
        "window_start": _utc(window_start, "window_start") if window_start else None,
        "window_end": _utc(window_end, "window_end") if window_end else None,
        "pages_requested": pages_requested,
        "api_calls": api_calls,
        "records_received": records_received,
        "records_normalized": records_normalized,
        "records_inserted": records_inserted,
        "records_updated_or_conflicted": records_updated_or_conflicted,
        "error_type": error_type,
        "error_summary": error_summary,
        "source_warnings": source_warnings,
    }


def validate_checkpoint_advance(status: str, complete: bool) -> None:
    if status != "success" or not complete:
        raise PersistenceDesignError("checkpoint may advance only after a complete successful run")


def merge_flow_completeness(existing: Optional[bool], incoming: Optional[bool]) -> Optional[bool]:
    """Return the database-equivalent completeness merge for a flow row."""
    if existing is True:
        return True
    if incoming is True:
        return True
    return incoming


class NansenRepository(Protocol):
    """Future driver boundary; audit writes are separate from data transactions."""

    def store_token_information(self, model: NormalizedTokenInformation, retrieved_at: datetime) -> None: ...
    def store_flows(self, models: list[NormalizedFlowRecord]) -> None: ...
    def store_dex_trades(self, models: list[NormalizedDexTrade]) -> None: ...
    def begin_ingestion_run(self, run: dict[str, Any]) -> None: ...
    def complete_ingestion_run(self, run_id: str, counts: dict[str, int], source_warnings: Optional[list[dict[str, Any]]] = None) -> None: ...
    def fail_ingestion_run(self, run_id: str, error_type: str, error_summary: str, partial: bool = False, counts: Optional[dict[str, int]] = None, source_warnings: Optional[list[dict[str, Any]]] = None) -> None: ...
    def begin_data_transaction(self) -> None: ...
    def commit_data_transaction(self) -> None: ...
    def rollback_data_transaction(self) -> None: ...
    def read_checkpoint(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> Optional[dict[str, Any]]: ...
    def advance_checkpoint(self, chain: str, endpoint: str, token_address: str, last_complete_timestamp: datetime, run_id: str, flow_label: Optional[str] = None) -> None: ...


@dataclass
class InMemoryCheckpointRepository:
    """Tiny test double for checkpoint invariants, not a database adapter."""

    checkpoints: dict[tuple[str, str, str, str], dict[str, Any]]

    def __init__(self) -> None:
        self.checkpoints = {}

    def read_checkpoint(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> Optional[dict[str, Any]]:
        return self.checkpoints.get(checkpoint_stream_key(chain, endpoint, token_address, flow_label))

    def advance_checkpoint(
        self, chain: str, endpoint: str, token_address: str,
        last_complete_timestamp: datetime, run_id: str,
        flow_label: Optional[str] = None,
    ) -> None:
        raise PersistenceDesignError("checkpoint eligibility requires a persisted ingestion run")


@dataclass
class InMemoryTransactionRepository:
    """Deterministic lifecycle double; audit state survives data rollback."""

    data: dict[str, dict[str, Any]]
    checkpoints: dict[tuple[str, str, str, str], dict[str, Any]]
    ingestion_runs: dict[str, dict[str, Any]]
    _staged_data: Optional[dict[str, dict[str, Any]]]
    _staged_checkpoints: Optional[dict[tuple[str, str, str, str], dict[str, Any]]]
    _staged_ingestion_runs: Optional[dict[str, dict[str, Any]]]

    def __init__(self) -> None:
        self.data = {"flows": {}, "dex_trades": {}, "token_information": {}}
        self.checkpoints = {}
        self.ingestion_runs = {}
        self._staged_data = None
        self._staged_checkpoints = None
        self._staged_ingestion_runs = None

    def begin_ingestion_run(self, run: dict[str, Any]) -> None:
        if run["status"] != "running":
            raise PersistenceDesignError("ingestion audit must start in running state")
        self.ingestion_runs[run["run_id"]] = dict(run)

    def begin_data_transaction(self) -> None:
        if self._staged_data is not None:
            raise PersistenceDesignError("data transaction already active")
        self._staged_data = {name: dict(values) for name, values in self.data.items()}
        self._staged_checkpoints = dict(self.checkpoints)
        self._staged_ingestion_runs = {run_id: dict(run) for run_id, run in self.ingestion_runs.items()}

    def _require_transaction(self) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str, str, str], dict[str, Any]], dict[str, dict[str, Any]]]:
        if self._staged_data is None or self._staged_checkpoints is None or self._staged_ingestion_runs is None:
            raise PersistenceDesignError("data transaction is not active")
        return self._staged_data, self._staged_checkpoints, self._staged_ingestion_runs

    def store_flows(self, models: list[NormalizedFlowRecord]) -> None:
        staged, _, _ = self._require_transaction()
        for model in models:
            payload = map_flow(model)
            staged["flows"][payload["flow_key"]] = payload

    def store_dex_trades(self, models: list[NormalizedDexTrade]) -> None:
        staged, _, _ = self._require_transaction()
        for model in models:
            payload = map_dex_trade(model)
            staged["dex_trades"][payload["trade_key"]] = payload

    def store_token_information(self, model: NormalizedTokenInformation, retrieved_at: datetime) -> None:
        staged, _, _ = self._require_transaction()
        payload = map_token_information(model, retrieved_at)
        key = (payload["chain"], payload["token_address"], payload["retrieved_at"])
        staged["token_information"][key] = payload

    def advance_checkpoint(
        self, chain: str, endpoint: str, token_address: str,
        last_complete_timestamp: datetime, run_id: str,
        flow_label: Optional[str] = None,
    ) -> None:
        _, checkpoints, runs = self._require_transaction()
        canonical_token = _canonical_address(chain, token_address)
        scope = canonical_request_scope(endpoint, flow_label)
        run = runs.get(run_id)
        if run is None or run.get("status") != "success":
            raise PersistenceDesignError("checkpoint requires an existing successful ingestion run")
        if (run.get("chain"), run.get("endpoint"), run.get("token_address"), run.get("flow_label")) != (chain, endpoint, canonical_token, scope):
            raise PersistenceDesignError("checkpoint run does not match stream identity")
        checkpoints[checkpoint_stream_key(chain, endpoint, canonical_token, scope)] = {
            "last_complete_timestamp": _utc(last_complete_timestamp, "last_complete_timestamp"),
            "last_success_run_id": run_id,
            "updated_at": datetime.now(timezone.utc),
        }

    def read_checkpoint(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> Optional[dict[str, Any]]:
        return self.checkpoints.get(checkpoint_stream_key(chain, endpoint, token_address, flow_label))

    def commit_data_transaction(self) -> None:
        staged, checkpoints, runs = self._require_transaction()
        self.data = staged
        self.checkpoints = checkpoints
        self.ingestion_runs = runs
        self._staged_data = None
        self._staged_checkpoints = None
        self._staged_ingestion_runs = None

    def rollback_data_transaction(self) -> None:
        self._staged_data = None
        self._staged_checkpoints = None
        self._staged_ingestion_runs = None

    def complete_ingestion_run(self, run_id: str, counts: dict[str, int], source_warnings: Optional[list[dict[str, Any]]] = None) -> None:
        _, _, runs = self._require_transaction()
        runs[run_id].update(counts, status="success", finished_at=datetime.now(timezone.utc), source_warnings=source_warnings if source_warnings is not None else [])

    def fail_ingestion_run(self, run_id: str, error_type: str, error_summary: str, partial: bool = False, counts: Optional[dict[str, int]] = None, source_warnings: Optional[list[dict[str, Any]]] = None) -> None:
        counts = counts or {}
        self.ingestion_runs[run_id].update(
            status="partial" if partial else "failed",
            pages_requested=counts.get("pages_requested", 0),
            api_calls=counts.get("api_calls", 0),
            records_received=counts.get("records_received", 0),
            records_normalized=counts.get("records_normalized", 0),
            error_type=error_type,
            error_summary=error_summary,
            **({"source_warnings": source_warnings} if source_warnings is not None else {}),
            finished_at=datetime.now(timezone.utc),
        )
