"""Interruption and failure recovery route planning engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.planner_models import NavigationStep, RecoveryPlan
from app.navigation.registry import RouteRegistry
from app.navigation.workflow_graph import WorkflowGraphEngine, WorkflowTransitionStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RecoveryPlannerEngine"
_COMPONENT_VERSION = "4.1"


class RecoveryPlannerEngine:
    """Engine generating deterministic recovery plans for interrupted, failed, or detoured user journeys."""

    def __init__(
        self,
        registry: RouteRegistry | None = None,
        workflow_graph: WorkflowGraphEngine | None = None,
    ) -> None:
        self._registry = registry or RouteRegistry()
        self._workflow_graph = workflow_graph or WorkflowGraphEngine()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._recovery_plans_count = 0

    def plan_recovery(
        self,
        current_route: str,
        failure_reason: str = "",
        active_workflow: str | None = None,
        checkpoint_step: str | None = None,
        history: list[str] | None = None,
        retry_count: int = 1,
    ) -> RecoveryPlan:
        """Synthesize a structured RecoveryPlan for navigation interruption or failure."""
        with self._lock:
            self._recovery_plans_count += 1
            rec_id = f"rec_{uuid4().hex[:8]}"
            hist = list(history or [])
            diagnostics: dict[str, Any] = {
                "current_route": current_route,
                "active_workflow": active_workflow,
                "failure_reason": failure_reason,
            }

            # 1. Payment Interruption Recovery
            if "payment" in failure_reason.lower() or current_route == "/payment":
                step = NavigationStep(
                    step_id="rec_step_payment",
                    step_index=1,
                    source_route=current_route,
                    target_route="/payment",
                    action_type="NAVIGATE",
                    description="Resume payment checkout procedure.",
                    required_parameters={"booking_id": "REQ"},
                    is_mandatory=True,
                )
                return RecoveryPlan(
                    recovery_id=rec_id,
                    reason=f"Payment recovery initiated: {failure_reason}",
                    recovery_steps=(step,),
                    retry_count=retry_count,
                    target_checkpoint="/payment",
                    estimated_cost=8.0,
                    diagnostics=diagnostics,
                )

            # 2. Workflow Detour / Interruption Recovery
            if active_workflow:
                wf_result = self._workflow_graph.recover_interruption(active_workflow, current_route, hist)
                target_node = wf_result.target_node
                target_path = target_node.route_path if target_node else "/"
                checkpoint_id = wf_result.current_step_id

                step = NavigationStep(
                    step_id=f"rec_step_{checkpoint_id.lower()}",
                    step_index=1,
                    source_route=current_route,
                    target_route=target_path,
                    action_type="NAVIGATE",
                    description=f"Recover workflow '{active_workflow}' at step '{checkpoint_id}'.",
                    is_mandatory=True,
                )
                return RecoveryPlan(
                    recovery_id=rec_id,
                    reason=f"Workflow recovery initiated for '{active_workflow}' at step '{checkpoint_id}'.",
                    recovery_steps=(step,),
                    retry_count=retry_count,
                    target_checkpoint=checkpoint_id,
                    estimated_cost=5.0,
                    diagnostics=diagnostics,
                )

            # 3. Default Home / Root Fallback Recovery
            fallback_route = checkpoint_step or "/"
            step = NavigationStep(
                step_id="rec_step_fallback",
                step_index=1,
                source_route=current_route,
                target_route=fallback_route,
                action_type="NAVIGATE",
                description=f"Recovery fallback navigation to '{fallback_route}'.",
                is_mandatory=True,
            )
            return RecoveryPlan(
                recovery_id=rec_id,
                reason=f"General navigation recovery fallback to '{fallback_route}'.",
                recovery_steps=(step,),
                retry_count=retry_count,
                target_checkpoint=fallback_route,
                estimated_cost=10.0,
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
                "recovery_plans_count": self._recovery_plans_count,
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
            message="RecoveryPlannerEngine operational.",
        )
