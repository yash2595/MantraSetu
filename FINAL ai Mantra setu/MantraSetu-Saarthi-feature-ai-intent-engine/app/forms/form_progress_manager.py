"""Form Completion & Missing Field Progress Calculator v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.form_models import FormDefinition, FormField, FormProgress

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FormProgressManager"
_COMPONENT_VERSION = "1.0.0"


class FormProgressManager:
    """Enterprise thread-safe manager calculating form completion progress and next prompt field (<2ms target)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._calculations_count = 0

    def calculate_progress(self, form_def: FormDefinition, values: dict[str, Any]) -> FormProgress:
        """Calculate form completion percentage and list missing required fields (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._calculations_count += 1
            total = len(form_def.fields)
            if total == 0:
                return FormProgress(
                    form_id=form_def.form_id,
                    total_fields=0,
                    completed_fields=0,
                    completion_percentage=100.0,
                    missing_required_fields=[],
                )

            completed = 0
            missing_required: list[str] = []

            for field in form_def.fields:
                val = values.get(field.field_name)
                val_str = str(val).strip() if val is not None else ""
                if val_str:
                    completed += 1
                elif field.is_required:
                    missing_required.append(field.field_name)

            pct = round((completed / total) * 100.0, 2)
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("FormProgressManager calculated %.1f%% for form '%s' in %.2fms", pct, form_def.form_id, duration_ms)

            return FormProgress(
                form_id=form_def.form_id,
                total_fields=total,
                completed_fields=completed,
                completion_percentage=pct,
                missing_required_fields=missing_required,
            )

    def get_next_unfilled_field(self, form_def: FormDefinition, values: dict[str, Any]) -> FormField | None:
        """Find the next required unfilled field to prompt the user."""
        with self._lock:
            for field in form_def.fields:
                if field.is_required:
                    val = values.get(field.field_name)
                    if val is None or str(val).strip() == "":
                        return field
            return None

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose progress manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "calculations_count": self._calculations_count,
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
