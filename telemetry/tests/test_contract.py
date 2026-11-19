import unittest
import uuid
from datetime import datetime, timezone

from telemetry import contract


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


class ConfigTests(unittest.TestCase):
    def test_off_by_default_and_ignores_unrelated_variables(self):
        config = contract.config_from_env({"DESIGN_ROUTER_TELEMETRY_URL": "http://127.0.0.1:1"})
        self.assertFalse(config.enabled)
        self.assertIsNone(config.endpoint)

    def test_enabled_requires_explicit_flag_and_loopback_http_is_allowed(self):
        config = contract.config_from_env({
            "DESIGN_ROUTER_TELEMETRY": "1",
            "DESIGN_ROUTER_TELEMETRY_URL": "http://127.0.0.1:8787/",
        })
        self.assertTrue(config.enabled)
        self.assertEqual(config.endpoint, "http://127.0.0.1:8787")

    def test_https_remote_is_allowed_but_plain_http_remote_is_not(self):
        self.assertEqual(
            contract.endpoint_origin("https://telemetry.example.com"),
            "https://telemetry.example.com",
        )
        for value in (
            "http://telemetry.example.com",
            "https://user:pass@telemetry.example.com",
            "https://telemetry.example.com/v1",
            "https://telemetry.example.com?x=1",
            "https://telemetry.example.com#x",
            "https://telemetry.example.com:0",
            "ftp://telemetry.example.com",
        ):
            with self.subTest(value=value):
                with self.assertRaises(contract.ContractError):
                    contract.endpoint_origin(value)

    def test_timeout_is_bounded(self):
        for value in ("0", "-1", "9", "nan"):
            with self.subTest(value=value):
                with self.assertRaises(contract.ContractError):
                    contract.config_from_env({
                        "DESIGN_ROUTER_TELEMETRY": "1",
                        "DESIGN_ROUTER_TELEMETRY_URL": "http://127.0.0.1:8787",
                        "DESIGN_ROUTER_TELEMETRY_TIMEOUT": value,
                    })


class ContractTests(unittest.TestCase):
    def test_explicit_null_required_identifiers_are_rejected(self):
        evaluation = str(uuid.uuid4())
        cases = [
            ("router.invoked", {"evaluation_id": None, "command": "node"}, "INVALID_EVALUATION_ID"),
            ("decision.node_visited", {"evaluation_id": evaluation, "node_id": None}, "INVALID_NODE_ID"),
            ("skill.selected", {"evaluation_id": evaluation, "skill_id": None}, "INVALID_SKILL_ID"),
            ("skill.execution_started", {"execution_id": None, "skill_id": "a/b", "source": "host"}, "INVALID_EXECUTION_ID"),
        ]
        for name, fields, code in cases:
            with self.subTest(name=name, fields=fields):
                candidate = event(name, **fields)
                with self.assertRaises(contract.ContractError) as raised:
                    contract.validate_batch({"schema": contract.SCHEMA, "events": [candidate]})
                self.assertEqual(raised.exception.code, code)

    def test_explicit_null_optional_identifiers_are_still_rejected(self):
        # Optional-id fields carrying null must not pass as absent either:
        # SQLite unique indexes treat NULLs as distinct, which would defeat
        # the semantic dedup indexes.
        evaluation = str(uuid.uuid4())
        candidate = event("router.invoked", evaluation_id=evaluation, command="node", route=None)
        with self.assertRaises(contract.ContractError) as raised:
            contract.validate_batch({"schema": contract.SCHEMA, "events": [candidate]})
        self.assertEqual(raised.exception.code, "INVALID_ROUTE")

    def test_valid_events_for_each_observable_name(self):
        evaluation = str(uuid.uuid4())
        execution = str(uuid.uuid4())
        events = [
            event("router.invoked", evaluation_id=evaluation, command="node", route="auditoria"),
            event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
            event("decision.branch_selected", evaluation_id=evaluation, node_id="Q00", branch_id="F00"),
            event("skill.selected", evaluation_id=evaluation, skill_id="fegome90-cmd/my-skills/agy-agent"),
            event("skill.execution_started", execution_id=execution, skill_id="a/b", source="host"),
            event("skill.execution_completed", execution_id=execution, skill_id="a/b", source="host"),
        ]
        batch = contract.validate_batch({"schema": contract.SCHEMA, "events": events})
        self.assertEqual([item["name"] for item in batch], [item["name"] for item in events])

    def test_execution_events_require_host_source(self):
        execution = str(uuid.uuid4())
        for name in ("skill.execution_started", "skill.execution_completed", "skill.execution_failed"):
            with self.subTest(name=name):
                candidate = event(name, execution_id=execution, skill_id="a/b", source="cli")
                with self.assertRaises(contract.ContractError) as raised:
                    contract.validate_batch({"schema": contract.SCHEMA, "events": [candidate]})
                self.assertEqual(raised.exception.code, "EXECUTION_SOURCE_MUST_BE_HOST")

    def test_sensitive_or_unknown_fields_are_rejected_without_echoing_values(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        for key in ("prompt", "message", "email", "user_id", "path", "ip", "reason"):
            with self.subTest(key=key):
                bad = {**candidate, key: "SECRET-SENTINEL"}
                with self.assertRaises(contract.ContractError) as raised:
                    contract.validate_batch({"schema": contract.SCHEMA, "events": [bad]})
                self.assertEqual(raised.exception.code, "SENSITIVE_FIELD_REJECTED")
                self.assertNotIn("SECRET-SENTINEL", str(raised.exception))

    def test_unknown_event_and_invalid_identifier_are_rejected(self):
        with self.assertRaises(contract.ContractError) as raised:
            contract.validate_batch({"schema": contract.SCHEMA, "events": [event("prompt.captured")]})
        self.assertEqual(raised.exception.code, "UNKNOWN_EVENT")
        bad = event("decision.node_visited", evaluation_id=str(uuid.uuid4()), node_id="../escape")
        with self.assertRaises(contract.ContractError) as raised:
            contract.validate_batch({"schema": contract.SCHEMA, "events": [bad]})
        self.assertEqual(raised.exception.code, "INVALID_NODE_ID")

    def test_occurred_at_is_normalized_and_bounded(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="status",
                          occurred_at="2026-11-18T10:00:00+00:00")
        normalized = contract.validate_event(candidate, now=datetime(2026, 11, 18, 11, tzinfo=timezone.utc))
        self.assertTrue(normalized["occurred_at"].endswith("Z"))
        old = {**candidate, "occurred_at": "2020-01-01T00:00:00Z"}
        with self.assertRaises(contract.ContractError):
            contract.validate_event(old, now=datetime(2026, 11, 18, 11, tzinfo=timezone.utc))

    def test_duplicate_event_ids_inside_one_batch_are_rejected(self):
        candidate = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with self.assertRaises(contract.ContractError) as raised:
            contract.validate_batch({"schema": contract.SCHEMA, "events": [candidate, dict(candidate)]})
        self.assertEqual(raised.exception.code, "DUPLICATE_EVENT_IN_BATCH")


if __name__ == "__main__":
    unittest.main()
