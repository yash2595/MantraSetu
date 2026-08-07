"""Strongly typed immutable domain models and enums for Navigation Execution Layer in MantraSetu AgentOS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class ExecutionLifecycleState(StrEnum):
    """Enumeration of execution directive lifecycle states."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class UIActionStep:
    """Immutable representation of an individual atomic UI action step."""

    action_id: str
    action_type: str
    target_element_id: str
    page_path: str
    parameters: dict[str, Any] = field(default_factory=dict)
    is_mandatory: bool = True
    sequence_index: int = 1


@dataclass(frozen=True)
class ExecutionCommand:
    """Immutable platform-neutral command representation."""

    command_id: str
    command_type: str
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    sequence_index: int = 1


@dataclass(frozen=True)
class ExecutionDirective:
    """Immutable execution directive emitted to frontend runtimes or automation engines."""

    directive_id: str
    action: str
    target: str
    path_sequence: tuple[str, ...] = field(default_factory=tuple)
    parameters: dict[str, Any] = field(default_factory=dict)
    status: ExecutionLifecycleState = ExecutionLifecycleState.CREATED
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serialize directive to dictionary."""
        return {
            "directive_id": self.directive_id,
            "action": self.action,
            "target": self.target,
            "path_sequence": list(self.path_sequence),
            "parameters": dict(self.parameters),
            "status": self.status.value,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable outcome of plan execution translation."""

    execution_id: str
    status: ExecutionLifecycleState
    directives: tuple[ExecutionDirective, ...] = field(default_factory=tuple)
    completed_steps: int = 0
    failed_step: str | None = None
    error_message: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class ExecutionDiagnostics:
    """Diagnostic snapshot for execution component audit and telemetry."""

    component_name: str
    component_version: str
    started_at: str
    uptime_seconds: float
    timestamp: str
    directives_created: int
    directives_completed: int
    directives_failed: int
    retries_count: int
    timeouts_count: int
    average_execution_latency_ms: float
    thread_safe: bool = True
    memory_usage_estimate: str = "1.2 MB"


@dataclass(frozen=True)
class ExecutionMetadata:
    """Metadata container for execution tracing."""

    session_id: str = ""
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex[:8]}")
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex[:8]}")
    decision_id: str = ""
    plan_id: str = ""
    execution_id: str = field(default_factory=lambda: f"exec_{uuid4().hex[:8]}")
    metadata_version: str = "4.1"
