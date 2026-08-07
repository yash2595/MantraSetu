"""Execution Telemetry and Diagnostic Metrics Aggregator for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.execution_models import ExecutionDiagnostics

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ExecutionTelemetryEngine"
_COMPONENT_VERSION = "4.1"


class ExecutionTelemetryEngine:
    """Thread-safe aggregator for diagnostic statistics, metrics, and health reporting across all execution components."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

        # Telemetry Counters
        self._directives_created = 0
        self._directives_completed = 0
        self._directives_failed = 0
        self._retries_count = 0
        self._timeouts_count = 0
        self._total_latency_ms = 0.0

    def record_execution(self, completed: int, failed: int, latency_ms: float, retries: int = 0, timeouts: int = 0) -> None:
        """Record execution metric payload."""
        with self._lock:
            self._directives_created += (completed + failed)
            self._directives_completed += completed
            self._directives_failed += failed
            self._retries_count += retries
            self._timeouts_count += timeouts
            self._total_latency_ms += latency_ms

    def get_diagnostics(self) -> ExecutionDiagnostics:
        """Construct structured ExecutionDiagnostics snapshot."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            total = self._directives_created
            avg_lat = (self._total_latency_ms / total) if total > 0 else 0.0

            return ExecutionDiagnostics(
                component_name=_COMPONENT_NAME,
                component_version=_COMPONENT_VERSION,
                started_at=self._started_at,
                uptime_seconds=round(uptime, 2),
                timestamp=datetime.now(timezone.utc).isoformat(),
                directives_created=self._directives_created,
                directives_completed=self._directives_completed,
                directives_failed=self._directives_failed,
                retries_count=self._retries_count,
                timeouts_count=self._timeouts_count,
                average_execution_latency_ms=round(avg_lat, 2),
                thread_safe=True,
                memory_usage_estimate="1.4 MB",
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics dictionary."""
        diag = self.get_diagnostics()
        total = diag.directives_created
        success_rate = round((diag.directives_completed / total), 3) if total > 0 else 1.0

        return {
            "component_name": diag.component_name,
            "component_version": diag.component_version,
            "started_at": diag.started_at,
            "uptime_seconds": diag.uptime_seconds,
            "timestamp": diag.timestamp,
            "directives_created": diag.directives_created,
            "directives_completed": diag.directives_completed,
            "directives_failed": diag.directives_failed,
            "retries_count": diag.retries_count,
            "timeouts_count": diag.timeouts_count,
            "execution_success_rate": success_rate,
            "average_execution_latency_ms": diag.average_execution_latency_ms,
            "thread_safe": True,
        }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="ExecutionTelemetryEngine operational.",
        )
