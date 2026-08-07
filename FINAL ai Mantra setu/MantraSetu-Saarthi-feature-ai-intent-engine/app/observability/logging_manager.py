"""Structured JSON Logging & Correlation Manager v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import LogLevel, StructuredLog
from app.observability.observability_telemetry import ObservabilityTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "LoggingManager"
_COMPONENT_VERSION = "1.0.0"


class LoggingManager:
    """Enterprise thread-safe manager dispatching structured JSON logs with correlation tracking (<2ms target)."""

    def __init__(self, telemetry: ObservabilityTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or ObservabilityTelemetryEngine()
        self._logs: list[StructuredLog] = []
        self._lock = RLock()
        self._total_logs_count = 0

    def log(
        self,
        level: LogLevel,
        message: str,
        logger_name: str = "app",
        trace_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> StructuredLog:
        """Dispatch a structured log entry (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._total_logs_count += 1
            context = context or {}

            s_log = StructuredLog(
                level=level,
                logger_name=logger_name,
                message=message,
                trace_id=trace_id,
                context=dict(context),
            )
            self._logs.append(s_log)
            if len(self._logs) > 2000:
                self._logs.pop(0)

            self._telemetry.record_log_dispatched()
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("LoggingManager dispatched log [%s] '%s' in %.2fms", level, message[:30], duration_ms)
            return s_log

    def search_logs(
        self,
        level: LogLevel | None = None,
        trace_id: str | None = None,
    ) -> list[StructuredLog]:
        """Search logs by level or trace_id."""
        with self._lock:
            results = []
            for s in self._logs:
                if level and s.level != level:
                    continue
                if trace_id and s.trace_id != trace_id:
                    continue
                results.append(s)
            return results

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose logging manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "logs_in_memory_count": len(self._logs),
                "total_logs_dispatched_count": self._total_logs_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
