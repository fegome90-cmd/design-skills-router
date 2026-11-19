"""Opt-in telemetry client with a bounded local outbox.

The client is used outside the design-tree plugin runtime. The plugin keeps its
tested no-network contract; this module observes the CLI at its process
boundary and the board at its UI boundary.

No prompts, project content, file paths, IPs, emails or user identifiers are
accepted by the event contract. A random installation UUID exists only to keep
idempotency and multi-instance tests honest; it is not a user identity.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

from . import contract

MAX_SPOOL_FILES = 100
POST_OK = "ok"
POST_RETRY = "retry"
POST_REJECT = "reject"
PERMANENT_HTTP = frozenset({400, 413, 415, 422})

_SPOOL_NAME_LOCK = threading.Lock()
_LAST_SPOOL_NS = 0
_LAST_SPOOL_SEQ = 0
_SPOOL_NAME_RE = re.compile(r"^[a-z]+-(\d{13})-(\d{6})-(\d{6})-")
_SPOOL_CLOCK_NAME = "spool-clock"
_SPOOL_CLOCK_RE = re.compile(r"^(\d+):(\d+)$")


def _read_response_json(response: http.client.HTTPResponse | urllib.error.HTTPError) -> object:
    raw = response.read(contract.MAX_BODY_BYTES + 1)
    length = response.headers.get("Content-Length")
    if len(raw) > contract.MAX_BODY_BYTES or (length is not None and int(length) != len(raw)):
        raise ValueError("invalid collector response length")
    return json.loads(raw)


def _read_spool_clock(clock_path: Path) -> tuple[int, int] | None:
    try:
        raw = clock_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    match = _SPOOL_CLOCK_RE.match(raw)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _write_spool_clock(clock_path: Path, ns: int, seq: int) -> bool:
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=clock_path.parent, delete=False
        ) as handle:
            temp = Path(handle.name)
            handle.write(f"{ns}:{seq}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, clock_path)
        temp = None
        return True
    except OSError:
        if temp is not None:
            try:
                temp.unlink()
            except OSError:
                pass
        return False


def _allocate_spool_name(
    prefix: str,
    existing: list[Path] | None = None,
    clock_path: Path | None = None,
) -> tuple[str, bool]:
    """Return a lexicographically monotonic spool filename and whether the
    persisted high-water clock file was updated.

    Combines wall clock, a process-wide lock-protected sequence, the persisted
    spool-clock high-water file (readable even in 0300 directories across
    restarts), and the highest existing timestamp/sequence in the spool
    directory so clock rollbacks or multiple client instances can never reverse
    causal order.
    """
    global _LAST_SPOOL_NS, _LAST_SPOOL_SEQ
    now_ns = time.time_ns()
    floor_ns = 0
    floor_seq = 0
    if existing:
        for path in existing:
            match = _SPOOL_NAME_RE.match(path.name)
            if match:
                ns = int(match.group(1)) * 1_000_000 + int(match.group(2))
                seq = int(match.group(3))
                if ns > floor_ns or (ns == floor_ns and seq > floor_seq):
                    floor_ns, floor_seq = ns, seq
    with _SPOOL_NAME_LOCK:
        if clock_path is not None:
            persisted = _read_spool_clock(clock_path)
            if persisted is not None:
                c_ns, c_seq = persisted
                if c_ns > floor_ns or (c_ns == floor_ns and c_seq > floor_seq):
                    floor_ns, floor_seq = c_ns, c_seq
        target_ns = max(now_ns, _LAST_SPOOL_NS, floor_ns)
        if target_ns == _LAST_SPOOL_NS and target_ns == floor_ns:
            seq = max(_LAST_SPOOL_SEQ, floor_seq) + 1
        elif target_ns == _LAST_SPOOL_NS:
            seq = _LAST_SPOOL_SEQ + 1
        elif target_ns == floor_ns:
            seq = floor_seq + 1
        else:
            seq = 1
        if seq > 999_999:
            target_ns += 1
            seq = 1
        _LAST_SPOOL_NS = target_ns
        _LAST_SPOOL_SEQ = seq
        clock_persisted = True
        if clock_path is not None:
            clock_persisted = _write_spool_clock(clock_path, target_ns, seq)
    name = (
        f"{prefix}-{target_ns // 1_000_000:013d}-{target_ns % 1_000_000:06d}"
        f"-{seq:06d}-{os.getpid()}-{uuid.uuid4().hex[:8]}.jsonl"
    )
    return name, clock_persisted


@dataclass
class Telemetry:
    config: contract.TelemetryConfig
    instance_id: str | None = None
    _events: list[dict] = field(default_factory=list)
    _rejected: list[dict] = field(default_factory=list, init=False, repr=False)
    _protected_spool: set[Path] = field(default_factory=set, init=False, repr=False)
    _last_reject_index: int | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.config.enabled and not self.instance_id:
            self.instance_id = load_instance_id(self.config)

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled and self.config.endpoint)

    def new_evaluation_id(self) -> str:
        return str(uuid.uuid4())

    def emit(self, name: str, **fields) -> dict | None:
        if not self.enabled:
            return None
        event = {
            "event_id": str(uuid.uuid4()),
            "name": name,
            "occurred_at": contract.iso_now(),
            "source": fields.pop("source", "cli"),
            "instance_id": self.instance_id,
            "router_version": fields.pop("router_version", contract.ROUTER_VERSION),
            "tree_version": fields.pop("tree_version", contract.TREE_VERSION),
            **fields,
        }
        contract.validate_event(event)
        self._protected_spool.clear()
        self._events.append(event)
        return event

    def _list_spool_files(self, directory: Path, prefix: str) -> list[Path] | None:
        """List spool files using os.listdir so PermissionError is never masked
        as an empty directory (Path.glob suppresses OSError on Python 3.13+).
        Returns None when the directory exists but cannot be read.
        """
        try:
            names = sorted(os.listdir(directory))
        except FileNotFoundError:
            return []
        except OSError:
            return None
        start = f"{prefix}-"
        return [
            directory / name
            for name in names
            if name.startswith(start) and name.endswith(".jsonl")
        ]

    def _has_pending_outbox(self) -> bool:
        files = self._list_spool_files(self._outbox_dir(), "outbox")
        if files is None:
            # Directory exists but cannot be listed (e.g. mode 0300): never assume
            # it is empty or post newer events ahead of potentially spooled ones.
            return True
        return bool(files)

    @contextmanager
    def _spool_lock(self, *, replay: bool = False) -> Iterator[bool]:
        """Serialize mutations of one collector's files, including replay.

        BEGIN IMMEDIATE uses SQLite's OS-level writer lock across processes
        and releases it on close or process exit. Only one process replays
        over HTTP. Producers can still acquire the separate mutation lock and
        persist events while replay waits for the collector. Fixed lock names
        inside the outbox work even when directory listing is forbidden.
        """
        directory = self._outbox_dir()
        connection = None
        try:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / ("replay.lock" if replay else "spool.lock")
                connection = sqlite3.connect(path, timeout=0 if replay else 10)
                connection.execute("BEGIN IMMEDIATE")
            except (OSError, sqlite3.Error):
                yield False
                return
            yield True
        finally:
            if connection is not None:
                connection.close()

    def _flush_rejected(self) -> None:
        while self._rejected:
            batch = self._rejected[:contract.MAX_BATCH_EVENTS]
            if not self._spool(batch, prefix="rejected"):
                return
            del self._rejected[: len(batch)]

    def _spool_remaining(self, protected: set[Path] | None = None) -> bool:
        guarded = protected if protected is not None else self._protected_spool
        while self._events:
            batch = self._events[:contract.MAX_BATCH_EVENTS]
            del self._events[:contract.MAX_BATCH_EVENTS]
            written = self._spool_batch(batch, prefix="outbox", protected=guarded)
            if written is None:
                self._events = batch + self._events
                return False
            guarded.add(written)
        return True

    def _deliver_batch(self, events: list[dict]) -> tuple[str, list[dict], bool]:
        """Deliver one batch while isolating individually rejected (400/422)
        events by collector-reported index so valid neighbors are never lost.

        Returns (status, remaining_events, had_reject):
        - status is POST_OK (all non-rejected events delivered), POST_RETRY
          (transient failure with remaining_events unsent), or POST_REJECT
          (batch-level permanent rejection with no offending index).
        """
        remaining = list(events)
        had_reject = False
        while remaining:
            self._last_reject_index = None
            result = self._post(remaining)
            if result == POST_OK:
                return POST_OK, [], had_reject
            if result == POST_RETRY:
                return POST_RETRY, remaining, had_reject
            idx = self._last_reject_index
            if idx is not None and 0 <= idx < len(remaining):
                poisoned = remaining.pop(idx)
                if not self._spool([poisoned], prefix="rejected"):
                    self._rejected.append(poisoned)
                    del self._rejected[:-contract.MAX_BATCH_EVENTS]
                had_reject = True
                continue
            return POST_REJECT, remaining, True
        return POST_OK, [], had_reject

    def flush(self) -> bool:
        if not self.enabled:
            return True
        self._flush_rejected()
        ok = self.flush_spool()
        if self._has_pending_outbox():
            # Older events remain queued (e.g., collector returned 429/503 or
            # spool dir is unreadable). Never post newer events ahead of them:
            # sending execution_completed before a spooled execution_started
            # gets rejected (422). Protect chunks already spooled by this
            # client so repeated retries without new emissions never evict them.
            self._spool_remaining(protected=self._protected_spool)
            return False
        while self._events:
            # POST in collector-sized chunks: a body larger than
            # MAX_BATCH_EVENTS is rejected permanently (BATCH_TOO_LARGE) and
            # would quarantine the whole buffer.
            batch = self._events[:contract.MAX_BATCH_EVENTS]
            del self._events[:contract.MAX_BATCH_EVENTS]
            status, remaining, had_reject = self._deliver_batch(batch)
            if had_reject:
                ok = False
            if status == POST_OK:
                continue
            if status == POST_REJECT:
                # Batch-level rejection: quarantine this batch without blocking
                # later batches. The rest of the buffer stays for the next flush.
                if not self._spool(remaining, prefix="rejected"):
                    self._events = remaining + self._events
                return False
            # POST_RETRY: spool the unsent batch and remainder behind it without
            # evicting chunks spooled during this same retryable flush.
            written = self._spool_batch(remaining, prefix="outbox", protected=self._protected_spool)
            if written is None:
                self._events = remaining + self._events
                return False
            self._protected_spool.add(written)
            self._spool_remaining(protected=self._protected_spool)
            return False
        return ok

    def _post(self, events: list[dict]) -> str:
        assert self.config.endpoint is not None  # guarded by enabled
        self._last_reject_index = None
        body = json.dumps(
            {"schema": contract.SCHEMA, "events": events},
            ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            self.config.endpoint + "/v1/events",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        if self.config.token:
            request.add_header("Authorization", f"Bearer {self.config.token}")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                if response.status != 202:
                    return POST_RETRY
                ack = _read_response_json(response)
                if not isinstance(ack, dict) or ack.get("schema") != contract.SCHEMA:
                    return POST_RETRY
                accepted, duplicates = ack.get("accepted"), ack.get("duplicates")
                if (type(accepted) is int and type(duplicates) is int
                        and accepted >= 0 and duplicates >= 0
                        and accepted + duplicates == len(events)):
                    return POST_OK
                return POST_RETRY
        except urllib.error.HTTPError as error:
            with error:
                if error.code in (400, 422):
                    try:
                        parsed = _read_response_json(error)
                    except (http.client.HTTPException, OSError, ValueError, RecursionError):
                        return POST_RETRY
                    idx = parsed.get("index") if isinstance(parsed, dict) else None
                    if type(idx) is int and 0 <= idx < len(events):
                        self._last_reject_index = idx
                return POST_REJECT if error.code in PERMANENT_HTTP else POST_RETRY
        except (http.client.HTTPException, OSError, ValueError, RecursionError):
            return POST_RETRY

    def _outbox_dir(self) -> Path:
        directory = self.config.state_dir or contract.default_state_dir()
        assert self.config.endpoint is not None  # only enabled clients spool
        # Legacy files at the state root have no recoverable destination.
        try:
            endpoint = contract.endpoint_origin(self.config.endpoint)
        except contract.ContractError:
            # Directly constructed clients may supply a more specific URL.
            endpoint = self.config.endpoint
        destination = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
        return directory / "collectors" / destination

    def _write_spool(self, path: Path, events: list[dict]) -> bool:
        payload = json.dumps({"schema": contract.SCHEMA, "events": events}, ensure_ascii=False)
        temp = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
                temp = Path(handle.name)
                handle.write(payload + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
            temp = None
            return True
        except OSError:
            # Disk-full/quota failures must be visible to the caller: a silent
            # swallow here lets a merge unlink an already-spooled batch, losing
            # both.
            if temp and temp.exists():
                try:
                    temp.unlink()
                except OSError:
                    pass
            return False

    def _merge_into_newest(self, files: list[Path], events: list[dict]) -> Path | bool | None:
        """Compact the outbox: append to the newest file while the merged
        batch still fits one POST, so 100 files hold up to 10,000 events.

        Returns the newly written Path when the merge succeeded, False when the
        merged write failed (disk full/quota: nothing was changed and the caller
        must keep the batch), or None when merging does not apply.
        """
        if not files:
            return None
        newest = files[-1]
        try:
            existing = contract.validate_batch(json.loads(newest.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError, contract.ContractError):
            return None
        if len(existing) + len(events) > contract.MAX_BATCH_EVENTS:
            return None
        # A pre-lock client may still acknowledge and unlink the old pathname.
        # Publish a different generation before retiring the old one. If a
        # crash leaves both, the collector deduplicates their event IDs.
        name, _ = _allocate_spool_name("outbox", files, newest.parent / _SPOOL_CLOCK_NAME)
        replacement = newest.with_name(name)
        if not self._write_spool(replacement, existing + events):
            return False
        try:
            newest.unlink(missing_ok=True)
        except OSError:
            # The replacement is durable. The predecessor can replay later.
            pass
        self._protected_spool.discard(newest)
        return replacement

    def _spool_batch(
        self,
        events: list[dict],
        prefix: str = "outbox",
        protected: set[Path] | None = None,
    ) -> Path | None:
        with self._spool_lock() as locked:
            if not locked:
                return None
            return self._spool_batch_locked(events, prefix, protected)

    def _spool_batch_locked(
        self,
        events: list[dict],
        prefix: str = "outbox",
        protected: set[Path] | None = None,
    ) -> Path | None:
        """Persist one batch and return the written Path, or None if it could
        not be persisted (disk failure or protected cap reached).
        """
        directory = self._outbox_dir()
        clock_path = directory / _SPOOL_CLOCK_NAME
        files = self._list_spool_files(directory, prefix)
        if files is None and prefix == "outbox":
            if _read_spool_clock(clock_path) is None:
                # Directory exists but cannot be listed and has no readable
                # high-water clock: refuse to write an out-of-order filename.
                return None
        if files is not None and prefix == "outbox":
            merged = self._merge_into_newest(files, events)
            if merged is False:
                return None
            if isinstance(merged, Path):
                return merged
        evictable: list[Path] = []
        need_evict = 0
        if files is not None and len(files) >= MAX_SPOOL_FILES:
            need_evict = max(1, len(files) - MAX_SPOOL_FILES + 1)
            guarded = protected or set()
            evictable = [p for p in files if p not in guarded]
            if len(evictable) < need_evict:
                # Do not evict chunks spooled earlier during the same flush;
                # caller keeps excess chunks in memory until the spool drains.
                return None
        name, clock_persisted = _allocate_spool_name(prefix, files, clock_path=clock_path)
        if files is None and prefix == "outbox" and not clock_persisted:
            return None
        target = directory / name
        if not self._write_spool(target, events):
            return None
        if need_evict:
            for stale in evictable[:need_evict]:
                try:
                    stale.unlink()
                except OSError:
                    pass
        return target

    def _spool(self, events: list[dict], prefix: str = "outbox") -> bool:
        """Persist one batch. Returns False when nothing could be written
        (disk failure): the caller must then keep the batch, never assume it
        was spooled."""
        return self._spool_batch(events, prefix=prefix) is not None

    def _quarantine(self, path: Path) -> bool:
        target = path.with_name("rejected-" + path.name.removeprefix("outbox-"))
        try:
            os.replace(path, target)
        except OSError:
            return False
        existing = self._list_spool_files(target.parent, "rejected")
        if not existing:
            return True
        older = [p for p in existing if p != target]
        if len(older) >= MAX_SPOOL_FILES:
            for stale in older[: max(1, len(older) - MAX_SPOOL_FILES + 1)]:
                try:
                    stale.unlink()
                except OSError:
                    pass
        return True

    def flush_spool(self) -> bool:
        if not self.enabled or not self._has_pending_outbox():
            return True
        with self._spool_lock(replay=True) as acquired:
            if not acquired:
                return False
            return self._replay_spool()

    def _replay_spool(self) -> bool:
        files = self._list_spool_files(self._outbox_dir(), "outbox")
        if files is None:
            return False
        ok = True
        for path in files:
            with self._spool_lock() as locked:
                if not locked:
                    return False
                try:
                    # os.listdir includes directories and symlinks with spool
                    # names. Isolate those entries instead of blocking valid
                    # files or reading through a link to an unrelated path.
                    if not stat.S_ISREG(path.lstat().st_mode):
                        if not self._quarantine(path):
                            return False
                        self._protected_spool.discard(path)
                        ok = False
                        continue
                    snapshot = path.read_bytes()
                except FileNotFoundError:
                    continue
                except PermissionError:
                    # Only isolate a file whose read access is still denied.
                    # Transient I/O failures leave the queue in causal order.
                    if os.access(path, os.R_OK) or not self._quarantine(path):
                        return False
                    self._protected_spool.discard(path)
                    ok = False
                    continue
                except OSError:
                    return False
            try:
                events = contract.validate_batch(json.loads(snapshot))
            except (ValueError, RecursionError):
                # An invalid local batch cannot be delivered.
                events = []
                status, remaining, had_reject = POST_REJECT, events, True
            else:
                status, remaining, had_reject = self._deliver_batch(events)

            with self._spool_lock() as locked:
                if not locked:
                    return False
                try:
                    if path.read_bytes() != snapshot:
                        # A concurrent reader may have isolated rejected rows
                        # during the POST. Leave its changed batch for replay.
                        return False
                except FileNotFoundError:
                    # Compaction can replace this generation while a response
                    # is in flight. A transient POST failure is still a retry.
                    if status == POST_RETRY:
                        return False
                    continue  # Its replacement must remain untouched.
                except OSError:
                    return False

                if had_reject:
                    ok = False
                if status == POST_RETRY:
                    if len(remaining) < len(events):
                        self._write_spool(path, remaining)
                    return False
                if status == POST_REJECT:
                    if len(remaining) == len(events) or self._spool_batch_locked(
                        remaining, prefix="rejected"
                    ) is None:
                        if self._quarantine(path):
                            self._protected_spool.discard(path)
                        ok = False
                        continue
                try:
                    path.unlink()
                    self._protected_spool.discard(path)
                except OSError:
                    ok = False
        return ok


def load_instance_id(config: contract.TelemetryConfig) -> str:
    directory = config.state_dir or contract.default_state_dir()
    path = directory / "instance-id"
    try:
        value = path.read_text(encoding="utf-8").strip()
        if contract.ID_PATTERNS["instance_id"].fullmatch(value):
            return value
    except OSError:
        pass
    value = str(uuid.uuid4())
    temp: Path | None = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as handle:
            temp = Path(handle.name)
            handle.write(value + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        try:
            # POSIX atomic create-only publication: concurrent processes starting
            # on an empty state_dir all converge on the single winning UUID.
            os.link(temp, path)
            return value
        except FileExistsError:
            try:
                winner = path.read_text(encoding="utf-8").strip()
                if contract.ID_PATTERNS["instance_id"].fullmatch(winner):
                    return winner
            except OSError:
                pass
            # Existing file is corrupted/invalid; replace atomically.
            os.replace(temp, path)
            temp = None
            return value
    except OSError:
        return value
    finally:
        if temp is not None:
            try:
                temp.unlink()
            except OSError:
                pass


def client_from_env(env: dict[str, str] | None = None) -> Telemetry:
    return Telemetry(contract.config_from_env(env))
