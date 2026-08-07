"""Dedicated Telemetry Aggregator Engine for Observability Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ObservabilityTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class ObservabilityTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking logging, metrics collection, tracing spans, and operational events."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry counts
        self._logs_dispatched_count = 0
        self._metrics_collected_count = 0
        self._spans_created_count = 0
        self._alerts_triggered_count = 0

    def record_log_dispatched(self) -> None:
        """Record a log dispatch event."""
        with self._lock:
            self._logs_dispatched_count += 1

    def record_metric_collected(self) -> None:
        """Record a metric collection event."""
        with self._lock:
            self._metrics_collected_count += 1

    def record_trace_span(self) -> None:
        """Record a trace span creation event."""
        with self._lock:
            self._spans_created_count += 1

    def record_alert_triggered(self) -> None:
        """Record an alert trigger event."""
        with self._lock:
            self._alerts_triggered_count += 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute observability telemetry operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "logs_dispatched_count": self._logs_dispatched_count,
                "metrics_collected_count": self._metrics_collected_count,
                "spans_created_count": self._spans_created_count,
                "alerts_triggered_count": self._alerts_triggered_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
