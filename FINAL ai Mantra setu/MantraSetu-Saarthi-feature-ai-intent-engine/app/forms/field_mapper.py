"""Semantic Slot-to-Field Mapping Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.form_models import FieldValue, FormDefinition, FormField

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FieldMapper"
_COMPONENT_VERSION = "1.0.0"


class FieldMapper:
    """Enterprise thread-safe engine mapping conversation slots to frontend form fields using semantic labels and aliases (<2ms target)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._mappings_count = 0

    def map_slot_to_field(
        self,
        form_def: FormDefinition,
        slot_name: str,
        slot_value: Any,
    ) -> tuple[FormField | None, float]:
        """Map a single conversation slot name to a target FormField and return confidence score (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._mappings_count += 1
            slot_clean = slot_name.lower().strip()

            # 1. Exact match on field_name
            for field in form_def.fields:
                if field.field_name.lower() == slot_clean:
                    duration_ms = (time.perf_counter() - start_ts) * 1000
                    logger.debug("FieldMapper exact match '%s' -> '%s' in %.2fms", slot_name, field.field_name, duration_ms)
                    return (field, 1.0)

            # 2. Match on aliases
            for field in form_def.fields:
                if slot_clean in [a.lower() for a in field.aliases]:
                    duration_ms = (time.perf_counter() - start_ts) * 1000
                    logger.debug("FieldMapper alias match '%s' -> '%s' in %.2fms", slot_name, field.field_name, duration_ms)
                    return (field, 0.9)

            # 3. Partial substring match
            for field in form_def.fields:
                if slot_clean in field.field_name.lower() or field.field_name.lower() in slot_clean:
                    duration_ms = (time.perf_counter() - start_ts) * 1000
                    return (field, 0.7)

            return (None, 0.0)

    def map_slots_batch(
        self,
        form_def: FormDefinition,
        slots: dict[str, Any],
    ) -> dict[str, FieldValue]:
        """Batch map conversation slots to a dictionary of FieldValue objects."""
        with self._lock:
            mapped_values: dict[str, FieldValue] = {}
            for s_name, s_val in slots.items():
                if s_val is None:
                    continue
                matched_field, conf = self.map_slot_to_field(form_def, s_name, s_val)
                if matched_field and conf >= 0.6:
                    mapped_values[matched_field.field_name] = FieldValue(
                        field_name=matched_field.field_name,
                        value=s_val,
                        confidence=conf,
                    )
            return mapped_values

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose field mapper operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "mappings_count": self._mappings_count,
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
