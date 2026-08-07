"""Pre-execution UI action validation engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.execution_models import UIActionStep
from app.navigation.registry import RouteRegistry
from app.navigation.ui_registry import UIRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "UIActionValidatorEngine"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class ActionValidationReport:
    """Immutable validation report returned by UIActionValidatorEngine."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: dict[str, Any] = field(default_factory=dict)


class UIActionValidatorEngine:
    """Engine validating UI action steps against UIRegistry and RouteRegistry before command building."""

    def __init__(
        self,
        registry: RouteRegistry | None = None,
        ui_registry: UIRegistry | None = None,
    ) -> None:
        self._registry = registry or RouteRegistry()
        self._ui_registry = ui_registry or UIRegistry()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._validation_count = 0
        self._failed_validations_count = 0

    def validate_action_steps(self, steps: tuple[UIActionStep, ...] | list[UIActionStep]) -> ActionValidationReport:
        """Validate UI action steps against structural knowledge prior to execution command building."""
        with self._lock:
            self._validation_count += 1
            errors: list[str] = []
            warnings: list[str] = []

            for step in steps:
                # 1. Route Path Validation for NAVIGATE action
                if step.action_type == "NAVIGATE":
                    node = self._registry.match_path(step.target_element_id)
                    if not node and step.target_element_id not in ("/", "/login"):
                        warnings.append(f"Route '{step.target_element_id}' is not registered in RouteRegistry.")

                # 2. UI Element Validation (if element ID targets a specific component)
                if step.action_type not in ("NAVIGATE", "BACK", "FORWARD"):
                    elem = self._ui_registry.get_element(step.target_element_id)
                    if elem:
                        if not elem.is_visible:
                            errors.append(f"Target UI element '{elem.element_id}' is hidden.")
                        if not elem.is_enabled:
                            errors.append(f"Target UI element '{elem.element_id}' is disabled.")

            is_valid = len(errors) == 0
            if not is_valid:
                self._failed_validations_count += 1

            return ActionValidationReport(
                is_valid=is_valid,
                errors=tuple(errors),
                warnings=tuple(warnings),
                diagnostics={"step_count": len(steps)},
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
            message="UIActionValidatorEngine operational.",
        )
