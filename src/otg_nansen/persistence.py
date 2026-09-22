"""Review-only persistence mappings and checkpoint rules."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Optional, Protocol

from .errors import NansenError
from .models import NormalizedDexTrade, NormalizedFlowRecord, NormalizedTokenInformation


class PersistenceDesignError(NansenError):
    """Raised when a persistence payload or checkpoint rule is invalid."""


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PersistenceDesignError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _utc(value, "timestamp").isoformat().replace("+00:00", "Z")
    if hasattr(value, "as_tuple"):
        return str(value)
    if isinstance(value, dict):
        return {key: _canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _fingerprint(values: dict[str, Any]) -> str:
    encoded = json.dumps(_canonical_value(values), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def checkpoint_stream_key(chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> tuple[str, str, str, str]:
    """Return a checkpoint identity that separates flow request scopes."""
    return chain, endpoint, token_address, flow_label or ""


def map_token_information(model: NormalizedTokenInformation, retrieved_at: datetime) -> dict[str, Any]:
    return {
        "chain": model.chain,
        "token_address": model.token_address,
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
    payload = {
        "chain": model.chain,
        "token_address": model.token_address,
        "date": _utc(model.date, "date"),
        "price_usd": model.price_usd,
        "token_amount": model.token_amount,
        "value_usd": model.value_usd,
        "holders_count": model.holders_count,
        "total_inflows_count": model.total_inflows_count,
        "total_outflows_count": model.total_outflows_count,
        "bucket_end": _utc(model.bucket_end, "bucket_end") if model.bucket_end else None,
        "is_complete": model.is_complete,
        "total_inflows_cex": model.total_inflows_cex,
        "total_inflows_dex": model.total_inflows_dex,
        "total_outflows_cex": model.total_outflows_cex,
        "total_outflows_dex": model.total_outflows_dex,
        "flow_label": model.flow_label,
    }
    payload["flow_key"] = _fingerprint({
        "chain": model.chain,
        "token_address": model.token_address,
        "flow_label": model.flow_label or "",
        "date": model.date,
        "bucket_end": model.bucket_end,
    })
    return payload


def map_dex_trade(model: NormalizedDexTrade) -> dict[str, Any]:
    payload = {
        "chain": model.chain,
        "requested_token_address": model.requested_token_address,
        "block_timestamp": _utc(model.block_timestamp, "block_timestamp"),
        "transaction_hash": model.transaction_hash,
        "trader_address": model.trader_address,
        "trader_address_label": model.trader_address_label,
        "action": model.action,
        "token_address": model.token_address,
        "token_name": model.token_name,
        "token_amount": model.token_amount,
        "traded_token_address": model.traded_token_address,
        "traded_token_name": model.traded_token_name,
        "traded_token_amount": model.traded_token_amount,
        "estimated_swap_price_usd": model.estimated_swap_price_usd,
        "estimated_value_usd": model.estimated_value_usd,
    }
    payload["trade_key"] = _fingerprint({
        "chain": model.chain,
        "requested_token_address": model.requested_token_address,
        "block_timestamp": model.block_timestamp,
        "transaction_hash": model.transaction_hash,
        "trader_address": model.trader_address,
        "action": model.action,
        "token_address": model.token_address,
        "token_amount": model.token_amount,
        "traded_token_address": model.traded_token_address,
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
) -> dict[str, Any]:
    if status not in {"running", "success", "failed", "partial"}:
        raise PersistenceDesignError("invalid ingestion run status")
    return {
        "run_id": run_id,
        "started_at": _utc(started_at, "started_at"),
        "status": status,
        "chain": chain,
        "endpoint": endpoint,
        "token_address": token_address,
        "flow_label": flow_label,
        "request_scope": {"chain": chain, "endpoint": endpoint, "token_address": token_address, "flow_label": flow_label or ""},
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
    }


def validate_checkpoint_advance(status: str, complete: bool) -> None:
    if status != "success" or not complete:
        raise PersistenceDesignError("checkpoint may advance only after a complete successful run")


class NansenRepository(Protocol):
    """Future driver-backed repository boundary; no implementation connects here."""

    def store_token_information(self, model: NormalizedTokenInformation, retrieved_at: datetime) -> None: ...
    def store_flows(self, models: list[NormalizedFlowRecord]) -> None: ...
    def store_dex_trades(self, models: list[NormalizedDexTrade]) -> None: ...
    def begin_ingestion_run(self, run: dict[str, Any]) -> None: ...
    def complete_ingestion_run(self, run_id: str, counts: dict[str, int]) -> None: ...
    def fail_ingestion_run(self, run_id: str, error_type: str, error_summary: str, partial: bool = False) -> None: ...
    def read_checkpoint(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> Optional[dict[str, Any]]: ...
    def advance_checkpoint(self, chain: str, endpoint: str, token_address: str, last_complete_timestamp: datetime, run_id: str, status: str, complete: bool, flow_label: Optional[str] = None) -> None: ...


@dataclass
class InMemoryCheckpointRepository:
    """Tiny test double for checkpoint invariants, not a database adapter."""

    checkpoints: dict[tuple[str, str, str, str], dict[str, Any]]

    def __init__(self) -> None:
        self.checkpoints = {}

    def read_checkpoint(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str] = None) -> Optional[dict[str, Any]]:
        return self.checkpoints.get(checkpoint_stream_key(chain, endpoint, token_address, flow_label))

    def advance_checkpoint(
        self,
        chain: str,
        endpoint: str,
        token_address: str,
        last_complete_timestamp: datetime,
        run_id: str,
        status: str,
        complete: bool,
        flow_label: Optional[str] = None,
    ) -> None:
        validate_checkpoint_advance(status, complete)
        self.checkpoints[checkpoint_stream_key(chain, endpoint, token_address, flow_label)] = {
            "last_complete_timestamp": _utc(last_complete_timestamp, "last_complete_timestamp"),
            "last_success_run_id": run_id,
            "updated_at": datetime.now(timezone.utc),
        }
