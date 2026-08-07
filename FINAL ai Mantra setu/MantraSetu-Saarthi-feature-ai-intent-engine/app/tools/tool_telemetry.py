"""Dedicated Telemetry Aggregator Engine for AI Tool Calling Framework v1.1."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolTelemetryEngine"
_COMPONENT_VERSION = "1.1.0"


class ToolTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking tool invocation latencies, success rates, retries, and timeouts."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._latencies: dict[str, list[float]] = {}
        self._success_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}
        self._retry_counts: dict[str, int] = {}
        self._timeout_counts: dict[str, int] = {}
        self._total_invocations = 0

    def record_invocation(self, tool_name: str, execution_time_ms: float, is_success: bool) -> None:
        """Record tool execution latency and outcome status."""
        with self._lock:
            self._total_invocations += 1
            if tool_name not in self._latencies:
                self._latencies[tool_name] = []
                self._success_counts[tool_name] = 0
                self._failure_counts[tool_name] = 0

            self._latencies[tool_name].append(execution_time_ms)
            if len(self._latencies[tool_name]) > 1000:
                self._latencies[tool_name].pop(0)

            if is_success:
                self._success_counts[tool_name] += 1
            else:
                self._failure_counts[tool_name] += 1

    def record_timeout(self, tool_name: str) -> None:
        """Record tool execution timeout event."""
        with self._lock:
            self._timeout_counts[tool_name] = self._timeout_counts.get(tool_name, 0) + 1

    def record_retry(self, tool_name: str) -> None:
        """Record tool execution retry event."""
        with self._lock:
            self._retry_counts[tool_name] = self._retry_counts.get(tool_name, 0) + 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute tool telemetry operational statistics."""
        with self._lock:
            tool_stats = {}
            for t_name, l_list in self._latencies.items():
                succ = self._success_counts.get(t_name, 0)
                fail = self._failure_counts.get(t_name, 0)
                tot = succ + fail
                avg_l = (sum(l_list) / len(l_list)) if l_list else 0.0
                tool_stats[t_name] = {
                    "total_invocations": tot,
                    "success_count": succ,
                    "failure_count": fail,
                    "success_rate": round((succ / tot), 4) if tot > 0 else 1.0,
                    "average_latency_ms": round(avg_l, 2),
                    "retry_count": self._retry_counts.get(t_name, 0),
                    "timeout_count": self._timeout_counts.get(t_name, 0),
                }

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_invocations": self._total_invocations,
                "tool_statistics": tool_stats,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report telemetry engine health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
