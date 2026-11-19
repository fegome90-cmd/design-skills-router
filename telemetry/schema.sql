-- Reference schema for the minimal Design Skills Router collector (SQLite).
-- The collector applies this idempotently at startup. Raw accepted events are
-- the source of truth; counters are computed, never stored as mutable totals.

PRAGMA journal_mode = WAL;

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

-- Semantic idempotency: retries with a new event_id must not inflate counters.
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
