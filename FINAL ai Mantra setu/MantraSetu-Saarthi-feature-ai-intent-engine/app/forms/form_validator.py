"""Field Type, Regex & Form Constraint Validator Engine v1.0."""

from __future__ import annotations

import logging
import re
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.form_models import FieldValidation, FormDefinition, FormField, ValidationState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FormValidator"
_COMPONENT_VERSION = "1.0.0"


class FormValidator:
    """Enterprise thread-safe form and field validation engine (<3ms target)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._validations_count = 0
        self._failures_count = 0

    def validate_field(self, field: FormField, value: Any) -> FieldValidation:
        """Validate a single field value against schema constraints (<3ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._validations_count += 1
            val_str = str(value).strip() if value is not None else ""

            # Required field check
            if field.is_required and not val_str:
                self._failures_count += 1
                return FieldValidation(
                    field_name=field.field_name,
                    state=ValidationState.FAILED,
                    error_message=f"Field '{field.field_label or field.field_name}' is required.",
                )

            # Regex validation check
            if val_str and field.validation_regex:
                if not re.match(field.validation_regex, val_str):
                    self._failures_count += 1
                    return FieldValidation(
                        field_name=field.field_name,
                        state=ValidationState.FAILED,
                        error_message=f"Field '{field.field_name}' value '{value}' failed regex rule.",
                    )

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("FormValidator passed for field '%s' in %.2fms", field.field_name, duration_ms)
            return FieldValidation(
                field_name=field.field_name,
                state=ValidationState.PASSED,
            )

    def validate_form(
        self,
        form_def: FormDefinition,
        values: dict[str, Any],
    ) -> tuple[bool, list[FieldValidation]]:
        """Validate all fields in a form definition (<3ms target)."""
        with self._lock:
            reports: list[FieldValidation] = []
            is_all_valid = True

            for field in form_def.fields:
                val = values.get(field.field_name)
                rep = self.validate_field(field, val)
                reports.append(rep)
                if rep.state == ValidationState.FAILED:
                    is_all_valid = False

            return (is_all_valid, reports)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose validator operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "validations_count": self._validations_count,
                "failures_count": self._failures_count,
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
