"""Domain models, value objects, and enums for Enterprise Observability, Monitoring & Operations Framework v1.0."""

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

class MetricType(StrEnum):
    """Enumeration of multi-dimensional metric types."""

    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    SUMMARY = "SUMMARY"


class HealthState(StrEnum):
    """Enumeration of subsystem health states."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class AlertSeverity(StrEnum):
    """Enumeration of operational alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TraceState(StrEnum):
    """Enumeration of distributed trace span states."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LogLevel(StrEnum):
    """Enumeration of structured log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceStatus(StrEnum):
    """Enumeration of service operational deployment modes."""

    ONLINE = "ONLINE"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass
class MetricRecord:
    """Model representing an individual multi-dimensional metric sample."""

    metric_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    metric_type: MetricType = MetricType.COUNTER
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "metric_type": str(self.metric_type),
            "value": self.value,
            "labels": dict(self.labels),
            "timestamp": self.timestamp,
        }


@dataclass
class HealthSnapshot:
    """Model representing a heartbeat snapshot of subsystem health."""

    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    subsystem_name: str = "system"
    state: HealthState = HealthState.HEALTHY
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "subsystem_name": self.subsystem_name,
            "state": str(self.state),
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }


@dataclass
class AlertEvent:
    """Model representing a triggered operational alert."""

    alert_id: str = field(default_factory=lambda: str(uuid4()))
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    source_component: str = ""
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": str(self.severity),
            "message": self.message,
            "source_component": self.source_component,
            "timestamp": self.timestamp,
        }


@dataclass
class TraceSpan:
    """Model representing an individual distributed tracing span."""

    span_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    parent_span_id: str | None = None
    name: str = ""
    state: TraceState = TraceState.ACTIVE
    duration_ms: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)
    start_time: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "state": str(self.state),
            "duration_ms": self.duration_ms,
            "tags": dict(self.tags),
            "start_time": self.start_time,
        }


@dataclass
class TraceContext:
    """Model holding trace correlation context."""

    trace_id: str = field(default_factory=lambda: str(uuid4()))
    active_span_id: str = field(default_factory=lambda: str(uuid4()))
    baggage: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "active_span_id": self.active_span_id,
            "baggage": dict(self.baggage),
        }


@dataclass
class StructuredLog:
    """Model representing a structured JSON log entry."""

    log_id: str = field(default_factory=lambda: str(uuid4()))
    level: LogLevel = LogLevel.INFO
    logger_name: str = "app"
    message: str = ""
    trace_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_id": self.log_id,
            "level": str(self.level),
            "logger_name": self.logger_name,
            "message": self.message,
            "trace_id": self.trace_id,
            "context": dict(self.context),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class DashboardSnapshot:
    """Snapshot model for executive operational dashboards."""

    dashboard_id: str = field(default_factory=lambda: str(uuid4()))
    active_metrics_count: int = 0
    active_alerts_count: int = 0
    overall_health: HealthState = HealthState.HEALTHY
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "active_metrics_count": self.active_metrics_count,
            "active_alerts_count": self.active_alerts_count,
            "overall_health": str(self.overall_health),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SLAReport:
    """SLA compliance report model."""

    report_id: str = field(default_factory=lambda: str(uuid4()))
    uptime_percentage: float = 99.99
    p95_latency_ms: float = 12.5
    sla_target_met: bool = True
    generated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "uptime_percentage": self.uptime_percentage,
            "p95_latency_ms": self.p95_latency_ms,
            "sla_target_met": self.sla_target_met,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class ObservabilityHealth:
    """Health status representation of the observability framework."""

    status: str
    active_spans: int
    total_logs: int
    total_metrics: int


@dataclass(frozen=True)
class ObservabilityDiagnostics:
    """Operational diagnostics data object for observability."""

    total_traces_recorded: int
    total_alerts_triggered: int
    average_logging_latency_ms: float
