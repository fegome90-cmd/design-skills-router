"""SQLite persistence and exact aggregate queries for router telemetry.

Raw accepted events are the source of truth. Aggregates are computed from them,
never from sampled traces. Duplicate event IDs and duplicate semantic records
are ignored by unique indexes, which also keeps concurrent retries idempotent.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from . import contract

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  received_at TEXT NOT NULL,
  source TEXT NOT NULL,
  instance_id TEXT NOT NULL,
  evaluation_id TEXT,
  execution_id TEXT,
  router_version TEXT NOT NULL,
  tree_version TEXT NOT NULL,
  route TEXT,
  scope TEXT,
  function_id TEXT,
  node_id TEXT,
  branch_id TEXT,
  skill_id TEXT,
  command TEXT
);
CREATE INDEX IF NOT EXISTS events_name_time ON events(name, occurred_at);
CREATE INDEX IF NOT EXISTS events_evaluation ON events(evaluation_id);
CREATE INDEX IF NOT EXISTS events_execution ON events(execution_id);
CREATE INDEX IF NOT EXISTS events_skill ON events(skill_id);
CREATE UNIQUE INDEX IF NOT EXISTS events_one_invocation
  ON events(evaluation_id) WHERE name = 'router.invoked';
CREATE UNIQUE INDEX IF NOT EXISTS events_one_start
  ON events(execution_id) WHERE name = 'skill.execution_started';
CREATE UNIQUE INDEX IF NOT EXISTS events_one_terminal
  ON events(execution_id)
  WHERE name IN ('skill.execution_completed', 'skill.execution_failed');
CREATE UNIQUE INDEX IF NOT EXISTS events_one_node_visit
  ON events(evaluation_id, node_id) WHERE name = 'decision.node_visited';
CREATE UNIQUE INDEX IF NOT EXISTS events_one_branch
  ON events(evaluation_id, node_id, branch_id) WHERE name = 'decision.branch_selected';
CREATE UNIQUE INDEX IF NOT EXISTS events_one_skill_selection
  ON events(evaluation_id, skill_id) WHERE name = 'skill.selected';
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

COLUMNS = (
    "event_id", "name", "occurred_at", "received_at", "source", "instance_id",
    "evaluation_id", "execution_id", "router_version", "tree_version",
    "route", "scope", "function_id", "node_id", "branch_id", "skill_id", "command",
)


class StoreError(ValueError):
    def __init__(self, code: str, index: int | None = None):
        super().__init__(code)
        self.code = code
        self.index = index


EVALUATION_SCOPED = frozenset({
    "decision.node_visited",
    "decision.branch_selected",
    "skill.selected",
})

# Conservative concentration heuristic for the data_quality signal: one
# installation (instance_id) contributing at least this many events inside a
# window flags the response as possibly inflated. instance_id is a
# self-declared UUID, so this is a visibility signal, not attribution.
INFLATION_SIGNAL_EVENTS = 5000


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema', ?)",
                (contract.SCHEMA,),
            )

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=10000")
            yield connection
        finally:
            connection.close()

    def append(self, events: list[dict], received_at: str | None = None) -> list[dict]:
        """Insert a validated batch atomically. Returns accepted/duplicate per event."""
        stamp = received_at or contract.iso_now()
        results: list[dict] = []
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for index, event in enumerate(events):
                    results.append(self._insert(connection, event, stamp, index))
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return results

    def _insert(self, connection: sqlite3.Connection, event: dict, stamp: str, index: int) -> dict:
        name = event["name"]
        if name in {"skill.execution_started", "skill.execution_completed", "skill.execution_failed"} \
                and event.get("source") != "host":
            raise StoreError("EXECUTION_SOURCE_MUST_BE_HOST", index)
        if name in EVALUATION_SCOPED:
            invocation = connection.execute(
                "SELECT 1 FROM events WHERE name = 'router.invoked' AND evaluation_id = ?",
                (event["evaluation_id"],),
            ).fetchone()
            if invocation is None:
                raise StoreError("INVOCATION_NOT_RECORDED", index)
        if name in {"skill.execution_completed", "skill.execution_failed"}:
            started = connection.execute(
                "SELECT skill_id, instance_id FROM events "
                "WHERE execution_id = ? AND name = 'skill.execution_started'",
                (event["execution_id"],),
            ).fetchone()
            if started is None:
                raise StoreError("EXECUTION_NOT_STARTED", index)
            if started["skill_id"] != event["skill_id"]:
                raise StoreError("EXECUTION_SKILL_MISMATCH", index)
            if started["instance_id"] != event["instance_id"]:
                raise StoreError("EXECUTION_INSTANCE_MISMATCH", index)
            terminal = connection.execute(
                "SELECT 1 FROM events WHERE execution_id = ? "
                "AND name IN ('skill.execution_completed', 'skill.execution_failed')",
                (event["execution_id"],),
            ).fetchone()
            if terminal is not None:
                return {"event_id": event["event_id"], "status": "duplicate"}
        # COLUMNS order puts received_at in the middle; build explicitly.
        values = tuple(
            stamp if column == "received_at" else event.get(column)
            for column in COLUMNS
        )
        try:
            cursor = connection.execute(
                f"INSERT OR IGNORE INTO events({', '.join(COLUMNS)}) "
                f"VALUES({', '.join('?' for _ in COLUMNS)})",
                values,
            )
        except sqlite3.IntegrityError as error:
            # A semantic unique index rejected a repeated evaluation/visit/selection.
            if "UNIQUE" in str(error):
                return {"event_id": event["event_id"], "status": "duplicate"}
            raise StoreError("STORE_INTEGRITY_ERROR", index) from None
        return {
            "event_id": event["event_id"],
            "status": "accepted" if cursor.rowcount == 1 else "duplicate",
        }

    @contextmanager
    def read_snapshot(self):
        """Pin one consistent read snapshot for a whole set of queries.

        A deferred read transaction under WAL mode sees a single point-in-time
        database state without blocking concurrent writers, so one metrics
        response can never mix results from different snapshots.
        """
        with self.connect() as connection:
            connection.execute("BEGIN")
            try:
                yield connection
            finally:
                connection.execute("COMMIT")

    def _where(self, since: str | None, until: str | None) -> tuple[str, list[str]]:
        clauses = []
        params: list[str] = []
        if since:
            clauses.append("occurred_at >= ?")
            params.append(since)
        if until:
            clauses.append("occurred_at <= ?")
            params.append(until)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def metrics(self, since: str | None = None, until: str | None = None, limit: int = 20) -> dict:
        limit = max(1, min(int(limit), 100))
        where, params = self._where(since, until)
        with self.read_snapshot() as connection:
            def scalar(sql: str) -> int:
                row = connection.execute(sql, params).fetchone()
                return int(row[0] or 0)

            totals = {
                "invocations": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'router.invoked'"
                ),
                "evaluations": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'router.invoked' "
                    "AND (source = 'board' OR command IN ('node', 'status'))"
                ),
                "events": scalar(f"SELECT COUNT(*) FROM events{where}"),
                "nodes_visited": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'decision.node_visited'"
                ),
                "branches_selected": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'decision.branch_selected'"
                ),
                "skills_selected": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'skill.selected'"
                ),
                "executions_started": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'skill.execution_started'"
                ),
                "executions_completed": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'skill.execution_completed'"
                ),
                "executions_failed": scalar(
                    f"SELECT COUNT(*) FROM events{where}{' AND' if where else ' WHERE'} name = 'skill.execution_failed'"
                ),
            }

            skill_where = (where + " AND" if where else " WHERE") + \
                " name IN ('skill.selected','skill.execution_started','skill.execution_completed','skill.execution_failed')"
            skills = [
                {
                    "skill_id": row["skill_id"],
                    "selected": int(row["selected"]),
                    "executions_started": int(row["started"]),
                    "executions_completed": int(row["completed"]),
                    "executions_failed": int(row["failed"]),
                }
                for row in connection.execute(
                    "SELECT skill_id,"
                    " SUM(name = 'skill.selected') AS selected,"
                    " SUM(name = 'skill.execution_started') AS started,"
                    " SUM(name = 'skill.execution_completed') AS completed,"
                    " SUM(name = 'skill.execution_failed') AS failed"
                    f" FROM events{skill_where}"
                    " GROUP BY skill_id"
                    " ORDER BY selected DESC, started DESC, skill_id"
                    " LIMIT ?",
                    [*params, limit],
                )
            ]

            # Independent execution ranking: must not depend on how selected a
            # skill is, so it gets its own aggregation, ordering and limit.
            execution_where = (where + " AND" if where else " WHERE") + \
                " name IN ('skill.execution_started','skill.execution_completed','skill.execution_failed')"
            skills_executed = [
                {
                    "skill_id": row["skill_id"],
                    "selected": 0,
                    "executions_started": int(row["started"]),
                    "executions_completed": int(row["completed"]),
                    "executions_failed": int(row["failed"]),
                }
                for row in connection.execute(
                    f"SELECT skill_id,"
                    " SUM(name = 'skill.execution_started') AS started,"
                    " SUM(name = 'skill.execution_completed') AS completed,"
                    " SUM(name = 'skill.execution_failed') AS failed"
                    f" FROM events{execution_where}"
                    " GROUP BY skill_id"
                    " ORDER BY (started + completed + failed) DESC, started DESC, skill_id"
                    " LIMIT ?",
                    [*params, limit],
                )
            ]

            nodes = [
                {"node_id": row["node_id"], "visits": int(row["count"])}
                for row in connection.execute(
                    f"SELECT node_id, COUNT(*) AS count FROM events{where}"
                    f"{' AND' if where else ' WHERE'} name = 'decision.node_visited' "
                    "GROUP BY node_id ORDER BY count DESC, node_id LIMIT ?",
                    [*params, limit],
                )
            ]
            branches = [
                {"node_id": row["node_id"], "branch_id": row["branch_id"], "selected": int(row["count"])}
                for row in connection.execute(
                    f"SELECT node_id, branch_id, COUNT(*) AS count FROM events{where}"
                    f"{' AND' if where else ' WHERE'} name = 'decision.branch_selected' "
                    "GROUP BY node_id, branch_id ORDER BY count DESC, node_id, branch_id LIMIT ?",
                    [*params, limit],
                )
            ]
            routes = [
                {"route": row["route"], "evaluations": int(row["count"])}
                for row in connection.execute(
                    f"SELECT route, COUNT(*) AS count FROM events{where}"
                    f"{' AND' if where else ' WHERE'} name = 'router.invoked' AND route IS NOT NULL "
                    "GROUP BY route ORDER BY count DESC, route LIMIT ?",
                    [*params, limit],
                )
            ]
            sources = [
                {"source": row["source"], "events": int(row["count"])}
                for row in connection.execute(
                    f"SELECT source, COUNT(*) AS count FROM events{where} GROUP BY source ORDER BY source",
                    params,
                )
            ]
            event_counts = {
                row["name"]: int(row["count"])
                for row in connection.execute(
                    f"SELECT name, COUNT(*) AS count FROM events{where} GROUP BY name",
                    params,
                )
            }
            daily: dict[str, dict] = {}
            for row in connection.execute(
                f"SELECT substr(occurred_at, 1, 10) AS day, name, source, command, COUNT(*) AS count "
                f"FROM events{where} GROUP BY day, name, source, command ORDER BY day",
                params,
            ):
                bucket = daily.setdefault(row["day"], {
                    "date": row["day"], "invocations": 0, "evaluations": 0,
                    "selections": 0, "nodes": 0, "started": 0, "completed": 0, "failed": 0,
                })
                count = int(row["count"])
                if row["name"] == "router.invoked":
                    bucket["invocations"] += count
                    if row["source"] == "board" or row["command"] in {"node", "status"}:
                        bucket["evaluations"] += count
                elif row["name"] == "skill.selected":
                    bucket["selections"] += count
                elif row["name"] == "decision.node_visited":
                    bucket["nodes"] += count
                elif row["name"] == "skill.execution_started":
                    bucket["started"] += count
                elif row["name"] == "skill.execution_completed":
                    bucket["completed"] += count
                elif row["name"] == "skill.execution_failed":
                    bucket["failed"] += count
            bounds = connection.execute(
                f"SELECT MIN(occurred_at), MAX(occurred_at), MIN(received_at), MAX(received_at) "
                f"FROM events{where}",
                params,
            ).fetchone()
            # All-time evidence, independent of the requested window: whether
            # an emitter was ever accredited by real accepted events.
            all_time_counts = {
                row["name"]: int(row["count"])
                for row in connection.execute(
                    "SELECT name, COUNT(*) AS count FROM events GROUP BY name"
                )
            }
            # Instance concentration within the requested window, for the
            # data_quality signal.
            instance_stats = connection.execute(
                f"SELECT COUNT(DISTINCT instance_id) AS instances, "
                f"COALESCE(MAX(per_instance), 0) AS max_per_instance FROM "
                f"(SELECT instance_id, COUNT(*) AS per_instance "
                f"FROM events{where} GROUP BY instance_id)",
                params,
            ).fetchone()

        observability = {}
        for name in contract.EVENT_NAMES:
            in_window = event_counts.get(name, 0)
            ever = all_time_counts.get(name, 0)
            if in_window > 0:
                observability[name] = "observed"
            elif name in contract.UNOBSERVABLE_BY_ROUTER and ever == 0:
                # No execution event has ever been accepted: no emitter can be
                # accredited from evidence. An empty window alone must never
                # produce this state, because absence of events inside a
                # window is not evidence that no emitter exists.
                observability[name] = "schema_supported_no_emitter"
            else:
                observability[name] = "observed_zero_events"

        return {
            "schema": "design-router-telemetry-metrics/1",
            "generated_at": contract.iso_now(),
            "window": {"since": since, "until": until},
            "totals": totals,
            "skills": skills,
            "skills_executed": skills_executed,
            "nodes": nodes,
            "branches": branches,
            "routes": routes,
            "sources": sources,
            "event_counts": event_counts,
            "daily": [daily[key] for key in sorted(daily)][-90:],
            "observability": observability,
            "data_quality": {
                "source_of_truth": "accepted_events",
                "sampling": False,
                "exact_event_counts": True,
                "instances": int(instance_stats["instances"]),
                "max_events_per_instance": int(instance_stats["max_per_instance"]),
                # Concentration heuristic, not proof: instance_id is a
                # self-declared installation UUID, so a writer rotating it
                # evades the signal. It makes the anomaly visible to the
                # operator reading this same response.
                "possibly_inflated": int(instance_stats["max_per_instance"]) >= INFLATION_SIGNAL_EVENTS,
                "execution_counts_note": (
                    "Sólo cuentan ejecuciones reportadas por un host que controla la invocación; "
                    "el router no observa la ejecución de skills."
                ),
            },
            "bounds": {
                "first_event_at": bounds[0] if bounds else None,
                "last_event_at": bounds[1] if bounds else None,
                "first_received_at": bounds[2] if bounds else None,
                "last_received_at": bounds[3] if bounds else None,
            },
        }

    def export_events(self, since: str | None = None, until: str | None = None) -> list[dict]:
        where, params = self._where(since, until)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT {', '.join(COLUMNS)} FROM events{where} ORDER BY occurred_at, event_id",
                params,
            ).fetchall()
        return [dict(row) for row in rows]


def open_store(path: str | Path) -> Store:
    return Store(path)
