"""Service Level Agreement (SLA) Compliance & Uptime Reporter v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import SLAReport

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SLAManager"
_COMPONENT_VERSION = "1.0.0"


class SLAManager:
    """Enterprise thread-safe manager tracking SLA uptime percentages and p95 latency targets."""

    def __init__(self) -> None:
        self._reports: list[SLAReport] = []
        self._lock = RLock()
        self._reports_generated_count = 0

    def generate_sla_report(
        self,
        uptime_percentage: float = 99.95,
        p95_latency_ms: float = 12.5,
        target_uptime: float = 99.9,
        target_p95: float = 20.0,
    ) -> SLAReport:
        """Generate a new SLA compliance report."""
        with self._lock:
            self._reports_generated_count += 1
            is_met = (uptime_percentage >= target_uptime) and (p95_latency_ms <= target_p95)

            report = SLAReport(
                uptime_percentage=uptime_percentage,
                p95_latency_ms=p95_latency_ms,
                sla_target_met=is_met,
            )
            self._reports.append(report)
            logger.info("SLAManager generated SLA report: Met=%s (Uptime=%.2f%%, P95=%.2fms)", is_met, uptime_percentage, p95_latency_ms)
            return report

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose SLA manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "reports_generated_count": self._reports_generated_count,
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
