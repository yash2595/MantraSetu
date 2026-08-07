"""Planning Telemetry and Diagnostic Metrics Aggregator for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.planner_models import PlanningDiagnostics

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PlanningTelemetryEngine"
_COMPONENT_VERSION = "4.1"


class PlanningTelemetryEngine:
    """Thread-safe aggregator for diagnostic statistics, metrics, and health reporting across all planning components."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

        # Telemetry Counters
        self._plans_generated = 0
        self._shortest_paths_generated = 0
        self._alternate_paths_generated = 0
        self._recovery_plans_generated = 0
        self._rollback_plans_generated = 0
        self._graph_traversals = 0
        self._planner_failures = 0
        self._validation_failures = 0
        self._total_path_length = 0
        self._total_latency_ms = 0.0

    def record_plan(self, strategy_name: str, path_length: int, latency_ms: float, is_success: bool = True) -> None:
        """Record plan generation metric payload."""
        with self._lock:
            self._plans_generated += 1
            self._total_path_length += path_length
            self._total_latency_ms += latency_ms

            if not is_success:
                self._planner_failures += 1

            if strategy_name == "SHORTEST_PATH":
                self._shortest_paths_generated += 1
            elif strategy_name == "ALTERNATE_PATH":
                self._alternate_paths_generated += 1
            elif strategy_name == "RECOVERY_PATH":
                self._recovery_plans_generated += 1
            elif strategy_name == "ROLLBACK_PATH":
                self._rollback_plans_generated += 1

    def record_traversal_event(self) -> None:
        """Record graph traversal metric."""
        with self._lock:
            self._graph_traversals += 1

    def record_validation_failure(self) -> None:
        """Record plan validation failure metric."""
        with self._lock:
            self._validation_failures += 1

    def get_diagnostics(self, cache_stats: dict[str, Any] | None = None) -> PlanningDiagnostics:
        """Construct structured PlanningDiagnostics snapshot."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            avg_len = (self._total_path_length / self._plans_generated) if self._plans_generated > 0 else 0.0
            avg_lat = (self._total_latency_ms / self._plans_generated) if self._plans_generated > 0 else 0.0

            c_hits = cache_stats.get("hits", 0) if cache_stats else 0
            c_misses = cache_stats.get("misses", 0) if cache_stats else 0

            return PlanningDiagnostics(
                component_name=_COMPONENT_NAME,
                component_version=_COMPONENT_VERSION,
                started_at=self._started_at,
                uptime_seconds=round(uptime, 2),
                timestamp=datetime.now(timezone.utc).isoformat(),
                plans_generated=self._plans_generated,
                shortest_paths_generated=self._shortest_paths_generated,
                alternate_paths_generated=self._alternate_paths_generated,
                recovery_plans_generated=self._recovery_plans_generated,
                rollback_plans_generated=self._rollback_plans_generated,
                average_path_length=round(avg_len, 2),
                average_planning_latency_ms=round(avg_lat, 2),
                graph_traversals=self._graph_traversals,
                cache_hits=c_hits,
                cache_misses=c_misses,
                thread_safe=True,
                memory_usage_estimate="1.5 MB",
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics dictionary."""
        diag = self.get_diagnostics()
        return {
            "component_name": diag.component_name,
            "component_version": diag.component_version,
            "started_at": diag.started_at,
            "uptime_seconds": diag.uptime_seconds,
            "timestamp": diag.timestamp,
            "plans_generated": diag.plans_generated,
            "shortest_paths_generated": diag.shortest_paths_generated,
            "alternate_paths_generated": diag.alternate_paths_generated,
            "recovery_plans_generated": diag.recovery_plans_generated,
            "rollback_plans_generated": diag.rollback_plans_generated,
            "average_path_length": diag.average_path_length,
            "average_planning_latency_ms": diag.average_planning_latency_ms,
            "graph_traversals": diag.graph_traversals,
            "planner_failures": self._planner_failures,
            "validation_failures": self._validation_failures,
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
            message="PlanningTelemetryEngine operational.",
        )
