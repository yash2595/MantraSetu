"""Enterprise Observability Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import RequestDiagnostics

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "EnterpriseObservabilityManager"
_COMPONENT_VERSION = "4.1"
_SUPPORTED_CONTRACT_VERSION = "4.1"
_COMPATIBILITY_VERSION = "4.0"


class EnterpriseObservabilityManager:
    """Read-only telemetry and distributed tracing correlation manager for AI Orchestrator."""

    def __init__(self) -> None:
        self._traces: dict[str, RequestDiagnostics] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._spans_recorded_count = 0

    def record_trace(self, diagnostics: RequestDiagnostics) -> None:
        """Record a completed request trace diagnostics snapshot."""
        with self._lock:
            self._traces[diagnostics.request_id] = diagnostics
            self._spans_recorded_count += 1

    def get_version_info(self) -> dict[str, str]:
        """Return component versioning strategy information."""
        return {
            "component_version": _COMPONENT_VERSION,
            "supported_contract_version": _SUPPORTED_CONTRACT_VERSION,
            "compatibility_version": _COMPATIBILITY_VERSION,
        }

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return observability statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "supported_contract_version": _SUPPORTED_CONTRACT_VERSION,
                "compatibility_version": _COMPATIBILITY_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "spans_recorded_count": self._spans_recorded_count,
                "recorded_traces_count": len(self._traces),
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="EnterpriseObservabilityManager operational.",
        )
