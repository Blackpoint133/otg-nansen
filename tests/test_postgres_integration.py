"""Opt-in integration coverage for the isolated staging Nansen schema."""

import os
from datetime import datetime, timezone
from dataclasses import replace
import json
from pathlib import Path
from uuid import UUID

import psycopg
import pytest
from psycopg.errors import CheckViolation
from psycopg.types.json import Jsonb

from otg_nansen.models import NormalizedFlowRecord
from otg_nansen.normalize import normalize_dex_trades, normalize_flows, normalize_token_information
from otg_nansen.persistence import INGESTION_RUN_INSERT_SQL, map_dex_trade, map_flow, map_ingestion_run
from otg_nansen.postgres import PostgresRepository


pytestmark = pytest.mark.postgres
FIXTURES = Path(__file__).parent / "fixtures" / "nansen"
TOKEN = "0x0000000000000000000000000000000000000001"
RUN_IDS = [
    "00000000-0000-0011-0000-000000000001",
    "00000000-0000-0011-0000-000000000002",
    "00000000-0000-0011-0000-000000000003",
    "00000000-0000-0011-0000-000000000004",
]


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _run(run_id: str, label: str) -> dict:
    return map_ingestion_run(
        run_id=run_id, started_at=datetime(2026, 9, 22, tzinfo=timezone.utc), status="running",
        chain="avalanche", endpoint="flows", token_address=TOKEN, flow_label=label,
    )


def _count(repo, table: str, where: str, value):
    params = () if value is None else (value if isinstance(value, tuple) else (value,))
    return repo.audit_connection.execute(f"SELECT count(*) FROM nansen.{table} WHERE {where}", params).fetchone()[0]


@pytest.mark.skipif(os.getenv("NANSEN_RUN_POSTGRES_TESTS") != "1", reason="staging PostgreSQL tests are opt-in")
def test_staging_repository_lifecycle_and_constraints():
    repo = PostgresRepository.from_env()
    flow = normalize_flows(_load("flows_avalanche.json"), chain="avalanche", token_address=TOKEN, flow_label="task012_smart_money")[0]
    incomplete = replace(flow, is_complete=False)
    complete = replace(flow, is_complete=True, value_usd=flow.value_usd + 1)
    trade = replace(
        normalize_dex_trades(_load("dex_trades_avalanche.json"), chain="avalanche", token_address=TOKEN)[0],
        transaction_hash="task012_trade_identity",
    )
    token = normalize_token_information(_load("token_information_avalanche.json"), chain="avalanche", token_address=TOKEN)

    def cleanup():
        with repo.audit_connection.transaction():
            for run_id in RUN_IDS:
                repo.audit_connection.execute("DELETE FROM nansen.checkpoints WHERE last_success_run_id = %s", (run_id,))
                repo.audit_connection.execute("DELETE FROM nansen.ingestion_runs WHERE run_id = %s", (run_id,))
            repo.audit_connection.execute("DELETE FROM nansen.flows WHERE flow_label IN ('task012_smart_money', 'task012_exchange', 'task012_success', 'task012_failure')")
            repo.audit_connection.execute("DELETE FROM nansen.dex_trades WHERE transaction_hash = 'task012_trade_identity'")
            repo.audit_connection.execute("DELETE FROM nansen.token_information WHERE name = 'TASK012_TEST_TOKEN'")

    try:
        cleanup()
        repo.begin_ingestion_run(_run(RUN_IDS[0], "task012_smart_money"))
        assert _count(repo, "ingestion_runs", "run_id = %s", RUN_IDS[0]) == 1

        repo.begin_data_transaction()
        repo.store_flows([incomplete])
        repo.commit_data_transaction()
        assert _count(repo, "flows", "flow_key = %s", map_flow(incomplete)["flow_key"]) == 1

        for model in (replace(incomplete, value_usd=incomplete.value_usd + 2), complete):
            repo.begin_data_transaction()
            repo.store_flows([model])
            repo.commit_data_transaction()
        row = repo.audit_connection.execute(
            "SELECT is_complete, value_usd FROM nansen.flows WHERE flow_key = %s", (map_flow(flow)["flow_key"],)
        ).fetchone()
        assert row[0] is True
        final_value = row[1]
        repo.begin_data_transaction()
        repo.store_flows([replace(flow, is_complete=False, value_usd=999)])
        repo.commit_data_transaction()
        row = repo.audit_connection.execute("SELECT is_complete, value_usd FROM nansen.flows WHERE flow_key = %s", (map_flow(flow)["flow_key"],)).fetchone()
        assert row[0] is True and row[1] == final_value

        repo.begin_ingestion_run(_run(RUN_IDS[3], "task012_exchange"))
        scoped_exchange = replace(flow, flow_label="task012_exchange")
        repo.begin_data_transaction()
        repo.store_flows([scoped_exchange])
        repo.complete_ingestion_run(RUN_IDS[3], {"records_inserted": 1})
        repo.advance_checkpoint("avalanche", "flows", TOKEN, scoped_exchange.date, RUN_IDS[3], "task012_exchange")
        repo.commit_data_transaction()
        assert _count(repo, "flows", "flow_label IN ('task012_smart_money', 'task012_exchange')", None) == 2
        assert repo.read_checkpoint("avalanche", "flows", TOKEN, "task012_exchange")["last_success_run_id"] == UUID(RUN_IDS[3])

        repo.begin_data_transaction()
        repo.store_dex_trades([trade])
        repo.commit_data_transaction()
        repo.begin_data_transaction()
        repo.store_dex_trades([replace(trade, trader_address_label="Updated", token_name="Updated", estimated_value_usd=2)])
        repo.commit_data_transaction()
        assert _count(repo, "dex_trades", "trade_key = %s", map_dex_trade(trade)["trade_key"]) == 1

        token = replace(token, name="TASK012_TEST_TOKEN")
        retrieved = datetime(2026, 9, 22, tzinfo=timezone.utc)
        repo.begin_data_transaction()
        repo.store_token_information(token, retrieved)
        repo.commit_data_transaction()
        repo.begin_data_transaction()
        repo.store_token_information(token, retrieved)
        repo.store_token_information(token, retrieved.replace(hour=1))
        repo.commit_data_transaction()
        assert _count(repo, "token_information", "name = %s", "TASK012_TEST_TOKEN") == 2

        repo.begin_ingestion_run(_run(RUN_IDS[1], "task012_success"))
        success_flow = replace(flow, flow_label="task012_success")
        repo.begin_data_transaction()
        repo.store_flows([success_flow])
        repo.complete_ingestion_run(RUN_IDS[1], {"records_inserted": 1})
        repo.advance_checkpoint("avalanche", "flows", TOKEN, success_flow.date, RUN_IDS[1], " task012_success ")
        before = repo.audit_connection.execute("SELECT status FROM nansen.ingestion_runs WHERE run_id = %s", (RUN_IDS[1],)).fetchone()[0]
        assert before == "running"
        repo.commit_data_transaction()
        after = repo.audit_connection.execute("SELECT status FROM nansen.ingestion_runs WHERE run_id = %s", (RUN_IDS[1],)).fetchone()[0]
        checkpoint = repo.read_checkpoint("avalanche", "flows", TOKEN, "task012_success")
        assert after == "success" and checkpoint["last_success_run_id"] == UUID(RUN_IDS[1])

        newer = success_flow.date.replace(hour=13)
        older = success_flow.date.replace(hour=11)
        repo.begin_data_transaction()
        repo.advance_checkpoint("avalanche", "flows", TOKEN, newer, RUN_IDS[1], "task012_success")
        repo.commit_data_transaction()
        repo.begin_data_transaction()
        repo.advance_checkpoint("avalanche", "flows", TOKEN, older, RUN_IDS[1], "task012_success")
        repo.commit_data_transaction()
        checkpoint_timestamp = repo.read_checkpoint("avalanche", "flows", TOKEN, "task012_success")["last_complete_timestamp"]
        assert checkpoint_timestamp.astimezone(timezone.utc).hour == 13

        repo.begin_ingestion_run(_run(RUN_IDS[2], "task012_failure"))
        repo.begin_data_transaction()
        repo.store_flows([replace(flow, flow_label="task012_failure")])
        repo.complete_ingestion_run(RUN_IDS[2], {"records_inserted": 1})
        repo.advance_checkpoint("avalanche", "flows", TOKEN, flow.date, RUN_IDS[2], "task012_failure")
        repo.rollback_data_transaction()
        assert repo.read_checkpoint("avalanche", "flows", TOKEN, "task012_failure") is None
        assert repo.audit_connection.execute("SELECT status FROM nansen.ingestion_runs WHERE run_id = %s", (RUN_IDS[2],)).fetchone()[0] == "running"
        repo.fail_ingestion_run(RUN_IDS[2], "TestFailure", "synthetic rollback")
        assert repo.audit_connection.execute("SELECT status FROM nansen.ingestion_runs WHERE run_id = %s", (RUN_IDS[2],)).fetchone()[0] == "failed"

        invalid_base = list((RUN_IDS[0], datetime(2026, 9, 22, tzinfo=timezone.utc), "running", "avalanche", "flows", TOKEN, "task012_invalid", Jsonb({}), None, None, 0, 0, 0, 0, 0, 0, None, None))
        invalid_scopes = [
            {"endpoint": "flows", "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": TOKEN},
            {"chain": None, "endpoint": "flows", "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": None, "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": None, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": TOKEN, "flow_label": None},
            {"chain": 7, "endpoint": "flows", "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": {}, "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": [], "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": TOKEN, "flow_label": True},
            [],
            "not-an-object",
            {"chain": "other", "endpoint": "flows", "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "inventory", "token_address": TOKEN, "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": "0x0000000000000000000000000000000000000002", "flow_label": "task012_invalid"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": TOKEN, "flow_label": "other_scope"},
            {"chain": "avalanche", "endpoint": "flows", "token_address": TOKEN, "flow_label": ""},
        ]
        for index, scope in enumerate(invalid_scopes):
            with pytest.raises(CheckViolation):
                with repo.audit_connection.transaction():
                    values = list(invalid_base)
                    values[0] = f"00000000-0000-0011-0000-0000000001{index + 10:02d}"
                    values[7] = Jsonb(scope)
                    repo.audit_connection.execute(INGESTION_RUN_INSERT_SQL, tuple(values))
        for endpoint, flow_label, scope in (
            ("flows", "", {"chain": "avalanche", "endpoint": "flows", "token_address": TOKEN, "flow_label": ""}),
            ("inventory", "task012_invalid", {"chain": "avalanche", "endpoint": "inventory", "token_address": TOKEN, "flow_label": "task012_invalid"}),
        ):
            with pytest.raises(CheckViolation):
                with repo.audit_connection.transaction():
                    values = list(invalid_base)
                    values[0] = "00000000-0000-0011-0000-000000000099"
                    values[4] = endpoint
                    values[6] = flow_label
                    values[7] = Jsonb(scope)
                    repo.audit_connection.execute(INGESTION_RUN_INSERT_SQL, tuple(values))
    finally:
        repo.rollback_data_transaction()
        cleanup()
        assert _count(repo, "flows", "flow_label IN ('task012_smart_money', 'task012_exchange', 'task012_success', 'task012_failure')", None) == 0
        assert _count(repo, "dex_trades", "transaction_hash LIKE %s", "task012_%") == 0
        assert _count(repo, "token_information", "name = %s", "TASK012_TEST_TOKEN") == 0
        assert _count(repo, "checkpoints", "last_success_run_id IN (%s, %s, %s, %s)", tuple(RUN_IDS)) == 0
        assert _count(repo, "ingestion_runs", "run_id IN (%s, %s, %s, %s)", tuple(RUN_IDS)) == 0
        repo.close()
