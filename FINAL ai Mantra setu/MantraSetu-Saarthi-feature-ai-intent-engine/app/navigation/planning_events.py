"""Enterprise diagnostic planning events for MantraSetu AgentOS."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PlanningEventType(StrEnum):
    """Enumeration of diagnostic planning event types."""

    PLAN_CREATED = "PLAN_CREATED"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    PLAN_REJECTED = "PLAN_REJECTED"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    RECOVERY_PLAN_CREATED = "RECOVERY_PLAN_CREATED"
    ALTERNATE_PLAN_CREATED = "ALTERNATE_PLAN_CREATED"
    PLANNING_FAILED = "PLANNING_FAILED"


@dataclass(frozen=True)
class PlanningEvent:
    """Immutable diagnostic planning event artifact."""

    event_type: PlanningEventType
    event_id: str = field(default_factory=lambda: f"evt_{uuid4().hex[:8]}")
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex[:8]}")
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex[:8]}")
    decision_id: str = ""
    session_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize planning event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }
