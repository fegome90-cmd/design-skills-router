import json
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from telemetry import contract
from telemetry.client import Telemetry
from telemetry.collector import make_server
from telemetry.host_adapter import observe_execution

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "plugin/skills/design-tree/scripts/runner.py"
OBSERVE = ROOT / "telemetry/observe.py"


class Collector:
    def __init__(self, db):
        self.db = db
        self.server = make_server(db, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def metrics(self):
        with urllib.request.urlopen(self.base + "/v1/metrics?window=all", timeout=5) as response:
            return json.loads(response.read())

    def close(self):
        if getattr(self, "closed", False):
            return
        self.closed = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.collector = Collector(self.base / "db.sqlite3")
        self.addCleanup(self.collector.close)
        self.env = {
            **os.environ,
            "DESIGN_ROUTER_TELEMETRY": "1",
            "DESIGN_ROUTER_TELEMETRY_URL": self.collector.base,
            "DESIGN_ROUTER_TELEMETRY_STATE": str(self.base / "state"),
            "DESIGN_ROUTER_TELEMETRY_TIMEOUT": "2",
        }
        self.state = self.base / "ledger.json"
        result = subprocess.run(
            [sys.executable, "-B", str(RUNNER), "--state", str(self.state),
             "init", "--project-id", "telemetry-e2e", "--scope", "synthetic"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def observe(self, *args, env=None):
        return subprocess.run(
            [sys.executable, "-B", str(OBSERVE), "--", *args],
            capture_output=True, text=True, env=env or self.env, encoding="utf-8",
        )

    def test_real_node_and_status_are_counted_without_candidate_skills(self):
        node = self.observe("--state", str(self.state), "node", "Q00")
        self.assertEqual(node.returncode, 0, node.stderr)
        status = self.observe("--state", str(self.state), "status")
        self.assertEqual(status.returncode, 0, status.stderr)
        metrics = self.collector.metrics()
        self.assertEqual(metrics["totals"]["invocations"], 2)
        self.assertEqual(metrics["totals"]["evaluations"], 2)
        self.assertGreaterEqual(metrics["totals"]["nodes_visited"], 1)
        self.assertEqual(metrics["totals"]["skills_selected"], 0)
        self.assertIn("Q00", [item["node_id"] for item in metrics["nodes"]])
        self.assertEqual(metrics["skills"], [])

    @unittest.skipUnless(os.name == "posix", "console launcher fixture uses a POSIX shebang")
    def test_console_launcher_on_path_records_a_real_node(self):
        launcher = self.base / "design-skills-router"
        launcher.write_text("#!/bin/sh\nexec " + shlex.join([sys.executable, "-B", str(RUNNER)]) + ' "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
        env = {**self.env, "PATH": str(self.base) + os.pathsep + self.env.get("PATH", "")}
        result = subprocess.run(
            [sys.executable, "-B", str(OBSERVE), "--exec", launcher.name, "--",
             "--state", str(self.state), "node", "Q00"],
            capture_output=True, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["node_id"], "Q00")
        totals = self.collector.metrics()["totals"]
        self.assertEqual((totals["invocations"], totals["nodes_visited"], totals["events"]), (1, 1, 2))

    def test_telemetry_off_does_not_touch_the_collector(self):
        env = {key: value for key, value in self.env.items() if not key.startswith("DESIGN_ROUTER_TELEMETRY")}
        result = self.observe("--state", str(self.state), "node", "Q00", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.collector.metrics()["totals"]["events"], 0)

    def test_multiple_cli_instances_aggregate_globally(self):
        def run(_):
            return self.observe("--state", str(self.state), "node", "Q00").returncode

        with ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(run, range(6)))
        self.assertEqual(codes, [0] * 6)
        metrics = self.collector.metrics()
        self.assertEqual(metrics["totals"]["evaluations"], 6)
        self.assertEqual(metrics["totals"]["nodes_visited"], 6)

    def test_counts_survive_collector_restart(self):
        self.assertEqual(self.observe("--state", str(self.state), "status").returncode, 0)
        self.collector.close()
        restarted = Collector(self.base / "db.sqlite3")
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.metrics()["totals"]["evaluations"], 1)

    def test_repeating_the_same_batch_is_idempotent_over_http(self):
        event = {
            "event_id": str(uuid.uuid4()),
            "name": "router.invoked",
            "occurred_at": contract.iso_now(),
            "source": "cli",
            "instance_id": str(uuid.uuid4()),
            "router_version": "1.3.0",
            "tree_version": "0.4",
            "evaluation_id": str(uuid.uuid4()),
            "command": "node",
        }
        body = json.dumps({"schema": contract.SCHEMA, "events": [event]}).encode()
        for _ in range(2):
            request = urllib.request.Request(
                self.collector.base + "/v1/events", data=body,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 202)
        self.assertEqual(self.collector.metrics()["totals"]["evaluations"], 1)

    def test_host_adapter_produces_real_execution_counters(self):
        client = Telemetry(contract.TelemetryConfig(
            enabled=True,
            endpoint=self.collector.base,
            timeout_seconds=2,
            state_dir=self.base / "host-state",
        ))
        with observe_execution(client, "fegome90-cmd/my-skills/break-ui"):
            pass
        with self.assertRaises(RuntimeError):
            with observe_execution(client, "fegome90-cmd/my-skills/break-ui"):
                raise RuntimeError("host failure")
        metrics = self.collector.metrics()
        self.assertEqual(metrics["totals"]["executions_started"], 2)
        self.assertEqual(metrics["totals"]["executions_completed"], 1)
        self.assertEqual(metrics["totals"]["executions_failed"], 1)
        executed = next(item for item in metrics["skills"] if item["skill_id"].endswith("/break-ui"))
        self.assertEqual(executed["executions_started"], 2)
        self.assertEqual(metrics["observability"]["skill.execution_started"], "observed")


if __name__ == "__main__":
    unittest.main()
