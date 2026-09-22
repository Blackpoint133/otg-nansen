"""Tests for review-only persistence mappings and checkpoint rules."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

import pytest

from otg_nansen.normalize import normalize_dex_trades, normalize_flows, normalize_token_information
from otg_nansen.persistence import (
    InMemoryCheckpointRepository,
    PersistenceDesignError,
    map_dex_trade,
    map_flow,
    map_token_information,
)


FIXTURES = Path(__file__).parent / "fixtures" / "nansen"
TOKEN = "0x0000000000000000000000000000000000000001"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_model_mappings_preserve_decimal_and_utc_datetime():
    token = normalize_token_information(load("token_information_avalanche.json"), chain="avalanche", token_address=TOKEN)
    flow = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN)[0]
    trade = normalize_dex_trades(load("dex_trades_avalanche.json"), chain="avalanche", token_address=TOKEN)[0]
    token_payload = map_token_information(token, datetime(2026, 9, 22, 12, tzinfo=timezone.utc))
    flow_payload = map_flow(flow)
    trade_payload = map_dex_trade(trade)
    assert isinstance(token_payload["market_cap_usd"], Decimal)
    assert isinstance(flow_payload["value_usd"], Decimal)
    assert isinstance(trade_payload["estimated_value_usd"], Decimal)
    assert flow_payload["date"].tzinfo is not None
    assert trade_payload["block_timestamp"].utcoffset().total_seconds() == 0
    assert "apikey" not in token_payload and "password" not in token_payload
    assert "apikey" not in flow_payload and "password" not in flow_payload
    assert "apikey" not in trade_payload and "password" not in trade_payload


def test_mapping_keys_are_deterministic_and_idempotency_keys_stable():
    flow = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN)[0]
    trade = normalize_dex_trades(load("dex_trades_avalanche.json"), chain="avalanche", token_address=TOKEN)[0]
    assert map_flow(flow)["flow_key"] == map_flow(flow)["flow_key"]
    assert map_dex_trade(trade)["trade_key"] == map_dex_trade(trade)["trade_key"]
    assert len(map_flow(flow)["flow_key"]) == 64
    assert len(map_dex_trade(trade)["trade_key"]) == 64


def test_checkpoint_cannot_advance_for_partial_or_failed_run():
    repository = InMemoryCheckpointRepository()
    timestamp = datetime(2026, 9, 22, tzinfo=timezone.utc)
    with pytest.raises(PersistenceDesignError):
        repository.advance_checkpoint("avalanche", "flows", TOKEN, timestamp, "run-1", "partial", False)
    assert repository.read_checkpoint("avalanche", "flows", TOKEN) is None
    repository.advance_checkpoint("avalanche", "flows", TOKEN, timestamp, "run-2", "success", True)
    assert repository.read_checkpoint("avalanche", "flows", TOKEN)["last_success_run_id"] == "run-2"


def test_migration_is_reviewable_but_not_executed():
    sql = Path(__file__).parents[1] / "sql" / "001_create_nansen_schema.sql"
    text = sql.read_text(encoding="utf-8")
    assert "Review-only migration artifact" in text
    for table in ("token_information", "flows", "dex_trades", "ingestion_runs", "checkpoints"):
        assert f"CREATE TABLE nansen.{table}" in text
    assert "TIMESTAMPTZ" in text
    assert "NUMERIC" in text
