"""Alert Rule Evaluation & Escalation Manager v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import AlertEvent, AlertSeverity
from app.observability.observability_telemetry import ObservabilityTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AlertManager"
_COMPONENT_VERSION = "1.0.0"


class AlertManager:
    """Enterprise thread-safe manager evaluating alert rules and deduplicating triggers (<2ms target)."""

    def __init__(self, telemetry: ObservabilityTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or ObservabilityTelemetryEngine()
        self._alerts: list[AlertEvent] = []
        self._lock = RLock()
        self._alerts_triggered_count = 0

    def trigger_alert(
        self,
        rule_name: str,
        severity: AlertSeverity,
        message: str,
        source_component: str = "system",
    ) -> AlertEvent | None:
        """Trigger an operational alert if deduplication checks pass (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            # Deduplicate matching active alerts
            for a in self._alerts:
                if a.rule_name == rule_name and a.severity == severity:
                    return None

            self._alerts_triggered_count += 1
            alert = AlertEvent(
                rule_name=rule_name,
                severity=severity,
                message=message,
                source_component=source_component,
            )
            self._alerts.append(alert)
            self._telemetry.record_alert_triggered()

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.warning("AlertManager triggered alert [%s - %s]: %s in %.2fms", rule_name, severity, message, duration_ms)
            return alert

    def get_active_alerts(self) -> list[AlertEvent]:
        """Retrieve active alert events."""
        with self._lock:
            return list(self._alerts)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose alert manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_alerts_count": len(self._alerts),
                "alerts_triggered_count": self._alerts_triggered_count,
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
