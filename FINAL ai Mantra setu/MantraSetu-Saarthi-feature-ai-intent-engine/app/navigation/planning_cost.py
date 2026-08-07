"""Multi-dimensional planning cost and execution latency calculation engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.planner_models import PlanningStrategy

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PlanningCostEngine"
_COMPONENT_VERSION = "4.1"


class PlanningCostEngine:
    """Thread-safe, stateless cost calculation engine for graph traversals and plan evaluation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._cost_evaluations_count = 0
        self._total_cost_latency_ms = 0.0

    def calculate_path_cost(
        self,
        path_nodes: tuple[str, ...] | list[str],
        strategy: PlanningStrategy = PlanningStrategy.SHORTEST_PATH,
        requires_auth: bool = False,
        is_redirect: bool = False,
        is_recovery: bool = False,
        is_alternate: bool = False,
        node_metadata_map: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> float:
        """Calculate multi-dimensional route cost deterministically."""
        start_t = time.perf_counter()

        with self._lock:
            nodes = list(path_nodes)
            if not nodes:
                return 0.0

            # 1. Base Step Cost (1.0 unit per transition)
            base_cost = float(max(0, len(nodes) - 1))

            # 2. Strategy Multipliers
            strategy_multiplier = 1.0
            if strategy == PlanningStrategy.WORKFLOW_PATH:
                strategy_multiplier = 0.9  # Preferred workflow path
            elif strategy == PlanningStrategy.RESUME_PATH:
                strategy_multiplier = 0.95
            elif strategy == PlanningStrategy.ALTERNATE_PATH:
                strategy_multiplier = 1.2
            elif strategy == PlanningStrategy.RECOVERY_PATH:
                strategy_multiplier = 1.3

            base_cost *= strategy_multiplier

            # 3. Penalties
            auth_penalty = 10.0 if requires_auth else 0.0
            redirect_penalty = 5.0 if is_redirect else 0.0
            recovery_penalty = 8.0 if is_recovery else 0.0
            alternate_penalty = 3.0 if is_alternate else 0.0

            # 4. Complexity & Metadata Cost additions
            meta_map = node_metadata_map or {}
            complexity_cost = 0.0
            for node_path in nodes:
                meta = meta_map.get(node_path, {})
                params = meta.get("parameters", [])
                forms = meta.get("forms", [])
                complexity_cost += len(params) * 0.2 + len(forms) * 0.5

            total_cost = round(base_cost + auth_penalty + redirect_penalty + recovery_penalty + alternate_penalty + complexity_cost, 3)

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            self._cost_evaluations_count += 1
            self._total_cost_latency_ms += elapsed_ms

            return total_cost

    def estimate_execution_complexity(self, route_metadata: Mapping[str, Any]) -> float:
        """Calculate complexity score (0.0 to 10.0) based on route components and inputs."""
        params = route_metadata.get("parameters", [])
        forms = route_metadata.get("forms", [])
        dropdowns = route_metadata.get("dropdowns", [])
        buttons = route_metadata.get("buttons", [])

        raw_score = len(params) * 1.5 + len(forms) * 2.0 + len(dropdowns) * 0.5 + len(buttons) * 0.2
        return round(min(10.0, raw_score), 2)

    def estimate_execution_latency_ms(self, path_nodes: tuple[str, ...] | list[str], route_metadata_map: Mapping[str, Mapping[str, Any]] | None = None) -> float:
        """Estimate execution latency in milliseconds for a path."""
        meta_map = route_metadata_map or {}
        nodes = list(path_nodes)
        if not nodes:
            return 0.0

        base_step_latency = 15.0  # 15 ms per page transition
        total_latency = float(len(nodes)) * base_step_latency

        for node_path in nodes:
            meta = meta_map.get(node_path, {})
            if meta.get("page_type") in ("CHECKOUT", "AUTHENTICATION"):
                total_latency += 100.0  # Async API/Gateway latency
            if meta.get("requires_auth", False):
                total_latency += 50.0

        return round(total_latency, 2)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic counters for PlanningCostEngine."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            avg_lat = (self._total_cost_latency_ms / self._cost_evaluations_count) if self._cost_evaluations_count > 0 else 0.0
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cost_evaluations_count": self._cost_evaluations_count,
                "average_cost_latency_ms": round(avg_lat, 3),
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
            message="PlanningCostEngine operational.",
        )
