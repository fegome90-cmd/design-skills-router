import http.server
import json
import multiprocessing
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from telemetry import contract
from telemetry.client import POST_OK, POST_REJECT, POST_RETRY, Telemetry, client_from_env


def _ack(accepted, duplicates=0):
    return json.dumps({
        "schema": contract.SCHEMA, "accepted": accepted, "duplicates": duplicates,
    }).encode()


def _offline_producer(config, barrier, result):
    client = Telemetry(config)
    identifiers = []
    barrier.wait(timeout=20)
    with patch.object(client, "_post", return_value=POST_RETRY):
        for _ in range(16):
            event = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
            identifiers.append(event["event_id"])
            client.flush()
    result.put((identifiers, len(client._events)))


class ClientTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)

    def config(self):
        return contract.TelemetryConfig(
            enabled=True,
            endpoint="http://127.0.0.1:8787",
            timeout_seconds=0.2,
            state_dir=self.state,
        )

    def test_disabled_client_never_emits_or_writes(self):
        client = Telemetry(contract.DISABLED)
        self.assertIsNone(client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node"))
        self.assertTrue(client.flush())
        self.assertEqual(list(self.state.iterdir()), [])

    def test_successful_flush_delivers_one_batch_and_clears_queue(self):
        client = Telemetry(self.config())
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_OK) as post:
            self.assertTrue(client.flush())
            events = post.call_args.args[0]
        self.assertEqual([item["name"] for item in events], ["router.invoked"])
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])

    def test_failed_delivery_spools_and_retries_once(self):
        client = Telemetry(self.config())
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        spool = list(self.state.rglob("outbox-*.jsonl"))
        self.assertEqual(len(spool), 1)
        payload = json.loads(spool[0].read_text())
        self.assertEqual(len(payload["events"]), 1)
        with patch.object(client, "_post", return_value=POST_OK):
            self.assertTrue(client.flush())
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])

    def test_only_a_matching_collector_receipt_retires_a_persisted_batch(self):
        response = [503, b"offline"]
        attempts = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                attempts.append([event["event_id"] for event in payload["events"]])
                status, body = response
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        client = Telemetry(contract.TelemetryConfig(
            True, f"http://127.0.0.1:{server.server_port}", state_dir=self.state,
        ))
        ids = [client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")["event_id"]
               for _ in range(2)]
        self.assertFalse(client.flush())
        invalid = [
            (200, b"<html>Login</html>"), (200, _ack(2)), (202, b"<html>Login</html>"),
            (202, b"{}"), (202, _ack(1)), (202, _ack(True, 1)), (202, _ack(-1, 3)),
            (202, json.dumps({"schema": "other", "accepted": 2, "duplicates": 0}).encode()),
        ]
        for status, body in invalid:
            with self.subTest(status=status, body=body):
                response[:] = [status, body]
                self.assertFalse(client.flush())
                self.assertEqual(len(list(self.state.rglob("outbox-*.jsonl"))), 1)
        response[:] = [202, _ack(1, 1)]
        self.assertTrue(client.flush())
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])
        self.assertEqual(attempts, [ids] * (len(invalid) + 2))

    def test_truncated_422_response_preserves_batch_for_retry(self):
        attempts = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                attempts.append([event["event_id"] for event in payload["events"]])
                if len(attempts) == 1:
                    self.send_response(422)
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    self.wfile.write(b'40\r\n{"error":')
                    self.close_connection = True
                    return
                self.send_response(202)
                self.end_headers()
                self.wfile.write(_ack(1))

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        client = Telemetry(contract.TelemetryConfig(
            True, f"http://127.0.0.1:{server.server_port}", state_dir=self.state,
        ))
        event = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        self.assertFalse(client.flush())
        self.assertEqual(len(list(self.state.rglob("outbox-*.jsonl"))), 1)
        self.assertEqual(list(self.state.rglob("rejected-*.jsonl")), [])
        self.assertTrue(client.flush())
        self.assertEqual(attempts, [[event["event_id"]]] * 2)
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])

    def test_processes_compact_and_recover_exactly_the_emitted_events(self):
        ctx = multiprocessing.get_context("spawn")
        workers = 4
        barrier = ctx.Barrier(workers)
        result = ctx.Queue()
        self.addCleanup(result.close)
        processes = [ctx.Process(target=_offline_producer, args=(self.config(), barrier, result))
                     for _ in range(workers)]
        for process in processes:
            process.start()
            self.addCleanup(process.join, 5)
            self.addCleanup(process.terminate)
        expected = []
        for _ in processes:
            identifiers, pending = result.get(timeout=30)
            self.assertEqual(pending, 0)
            expected.extend(identifiers)
        for process in processes:
            process.join(10)
            self.assertEqual(process.exitcode, 0)
        recovered = []
        def delivered(events):
            recovered.extend(event["event_id"] for event in events)
            return POST_OK

        client = Telemetry(self.config())
        with patch.object(client, "_post", side_effect=delivered):
            self.assertTrue(client.flush())
        self.assertCountEqual(recovered, expected)
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])

    def test_producer_can_persist_while_another_client_awaits_ack(self):
        producer, consumer = Telemetry(self.config()), Telemetry(self.config())
        first = producer.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(producer, "_post", return_value=POST_RETRY):
            self.assertFalse(producer.flush())
        sending = threading.Event()
        unblock = threading.Event()
        def slow_post(events):
            sending.set()
            return POST_OK if unblock.wait(timeout=5) else POST_RETRY

        with patch.object(consumer, "_post", side_effect=slow_post):
            replay = threading.Thread(target=consumer.flush_spool)
            replay.start()
            try:
                self.assertTrue(sending.wait(timeout=5))
                second = producer.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
                with patch.object(producer, "_post", side_effect=AssertionError("another process owns replay")):
                    self.assertFalse(producer.flush())
                self.assertEqual(producer._events, [])
            finally:
                unblock.set()
                replay.join(timeout=5)
        client = Telemetry(self.config())
        with patch.object(client, "_post", return_value=POST_OK) as post:
            self.assertTrue(client.flush())
            post.assert_called_once_with([first, second])

    def test_compaction_survives_ack_from_a_legacy_reader_of_the_previous_file(self):
        client = Telemetry(self.config())
        first = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
            old_path, = client._outbox_dir().glob("outbox-*.jsonl")
            # A client from before the replay lock has read this generation.
            acknowledged = json.loads(old_path.read_text())["events"]
            second = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
            self.assertFalse(client.flush())
        # Its successful POST can delete only the pathname it originally read.
        old_path.unlink(missing_ok=True)
        recovered = Telemetry(self.config())
        with patch.object(recovered, "_post", return_value=POST_OK) as post:
            self.assertTrue(recovered.flush())
        sent = acknowledged + [event for call in post.call_args_list for event in call.args[0]]
        self.assertEqual({event["event_id"] for event in sent}, {first["event_id"], second["event_id"]})
        self.assertEqual(list(client._outbox_dir().glob("outbox-*.jsonl")), [])

    def test_non_regular_spool_entry_is_quarantined_without_blocking_valid_batch(self):
        client = Telemetry(self.config())
        event = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        directory = client._outbox_dir()
        bogus = directory / "outbox-0000.jsonl"
        bogus.mkdir()
        with patch.object(client, "_post", return_value=POST_OK) as post:
            self.assertFalse(client.flush_spool())
            post.assert_called_once_with([event])
        self.assertFalse(bogus.exists())
        self.assertTrue((directory / "rejected-0000.jsonl").is_dir())
        self.assertEqual(list(directory.glob("outbox-*.jsonl")), [])

    def test_retry_after_compaction_of_in_flight_file_reports_failure(self):
        reader, producer = Telemetry(self.config()), Telemetry(self.config())
        original = reader.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(reader, "_post", return_value=POST_RETRY):
            self.assertFalse(reader.flush())
        old_path, = reader._outbox_dir().glob("outbox-*.jsonl")
        appended = []

        def retry_after_compaction(events):
            next_event = producer.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
            appended.append(next_event)
            replacement = producer._spool_batch([next_event])
            self.assertIsNotNone(replacement)
            self.assertFalse(old_path.exists())
            return POST_RETRY, events, False

        with patch.object(reader, "_deliver_batch", side_effect=retry_after_compaction):
            self.assertFalse(reader.flush_spool())
        replacement, = reader._outbox_dir().glob("outbox-*.jsonl")
        self.assertEqual(json.loads(replacement.read_text())["events"], [original, appended[0]])

    @unittest.skipUnless(hasattr(os, "geteuid") and os.geteuid() != 0,
                         "requires POSIX file permissions and an unprivileged user")
    def test_unreadable_file_is_quarantined_while_readable_events_can_recover(self):
        client = Telemetry(self.config())
        events = [client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
                  for _ in range(contract.MAX_BATCH_EVENTS + 1)]
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        directory = client._outbox_dir()
        first, _ = sorted(directory.glob("outbox-*.jsonl"))
        first.chmod(0)
        newest = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
        with patch.object(client, "_post", return_value=POST_OK) as post:
            self.assertFalse(client.flush())
            self.assertTrue(client.flush())
        self.assertEqual([event for call in post.call_args_list for event in call.args[0]],
                         [events[-1], newest])
        rejected, = directory.glob("rejected-*.jsonl")
        rejected.chmod(0o600)
        self.assertEqual(json.loads(rejected.read_text())["events"], events[:-1])
        self.assertEqual(list(directory.glob("outbox-*.jsonl")), [])

    def test_transient_spool_read_failure_keeps_the_batch_pending(self):
        client = Telemetry(self.config())
        event = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        directory = client._outbox_dir()
        for failure in (OSError("I/O unavailable"), PermissionError("temporary sharing conflict")):
            with self.subTest(failure=failure), patch.object(Path, "read_bytes", side_effect=failure):
                self.assertFalse(client.flush())
                self.assertEqual(list(directory.glob("rejected-*.jsonl")), [])
        with patch.object(client, "_post", return_value=POST_OK) as post:
            self.assertTrue(client.flush())
            post.assert_called_once_with([event])

    def test_equivalent_collector_origins_share_pending_events(self):
        def configured(url):
            return Telemetry(contract.TelemetryConfig(True, url, state_dir=self.state))

        first = configured("https://Collector.Example:443/")
        event = first.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(first, "_post", return_value=POST_RETRY):
            self.assertFalse(first.flush())
        reopened = configured("https://collector.example")
        with patch.object(reopened, "_post", return_value=POST_OK) as post:
            self.assertTrue(reopened.flush())
            post.assert_called_once_with([event])

    def test_permanent_rejection_is_quarantined_without_blocking_later_batches(self):
        client = Telemetry(self.config())
        directory = client._outbox_dir()
        directory.mkdir(parents=True)
        first = directory / "outbox-0001-a.jsonl"
        second = directory / "outbox-0002-b.jsonl"
        payload = {"schema": contract.SCHEMA, "events": []}
        for path, command in ((first, "node"), (second, "status")):
            payload["events"] = [{
                "event_id": str(uuid.uuid4()), "name": "router.invoked",
                "occurred_at": contract.iso_now(), "source": "cli",
                "instance_id": str(uuid.uuid4()), "router_version": "1.3.0",
                "tree_version": "0.4", "evaluation_id": str(uuid.uuid4()),
                "command": command,
            }]
            path.write_text(json.dumps(payload))
        with patch.object(client, "_post", side_effect=[POST_REJECT, POST_OK]):
            self.assertFalse(client.flush_spool())
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        self.assertTrue(list(self.state.rglob("rejected-*.jsonl")))

    def test_current_batch_rejected_is_quarantined_not_retried(self):
        client = Telemetry(self.config())
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_REJECT):
            self.assertFalse(client.flush())
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])
        self.assertEqual(len(list(self.state.rglob("rejected-*.jsonl"))), 1)

    def test_instance_identifier_is_random_and_persistent(self):
        first = Telemetry(self.config())
        second = Telemetry(self.config())
        self.assertEqual(first.instance_id, second.instance_id)
        self.assertTrue(contract.ID_PATTERNS["instance_id"].fullmatch(first.instance_id))

    def test_sensitive_field_is_rejected_locally(self):
        client = Telemetry(self.config())
        with self.assertRaises(contract.ContractError):
            client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node",
                        prompt="SECRET-SENTINEL")

    def test_flush_chunks_a_buffer_larger_than_one_batch(self):
        # Regression: a buffer over MAX_BATCH_EVENTS used to post as a single
        # body, get BATCH_TOO_LARGE (permanent) and be quarantined, losing
        # every event.
        delivered = []
        client = Telemetry(self.config())
        for _ in range(contract.MAX_BATCH_EVENTS + 1):
            client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post",
                          side_effect=lambda batch: (delivered.append(len(batch)), POST_OK)[1]):
            self.assertTrue(client.flush())
        self.assertEqual(delivered, [contract.MAX_BATCH_EVENTS, 1])
        self.assertEqual(client._events, [])

    def test_failed_spool_write_keeps_the_batch_in_the_buffer(self):
        # Regression: a disk failure during spooling used to swallow the
        # OSError and drop the batch silently.
        client = Telemetry(self.config())
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_RETRY):
            with patch.object(client, "_write_spool", return_value=False):
                self.assertFalse(client.flush())
        self.assertEqual(len(client._events), 1,
                         "the batch must stay in the buffer when spooling fails")

    def test_merge_write_failure_preserves_the_existing_outbox_file(self):
        # Regression: a failed merged write used to unlink the already-spooled
        # file anyway, destroying both batches.
        client = Telemetry(self.config())
        first = [client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
                 for _ in range(3)]
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        files = sorted(self.state.rglob("outbox-*.jsonl"))
        self.assertEqual(len(files), 1)
        with patch.object(client, "_write_spool", return_value=False):
            more = [client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
                    for _ in range(2)]
            self.assertFalse(client.flush())
        after = sorted(self.state.rglob("outbox-*.jsonl"))
        self.assertEqual(after, files, "a failed merge must leave the spooled file untouched")
        self.assertEqual(len(json.loads(after[0].read_text())["events"]), 3)
        self.assertEqual(len(client._events), 2,
                         "the new batch must return to the buffer on merge failure")

    def test_env_client_is_off_without_explicit_flag(self):
        client = client_from_env({"DESIGN_ROUTER_TELEMETRY_URL": "http://127.0.0.1:8787"})
        self.assertFalse(client.enabled)

    def test_env_client_uses_configured_state_directory(self):
        client = client_from_env({
            "DESIGN_ROUTER_TELEMETRY": "1",
            "DESIGN_ROUTER_TELEMETRY_URL": "http://127.0.0.1:8787",
            "DESIGN_ROUTER_TELEMETRY_STATE": str(self.state),
        })
        self.assertTrue(client.enabled)
        self.assertTrue((self.state / "instance-id").is_file())

    def test_spool_compaction_merges_batches_under_the_post_cap(self):
        client = Telemetry(self.config())

        def emit(amount):
            for _ in range(amount):
                client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")

        with patch.object(client, "_post", return_value=POST_RETRY):
            emit(60)
            self.assertFalse(client.flush())
            emit(40)
            self.assertFalse(client.flush())
            emit(40)
            self.assertFalse(client.flush())
        files = sorted(self.state.rglob("outbox-*.jsonl"))
        self.assertEqual(len(files), 2)
        counts = [len(json.loads(path.read_text())["events"]) for path in files]
        self.assertEqual(counts, [100, 40])
        self.assertTrue(all(count <= contract.MAX_BATCH_EVENTS for count in counts),
                        "a merged file must never exceed one POST batch")

        delivered = []
        with patch.object(client, "_post",
                          side_effect=lambda events: (delivered.extend(events), POST_OK)[1]):
            self.assertTrue(client.flush_spool())
        self.assertEqual(len(delivered), 140)
        self.assertEqual(len({event["event_id"] for event in delivered}), 140,
                         "no event may be duplicated or lost by compaction")
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])

    def test_spool_evicts_the_oldest_file_beyond_the_cap(self):
        client = Telemetry(self.config())

        def failed_flush_of(amount):
            for _ in range(amount):
                client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
            with patch.object(client, "_post", return_value=POST_RETRY):
                self.assertFalse(client.flush())

        with patch("telemetry.client.MAX_SPOOL_FILES", 3):
            failed_flush_of(100)
            oldest = sorted(self.state.rglob("outbox-*.jsonl"))[0]
            failed_flush_of(100)
            failed_flush_of(100)
            self.assertEqual(len(list(self.state.rglob("outbox-*.jsonl"))), 3)
            failed_flush_of(100)
            files = sorted(self.state.rglob("outbox-*.jsonl"))
            self.assertEqual(len(files), 3)
            self.assertNotIn(oldest, files, "the oldest file is evicted at the cap")
            total = sum(len(json.loads(path.read_text())["events"]) for path in files)
            self.assertEqual(total, 300)

    def test_spool_write_failure_at_cap_preserves_existing_files(self):
        # Regression: evicting oldest spool files before writing the new batch
        # lost already-spooled events when the new write failed (disk/quota).
        client = Telemetry(self.config())

        def failed_flush_of(amount):
            for _ in range(amount):
                client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
            with patch.object(client, "_post", return_value=POST_RETRY):
                self.assertFalse(client.flush())

        with patch("telemetry.client.MAX_SPOOL_FILES", 2):
            failed_flush_of(100)
            failed_flush_of(100)
            before = sorted(self.state.rglob("outbox-*.jsonl"))
            self.assertEqual(len(before), 2)
            for _ in range(10):
                client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="status")
            with patch.object(client, "_post", return_value=POST_RETRY):
                with patch.object(client, "_write_spool", return_value=False):
                    self.assertFalse(client.flush())
            after = sorted(self.state.rglob("outbox-*.jsonl"))
            self.assertEqual(after, before,
                             "a failed write at spool cap must not unlink existing files")
            self.assertEqual(len(client._events), 10,
                             "the new batch must remain buffered when spool write fails")

    def test_spool_directory_error_preserves_batch_in_buffer(self):
        # Regression: if state_dir is an existing regular file, mkdir() used to
        # raise FileExistsError after flush() drained self._events.
        blocked = self.state / "not-a-directory"
        blocked.write_text("file", encoding="utf-8")
        config = contract.TelemetryConfig(
            enabled=True,
            endpoint="http://127.0.0.1:8787",
            timeout_seconds=0.2,
            state_dir=blocked,
        )
        client = Telemetry(config)
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        self.assertEqual(len(client._events), 1,
                         "a spool directory failure must restore the batch into memory")

    def test_quarantine_enforces_max_spool_files_cap(self):
        # Regression: _quarantine() renamed outbox files into rejected-* without
        # enforcing MAX_SPOOL_FILES, letting rejected files grow unboundedly.
        client = Telemetry(self.config())
        directory = client._outbox_dir()
        directory.mkdir(parents=True)
        with patch("telemetry.client.MAX_SPOOL_FILES", 2):
            for idx in range(4):
                path = directory / f"outbox-000{idx}-test.jsonl"
                payload = {"schema": contract.SCHEMA, "events": [{
                    "event_id": str(uuid.uuid4()), "name": "router.invoked",
                    "occurred_at": contract.iso_now(), "source": "cli",
                    "instance_id": str(uuid.uuid4()), "router_version": "1.3.0",
                    "tree_version": "0.4", "evaluation_id": str(uuid.uuid4()),
                    "command": "node",
                }]}
                path.write_text(json.dumps(payload), encoding="utf-8")
                with patch.object(client, "_post", return_value=POST_REJECT):
                    self.assertFalse(client.flush_spool())
            rejected = sorted(self.state.rglob("rejected-*.jsonl"))
            self.assertEqual(len(rejected), 2,
                             "quarantine must cap rejected-* files at MAX_SPOOL_FILES")
            self.assertTrue(any("0003" in p.name for p in rejected))

    def test_http_429_is_retryable_and_never_quarantined(self):
        mode = {"fail": True}

        class StubHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                events = json.loads(self.rfile.read(length))["events"]
                body = _ack(len(events))
                if mode["fail"]:
                    self.send_response(429)
                else:
                    self.send_response(202)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        stub = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
        thread = threading.Thread(target=stub.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(stub.shutdown)
        self.addCleanup(stub.server_close)
        client = Telemetry(contract.TelemetryConfig(
            enabled=True,
            endpoint=f"http://127.0.0.1:{stub.server_port}",
            timeout_seconds=2,
            state_dir=self.state,
        ))
        client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        self.assertFalse(client.flush())
        self.assertEqual(len(list(self.state.rglob("outbox-*.jsonl"))), 1,
                         "a rate-limited batch must be spooled for retry")
        self.assertEqual(list(self.state.rglob("rejected-*.jsonl")), [],
                         "429 must never quarantine the batch")

        mode["fail"] = False
        self.assertTrue(client.flush())
        self.assertEqual(list(self.state.rglob("outbox-*.jsonl")), [])


    def test_emit_defaults_router_version_to_1_4_0(self):
        client = Telemetry(self.config())
        ev = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        self.assertIsNotNone(ev)
        assert ev is not None
        self.assertEqual(ev["router_version"], "1.4.0")

    def test_unreadable_spool_directory_never_bypasses_older_events(self):
        if os.geteuid() == 0:
            self.skipTest("chmod 0300 does not restrict root")
        client = Telemetry(self.config())
        ev_id = str(uuid.uuid4())
        ex_id = str(uuid.uuid4())
        client.emit("skill.execution_started", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
        with patch.object(client, "_post", return_value=POST_RETRY):
            self.assertFalse(client.flush())
        directory = client._outbox_dir()
        os.chmod(directory, 0o300)
        self.addCleanup(lambda: os.chmod(directory, 0o700))
        posted: list[list[dict]] = []
        client.emit("skill.execution_completed", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
        client.emit("router.invoked", evaluation_id=ev_id, command="node")
        with patch.object(client, "_post", side_effect=lambda batch: (posted.append(batch), POST_OK)[1]):
            self.assertFalse(client.flush())
        self.assertEqual(posted, [], "unreadable spool dir must block direct posting of newer events")
        os.chmod(directory, 0o700)
        with patch.object(client, "_post", side_effect=lambda batch: (posted.append(batch), POST_OK)[1]):
            self.assertTrue(client.flush())
        names = [e["name"] for batch in posted for e in batch]
        self.assertEqual(names, ["skill.execution_started", "skill.execution_completed", "router.invoked"])

    def test_existing_write_only_outbox_under_read_only_parent_can_upgrade(self):
        if not hasattr(os, "geteuid") or os.geteuid() == 0:
            self.skipTest("requires POSIX directory permissions and an unprivileged user")
        client = Telemetry(self.config())
        directory = client._outbox_dir()
        directory.mkdir(parents=True)
        # An older client already established the high-water clock, but
        # neither of the new lock files exists yet.
        (directory / "spool-clock").write_text("1800000000000000000:1")
        os.chmod(directory.parent, 0o500)
        os.chmod(directory, 0o300)
        self.addCleanup(os.chmod, directory.parent, 0o700)
        self.addCleanup(os.chmod, directory, 0o700)
        event = client.emit("router.invoked", evaluation_id=str(uuid.uuid4()), command="node")
        with patch.object(client, "_post", side_effect=AssertionError("outbox cannot be listed")):
            self.assertFalse(client.flush())
            self.assertEqual(client._events, [])
        os.chmod(directory, 0o700)
        with patch.object(client, "_post", return_value=POST_OK) as post:
            self.assertTrue(client.flush())
            post.assert_called_once_with([event])

    def test_spool_filenames_stay_monotonic_across_clock_rollback_and_instances(self):
        c1 = Telemetry(self.config())
        c2 = Telemetry(self.config())
        ev_id = str(uuid.uuid4())
        with patch("telemetry.client.time.time_ns", side_effect=[1_700_000_000_500_000_000, 1_700_000_000_100_000_000, 1_700_000_000_100_000_000]):
            # Fill batch 1 so compaction does not merge batch 2 into batch 1.
            for _ in range(contract.MAX_BATCH_EVENTS):
                c1.emit("router.invoked", evaluation_id=ev_id, command="node")
            with patch.object(c1, "_post", return_value=POST_RETRY):
                c1.flush()
            c2.emit("router.invoked", evaluation_id=ev_id, command="status")
            with patch.object(c2, "_post", return_value=POST_RETRY):
                c2.flush()
        files = sorted(self.state.rglob("outbox-*.jsonl"))
        self.assertEqual(len(files), 2)
        first = json.loads(files[0].read_text())["events"][0]["command"]
        second = json.loads(files[1].read_text())["events"][0]["command"]
        self.assertEqual((first, second), ("node", "status"))

    def test_large_retryable_flush_preserves_chunk_1_and_indexed_422_isolates_only_bad_event(self):
        client = Telemetry(self.config())
        ev_id = str(uuid.uuid4())
        ex_id = str(uuid.uuid4())
        with patch("telemetry.client.MAX_SPOOL_FILES", 3):
            # 4 full chunks (exceeds cap 3): chunk 1 has start, chunk 2 has completion + 99 invocations.
            client.emit("skill.execution_started", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
            for _ in range(contract.MAX_BATCH_EVENTS - 1):
                client.emit("router.invoked", evaluation_id=ev_id, command="node")
            client.emit("skill.execution_completed", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
            for _ in range(contract.MAX_BATCH_EVENTS * 3 - 1):
                client.emit("router.invoked", evaluation_id=ev_id, command="node")
            with patch.object(client, "_post", return_value=POST_RETRY):
                self.assertFalse(client.flush())
            spooled = sorted(self.state.rglob("outbox-*.jsonl"))
            self.assertEqual(len(spooled), 3)
            self.assertEqual(json.loads(spooled[0].read_text())["events"][0]["name"], "skill.execution_started")
            self.assertEqual(len(client._events), contract.MAX_BATCH_EVENTS)
            delivered: list[dict] = []
            with patch.object(client, "_post", side_effect=lambda batch: (delivered.extend(batch), POST_OK)[1]):
                self.assertTrue(client.flush())
            self.assertEqual(len(delivered), contract.MAX_BATCH_EVENTS * 4)
            self.assertEqual(delivered[0]["name"], "skill.execution_started")
            self.assertEqual(delivered[contract.MAX_BATCH_EVENTS]["name"], "skill.execution_completed")
            self.assertEqual(list(self.state.rglob("rejected-*.jsonl")), [])

        # Indexed 422 from HTTP collector isolates only offending event and delivers valid neighbors.
        received: list[list[dict]] = []
        class IndexedRejectHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                events = body["events"]
                for i, ev in enumerate(events):
                    if ev["name"] == "skill.execution_completed":
                        payload = json.dumps({"error": "EXECUTION_NOT_STARTED", "index": i}).encode()
                        self.send_response(422)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                received.append(events)
                self.send_response(202)
                self.end_headers()
                self.wfile.write(_ack(len(events)))
            def log_message(self, format, *args):
                pass
        stub = http.server.ThreadingHTTPServer(("127.0.0.1", 0), IndexedRejectHandler)
        thread = threading.Thread(target=stub.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(stub.shutdown)
        self.addCleanup(stub.server_close)
        c_http = Telemetry(contract.TelemetryConfig(
            enabled=True, endpoint=f"http://127.0.0.1:{stub.server_port}",
            timeout_seconds=2, state_dir=self.state,
        ))
        c_http.emit("skill.execution_completed", source="host", execution_id=str(uuid.uuid4()), skill_id="emilkowalski/skills/ask-emil")
        c_http.emit("router.invoked", evaluation_id=ev_id, command="node")
        c_http.emit("router.invoked", evaluation_id=ev_id, command="status")
        self.assertFalse(c_http.flush())
        self.assertEqual([e["command"] for batch in received for e in batch], ["node", "status"])
        rejected_files = list(self.state.rglob("rejected-*.jsonl"))
        self.assertEqual(len(rejected_files), 1)
        self.assertEqual(len(json.loads(rejected_files[0].read_text())["events"]), 1)

    def test_concurrent_processes_converge_on_single_instance_id(self):
        import subprocess, sys
        fresh = self.state / "race"
        code = (
            "from pathlib import Path; import sys; "
            f"sys.path.insert(0, {str(Path(__file__).resolve().parents[2])!r}); "
            "from telemetry import contract, client; "
            f"cfg = contract.TelemetryConfig(enabled=True, endpoint='http://127.0.0.1:8787', state_dir=Path({str(fresh)!r})); "
            "print(client.load_instance_id(cfg))"
        )
        procs = [
            subprocess.Popen([sys.executable, "-B", "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for _ in range(8)
        ]
        ids = []
        for proc in procs:
            out, err = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 0, err)
            ids.append(out.strip())
        self.assertEqual(len(set(ids)), 1, f"concurrent processes diverged: {ids}")
        entries = sorted(p.name for p in fresh.iterdir())
        self.assertEqual(entries, ["instance-id"])

    def test_repeated_503_retries_never_evict_protected_chunks_without_new_events(self):
        client = Telemetry(self.config())
        ev_id = str(uuid.uuid4())
        ex_id = str(uuid.uuid4())
        with patch("telemetry.client.MAX_SPOOL_FILES", 3):
            # 4 full chunks (400 events, exceeding 3-file disk cap): chunk 1 starts execution.
            client.emit("skill.execution_started", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
            for _ in range(contract.MAX_BATCH_EVENTS - 1):
                client.emit("router.invoked", evaluation_id=ev_id, command="node")
            client.emit("skill.execution_completed", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
            for _ in range(contract.MAX_BATCH_EVENTS * 3 - 1):
                client.emit("router.invoked", evaluation_id=ev_id, command="node")

            with patch.object(client, "_post", return_value=POST_RETRY):
                self.assertFalse(client.flush())
                first_pass = sorted(self.state.rglob("outbox-*.jsonl"))
                self.assertEqual(len(first_pass), 3)
                # Second and third retries with zero new emissions must NOT evict chunk 1.
                self.assertFalse(client.flush())
                self.assertFalse(client.flush())
                after_retries = sorted(self.state.rglob("outbox-*.jsonl"))
                self.assertEqual(after_retries, first_pass)
                self.assertEqual(json.loads(after_retries[0].read_text())["events"][0]["name"], "skill.execution_started")
                self.assertEqual(len(client._events), contract.MAX_BATCH_EVENTS)

            delivered: list[dict] = []
            with patch.object(client, "_post", side_effect=lambda batch: (delivered.extend(batch), POST_OK)[1]):
                self.assertTrue(client.flush())
            self.assertEqual(len(delivered), contract.MAX_BATCH_EVENTS * 4)
            self.assertEqual(delivered[0]["name"], "skill.execution_started")
            self.assertEqual(delivered[contract.MAX_BATCH_EVENTS]["name"], "skill.execution_completed")

    def test_restart_and_clock_rollback_under_0300_spool_dir_preserves_order(self):
        if os.geteuid() == 0:
            self.skipTest("chmod 0300 does not restrict root")
        import telemetry.client as tc
        ex_id = str(uuid.uuid4())
        c1 = Telemetry(self.config())
        with patch("telemetry.client.time.time_ns", return_value=2_000_000_000_000_000_000):
            c1.emit("skill.execution_started", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
            with patch.object(c1, "_post", return_value=POST_RETRY):
                self.assertFalse(c1.flush())
        directory = c1._outbox_dir()
        os.chmod(directory, 0o300)
        self.addCleanup(lambda: os.chmod(directory, 0o700))

        # Simulate a fresh process restart (zeroed module clock state) with a rolled-back clock.
        saved_ns, saved_seq = tc._LAST_SPOOL_NS, tc._LAST_SPOOL_SEQ
        try:
            tc._LAST_SPOOL_NS = 0
            tc._LAST_SPOOL_SEQ = 0
            c2 = Telemetry(self.config())
            with patch("telemetry.client.time.time_ns", return_value=1_000_000_000_000_000_000):
                c2.emit("skill.execution_completed", source="host", execution_id=ex_id, skill_id="emilkowalski/skills/ask-emil")
                with patch.object(c2, "_post", return_value=POST_RETRY):
                    self.assertFalse(c2.flush())
        finally:
            tc._LAST_SPOOL_NS, tc._LAST_SPOOL_SEQ = saved_ns, saved_seq

        os.chmod(directory, 0o700)
        files = sorted(self.state.rglob("outbox-*.jsonl"))
        self.assertEqual(len(files), 2)
        names = [json.loads(p.read_text())["events"][0]["name"] for p in files]
        self.assertEqual(names, ["skill.execution_started", "skill.execution_completed"])

    def test_indexed_422_retains_rejected_diagnostic_when_spool_dir_is_readonly(self):
        if os.geteuid() == 0:
            self.skipTest("chmod 0500 does not restrict root")
        ev_id = str(uuid.uuid4())
        received: list[list[dict]] = []

        class RejectFirstHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                events = body["events"]
                for i, ev in enumerate(events):
                    if ev["name"] == "skill.execution_completed":
                        payload = json.dumps({"error": "EXECUTION_NOT_STARTED", "index": i}).encode()
                        self.send_response(422)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                received.append(events)
                self.send_response(202)
                self.end_headers()
                self.wfile.write(_ack(len(events)))
            def log_message(self, format, *args):
                pass

        stub = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RejectFirstHandler)
        thread = threading.Thread(target=stub.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(stub.shutdown)
        self.addCleanup(stub.server_close)

        client = Telemetry(contract.TelemetryConfig(
            enabled=True, endpoint=f"http://127.0.0.1:{stub.server_port}",
            timeout_seconds=2, state_dir=self.state,
        ))
        directory = client._outbox_dir()
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o500)
        self.addCleanup(lambda: os.chmod(directory, 0o700))

        client.emit("skill.execution_completed", source="host", execution_id=str(uuid.uuid4()), skill_id="emilkowalski/skills/ask-emil")
        client.emit("router.invoked", evaluation_id=ev_id, command="node")
        self.assertFalse(client.flush())
        self.assertEqual([e["command"] for batch in received for e in batch], ["node"])
        self.assertEqual(list(self.state.rglob("rejected-*.jsonl")), [])
        self.assertEqual(len(client._rejected), 1)

        # Once directory becomes writable again, next flush persists the retained diagnostic.
        os.chmod(directory, 0o700)
        self.assertTrue(client.flush())
        self.assertEqual(client._rejected, [])
        rejected_files = list(self.state.rglob("rejected-*.jsonl"))
        self.assertEqual(len(rejected_files), 1)
        saved = json.loads(rejected_files[0].read_text())["events"]
        self.assertEqual([e["name"] for e in saved], ["skill.execution_completed"])

if __name__ == "__main__":
    unittest.main()
