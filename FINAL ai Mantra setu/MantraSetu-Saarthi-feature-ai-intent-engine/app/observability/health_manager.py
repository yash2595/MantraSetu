"""System Subsystem Health & Availability Aggregator v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import HealthSnapshot, HealthState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "HealthManager"
_COMPONENT_VERSION = "1.0.0"


class HealthManager:
    """Enterprise thread-safe manager collecting heartbeat snapshots across all AgentOS subsystems (<2ms target)."""

    def __init__(self) -> None:
        self._snapshots: dict[str, HealthSnapshot] = {}
        self._lock = RLock()
        self._health_checks_count = 0

    def register_health(
        self,
        subsystem_name: str,
        state: HealthState,
        details: dict[str, Any] | None = None,
    ) -> HealthSnapshot:
        """Register a heartbeat snapshot for a subsystem (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._health_checks_count += 1
            details = details or {}

            snapshot = HealthSnapshot(
                subsystem_name=subsystem_name,
                state=state,
                details=dict(details),
            )
            self._snapshots[subsystem_name] = snapshot

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("HealthManager registered health for '%s': %s in %.2fms", subsystem_name, state, duration_ms)
            return snapshot

    def get_system_health(self) -> HealthSnapshot:
        """Aggregate system-wide overall HealthSnapshot."""
        with self._lock:
            states = [s.state for s in self._snapshots.values()]
            if HealthState.UNHEALTHY in states:
                overall = HealthState.UNHEALTHY
            elif HealthState.DEGRADED in states:
                overall = HealthState.DEGRADED
            else:
                overall = HealthState.HEALTHY

            return HealthSnapshot(
                subsystem_name="AgentOS_System",
                state=overall,
                details={"monitored_subsystems": len(self._snapshots)},
            )

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose health manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "monitored_subsystems_count": len(self._snapshots),
                "health_checks_count": self._health_checks_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
