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


def _fingerprint(values: dict[str, Any]) -> str:
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


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
    }
    payload["flow_key"] = _fingerprint({key: str(value) for key, value in payload.items()})
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
    payload["trade_key"] = _fingerprint({key: str(value) for key, value in payload.items()})
    return payload


def validate_checkpoint_advance(status: str, complete: bool) -> None:
    if status != "success" or not complete:
        raise PersistenceDesignError("checkpoint may advance only after a complete successful run")


class NansenRepository(Protocol):
    """Future driver-backed repository boundary; no implementation connects here."""

    def store_token_information(self, model: NormalizedTokenInformation, retrieved_at: datetime) -> None: ...
    def store_flows(self, models: list[NormalizedFlowRecord]) -> None: ...
    def store_dex_trades(self, models: list[NormalizedDexTrade]) -> None: ...
    def read_checkpoint(self, chain: str, endpoint: str, token_address: str) -> Optional[dict[str, Any]]: ...


@dataclass
class InMemoryCheckpointRepository:
    """Tiny test double for checkpoint invariants, not a database adapter."""

    checkpoints: dict[tuple[str, str, str], dict[str, Any]]

    def __init__(self) -> None:
        self.checkpoints = {}

    def read_checkpoint(self, chain: str, endpoint: str, token_address: str) -> Optional[dict[str, Any]]:
        return self.checkpoints.get((chain, endpoint, token_address))

    def advance_checkpoint(
        self,
        chain: str,
        endpoint: str,
        token_address: str,
        last_complete_timestamp: datetime,
        run_id: str,
        status: str,
        complete: bool,
    ) -> None:
        validate_checkpoint_advance(status, complete)
        self.checkpoints[(chain, endpoint, token_address)] = {
            "last_complete_timestamp": _utc(last_complete_timestamp, "last_complete_timestamp"),
            "last_success_run_id": run_id,
            "updated_at": datetime.now(timezone.utc),
        }
