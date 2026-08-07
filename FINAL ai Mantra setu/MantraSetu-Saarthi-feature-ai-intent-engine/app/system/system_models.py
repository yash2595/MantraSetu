"""Domain models, value objects, and enums for Enterprise AgentOS Integration & System Orchestrator Framework v1.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


class SystemState(StrEnum):
    """Global operational states for AgentOS runtime."""

    UNINITIALIZED = "UNINITIALIZED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"


class FrameworkLifecycleState(StrEnum):
    """Lifecycle states for registered subsystems."""

    REGISTERED = "REGISTERED"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"


@dataclass
class FrameworkMetadata:
    """Metadata specification for a registered AgentOS framework."""

    name: str
    version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    state: FrameworkLifecycleState = FrameworkLifecycleState.REGISTERED
    startup_order: int = 0
    health_status: str = "HEALTHY"
    metrics: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "dependencies": list(self.dependencies),
            "state": str(self.state),
            "startup_order": self.startup_order,
            "health_status": self.health_status,
            "metrics": dict(self.metrics),
            "registered_at": self.registered_at,
        }


@dataclass
class SystemEvent:
    """Cross-framework system event payload for event bus routing."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = "system.general"
    source_framework: str = "System"
    target_framework: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "topic": self.topic,
            "source_framework": self.source_framework,
            "target_framework": self.target_framework,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


@dataclass
class SystemHealthAggregated:
    """Aggregated health representation across all AgentOS frameworks."""

    system_state: SystemState = SystemState.RUNNING
    overall_health: str = "HEALTHY"
    active_frameworks_count: int = 15
    total_frameworks_count: int = 15
    framework_health_map: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_state": str(self.system_state),
            "overall_health": self.overall_health,
            "active_frameworks_count": self.active_frameworks_count,
            "total_frameworks_count": self.total_frameworks_count,
            "framework_health_map": dict(self.framework_health_map),
            "timestamp": self.timestamp,
        }


@dataclass
class SystemDiagnosticsReport:
    """System diagnostic snapshot."""

    report_id: str = field(default_factory=lambda: str(uuid4()))
    system_state: SystemState = SystemState.RUNNING
    frameworks_registered: int = 15
    dependency_graph_valid: bool = True
    active_event_listeners: int = 0
    total_events_dispatched: int = 0
    diagnostics_summary: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "system_state": str(self.system_state),
            "frameworks_registered": self.frameworks_registered,
            "dependency_graph_valid": self.dependency_graph_valid,
            "active_event_listeners": self.active_event_listeners,
            "total_events_dispatched": self.total_events_dispatched,
            "diagnostics_summary": dict(self.diagnostics_summary),
            "timestamp": self.timestamp,
        }
