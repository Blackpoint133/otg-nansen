"""Immutable normalized models and deterministic serialization."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def serialize_model(model: Any) -> dict[str, Any]:
    """Return stable field names with UTC datetimes and decimal strings."""
    return _serialize(asdict(model))


@dataclass(frozen=True)
class NormalizedTokenInformation:
    chain: str
    token_address: str
    name: str
    symbol: str
    market_cap_usd: Optional[Decimal] = None
    fdv_usd: Optional[Decimal] = None
    circulating_supply: Optional[Decimal] = None
    total_supply: Optional[Decimal] = None
    volume_total_usd: Optional[Decimal] = None
    buy_volume_usd: Optional[Decimal] = None
    sell_volume_usd: Optional[Decimal] = None
    total_buys: Optional[int] = None
    total_sells: Optional[int] = None
    unique_buyers: Optional[int] = None
    unique_sellers: Optional[int] = None
    liquidity_usd: Optional[Decimal] = None
    total_holders: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


@dataclass(frozen=True)
class NormalizedFlowRecord:
    chain: str
    token_address: str
    date: datetime
    price_usd: Decimal
    token_amount: Decimal
    value_usd: Decimal
    holders_count: int
    total_inflows_count: int
    total_outflows_count: int
    flow_label: Optional[str] = None
    bucket_end: Optional[datetime] = None
    is_complete: Optional[bool] = None
    total_inflows_cex: Optional[int] = None
    total_inflows_dex: Optional[int] = None
    total_outflows_cex: Optional[int] = None
    total_outflows_dex: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


@dataclass(frozen=True)
class NormalizedDexTrade:
    chain: str
    requested_token_address: str
    block_timestamp: datetime
    transaction_hash: str
    trader_address: str
    trader_address_label: Optional[str]
    action: str
    token_address: str
    token_name: str
    token_amount: Decimal
    traded_token_address: str
    traded_token_name: str
    traded_token_amount: Decimal
    estimated_swap_price_usd: Decimal
    estimated_value_usd: Decimal

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)
