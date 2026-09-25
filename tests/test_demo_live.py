from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib

import pytest

from otg_nansen.config import TOKEN_IDENTITIES
from otg_nansen.demo_data import load_historical_artifacts
from otg_nansen.demo_live import DemoLiveAdapter, DemoLiveError, classify_live_return
from otg_nansen.source_warnings import NON_EXCHANGE_BREAKDOWN_UNAVAILABLE


TOKEN = TOKEN_IDENTITIES["avalanche"]
NOW = datetime(2026, 9, 25, 12, 37, tzinfo=timezone.utc)


def flow(hour, price, *, complete=True, inflows=8, outflows=2, bucket_hours=1):
    return {
        "date": f"2026-09-25T{hour:02d}:00:00Z",
        "bucket_end": f"2026-09-25T{hour + bucket_hours:02d}:00:00Z",
        "price_usd": price,
        "token_amount": 10,
        "value_usd": price * 10,
        "holders_count": 24,
        "total_inflows_count": inflows,
        "total_outflows_count": outflows,
        "is_complete": complete,
        "total_inflows_cex": None,
        "total_inflows_dex": None,
        "total_outflows_cex": None,
        "total_outflows_dex": None,
    }


def response(records, warnings=None, last=True):
    return {
        "data": records,
        "warnings": warnings or [],
        "pagination": {"page": 1, "per_page": 1000, "is_last_page": last},
    }


class FakeClient:
    def __init__(self, body):
        self.body = body
        self.requests_attempted = 0
        self.calls = []

    def request(self, endpoint, payload):
        self.requests_attempted += 1
        self.calls.append((endpoint, deepcopy(payload)))
        return deepcopy(self.body)


def historical():
    return load_historical_artifacts()


def make_adapter(body, now=NOW):
    client = FakeClient(body)
    return DemoLiveAdapter(client, now=lambda: now), client


def test_selects_two_latest_complete_hourly_buckets_and_calculates_live_metrics():
    body = response([
        flow(1, 1.0),
        flow(2, 2.0, complete=False),
        flow(3, 2.0, inflows=9, outflows=3),
        flow(4, 2.2, inflows=4, outflows=6),
    ])
    adapter, client = make_adapter(body)
    result = adapter.fetch(historical())
    assert result["latest_bucket_start_utc"] == "2026-09-25T04:00:00Z"
    assert result["latest_bucket_end_utc"] == "2026-09-25T05:00:00Z"
    assert result["complete_hourly_bucket_count"] == 3
    assert result["latest_price_usd"] == pytest.approx(2.2)
    assert result["previous_price_usd"] == pytest.approx(2.0)
    assert result["price_return_1h"] == pytest.approx(0.1)
    assert result["flow_imbalance_share"] == pytest.approx(-0.2)
    assert result["current_regime"] == "POSITIVE_SHOCK_RANGE"
    assert result["historical_reference_direction"] == "positive"
    assert len(result["historical_event_responses"]) == 12
    assert result["historical_event_count"] == 145
    assert client.requests_attempted == 1
    endpoint, payload = client.calls[0]
    assert endpoint == "/api/v1/tgm/flows"
    assert payload["chain"] == "avalanche" and payload["token_address"] == TOKEN
    assert payload["label"] == "smart_money"
    assert payload["pagination"] == {"page": 1, "per_page": 1000}
    assert payload["order_by"] == [{"field": "date", "direction": "ASC"}]
    assert payload["date"]["from"] == "2026-09-25T00:00:00Z"
    assert payload["date"]["to"] == "2026-09-25T11:59:59Z"


@pytest.mark.parametrize(
    "value,q05,q95,expected",
    [
        (0.02, -0.016, 0.017, "POSITIVE_SHOCK_RANGE"),
        (-0.02, -0.016, 0.017, "NEGATIVE_SHOCK_RANGE"),
        (0.0, -0.016, 0.017, "MIDDLE_90_PERCENT"),
        (None, -0.016, 0.017, "LIVE_RETURN_UNAVAILABLE"),
    ],
)
def test_live_regime_classification(value, q05, q95, expected):
    assert classify_live_return(value, q05, q95) == expected


def test_zero_previous_price_makes_return_unavailable_and_middle_does_not_select_events():
    adapter, _ = make_adapter(response([flow(3, 0.0), flow(4, 1.0)]))
    result = adapter.fetch(historical())
    assert result["price_return_1h"] is None
    assert result["current_regime"] == "LIVE_RETURN_UNAVAILABLE"
    assert result["historical_reference_direction"] is None
    assert result["historical_event_count"] == 0
    assert result["historical_event_responses"] == []


def test_zero_flow_denominator_is_null():
    adapter, _ = make_adapter(response([flow(3, 1.0, inflows=0, outflows=0), flow(4, 1.0, inflows=0, outflows=0)]))
    result = adapter.fetch(historical())
    assert result["flow_imbalance_share"] is None


def test_non_hourly_bucket_rejected_even_when_incomplete():
    adapter, _ = make_adapter(response([flow(3, 1.0, bucket_hours=2), flow(4, 1.1)]))
    with pytest.raises(DemoLiveError, match="NON_HOURLY_BUCKET"):
        adapter.fetch(historical())


def test_too_few_complete_buckets_rejected():
    adapter, _ = make_adapter(response([flow(3, 1.0), flow(4, 1.1, complete=False)]))
    with pytest.raises(DemoLiveError, match="INSUFFICIENT_COMPLETE_BUCKETS"):
        adapter.fetch(historical())


def test_latest_complete_buckets_must_be_consecutive_for_one_hour_return():
    adapter, _ = make_adapter(response([flow(1, 1.0), flow(2, 1.1), flow(4, 1.2)]))
    with pytest.raises(DemoLiveError, match="CONSECUTIVE_HOURLY_BUCKETS_REQUIRED"):
        adapter.fetch(historical())


def test_single_page_cap_fails_closed_instead_of_paginating():
    client = FakeClient(response([flow(3, 1.0), flow(4, 1.1)], last=False))
    adapter = DemoLiveAdapter(client, now=lambda: NOW)
    with pytest.raises(DemoLiveError, match="SINGLE_PAGE_LIMIT_REACHED"):
        adapter.fetch(historical())
    assert client.requests_attempted == 1


def test_chain_token_or_label_identity_mismatch_rejected():
    bad = flow(4, 1.1)
    bad["token_address"] = "0x0000000000000000000000000000000000000001"
    adapter, _ = make_adapter(response([flow(3, 1.0), bad]))
    with pytest.raises(DemoLiveError, match="RESPONSE_IDENTITY_MISMATCH"):
        adapter.fetch(historical())


def test_unknown_warning_rejected_without_echoing_source_text():
    warning = "private warning text that must not escape"
    adapter, _ = make_adapter(response([flow(3, 1.0), flow(4, 1.1)], warnings=[warning]))
    with pytest.raises(DemoLiveError) as error:
        adapter.fetch(historical())
    assert error.value.code == "WARNING_POLICY_REJECTED"
    assert warning not in str(error.value)


def test_known_warning_accepted_only_after_structural_guard(monkeypatch):
    import otg_nansen.source_warnings as warning_module
    warning = "synthetic accepted warning"
    fingerprint = hashlib.sha256(warning.encode("utf-8")).hexdigest()
    monkeypatch.setattr(warning_module, "KNOWN_FLOW_WARNING_FINGERPRINTS", {
        fingerprint: NON_EXCHANGE_BREAKDOWN_UNAVAILABLE,
    })
    adapter, _ = make_adapter(response([flow(3, 1.0), flow(4, 1.1)], warnings=[warning]))
    assert adapter.fetch(historical())["status"] == "success"

    broken = flow(4, 1.1)
    broken["total_inflows_cex"] = 1
    adapter, _ = make_adapter(response([flow(3, 1.0), broken], warnings=[warning]))
    with pytest.raises(DemoLiveError) as error:
        adapter.fetch(historical())
    assert error.value.code == "WARNING_POLICY_REJECTED"
    assert warning not in str(error.value)


def test_configured_client_caps_calls_retries_pages_and_timeout(monkeypatch):
    monkeypatch.setenv("NANSEN_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("NANSEN_MAX_CALLS", "50")
    monkeypatch.setenv("NANSEN_MAX_RETRIES", "4")
    monkeypatch.setenv("NANSEN_MAX_PAGES", "9")
    monkeypatch.setenv("NANSEN_TIMEOUT_SECONDS", "300")
    adapter = DemoLiveAdapter.from_env(now=lambda: NOW)
    cfg = adapter.client.config
    assert cfg.max_calls == 1 and cfg.max_retries == 0 and cfg.max_pages == 1
    assert cfg.timeout_seconds <= 120
    assert "synthetic-test-key" not in str(adapter.__dict__)


def test_custom_api_base_url_fails_before_client_creation(monkeypatch):
    monkeypatch.setenv("NANSEN_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("NANSEN_API_BASE_URL", "https://example.invalid")
    with pytest.raises(DemoLiveError, match="UNAPPROVED_NANSEN_API_BASE_URL"):
        DemoLiveAdapter.from_env(now=lambda: NOW)


def test_live_serialized_result_never_contains_client_key():
    key = "synthetic-secret-key-never-serialize"
    source_row = flow(4, 1.1)
    source_row["wallet_address"] = "synthetic-wallet-must-not-escape"
    source_row["transaction_hash"] = "synthetic-tx-must-not-escape"
    adapter, _ = make_adapter(response([flow(3, 1.0), source_row]))
    adapter.client.api_key = key
    result = adapter.fetch(historical())
    import json
    encoded = json.dumps(result)
    assert key not in encoded
    assert "synthetic-wallet-must-not-escape" not in encoded
    assert "synthetic-tx-must-not-escape" not in encoded
