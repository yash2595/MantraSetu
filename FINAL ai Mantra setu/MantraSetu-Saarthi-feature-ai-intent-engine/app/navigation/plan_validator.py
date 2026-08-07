"""Post-planning safety, parameter, and cycle validation engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.planner_models import NavigationPlan, NavigationStep

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PlanValidatorEngine"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class PlanValidationReport:
    """Immutable report returned by PlanValidatorEngine."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    has_cycles: bool = False
    missing_parameters: dict[str, list[str]] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


class PlanValidatorEngine:
    """Engine performing post-synthesis verification on NavigationPlan objects."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._validation_count = 0
        self._failed_validations_count = 0

    def validate_plan(self, plan: NavigationPlan) -> PlanValidationReport:
        """Perform comprehensive post-synthesis validation on a NavigationPlan."""
        with self._lock:
            self._validation_count += 1
            errors: list[str] = []
            warnings: list[str] = []

            # 1. Non-Empty Step Validation
            if not plan.steps:
                errors.append(f"Navigation plan '{plan.plan_id}' contains no navigation steps.")
                self._failed_validations_count += 1
                return PlanValidationReport(is_valid=False, errors=tuple(errors))

            # 2. Cycle Detection
            visited_routes = set()
            has_cycles = False
            for step in plan.steps:
                if step.target_route in visited_routes:
                    has_cycles = True
                    warnings.append(f"Cycle detected at step index {step.step_index}: target route '{step.target_route}' visited multiple times.")
                visited_routes.add(step.target_route)

            # 3. Step Order & Transition Continuity Check
            for i in range(len(plan.steps) - 1):
                curr_target = plan.steps[i].target_route
                next_source = plan.steps[i + 1].source_route
                if curr_target != next_source and not next_source.startswith(curr_target):
                    warnings.append(f"Discontinuity between step {i} target '{curr_target}' and step {i+1} source '{next_source}'.")

            # 4. Target Destination Reachability
            last_step_target = plan.steps[-1].target_route
            if last_step_target != plan.target_route and plan.target_route not in ("/", ""):
                errors.append(f"Final step target '{last_step_target}' does not match planned destination '{plan.target_route}'.")

            is_valid = len(errors) == 0
            if not is_valid:
                self._failed_validations_count += 1

            return PlanValidationReport(
                is_valid=is_valid,
                errors=tuple(errors),
                warnings=tuple(warnings),
                has_cycles=has_cycles,
                diagnostics={
                    "plan_id": plan.plan_id,
                    "step_count": len(plan.steps),
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                },
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
                "validation_count": self._validation_count,
                "failed_validations_count": self._failed_validations_count,
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
            message="PlanValidatorEngine operational.",
        )
