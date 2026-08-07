"""Dedicated Telemetry Aggregator Engine for Security & Identity Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.security.security_models import ThreatLevel

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SecurityTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class SecurityTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking failed logins, permission denials, threats, and audit events."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._auth_latencies: list[float] = []
        self._authz_latencies: list[float] = []
        self._failed_logins_count = 0
        self._permission_denials_count = 0
        self._threats_detected_count = 0
        self._total_audit_events = 0

    def record_authentication_attempt(self, is_success: bool, latency_ms: float) -> None:
        """Record an authentication attempt latency and outcome."""
        with self._lock:
            self._auth_latencies.append(latency_ms)
            if len(self._auth_latencies) > 1000:
                self._auth_latencies.pop(0)
            if not is_success:
                self._failed_logins_count += 1

    def record_authorization_attempt(self, is_granted: bool, latency_ms: float) -> None:
        """Record an authorization attempt latency and outcome."""
        with self._lock:
            self._authz_latencies.append(latency_ms)
            if len(self._authz_latencies) > 1000:
                self._authz_latencies.pop(0)
            if not is_granted:
                self._permission_denials_count += 1

    def record_threat_detected(self, threat_level: ThreatLevel) -> None:
        """Record a threat/anomaly detection event."""
        with self._lock:
            self._threats_detected_count += 1

    def record_audit_event(self) -> None:
        """Record an audit event count."""
        with self._lock:
            self._total_audit_events += 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute security telemetry operational statistics."""
        with self._lock:
            avg_auth = round(sum(self._auth_latencies) / len(self._auth_latencies), 2) if self._auth_latencies else 0.0
            avg_authz = round(sum(self._authz_latencies) / len(self._authz_latencies), 2) if self._authz_latencies else 0.0

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "failed_logins_count": self._failed_logins_count,
                "permission_denials_count": self._permission_denials_count,
                "threats_detected_count": self._threats_detected_count,
                "total_audit_events": self._total_audit_events,
                "average_auth_latency_ms": avg_auth,
                "average_authz_latency_ms": avg_authz,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
