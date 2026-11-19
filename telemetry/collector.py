"""Minimal HTTP collector for global Design Skills Router counters.

One process, one SQLite file, one write path. This is intentionally not an
analytics platform: it accepts a fixed event contract, stores raw accepted
events, and exposes exact aggregates plus a compact read-only dashboard.

Run:
    python3 -m telemetry.collector --db var/telemetry.sqlite3 --port 8787
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

from . import contract
from .store import Store, StoreError

DASHBOARD = Path(__file__).with_name("dashboard.html")
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
CORS_POLICIES = ("loopback", "none", "*")
DEFAULT_MAX_EVENTS_PER_MINUTE = 6000
RATE_WINDOW_SECONDS = 60.0


class EventRateLimiter:
    """Fixed-window global cap on validated events per minute.

    Bounds the write rate of any writer; it does not attribute or
    authenticate them. 429 stays retryable on purpose: it is not in the
    clients' permanent-rejection set, so a limited batch is spooled and
    retried instead of being quarantined.
    """

    def __init__(self, max_events: int):
        self.max_events = max_events
        self._lock = threading.Lock()
        self._window_start = time.monotonic()
        self._window_id = 0
        self._count = 0

    def reserve(self, amount: int) -> int | None:
        with self._lock:
            now = time.monotonic()
            if now - self._window_start >= RATE_WINDOW_SECONDS:
                self._window_start = now
                self._window_id += 1
                self._count = 0
            if self._count + amount > self.max_events:
                return None
            self._count += amount
            return self._window_id

    def allow(self, amount: int) -> bool:
        return self.reserve(amount) is not None

    def refund(self, amount: int, window_id: int | None = None) -> None:
        """Give back budget charged for a batch that was rejected before
        writing anything, so traffic that writes zero rows cannot starve
        legitimate writers for the rest of the window."""
        with self._lock:
            if window_id is not None and window_id != self._window_id:
                return
            if self._count >= amount:
                self._count -= amount


def _is_loopback(host: str) -> bool:
    return host in LOOPBACK_HOSTS


def validate_exposure(host: str, token: str | None, allow_anonymous: bool = False) -> None:
    """Refuse accidental anonymous writes when the collector leaves loopback."""
    if not _is_loopback(host) and not token and not allow_anonymous:
        raise ValueError("NON_LOOPBACK_LISTENER_REQUIRES_TOKEN_OR_EXPLICIT_ANONYMOUS_WRITES")


def normalize_cors_policy(value: str | None) -> str:
    """Resolve the cross-origin policy: 'loopback' by default, 'none', '*', or
    one explicit origin URL."""
    policy = value or "loopback"
    if policy in CORS_POLICIES:
        return policy
    try:
        parts = urlsplit(policy)
    except ValueError:
        raise ValueError("INVALID_CORS_ORIGIN") from None
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.query or parts.fragment:
        raise ValueError("INVALID_CORS_ORIGIN")
    return f"{parts.scheme}://{parts.netloc}"


def _origin_parts(origin: str):
    try:
        parts = urlsplit(origin)
    except ValueError:
        return None
    if not parts.scheme or not parts.hostname:
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    return parts.scheme.lower(), parts.hostname.lower(), port


def origin_allowed(origin: str, policy: str) -> bool:
    """Decide whether one browser origin may talk to this collector.

    CORS is not authentication: it only constrains browsers. Local processes
    send no Origin header and are not affected by this policy.
    """
    if policy == "*":
        return True
    if policy == "none":
        return False
    parsed = _origin_parts(origin)
    if parsed is None:
        return False
    if policy == "loopback":
        return parsed[1] in LOOPBACK_HOSTS
    return parsed == _origin_parts(policy)


def _window(since: str | None, until: str | None, window: str | None) -> tuple[str | None, str | None]:
    if since or until:
        return since, until
    if not window or window == "all":
        return None, None
    days = {"7d": 7, "30d": 30, "90d": 90}.get(window)
    if days is None:
        raise ValueError("INVALID_WINDOW")
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=days)).isoformat(timespec="milliseconds").replace("+00:00", "Z"), None


class TelemetryServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, store: Store, token: str | None = None,
                 cors_origin: str = "loopback", verbose: bool = False,
                 allow_anonymous: bool = False,
                 max_events_per_minute: int = DEFAULT_MAX_EVENTS_PER_MINUTE):
        validate_exposure(address[0], token, allow_anonymous)
        if (not isinstance(max_events_per_minute, int) or isinstance(max_events_per_minute, bool)
                or max_events_per_minute < 1):
            raise ValueError("INVALID_MAX_EVENTS_PER_MINUTE")
        super().__init__(address, TelemetryHandler)
        self.store = store
        self.token = token
        self.cors_origin = normalize_cors_policy(cors_origin)
        self.verbose = verbose
        self.rate_limiter = EventRateLimiter(max_events_per_minute)


class TelemetryHandler(BaseHTTPRequestHandler):
    server: TelemetryServer
    server_version = "DesignRouterTelemetry/1"
    sys_version = ""

    def log_message(self, fmt, *args):
        if self.server.verbose:
            # Deliberately omits the client address and request body.
            sys.stderr.write("telemetry %s\n" % (fmt % args))

    def _cors_allow_value(self) -> str | None:
        """The Access-Control-Allow-Origin value for this request, if any.

        Only browser requests carry Origin. Same-origin and non-browser
        clients need no CORS headers, so the value is echoed only when an
        Origin is present and the policy admits it.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return None
        if not origin_allowed(origin, self.server.cors_origin):
            return None
        return "*" if self.server.cors_origin == "*" else origin

    def _headers(self, status: int, content_type: str, length: int, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        allow_origin = self._cors_allow_value()
        if allow_origin is not None:
            self.send_header("Access-Control-Allow-Origin", allow_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "content-type, authorization")
            self.send_header("Access-Control-Expose-Headers", "Retry-After")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def _json(self, status: int, payload: dict, extra: dict | None = None):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body), extra)
        self.wfile.write(body)

    def _error(self, status: int, code: str, index: int | None = None, extra: dict | None = None):
        payload: dict[str, str | int] = {"error": code}
        if index is not None:
            payload["index"] = index
        self._json(status, payload, extra)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin")
        if origin and not origin_allowed(origin, self.server.cors_origin):
            # Refuse the preflight itself: the browser then blocks the write.
            self.close_connection = True
            self._error(403, "ORIGIN_NOT_ALLOWED")
            return
        self._headers(204, "text/plain; charset=utf-8", 0)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/healthz":
            self._json(200, {"status": "ok", "schema": contract.SCHEMA, "contract": contract.CONTRACT_VERSION})
            return
        if parsed.path == "/v1/metrics":
            try:
                query = parse_qs(parsed.query, keep_blank_values=False)
                since = query.get("since", [None])[0]
                until = query.get("until", [None])[0]
                window = query.get("window", [None])[0]
                if since:
                    since = contract.parse_time(since).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                if until:
                    until = contract.parse_time(until).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                limit = int(query.get("limit", ["20"])[0])
                if limit < 1 or limit > 100:
                    raise ValueError("INVALID_LIMIT")
                since, until = _window(since, until, window)
                metrics = self.server.store.metrics(since, until, limit)
            except (ValueError, TypeError):
                self._error(400, "INVALID_QUERY")
                return
            except sqlite3.Error:
                self._error(503, "STORE_UNAVAILABLE")
                return
            except Exception:
                self._error(500, "INTERNAL_ERROR")
                return
            self._json(200, metrics)
            return
        if parsed.path in {"/", "/index.html"}:
            try:
                body = DASHBOARD.read_bytes()
            except OSError:
                self._error(500, "DASHBOARD_UNAVAILABLE")
                return
            self._headers(
                200, "text/html; charset=utf-8", len(body),
                {"Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'self'"},
            )
            self.wfile.write(body)
            return
        self._error(404, "NOT_FOUND")

    def do_POST(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/v1/events":
            self._error(404, "NOT_FOUND")
            return
        origin = self.headers.get("Origin")
        if origin and not origin_allowed(origin, self.server.cors_origin):
            # Defense in depth behind the preflight refusal: even a request
            # that bypassed preflight checks cannot write from a browser
            # origin the policy does not admit.
            self.close_connection = True
            self._error(403, "ORIGIN_NOT_ALLOWED")
            return
        if self.server.token:
            header = self.headers.get("Authorization", "")
            if not hmac.compare_digest(
                header.encode("utf-8", "replace"),
                f"Bearer {self.server.token}".encode("utf-8"),
            ):
                self.close_connection = True
                self._error(401, "UNAUTHORIZED")
                return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self.close_connection = True
            self._error(415, "CONTENT_TYPE_MUST_BE_JSON")
            return
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            self._error(411, "CONTENT_LENGTH_REQUIRED")
            return
        try:
            length = int(raw_length)
        except ValueError:
            self._error(400, "INVALID_CONTENT_LENGTH")
            return
        if length <= 0 or length > contract.MAX_BODY_BYTES:
            self.close_connection = True
            self._error(413, "BODY_TOO_LARGE")
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self._error(400, "INCOMPLETE_BODY")
            return
        try:
            payload = json.loads(body.decode("utf-8"))
            events = contract.validate_batch(payload)
        except contract.ContractError as error:
            self._error(400, error.code, error.index)
            return
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(400, "INVALID_JSON")
            return
        window_id = self.server.rate_limiter.reserve(len(events))
        if window_id is None:
            # Bounds the write rate; retryable by design (429 is not in the
            # clients' permanent-rejection set). The batch is not counted.
            self._error(429, "RATE_LIMITED", extra={"Retry-After": "60"})
            return
        try:
            results = self.server.store.append(events)
        except StoreError as error:
            # Nothing was written (precedence/pairing rejection): refund the
            # budget this batch charged, so traffic that writes zero rows
            # cannot starve legitimate writers for the rest of the window.
            self.server.rate_limiter.refund(len(events), window_id)
            self._error(422, error.code, error.index)
            return
        except sqlite3.Error:
            self._error(503, "STORE_UNAVAILABLE")
            return
        except Exception:
            self._error(500, "INTERNAL_ERROR")
            return
        accepted = sum(item["status"] == "accepted" for item in results)
        self._json(202, {
            "schema": contract.SCHEMA,
            "accepted": accepted,
            "duplicates": len(results) - accepted,
            "results": results,
        })


def make_server(db: str | Path, host: str = "127.0.0.1", port: int = 8787,
                token: str | None = None, cors_origin: str = "loopback",
                verbose: bool = False, allow_anonymous: bool = False,
                max_events_per_minute: int = DEFAULT_MAX_EVENTS_PER_MINUTE) -> TelemetryServer:
    validate_exposure(host, token, allow_anonymous)
    policy = normalize_cors_policy(cors_origin)
    return TelemetryServer((host, port), Store(db), token, policy, verbose,
                           allow_anonymous, max_events_per_minute)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("var/telemetry.sqlite3"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--token", default=os.environ.get("DESIGN_ROUTER_TELEMETRY_COLLECTOR_TOKEN"))
    parser.add_argument(
        "--cors-origin", default=os.environ.get("DESIGN_ROUTER_TELEMETRY_CORS", "loopback"),
        help="Cross-origin policy for browser requests: 'loopback' (default, only "
             "localhost origins), 'none', an explicit origin URL, or '*' (allows any "
             "website to write; only for controlled networks).")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--allow-anonymous-writes", action="store_true",
        help="Explicitly allow unauthenticated writes on a non-loopback listener.",
    )
    parser.add_argument(
        "--max-events-per-minute",
        default=os.environ.get("DESIGN_ROUTER_TELEMETRY_MAX_EVENTS_PER_MINUTE",
                               DEFAULT_MAX_EVENTS_PER_MINUTE),
        type=int,
        help=f"Global cap on validated events accepted per minute (default "
             f"{DEFAULT_MAX_EVENTS_PER_MINUTE}, minimum {contract.MAX_BATCH_EVENTS} — "
             "one full batch). Excess batches get 429 and are "
             "retried by the clients, never counted.",
    )
    args = parser.parse_args(argv)
    # Operator-surface guard: a cap below one full batch can never admit that
    # batch, so any batch larger than the cap would retry forever. Programmatic
    # callers (tests) may set lower caps deliberately with small batches.
    if args.max_events_per_minute < contract.MAX_BATCH_EVENTS:
        parser.error(
            f"--max-events-per-minute must be at least {contract.MAX_BATCH_EVENTS} "
            "(one full batch): a lower cap strands any larger batch in endless 429 retries"
        )
    try:
        server = make_server(args.db, args.host, args.port, args.token, args.cors_origin,
                             args.verbose, args.allow_anonymous_writes,
                             args.max_events_per_minute)
    except ValueError as error:
        parser.error(str(error))
    print(f"Design Skills Router telemetry: http://{args.host}:{server.server_port}/", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
