"""Alternate and fallback route planning engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.planner_models import AlternateNavigationPlan, NavigationStep, PlanningStrategy
from app.navigation.registry import RouteRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AlternateRoutePlannerEngine"
_COMPONENT_VERSION = "4.1"


class AlternateRoutePlannerEngine:
    """Engine synthesizing intelligent fallback navigation plans when primary target paths are unavailable."""

    def __init__(self, registry: RouteRegistry | None = None) -> None:
        self._registry = registry or RouteRegistry()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._alternate_plans_count = 0

    def plan_alternate_route(
        self,
        current_route: str,
        blocked_target: str,
        reason: str = "",
    ) -> AlternateNavigationPlan:
        """Synthesize an AlternateNavigationPlan using semantic or capability matching."""
        with self._lock:
            self._alternate_plans_count += 1
            alt_id = f"alt_{uuid4().hex[:8]}"
            blocked_node = self._registry.match_path(blocked_target)
            diagnostics: dict[str, Any] = {
                "blocked_target": blocked_target,
                "current_route": current_route,
                "reason": reason,
            }

            alternate_target = "/"
            if blocked_node and blocked_node.metadata:
                parent = blocked_node.metadata.get("parent")
                capabilities = blocked_node.metadata.get("page_capabilities", [])

                if capabilities:
                    # Find route sharing same capabilities
                    cap_routes = self._registry.get_routes_by_capability(capabilities[0])
                    for r in cap_routes:
                        if r.url != blocked_target and r.url != current_route:
                            alternate_target = r.url
                            diagnostics["fallback_type"] = "capability_match"
                            break

                if alternate_target == "/" and parent:
                    alternate_target = parent
                    diagnostics["fallback_type"] = "parent_fallback"

            step = NavigationStep(
                step_id="alt_step_1",
                step_index=1,
                source_route=current_route,
                target_route=alternate_target,
                action_type="NAVIGATE",
                description=f"Alternate fallback navigation to '{alternate_target}' as '{blocked_target}' is blocked.",
                is_mandatory=True,
            )

            return AlternateNavigationPlan(
                alternate_id=alt_id,
                primary_target=blocked_target,
                alternate_target=alternate_target,
                strategy=PlanningStrategy.ALTERNATE_PATH,
                steps=(step,),
                confidence=0.85,
                reason=f"Primary target '{blocked_target}' blocked ({reason}). Fallback to '{alternate_target}'.",
                diagnostics=diagnostics,
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alternate_plans_count": self._alternate_plans_count,
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
            message="AlternateRoutePlannerEngine operational.",
        )
