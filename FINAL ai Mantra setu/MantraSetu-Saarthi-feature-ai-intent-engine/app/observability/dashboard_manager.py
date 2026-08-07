"""Executive Operational Dashboard Assembly Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.alert_manager import AlertManager
from app.observability.health_manager import HealthManager
from app.observability.metrics_manager import MetricsManager
from app.observability.observability_models import DashboardSnapshot

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "DashboardManager"
_COMPONENT_VERSION = "1.0.0"


class DashboardManager:
    """Enterprise thread-safe manager assembling executive operational dashboard snapshots."""

    def __init__(
        self,
        metrics_manager: MetricsManager | None = None,
        alert_manager: AlertManager | None = None,
        health_manager: HealthManager | None = None,
    ) -> None:
        self._metrics_manager = metrics_manager or MetricsManager()
        self._alert_manager = alert_manager or AlertManager()
        self._health_manager = health_manager or HealthManager()

        self._lock = RLock()
        self._snapshots_count = 0

    def get_dashboard_snapshot() -> DashboardSnapshot:
        """Assemble current executive operational dashboard snapshot."""
        with self._lock:
            self._snapshots_count += 1
            m_stats = self._metrics_manager.statistics()
            a_alerts = self._alert_manager.get_active_alerts()
            sys_health = self._health_manager.get_system_health()

            snapshot = DashboardSnapshot(
                active_metrics_count=m_stats.get("unique_metrics_count", 0),
                active_alerts_count=len(a_alerts),
                overall_health=sys_health.state,
            )
            logger.debug("DashboardManager assembled snapshot [%s]", sys_health.state)
            return snapshot

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose dashboard manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "snapshots_count": self._snapshots_count,
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
