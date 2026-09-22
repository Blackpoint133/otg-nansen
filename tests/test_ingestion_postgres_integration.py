"""Opt-in fixture-backed orchestration validation against staging PostgreSQL."""

import os
from datetime import datetime, timezone
from uuid import UUID

import pytest

from otg_nansen.ingestion import IngestionWindow, NansenIngestionOrchestrator
from otg_nansen.postgres import PostgresRepository
from test_ingestion import FakeSource, flow_records


pytestmark = pytest.mark.postgres


@pytest.mark.skipif(os.getenv("NANSEN_RUN_POSTGRES_TESTS") != "1", reason="staging PostgreSQL tests are opt-in")
def test_task014_fixture_flow_orchestration_is_idempotent():
    repo = PostgresRepository.from_env()
    token = "0x00000000000000000000000000000000000000Cc"
    label = "task014_fixture_smart_money"
    run_ids = ("00000000-0000-0014-0000-000000000001", "00000000-0000-0014-0000-000000000002")
    window = IngestionWindow(datetime(2026, 9, 20, tzinfo=timezone.utc), datetime(2026, 9, 20, 23, 59, tzinfo=timezone.utc))

    def cleanup():
        with repo.audit_connection.transaction():
            for run_id in run_ids:
                repo.audit_connection.execute("DELETE FROM nansen.checkpoints WHERE last_success_run_id = %s", (run_id,))
            repo.audit_connection.execute("DELETE FROM nansen.flows WHERE flow_label = %s", (label,))
            for run_id in run_ids:
                repo.audit_connection.execute("DELETE FROM nansen.ingestion_runs WHERE run_id = %s", (run_id,))

    try:
        cleanup()
        ids = iter(run_ids)
        for _ in run_ids:
            source = FakeSource(pages=[flow_records()])
            orchestrator = NansenIngestionOrchestrator(
                source, repo, clock=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc), run_id_factory=lambda: next(ids)
            )
            result = orchestrator.ingest_flows(chain="avalanche", token_address=token, window=window, flow_label=label)
            assert result.api_calls == 1
            assert source.requests_attempted == 1

        assert repo.audit_connection.execute("SELECT count(*) FROM nansen.flows WHERE flow_label = %s", (label,)).fetchone()[0] == 1
        runs = repo.audit_connection.execute(
            "SELECT count(*) FROM nansen.ingestion_runs WHERE run_id IN (%s, %s) AND status = 'success'", run_ids
        ).fetchone()[0]
        assert runs == 2
        checkpoint = repo.read_checkpoint("avalanche", "flows", token, label)
        assert checkpoint["last_complete_timestamp"] == window.end
        assert checkpoint["last_success_run_id"] in {UUID(run_ids[0]), UUID(run_ids[1])}
    finally:
        repo.rollback_data_transaction()
        cleanup()
        assert repo.audit_connection.execute("SELECT count(*) FROM nansen.flows WHERE flow_label = %s", (label,)).fetchone()[0] == 0
        assert repo.audit_connection.execute("SELECT count(*) FROM nansen.checkpoints WHERE flow_label = %s", (label,)).fetchone()[0] == 0
        assert repo.audit_connection.execute("SELECT count(*) FROM nansen.ingestion_runs WHERE run_id IN (%s, %s)", run_ids).fetchone()[0] == 0
        repo.close()
