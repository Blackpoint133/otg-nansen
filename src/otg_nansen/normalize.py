"""Strict conversion from verified Nansen responses to project models."""

from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from .errors import NormalizationError
from .identity import token_identity_matches
from .models import NormalizedDexTrade, NormalizedFlowRecord, NormalizedTokenInformation


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NormalizationError(f"{context}: expected object")
    return value


def _required_string(record: Mapping[str, Any], field: str, context: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise NormalizationError(f"{context}.{field}: expected non-empty string")
    return value


def _optional_string(record: Mapping[str, Any], field: str, context: str) -> Optional[str]:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise NormalizationError(f"{context}.{field}: expected string or null")
    return value


def _decimal(record: Mapping[str, Any], field: str, context: str, required: bool = True) -> Optional[Decimal]:
    value = record.get(field)
    if value is None and not required:
        return None
    if isinstance(value, bool) or value is None:
        raise NormalizationError(f"{context}.{field}: expected finite number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise NormalizationError(f"{context}.{field}: invalid number") from exc
    if not result.is_finite():
        raise NormalizationError(f"{context}.{field}: number must be finite")
    return result


def _integer(record: Mapping[str, Any], field: str, context: str, required: bool = True) -> Optional[int]:
    value = record.get(field)
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise NormalizationError(f"{context}.{field}: expected integer")
    return value


def _boolean(record: Mapping[str, Any], field: str, context: str) -> Optional[bool]:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise NormalizationError(f"{context}.{field}: expected boolean")
    return value


def _timestamp(record: Mapping[str, Any], field: str, context: str, required: bool = True) -> Optional[datetime]:
    value = record.get(field)
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise NormalizationError(f"{context}.{field}: expected ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NormalizationError(f"{context}.{field}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NormalizationError(f"{context}.{field}: timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def normalize_token_information(response: Mapping[str, Any], *, chain: str, token_address: str) -> NormalizedTokenInformation:
    context = "token-information"
    root = _mapping(response, context)
    data = _mapping(root.get("data"), f"{context}.data")
    contract_address = _required_string(data, "contract_address", f"{context}.data")
    if not token_identity_matches(chain, token_address, contract_address):
        raise NormalizationError(f"{context}.data.contract_address: does not match requested token identity")
    details = data.get("token_details", {})
    metrics = data.get("spot_metrics", {})
    details = _mapping(details, f"{context}.token_details")
    metrics = _mapping(metrics, f"{context}.spot_metrics")
    return NormalizedTokenInformation(
        chain=chain,
        token_address=token_address,
        name=_required_string(data, "name", f"{context}.data"),
        symbol=_required_string(data, "symbol", f"{context}.data"),
        market_cap_usd=_decimal(details, "market_cap_usd", context, False),
        fdv_usd=_decimal(details, "fdv_usd", context, False),
        circulating_supply=_decimal(details, "circulating_supply", context, False),
        total_supply=_decimal(details, "total_supply", context, False),
        volume_total_usd=_decimal(metrics, "volume_total_usd", context, False),
        buy_volume_usd=_decimal(metrics, "buy_volume_usd", context, False),
        sell_volume_usd=_decimal(metrics, "sell_volume_usd", context, False),
        total_buys=_integer(metrics, "total_buys", context, False),
        total_sells=_integer(metrics, "total_sells", context, False),
        unique_buyers=_integer(metrics, "unique_buyers", context, False),
        unique_sellers=_integer(metrics, "unique_sellers", context, False),
        liquidity_usd=_decimal(metrics, "liquidity_usd", context, False),
        total_holders=_integer(metrics, "total_holders", context, False),
    )


def normalize_flows(
    response: Mapping[str, Any],
    *,
    chain: str,
    token_address: str,
    flow_label: Optional[str] = None,
) -> list[NormalizedFlowRecord]:
    context = "flows"
    root = _mapping(response, context)
    data = root.get("data")
    if not isinstance(data, list):
        raise NormalizationError(f"{context}.data: expected list")
    result = []
    for index, record in enumerate(data):
        item_context = f"{context}.data[{index}]"
        item = _mapping(record, item_context)
        result.append(_normalize_flow(item, chain, token_address, flow_label, item_context))
    return result


def _normalize_flow(
    item: Mapping[str, Any],
    chain: str,
    token_address: str,
    flow_label: Optional[str],
    context: str,
) -> NormalizedFlowRecord:
    return NormalizedFlowRecord(
        chain=chain,
        token_address=token_address,
        date=_timestamp(item, "date", context),
        price_usd=_decimal(item, "price_usd", context),
        token_amount=_decimal(item, "token_amount", context),
        value_usd=_decimal(item, "value_usd", context),
        holders_count=_integer(item, "holders_count", context),
        total_inflows_count=_integer(item, "total_inflows_count", context),
        total_outflows_count=_integer(item, "total_outflows_count", context),
        flow_label=flow_label,
        bucket_end=_timestamp(item, "bucket_end", context, False),
        is_complete=_boolean(item, "is_complete", context),
        total_inflows_cex=_integer(item, "total_inflows_cex", context, False),
        total_inflows_dex=_integer(item, "total_inflows_dex", context, False),
        total_outflows_cex=_integer(item, "total_outflows_cex", context, False),
        total_outflows_dex=_integer(item, "total_outflows_dex", context, False),
    )


def normalize_dex_trades(response: Mapping[str, Any], *, chain: str, token_address: str) -> list[NormalizedDexTrade]:
    context = "dex-trades"
    root = _mapping(response, context)
    data = root.get("data")
    if not isinstance(data, list):
        raise NormalizationError(f"{context}.data: expected list")
    result = []
    for index, record in enumerate(data):
        item_context = f"{context}.data[{index}]"
        item = _mapping(record, item_context)
        response_token = _required_string(item, "token_address", item_context)
        if not token_identity_matches(chain, token_address, response_token):
            raise NormalizationError(f"{item_context}.token_address: does not match requested token identity")
        result.append(
            NormalizedDexTrade(
                chain=chain,
                requested_token_address=token_address,
                block_timestamp=_timestamp(item, "block_timestamp", item_context),
                transaction_hash=_required_string(item, "transaction_hash", item_context),
                trader_address=_required_string(item, "trader_address", item_context),
                trader_address_label=_optional_string(item, "trader_address_label", item_context),
                action=_required_string(item, "action", item_context),
                token_address=response_token,
                token_name=_required_string(item, "token_name", item_context),
                token_amount=_decimal(item, "token_amount", item_context),
                traded_token_address=_required_string(item, "traded_token_address", item_context),
                traded_token_name=_required_string(item, "traded_token_name", item_context),
                traded_token_amount=_decimal(item, "traded_token_amount", item_context),
                estimated_swap_price_usd=_decimal(item, "estimated_swap_price_usd", item_context),
                estimated_value_usd=_decimal(item, "estimated_value_usd", item_context),
            )
        )
    return result
