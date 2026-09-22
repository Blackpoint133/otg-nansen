"""Bounded JSON client for the small initial Nansen endpoint surface."""

from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Callable, Dict, Optional

import requests

from .config import NansenConfig
from .errors import (
    ConfigurationError,
    NansenHTTPError,
    RequestBudgetExceeded,
    ResponseDecodeError,
)

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class NansenClient:
    """A small client with hard request, retry, timeout, and page bounds."""

    def __init__(
        self,
        config: NansenConfig,
        session: Optional[requests.Session] = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not config.api_key:
            raise ConfigurationError("NANSEN_API_KEY is required")
        self.config = config
        self.session = session or requests.Session()
        self._sleeper = sleeper
        self.requests_attempted = 0

    @property
    def headers(self) -> Dict[str, str]:
        return {"apikey": self.config.api_key, "Content-Type": "application/json", "Accept": "application/json"}

    def request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST one JSON request, retrying only bounded transient failures."""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        for retry_number in range(self.config.max_retries + 1):
            if self.config.rate_pacing_seconds and self.requests_attempted:
                self._sleeper(self.config.rate_pacing_seconds)
            self._reserve_request(endpoint)
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.config.timeout_seconds,
                )
            except requests.Timeout as exc:
                if retry_number >= self.config.max_retries:
                    raise NansenHTTPError(endpoint, 0, "request timed out") from exc
                self._sleeper(self._backoff(retry_number))
                continue
            if response.status_code in RETRYABLE_STATUSES and retry_number < self.config.max_retries:
                self._sleeper(self._retry_delay(response, retry_number))
                continue
            if not 200 <= response.status_code < 300:
                raise NansenHTTPError(endpoint, response.status_code, self._safe_summary(response.text))
            try:
                result = response.json()
            except ValueError as exc:
                raise ResponseDecodeError(f"Nansen response was not valid JSON: endpoint={endpoint}") from exc
            if not isinstance(result, dict):
                raise ResponseDecodeError(f"Nansen response must be a JSON object: endpoint={endpoint}")
            return result
        raise NansenHTTPError(endpoint, 0, "retry policy exhausted")

    def paginate(self, endpoint: str, payload: Dict[str, Any]) -> list[Any]:
        """Collect bounded pages until the response marks the final page."""
        request_payload = deepcopy(payload)
        pagination = dict(request_payload.get("pagination", {}))
        pagination.setdefault("page", 1)
        pagination.setdefault("per_page", self.config.page_size)
        request_payload["pagination"] = pagination
        records: list[Any] = []
        for _ in range(self.config.max_pages):
            response = self.request(endpoint, request_payload)
            data = response.get("data", [])
            if isinstance(data, list):
                records.extend(data)
            response_pagination = response.get("pagination") or {}
            if response_pagination.get("is_last_page", True):
                return records
            pagination["page"] = int(pagination["page"]) + 1
        return records

    def token_information(self, chain: str, token_address: str, timeframe: str = "1d") -> Dict[str, Any]:
        return self.request("/api/v1/tgm/token-information", {"chain": chain, "token_address": token_address, "timeframe": timeframe})

    def flows(
        self,
        chain: str,
        token_address: str,
        date: Dict[str, str],
        label: Optional[str] = None,
        pagination: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"chain": chain, "token_address": token_address, "date": date}
        if label is not None:
            payload["label"] = label
        if pagination is not None:
            payload["pagination"] = pagination
        return self.request("/api/v1/tgm/flows", payload)

    def dex_trades(
        self,
        chain: str,
        token_address: str,
        date: Optional[Dict[str, str]] = None,
        pagination: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"chain": chain, "token_address": token_address}
        if date is not None:
            payload["date"] = date
        if pagination is not None:
            payload["pagination"] = pagination
        return self.request("/api/v1/tgm/dex-trades", payload)

    def _reserve_request(self, endpoint: str) -> None:
        if self.requests_attempted >= self.config.max_calls:
            raise RequestBudgetExceeded(f"request budget exceeded before endpoint={endpoint}")
        self.requests_attempted += 1

    @staticmethod
    def _backoff(retry_number: int) -> float:
        return min(8.0, 0.5 * (2**retry_number))

    def _retry_delay(self, response: requests.Response, retry_number: int) -> float:
        value = response.headers.get("Retry-After")
        try:
            return max(0.0, min(30.0, float(value))) if value is not None else self._backoff(retry_number)
        except ValueError:
            return self._backoff(retry_number)

    def _safe_summary(self, text: str) -> str:
        summary = " ".join(text.split())[:240]
        return summary.replace(self.config.api_key, "[redacted]")
