from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

from datetime import datetime, timedelta, timezone

from otg_nansen.demo_app import REFRESH_INTERVAL_SECONDS, DemoService, make_handler
from otg_nansen.demo_data import load_historical_artifacts


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class RunningServer:
    def __init__(self, service):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service, WEB))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def get(self, path):
        try:
            response = urlopen(self.base + path, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers.get("Content-Type", ""), response.read()


def test_api_history_shape_health_and_static_routes_without_live_call():
    calls = []
    service = DemoService(live_fetch=lambda _: calls.append("live") or {"status": "success"})
    server = RunningServer(service)
    try:
        status, content_type, html = server.get("/")
        assert status == 200 and "text/html" in content_type
        assert b"LIVE NANSEN DATA" in html
        assert b"/demo.js" in html and b"/demo.css" in html
        _, _, js = server.get("/demo.js")
        _, _, css = server.get("/demo.css")
        assert b"cdn" not in js.lower() and b"cdn" not in css.lower()
        status, _, health_bytes = server.get("/api/health")
        health = json.loads(health_bytes)
        assert status == 200 and health["database_required"] is False
        assert health["live_data"] == "automatic_hourly"
        status, _, history_bytes = server.get("/api/history")
        history = json.loads(history_bytes)
        assert status == 200 and len(history["relationship_rows"]) == 12
        assert len(history["event_rows"]) == 24
        assert calls == []
    finally:
        server.close()


def test_frontend_reads_and_interactions_never_trigger_shared_live_refresh():
    fake_clock = [datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc)]
    calls = []

    def live_fetch(hist):
        calls.append(hist["snapshot_digest"])
        return {
            "status": "success", "source": "Nansen Avalanche TGM Flows / smart_money",
            "fetched_at_utc": "ignored",
            "price_return_1h": 0.0, "current_regime": "MIDDLE_90_PERCENT",
            "historical_reference_direction": None, "historical_event_count": 0,
            "historical_event_responses": [], "decision_message": "middle",
        }

    service = DemoService(live_fetch=live_fetch, wall_clock=lambda: fake_clock[0], state_path=None)
    assert service.refresh_if_due(startup=True) is True
    server = RunningServer(service)
    try:
        status1, _, data1 = server.get("/api/live-gun")
        status2, _, data2 = server.get("/api/live-gun")
        body1, body2 = json.loads(data1), json.loads(data2)
        assert status1 == status2 == 200
        assert body1["fetched_at_utc"] == "2026-09-25T13:05:00Z"
        assert "fetch_mode" not in body1
        # Separate simulated users and UI interactions only read the shared snapshot.
        for _ in range(12):
            assert json.loads(server.get("/api/live-gun")[2]) == body2
        assert len(calls) == 1
        fake_clock[0] = datetime(2026, 9, 25, 14, 5, 2, tzinfo=timezone.utc)
        assert service.refresh_if_due() is True
        _, _, data3 = server.get("/api/live-gun")
        assert json.loads(data3)["fetched_at_utc"] == "2026-09-25T14:05:02Z"
        assert len(calls) == 2
    finally:
        server.close()


def test_failed_hourly_refresh_preserves_last_successful_result():
    secret = "synthetic-api-key-do-not-return"
    calls = []
    now = [datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc)]

    def fetch(_):
        calls.append(1)
        if len(calls) == 1:
            return {"status": "success", "fetched_at_utc": "old", "price_return_1h": 0.1}
        raise RuntimeError(f"request failed with {secret}")

    service = DemoService(live_fetch=fetch, wall_clock=lambda: now[0], state_path=None)
    assert service.refresh_if_due(startup=True)
    old_status, old_body = service.live()
    now[0] += timedelta(hours=1)
    assert service.refresh_if_due() is False
    server = RunningServer(service)
    try:
        status, _, data = server.get("/api/live-gun")
        assert status == old_status == 200
        assert json.loads(data) == old_body
        assert json.loads(data)["fetched_at_utc"] == "2026-09-25T13:05:00Z"
        assert secret not in data.decode()
        assert len(calls) == 2
        now[0] += timedelta(hours=1)
        assert service.refresh_if_due() is False
        assert len(calls) == 3
        assert service.live()[1] == old_body
    finally:
        server.close()


def test_hourly_cadence_is_stable_and_enforces_one_hour_minimum():
    due = DemoService.next_refresh_time
    assert due(datetime(2026, 9, 25, 13, 4, tzinfo=timezone.utc), None) == datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc)
    assert due(datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc), datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc)) == datetime(2026, 9, 25, 14, 5, tzinfo=timezone.utc)
    # The first startup attempt anchors the stable UTC minute/second cadence.
    assert due(datetime(2026, 9, 25, 13, 6, tzinfo=timezone.utc), datetime(2026, 9, 25, 13, 6, tzinfo=timezone.utc)) == datetime(2026, 9, 25, 14, 6, tzinfo=timezone.utc)


def test_concurrent_due_refreshes_are_single_flight():
    now = datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc)
    entered = threading.Event()
    release = threading.Event()
    calls = []

    def fetch(_):
        calls.append(1)
        entered.set()
        release.wait(timeout=2)
        return {"status": "success", "price_return_1h": 0.0}

    service = DemoService(live_fetch=fetch, wall_clock=lambda: now, state_path=None)
    first = threading.Thread(target=lambda: service.refresh_if_due(startup=True))
    first.start()
    assert entered.wait(timeout=1)
    second = threading.Thread(target=lambda: service.refresh_if_due(startup=True))
    second.start()
    second.join(timeout=1)
    release.set()
    first.join(timeout=2)
    assert len(calls) == 1
    assert service.live()[0] == 200


def test_persisted_success_is_shared_after_service_restart(tmp_path):
    state_path = tmp_path / "global" / "live.json"
    now = datetime(2026, 9, 25, 13, 5, tzinfo=timezone.utc)
    calls = []
    first = DemoService(live_fetch=lambda _: calls.append(1) or {"status": "success", "price_return_1h": 0.0}, wall_clock=lambda: now, state_path=state_path)
    assert first.refresh_if_due(startup=True)
    second = DemoService(live_fetch=lambda _: calls.append(2) or {}, wall_clock=lambda: now, state_path=state_path)
    assert second.refresh_if_due(startup=True) is False
    assert second.live()[1]["fetched_at_utc"] == "2026-09-25T13:05:00Z"
    assert calls == [1]


def test_historical_artifact_failure_does_not_call_live_adapter():
    calls = []
    service = DemoService(
        historical_loader=lambda: (_ for _ in ()).throw(ValueError("bad artifact")),
        live_fetch=lambda _: calls.append(1) or {},
    )
    status, body = service.history()
    assert status == 503 and body["error_code"] == "HISTORICAL_ARTIFACT_INVALID"
    status, body = service.live()
    assert status == 503 and body["error_code"] == "LIVE_DATA_NOT_READY"
    assert calls == []


def test_path_traversal_is_rejected():
    server = RunningServer(DemoService())
    try:
        status, _, _ = server.get("/%2e%2e/README.md")
        assert status == 404
    finally:
        server.close()


def test_demo_html_contract_has_live_historical_disclaimer_and_identity():
    html = (WEB / "demo.html").read_text(encoding="utf-8")
    script = (WEB / "demo.js").read_text(encoding="utf-8")
    styles = (WEB / "demo.css").read_text(encoding="utf-8")
    assert "LIVE NANSEN DATA" in html
    assert "historical relationship" in html.lower()
    assert "weak and time-inconsistent" in html
    assert "not causality or prediction" in html
    assert "Blackpoint133/otg-nansen" in html
    assert "POSITIVE_SHOCK_RANGE" in script and "NEGATIVE_SHOCK_RANGE" in script
    assert "NANSEN_API_KEY" not in html + script + styles
