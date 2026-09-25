"""Local, read-only Meridian demo server; no database access is required."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import threading
import time
from typing import Any, Callable
from urllib.parse import urlsplit

from .demo_data import HistoricalArtifactError, load_historical_artifacts
from .demo_live import DemoLiveAdapter, DemoLiveError, sanitized_error_code

CACHE_TTL_SECONDS = 60
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
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
    """Sanitized static history plus explicit, cached live refreshes."""

    def __init__(
        self,
        *,
        historical_loader: Callable[[], dict[str, Any]] = load_historical_artifacts,
        live_fetch: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        self._historical: dict[str, Any] | None = None
        self._historical_error: str | None = None
        try:
            self._historical = historical_loader()
        except Exception:
            self._historical_error = "HISTORICAL_ARTIFACT_INVALID"
        self._live_fetch = live_fetch or self._default_live_fetch
        self._clock = clock
        self._wall_clock = wall_clock
        self.cache_ttl_seconds = max(CACHE_TTL_SECONDS, cache_ttl_seconds)
        self._cache_lock = threading.Lock()
        self._cached_live: dict[str, Any] | None = None
        self._cached_at: float | None = None

    @staticmethod
    def _default_live_fetch(historical: dict[str, Any]) -> dict[str, Any]:
        return DemoLiveAdapter.from_env().fetch(historical)

    def history(self) -> tuple[int, dict[str, Any]]:
        if self._historical is None:
            return 503, {"status": "error", "error_code": self._historical_error or "HISTORICAL_ARTIFACT_INVALID"}
        return 200, _json_safe({"status": "success", **self._historical})

    def live(self) -> tuple[int, dict[str, Any]]:
        with self._cache_lock:
            now = self._clock()
            if self._cached_live is not None and self._cached_at is not None and now - self._cached_at < self.cache_ttl_seconds:
                cached = dict(self._cached_live)
                cached["fetch_mode"] = "CACHED"
                return (200 if cached.get("status") == "success" else 503), _json_safe(cached)
            if self._historical is None:
                result = {
                    "status": "error",
                    "error_code": "HISTORICAL_ARTIFACT_INVALID",
                    "fetch_mode": "LIVE",
                    "fetched_at_utc": self._timestamp(),
                }
            else:
                try:
                    result = _json_safe(self._live_fetch(self._historical))
                    if not isinstance(result, dict) or result.get("status") != "success":
                        raise DemoLiveError("INVALID_LIVE_SERVICE_RESULT")
                    result["fetch_mode"] = "LIVE"
                except Exception as exc:
                    result = {
                        "status": "error",
                        "error_code": sanitized_error_code(exc),
                        "fetch_mode": "LIVE",
                        "fetched_at_utc": self._timestamp(),
                    }
            self._cached_live = dict(result)
            self._cached_at = self._clock()
            return (200 if result.get("status") == "success" else 503), _json_safe(result)

    def health(self) -> tuple[int, dict[str, Any]]:
        return 200, {
            "status": "ok",
            "historical_artifacts": "ready" if self._historical is not None else "unavailable",
            "live_data": "requested_on_demand",
            "database_required": False,
        }

    def _timestamp(self) -> str:
        now = self._wall_clock()
        if now.tzinfo is None or now.utcoffset() is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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
    server = ThreadingHTTPServer((host, port), make_handler(service or DemoService()))
    print(f"OTG Nansen demo listening at http://{host}:{server.server_port}/")
    print("Live Nansen data is requested only after selecting Refresh Live Data.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
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
