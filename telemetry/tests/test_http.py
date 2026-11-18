import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from telemetry import contract
from telemetry.collector import make_server, validate_exposure


def event(name, **fields):
    base = {
        "event_id": str(uuid.uuid4()),
        "name": name,
        "occurred_at": contract.iso_now(),
        "source": "cli",
        "instance_id": str(uuid.uuid4()),
        "router_version": "1.3.0",
        "tree_version": "0.4",
    }
    base.update(fields)
    return base


class Server:
    def __init__(self, db, token=None, store=None, max_events=None):
        self.db = db
        kwargs = {"max_events_per_minute": max_events} if max_events is not None else {}
        self.server = make_server(db, host="127.0.0.1", port=0, token=token, **kwargs)
        if store is not None:
            self.server.store = store
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        if getattr(self, "closed", False):
            return
        self.closed = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def post(self, events, token=None):
        request = urllib.request.Request(
            self.base + "/v1/events",
            data=json.dumps({"schema": contract.SCHEMA, "events": events}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as response:
            return response.status, response.read()


class BrokenStore:
    def __init__(self, error=sqlite3.OperationalError("locked")):
        self.error = error

    def append(self, events):
        raise self.error

    def metrics(self, *args, **kwargs):
        raise self.error


class HttpTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.server = Server(self.directory / "db.sqlite3")
        self.addCleanup(self.server.close)

    def test_batch_roundtrip_and_metrics(self):
        evaluation = str(uuid.uuid4())
        status, body = self.server.post([
            event("router.invoked", evaluation_id=evaluation, command="node", route="auditoria"),
            event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
            event("skill.selected", evaluation_id=evaluation, skill_id="skill/a"),
        ])
        self.assertEqual(status, 202)
        self.assertEqual(body["accepted"], 3)
        status, raw = self.server.get("/v1/metrics?window=all")
        self.assertEqual(status, 200)
        metrics = json.loads(raw)
        self.assertEqual(metrics["totals"]["evaluations"], 1)
        self.assertEqual(metrics["totals"]["skills_selected"], 1)
        self.assertEqual(metrics["skills"][0]["skill_id"], "skill/a")
        self.assertEqual(metrics["skills_executed"], [])

    def test_executed_ranking_is_served_over_http_beyond_the_selection_limit(self):
        for index in range(21):
            evaluation = str(uuid.uuid4())
            self.assertEqual(self.server.post([
                event("router.invoked", evaluation_id=evaluation, command="node"),
                event("skill.selected", evaluation_id=evaluation, skill_id=f"skill/sel-{index:02d}"),
            ])[0], 202)
        instance = str(uuid.uuid4())
        execution = str(uuid.uuid4())
        status, _ = self.server.post([
            event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node", instance_id=instance),
            event("skill.execution_started", execution_id=execution, skill_id="skill/only-executed",
                  source="host", instance_id=instance),
            event("skill.execution_completed", execution_id=execution, skill_id="skill/only-executed",
                  source="host", instance_id=instance),
        ])
        self.assertEqual(status, 202)
        metrics = json.loads(self.server.get("/v1/metrics?window=all&limit=20")[1])
        self.assertEqual(metrics["totals"]["executions_started"], 1)
        self.assertEqual(len(metrics["skills"]), 20)
        self.assertNotIn("skill/only-executed", [item["skill_id"] for item in metrics["skills"]])
        self.assertEqual([item["skill_id"] for item in metrics["skills_executed"]], ["skill/only-executed"])

    def test_retry_is_idempotent(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
        self.assertEqual(self.server.post([candidate])[0], 202)
        status, body = self.server.post([candidate])
        self.assertEqual(status, 202)
        self.assertEqual(body["duplicates"], 1)
        metrics = json.loads(self.server.get("/v1/metrics")[1])
        self.assertEqual(metrics["totals"]["evaluations"], 1)

    def test_sensitive_field_is_rejected_without_echoing_the_value(self):
        bad = {**event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node"),
               "prompt": "SECRET-SENTINEL"}
        status, body = self.server.post([bad])
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "SENSITIVE_FIELD_REJECTED")
        self.assertNotIn("SECRET-SENTINEL", json.dumps(body))

    def test_execution_orphan_is_rejected(self):
        status, body = self.server.post([
            event("skill.execution_completed", execution_id=str(uuid.uuid4()),
                  skill_id="a/b", source="host")
        ])
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "EXECUTION_NOT_STARTED")
        metrics = json.loads(self.server.get("/v1/metrics")[1])
        self.assertEqual(metrics["totals"]["executions_completed"], 0)

    def test_token_protects_writes_but_not_aggregate_reads(self):
        server = Server(self.directory / "token.sqlite3", token="s3cret")
        self.addCleanup(server.close)
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        self.assertEqual(server.post([candidate])[0], 401)
        self.assertEqual(server.post([candidate], token="wrong")[0], 401)
        self.assertEqual(server.post([candidate], token="s3cret")[0], 202)
        self.assertEqual(server.get("/v1/metrics")[0], 200)

    def test_body_limit_and_invalid_json(self):
        request = urllib.request.Request(
            self.server.base + "/v1/events",
            data=b"x" * (contract.MAX_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 413)
        request = urllib.request.Request(
            self.server.base + "/v1/events",
            data=b"{",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 400)

    def test_dashboard_is_offline_and_states_the_unobservable_limit(self):
        status, raw = self.server.get("/")
        self.assertEqual(status, 200)
        page = raw.decode("utf-8")
        self.assertIn("Telemetría global", page)
        self.assertIn("No observable", page)
        self.assertNotIn("https://", page.split("<script>")[0])

    def test_concurrent_batches_are_all_counted(self):
        def send(index):
            evaluation = str(uuid.uuid4())
            return self.server.post([
                event("router.invoked", evaluation_id=evaluation, command="node"),
                event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
                event("skill.selected", evaluation_id=evaluation, skill_id=f"skill/{index % 4}"),
            ])[0]

        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(send, range(40)))
        self.assertEqual(statuses, [202] * 40)
        metrics = json.loads(self.server.get("/v1/metrics?window=all")[1])
        self.assertEqual(metrics["totals"]["evaluations"], 40)
        self.assertEqual(sum(item["selected"] for item in metrics["skills"]), 40)

    def test_reads_are_consistent_while_writes_are_in_flight(self):
        def write(index):
            evaluation = str(uuid.uuid4())
            return self.server.post([
                event("router.invoked", evaluation_id=evaluation, command="node"),
                event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
            ])[0]

        violations = []

        def read(_):
            status, raw = self.server.get("/v1/metrics?window=all")
            if status != 200:
                violations.append(("status", status))
                return status
            metrics = json.loads(raw)
            by_name = sum(metrics["event_counts"].values())
            by_source = sum(source["events"] for source in metrics["sources"])
            if not (metrics["totals"]["events"] == by_name == by_source):
                violations.append(("mixed-snapshot", metrics["totals"]["events"], by_name, by_source))
            return status

        with ThreadPoolExecutor(max_workers=4) as pool:
            writes = pool.map(write, range(20))
            reads = [pool.submit(read, index) for index in range(20)]
            self.assertEqual(list(writes), [202] * 20)
            self.assertEqual([future.result() for future in reads], [200] * 20)
        self.assertEqual(violations[:3], [])
        metrics = json.loads(self.server.get("/v1/metrics?window=all")[1])
        self.assertEqual(metrics["totals"]["evaluations"], 20)
        self.assertEqual(metrics["totals"]["nodes_visited"], 20)
        self.assertEqual(metrics["totals"]["events"],
                         metrics["totals"]["invocations"] + metrics["totals"]["nodes_visited"])

    def test_history_windows_and_bounds_are_validated(self):
        for query in ("?window=7d", "?window=30d", "?window=90d",
                      "?since=2026-11-01T00:00:00Z", "?until=2026-11-18T00:00:00Z"):
            with self.subTest(query=query):
                self.assertEqual(self.server.get("/v1/metrics" + query)[0], 200)
        for query in ("?window=1d", "?since=not-a-date", "?limit=0", "?limit=101"):
            with self.subTest(query=query):
                try:
                    self.server.get("/v1/metrics" + query)
                    self.fail("expected HTTPError")
                except urllib.error.HTTPError as error:
                    self.assertEqual(error.code, 400)

    def test_persistence_after_restart(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        self.assertEqual(self.server.post([candidate])[0], 202)
        self.server.close()
        restarted = Server(self.directory / "db.sqlite3")
        self.addCleanup(restarted.close)
        metrics = json.loads(restarted.get("/v1/metrics")[1])
        self.assertEqual(metrics["totals"]["evaluations"], 1)

    def test_cors_preflight(self):
        request = urllib.request.Request(self.server.base + "/v1/events", method="OPTIONS")
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 204)

    def test_public_origin_preflight_is_refused(self):
        request = urllib.request.Request(
            self.server.base + "/v1/events", method="OPTIONS",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 403)
            self.assertIsNone(error.headers.get("Access-Control-Allow-Origin"))

    def test_public_origin_write_is_refused_and_never_counted(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        request = urllib.request.Request(
            self.server.base + "/v1/events",
            data=json.dumps({"schema": contract.SCHEMA, "events": [candidate]}).encode(),
            headers={"Content-Type": "application/json", "Origin": "https://evil.example"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 403)
            self.assertEqual(json.loads(error.read())["error"], "ORIGIN_NOT_ALLOWED")
        metrics = json.loads(self.server.get("/v1/metrics?window=all")[1])
        self.assertEqual(metrics["totals"]["events"], 0, "a refused write must not be counted")

    def test_loopback_origin_preflight_and_write_are_allowed(self):
        origin = f"http://127.0.0.1:{self.server.server.server_port - 1 or 8000}"
        request = urllib.request.Request(
            self.server.base + "/v1/events", method="OPTIONS",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), origin)
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        request = urllib.request.Request(
            self.server.base + "/v1/events",
            data=json.dumps({"schema": contract.SCHEMA, "events": [candidate]}).encode(),
            headers={"Content-Type": "application/json", "Origin": origin},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 202)
        metrics = json.loads(self.server.get("/v1/metrics?window=all")[1])
        self.assertEqual(metrics["totals"]["events"], 1)

    def test_explicit_cors_origin_allows_only_that_origin(self):
        server = Server(self.directory / "explicit.sqlite3")
        self.addCleanup(server.close)
        server.server.cors_origin = "https://board.internal"
        allowed = "https://board.internal"
        other = "https://other.internal"
        for origin, expected in ((allowed, 204), (other, 403)):
            with self.subTest(origin=origin):
                request = urllib.request.Request(
                    server.base + "/v1/events", method="OPTIONS",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type",
                    },
                )
                try:
                    with urllib.request.urlopen(request, timeout=5) as response:
                        self.assertEqual(response.status, expected)
                        if expected == 204:
                            self.assertEqual(
                                response.headers.get("Access-Control-Allow-Origin"), origin)
                except urllib.error.HTTPError as error:
                    self.assertEqual(error.code, expected)

    def test_wildcard_cors_is_an_explicit_opt_in(self):
        server = Server(self.directory / "wildcard.sqlite3")
        self.addCleanup(server.close)
        server.server.cors_origin = "*"
        request = urllib.request.Request(
            server.base + "/v1/events", method="OPTIONS",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    def test_null_origin_from_file_pages_is_refused_by_default(self):
        request = urllib.request.Request(
            self.server.base + "/v1/events", method="OPTIONS",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 403)


    def test_non_loopback_listener_requires_token_or_explicit_override(self):
        with self.assertRaises(ValueError):
            validate_exposure("0.0.0.0", None)
        validate_exposure("0.0.0.0", "token")
        validate_exposure("0.0.0.0", None, allow_anonymous=True)
        validate_exposure("127.0.0.1", None)

    def test_cli_refuses_non_loopback_without_token(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "-B", "-m", "telemetry.collector",
             "--db", str(self.directory / "cli.sqlite3"), "--host", "0.0.0.0", "--port", "0"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("NON_LOOPBACK_LISTENER_REQUIRES_TOKEN_OR_EXPLICIT_ANONYMOUS_WRITES", result.stderr)

    def test_cli_rejects_an_invalid_cors_policy(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "-B", "-m", "telemetry.collector",
             "--db", str(self.directory / "cli.sqlite3"), "--cors-origin", "not an origin"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID_CORS_ORIGIN", result.stderr)

    def test_server_rejects_a_non_positive_rate_limit(self):
        with self.assertRaises(ValueError) as raised:
            make_server(self.directory / "neg.sqlite3", max_events_per_minute=0)
        self.assertIn("INVALID_MAX_EVENTS_PER_MINUTE", str(raised.exception))

    def test_cli_rejects_a_rate_limit_below_one_full_batch(self):
        root = Path(__file__).resolve().parents[2]
        # Without the guard the server would start and block forever, so the
        # subprocess needs a timeout to fail fast on regression.
        result = subprocess.run(
            [sys.executable, "-B", "-m", "telemetry.collector",
             "--db", str(self.directory / "cli.sqlite3"), "--max-events-per-minute", "50"],
            cwd=root, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be at least 100", result.stderr)

    def test_rate_limit_refunds_budget_for_batches_that_write_nothing(self):
        # Regression: a batch rejected with 422 (nothing written) used to
        # consume the window budget anyway, so rejected traffic starved
        # legitimate writers for the rest of the window.
        server = Server(self.directory / "refund.sqlite3", max_events=100)
        self.addCleanup(server.close)
        instance = str(uuid.uuid4())
        # Two 50-event batches of terminals with no started: 422, zero rows.
        for _ in range(2):
            status, _ = server.post([
                event("skill.execution_failed", execution_id=str(uuid.uuid4()),
                      skill_id="a/b", source="host", instance_id=instance)
                for _ in range(50)
            ])
            self.assertEqual(status, 422)
        metrics = json.loads(server.get("/v1/metrics?window=all")[1])
        self.assertEqual(metrics["totals"]["events"], 0)
        # The innocent writer must still get through in the same window.
        status, body = server.post([
            event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        ])
        self.assertEqual(status, 202)
        self.assertEqual(body["accepted"], 1)

    def test_rate_limit_bounds_accepted_events_per_minute(self):
        server = Server(self.directory / "rated.sqlite3", max_events=2)
        self.addCleanup(server.close)
        first = [
            event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node"),
            event("router.invoked", evaluation_id=str(uuid.uuid4()), command="status"),
        ]
        status, body = server.post(first)
        self.assertEqual(status, 202)
        self.assertEqual(body["accepted"], 2)
        second = [event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")]
        request = urllib.request.Request(
            server.base + "/v1/events",
            data=json.dumps({"schema": contract.SCHEMA, "events": second}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 429)
            self.assertEqual(json.loads(error.read())["error"], "RATE_LIMITED")
            self.assertEqual(error.headers.get("Retry-After"), "60")
        metrics = json.loads(server.get("/v1/metrics?window=all")[1])
        self.assertEqual(metrics["totals"]["events"], 2,
                         "a rate-limited batch must never be counted")

    def test_dashboard_csp_blocks_framing(self):
        with urllib.request.urlopen(self.server.base + "/", timeout=5) as response:
            policy = response.headers.get("Content-Security-Policy", "")
        self.assertIn("frame-ancestors 'self'", policy)

    def test_content_type_must_be_json(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        request = urllib.request.Request(
            self.server.base + "/v1/events",
            data=json.dumps({"schema": contract.SCHEMA, "events": [candidate]}).encode(),
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 415)
            self.assertEqual(json.loads(error.read())["error"], "CONTENT_TYPE_MUST_BE_JSON")

    def test_store_failure_is_isolated_as_json_503(self):
        server = Server(self.directory / "broken.sqlite3", store=BrokenStore())
        self.addCleanup(server.close)
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        request = urllib.request.Request(
            server.base + "/v1/events",
            data=json.dumps({"schema": contract.SCHEMA, "events": [candidate]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 503)
            self.assertEqual(json.loads(error.read())["error"], "STORE_UNAVAILABLE")
        try:
            urllib.request.urlopen(server.base + "/v1/metrics", timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 503)
            self.assertEqual(json.loads(error.read())["error"], "STORE_UNAVAILABLE")

    def test_unexpected_store_failure_is_isolated_as_json_500(self):
        server = Server(self.directory / "unexpected.sqlite3", store=BrokenStore(RuntimeError("boom")))
        self.addCleanup(server.close)
        try:
            urllib.request.urlopen(server.base + "/v1/metrics", timeout=5)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 500)
            self.assertEqual(json.loads(error.read())["error"], "INTERNAL_ERROR")

    def test_rate_limiter_delayed_refund_does_not_credit_next_window(self):
        from telemetry import collector
        limiter = collector.EventRateLimiter(max_events=10)
        first_window = limiter.reserve(6)
        self.assertIsNotNone(first_window)
        # Advance window past RATE_WINDOW_SECONDS so the next reservation opens a new window.
        limiter._window_start -= collector.RATE_WINDOW_SECONDS + 1
        second_window = limiter.reserve(8)
        self.assertIsNotNone(second_window)
        self.assertNotEqual(first_window, second_window)
        # A delayed refund from the first window must not free budget in the second window.
        limiter.refund(6, first_window)
        self.assertIsNone(limiter.reserve(3),
                          "delayed refund from an expired window must not credit the new window")

    def test_rate_limit_preserves_started_before_completed_against_real_collector(self):
        from telemetry.client import Telemetry
        # Allow 3 events per window; pre-fill 2 events so a 2-event batch with
        # started gets 429 while a single completed event would otherwise fit
        # and fail with 422 EXECUTION_NOT_STARTED if sent ahead of the outbox.
        server = Server(self.directory / "ratelimit-order.sqlite3", max_events=3)
        self.addCleanup(server.close)
        state_dir = self.directory / "client-state"
        config = contract.TelemetryConfig(enabled=True, endpoint=server.base, state_dir=state_dir)
        client = Telemetry(config)

        # Consume 2 of the 3 allowed events in the current window.
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
        self.assertTrue(client.flush())

        execution_id = str(uuid.uuid4())
        skill_id = "fegome90-cmd/my-skills/design-process-orchestrator"
        # Batch of 2 events exceeds remaining budget (1) -> 429 -> spooled.
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        client.emit("skill.execution_started", execution_id=execution_id, skill_id=skill_id, source="host")
        self.assertFalse(client.flush())
        self.assertEqual(len(list(state_dir.glob("outbox-*.jsonl"))), 1)

        # Now emit completed (1 event, which would fit the remaining budget of 1
        # if sent ahead of the spooled outbox!). Client must preserve order and
        # NOT send completed ahead of the pending outbox.
        client.emit("skill.execution_completed", execution_id=execution_id, skill_id=skill_id, source="host")
        self.assertFalse(client.flush())
        self.assertEqual(list(state_dir.glob("rejected-*.jsonl")), [],
                         "completed must never be sent ahead of spooled started and quarantined")

        # Advance collector rate-limit window and flush again.
        server.server.rate_limiter._window_start -= 120
        self.assertTrue(client.flush())
        self.assertEqual(list(state_dir.glob("outbox-*.jsonl")), [])
        self.assertEqual(list(state_dir.glob("rejected-*.jsonl")), [])
        metrics = server.server.store.metrics()
        self.assertEqual(metrics["totals"]["executions_started"], 1)
        self.assertEqual(metrics["totals"]["executions_completed"], 1)


if __name__ == "__main__":
    unittest.main()
