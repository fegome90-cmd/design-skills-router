import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from telemetry import contract
from telemetry.store import Store, StoreError


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


class StoreTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "telemetry.sqlite3"
        self.store = Store(self.path)

    def test_event_id_and_semantic_retries_do_not_inflate_counts(self):
        evaluation = str(uuid.uuid4())
        invoked = event("router.invoked", evaluation_id=evaluation, command="node")
        visited = event("decision.node_visited", evaluation_id=evaluation, node_id="Q00")
        selected = event("skill.selected", evaluation_id=evaluation, skill_id="a/b")
        first = self.store.append([invoked, visited, selected])
        self.assertEqual([item["status"] for item in first], ["accepted"] * 3)
        self.assertEqual(self.store.append([invoked])[0]["status"], "duplicate")
        retry_visit = {**visited, "event_id": str(uuid.uuid4())}
        retry_skill = {**selected, "event_id": str(uuid.uuid4())}
        self.assertEqual(self.store.append([retry_visit])[0]["status"], "duplicate")
        self.assertEqual(self.store.append([retry_skill])[0]["status"], "duplicate")
        metrics = self.store.metrics()
        self.assertEqual(metrics["totals"]["evaluations"], 1)
        self.assertEqual(metrics["totals"]["nodes_visited"], 1)
        self.assertEqual(metrics["totals"]["skills_selected"], 1)

    def test_two_invocations_with_the_same_evaluation_id_are_rejected_as_duplicate(self):
        evaluation = str(uuid.uuid4())
        first = event("router.invoked", evaluation_id=evaluation, command="status")
        second = {**first, "event_id": str(uuid.uuid4())}
        self.store.append([first])
        self.assertEqual(self.store.append([second])[0]["status"], "duplicate")
        self.assertEqual(self.store.metrics()["totals"]["evaluations"], 1)

    def test_execution_pairing_is_enforced_and_terminal_events_are_unique(self):
        execution = str(uuid.uuid4())
        instance = str(uuid.uuid4())
        skill = "fegome90-cmd/my-skills/design-process-orchestrator"
        completion = event("skill.execution_completed", execution_id=execution, skill_id=skill,
                           source="host", instance_id=instance)
        with self.assertRaises(StoreError) as raised:
            self.store.append([completion])
        self.assertEqual(raised.exception.code, "EXECUTION_NOT_STARTED")

        start = event("skill.execution_started", execution_id=execution, skill_id=skill,
                      source="host", instance_id=instance)
        self.assertEqual(self.store.append([start])[0]["status"], "accepted")
        self.assertEqual(self.store.append([completion])[0]["status"], "accepted")
        failed = event("skill.execution_failed", execution_id=execution, skill_id=skill,
                       source="host", instance_id=instance)
        self.assertEqual(self.store.append([failed])[0]["status"], "duplicate")
        metrics = self.store.metrics()
        self.assertEqual(metrics["totals"]["executions_started"], 1)
        self.assertEqual(metrics["totals"]["executions_completed"], 1)
        self.assertEqual(metrics["totals"]["executions_failed"], 0)

    def test_store_rejects_non_host_execution_even_if_called_directly(self):
        execution = str(uuid.uuid4())
        with self.assertRaises(StoreError) as raised:
            self.store.append([event("skill.execution_started", execution_id=execution,
                                     skill_id="a/b", source="cli")])
        self.assertEqual(raised.exception.code, "EXECUTION_SOURCE_MUST_BE_HOST")

    def test_skill_mismatch_is_rejected(self):
        execution = str(uuid.uuid4())
        instance = str(uuid.uuid4())
        start = event("skill.execution_started", execution_id=execution, skill_id="a/one",
                      source="host", instance_id=instance)
        completion = event("skill.execution_completed", execution_id=execution, skill_id="a/two",
                           source="host", instance_id=instance)
        self.store.append([start])
        with self.assertRaises(StoreError) as raised:
            self.store.append([completion])
        self.assertEqual(raised.exception.code, "EXECUTION_SKILL_MISMATCH")

    def test_evaluation_scoped_events_require_a_prior_invocation(self):
        for name, fields in (
            ("decision.node_visited", {"node_id": "Q00"}),
            ("decision.branch_selected", {"node_id": "Q00", "branch_id": "F00"}),
            ("skill.selected", {"skill_id": "a/b"}),
        ):
            with self.subTest(name=name):
                evaluation = str(uuid.uuid4())
                with self.assertRaises(StoreError) as raised:
                    self.store.append([event(name, evaluation_id=evaluation, **fields)])
                self.assertEqual(raised.exception.code, "INVOCATION_NOT_RECORDED")

    def test_invocation_must_precede_evaluation_events_in_the_batch(self):
        evaluation = str(uuid.uuid4())
        with self.assertRaises(StoreError) as raised:
            self.store.append([
                event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
                event("router.invoked", evaluation_id=evaluation, command="node"),
            ])
        self.assertEqual(raised.exception.code, "INVOCATION_NOT_RECORDED")

    def test_collector_restart_between_started_and_completed_keeps_pairing(self):
        execution = str(uuid.uuid4())
        instance = str(uuid.uuid4())
        start = event("skill.execution_started", execution_id=execution,
                      skill_id="a/b", source="host", instance_id=instance)
        self.store.append([start])
        reopened = Store(self.path)
        completion = event("skill.execution_completed", execution_id=execution,
                           skill_id="a/b", source="host", instance_id=instance)
        self.assertEqual(reopened.append([completion])[0]["status"], "accepted")
        self.assertEqual(reopened.metrics()["totals"]["executions_completed"], 1)

    def test_executed_skill_appears_in_its_own_ranking_beyond_the_selection_limit(self):
        for index in range(21):
            evaluation = str(uuid.uuid4())
            self.store.append([
                event("router.invoked", evaluation_id=evaluation, command="node"),
                event("skill.selected", evaluation_id=evaluation, skill_id=f"skill/selected-{index:02d}"),
            ])
        instance = str(uuid.uuid4())
        execution = str(uuid.uuid4())
        self.store.append([
            event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node", instance_id=instance),
            event("skill.execution_started", execution_id=execution, skill_id="skill/only-executed",
                  source="host", instance_id=instance),
            event("skill.execution_completed", execution_id=execution, skill_id="skill/only-executed",
                  source="host", instance_id=instance),
        ])
        metrics = self.store.metrics(limit=20)
        self.assertEqual(metrics["totals"]["executions_started"], 1)
        self.assertEqual(metrics["totals"]["executions_completed"], 1)
        # The selection ranking is limited and may not contain the executed skill.
        self.assertEqual(len(metrics["skills"]), 20)
        self.assertNotIn("skill/only-executed", [item["skill_id"] for item in metrics["skills"]])
        # The execution ranking must not depend on the selection ranking.
        executed = metrics["skills_executed"]
        self.assertEqual([item["skill_id"] for item in executed], ["skill/only-executed"])
        self.assertEqual(executed[0]["executions_started"], 1)
        self.assertEqual(executed[0]["executions_completed"], 1)
        self.assertEqual(executed[0]["executions_failed"], 0)
        self.assertEqual(executed[0].get("selected", 0), 0)

    def test_execution_ranking_orders_by_execution_activity_then_id(self):
        instance = str(uuid.uuid4())
        a_completed = str(uuid.uuid4())
        a_failed = str(uuid.uuid4())
        b_started = str(uuid.uuid4())
        self.store.append([
            event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node", instance_id=instance),
            event("skill.execution_started", execution_id=a_completed, skill_id="skill/a",
                  source="host", instance_id=instance),
            event("skill.execution_completed", execution_id=a_completed, skill_id="skill/a",
                  source="host", instance_id=instance),
            event("skill.execution_started", execution_id=a_failed, skill_id="skill/a",
                  source="host", instance_id=instance),
            event("skill.execution_failed", execution_id=a_failed, skill_id="skill/a",
                  source="host", instance_id=instance),
            event("skill.execution_started", execution_id=b_started, skill_id="skill/b",
                  source="host", instance_id=instance),
        ])
        ranking = self.store.metrics()["skills_executed"]
        self.assertEqual([item["skill_id"] for item in ranking], ["skill/a", "skill/b"])
        self.assertEqual(ranking[0]["executions_started"], 2)
        self.assertEqual(ranking[0]["executions_completed"], 1)
        self.assertEqual(ranking[0]["executions_failed"], 1)
        self.assertEqual(ranking[1]["executions_started"], 1)

    def test_metrics_read_one_consistent_snapshot_under_concurrent_writes(self):
        stop = threading.Event()
        inserted = [0]

        def writer():
            while not stop.is_set():
                evaluation = str(uuid.uuid4())
                try:
                    self.store.append([
                        event("router.invoked", evaluation_id=evaluation, command="node"),
                        event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
                        event("skill.selected", evaluation_id=evaluation, skill_id="skill/a"),
                    ])
                    inserted[0] += 1
                except StoreError:
                    pass

        threads = [threading.Thread(target=writer, daemon=True) for _ in range(4)]
        for thread in threads:
            thread.start()
        try:
            violations = []
            for _ in range(300):
                metrics = self.store.metrics()
                # Every figure in one response must describe the same snapshot.
                by_name = sum(metrics["event_counts"].values())
                by_source = sum(source["events"] for source in metrics["sources"])
                by_skill = sum(item["selected"] for item in metrics["skills"])
                if not (metrics["totals"]["events"] == by_name == by_source):
                    violations.append(("totals-vs-groups", metrics["totals"]["events"], by_name, by_source))
                if metrics["totals"]["skills_selected"] != by_skill:
                    violations.append(("skills", metrics["totals"]["skills_selected"], by_skill))
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=10)
        self.assertGreater(inserted[0], 0)
        self.assertEqual(violations[:3], [], "metrics mixed snapshots from concurrent writes")

    def test_empty_window_after_real_executions_reports_zero_not_missing_emitter(self):
        instance = str(uuid.uuid4())
        execution = str(uuid.uuid4())
        old = "2026-11-01T00:00:00Z"
        batch = [
            event("skill.execution_started", execution_id=execution, skill_id="skill/x",
                  source="host", instance_id=instance),
            event("skill.execution_completed", execution_id=execution, skill_id="skill/x",
                  source="host", instance_id=instance),
        ]
        for item in batch:
            item["occurred_at"] = old
        self.store.append(batch)

        whole = self.store.metrics()
        window = self.store.metrics(since="2026-11-17T00:00:00Z")

        # All-time evidence: executions really happened and were observed.
        self.assertEqual(whole["observability"]["skill.execution_started"], "observed")
        self.assertEqual(whole["totals"]["executions_started"], 1)
        # The empty window must not claim there is no emitter: an emitter was
        # accredited by real events, just not inside this window.
        self.assertEqual(window["observability"]["skill.execution_started"], "observed_zero_events")
        self.assertEqual(window["observability"]["skill.execution_completed"], "observed_zero_events")
        self.assertEqual(window["totals"]["executions_started"], 0)
        # A store with no execution event ever keeps the conservative state.
        fresh = Store(self.path.with_name("fresh.sqlite3"))
        self.assertEqual(
            fresh.metrics()["observability"]["skill.execution_started"],
            "schema_supported_no_emitter",
        )

    def test_data_quality_flags_one_instance_concentrating_events(self):
        with patch("telemetry.store.INFLATION_SIGNAL_EVENTS", 5):
            instance = str(uuid.uuid4())
            for _ in range(3):
                evaluation = str(uuid.uuid4())
                self.store.append([
                    event("router.invoked", evaluation_id=evaluation, command="node",
                          instance_id=instance),
                    event("decision.node_visited", evaluation_id=evaluation, node_id="Q00",
                          instance_id=instance),
                ])
            quality = self.store.metrics()["data_quality"]
            self.assertEqual(quality["instances"], 1)
            self.assertEqual(quality["max_events_per_instance"], 6)
            self.assertTrue(quality["possibly_inflated"])

    def test_data_quality_stays_calm_when_events_spread_across_instances(self):
        with patch("telemetry.store.INFLATION_SIGNAL_EVENTS", 5):
            # The event() helper gives each event a fresh instance_id.
            for _ in range(3):
                evaluation = str(uuid.uuid4())
                self.store.append([
                    event("router.invoked", evaluation_id=evaluation, command="node"),
                    event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
                ])
            quality = self.store.metrics()["data_quality"]
            self.assertEqual(quality["instances"], 6)
            self.assertEqual(quality["max_events_per_instance"], 1)
            self.assertFalse(quality["possibly_inflated"])

    def test_metrics_are_exact_and_aggregate_instances(self):
        for index in range(3):
            evaluation = str(uuid.uuid4())
            self.store.append([
                event("router.invoked", evaluation_id=evaluation, command="node",
                      instance_id=str(uuid.uuid4())),
                event("decision.node_visited", evaluation_id=evaluation, node_id="Q00"),
                event("skill.selected", evaluation_id=evaluation, skill_id="skill/a"),
                event("skill.selected", evaluation_id=evaluation, skill_id="skill/b"),
            ])
        metrics = self.store.metrics()
        self.assertEqual(metrics["totals"]["invocations"], 3)
        self.assertEqual(metrics["totals"]["evaluations"], 3)
        self.assertEqual(metrics["totals"]["nodes_visited"], 3)
        self.assertEqual(metrics["totals"]["skills_selected"], 6)
        by_skill = {item["skill_id"]: item["selected"] for item in metrics["skills"]}
        self.assertEqual(by_skill, {"skill/a": 3, "skill/b": 3})
        self.assertEqual(metrics["nodes"][0], {"node_id": "Q00", "visits": 3})

    def test_persistence_survives_reopening(self):
        evaluation = str(uuid.uuid4())
        self.store.append([event("router.invoked", evaluation_id=evaluation, command="status")])
        reopened = Store(self.path)
        self.assertEqual(reopened.metrics()["totals"]["evaluations"], 1)

    def test_window_filters_by_occurred_at(self):
        old = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node",
                    occurred_at="2026-11-01T00:00:00Z")
        new = event("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        self.store.append([old, new])
        self.assertEqual(self.store.metrics(since="2026-11-10T00:00:00Z")["totals"]["evaluations"], 1)
        self.assertEqual(self.store.metrics(until="2026-11-10T00:00:00Z")["totals"]["evaluations"], 1)

    def test_unobservable_events_are_labelled_without_fake_counts(self):
        metrics = self.store.metrics()
        self.assertEqual(metrics["observability"]["skill.execution_started"], "schema_supported_no_emitter")
        self.assertEqual(metrics["totals"]["executions_started"], 0)
        self.assertFalse(metrics["data_quality"]["sampling"])


    def test_skill_ranking_limit_does_not_alter_counts_for_a_skill(self):
        instance = str(uuid.uuid4())
        # Skill A is selected more often (3x) and executed once;
        # Skill B is selected less often (1x) and executed twice.
        for _ in range(3):
            ev = str(uuid.uuid4())
            self.store.append([
                event("router.invoked", evaluation_id=ev, command="node", instance_id=instance),
                event("skill.selected", evaluation_id=ev, skill_id="skill/a", instance_id=instance),
            ])
        ev_b = str(uuid.uuid4())
        self.store.append([
            event("router.invoked", evaluation_id=ev_b, command="node", instance_id=instance),
            event("skill.selected", evaluation_id=ev_b, skill_id="skill/b", instance_id=instance),
        ])
        exec_a = str(uuid.uuid4())
        self.store.append([
            event("skill.execution_started", execution_id=exec_a, skill_id="skill/a", source="host", instance_id=instance),
            event("skill.execution_completed", execution_id=exec_a, skill_id="skill/a", source="host", instance_id=instance),
        ])
        for _ in range(2):
            exec_b = str(uuid.uuid4())
            self.store.append([
                event("skill.execution_started", execution_id=exec_b, skill_id="skill/b", source="host", instance_id=instance),
                event("skill.execution_completed", execution_id=exec_b, skill_id="skill/b", source="host", instance_id=instance),
            ])

        top1 = self.store.metrics(limit=1)["skills"]
        top2 = self.store.metrics(limit=2)["skills"]
        self.assertEqual(len(top1), 1)
        self.assertEqual(top1[0]["skill_id"], "skill/a")
        self.assertEqual(top1[0], top2[0],
                         "counts for the same skill must not change with ranking limit")
        self.assertEqual(top1[0]["selected"], 3)
        self.assertEqual(top1[0]["executions_started"], 1)
        self.assertEqual(top1[0]["executions_completed"], 1)


if __name__ == "__main__":
    unittest.main()
