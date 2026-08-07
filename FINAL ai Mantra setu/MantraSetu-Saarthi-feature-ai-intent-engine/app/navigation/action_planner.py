"""UI Action Planning Engine decomposing navigation plans into atomic UI interaction sequences."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.execution_models import UIActionStep
from app.navigation.planner_models import NavigationPlan

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "UIActionPlannerEngine"
_COMPONENT_VERSION = "4.1"


class UIActionPlannerEngine:
    """Engine decomposing high-level navigation plan steps into atomic UIActionStep sequences."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._action_plans_count = 0

    def plan_ui_actions(self, plan: NavigationPlan) -> tuple[UIActionStep, ...]:
        """Decompose NavigationPlan into an ordered sequence of atomic UIActionStep objects."""
        with self._lock:
            self._action_plans_count += 1
            action_steps: list[UIActionStep] = []
            idx = 1

            for step in plan.steps:
                # 1. Navigation Transition Step
                act_id = f"act_{uuid4().hex[:8]}"
                action_steps.append(
                    UIActionStep(
                        action_id=act_id,
                        action_type=step.action_type,
                        target_element_id=step.target_route,
                        page_path=step.source_route,
                        parameters=dict(step.required_parameters),
                        is_mandatory=step.is_mandatory,
                        sequence_index=idx,
                    )
                )
                idx += 1

                # 2. Check for secondary form or submit parameters
                if step.required_parameters and "form" in step.required_parameters:
                    sub_act_id = f"act_sub_{uuid4().hex[:8]}"
                    action_steps.append(
                        UIActionStep(
                            action_id=sub_act_id,
                            action_type="SUBMIT",
                            target_element_id=str(step.required_parameters["form"]),
                            page_path=step.target_route,
                            parameters=dict(step.required_parameters),
                            is_mandatory=True,
                            sequence_index=idx,
                        )
                    )
                    idx += 1

            return tuple(action_steps)

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
                "action_plans_count": self._action_plans_count,
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
            message="UIActionPlannerEngine operational.",
        )
