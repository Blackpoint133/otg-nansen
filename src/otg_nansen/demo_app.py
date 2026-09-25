"""Local, read-only Meridian demo server; no database access is required."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import math
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Callable
from urllib.parse import urlsplit

from .demo_data import HistoricalArtifactError, load_historical_artifacts
from .demo_live import DemoLiveAdapter, DemoLiveError, sanitized_error_code

REFRESH_INTERVAL_SECONDS = 60 * 60
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
_PROGRAM_DATA = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
DEFAULT_STATE_PATH = Path(os.environ.get(
    "OTG_NANSEN_DEMO_STATE_PATH",
    str(_PROGRAM_DATA / "OTG" / "NansenDemo" / "live-state.json"),
))
WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
STATIC_FILES = {
    "/demo.js": ("demo.js", "text/javascript; charset=utf-8"),
    "/demo.css": ("demo.css", "text/css; charset=utf-8"),
}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    raise TypeError("response contains an unsupported value")


class DemoService:
    """Sanitized history and one process-wide, hourly live observation."""

    def __init__(
        self,
        *,
        historical_loader: Callable[[], dict[str, Any]] = load_historical_artifacts,
        live_fetch: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        state_path: Path | None = DEFAULT_STATE_PATH,
    ) -> None:
        self._historical: dict[str, Any] | None = None
        self._historical_error: str | None = None
        try:
            self._historical = historical_loader()
        except Exception:
            self._historical_error = "HISTORICAL_ARTIFACT_INVALID"
        self._live_fetch = live_fetch or self._default_live_fetch
        self._wall_clock = wall_clock
        self._state_path = Path(state_path) if state_path is not None else None
        self._state_lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._cached_live: dict[str, Any] | None = None
        self._last_attempt_utc: datetime | None = None
        self._last_error_code: str | None = None
        self._load_state()

    @staticmethod
    def next_refresh_time(now: datetime, last_attempt: datetime | None) -> datetime:
        """Return the next stable hourly slot, never less than 60 minutes apart."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must be timezone-aware")
        now = now.astimezone(timezone.utc)
        if last_attempt is None:
            return now.replace(minute=5, second=0, microsecond=0) + (timedelta(hours=1) if now.minute >= 5 else timedelta(0))
        next_at = last_attempt.astimezone(timezone.utc) + timedelta(seconds=REFRESH_INTERVAL_SECONDS)
        return max(now, next_at)

    def _load_state(self) -> None:
        if self._state_path is None:
            return
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return
            live = payload.get("last_success")
            if isinstance(live, dict) and live.get("status") == "success" and isinstance(live.get("fetched_at_utc"), str):
                self._cached_live = _json_safe(live)
            self._last_attempt_utc = _parse_timestamp(payload.get("last_attempt_utc"))
            if self._last_attempt_utc is None and self._cached_live is not None:
                self._last_attempt_utc = _parse_timestamp(self._cached_live.get("fetched_at_utc"))
            error = payload.get("last_error_code")
            self._last_error_code = error if isinstance(error, str) and error.isupper() else None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self._cached_live = None
            self._last_attempt_utc = None
            self._last_error_code = None

    def _persist_state(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "last_success": self._cached_live,
            "last_attempt_utc": _format_timestamp(self._last_attempt_utc) if self._last_attempt_utc else None,
            "last_error_code": self._last_error_code,
        }
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(prefix="live-state-", suffix=".tmp", dir=self._state_path.parent)
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as stream:
                    json.dump(payload, stream, allow_nan=False, separators=(",", ":"))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_name, self._state_path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        except OSError:
            logging.getLogger(__name__).warning("Nansen live cache persistence failed")

    def _success_is_recent(self, now: datetime) -> bool:
        cached = self._cached_live
        if not cached:
            return False
        fetched = _parse_timestamp(cached.get("fetched_at_utc"))
        return fetched is not None and timedelta(0) <= now.astimezone(timezone.utc) - fetched <= timedelta(seconds=REFRESH_INTERVAL_SECONDS)

    def live(self) -> tuple[int, dict[str, Any]]:
        """Read the shared sanitized snapshot. This endpoint never calls Nansen."""
        with self._state_lock:
            if self._cached_live is not None:
                return 200, _json_safe(dict(self._cached_live))
            return 503, {"status": "error", "error_code": "LIVE_DATA_NOT_READY"}

    def refresh_if_due(self, *, startup: bool = False) -> bool:
        """Perform at most one request when a startup/UTC hourly cycle is due."""
        now = self._wall_clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must be timezone-aware")
        now = now.astimezone(timezone.utc)
        if not self._refresh_lock.acquire(blocking=False):
            return False
        try:
            with self._state_lock:
                if startup and self._success_is_recent(now):
                    return False
                if self._last_attempt_utc is not None and now - self._last_attempt_utc < timedelta(seconds=REFRESH_INTERVAL_SECONDS):
                    return False
                if not startup and (self._last_attempt_utc is None or now - self._last_attempt_utc < timedelta(seconds=REFRESH_INTERVAL_SECONDS)):
                    return False
                self._last_attempt_utc = now
                self._last_error_code = None
                self._persist_state()
                historical = self._historical
            try:
                if historical is None:
                    raise DemoLiveError("HISTORICAL_ARTIFACT_INVALID")
                result = _json_safe(self._live_fetch(historical))
                if not isinstance(result, dict) or result.get("status") != "success":
                    raise DemoLiveError("INVALID_LIVE_SERVICE_RESULT")
                result["fetched_at_utc"] = _format_timestamp(self._wall_clock())
                result.pop("fetch_mode", None)
                with self._state_lock:
                    self._cached_live = result
                    self._last_error_code = None
                    self._persist_state()
                return True
            except Exception as exc:
                code = sanitized_error_code(exc)
                with self._state_lock:
                    self._last_error_code = code
                    self._persist_state()
                logging.getLogger(__name__).warning("Nansen hourly refresh failed: %s", code)
                return False
        finally:
            self._refresh_lock.release()

    def start_scheduler(self) -> threading.Event:
        """Start one daemon scheduler for this persistent service process."""
        stop_event = threading.Event()

        def run() -> None:
            self.refresh_if_due(startup=True)
            while not stop_event.is_set():
                now = self._wall_clock()
                with self._state_lock:
                    next_at = self.next_refresh_time(now, self._last_attempt_utc)
                delay = max(0.1, (next_at - now.astimezone(timezone.utc)).total_seconds())
                if stop_event.wait(delay):
                    break
                self.refresh_if_due()

        threading.Thread(target=run, name="nansen-hourly-refresh", daemon=True).start()
        return stop_event

    @staticmethod
    def _default_live_fetch(historical: dict[str, Any]) -> dict[str, Any]:
        return DemoLiveAdapter.from_env().fetch(historical)

    def history(self) -> tuple[int, dict[str, Any]]:
        if self._historical is None:
            return 503, {"status": "error", "error_code": self._historical_error or "HISTORICAL_ARTIFACT_INVALID"}
        return 200, _json_safe({"status": "success", **self._historical})

    def health(self) -> tuple[int, dict[str, Any]]:
        return 200, {
            "status": "ok",
            "historical_artifacts": "ready" if self._historical is not None else "unavailable",
            "live_data": "automatic_hourly",
            "database_required": False,
        }

    def _timestamp(self) -> str:
        return _format_timestamp(self._wall_clock())


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def make_handler(service: DemoService, web_root: Path = WEB_ROOT):
    class Handler(BaseHTTPRequestHandler):
        server_version = "OTGNansenDemo/1"

        def log_message(self, format: str, *args: Any) -> None:
            # Never log headers, query values, response content, or credentials.
            return

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                self._static("demo.html", "text/html; charset=utf-8")
            elif path in STATIC_FILES:
                filename, content_type = STATIC_FILES[path]
                self._static(filename, content_type)
            elif path == "/api/history":
                self._json(*service.history())
            elif path == "/api/live-gun":
                self._json(*service.live())
            elif path == "/api/health":
                self._json(*service.health())
            else:
                self._json(404, {"status": "error", "error_code": "NOT_FOUND"})

        def _static(self, filename: str, content_type: str) -> None:
            try:
                body = (web_root / filename).read_bytes()
            except OSError:
                self._json(404, {"status": "error", "error_code": "STATIC_ASSET_UNAVAILABLE"})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(_json_safe(payload), allow_nan=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *, service: DemoService | None = None) -> None:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("demo server may bind only to loopback")
    service = service or DemoService()
    service.refresh_if_due(startup=True)
    server = ThreadingHTTPServer((host, port), make_handler(service))
    stop_event = service.start_scheduler()
    print(f"OTG Nansen demo listening at http://{host}:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local read-only OTG Nansen demo.")
    parser.add_argument("--serve", action="store_true", required=True)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
