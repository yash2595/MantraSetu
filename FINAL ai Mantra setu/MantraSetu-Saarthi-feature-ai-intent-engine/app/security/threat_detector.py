"""Realtime Anomaly Detection & Threat Analysis Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.security.security_models import SecurityIncident, ThreatLevel
from app.security.security_telemetry import SecurityTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ThreatDetector"
_COMPONENT_VERSION = "1.0.0"


class ThreatDetector:
    """Enterprise thread-safe engine detecting access anomalies, rate-limit attacks, and security threats."""

    def __init__(self, telemetry: SecurityTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or SecurityTelemetryEngine()
        self._failed_attempts: dict[str, list[float]] = {}
        self._incidents: list[SecurityIncident] = []
        self._lock = RLock()
        self._threats_evaluated_count = 0

    def evaluate_threat(self, client_ip: str, user_id: str, action: str) -> SecurityIncident | None:
        """Evaluate request metadata for brute-force or rate-limit anomalies."""
        with self._lock:
            self._threats_evaluated_count += 1
            now = time.time()

            key = f"{client_ip}:{user_id}"
            if key not in self._failed_attempts:
                self._failed_attempts[key] = []

            # Prune entries older than 60s
            self._failed_attempts[key] = [t for t in self._failed_attempts[key] if (now - t) < 60.0]

            # Detect rapid repeat actions
            if len(self._failed_attempts[key]) >= 10:
                incident = SecurityIncident(
                    threat_level=ThreatLevel.HIGH,
                    description=f"Rate limit anomaly detected for {user_id} from IP {client_ip}",
                    source_ip=client_ip,
                )
                self._incidents.append(incident)
                self._telemetry.record_threat_detected(ThreatLevel.HIGH)
                logger.warning("ThreatDetector identified incident on IP '%s': %s", client_ip, incident.description)
                return incident

            self._failed_attempts[key].append(now)
            return None

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose threat detector operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "threats_evaluated_count": self._threats_evaluated_count,
                "total_incidents_detected": len(self._incidents),
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
