"""One-request, no-retry live Avalanche $GUN observation for the local demo."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
from typing import Any, Callable

from .client import NansenClient, PaginationPageMetadata
from .config import DEFAULT_BASE_URL, NansenConfig, TOKEN_IDENTITIES
from .errors import NansenError, SourceWarningError
from .normalize import normalize_flows
from .source_warnings import classify_page_warnings, validate_warning_structure

UTC = timezone.utc
FLOW_LABEL = "smart_money"
CHAIN = "avalanche"
MAX_RESPONSE_RECORDS = 1_000
ONE_HOUR = timedelta(hours=1)


class DemoLiveError(RuntimeError):
    """Sanitized live-data failure carrying a stable public error code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _finite_float(value: Decimal | int | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    number = float(value)
    if not math.isfinite(number):
        raise DemoLiveError("INVALID_NUMERIC_VALUE")
    return number


def classify_live_return(value: float | None, q05: float, q95: float) -> str:
    if value is None or not math.isfinite(value):
        return "LIVE_RETURN_UNAVAILABLE"
    if value >= q95:
        return "POSITIVE_SHOCK_RANGE"
    if value <= q05:
        return "NEGATIVE_SHOCK_RANGE"
    return "MIDDLE_90_PERCENT"


class DemoLiveAdapter:
    """Fetch exactly one recent Flows page and return sanitized aggregates."""

    def __init__(
        self,
        client: NansenClient,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client
        self._now = now or (lambda: datetime.now(UTC))

    @classmethod
    def from_env(cls, *, now: Callable[[], datetime] | None = None) -> "DemoLiveAdapter":
        config = NansenConfig.from_env()
        if config.base_url.rstrip("/") != DEFAULT_BASE_URL:
            raise DemoLiveError("UNAPPROVED_NANSEN_API_BASE_URL")
        # Hard caps override looser local .env settings for this demo surface.
        bounded = replace(
            config,
            timeout_seconds=min(120.0, config.timeout_seconds),
            max_calls=1,
            max_retries=0,
            max_pages=1,
            page_size=MAX_RESPONSE_RECORDS,
        )
        return cls(NansenClient(bounded), now=now)

    def fetch(self, historical: dict[str, Any]) -> dict[str, Any]:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise DemoLiveError("CLOCK_MUST_BE_TIMEZONE_AWARE")
        now = now.astimezone(UTC)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        window_start = current_hour - timedelta(hours=12)
        window_end = current_hour - timedelta(seconds=1)
        payload = {
            "chain": CHAIN,
            "token_address": TOKEN_IDENTITIES[CHAIN],
            "date": {
                "from": window_start.isoformat().replace("+00:00", "Z"),
                "to": window_end.isoformat().replace("+00:00", "Z"),
            },
            "label": FLOW_LABEL,
            "pagination": {"page": 1, "per_page": MAX_RESPONSE_RECORDS},
            "order_by": [{"field": "date", "direction": "ASC"}],
        }
        try:
            response = self.client.request("/api/v1/tgm/flows", payload)
            if not isinstance(response, dict):
                raise DemoLiveError("INVALID_RESPONSE_SHAPE")
            raw_records = response.get("data")
            pagination = response.get("pagination")
            if not isinstance(raw_records, list) or not isinstance(pagination, dict):
                raise DemoLiveError("INVALID_RESPONSE_SHAPE")
            if pagination.get("is_last_page") is not True:
                raise DemoLiveError("SINGLE_PAGE_LIMIT_REACHED")
            if len(raw_records) > MAX_RESPONSE_RECORDS:
                raise DemoLiveError("RESPONSE_PAGE_LIMIT_EXCEEDED")
            response_chain = response.get("chain")
            response_token = response.get("token_address")
            response_label = response.get("label", response.get("flow_label"))
            if response_chain is not None and str(response_chain).lower() != CHAIN:
                raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
            if response_token is not None and str(response_token).lower() != TOKEN_IDENTITIES[CHAIN].lower():
                raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
            if response_label is not None and response_label != FLOW_LABEL:
                raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
            warnings = response.get("warnings", [])
            if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
                raise DemoLiveError("WARNING_POLICY_REJECTED")
            page = PaginationPageMetadata(page=1, warnings=tuple(warnings))
            try:
                warning_summary = classify_page_warnings("flows", FLOW_LABEL, page) if warnings else []
            except SourceWarningError as exc:
                raise DemoLiveError("WARNING_POLICY_REJECTED") from exc

            for raw in raw_records:
                if not isinstance(raw, dict):
                    raise DemoLiveError("INVALID_RESPONSE_SHAPE")
                if "chain" in raw and raw["chain"] != CHAIN:
                    raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
                if "token_address" in raw and str(raw["token_address"]).lower() != TOKEN_IDENTITIES[CHAIN].lower():
                    raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
                if "flow_label" in raw and raw["flow_label"] != FLOW_LABEL:
                    raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
                if "label" in raw and raw["label"] != FLOW_LABEL:
                    raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
            models = normalize_flows(
                response,
                chain=CHAIN,
                token_address=TOKEN_IDENTITIES[CHAIN],
                flow_label=FLOW_LABEL,
            )
            try:
                validate_warning_structure([warning_summary] if warning_summary else [], models, endpoint="flows")
            except SourceWarningError as exc:
                raise DemoLiveError("WARNING_POLICY_REJECTED") from exc
        except DemoLiveError:
            raise
        except NansenError as exc:
            raise DemoLiveError("NANSEN_REQUEST_FAILED") from exc
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise DemoLiveError("INVALID_RESPONSE_DATA") from exc

        if not models:
            raise DemoLiveError("NO_HOURLY_BUCKETS")
        if self.client.requests_attempted != 1:
            raise DemoLiveError("REQUEST_BUDGET_CONTRACT_FAILED")

        identities: set[datetime] = set()
        valid_complete = []
        for model in models:
            if model.chain != CHAIN or model.token_address.lower() != TOKEN_IDENTITIES[CHAIN].lower() or model.flow_label != FLOW_LABEL:
                raise DemoLiveError("RESPONSE_IDENTITY_MISMATCH")
            if model.date.tzinfo is None or model.date.utcoffset() is None:
                raise DemoLiveError("INVALID_BUCKET_TIME")
            if model.bucket_end is None or model.bucket_end.tzinfo is None or model.bucket_end.utcoffset() is None:
                raise DemoLiveError("INVALID_BUCKET_TIME")
            start = model.date.astimezone(UTC)
            end = model.bucket_end.astimezone(UTC)
            if start < window_start or start >= current_hour:
                raise DemoLiveError("BUCKET_OUTSIDE_REQUEST_WINDOW")
            if end - start != ONE_HOUR:
                raise DemoLiveError("NON_HOURLY_BUCKET")
            if start in identities:
                raise DemoLiveError("DUPLICATE_BUCKET")
            identities.add(start)
            if model.is_complete is True:
                valid_complete.append(model)
        valid_complete.sort(key=lambda item: item.date.astimezone(UTC))
        if len(valid_complete) < 2:
            raise DemoLiveError("INSUFFICIENT_COMPLETE_BUCKETS")
        previous, latest = valid_complete[-2], valid_complete[-1]
        if latest.date.astimezone(UTC) - previous.date.astimezone(UTC) != ONE_HOUR:
            raise DemoLiveError("CONSECUTIVE_HOURLY_BUCKETS_REQUIRED")
        previous_price = previous.price_usd
        latest_price = latest.price_usd
        price_return = None
        if previous_price != 0:
            price_return = float(latest_price / previous_price - Decimal(1))
            if not math.isfinite(price_return):
                raise DemoLiveError("INVALID_NUMERIC_VALUE")

        inflows = latest.total_inflows_count
        outflows = latest.total_outflows_count
        flow_total = inflows + outflows
        imbalance = None if flow_total <= 0 else float((inflows - outflows) / flow_total)
        if imbalance is not None and not math.isfinite(imbalance):
            raise DemoLiveError("INVALID_NUMERIC_VALUE")

        q05 = float(historical["q05_historical_threshold"])
        q95 = float(historical["q95_historical_threshold"])
        regime = classify_live_return(price_return, q05, q95)
        direction = {
            "POSITIVE_SHOCK_RANGE": "positive",
            "NEGATIVE_SHOCK_RANGE": "negative",
        }.get(regime)
        if direction is None:
            event_context = []
            context_message = (
                "Current 1h move is inside the historical middle 90%."
                if regime == "MIDDLE_90_PERCENT"
                else "Current 1h move is unavailable; no historical event group was selected."
            )
        else:
            event_context = [row for row in historical["event_rows"] if row["direction"] == direction]
            context_message = f"Current move entered historical {direction} shock range."
        historical_event_count = event_context[0]["event_count"] if event_context else 0
        return {
            "status": "success",
            "source": "Nansen Avalanche TGM Flows / smart_money",
            "fetch_mode": "LIVE",
            "fetched_at_utc": now.isoformat().replace("+00:00", "Z"),
            "response_record_count": len(models),
            "complete_hourly_bucket_count": len(valid_complete),
            "latest_bucket_start_utc": latest.date.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "latest_bucket_end_utc": latest.bucket_end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "latest_price_usd": _finite_float(latest_price),
            "previous_price_usd": _finite_float(previous_price),
            "price_return_1h": price_return,
            "total_inflows_count": _finite_float(inflows),
            "total_outflows_count": _finite_float(outflows),
            "flow_imbalance_share": imbalance,
            "holders_count": latest.holders_count,
            "q05_historical_threshold": q05,
            "q95_historical_threshold": q95,
            "current_regime": regime,
            "historical_reference_direction": direction,
            "historical_event_count": historical_event_count,
            "historical_event_responses": event_context,
            "decision_message": context_message,
        }


def sanitized_error_code(exc: BaseException) -> str:
    if isinstance(exc, DemoLiveError):
        return exc.code
    if isinstance(exc, NansenError):
        return "NANSEN_REQUEST_FAILED"
    return "LIVE_DATA_UNAVAILABLE"
