"""Dedicated Telemetry Aggregator Engine for Multi-Agent Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AgentTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class AgentTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking agent task execution latencies, success rates, and message counts."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._task_latencies: dict[str, list[float]] = {}
        self._success_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}
        self._message_counts: dict[str, int] = {}
        self._total_tasks = 0

    def record_task_executed(self, agent_id: str, execution_time_ms: float, is_success: bool) -> None:
        """Record an agent task execution outcome and latency."""
        with self._lock:
            self._total_tasks += 1
            if agent_id not in self._task_latencies:
                self._task_latencies[agent_id] = []
                self._success_counts[agent_id] = 0
                self._failure_counts[agent_id] = 0

            self._task_latencies[agent_id].append(execution_time_ms)
            if len(self._task_latencies[agent_id]) > 1000:
                self._task_latencies[agent_id].pop(0)

            if is_success:
                self._success_counts[agent_id] += 1
            else:
                self._failure_counts[agent_id] += 1

    def record_message_sent(self, sender_id: str) -> None:
        """Record inter-agent bus message dispatch event."""
        with self._lock:
            self._message_counts[sender_id] = self._message_counts.get(sender_id, 0) + 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute multi-agent telemetry operational statistics."""
        with self._lock:
            agent_stats = {}
            for a_id, l_list in self._task_latencies.items():
                succ = self._success_counts.get(a_id, 0)
                fail = self._failure_counts.get(a_id, 0)
                tot = succ + fail
                avg_l = (sum(l_list) / len(l_list)) if l_list else 0.0
                agent_stats[a_id] = {
                    "total_tasks": tot,
                    "success_count": succ,
                    "failure_count": fail,
                    "success_rate": round((succ / tot), 4) if tot > 0 else 1.0,
                    "average_latency_ms": round(avg_l, 2),
                    "messages_sent": self._message_counts.get(a_id, 0),
                }

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_tasks_processed": self._total_tasks,
                "agent_statistics": agent_stats,
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
