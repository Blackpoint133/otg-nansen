"""Tests for review-only persistence mappings and checkpoint rules."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

import pytest

from otg_nansen.normalize import normalize_dex_trades, normalize_flows, normalize_token_information
from otg_nansen.persistence import (
    CHECKPOINT_READ_SQL,
    CHECKPOINT_UPSERT_SQL,
    DEX_TRADE_UPSERT_SQL,
    FLOW_UPSERT_SQL,
    INGESTION_RUN_FAILURE_SQL,
    INGESTION_RUN_INSERT_SQL,
    INGESTION_RUN_SUCCESS_SQL,
    TOKEN_INFORMATION_INSERT_SQL,
    InMemoryCheckpointRepository,
    InMemoryTransactionRepository,
    NansenRepository,
    PersistenceDesignError,
    _canonical_value,
    merge_flow_completeness,
    map_ingestion_run,
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
    flow = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
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
    flow = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
    trade = normalize_dex_trades(load("dex_trades_avalanche.json"), chain="avalanche", token_address=TOKEN)[0]
    assert map_flow(flow)["flow_key"] == map_flow(flow)["flow_key"]
    assert map_dex_trade(trade)["trade_key"] == map_dex_trade(trade)["trade_key"]
    assert len(map_flow(flow)["flow_key"]) == 64
    assert len(map_dex_trade(trade)["trade_key"]) == 64


def test_flow_scope_is_preserved_and_mutable_metrics_do_not_change_key():
    response = load("flows_avalanche.json")
    first = normalize_flows(response, chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
    second_response = load("flows_avalanche.json")
    second_response["data"][0]["value_usd"] = 999999
    second = normalize_flows(second_response, chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
    other_scope = normalize_flows(response, chain="avalanche", token_address=TOKEN, flow_label="exchange")[0]
    assert map_flow(first)["flow_label"] == "smart_money"
    assert map_flow(first)["flow_key"] == map_flow(second)["flow_key"]
    assert map_flow(first)["flow_key"] != map_flow(other_scope)["flow_key"]


def test_flow_key_excludes_bucket_and_observation_values():
    response = load("flows_avalanche.json")
    first = normalize_flows(response, chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
    changed = load("flows_avalanche.json")
    changed["data"][0].update({
        "bucket_end": "2026-09-21T00:00:00Z",
        "price_usd": "9",
        "value_usd": "8",
        "holders_count": 99,
        "total_inflows_count": 98,
        "total_outflows_count": 97,
        "is_complete": False,
    })
    second = normalize_flows(changed, chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
    assert map_flow(first)["flow_key"] == map_flow(second)["flow_key"]


def test_equivalent_decimal_identity_values_are_canonical():
    assert _canonical_value(Decimal("1")) == _canonical_value(Decimal("1.00")) == "1"
    assert _canonical_value(Decimal("10.500")) == "10.5"
    assert _canonical_value(Decimal("-0.00")) == "0"
    with pytest.raises(PersistenceDesignError):
        _canonical_value(Decimal("NaN"))


def test_flow_completeness_never_downgrades_complete_data():
    assert merge_flow_completeness(False, False) is False
    assert merge_flow_completeness(False, True) is True
    assert merge_flow_completeness(True, True) is True
    assert merge_flow_completeness(True, False) is True
    assert merge_flow_completeness(True, None) is True


def test_trade_key_excludes_mutable_enrichment_and_estimates():
    first = normalize_dex_trades(load("dex_trades_avalanche.json"), chain="avalanche", token_address=TOKEN)[0]
    changed_response = load("dex_trades_avalanche.json")
    changed_response["data"][0]["estimated_value_usd"] = 999999
    changed_response["data"][0]["token_name"] = "Updated Name"
    second = normalize_dex_trades(changed_response, chain="avalanche", token_address=TOKEN)[0]
    assert map_dex_trade(first)["trade_key"] == map_dex_trade(second)["trade_key"]


def test_ingestion_provenance_contains_token_and_scope():
    started = datetime(2026, 9, 22, tzinfo=timezone.utc)
    run = map_ingestion_run(
        run_id="run-1",
        started_at=started,
        status="running",
        chain="avalanche",
        endpoint="flows",
        token_address=TOKEN,
        flow_label="smart_money",
    )
    assert run["token_address"] == TOKEN
    assert run["flow_label"] == "smart_money"
    assert run["request_scope"]["flow_label"] == "smart_money"


def test_checkpoint_cannot_advance_for_partial_or_failed_run():
    repository = InMemoryCheckpointRepository()
    timestamp = datetime(2026, 9, 22, tzinfo=timezone.utc)
    with pytest.raises(PersistenceDesignError):
        repository.advance_checkpoint("avalanche", "flows", TOKEN, timestamp, "run-1", "partial", False, "smart_money")
    assert repository.read_checkpoint("avalanche", "flows", TOKEN, "smart_money") is None
    repository.advance_checkpoint("avalanche", "flows", TOKEN, timestamp, "run-2", "success", True, "smart_money")
    assert repository.read_checkpoint("avalanche", "flows", TOKEN, "smart_money")["last_success_run_id"] == "run-2"
    assert repository.read_checkpoint("avalanche", "flows", TOKEN, "exchange") is None


def test_migration_is_reviewable_but_not_executed():
    sql = Path(__file__).parents[1] / "sql" / "001_create_nansen_schema.sql"
    text = sql.read_text(encoding="utf-8")
    assert "Review-only migration artifact" in text
    for table in ("token_information", "flows", "dex_trades", "ingestion_runs", "checkpoints"):
        assert f"CREATE TABLE nansen.{table}" in text
    assert "TIMESTAMPTZ" in text
    assert "NUMERIC" in text
    assert "flow_label TEXT NOT NULL" in text
    assert "request_scope JSONB" in text
    assert "UNIQUE (chain, token_address, flow_label, date, flow_key)" not in text
    assert "UNIQUE (chain, transaction_hash, trader_address, action, token_address, traded_token_address, trade_key)" not in text


def test_parameterized_sql_contains_required_semantics():
    for statement in (
        TOKEN_INFORMATION_INSERT_SQL, FLOW_UPSERT_SQL, DEX_TRADE_UPSERT_SQL,
        INGESTION_RUN_INSERT_SQL, INGESTION_RUN_SUCCESS_SQL,
        INGESTION_RUN_FAILURE_SQL, CHECKPOINT_READ_SQL, CHECKPOINT_UPSERT_SQL,
    ):
        assert "%s" in statement
        assert "NANSEN_API_KEY" not in statement
    assert "ON CONFLICT (flow_key) DO UPDATE" in FLOW_UPSERT_SQL
    assert "WHERE nansen.flows.is_complete IS NOT TRUE OR EXCLUDED.is_complete IS TRUE" in FLOW_UPSERT_SQL
    assert "ON CONFLICT (trade_key) DO UPDATE" in DEX_TRADE_UPSERT_SQL
    assert "DO NOTHING" in TOKEN_INFORMATION_INSERT_SQL


def test_in_memory_transaction_success_and_failure_lifecycle():
    flow = normalize_flows(load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN, flow_label="smart_money")[0]
    timestamp = datetime(2026, 9, 22, tzinfo=timezone.utc)
    success = InMemoryTransactionRepository()
    success.begin_ingestion_run(map_ingestion_run(
        run_id="run-success", started_at=timestamp, status="running", chain="avalanche",
        endpoint="flows", token_address=TOKEN, flow_label="smart_money"))
    success.begin_data_transaction()
    success.store_flows([flow])
    success.advance_checkpoint("avalanche", "flows", TOKEN, timestamp, "run-success", "success", True, "smart_money")
    success.commit_data_transaction()
    success.complete_ingestion_run("run-success", {"records_inserted": 1})
    assert success.data["flows"]
    assert success.read_checkpoint("avalanche", "flows", TOKEN, "smart_money")
    assert success.ingestion_runs["run-success"]["status"] == "success"

    failed = InMemoryTransactionRepository()
    failed.begin_ingestion_run(map_ingestion_run(
        run_id="run-failed", started_at=timestamp, status="running", chain="avalanche",
        endpoint="flows", token_address=TOKEN, flow_label="smart_money"))
    failed.begin_data_transaction()
    failed.store_flows([flow])
    failed.advance_checkpoint("avalanche", "flows", TOKEN, timestamp, "run-failed", "success", True, "smart_money")
    failed.rollback_data_transaction()
    failed.fail_ingestion_run("run-failed", "NormalizationError", "safe summary")
    assert failed.data["flows"] == {}
    assert failed.read_checkpoint("avalanche", "flows", TOKEN, "smart_money") is None
    assert failed.ingestion_runs["run-failed"]["status"] == "failed"


def test_repository_protocol_exposes_full_lifecycle():
    for method in ("begin_ingestion_run", "complete_ingestion_run", "fail_ingestion_run", "begin_data_transaction", "commit_data_transaction", "rollback_data_transaction", "read_checkpoint", "advance_checkpoint"):
        assert hasattr(NansenRepository, method)
