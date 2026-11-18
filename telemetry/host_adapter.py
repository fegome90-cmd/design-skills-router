"""Host-side execution observation contract.

The router never invokes skills, so it cannot observe their execution. A host
that actually controls the invocation may use this context manager around the
call. Only then are `skill.execution_*` counters produced. There is no host
integration in this repository yet; without one, execution totals stay at zero
and the dashboard says so.

Example (inside a host that really invokes the skill):

    client = client_from_env()
    with observe_execution(client, "fegome90-cmd/my-skills/break-ui"):
        host.invoke_skill("break-ui")
"""

from __future__ import annotations

import uuid

from .client import Telemetry


class ExecutionObservation:
    def __init__(self, client: Telemetry, skill_id: str, execution_id: str | None = None):
        self.client = client
        self.skill_id = skill_id
        self.execution_id = execution_id or str(uuid.uuid4())
        self.started = False
        self.finished = False

    def __enter__(self):
        if self.client.enabled:
            try:
                self.client.emit(
                    "skill.execution_started",
                    execution_id=self.execution_id,
                    skill_id=self.skill_id,
                    source="host",
                )
                self.client.flush()
                self.started = True
            except Exception:
                # Telemetry must never block or alter the host invocation.
                self.started = False
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.started and not self.finished:
            name = "skill.execution_failed" if exc_type else "skill.execution_completed"
            try:
                self.client.emit(
                    name,
                    execution_id=self.execution_id,
                    skill_id=self.skill_id,
                    source="host",
                )
                self.client.flush()
                self.finished = True
            except Exception:
                pass
        return False


def observe_execution(client: Telemetry, skill_id: str, execution_id: str | None = None) -> ExecutionObservation:
    return ExecutionObservation(client, skill_id, execution_id)
