"""Bounded, fixture-friendly ingestion orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Callable, Optional, Protocol
from uuid import uuid4

from .client import PaginationResult
from .errors import IncompleteSourceWindow, IngestionWindowError, PaginationLimitReached
from .models import NormalizedDexTrade, NormalizedFlowRecord, NormalizedTokenInformation
from .normalize import normalize_dex_trades, normalize_flows, normalize_token_information
from .persistence import NansenRepository, canonical_request_scope, map_ingestion_run


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise IngestionWindowError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class IngestionWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start = _utc(self.start, "window.start")
        end = _utc(self.end, "window.end")
        if start > end:
            raise IngestionWindowError("window.start must not be after window.end")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def validate_against(self, now: datetime) -> None:
        if self.end > _utc(now, "clock"):
            raise IngestionWindowError("window.end must not be in the future")

    def to_payload(self) -> dict[str, str]:
        def wire(value: datetime) -> str:
            return value.isoformat().replace("+00:00", "Z")

        return {"from": wire(self.start), "to": wire(self.end)}


@dataclass(frozen=True)
class IngestionResult:
    run_id: str
    endpoint: str
    pages_requested: int
    api_calls: int
    records_received: int
    records_normalized: int


class IngestionSource(Protocol):
    requests_attempted: int

    def request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def paginate_with_metadata(self, endpoint: str, payload: dict[str, Any]) -> PaginationResult: ...


def safe_failure_summary(error: BaseException, secrets: tuple[str, ...] = ()) -> str:
    """Return a bounded failure description without credentials or headers."""
    message = " ".join(str(error).split())
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    message = re.sub(r"(?i)(apikey|authorization|password)\s*[:=]\s*[^\s,;]+", r"\1=[redacted]", message)
    return f"{type(error).__name__}: {message[:470]}"[:500]


class NansenIngestionOrchestrator:
    """Coordinate one bounded source window and one repository lifecycle."""

    def __init__(
        self,
        source: IngestionSource,
        repository: NansenRepository,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        run_id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self.source = source
        self.repository = repository
        self.clock = clock
        self.run_id_factory = run_id_factory

    def ingest_token_information(self, *, chain: str, token_address: str, timeframe: str = "1d") -> IngestionResult:
        endpoint = "token-information"
        run_id, started_at = self._start_run(chain, endpoint, token_address, None, None)
        calls_before = self.source.requests_attempted
        pages = 0
        received = normalized = 0
        try:
            response = self.source.request("/api/v1/tgm/token-information", {
                "chain": chain, "token_address": token_address, "timeframe": timeframe,
            })
            pages = 1
            received = 1
            model = normalize_token_information(response, chain=chain, token_address=token_address)
            normalized = 1
            calls = self.source.requests_attempted - calls_before
            self.repository.begin_data_transaction()
            try:
                self.repository.store_token_information(model, _utc(self.clock(), "clock"))
                self.repository.complete_ingestion_run(run_id, self._counts(pages, calls, received, normalized))
                self.repository.commit_data_transaction()
            except BaseException:
                self.repository.rollback_data_transaction()
                raise
            return IngestionResult(run_id, endpoint, pages, calls, received, normalized)
        except BaseException as error:
            self.repository.rollback_data_transaction()
            self._fail(run_id, error, pages, self.source.requests_attempted - calls_before, received, normalized)
            raise

    def ingest_flows(self, *, chain: str, token_address: str, window: IngestionWindow, flow_label: str) -> IngestionResult:
        return self._ingest_historical("flows", chain, token_address, window, flow_label)

    def ingest_dex_trades(self, *, chain: str, token_address: str, window: IngestionWindow) -> IngestionResult:
        return self._ingest_historical("dex-trades", chain, token_address, window, None)

    def _ingest_historical(self, endpoint: str, chain: str, token_address: str, window: IngestionWindow, flow_label: Optional[str]) -> IngestionResult:
        now = _utc(self.clock(), "clock")
        window.validate_against(now)
        scope = canonical_request_scope("flows" if endpoint == "flows" else "dex-trades", flow_label)
        run_id, _ = self._start_run(chain, endpoint, token_address, scope, window)
        calls_before = self.source.requests_attempted
        pages = received = normalized = 0
        try:
            payload: dict[str, Any] = {
                "chain": chain, "token_address": token_address, "date": window.to_payload(),
                "order_by": [{"field": "date" if endpoint == "flows" else "block_timestamp", "direction": "ASC"}],
            }
            api_endpoint = "/api/v1/tgm/flows" if endpoint == "flows" else "/api/v1/tgm/dex-trades"
            if endpoint == "flows":
                payload["label"] = scope
            result = self.source.paginate_with_metadata(api_endpoint, payload)
            pages = result.pages_fetched
            received = len(result.records)
            if endpoint == "flows":
                models = normalize_flows({"data": result.records}, chain=chain, token_address=token_address, flow_label=scope)
                self._validate_flows(models, window)
            else:
                models = normalize_dex_trades({"data": result.records}, chain=chain, token_address=token_address)
                self._validate_trades(models, window)
            normalized = len(models)
            calls = self.source.requests_attempted - calls_before
            self.repository.begin_data_transaction()
            try:
                if endpoint == "flows":
                    self.repository.store_flows(models)
                else:
                    self.repository.store_dex_trades(models)
                self.repository.complete_ingestion_run(run_id, self._counts(pages, calls, received, normalized))
                self.repository.advance_checkpoint(chain, endpoint, token_address, window.end, run_id, scope or None)
                self.repository.commit_data_transaction()
            except BaseException:
                self.repository.rollback_data_transaction()
                raise
            return IngestionResult(run_id, endpoint, pages, calls, received, normalized)
        except BaseException as error:
            self.repository.rollback_data_transaction()
            if isinstance(error, PaginationLimitReached):
                pages = error.pages_fetched
                received = error.records_collected
                normalized = 0
            self._fail(run_id, error, pages, self.source.requests_attempted - calls_before, received, normalized)
            raise

    def _start_run(self, chain: str, endpoint: str, token_address: str, flow_label: Optional[str], window: Optional[IngestionWindow]) -> tuple[str, datetime]:
        started_at = _utc(self.clock(), "clock")
        scope = canonical_request_scope(endpoint, flow_label)
        run_id = self.run_id_factory()
        self.repository.begin_ingestion_run(map_ingestion_run(
            run_id=run_id, started_at=started_at, status="running", chain=chain,
            endpoint=endpoint, token_address=token_address, flow_label=scope or None,
            window_start=window.start if window else None, window_end=window.end if window else None,
        ))
        return run_id, started_at

    @staticmethod
    def _counts(pages: int, calls: int, received: int, normalized: int) -> dict[str, int]:
        return {"pages_requested": pages, "api_calls": calls, "records_received": received, "records_normalized": normalized,
                "records_inserted": 0, "records_updated_or_conflicted": 0}

    def _fail(self, run_id: str, error: BaseException, pages: int, calls: int, received: int, normalized: int) -> None:
        secrets = tuple(value for value in (getattr(getattr(self.source, "config", None), "api_key", None),) if value)
        self.repository.fail_ingestion_run(run_id, type(error).__name__, safe_failure_summary(error, secrets), counts=self._counts(pages, calls, received, normalized))

    @staticmethod
    def _validate_flows(models: list[NormalizedFlowRecord], window: IngestionWindow) -> None:
        for model in models:
            if not (window.start <= model.date <= window.end):
                raise IngestionWindowError("flow record is outside requested window")
            if model.bucket_end is None or model.bucket_end <= model.date:
                raise IngestionWindowError("flow bucket interval must have a positive bucket_end")
            if model.is_complete is not True:
                raise IncompleteSourceWindow("flow window contains an incomplete record")

    @staticmethod
    def _validate_trades(models: list[NormalizedDexTrade], window: IngestionWindow) -> None:
        for model in models:
            if not (window.start <= model.block_timestamp <= window.end):
                raise IngestionWindowError("DEX trade is outside requested window")
