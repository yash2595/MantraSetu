"""Domain models, value objects, and enums for Enterprise Multi-Agent Collaboration Framework v1.0."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Centralized Enums
# ----------------------------------------------------------------------

class AgentType(StrEnum):
    """Enumeration of agent structural archetypes."""

    SUPERVISOR = "SUPERVISOR"
    WORKER = "WORKER"
    SPECIALIST = "SPECIALIST"
    VALIDATOR = "VALIDATOR"
    ROUTER = "ROUTER"


class AgentState(StrEnum):
    """Enumeration of agent lifecycle states."""

    IDLE = "IDLE"
    BUSY = "BUSY"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    OFFLINE = "OFFLINE"


class AgentRole(StrEnum):
    """Enumeration of specialized domain roles assigned to agents."""

    COORDINATOR = "COORDINATOR"
    SEARCH_AGENT = "SEARCH_AGENT"
    PUJA_AGENT = "PUJA_AGENT"
    KUNDALI_AGENT = "KUNDALI_AGENT"
    FORM_AGENT = "FORM_AGENT"
    AUDITOR = "AUDITOR"


class TaskPriority(StrEnum):
    """Enumeration of task execution priorities."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(StrEnum):
    """Enumeration of task execution lifecycle statuses."""

    CREATED = "CREATED"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MessageType(StrEnum):
    """Enumeration of inter-agent communication message types."""

    DIRECT = "DIRECT"
    BROADCAST = "BROADCAST"
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"
    RESULT_RESPONSE = "RESULT_RESPONSE"
    HEARTBEAT = "HEARTBEAT"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass
class AgentDefinition:
    """Enterprise model defining a registered specialized agent capability."""

    agent_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    agent_type: AgentType = AgentType.WORKER
    role: AgentRole = AgentRole.SEARCH_AGENT
    capabilities: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    state: AgentState = AgentState.IDLE
    registered_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "agent_type": str(self.agent_type),
            "role": str(self.role),
            "capabilities": list(self.capabilities),
            "version": self.version,
            "state": str(self.state),
            "registered_at": self.registered_at,
        }


@dataclass
class AgentTask:
    """Model representing an atomic task unit delegated to a worker agent."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    assigned_agent_id: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.CREATED
    dependencies: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "assigned_agent_id": self.assigned_agent_id,
            "priority": str(self.priority),
            "status": str(self.status),
            "dependencies": list(self.dependencies),
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }


@dataclass
class AgentMessage:
    """Structured immutable message frame for inter-agent bus communication."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    sender_id: str = ""
    receiver_id: str = "BROADCAST"
    msg_type: MessageType = MessageType.DIRECT
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "msg_type": str(self.msg_type),
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class AgentResponse:
    """Immutable output payload produced by worker agent task execution."""

    response_id: str
    task_id: str
    agent_id: str
    status: TaskStatus
    data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": str(self.status),
            "data": dict(self.data),
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class AgentContext:
    """Shared read-only runtime context provided to executing agents."""

    session_id: str = ""
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    shared_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "shared_data": dict(self.shared_data),
        }


@dataclass
class AgentExecutionPlan:
    """Model defining a decomposed master plan for goal execution."""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    goal: str = ""
    tasks: list[AgentTask] = field(default_factory=list)
    is_parallel: bool = False
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "is_parallel": self.is_parallel,
            "dependency_graph": {k: list(v) for k, v in self.dependency_graph.items()},
        }


@dataclass(frozen=True)
class AgentHealth:
    """Health status representation of a registered agent."""

    agent_id: str
    state: AgentState
    active_tasks_count: int
    last_heartbeat: str


@dataclass(frozen=True)
class AgentDiagnostics:
    """Operational diagnostics data object for an agent."""

    agent_id: str
    total_tasks_completed: int
    average_execution_time_ms: float
    failure_count: int
