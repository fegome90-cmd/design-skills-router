"""Event contract and opt-in configuration for Design Skills Router telemetry.

This module is deliberately dependency-free. It defines what may be counted and
what must never be collected. It does not store or send events.

The opt-in configuration contract is OFF by default, requires explicit
enablement, enforces budgeted timeouts, and restricts remote endpoints to HTTPS
outside loopback.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import os
import re
from urllib.parse import urlsplit

SCHEMA = "design-router-telemetry/1"
CONTRACT_VERSION = "1.0.0"

ROUTER_VERSION = "1.4.0"
TREE_VERSION = "0.4"

EVENT_NAMES = (
    "router.invoked",
    "decision.node_visited",
    "decision.branch_selected",
    "skill.selected",
    "skill.execution_started",
    "skill.execution_completed",
    "skill.execution_failed",
)

EXECUTION_NAMES = frozenset({
    "skill.execution_started",
    "skill.execution_completed",
    "skill.execution_failed",
})

UNOBSERVABLE_BY_ROUTER = frozenset({
    "skill.execution_started",
    "skill.execution_completed",
    "skill.execution_failed",
})

# Identifiers are stable catalog/tree references, never free text.
ID_PATTERNS = {
    "instance_id": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    "evaluation_id": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    "execution_id": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    "event_id": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    "router_version": re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,31}$"),
    "tree_version": re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,31}$"),
    "route": re.compile(r"^[a-z][a-z0-9_-]{0,31}$"),
    "scope": re.compile(r"^[a-z][a-z0-9_-]{0,31}$"),
    "function_id": re.compile(r"^[a-z][a-z0-9_-]{0,63}$"),
    "node_id": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    "branch_id": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    "skill_id": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"),
    "command": re.compile(r"^[a-z][a-z0-9_-]{0,31}$"),
}

COMMON_KEYS = frozenset({
    "event_id", "name", "occurred_at", "source", "instance_id",
    "router_version", "tree_version",
})

EVENT_KEYS = {
    "router.invoked": frozenset({"evaluation_id", "route", "scope", "function_id", "command"}),
    "decision.node_visited": frozenset({"evaluation_id", "node_id"}),
    "decision.branch_selected": frozenset({"evaluation_id", "node_id", "branch_id"}),
    "skill.selected": frozenset({"evaluation_id", "skill_id", "function_id"}),
    "skill.execution_started": frozenset({"execution_id", "skill_id"}),
    "skill.execution_completed": frozenset({"execution_id", "skill_id"}),
    "skill.execution_failed": frozenset({"execution_id", "skill_id"}),
}

EVENT_REQUIRED = {
    "router.invoked": frozenset({"evaluation_id"}),
    "decision.node_visited": frozenset({"evaluation_id", "node_id"}),
    "decision.branch_selected": frozenset({"evaluation_id", "node_id", "branch_id"}),
    "skill.selected": frozenset({"evaluation_id", "skill_id"}),
    "skill.execution_started": frozenset({"execution_id", "skill_id"}),
    "skill.execution_completed": frozenset({"execution_id", "skill_id"}),
    "skill.execution_failed": frozenset({"execution_id", "skill_id"}),
}

SOURCES = frozenset({"board", "cli", "host"})

MAX_BATCH_EVENTS = 100
MAX_BODY_BYTES = 64 * 1024
MAX_ID_LENGTH = 128


class ContractError(ValueError):
    """Validation failure that never echoes the rejected value."""

    def __init__(self, index: int | None, code: str):
        super().__init__(code)
        self.index = index
        self.code = code


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool
    endpoint: str | None = None
    token: str | None = None
    timeout_seconds: float = 0.5
    state_dir: Path | None = None


DISABLED = TelemetryConfig(enabled=False)


def _loopback(hostname: str) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}


def endpoint_origin(value: object) -> str:
    """Validate an OTLP-style base origin before URL normalization hides syntax."""
    invalid = "INVALID_TELEMETRY_ENDPOINT"
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ContractError(None, invalid)
    if not re.match(r"^https?://[^\s\\/?#@]+/?$", value, re.IGNORECASE):
        raise ContractError(None, invalid)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise ContractError(None, invalid) from None
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ContractError(None, invalid)
    if parts.scheme == "http" and not _loopback(parts.hostname):
        raise ContractError(None, invalid)
    if parts.username or parts.password or parts.path not in {"", "/"} or parts.query or parts.fragment:
        raise ContractError(None, invalid)
    if port == 0:
        raise ContractError(None, invalid)
    return f"{parts.scheme}://{parts.netloc}"


def _bounded_timeout(value: object) -> float:
    if value is None:
        return 0.5
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            raise ContractError(None, "INVALID_TELEMETRY_TIMEOUT") from None
    else:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ContractError(None, "INVALID_TELEMETRY_TIMEOUT") from None
    if not 0.1 <= number <= 5.0:
        raise ContractError(None, "INVALID_TELEMETRY_TIMEOUT")
    return number


def config_from_env(env: Mapping[str, str] | None = None) -> TelemetryConfig:
    """Resolve explicit opt-in configuration. Never reads the environment at import."""
    source = os.environ if env is None else env
    if source.get("DESIGN_ROUTER_TELEMETRY") != "1":
        return DISABLED
    endpoint = endpoint_origin(source.get("DESIGN_ROUTER_TELEMETRY_URL"))
    token = source.get("DESIGN_ROUTER_TELEMETRY_TOKEN") or None
    if token is not None and not token.strip():
        raise ContractError(None, "INVALID_TELEMETRY_TOKEN")
    timeout = _bounded_timeout(source.get("DESIGN_ROUTER_TELEMETRY_TIMEOUT"))
    state = source.get("DESIGN_ROUTER_TELEMETRY_STATE")
    state_dir = Path(state).expanduser() if state else default_state_dir(source)
    return TelemetryConfig(True, endpoint, token, timeout, state_dir)


def default_state_dir(env: Mapping[str, str] | None = None) -> Path:
    source: Mapping[str, str] = os.environ if env is None else env
    base = source.get("XDG_STATE_HOME")
    if base:
        return Path(base).expanduser() / "design-router"
    return Path.home() / ".local" / "state" / "design-router"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError(None, "INVALID_OCCURRED_AT")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        raise ContractError(None, "INVALID_OCCURRED_AT") from None
    if parsed.tzinfo is None:
        raise ContractError(None, "INVALID_OCCURRED_AT")
    return parsed.astimezone(timezone.utc)


def validate_event(event: object, index: int = 0, now: datetime | None = None) -> dict:
    """Return a normalized event or raise ContractError without echoing values."""
    if not isinstance(event, dict):
        raise ContractError(index, "EVENT_OBJECT_REQUIRED")
    name = event.get("name")
    if not isinstance(name, str) or name not in EVENT_NAMES:
        raise ContractError(index, "UNKNOWN_EVENT")
    allowed = COMMON_KEYS | EVENT_KEYS[name]
    extra = set(event) - allowed
    if extra:
        # The code names the rejected field class, never its value.
        if any(str(key).lower() in {
            "prompt", "messages", "message", "text", "content", "email", "user",
            "user_id", "path", "url", "ip", "reason", "summary", "quote",
        } for key in extra):
            raise ContractError(index, "SENSITIVE_FIELD_REJECTED")
        raise ContractError(index, "UNKNOWN_FIELD")
    missing = EVENT_REQUIRED[name] - set(event)
    if missing:
        raise ContractError(index, "REQUIRED_FIELD_MISSING")
    for key in COMMON_KEYS:
        if key not in event:
            raise ContractError(index, "REQUIRED_FIELD_MISSING")
    source = event.get("source")
    if source not in SOURCES:
        raise ContractError(index, "UNKNOWN_SOURCE")
    # Execution can only be asserted by a host that controlled the invocation.
    if name in EXECUTION_NAMES and source != "host":
        raise ContractError(index, "EXECUTION_SOURCE_MUST_BE_HOST")
    for key, pattern in ID_PATTERNS.items():
        value = event.get(key)
        if value is None:
            if key in event:
                # An explicit JSON null in an identifier field is never
                # "absent": SQLite unique indexes treat NULLs as distinct,
                # which would defeat every semantic deduplication index.
                raise ContractError(index, "INVALID_" + key.upper())
            continue
        if not isinstance(value, str) or len(value) > MAX_ID_LENGTH or not pattern.fullmatch(value):
            raise ContractError(index, "INVALID_" + key.upper())
    occurred = parse_time(event["occurred_at"])
    reference = now or datetime.now(timezone.utc)
    # Accept delayed outbox deliveries, but reject far-future timestamps.
    delta = (reference - occurred).total_seconds()
    if delta < -7 * 24 * 60 * 60 or delta > 365 * 24 * 60 * 60:
        raise ContractError(index, "OCCURRED_AT_OUT_OF_RANGE")
    normalized = dict(event)
    normalized["occurred_at"] = occurred.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return normalized


def validate_batch(payload: object, now: datetime | None = None) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ContractError(None, "INVALID_BATCH_SCHEMA")
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise ContractError(None, "EVENTS_REQUIRED")
    if len(events) > MAX_BATCH_EVENTS:
        raise ContractError(None, "BATCH_TOO_LARGE")
    normalized = [validate_event(event, index, now) for index, event in enumerate(events)]
    seen = set()
    for index, event in enumerate(normalized):
        if event["event_id"] in seen:
            raise ContractError(index, "DUPLICATE_EVENT_IN_BATCH")
        seen.add(event["event_id"])
    return normalized
