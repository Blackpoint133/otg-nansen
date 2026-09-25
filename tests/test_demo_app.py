from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

from otg_nansen.demo_app import CACHE_TTL_SECONDS, DemoService, make_handler
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
        status, _, history_bytes = server.get("/api/history")
        history = json.loads(history_bytes)
        assert status == 200 and len(history["relationship_rows"]) == 12
        assert len(history["event_rows"]) == 24
        assert calls == []
    finally:
        server.close()


def test_live_endpoint_shape_and_cache_prevent_second_live_request():
    fake_clock = [10.0]
    calls = []

    def live_fetch(hist):
        calls.append(hist["snapshot_digest"])
        return {
            "status": "success", "source": "Nansen Avalanche TGM Flows / smart_money",
            "fetch_mode": "LIVE", "fetched_at_utc": "2026-09-25T12:00:00Z",
            "price_return_1h": 0.0, "current_regime": "MIDDLE_90_PERCENT",
            "historical_reference_direction": None, "historical_event_count": 0,
            "historical_event_responses": [], "decision_message": "middle",
        }

    service = DemoService(live_fetch=live_fetch, clock=lambda: fake_clock[0])
    server = RunningServer(service)
    try:
        status1, _, data1 = server.get("/api/live-gun")
        status2, _, data2 = server.get("/api/live-gun")
        body1, body2 = json.loads(data1), json.loads(data2)
        assert status1 == status2 == 200
        assert body1["fetch_mode"] == "LIVE"
        assert body2["fetch_mode"] == "CACHED"
        assert len(calls) == 1
        fake_clock[0] += CACHE_TTL_SECONDS + 1
        _, _, data3 = server.get("/api/live-gun")
        assert json.loads(data3)["fetch_mode"] == "LIVE"
        assert len(calls) == 2
    finally:
        server.close()


def test_live_error_is_sanitized_and_cached():
    secret = "synthetic-api-key-do-not-return"
    calls = []

    def fail(_):
        calls.append(1)
        raise RuntimeError(f"request failed with {secret}")

    service = DemoService(live_fetch=fail)
    server = RunningServer(service)
    try:
        status1, _, data1 = server.get("/api/live-gun")
        status2, _, data2 = server.get("/api/live-gun")
        assert status1 == status2 == 503
        body1, body2 = json.loads(data1), json.loads(data2)
        assert body1["status"] == "error"
        assert body2["fetch_mode"] == "CACHED"
        assert secret not in data1.decode() and secret not in data2.decode()
        assert len(calls) == 1
    finally:
        server.close()


def test_historical_artifact_failure_does_not_call_live_adapter():
    calls = []
    service = DemoService(
        historical_loader=lambda: (_ for _ in ()).throw(ValueError("bad artifact")),
        live_fetch=lambda _: calls.append(1) or {},
    )
    status, body = service.history()
    assert status == 503 and body["error_code"] == "HISTORICAL_ARTIFACT_INVALID"
    status, body = service.live()
    assert status == 503 and body["error_code"] == "HISTORICAL_ARTIFACT_INVALID"
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
