"""Directive lifecycle state monitoring engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.execution_models import ExecutionDirective, ExecutionLifecycleState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ExecutionMonitorEngine"
_COMPONENT_VERSION = "4.1"


class ExecutionMonitorEngine:
    """Engine tracking non-blocking lifecycle states of active execution directives."""

    def __init__(self) -> None:
        self._directives: dict[str, ExecutionDirective] = {}
        self._states: dict[str, ExecutionLifecycleState] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

        # Telemetry
        self._directives_registered_count = 0
        self._directives_completed_count = 0
        self._directives_failed_count = 0

    def register_directive(self, directive: ExecutionDirective) -> None:
        """Register a new execution directive for monitoring."""
        with self._lock:
            self._directives[directive.directive_id] = directive
            self._states[directive.directive_id] = directive.status
            self._directives_registered_count += 1

    def update_status(self, directive_id: str, new_status: ExecutionLifecycleState) -> None:
        """Update lifecycle state of an active execution directive."""
        with self._lock:
            if directive_id in self._directives:
                old = self._directives[directive_id]
                updated = ExecutionDirective(
                    directive_id=old.directive_id,
                    action=old.action,
                    target=old.target,
                    path_sequence=old.path_sequence,
                    parameters=dict(old.parameters),
                    status=new_status,
                    created_at=old.created_at,
                )
                self._directives[directive_id] = updated
                self._states[directive_id] = new_status

                if new_status == ExecutionLifecycleState.COMPLETED:
                    self._directives_completed_count += 1
                elif new_status == ExecutionLifecycleState.FAILED:
                    self._directives_failed_count += 1

    def get_status(self, directive_id: str) -> ExecutionLifecycleState | None:
        """Return active lifecycle state for a directive ID."""
        with self._lock:
            return self._states.get(directive_id)

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
                "directives_registered_count": self._directives_registered_count,
                "directives_completed_count": self._directives_completed_count,
                "directives_failed_count": self._directives_failed_count,
                "active_monitoring_count": len(self._directives),
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
            message="ExecutionMonitorEngine operational.",
        )
