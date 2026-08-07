"""Enterprise diagnostic execution events for MantraSetu AgentOS."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionEventType(StrEnum):
    """Enumeration of diagnostic execution event types."""

    COMMAND_CREATED = "COMMAND_CREATED"
    COMMAND_SENT = "COMMAND_SENT"
    COMMAND_RECEIVED = "COMMAND_RECEIVED"
    ACTION_STARTED = "ACTION_STARTED"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    ACTION_FAILED = "ACTION_FAILED"
    ACTION_RETRY = "ACTION_RETRY"
    ACTION_TIMEOUT = "ACTION_TIMEOUT"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    SESSION_RECOVERED = "SESSION_RECOVERED"
    EXECUTION_ABORTED = "EXECUTION_ABORTED"


@dataclass(frozen=True)
class ExecutionEvent:
    """Immutable diagnostic execution event artifact."""

    event_type: ExecutionEventType
    event_id: str = field(default_factory=lambda: f"evt_exec_{uuid4().hex[:8]}")
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex[:8]}")
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex[:8]}")
    decision_id: str = ""
    plan_id: str = ""
    execution_id: str = ""
    session_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize execution event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "plan_id": self.plan_id,
            "execution_id": self.execution_id,
            "session_id": self.session_id,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }
