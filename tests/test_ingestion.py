"""Offline tests for bounded ingestion orchestration."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from otg_nansen.client import PaginationPageMetadata, PaginationResult
from otg_nansen.errors import IncompleteSourceWindow, IngestionWindowError, PaginationLimitReached, RequestBudgetExceeded, ResponseContractError, SourceWarningError
from otg_nansen.ingestion import IngestionWindow, NansenIngestionOrchestrator, safe_failure_summary
from otg_nansen.persistence import InMemoryTransactionRepository


FIXTURES = Path(__file__).parent / "fixtures" / "nansen"
TOKEN = "0x0000000000000000000000000000000000000001"
NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)
WINDOW = IngestionWindow(datetime(2026, 9, 20, tzinfo=timezone.utc), datetime(2026, 9, 20, 23, 59, tzinfo=timezone.utc))


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeSource:
    def __init__(self, token=None, pages=None, error=None, attempts=0, page_metadata=None):
        self.token = token or load("token_information_avalanche.json")
        self.pages = pages or []
        self.error = error
        self.requests_attempted = attempts
        self.requests = []
        self.page_metadata = tuple(page_metadata or ())

    def request(self, endpoint, payload):
        self.requests_attempted += 1
        self.requests.append((endpoint, payload))
        if self.error:
            raise self.error
        return self.token

    def paginate_with_metadata(self, endpoint, payload):
        self.requests.append((endpoint, payload))
        records = []
        for page in self.pages:
            self.requests_attempted += 1
            if isinstance(page, BaseException):
                raise page
            records.extend(page)
        return PaginationResult(records, len(self.pages), self.page_metadata)


def flow_records():
    return load("flows_avalanche.json")["data"]


def trade_records():
    return load("dex_trades_avalanche.json")["data"]


def orchestrator(source, repository=None, run_ids=None):
    repository = repository or InMemoryTransactionRepository()
    ids = iter(run_ids or [f"run-{index}" for index in range(20)])
    return NansenIngestionOrchestrator(source, repository, clock=lambda: NOW, run_id_factory=lambda: next(ids)), repository


def test_window_is_utc_bounded_and_payload_is_deterministic():
    window = IngestionWindow(
        datetime(2026, 9, 20, 5, tzinfo=timezone(timedelta(hours=-7))),
        datetime(2026, 9, 20, 17, tzinfo=timezone(timedelta(hours=-7))),
    )
    assert window.start.tzinfo == timezone.utc
    assert window.to_payload() == {"from": "2026-09-20T12:00:00Z", "to": "2026-09-21T00:00:00Z"}
    with pytest.raises(IngestionWindowError):
        window.validate_against(datetime(2026, 9, 20, 23, tzinfo=timezone.utc))


def test_flow_success_audits_and_checkpoints_at_window_end():
    source = FakeSource(pages=[flow_records()])
    orchestrator_instance, repository = orchestrator(source)
    result = orchestrator_instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label=" smart_money ")
    assert result.pages_requested == 1 and result.api_calls == 1
    run = repository.ingestion_runs[result.run_id]
    assert run["status"] == "success" and run["records_received"] == 1
    checkpoint = repository.read_checkpoint("avalanche", "flows", TOKEN, "smart_money")
    assert checkpoint["last_complete_timestamp"] == WINDOW.end
    assert source.requests[0][1]["date"] == WINDOW.to_payload()
    assert source.requests[0][1]["order_by"] == [{"field": "date", "direction": "ASC"}]
    assert "order" not in source.requests[0][1]
    assert run["source_warnings"] == []


def test_benign_warning_is_audited_sanitized_and_ingested(monkeypatch):
    import otg_nansen.source_warnings as warning_policy
    synthetic = "synthetic verified breakdown notice"
    monkeypatch.setattr(warning_policy, "KNOWN_FLOW_WARNING_FINGERPRINTS", {
        hashlib.sha256(synthetic.encode("utf-8")).hexdigest(): "NON_EXCHANGE_BREAKDOWN_UNAVAILABLE"
    })
    source = FakeSource(pages=[flow_records()], page_metadata=[PaginationPageMetadata(1, (synthetic,))])
    instance, repository = orchestrator(source)
    result = instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    assert repository.ingestion_runs[result.run_id]["source_warnings"] == [
        {"page": 1, "warning_count": 1, "categories": ["NON_EXCHANGE_BREAKDOWN_UNAVAILABLE"]}
    ]


@pytest.mark.parametrize("field", ["total_inflows_cex", "total_inflows_dex", "total_outflows_cex", "total_outflows_dex"])
def test_non_null_breakdown_warning_fails_before_data_or_checkpoint(monkeypatch, field):
    import otg_nansen.source_warnings as warning_policy
    synthetic = "synthetic verified breakdown notice"
    monkeypatch.setattr(warning_policy, "KNOWN_FLOW_WARNING_FINGERPRINTS", {
        hashlib.sha256(synthetic.encode("utf-8")).hexdigest(): "NON_EXCHANGE_BREAKDOWN_UNAVAILABLE"
    })
    record = deepcopy(flow_records()[0])
    record[field] = 1
    source = FakeSource(pages=[[record]], page_metadata=[PaginationPageMetadata(1, (synthetic,))])
    instance, repository = orchestrator(source)
    with pytest.raises(SourceWarningError) as error:
        instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    run = next(iter(repository.ingestion_runs.values()))
    assert run["status"] == "failed"
    assert run["source_warnings"] == [{"page": 1, "warning_count": 1, "categories": ["UNKNOWN"]}]
    assert repository.data["flows"] == {} and repository.checkpoints == {}
    assert "synthetic verified breakdown notice" not in str(error.value)


def test_unknown_warning_fails_before_rows_or_checkpoint_commit():
    raw = "synthetic unrelated source warning"
    source = FakeSource(pages=[flow_records()], page_metadata=[PaginationPageMetadata(1, (raw,))])
    instance, repository = orchestrator(source)
    with pytest.raises(SourceWarningError) as error:
        instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    run = next(iter(repository.ingestion_runs.values()))
    assert run["status"] == "failed"
    assert run["source_warnings"] == [{"page": 1, "warning_count": 1, "categories": ["UNKNOWN"]}]
    assert raw not in str(error.value) and raw not in run["error_summary"]
    assert repository.data["flows"] == {} and repository.checkpoints == {}


def test_malformed_warning_container_retains_only_unknown_audit_evidence():
    error = ResponseContractError("Paginated endpoint returned invalid warnings: endpoint=flows page=1")
    error.page_metadata = (PaginationPageMetadata(1, ("<malformed-warning-container>",)),)
    instance, repository = orchestrator(FakeSource(pages=[error]))
    with pytest.raises(ResponseContractError):
        instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    run = next(iter(repository.ingestion_runs.values()))
    assert run["status"] == "failed"
    assert run["source_warnings"] == [{"page": 1, "warning_count": 1, "categories": ["UNKNOWN"]}]
    assert repository.data["flows"] == {} and repository.checkpoints == {}


def test_flow_multi_page_and_retry_attempt_accounting():
    second = deepcopy(flow_records()[0])
    second["date"] = "2026-09-20T13:00:00Z"
    second["bucket_end"] = "2026-09-20T13:59:59Z"
    source = FakeSource(pages=[flow_records(), [second]], attempts=1)
    orchestrator_instance, repository = orchestrator(source)
    result = orchestrator_instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    assert result.pages_requested == 2 and result.api_calls == 2
    assert repository.ingestion_runs[result.run_id]["api_calls"] == 2


def test_dex_request_uses_documented_order_by_array():
    source = FakeSource(pages=[trade_records()])
    orchestrator_instance, _ = orchestrator(source)
    orchestrator_instance.ingest_dex_trades(chain="avalanche", token_address=TOKEN, window=WINDOW)
    payload = source.requests[0][1]
    assert payload["order_by"] == [{"field": "block_timestamp", "direction": "ASC"}]
    assert "order" not in payload


def test_empty_complete_windows_succeed_for_flows_and_trades():
    source = FakeSource(pages=[[]])
    orchestrator_instance, repository = orchestrator(source, run_ids=["empty-flow", "empty-trade"])
    flow_result = orchestrator_instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    trade_result = orchestrator_instance.ingest_dex_trades(chain="avalanche", token_address=TOKEN, window=WINDOW)
    assert repository.ingestion_runs[flow_result.run_id]["status"] == "success"
    assert repository.ingestion_runs[trade_result.run_id]["status"] == "success"
    assert repository.read_checkpoint("avalanche", "flows", TOKEN, "smart_money")["last_complete_timestamp"] == WINDOW.end
    assert repository.read_checkpoint("avalanche", "dex-trades", TOKEN)["last_complete_timestamp"] == WINDOW.end


@pytest.mark.parametrize("mutator,error_type", [
    (lambda record: record.update(is_complete=False), IncompleteSourceWindow),
    (lambda record: record.update(is_complete=None), IncompleteSourceWindow),
    (lambda record: record.update(date="2026-09-21T00:00:01Z"), IngestionWindowError),
    (lambda record: record.update(bucket_end=None), IngestionWindowError),
    (lambda record: record.update(bucket_end=record["date"]), IngestionWindowError),
    (lambda record: record.update(bucket_end="2026-09-20T11:00:00Z"), IngestionWindowError),
])
def test_flow_completeness_and_window_fail_without_data_or_checkpoint(mutator, error_type):
    record = deepcopy(flow_records()[0])
    mutator(record)
    source = FakeSource(pages=[[record]])
    orchestrator_instance, repository = orchestrator(source)
    with pytest.raises(error_type):
        orchestrator_instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    run = next(iter(repository.ingestion_runs.values()))
    assert run["status"] == "failed"
    assert repository.data["flows"] == {}
    assert repository.checkpoints == {}


def test_dex_success_and_out_of_window_failure():
    source = FakeSource(pages=[trade_records()])
    orchestrator_instance, repository = orchestrator(source, run_ids=["trade-success", "trade-fail"])
    result = orchestrator_instance.ingest_dex_trades(chain="avalanche", token_address=TOKEN, window=WINDOW)
    assert repository.ingestion_runs[result.run_id]["status"] == "success"
    outside = deepcopy(trade_records()[0])
    outside["block_timestamp"] = "2026-09-21T00:00:01Z"
    with pytest.raises(IngestionWindowError):
        NansenIngestionOrchestrator(FakeSource(pages=[[outside]]), repository, clock=lambda: NOW, run_id_factory=lambda: "trade-fail").ingest_dex_trades(chain="avalanche", token_address=TOKEN, window=WINDOW)
    assert repository.ingestion_runs["trade-fail"]["status"] == "failed"


def test_token_snapshot_audits_without_checkpoint():
    source = FakeSource()
    orchestrator_instance, repository = orchestrator(source)
    result = orchestrator_instance.ingest_token_information(chain="avalanche", token_address=TOKEN)
    assert repository.ingestion_runs[result.run_id]["status"] == "success"
    assert repository.checkpoints == {}
    assert len(repository.data["token_information"]) == 1


def test_pagination_and_budget_failures_are_audited():
    for error in (PaginationLimitReached("flows", 2, 3), RequestBudgetExceeded("budget")):
        source = FakeSource(pages=[error])
        orchestrator_instance, repository = orchestrator(source)
        with pytest.raises(type(error)):
            orchestrator_instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
        assert next(iter(repository.ingestion_runs.values()))["status"] == "failed"
        assert repository.data["flows"] == {}
        run = next(iter(repository.ingestion_runs.values()))
        if isinstance(error, PaginationLimitReached):
            assert run["pages_requested"] == 2 and run["records_received"] == 3
        else:
            assert run["pages_requested"] == 0 and run["records_received"] == 0


def test_pagination_limit_preserves_sanitized_warning_audit_and_atomicity():
    metadata = [PaginationPageMetadata(1, ("synthetic warning A",)), PaginationPageMetadata(2, ("synthetic warning B",))]
    limit = PaginationLimitReached("/api/v1/tgm/flows", 2, 3, metadata)
    source = FakeSource(pages=[limit])
    instance, repository = orchestrator(source)
    with pytest.raises(PaginationLimitReached):
        instance.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    run = next(iter(repository.ingestion_runs.values()))
    assert run["source_warnings"] == [
        {"page": 1, "warning_count": 1, "categories": ["UNKNOWN"]},
        {"page": 2, "warning_count": 1, "categories": ["UNKNOWN"]},
    ]
    assert run["pages_requested"] == 2 and run["records_received"] == 3
    assert repository.data["flows"] == {} and repository.checkpoints == {}


def test_rerunning_same_window_is_idempotent_and_audited_twice():
    repository = InMemoryTransactionRepository()
    ids = iter(("rerun-1", "rerun-2"))
    first = NansenIngestionOrchestrator(FakeSource(pages=[flow_records()]), repository, clock=lambda: NOW, run_id_factory=lambda: next(ids))
    second = NansenIngestionOrchestrator(FakeSource(pages=[flow_records()]), repository, clock=lambda: NOW, run_id_factory=lambda: next(ids))
    first.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    second.ingest_flows(chain="avalanche", token_address=TOKEN, window=WINDOW, flow_label="smart_money")
    assert len(repository.data["flows"]) == 1
    assert len(repository.ingestion_runs) == 2


def test_failure_summary_is_bounded_and_redacts_secret():
    secret = "fixture-api-secret"
    summary = safe_failure_summary(RuntimeError(f"apikey={secret} details=" + "x" * 700), (secret,))
    assert len(summary) <= 500
    assert secret not in summary
    assert "[redacted]" in summary
