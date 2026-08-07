"""Dedicated Telemetry Aggregator Engine for Voice Form Automation v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FormTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class FormTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking form completion rates, fill times, corrections, and validation errors."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._filled_counts: dict[str, int] = {}
        self._corrected_counts: dict[str, int] = {}
        self._validation_error_counts: dict[str, int] = {}
        self._fill_times: dict[str, list[float]] = {}
        self._submitted_count = 0

    def record_field_filled(self, form_id: str, field_name: str) -> None:
        """Record field populating event."""
        with self._lock:
            key = f"{form_id}:{field_name}"
            self._filled_counts[key] = self._filled_counts.get(key, 0) + 1

    def record_field_corrected(self, form_id: str, field_name: str) -> None:
        """Record user voice field correction event."""
        with self._lock:
            key = f"{form_id}:{field_name}"
            self._corrected_counts[key] = self._corrected_counts.get(key, 0) + 1

    def record_validation_error(self, form_id: str, field_name: str) -> None:
        """Record field validation error event."""
        with self._lock:
            key = f"{form_id}:{field_name}"
            self._validation_error_counts[key] = self._validation_error_counts.get(key, 0) + 1

    def record_form_submitted(self, form_id: str, fill_time_seconds: float) -> None:
        """Record successful form submission event and total fill time."""
        with self._lock:
            self._submitted_count += 1
            if form_id not in self._fill_times:
                self._fill_times[form_id] = []
            self._fill_times[form_id].append(fill_time_seconds)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute form telemetry operational statistics."""
        with self._lock:
            avg_fill_times = {
                k: round(sum(v) / len(v), 2) if v else 0.0 for k, v in self._fill_times.items()
            }
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_forms_submitted": self._submitted_count,
                "average_fill_times_seconds": avg_fill_times,
                "total_fields_filled": sum(self._filled_counts.values()),
                "total_corrections": sum(self._corrected_counts.values()),
                "total_validation_errors": sum(self._validation_error_counts.values()),
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
