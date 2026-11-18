import unittest

from telemetry.host_adapter import observe_execution


class FakeClient:
    enabled = True

    def __init__(self):
        self.events = []
        self.flushes = 0

    def emit(self, name, **fields):
        self.events.append({"name": name, **fields})

    def flush(self):
        self.flushes += 1
        return True


class ExecutionTests(unittest.TestCase):
    def test_success_emits_start_and_completion_with_one_execution_id(self):
        client = FakeClient()
        with observe_execution(client, "fegome90-cmd/my-skills/break-ui"):
            pass
        self.assertEqual([event["name"] for event in client.events],
                         ["skill.execution_started", "skill.execution_completed"])
        self.assertEqual(client.events[0]["execution_id"], client.events[1]["execution_id"])
        self.assertEqual(client.events[0]["source"], "host")
        self.assertEqual(client.flushes, 2)

    def test_failure_emits_start_and_failure_and_preserves_the_exception(self):
        client = FakeClient()
        with self.assertRaises(RuntimeError):
            with observe_execution(client, "fegome90-cmd/my-skills/break-ui"):
                raise RuntimeError("host failure")
        self.assertEqual([event["name"] for event in client.events],
                         ["skill.execution_started", "skill.execution_failed"])

    def test_disabled_client_does_not_emit(self):
        class Disabled:
            enabled = False
        client = Disabled()
        with observe_execution(client, "a/b"):
            pass

    def test_unexpected_telemetry_error_does_not_break_the_host_call(self):
        class Broken(FakeClient):
            def emit(self, name, **fields):
                raise RuntimeError("telemetry bug")
        client = Broken()
        with observe_execution(client, "a/b"):
            pass
        self.assertEqual(client.events, [])


if __name__ == "__main__":
    unittest.main()
