"""Immutable Security Audit Trail & Compliance Logger v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.security.security_models import AuditAction, SecurityAudit
from app.security.security_telemetry import SecurityTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AuditManager"
_COMPONENT_VERSION = "1.0.0"


class AuditManager:
    """Enterprise thread-safe manager creating immutable security audit trails for compliance."""

    def __init__(self, telemetry: SecurityTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or SecurityTelemetryEngine()
        self._audit_logs: list[SecurityAudit] = []
        self._lock = RLock()

    def log_audit(
        self,
        user_id: str,
        action: AuditAction,
        resource: str = "",
        status: str = "SUCCESS",
        trace_id: str = "",
    ) -> SecurityAudit:
        """Create and log an immutable SecurityAudit record."""
        with self._lock:
            audit = SecurityAudit(
                user_id=user_id,
                action=action,
                resource=resource,
                status=status,
                trace_id=trace_id,
            )
            self._audit_logs.append(audit)
            self._telemetry.record_audit_event()
            logger.info("AuditManager logged audit record [%s - %s] for user '%s'", action, status, user_id)
            return audit

    def get_audit_logs(self, user_id: str | None = None) -> list[SecurityAudit]:
        """Retrieve audit history, optionally filtered by user_id."""
        with self._lock:
            if user_id is None:
                return list(self._audit_logs)
            return [a for a in self._audit_logs if a.user_id == user_id]

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose audit manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "total_audit_logs": len(self._audit_logs),
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
