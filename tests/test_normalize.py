"""Fixture-only tests for the raw-to-normalized boundary."""

from copy import deepcopy
import json
from datetime import timezone
from decimal import Decimal
from pathlib import Path

import pytest

from otg_nansen.errors import NormalizationError, PaginationLimitReached
from otg_nansen.models import NormalizedDexTrade, NormalizedFlowRecord, NormalizedTokenInformation
from otg_nansen.normalize import normalize_dex_trades, normalize_flows, normalize_token_information
from otg_nansen.client import NansenClient
from otg_nansen.config import NansenConfig
from test_client import FakeResponse, client


FIXTURES = Path(__file__).parent / "fixtures" / "nansen"
TOKEN_ADDRESS = "0x0000000000000000000000000000000000000001"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_token_information_normalizes_object_and_decimals():
    model = normalize_token_information(load("token_information_avalanche.json"), chain="avalanche", token_address=TOKEN_ADDRESS)
    assert isinstance(model, NormalizedTokenInformation)
    assert model.token_address == TOKEN_ADDRESS
    assert model.market_cap_usd == Decimal("1000000.0")
    assert model.total_holders == 1000
    assert model.to_dict()["market_cap_usd"] == "1000000.0"


def test_token_information_allows_missing_optional_fields_and_extra_data():
    response = load("token_information_avalanche.json")
    response["data"].pop("spot_metrics")
    response["data"]["future_field"] = {"ignored": True}
    model = normalize_token_information(response, chain="avalanche", token_address=TOKEN_ADDRESS)
    assert model.volume_total_usd is None


@pytest.mark.parametrize("response", [{}, {"data": []}, {"data": {"name": "GUN"}}])
def test_token_information_rejects_malformed_container(response):
    with pytest.raises(NormalizationError):
        normalize_token_information(response, chain="avalanche", token_address=TOKEN_ADDRESS)


def test_token_information_rejects_identity_mismatch():
    response = load("token_information_avalanche.json")
    response["data"]["contract_address"] = "0xOTHER"
    with pytest.raises(NormalizationError, match="identity"):
        normalize_token_information(response, chain="avalanche", token_address=TOKEN_ADDRESS)


def test_flows_normalize_and_convert_to_utc():
    model = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN_ADDRESS, flow_label="smart_money")[0]
    assert isinstance(model, NormalizedFlowRecord)
    assert model.date.tzinfo is timezone.utc
    assert model.price_usd == Decimal("0.01")
    assert model.total_inflows_count == 5
    assert model.to_dict()["date"] == "2026-09-20T12:00:00Z"


def test_flows_convert_positive_and_negative_offsets():
    response = load("flows_avalanche.json")
    response["data"][0]["date"] = "2026-09-20T14:00:00+02:00"
    response["data"][0]["bucket_end"] = "2026-09-20T07:00:00-05:00"
    model = normalize_flows(response, chain="avalanche", token_address=TOKEN_ADDRESS, flow_label="smart_money")[0]
    assert model.date.isoformat() == "2026-09-20T12:00:00+00:00"
    assert model.bucket_end.isoformat() == "2026-09-20T12:00:00+00:00"


def test_empty_solana_flows_are_valid():
    assert normalize_flows(load("flows_solana_empty.json"), chain="solana", token_address="SOL_TOKEN", flow_label="smart_money") == []


@pytest.mark.parametrize("label", [None, "", "   "])
def test_flows_require_explicit_non_empty_scope(label):
    with pytest.raises(NormalizationError, match="flow_label"):
        normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN_ADDRESS, flow_label=label)


def test_flow_scope_is_trimmed_without_case_normalization():
    model = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN_ADDRESS, flow_label=" smart_money ")[0]
    assert model.flow_label == "smart_money"


@pytest.mark.parametrize("field,value", [("price_usd", "bad"), ("token_amount", "NaN"), ("value_usd", "Infinity")])
def test_flows_reject_invalid_numeric_values(field, value):
    response = load("flows_avalanche.json")
    response["data"][0][field] = value
    with pytest.raises(NormalizationError):
        normalize_flows(response, chain="avalanche", token_address=TOKEN_ADDRESS, flow_label="smart_money")


@pytest.mark.parametrize("timestamp", ["not-a-time", "2026-09-20T12:00:00"])
def test_flows_reject_malformed_or_naive_timestamps(timestamp):
    response = load("flows_avalanche.json")
    response["data"][0]["date"] = timestamp
    with pytest.raises(NormalizationError):
        normalize_flows(response, chain="avalanche", token_address=TOKEN_ADDRESS, flow_label="smart_money")


def test_flows_reject_missing_or_non_object_records():
    response = load("flows_avalanche.json")
    response["data"][0].pop("value_usd")
    with pytest.raises(NormalizationError, match="value_usd"):
        normalize_flows(response, chain="avalanche", token_address=TOKEN_ADDRESS, flow_label="smart_money")
    response["data"] = ["bad"]
    with pytest.raises(NormalizationError):
        normalize_flows(response, chain="avalanche", token_address=TOKEN_ADDRESS, flow_label="smart_money")


def test_dex_trade_normalizes_and_preserves_source_action():
    response = load("dex_trades_avalanche.json")
    response["data"][0]["future_field"] = "ignored"
    model = normalize_dex_trades(response, chain="avalanche", token_address=TOKEN_ADDRESS)[0]
    assert isinstance(model, NormalizedDexTrade)
    assert model.action == "BUY"
    assert model.block_timestamp.tzinfo is timezone.utc
    assert model.estimated_value_usd == Decimal("1.0")
    assert model.requested_token_address == TOKEN_ADDRESS


@pytest.mark.parametrize("field,value", [("estimated_value_usd", "bad"), ("token_amount", "NaN")])
def test_dex_trade_rejects_invalid_numeric_values(field, value):
    response = load("dex_trades_avalanche.json")
    response["data"][0][field] = value
    with pytest.raises(NormalizationError):
        normalize_dex_trades(response, chain="avalanche", token_address=TOKEN_ADDRESS)


def test_dex_trade_rejects_missing_critical_field_and_bad_timestamp():
    response = load("dex_trades_avalanche.json")
    response["data"][0].pop("transaction_hash")
    with pytest.raises(NormalizationError):
        normalize_dex_trades(response, chain="avalanche", token_address=TOKEN_ADDRESS)
    response = load("dex_trades_avalanche.json")
    response["data"][0]["block_timestamp"] = "2026-09-20T12:00:00"
    with pytest.raises(NormalizationError):
        normalize_dex_trades(response, chain="avalanche", token_address=TOKEN_ADDRESS)


def test_pagination_limit_is_distinct_and_reports_metadata():
    responses = [FakeResponse(body={"data": [1], "pagination": {"is_last_page": False}})]
    api, _ = client(responses, max_pages=1)
    with pytest.raises(PaginationLimitReached) as error:
        api.paginate("/pages", {})
    assert error.value.pages_fetched == 1
    assert error.value.records_collected == 1


def test_pagination_succeeds_when_last_page_is_final_allowed_page():
    api, _ = client([FakeResponse(body={"data": [1], "pagination": {"is_last_page": True}})], max_pages=1)
    assert api.paginate("/pages", {}) == [1]
