"""Deterministic contract tests for the bounded client."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import requests

from otg_nansen.client import NansenClient
from otg_nansen.config import NansenConfig, TOKEN_IDENTITIES
from otg_nansen.errors import (
    ConfigurationError,
    NansenHTTPError,
    NansenTransportError,
    RequestBudgetExceeded,
    ResponseContractError,
    ResponseDecodeError,
)


class FakeResponse:
    def __init__(self, status_code=200, body=None, text="", headers=None):
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")
        self.headers = headers or {}

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, deepcopy(kwargs)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def client(responses, **overrides):
    settings = NansenConfig(api_key="fake-secret-key", **{"max_retries": 0, **overrides})
    session = FakeSession(responses)
    return NansenClient(settings, session=session, sleeper=lambda _: None), session


def test_config_requires_key(monkeypatch):
    monkeypatch.delenv("NANSEN_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        NansenConfig.from_env()


@pytest.mark.parametrize("variable,value", [
    ("NANSEN_TIMEOUT_SECONDS", "bad"),
    ("NANSEN_TIMEOUT_SECONDS", "0"),
    ("NANSEN_TIMEOUT_SECONDS", "-1"),
    ("NANSEN_TIMEOUT_SECONDS", "nan"),
    ("NANSEN_TIMEOUT_SECONDS", "inf"),
    ("NANSEN_RATE_PACING_SECONDS", "bad"),
    ("NANSEN_RATE_PACING_SECONDS", "-1"),
    ("NANSEN_RATE_PACING_SECONDS", "nan"),
    ("NANSEN_RATE_PACING_SECONDS", "inf"),
])
def test_invalid_float_configuration_is_safe(monkeypatch, variable, value):
    monkeypatch.setenv("NANSEN_API_KEY", "fake-secret-key")
    monkeypatch.setenv(variable, value)
    with pytest.raises(ConfigurationError) as error:
        NansenConfig.from_env()
    assert "fake-secret-key" not in str(error.value)


def test_token_configuration_is_public_and_stable():
    assert TOKEN_IDENTITIES["avalanche"].startswith("0x")
    assert TOKEN_IDENTITIES["solana"].startswith("3j")


def test_success_injects_apikey_and_returns_json():
    api, session = client([FakeResponse(body={"data": []})])
    result = api.token_information("avalanche", TOKEN_IDENTITIES["avalanche"])
    assert result == {"data": []}
    assert session.calls[0][1]["headers"]["apikey"] == "fake-secret-key"
    assert api.requests_attempted == 1


def test_malformed_json_raises_safe_error():
    api, _ = client([FakeResponse(body=ValueError(), text="not-json")])
    with pytest.raises(ResponseDecodeError, match="endpoint="):
        api.request("/bad", {})


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 422])
def test_normal_client_errors_are_not_retried(status):
    api, session = client([FakeResponse(status_code=status, text="safe error")], max_retries=2)
    with pytest.raises(NansenHTTPError) as error:
        api.request("/bad", {})
    assert error.value.status_code == status
    assert len(session.calls) == 1


@pytest.mark.parametrize("status", [429, 500])
def test_transient_errors_retry_with_bounded_backoff(status):
    api, session = client(
        [FakeResponse(status_code=status, text="temporary"), FakeResponse(body={"ok": True})],
        max_retries=1,
    )
    assert api.request("/retry", {}) == {"ok": True}
    assert len(session.calls) == 2
    assert api.requests_attempted == 2


def test_retry_after_is_honored_without_real_sleep():
    delays = []
    settings = NansenConfig(api_key="fake-secret-key", max_retries=1)
    session = FakeSession([FakeResponse(429, text="busy", headers={"Retry-After": "3"}), FakeResponse(body={})])
    api = NansenClient(settings, session=session, sleeper=delays.append)
    api.request("/retry", {})
    assert 3.0 in delays


def test_timeout_is_bounded_and_retries():
    api, session = client([requests.Timeout(), FakeResponse(body={"ok": True})], max_retries=1)
    assert api.request("/timeout", {}) == {"ok": True}
    assert api.requests_attempted == 2
    assert len(session.calls) == 2


def test_connection_failure_is_project_error_and_retries():
    api, session = client([requests.ConnectionError("connection failed"), FakeResponse(body={})], max_retries=1)
    assert api.request("/network", {}) == {}
    assert api.requests_attempted == 2
    assert len(session.calls) == 2


def test_transport_exhaustion_is_safe_and_redacts_key():
    secret = "fake-secret-key"
    settings = NansenConfig(api_key=secret, max_retries=1)
    session = FakeSession([requests.ConnectionError(f"failed with {secret}"), requests.ConnectionError(f"failed with {secret}")])
    api = NansenClient(settings, session=session, sleeper=lambda _: None)
    with pytest.raises(NansenTransportError) as error:
        api.request("/network", {})
    assert secret not in str(error.value)
    assert api.requests_attempted == 2


def test_retry_exhaustion_is_safe():
    api, _ = client([FakeResponse(503, text="temporary")], max_retries=0)
    with pytest.raises(NansenHTTPError):
        api.request("/retry", {})


def test_budget_blocks_before_next_http_request():
    api, session = client([FakeResponse(body={}), FakeResponse(body={})], max_calls=1)
    api.request("/one", {})
    with pytest.raises(RequestBudgetExceeded):
        api.request("/two", {})
    assert len(session.calls) == 1


def test_pagination_stops_on_last_page():
    responses = [
        FakeResponse(body={"data": [1], "pagination": {"is_last_page": False}}),
        FakeResponse(body={"data": [2], "pagination": {"is_last_page": True}}),
    ]
    api, session = client(responses, max_pages=5)
    assert api.paginate("/pages", {"pagination": {"page": 1, "per_page": 2}}) == [1, 2]
    assert [call[1]["json"]["pagination"]["page"] for call in session.calls] == [1, 2]


def test_pagination_stops_at_max_pages():
    responses = [FakeResponse(body={"data": [1], "pagination": {"is_last_page": False}}) for _ in range(2)]
    api, _ = client(responses, max_pages=2)
    assert api.paginate("/pages", {}) == [1, 1]


def test_pagination_rejects_non_list_data():
    api, _ = client([FakeResponse(body={"data": {"name": "GUN"}, "pagination": {"is_last_page": True}})])
    with pytest.raises(ResponseContractError):
        api.paginate("/pages", {})


def test_pagination_rejects_malformed_pagination():
    api, _ = client([FakeResponse(body={"data": [], "pagination": {}})])
    with pytest.raises(ResponseContractError):
        api.paginate("/pages", {})


def test_contract_fixtures_match_endpoint_shapes():
    fixture_dir = Path(__file__).parent / "fixtures" / "nansen"
    token = json.loads((fixture_dir / "token_information_avalanche.json").read_text(encoding="utf-8"))
    flows = json.loads((fixture_dir / "flows_avalanche.json").read_text(encoding="utf-8"))
    trades = json.loads((fixture_dir / "dex_trades_avalanche.json").read_text(encoding="utf-8"))
    assert isinstance(token["data"], dict)
    assert set(("token_details", "spot_metrics")) <= set(token["data"])
    assert isinstance(flows["data"], list)
    assert set(("date", "price_usd", "token_amount", "value_usd", "holders_count", "total_inflows_count", "total_outflows_count")) <= set(flows["data"][0])
    assert isinstance(trades["data"], list)
    assert set(("block_timestamp", "transaction_hash", "trader_address", "action", "estimated_swap_price_usd", "estimated_value_usd")) <= set(trades["data"][0])


def test_empty_fixture_shape_is_supported():
    fixture = Path(__file__).parent / "fixtures" / "nansen" / "flows_solana_empty.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert payload["data"] == []
    assert payload["pagination"]["is_last_page"] is True


def test_secret_is_not_in_exception_text():
    secret = "fake-secret-key"
    settings = NansenConfig(api_key=secret, max_retries=0)
    session = FakeSession([FakeResponse(status_code=403, text=f"invalid key {secret}")])
    api = NansenClient(settings, session=session)
    with pytest.raises(NansenHTTPError) as error:
        api.request("/secret", {})
    assert secret not in str(error.value)
    assert "[redacted]" in str(error.value)
