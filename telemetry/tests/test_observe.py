import json
import os
import signal
import subprocess
import sys
import tracemalloc
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from telemetry import observe


FAKE_RUNNER = """#!/usr/bin/env python3
import json, os, sys
payload = json.loads(os.environ.get('FAKE_OUTPUT', '{}'))
sys.stdout.write(json.dumps(payload))
sys.stderr.write('child stderr\\n')
sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
"""


class FakeClient:
    enabled = True

    def __init__(self):
        self.events = []
        self.flushed = 0

    def new_evaluation_id(self):
        return str(uuid.uuid4())

    def emit(self, name, **fields):
        self.events.append({"name": name, **fields})

    def flush(self):
        self.flushed += 1
        return True


class ObserveTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.runner = self.base / "fake_runner.py"
        self.runner.write_text(FAKE_RUNNER)
        self.runner.chmod(0o755)

    def run_main(self, args):
        with tempfile.TemporaryFile("w+") as stdout, tempfile.TemporaryFile("w+") as stderr:
            with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
                code = observe.main(args)
            stdout.seek(0)
            stderr.seek(0)
            return code, stdout.buffer.read(), stderr.buffer.read()

    def run_observe(self, args, client):
        with patch.object(observe, "client_from_env", return_value=client):
            return self.run_main(["--runner", str(self.runner), *args])

    def test_node_emits_invocation_and_visit_but_not_candidate_skills(self):
        client = FakeClient()
        payload = {
            "node_id": "Q00",
            "skills": [{"id": "fegome90-cmd/my-skills/agy-agent"}, {"id": "fegome90-cmd/my-skills/agy-agent"}],
            "summary": "must not be collected",
        }
        with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps(payload)}):
            code, stdout, stderr = self.run_observe(["--state", "x", "node", "Q00"], client)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), payload)
        self.assertEqual(stderr, b"child stderr\n")
        names = [event["name"] for event in client.events]
        self.assertEqual(names, ["router.invoked", "decision.node_visited"])
        self.assertEqual(client.events[0]["command"], "node")
        self.assertEqual(client.events[1]["node_id"], "Q00")
        self.assertNotIn("skill_id", json.dumps(client.events))
        self.assertNotIn("summary", json.dumps(client.events))
        self.assertEqual(client.flushed, 1)

    def test_propose_emits_the_selected_branch_without_proposal_content(self):
        client = FakeClient()
        proposal = self.base / "proposal.json"
        proposal.write_text(json.dumps({
            "summary": "SECRET-SENTINEL",
            "selected": "F00",
            "evidence": [{"path": "/private/secret", "note": "SECRET-SENTINEL"}],
        }))
        with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"proposal_hash": "abc"})}):
            code, _, _ = self.run_observe(["--state", "x", "propose", "Q00", "--file", str(proposal)], client)
        self.assertEqual(code, 0)
        self.assertEqual([event["name"] for event in client.events],
                         ["router.invoked", "decision.branch_selected"])
        branch = client.events[1]
        self.assertEqual((branch["node_id"], branch["branch_id"]), ("Q00", "F00"))
        self.assertNotIn("SECRET-SENTINEL", json.dumps(client.events))
        self.assertNotIn("/private/secret", json.dumps(client.events))

    def test_status_emits_only_an_invocation(self):
        client = FakeClient()
        with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"project_id": "x"})}):
            code, _, _ = self.run_observe(["--state", "x", "status"], client)
        self.assertEqual(code, 0)
        self.assertEqual([event["name"] for event in client.events], ["router.invoked"])

    def test_propose_accepts_the_equals_form_of_the_option(self):
        # Pins the '--file=PATH' form: option_value must read the file and
        # positional_after must still resolve the node id (not the option).
        client = FakeClient()
        proposal = self.base / "proposal.json"
        proposal.write_text(json.dumps({"summary": "s", "selected": "F00"}))
        with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"proposal_hash": "abc"})}):
            code, _, _ = self.run_observe(
                ["--state", "x", "propose", "Q00", f"--file={proposal}"], client)
        self.assertEqual(code, 0)
        self.assertEqual([event["name"] for event in client.events],
                         ["router.invoked", "decision.branch_selected"])
        branch = client.events[1]
        self.assertEqual((branch["node_id"], branch["branch_id"]), ("Q00", "F00"))
        self.assertNotIn(str(proposal), json.dumps(client.events))

    def test_failed_command_is_preserved_and_not_counted(self):
        client = FakeClient()
        with patch.dict(os.environ, {"FAKE_OUTPUT": "{}", "FAKE_EXIT": "2"}):
            code, _, _ = self.run_observe(["--state", "x", "node", "Q00"], client)
        self.assertEqual(code, 2)
        self.assertEqual(client.events, [])

    def test_help_is_not_counted(self):
        client = FakeClient()
        with patch.dict(os.environ, {"FAKE_OUTPUT": "{}"}):
            code, _, _ = self.run_observe(["--help"], client)
        self.assertEqual(code, 0)
        self.assertEqual(client.events, [])

    def test_invalid_telemetry_configuration_does_not_block_the_command(self):
        with patch.dict(os.environ, {
            "DESIGN_ROUTER_TELEMETRY": "1",
            "DESIGN_ROUTER_TELEMETRY_URL": "http://telemetry.example.com",
            "FAKE_OUTPUT": json.dumps({"node_id": "Q00", "skills": []}),
        }, clear=True):
            code, stdout, _ = self.run_main(["--runner", str(self.runner), "--state", "x", "node", "Q00"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"node_id": "Q00", "skills": []})

    def test_unexpected_telemetry_failure_does_not_change_exit_or_output(self):
        client = FakeClient()
        def broken_flush():
            raise RuntimeError("telemetry bug")
        client.flush = broken_flush
        with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"node_id": "Q00", "skills": []})}):
            code, stdout, stderr = self.run_observe(["--state", "x", "node", "Q00"], client)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"node_id": "Q00", "skills": []})
        self.assertEqual(stderr, b"child stderr\n")

    def test_unexpected_configuration_error_does_not_block_the_command(self):
        with patch.object(observe, "client_from_env", side_effect=RuntimeError("config bug")):
            with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"node_id": "Q00", "skills": []})}):
                code, stdout, _ = self.run_main(["--runner", str(self.runner), "--state", "x", "node", "Q00"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"node_id": "Q00", "skills": []})

    def test_telemetry_is_off_by_default_without_touching_stdout(self):
        with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"node_id": "Q00", "skills": []})}, clear=True):
            code, stdout, _ = self.run_main(["--runner", str(self.runner), "--state", "x", "node", "Q00"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"node_id": "Q00", "skills": []})

    def test_exec_runs_the_installed_launcher_and_passes_argv_verbatim(self):
        # Launch a real executable. Tokens beyond the separator belong to it,
        # including wrapper options used as literal argument values.
        script = ("import json, sys; print(json.dumps(sys.argv[1:])); "
                  "sys.stderr.buffer.write(bytes([255])); sys.exit(7)")
        with patch.object(observe, "client_from_env", return_value=FakeClient()):
            code, out, err = self.run_main(
                ["--exec", sys.executable, "--", "-c", script, "--runner", "a path", "--verbose"]
            )
        self.assertEqual((code, err), (7, bytes([255])))
        self.assertEqual(json.loads(out), ["--runner", "a path", "--verbose"])

    @unittest.skipUnless(os.name == "posix", "POSIX wait status exposes signal termination")
    def test_child_signal_is_visible_to_the_parent_and_shell(self):
        self.runner.write_text("import os, sys\nos.kill(os.getpid(), int(sys.argv[1]))\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("DESIGN_ROUTER_TELEMETRY")}
        for sig in (signal.SIGTERM, signal.SIGKILL):
            with self.subTest(signal=sig):
                argv = [sys.executable, "-B", observe.__file__, "--runner", str(self.runner), "--", str(int(sig))]
                result = subprocess.run(argv, capture_output=True, env=env)
                self.assertEqual(result.returncode, -sig, result.stderr)
                shell = subprocess.run(["/bin/sh", "-c", '"$@"; exit $?', "sh", *argv], capture_output=True, env=env)
                self.assertEqual(shell.returncode, 128 + sig, shell.stderr)

    def test_large_child_outputs_are_forwarded_with_bounded_memory(self):
        size = 8 * 1024 * 1024
        prefix = b'{"node_id":"Q00","title":"'
        suffix = b'"}'
        self.runner.write_text(
            f"import sys\nsys.stdout.buffer.write({prefix!r} + b'x' * {size-len(prefix)-len(suffix)} + {suffix!r})\n"
            f"sys.stderr.buffer.write(bytes([255]) * {size})\n"
        )
        for command in ("status", "node"):
            with self.subTest(command=command), tempfile.TemporaryFile("w+") as stdout, tempfile.TemporaryFile("w+") as stderr:
                client = FakeClient()
                with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr), \
                        patch.object(observe, "client_from_env", return_value=client):
                    tracemalloc.start()
                    try:
                        code = observe.main(["--runner", str(self.runner), "--", command, "Q00"])
                        _, peak = tracemalloc.get_traced_memory()
                    finally:
                        tracemalloc.stop()
                self.assertEqual(code, 0)
                self.assertEqual(stdout.buffer.tell(), size)
                self.assertEqual(stderr.buffer.tell(), size)
                self.assertLess(peak, size // 2, "the observer retained the child's full output")
                self.assertEqual([e["name"] for e in client.events], ["router.invoked"])

    def test_subcommand_help_flags_are_not_counted(self):
        for flag in ("--help", "-h", "--hel"):
            client = FakeClient()
            with patch.dict(os.environ, {"FAKE_OUTPUT": "{}"}):
                code, _, _ = self.run_observe(["--state", "x", "node", flag], client)
            self.assertEqual(code, 0)
            self.assertEqual(client.events, [], f"node {flag} must emit zero events")

    def test_abbreviated_state_option_still_resolves_command(self):
        for args in (["--st", "x", "node", "Q00"], ["--sta=x", "node", "Q00"]):
            client = FakeClient()
            with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"node_id": "Q00", "skills": []})}):
                code, _, _ = self.run_observe(args, client)
            self.assertEqual(code, 0)
            self.assertEqual([e["name"] for e in client.events], ["router.invoked", "decision.node_visited"])
            self.assertEqual(client.events[0]["command"], "node")
            self.assertEqual(client.events[1]["node_id"], "Q00")

    def test_propose_abbreviated_file_option_resolves_payload_and_node(self):
        proposal = self.base / "proposal.json"
        proposal.write_text(json.dumps({"summary": "s", "selected": "F00"}))
        for args in (
            ["--st", "x", "propose", "--fi", str(proposal), "Q00"],
            ["--state", "x", "propose", f"--fi={proposal}", "Q00"],
        ):
            client = FakeClient()
            with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"proposal_hash": "abc"})}):
                code, _, _ = self.run_observe(args, client)
            self.assertEqual(code, 0)
            self.assertEqual([e["name"] for e in client.events], ["router.invoked", "decision.branch_selected"])
            self.assertEqual((client.events[1]["node_id"], client.events[1]["branch_id"]), ("Q00", "F00"))

    def test_repeated_file_options_use_last_wins_matching_argparse(self):
        first = self.base / "first.json"
        second = self.base / "second.json"
        first.write_text(json.dumps({"summary": "first", "selected": "F00"}))
        second.write_text(json.dumps({"summary": "second", "selected": "F01"}))
        for args in (
            ["--state", "x", "propose", f"--file={first}", f"--fi={second}", "Q00"],
            ["--state", "x", "propose", "--file", str(first), "--fi", str(second), "Q00"],
        ):
            client = FakeClient()
            with patch.dict(os.environ, {"FAKE_OUTPUT": json.dumps({"proposal_hash": "abc"})}):
                code, _, _ = self.run_observe(args, client)
            self.assertEqual(code, 0)
            self.assertEqual([e["name"] for e in client.events], ["router.invoked", "decision.branch_selected"])
            self.assertEqual((client.events[1]["node_id"], client.events[1]["branch_id"]), ("Q00", "F01"))

if __name__ == "__main__":
    unittest.main()
